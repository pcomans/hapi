---
name: Baud 1999 Phase-0 extraction
description: Context for the chunk-by-chunk Baud 1999 BdE 126 Corpus extraction project
type: project
---

Phase-0 authority source onboarding of Baud 1999 *Famille royale et pouvoir sous l'Ancien Empire égyptien* (BdE 126, IFAO 1999), vol. 2 *Corpus*, entries [1]–[282] across ~7 PRs, ~40 entries per chunk.

**Why:** D&H's OK coverage is weak; Baud is the standard OK prosopography and the natural OK analogue. Needed for Phase-A ruler/royal-family reconciliation across museum data.

**How to apply:** When reviewing a new chunk, prioritize the Baud-specific risks: dropped hedges, scholarly-judgment promotion (per-Baud vs attested), `service_personnel` asterisk fidelity, tomb designation format (G/LG/D/Mastaba N), cross-reference stubs, French ordinal → dynasty mapping, and `baud_refs` completeness under rubric (e). Pool reviewer's corrections are applied under "LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED" per ADR-017 step 6; a human Egyptologist sign-off is a separate layer.

**Schema features unique to Baud source:** `service_personnel: true` flags asterisk-suffixed headwords (attached personnel, not family); `roles` vocabulary is seeded from chunk 1 and grows; `name_egyptian` preserves Baud's French-school transliteration verbatim (dots for suffix, `j` for iod); `father_name`/`mother_name` carry hedges inline as `"X (probable)"`, `"[X]"`, or `"X (per Baud)"`.
