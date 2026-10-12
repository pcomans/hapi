"""#337 re-registration: one case per call through headless Claude Code (`claude -p`).

Runs any review role (`review_protocol.ROLES`): the Stage 1 and Stage 2 reviewers over their
queues, and the reconcilers over a reconciliation queue (`review_protocol.py
prepare-reconciliation`). Each case is a separate `claude -p` process in a fresh empty
directory, so no project CLAUDE.md, memory or other case can reach it, with only the
WebSearch and WebFetch tools, no MCP servers, and ANTHROPIC_API_KEY removed from its
environment, so it runs on the Claude Code subscription and is never billed at API rates.

Each call's complete record is persisted before its decision is used (Constitutional Rule
13): the exact command, system prompt and user content, and the full stream-json event log
verbatim (every message, each search query with its result titles and URLs, each fetch with
its HTTP status, size and the page summary the model received, the final answer, usage).

Fail loud (Rule 2): API-key (billed) auth, any tool beyond the two web tools, an MCP
server, a model other than the requested one, or a case decided without a search result or
successful fetch stops the run after the case's record is written. An answer rejected for
its format, or a run whose search results or fetches touched a blocked domain, is retried
(`MAX_ATTEMPTS`).

    pipeline/.venv/bin/python \\
      docs/evaluations/authority-independent-control-2026-10-11/scripts/run_harness_review.py \\
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
    SESSION_LIMIT_TEXT,
    TOOLS,
    ProtocolFailure,
    compose_user_content,
    read_json,
    role_inputs,
    sha256_bytes,
    validate,
    write_atomic,
)

MODEL_ALIAS = "sonnet"
EFFORT = "high"
# A malformed answer (not JSON, schema-invalid, a miscopied case ID or hash, or a reconciler
# answer that resolves other than the disputed questions), or a run whose search results or
# fetches touched a blocked domain (the search tool cannot exclude them, and its summary may
# draw on them), is retried, up to this many attempts per case. Every attempt is kept; a
# case's decision is its one valid attempt (the run stops retrying a case once it has one).
MAX_ATTEMPTS = 3
FORMAT_FAILURES = ("invalid decision:", "decision does not echo", "blocked domain used:")


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


def call(case: dict, inputs: dict) -> dict:
    user_content = compose_user_content(case, inputs["prompt"], inputs["schema"])
    argv = command(inputs["system_prompt"], user_content)
    record = {
        "case_id": case["case_id"],
        "evidence_sha256": case["evidence_sha256"],
        "requested_model": MODEL_ALIAS,
        "parameters": {"effort": EFFORT, "tools": list(TOOLS), "mcp_servers": []},
        "command": argv[:2] + ["<user_content>"] + argv[3:],
        "system_prompt": inputs["system_prompt"],
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
    return record


def _status(record: dict, fields: tuple[str, ...]) -> str:
    if "failure" in record:
        return record["failure"]
    decision = record["decision"]
    if "resolutions" in decision:
        return " / ".join(f"{f}={r['outcome']}" for f, r in decision["resolutions"].items())
    return " / ".join(decision[f] for f in fields)


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
        # Attempts are <case>.attempt-<n>.json, never overwritten. A case with a valid
        # attempt is done; a rerun resumes with the cases that are not.
        attempts = sorted(
            out.glob(f"{case['case_id']}.attempt-*.json"),
            key=lambda p: int(p.name.rsplit("-", 1)[1].removesuffix(".json")),
        )
        if any("decision" in read_json(a) for a in attempts):
            continue
        # A stored attempt rejected for its answer's format is first re-checked under the
        # current rules from its saved events, with no new model call; the re-check is kept
        # as a new attempt that names its source.
        if attempts:
            last = read_json(attempts[-1])
            if (last.get("failure", "").startswith(FORMAT_FAILURES) and "events" in last
                    and "revalidated_from" not in last):
                stored = {k: last[k] for k in (
                    "case_id", "evidence_sha256", "requested_model", "parameters", "command",
                    "system_prompt", "user_content", "user_content_sha256", "exit_code",
                    "stderr", "events", "reviewer")}
                recheck = validate(stored, case, role, inputs["schema"])
                recheck["attempt"] = len(attempts) + 1
                recheck["revalidated_from"] = attempts[-1].name
                path = out / f"{case['case_id']}.attempt-{recheck['attempt']}.json"
                write_atomic(path, recheck)
                attempts.append(path)
                print(f"{tag} {case['case_id']} re-checked {recheck['revalidated_from']}: "
                      f"{recheck.get('failure') or 'valid'}", flush=True)
                if "decision" in recheck:
                    continue
        while True:
            # Only model answers rejected for their format count toward the limit; a re-check
            # or a session-limit stop does not.
            answered = [
                r for r in (read_json(a) for a in attempts)
                if r.get("failure", "").startswith(FORMAT_FAILURES) and "revalidated_from" not in r
                and SESSION_LIMIT_TEXT not in r.get("final_text", "")
            ]
            if len(answered) >= MAX_ATTEMPTS:
                raise ProtocolFailure(f"{case['case_id']}: no valid answer in {MAX_ATTEMPTS} attempts")
            path = out / f"{case['case_id']}.attempt-{len(attempts) + 1}.json"
            record = call(case, inputs)
            if "failure" not in record:
                record = validate(record, case, role, inputs["schema"])
            record["reviewer"] = "reconciler" if role.reconciler else args.label
            record["role"] = role.name
            record["attempt"] = len(attempts) + 1
            write_atomic(path, record)
            attempts.append(path)
            print(f"{tag} {case['case_id']} attempt {record['attempt']}: {_status(record, role.fields)} | "
                  f"searches {len(record.get('web_searches', []))} | fetches "
                  f"{sum(f['status_code'] == 200 for f in record.get('web_fetches', []))}/"
                  f"{len(record.get('web_fetches', []))} ok", flush=True)
            if "failure" not in record:
                break
            if not record["failure"].startswith(FORMAT_FAILURES):
                raise ProtocolFailure(f"{case['case_id']}: {record['failure']} (record: {path})")
    print(f"{tag} {len(cases)} cases done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
