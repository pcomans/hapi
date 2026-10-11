"""#337 re-registration: per-case Stage 1 review through headless Claude Code (`claude -p`).

The same audited role prompt, system prompt, response schema, cases and validation as
`run_claude_review.py`, run on the Claude Code subscription instead of the billed API. Each
case is a separate `claude -p` process in a fresh empty directory, so no project CLAUDE.md,
memory or other case can reach it, with only the WebSearch and WebFetch tools, no MCP
servers, and ANTHROPIC_API_KEY removed from its environment.

Each case's complete record is persisted before its decision is used (Constitutional Rule
13): the exact command, system prompt and user content, and the full stream-json event log
verbatim (every message, each search query with its result titles and URLs, each fetch with
its HTTP status, size and the page summary the model received, the final answer, usage).

Fail loud (Rule 2): API-key (billed) auth, any tool beyond the two web tools, an MCP
server, a model other than the requested one, an unparseable or schema-invalid answer, a
wrong case ID or evidence hash, a case decided without a search result or successful
fetch, or a search result or fetch on a blocked domain stops the run after the case's
record is written.

    pipeline/.venv/bin/python \\
      docs/evaluations/authority-independent-control-2026-10-11/scripts/run_harness_review.py \\
      --queue <run>/review/stage-1-queue.json --reviewer A --out <private dir> \\
      --case-id review-unit-014
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import jsonschema

from run_claude_review import (
    RESPONSE_SCHEMA,
    ROLE_PROMPT,
    SYSTEM_PROMPT_PATH,
    ReviewFailure,
    compose_user_content,
    sha256_bytes,
    write_atomic,
)

MODEL_ALIAS = "sonnet"
SERVED_MODEL = "claude-sonnet-5-5"
EFFORT = "high"
TOOLS = ("WebFetch", "WebSearch")
BLOCKED_DOMAINS = ("wikidata.org", "github.com", "raw.githubusercontent.com")


def command(system_prompt: str, user_content: str) -> list[str]:
    return [
        "claude", "-p", user_content,
        "--model", MODEL_ALIAS,
        "--effort", EFFORT,
        "--system-prompt", system_prompt,
        "--tools", ",".join(TOOLS),
        "--allowedTools", *TOOLS,
        "--strict-mcp-config",
        "--output-format", "stream-json",
        "--verbose",
        "--no-session-persistence",
    ]


def _blocked(url: str | None) -> bool:
    host = (urlparse(url or "").hostname or "").lower()
    return any(host == domain or host.endswith("." + domain) for domain in BLOCKED_DOMAINS)


def review_case(case: dict, role_prompt: str, schema: dict, system_prompt: str) -> dict:
    user_content = compose_user_content(case, role_prompt, schema)
    argv = command(system_prompt, user_content)
    record = {
        "case_id": case["case_id"],
        "evidence_sha256": case["evidence_sha256"],
        "requested_model": MODEL_ALIAS,
        "parameters": {"effort": EFFORT, "tools": list(TOOLS), "mcp_servers": []},
        "command": argv[:2] + ["<user_content>"] + argv[3:],
        "system_prompt": system_prompt,
        "user_content": user_content,
        "user_content_sha256": sha256_bytes(user_content.encode("utf-8")),
    }
    env = {key: value for key, value in os.environ.items() if key != "ANTHROPIC_API_KEY"}
    with tempfile.TemporaryDirectory(prefix="hapi-337-review-") as cwd:
        proc = subprocess.run(argv, capture_output=True, text=True, cwd=cwd, env=env)
    record["exit_code"] = proc.returncode
    record["stderr"] = proc.stderr
    try:
        events = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    except json.JSONDecodeError as err:
        record["stdout"] = proc.stdout
        record["failure"] = f"stream is not JSON lines: {err}"
        return record
    record["events"] = events

    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), None)
    if init is None:
        record["failure"] = "no init event"
        return record
    record["served_model"] = init.get("model")
    record["auth"] = init.get("apiKeySource")
    if init.get("apiKeySource") != "none":
        record["failure"] = f"API-key auth would bill this call: {init.get('apiKeySource')!r}"
        return record
    if sorted(init.get("tools") or []) != sorted(TOOLS) or init.get("mcp_servers"):
        record["failure"] = f"unexpected tools {init.get('tools')} or MCP servers {init.get('mcp_servers')}"
        return record
    if init.get("model") != SERVED_MODEL:
        record["failure"] = f"served model {init.get('model')!r}, not {SERVED_MODEL!r}"
        return record

    blocks = [
        (e["type"], b, e.get("tool_use_result"))
        for e in events if e.get("type") in ("assistant", "user")
        and isinstance(e["message"].get("content"), list)
        for b in e["message"]["content"]
    ]
    calls = {b["id"]: b for kind, b, _ in blocks if b.get("type") == "tool_use"}
    record["stated_text"] = [b["text"] for kind, b, _ in blocks if kind == "assistant" and b.get("type") == "text"]
    record["thinking"] = [b.get("thinking", "") for kind, b, _ in blocks if b.get("type") == "thinking"]
    record["web_searches"] = [b["input"].get("query") for b in calls.values() if b["name"] == "WebSearch"]
    record["web_search_results"] = []
    record["web_fetches"] = []
    for kind, b, result in blocks:
        if b.get("type") != "tool_result" or not isinstance(result, dict):
            continue
        name = calls[b["tool_use_id"]]["name"]
        if name == "WebSearch":
            record["web_search_results"].extend(
                {"title": item.get("title"), "url": item.get("url")}
                for group in result.get("results") or [] if isinstance(group, dict)
                for item in group.get("content") or []
            )
        elif name == "WebFetch":
            record["web_fetches"].append({
                "url": calls[b["tool_use_id"]]["input"].get("url"),
                "status_code": result.get("code"), "bytes": result.get("bytes"),
            })
    final = next((e for e in reversed(events) if e.get("type") == "result"), None)
    record["usage"] = final.get("usage") if final else None
    record["notional_cost_usd"] = final.get("total_cost_usd") if final else None

    if not record["stated_text"]:
        record["failure"] = "no final text"
        return record
    text = record["stated_text"][-1].strip()
    record["final_text"] = text
    try:
        decision = json.loads(text)
        jsonschema.validate(decision, schema)
    except (json.JSONDecodeError, jsonschema.ValidationError) as err:
        record["failure"] = f"invalid decision: {type(err).__name__}: {str(err)[:500]}"
        return record
    if decision["case_id"] != case["case_id"] or decision["evidence_sha256"] != case["evidence_sha256"]:
        record["failure"] = "decision does not echo the case ID and evidence hash exactly"
        return record
    if not record["web_search_results"] and not any(f["status_code"] == 200 for f in record["web_fetches"]):
        record["failure"] = "case decided without a search result or successful fetch"
        return record
    touched = [r["url"] for r in record["web_search_results"]] + [f["url"] for f in record["web_fetches"]]
    if any(_blocked(url) for url in touched):
        record["failure"] = f"blocked domain used: {[u for u in touched if _blocked(u)]}"
        return record
    record["decision"] = decision
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", type=Path, required=True)
    ap.add_argument("--reviewer", required=True, help="independent reviewer label, e.g. A or B")
    ap.add_argument("--out", type=Path, required=True, help="private output directory")
    ap.add_argument("--case-id", action="append", help="review only these case IDs (pilot)")
    args = ap.parse_args()

    queue = json.loads(args.queue.read_text("utf-8"))
    cases = queue["cases"]
    if args.case_id:
        unknown = set(args.case_id) - {c["case_id"] for c in cases}
        if unknown:
            raise ReviewFailure(f"unknown case IDs: {sorted(unknown)}")
        cases = [c for c in cases if c["case_id"] in set(args.case_id)]
    role_prompt = ROLE_PROMPT.read_text("utf-8")
    system_prompt = SYSTEM_PROMPT_PATH.read_text("utf-8")
    schema = json.loads(RESPONSE_SCHEMA.read_text("utf-8"))
    out = args.out / f"reviewer-{args.reviewer}"
    out.mkdir(parents=True, exist_ok=True)

    for case in cases:
        path = out / f"{case['case_id']}.json"
        if path.exists():
            raise ReviewFailure(f"{path} already exists; records are never overwritten")
        record = review_case(case, role_prompt, schema, system_prompt)
        record["reviewer"] = args.reviewer
        write_atomic(path, record)
        status = record.get("failure") or (
            f"{record['decision']['same_entity']} / {record['decision']['useful_granularity']}"
        )
        print(f"[harness {args.reviewer}] {case['case_id']}: {status} | searches "
              f"{len(record.get('web_searches', []))} | fetches "
              f"{sum(f['status_code'] == 200 for f in record.get('web_fetches', []))}/"
              f"{len(record.get('web_fetches', []))} ok", flush=True)
        if "failure" in record:
            raise ReviewFailure(f"{case['case_id']}: {record['failure']} (record: {path})")
    print(f"[harness {args.reviewer}] {len(cases)} cases reviewed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
