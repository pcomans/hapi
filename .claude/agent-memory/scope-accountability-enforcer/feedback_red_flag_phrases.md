---
name: Red-flag phrases signaling illegitimate punts
description: Language patterns in main-agent review responses that warrant close scope scrutiny
type: feedback
---

Phrases that signal a likely scope punt and require close inspection:

- "defer to a follow-up PR" / "follow-up needed" — legitimate only with a tracking artifact (see deferral checklist)
- "cross-cutting" / "out of scope for this pass" — often accurate, but check whether the current PR is the cause
- "must be added manually" — diagnosis-without-execution; if the manual addition is in scope, it must happen now
- "known limitation" / "the tool doesn't support this" — explanation of WHY, not justification of WHETHER to defer
- "consistent with existing patterns" — constitutional rule 12 forbids this; existing violations don't justify new ones
- "pre-existing" / "unrelated" applied to CI failures — constitutional rule 11 forbids this
- Domain-jargon authority flexing (e.g., "the iDAI typology filters this out") — explains the pipeline, doesn't answer scope

**Why:** These phrases cluster around the main agent's rationalization patterns. Not every use is a punt, but every use deserves a scope check.

**How to apply:** When any of these phrases appear in a main-agent response, apply the Exemplar Test: has the agent diagnosed a fix within current scope and then declined to execute it? If yes, flag as ILLEGITIMATE PUNT.
