---
name: HKW 2006 chronology review patterns
description: Recurring review issues in HKW Chronological Table (printed pp. 490-495) — name-type mislabeling in rationale strings, slash-vs-contraction patterns, prose-vs-table provenance attribution
type: project
---

Recurring patterns observed in HKW chronology Phase-0 source (`pipeline/pipeline/authority/sources/hkw-chronology-2006/`).

**Why**: PR #188 audit found one P1 and several P2 issues clustered around `_rationale` strings in `fix_rows.py` that mislabeled the *type* of name (Horus name vs birth name vs throne name) when HKW's table itself prints no name-type label. Pattern is silent because the typed fields (`alt_names`) are correct — only the rationale-as-provenance is wrong.

**How to apply**: when reviewing HKW migrations or any future schema audit on this source:

1. **Parenthetical-name patterns in HKW's table are NOT typed by HKW.** When HKW prints `Khufu (Cheops)`, `Menkaure (Mycerinus)`, `Khephren (Ra'kha'ef)`, `Djoser (Netjery-khet)` — all four are just "alternative name forms HKW prints in parentheses." Ra'kha'ef is the birth name (nomen) of Khafre/Khephren — it's NOT a Horus name (Horus name = Userib). Netjery-khet IS Djoser's Horus name historically, but HKW's table doesn't label it as such. Conservative rationale: "HKW prints '<X> (<Y>)'; <Y> moved to alt_names." Don't claim Horus/throne/Greek-form classification unless HKW does.

2. **Slash-row patterns have at least three distinct shapes**, all currently lumped as "transliteration-variant pair":
   - True transliteration variants (`'Adj-ib/Anedjib`, `Ra'djedef/Djedefre'`, `Ra'neferef/Neferefre'`, `Piye/Pi'ankhy`) — one king, two romanizations.
   - Printer's contraction (`Tut'ankhaten/amun` = shared stem `Tut'ankh-` + endings `-aten`/`-amun`). The verbatim string `Tut'ankhaten/amun` is itself a useful alt for matching but needs explicit expansion.
   - Hedge/uncertainty (`Smenkhkare'/Nefernefruaten 'Ankhkheprure'`) — one prenomen, two candidate kings; HKW p. 477 prose actually leans toward Smenkhkare. The `name_uncertain=True` typed flag is right; the rationale should cite both the table AND the prose discussion.

3. **Coregency reciprocal links** — HKW's table shows the date overlap symmetrically (both rows carry the overlapping years), so the "fact lives on the OTHER ruler's row" framing is misleading. The asymmetry is in the reconciled.jsonl prose-note placement, not in HKW's encoding. Rewrite reciprocal-row rationales to say so.

4. **Verifying chronology dates**: the printed table is at physical-PDF pp. 504-509 (= printed pp. 490-495). Krauss/Warburton's prose justification is at physical-PDF pp. 491-495 (= printed pp. 477-481) and earlier. Always cite both the table and the prose when the table itself has a hedge (slash, parenthetical, `?`, multi-ruler aggregation).

5. **Multi-ruler aggregations**: HKW genuinely groups N rulers under one date range when the order is unknown — this is a HKW signal, not transcription error. The 5 aggregations on pp. 492-494 are: Dyn 13 (4 kings), Dyns 16/17 (6 kings, with `Sobekemzaf I & II` as a tighter sub-pair), Dyn 23 UE (2 kings), Dyn 23 UE (3 kings), Dyn 23 LE (2 kings with one `(?)` hedge). The `&`-vs-`,` distinction within a row is currently lost in `rulers[]` flattening — flag if seen elsewhere.
