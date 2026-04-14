# Shaw (ed.) 2000 — *The Oxford History of Ancient Egypt*

Period date-ranges at the head of each dated chapter, plus two chapter-body sub-periods where the author states BCE intervals explicitly.

## Citation

Shaw, I. (ed.) (2000) *The Oxford History of Ancient Egypt*. Oxford University Press.

- **Edition used:** 2003 paperback reissue of the 2000 hardback — ISBN-13 978-0-19-280458-7, printed in Great Britain by Clays Ltd. Pagination and content are identical to the 2000 hardback; the reissue is a straight paper-binding of the original typesetting. Verified by spot-checking the TOC page numbers (16, 41, 57, 83, 108, 137, 172, 207, 265, 324, 364, 388, 414) against the scanned pages of this copy — every chapter opens on the page number stated in the TOC.
- **Retrieved:** 2026-04-14 (Internet Archive plain-text extract of the scanned book; Internet Archive identifier `oxfordhistoryofa0000unse`) and in-repo PDF (`proprietary/books/Shaw 2000 - Oxford History of Ancient Egypt.pdf`, SHA-256 `080a7d0e0dd9d3e19a65d0c20f031f66ee8855dbbb018bd0a5eac4534b05d83f`).

## Scope

Each of the thirteen dated-period chapters in Shaw's history opens with a banner giving the period name and an absolute BCE date range. This source transcribes those banners into one row per chapter. Chapters 1 (Introduction) and 11 (Egypt and the Outside World) are excluded — they carry no BCE range on their opening pages and are thematic essays, not periodisations.

**Expected row count:** 13 (chapters 2–10 and 12–15).

## Schema

Per `docs/handoff-phase-0-transcription.md` Source 1 spec. Each row:

```json
{
  "period_name": "...",
  "chapter_number": 3,
  "chapter_title": "The Naqada Period (c.4000-3200 bc)",
  "date_range_start_bce": -4000,
  "date_range_end_bce": -3200,
  "date_qualifier": "c.",
  "sub_periods": [
    {"name": "Naqada I (Amratian)", "start_bce": -4000, "end_bce": -3500},
    {"name": "Naqada II (Gerzean)", "start_bce": -3500, "end_bce": -3200}
  ],
  "source_citation": {"page": 41, "edition": "OUP 2003 paperback (= 2000 hardback), ISBN 978-0-19-280458-7"}
}
```

### `period_name` follows Shaw's chapter titles, not canonical Egyptological labels

`period_name` is the bare period name as Shaw presents it in the chapter banner — derived from the chapter title by dropping the leading `"The"` and the parenthetical date. For chapter 2 (whose title lacks a leading `"The"`), the compact stub `"Prehistory"` is used, matching the running-header word Shaw prints on the subsequent pages of that chapter.

Phase A must map these chapter-title period names onto the canonical labels in `periods.json`. Keeping Shaw's own wording preserves rule 1 (faithful extract) and makes Shaw's framing auditable against HKW's and other sources' framings side-by-side during Phase A.

### `source_note` field on composite / non-canonical rows

Per handoff ground rule 5, rows whose `period_name` cannot map 1:1 onto a canonical Egyptological period carry a `source_note` field describing the composition and the Phase-A mapping decision required:

- **Ch 4** `"Emergence of the Egyptian State"` — Shaw's framing; covers what is canonically the Early Dynastic Period (~Dyn 0–2).
- **Ch 9** `"18th Dynasty before the Amarna Period"` — chapter-scope label; covers the first half of the 18th Dynasty (Ahmose–Amenhotep III).
- **Ch 10** `"Amarna Period and the Later New Kingdom"` — composite: covers the Amarna Period (Akhenaten-era), the post-Amarna end of Dyn 18, and the Ramesside Period (Dyns 19–20). Van Dijk's banner gives a single combined BCE range; the chapter opening does not state sub-period boundaries in the Midant-Reynes manner, so `sub_periods` remains empty.

