#!/bin/bash
# PreToolUse hook: BLOCK any `curl` against GitHub (api.github.com or
# github.com), read or write. All GitHub interactions must go through
# `gh` so PR/issue creation, comment-posting, and review-fetching all
# route through the workflow hooks (post-pr-create.sh, pre-merge-check.sh).
# Constitutional rule 3: deterministic enforcement over convention.
#
# Why entirely (not just mutations):
#   - Mutations via curl bypass post-pr-create.sh (no reviewer spawning).
#   - Reads via curl are ad-hoc; gh wraps them with auth, retry, paging.
#   - One uniform tool surface = one hook surface.
#
# Detection: any curl invocation whose flat token sequence contains a
# (api.)?github.com host. Covers:
#   * curl https://api.github.com/...
#   * curl -H "..." https://github.com/...
#   * curl ${GITHUB_API}/repos/... where the URL is in an env var → still
#     matches because the literal string is in the command line as
#     "$GITHUB_API/..." or after expansion is in the resolved CMD.
#   * Multi-line continuation (\) — flattened first.
# Method-agnostic: GET / POST / PUT / PATCH / DELETE all blocked.
#
# False-positive avoidance:
#   * Word-boundary anchor on `curl` so `occurl` etc. don't trip.
#   * Statement-start anchor (start of line / after shell separator) so
#     a github.com URL mentioned inside an unrelated command body (e.g.
#     `echo "see https://github.com/foo for details"`) does not match.
#   * Allow `gh api` (which talks to api.github.com under the hood) — the
#     anchor is on the `curl` token, not the host.

CMD=$(echo "$TOOL_INPUT" | jq -r '.command // ""' 2>/dev/null)
if [ -z "$CMD" ]; then
  CMD=$(jq -r '.tool_input.command // ""' 2>/dev/null)
fi

CMD_FLAT=$(printf '%s\n' "$CMD" | sed 's/\\[[:space:]]*$//' | tr '\n' ' ')

# (a) `curl` invoked at a statement boundary, possibly after env-var prefixes
# (b) (api.)?github.com appearing somewhere in the same flat command
if printf '%s\n' "$CMD_FLAT" | grep -qE '(^|[|;&(`$])[[:space:]]*([a-zA-Z_][a-zA-Z0-9_]*=[^[:space:]]*[[:space:]]+)*curl\b' \
   && printf '%s\n' "$CMD_FLAT" | grep -qE '\b(api\.)?github\.com\b'; then
  cat <<'HEREDOC'
{
  "decision": "block",
  "reason": "curl to GitHub is blocked. Use `gh` instead — `gh pr create`, `gh pr comment`, `gh pr view`, `gh issue create`, `gh api repos/owner/repo/pulls/N/comments`, etc. Routing through `gh` ensures PR/issue creation triggers the post-pr-create workflow hook (reviewer spawning, /gemini review, /watch-pr-reviews armament). Constitutional rule 3: deterministic enforcement over convention — one tool surface for GitHub, one hook surface."
}
HEREDOC
  exit 0
fi

exit 0
