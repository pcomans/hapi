---
name: watch-pr-reviews
description: After pushing to a PR branch, arm a Monitor that notifies on any new review (any reviewer, first review or re-review) landing on the current HEAD commit. Filters out reviews already present at invocation time so only genuinely new reviews fire.
allowed-tools: Bash, Monitor
---

Default args (derive if not supplied):
- `PR` = `gh pr view --json number -q .number`
- `SHA` = `git rev-parse HEAD`
- `REPO` = `gh repo view --json nameWithOwner -q .nameWithOwner`

Arm a `Monitor` with a 15-minute timeout and this command. The poll logic lives in committed Python files (`seed.py`, `poll.py`) next to this skill — the bash wrapper just invokes them, so no Python source is ever embedded in the bash string.

```bash
PR=<pr>; SHA=<sha>; REPO=<owner/repo>
TOKEN=$(gh auth token)
SEEN=$(mktemp)
SKILL_DIR=.claude/skills/watch-pr-reviews

curl -sS -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/$REPO/pulls/$PR/reviews" \
  | SHA="$SHA" python3 "$SKILL_DIR/seed.py" > "$SEEN"

while true; do
  curl -sS -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$REPO/pulls/$PR/reviews" 2>&1 \
    | SEEN="$SEEN" SHA="$SHA" python3 "$SKILL_DIR/poll.py"
  sleep 30
done
```

Rules (load-bearing — do not relax):
- **Python lives in committed `.py` files, never embedded in `python3 -c "..."`.** Every past attempt to inline the poll logic hit a different shell-escape landmine (`!=` expanded by zsh history, nested double quotes mangled, backslashes injected). The `.py` files sidestep all of it.
- `curl` + `python3`. Not `gh api` (keychain TLS error in the Monitor's sandbox). Not `jq` (silently errors on control characters in review bodies).
- `poll.py` surfaces JSON parse errors as `POLL-ERROR:` lines on stdout. Do not wrap the `python3` call in `2>/dev/null` — silenced errors hid four consecutive Monitor failures in one session.
- On event, fetch inline comments with `curl .../pulls/$PR/comments`.
- If the 15-minute timeout fires with no event, verify manually via `curl .../pulls/$PR/reviews` and re-arm. Timeout is **not** acceptance.
