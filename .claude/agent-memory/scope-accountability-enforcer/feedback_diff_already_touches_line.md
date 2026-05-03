---
name: Diff-already-touches-line scope promotion
description: When the PR diff is editing the exact line/paragraph that contains a factual error a reviewer flagged, deferral becomes a Rule-12 violation
type: feedback
---

If a reviewer flags a factual error or ambiguity on a line that the PR's diff is *already editing*, that finding is in-scope regardless of whether the reviewer recommended tracking it in a follow-up issue.

**Why:** Constitutional Rule 12 says existing violations do not justify new ones. When the PR rewrites a line, every assertion left on that line is *re-asserted by this PR*, not inherited from history. A reviewer's "track in follow-up issue" is workflow deference, not a scope ruling — they often defer because they assume the PR is narrowly typed (e.g., "docs-only deferral note") without realizing the diff already mechanically touches the offending text. Documentation-only PRs are especially prone to this: a one-word string fix is rarely a scope expansion.

**How to apply:** When auditing a deferral, check whether the flagged content sits *on a line that appears in the diff*. If yes, treat the deferral as a punt unless the fix would require new artifacts not in the current diff (e.g., a `_source` block in an authority file that doesn't exist yet — that genuinely belongs in the follow-up). Single-string substitutions and disambiguation tokens within already-edited prose are in-scope. Schema changes, dirname conventions, and ingest pipelines are out-of-scope. The line "we're already here, it's a 5-second fix" from the main agent is itself a tell that the deferral is illegitimate.

Observed: PR #167 (2026-05-01) — egyptologist recommended deferring "Augustus → Caracalla and beyond" → "Augustus → Maximinus Daia" to issue #166, but the PR's diff was rewriting the deferral-note paragraph itself. Promoted to in-scope.
