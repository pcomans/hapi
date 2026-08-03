#!/bin/bash
# PostToolUse hook for PR-related commands:
# - gh pr create: post an `@codex review` comment. Unlike the retired
#   third-party review app, Codex does NOT auto-review on PR open — it
#   must be triggered explicitly, on creation as well as on every push.
# - git push: post an `@codex review` comment so Codex re-reviews the new HEAD.

# TOOL_INPUT is a JSON env var with the tool's input parameters
# For Bash tool, it contains { "command": "..." }. Older hook format
# wraps it as { "tool_input": { "command": "..." } }; jq's `//` operator
# tries each path in turn.
CMD=$(printf '%s' "$TOOL_INPUT" | jq -r '.command // .tool_input.command // ""' 2>/dev/null)

# Determine what triggered us. We match three patterns:
#   * `gh pr create` — direct PR creation via gh CLI.
#   * `gh api repos/o/r/pulls -X POST` — PR creation via gh REST passthrough.
#   * `git push` — push to a branch that already has an open PR (re-review).
# curl-based PR creation is blocked upstream by block-curl-github.sh, so we
# don't need a curl matcher here.
#
# Use shlex tokenisation (same pattern as block-curl-github.sh) so the
# matchers operate on the actual statement verb + argument tokens, not
# on flat string occurrences. A pure-grep matcher misfires when a
# commit body / PR body / heredoc literally contains the words
# `gh api`, `repos/.../pulls`, and `-X POST` (e.g. when documenting
# this very hook). shlex-then-statement-split-then-verb-check produces
# zero false positives on commit bodies, regardless of content.
IS_PR_CREATE=false
IS_GIT_PUSH=false

# Decide via python3 + shlex. Output is a single token: PR_CREATE,
# GIT_PUSH, or NONE. CMD is passed via env to avoid the heredoc-stdin
# trap (see block-curl-github.sh).
KIND=$(CMD_TO_CLASSIFY="$CMD" python3 <<'PYEOF'
import os
import re
import shlex
import sys

cmd = os.environ.get("CMD_TO_CLASSIFY", "")
if not cmd.strip():
    print("NONE")
    sys.exit(0)

try:
    tokens = shlex.split(cmd, comments=False, posix=True)
except ValueError:
    print("NONE")
    sys.exit(0)

# Re-split on shell statement separators (shlex doesn't split on these
# unless whitespace-separated).
SEP_RE = re.compile(r'(&&|\|\||;|\||&|\(|\))')
flat = []
for t in tokens:
    parts = SEP_RE.split(t)
    for p in parts:
        if p:
            flat.append(p)

SEPS = {"&&", "||", ";", "|", "&", "(", ")"}
statements = []
current = []
for t in flat:
    if t in SEPS:
        if current:
            statements.append(current)
            current = []
    else:
        current.append(t)
if current:
    statements.append(current)

ENV_VAR_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')
# Pattern for the bare pulls collection URL — anchored end-to-end so a
# trailing `/<N>` or `/<N>/...` sub-path does NOT match. Allows host
# prefix (`https://api.github.com/...`) or bare path forms.
PULLS_COLLECTION_RE = re.compile(
    r'(?:^|/)repos/[^/]+/[^/]+/pulls/?$'
)


def find_chain_after_verb(stmt_after_verb, chain):
    """Return the index in `stmt_after_verb` of the LAST chain token,
    skipping global flags between/around them. Global flags are
    handled in two forms:
      * `--flag=value` (single token; consume one).
      * `--flag value` (two tokens; consume two — UNLESS the next
        token equals the expected chain element, in which case treat
        `--flag` as a boolean and consume one).

    Returns the integer index of the last chain element on success,
    or None if the chain is not found in order.

    Example: for `['--repo', 'o/r', 'pr', 'comment', '124']` and
    chain=('pr', 'comment'), returns 3 (index of 'comment').
    """
    j = 0
    chain_idx = 0
    while j < len(stmt_after_verb) and chain_idx < len(chain):
        t = stmt_after_verb[j]
        if t.startswith("-"):
            if "=" in t:
                j += 1
            else:
                if j + 1 < len(stmt_after_verb) \
                        and stmt_after_verb[j + 1] == chain[chain_idx]:
                    j += 1
                else:
                    j += 2
            continue
        if t == chain[chain_idx]:
            chain_idx += 1
            if chain_idx == len(chain):
                return j
            j += 1
        else:
            return None
    return None


def extract_method(rest):
    """Find request method via -X / --request / --method. Walks tokens
    one at a time, only consuming pairs for known method-bearing flags
    so it doesn't mistake an arbitrary flag value for the method."""
    method = None
    j = 0
    while j < len(rest):
        t = rest[j]
        if t in ("-X", "--request", "--method"):
            if j + 1 < len(rest):
                method = rest[j + 1].upper()
                j += 2
                continue
        elif t.startswith("-X="):
            method = t[3:].upper()
        elif t.startswith("--request="):
            method = t[len("--request="):].upper()
        elif t.startswith("--method="):
            method = t[len("--method="):].upper()
        j += 1
    return method


def find_url_matching(rest, pattern):
    """Find the first token in `rest` matching `pattern`. Robust
    against interleaved flag values like `-H "Authorization: ..."`."""
    for t in rest:
        if pattern.search(t):
            return t
    return None


for stmt in statements:
    i = 0
    while i < len(stmt) and ENV_VAR_RE.match(stmt[i]):
        i += 1
    if i >= len(stmt):
        continue
    verb = stmt[i]
    rest = stmt[i + 1:]

    # gh pr create (skips global flags like `gh --repo o/r pr create`)
    if verb == "gh":
        end_idx = find_chain_after_verb(rest, ("pr", "create"))
        if end_idx is not None:
            print("PR_CREATE")
            sys.exit(0)

        # gh api repos/o/r/pulls -X POST (no sub-resource path)
        api_idx = find_chain_after_verb(rest, ("api",))
        if api_idx is not None:
            api_rest = rest[api_idx + 1:]
            method = extract_method(api_rest)
            url = find_url_matching(api_rest, PULLS_COLLECTION_RE)
            if url and method == "POST":
                print("PR_CREATE")
                sys.exit(0)

    # git push
    if verb == "git":
        end_idx = find_chain_after_verb(rest, ("push",))
        if end_idx is not None:
            print("GIT_PUSH")
            sys.exit(0)

print("NONE")
PYEOF
)

