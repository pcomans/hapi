---
name: watch-pr-reviews
description: After pushing to a PR branch, arm a Monitor that notifies on any new review (any reviewer, first review or re-review) landing on the current HEAD commit. Filters out reviews already present at invocation time so only genuinely new reviews fire.
allowed-tools: Bash, Monitor
---

Default args (derive if not supplied):
- `PR` = `gh pr view --json number -q .number`
- `SHA` = `git rev-parse HEAD`
- `REPO` = `gh repo view --json nameWithOwner -q .nameWithOwner`

Arm a `Monitor` with a 15-minute timeout and this command. Seed the "already seen" set before the loop so only new reviews fire:

```bash
TOKEN=$(gh auth token)
SEEN=$(mktemp)
curl -sS -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/$REPO/pulls/$PR/reviews" \
  | SHA="$SHA" python3 -c "
import json, os, sys
for r in json.loads(sys.stdin.read(), strict=False):
    if r.get('commit_id') == os.environ['SHA']:
        print(r['id'])
" > "$SEEN"

while true; do
  resp=$(curl -sS -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$REPO/pulls/$PR/reviews" 2>&1)
  out=$(printf '%s' "$resp" | SEEN="$SEEN" SHA="$SHA" python3 -c "
import json, os, sys
try:
    data = json.loads(sys.stdin.read(), strict=False)
except Exception as e:
    print(f'POLL-ERROR: {e}'); sys.exit(0)
seen = set(open(os.environ['SEEN']).read().split())
for r in data:
    if r.get('commit_id') != os.environ['SHA']: continue
    rid = str(r['id'])
    if rid in seen: continue
    print(f\"REVIEW {r['user']['login']} {r.get('state','?')} id={rid}\")
    open(os.environ['SEEN'], 'a').write(rid + '\n')
" 2>&1)
  [ -n "$out" ] && echo "$out"
  sleep 30
done
```

Rules (load-bearing — do not relax):
- `curl` + `python3` only. Not `gh api` (keychain TLS error in the Monitor's sandbox). Not `jq` (chokes on control characters inside review bodies, silently).
- Parse or HTTP errors surface as `POLL-ERROR: <detail>` events. Never `2>/dev/null` a poll error — that silenced a four-Monitor streak once.
- On event, follow up with `curl .../pulls/$PR/comments` to fetch inline comments for the review, so the main loop can act on specifics.
- If the 15-minute timeout fires with no event, verify manually via `curl .../pulls/$PR/reviews` — timeout is not acceptance.
