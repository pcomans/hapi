#!/bin/bash
# PreToolUse hook for PR merges:
# - Block 1 — `curl -X PUT .../pulls/<N>/merge` and `gh api -X PUT
#   .../pulls/<N>/merge`: BLOCK the call. The agent has been bypassing
#   the `gh pr merge` reminder by using REST passthrough directly.
#   This hook funnels all merges through the single enforced path.
#   Constitutional rule 3 (deterministic enforcement over convention).
# - Block 1.5 — `gh pr merge` without `REVIEWERS_SPAWNED=1`: BLOCK.
#   Mirrors the existing TASK_LIST_UPDATED=1 idiom; forces explicit
#   confirmation that code-reviewer + egyptologist-reviewer subagents
#   were spawned in parallel against the PR diff before merging.
# - Block 2 — `gh pr merge` (with REVIEWERS_SPAWNED=1): inject a
#   reminder to verify PR title and description match the final merged
#   state before the merge lands. PR titles and bodies are written at
#   PR-open time and frequently drift as commits accrete; the merge
#   commit on main inherits whatever the PR body currently says.
#
# Implementation: shlex tokenisation (same pattern as the other hooks
# in this dir). Earlier rounds of regex-only matching had documented
# false-positive classes when commit bodies / PR descriptions
# literally quoted the matched patterns. shlex tokens come from
# POSIX-aware quoting, so the verb check operates on actual command
# tokens, not on string contents inside quoted arguments.

CMD=$(printf '%s' "$TOOL_INPUT" | jq -r '.command // .tool_input.command // ""' 2>/dev/null)

# Empty CMD → nothing to check.
[ -z "$CMD" ] && exit 0

# Decide via python3 + shlex. Output is one of:
#   API_PUT_MERGE_BYPASS — curl or gh-api PUT to /pulls/<N>/merge
#   GH_PR_MERGE_NEED_REVIEWERS — gh pr merge without REVIEWERS_SPAWNED=1
#   GH_PR_MERGE_OK — gh pr merge with REVIEWERS_SPAWNED=1
#   NONE — no merge-relevant statement found
DECISION=$(CMD_TO_CHECK="$CMD" python3 <<'PYEOF'
import os
import re
import shlex
import sys

cmd = os.environ.get("CMD_TO_CHECK", "")
if not cmd.strip():
    print("NONE")
    sys.exit(0)

try:
    tokens = shlex.split(cmd, comments=False, posix=True)
except ValueError:
    print("NONE")
    sys.exit(0)

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
# PULLS_MERGE_RE matches both the gh-api short form
# (`repos/o/r/pulls/N/merge`) and the curl long form
# (`https://api.github.com/repos/o/r/pulls/N/merge`). Anchored on
# `(?:^|/)repos/...` so any valid URL prefix (host, scheme, leading
# slash, or none) passes; trailing `(?:/|$)` so a longer sub-path
# (`/merge/foo`) does NOT spuriously match.
PULLS_MERGE_RE = re.compile(
    r'(?:^|/)repos/[^/]+/[^/]+/pulls/[0-9]+/merge(?:/|$)'
)


def extract_method(rest):
    """Walk `rest` looking for the request method via `-X / --request /
    --method`. Handles both `-X POST` and `-X=POST` forms. Other flags
    that take values (e.g. curl's `-H "..."`) are tolerated by walking
    one token at a time and not consuming arbitrary flag values."""
    method = None
    j = 0
    while j < len(rest):
        t = rest[j]
        if t in ("-X", "--request", "--method"):
            if j + 1 < len(rest):
                method = rest[j + 1].strip("\"'").upper()
                j += 2
                continue
        elif t.startswith("-X="):
            method = t[3:].strip("\"'").upper()
        elif t.startswith("--request="):
            method = t[len("--request="):].strip("\"'").upper()
        elif t.startswith("--method="):
            method = t[len("--method="):].strip("\"'").upper()
        j += 1
    return method


def find_pulls_merge_url(rest, pattern):
    """Walk `rest` and return the first token that matches `pattern`.
    More robust than picking-the-first-non-flag-token because curl
    invocations interleave flag values (`-H "Authorization: ..."`) with
    URLs; we don't want to mistake a header value for a URL. Pattern
    is precompiled and matches the path shape, which can appear
    anywhere in the token (host prefix, leading slash, or bare)."""
    for t in rest:
        if pattern.search(t):
            return t
    return None


for stmt in statements:
    env_prefixes = []
    i = 0
    while i < len(stmt) and ENV_VAR_RE.match(stmt[i]):
        env_prefixes.append(stmt[i])
        i += 1
    if i >= len(stmt):
        continue
    verb = stmt[i]
    rest_after_verb = stmt[i + 1:]

    # Block 1: curl PUT to /pulls/<N>/merge
    if verb == "curl":
        method = extract_method(rest_after_verb)
        url = find_pulls_merge_url(rest_after_verb, PULLS_MERGE_RE)
        if url and method == "PUT":
            print("API_PUT_MERGE_BYPASS")
            sys.exit(0)
        # Curl to anything else — defer to other hooks (block-curl-github.sh
        # already covers all curl-to-github traffic).
        continue

    # Block 1: gh api PUT to /pulls/<N>/merge
    if verb == "gh" and len(rest_after_verb) >= 1 and rest_after_verb[0] == "api":
        sub = rest_after_verb[1:]
        method = extract_method(sub)
        url = find_pulls_merge_url(sub, PULLS_MERGE_RE)
        if url and method == "PUT":
            print("API_PUT_MERGE_BYPASS")
            sys.exit(0)
        continue

    # Block 1.5 / Block 2: gh pr merge
    if (verb == "gh"
            and len(rest_after_verb) >= 2
            and rest_after_verb[0] == "pr"
            and rest_after_verb[1] == "merge"):
        if any(p == "REVIEWERS_SPAWNED=1" for p in env_prefixes):
            print("GH_PR_MERGE_OK")
            sys.exit(0)
        print("GH_PR_MERGE_NEED_REVIEWERS")
        sys.exit(0)

print("NONE")
PYEOF
)

