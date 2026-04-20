# Leprohon 2013 transcription — method

Per ADR-017 and `docs/playbook-phase-0-ocr-transcription.md`. Multi-chunk source; this file is authoritative across every chunk. Per-chunk OCR / extraction details are logged in the chunk table at the bottom.

## Source

- **Book:** Leprohon, Ronald J. (2013) *The Great Name: Ancient Egyptian Royal Titulary*, ed. Denise M. Doxey. SBL Writings from the Ancient World 33. Atlanta: SBL. ISBN 978-1-58983-735-5.
- **PDF path:** `proprietary/books/Leprohon 2013 - The Great Name.pdf` (gitignored).
- **PDF SHA-256:** `0a59c2763002c76fc7a17b4ff9f9e093f3dc1c887a537f75761de9fdf0ff3f5c`
- **Page count:** 280 pages (physical PDF).
- **Running-header format:** Odd pages: right-aligned SMALLCAP chapter title (`EARLY DYNASTIC PERIOD`), right-aligned printed page number. Even pages: left-aligned printed page number, centre-aligned SMALLCAP `THE GREAT NAME`. Footer carries the EBSCO Publishing watermark (`EBSCO Publishing : eBook Collection (EBSCOhost)`) — not transcribed, not extracted.
- **Physical-to-printed offset:** +21 for chunk 1 (verified printed p. 21 = physical p. 42 at the chapter-II headword, and printed p. 29 = physical p. 50 at the Khasekhemwy tail). Re-verify at each chunk's first and last pages per the multi-chunk-pattern gotcha; may drift at part boundaries (chapter-I/II boundary, chapter VIII/IX boundary are likely drift points).

## Pipeline

For each chunk:

### 1. Text-layer extraction — deterministic `transcribe_chunk.py`

**Method deviation from the playbook default** (supersedes ADR-017 step 1 for this source specifically): Leprohon's PDF is born-digital InDesign (File Type: InDesign in the copyright-page metadata, 280 pages, 2013 SBL WAW 33 publication), so the embedded text layer IS the publisher's typed Unicode, not a scan that needs OCR. Run `transcribe_chunk.py` to pull the text layer via `pypdf` and apply a Manuel de Codage → Egyptological-Unicode normalization on transliteration tokens (identified structurally: between a name-type label `Horus:` / `Two Ladies:` / etc. and the parenthetical anglicised gloss that follows). MdC map: `A→ꜣ, a→ꜥ, H→ḥ, x→ḫ, X→ẖ, S→š, T→ṯ, D→ḏ, q→ḳ`. The script is deterministic, reproducible, and reads directly from the publisher's text layer — an OCR vision model on top of that layer would be a strictly lossier detour (observed on chunk 1: OCR subagent misread `ḥꜣty` as `hꜣty`, losing the h-with-dot-below that the publisher's text layer carried correctly).

Written to `raw/chunk-pNN-pMM-pypdf.md`. Not committed (Layer-2 rights policy).

**Chunk 1 only — parallel OCR cross-validation**: chunk 1 additionally runs an OCR Claude Code subagent to produce `raw/chunk-p42-p50-ocr.md` as an independent cross-reference. The purpose is to validate the pypdf+MdC output against a second pipeline, not to provide ongoing redundancy. Validation outcome: pypdf+MdC was strictly more accurate on transliteration content; OCR was cleaner on structural markdown (italics, page delimiters, footnote grouping). The deterministic cleanup rules in `transcribe_chunk.py` close most of the structural gap; the residual gap is absorbed by the 3-agent extraction majority vote downstream.

**Chunks 2+ — pypdf-only**: no OCR subagent step. `transcribe_chunk.py` is the sole transcription vehicle. Cost savings: one fewer subagent invocation per chunk (removes content-filter-refusal risk per the D&H chunk-1 precedent), fully reproducible from the SHA-pinned PDF.

### Escalation path (fallback tiers if `transcribe_chunk.py` fails)

