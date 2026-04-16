# Human sign-off — Dodson-Hilton "The Power and the Glory" Brief Lives chunk

Per ADR-017 step 6 ("Human review — required, not yet performed"), a
human reviewer walked a sample of rows against the source PDF on
**2026-04-15** and an automated extraction-vs-transcription diff was
run over the full chunk.

This is the second human sign-off on a Dodson-Hilton chunk (the Amarna
Interlude was signed off earlier the same day in
`human-review-2026-04-15.md`). This review fully validates the 59
reconciled Power rows for Phase A authority-curation purposes, modulo
the caveats below; the earlier Amarna sign-off accepted only its
sampled rows, and the remaining 34 Amarna rows remain provisional.

## Methodology — four-layer validation

The 59 Power rows were validated by four complementary passes. No
single pass is sufficient; together they give stronger coverage on
`roles`/`notes` than the Amarna-chunk protocol (character-diff of all
59 rows) and comparable-but-more-targeted coverage on relationship
fields (17 rows human-sampled + algorithmic audit of the 12 Unplaced
rows).

### Layer 1 — automated extraction-vs-transcription diff (all 59 rows)

The committed script `diff_power.py` (in this directory) parses the
transcribed source chunk (`raw/chunk-p126-p130.md`) and compares each
reconciled row's `roles` and `notes` fields character-for-character
against the corresponding transcription entry. Run it with
`python3 diff_power.py` from this directory.

Result: **58 of 59 rows match exactly**; 1 row (`Tiaa A`) differs in
one short phrase where the reconciled value matches the printed PDF
and the transcription contains a short OCR typo
(`"including: number"` in transcription vs `"including a number"` in
both the reconciled row and the printed scan). The 3 extraction agents
silently corrected the transcription error during extraction.
**Reconciled is authoritative; transcription has the typo.**

This proves row-level extraction fidelity across all 59 rows for the
auto-diffable fields (`roles`, `notes`).

### Layer 2a — human spot-check against printed scan (8 rows, diversified sample)

