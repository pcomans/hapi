"""#337 re-registration: per-case Stage 1 review with a DeepSeek model through the Vercel AI Gateway.

The same audited role prompt, system prompt, response schema, cases and validation as
`run_claude_review.py`. Only the model and tools differ: the gateway's Perplexity search and
Browserbase fetch, which the gateway executes and whose raw output it returns. The call
itself is made by `gateway-review/call.mjs` (AI SDK, pinned in its package-lock.json).

Each case's complete record is persisted before its decision is used (Constitutional Rule
13): the request parameters, system prompt, user content, every step verbatim (the model's
reasoning text, each search and its raw results, each fetch and its raw response, text),
the serving provider and build, cost and usage, and the validated decision.

Fail loud (Rule 2): a call error, a response served by any provider but the pinned one or
without its build, an unparseable or schema-invalid answer, a wrong case ID or evidence
hash, a case decided without a search result or successful fetch, or a search result or
fetch on a blocked domain stops the run after the case's record is written.

    AI_GATEWAY_API_KEY=... pipeline/.venv/bin/python \\
      docs/evaluations/authority-independent-control-2026-10-11/scripts/run_gateway_review.py \\
      --model deepseek/deepseek-v4-pro --queue <run>/review/stage-1-queue.json \\
      --reviewer A --out <private dir> --case-id review-unit-014
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
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

CALLER_DIR = Path(__file__).resolve().parent / "gateway-review"
MODELS = ("deepseek/deepseek-v4-pro", "deepseek/deepseek-v4.1-flash")
# Served only by DeepSeek's own endpoint, with no fallback, so a run is attributable to one
# deployment; every step is checked to have been served there.
PINNED_PROVIDER = "deepseek"
# Enforced on search through Perplexity's domain filter, and checked on every search result
# and fetch afterwards (Browserbase fetch has no domain filter).
BLOCKED_DOMAINS = ("wikidata.org", "github.com", "raw.githubusercontent.com")
PARAMETERS = {
    "maxOutputTokens": 32000,
    "reasoning": "xhigh",
    # Gateway tools run inside one step; the cap only bounds the client-side loop.
    "maxSteps": 5,
    "providerOptions": {"gateway": {"only": [PINNED_PROVIDER], "order": [PINNED_PROVIDER]}},
    "tools": {
        "perplexity_search": {
            "maxResults": 10,
            "searchDomainFilter": [f"-{domain}" for domain in BLOCKED_DOMAINS],
        },
        # Format and proxies set the per-fetch price, so both are pinned.
        "browserbase_fetch": {"format": "markdown", "proxies": False, "allowRedirects": True},
    },
}


def _parts(result: dict) -> list[dict]:
    return [part for step in result["steps"] for part in step["content"]]


def _blocked(url: str | None) -> bool:
    host = (urlparse(url or "").hostname or "").lower()
    return any(host == domain or host.endswith("." + domain) for domain in BLOCKED_DOMAINS)


def review_case(model: str, case: dict, role_prompt: str, schema: dict, system_prompt: str) -> dict:
    user_content = compose_user_content(case, role_prompt, schema)
    record = {
        "case_id": case["case_id"],
        "evidence_sha256": case["evidence_sha256"],
        "requested_model": model,
        "parameters": PARAMETERS,
        "system_prompt": system_prompt,
        "user_content": user_content,
        "user_content_sha256": sha256_bytes(user_content.encode("utf-8")),
    }
    proc = subprocess.run(
        ["node", str(CALLER_DIR / "call.mjs")],
        input=json.dumps({
            "model": model, "system": system_prompt, "user": user_content, "parameters": PARAMETERS,
        }),
        capture_output=True, text=True, cwd=CALLER_DIR,
    )
    record["caller_stderr"] = proc.stderr
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as err:
        record["caller_stdout"] = proc.stdout
        record["failure"] = f"caller output is not JSON (exit {proc.returncode}): {err}"
        return record
    record["result"] = result
    if "error" in result:
        record["failure"] = f"gateway call error: {result['error'].get('message')}"
        return record

    served = [
        (step.get("providerMetadata") or {}).get("gateway", {}).get("routing", {}).get("finalProvider")
        for step in result["steps"]
    ]
    builds = sorted({
        (step.get("providerMetadata") or {}).get(PINNED_PROVIDER, {}).get("systemFingerprint")
        for step in result["steps"]
    } - {None})
    record["served_provider"] = served
    record["served_build"] = builds
    record["served_model"] = sorted({step["response"]["modelId"] for step in result["steps"]})
    if any(provider != PINNED_PROVIDER for provider in served) or not builds:
        record["failure"] = f"not served by the pinned {PINNED_PROVIDER!r} build: {served} {builds}"
        return record

    parts = _parts(result)
    calls = {p["toolCallId"]: p for p in parts if p["type"] == "tool-call"}
    tool_results = [p for p in parts if p["type"] == "tool-result"]
    record["reasoning"] = [p["text"] for p in parts if p["type"] == "reasoning"]
    record["web_searches"] = [
        p["input"] for p in calls.values() if p["toolName"] == "perplexity_search"
    ]
    record["web_search_results"] = [
        {"url": res.get("url"), "title": res.get("title"), "date": res.get("date"),
         "last_updated": res.get("last_updated")}
        for p in tool_results if p["toolName"] == "perplexity_search"
        for res in (p["output"].get("results") or [])
    ]
    record["web_fetches"] = [
        {"url": calls[p["toolCallId"]]["input"].get("url"),
         "status_code": p["output"].get("statusCode"), "error": p["output"].get("error")}
        for p in tool_results if p["toolName"] == "browserbase_fetch"
    ]
    record["cost_usd"] = round(sum(
        float((step.get("providerMetadata") or {}).get("gateway", {}).get("cost") or 0)
        for step in result["steps"]
    ), 6)

    texts = [p["text"] for p in result["steps"][-1]["content"] if p["type"] == "text"]
    if not texts:
        record["failure"] = "final step has no text part"
        return record
    # The answer is the last text part; earlier ones are notes between tool calls.
    text = texts[-1].strip()
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
    ap.add_argument("--model", required=True, choices=MODELS)
    ap.add_argument("--queue", type=Path, required=True)
    ap.add_argument("--reviewer", required=True, help="independent reviewer label, e.g. A or B")
    ap.add_argument("--out", type=Path, required=True, help="private output directory")
    ap.add_argument("--case-id", action="append", required=True, help="review only these case IDs")
    args = ap.parse_args()

    queue = json.loads(args.queue.read_text("utf-8"))
    unknown = set(args.case_id) - {c["case_id"] for c in queue["cases"]}
    if unknown:
        raise ReviewFailure(f"unknown case IDs: {sorted(unknown)}")
    cases = [c for c in queue["cases"] if c["case_id"] in set(args.case_id)]
    role_prompt = ROLE_PROMPT.read_text("utf-8")
    system_prompt = SYSTEM_PROMPT_PATH.read_text("utf-8")
    schema = json.loads(RESPONSE_SCHEMA.read_text("utf-8"))
    out = args.out / args.model.replace("/", "__") / f"reviewer-{args.reviewer}"
    out.mkdir(parents=True, exist_ok=True)

    total_usd = 0.0
    for case in cases:
        path = out / f"{case['case_id']}.json"
        if path.exists():
            raise ReviewFailure(f"{path} already exists; records are never overwritten")
        record = review_case(args.model, case, role_prompt, schema, system_prompt)
        record["reviewer"] = args.reviewer
        write_atomic(path, record)
        total_usd += record.get("cost_usd", 0.0)
        status = record.get("failure") or (
            f"{record['decision']['same_entity']} / {record['decision']['useful_granularity']}"
        )
        print(f"[{args.model} {args.reviewer}] {case['case_id']}: {status} | searches "
              f"{len(record.get('web_searches', []))} | fetches "
              f"{sum(f['status_code'] == 200 for f in record.get('web_fetches', []))}/"
              f"{len(record.get('web_fetches', []))} ok | ${record.get('cost_usd', 0):.3f}", flush=True)
        if "failure" in record:
            raise ReviewFailure(f"{case['case_id']}: {record['failure']} (record: {path})")
    print(f"[{args.model} {args.reviewer}] {len(cases)} cases, gateway cost ${total_usd:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
