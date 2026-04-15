# Human sign-off — Dodson-Hilton "The Power and the Glory" Brief Lives chunk

Per ADR-017 step 6 ("Human review — required, not yet performed"), a
human reviewer walked a sample of rows against the source PDF on
**2026-04-15** and an automated extraction-vs-transcription diff was
run over the full chunk.

This is the second human sign-off on a Dodson-Hilton chunk (the Amarna
Interlude was signed off earlier the same day in
`human-review-2026-04-15.md`). With both chunks signed off, all 100
reconciled rows across PRs #37 and #38 are validated for Phase A
authority-curation purposes, modulo the caveats below.

## Methodology — two-layer validation

The 59 Power rows were validated by two complementary passes. Neither
pass alone is sufficient; together they cover all the risks the
earlier single-sample Amarna methodology missed.

### Layer 1 — automated extraction-vs-transcription diff (all 59 rows)

A script (`/tmp/claude/diff_power.py` at the time of review) parsed
the transcribed source chunk (`raw/chunk-p126-p130.md`) and compared
each reconciled row's `roles` and `notes` fields character-for-
character against the corresponding transcription entry.

Result: **58 of 59 rows match exactly**; 1 row (`Tiaa A`) differs by
a single character where the reconciled value matches the printed PDF
and the transcription contains a 1-character OCR typo
(`"including:"` in transcription vs `"including a"` in both the
reconciled row and the printed scan). The 3 extraction agents silently
corrected the transcription error during extraction. **Reconciled is
authoritative; transcription has the typo.**

This proves row-level extraction fidelity across all 59 rows for the
auto-diffable fields (`roles`, `notes`).

### Layer 2 — human spot-check against printed scan (8 rows)

The reviewer walked 8 rows against the printed PDF (physical pages
137–141 of the Thames & Hudson 2004 hardback; see metadata caveat
below) selected to diversify on fame (Ahmes B, Tiaa A, Neferure A vs
obscure Pyihia, Webensenu), role-tuple complexity (single-role
Menkheperre A vs four-role Mutneferet A territory), and name-form
quirks (parenthetical Meryetre(-Hatshepsut), bracketed
Akheper[ka?]re).

Rows sampled: `Ahmes B`, `Iaret`, `Neferure A`, `Tiaa A`,
`Menkheperre A`, `Webensenu`, `Meryetre(-Hatshepsut)`, `Pyihia`.

Scope of each spot-check: roles attested; derived relationship
fields (`father_name`, `mother_name`, `spouse_names`,
`children_names`) grounded in the entry text and not fabricated;
notes content reproduced faithfully including hedges like "simple
cobra" transcription-uncertainty wording.

Result: **all 8 rows verified clean.** No corrections, no deferrals.

## Verdict per sampled row

| # | Row | D&H p. (printed) | Verdict | Notes |
|---|---|---|---|---|
| Q1 | `Ahmes B` | 137 | ✅ | Roles `KM; KGW; KSis` all attested; no father/mother listed in entry |
| Q2 | `Iaret` | 138 | ✅ | Roles `KGW; KD; KSis` all attested; "simple cobra" transcription-uncertainty note present |
| Q3 | `Neferure A` | 140 | ✅ | `KGW` is explicitly listed in the source role-tuple `(KD; GW; KGW)` despite the "possibly wife of Thutmose III" hedge in notes — extraction correct |
| Q4 | `Tiaa A` | 140 | ✅ | `GW` distinct from `KGW` confirmed in source; KV32/KV47/Siptah mix-up all present in notes |
| Q5 | `Menkheperre A` | 138 | ✅ | Both parents explicitly named in entry (Thutmose III and Meryetre-Hatshepsut); no additional titles missed |
| Q6 | `Webensenu` | 141 | ✅ | Mother genuinely unnamed in source — `mother_name: null` is correct, not an extraction gap |
| Q7 | `Meryetre(-Hatshepsut)` | 139 | ✅ | D&H prints the headword with parentheses exactly as extracted; no father listed in source |
| Q8 | `Pyihia` | 140 | ✅ | Name spelling `Pyihia` confirmed against the printed headword; role `KD` only — no additional titles |

## Consequence

All 59 reconciled Power rows are sign-off accepted for Phase A
authority-curation purposes. Combining Layer 1 (full-chunk automated
fidelity proof on `roles` and `notes`) and Layer 2 (8-row human
spot-check on derived relationship fields and narrative accuracy
against the printed scan) gives coverage materially stronger than the
Amarna-chunk sample-only protocol. **All 59 rows should no longer be
marked provisional.**

The 1 auto-diff residue (`Tiaa A` `"including: number"` →
`"including a number"`) is a transcription-layer correction, not a
row error — it improves fidelity relative to `chunk-p126-p130.md`.

## Deferred items — none row-level

No row was deferred at this review. The source-wide
`children_names` architectural question (Q5 in the Amarna log) still
stands as a Phase A decision, not a Power-chunk concern.

## Metadata finding — `source_citation.pdf_pages` is wrong

Every Power row in `reconciled.jsonl` carries
`source_citation.pdf_pages: "126-130"`, which is a printed-page-
vs-PDF-viewer-page confusion. The printed page numbers in the
Dodson-Hilton book for this chunk are **137–141**, not 126–130.
The raw file `raw/source-p126-p130.pdf` is similarly misnamed.
Offset is ~11 pages of frontmatter.

Scope of the error:
- All 59 Power rows need `pdf_pages` corrected to `"137-141"`.
- The Amarna chunk likely has the same offset bug
  (`raw/source-p142-p145.pdf` likely corresponds to printed pp.
  ~153–156, not 142–145); check and correct all 41 Amarna rows.
- The transcription filenames (`chunk-p126-p130.md`,
  `chunk-p142-p145.md`) and raw-PDF filenames are consistent with
  each other but inconsistent with the printed book. Decision: rename
  or leave with a CONVENTIONS note. Prefer renaming for future
  chunks (Ramesside and beyond) so the filename reflects the
  printed page numbers that citations will use downstream.

This is a metadata cleanup, **not** a correctness issue for the
extracted row content — rows were extracted from the right pages,
the citation field just labels them with the wrong page numbers.
Low-risk hygiene fix; suitable as a standalone PR.

## Pointers

- Amarna sign-off log: `human-review-2026-04-15.md` (same directory)
- Reconciled data: `reconciled.jsonl` (100 rows total, 59 Power +
  41 Amarna)
- Raw transcription used for Layer 1: `raw/chunk-p126-p130.md`
- Raw PDF used for Layer 2: `raw/source-p126-p130.pdf`
  (printed pp. 137–141; see metadata finding above)
