---
name: project_chunk43_porter_moss_theban
description: Chunk 43 (TT341–TT350) merge and fix_rows status, tie-breaks, deriver override, pending egyptologist flags
metadata:
  type: project
---

Chunk 43 (TT341–TT350) merged and fixed. 425 rows total (415 prior + 10 new). 3 tie-breaks resolved. 1 DERIVER_OVERRIDE. CHUNK43_CORRECTIONS=[] (empty, but registered). All tests pass (2109).

**Why:** Chunk-43 had three 1/1/1 ties (all in notes_from_pm), all requiring constructed values from PDF verification. No single agent was fully correct on any of the three.

**How to apply:** Status is complete except for egyptologist review items below.

## Tie-breaks (all in notes_from_pm)

- `TT343|notes_from_pm`: Agent B pinned (has `called Paḥeḳmen,` prefix + clean `.) Parents,`). PDF p.428 confirmed. C dropped prefix; A had spurious double-period.
- `TT345|notes_from_pm`: Constructed: wʿb-priest (ayin from B) + `Senidhout` (from A, PDF p.431 plain `d`) + clean punctuation from B/C. Three-way split on ayin, parent name, punctuation.
- `TT346|notes_from_pm`: Constructed: `Tentōpet` (macron-ō from A, PDF p.432 confirmed) + `Penrēʿ` (title-case + macron-ē from PDF p.432 small-caps). No agent captured both macrons correctly.

## DERIVER_OVERRIDE

- `TT346 attribution_certainty=attested`: `Probably` in `Probably usurped from Penrēʿ` qualifies who the prior owner was (usurpation-source uncertainty), NOT primary Amenhotp identity. Same structural class as TT340 (chunk-42). is_usurped=True is CORRECT.

## Pending for egyptologist review (DEFERRED)

1. **TT345 `Senidhout` vs `Seniḥout`** — PDF p.431 OCR shows plain `d` but printed hieroglyph may have underdot-ḥ. Egyptologist should confirm from printed page before any correction.
2. **TT342 wife name `Tepihu` vs `Tepiḥu`** — agent A has ḥ-underdot, agents B+C do not. PDF p.409 / physical p.427 not conclusive from OCR alone. Egyptologist should confirm.

## Files modified

- `tie-break-overrides.json`: 3 new entries (TT343, TT345, TT346 notes_from_pm)
- `fix_rows.py`: CHUNK43_CORRECTIONS=[], CHUNK43_RENAMES={}, registered in ALL_CORRECTIONS/ALL_RENAMES; TT346 DERIVER_OVERRIDE appended to chunk-43 block
- `tests/test_porter_moss_merge_tie_break.py`: 3 pins (TT343, TT345, TT346 notes_from_pm); test_chunk43_row_count (425)
- `tests/test_sources_porter_moss_theban_necropolis.py`: CHUNK43_TOMB_IDS, EXPECTED_TOMB_IDS extended; is_usurped set extended (TT346, TT348); uncertain set extended (TT348); 7 chunk-43 per-row tests added
