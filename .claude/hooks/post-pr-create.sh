#!/bin/bash
# PostToolUse hook for PR-related commands:
# - gh pr create: request Copilot review + remind agent to document learnings
# - git push: request Copilot review if on a PR branch

# TOOL_INPUT is a JSON env var with the tool's input parameters
# For Bash tool, it contains { "command": "..." }
CMD=$(echo "$TOOL_INPUT" | jq -r '.command // ""' 2>/dev/null)

# Fallback: try reading from stdin (older hook format uses .tool_input.command)
if [ -z "$CMD" ]; then
  CMD=$(jq -r '.tool_input.command // ""' 2>/dev/null)
fi

# Determine what triggered us
IS_PR_CREATE=false
IS_GIT_PUSH=false

if echo "$CMD" | grep -q 'gh pr create'; then
  IS_PR_CREATE=true
elif echo "$CMD" | grep -q '^git push'; then
  IS_GIT_PUSH=true
else
  exit 0
fi

# Find the PR number
PR_NUMBER=$(gh pr view --json number --jq .number 2>/dev/null) || true
if [ -z "$PR_NUMBER" ]; then
  # No PR for this branch — nothing to do
  exit 0
fi

# Request Copilot review and verify it was added
REVIEW_OUTPUT=$(gh pr edit "$PR_NUMBER" --add-reviewer @copilot 2>&1)
REVIEW_STATUS=$?

# Verify the reviewer was actually added
REVIEWERS=$(gh pr view "$PR_NUMBER" --json reviewRequests --jq '.reviewRequests[].login' 2>/dev/null)
COPILOT_ADDED=false
if echo "$REVIEWERS" | grep -qi copilot; then
  COPILOT_ADDED=true
fi

# Build the response message
MESSAGES=""

if [ "$COPILOT_ADDED" = true ]; then
  MESSAGES="Copilot review requested on PR #$PR_NUMBER."
elif [ $REVIEW_STATUS -ne 0 ]; then
  MESSAGES="WARNING: Failed to request Copilot review on PR #$PR_NUMBER: $REVIEW_OUTPUT. Do NOT silently skip this — tell the user."
else
  MESSAGES="WARNING: Copilot review request returned success but reviewer was not added to PR #$PR_NUMBER. Do NOT silently skip this — tell the user."
fi

# Add documentation reminder for PR creation
if [ "$IS_PR_CREATE" = true ]; then
  MESSAGES="$MESSAGES\n\nYou just created PR #$PR_NUMBER. Before finishing, you MUST:\n1. Update the task list — mark completed tasks as done.\n2. Document learnings in docs/museum-sources/*.md or pipeline/CLAUDE.md.\n3. Wait for CI to pass and Copilot review, then reply to every comment."
fi

# MVP task list guard: agent must pass TASK_LIST_UPDATED=1 AND the file must be in the diff.
# This forces the agent to consciously confirm it reviewed and updated the task list.
#   TASK_LIST_UPDATED=1 + file changed  → allow (agent thought about it, file confirms)
#   TASK_LIST_UPDATED=1 + file unchanged → block (agent is lying)
#   no flag + file changed              → block (agent didn't consciously confirm)
#   no flag + file unchanged             → block (agent didn't think about it)
if [ "$IS_GIT_PUSH" = true ] || [ "$IS_PR_CREATE" = true ]; then
  AGENT_CLAIMS_UPDATED=$(echo "$CMD" | grep -c 'TASK_LIST_UPDATED=1')
  MVP_IN_DIFF=$(git diff origin/main...HEAD --name-only 2>/dev/null | grep -c 'docs/mvp-tasks.md')

  if [ "$AGENT_CLAIMS_UPDATED" -gt 0 ] && [ "$MVP_IN_DIFF" -gt 0 ]; then
    : # Both conditions met — allow
  elif [ "$AGENT_CLAIMS_UPDATED" -gt 0 ] && [ "$MVP_IN_DIFF" -eq 0 ]; then
    cat <<HEREDOC
{
  "decision": "block",
  "reason": "You passed TASK_LIST_UPDATED=1 but docs/mvp-tasks.md has no changes in the branch diff. You must actually update the file before claiming you did."
}
HEREDOC
    exit 0
  elif [ "$AGENT_CLAIMS_UPDATED" -eq 0 ] && [ "$MVP_IN_DIFF" -gt 0 ]; then
    cat <<HEREDOC
{
  "decision": "block",
  "reason": "docs/mvp-tasks.md was modified but you did not pass TASK_LIST_UPDATED=1 in your push command. Prefix your push with TASK_LIST_UPDATED=1 to confirm you have reviewed the task list and the changes are correct."
}
HEREDOC
    exit 0
  else
    cat <<HEREDOC
{
  "decision": "block",
  "reason": "docs/mvp-tasks.md has not been updated on this branch. Before pushing, update the MVP task list to reflect any completed, dropped, or new tasks, then push with TASK_LIST_UPDATED=1 git push ... to confirm."
}
HEREDOC
    exit 0
  fi
fi

# Escape for JSON
MESSAGES_ESCAPED=$(echo "$MESSAGES" | sed 's/"/\\"/g')

cat <<HEREDOC
{
  "systemMessage": "$MESSAGES_ESCAPED"
}
HEREDOC
exit 0
