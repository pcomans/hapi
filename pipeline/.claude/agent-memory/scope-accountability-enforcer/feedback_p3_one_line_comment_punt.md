---
name: p3-one-line-comment-deferrals-when-reviewer-named-the-failure-mode
description: P3 docstring/comment deferrals are illegitimate when the reviewer already articulated a specific failure mode the comment prevents
type: feedback
---

P3 findings (doc nits, comments) are NOT under the strict-all-P1 merge policy. But "P3 + low value" is not a valid blanket dismissal when:

- The reviewer named a **specific** future-maintainer misreading risk (e.g. "a future maintainer will 'fix' the asymmetry"), AND
- The fix is one line of comment / docstring.

**Why:** The reviewer already paid the cost of articulating the value. The agent's "low value vs work" framing ignores that the value calculation was already done by the reviewer. One-line comment work is ~30 seconds; the failure mode is concrete.

**How to apply:** When a P3 deferral cites "low value" or "doc-only nit," check whether the reviewer's finding includes a **named specific** future failure mode. If yes, the deferral is an ILLEGITIMATE (mild) PUNT — apply the one-line fix. Pure stylistic nits ("could be clearer") without a named failure mode are legitimate P3 deferrals.

Saved 2026-05-03 from PR #190 audit (code-reviewer P3.2 / P3.4).
