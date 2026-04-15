# Transcription method — Ryholt 1997

Reproducible protocol per ADR-017 (two-model vision OCR with diff adjudication).

## Inputs

1. `proprietary/books/Ryholt 1997 - Political Situation SIP.pdf` — full scanned book (466 pages, 37 MB). Not committed to the public repo.
2. Printed pages **333–411**: File 1 / Catalogue of Attestations (pp. 333–407) + Chronological Tables (pp. 408–411).

## Pipeline

See `fetch.py` in this directory. Per ADR-017, Gemini 3.1 Pro preview is the only OCR; human spot-check is the QA.

### Bulk OCR

```
cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/fetch.py \
    --physical 336-416 --chunk-size 5
```

For each 5-page chunk, the runner:
- combines those physical pages (1-indexed PDF pages) into one PDF via pypdf,
- sends it to Gemini 3.1 Pro preview (`gemini-3.1-pro-preview`) with the ADR-017 prompt,
- writes the response verbatim to `raw/chunk-pNNN-pMMM.md`, prefixed with an HTML comment stating the physical-page range.

The chunk is the atomic unit of both OCR and citation. We do not try to split chunks back into per-page files — that introduces an alignment problem (see ADR-017 "Why physical pages, not printed pages") for no gain, since citations work fine at chunk-range granularity.

### Spot-check QA

Before committing `reconciled.jsonl`, the transcriber reads ~2-3 sampled `raw/chunk-…md` files against the corresponding physical PDF pages, checking titulary diacritics (ꜣ ꜥ ḥ ḫ nṯ), regnal dates, and File N/M labels. Corrections are made inline in the chunk file with a short comment (e.g. `<!-- Gemini: Fuad; PDF: Fûad — corrected -->`).

### JSONL derivation

Once `raw/chunk-…md` files are committed and spot-checked, a parser (added in a later commit) walks them and emits `reconciled.jsonl`. Each row's `source_citation.pdf_pages` is the chunk's physical page range.

## The prompt

Both models receive an identical prompt that:

- Names the book, so the model has context
- Enumerates the Egyptological Unicode character set (`ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ`) and explicitly forbids ASCII substitutions (`3` for ꜣ, `c` for ꜥ, `h` for ḥ/ḫ)
- Demands Markdown output preserving the two-column layout and HTML `<u>…</u>` for underlined primary attestation locations
- Forbids any preamble or closing remarks

The prompt is the load-bearing part of the pipeline — a generic "transcribe this PDF" prompt produces worse diacritic output. See `fetch.py` for the exact text.

## Known model biases (from the p. 336 benchmark)

- **Claude Opus 4.6** has been observed to conflate `ḥ` and `ḫ` in Horus names (`mnḫ` → `mnḥ`). Trust Gemini where they disagree on the h-with-dot diacritic unless the PDF pixels say otherwise.
- **Gemini 3.1 Pro preview** has been observed to drop proper-noun diacritics (`Fûad` → `Fuad`) and to misread some roman-numeral references (`PM II²` → `PM I²`). Trust Claude on roman numerals and on the circumflex/macron accents on proper nouns.
- Both are reliable on `ꜣ ꜥ nṯ` once the prompt is enforced.

## PDF page ↔ printed page mapping

Front matter adds 4 physical pages before page 1 of the main text. Printed page N = physical page N + 4 (i.e. the 0-indexed `reader.pages[N + 3]`). Verified by spot-check: printed p. 336 (Sobkhotep I entry) is physical page 340.

## Structure of File 1 entries

Every king entry follows the same template (see README for the full list):

```
Appellation: <Anglicised name>         File <dyn>/<seq>
H: <horus name>                        ← transliterated; dash if unknown
D: <nebty name>
G: <golden Horus name>
P: <prenomen>
N: <nomen> [with filiation to his father X]
Turin King-list, <col>/<row>: <...>    ← optional, if attested
Attestations:
  1) <findspot>, <object-type>.
     <current location>.
     Bibl.: <citations>.
  …
Remarks: <optional narrative>
Notes:
  1. …
  2. …
```

The JSONL parser (added when Phase 2 lands) uses this template to extract structured fields. Non-canonical entries — kings Ryholt lists in the "Unattributed" bucket at the end — require manual schema handling and are flagged in README known-gaps.

## Chronological Tables (pp. 408–411)

These pages summarise Ryholt's reconstructed parallel-dynasty chronology. They populate the `polity` and `concurrent_with` fields on every king entry. Extraction is done by table transcription from the OCR markdown, cross-referenced against the per-king entries in File 1 for consistency.

## PDF hash pinning

Source PDF SHA-256: `078c0d92bc3310c1044d4b736db6a8af9c309ef6839bd9e96b6864d200bbc972`. A reviewer re-running `fetch.py` against a PDF with a different hash should not expect byte-for-byte OCR reproduction (model outputs are stochastic across different input bytes even when the content looks identical).

## Verification

`pipeline/tests/test_sources_ryholt_sip.py` (added in Phase 2) will assert specific field values for 3+ sampled rows and enforce the rule-5 "all populated fields" contract.
