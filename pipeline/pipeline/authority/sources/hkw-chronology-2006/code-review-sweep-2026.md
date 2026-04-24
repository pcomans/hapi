# Sweep Code Review — hkw-chronology-2006

Scope: retrospective review of `pipeline/pipeline/authority/sources/hkw-chronology-2006/` plus the HKW tests in `pipeline/tests/test_authority.py`. No `merge.py` or `fix_rows.py` is committed for this source; no multi-chunk `ALL_CORRECTIONS` / `ALL_RENAMES` ledger exists to validate.

## Findings

### P2 — The original 203 HKW rows have no value-pinning tests

`pipeline/tests/test_authority.py:38-99` checks HKW row count, valid kinds, referential links, negative dates, positive uncertainty, and broad page membership. It only pins field values for the 4 Hendrickx Ch 2 addendum rows (`test_dyn0_*`, lines 101-202). The initial IV.2/IV.3 table rows make up 203 of 207 rows, including high-value chronology facts such as Khufu dates, Hatshepsut/Thutmose III coregency dates, prenomens, Greek forms, and multi-ruler rows, but almost any field-level drift there would pass as long as the value remains structurally plausible. That violates Rule 5 ("Tests assert values") and Rule 3 ("Deterministic enforcement"). Add a curated regression fixture/table that pins representative rows across every page/kind and every special case documented in README: Dyns. 16/17 split, two Dyn. 23 rows, multi-ruler rows, `Osorkon III, Takelot III`, and the Dyn. 8 Neferirkare correction.

### P2 — Parent-period enforcement still silently allows new orphan dynasties

`test_dynasty_parent_period_references_exist` (`pipeline/tests/test_authority.py:59-66`) only validates `parent_period` when it is non-null. The current data intentionally has Dyn. 0 as the sole orphan (`reconciled.jsonl:3`, asserted at lines 186-202), but the general invariant does not enforce that exclusivity. A future edit could drop `parent_period` from Dyn. 12, Dyn. 18, or any other dynasty and pass. That is the same deterministic-enforcement gap identified in the prior code review, only partially addressed by pinning Dyn. 0. Tighten the test to assert that null `parent_period` is allowed only for `number == 0` (or add a sourced Predynastic period row and remove the orphan).

### P2 — README still states Scorpion I is a Dyn-0 ruler

The reconciled data correctly carries Scorpion I as `dynasty: null` with a note explaining that Hendrickx does not consistently place him in Dyn. 0 (`reconciled.jsonl:6`). The tests also pin this (`pipeline/tests/test_authority.py:129-155`). But README still says Ch 2 "Added 3 Dyn-0 ruler rows (Iry-Hor, Ka, Scorpion I)" and repeats "3 Dyn-0 ruler rows" at `README.md:9` and `README.md:32-35`. That source documentation now contradicts the curated fact and can mislead future authority consumers into reintroducing the prior P1. Rewrite as "3 Dyn-0-era / boundary ruler rows" and explicitly say only Iry-Hor and Ka are assigned `dynasty: 0`.

### P3 — Dyn. 8 Neferirkare correction is not deterministically pinned

`README.md:104-113` documents that HKW prints `2119-2218+25` and that the row was normalized to `2119-2118+25` using the dynasty-end constraint plus Baud's chapter. The row note at `reconciled.jsonl:58` records the correction, but no test pins the corrected value or the explanatory note. This is exactly the class of reviewer-inserted character/value repair that should not rely on prose alone. Add a focused test for display `Neferirkare'`, `dynasty == 8`, `start_year == -2119`, `end_year == -2118`, and a note mentioning the printed `2218` typo.

## Non-findings

The previous Ch 2 P1/P2 issues appear fixed: Ka no longer has unsourced `Sekhen`, Scorpion I is `dynasty: null`, and Ch 2 pages are narrowed to `{88, 89, 91}`. I saw no committed `fix_rows.py` characters to audit in this source directory.
