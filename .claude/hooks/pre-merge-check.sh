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
#
# KNOWN LIMITATIONS (shlex rewrite TODO).
# After 8 rounds of regex hardening the matcher reliably handles every
# realistic agent-originated merge-attempt form (bare curl/gh/gh-api,
# multi-line `\` continuations, env-var prefixes, space- or `=`-separated
# flag values, quoted-argument MENTIONS inside other commands). It has,
# however, hit its ceiling on adversarial shell tokenisation:
#   - Env-var VALUES with quoted whitespace (`FOO="bar baz" curl ...`) —
#     the `VAR=[^[:space:]]*` pattern truncates at the first internal
#     space and falls out of the prefix group. Gemini's round-8 cited
#     examples used impossible inputs (repo slugs cannot contain
#     whitespace; GitHub PATs are alphanumeric), but the underlying
#     regex gap generalises to any env-var whose value happens to carry
#     quoted spaces (e.g. `GIT_AUTHOR_NAME="John Doe"`).
#   - Flag VALUES with quoted whitespace (`gh --repo "owner/repo name"
#     api ...`) — same root cause.
# A proper fix needs shell-aware tokenisation: invoke
#   python3 -c "import shlex, sys; print('\n'.join(shlex.split(sys.stdin.read())))"
# on `$CMD_FLAT`, split the token list on `;`/`&&`/`||`/`|`, and inspect
# the first token of each statement. That is a categorically different
# mechanism from a regex patch and is tracked as a follow-up PR rather
# than another round of regex accretion. See this block for the current
# state-of-the-art regex; see the harness at `/tmp/claude/run-hook-tests.sh`
# (local dev artifact, not versioned) for the 42 cases it covers.

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
CMD_FLAT=$(printf '%s\n' "$CMD" | sed 's/\\[[:space:]]*$//' | tr '\n' ' ')

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
# The statement-start anchor ensures the forbidden verb is being INVOKED,
# not merely mentioned inside a quoted string. Additional round-6
# hardening:
#   * `(VAR=val[[:space:]]+)*` absorbs zero-or-more leading env-var
#     assignments (`GITHUB_TOKEN=xxx curl -X PUT ...`) which the plain
#     anchor would have missed;
#   * alternation `curl|gh\b.*\bapi` also blocks `gh api -X PUT .../merge`,
#     the sibling bypass route — `gh api` hits the same REST endpoint
#     without going through `gh pr merge` so the title-drift reminder is
#     skipped;
#   * URL path made `/?repos/...` so `gh api repos/o/r/pulls/N/merge`
#     (leading-slash-omitted form that gh api accepts) still matches;
#   * `printf '%s\n'` (trailing newline) for POSIX-portable `grep` input.
# Statement separators covered: start-of-string, `|`, `;`, `&`, `(`.
# Gemini round-2 + round-3 + round-5 + round-6 findings on PR #104.
if printf '%s\n' "$CMD_FLAT" | grep -qE '(^|[|;&(])[[:space:]]*([a-zA-Z_][a-zA-Z0-9_]*=[^[:space:]]*[[:space:]]+)*(curl|gh\b([[:space:]]+--?[a-zA-Z0-9-]+(=[^[:space:]]*)?([[:space:]]+[^-[:space:]][^[:space:]]*)?)*[[:space:]]+api)\b' \
   && printf '%s\n' "$CMD_FLAT" | grep -qE '/?repos/[^/]+/[^/]+/pulls/[0-9]+/merge\b' \
   && printf '%s\n' "$CMD_FLAT" | grep -qiE "(-X|--request|--method)[ =]*[\"']?PUT[\"']?"; then
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
# Regex requires:
#   - `gh` at a command-statement boundary (start-of-string or after a
#     shell separator `| ; & (`) so strings like
#     `gh pr comment --body "gh pr merge"` or `echo "gh pr merge"` don't
#     false-REMIND (round-5 finding);
#   - `pr merge` adjacent with only whitespace between them, per the
#     round-4 tightening (eliminates `gh pr list --search "merge"` and
#     `gh pr view --json body` false positives);
#   - `.*` between `gh` and `pr` so global flags like `--repo o/r` still
#     pass (round-3 requirement: `gh --repo o/r pr merge` must REMIND);
#   - `(VAR=val[[:space:]]+)*` absorbs leading env-var assignments so
#     `GH_TOKEN=xxx gh pr merge 1` still REMINDs (round-6 finding);
#   - `printf '%s\n'` for POSIX-portable `grep` input.
if ! printf '%s\n' "$CMD_FLAT" | grep -qE '(^|[|;&(])[[:space:]]*([a-zA-Z_][a-zA-Z0-9_]*=[^[:space:]]*[[:space:]]+)*gh\b([[:space:]]+--?[a-zA-Z0-9-]+(=[^[:space:]]*)?([[:space:]]+[^-[:space:]][^[:space:]]*)?)*[[:space:]]+pr[[:space:]]+merge\b'; then
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
