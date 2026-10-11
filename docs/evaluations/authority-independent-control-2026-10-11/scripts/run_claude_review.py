"""#337 re-registration: per-case Stage 1 review with Claude Sonnet 5.5, web search and web fetch.

One API conversation per case per reviewer. Every reviewer is an independent run over the
same queue (separate calls, no shared context). Each case's complete record is persisted
before its decision is used (Constitutional Rule 13): the request parameters, system prompt,
user content, every response round verbatim (thinking, web-search queries and results,
final text, fetched pages), the served model, token usage, and the validated decision. An LLM call cannot
be re-executed to reproduce a decision; this record is what is re-read.

Fail loud (Rule 2): a refusal, an unparseable or schema-invalid answer, a wrong case ID or
evidence hash, a case decided without any web search or successful web fetch, or an exhausted pause_turn budget
stops the run after the case's record is written. No automatic fallback to another model:
a refusal must not silently change which model reviewed a case.

    ANTHROPIC_API_KEY=... pipeline/.venv/bin/python \\
      docs/evaluations/authority-independent-control-2026-10-11/scripts/run_claude_review.py \\
      --queue <run>/review/stage-1-queue.json --reviewer A --out <private dir> --limit 5
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import anthropic
import jsonschema

EVALUATION_ROOT = Path(__file__).resolve().parents[1]
ROLE_PROMPT = EVALUATION_ROOT / "prompts" / "stage-1-reviewer-v3.txt"
SYSTEM_PROMPT_PATH = EVALUATION_ROOT / "launcher-instructions" / "review-system-v2.txt"
RESPONSE_SCHEMA = EVALUATION_ROOT / "raw-response-contracts" / "stage-1-reviewer-case-v1.schema.json"

MODEL = "claude-sonnet-5-5"
# Committed request parameters. Thinking is adaptive (the model thinks when the case calls
# for it) with display "summarized" so the reasoning text is returned; effort is set
# explicitly so the record states it. Web search finds pages; web fetch opens the shown
# museum record URLs directly, and its page text is returned (and recorded) in plain text.
# Blocked on both tools, enforcing the role prompt: "Never use Wikidata", and "Do not search
# for, open or cite this evaluation's repository" (the repository is public on GitHub).
BLOCKED_DOMAINS = ["wikidata.org", "github.com", "raw.githubusercontent.com"]
PARAMETERS = {
    "max_tokens": 32000,
    "thinking": {"type": "adaptive", "display": "summarized"},
    "output_config": {"effort": "high"},
    "tools": [
        {"type": "web_search_20260209", "name": "web_search", "max_uses": 99,
         "blocked_domains": BLOCKED_DOMAINS},
        {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 99,
         "max_content_tokens": 20000, "blocked_domains": BLOCKED_DOMAINS},
    ],
}
# pause_turn resumptions per case: the server pauses every 10 sampling iterations, and up to
# 99 searches can need about 10 resumptions.
MAX_CONTINUATIONS = 20

# Claude Sonnet 5.5 list prices (USD per million tokens; web search per request), for the
# cost estimate reported with the run. Cache writes are estimated at the input price.
PRICE = {"input": 2.00, "output": 10.00, "cache_read": 0.20, "web_search": 0.01}


class ReviewFailure(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def compose_user_content(case: dict, role_prompt: str, schema: dict) -> str:
    return "\n\n".join([
        role_prompt.strip(),
        "Response schema:\n" + json.dumps(schema, indent=1, sort_keys=True),
        "Case:\n" + json.dumps(case, indent=1, sort_keys=True, ensure_ascii=False),
    ])


def _blocks(response: dict, kind: str) -> list[dict]:
    return [b for b in response["content"] if b.get("type") == kind]


def review_case(client, case: dict, role_prompt: str, schema: dict, system_prompt: str) -> dict:
    user_content = compose_user_content(case, role_prompt, schema)
    messages = [{"role": "user", "content": user_content}]
    rounds = []
    record = {
        "case_id": case["case_id"],
        "evidence_sha256": case["evidence_sha256"],
        "requested_model": MODEL,
        "parameters": PARAMETERS,
        "system_prompt": system_prompt,
        "user_content": user_content,
        "user_content_sha256": sha256_bytes(user_content.encode("utf-8")),
        "rounds": rounds,
    }
    for _ in range(MAX_CONTINUATIONS + 1):
        # An API error (e.g. exhausted credit) stops the run; record it, with any rounds
        # already returned, so the interrupted case still leaves a record.
        try:
            with client.messages.stream(
                model=MODEL, system=system_prompt, messages=messages, **PARAMETERS
            ) as stream:
                message = stream.get_final_message()
        except anthropic.APIError as err:
            record["failure"] = f"API error: {type(err).__name__}: {err}"
            return record
        response = message.model_dump(mode="json")
        rounds.append(response)
        if message.stop_reason != "pause_turn":
            break
        # Resume a paused server-tool turn: re-send the turn unchanged, no extra message.
        messages = [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": message.content},
        ]
    else:
        record["failure"] = f"pause_turn persisted after {MAX_CONTINUATIONS} continuations"
        return record

    final = rounds[-1]
    record["served_model"] = final["model"]
    record["stop_reason"] = final["stop_reason"]
    record["thinking"] = [b.get("thinking", "") for r in rounds for b in _blocks(r, "thinking")]
    record["web_searches"] = [
        b.get("input", {}).get("query") for r in rounds for b in _blocks(r, "server_tool_use")
        if b.get("name") == "web_search"
    ]
    # web_search_20260209 filters results with server-side code execution: the code is
    # plain text here; its stdout comes back encrypted, like search page content.
    record["code_executions"] = [
        b.get("input", {}).get("code") for r in rounds for b in _blocks(r, "server_tool_use")
        if b.get("name") == "code_execution"
    ]
    # A failed fetch's result carries no URL, so the URL comes from the fetch call itself.
    fetch_urls = {
        b["id"]: b.get("input", {}).get("url") for r in rounds for b in _blocks(r, "server_tool_use")
        if b.get("name") == "web_fetch"
    }
    record["web_fetches"] = [
        {
            "url": fetch_urls[b["tool_use_id"]],
            "retrieved_at": (b.get("content") or {}).get("retrieved_at"),
            "error_code": (b.get("content") or {}).get("error_code"),
        }
        for r in rounds for b in _blocks(r, "web_fetch_tool_result")
    ]
    record["web_search_results"] = [
        {"title": res.get("title"), "url": res.get("url"), "page_age": res.get("page_age")}
        for r in rounds for b in _blocks(r, "web_search_tool_result")
        if isinstance(b.get("content"), list) for res in b["content"]
    ]
    if final["stop_reason"] == "refusal":
        record["failure"] = f"refusal: {final.get('stop_details')}"
        return record
    # The answer is the last text block. Earlier text blocks are the model's notes between
    # tool calls (kept verbatim in the rounds), not part of the answer.
    texts = [b.get("text", "") for b in _blocks(final, "text")]
    if not texts:
        record["failure"] = "final round has no text block"
        return record
    text = texts[-1].strip()
    record["interstitial_text"] = [t for r in rounds for t in (b.get("text", "") for b in _blocks(r, "text"))][:-1]
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
    if not record["web_searches"] and not any(f["error_code"] is None for f in record["web_fetches"]):
        record["failure"] = (
            "case decided without any web search or successful web fetch "
            "(the role prompt requires research)"
        )
        return record
    record["decision"] = decision
    return record


def usage_cost(record: dict) -> dict:
    totals = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "web_search": 0, "web_fetch": 0}
    for r in record["rounds"]:
        u = r.get("usage") or {}
        totals["input"] += u.get("input_tokens") or 0
        totals["output"] += u.get("output_tokens") or 0
        totals["cache_read"] += u.get("cache_read_input_tokens") or 0
        totals["cache_write"] += u.get("cache_creation_input_tokens") or 0
        totals["web_search"] += ((u.get("server_tool_use") or {}).get("web_search_requests") or 0)
        # Web fetch has no per-request fee; fetched pages are billed as input tokens.
        totals["web_fetch"] += ((u.get("server_tool_use") or {}).get("web_fetch_requests") or 0)
    usd = (
        (totals["input"] + totals["cache_write"]) * PRICE["input"]
        + totals["output"] * PRICE["output"]
        + totals["cache_read"] * PRICE["cache_read"]
    ) / 1e6 + totals["web_search"] * PRICE["web_search"]
    return {**totals, "estimated_usd": round(usd, 4)}


def write_atomic(path: Path, value: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True) + "\n", "utf-8")
    tmp.replace(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", type=Path, required=True)
    ap.add_argument("--reviewer", required=True, help="independent reviewer label, e.g. A or B")
    ap.add_argument("--out", type=Path, required=True, help="private output directory")
    ap.add_argument("--limit", type=int, help="review only the first N queue cases (pilot)")
    ap.add_argument("--case-id", action="append", help="review only these case IDs (pilot)")
    args = ap.parse_args()

    queue = json.loads(args.queue.read_text("utf-8"))
    cases = queue["cases"][: args.limit] if args.limit else queue["cases"]
    if args.case_id:
        unknown = set(args.case_id) - {c["case_id"] for c in queue["cases"]}
        if unknown:
            raise ReviewFailure(f"unknown case IDs: {sorted(unknown)}")
        cases = [c for c in cases if c["case_id"] in set(args.case_id)]
    role_prompt = ROLE_PROMPT.read_text("utf-8")
    system_prompt = SYSTEM_PROMPT_PATH.read_text("utf-8")
    schema = json.loads(RESPONSE_SCHEMA.read_text("utf-8"))
    out = args.out / f"reviewer-{args.reviewer}"
    out.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic()

    total_usd = 0.0
    for case in cases:
        path = out / f"{case['case_id']}.json"
        if path.exists():
            raise ReviewFailure(f"{path} already exists; records are never overwritten")
        record = review_case(client, case, role_prompt, schema, system_prompt)
        record["reviewer"] = args.reviewer
        record["usage"] = usage_cost(record)
        write_atomic(path, record)
        total_usd += record["usage"]["estimated_usd"]
        status = record.get("failure") or (
            f"{record['decision']['same_entity']} / {record['decision']['useful_granularity']}"
        )
        print(f"[{args.reviewer}] {case['case_id']}: {status} | searches "
              f"{len(record['web_searches'])} | fetches {len(record.get('web_fetches', []))} | ${record['usage']['estimated_usd']:.3f}", flush=True)
        if "failure" in record:
            raise ReviewFailure(f"{case['case_id']}: {record['failure']} (record: {path})")
    print(f"[{args.reviewer}] {len(cases)} cases, estimated ${total_usd:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