The reviewer walked 8 rows against the printed PDF (printed pp.
137–141 of the Thames & Hudson 2004 hardback; PDF-viewer pp. 126–130
per the convention documented in `README.md`) selected to diversify
on fame (Ahmes B, Tiaa A, Neferure A vs
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

### Layer 2b — targeted hedge-risk spot-check (9 rows)

After the initial egyptologist-reviewer pass on PR #40 flagged that
relationship-field verification on Layer 2a's 8 rows was too narrow,
the reviewer identified ~12 hedge-sensitive rows where the
highest-risk extraction failures would be expected (hedge promotion,
Syrian-extraction trio cross-refs, lacuna-token normalization,
Unplaced-section parentage fabrication).

9 of those flagged rows were surfaced to the human reviewer for a
focused second-layer check: `Mutneferet A`, `Hatshepsut D`, `Sitiah`,
`Iset A`, `Menhet`, `Menwi`, `Merti`, `Akheper[ka?]re`,
`[...]pentepkau`. The remaining flagged rows in the Unplaced section
were handled by Layer 2c (below).

Result: **all 9 rows verified clean.** Per-row verdicts:

| R# | Row | D&H hedge | Reconciled capture | Verdict |
|---|---|---|---|---|
| R1 | `Mutneferet A` | "probable daughter of Ahmose I" | `father_name: "Ahmose I (probable)"` | ✅ Hedge preserved in value |
| R2 | `Hatshepsut D` | "and later king" | Preserved in `notes`; role tuple includes `UWC` as printed | ✅ Reign acknowledged |
| R3 | `Sitiah` | "perhaps the mother of Amenemhat B" | `children_names: ["Amenemhat B (perhaps)"]`; `mother_name: "Ipu B"` | ✅ Hedge preserved |
| R4 | `Iset A` | no parents stated in entry | `father_name: null`, `mother_name: null`, `children_names: ["Thutmose III"]` | ✅ Faithful silence |
| R5 | `Menhet` | "probably of Syrian extraction" | Origin hedge lives in `notes`, not promoted to a structured origin field | ✅ |
| R6 | `Menwi` | ditto | ditto | ✅ |
| R7 | `Merti` | ditto | ditto | ✅ |
| R8 | `Akheper[ka?]re` | lacuna bracket `[ka?]` in name | Preserved verbatim in `dh_id` and `name` | ✅ Lacuna survives |
| R9 | `[...]pentepkau` | leading lacuna ellipsis | Preserved verbatim in `dh_id` and `name` | ✅ Lacuna survives |

### Layer 2c — algorithmic audit of the Unplaced section (12 rows)

All 12 rows in the Power chunk's "Unplaced" subsection were scanned
for any non-null relationship field (`father_name`, `mother_name`,
`spouse_names`, `children_names`). 8 rows had all-null relationship
fields as expected. 4 rows carry a D&H-native placeholder phrase in
the relevant field (`Henut Q` / `Nebetnehat A`:
`spouse_names: ["a king of the mid-18th Dynasty"]`; `Ti`:
`father_name: "a king of the mid-18th Dynasty"`; `Merybennu`:
`father_name: "Thutmose III or Amenhotep II (probable)"`).

Result: **zero fabricated parentage across 12 Unplaced rows.** The 4
placeholder-phrase captures are faithful reproductions of D&H's own
wording, not extractor inventions. Whether a placeholder phrase like
`"a king of the mid-18th Dynasty"` should surface in a structured
relationship field at all is a design question for Phase A authority
curation, not an extraction-correctness issue.

## Verdict per Layer 2a sampled row

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

## Consequence — sign-off split by field type

The sign-off claim is deliberately split by field type to reflect
what each validation layer actually proves:

- **`roles` and `notes` on all 59 rows — sign-off accepted.** Layer 1
  character-diffs every row's `roles` and `notes` against the
  transcription; 58/59 match exactly and the 59th is a
  transcription-layer correction in reconciled's favor.
- **Relationship fields (`father_name`, `mother_name`,
  `spouse_names`, `children_names`) on 17 rows (Layer 2a's 8-row
  diversified sample ∪ Layer 2b's 9-row hedge-risk sample) — sign-off
  accepted.** Includes all rows the egyptologist-reviewer flagged as
  hedge-sensitive, plus the original diversified spot-check.
- **Relationship fields on the 12 Unplaced rows — algorithmically
  audited.** Zero fabrications found; 4 placeholder-phrase captures
  are D&H-native wording, not invented parentage. Sign-off accepted.
- **Relationship fields on the remaining 42 rows — accepted with
  medium confidence, not rigorously validated.** These 42 rows were
  not hedge-flagged by the egyptologist-reviewer and are not in the
  Layer 2a/2b human samples. No fabricated parentage was found in the
  29 human-sampled + algorithmically-audited rows (17 + 12), which is
  strong circumstantial evidence the extractor's hedge-preservation
  behaviour is consistent, but the 42 are not individually
  human-verified. **De-provisionalise for Phase A, but flag for
  revisit if any cross-source reconciliation during authority
  curation surfaces an unexpected parent/spouse claim.**

The 1 Layer 1 auto-diff residue (`Tiaa A` `"including: number"` →
`"including a number"`) is a transcription-layer correction, not a
row error — it improves fidelity relative to `chunk-p126-p130.md`.

## Deferred items — none row-level

No row was deferred at this review. The source-wide
`children_names` architectural question (Q5 in the Amarna log) still
stands as a Phase A decision, not a Power-chunk concern.

## Metadata note — `source_citation.pdf_pages` convention (retracted earlier finding)

An earlier draft of this log flagged
`source_citation.pdf_pages: "126-130"` as a bug on the theory that
printed pages should be cited. That was wrong: `README.md` in this
directory documents `pdf_pages` as the **PDF-viewer page range** of
the OCR chunk (counting from the first rendered PDF page, before
frontmatter offset). By that convention, `"126-130"` for Power and
`"142-145"` for Amarna are both correct; the printed page numbers
(137–141 and 154–157 respectively) are cross-referenced through the
OCR markdown. No metadata fix is needed.

As part of addressing this review round, the README's wording was
tightened from "physical-page range" (imprecise — a PDF page is not
physical) to "PDF-viewer page range" so the convention is harder to
misread in future.

## Pointers

- Amarna sign-off log: `human-review-2026-04-15.md` (same directory)
- Reconciled data: `reconciled.jsonl` (100 rows total, 59 Power +
  41 Amarna)
- Raw transcription used for Layer 1: `raw/chunk-p126-p130.md`
- Raw PDF used for Layer 2: `raw/source-p126-p130.pdf`
  (PDF-viewer pp. 126–130 = printed pp. 137–141; see README for the
  `pdf_pages` convention)
- Diff script: `diff_power.py` (in this directory)
