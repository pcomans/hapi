# Extraction prompt — Leprohon 2013 chunk 3 (Chapter IV First Intermediate Period)

Pass this to **three** independent Claude Code subagents in parallel. Each agent writes its JSONL output to a distinct filename (`agent-{a,b,c}-fip.jsonl` per the multi-chunk pattern). The three outputs are then merged by `merge.py` via majority vote.

---

You are extracting structured king data from the pypdf+MdC-normalised text of Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, SBL Writings from the Ancient World 33. Ed. Denise M. Doxey.

**Input:** the deterministic pypdf+MdC chunk file at

`/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p70-p74-pypdf.md`

(Absolute path; the Read tool requires it.) This chunk covers physical PDF pages 70–74 = printed pages 49–53. It contains Chapter IV *First Intermediate Period*: **Dynasties 9–10a**, **Dynasties 9–10b**, and **Dynasty 11a**.

**Output:** write your final JSONL to

`/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/agent-{a|b|c}-fip.jsonl`

One JSON object per line. No trailing newline required, no preamble, no code fences.

## Prerequisite reading

Read `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/prompt.md` (chunk 1) AND `prompt-old-kingdom.md` (chunk 2) first — the schema, field semantics, and hazard catalogue defined there all carry over. The chunk-3 instructions below are DIFFERENCES and ADDITIONS; everything else stays the same.

## Schema additions for chunk 3

### Combined dynasty labels (`Dynasties 9–10a`)

Leprohon bundles Dynasties 9 and 10 into two combined sections because the Turin Canon treats them as one family and their reign-order is unrecoverable. Schema handling:

- `dynasty_number`: **integer lower bound**. Dynasties 9–10a → `9`. Dynasties 9–10b → `9`.
- `dynasty_label`: the full label **verbatim with Leprohon's en-dash `–` preserved**. Use `"Dynasties 9–10a"` and `"Dynasties 9–10b"` (en-dash U+2013, NOT an ASCII hyphen). This matches the README "verbatim" rule — the en-dash is Leprohon's own typography.
- `leprohon_id`: `leprohon-9-10a.NN` and `leprohon-9-10b.NN` — the hyphenated-range ID format uses an **ASCII hyphen** (not an en-dash) for regex/filesystem safety. Example: `leprohon-9-10a.01` for Khety I, `leprohon-9-10b.05` for Meryibre Khety (VIII). The merge.py sort key already handles this format.
- `chapter`: `"First Intermediate Period"` for all chunk-3 rows.

### Dynasty 11a

- `dynasty_number`: `11`
- `dynasty_label`: `"Dynasty 11a"`
- `leprohon_id`: `leprohon-11a.NN`
- `chapter`: `"First Intermediate Period"` (Leprohon places Dyn 11a in chapter IV FIP because its early rulers were contemporary with Dyn 10; the later Dyn 11b will be in chapter V MK, chunk 4)

### New name-type field: `later_horus_names`

Chapter IV introduces a new label: `Later Horus name:`. Leprohon uses this when a Horus name is a *post-hoc Ramesside / New Kingdom fabrication*, not a contemporary attestation. Example from Dyn 11a entry 1 (Mentuhotep I): `Later Horus name: tp ꜥ (tepy a),* "The ancestor"` with footnote 27 noting "This Horus name is a New Kingdom fabrication, found in the Karnak List."

Schema:

- Add a new top-level field `later_horus_names: []` to **every row** you emit (even rows with no such entry — include `"later_horus_names": []` so the schema shape is consistent).
- Entries in `later_horus_names` use the same 7-field schema as other name-type lists (`transliteration`, `anglicised`, `translation`, `variant_index`, `is_variant`, `attested_in`, `source_note`).
- The trailing `*` on a `Later Horus name:` entry (e.g. `tp ꜥ (tepy a),*`) signals the name's Ramesside-fabrication status and is *consumed by the field name* — do NOT preserve the `*` in the `transliteration` or `anglicised` fields. The field-name `later_horus_names` carries the signal.
- `source_note`: include the footnote text explaining the fabrication. For Mentuhotep I: `"Karnak List (Urk. IV, 608:14); per Leprohon fn. 27, this Horus name is a New Kingdom fabrication (cf. Postel 2004, 46)."`

### Combined `Throne and birth:` / `Throne and Birth:` label

