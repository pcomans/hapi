"""Print IDs of reviews already present on the target commit.

Reads PR-reviews JSON from stdin (curl response from
/repos/{owner}/{repo}/pulls/{pr}/reviews) and writes one review-ID per
line for reviews whose `commit_id` equals `$SHA`.

Used by watch-pr-reviews to seed the "already seen" set so the poll
loop only fires on genuinely new reviews.

Fails loud: on JSON parse failure, unexpected shape, or any other
error, emits `POLL-ERROR: <detail>` to stderr and exits non-zero so the
caller does not proceed with an empty seed set (which would mis-fire
on every existing review).
"""
import json
import os
import sys

sha = os.environ["SHA"]

try:
    data = json.loads(sys.stdin.read(), strict=False)
    if not isinstance(data, list):
        raise ValueError(
            f"expected JSON array of reviews, got {type(data).__name__}"
        )
    for r in data:
        if not isinstance(r, dict):
            raise ValueError(
                f"expected review object, got {type(r).__name__}"
            )
        if r.get("commit_id") == sha:
            rid = r.get("id")
            if rid is None:
                raise ValueError("matching review is missing `id`")
            print(rid)
except Exception as exc:
    print(f"POLL-ERROR: {exc}", file=sys.stderr)
    sys.exit(2)
