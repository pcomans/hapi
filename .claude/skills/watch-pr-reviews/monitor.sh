#!/usr/bin/env bash
# Poll a PR's reviews endpoint and emit one line per new review on the
# target commit. Used as the `command` arg to the Monitor tool via the
# watch-pr-reviews skill.
#
# Usage: monitor.sh <pr-number> <target-sha> <owner/repo>
#
# Emits to stdout:
#   REVIEW <login> <state> id=<id>   — one line per new review
#   POLL-ERROR: <detail>             — on parse or HTTP failure
#
# Exits only on SIGTERM (Monitor timeout or TaskStop). The Monitor tool
# translates each stdout line into a chat notification.
set -u
PR=$1
SHA=$2
REPO=$3
SKILL_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

TOKEN=$(gh auth token)
SEEN=$(mktemp)

curl -sS -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/$REPO/pulls/$PR/reviews" \
  | SHA="$SHA" python3 "$SKILL_DIR/seed.py" > "$SEEN"

while true; do
  curl -sS -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$REPO/pulls/$PR/reviews" 2>&1 \
    | SEEN="$SEEN" SHA="$SHA" python3 "$SKILL_DIR/poll.py"
  sleep 30
done