Two Dyn 9–10 entries use this combined label (Dyn 9–10a #7 Khety IV; Dyn 9–10b #3 Khety VI). The same transliteration text serves as both prenomen and nomen because Leprohon cannot cleanly separate them in the fragmentary evidence.

- **Emit the entry in BOTH `throne_names` AND `birth_names`**, as separate entries with `variant_index: 1, is_variant: false` in each list.
- In the `source_note` of both copies: append `"Leprohon labels as 'Throne and Birth' — a combined prenomen/nomen where fragmentary evidence prevents separation."` (after any existing footnote commentary).

This follows the same dual-classification pattern as Khasekhemwy's `Horus/Seth 2` in chunk 1.

### Standalone `Cartouche:` label

One entry uses this label: Dyn 9–10a #5 Senen//// (`Cartouche: snn//// (senen///),*`). Leprohon uses `Cartouche:` when a cartouche-enclosed name cannot be classified as prenomen or nomen in the fragmentary evidence.

- **Emit to `birth_names` only** (not both). Rationale: a standalone cartouche with no `n-sw-bity` (nesu-bity) prefix most plausibly represents the king's personal name (nomen).
- In the `source_note`: include `"Leprohon labels as 'Cartouche' (cartouche-enclosed name of unclear prenomen/nomen classification)."`
- The entry also carries the Ramesside-only tag (see Asterisked-headword rules below — Senen//// has `5. s En En  ////*` in the SMALLCAP, i.e. asterisk is on the headword).

### Stub entry `/////` for Dyn 9–10a #2

Dyn 9–10a entry 2 is not a king at all — it's a placeholder for a destroyed name in the Turin Canon: `2. ///// (name missing in the Turin list [4,19])`. Leprohon preserves the numeric position because the Turin Canon row is counted, even though the name is unreadable.

Emit this as a row anyway, for sequence integrity:

```json
{
  "leprohon_id": "leprohon-9-10a.02",
  "dynasty_number": 9,
  "dynasty_label": "Dynasties 9-10a",
  "chapter": "First Intermediate Period",
  "sequence_in_chapter_section": 2,
  "display_name": "/////",
  "alt_display_names": [],
  "horus_names": [],
  "nebty_names": [],
  "golden_horus_names": [],
  "throne_names": [],
  "birth_names": [],
  "later_cartouche_names": [],
  "later_horus_names": [],
  "seth_names": [],
  "source_citation": {
    "book": "Leprohon 2013",
    "edition": "SBL Writings from the Ancient World 33",
    "printed_page": 50,
    "physical_pdf_page": 71
  }
}
```

## Asterisked-headword rules (carried over from chunk 2) — READ CAREFULLY

Leprohon's opening prose for Dyn 9–10a says:
> "Only five kings of this Herakleopolitan dynasty are known from contemporary monuments: Neferkare, Nebkaure Khety, Meryibre Khety, Merykare, and Wahkare Khety. ... their names will be followed by an asterisk."

meaning kings *without* asterisks on the headword are contemporarily attested; kings *with* asterisks are Ramesside-only.

**Dyn 9–10a** headword asterisks (per the chunk file — check each one):
- `1. [KHETY I]*` — Ramesside-only (tag with the canonical Ramesside-only source_note)
- `2. /////` — stub, see above
- `3. NEFERKARE (III)` — **no asterisk, contemporarily attested** (one of the five named in the opening prose, per footnote 6 "Turin 4,20" plus possible Mo'alla tomb inscription)
- `4. KHETY II*` — Ramesside-only
- `5. SENEN ////*` — Ramesside-only
- `6. [KHETY III]*` — Ramesside-only
- `7. [KHETY IV]*` — Ramesside-only
- `8. SHED ////*` — Ramesside-only
- `9. HU ////*` — Ramesside-only

**Dyn 9–10b**: Leprohon's opening prose explicitly says "The following kings ... are attested in contemporary records." **None carries an asterisk; none gets the Ramesside-only tag.**

**Dyn 11a**: All four rulers are contemporarily attested; no headword asterisks; none gets the Ramesside-only tag. *However*, the individual `Later Horus name:` entry for Mentuhotep I (`tp ꜥ*`) is itself Ramesside-fabricated — that signal is already captured by the `later_horus_names` field name and its source_note, NOT by tagging the king as Ramesside-only. **Do NOT tag Mentuhotep I as Ramesside-only — only his "Later Horus" name is fabricated, and the king himself is real and contemporarily attested.**

This is the inverse of the Dyn-8a lesson from chunk 2: there, the extraction prompt wrongly framed Dyn 8a as Ramesside-only and the agents correctly ignored it per constitutional rule 1. Here, the Dyn 9–10a section is *genuinely* mostly-Ramesside-only, so the tag applies to 8 of its 9 entries.

### Canonical Ramesside-only tag

Append to the first name entry's `source_note`:
```
"Ramesside-attested only — no contemporary attestation per Leprohon's headword asterisk."
```
(This phrasing matches `tests/test_sources_leprohon_titulary.py::RAMESSIDE_ONLY_TAG`.)

For bracket-reconstructed headwords (`[KHETY I]*`, `[KHETY III]*`, `[KHETY IV]*`): strip the brackets from `display_name` (`Khety I`, `Khety III`, `Khety IV`), but additionally append `"Leprohon marks this king's headword with square brackets, indicating a reconstructed name."` to the same source_note.

### Roman-numeral disambiguators

Dyn 9–10a and 9–10b use Roman numeral disambiguators extensively: `Khety I`, `Khety II`, ..., `Khety VII`, `Khety VIII`, and `Intef I/II/III` in Dyn 11a. Keep the roman numeral in `display_name` with a single space separator (`"Khety I"`, `"Intef II"`). Do not emit alt_display_names for roman-numeral variants — they're disambiguators, not alternate names.

For `Wahkare Khety (V)`, `Khety (VI)`, `Nebkaure Khety (VII)`, `Meryibre Khety (VIII)`: the Roman numeral is in parentheses because it's a cross-reference to the overall Khety-count across Dyn 9–10a+b. Keep it in `display_name`: `"Wahkare Khety (V)"`, `"Khety (VI)"`, `"Nebkaure Khety (VII)"`, `"Meryibre Khety (VIII)"`.

### Fragmentary name glyphs

Chunk 3 has extensive use of `////` (four-slash wildcards) and `[square brackets]` for partial / reconstructed readings. Preserve them verbatim in `transliteration`, `anglicised`, and `translation` — they're the author's positive assertion of "reading is fragmentary / partially hypothetical." Do not strip them.

Examples to preserve:
- `snn////` / `senen///` / `The (very) likeness [of ? ///]`
- `ẖty sꜣ? nfr kꜣ rꜥ` (from `6. [KHETY III]*`) — the `?` uncertainty mark stays
- `[Khety's son(?), Neferkare]`

## Expected row count

**Dynasties 9–10a: 9 rows** (1 stub + 8 kings including Neferkare III)
**Dynasties 9–10b: 6 rows**
**Dynasty 11a: 4 rows** (Mentuhotep I, Intef I, Intef II, Intef III)

**Total: 19 rows.** If you produce fewer than 17 or more than 21, re-read the chunk file and re-scan for missed entries or mis-parsed headers.

## Dyn 11a specifics

- **Mentuhotep I** (Dyn 11a #1): Emit `Later Horus name:` + `Birth:`. No other name types. The Birth name is extravagant: `it-nṯrw mnṯw-ḥtp(.w) ꜥꜣ mry sṯt nbt ꜣbw` with anglicised `it netjeru mentu hotep aa, mery Satet nebet Abu` and translation involving "The God's Father Mentuhotep ... the Great, beloved of Satet, mistress of Elephantine". Preserve the full transliteration, anglicised, and translation verbatim including parenthetical glosses and epithet chains.
- **Intef I, II, III**: Each has `Horus:` + `Birth:` only. No Two Ladies, Golden Horus, Throne, Later cartouche, Seth. Emit empty lists for those.

## Output ordering

Sort the emitted rows in your output file by the merge.py sort key order:
1. `leprohon-9-10a.01` through `leprohon-9-10a.09`
2. `leprohon-9-10b.01` through `leprohon-9-10b.06`
3. `leprohon-11a.01` through `leprohon-11a.04`

`merge.py` re-sorts anyway, but consistent ordering in your raw file makes disagreement diffs easier to read.

## Final response

In your final response message, give a one-line summary: row count per (sub-)dynasty (e.g. `"9-10a:9, 9-10b:6, 11a:4"`), highest footnote number seen, any transliteration-vs-anglicised disagreements or MdC edge cases you flagged, and confirmation that the stub row `leprohon-9-10a.02` was emitted. Under 100 words.
