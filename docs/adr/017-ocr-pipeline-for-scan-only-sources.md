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

For every scan-only Phase 0 source (and any future scholarly PDF where transliteration diacritics or tabular layout matter), the transcription method is **Gemini 3.1 Pro preview as the primary bulk OCR**, with **Claude Opus 4.6 vision as a targeted cross-checker** for titulary-heavy pages where diacritic fidelity matters most:

1. **Run Gemini 3.1 Pro preview** on the full target page range with a prompt constraining the character set to the Egyptological Unicode block and forbidding ASCII substitutions (`3` for ꜣ, `c` for ꜥ). Gemini handles multi-page batches without restriction (the fetch.py runner defaults to 5 pages per call).
2. **Run Claude Opus 4.6 vision** only on a curated subset of pages where titulary lines dominate — in practice, one Claude call per king entry where the transliterated prenomen/Horus/nomen names would otherwise go unchecked. **Claude calls are one page at a time** (the model refuses bulk-book transcription requests as copyright reproduction; single-page calls with a factual-extraction framing consistently succeed).
3. **Where both models ran, diff the outputs** into `raw/diff/page-NNN.diff`. Where only Gemini ran, the diff file is absent and the transcriber's sole cross-check is a PDF spot-read.
4. **Human adjudicates disagreements** against the physical PDF page. The canonical OCR for each page is committed as `raw/page-NNN.md` and records which model's reading won on each flagged line (with a short comment, e.g. `# diff: PM II² (Claude) vs PM I² (Gemini) — chose Claude, confirmed against PDF`).
5. **The structured `reconciled.jsonl` is derived from the committed per-page markdowns, not from the raw model outputs** — i.e. if both models were wrong about a character, the committed markdown must be corrected first, and the comment record notes the override.

### Why not symmetric two-model OCR?

The original plan was to run Claude and Gemini on every page in parallel and diff. In practice, **Claude declines multi-page transcription requests of in-copyright books as copyright reproduction** — a correct call on its side given that our proprietary PDFs are under OUP / Museum Tusculanum / IFAO / etc. licenses. Single-page Claude calls with a factual-extraction framing succeed, but running Claude single-page on every page while Gemini goes batched defeats the efficiency purpose of batching. Gemini has no equivalent restriction and handles 5-page batches reliably.

The compromise: Gemini bulk, Claude targeted. Titulary pages (one per king entry, where the Egyptological transliteration is the load-bearing extract) get a Claude cross-check and a diff; everything else (Remarks, Notes, Attestations bibliographic lists) relies on Gemini alone plus human spot-check against the PDF. The benchmark on p. 336 showed Claude catches errors Gemini misses and vice versa, so this compromise trades some coverage for a pragmatic throughput.

### Why not one model plus a human?

Faster, but a single model's silent conflations (e.g. Gemini 3 Flash dropping the `ṯ` under-bar on every occurrence) are exactly the errors a human reader does not catch by spot-check — the character looks reasonable. The two-model cross-check on titulary lines surfaces exactly where the models disagree; the human's attention is spent there, not on global re-reading.

### Why not Mistral OCR?

Mistral's Egyptological-transliteration substitutions (`ꜣ→š`, `ꜥ→ᵉ`) are systematic, not random, and were *worse than pdftotext's*. Mistral is viable only for pages with no transliteration at all (bibliographic-only pages, index pages).

### Pages that do not need the full pipeline

For pages where only facts like Roman-numeral dynasty counts, regnal-year integers, and Latin-alphabet site names are needed (Chapter 5 concurrency tables, dynasty overview pages), a single-model run is acceptable, provided the structured extract is spot-checked by the transcriber. The pipeline is sized to the *stakes*, not applied uniformly.

## Consequences

- **Per-source API cost** is approximately $2–5 for a full book OCR pass (Gemini 3.1 Pro preview in 5-page batches on ~80–500 pages, plus ~30–60 single-page Claude cross-check calls on titulary pages). Trivial for the project.
- **Committed evidence trail**: every reconciled-JSONL row's titulary traces back to a committed per-page `.md` in the source's `raw/` directory, and that markdown traces back to one of two documented model outputs (or a human override recorded in the diff). This is the rule-1 (work like a scholar) standard for transcription.
- **Two API keys required** in `.env`: `ANTHROPIC_API_KEY` and `GEMINI_API_KEY` (Gemini Pro models require a billing-enabled Google AI key; free tier has zero quota on the Pro lineage).
- **Shared tooling**: the first source to use this pipeline (Ryholt) implements it in its own `fetch.py`. When Source 3 (Kitchen 1996) lands, common code is promoted to a shared module (`pipeline/pipeline/authority/ocr.py` or equivalent). No premature abstraction.
- **Supersedes the "Fire-PDF first" provisional plan**: Firecrawl's PDF parser is URL-only, which requires exposing a proprietary in-copyright book on a public URL — an unacceptable rights risk. Claude and Gemini both accept base64 document input directly, keeping the PDF local.

## Not covered by this ADR

- **Gemini 3 Flash and Mistral** remain in the toolbox for bulk non-titulary pages but are not primary transcribers. If a future source is all-bibliographic (e.g. the Porter-Moss index volumes), Flash or Mistral may be promoted to primary and revisited in a follow-up ADR.
- **Vision-LLM cost at scale** (all eleven sources) is bounded — current projection is under $100 total across the Phase 0 handoff list. Revisit if a source with >2,000 titulary pages is added.
