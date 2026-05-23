---
name: project_chunk48_porter_moss_theban
description: Chunk 48 (TT391–TT400) merged and fixed; 475 rows; 1 tie-break; 9 CHUNK48_CORRECTIONS; 5 DERIVER_OVERRIDES; 0 substantive flags.
metadata:
  type: project
---

Chunk 48 (TT391–TT400) reconciled 2026-05-22.

**Why:** Standard Phase-0 reconciliation run; 10 rows (7 anonymous + 3 named).

**How to apply:** All rows clean; ready for reviewer passes.

## Stats
- Total reconciled rows after chunk 48: 475 (465 + 10)
- Tie-breaks added: 1 (`TT398|notes_from_pm`)
- CHUNK48_CORRECTIONS: 9 (7 sentinel-null role restorations + 2 cosmetic macron/space fixes)
- DERIVER_OVERRIDES: 5 (TT391/TT397/TT398 attribution_certainty=attested; TT394/TT400 is_uninscribed=True)

## Tie-break
- `TT398|notes_from_pm`: 1/1/1 split on (1) called-name caps (A=NENTOWAREF, B=Nentowaref, C=NENTOWAREF) and (2) `(from cones)` placement (A+B after `nursery` = correct; C reordered = wrong). Pinned agent A's form per PDF p.443.

## CHUNK48_CORRECTIONS
- TT392–TT396, TT399, TT400: `occupant_role="Unknown"` restored (sentinel-null collapse)
- TT391 `notes_from_pm`: macron-ē on `Khonsemwēset` + macron-ō on `Neferḥōtep` restored (PDF p.441)
- TT397 `notes_from_pm`: space in `Dyn. XVIII (?)` restored (PDF p.443; B+C 2/1 dropped space)

## DERIVER_OVERRIDES
- TT391 `attribution_certainty=attested`: `Probably Dyn. XXV` is regnal-date hedge (TT2/TT12 precedent)
- TT397 `attribution_certainty=attested`: `Dyn. XVIII(?)` is regnal-date hedge (same precedent)
- TT398 `attribution_certainty=attested`: `Probably Dyn. XVIII` is regnal-date hedge (same precedent)
- TT394 `is_uninscribed=True`: `No texts. Ramesside.` per TT115 chunk-20 + TT388 chunk-47 precedent
- TT400 `is_uninscribed=True`: `No texts.` same class

## Sub-site distribution
- Sh. ʿAbd el-Qurna: TT391, TT397, TT398, TT399, TT400 (5)
- Khokha: TT392 (1)
- Dra' Abu el-Naga: TT393, TT394, TT395, TT396 (4)

## Disagreement profile
- TT391: cosmetic (macron-ē on Khonsemwēset; 2/1 majority dropped it → CHUNK48_CORRECTIONS)
- TT397: cosmetic (space before `(?)` in `Dyn. XVIII (?)`; 2/1 dropped → CHUNK48_CORRECTIONS)
- TT398: 1/1/1 tie on caps + sentence structure → tie-break override
- All other chunk-48 rows: unanimous
