"""Emit one line per new PR review on the target commit.

Reads the PR-reviews JSON from stdin, filters to reviews whose
`commit_id` equals `$SHA`, and prints one line per review ID not yet
present in the `$SEEN` file. Appends new IDs to the seen file.

On JSON parse failure, prints `POLL-ERROR: <detail>` and exits 0 —
the caller's Monitor loop surfaces this as a user-visible event instead
of dying silently.
"""
import json
import os
import sys

sha = os.environ["SHA"]
seen_path = os.environ["SEEN"]

try:
    data = json.loads(sys.stdin.read(), strict=False)
except Exception as exc:
    print(f"POLL-ERROR: {exc}")
    sys.exit(0)

with open(seen_path) as f:
    seen = set(f.read().split())

with open(seen_path, "a") as f:
    for r in data:
        if r.get("commit_id") != sha:
            continue
        rid = str(r["id"])
        if rid in seen:
            continue
        login = r.get("user", {}).get("login", "?")
        state = r.get("state", "?")
        print(f"REVIEW {login} {state} id={rid}")
        f.write(rid + "\n")
        seen.add(rid)
