---
name: Preserve Baud's hedges aggressively
description: Hedges on filiation fields are load-bearing in Baud; flag any stripped hedge as a correction
type: feedback
---

Baud's filiation attributions are often scholarly inferences, not inscribed attestations. The README schema rule is explicit: `"X (probable)"` for parenthesised-probable, `"[X]"` for bracketed-reconstructed, `"X (per Baud)"` when a row would otherwise promote an interpretive claim to a hard one.

**Why:** OK prosopography is sparsely attested; Baud is unusually hedge-heavy because he's careful about distinguishing inscribed facts from titular-synchronism guesses. The whole point of Phase-0 extraction is to land the hedge so Phase-A can decide how aggressively to trust it.

**How to apply:** When reviewing a chunk, for every `father_name`/`mother_name`/`spouse_names`/`children_names` that has NO hedge, cross-check the PARENTÉ prose. If Baud writes "Kanawati a supposé...", "Schmitz estime...", "filiation possible", "serait donc...", "peut-être fils de...", "hypothétique" — the extract should carry `(probable)`, `(per Baud)`, or an explanatory `notes_from_baud` fragment. Flag absent hedges even when majority vote stripped them.
