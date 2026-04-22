# Extraction prompt — Leprohon 2013 chunk 14 (Chapter X Macedonian and Ptolemaic Dynasties)

Pass this to **three** independent Claude Code subagents in parallel. Each agent writes to `agent-{a,b,c}-macedonian-ptolemaic.jsonl`.

---

You are extracting structured king data from Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, SBL WAW 33.

**Input:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p196-p209-pypdf.md` — physical pp. 196–209 = printed 175–188. Contains Leprohon's Chapter X: the **Macedonian Dynasty** (3 kings: Alexander the Great, Philip Arrhidaeus, Alexander IV) followed by the **Ptolemaic Dynasty** (17 entries: Ptolemy I through Ptolemy XV Caesarion, with Berenike inserted as entry 12). This is the final chapter of Leprohon's titulary survey.

**Output:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/agent-{a|b|c}-macedonian-ptolemaic.jsonl`

## Prerequisite reading

Read prompts for chunks 1–13 first (`prompt.md` + `prompt-*.md` in this directory), plus the source `README.md` for schema. Schema, hazard catalogue, and accumulated rules carry over. Chunk 14 introduces no new schema fields but does introduce the Macedonian/Ptolemaic dynasty-number convention below.

## Chunk-14 specifics

### Dynasty numbers, labels, chapter, IDs

The Macedonian and Ptolemaic dynasties sit outside the standard 1–31 numbering. Per the source `README.md` schema convention:

- **Macedonian Dynasty** rows: `dynasty_number: 32`, `dynasty_label: "Macedonian Dynasty"`, `chapter: "Macedonian and Ptolemaic Dynasties"`, IDs `leprohon-32.01` / `leprohon-32.02` / `leprohon-32.03`.
- **Ptolemaic Dynasty** rows: `dynasty_number: 33`, `dynasty_label: "Ptolemaic Dynasty"`, `chapter: "Macedonian and Ptolemaic Dynasties"`, IDs `leprohon-33.01` through `leprohon-33.17` (the merge.py `_sort_key` accepts arbitrary integer dynasty numbers, so the two-digit `32` / `33` prefix is fine).

The README's rationale that this convention is "consistent with pharaoh.se" is itself slightly misleading (pharaoh.se uses `dynasty_number: null` for both dynasties), but the integer convention has been the Leprohon-local choice from chunk 1 and is what `dynasty_number` carries throughout the rest of `reconciled.jsonl`. Stay consistent.

`stage_suffix`: Several Ptolemies and the Macedonian kings have multi-stage titularies announced by the in-text labels `Original titulary`, `Later titulary`, `Second titulary`, etc. (for example, Ptolemy IV's `Later titulary` after his accession festival; Alexander the Great's `Later titulary` per his Karnak Temple cartouche). Where Leprohon explicitly marks a king with two or more stages, emit one row per stage with the conventional `stage_suffix: "a"` for the first / "Original" titulary and `"b"` (etc.) for the next. Where Leprohon prints only a single titulary set (no `Original titulary` / `Later titulary` heading), `stage_suffix: null`. Multi-stage rows share the same `sequence_in_chapter_section` integer (e.g. Ptolemy IV stage a and stage b both have `sequence_in_chapter_section: 4`); the stage letter alone disambiguates the row IDs.

### Letterspacing artifact in headwords (critical)

The pypdf text layer for chapter X renders SMALLCAP headwords with intra-word spacing and lower-case-first-letter artifacts. Examples from the chunk file:

- `1. a l EXan DEr  t HE g r Eat 3` → king 1, display name **Alexander the Great**.
- `1. Ptol Emy  i s ot Er  (“s a Vior ”) 17` → Ptolemy 1, display name **Ptolemy I Soter**.
- `13. Ptol Emy  Xii n Eos  Dionysos  a ul Et Es  (“f lut E-Play Er ”)51` → Ptolemy 13, display name **Ptolemy XII Neos Dionysos Auletes**.

