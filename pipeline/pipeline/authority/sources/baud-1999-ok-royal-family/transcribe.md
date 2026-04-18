# Transcription method — Baud 1999 BdE 126 Corpus

Per ADR-017 and the Phase-0 playbook. One chunk per PR, ~40 entries per chunk, seven chunks total.

## Source pinning

- **Book:** Michel Baud, *Famille royale et pouvoir sous l'Ancien Empire égyptien*, BdE 126, IFAO, Cairo, 1999. Vol. 2 *Corpus*.
- **PDF path:** `proprietary/books/Baud 1999 - Famille royale AE vol 2.pdf` (gitignored).
- **PDF SHA-256:** `8768536a13fb5428d8ec7fbd96263d028aabb557a5411e7f796cad99ed6881cb`.
- **Page count (vol. 2):** 296 physical pages.

## Pipeline (all stages Claude Opus 4.7)

1. **Scope the chunk** — identify the physical-page range covering the target Baud entry-number range. Cite by physical PDF pages (ADR-017). Verify boundary at both ends (first entry starts here, last entry ends there, next entry does NOT appear).
2. **No committed OCR intermediate.** Per the playbook's rights policy, Baud's prose paragraphs are the unsafe-to-commit category. Extractors Read the sub-PDF directly. The 17 MB vol. 2 PDF is well under the 100 MB Read limit and a 30–50 page sub-chunk is small enough to feed as a single Read (paginated in 20-page windows per Read).
3. **Split the sub-PDF** — write `raw/source-chunk-<N>.pdf` covering the chunk's physical-page range via `pypdf`. Gitignored under the `raw/*` pattern. Exact command (run from repo root):
   ```bash
   cd pipeline && uv run --with pypdf python -c "
   from pypdf import PdfReader, PdfWriter
   r = PdfReader('../proprietary/books/Baud 1999 - Famille royale AE vol 2.pdf')
   w = PdfWriter()
   for i in range(START_PHYS-1, END_PHYS):
       w.add_page(r.pages[i])
   with open('pipeline/authority/sources/baud-1999-ok-royal-family/raw/source-chunk-<N>.pdf', 'wb') as f:
       w.write(f)
   "
   ```
4. **Three parallel extraction subagents** — spawn `general-purpose` Claude Code subagents A/B/C in parallel, each with the chunk-specific prompt (`prompt-chunk-<N>.md`), each Reading `raw/source-chunk-<N>.pdf`, each writing to `raw/agent-{a,b,c}-chunk-<N>.jsonl`. Expected row count: one row per Baud-numbered entry in the chunk (~40 for chunks 1–6, ~42 for chunk 7). The extraction prompt preserves Baud's hedges and French-school transliteration verbatim; see `prompt-chunk-1.md`.
5. **Deterministic merge** — `cd pipeline && uv run python pipeline/authority/sources/baud-1999-ok-royal-family/merge.py`. Primary key is the flat `baud_id` string (`"baud-N"`); merge loudly fails on duplicate IDs across agents or across chunks. Majority-vote per field; sentinel-null normalisation (`"none"`, `"-"`, `"—"`, `"n/a"`, `"unknown"`) turns those strings into actual `null`. Bracketed placeholders like `[X]` are NOT sentinel-null — they are Baud's authorial reconstruction markers and survive verbatim.
6. **Egyptologist-reviewer pass** — spawn the `egyptologist-reviewer` subagent with `reconciled.jsonl`, `merge-disagreements.txt`, the source PDF path, and the chunk physical-page range. Baud-specific risks to flag:
   - Dropped hedges (Baud is especially hedge-heavy; OK prosopography is sparsely attested).
   - Promotion of a scholarly judgment (e.g. Baud's "probable filiation") to a hard claim.
   - Tomb-designation format (G xxxx for Giza, D xx for Saqqara mastabas, LG nn for Lepsius-numbered).
   - Transliteration drift between the extracted `name_egyptian` and Baud's printed form — especially dot/hyphen positions.
   - Missing `service_personnel: true` for asterisk-marked headwords.
   - Missing `baud_refs` entries (Baud gives cross-refs to Baer / Schmitz / Harpur / Troy etc. as standard; silent rows are suspicious).
   - Overlap with D&H earlier chapters: the reviewer should flag discrepancies with D&H OK rows when both exist, but NOT auto-reconcile — Phase A curates.
7. **`fix_rows.py` overrides** — apply reviewer corrections idempotently; append an `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED` section to `merge-disagreements.txt`.
8. **Tests** — `pipeline/tests/test_sources_baud_ok_royal_family.py` asserts row count, ID uniqueness and shape, citation completeness, one fully-populated flagship row's every field, and chunk-specific hedge-preservation regression tests.
9. **Human Egyptologist sign-off** (ADR-017 step 6, deferred) — logged in `human-review-<YYYY-MM-DD>-chunk-<N>.md` when the human pass runs. Until then, each chunk remains provisional.

## Chunks

### Chunk 1 — entries `[1]`–`[40]`

- **Physical pages:** 11–49 (vol. 2). Includes the Corpus methodological intro (pp. 11–16) so extractors have the field-structure context Baud documents on pp. 395–397 (his header letters `a`–`h`).
- **First entry:** `[1] ///-Ḥr (?)` on physical p. 14 (printed p. 399).
- **Last entry:** `[40] ɛnḫ-Špss-kɜ.f*` on physical p. 49 (printed p. 432). `[41]` header appears at the bottom of physical p. 49 and continues onto p. 50; the extraction prompt instructs extractors to stop at the end of `[40]` and to NOT extract `[41]`.
- **Offset drift:** printed–physical drift ranges from 384 (at p. 11/printed 395) to 383 (at p. 49/printed 432). Normal inter-frontmatter drift; document, do not resolve. Cite physical pages only.

Subsequent chunks: see `README.md` table. Boundary physical-page ranges are determined during each chunk's scoping step.

## Model pinning

All stages on Claude Opus 4.7 (`claude-opus-4-7`), the current-good model for this project. If Opus refuses OCR-style content on a given chunk, the Phase-0 playbook's per-chunk fallback ladder applies (main-session Opus → Gemini 3.1 Pro per ADR-017 amendment). No deviations on chunk 1 — the extractors Read the PDF directly without an OCR step, so the refusal surface is the extraction prompt rather than bulk OCR.
