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

# Normalise the command once: strip the trailing `\` that shell line-
# continuations leave at end-of-line, THEN flatten newlines to spaces.
# Without the strip step, a split like `curl -X \<NL>PUT` flattens to
# `curl -X \ PUT`, and the subsequent `-X[ =]*PUT` method-grep fails
# because `[ =]*` does not match a literal backslash. Using
# `printf '%s\n'` rather than `echo` avoids `echo`'s misbehaviour when
# the first argument starts with `-`. Gemini round-1 HIGH + round-4
# medium findings on PR #104.
CMD_FLAT=$(printf '%s\n' "$CMD" | sed 's/\\$//' | tr '\n' ' ')

# --- Block 1: curl-to-API merge bypass --------------------------------------
# Three independent AND-ed checks so an adversarially-formatted merge call
# still trips the hook:
#   (a) `\bcurl\b` somewhere in the flattened command;
#   (b) the GitHub pulls-merge URL path somewhere in the flattened command;
#   (c) a PUT method flag somewhere in the flattened command.
# Splitting into three independent matches (rather than `\bcurl\b.*URL`)
# closes the `URL="..."; curl -X PUT $URL` bypass where the URL appears
# BEFORE `curl` in the shell source. A read-only GET on the same endpoint
# ("has this PR been merged?") has no PUT flag, so it passes unblocked.
# Method alternation covers `-X`, `--request`, and `--method` (case-
# insensitive) with optional space / `=` / surrounding quotes around PUT
# (e.g. `-X "PUT"`, `--request='PUT'`). Word boundaries on `curl` and the
# URL suffix prevent substring false-positives (e.g. `occurl`, or commands
# that merely echo the URL as text — including this hook's own output).
# Gemini round-2 + round-3 findings on PR #104.
if printf '%s' "$CMD_FLAT" | grep -qE '\bcurl\b' \
   && printf '%s' "$CMD_FLAT" | grep -qE '/repos/[^/]+/[^/]+/pulls/[0-9]+/merge\b' \
   && printf '%s' "$CMD_FLAT" | grep -qiE "(-X|--request|--method)[ =]*[\"']?PUT[\"']?"; then
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
# `\bgh\b.*\bpr[[:space:]]+merge\b` allows global `gh` flags (like
# `--repo o/r`) to appear between `gh` and `pr` (round-3 requirement), but
# requires `pr` and `merge` to be adjacent with only whitespace between
# them — `pr merge` IS the canonical gh subcommand sequence. Round-4
# finding: the looser `gh.*pr.*merge` matched unrelated invocations like
# `gh pr list --search "merge"` or `gh pr view --json body`. Restoring
# pr+merge adjacency eliminates that class of false positive without
# re-opening the global-flag bypass.
if ! printf '%s' "$CMD_FLAT" | grep -qE '\bgh\b.*\bpr[[:space:]]+merge\b'; then
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
