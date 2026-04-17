---
name: watch-pr-reviews
description: After pushing to a PR branch, arm a Monitor that notifies on any new review (any reviewer, first review or re-review) landing on the current HEAD commit. Filters out reviews already present at invocation time so only genuinely new reviews fire.
allowed-tools: Bash, Monitor
---

Arm a `Monitor` with a 15-minute timeout running:

```
.claude/skills/watch-pr-reviews/monitor.sh <PR> <SHA> <owner/repo>
```

Default args if not supplied:
- `PR` = `gh pr view --json number -q .number`
- `SHA` = `git rev-parse HEAD`
- `REPO` = `gh repo view --json nameWithOwner -q .nameWithOwner`

Rules (load-bearing):
- **Parse / HTTP errors surface as `POLL-ERROR: <detail>`.** The script never `2>/dev/null`s anything — silenced errors ate four consecutive Monitors in one session.
- **Timeout is not acceptance.** If the 15-minute window fires with no event, verify manually via `curl .../pulls/<PR>/reviews` and re-arm.
- **Python stays in `seed.py` / `poll.py`**, never inside `python3 -c "..."`. Every attempt to inline the logic hit a shell-escape landmine (`!=` → `\!=` zsh history expansion, env-var passthrough losing state through nested subshells).
- On event, fetch inline comments with `curl .../pulls/<PR>/comments` to act on specifics.
