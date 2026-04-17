"""Emit one line per new PR review on the target commit.

Reads the PR-reviews JSON from stdin, filters to reviews whose
`commit_id` equals `$SHA`, and prints one line per review ID not yet
present in the `$SEEN` file. Appends new IDs to the seen file.

Contract: on any failure — missing env var, parse failure, unexpected
shape, malformed review object, filesystem trouble — prints
`POLL-ERROR: poll: <detail>` to stdout (visible to the Monitor tool as
an event) and exits 0. Never exits non-zero from the polling path;
that would kill the Monitor.
"""
import json
import os
import sys

try:
    sha = os.environ["SHA"]
    seen_path = os.environ["SEEN"]
    raw = sys.stdin.read()
    try:
        data = json.loads(raw, strict=False)
    except Exception as exc:
        excerpt = raw[:200].replace("\n", " ")
        raise ValueError(f"JSON parse failed: {exc}; raw: {excerpt!r}")
    if not isinstance(data, list):
        raise ValueError(
            f"expected JSON array of reviews, got {type(data).__name__}"
        )
    with open(seen_path) as f:
        seen = set(f.read().split())
    with open(seen_path, "a") as f:
        for r in data:
            if not isinstance(r, dict):
                raise ValueError(
                    f"expected review object, got {type(r).__name__}"
                )
            if r.get("commit_id") != sha:
                continue
            rid_val = r.get("id")
            if rid_val is None:
                raise ValueError("review is missing `id`")
            rid = str(rid_val)
            if rid in seen:
                continue
            login = r.get("user", {}).get("login", "?")
            state = r.get("state", "?")
            print(f"REVIEW {login} {state} id={rid}")
            f.write(rid + "\n")
            seen.add(rid)
except Exception as exc:
    print(f"POLL-ERROR: poll: {exc}")
    sys.exit(0)
