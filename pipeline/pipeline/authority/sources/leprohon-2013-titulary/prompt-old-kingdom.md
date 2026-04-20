# Extraction prompt — Leprohon 2013 chunk 2 (Dyn 2 tail + Dyn 2a + Chapter III Old Kingdom)

Pass this to **three** independent Claude Code subagents in parallel. Each agent writes its JSONL output to a distinct filename (`agent-{a,b,c}-old-kingdom.jsonl` per the multi-chunk pattern). The three outputs are then merged by `merge.py` via majority vote.

---

You are extracting structured king data from the OCR'd text of Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, SBL Writings from the Ancient World 33. Ed. Denise M. Doxey.

**Input:** the deterministic pypdf+MdC chunk file at

`/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p51-p69-pypdf.md`

(Absolute path; the Read tool requires it.) This chunk covers physical PDF pages 51–69 = printed pages 30–48. It contains:

- **Dynasty 2 tail** (printed p. 30, physical p. 51): entry `9. SENEFERKA` — a Dyn 2 king not covered by chunk 1 because chunk 1's scope mis-ended at printed p. 29.
- **Dynasty 2a** (printed p. 30): 2 Ramesside-only entries (`1. NEFERKASOKAR*`, `2. "HUDJEFA" (I)* (?)`). Leprohon opens the section with "The Ramesside Lists add a number of kings in this group, although none of these rulers is actually attested in contemporary documents."
- **Chapter III Old Kingdom** (printed pp. 31–48, physical pp. 52–69): Dynasties 3, 3a, 4, 5, 6, 8, 8a. Note Leprohon has NO Dynasty 7 — following the scholarly consensus that Manetho's "Dynasty 7" (70 kings in 70 days) is fictional / conflated with Dynasty 8. Dyn 8a runs to 8 entries: 1-2 on printed p. 47, 3-8 on printed p. 48 (Iti, Imhotep, Hotep, Khui, Isu, Iytjenu).

**Output:** write your final JSONL to

`/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/agent-{a|b|c}-old-kingdom.jsonl`

One JSON object per line. No trailing newline required, no preamble, no code fences.

## Prerequisite reading

Read `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/prompt.md` first — the chunk-1 prompt — for the full schema, field semantics, and hazard catalogue. The chunk-2 instructions below are DIFFERENCES and ADDITIONS; everything else carries over.

## Schema additions for chunk 2

### Sub-dynasty ID scheme

Leprohon types several sub-dynasty sections (`Dynasty 2a`, `Dynasty 3a`, `Dynasty 8a`) for groups of Ramesside-added kings that have no contemporary attestation. Schema changes:

