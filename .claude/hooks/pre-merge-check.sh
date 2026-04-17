#!/bin/bash
# PreToolUse hook for `gh pr merge`:
# Injects a reminder to verify the PR title and description match the final
# merged state before the merge lands.
#
# Rationale: PR titles and bodies are written at PR-open time and frequently
# drift as commits accrete, reviewers request changes, and scope shifts. The
# merge commit message on main inherits whatever the PR body currently says,
# so a stale body bakes bad history into the repo. This hook forces a
# deliberate review step at the last responsible moment.

CMD=$(echo "$TOOL_INPUT" | jq -r '.command // ""' 2>/dev/null)
if [ -z "$CMD" ]; then
  CMD=$(jq -r '.tool_input.command // ""' 2>/dev/null)
fi

# Only fire on `gh pr merge`. Any other Bash command passes through untouched.
if ! echo "$CMD" | grep -q 'gh pr merge'; then
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
