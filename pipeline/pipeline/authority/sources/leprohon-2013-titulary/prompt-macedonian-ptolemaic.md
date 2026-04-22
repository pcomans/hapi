# Extraction prompt — Leprohon 2013 chunk 14 (Chapter X Macedonian + Ptolemaic Dynasties)

Pass this to **three** independent Claude Code subagents in parallel. Each agent writes to `agent-{a,b,c}-macedonian-ptolemaic.jsonl`.

---

You are extracting structured king data from Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, SBL WAW 33.

**Input:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/chunk-p196-p209-pypdf.md` — physical pp. 196–209 = printed 175–188. Contains Leprohon's Chapter X **Macedonian and Ptolemaic Dynasties**: three Macedonian rulers (Alexander the Great, Philip Arrhidaeus, Alexander II/IV) and the Ptolemaic line from Ptolemy I Soter through Ptolemy XV Caesarion — including the queens Cleopatra II (8a), Berenike (12), and Cleopatra VII (14).

**Output:** `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/leprohon-2013-titulary/raw/agent-{a|b|c}-macedonian-ptolemaic.jsonl`

## Prerequisite reading

Read prompts for chunks 1–13 first. Schema, hazard catalogue, and accumulated rules carry over. Chunk 14 introduces **one new schema pattern** (named-dynasty IDs — see below) and carries two recurring hazards worth re-reading (Persian-style Greek headwords from chunk 13; queen entries without throne titularies from earlier TIP chunks).

## Chunk-14 specifics

### Dynasty labels, chapter, IDs — **new pattern**

Chapter X has no canonical Egyptian dynasty number. Leprohon prints the two dynasty headings as "MACEDONIAN DYNASTY (332–305 B.C.E.)" and "PTOLEMAIC DYNASTY (305–30 B.C.E.)" without a Dyn-NN. **Do not fabricate** Dyn 32 / Dyn 33 numbers Leprohon did not print.

Field conventions for this chunk:

- `chapter: "Macedonian and Ptolemaic"` — new chapter value matching Leprohon's Chapter X title exactly (no "Dynasties" suffix; both are dynasties, so the plural is implicit).
- `dynasty_number: null` — both Macedonian and Ptolemaic rows.
- `dynasty_label: "Macedonian Dynasty"` for Macedonian rows; `"Ptolemaic Dynasty"` for Ptolemaic rows. Match the singular form; the section headings use singular ("MACEDONIAN DYNASTY", "PTOLEMAIC DYNASTY").
- `leprohon_id`:
  - Macedonian rows: `leprohon-macedonian.01` … `leprohon-macedonian.03` (Alexander, Philip, Alexander II/IV).
  - Ptolemaic rows: `leprohon-ptolemaic.NN` — `NN` is the two-digit Ptolemaic in-chapter-section sequence (1-indexed). See "Sequence numbering" below for the exact mapping — **Leprohon's in-section numbering is not 1…17 contiguously**.
- `sequence_in_chapter_section`: the numeric part of `NN` as an integer (standard across chunks). Resets to 1 at the start of each dynasty section.
- `stage_suffix: null` for every row. No multi-stage kings expected in Chapter X (verify).

The merge.py `_LID_RE` and `_sort_key` are already extended to accept these two slugs; the test `test_sort_key_orders_named_dynasties_after_numeric` guards the ordering.

### Sequence numbering for Ptolemies — transcribe Leprohon verbatim, do not renumber

Leprohon numbers Chapter X entries like this (verify against the chunk file — re-scan if your transcription disagrees):

Macedonian section:

1. Alexander the Great
2. Philip Arrhidaeus
3. Alexander II / Alexander IV

Ptolemaic section:

1.  Ptolemy I Soter
2.  Ptolemy II Philadelphus
2a. Arsinoe II (queen sub-entry, after Ptolemy II)
3.  Ptolemy III Euergetes
3a. Berenike II (queen sub-entry, after Ptolemy III)
4.  Ptolemy IV Philopator
5.  Ptolemy V Epiphanes
5a. Cleopatra I (queen sub-entry, after Ptolemy V)
6.  Ptolemy VI Philometor
7.  Ptolemy VII Neos Philopator
8.  Ptolemy VIII Euergetes II Tryphon
8a. Cleopatra II (queen sub-entry, after Ptolemy VIII)
9.  Ptolemy IX Philometor Soter II
10. Ptolemy X Alexander I
11. Ptolemy XI Alexander II (no hieroglyphic titulary attested)
12. Berenike (queen; chronologically Berenike III — Leprohon uses the bare headword, confirm against chunk file; only a Birth name with epithet)
13. Ptolemy XII Neos Dionysos (Auletes)
14. Cleopatra VII Philopator
15. Ptolemy XIII (no hieroglyphic titulary)
16. Ptolemy XIV (no hieroglyphic titulary)
17. Ptolemy XV Caesarion

### Queen sub-entries (2a / 3a / 5a / 8a) — stage-suffix, not the titulary-stage semantic

Leprohon labels four queens with a letter-suffix sub-entry inside the preceding Ptolemy's section — they reigned jointly with or adjacent to their husband/brother, and Leprohon tucks their titulary there rather than giving them a fresh main-number:

- 2a  Arsinoe II (after Ptolemy II Philadelphus)
- 3a  Berenike II (after Ptolemy III Euergetes)
- 5a  Cleopatra I (after Ptolemy V Epiphanes)
- 8a  Cleopatra II (after Ptolemy VIII Euergetes II Tryphon)

Each is a **separate person** from the Ptolemy they sit after — so this is NOT the titulary-stage convention from Dyn 11b/12/18 where the letter suffix marked the same king's successive titulary sets. But mechanically, the cleanest fit to Leprohon's own labelling is to use the `stage_suffix` slot to hold the `a`:

- `leprohon_id: "leprohon-ptolemaic.02a"` / `03a` / `05a` / `08a` — the `a` sits in the `stage_suffix` slot of the merge.py regex, which places the sub-entry row immediately after the parent Ptolemy (`08a` after `08`, before `09`).
- `stage_suffix: "a"` on each queen row (the only chunk-14 rows with a non-null stage_suffix).
- `sequence_in_chapter_section: 2 / 3 / 5 / 8` (per the existing rule — the numeric part, not the letter). These values therefore collide with the preceding Ptolemy's `sequence_in_chapter_section` — which is already how the schema works for multi-stage kings (`leprohon-12.01a` and `leprohon-12.01b` both have `sequence_in_chapter_section: 1`). Do NOT invent fresh sequence numbers.
- `dynasty_label: "Ptolemaic Dynasty"`, same as the parent Ptolemy.

This is a narrower interpretation of `stage_suffix` than "same king, successive titulary sets" — here it marks a co-regent sub-entry. The existing `test_stage_suffix_is_valid_letter_or_none` test accepts `"a"` so no schema change is needed.

### Rows with no attested hieroglyphic titulary

Entries 11 (Ptolemy XI Alexander II), 15 (Ptolemy XIII), 16 (Ptolemy XIV) are labelled "No royal titulary is attested in hieroglyphs" in Leprohon. Emit them anyway with all name-list fields as empty lists (`horus_names: []`, `nebty_names: []`, etc.) — same pattern as the Dyn 27 Persian placeholder rows (Xerxes II / Darius II / Artaxerxes II) in chunk 13. `display_name` is the headword Leprohon printed; `source_citation` populated; `alt_display_names: []` unless Leprohon prints a parenthetical.

### Greek / Persian-style headwords — display_name is the Greek form

Same convention as Persian kings in chunk 13: every Macedonian and Ptolemaic ruler has a Greek (Macedonian) name and Leprohon prints it in SMALLCAP Greek form, not Egyptian-form. `display_name` is the Greek form as printed — e.g. `Alexander the Great`, `Philip Arrhidaeus`, `Alexander II/IV`, `Ptolemy I Soter`, `Ptolemy VIII Euergetes II Tryphon`, `Cleopatra II`, `Cleopatra VII Philopator`. The Egyptian transliterated Birth name (e.g. `ꜣlksndrs`, `p(h)lpws`, `ptwlmys`, `ḳlwpdrꜣ`) goes in `birth_names`, not as `display_name`.

Leprohon also prints Greek epithet nicknames in quotes in the section heading — e.g. Ptolemy I Soter ("Savior"), Ptolemy II Philadelphus ("Brother-Loving"), Ptolemy XII Neos Dionysos Auletes ("Flute-Player"). These quoted epithets are header flavour, not alt display names; do NOT populate them in `alt_display_names` unless Leprohon gives them as a separate parenthetical alias. Standard non-Leprohon aliases (e.g. `Lagos`, `Lagides` for Ptolemy I; `Ochus` for Artaxerxes III) land via fix_rows post-pass with explicit attribution.

### Alexander II / IV — slashed headword

Leprohon's section heading is "ALEXANDER II / IV" (two numbers, one king — his Macedonian numbering is II, his pharaonic Egyptian numbering is IV). Treat the same as chunk-1 Djet/Wadjet and chunk-2 Netjerikhet/Djoser: `display_name: "Alexander II/IV"` (single slash, no spaces — match chunk-1/2 convention) and populate `alt_display_names: ["Alexander II", "Alexander IV"]` if the two forms are enumerable as independent headwords Leprohon uses (verify by scanning for "Alexander IV" in prose). If Leprohon uses only the combined form, leave `alt_display_names: []` and defer to fix_rows.

### Berenike (entry 12)

Queen with only a Birth name `iry-pꜣꜥtt wr(t)-ḥsw(t) birnikt` ("The hereditary princess who is great of praise, Berenike"). `display_name: "Berenike"`. All other name-list fields explicitly `[]`. If Leprohon prints "Berenike III" as the formal disambiguation, use `"Berenike III"` instead — scan the chunk file for the exact printed form.

### Cleopatra VII (entry 14)

Prolific queen — Leprohon typically gives her a substantial titulary. Expect Horus, Two Ladies, Throne, Birth entries with possible variants. Leprohon prints the section heading as `CLEOPATRA VII PHILOPATOR ("Father-Loving")`. `display_name: "Cleopatra VII Philopator"` (verify exact printed form).

### Sparse titularies + numbered name-types

Same conventions as chunks 5-13.

### No Ramesside-only tags

All Macedonian and Ptolemaic kings are contemporarily attested. Do NOT apply the Ramesside-only tag.

## Expected row counts

Conservative estimates (verify against chunk file; re-scan if your totals diverge materially):

- **Macedonian Dynasty:** 3 entries (Alexander, Philip, Alexander II/IV).
- **Ptolemaic Dynasty:** 21 entries — 17 base numbered Ptolemies (1 through 17, with 11/15/16 as empty-titulary placeholders) plus 4 queen sub-entries (2a Arsinoe II, 3a Berenike II, 5a Cleopatra I, 8a Cleopatra II). Sequence set: `01, 02, 02a, 03, 03a, 04, 05, 05a, 06, 07, 08, 08a, 09, 10, 11, 12, 13, 14, 15, 16, 17`.

**Total: 24 rows** (3 Macedonian + 21 Ptolemaic). If you produce fewer than 21 or more than 27, re-scan the chunk file before writing.

## Output ordering

Sort each agent's output by (dynasty slug, `sequence_in_chapter_section`, `stage_suffix`) — Macedonian rows first (01, 02, 03), then Ptolemaic rows interleaved with the four `a` sub-entries in Leprohon's printed order (01, 02, 02a, 03, 03a, 04, 05, 05a, 06, 07, 08, 08a, 09, 10, 11, 12, 13, 14, 15, 16, 17). merge.py re-sorts via `_sort_key` which places these slugs chronologically after every numeric dynasty and places each stage-suffixed row immediately after its numeric parent.

## Final response

One-line summary: row counts per dynasty, any Cleopatra VII titulary density notes, any surprising 8a / slashed-headword decisions you made while extracting. Under 100 words.