case "$KIND" in
    PR_CREATE) IS_PR_CREATE=true ;;
    GIT_PUSH) IS_GIT_PUSH=true ;;
    *) exit 0 ;;
esac

# Find the PR number
PR_NUMBER=$(gh pr view --json number --jq .number 2>/dev/null) || true
if [ -z "$PR_NUMBER" ]; then
  # No PR for this branch — nothing to do
  exit 0
fi

MESSAGES=""
BLOCK_REASON=""

# NOTE on ordering: the `@codex review` trigger is posted AFTER the gates
# below have run, but it is posted whether or not they pass — the gates set
# BLOCK_REASON rather than exiting. Duplicate reviews are prevented by the
# HEAD-SHA check at the trigger itself, not by gate outcome. Suppressing the
# trigger on a failed gate suppressed the FIRST review of a PR that already
# existed on GitHub, which is strictly worse than the duplicate it avoided.

# Add reviewer-spawn requirement for PR creation. Kept focused: reviewer
# spawning + Monitor armament are the tightly-coupled post-PR-creation
# protocol. Task-list updates have their own gate above; doc-learnings
# are soft and don't belong stacked next to a hard rule (signal dilution).
if [ "$IS_PR_CREATE" = true ]; then
  MESSAGES="$MESSAGES\n\nPR #$PR_NUMBER created. Required next actions (the merge will be blocked otherwise):\n1. Spawn code-reviewer AND egyptologist-reviewer subagents IN PARALLEL (single message, two Agent tool calls) against the PR diff.\n2. Arm /watch-pr-reviews so the Codex review notifies you when it lands.\n3. When merging, prefix the command with REVIEWERS_SPAWNED=1 (e.g. REVIEWERS_SPAWNED=1 gh pr merge $PR_NUMBER --squash --delete-branch). The pre-merge hook blocks without it."
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

  # The gate records its verdict but does NOT exit here. This hook is
  # PostToolUse: by the time it runs the push or the PR already happened, so
  # blocking cannot undo it — it only tells the agent to go fix something.
  # Exiting early therefore suppressed the REVIEW of a PR that exists on
  # GitHub regardless, which is how #315 and #316 reached `main`-ready state
  # with no trigger posted. Bookkeeping debt must not cost a code review.
  if [ "$AGENT_CLAIMS_UPDATED" -gt 0 ] && [ "$MVP_IN_DIFF" -gt 0 ]; then
    : # Both conditions met — allow
  elif [ "$AGENT_CLAIMS_UPDATED" -gt 0 ] && [ "$MVP_IN_DIFF" -eq 0 ]; then
    BLOCK_REASON="You passed TASK_LIST_UPDATED=1 but docs/mvp-tasks.md has no changes in the branch diff. You must actually update the file before claiming you did."
  elif [ "$AGENT_CLAIMS_UPDATED" -eq 0 ] && [ "$MVP_IN_DIFF" -gt 0 ]; then
    BLOCK_REASON="docs/mvp-tasks.md was modified but you did not pass TASK_LIST_UPDATED=1 in your push command. Prefix your push with TASK_LIST_UPDATED=1 to confirm you have reviewed the task list and the changes are correct."
  else
    BLOCK_REASON="docs/mvp-tasks.md has not been updated on this branch. Before pushing, update the MVP task list to reflect any completed, dropped, or new tasks, then push with TASK_LIST_UPDATED=1 git push ... to confirm."
  fi