- `dynasty_number`: integer parent dynasty. Dynasty 2a → `2`; Dynasty 3a → `3`; Dynasty 8a → `8`.
- `dynasty_label`: the full label verbatim including the letter suffix. `"Dynasty 2a"`, `"Dynasty 3a"`, `"Dynasty 8a"` (no BCE range in parentheses — sub-dynasties don't carry date ranges in Leprohon).
- `leprohon_id`: `leprohon-{dynasty_number}{letter_suffix}.{NN}` where `{letter_suffix}` is `""` for the main dynasty and `"a"` for the sub-dynasty. Examples:
  - Seneferka (Dyn 2, entry 9) → `leprohon-2.09`
  - Neferkasokar (Dyn 2a, entry 1) → `leprohon-2a.01`
  - Hudjefa (Dyn 2a, entry 2) → `leprohon-2a.02`
  - Djoser (Dyn 3, entry 1) → `leprohon-3.01`
  - (hypothetical Dyn 3a entry 1) → `leprohon-3a.01`
  - Khufu (Dyn 4, entry 2) → `leprohon-4.02`
- `sequence_in_chapter_section`: Leprohon's explicit numbering. Resets at each (sub-)dynasty section. `1. NEFERKASOKAR` → sequence 1 (within Dyn 2a), even though it's visually the 10th king entry on that page.

### Chapter label

- For Dyn 2 tail + Dyn 2a (printed p. 30, still within chapter II Early Dynastic): `chapter: "Early Dynastic Period"`.
- For chapter III (printed pp. 31+, Dyn 3 onward): `chapter: "Old Kingdom"`.

The `chapter` field is NOT the same as the dynasty section header — it's the parent chapter in Leprohon's TOC. Page 30 is in chapter II despite physically being the last page before chapter III starts; the `III Old Kingdom` section opens on printed p. 31.

### Asterisked headwords (Ramesside-only)

Leprohon sometimes marks entire king entries with an asterisk in the SMALLCAP headword itself (not just in individual name-rows), signalling that the king is attested ONLY in Ramesside king-lists, not in any contemporary document. Examples: `1. NEFERKASOKAR*`, `5. QA HEDJET/HUI/HUNI*`.

Rule:

- Drop the `*` from `display_name`. `NEFERKASOKAR*` → `display_name: "Neferkasokar"`.
- Do NOT leak the asterisk into `alt_display_names`.
- The asterisk signals Ramesside-only attestation, which we do NOT yet carry as a structured field (deferred — see chunk-1 egyptologist-reviewer note about `contemporary_attestation` boolean). Document it in `source_note` of the first name entry for that king, with exact phrasing `"Ramesside-attested only — no contemporary attestation per Leprohon's headword asterisk."` appended AFTER any existing footnote commentary (or as the sole content if no footnote exists for that name entry).

### Quoted + letter-hedged headwords

Leprohon uses quote marks + parenthetical qualifiers in some Dyn 2a / Dyn 3a / Dyn 8a entries. Example from chunk 2: `2. "HUDJEFA" (I)* (?)`.

Parse:

- `display_name`: strip the outer asterisks and trailing `(?)` uncertainty marker. Preserve the quote marks and any roman-numeral disambiguator `(I)`, `(II)`. `"HUDJEFA" (I)* (?)` → `display_name: "\"Hudjefa\" (I)"`. Title-case the SMALLCAP but keep internal punctuation.
- `alt_display_names`: `[]` (no slashes).
- Append to the first name entry's `source_note`: `"Ramesside-attested only — no contemporary attestation per Leprohon's headword asterisk."` AND if a trailing `(?)` is present, also append `"Leprohon marks this king with a `(?)` uncertainty hedge."`

### Slashed + letter-tagged headwords

Chunk 2's Dyn 3 has `5. QA HEDJET/HUI/HUNI*` — a three-way slashed homonym that's ALSO Ramesside-only. Parse:

- `display_name`: `"Qa Hedjet/Hui/Huni"` (title-cased, slashes preserved, asterisk dropped)
- `alt_display_names`: `["Qa Hedjet", "Hui", "Huni"]` (split on slash)
- First name entry's `source_note` appends: `"Ramesside-attested only — no contemporary attestation per Leprohon's headword asterisk."`

### Chapter III king density

Expected king counts per dynasty (rough — verify against the chunk file):

- Dyn 2 tail: 1 row (Seneferka)
- Dyn 2a: 2 rows (Neferkasokar, Hudjefa)
- Dyn 3: ~5-7 rows (Djoser, Sekhemkhet, Khaba, Sanakht, Qa Hedjet/Hui/Huni, ...)
- Dyn 3a: unknown, probably 2-5 rows
- Dyn 4: ~6-8 rows (Snefru, Khufu/Cheops, Djedefre/Radjedef, Khafre/Chephren, Menkaure/Mycerinus, Shepseskaf, ...)
- Dyn 5: ~9-10 rows (Userkaf, Sahure, Neferirkare, Shepseskare, Neferefre, Niuserre, Menkauhor, Djedkare Isesi, Unas)
- Dyn 6: ~5-7 rows (Teti, Userkare?, Pepi I, Merenre, Pepi II, Neith?, ...)
- Dyn 8 (no Dyn 7!): ~15-17 rows (Leprohon documents an unusually full Dyn 8 list)
- Dyn 8a: 8 rows (Ramesside-added)

**Expected total row count: ~60.** If you produce fewer than 55 or more than 65, re-read the chunk file and re-scan for missed dynasty sections or king entries.

### Big-name Dyn 4 kings — alias emission

Several Dyn 4 kings have well-established Greek aliases Leprohon prints in the SMALLCAP headword itself, like `2. KHUFU (CHEOPS)` and `4. KHAFRE (CHEPHREN)`. Parse:

- `display_name`: the primary Egyptian form in title case. `"Khufu"`, `"Khafre"`.
- `alt_display_names`: include the parenthesised Greek form. `["Cheops"]`, `["Chephren"]`.

For `3. RADJEDEF` (Leprohon's preferred reading) or `3. DJEDEFRE` (alternative in the book), Leprohon opts for one based on his footnote (fn. 35 in the chunk's footnotes). Use whichever he prints in the SMALLCAP headword as `display_name`; the alternative goes in `alt_display_names`.

### "Son of Re" / throne-name prefix

In Dyn 4+, Leprohon adopts the "Son of Re" convention. Throne-name entries often include the swt-bit / s3-rc prefix inside the transliteration (e.g. `swty-bity mr(y)-rꜥ`). Preserve the full transliteration verbatim in the transliteration field. Do not strip the swty-bity / sꜣ-rꜥ prefix.

### BCE-range in dynasty label

Dyn 3 through Dyn 8 all have BCE ranges in their section headers (`Dynasty 3 (2686–2613 B.C.E.)`, `Dynasty 4 (2613–2498 B.C.E.)`, ...). Do NOT include the BCE range in `dynasty_label` — `dynasty_label: "Dynasty 3"` only. The BCE range is chronology data that belongs in a separate `dynasty_dates` authority (HKW etc.), not in Leprohon's titulary extract.

## Chunk-1 scope recovery

Chunk 1 (PR #83) silently dropped printed p. 30 — the chapter-II boundary was misread as ending at p. 29. Chunk 2 picks up the 3 missed rows (Seneferka, Neferkasokar, Hudjefa) as the first 3 emissions in your output. They have `chapter: "Early Dynastic Period"` and the printed-page citation is `30`. Do not skip them.

## Expected row count

**Exactly 3 ED-recovery rows + ~57 chapter-III rows = ~60 rows total** (expected per-dynasty: 2:1, 2a:2, 3:5, 3a:4, 4:7, 5:9, 6:7, 8:17, 8a:8).

If you come in significantly under 55, you've missed something; re-scan for dynasty sub-section headers (`Dynasty 3a`, `Dynasty 8a`) and king entries inside them.

## Output

Sort the emitted rows by `(dynasty_number, dynasty_suffix_letter, sequence_in_chapter_section)`. Rows go in order: `leprohon-2.09`, `leprohon-2a.01`, `leprohon-2a.02`, `leprohon-3.01`, ..., `leprohon-3a.01`, ..., `leprohon-8.NN`, `leprohon-8a.NN`.

In your final response message, give a one-line summary: row count per dynasty (e.g. `"2:1, 2a:2, 3:6, 3a:3, 4:8, 5:9, 6:6, 8:4, 8a:3"`), highest footnote number seen, any OCR-vs-pypdf transliteration disagreements you flagged, and any Ramesside-only kings you tagged with the `source_note` addition. Under 100 words.
