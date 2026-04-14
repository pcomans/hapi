# Transcription method — Shaw 2000

Reproducible protocol. A reviewer should be able to run these steps from the source PDF and arrive at the same `reconciled.jsonl`.

## Inputs

1. `proprietary/books/Shaw 2000 - Oxford History of Ancient Egypt.pdf` — scanned book PDF (not committed to the public repo).
2. `proprietary/books/Shaw 2000 - Oxford History of Ancient Egypt.txt` — Internet Archive OCR plain-text extract of the same scan (not committed).

## Pages consulted

- **Table of Contents (pp. v–vi):** lists all fifteen chapters with chapter titles, BCE date ranges (in the form `(c.4000-3200 bc)`), and starting page numbers.
- **Each chapter's opening banner:** verified against the Internet Archive OCR `.txt` by locating the chapter-number / title / date block that precedes the author attribution (e.g. `3 | The Naqada Period | (c.4000-3200 bc) | BEATRIX MIDANT-REYNES`). All twelve banners match the TOC entries character-for-character modulo OCR noise (e.g. ch 5 OCR renders `"(C. 2686-2l6o BC)"` — lowercase-L-for-1 and lowercase-O-for-0 — where the PDF prints `(c.2686-2160 bc)`).
- **Page numbers** in the `source_citation.page` field come from the printed page numbers at the top of each chapter's opening page, as given in the TOC and corroborated by the OCR page-number markers in the `.txt`.

## Extraction rules

1. **One row per chapter** where the chapter banner states a single BCE date range.
2. **Chapter banner only.** Sub-periods (Naqada I/II, Early/Late Ramesside, etc.) are discussed in chapter bodies, not banners; they are **not** transcribed here.
3. **Date conversion:**
   - `c.4000-3200 bc` → `date_range_start_bce: -4000`, `date_range_end_bce: -3200`, `date_qualifier: "c."`
   - `1069-664 bc` (no `c.`) → start/end as above, `date_qualifier: null`
   - `30 bc-ad 395` → `date_range_start_bce: -30`, `date_range_end_bce: 395`, `date_qualifier: null`
4. **Exclude chapters** 1 (Introduction), 2 (Prehistory — no single BCE range in banner), and 11 (Egypt and the Outside World — thematic).
5. **Page citation** = the page number printed at the top of the chapter's opening-banner page. These correspond to the TOC.
6. **Edition string** is identical on every row: `"OUP 2003 paperback (= 2000 hardback), ISBN 978-0-19-280458-7"`.

## Chapter banner list (verified from PDF)

| Ch | Banner (as printed) | Page |
|---:|---|---:|
| 3 | The Naqada Period (c.4000-3200 bc) | 41 |
| 4 | The Emergence of the Egyptian State (c.3200-2686 bc) | 57 |
| 5 | The Old Kingdom (c.2686-2160 bc) | 83 |
| 6 | The First Intermediate Period (c.2160-2055 bc) | 108 |
| 7 | The Middle Kingdom Renaissance (c.2055-1650 bc) | 137 |
| 8 | The Second Intermediate Period (c.1650-1550 bc) | 172 |
| 9 | The 18th Dynasty before the Amarna Period (c.1550-1352 bc) | 207 |
| 10 | The Amarna Period and the Later New Kingdom (c.1352-1069 bc) | 265 |
| 12 | The Third Intermediate Period (1069-664 bc) | 324 |
| 13 | The Late Period (664-332 bc) | 364 |
| 14 | The Ptolemaic Period (332-30 bc) | 388 |
| 15 | The Roman Period (30 bc-ad 395) | 414 |

## Normalisation notes

- Shaw uses lowercase `bc` / `ad`; this is preserved in `chapter_title` verbatim (with en-dash normalisation — the TOC uses a hyphen, which is preserved as `-`).
- The `period_name` field is the bare period name without qualifier or date — e.g. `"Naqada Period"` not `"The Naqada Period (c.4000-3200 bc)"`.
- No diacritics appear in Shaw's chapter banners, so no Egyptological transliteration handling is needed for this source.

## Verification

The row-level field values are asserted by `pipeline/tests/test_sources_shaw_ohae.py` against three known rows (Naqada, Old Kingdom, Ptolemaic). A structural citation test in `tests/test_structure.py` (added when all eleven sources land) will verify every row carries `source_citation.page` and `source_citation.edition`.
