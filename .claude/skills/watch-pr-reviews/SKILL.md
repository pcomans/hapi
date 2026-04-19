---
name: watch-pr-reviews
description: After pushing to a PR branch, arm a Monitor that notifies on any new review (any reviewer, first review or re-review) landing on the current HEAD commit. Filters out reviews already present at invocation time so only genuinely new reviews fire.
allowed-tools: Bash, Monitor
---

Arm a `Monitor` with a 15-minute timeout running:

```
.claude/skills/watch-pr-reviews/monitor.sh <PR> [SHA] [owner/repo]
```

- `PR` is **required** — no safe default inside the Monitor sandbox. `gh pr view` uses GraphQL, which fails on keychain TLS there, so the agent arming the Monitor must pass the PR number explicitly (get it via `gh pr view --json number -q .number` from the main agent's shell, not the Monitor's).
- `SHA` defaults to `git rev-parse HEAD` (git-only, sandbox-safe). Any commit-ish is accepted — a short SHA, branch name, tag, or `HEAD~N` all work; `monitor.sh` normalises to the full 40-char SHA via `git rev-parse --verify <X>^{commit}` before passing to the poll loop. (GitHub's `/pulls/<N>/reviews` API returns full 40-char `commit_id` values and the filter uses string equality — without normalisation, a short SHA silently matches nothing and the Monitor polls in silence until it times out.)
- `REPO` defaults to `owner/name` parsed from `git remote get-url origin` (git-only, sandbox-safe).

Rules (load-bearing):
- **Parse / HTTP errors surface as `POLL-ERROR: <detail>`.** The script never `2>/dev/null`s anything — silenced errors ate four consecutive Monitors in one session.
- **Timeout is not acceptance.** If the 15-minute window fires with no event, verify manually via `curl -H "Authorization: token $(gh auth token)" -H "Accept: application/vnd.github+json" .../pulls/<PR>/reviews` and re-arm.
- **Python stays in `seed.py` / `poll.py`**, never inside `python3 -c "..."`. Every attempt to inline the logic hit a shell-escape landmine (`!=` → `\!=` zsh history expansion, env-var passthrough losing state through nested subshells).
- On event, fetch inline comments with `curl -H "Authorization: token $(gh auth token)" -H "Accept: application/vnd.github+json" .../pulls/<PR>/comments` to act on specifics.
- **Not every finding is worth fixing.** Accept findings that address the PR's contract, a real bug, or a documented guarantee the code doesn't meet. Push back on cosmetic parity, stylistic preferences, or defensive detail the PR didn't promise — accepting every suggestion bloats the PR past its brief and is itself a scope failure. The `scope-accountability-enforcer` catches under-accepting (punting in-scope feedback); the reviewer (you) catches over-accepting.
