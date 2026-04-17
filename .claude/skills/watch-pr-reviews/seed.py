"""Print IDs of reviews already present on the target commit.

Reads the PR-reviews JSON from stdin (curl response from
/repos/{owner}/{repo}/pulls/{pr}/reviews) and writes one review-ID per
line for reviews whose `commit_id` equals `$SHA`.

Used by watch-pr-reviews to seed the "already seen" set so the poll
loop only fires on genuinely new reviews.
"""
import json
import os
import sys

sha = os.environ["SHA"]
for r in json.loads(sys.stdin.read(), strict=False):
    if r.get("commit_id") == sha:
        print(r["id"])
