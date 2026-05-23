---
name: zero-hits-defense-against-silent-fallback-findings
description: "Zero hits in current corpus" is NOT a valid rejection for reviewer findings about silent failure modes; constitutes a Rule-2 punt
type: feedback
---

When a reviewer flags a regex / parser / lookup that **silently returns None / empty / shorter-list** on edge-case input, the main agent often defers with "real-data check shows zero hits in current corpus."

This reasoning is invalid as a rejection.

**Why:** The reviewer's concern IS the silent-failure mode. Post-extraction reconciled-row evidence cannot distinguish "input never occurred" from "input occurred and was silently dropped" — both produce identical output (None / absent). Constitutional Rule 2 ("no silent fallbacks") makes this exact failure mode the thing the rule forbids. Using the rule's own failure surface to argue against fixing the rule violation is circular.

**How to apply:** When auditing a deferral that cites "zero hits in current corpus" against a reviewer-flagged silent-fallback regex/parser:
- If the reviewer proposed a cheap zero-risk hardening (e.g. tighten regex, add lookahead, normalize case): the deferral is an ILLEGITIMATE PUNT. The hardening IS the Rule-2 compliance. Demand the fix.
- If the only fix is widening with new false-positive risk: the "zero hits" check is still inadequate — the agent must verify against the **source** (PDF / API), not the post-extraction reconciled output, before deferring.
- Specifically named rows in the reviewer finding (e.g. "baud-85 doc 3 if punctuation is a period") are diagnosis-with-source-verification-needed, not diagnosis-resolved-by-output-grep.

Saved 2026-05-03 from PR #190 (Baud 1999 #178) audit; pattern repeated on egyptologist P2.1 / P2.3 / P2.4.
