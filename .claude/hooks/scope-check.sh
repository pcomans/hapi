#!/bin/bash
# PreToolUse hook for `gh pr comment`:
# Blocks unless SCOPE_CHECKED=1 is passed, forcing the agent to invoke the
# scope-accountability-enforcer subagent before posting a response to feedback.
#
# Rationale: the main agent tends to defer in-scope work ("I'll handle this in
# Phase A...") when responding to reviewers. The enforcer subagent challenges
# those deferrals. This hook ensures the enforcer runs before any public reply.

CMD=$(echo "$TOOL_INPUT" | jq -r '.command // ""' 2>/dev/null)
if [ -z "$CMD" ]; then
  CMD=$(jq -r '.tool_input.command // ""' 2>/dev/null)
fi

# Only guard `gh pr comment`. That's the one command where the agent writes
# natural-language responses to reviewer feedback — the place where deferrals
# show up as prose.
if ! echo "$CMD" | grep -q 'gh pr comment'; then
  exit 0
fi

if echo "$CMD" | grep -q 'SCOPE_CHECKED=1'; then
  exit 0
fi

cat <<'HEREDOC'
{
  "decision": "block",
  "reason": "Before posting a reply to PR feedback, you MUST invoke the scope-accountability-enforcer subagent to verify you are not improperly deferring in-scope work. Then re-run this command prefixed with SCOPE_CHECKED=1 (e.g., SCOPE_CHECKED=1 gh pr comment ...)."
}
HEREDOC
exit 0
