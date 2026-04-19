#!/usr/bin/env bash
# Poll a PR's reviews endpoint and emit one line per new review on the
# target commit. Used as the `command` arg to the Monitor tool via the
# watch-pr-reviews skill.
#
# Usage: monitor.sh <PR> [SHA] [OWNER/REPO]
#
#   PR    required — no safe default inside the Monitor sandbox. The
#         obvious fallback (`gh pr view`) uses GraphQL, which fails on
#         keychain TLS in the Monitor's sandbox.
#   SHA   defaults to `git rev-parse HEAD` (git-only, sandbox-safe).
#   REPO  defaults to the owner/name parsed from `git remote get-url
#         origin` (git-only, sandbox-safe).
#
# Emits to stdout:
#   REVIEW <login> <state> id=<id>   — one line per new review
#   POLL-ERROR: seed: <detail>       — seed stage failure (then exit 2)
#   POLL-ERROR: poll: <detail>       — poll stage failure (loop continues)
#
# Exits only on SIGTERM (Monitor timeout / TaskStop) or seed failure.
# Cleans up the temp seed file on any exit.
set -uo pipefail

if [ -z "${1:-}" ]; then
  echo "POLL-ERROR: monitor.sh requires a PR number as arg 1 (cannot derive inside the Monitor sandbox — gh pr view uses GraphQL which fails on keychain TLS)"
  exit 2
fi
PR=$1
SHA=${2:-$(git rev-parse HEAD)}
# Normalise to a full 40-char SHA. GitHub's /pulls/<N>/reviews API always
# returns commit_id as the full 40-char SHA; seed.py and poll.py use literal
# string equality to filter, so a short (7-char) SHA here silently matches
# nothing and the Monitor polls in silence until it times out. `git rev-parse
# --verify <X>^{commit}` resolves any commit-ish (short SHA, branch, tag,
# HEAD~N, etc.) to its full 40-char form; failure means the ref doesn't
# resolve and we should bail loud before the seed stage.
FULL_SHA=$(git rev-parse --verify "$SHA^{commit}" 2>/dev/null) || {
  echo "POLL-ERROR: cannot resolve SHA '$SHA' via git rev-parse (need a commit-ish — short SHA, branch, tag, or HEAD~N)"
  exit 2
}
# NB: do NOT add `--` between `--verify` and the revision — unlike other
# git subcommands, `rev-parse --verify` treats arguments after `--` as
# PATHSPECS (file paths), not revisions, so the command fails with
# "Needed a single revision". Caught live on PR #73 when a Gemini-suggested
# `--` broke the Monitor's seed step on its first arm cycle.
SHA=$FULL_SHA
REPO=${3:-$(git remote get-url origin 2>/dev/null | sed -E 's#^.*github\.com[:/]##; s#\.git$##')}
if ! echo "$REPO" | grep -qE '^[^/]+/[^/]+$'; then
  echo "POLL-ERROR: could not derive OWNER/REPO from git remote origin (got '$REPO'); pass as arg 3"
  exit 2
fi
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
if ! curl -fsSL -H "Authorization: token $TOKEN" \
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
