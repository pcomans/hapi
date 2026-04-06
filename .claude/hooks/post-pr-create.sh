#!/bin/bash
# PostToolUse hook: remind agent to document learnings and update task list after creating a PR

# Only fire on gh pr create commands
CMD=$(echo "$TOOL_INPUT" | jq -r '.command // ""' 2>/dev/null)
if ! echo "$CMD" | grep -q 'gh pr create'; then
  exit 0
fi

cat <<'EOF'
{
  "systemMessage": "You just created a PR. Before finishing, you MUST do the following:\n\n1. **Update the task list** — Mark completed tasks as done and add brief notes on what was built. Update any in-progress or blocked tasks.\n\n2. **Document learnings:**\n   - Update docs/museum-sources/*.md with any API quirks, data quality observations, or rate limit findings\n   - Update pipeline/CLAUDE.md or web/CLAUDE.md with any operational patterns or conventions discovered\n   - If an architectural decision was made, consider whether it warrants an ADR in docs/adr/\n\nReview what you learned and write it down in the appropriate place. Do not skip these steps."
}
EOF
exit 0
