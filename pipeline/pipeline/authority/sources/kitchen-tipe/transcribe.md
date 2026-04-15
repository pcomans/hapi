# Transcription method — Kitchen 1996 TIPE

Reproducible protocol per ADR-017 (Claude Code subagent OCR, followed by three-subagent structured extraction and deterministic majority-vote merge).

## Inputs

1. `proprietary/books/Kitchen 1996 - Third Intermediate Period 3rd ed.pdf` — scanned 3rd-ed. reprint. Not committed to the repo.
2. **Target range**: physical PDF pages **240–243** (printed pp. 465–468), covering Part VI Section I *Dates of Kings*, Tables 1, 3, 4. Table 2 is deliberately excluded (see README — it's an alternative-dates hypothesis for the same Dyn 21 kings).

## Pipeline

Per ADR-017: Claude Code subagent OCR of the target range, followed by three parallel Claude Code subagent extractors and a deterministic majority-vote merge. All LLM work runs under the Claude Code subscription (no new external OCR vendor, no per-page billing).

### OCR

Kitchen's Tables 1, 3, 4 are tight four pages — small enough for a single-chunk OCR pass. A Claude Code general-purpose subagent uses the `Read` tool with `pages:"240-243"` and writes `raw/chunk-p240-p243.md` on local disk. The chunk file is **not committed** (per ADR-017 and `.gitignore` pattern `pipeline/pipeline/authority/sources/*/raw/chunk-*.md`).

Unlike Ryholt's catalogue-style text, Kitchen's pages are fully tabular. The OCR output uses Markdown tables to preserve the Tanite/HPA parallel-column structure of Table 1 and the dynasty-labelled groupings of Tables 3 and 4. Running-header text (e.g. `TABLES`, `DATES OF KINGS`) and the printed page numbers `465` / `466` / `467` / `468` are preserved inline so a reviewer can cross-reference the printed edition.

### Structured extraction — three parallel subagents

The single OCR chunk is read by three independent Claude Code general-purpose subagents in parallel, each with the identical prompt committed to `prompt.md`. Each writes JSONL to a distinct file under the agent directory (default `<source_dir>/raw/`, overridable via `--agent-dir` / `KITCHEN_AGENT_DIR`):

- Agent A → `<agent_dir>/agent-a.jsonl`
- Agent B → `<agent_dir>/agent-b.jsonl`
- Agent C → `<agent_dir>/agent-c.jsonl`

The three-subagent protocol (rather than a single pass) is kept even for this small source because Kitchen's tables have several error-prone micro-features: `c.` prefixes for approximate dates, hedge markers like `(?)` / `(??)`, co-regency annotations embedded mid-row, `[Prenomen unknown]` placeholders, and single Roman-numeral suffixes vs double-quoted ones (`"III"` vs `'III'`). Majority vote across three agents absorbs stochastic diacritic / punctuation drift.

### Merge

```
cd pipeline && uv run python pipeline/authority/sources/kitchen-tipe/merge.py
```

`merge.py` groups rows by `kitchen_id`, takes a per-field majority vote, writes `reconciled.jsonl` (committed), and writes `merge-disagreements.txt` (committed) listing every row whose fields didn't unanimously agree. The merge is pure Python with no LLM calls; re-running on identical agent outputs produces byte-identical results.

`merge.py` is structurally the Ryholt merge with three adaptations:

- `ryholt_id` → `kitchen_id` throughout.
- The `_sort_key` recognises compound prefixes (`20`, `21`, `21H`, `22`, `23`, `24E`, `24`, `24P`, `25`, `26`) and maps each to a `(dynasty_int, polity_rank)` ordering so streams within the same dynasty interleave predictably.
- `DEFAULT_AGENT_DIR` points at `<source_dir>/raw/`. The 3-subagent parallel extraction writes `agent-{a,b,c}.jsonl` alongside the OCR chunk; both are gitignored (the main `.gitignore` covers `raw/chunk-*.md` and `raw/agent-*.jsonl`). Ryholt's `/tmp/claude-501/ryholt/` convention was dropped for this source because Claude Code general-purpose subagents could not write to `/tmp/claude/` or `/tmp/claude-501/` under the current sandbox; the repo working directory is the only cross-subagent writable path.

Sentinel-null normalisation (`"none"`, `"-"`, `"n/a"`, etc. → `null`) is retained verbatim from Ryholt, because Kitchen also uses `"-"` in a few table cells (e.g. Iuput II's prenomen `[Prenomen unknown]` where some agents render as `"-"` and others as the bracketed phrase).

### Review (LLM, then human — honestly labelled)

Per ADR-017 step 6:

- **LLM review (done on this source):** after the 3-subagent merge, the `egyptologist-reviewer` Claude Code subagent walks every entry in `merge-disagreements.txt`, cross-checks against the PDF, and flags rows where the majority vote is wrong. The main agent applies flagged corrections to `reconciled.jsonl` via a committed override snippet and records each change in `merge-disagreements.txt` under `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED`. **This is an LLM checking an LLM.** Better than unreviewed merge output, but not scholarly validation.
- **Human review (required, NOT yet done on this source):** an actual Egyptologist reads a sample of king rows against Kitchen's printed PDF and signs off. Until that happens, this extract is **provisional**.

## Audit trail

- PDF (SHA-256 pinned below; not committed) → `raw/chunk-p240-p243.md` (Claude Code subagent OCR; not committed, per-transcriber regenerable)
- `raw/chunk-p240-p243.md` → three per-extraction-agent JSONLs (Claude Code subagents; non-deterministic; ephemeral in `/tmp/claude-501/kitchen/` — not committed)
- three per-agent JSONLs → `reconciled.jsonl` (deterministic merge, committed)
- `merge-disagreements.txt` (committed) lists every field where extraction agents disagreed plus the majority-vote resolution and the LLM reviewer's overrides.

## PDF hash pinning

Source PDF SHA-256: `18605ca79b5dbd0149280e243ef4219f557c5603305796d51ad17a25e3bf42bb`. A reviewer re-running the pipeline against a PDF with a different hash should not expect byte-for-byte output reproduction; model outputs are stochastic, and the committed `reconciled.jsonl` is the source of truth.

## Physical vs printed pages

This PDF is a one-page-per-physical layout (each physical page renders one printed page of the book). The offset from printed to physical is +NN and drifts across Part boundaries; rather than resolve it, `reconciled.jsonl` cites the **physical PDF page range** (`"240-243"`) per ADR-017. A reviewer opens the PDF at physical pp 240-243 to verify any row; printed page numbers 465–468 are visible at the bottom of each page for scholarly cross-reference.

## Structure of Kitchen's Tables 1, 3, 4

**Table 1 (physical 240, printed 465)** — two-column layout. Left column: `About B.C.` dates and Tanite kings with name + `(length_y)`. Right column: HPAs with name + `(length_y)`. A few kings (Amenemope, Osochor) carry `(9 y; 2, co-rgt)` meaning "9 years reign; of which 2 as co-regent" — extract the main length and treat co-rgt as a note. Pinudjem I appears twice in the HPA column: once as `"Pinudjem I, hp (15 y)"` (high priest) and once as `"Pinudjem I, 'kg' (22 y)"` (self-declared 'king'). Both rows preserved.

**Table 3 (physical 241, printed 467)** — single-column layout per dynasty. Each line is `"{start}–{end}: {Name}, {Prenomen} ({length} y)"`. Some lines have mid-line annotations: `"Shoshenq II, Heqakheperre Setepenre (x yrs; co-rgt only)"`, `"Harsiese, Hedjkheperre Setepenre (c. 10 y?; co-rgt only)"`. The line `"c. 870–860: Harsiese..."` sits indented under Osorkon II (22nd Dyn) because Kitchen marks him as a Theban co-regent; we tag polity `"Theban (HPA)"` on Harsiese A. The 23rd-Dyn block is marked by `"[Start of Dyn. 23.]"` after Shoshenq III's line.

**Table 4 (physical 242–243, printed 468)** — grouped by sub-dynasty with section headings `Early Saite Princes`, `24th Dynasty`, `Proto-Saite Dynasty`, `25th (Nubian) Dynasty`, `26th Dynasty`. Date format drops the prenomen for some early rows (e.g. `"c. 770: Pimay (the later king??)"`). 25th-Dyn rows include prenomen after the name, same format as Table 3.
