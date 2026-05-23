---
name: project_chunk44_porter_moss_theban
description: Chunk 44 (TT351–TT360) merged and fixed; 435 rows; 1 tie-break; 1 CHUNK44_CORRECTIONS entry; 0 DERIVER_OVERRIDES; 0 substantive flags.
metadata:
  type: project
---

Chunk 44 (TT351–TT360) — PM I.1 pp. 418–424 (physical PDF pp. 436–442).

**Fact:** 435 rows total after merge. 1 tie-break override added. 1 CHUNK44_CORRECTIONS entry. 0 DERIVER_OVERRIDES. 0 egyptologist flags. Idempotent. All 618 tests pass.

**Why:** Standard Phase-0 reconciliation run. Only one 1/1/1 tie (TT354 notes_from_pm); other disagreements resolved by 2/1 majority.

**How to apply:** Next chunk starts at TT361. Row count baseline is 435.

## Tie-break overrides added

- `TT354|notes_from_pm`: 1/1/1 split on (1) CAPS vs title-case for inline name `Perhaps AMENEMḤET` (A had raw text-layer all-caps; B/C correct title-case) and (2) truncation (C dropped `(tomb 340, ...)` parenthetical). Pinned B's title-case reading with full parenthetical. PDF p.418 confirmed.

## CHUNK44_CORRECTIONS

- `TT358 location_sub_area = "In Court of Temple of Ḥatshepsut"`: Agent A correctly extracted; majority B+C emitted null. PM p.421 explicit sub-area descriptor, parallel to TT308 Kemsit's `"In the Temple of Mentuḥotp"`.

## DERIVER_OVERRIDES

None. TT354 and TT355 both have `Perhaps` qualifying the PRIMARY OCCUPANT — deriver correctly fires `uncertain`. Both added to `test_182_uncertain_attribution_canonical_set`.

## Cosmetic disagreements resolved by majority

- TT353/TT358 `theban_area`: B had `Deir el-Baḥri` (Ḥ-underdot); A+C had `Deir el-Bahari` (plain h). 2/1 majority + 10 prior canonical rows confirm plain-h form. No override.
- TT360 `source_page`: B=423 (off-by-one); A+C=424. 2/1 majority correct.

## Key semantics decisions

- TT354 `shared_with_tombs=["TT340"]`: Majority B+C correct. TT340 (chunk-42) has `(perhaps also owner of tomb 354)` — explicit ownership phrasing → shared_with_tombs=["TT354"] on TT340's side. Symmetry invariant requires TT354 to reciprocate. No CHUNK44_CORRECTIONS override needed.
- TT360 `shared_with_tombs=[]`: `(tomb 361)` qualifies parent Ḥuy's burial location — provenance-of-find, not co-ownership. All 3 agents agreed `[]`. Correct.

## Test additions

- `test_chunk44_row_count` (asserts 435, replacing test_chunk43_row_count which asserted 425)
- `test_chunk44_all_rows_present`, `test_chunk44_theban_areas`, `test_chunk44_source_pages`, `test_chunk44_attribution_certainties`, `test_chunk44_tt354_corrections`, `test_chunk44_tt358_location_sub_area`, `test_chunk44_tt353_senenmut_shared`, `test_chunk44_tt359_inherkha_shared`, `test_chunk44_tt360_kaha`, `test_chunk44_tt352_anonymous`
- TT354 + TT355 added to `test_182_uncertain_attribution_canonical_set` canonical set

## Symmetry invariant lesson

If either side of a PM cross-reference uses "Also owner of N" / "perhaps also owner of N", that triggers symmetric shared_with_tombs on both sides. `(tomb N, cf. box-lid)` on TT354 looks like evidential rationale but is actually the other side of TT340's ownership assertion — do not suppress it.
