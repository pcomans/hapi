# Leprohon 2013 — *The Great Name: Ancient Egyptian Royal Titulary*

Primary titulary authority for Hapi. Every reigning king from Dynasty 0 through the Ptolemaic period, with the full fivefold titulary (Horus, Two Ladies/Nebty, Golden Horus, Throne/prenomen, Birth/nomen) in Egyptological transliteration, anglicised pronunciation, and English translation, plus Ramesside-era "Later cartouche" king-list forms preserved as a separate attestation class.

## Citation

Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, edited by Denise M. Doxey. Writings from the Ancient World 33. Atlanta: Society of Biblical Literature. ISBN 978-1-58983-735-5 (paper), 978-1-58983-767-6 (cloth), 978-1-58983-736-2 (electronic). x + 280 pp.

- **Edition used:** first edition, 2013. SBL Writings from the Ancient World series, Theodore J. Lewis general editor.
- **PDF SHA-256:** `0a59c2763002c76fc7a17b4ff9f9e093f3dc1c887a537f75761de9fdf0ff3f5c` (also pinned in `transcribe.md`).
- **Source PDF held in `proprietary/books/Leprohon 2013 - The Great Name.pdf`, not committed.**

## Role in the authority architecture

Leprohon 2013 is the **primary titulary authority**. Per the 2026-04-19 egyptologist review and the MVP prioritization landed in PR #82:

- `sources/pharaoh-se/` is demoted to secondary / coverage-completeness cross-validator. Where Leprohon's canonical prenomen disagrees with pharaoh.se's primary, Leprohon wins for the canonical form. pharaoh.se's variant is retained as an alias when Leprohon lists it among his attested variants, and flagged for review when Leprohon does not.
- `proprietary/books/Beckerath 1999 - Handbuch Königsnamen 2nd ed.pdf` remains available as a tie-breaker for contested prenomina where Leprohon and pharaoh.se disagree but is not itself a Phase-0 transcription target (pharaoh.se is already Beckerath-saturated per the 2026-04-19 audit).

Scope pharaoh.se retains primacy over Leprohon:

- Ephemeral / contested kings Leprohon treats as non-canonical: the Abydos Dynasty (Woseribre Senebkay etc., Ryholt 1997 reconstructions), late Hyksos minor rulers, the Dyn-23 Theban parallel line in its fuller form, Roman emperors-as-pharaohs.
- Chronological / reign-date aggregation across multiple schools — Leprohon's focus is titulary, not chronology.

Phase A builds `rulers.json` by joining Leprohon's titulary-authoritative rows against pharaoh.se's coverage-authoritative rows; disagreements are flagged for review, not silently reconciled.

## Scope

Chapters II–X of the book, each covering one historical period:

| Chapter | Period | Printed pages | Physical-PDF pages | Chunk |
|---|---|---|---|---|
| II | Early Dynastic Period (Dyn 0–2) | 21–30 | 42–51 | chunk 1 (PR #83) + recovered p. 30 in chunk 2 |
| III | Old Kingdom (Dyn 3–8) | 31–48 | 52–69 | **chunk 2 (this PR)** |
| IV | First Intermediate Period (Dyn 9–11 early) | 49–53 | 70–74 | chunk 3 |
| V | Middle Kingdom (Dyn 11 late–12) | 54–80 | 75–101 | chunk 4 |
| VI | Second Intermediate Period (Dyn 13–17) | 81–92 | 102–113 | chunk 5 |
| VII | New Kingdom (Dyn 18–20) | 93–135 | 114–156 | chunks 6–9 (likely Dyn 18 / Dyn 19 / Dyn 20 splits) |
| VIII | Third Intermediate Period (Dyn 21–25) | 136–163 | 157–184 | chunk 10 |
| IX | Late Period (Dyn 26–31) | 164–174 | 185–195 | chunk 11 |
| X | Macedonian and Ptolemaic Dynasties | 175–188 | 196–209 | chunk 12 |

(Physical-PDF-page ranges for chunks 2+ will be verified at the chunk's first and last pages per the playbook — the +21 offset observed in chunk 1 may drift at part boundaries. Chapter lengths are nominal; final chunk count depends on kings-per-chapter density. Egyptologist estimate: ~10–14 PRs total, with Dyn 18 and Dyn 19 warranting one PR each given the density of attested prenomen variants per king.)

**In scope:**

- Every numbered king entry (e.g. `1. IRY-HOR`, `4. DEN`) in chapters II–X.
- Every name row under each king: `Horus:`, `Two Ladies:`, `Golden Horus:`, `Throne:`, `Birth:`, `Later cartouche name:`, `Seth name:`, and any multi-form variants (`Horus 1`, `Horus 2`, `Two Ladies 1`, `Two Ladies 2`, `Two Ladies 3`, etc.).
- Per-name transliteration (Egyptological diacritics preserved: ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ), anglicised pronunciation from Leprohon's parenthetical gloss, and English translation.
- Per-name attestation notes from Leprohon's footnotes (e.g. `Abydos 2`, `Turin 2,12`, `Saqqara 1`) where present — these are the concordance references that make Leprohon a *citable* authority rather than a flat list.

**Out of scope:**

- Chapter I (Introduction §§ 1–5.7, printed pp. 1–20) — methodology and title-discussion prose, no king entries.
- Appendix A (Index of Royal Names, pp. 189–229) — redundant with the chapter extractions.
- Appendix B (Alphabetical List of Kings, pp. 231–239) — ditto.
- Appendix C (Greek-Egyptian Equivalents, pp. 241–242) — covered in pharaoh.se's `alt_labels` for Ptolemaic-period kings; could be pulled in a later chunk if Phase-A surfaces a gap.
- Footnote bibliographic chains beyond the first attestation citation. Leprohon's footnotes often chain `Gauthier 1907, X; von Beckerath 1999, Y` secondary references; only the *primary* attestation (Turin/Abydos/Saqqara king-list numbers) is preserved in the `attested_in` field.
- Leprohon's prose framing paragraphs at the start of each chapter / dynasty. These are scholarly interpretation, not king-row data.

## Method — Claude Code subagent OCR + three-subagent structured extraction (ADR-017)

Per `docs/playbook-phase-0-ocr-transcription.md` and ADR-017:

1. **OCR:** Claude Code subagent transcribes this chunk's physical-page range into `raw/chunk-p42-p50.md`. Not committed (Layer-2 rights policy — the chunk contains verbatim narrative-prose framing paragraphs alongside the structured king entries, and cannot be pulled cleanly from the publisher's text layer the way Porter-Moss can).
2. **Structured extraction:** three independent Claude Code subagents read the chunk file and emit JSONL per the schema below to `raw/agent-{a,b,c}.jsonl`.
3. **Deterministic merge:** `merge.py` majority-votes per field across the three agents, writing `reconciled.jsonl` plus `merge-disagreements.txt`.
4. **LLM review:** `egyptologist-reviewer` subagent cross-checks the reconciled rows against the PDF, flags errors for `fix_rows.py` override application.
5. **Human sign-off (ADR-017 step 6):** deferred. The extract is provisional at the chunk level until a credentialed Egyptologist signs off in `human-review-<YYYY-MM-DD>-<chunk>.md`.

Multi-chunk source pattern: this is the first chunk. Subsequent chunks ship as separate PRs that reuse this source directory. Per-chunk prompts live at `prompt-<chunk-suffix>.md`; per-chunk agent outputs live at `raw/agent-{a,b,c}-<chunk-suffix>.jsonl`. Chunk 1 uses the default un-suffixed filenames (`prompt.md`, `raw/agent-{a,b,c}.jsonl`) per the multi-chunk-pattern convention. See `docs/playbook-phase-0-ocr-transcription.md` § "Multi-chunk source pattern".

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
      "is_variant": false,
      "attested_in": [],
      "source_note": null
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

### Field semantics

- `leprohon_id`: `"leprohon-{dynasty_number}.{NN}"` where NN is a zero-padded 2-digit sequence within the dynasty section (01, 02, ..., 12). Dynasty 0 uses `0` as the prefix. Within-chapter ordering follows Leprohon's own numbering (`1. IRY-HOR`, `2. KA`, ...).
- `dynasty_number`: integer 0, 1, 2, ..., 31. `0` for Dyn 0; explicit (not null) for Ptolemaic rulers (mapped to dynasty `33` by convention consistent with pharaoh.se).
- `dynasty_label`: Leprohon's own label verbatim, including the quotation marks on "Dynasty '0'" and the roman-numeral chapter label. `Dynasty "0"`, `Dynasty 1`, `Dynasty 2`, ..., `Macedonian Dynasty`, `Ptolemaic Dynasty`.
- `chapter`: Leprohon's chapter title. For Early Dynastic, `"Early Dynastic Period"`.
- `sequence_in_chapter_section`: the integer in Leprohon's own numbering (`1.`, `2.`, etc.). Resets at each dynasty section within a chapter.
- `display_name`: the SMALLCAP headword from Leprohon verbatim, title-cased (e.g. `IRY-HOR` → `Iry-Hor`, `DJET/WADJET` → `Djet/Wadjet`). Slash-separated homonyms are preserved in the display name; both forms are also populated in `alt_display_names`.
- `alt_display_names`: for slashed homonyms (`Djet/Wadjet`, `Khasekhem/Khasekhemwy`), list each form individually so Phase A can match against either. Empty list for single-form names.
- `horus_names` / `nebty_names` / `golden_horus_names` / `throne_names` / `birth_names` / `later_cartouche_names` / `seth_names`: lists of name entries. Empty list if Leprohon records none.
- Each name entry:
  - `transliteration`: the italicised transliteration in Leprohon's leftmost position, with Egyptological diacritics preserved verbatim (ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ). Substitution characters (3, c, h, etc.) that arise in broken PDF text layers are a *failure mode* and must be corrected from the PDF's visual rendering.
  - `anglicised`: Leprohon's parenthetical gloss in the middle position (e.g. `(iry-hor)`, `(ka)`, `(nar mer)`).
  - `translation`: Leprohon's English translation in the rightmost position, excluding trailing footnote superscripts.
  - `is_variant`: `false` for the first entry in a name-type list, `true` for subsequent variants (`Horus 1` → false, `Horus 2` → true; likewise `Two Ladies 1/2/3`).
  - `attested_in`: list of primary attestation citations — the Ramesside king-list numbers Leprohon gives in the per-entry footnote. Formats: `"Abydos 2"`, `"Turin 2,12"`, `"Saqqara 1"`, sometimes with hedges (`"Abydos 14; according to Kitchen (1993, 154), this refers to King Khasekhemwy"`). Empty list if Leprohon gives no king-list citation for this specific name entry (common for primary Horus/Nebty/Throne entries; near-universal for `later_cartouche_names`).
  - `source_note`: non-attestation scholarly commentary from the same footnote when present, e.g. `"Gauthier 1907, 3–4, 29–30; von Beckerath 1999, 38–39"`. `null` when the footnote carries only attestation data (already captured in `attested_in`) or is absent entirely.
- `source_citation.printed_page`: Leprohon's running-header printed page number for the ENTRY'S HEADWORD — the page where the SMALLCAP `N. NAME` line appears. Not the footnote page.
- `source_citation.physical_pdf_page`: the physical PDF page number for the same headword.

### Hazards (agent pitfalls)

- **Later cartouche asterisks.** Leprohon marks Ramesside-era king-list forms with a trailing `*` (e.g. `tti (teti)*`, `mry p biꜣ (mer pe biai)`). Do not drop the asterisk class — these go in `later_cartouche_names`, not `birth_names`. The asterisk itself is NOT preserved in the transliteration or anglicised fields; the schema field name carries the attestation-class signal.
- **Footnote vs attestation distinction.** The per-entry footnote often has TWO pieces: a scholarly source citation (Gauthier/von Beckerath/Wilkinson) AND the primary attestation (Abydos/Turin/Saqqara number). Split them: `attested_in` gets only the king-list citations; `source_note` gets the scholarly chain.
- **Multi-form variants.** When Leprohon numbers a name-type (`Horus 1`, `Horus 2`), both forms are attested variants of the same name class. Emit them as two entries in the same list, with `is_variant: false, true`. When Leprohon writes `Two Ladies 1`, `Two Ladies 2`, `Two Ladies 3`, emit three entries. The `is_variant` flag matches the `false`-for-first, `true`-for-rest convention pharaoh.se uses.
- **Peribsen's `Seth name`.** Dyn-2 king Peribsen replaced his Horus name with a Seth name — one of the few such cases in all of Egyptian history. This goes in `seth_names`, not `horus_names`. Do not coerce it into the Horus slot.
- **Khasekhem/Khasekhemwy `Horus/Seth 2`.** Dyn-2 king Khasekhemwy reconciles the Seth and Horus traditions; one of his name-form entries is labelled `Horus/Seth 2`. Emit this as an entry in both `horus_names` and `seth_names` (duplicated across lists, since it is genuinely both). `is_variant` tracks position *within each list*: in `horus_names` the entry is `is_variant: true` (it is the second Horus entry, following the plain `Horus: ḫꜥ sḫm`); in `seth_names` it is `is_variant: false` (it is the only / first Seth entry). The `variant_index` follows the same per-list rule (`horus_names[1].variant_index == 2`, `seth_names[0].variant_index == 1`). Include a `source_note` in both copies explaining the dual classification.
- **Hedges in attestations.** Leprohon hedges some attestations with `(?)` or a follow-on clause (`Abydos 14; according to Kitchen (1993, 154), this refers to King Khasekhemwy`). Preserve the full hedge verbatim in `attested_in` — do not strip to just the bare number.
- **Homonym slashes.** `Djet/Wadjet`, `Khasekhem/Khasekhemwy`: keep the slash verbatim in `display_name`, split into individual forms in `alt_display_names`. Do not pick one as canonical — that decision is Phase-A's, not extraction's.
- **Bracket-hedged name glyphs.** Leprohon encodes partially-reconstructed names with angle brackets: `n(y)-<ḥr>` (`ny-<hor>`), `hꜣty-<ḥr>` (`haty-<hor>`). Preserve the brackets verbatim — they are the author's positive assertion of "reading is partially hypothetical."

## Rights statement

Transformative scholarly extraction for a cross-museum provenance index. The committed artifact is `reconciled.jsonl` — a per-king structured fact table (titulary strings, dynasty numbers, king-list concordances, page citations). Leprohon's narrative prose, footnote discussion chains, and book layout are deliberately not extracted. The project's working assumption is that this extract is a fact compilation rather than a derivative of the source's protectable expression; under the Anglo-American copyright tradition following *Feist v. Rural* (499 U.S. 340, 1991), raw facts are uncopyrightable. The US/EU *sui generis* database right is read not to reach fact-level extractions of the sort committed here.

Per the playbook's Rights policy § Interpretive facts are still facts, but cite them as such: Leprohon's choice of *canonical* anglicised form for each king, and the inclusion or exclusion of particular attested variants, is scholarly judgment. Each row's `display_name` and `alt_display_names` fields should be read as "per Leprohon 2013" when they are used in Phase-A normalisation — that attribution belongs in the `rulers.json` authority's `_source` block when Leprohon is consumed, not in each reconciled row.

The source PDF is held in `proprietary/books/Leprohon 2013 - The Great Name.pdf`; it is not committed to this repository. No verbatim prose OCR of Leprohon's scholarly discussion is committed either — the `raw/chunk-*.md` OCR files are gitignored and function as local working state.

## Known gaps / deferred work

- **Greek-Egyptian equivalents (Appendix C).** Not transcribed in this source; for Ptolemaic-period kings the Greek form is picked up from pharaoh.se's `alt_labels` instead. If Phase-A surfaces a Ptolemaic queen where Leprohon-chapter-X and pharaoh.se disagree on the Greek alias, revisit Appendix C.
- **Bibliography (pp. 243–260), Concordances (pp. 269+), and Indexes (pp. 261–267).** Not transcribed. These are working-scholar cross-references, not primary titulary data.
- **Human Egyptologist sign-off.** Per ADR-017 step 6, a credentialed reviewer walking a sample of rows against the PDF has NOT been performed. The extract is provisional at the chunk level until that happens; the `egyptologist-reviewer` subagent does NOT satisfy this. Log the future human-review pass in `human-review-<YYYY-MM-DD>-<chunk>.md`.

## Running the pipeline

See `transcribe.md` for the per-chunk OCR/extraction/merge/review sequence. Single command to materialise the merge step for chunk 1:

```bash
cd pipeline && uv run python pipeline/authority/sources/leprohon-2013-titulary/merge.py
```

Writes `reconciled.jsonl` and `merge-disagreements.txt` next to `merge.py`.
