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
# Implementation: shell-aware tokenisation via `python3 -c 'shlex'`. A
# pure-regex pass against the flat command misfires when a PR body /
# comment / heredoc literally contains the words "curl" and
# "github.com" (e.g. when documenting the very block hook below). shlex
# strips quoting so we only see the actual argument tokens, not their
# string contents — `gh pr create --body "we block curl to api.github.com"`
# tokenises to ['gh','pr','create','--body','we block curl to api.github.com']
# and the github.com substring lives inside the --body argument, not as
# its own token, so the per-statement check below correctly does not
# trip on it.
#
# KNOWN EVASION CLASSES (deliberately unhandled — this is policy
# enforcement against accidental bypass, not adversarial sandboxing):
#
#   * **Backtick command substitution:** `echo \`curl ...github.com\``.
#     shlex(posix=True) does not interpret backticks; tokens come out
#     as `['echo', '\\`curl', '...\\`']`, the verb is `echo`, no block.
#     `$(...)` IS handled because SEP_RE catches `(` and `)` as
#     statement separators. Recommended idiom: `$(...)`.
#   * **Indirect invocation via `bash -c "curl ..."`:** quoted
#     argument is one token, verb is `bash`, no block.
#   * **Pipe through `xargs`:** `echo URL | xargs curl` — verb of the
#     final statement is `xargs`, not `curl`.
#
# All three are pre-existing shell-quoting limitations and would require
# a defensive sandboxing-grade matcher to catch (recursive shlex on
# nested -c args; full bash parser). Out of scope: an agent who wants
# to bypass the hook on purpose has many easier paths (e.g. running
# `gh` itself bypasses curl entirely, which is the point). The hook
# closes the accidental-bypass surface — typing `curl` in a normal
# Bash command — not the deliberate-bypass surface.

CMD=$(echo "$TOOL_INPUT" | jq -r '.command // ""' 2>/dev/null)
if [ -z "$CMD" ]; then
  CMD=$(jq -r '.tool_input.command // ""' 2>/dev/null)
fi

# Empty CMD → nothing to check.
[ -z "$CMD" ] && exit 0

# Tokenise the whole command via shlex, then split on shell statement
# separators (;, &, |, &&, ||, (). For each statement, scan the leading
# tokens (skipping env-var assignments like `FOO=bar`) for a `curl`
# command verb. If we find one, check whether ANY token within that
# same statement contains a github.com host.
#
# The python script reads CMD from the CMD_TO_CHECK env var (NOT stdin —
# the heredoc itself redirects stdin to feed python the script, so a
# `printf | python3 <<HEREDOC` pipe is silently swallowed by the
# heredoc redirect). prints "BLOCK" if a blocking pattern is found,
# "OK" otherwise. shlex.split honours POSIX quoting, so quoted strings
# collapse into single tokens whose *content* doesn't pollute the
# per-statement check.
RESULT=$(CMD_TO_CHECK="$CMD" python3 <<'PYEOF'
import os
import re
import shlex
import sys

cmd = os.environ.get("CMD_TO_CHECK", "")
if not cmd.strip():
    print("OK")
    sys.exit(0)

try:
    tokens = shlex.split(cmd, comments=False, posix=True)
except ValueError:
    # Unbalanced quotes etc. — let it through; regex hooks downstream
    # will still see the literal text. Loud failure beats silent block.
    print("OK")
    sys.exit(0)

# Statement separators we recognise as their own tokens after shlex.
# shlex does NOT split on these — it keeps "&&" / "||" / ";" / "|" /
# "(" / ")" as part of adjacent tokens unless they're whitespace-
# separated. So we re-split each token on these operators.
SEP_RE = re.compile(r'(&&|\|\||;|\||&|\(|\))')

flat = []
for t in tokens:
    parts = SEP_RE.split(t)
    for p in parts:
        if p:
            flat.append(p)

# Group tokens into statements (split on separator tokens).
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
GITHUB_RE = re.compile(r'\b(api\.)?github\.com\b')

for stmt in statements:
    # Skip leading env-var assignments to find the verb.
    i = 0
    while i < len(stmt) and ENV_VAR_RE.match(stmt[i]):
        i += 1
    if i >= len(stmt):
        continue
    verb = stmt[i]
    if verb != "curl":
        continue
    # Found a curl invocation. Check if any token in this statement
    # references a github.com host.
    for tok in stmt[i:]:
        if GITHUB_RE.search(tok):
            print("BLOCK")
            sys.exit(0)

print("OK")
PYEOF
)

if [ "$RESULT" = "BLOCK" ]; then
  cat <<'HEREDOC'
{
  "decision": "block",
  "reason": "curl to GitHub is blocked. Use `gh` instead — `gh pr create`, `gh pr comment`, `gh pr view`, `gh issue create`, `gh api repos/owner/repo/pulls/N/comments`, etc. Routing through `gh` ensures PR/issue creation triggers the post-pr-create workflow hook (reviewer spawning, /gemini review, /watch-pr-reviews armament). Constitutional rule 3: deterministic enforcement over convention — one tool surface for GitHub, one hook surface."
}
HEREDOC
  exit 0
fi

exit 0
