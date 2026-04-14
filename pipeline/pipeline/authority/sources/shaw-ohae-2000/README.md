# Shaw (ed.) 2000 — *The Oxford History of Ancient Egypt*

Period date-ranges at the head of each chapter.

## Citation

Shaw, I. (ed.) (2000) *The Oxford History of Ancient Egypt*. Oxford University Press.

- **Edition used:** 2003 paperback reissue of the 2000 hardback — ISBN-13 978-0-19-280458-7, printed in Great Britain by Clays Ltd. Pagination and content are identical to the 2000 hardback; the reissue is a straight paper-binding of the original typesetting.
- **Retrieved:** 2026-04-14 (Internet Archive plain-text extract of the scanned book) and in-repo PDF (`proprietary/books/Shaw 2000 - Oxford History of Ancient Egypt.pdf`).

## Scope

Each of the twelve dated-period chapters in Shaw's history opens with a banner giving the period name and absolute BCE date range. This source transcribes those banners into one row per chapter. Chapters 1 (Introduction), 2 (Prehistory), and 11 (Egypt and the Outside World) are excluded — they are thematic chapters without a single BCE date range.

**Expected row count:** 12 (chapters 3–10 and 12–15).

## Schema

Per `docs/handoff-phase-0-transcription.md` Source 1 spec. Each row:

```json
{
  "period_name": "...",
  "chapter_number": 3,
  "chapter_title": "The Naqada Period (c.4000–3200 BC)",
  "date_range_start_bce": -4000,
  "date_range_end_bce": -3200,
  "date_qualifier": "c.",
  "sub_periods": [],
  "source_citation": {"page": 41, "edition": "OUP 2003 paperback (= 2000 hardback), ISBN 978-0-19-280458-7"}
}
```

### On `sub_periods`

Per handoff schema: "If sub-periods are listed in the chapter opening, include them; otherwise `sub_periods: []`." No chapter banner in Shaw 2000 enumerates sub-periods with absolute BCE boundaries on its opening page. Naqada I/II/III are discussed later in the Naqada chapter (pp. 42 ff.) via Petrie's sequence-date ranges (SD 30–38, SD 39–60, SD 61–80), not as absolute BCE intervals; those would be a separate extract and would require Hendrickx/Kaiser seriation work beyond the chapter opening. Left empty here to preserve rule 1 (work like a scholar — no invention).

### `period_name` follows Shaw's chapter titles, not canonical Egyptological labels

`period_name` is the bare period name as Shaw presents it in the chapter banner — e.g. chapter 4 `period_name` is `"Emergence of the Egyptian State"` (Shaw's own framing), not a canonical label like "Early Dynastic Period" or "Protodynastic." Phase A must map these chapter-title period names onto the canonical labels in `periods.json`. Keeping Shaw's own wording here preserves rule 1 (faithful extract) and makes Shaw's framing auditable against HKW's and other sources' framings side-by-side during Phase A curation.

### Sign convention for dates

- BCE years are negative integers (`-4000` = 4000 BC).
- CE years are positive integers (`395` = AD 395).
- `date_qualifier` carries the book's hedge: `"c."` for chapters that use `c.` in the banner, `null` for the three chapters (Third Intermediate, Late, Ptolemaic, Roman) whose banners give unqualified dates.

## Rights

OUP, in copyright. This extract contains twelve rows of **factual data** — period names, chapter numbers, and BCE date ranges — which are not copyrightable. No prose from Shaw's text is reproduced. Per handoff rule 4, no raw artifact is committed; the scanned PDF lives at `proprietary/books/Shaw 2000 - Oxford History of Ancient Egypt.pdf` outside the public repo, and `raw/.gitkeep` stands in.

## Method

See `transcribe.md`. Summary: the chapter titles and date ranges were read from the book's Table of Contents (pp. v–vi) — which lists all fifteen chapters with their BCE date ranges and starting page numbers — and cross-verified against each chapter's opening banner using both the Internet Archive OCR `.txt` and the source PDF. No OCR-generated text was committed without cross-checking against the PDF page image.

## Known gaps

- **Sub-period BCE intervals** (Naqada I/II/III, Amarna narrowly defined, Ramesside) are not in Shaw's chapter banners. Phase A will need to pull sub-period dates from a different source (HKW 2006 already in-repo covers Naqada seriation; Dreyer 1998 will cover Dyn 0).
- **Chapter 2 (Prehistory)** is excluded: its banner gives no single BCE range — it spans Palaeolithic to Badarian, treated via cultural phases not dates.
- **Chapter 11 (Egypt and the Outside World)** is thematic and excluded.
