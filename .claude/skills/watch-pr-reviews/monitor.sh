#!/usr/bin/env bash
# Poll a PR's reviews endpoint and emit one line per new review on the
# target commit. Used as the `command` arg to the Monitor tool via the
# watch-pr-reviews skill.
#
# Usage: monitor.sh [PR] [SHA] [OWNER/REPO]
#   Each arg defaults to values derived from the working copy / gh CLI.
#
# Emits to stdout:
#   REVIEW <login> <state> id=<id>   — one line per new review
#   POLL-ERROR: <detail>             — on parse / HTTP / shape failure
#
# Exits only on SIGTERM (Monitor timeout or TaskStop), or non-zero if
# the initial seed request fails — an empty seen set would mis-fire on
# every existing review. Cleans up the temp seed file on any exit.
set -uo pipefail

PR=${1:-$(gh pr view --json number -q .number)}
SHA=${2:-$(git rev-parse HEAD)}
REPO=${3:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}
SKILL_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

TOKEN=$(gh auth token)

# macOS default TMPDIR (/var/folders/...) is not in the Monitor's
# sandbox write-allowlist; /tmp/claude is. Prefer that when it exists,
# fall back to default mktemp outside the sandbox.
if mkdir -p /tmp/claude 2>/dev/null && [ -w /tmp/claude ]; then
  SEEN=$(mktemp /tmp/claude/watch-pr-reviews.XXXXXX)
else
  SEEN=$(mktemp)
fi
trap 'rm -f "$SEEN"' EXIT

# Seed: fail loud if the request or parse fails. An empty seed set
# would cause every pre-existing review to look new on the first poll.
if ! curl -fsSL -H "Authorization: token $TOKEN" \
       "https://api.github.com/repos/$REPO/pulls/$PR/reviews" 2>&1 \
     | SHA="$SHA" python3 "$SKILL_DIR/seed.py" > "$SEEN"; then
  echo "POLL-ERROR: seed failed for $REPO#$PR @ $SHA"
  exit 2
fi

while true; do
  # Merge curl stderr into stdout so network / HTTP errors reach
  # poll.py, which emits them as POLL-ERROR. No 2>/dev/null anywhere.
  curl -sS -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
       "https://api.github.com/repos/$REPO/pulls/$PR/reviews" 2>&1 \
    | SEEN="$SEEN" SHA="$SHA" python3 "$SKILL_DIR/poll.py"
  sleep 30
done
