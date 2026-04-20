# Extraction prompt — Leprohon 2013 chunk 5 (Chapter V Middle Kingdom — Dynasty 13 ephemeral line)

Pass this to **three** independent Claude Code subagents in parallel. Each agent writes to `agent-{a,b,c}-dyn13.jsonl`. The three outputs are then merged by `merge.py` via majority vote.

---

You are extracting structured king data from the pypdf+MdC-normalised text of Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, SBL Writings from the Ancient World 33. Ed. Denise M. Doxey.

**Input:** the deterministic pypdf+MdC chunk file at

`/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p81-p92-pypdf.md`

This chunk covers physical PDF pages 81–92 = printed pages 60–71. It contains **Dynasty 13** (the long ephemeral-king line that followed Queen Sobekneferu at the end of the Middle Kingdom). Leprohon treats Dyn 13 as chapter-V Middle Kingdom (NOT chapter-VI Second Intermediate Period as a naïve reader might expect — his chapter VI SIP is reserved for Dyn 15-17 Hyksos + Theban).

**Scope boundary:** physical p. 81 is SHARED with chunk 4. At the top of p. 81 is the tail of Dyn 12 entry 8 (Queen Sobekneferu — already extracted in chunk 4 PR #87, do NOT re-emit her). The `Dynasty 13 (1782–1650 B.C.E.)` header appears mid-page 81 followed by 4-5 paragraphs of opening prose. **START your extraction at the first numbered Dyn 13 entry (`1. SOBEKHOTEP I`)**, skipping the opening prose.

**Output:** write your JSONL to

`/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/agent-{a|b|c}-dyn13.jsonl`

One JSON object per line. No preamble, no code fences, no trailing newline required.

## Prerequisite reading

Read prompt.md (chunk 1), prompt-old-kingdom.md (chunk 2), prompt-fip.md (chunk 3), and prompt-mk.md (chunk 4) first. The schema, hazard catalogue, and recent schema additions (`later_horus_names`, `stage_suffix`) carry over.

## Chunk-5 specifics

### Dynasty label and chapter

- `dynasty_number: 13`
- `dynasty_label: "Dynasty 13"` (no en-dash, no sub-suffix)
- `chapter: "Middle Kingdom"` (Leprohon places Dyn 13 in chapter V MK)
- `leprohon_id`: `leprohon-13.NN` where NN is Leprohon's own numbering (see "Entry numbering" below).
- `stage_suffix: null` for every row (Dyn 13 has no stage-suffixed entries).

### Entry numbering — `sequence_in_chapter_section` resets to 1 for Dyn 13

Dyn 13 starts its own numbering from entry 1 (Sobekhotep I), resetting from the chapter-V Dyn-12 tail that ended at entry 8 (Queen Sobekneferu). This is the NORMAL Leprohon convention (Dyn 11b's continuation from 11a is the one-off exception).

### Expected entry numbers

Leprohon numbers Dyn 13 entries **1 through ~55**, with gaps at 39-45 (Leprohon simply skips those numbers — possibly reserved for kings he later elected not to include). Expect roughly **48 emitted rows** (entries 1-38 + entries 46, 47, 48, 49 stub, 50, 51, 52, 53, 54, 55 = 38 + 10 = 48 rows). Verify against the chunk file; if you produce fewer than 44 or more than 52, re-scan for missed or double-counted entries.

### Sparse titularies are the norm

Unlike MK proper (chunk 4) where kings had full fivefold titularies, Dyn 13 kings are mostly attested in fragmentary form. **Throne + Birth is the typical pair;** Horus, Two Ladies, and Golden Horus are usually `none attested` for each king. Leprohon explicitly writes the phrase `"none attested"` for name-types he has no record of.

**Rule:** when Leprohon writes `Horus: none attested` (or any other `{name-type}: none attested`), emit an EMPTY LIST for that name-type list (`"horus_names": []`), NOT an entry with transliteration `"none attested"`. The `none attested` text is Leprohon's authorial shorthand for "empty"; parsing it as a real name-row would be wrong.

### Ramesside-only headword asterisks

Entries `7. IUFNI*`, `11. SEWADJKARE (I)*`, `12. NEDJEMIBRE*`, `36. INED*`, etc. carry headword-asterisks marking Ramesside-only attestation (per Leprohon's opening prose: "As before, the names not attested in contemporary records will be followed by an asterisk."). Apply the canonical Ramesside-only source_note tag (`"Ramesside-attested only — no contemporary attestation per Leprohon's headword asterisk."`) on the first populated name-entry of those rows. Same convention as chunks 2 and 3.

### Stub entries for destroyed / missing names

Leprohon sometimes preserves a sequence-numbering slot for a king whose name is entirely unreadable in his sources (e.g. a Turin Canon row that survives as a number-only entry without legible name glyphs). The pattern looks like `N. [DESCRIPTIVE PHRASE IN SMALLCAP]` with no name-row section following. Apply the same general convention as every other headword: normalise the SMALLCAP phrase to Title Case for `display_name`. Emit empty lists for every name-type field. Similar to the chunk-3 `/////` stub (Dyn 9-10a.02) except the descriptor is a prose phrase rather than a glyph sequence.

### Roman-numeral disambiguators and parenthesised qualifiers

Dyn 13 uses many Roman-numeral disambiguators (`I`, `II`, `III`, `IV`, `V`, `VI`, `VII`) and occasional `(?)` uncertainty markers. Preserve verbatim in `display_name`. No `alt_display_names` for Roman numerals alone; `alt_display_names` only gets populated when the display_name contains SLASH-separated homonyms.

### Fragmentary names with `////` wildcards and `[...]` epigraphic reconstructions

Several entries have `////` wildcards (four consecutive slashes) or `[square brackets]` indicating partially-reconstructed readings. Preserve verbatim in `transliteration` and `display_name` fields. Hedge-glyphs are Leprohon's positive assertion of "reading is fragmentary / partially hypothetical." Do not strip, smooth, or normalise.

### Headword-pattern rules

- Plain SMALLCAP headword (`N. NAME I`): Title-Case the name, preserve any Roman-numeral disambiguator.
- Headword with parenthesised roman-numeral disambiguator (`N. NAME (I)`): Title-Case and preserve the `(I)`, `(II)`, etc.
- Headword with trailing `(?)` uncertainty marker: preserve the `(?)` verbatim in `display_name`.
- Headword with a slash between two or more homonyms (e.g. `NAME1 / NAME2` or `NAME1 / NAME2 (?)`): `display_name` keeps the slash and any trailing `(?)` verbatim; `alt_display_names` lists each slash-separated form individually (strip any trailing `(?)` before splitting, because the uncertainty qualifies the whole king-identification, not a specific homonym spelling).
- Headword with fragmentary-reading markers (`[...]`, `////`): preserve verbatim in `display_name` and `transliteration` fields.
- Trailing `*` on the headword (not on a name-row): signals Ramesside-only attestation for the whole king. Drop the `*` from `display_name`, append the canonical Ramesside-only tag to the first populated name-entry's `source_note` (same rule as chunks 2-3).

### Family-reference "son of" genealogy in Birth names

Dyn 13 Birth names often include a `<sꜣ>` ("son of X") element linking to the previous king. Example: `imn-m-ḥꜣt <sꜣ> sbk ḥtp(w)` ("Amenemhat's son, Sobekhotep"). Preserve the angle-bracketed `<sꜣ>` verbatim in the transliteration — it's Leprohon's positive assertion that the son-of-X element is epigraphically explicit.

### Numbered variant entries within a name-type list

Dyn 13 has some kings with multiple Throne variants (e.g. `Throne 1:` / `Throne 2:`). Emit each as a separate entry in the same `throne_names` list with `variant_index` tracking position.

### Asterisked individual name-entries

Some Dyn 13 entries have `*` on an individual NAME-ROW (not the headword) signalling that specific name is Karnak-List-only. Apply the per-entry source_note policy from chunk 4 (rule 2 of prompt-mk.md): keep the entry in its originating name-type list with a source_note noting the later-attestation provenance. Do NOT route to `later_cartouche_names` / `later_horus_names`.

## Output ordering

Sort by `sequence_in_chapter_section` ascending: 1, 2, 3, ..., 38, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55.

## Final response

Give a one-line summary: total row count, highest entry number seen, Ramesside-only count, confirmation of stub-row 49 emission, any edge cases. Under 100 words.
