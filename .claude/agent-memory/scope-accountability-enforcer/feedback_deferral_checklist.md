---
name: Deferral legitimacy checklist
description: Two conditions every "defer to follow-up PR" response must satisfy to avoid being an illegitimate punt
type: feedback
---

When the main agent defers a review finding to a follow-up PR, the deferral is only legitimate if BOTH conditions hold:

1. **The current PR is not the cause or amplifier of the problem.** If the current PR introduced the issue, or grew an exception list, or added a new override — the fix belongs here, not a follow-up.
2. **A concrete, trackable follow-up artifact is recorded.** This means a `docs/mvp-tasks.md` entry, a GitHub issue, or an equivalent durable reference — cited by identifier in the PR reply. "Deferred to follow-up PR" without an artifact is a punt.

**Why:** "Follow-up PR" is one of the highest-frequency rationalization phrases for scope punts. Without a durable artifact, the follow-up quietly disappears and the debt compounds.

**How to apply:** When auditing any deferral, explicitly check for both conditions. If either is missing, flag as ILLEGITIMATE PUNT and require the main agent to either do the work now or produce the tracking artifact before replying to the reviewer.
