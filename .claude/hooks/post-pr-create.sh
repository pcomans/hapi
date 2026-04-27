#!/bin/bash
# PostToolUse hook for PR-related commands:
# - gh pr create: Gemini Code Assist auto-reviews on PR open; just remind
#   the agent to document learnings.
# - git push: post a /gemini review comment so Gemini re-reviews the new
#   HEAD (auto-review only fires on PR creation, not on subsequent pushes).

# TOOL_INPUT is a JSON env var with the tool's input parameters
# For Bash tool, it contains { "command": "..." }
CMD=$(echo "$TOOL_INPUT" | jq -r '.command // ""' 2>/dev/null)

# Fallback: try reading from stdin (older hook format uses .tool_input.command)
if [ -z "$CMD" ]; then
  CMD=$(jq -r '.tool_input.command // ""' 2>/dev/null)
fi

# Determine what triggered us. We match three patterns:
#   * `gh pr create` — direct PR creation via gh CLI.
#   * `gh api .../pulls -f ...` (POST) — PR creation via gh REST passthrough.
#   * `git push` — push to a branch that already has an open PR (re-review).
# curl-based PR creation is blocked upstream by block-curl-github.sh, so we
# don't need a curl matcher here.
IS_PR_CREATE=false
IS_GIT_PUSH=false

if echo "$CMD" | grep -qE 'gh[[:space:]]+pr[[:space:]]+create\b'; then
  IS_PR_CREATE=true
elif echo "$CMD" | grep -qE 'gh[[:space:]]+api\b' \
     && echo "$CMD" | grep -qE 'repos/[^/]+/[^/]+/pulls([[:space:]]|"|'\''|$)' \
     && echo "$CMD" | grep -qE '(-X|--request|--method)[[:space:]=]*[\"'\'']?POST[\"'\'']?'; then
  # PR creation via gh api uses the *exact* `pulls` collection endpoint
  # (no sub-resource path) with POST. The earlier matcher used
  # `/pulls\b` + `-f`, which also matched
  # `repos/o/r/pulls/<N>/comments/<id>/replies -f body=...` — the
  # CLAUDE.md-mandated review-reply form — and incorrectly tagged
  # every comment-reply as PR-creation. Anchor the URL so a trailing
  # `/<N>/...` sub-path does NOT match: only `…/pulls` followed by
  # whitespace, quote, or end-of-string. Also require explicit
  # `-X POST` (or `--request POST`) since `-f` alone is ambiguous —
  # comment-reply, review-post, and PR-edit all use `-f`.
  IS_PR_CREATE=true
elif echo "$CMD" | grep -qE '^[[:space:]]*([a-zA-Z_][a-zA-Z0-9_]*=[^[:space:]]*[[:space:]]+)*git[[:space:]]+push\b'; then
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

# Build the response message. For PR creation the Gemini Code Assist
# GitHub App auto-reviews; no explicit trigger needed. For subsequent
# pushes we post `/gemini review` so the bot re-reviews the new HEAD.
MESSAGES=""

if [ "$IS_GIT_PUSH" = true ]; then
  REVIEW_OUTPUT=$(gh pr comment "$PR_NUMBER" --body "/gemini review" 2>&1)
  if [ $? -eq 0 ]; then
    MESSAGES="Gemini Code Assist re-review requested on PR #$PR_NUMBER."
  else
    REVIEW_OUTPUT_FLAT=$(echo "$REVIEW_OUTPUT" | tr '\n' ' ')
    MESSAGES="WARNING: Failed to post /gemini review on PR #$PR_NUMBER: $REVIEW_OUTPUT_FLAT. Do NOT silently skip this — tell the user."
  fi
else
  MESSAGES="Gemini Code Assist will auto-review PR #$PR_NUMBER within ~5 minutes."
fi

# Add reviewer-spawn requirement for PR creation. Kept focused: reviewer
# spawning + Monitor armament are the tightly-coupled post-PR-creation
# protocol. Task-list updates have their own gate above; doc-learnings
# are soft and don't belong stacked next to a hard rule (signal dilution).
if [ "$IS_PR_CREATE" = true ]; then
  MESSAGES="$MESSAGES\n\nPR #$PR_NUMBER created. Required next actions (the merge will be blocked otherwise):\n1. Spawn code-reviewer AND egyptologist-reviewer subagents IN PARALLEL (single message, two Agent tool calls) against the PR diff.\n2. Arm /watch-pr-reviews so Gemini's review notifies you when it lands.\n3. When merging, prefix the command with REVIEWERS_SPAWNED=1 (e.g. REVIEWERS_SPAWNED=1 gh pr merge $PR_NUMBER --squash --delete-branch). The pre-merge hook blocks without it."
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
