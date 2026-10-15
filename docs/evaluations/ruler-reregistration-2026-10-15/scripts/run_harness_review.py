"""#337 re-registration: one case per call through headless Claude Code (`claude -p`).

Runs any review role (`review_protocol.ROLES`): the Stage 1 and Stage 2 reviewers over their
queues, and the reconcilers over a reconciliation queue (`review_protocol.py
prepare-reconciliation`). Each case is a separate `claude -p` process in a fresh empty
directory, so no project CLAUDE.md, memory or other case can reach it, with only two tools:
WebSearch, to find pages, and `open_page`, the one MCP server (`open_page_server.py`, a
headless Chromium), to read them. ANTHROPIC_API_KEY is removed from its environment, so it
runs on the Claude Code subscription and is never billed at API rates.
User-level plugins and hooks still load; any hook output fails the call.

Each call's complete record is persisted before its decision is used (Constitutional Rule
13): the exact command, system prompt and user content, and the full stream-json event log
verbatim (every message, each search query with its result titles and URLs, each opened
page with its HTTP status, final URL, title and the visible text the model received, the
final answer, usage).

Fail loud (Rule 2): API-key (billed) auth, any tool or MCP server beyond the two, hook
output, or a model other than the requested one stops the run after the case's record is
written, and a later run does not resume that case. An answer rejected for its format, one
that cites a page the call did not open or a page outside the citable sources
(`citable-sources.json`), or a call whose search results, opened pages or citations touched
a blocked domain, is retried (`MAX_ATTEMPTS` such calls per case). A session limit stops
the run; a later run resumes the case.

Run it with the interpreter of the recorded runtime (`runtime/`, README); the browser server
starts with the same interpreter.

    docs/evaluations/ruler-reregistration-2026-10-15/runtime/.venv/bin/python \\
      docs/evaluations/ruler-reregistration-2026-10-15/scripts/run_harness_review.py \\
      --role stage_1_reviewer --queue <stage-1-queue.json> --label A --out <private stage-1 dir>
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from review_protocol import (
    ROLES,
    TOOLS,
    OPEN_PAGE_SERVER,
    OPEN_PAGE_SERVER_PATH,
    ProtocolFailure,
    Role,
    attempt_number,
    calls_by_latest_attempt,
    compose_user_content,
    read_json,
    role_inputs,
    run_bindings,
    sha256_bytes,
    validate,
    write_new,
)

MODEL_ALIAS = "sonnet"
EFFORT = "high"
# A malformed answer (not JSON, schema-invalid, a miscopied case ID, or a reconciler
# answer that resolves other than the disputed questions), an answer citing a page the call
# did not open or a non-citable source, or a run whose search results or opened pages touched a blocked domain (the
# search tool cannot exclude them), is retried, up to this many attempts per case. Every attempt is kept; a
# case's decision is its one valid attempt (the run stops retrying a case once it has one).
MAX_ATTEMPTS = 3
FORMAT_FAILURES = (
    "invalid decision:", "decision does not echo", "blocked domain used:", "cites a page it did not open:",
    "cites a non-citable source:",
)
# The browser server runs from the evaluation's own interpreter (the recorded runtime),
# under a virtual X display, so the browser can run headful (open_page_server.py).
MCP_CONFIG = json.dumps({"mcpServers": {OPEN_PAGE_SERVER: {
    "command": "xvfb-run", "args": ["-a", sys.executable, str(OPEN_PAGE_SERVER_PATH)],
}}}, sort_keys=True)
SESSION_LIMIT_FAILURE = "Claude Code session limit"
RECORD_KEYS = (
    "case_id", "evidence_sha256", "requested_model", "parameters", "command", "system_prompt",
    "user_content", "user_content_sha256", "run_bindings", "exit_code", "stderr", "events", "reviewer",
)


def command(system_prompt: str, user_content: str) -> list[str]:
    return [
        "claude", "-p", user_content,
        "--model", MODEL_ALIAS,
        "--effort", EFFORT,
        # Without this, Claude Code returns every thinking block with empty text.
        "--thinking-display", "summarized",
        "--system-prompt", system_prompt,
        "--tools", ",".join(TOOLS),
        "--allowedTools", *TOOLS,
        "--mcp-config", MCP_CONFIG,
        "--strict-mcp-config",
        "--output-format", "stream-json",
        "--verbose",
        "--no-session-persistence",
    ]


def call(case: dict, inputs: dict) -> dict:
    user_content = compose_user_content(case, inputs["prompt"], inputs["schema"], inputs["citable_sources"])
    argv = command(inputs["system_prompt"], user_content)
    record = {
        "case_id": case["case_id"],
        "evidence_sha256": case["evidence_sha256"],
        "requested_model": MODEL_ALIAS,
        "parameters": {"effort": EFFORT, "thinking_display": "summarized", "tools": list(TOOLS),
                       "mcp_servers": [OPEN_PAGE_SERVER]},
        "command": argv[:2] + ["<user_content>"] + argv[3:],
        "system_prompt": inputs["system_prompt"],
        "user_content": user_content,
        "user_content_sha256": sha256_bytes(user_content.encode("utf-8")),
        "run_bindings": run_bindings(),
    }
    env = {key: value for key, value in os.environ.items() if key != "ANTHROPIC_API_KEY"}
    with tempfile.TemporaryDirectory(prefix="hapi-337-review-") as cwd:
        proc = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True, cwd=cwd, env=env)
    record["exit_code"] = proc.returncode
    record["stderr"] = proc.stderr
    try:
        events = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    except json.JSONDecodeError as err:
        record["stdout"] = proc.stdout
        record["failure"] = f"stream is not JSON lines: {err}"
        return record
    record["events"] = events
    return record


def _status(record: dict, fields: tuple[str, ...]) -> str:
    if "failure" in record:
        return record["failure"]
    decision = record["decision"]
    if "resolutions" in decision:
        return " / ".join(f"{f}={r['outcome']}" for f, r in decision["resolutions"].items())
    return " / ".join(decision[f] for f in fields)


def next_path(out: Path, case_id: str) -> Path:
    numbers = [attempt_number(p) for p in out.glob(f"{case_id}.attempt-*.json")]
    return out / f"{case_id}.attempt-{max(numbers, default=0) + 1}.json"


def recheck_calls(case: dict, role: Role, inputs: dict, out: Path, tag: str) -> dict[str, dict]:
    """Re-check the latest attempt of every stored call under the current rules, from its saved
    events, with no new model call. A call whose verdict changed (an answer format accepted by
    a later parsing rule, or a decision formed while the session limit refused tool calls)
    gets the re-check as a new attempt naming the call. Returns each call's current record."""
    current = {}
    for call, path in calls_by_latest_attempt(out, case["case_id"]).items():
        last = read_json(path)
        if "events" in last:
            stored = {k: last[k] for k in RECORD_KEYS if k in last}
            recheck = validate(stored, case, role, inputs["schema"])
            if (recheck.get("decision"), recheck.get("failure")) != (last.get("decision"), last.get("failure")):
                target = next_path(out, case["case_id"])
                recheck.update(role=role.name, attempt=attempt_number(target), revalidated_from=call)
                write_new(target, recheck)
                print(f"{tag} {case['case_id']} re-checked {call}: {recheck.get('failure') or 'valid'}", flush=True)
                last = recheck
        current[call] = last
    return current