case "$DECISION" in
    API_PUT_MERGE_BYPASS)
        cat <<'HEREDOC'
{
  "decision": "block",
  "reason": "Direct curl/gh-api PUT-to-/pulls/<N>/merge bypasses the pre-merge-check reminder and the REVIEWERS_SPAWNED=1 gate. Use `REVIEWERS_SPAWNED=1 gh pr merge <N> --squash --delete-branch` instead (add `--body '...'` if you need a custom merge commit message). The `gh pr merge` route is the single enforced merge path: it triggers Block 1.5 (REVIEWERS_SPAWNED=1 gate) AND Block 2 (title/body drift reminder). Constitutional rule 3: deterministic enforcement over convention — one merge path, one hook."
}
HEREDOC
        exit 0
        ;;
    GH_PR_MERGE_NEED_REVIEWERS)
        cat <<'HEREDOC'
{
  "decision": "block",
  "reason": "Merge blocked: REVIEWERS_SPAWNED=1 not set. Before merging, you MUST have spawned code-reviewer AND egyptologist-reviewer subagents in parallel against the PR diff (memory: feedback_pr_reviewers.md), confirmed Gemini/Codex review on the current HEAD via `gh api repos/{owner}/{repo}/pulls/<N>/reviews` (memory: feedback_never_merge_without_gemini_or_codex.md), and addressed every reviewer finding. Once done, re-run with `REVIEWERS_SPAWNED=1 gh pr merge ...` to confirm. Constitutional rule 3: deterministic enforcement over convention."
}
HEREDOC
        exit 0
        ;;
    GH_PR_MERGE_OK)
        cat <<'HEREDOC'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "BEFORE merging this PR, verify the PR title and description reflect the FINAL merged state — not the state at PR-open time. Specifically:\n\n1. Run `gh pr view <N>` and read the current title + body.\n2. Run `git log --oneline main..HEAD` to see every commit that will land.\n3. Confirm the title accurately describes what's merging (≤70 chars, imperative mood).\n4. Confirm the body's Summary / Test plan / any bullet lists match what's actually in the diff — updates, deferrals, and out-of-scope carve-outs should all be reflected.\n5. If anything has drifted (new commits addressing review feedback, scope changes, corrections landed since the original body), update via `gh pr edit <N> --title \"...\" --body \"...\"` BEFORE running `gh pr merge`.\n\nThe merge commit on main inherits the current PR body — stale bodies bake bad history into the repo. Only proceed with `gh pr merge` after confirming the PR metadata is current."
  }
}
HEREDOC
        exit 0
        ;;
    *)
        exit 0
        ;;
esac