`source_note` is present only on these three rows. `test_composite_rows_carry_source_notes` enforces the contract: the field appears iff the chapter number is in `{4, 9, 10}`.

### `sub_periods` rule: banner intervals, plus author's own BCE breakdown in the opening chronology section

The handoff schema says "if sub-periods are listed in the chapter opening, include them; otherwise `sub_periods: []`." "Chapter opening" is interpreted narrowly: the banner page itself, plus the first ~two pages where the author states a BCE-bounded sub-period breakdown in prose. Midant-Reynes (ch 3, p. 42-43) meets this bar — she writes "phase (Amratian) lies between 4000 and 3500 bc, followed by the second phase (Gerzean), from 3500 to 3200 bc". That sentence is the attestation captured in `sub_periods` on the Naqada row. The Naqada III phase (3200-3000 BC per Midant-Reynes) crosses the chapter banner's end boundary (-3200) and is not captured here — Phase A will reconcile against chapter 4's range.

No other chapter banner or opening chronology section in Shaw states sub-period BCE boundaries explicitly, so those rows have `sub_periods: []`. This is a conservative extract; Phase A can supplement from HKW (in-repo) and Hendrickx's seriation work.

### Sign convention for dates

- BCE years are negative integers (`-4000` = 4000 BC; `-700000` = 700,000 BC).
- CE years are positive integers (`395` = AD 395).
- `date_qualifier` carries the book's hedge: `"c."` for chapters whose banner uses `c.` (chapters 2–10), `null` for the four chapters (Third Intermediate, Late, Ptolemaic, Roman) whose banners give unqualified dates.

## Rights

OUP, in copyright. This extract contains **factual data** — period names, chapter numbers, BCE date ranges, author attributions, and page numbers — which are not copyrightable. The Naqada I/II BCE boundaries on the chapter 3 row come from Midant-Reynes (pp. 42-43); those numeric intervals are recorded as facts (with page citations) in `raw/chapter-banners.txt` and in the `sub_periods` field, not as verbatim prose. No chapter-body sentences are reproduced. Per handoff rule 4, the book PDF itself is not committed; the scan lives at `proprietary/books/Shaw 2000 - Oxford History of Ancient Egypt.pdf` outside the public repo and is pinned by SHA-256 above.

## Method

See `transcribe.md`. Summary: chapter titles, date ranges, and opening page numbers were read from the book's Table of Contents (pp. v–vi) and re-verified against each chapter's opening banner in the Internet Archive OCR `.txt` extract; the PDF page image was consulted wherever the OCR was noisy. `raw/chapter-banners.txt` commits the thirteen banner blocks verbatim from the OCR so a reviewer without the PDF can still audit the extracted values.

## Known gaps

- **Sub-period BCE intervals beyond Naqada I/II.** Naqada III (3200–3000 BC per Midant-Reynes) crosses the chapter boundary and is not captured. Amarna narrowly defined (c.1353–1336), Ramesside (c.1295–1069), and Saite (c.664–525) are not stated with BCE boundaries in Shaw's chapter banners or opening paragraphs; pulling them requires a different source. HKW 2006 (already in-repo at `sources/hkw-chronology-2006/`) covers most of this.
- **Palaeolithic sub-periods.** Hendrickx & Vermeersch (ch 2) have section headers "The Lower Palaeolithic," "The Middle Palaeolithic," "The Upper Palaeolithic," "The Late Palaeolithic" but I have not transcribed BCE boundaries for them. The 700,000-year span is a geological approximation; Phase A should treat ch 2's `date_range_start_bce: -700000` with care (it is a limit of Shaw's span, not a strict ruler-era date).
- **Cross-source reconciliation.** Shaw's sub-period framing (e.g. Midant-Reynes' Naqada I/II) is chronologically slightly different from HKW's and from Hendrickx's more recent seriation work. Phase A is the correct place to reconcile, not this source.