fi

# Trigger the review. Codex never auto-reviews, so BOTH PR creation and
# subsequent pushes post an explicit trigger.
#
# Duplicate suppression is by HEAD SHA, not by gate outcome: skip only when a
# trigger was already posted AFTER the current HEAD commit was authored, which
# means this exact revision has one. That kills the re-push duplicate without
# ever suppressing a revision's FIRST review.
HEAD_SHA=$(git rev-parse HEAD 2>/dev/null)
HEAD_DATE=$(git show -s --format=%cI "$HEAD_SHA" 2>/dev/null)
ALREADY_TRIGGERED=$(gh api "repos/{owner}/{repo}/issues/$PR_NUMBER/comments" \
  --jq "[.[] | select((.body // \"\") | ascii_downcase | gsub(\"^\\\\s+|\\\\s+$\";\"\") == \"@codex review\") | select(.created_at > \"$HEAD_DATE\")] | length" 2>/dev/null)
[ -z "$ALREADY_TRIGGERED" ] && ALREADY_TRIGGERED=0

if [ "$ALREADY_TRIGGERED" -gt 0 ]; then
  MESSAGES="Codex review already requested for HEAD $HEAD_SHA on PR #$PR_NUMBER — not re-posting.\n$MESSAGES"
else
  REVIEW_OUTPUT=$(gh pr comment "$PR_NUMBER" --body "@codex review" 2>&1)
  if [ $? -eq 0 ]; then
    if [ "$IS_GIT_PUSH" = true ]; then
      MESSAGES="Codex re-review requested on PR #$PR_NUMBER.\n$MESSAGES"
    else
      MESSAGES="Codex review requested on PR #$PR_NUMBER.\n$MESSAGES"
    fi
  else
    REVIEW_OUTPUT_FLAT=$(echo "$REVIEW_OUTPUT" | tr '\n' ' ')
    MESSAGES="WARNING: Failed to post @codex review on PR #$PR_NUMBER: $REVIEW_OUTPUT_FLAT. Do NOT silently skip this — tell the user.\n$MESSAGES"
  fi
fi

# The review is now requested; emit the gate's block (if any) as the response.
if [ -n "$BLOCK_REASON" ]; then
  BLOCK_REASON_ESCAPED=$(echo "$BLOCK_REASON" | sed 's/"/\\"/g')
  MESSAGES_ESCAPED=$(echo "$MESSAGES" | sed 's/"/\\"/g')
  cat <<HEREDOC
{
  "decision": "block",
  "reason": "$BLOCK_REASON_ESCAPED",
  "systemMessage": "$MESSAGES_ESCAPED"
}
HEREDOC
  exit 0
fi

# Escape for JSON
MESSAGES_ESCAPED=$(echo "$MESSAGES" | sed 's/"/\\"/g')

cat <<HEREDOC
{
  "systemMessage": "$MESSAGES_ESCAPED"
}
HEREDOC
exit 0
