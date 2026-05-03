---
name: "Subsumed by accepting X" can hide a partial punt
description: When a main agent marks a finding as subsumed by another acceptance, verify the second finding is fully covered — not just partially overlapping
type: feedback
---

When a main agent says "Item B is subsumed by accepting Item A" — verify that A's fix actually covers B's complaint in full. Often A covers the majority case but B was specifically about a minority/edge case A doesn't touch.

**Example (PR #139):** Main agent claimed code-reviewer P2-3 (Greek-alias rationale wording) was "subsumed" by accepting egyptologist-P1 (split all 17 unsplit rows). But P2-3's actual gripe was about the *keep-case* override entries (03.06, 15.04) where the heuristic is "keep parens because the parenthetical is a compound titulary, not a single alias." Splitting 17 more rows doesn't tighten the keep-case rationale — those entries still need their wording updated to spell out the strip-vs-keep heuristic.

**Why:** "Subsumed" is a tidy-sounding way to drop one of two findings. If the second finding addresses a class of cases the first doesn't touch, the subsumption is false and the second finding is being silently punted.

**How to apply:** For every "subsumed by" claim, name the specific cases each finding covers and check the intersection. If finding B has cases A doesn't touch, it isn't subsumed.
