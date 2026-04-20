# Extraction prompt — Leprohon 2013 chunk 7 (Chapter VI Second Intermediate Period — Dyn 15 + 16 + 16a + 17 + 17a)

Pass this to **three** independent Claude Code subagents in parallel. Each agent writes to `agent-{a,b,c}-sip.jsonl`.

---

You are extracting structured king data from Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, SBL WAW 33.

**Input:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p102-p113-pypdf.md` — physical pp. 102–113 = printed 81–92. Contains Leprohon's Chapter VI Second Intermediate Period: **Dyn 15** (Hyksos), **Dyn 16** (Upper-Egyptian Theban line), **Dyn 16a** (Five kings whose position in Dyn 16 is uncertain), **Dyn 17** (Theban line including Senakhtenre / Seqenenre / Kamose), **Dyn 17a** (one king appended to Dyn 17).

**Output:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/agent-{a|b|c}-sip.jsonl`

## Prerequisite reading

Read prompts for chunks 1–6 for schema, hazard catalogue, and all rules previously established. Chunk-7 notes below cover only what's new.

## Chunk-7 specifics

### Dynasty labels, chapter, IDs

All rows: `chapter: "Second Intermediate Period"`. IDs:
- Dyn 15: `leprohon-15.NN`, `dynasty_number: 15`, `dynasty_label: "Dynasty 15"`.
- Dyn 16: `leprohon-16.NN`, `dynasty_number: 16`, `dynasty_label: "Dynasty 16"`.
- Dyn 16a: `leprohon-16a.NN`, `dynasty_number: 16`, `dynasty_label: "Dynasty 16a"`.
- Dyn 17: `leprohon-17.NN`, `dynasty_number: 17`, `dynasty_label: "Dynasty 17"`.
- Dyn 17a: `leprohon-17a.NN`, `dynasty_number: 17`, `dynasty_label: "Dynasty 17a"`.

All rows: `stage_suffix: null` (no multi-stage kings in this chunk).

Each sub-dynasty resets its sequence numbering at 1 (standard Leprohon convention; the Dyn-11b continuation from 11a is the one-off exception).

### New name-type label: `Title and name:` and `Title and birth (?) name:`

Dyn 15 (Hyksos) entries often have a combined name-row headed `Title and name:` or `Title and birth (?) name:` that fuses the Egyptian ruler-title `ḥqꜣ ḫꜣswt` ("Ruler of Foreign Lands") with the king's personal name. Treat these as a **combined dual-emission to `throne_names` + `birth_names`** (same pattern as `Throne and birth:` in chunks 3 and 5). The source_note on both copies should carry a canonical marker:
```
"Leprohon labels as 'Title and [birth (?)] name' — the Hyksos `ḥqꜣ ḫꜣswt` ('Ruler of Foreign Lands') ruler-title is attested fused with the king's personal name; dual-emitted to both `throne_names` and `birth_names` for downstream matching."
```
(Variant: omit the `(?)` when Leprohon's label doesn't include it.)

### Multi-slot stubs

Dyn 16 ends with a multi-slot stub `11–15. FIVE NAMES LOST`. Dyn 17 has TWO multi-slot stubs: `3–10. EIGHT NAMES LOST` and `12–14. THREE NAMES LOST`. Emit ONE row per multi-slot stub header, with `sequence_in_chapter_section` set to the FIRST slot in the range. Title-Case the descriptor phrase for `display_name` (`"Eight Names Lost"`, `"Three Names Lost"`, `"Five Names Lost"`). All name-lists empty. Same convention as chunks 5 and 6.

### Ramesside-only headword asterisks

Apply the canonical Ramesside-only tag (`"Ramesside-attested only — no contemporary attestation per Leprohon's headword asterisk."`) to every row whose HEADWORD carries a trailing `*`. Per-entry asterisks on individual name-rows stay in their originating name-type list with a per-entry source_note, same as chunks 4–6.

### Fragmentary / bracketed name headwords

Many Dyn 17 entries have `///` wildcards or `[bracketed]` reconstructions in their SMALLCAP headword (`USER /// RE (I)*`, `/// HEBRE (I)*`, `/// HEB(?)-RE (II)*`, `/// WEBENRE (III)*`). Preserve the `///` verbatim in `display_name` and `transliteration`; do not strip or smooth.

### Roman-numeral disambiguators with `(?)` markers

Some entries have `(?)` inside the disambiguation `(II)` parenthetical: `/// HEB(?)-RE (II)*`. Preserve verbatim in `display_name`.

### Expected row counts

- **Dyn 15:** 6 rows (entries 1–6 contiguous: Semqen, Aper-anati, Seker-her, Khyan, Apepi/Apophis, Khamudi).
- **Dyn 16:** 11 rows (entries 1–10 contiguous + multi-slot stub at slots 11–15 = 10 + 1).
- **Dyn 16a:** 5 rows (entries 1–5 contiguous: Dedumose I, Dedumose II, Montuemsaf, Mentuhotep VII, Senwosret IV).
- **Dyn 17:** 19 rows (entries 1–2 + stub 3–10 + entry 11 + stub 12–14 + entries 15–28 = 2 + 1 + 1 + 1 + 14).
- **Dyn 17a:** 1 row.

**Total: 42 rows.** If you come in significantly under 38 or over 46, re-scan.

### Name-types and Greek alias

Dyn 15 entry 5 is headed `5. APEPI (APOPHIS)` — the Greek form Apophis in the parenthetical. Same convention as chunk-2 Khufu/Cheops, Khafre/Chephren: `display_name: "Apepi"`, `alt_display_names: ["Apophis"]`.

Dyn 17 entry 26 is `26. SENAKHTENRE AHMOSE (I)` — here `(I)` is a Roman-numeral disambiguator (distinguishing this Ahmose from the Dyn 18 founder Ahmose I). Preserve verbatim in display_name: `"Senakhtenre Ahmose (I)"`.

### Sparse titularies

Dyn 16 and 17 kings mostly have only Throne + Birth. `Horus: none attested` → empty list. Same as chunks 5 and 6.

## Output ordering

Sort by (`dynasty_label`, `sequence_in_chapter_section`). merge.py re-sorts.

## Final response

Give a one-line summary: row count per (sub-)dynasty, highest footnote seen, Ramesside-only + `Title and name` dual-emit counts, multi-slot stub confirmations. Under 100 words.