Only escalate if the pypdf text layer for a specific chunk shows systemic quirks a regex-level normalizer cannot fix (e.g. a chapter typeset with a different font-mapping, an embedded scan for a figure the text layer can't reproduce, text-layer corruption). For Leprohon as currently scoped, no such chunks are expected — the book is a single-format SBL publication. Document any escalation in the § "Chunk log" row for that chunk.

- **Tier 2 — main-session Opus 4.6 OCR**: the main session reads the PDF pages and writes the markdown transcription itself. Used if the pypdf text layer is corrupt for a chunk.
- **Tier 3 — OCR subagent on Claude Opus 4.6** (playbook default, now demoted): only if tiers 1 and 2 fail. Apply the playbook's fair-use-scholarly-extraction refusal-framing paragraph. Preserves Egyptological diacritics + italic conventions in the output markdown.
- **Tier 4 — Gemini 3.1 Pro** (ADR-017 amendment 2026-04-15): only if tiers 1, 2, 3 all refuse. Commit the Gemini prompt at `transcribe-gemini-prompt.md`; pin the Gemini model version; keep every downstream stage (extraction, merge, review, fix_rows) on Opus 4.6.

### 2. Three parallel extraction subagents

Three general-purpose subagents, each reading `prompt.md` (chunk 1) / `prompt-<chunk>.md` (later chunks) and the chunk's OCR markdown. Each writes JSONL to `raw/agent-{a,b,c}.jsonl` (chunk 1) or `raw/agent-{a,b,c}-<chunk>.jsonl` (later chunks).

### 3. Deterministic merge

```bash
cd pipeline && uv run python pipeline/authority/sources/leprohon-2013-titulary/merge.py
```

Reads every `agent-{a,b,c}(-*).jsonl` file under `raw/`, unions the rows across chunks (cross-chunk ID collisions raise), majority-votes per field per row, and writes:

- `reconciled.jsonl` — the union-across-chunks majority-voted result, sorted by `(dynasty_number, sequence_in_chapter_section)`.
- `merge-disagreements.txt` — every non-unanimous row-field for audit.

### 4. LLM egyptologist review

Spawn `egyptologist-reviewer` Claude Code subagent with:

- Path to `reconciled.jsonl`.
- Path to `merge-disagreements.txt`.
- Path to the source PDF + the target physical-page range.
- Path to `README.md` (for schema context).

Asked to return a structured error report: `leprohon_id` / field / current / correct / evidence quote from the PDF.

### 5. Apply overrides via `fix_rows.py`

`SPOT_CORRECTIONS` list of `(leprohon_id, field, new_value, rationale)` tuples. Every correction appended to `merge-disagreements.txt` under `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED`. Idempotent on re-run.

Multi-chunk sources split `SPOT_CORRECTIONS` into per-chunk lists (`EARLY_DYNASTIC_CORRECTIONS`, `OLD_KINGDOM_CORRECTIONS`, ...) when the flat list passes ~10 entries.

### 6. Tests

`pipeline/tests/test_sources_leprohon_titulary.py` asserts exact values on every populated field of a flagship row + row-count invariants + ID uniqueness + ID regex + citation completeness + schema edge cases (Peribsen seth_names, Khasekhemwy horus_names-plus-seth_names, slash-display-name splitting, later_cartouche attestation, multi-variant Horus/Two-Ladies entries, etc.).

### 7. Human Egyptologist sign-off (ADR-017 step 6)

Deferred. When performed, log as `human-review-<YYYY-MM-DD>-<chunk>.md` per the playbook's multi-chunk naming convention.

## Chunk log

### Chunk 1 — Early Dynastic Period

- **Physical PDF pages:** 42–50 (9 pages).
- **Printed pages:** 21–29 (chapter II).
- **Physical-to-printed offset at chunk start / end:** +21 / +21. No drift.
- **Expected row count:** 27 kings. Dyn 0: 12 entries (Iry-Hor, Ka, Narmer, Scorpion, Crocodile, Hedju-Hor, Ny-<Hor>, Haty-Hor, Horwy, Ny-Neith, Horus "A", Horus "Pe"). Dyn 1: 7 entries (Aha, Djer, Djet/Wadjet, Den, Adjib, Semerkhet, Qa'a). Dyn 2: 8 entries (Hetepsekhemwy, Nebre, Ninetjer, Weneg, Sened, Sekhemib, Peribsen, Khasekhem/Khasekhemwy).
- **Known flagship rows for tests:** Den (Dyn 1, full titulary including throne + multi-form later cartouche), Khasekhem/Khasekhemwy (Dyn 2, slashed homonym + horus/seth dual classification + multi-form Horus and Two-Ladies), Peribsen (Dyn 2, Seth name replacing Horus).
- **OCR tier used:** TBD (fill after chunk 1 OCR step runs).
- **OCR output:** `raw/chunk-p42-p50.md` (gitignored).
- **Extraction output:** `raw/agent-{a,b,c}.jsonl` (gitignored).
- **Merge output:** `reconciled.jsonl`, `merge-disagreements.txt` (committed).
- **Reviewer log:** TBD.

### Chunk 2+ — TBD

Later chunks will populate rows in this table as they land.
