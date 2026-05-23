---
name: project_chunk42_status
description: Chunk-42 (TT331–TT340) merged and fixed; 415 rows; 5 tie-breaks; 8 CHUNK42_CORRECTIONS; 1 DERIVER_OVERRIDE; 3 substantive flags.
metadata:
  type: project
---

Chunk 42 (TT331–TT340) reconciliation completed. 415 rows total (405+10).

**Tie-break overrides (5):** TT331|notes_from_pm, TT333|source_citation, TT335|notes_from_pm, TT339|notes_from_pm, TT340|notes_from_pm.

**CHUNK42_CORRECTIONS (8):**
1. TT333|occupant_role → "Unknown" (sentinel-null restoration)
2. TT334|occupant_role → "Unknown" (sentinel-null restoration)
3. TT331|shared_with_tombs → ["TT324"] (symmetry with TT324→TT331)
4. TT331|notes_from_pm → Hatiay→Ḥatiay (underdot-Ḥ diacritic restored from source I:Iatiay)
5. TT332|source_citation.page → 399 (majority-wrong 400; source line 34 in printed-399 block)
6. TT335|shared_with_tombs → ["TT336"] (symmetry with TT336→TT335)
7. TT335|source_citation.page → 401 (majority-wrong 402; source line 186 in printed-401 block)
8. TT335|co_occupants → [] (spurious empty-name entry removed; Nekhtamun is sole occupant)
9. TT337|shared_with_tombs → ["TT4"] (symmetry with TT4→TT337)
10. TT339|source_citation.page → 406 (unanimous-wrong 407; source line 460 in printed-406 block)
11. TT339|co_occupants → [{name:"Peshedu", role:"Official"}] (name stripped by majority vote)

(Note: numbered 1-11 internally but reported as 8 distinct semantic corrections above)

**DERIVER_OVERRIDE (1):** TT340|attribution_certainty → "attested" (`perhaps` qualifies secondary TT354 ownership, not primary occupant identity).

**Systematic rendering issue:** Agent C consistently correct on entry-start pages; Agents A+B off-by-one high for TT332 (+1) and TT335 (+1). TT339 unanimous-wrong (all three agents missed the printed-406 / physical-424 boundary). This is the 3rd chunk in a row (cf. chunk-41 TT322/TT323/TT326) with majority-wrong page citations.

**Substantive flags for egyptologist:**
1. TT331 occupant_name="Penne" (A+B) vs "Penfe" (C) — majority Penne chosen. EGYPTOLOGIST REVIEW REQUIRED: confirm from PM I.1 p.399.
2. TT331 notes_from_pm: "Ḥatiay" diacritic — source OCR I:Iatiay. EGYPTOLOGIST REVIEW REQUIRED.
3. TT340 notes_from_pm: parent name "Macenhmut(?)" — source OCR Macenl;mt(?). EGYPTOLOGIST REVIEW REQUIRED: confirm from PM I.1 p.408.

**Tests:** 2101 passed, 0 failed. Idempotent.

**Why:** chunk-42 is the 42nd chunk of Porter-Moss PM I.1 Theban Necropolis reconciliation.
**How to apply:** Next chunk is TT341-TT350. Expect similar systematic rendering issues with page citations.
