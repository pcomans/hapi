"""Populate the "already seen" review-ID file from GitHub's reviews API.

Reads the PR-reviews JSON from stdin, filters to reviews whose
`commit_id` equals `$SHA`, and writes one review-ID per line to the
path in `$SEEN`.

Contract: on any failure — missing env var, parse failure, unexpected
shape, filesystem trouble — prints `POLL-ERROR: seed: <detail>` to
stdout (visible to the Monitor tool as an event) and exits 2 so the
caller (monitor.sh) does not proceed with an empty seen set, which
would mis-fire on every existing review.
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
    with open(seen_path, "w") as f:
        for r in data:
            if not isinstance(r, dict):
                raise ValueError(
                    f"expected review object, got {type(r).__name__}"
                )
            if r.get("commit_id") == sha:
                rid = r.get("id")
                if rid is None:
                    raise ValueError("matching review is missing `id`")
                f.write(f"{rid}\n")
except Exception as exc:
    print(f"POLL-ERROR: seed: {exc}")
    sys.exit(2)