def review_case(case: dict, role: Role, inputs: dict, out: Path, label: str | None, tag: str) -> None:
    calls = recheck_calls(case, role, inputs, out, tag)
    if any("decision" in record for record in calls.values()):
        return
    if calls:
        newest = calls[max(calls, key=lambda name: attempt_number(Path(name)))]
        failure = newest.get("failure", "")
        if not failure.startswith(FORMAT_FAILURES + (SESSION_LIMIT_FAILURE,)):
            # A stop (e.g. no research) is not re-drawn by resuming the run.
            raise ProtocolFailure(f"{case['case_id']}: stopped on {failure!r}; not resumed automatically")
    format_calls = sum(r.get("failure", "").startswith(FORMAT_FAILURES) for r in calls.values())
    while True:
        if format_calls >= MAX_ATTEMPTS:
            raise ProtocolFailure(f"{case['case_id']}: no valid answer in {MAX_ATTEMPTS} attempts")
        path = next_path(out, case["case_id"])
        record = call(case, inputs)
        if "failure" not in record:
            record = validate(record, case, role, inputs["schema"])
        record.update(reviewer="reconciler" if role.reconciler else label, role=role.name,
                      attempt=attempt_number(path))
        write_new(path, record)
        print(f"{tag} {case['case_id']} attempt {record['attempt']}: {_status(record, role.fields)} | "
              f"searches {len(record.get('web_searches', []))} | pages "
              f"{sum(o['loaded'] for o in record.get('page_opens', []))}/"
              f"{len(record.get('page_opens', []))} loaded", flush=True)
        if "failure" not in record:
            return
        if not record["failure"].startswith(FORMAT_FAILURES):
            raise ProtocolFailure(f"{case['case_id']}: {record['failure']} (record: {path})")
        format_calls += 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", required=True, choices=sorted(ROLES))
    ap.add_argument("--queue", type=Path, required=True, help="review queue, or reconciliation queue for a reconciler")
    ap.add_argument("--label", help="independent reviewer label (A or B); not used by a reconciler")
    ap.add_argument("--out", type=Path, required=True, help="private stage directory")
    ap.add_argument("--case-id", action="append", help="run only these case IDs")
    args = ap.parse_args()
    role = ROLES[args.role]
    if role.reconciler == bool(args.label):
        raise ProtocolFailure("--label is required for a reviewer and not allowed for a reconciler")

    cases = read_json(args.queue)["cases"]
    if args.case_id:
        unknown = set(args.case_id) - {c["case_id"] for c in cases}
        if unknown:
            raise ProtocolFailure(f"unknown case IDs: {sorted(unknown)}")
        cases = [c for c in cases if c["case_id"] in set(args.case_id)]
    inputs = role_inputs(role)
    out = args.out / ("reconciler" if role.reconciler else f"reviewer-{args.label}")
    out.mkdir(parents=True, exist_ok=True)
    tag = f"[{role.name}{'' if role.reconciler else ' ' + args.label}]"

    for case in cases:
        review_case(case, role, inputs, out, args.label, tag)
    print(f"{tag} {len(cases)} cases done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