To denoise: collapse runs of intra-word whitespace, fold the lowercase-first-letter pattern back to title case, drop the trailing footnote-superscript digit and any trailing parenthetical Greek-meaning gloss (the gloss like `("Savior")` is Leprohon's English translation of the epithet, not a separate alias — see below). Verify each denoised headword by cross-checking the standard Greek/Manetho form for that king. **Do not** copy the letterspaced PDF text verbatim into `display_name`.

### Greek epithet glosses are not aliases

Each Ptolemaic headword carries a translation of the Greek epithet in parentheses: `Ptolemy I Soter ("Savior")`, `Ptolemy II Philadelphus ("Brother-Loving")`, `Ptolemy III Euergetes ("Benefactor")`, `Cleopatra VII Philopator ("Father-Loving")`. **These are English glosses of the Greek epithet that already appears in the display name, not alternative names for the king.** Drop them from `display_name` and from `alt_display_names`. `alt_display_names` for Ptolemaic / Macedonian kings stays empty — Phase A consumers needing the Greek-epithet translation can read it from the source PDF; we do not duplicate translation strings in this layer.

### Alexander vs Alexander IV vs Alexander II

Leprohon's three Macedonian kings are typeset slightly inconsistently in the pypdf output. The headwords are:

- `1. ALEXANDER THE GREAT` (Alexander III of Macedon, 332–323 BCE).
- `2. PHILIP ARRHIDAEUS` (Alexander's half-brother, 323–317 BCE).
- `3. ALEXANDER III/IV` or `ALEXANDER IV` (Alexander's son, 316–304 BCE — Leprohon's prose preamble at the chapter top says "Alexander II", but his actual SMALLCAP headword is `Alexander III/IV` or similar — read the chunk file to disambiguate, do not infer).

For king 3 specifically, follow the chunk-1 slashed-homonym rule: if the headword reads `Alexander III/IV`, set `display_name: "Alexander III/IV"` and populate both forms in `alt_display_names: ["Alexander III", "Alexander IV"]`. If the headword reads only `Alexander IV`, `display_name: "Alexander IV"` and `alt_display_names: []`. Read the chunk file before committing.

### Berenike interpolation

Ptolemaic entry 12 is **Berenike** (Berenike III, the daughter of Ptolemy IX who briefly ruled in 81 BCE between Ptolemy XI and Ptolemy XII). Leprohon places her at slot 12 within the Ptolemaic numbering, so her ID is `leprohon-33.12` with `sequence_in_chapter_section: 12` and `display_name: "Berenike"`. The subsequent Ptolemy XII / XIII / XIV / XV correspond to slots 13 / 15 / 16 / 17, with Cleopatra VII Philopator at slot 14. Verify against the chunk file.

### Egyptian transliteration of Greek-named kings

The Birth (`Birth:`) name for each Macedonian and Ptolemaic king is the Egyptian-language phonetic transcription of the Greek name (`ꜣlksindrs` for Alexander, `pjwlmjs` for Ptolemy, `klwptr` for Cleopatra, etc.). These belong in `birth_names` per the standard schema — `display_name` carries the Greek/Latinate form, the Egyptian phonetic form lives in `birth_names[i].transliteration`. Do not flip the two.

### Multi-stage titularies

When a king's section is internally divided by Leprohon's headings `Original titulary`, `Later titulary`, `Second titulary`, etc., emit one row per titulary stage per the chunk-1 convention (Mentuhotep II's a/b/c stages were the prototypical case). Each stage carries its own full cross-name-type titulary; do not merge stages into a single row. Confirmed multi-stage cases in this chunk include at least Alexander the Great (Original + Later) and Ptolemy IV (Original + Later); read the chunk file for the full list. Single-titulary kings (no explicit "Original" heading) get one row with `stage_suffix: null`.

### Sparse titularies + numbered name-types

Same conventions as chunks 5–13. `is_variant: false` for the first entry in a name-type list, `true` for subsequent variants (`Horus 1` → false, `Horus 2` → true, etc.). Asterisks on individual name entries follow the chunk-4 convention — they stay in their originating name-type list with a per-entry `source_note` flagging later-attestation provenance.

### No Ramesside-only tags

All Macedonian and Ptolemaic kings are contemporarily attested. Do NOT apply the Ramesside-only tag.

### `attested_in` and `source_note`

Per chunk-1 conventions: per-entry footnotes mix scholarly source citations (Gauthier 1916, von Beckerath 1999, Hölbl 2001) with primary attestation citations (specific monuments, e.g. "From a stela at Buto", "From the temple of Edfu"). Split them: `attested_in` gets only the primary attestation citations (in this chunk these are usually monument references rather than Ramesside king-list numbers); `source_note` gets the scholarly chain. Where Leprohon's footnote is purely scholarly with no monument reference, `attested_in: []` and the citation goes in `source_note`.

## Expected row counts

- **Macedonian Dynasty:** 3 kings → 3 single-stage rows OR more if any king has multi-stage titularies (Alexander the Great is at minimum a 2-stage candidate, so could be 4–5 total Macedonian rows).
- **Ptolemaic Dynasty:** 17 entries (Ptolemies I–XII, Berenike at slot 12, Cleopatra VII at slot 14, Ptolemies XIII–XV) → 17 single-stage rows OR more if any king has multi-stage titularies.

**Total: ~20 rows minimum, possibly up to ~25 if multi-stage emission is dense.** If you produce fewer than 18 or more than 30, re-scan.

## Output ordering

Sort by (`dynasty_number`, `sequence_in_chapter_section`, `stage_suffix`). merge.py re-sorts.

## Final response

One-line summary: row count per dynasty, multi-stage cases observed, headword denoising notes (any king where the letterspaced PDF text was ambiguous). Under 100 words.
