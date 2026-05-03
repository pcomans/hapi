#!/bin/bash
# PreToolUse hook for the revise-priors workflow.
#
# Blocks `git push`, `git commit`, `gh pr create`, `gh pr merge` (and the
# raw-API equivalent) when any unresolved marker file exists in
# .claude/revise-priors/. The block message includes the marker contents
# so the calling agent can see why the workflow is halted and surface
# the decision to the user.
#
# Resolution path (human only):
#   - Dismiss: `rm .claude/revise-priors/<file>.md`
#   - Resolve: `mv .claude/revise-priors/<file>.md .claude/revise-priors/resolved/`
#
# Reads the PreToolUse JSON on stdin; uses jq to extract the Bash
# command. Exits 0 (allow) on non-blocking commands; exits 2 (block)
# with stderr message on blocking commands when markers exist.

set -u

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Match the four blocking command shapes. Each has both the
# `command-with-args` form (` ` suffix) AND the bare-command form
# (no suffix) so commands like `git commit` (no args) don't bypass.
# PR #187 Gemini round-1 caught the missing bare forms on `git commit`
# and `gh pr merge`.
BLOCKED=0
case "$COMMAND" in
  *"git push "*|*"git push"|\
  *"git commit "*|*"git commit"|\
  *"gh pr create "*|*"gh pr create"|\
  *"gh pr merge "*|*"gh pr merge"|\
  *"gh api"*"-X POST"*"/pulls"*)
    BLOCKED=1
    ;;
esac

if [ "$BLOCKED" -eq 0 ]; then
  exit 0
fi

# Glob for unresolved markers (everything in .claude/revise-priors/
# except the resolved/ subdirectory).
MARKER_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude/revise-priors"
shopt -s nullglob
markers=("$MARKER_DIR"/*.md)
shopt -u nullglob

if [ ${#markers[@]} -eq 0 ]; then
  exit 0
fi

echo "BLOCKED: ${#markers[@]} unresolved revise-priors marker(s) exist." >&2
echo "" >&2
echo "Read each, surface the situation to the user via AskUserQuestion," >&2
echo "and let the user resolve before re-attempting the push/commit/PR." >&2
echo "" >&2

for m in "${markers[@]}"; do
  echo "=== $m ===" >&2
  cat "$m" >&2
  echo "" >&2
done

echo "Resolution paths (human only — do not auto-resolve):" >&2
echo "  - Dismiss (agent concern unfounded): rm <file>" >&2
echo "  - Resolve (prior revised in code/docs): mv <file> .claude/revise-priors/resolved/" >&2
echo "(replace <file> with the specific marker path printed above)" >&2

exit 2
