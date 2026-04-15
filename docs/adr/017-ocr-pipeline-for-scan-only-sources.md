# ADR-017: OCR Pipeline for Scan-Only Scholarly Sources

## Status

Accepted — 2026-04-14.

## Context

Phase 0 Source 1 (Shaw 2000) was transcribable from an existing Internet Archive OCR plaintext plus banner-page spot-checks. Sources 2–11 per `docs/handoff-phase-0-transcription.md` are largely in-copyright academic books whose PDFs do **not** have clean text layers, or whose text layers mangle the Egyptological transliteration characters the extraction depends on (ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ).

Probing Ryholt 1997 (Source 2) showed the concrete failure mode: the embedded OCR renders `sḫm-rꜥ-ḫw-tꜣwy` as `shm-rr-hw-t3wy` and `ꜥnḫ-nṯrw` as `cnh-ntrw`. Roman numerals (`II², VII, XIII`) come through as `Π2, VH, ΧΠΙ` (Greek Pi, V-H, Greek letters). A mapper that read those transliteration strings would silently encode wrong king names into the authority layer.

We benchmarked five OCRs on Ryholt p. 336 (Sobkhotep I File 1 entry) — a dense titulary page representative of File 1's ~80 pages:

| OCR | Egyptological diacritics (ꜣ ꜥ ḥ ḫ nṯ) | Layout | Roman numerals | Notes |
|---|---|---|---|---|
| Embedded pdftotext | all corrupted (ꜣ→3, ꜥ→c/rr, ḥ→h, ḫ→h) | broken on tables | corrupted (Π for II) | Unusable as sole source for titulary |
| Mistral OCR | **worse than pdftotext** (ꜣ→š, ꜥ→ᵉ/r) | clean structure | correct | Strong on bibliographies, fails on the discipline |
| Gemini 3 Flash preview | ḥ/ḫ conflated, ṯ bar dropped | clean | correct | Adequate only for non-titulary pages |
| **Claude Opus 4.6 vision** | **all correct** | clean | correct on this page | One proper-noun diacritic error elsewhere (Fûad → Fūad) |
| **Gemini 3.1 Pro preview** | **all correct** | clean, preserves `<u>` underline typography | correct on this page | Dropped the Fûad circumflex on same ref |

Every frontier model made at least one error on one page — different errors on different refs. No single model is scholar-grade alone.

## Decision

For every scan-only Phase 0 source (and any future scholarly PDF where transliteration diacritics or tabular layout matter), the transcription method is **Gemini 3.1 Pro preview for bulk OCR, plus human spot-check on a sample of pages against the source PDF**:

1. **Run Gemini 3.1 Pro preview** on the full target page range with a prompt constraining the character set to the Egyptological Unicode block and forbidding ASCII substitutions (`3` for ꜣ, `c` for ꜥ). Pages are batched (the fetch.py runner defaults to 5 pages per API call) with `=== PAGE NNN ===` delimiters in the output for per-page recovery.
2. **Per-page markdown lands in `raw/page-NNN.md` directly** — one file per page, committed as the canonical OCR. No intermediate per-model scratch directories.
3. **Human spot-checks a sample** of ~5 pages per source against the PDF page image, focused on the fields that actually flow into `reconciled.jsonl` — king names, titulary diacritics, dates, dynasty numbers, polity assignments. If the sample is clean, the rest is trusted.
4. **The structured `reconciled.jsonl` is derived from the committed `raw/page-NNN.md` files** — i.e. the transcription is the committed OCR. Any corrections the human finds during spot-check are made directly in `raw/page-NNN.md` with a short comment explaining the override (e.g. `# Gemini: Fuad; PDF: Fûad — corrected`).

### Why not a two-model cross-check?

The benchmark on p. 336 initially motivated a Claude + Gemini diff pipeline. In practice:

