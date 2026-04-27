#!/bin/bash
# PreToolUse hook for `gh pr comment`:
# Blocks unless SCOPE_CHECKED=1 is passed, forcing the agent to invoke the
# scope-accountability-enforcer subagent before posting a response to feedback.
#
# Rationale: the main agent tends to defer in-scope work ("I'll handle this in
# Phase A...") when responding to reviewers. The enforcer subagent challenges
# those deferrals. This hook ensures the enforcer runs before any public reply.
#
# Implementation: shlex tokenisation (same pattern as block-curl-github.sh
# and post-pr-create.sh). A pure-grep matcher misfires when a commit body /
# heredoc literally contains `gh pr comment` as a quoted example (e.g. when
# documenting this hook). shlex strips quoting so the verb check operates
# on actual tokens, not on string contents.

CMD=$(echo "$TOOL_INPUT" | jq -r '.command // ""' 2>/dev/null)
if [ -z "$CMD" ]; then
  CMD=$(jq -r '.tool_input.command // ""' 2>/dev/null)
fi

# Empty CMD → nothing to check.
[ -z "$CMD" ] && exit 0

# Decide via python3 + shlex. Outputs a single token: BLOCK, EXEMPT, or OK.
#  - BLOCK: at least one statement is `gh pr comment <args>` and SCOPE_CHECKED=1
#    is not present in the env-var prefix of that statement. Also exclude
#    `/gemini ...` trigger comments (workflow triggers, not feedback replies).
#  - EXEMPT: SCOPE_CHECKED=1 set OR every gh-pr-comment statement is a
#    /gemini trigger.
#  - OK: no `gh pr comment` invocation at all (e.g. `git commit` whose body
#    happens to contain the literal string).
DECISION=$(CMD_TO_CHECK="$CMD" python3 <<'PYEOF'
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
    # Unbalanced quotes — let it through; loud-fail elsewhere.
    print("OK")
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

found_any_pr_comment = False

for stmt in statements:
    # Capture any env-var prefixes (so we can detect SCOPE_CHECKED=1).
    env_prefixes = []
    i = 0
    while i < len(stmt) and ENV_VAR_RE.match(stmt[i]):
        env_prefixes.append(stmt[i])
        i += 1
    if i + 2 >= len(stmt):
        continue
    verb, sub, action = stmt[i], stmt[i + 1], stmt[i + 2]
    rest = stmt[i + 3:]
    if verb != "gh" or sub != "pr" or action != "comment":
        continue

    found_any_pr_comment = True

    # SCOPE_CHECKED=1 anywhere in the env prefix exempts this statement.
    if any(p == "SCOPE_CHECKED=1" for p in env_prefixes):
        continue

    # /gemini trigger comments are exempt (workflow triggers, not replies).
    # Look for `--body /gemini...`, `--body=/gemini...`, `-b /gemini...`,
    # `-b=/gemini...`.
    is_gemini_trigger = False
    j = 0
    while j < len(rest):
        t = rest[j]
        if t in ("--body", "-b"):
            if j + 1 < len(rest) and rest[j + 1].lstrip().startswith("/gemini"):
                is_gemini_trigger = True
                break
            j += 2
            continue
        if t.startswith("--body=") and t[len("--body="):].lstrip().startswith("/gemini"):
            is_gemini_trigger = True
            break
        if t.startswith("-b=") and t[len("-b="):].lstrip().startswith("/gemini"):
            is_gemini_trigger = True
            break
        j += 1
    if is_gemini_trigger:
        continue

    print("BLOCK")
    sys.exit(0)

# We saw at least one gh pr comment but every one was exempted (gemini
# trigger or SCOPE_CHECKED=1).
if found_any_pr_comment:
    print("EXEMPT")
else:
    print("OK")
PYEOF
)

if [ "$DECISION" = "BLOCK" ]; then
  cat <<'HEREDOC'
{
  "decision": "block",
  "reason": "Before posting a reply to PR feedback, you MUST invoke the scope-accountability-enforcer subagent to verify you are not improperly deferring in-scope work. Then re-run this command prefixed with SCOPE_CHECKED=1 (e.g., SCOPE_CHECKED=1 gh pr comment ...)."
}
HEREDOC
  exit 0
fi

exit 0
