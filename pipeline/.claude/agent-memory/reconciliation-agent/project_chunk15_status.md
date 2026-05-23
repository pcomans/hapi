---
name: project_chunk15_status
description: Porter-Moss chunk 15 (TT61–TT70) merge pipeline status as of 2026-05-10
type: project
---

Chunk 15 (TT61–TT70, Sh. ʿAbd el-Qurna) merged and fixed on 2026-05-10.

**Final reconciled.jsonl:** 145 rows (135 pre-existing + 10 new).

**Tie-break overrides added:**
- `TT65|notes_from_pm`: 1/1/1 on citation position + `Mutemmeres` vs `Mut-emmeres` + `accounts(?)` spacing. Pinned agent A (mid-sentence citation per chunk-12 precedent). CHUNK15_CORRECTIONS layers `accounts (?)` spacing fix post-merge.
- `TT68|notes_from_pm`: 1/1/1 on ayin position in `wʿab-priest`. A=`wʿab-priest`, B=`wab-priest`, C=`waʿb-priest`. Pinned agent A per TT14 (p.26) precedent.

**DERIVER_OVERRIDES added for chunk-15:** TT62, TT65, TT69 — all `(?)` qualify regnal-date, not primary occupant identification. Same TT2-precedent chain.

**TT70 `attribution_certainty`:** Deriver fires `uncertain` from `sandal-makers (?)` in usurper clause. Left as `uncertain` (original occupant is genuinely anonymous — no name, no attribution). Flagged for egyptologist review.

**Canonical test pinned:** `test_182_uncertain_attribution_canonical_set` now includes TT70.

**Substantive disagreements for egyptologist:**
- TT64 `occupant_name`: A=C=`Heḳerneheh` (2/1 majority chosen), B=`Heṭerneheh`. The `~` OCR glyph is ambiguous (underdot-Ḳ vs underdot-Ṭ). Needs PDF check at PM I.1 p.128.
- TT65 `occupant_name`: A=C=`Nebamun` (majority), B=`Nebamūn` (pre-derived macron — prompt-rule violation). Egyptologist likely to flip to `Nebamūn` per TT17 precedent if PDF confirms capital macron.
- TT65 `tomb_aliases`: C extracted `["Alchesi"]` (from PM's `'Alchesi' of Prisse` in notes); A and B have `[]`. Majority chose `[]`. Egyptologist should decide if `Alchesi` belongs in `tomb_aliases`.

**Off-by-one page citation:** TT62 — agent C cited p.124, A and B cited p.125 (2/1 resolved correctly). Agent C is systematically off-by-one.

**Why:** Standard Phase-0 reconciliation PR for PM I.1 chunk-15 block.
**How to apply:** Chunk 16 will be TT71–TT80. Follow same pattern.
