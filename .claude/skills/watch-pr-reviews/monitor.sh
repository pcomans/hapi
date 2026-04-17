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
#   POLL-ERROR: seed: <detail>       — seed stage failure (then exit 2)
#   POLL-ERROR: poll: <detail>       — poll stage failure (loop continues)
#
# Exits only on SIGTERM (Monitor timeout / TaskStop) or seed failure.
# Cleans up the temp seed file on any exit.
set -uo pipefail

PR=${1:-$(gh pr view --json number -q .number)}
SHA=${2:-$(git rev-parse HEAD)}
REPO=${3:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}
SKILL_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

TOKEN=$(gh auth token)

# macOS default TMPDIR (/var/folders/...) is not in the Monitor's
# sandbox write-allowlist; /tmp/claude is. Prefer that when it exists,
# fall back to default mktemp outside the sandbox. Check exit status
# either way — a missing $SEEN would manifest as a confusing redirect
# error several lines later.
if mkdir -p /tmp/claude 2>/dev/null && [ -w /tmp/claude ]; then
  SEEN=$(mktemp /tmp/claude/watch-pr-reviews.XXXXXX) \
    || { echo "POLL-ERROR: mktemp failed under /tmp/claude"; exit 2; }
else
  SEEN=$(mktemp) \
    || { echo "POLL-ERROR: mktemp failed (no writable tempdir)"; exit 2; }
fi
trap 'rm -f "$SEEN"' EXIT

# Seed: seed.py writes the SEEN file itself (via $SEEN env var) and
# prints POLL-ERROR to stdout on any failure. Exits 2 on seed failure
# so this script bails loud rather than proceeding with an empty set.
if ! curl -fsSL -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
       "https://api.github.com/repos/$REPO/pulls/$PR/reviews" 2>&1 \
     | SHA="$SHA" SEEN="$SEEN" python3 "$SKILL_DIR/seed.py"; then
  exit 2
fi

while true; do
  # curl stderr merged into stdout so network / HTTP errors reach
  # poll.py, which emits them as POLL-ERROR. No 2>/dev/null anywhere.
  curl -sS -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
       "https://api.github.com/repos/$REPO/pulls/$PR/reviews" 2>&1 \
    | SEEN="$SEEN" SHA="$SHA" python3 "$SKILL_DIR/poll.py"
  sleep 30
done
