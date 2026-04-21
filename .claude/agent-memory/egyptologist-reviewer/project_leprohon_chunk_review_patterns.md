---
name: Leprohon 2013 chunk-review recurring patterns
description: Recurring issues seen in Leprohon titulary chunk PRs — pypdf OCR artifacts bleeding into anglicised/translation fields, and silent translation fabrication for untranslated Semitic names
type: project
---

Recurring failure modes in Leprohon 2013 titulary chunk PRs (authority source `leprohon-2013-titulary`):

1. **pypdf OCR artifacts leaking into `anglicised` and `translation` fields.** The raw pypdf chunk files preserve mis-OCR artefacts like `ꜥꜥ mu` (should be `aa mu`) and garbled translations like `"ṯhe ꜣsiꜥtic"` (should be `the Asiatic`). Reconciliation is expected to normalise these to plain ASCII in anglicised/translation fields — the MdC `ꜥ`/`ꜣ` characters belong ONLY in `transliteration`. Seen in chunk 6 row 14.4 Aamu.

2. **Silent translation fabrication for Semitic-origin birth names.** When Leprohon's source gives no gloss (just a transliteration), reconciliation sometimes fills `translation` with the anglicised form (e.g. `"translation": "Nuya"` for `nu-ya` where source provides no gloss). Expected: `translation: null`. Fabricating the anglicised form as "translation" pollutes downstream fuzzy-matching. Seen in Dyn 14a rows 1, 2, 4, 5.

3. **MdC `rꜥ` leaking into `anglicised` field** where it should be "ra". E.g. chunk 6 row 14.25 anglicised `"nefertum /// rꜥ"` vs correct `"nefertum /// ra"` (compare 14.29 `"i /// ra"` which is correct). Chunk file itself may carry the bug; reconciliation should catch.

4. **Alias coverage gap: older name readings.** Kings whose names were re-read in the Ryholt era often lack aliases for their older readings. E.g. 14.3 Qareh was formerly read "Qar" per fn 140; museums catalogued before 1997 still use "Qar". `alt_display_names` should capture these.

5. **Page-range chunk boundaries cutting dynasties mid-section.** Chunks defined by raw PDF page ranges (e.g. "p128-p145") can truncate a dynasty before its last ruler. Seen in chunk 9 (p128-p145): Leprohon places Tausret as 19.8 on printed p.125 = PDF p.146, one page past the chunk boundary, so `dynasty_label == "Dynasty 19"` yields 7/8 rulers silently. Future chunks should be bounded by Leprohon's numbered ruler sections, not raw PDF pages. Reviewer check: for every full dynasty in a chunk, count rulers against Leprohon's TOC.

6. **Anglicisation typos vs. source-fidelity "Ramses" vs modern "Ramesses".** Leprohon uses "Ramses" throughout; museums + HKW + von Beckerath use "Ramesses". Keeping Leprohon's form as `display_name` is defensible for source fidelity, but `alt_display_names` must carry "Ramesses I/II/III..." or downstream matching against Met/Brooklyn/BM catalogs will miss. Chunk 9 rows 19.01, 19.03 had empty `alt_display_names`. Also watch for slashed dual-spelling display names like "Merenptah/Merneptah" (19.04) — unusual and bad for matching; prefer single canonical + aliases.

7. **Internal anglicisation typos — spot-check long variant lists.** Long variant arrays (e.g. Ramesses II's 42 Horus + 14 GH + 14 TL) accumulate typos that escape reconciliation. Chunk 9 had `"sekehm khepesh"` for `sḫm-ḫpš` at Ramesses II GH variant 14 while the same phrase is correctly "sekhem khepesh" elsewhere. Reviewer check: for repeated high-frequency phrases (`kꜣ nḫt`, `sḫm-ḫpš`, `ḥḳꜣ mꜣꜥt`, `wḥm ḫꜥw`, `mry rꜥ`), confirm anglicised forms are consistent across rows.

8. **MdC decoding — reviewer self-check.** When auditing transliteration fidelity, decode MdC carefully: uppercase `A` = `ꜣ` (aleph), lowercase `a` = `ꜥ` (ayin); uppercase `H` = `ḥ`, lowercase `h` = `h`; uppercase `S` = `š`, lowercase `s` = `s`; etc. Easy to flip aleph↔ayin when reading quickly. Cross-check against a known standard form (e.g. Avaris = `ḥwt-wꜥrt` with ayin, not aleph) before raising a P1. **Self-incident 2026-04-20 (chunk 7 SIP review)**: flagged Apepi's `ḥwt-wꜥrt` as wrong, thinking MdC `wart` decoded to `wꜣrt`; actually lowercase `a` = ayin so `wꜥrt` was correct. Advisor caught it.

9. **HPA preamble promoted to throne_names for Dyn 21a kings.** Leprohon prefaces HPA-pharaohs (Herihor, Menkheperre, Pinodjem I, Psusennes III) with their priestly title `ḥm nṯr tpy n imn` (High Priest of Amun) *before* the royal titulary proper. Extractors have mis-classified this preamble as a `Throne` entry. Correct handling: HPA title goes in a record-level `source_note` (see Psusennes III `leprohon-21a.03` as correct template — Throne = `tit kheperu ra`, HPA narrated in note). Seen in chunk 11 rows `leprohon-21.01` (Herihor) and `leprohon-21a.02` (Menkheperre), where `throne_names[0].anglicised == "hem netjer tepy en imen"`. Downstream risk: poisons prenomen index — every HPA-Amun artifact cross-matches all HPA kings.

10. **Sheshonq/Shoshenq spelling — alt_display_names gap.** Leprohon prints "Sheshonq"; Met/Brooklyn/Harvard/Kitchen-TIPE use "Shoshenq". Chunk 11 left all Dyn 22 Sheshonq rows with empty `alt_display_names`. This isn't a Greek form (so the prompt's "no Greek aliases not printed by Leprohon" rule doesn't apply) — it's a transliteration variant. Phase-A matcher will miss every Shoshenq artifact without explicit alias coverage. Applies to Sheshonq I–V + IIa/IIb/IIc.

11. **Name-form display issue: birth-name-as-headword.** Leprohon uses Egyptian birth names as headwords (`Nesbanebdjed (Smendes)`, `Paseba-kha-en-niut (Psusennes) I`), but museums and general readers expect the Greek/conventional form (Smendes, Psusennes I). Consider flipping `display_name` to the conventional form with Leprohon's birth-name in `alt_display_names`, rather than the current parenthetical. Chunk 11: Smendes (`leprohon-21.02`), Psusennes I/II/III (`leprohon-21.04`, `leprohon-21.08`, `leprohon-21a.03`).

**Why:** Downstream fuzzy matching against museum catalog data is highly sensitive to noise in anglicised/translation fields — MdC characters, fabricated translations, and missing historical name-variants all degrade match quality.

**How to apply:** When reviewing a new Leprohon chunk PR, grep the reconciled rows for:
- `ꜥ`, `ꜣ`, `ḫ`, `ḏ`, `š`, `ṯ` etc. in `anglicised` or `translation` fields (these belong in transliteration only)
- `translation` fields that equal the `anglicised` field (likely fabrication)
- Footnotes mentioning older name readings ("previously read as X", "formerly known as Y") → check `alt_display_names`
