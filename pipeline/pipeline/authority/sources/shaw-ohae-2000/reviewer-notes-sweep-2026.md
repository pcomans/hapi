# Egyptologist sweep review, 2026

Source reviewed: Shaw (ed.) 2000/2003, *The Oxford History of Ancient Egypt*, PDF SHA-256 matches README. Read `README.md`, `transcribe.md`, `chapter-banners.txt`, and all 13 rows in `reconciled.jsonl`. No prior `reviewer-notes-*.md` files were present in this source directory.

Spot-check coverage: checked all 13 rows against the cited PDF chapter openings or TOC/page images: chs. 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15. Numeric ranges, page citations, chapter order, exclusions of ch. 1 and ch. 11, and author/chapter identifications are broadly correct.

## P1

None found.

## P2

- `reconciled.jsonl`, all rows: `chapter_title` is documented as preserving Shaw's chapter-title date text verbatim, but the PDF prints uppercase `BC`/`AD` and typographic en dashes in chapter banners/TOC, while JSON uses lowercase `bc`/`ad` and ASCII hyphen. Examples: ch. 2 PDF banner has `(c.700,000-4000 BC)` with an en dash between years; ch. 3 has `(c.4000-3200 BC)`; ch. 13 has `The Late Period (664-332 BC)`; ch. 15 has `The Roman Period (30 BC-AD 395)`. README/transcribe currently state Shaw uses lowercase `bc`/`ad` and hyphen-minus, which is contradicted by the page images. The factual date fields are not affected, but provenance fidelity is.

- `reconciled.jsonl`, ch. 10 `source_note`: the note imports explicit sub-period bounds for Akhenaten-era Amarna (`c.1352-1336`) and Ramesside (`c.1295-1069`) while also saying the chapter opening does not state sub-period BCE boundaries. Those dates are plausible Egyptological chronology, but they are not sourced by the Shaw banner/opening extraction rule and are not cited in this source row. Either remove the numeric bounds from this source note or cite the external authority used; otherwise the row mixes faithful Shaw extraction with uncited reconciliation data.

## P3

- `reconciled.jsonl`, chs. 3-4 / README: the Naqada handling is defensible but should remain flagged as a Phase-0 contradiction. Midant-Reynes explicitly gives Naqada III/final Predynastic as `c.3200-3000 BC` immediately after the Naqada I/II intervals, while the chapter 3 banner ends at `c.3200 BC` and ch. 4 begins at `c.3200 BC`. Omitting Naqada III from ch. 3 `sub_periods` avoids an out-of-range child interval, but it means the stated "Naqada Period" sub-period extract is incomplete by design. Phase A should not infer that Shaw lacks a Naqada III interval; it is present in the body but crosses the banner boundary.

- `chapter-banners.txt` / `transcribe.md`: several committed banner snippets reflect OCR artifacts or normalized text rather than the page image, e.g. ch. 2 `bc` vs PDF `BC`, ch. 5 note says PDF prints lowercase `bc` but the image shows `BC`, and ch. 15 OCR reads `BOAD`/`EC` in extracted text while the page image resolves to `BC-AD`. Keep the OCR-noise annotations, but correct claims about the PDF's actual capitalization/dash forms so later reviewers do not re-normalize from OCR.

Overall: the source is usable for period ranges after fixing documentation/title fidelity and separating Shaw-attested facts from Phase-A/general chronology annotations.
