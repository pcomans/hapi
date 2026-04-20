# Extraction prompt — Leprohon 2013 chunk 1 (Early Dynastic Period)

Pass this to **three** independent Claude Code subagents in parallel (general-purpose, with Read/Write tools). Each agent writes its JSONL output to a distinct filename. The three outputs are then merged by `merge.py` via majority vote.

The prompt below is verbatim; the only per-agent substitution is the output-file suffix (`-a`, `-b`, `-c`).

---

You are extracting structured king data from the OCR'd chapter-II (Early Dynastic Period) of Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*. SBL Writings from the Ancient World 33. Edited by Denise M. Doxey.

**Input:** TWO chunk files, produced by independent transcription methods:

1. `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p42-p50-ocr.md` — Claude Code OCR subagent transcription. Cleaner STRUCTURE: proper markdown, italicised transliterations marked with `*...*`, footnotes grouped under `## Footnotes` per page, explicit `<!-- physical page NN (printed page MM) -->` delimiters.
2. `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p42-p50-pypdf.md` — deterministic `pypdf` text-layer extraction with Manuel de Codage → Egyptological-Unicode normalization applied to transliteration tokens (`A→ꜣ, a→ꜥ, H→ḥ, x→ḫ, X→ẖ, S→š, T→ṯ, D→ḏ, q→ḳ`). Cleaner CONTENT fidelity for transliteration glyphs (straight from the publisher's text layer), but looser structure (hyphenation breaks in footnotes, interleaved-space SMALLCAP headwords like `1. i ry -Hor`, EBSCO watermark lines embedded).

**How to use both files.** Read them BOTH before extracting. Cross-reference:

- **Structure (king-entry boundaries, footnote numbers, section headers, page citations)** — trust the OCR file (chunk-p42-p50-ocr.md). Use it to identify where each king entry starts/ends.
- **Transliteration content (the italicised Egyptological string in each name row)** — when OCR and pypdf agree, emit that. When they DISAGREE on a transliteration, the pypdf version is more likely correct because MdC normalization is mechanical and traceable to the publisher's text layer; but look at the anglicised gloss in parentheses as a tiebreaker (e.g. `(hedju-hor)` implies the transliteration is `ḥḏw-ḥr` with two h-with-dots rather than anything exotic). If the disagreement cannot be resolved on structural grounds, flag the row in `source_note` as `"OCR vs pypdf transliteration disagreement: OCR='<ocr>', pypdf='<pypdf>'"` and pick the pypdf form.
- **Footnote body text, English translations, prose** — use the OCR file (cleaner line breaks, proper sentence reconstruction).
- **Printed page numbers** — use the OCR file's `<!-- physical page NN (printed page MM) -->` delimiters. Verify against pypdf's EBSCO-watermark context if uncertain. Every king entry's `source_citation.printed_page` = the printed page number where the SMALLCAP `N. NAME` headword line appears (NOT the page where footnotes reside, NOT a spillover page).

The chunk covers physical PDF pages 42–50 (= printed pages 21–29 of the book, chapter II).

**Output:** write your final JSONL to `<repo_root>/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/agent-{a|b|c}.jsonl`. One JSON object per line, no trailing newline required, no preamble, no code fences.

**Task:** walk the chunk. Find every numbered king entry in chapter II — each one begins with a SMALLCAP headword line of the form `N. NAME` or `N. NAME/NAME` (the slashed form for homonym-variants like `DJET/WADJET`, `KHASEKHEM/KHASEKHEMWY`) inside one of three dynasty sections: `DYNASTY "0"`, `DYNASTY 1`, or `DYNASTY 2`. For each king entry, emit ONE JSON object with the schema below.

## Schema

```json
{
  "leprohon_id": "leprohon-0.01",
  "dynasty_number": 0,
  "dynasty_label": "Dynasty \"0\"",
  "chapter": "Early Dynastic Period",
  "sequence_in_chapter_section": 1,
  "display_name": "Iry-Hor",
  "alt_display_names": [],
  "horus_names": [
    {
      "transliteration": "iry-ḥr",
      "anglicised": "iry-hor",
      "translation": "The companion of Horus",
      "variant_index": 1,
      "is_variant": false,
      "attested_in": [],
      "source_note": "Von Beckerath 1999, 36–37."
    }
  ],
  "nebty_names": [],
  "golden_horus_names": [],
  "throne_names": [],
  "birth_names": [],
  "later_cartouche_names": [],
  "seth_names": [],
  "source_citation": {
    "book": "Leprohon 2013",
    "edition": "SBL Writings from the Ancient World 33",
    "printed_page": 22,
    "physical_pdf_page": 43
  }
}
```

## Field semantics

- `leprohon_id` = `"leprohon-{dynasty_number}.{NN}"` where NN is zero-padded 2-digit. For Dyn 0 → `leprohon-0.01`, `leprohon-0.02`, ..., `leprohon-0.12`. For Dyn 1 → `leprohon-1.01`, ..., `leprohon-1.07`. For Dyn 2 → `leprohon-2.01`, ..., `leprohon-2.08`.
- `dynasty_number` = integer. `0` for Dyn 0, `1` for Dyn 1, `2` for Dyn 2.
- `dynasty_label` = Leprohon's section header verbatim: `Dynasty "0"` (note the double quotes around 0), `Dynasty 1`, `Dynasty 2`. Do NOT include the reign dates that follow in parentheses.
- `chapter` = `"Early Dynastic Period"` for every row in this chunk.
- `sequence_in_chapter_section` = the integer in Leprohon's own numbering (`1. IRY-HOR` → 1, `7. QAA` → 7). Resets at each dynasty section.
- `display_name` = Leprohon's SMALLCAP headword verbatim, title-cased. Examples:
  - `IRY-HOR` → `"Iry-Hor"` (hyphen preserved, both parts capitalised)
  - `KA` → `"Ka"`
  - `NARMER` → `"Narmer"`
  - `NY-<HOR>` → `"Ny-<Hor>"` (preserve the angle brackets verbatim — they are Leprohon's own "partial reading" marker)
  - `HATY-HOR` → `"Haty-Hor"`
  - `HORUS "A"` → `"Horus \"A\""` (the letter suffix and quote marks are part of the name)
  - `HORUS "PE"` → `"Horus \"Pe\""`
  - `DJET/WADJET` → `"Djet/Wadjet"` (slash preserved)
  - `KHASEKHEM/KHASEKHEMWY` → `"Khasekhem/Khasekhemwy"` (slash preserved)
- `alt_display_names` = for slashed homonyms, list each form individually. Examples:
  - `DJET/WADJET` → `["Djet", "Wadjet"]`
  - `KHASEKHEM/KHASEKHEMWY` → `["Khasekhem", "Khasekhemwy"]`
  - Single-form names → `[]` (empty list, NOT `null`).
- Name-type lists (`horus_names`, `nebty_names`, `golden_horus_names`, `throne_names`, `birth_names`, `later_cartouche_names`, `seth_names`):
  - Each is a list of 0 or more name entries. Empty list `[]` if Leprohon records none for that type.
  - Dispatch by Leprohon's per-row label:
    - `Horus:` (or `Horus 1:` / `Horus 2:`) → `horus_names`
    - `Two Ladies:` (or `Two Ladies 1:` / `Two Ladies 2:` / `Two Ladies 3:`) → `nebty_names`
    - `Golden Horus:` (or numbered variants) → `golden_horus_names`
    - `Throne:` (or numbered variants) → `throne_names`
    - `Birth:` (or numbered variants) → `birth_names`
    - `Later cartouche name:` (always has a trailing `*` in the transliteration or anglicised-gloss) → `later_cartouche_names`
    - `Seth name:` → `seth_names`
    - `Horus/Seth:` or `Horus/Seth 2:` → emit the entry to BOTH `horus_names` AND `seth_names`, with `is_variant: true` in each list and a `source_note` explaining the dual classification (see Khasekhemwy below).

## Name-entry format

Each Leprohon name line has three substantive parts:

```
Two Ladies: mn (men) The established one[^29]
             ^^^^    ^^^^^^^^^^^^^^^^^^^
             |       |
             |       English translation
             anglicised pronunciation
^^ transliteration
```

From this line, emit:

```json
{
  "transliteration": "mn",
  "anglicised": "men",
  "translation": "The established one",
  "variant_index": 1,
  "is_variant": false,
  "attested_in": [],
  "source_note": "..."
}
```

### Transliteration

- Copy the italicised text to the LEFT of the parenthetical gloss, character-for-character. Preserve Egyptological diacritics exactly: `ꜣ` (aleph), `ꜥ` (ayin), `ḥ` (h-with-dot-below), `ḫ` (h-with-breve-below), `ẖ` (h-with-line-below), `š` (s-with-hacek), `ṯ` (t-with-breve-below), `ḏ` (d-with-breve-below).
- If the transliteration contains angle brackets (e.g. `n(y)-<ḥr>`, `hꜣty-<ḥr>`), preserve them verbatim — they mark partially-reconstructed text.
- If the transliteration contains parentheses for optional glyphs (e.g. `n(y)`, `kh(a) sekhem nbwy htp(.w) im.f`), preserve them verbatim.
- Do NOT include the trailing `*` that marks Ramesside king-list forms — the schema's `later_cartouche_names` list name carries that signal; the asterisk itself is NOT in the transliteration.
- Do NOT include italicisation markdown (`*text*`) in the output — the transliteration field is a plain Unicode string.

### Anglicised

- Copy the text INSIDE the parentheses verbatim (e.g. `(iry-hor)` → `"iry-hor"`). Do not wrap in italics.
- Do NOT include the trailing `*` on later-cartouche forms.

### Translation

- Copy the English text to the RIGHT of the parenthetical gloss, up to but not including the footnote superscript number.
- Preserve inline quotes (e.g. `The "dreadful" one`).
- If Leprohon's translation includes a parenthetical qualifier (e.g. `The maces (of?) Horus`), preserve it verbatim.
- If Leprohon gives no translation (e.g. `Later cartouche name: tti (teti)*, Teti` — where "Teti" is both the anglicised *and* the translation), the `translation` field = `"Teti"`.
- When Leprohon preserves a later cartouche name that is a name-form itself without a semantic gloss (e.g. `*bhy/bhty (beby/bebty)*, Beby/Bebty`), the translation field holds the name as given, including the slash.

### variant_index

- Integer, 1-indexed position within the name-type list. `1` for the FIRST entry, `2` for the second, etc.
- When Leprohon writes `Horus 1:` / `Horus 2:` / `Two Ladies 1:` / `Two Ladies 2:` / `Two Ladies 3:`, the integer after the name-type label MUST match `variant_index` exactly. This preserves Leprohon's explicit authorial numbering.
- When Leprohon does NOT number the entries (e.g. multiple `Later cartouche name:` entries in a row — Adjib has 3, Aha has 2, Khasekhemwy has 2; none carry explicit numbers), use sequence index from the order Leprohon prints them: first = 1, second = 2, third = 3.
- Cross-list independence: `horus_names` variant_index counter is independent of `nebty_names` variant_index counter. Each list starts at 1.

### is_variant

- `false` for the FIRST entry in a given name-type list (`variant_index == 1`).
- `true` for every subsequent entry in the same list (`variant_index > 1`).
- This field is redundant with `variant_index > 1` but kept for parity with pharaoh.se's schema, so Phase-A can join the two sources without a field-shape conversion.

### attested_in

- A list of the PRIMARY king-list attestations from the per-entry footnote. Leprohon's footnotes often give `Abydos N`, `Turin N,M`, or `Saqqara N` — these are Ramesside king-list row numbers and go in `attested_in`.
- Format: preserve Leprohon's own notation verbatim. `"Abydos 2"`, `"Turin 2,12"`, `"Saqqara 1"`.
- Hedged attestations: preserve the hedge. `"Abydos 14; according to Kitchen (1993, 154), this refers to King Khasekhemwy"` is kept as a single string including the hedge clause.
- Only populate `attested_in` from footnotes that are attached to the SPECIFIC name entry via Leprohon's superscript numbering. If a king's footnote list has attestation data for entry 3 but not entry 1, only entry 3's `attested_in` is populated.
- `[]` (empty list) when the name entry has no footnote or the footnote contains only scholarly commentary (Gauthier, von Beckerath, etc.) with no Abydos/Turin/Saqqara citation.

### source_note

- Non-attestation scholarly commentary from the per-entry footnote: Gauthier references, von Beckerath references, reading debates, etymology discussions, Kaplony / T. A. H. Wilkinson / Jiménez-Serrano cross-references, Baud and Dobrev mentions, etc.
- Verbatim from Leprohon's footnote text, excluding the footnote number itself.
- When the footnote has both scholarly discussion AND a king-list citation, populate `attested_in` with the king-list citation AND `source_note` with the scholarly discussion. Do not double-count.
- `null` when the footnote is empty, absent, or contains ONLY the king-list citation already captured in `attested_in`.
- Short hedges like `(?)` inline in the transliteration or translation stay in those fields — they're part of Leprohon's orthographic choice, not the footnote.

## Source citation

```json
"source_citation": {
  "book": "Leprohon 2013",
  "edition": "SBL Writings from the Ancient World 33",
  "printed_page": <int>,
  "physical_pdf_page": <int>
}
```

- `printed_page` = the running-header printed page number where the ENTRY'S HEADWORD (`N. NAME` line) appears. For `1. IRY-HOR` this is printed 22 (physical 43). Not the page where the entry's last footnote appears; not the page where the last name entry spills over to.
- `physical_pdf_page` = `printed_page + 21` for every row in this chunk. (Verified offset; see `transcribe.md` chunk log.)

## Special cases (spot hazards)

1. **`Horus "A"` / `Horus "Pe"` / other letter-tagged `HORUS` entries** (Dyn 0 entries 11, 12). The display_name includes the letter suffix and quote marks: `Horus "A"`, `Horus "Pe"`. The single name row is labelled `Horus:` as usual.

2. **Peribsen's Seth name** (Dyn 2 entry 7). Peribsen replaced his Horus name with a Seth name. The entry has `Seth name:` instead of `Horus:`. Emit to `seth_names`, NOT `horus_names`. `horus_names: []` for this king.

3. **Khasekhem/Khasekhemwy** (Dyn 2 entry 8). Multiple special handling:
   - Display name: `"Khasekhem/Khasekhemwy"` with `alt_display_names: ["Khasekhem", "Khasekhemwy"]`.
   - `Horus:` entry → normal, goes to `horus_names`, `is_variant: false`.
   - `Horus/Seth 2:` entry → emit to BOTH `horus_names` (with `is_variant: true`) AND `seth_names` (with `is_variant: false`, since it's the first entry in `seth_names`). Both copies should have `source_note` that explains: `"Horus/Seth 2 form: the king reconciled the Seth and Horus traditions; the serekh is topped by BOTH Horus and Seth animals. See the accompanying Two Ladies entries which repeat this dual form."`
   - `Two Ladies 1:` and `Two Ladies 2:` both repeat the Horus/Seth dual-form pattern. Emit both as `nebty_names` entries (`is_variant: false, true`) with the same dual-form `source_note`.
   - `Later cartouche name:` entries (`ḏꜣḏꜣy` and `bhy/bhty`) → `later_cartouche_names`.

4. **Khasekhemwy's Horus-name numbered variants.** Leprohon uses `Horus 1:` (simple `ḫꜥ šm`, "The powerful one has appeared") and `Horus 2:` (but the label printed is actually `Horus/Seth 2:` — the dual form). Emit `Horus 1:` as `horus_names[0]` with `is_variant: false`; emit `Horus/Seth 2:` as described above.

5. **Peribsen's Two Ladies and Throne entries.** Leprohon gives `Two Ladies: pr ib.sn (per ib.sen)` AND `Throne: pr ib.sn (per ib.sen)` — same transliteration and anglicised form, same translation `"(For whom) Their will has come forth"`. Emit both: one in `nebty_names`, one in `throne_names`. They happen to match textually; do not deduplicate across different name-type lists.

6. **Aha's Two Ladies with a note.** Leprohon's entry for Aha's Two Ladies name ends with a long footnote saying "I have included this entry for the sake of completeness, but it is likely that the hieroglyphs of the vulture and the cobra may not actually be part of Aha's titulary." Preserve this as `source_note` on the Two Ladies entry.

7. **Homonymous later cartouche names.** Some kings (Adjib, Den, Semerkhet, Qa'a) have multiple `Later cartouche name:` entries, each a different attested Ramesside-era form. Emit each as a separate entry in `later_cartouche_names`, in the order Leprohon prints them. Each entry's `is_variant` is `false` for the first, `true` for the rest.

8. **Qa'a's multi-form Two Ladies.** Leprohon gives `Two Ladies 1:`, `Two Ladies 2:`, `Two Ladies 3:` for Qa'a. Emit three `nebty_names` entries in that order (`is_variant: false, true, true`).

9. **Dyn 0 kings with ONLY a Horus name.** Entries 1–12 in Dyn 0 each have a single `Horus:` line and nothing else (one `Seth name:` never appears in Dyn 0). Every other name-type list is `[]`.

10. **Horwy's name.** Leprohon prints "The double falcon" — preserve the definite article.

11. **Ny-<Hor>'s brackets.** The transliteration is `n(y)-<ḥr>` (angle brackets around `ḥr`), the anglicised is `(ny-<hor>)`, and the translation is `"The one who belongs to <Horus>"`. Preserve every bracket verbatim.

12. **Sened's Birth name.** Dyn 2 entry 5 has `Birth:` (not `Throne:` or `Horus:`) — the only Early Dynastic Birth-name entry. Emit to `birth_names`. Leprohon's prefatory sentence notes "This Birth name is found on a few Dynasty 4 texts". The footnote's content goes in `source_note`.

13. **Sekhemib's Horus 2.** Dyn 2 entry 6 has `Horus 1:` (simple "sekhem-ib") and `Horus 2:` (longer form). Both go in `horus_names`, `is_variant: false, true`.

14. **Den's Horus name translation hedge.** Leprohon gives "The severer (of heads)" for Den's Horus name with the parenthetical "(of heads)" as part of the translation. Preserve verbatim: `"The severer (of heads)"`.

## Output

Sort the emitted rows by `(dynasty_number, sequence_in_chapter_section)`. Dyn 0 rows first (leprohon-0.01 → leprohon-0.12), then Dyn 1 rows (leprohon-1.01 → leprohon-1.07), then Dyn 2 rows (leprohon-2.01 → leprohon-2.08).

**Expected row count: exactly 27.** If you produce fewer than 25 or more than 29, re-read the chunk against the schema — you have either missed a king entry or (more likely) emitted one entry per name-type row instead of one row per king.

In your final response message, give a one-line summary: row count, plus any anomalies or ambiguities you flagged in `source_note` fields that a human reviewer should revisit. Under 80 words.
