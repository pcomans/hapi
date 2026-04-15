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

For every scan-only Phase 0 source (and any future scholarly PDF where transliteration diacritics or tabular layout matter), the transcription method is **Claude Code subagents over physical-page chunks, with the chunks treated as local-only intermediate artifacts** and a three-subagent + deterministic-merge extraction on the committed-to-disk chunks:

1. **OCR pass — Claude Code subagent per chunk.** The `Read` tool in Claude Code renders PDF pages as images for the model, so a general-purpose subagent can directly OCR a physical-page range of the source PDF with no external API call. One subagent call handles up to ~20 pages; for larger books, spawn multiple parallel subagents, each covering a chunk of the PDF. A single-subagent test on Ryholt pp. 336-340 produced correct Egyptological diacritics (ꜣ ꜥ ḥ ḫ nṯ) with no copyright refusal when the task was framed as "fair-use scholarly extraction for a private research repository."
2. **Chunk the PDF by physical (1-indexed PDF) page index**, five pages per chunk by default. Physical page indices are unambiguous — they do not depend on resolving the book's printed page numbering against any front-matter / blank / Part-heading pages, which the agent often gets wrong.
3. **Per-chunk markdown is written to `raw/chunk-pNNN-pMMM.md`** where `NNN-MMM` is the physical-page range. **These files are NOT committed.** They contain the source's own introductory prose / section commentary verbatim — copyrightable material the repo cannot redistribute. `.gitignore` excludes `pipeline/pipeline/authority/sources/*/raw/chunk-*.md`. The chunks exist on the transcriber's local machine only; a reviewer re-running the pipeline regenerates them from the (also uncommitted) PDF.
4. **Structured extraction — three parallel subagents + deterministic merge.** Once the chunks are on disk, spawn three independent Claude Code subagents in parallel, each reading every chunk and emitting JSONL per the source's schema. Then run a deterministic `merge.py` that majority-votes per-field across the three outputs. The merge is the reproducible step; the extraction is not (LLM output), but the committed `reconciled.jsonl` and `merge-disagreements.txt` ARE the audit trail.
5. **`reconciled.jsonl` rows cite the physical-page range of the chunk the row came from**: `source_citation: {pdf_pages: "340-344", edition: "…"}`. Anyone verifying a row opens the PDF at physical pages 340-344 and finds the content there.
6. **Review layer.** Two passes, each honestly labelled in `merge-disagreements.txt`:

   a. **LLM review (automatable).** The `egyptologist-reviewer` Claude Code subagent walks every field disagreement in `merge-disagreements.txt` and cross-checks against the PDF. The main agent applies the subagent's recommendations to `reconciled.jsonl` via a committed override script (or a small hand-edit), recording each change in a new `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED` section at the bottom of `merge-disagreements.txt`. This is NOT human review — it is an LLM checking an LLM. It is better than unreviewed merge output, but it is not scholarly validation.

   b. **Human review (required, not yet performed on Source 2).** An actual working Egyptologist reads a sample of ~5-10 king rows against the source PDF and signs off. Until this happens, the source is **provisional**: downstream consumers (authority layer, `rulers.json`, display UI) treat the data as tentatively correct but flag it in any reviewer-visible context. The `reconciled.jsonl` carries no schema field for validation status yet — this is a gap to close when the authority layer schema is finalised (post-MVP).

### Why physical pages, not printed pages

Every scan has some offset between "physical page 1" (PDF page 1) and "printed page 1" (first numbered page of the book body), driven by front matter, blank filler pages inserted for even/odd page layout, Part-heading pages, and so on. That offset can also *shift mid-book* if a section break has an odd number of pages before it. An agent trying to resolve "printed page N" on the fly regularly gets it wrong; we verified this on Ryholt 1997, where the offset was 4 for File 1 (pp. 333-407) but 3 for the Chronological Tables (pp. 408-411) because of a Part-heading page. Citing by physical page sidesteps this entirely.

### Why not a two-model OCR cross-check?

The benchmark on p. 336 initially motivated a multi-model diff pipeline. In practice:

- **On the fields we actually extract into `reconciled.jsonl`** (titulary diacritics, dates, dynasty numbers, polity), single-model runs were clean on representative titulary pages. The specific Egyptological errors we were guarding against (`ꜣ`/`ꜥ`/`ḥ`/`ḫ`/`nṯ` conflations) happened only in the weaker OCRs (Gemini 3 Flash preview, Mistral OCR) — not in Claude Code subagent OCR on Opus 4.6, which handled every diacritic correctly once given a prompt naming the Unicode character set.
- **The disagreements the diff surfaced** in earlier benchmarks were in bibliographic reference details (`PM II²` vs `PM I²`, proper-noun diacritics like `Fûad` vs `Fūad`) that don't feed the authority layer. Cross-checking OCRs costs its own overhead without producing actionable fixes for extracted fields.

So: trust Claude Code subagent OCR on a model with a strong prompt, sample the output for QA, and stop paying multi-model overhead for cross-checking errors outside the extraction schema.

### Why not Mistral OCR or Gemini 3 Flash?

Mistral's Egyptological-transliteration substitutions (`ꜣ→š`, `ꜥ→ᵉ`) are systematic, not random, and were *worse than pdftotext's*. Flash conflates `ḥ` and `ḫ` (h-with-dot-above vs h-with-dot-below) and drops the `ṯ` under-bar. Both are silent discipline-level errors that a human reader does not catch by spot-check because the characters look plausible. Both stay in reserve for non-titulary pages only, and are not part of the production pipeline.

### Pages that do not need the full pipeline

For pages where only facts like Roman-numeral dynasty counts, regnal-year integers, and Latin-alphabet site names are needed (Chapter 5 concurrency tables, dynasty overview pages), a single-model run is acceptable, provided the structured extract is spot-checked by the transcriber. The pipeline is sized to the *stakes*, not applied uniformly.

## Consequences

- **Per-source cost**: $0 in external API charges. OCR and extraction both run under the existing Claude Code subscription.
- **Committed evidence trail**: every `reconciled.jsonl` row traces back to a `pdf_pages` range in the source PDF. The intermediate `raw/chunk-*.md` files are NOT committed (they contain the source's prose) — they are regenerated from the PDF by anyone re-running the pipeline. `merge-disagreements.txt` IS committed and records the three subagents' per-field disagreements plus the majority-vote resolution. This is the rule-1 (work like a scholar) standard for transcription: the input (PDF) is pinned by SHA-256, the output (JSONL) is committed, the intermediate model outputs are reproducible by re-running three subagents against the pinned PDF.
- **No external API keys required** beyond Claude Code. No per-page OCR billing.
- **Shared tooling**: `merge.py` lives per-source for now. When Source 3 (Kitchen 1996) lands, common code is promoted to a shared module. No premature abstraction.
- **Supersedes earlier provisional plans** (Firecrawl's URL-only PDF parser, external OCR APIs): Claude Code subagents route the PDF through Anthropic's Claude API under the existing subscription — same network trust boundary as any other Claude Code tool use, no new external vendor, no per-page OCR billing. Firecrawl was ruled out because it requires exposing the PDF at a public URL, which is a genuinely different (and worse) rights posture.

## Not covered by this ADR

- **External OCR APIs** (the models listed in the benchmark table) are referenced only as historical baselines. They are not part of the production pipeline. If Claude Code subagents ever refuse a specific source's OCR, we revisit this ADR rather than silently fall back.
- **Bulk cost at scale**: projected $0 in external charges across the remaining scan-only sources. Revisit only if a subagent refusal pattern emerges or if Claude Code's subscription limits become a bottleneck.
