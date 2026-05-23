---
name: project_chunk46_porter_moss_theban
description: Chunk 46 (TT371–TT380) merge and fix status for porter-moss-theban-necropolis
metadata:
  type: project
---

Chunk 46 (TT371–TT380) merged and fixed; 455 rows total (10 new); 0 tie-breaks; 7 CHUNK46_CORRECTIONS; 0 DERIVER_OVERRIDES; 0 substantive egyptologist flags.

**Why:** Chunk 46 adds 4 Khokha + 5 Dra' Abu el-Naga + 1 Qurnet Muraʿi. 6 anonymous rows, 4 named.

**How to apply:** Landmark for next chunk: expect 465 rows after chunk 47.

## Disagreements resolved (all by majority)

- **TT372 notes_from_pm**: Agent B `Medînet Habu` (circumflex î) vs A+C `Medinet Habu`. Cosmetic OCR artefact; A+C majority correct.
- **TT374 notes_from_pm**: A+B dropped `"For position, see p. 292."` vs C kept it. CHUNK46_CORRECTIONS restored the verbatim cross-reference (PDF p.434 confirmed; TT304/TT365 precedent).
- **TT380 occupant_name**: A `Rʿ` vs B+C `Reʿ`. B+C majority correct (PDF p.435 `R:Ec` = Reʿ). Merge chose correctly.
- **TT380 notes_from_pm (parent)**: B `Ḏhout` (no ḥ-underdot) vs A+C `Ḏḥout`. A+C majority correct. Merge chose correctly.

## CHUNK46_CORRECTIONS (7 entries)

1. TT371 occupant_role: null → "Unknown" (sentinel-null collapse)
2. TT374 notes_from_pm: restored "For position, see p. 292." (agent C had it; A+B dropped)
3. TT375 occupant_role: null → "Unknown"
4. TT376 occupant_role: null → "Unknown"
5. TT377 occupant_role: null → "Unknown"
6. TT378 occupant_role: null → "Unknown"
7. TT379 occupant_role: null → "Unknown"

## Notes

- No tie-break-overrides.json entries needed (no 1/1/1 ties).
- Idempotency confirmed (second fix_rows.py run byte-equal).
- 2146 tests pass.
- TT380 parent `Ḏḥout`: agent C's novel cluster `!)!;lout` → `Ḏḥout` decoding was correct; A also read Ḏḥout; B read Ḏhout (dropped underdot). Majority A+C wins.
- TT374 occupant_name `Amenemopet`: all 3 agents correctly stripped macron-Ō from PM's `AMENEMŌPET` per matchable-name policy. No correction needed.
