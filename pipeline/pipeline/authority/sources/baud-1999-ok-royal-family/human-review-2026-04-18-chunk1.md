# Human review — Baud 1999 Corpus chunk 1 ([1]–[40])

**Date:** 2026-04-18
**Authoriser:** Philipp Comans (project owner)
**Verifier:** Claude Opus 4.7 working under authoriser's direction — visual PDF page rendering + field-by-field comparison against `reconciled.jsonl`. The LLM-assisted verification is explicitly labelled below (not claimed as independent human validation).

## Rows sampled (3 of 40)

- **`baud-3`** Jḥtj-ḥtp (chunk-1 flagship / schema exemplar): physical p. 17.
- **`baud-9`** Jj-[ḥr ?]-nfr (random drift sample, seed=42): physical p. 22.
- **`baud-37`** ꜥnḫ.s-n-Mrjj-Rꜥ Iʳᵉ (additional high-interest row; Ankhesenmeryre I, Pépi Iᵉʳ's wife and Merenrê's mother): physical p. 43.

## Methodology

Each sampled row was checked by the LLM verifier against a direct visual rendering of the cited PDF page. Fields compared: `name_egyptian`, `monument`, `localisation`, `pm_ref`, `date_attested`, `baud_refs`, `titles_from_baud`, kinship fields. Transliteration glyphs (ꜥ/ꜣ/ḥ/ḫ/ẖ/š/ṯ/ḏ) and Baud's original hedges (`[X]`, `(?)`, `(probable)`) compared against the printed page.

## Verdict per row

| baud_id | verdict | notes |
|---|---|---|
| baud-3 | ✅ all fields match PDF p.17 | 7 titles, French spouse name, Mastaba G 7650, PM 200-201, date "Rêkhaef au plus tard", and the notes_from_baud PARENTÉ line all verbatim. User-flagged dot-under on `ꜥḏ-mr` (was drifting to `ꜥd-mr` in extraction) — fixed source-wide via `_WORD_LEVEL_FIXES` in `fix_rows.py`, affecting 18 instances across the corpus. |
| baud-9 | ✅ cross-ref stub matches | `Jj-[ḥr ?]-nfr. Voir à Nfrt-kꜣw II [132].` verbatim on PDF p.22; all structured fields null as expected for a cross-reference. |
| baud-37 | ✅ all fields match PDF p.43 | 9 titles (incl. complex mother/wife-of-pyramid titles), Stèle du vizir Ḏꜥw at Abydos, PM V p.95, date Pépi Iᵉʳ-Merenrê, spouse Pépi Iᵉʳ, child Merenrê. |

## Consequence statement

The 3 reviewed rows are **no longer provisional for the citation-fidelity / transcription layer**. The remaining 37 un-sampled rows in chunk 1 **remain provisional at the chunk level** per ADR-017 step 6. Scholarly judgment fields (role vocab semantics, kinship inference, hedge calibration) across all chunk-1 rows **remain provisional** pending a future Egyptological pass.
