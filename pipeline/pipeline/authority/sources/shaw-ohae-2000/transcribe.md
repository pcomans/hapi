# Transcription method — Shaw 2000

Reproducible protocol. A reviewer should be able to run these steps from the source PDF and arrive at the same `reconciled.jsonl`.

## Inputs

1. `proprietary/books/Shaw 2000 - Oxford History of Ancient Egypt.pdf` — scanned book PDF (not committed to the public repo). SHA-256 `080a7d0e0dd9d3e19a65d0c20f031f66ee8855dbbb018bd0a5eac4534b05d83f`.
2. `proprietary/books/Shaw 2000 - Oxford History of Ancient Egypt.txt` — Internet Archive OCR plain-text extract of the same scan (not committed). Internet Archive identifier `oxfordhistoryofa0000unse`.
3. `raw/chapter-banners.txt` (committed) — the thirteen chapter-banner blocks transcribed verbatim from the OCR, with OCR artifacts preserved in square brackets. This is the auditable record a reviewer can check without access to the PDF.

## Pages consulted

- **Table of Contents (pp. v–vi):** lists all fifteen chapters with chapter titles, BCE date ranges, and starting page numbers.
- **Each chapter's opening banner:** the chapter-number / title / date block, located in the OCR `.txt` by grepping for the chapter title stub (e.g. `^The Naqada Period`). Thirteen banners verified; see `raw/chapter-banners.txt`.
- **Midant-Reynes (ch 3, pp. 42–43):** two sentences from the chapter body quoted in `raw/chapter-banners.txt` to attest the Naqada I / Naqada II BCE boundaries included as sub-periods on the chapter 3 row.

## Extraction rules

1. **One row per chapter** where the chapter banner states a single BCE date range. This gives thirteen rows: chapters 2–10 and 12–15.
2. **Banner is the primary source.** Chapter-body prose is consulted only for explicit BCE sub-period breakdowns stated in the opening chronology section (currently, only Midant-Reynes on Naqada I/II — see `sub_periods` rule in `README.md`).
3. **Date conversion:**
   - `c.700, 000-4000 bc` → `date_range_start_bce: -700000`, `date_range_end_bce: -4000`, `date_qualifier: "c."` (the OCR preserves a stray space; the PDF prints `c.700,000-4000 bc`)
   - `c.4000-3200 bc` → `-4000`, `-3200`, `"c."`
   - `1069-664 bc` (no `c.`) → `-1069`, `-664`, `date_qualifier: null`
   - `30 bc-ad 395` → `-30`, `395`, `null`
4. **Exclude chapters** 1 (Introduction — TOC page `i`, Roman-numeral front matter, no BCE range) and 11 (Egypt and the Outside World — thematic essay, no BCE range in banner).
5. **Page citation** = the page number printed at the top of the chapter's opening-banner page. All thirteen were spot-checked in the scanned PDF; every chapter opens on the TOC-stated page.
6. **Edition string** is identical on every row: `"OUP 2003 paperback (= 2000 hardback), ISBN 978-0-19-280458-7"`.

## Chapter banner list

| Ch | Banner (as printed) | Page | Author(s) |
|---:|---|---:|---|
| 2 | Prehistory: From the Palaeolithic to the Badarian Culture (c.700,000-4000 bc) | 16 | Hendrickx & Vermeersch |
| 3 | The Naqada Period (c.4000-3200 bc) | 41 | Midant-Reynes |
| 4 | The Emergence of the Egyptian State (c.3200-2686 bc) | 57 | Bard |
| 5 | The Old Kingdom (c.2686-2160 bc) | 83 | Malek |
| 6 | The First Intermediate Period (c.2160-2055 bc) | 108 | Seidlmayer |
| 7 | The Middle Kingdom Renaissance (c.2055-1650 bc) | 137 | Callender |
| 8 | The Second Intermediate Period (c.1650-1550 bc) | 172 | Bourriau |
| 9 | The 18th Dynasty before the Amarna Period (c.1550-1352 bc) | 207 | Bryan |
| 10 | The Amarna Period and the Later New Kingdom (c.1352-1069 bc) | 265 | Van Dijk |
| 12 | The Third Intermediate Period (1069-664 bc) | 324 | Taylor |
| 13 | The Late Period (664-332 bc) | 364 | Lloyd |
| 14 | The Ptolemaic Period (332-30 bc) | 388 | Lloyd |
| 15 | The Roman Period (30 bc-ad 395) | 414 | Peacock |

## Normalisation notes

- Shaw uses lowercase `bc` / `ad`; this is preserved in `chapter_title` verbatim.
- Shaw's TOC and body text use ASCII hyphen-minus in date ranges (e.g. `c.4000-3200 bc`), not en-dash. `chapter_title` preserves the hyphen verbatim — no dash normalisation is applied.
- The `period_name` field is the bare period name without qualifier or date — e.g. `"Naqada Period"` not `"The Naqada Period (c.4000-3200 bc)"`. See `README.md` for the convention's scope and the two conflation cases (Ch 9, Ch 10) flagged for Phase A.
- No diacritics appear in Shaw's chapter banners, so no Egyptological transliteration handling is needed for this source.

## Verification

The row-level field values are asserted by `pipeline/tests/test_sources_shaw_ohae.py` against all populated fields on five sampled rows (rule 5). A structural citation test in `tests/test_structure.py` (added when all eleven sources land) will verify every row carries `source_citation.page` and `source_citation.edition`.
