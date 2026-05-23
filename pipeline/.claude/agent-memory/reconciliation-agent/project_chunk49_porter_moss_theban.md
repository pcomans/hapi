---
name: project_chunk49_porter_moss_theban
description: Chunk 49 (TT401–TT409) merge + fix status — final § I chunk for PM I.1 TT-numbering
metadata:
  type: project
---

Chunk 49 (TT401–TT409) merged and fixed; 484 rows total (475+9); 0 tie-breaks; 5 CHUNK49_CORRECTIONS; 3 DERIVER_OVERRIDES; 0 substantive flags.

**Why:** This is the FINAL numbered TT chunk in PM I.1 § I. TT-numbering ends at TT409.

**How to apply:** No further TT chunks from PM I.1 § I. Future work covers § II (Tombs Without Official Numbers) if those are to be extracted.

## Disagreements resolved

- **TT401 occupant_name**: A+C=`Nebseny`, B=`Nebsenyʿ` (ayin) → 2/1 majority chose `Nebseny`. PDF p.444/physical p.462 confirmed: PM headword is plain `NEBSENY` with no trailing ayin. No tie-break needed.
- **TT405 shared_with_tombs**: A=["TT186"], B+C=[] → 2/1 majority chose []. Correct: `Father (probably), Iḥy (tomb 186)` is filiation, not co-ownership. Per chunk-45 TT361 precedent.
- **TT406 is_unfinished**: A+B=false, C=true → 2/1 chose false. Correct: `(Unfinished)` appears on `Hall.` body sub-header line (out of headword block). Strict rule: only headword-block `(Unfinished)` triggers is_unfinished=true.
- **TT408 is_unfinished**: A+B+C unanimous true. `(Unfinished.)` is in the headword block (before sub-site line).
- **TT403 notes_from_pm**: A+B=`Dyn. XVIII(?)` (no space), C=`Dyn. XVIII (?)` → 2/1 no-space. CHUNK49_CORRECTIONS restores space (PDF p.445 confirms space before parenthetical, same as TT397 chunk-48).

## Cosmetic / OCR disagreements

All notes_from_pm disagreements (Amūn macron drops on TT401/TT404, macron-ū on TT408 was unanimous) were cosmetic OCR-noise. Agent C preserved macrons correctly; A+B dropped them. Majority chose no-macron → CHUNK49_CORRECTIONS restores macrons.

## CHUNK49_CORRECTIONS (5 entries)

1. TT402 occupant_role → "Unknown" (sentinel-null restore)
2. TT409 occupant_role → "Unknown" (sentinel-null restore)
3. TT401 notes_from_pm → restore macron-ū in `Amūn` (PDF p.444)
4. TT403 notes_from_pm → restore space in `Dyn. XVIII (?)` (PDF p.445)
5. TT404 notes_from_pm → restore macron-ū in `Amūn` (PDF p.445)

## DERIVER_OVERRIDES (3 entries, added to chunk-49 section)

1. TT401 attribution_certainty → attested (`Temp. ... (?)` = regnal-date hedge)
2. TT403 attribution_certainty → attested (`Dyn. XVIII(?)` = regnal-date hedge)
3. TT405 attribution_certainty → attested (`Father (probably), Iḥy` = filiation hedge, not occupant identity)

## Special cases

- TT409: stub entry, theban_area=null (only TT281 + TT409 allowed null theban_area per test update)
- No tie-break-overrides.json entries needed (all disagreements resolved by majority or were cosmetic)

## Tests updated

- `test_porter_moss_merge_tie_break.py`: row count updated 475→484; 9 new per-row pin tests added (TT401–TT409)
- `test_sources_porter_moss_theban_necropolis.py`: CHUNK49_TOMB_IDS added; null-theban_area allowlist updated to include TT409
