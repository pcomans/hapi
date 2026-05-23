---
name: project_chunk35_status
description: Porter-Moss chunk 35 (TT261–TT270) merge pipeline status as of 2026-05-21
type: project
---

Chunk 35 (TT261–TT270) merged and fixed on 2026-05-21.

**Final reconciled.jsonl:** 345 rows (335 pre-existing + 10 new).

**Tie-break overrides added (4):**
- `TT266|occupant_name`: 1/1/1 on Amennakit/Amennakht/Amenakht. PDF p.364 confirms AMENNAKHT.
- `TT266|notes_from_pm`: 1/1/1 on father Buentiaf/Busentef/Busetef + wife diacritics. PDF confirms `Buḳentef` (underdot-ḳ) + `Ḥenutrayunu`.
- `TT267|notes_from_pm`: 1/1/1 on mother Taarakhkau/Tarékhmani/Tarekhan + wife Henumet/Henutumet/Henutmet. PDF p.365 confirms `Tārekhʿan` (ayin) + `Ḥenutmet`.
- `TT268|notes_from_pm`: 1/1/1 on lead clause + ayin on ʿAuti. PDF p.367 confirms `Family tomb of Nebnakht.` + `ʿAuti`.

**CHUNK35_CORRECTIONS (6):**
- TT261 occupant_name: → `Khaʿemweset` (ayin from PDF p.362 `KHA<EMWĒSET`).
- TT262 occupant_role: null → `Unknown` (null-name rule).
- TT266 source_citation: page 347 → 346 (headword starts on p.346; all agents off-by-one).
- TT266 shared_with_tombs: ["TT219"] → [] (`names in tomb 219` is genealogical name-record ref, not physical sharing; symmetry test rejects asymmetric relation).
- TT269 occupant_role: null → `Unknown` (null-name rule).
- TT270 notes_from_pm: `Ptah-Sokari` → `Ptaḥ-Sokari` (PDF p.368 underdot-ḥ).

**DERIVER_OVERRIDE added (1):**
- TT262 attribution_certainty: `uncertain` → `attested` (`Tuthmosis III (?)` hedges regnal date, not occupant identity; same class as TT253/TT260 chain).

**Substantive flag for egyptologist:**
- TT266 shared_with_tombs: `names in tomb 219` intentionally zeroed out. TT219's occupant is a different Amennakht (son of TT218). The cross-reference is one-way genealogical; not a physical sharing. Egyptologist should confirm this interpretation.

**Why:** Standard Phase-0 reconciliation PR for PM I.1 chunk-35 block.
**How to apply:** Chunk 36 will be TT271–TT280.
