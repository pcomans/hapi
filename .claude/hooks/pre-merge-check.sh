#!/bin/bash
# PreToolUse hook for PR merges:
# - Block 1 — `curl -X PUT .../pulls/<N>/merge` (the GitHub REST API merge
#   path): BLOCK the call. The agent has been bypassing the `gh pr merge`
#   reminder by using curl directly against the API. This hook now funnels
#   all merges through the single enforced path. Per CLAUDE.md rule 3
#   (deterministic enforcement over convention).
# - Block 2 — `gh pr merge`: inject a reminder to verify PR title and
#   description match the final merged state before the merge lands. PR
#   titles and bodies are written at PR-open time and frequently drift as
#   commits accrete, reviewers request changes, and scope shifts. The
#   merge commit on main inherits whatever the PR body currently says, so
#   a stale body bakes bad history into the repo. Force a deliberate
#   review step at the last responsible moment.

CMD=$(echo "$TOOL_INPUT" | jq -r '.command // ""' 2>/dev/null)
if [ -z "$CMD" ]; then
  CMD=$(jq -r '.tool_input.command // ""' 2>/dev/null)
fi

# Normalise the command once: flatten multi-line commands (e.g. long curl
# calls with `\` line-continuations) into a single line, so a line-oriented
# `grep` can't be bypassed by splitting the command across lines. Using
# `printf '%s\n'` rather than `echo` avoids `echo`'s misbehaviour when the
# first argument starts with `-`. Gemini round-1 HIGH finding on PR #104.
CMD_FLAT=$(printf '%s\n' "$CMD" | tr '\n' ' ')

# --- Block 1: curl-to-API merge bypass --------------------------------------
# Match any `curl` invocation whose URL hits a GitHub pulls-merge endpoint.
# Covers the canonical `https://api.github.com/repos/<owner>/<repo>/pulls/<N>/merge`
# pattern and its path-only form. Intentionally permissive on flags/method
# so `-X PUT`, `-XPUT`, `--request PUT`, shorthand variants and subsequent
# piped invocations all match. Blocks the call and redirects to `gh pr merge`.
if printf '%s' "$CMD_FLAT" | grep -qE 'curl.*/repos/[^/]+/[^/]+/pulls/[0-9]+/merge'; then
  cat <<'HEREDOC'
{
  "decision": "block",
  "reason": "Direct curl-to-GitHub-API merges bypass the pre-merge-check reminder and make the merge path non-uniform. Use `gh pr merge <N> --squash --delete-branch` instead (add `--body '...'` if you need a custom merge commit message). The `gh` CLI routes through this hook so you get the title/body drift check before the merge lands. Constitutional rule 3: deterministic enforcement over convention — one merge path, one hook."
}
HEREDOC
  exit 0
fi

# --- Block 2: gh pr merge reminder ------------------------------------------
# Only fire on `gh pr merge`. Any other Bash command passes through untouched.
# The `gh +pr +merge` pattern (one-or-more spaces between tokens) tolerates
# extra whitespace from line-continuation joins.
if ! printf '%s' "$CMD_FLAT" | grep -qE 'gh +pr +merge'; then
  exit 0
fi

# Emit additionalContext — the merge is NOT blocked, the agent just gets
# a reminder injected into the model context before the tool call runs.
cat <<'HEREDOC'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "BEFORE merging this PR, verify the PR title and description reflect the FINAL merged state — not the state at PR-open time. Specifically:\n\n1. Run `gh pr view <N>` and read the current title + body.\n2. Run `git log --oneline main..HEAD` to see every commit that will land.\n3. Confirm the title accurately describes what's merging (≤70 chars, imperative mood).\n4. Confirm the body's Summary / Test plan / any bullet lists match what's actually in the diff — updates, deferrals, and out-of-scope carve-outs should all be reflected.\n5. If anything has drifted (new commits addressing review feedback, scope changes, corrections landed since the original body), update via `gh pr edit <N> --title \"...\" --body \"...\"` BEFORE running `gh pr merge`.\n\nThe merge commit on main inherits the current PR body — stale bodies bake bad history into the repo. Only proceed with `gh pr merge` after confirming the PR metadata is current."
  }
}
HEREDOC
exit 0
