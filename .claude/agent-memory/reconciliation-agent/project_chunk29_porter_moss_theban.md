---
name: project_chunk29_porter_moss_theban
description: Chunk-29 outcome for porter-moss-theban-necropolis: 10 rows TT201-TT210 (Khôkha ×8, ʿAsâsîf ×1, Deir el-Medina ×1). 4 tie-break overrides, 7 CHUNK29_CORRECTIONS, 3 DERIVER_OVERRIDES.
metadata:
  type: project
---

Chunk-29 PM I.1 § I TT201-TT210 completed. Merged 285 rows (275 → 285).

**Why:** Chunk-29 added 8 Khôkha tombs (TT201-208), 1 ʿAsâsîf (TT209), 1 Deir el-Medina (TT210 — Deir el-Medina already existed in reconciled.jsonl from chunk-9; not truly "new".)

**Tie-break overrides (4, all notes_from_pm):**
- `TT202|notes_from_pm`: Ptaḥ underdot + no spurious comma after Ptaḥ; pinned agent C
- `TT207|notes_from_pm`: Ḥemawen underdot (PM `~emawen`); pinned agent C
- `TT209|notes_from_pm`: `(?)` uncertainty marker + `(formerly read Ḥatashemro)` parenthetical; composite
- `TT210|notes_from_pm`: L.D. cite mid-sentence + Piay comma + Nefertkhaʿ ayin; pinned agent C

**CHUNK29_CORRECTIONS (7):**
- TT201 `occupant_name`: `Re` → `Reʿ` (2/1 majority had no-ayin; PM `RE<`)
- TT202 `occupant_role`: `High Priest` → `Official` (2/1 majority wrong; `Prophet of Ptaḥ` is not First Prophet rank)
- TT202 `notes_from_pm`: `Amun` → `Amūn` macron
- TT204 `occupant_name`: `Nebanensu` → `Nebʿanensu` (2/1; PM `NEB<ANENSU`)
- TT207 `notes_from_pm`: `Amun` → `Amūn` macron
- TT208 `notes_from_pm`: `Amen-Re` → `Amen-reʿ` (2/1 majority wrong; PM `Amen-rec`)
- TT210 `occupant_name`: `Raweben` → `Raʿweben` (2/1; PM `RA<WEBEN`)

**DERIVER_OVERRIDES (3):**
- TT202: `attribution_certainty="attested"` — `Dyn. XIX(?)` is dynastic-date hedge
- TT205: `attribution_certainty="attested"` — `Tuthmosis III(?) to Amenophis II(?)` are regnal-date hedges
- TT210: `attribution_certainty="attested"` — `Parents(?)` qualifies parentage, not occupant identity

**TT209 deriver: NO override** — `(?)` in `(?) Hereditary prince...` IS a genuine name-reading uncertainty (PM applies it to the hieroglyphic name transcription itself). `attribution_certainty="uncertain"` is correct. Added to `test_182_uncertain_attribution_canonical_set`.

**Egyptologist flags:**
- TT202 `occupant_role`: `Official` assigned for `Prophet of Ptaḥ` — confirm not High Priest rank
- TT209: Confirm whether PM's `(?)` on the name transcription warrants `uncertain` vs `attested` in this schema context

**Row count verified:** 285 (= 275 + 10) ✓
**Idempotency:** reconciled.jsonl byte-identical on second fix_rows.py run ✓
**Tests:** 1891 passed ✓

**How to apply:** Reference for TT201-TT210 ayin-preserve corrections (3 rows in one chunk), the `Prophet of X` → `Official` role convention, and the distinction between name-reading `(?)` (TT209, uncertain) vs regnal/parentage `(?)` (TT202/TT205/TT210, attested).