- **On the fields we actually extract into `reconciled.jsonl`** (titulary diacritics, dates, dynasty numbers, polity), Gemini 3.1 Pro was clean on the benchmark. The specific Egyptological errors we were guarding against (`ꜣ`/`ꜥ`/`ḥ`/`ḫ`/`nṯ` conflations) happened in Gemini 3 *Flash* and Mistral — not in Gemini 3.1 *Pro*, which handled all five correctly. Claude, surprisingly, got `mnḫ` wrong as `mnḥ`.
- **The disagreements the diff did surface** (`PM II²` vs `PM I²`, `Fûad` vs `Fūad`) were in bibliographic reference details that don't feed the authority layer. The diff cost its own overhead without producing actionable fixes for extracted fields.
- **Claude Opus 4.6 declines bulk multi-page transcription** of in-copyright scholarly PDFs as copyright reproduction — a correct call on Anthropic's side. Working around it (single-page Claude while Gemini batches) surrenders the batching throughput advantage.

So: trust Gemini 3.1 Pro, sample the output for QA, and stop paying the two-model overhead for cross-checking errors outside the extraction schema.

### Why not Mistral OCR?

Mistral's Egyptological-transliteration substitutions (`ꜣ→š`, `ꜥ→ᵉ`) are systematic, not random, and were *worse than pdftotext's*. Mistral is viable only for pages with no transliteration at all (bibliographic-only pages, index pages).

### Why not Gemini 3 Flash?

Flash conflates `ḥ` and `ḫ` (h-with-dot-above vs h-with-dot-below) and drops the `ṯ` under-bar. Both are silent discipline-level errors that a human reader does not catch by spot-check because the characters look plausible. Flash stays in reserve for non-titulary pages only.

### Pages that do not need the full pipeline

For pages where only facts like Roman-numeral dynasty counts, regnal-year integers, and Latin-alphabet site names are needed (Chapter 5 concurrency tables, dynasty overview pages), a single-model run is acceptable, provided the structured extract is spot-checked by the transcriber. The pipeline is sized to the *stakes*, not applied uniformly.

## Consequences

- **Per-source API cost** is approximately $1–3 for a full book OCR pass (Gemini 3.1 Pro preview in 5-page batches on ~80–500 pages). Trivial for the project.
- **Committed evidence trail**: every `reconciled.jsonl` row traces back to a committed `raw/page-NNN.md` in the source's `raw/` directory. The markdown is Gemini's output with any human-spot-check corrections inline-commented. This is the rule-1 (work like a scholar) standard for transcription.
- **One API key required** in `.env`: `GEMINI_API_KEY` (Gemini Pro models require a billing-enabled Google AI key; free tier has zero quota on the Pro lineage).
- **Shared tooling**: the first source to use this pipeline (Ryholt) implements it in its own `fetch.py`. When Source 3 (Kitchen 1996) lands, common code is promoted to a shared module (`pipeline/pipeline/authority/ocr.py` or equivalent). No premature abstraction.
- **Supersedes the "Fire-PDF first" provisional plan**: Firecrawl's PDF parser is URL-only, which requires exposing a proprietary in-copyright book on a public URL — an unacceptable rights risk. Gemini accepts base64 document input directly, keeping the PDF local.

## Not covered by this ADR

- **Claude Opus 4.6 as a targeted spot-checker** is still available if a specific page's titulary looks suspicious during the human QA sample and we want a second opinion. Single-page Claude calls work; it's only bulk batches the model refuses. Use sparingly.
- **Gemini 3 Flash and Mistral** remain in the toolbox for bulk non-titulary pages but are not primary transcribers for anything with Egyptological diacritics. If a future source is all-bibliographic (e.g. the Porter-Moss index volumes), Flash or Mistral may be promoted to primary and revisited in a follow-up ADR.
- **Vision-LLM cost at scale** (all eleven sources) is bounded — current projection is under $30 total across the Phase 0 handoff list. Revisit if a source with >2,000 titulary pages is added.
