# Transcription method — Beckerath 1997 Chronologie

Reproducible protocol per ADR-017 (Claude Code subagent OCR, followed by three-subagent structured extraction and deterministic majority-vote merge).

## Inputs

1. `proprietary/books/Beckerath 1997 - Chronologie des pharaonischen Aegypten.pdf` — gscan2pdf scan of the 1997 von Zabern 1st edition. Not committed to the repo.
2. **Target range**: physical PDF pages **105–109** (printed pp. 187–194), covering Anhang A *Chronologische Übersicht über die Geschichte Altägyptens* (printed pp. 187–193) and the immediately following *Supplement zu A* with full Dyn 19–23 titularies (printed pp. 193–194). Anhang B (calendar conversion, PDF p109+) and Anhang C (calendar drift, PDF p110+) are deliberately excluded — they are auxiliary calendar tables, not chronology.

   **PDF p109 fold rule.** Page 109 is a double-page-spread containing the *end of Supplement zu A* on the left half (book p194) and the *start of Anhang B* on the right half (book p195). OCR transcribers must **stop at the fold** — capture only the left half of PDF p109. The first row of Anhang B (`B. Tabelle zur Umrechnung julianischer in gregorianische Daten`) is the explicit cutoff marker.

## Pipeline

Per ADR-017: Claude Code subagent OCR of the target range, followed by three parallel Claude Code subagent extractors and a deterministic majority-vote merge. All LLM work runs under the Claude Code subscription.

### OCR

Beckerath's PDF is a gscan2pdf scan with **no embedded text layer** and a **double-page-spread layout** — every physical PDF page renders two facing book pages side-by-side. The OCR pass is one Claude Code general-purpose subagent (sonnet model) that uses the `Read` tool to ingest pre-rendered JPEGs of the target PDF pages from `$TMPDIR/beckerath_scan/scan-NNN.jpg` and writes a single Markdown chunk file at `raw/chunk-p105-p109.md` capturing both book pages per PDF page in left-then-right reading order.

Within each PDF-page render, the subagent preserves Beckerath's typography:

- Italic section headings (`FRÜHZEIT`, `ALTES REICH`, `I. ZWISCHENZEIT`, `MITTLERES REICH`, `II. ZWISCHENZEIT`, `NEUES REICH`, `III. ZWISCHENZEIT`, `SPÄTZEIT`) drive the `period` field downstream.
- Dynasty headings (`1. Dynastie (etwa 3032/2982–2853/2803)`) anchor the `dynasty` integer and provide a sanity-check for the rows that follow.
- Two-column dates `3032/2982–3000/2950` — the slash separates Beckerath's high and low alternative endpoints; both must be preserved.
- Italicised Egyptian titularies in parentheses (e.g. `(Hor Aha)`, `(Nefer-cheprurê wa-en-rê)`).
- The printed page numbers `186` / `187` / `188` ... at the top of each book-page render are preserved inline so a reviewer can cross-reference.

The chunk file is **not committed** (gitignored via `pipeline/pipeline/authority/sources/*/raw/chunk-*.md`).

### Page-level post-processing — `postprocess.py`

After OCR and BEFORE the 3-subagent extraction reads `chunk-p105-p109.md`, run:

```
cd pipeline && uv run python pipeline/authority/sources/beckerath-1997-chronologie/postprocess.py
```

The post-processor restores **persistent dynasty + section context across page boundaries** that the OCR markdown loses. It injects two HTML-comment annotations into the chunk file (in place by default; pure-function `process_chunk(md) -> md` is also available as a library):

1. **After every dynasty heading** (`**N. Dynastie (...)**`), emit `<!-- period: <SectionTitleCase> -->` so the section is *directly attached* to the dynasty heading. Defeats the look-ahead-too-far misfile observed in `merge-disagreements.txt` LLM-OVERRIDES at rows 24.01 and 24.02 — Dyn 24 and 25 sit under `### III. ZWISCHENZEIT` but agents read the closer-following `### SPÄTZEIT` and mis-attribute these short dynasties to Spätzeit.

2. **After every `## Book pNNN` page boundary that lands inside a dynasty's span** (i.e. the next non-empty line is NOT itself a section heading or new dynasty heading), emit `<!-- dynasty-context: <full-dynasty-heading-text> -->` and `<!-- period: <SectionTitleCase> -->`. Defeats the page-break-loses-`etwa` case observed in LLM-OVERRIDES at rows 04.02–04.08 — the Dyn-4 heading `**4. Dynastie (etwa 2639/2589–2504/2454)**` is on book p187 but rows from Cheops onward are on book p188, and agents reading p188 silently dropped `start_approximate=true`/`end_approximate=true` because the heading context was off-screen.

The 3 extraction agents interpret these comments per `prompt.md`'s "post-processor annotations" rule: a `<!-- dynasty-context: ... -->` comment refreshes the dynasty heading at that point in the document; `<!-- period: ... -->` directly attaches the section to the dynasty for the `period` field. The post-processor adds NO new agent-facing semantics beyond making the existing context inescapably visible at every page within a span.

Idempotent: running the post-processor twice on the same chunk file yields the same output (existing injected comments are stripped on re-run before re-emission).

The post-processed file overwrites the OCR chunk file at `raw/chunk-p105-p109.md` (gitignored). The OCR step is regenerable from the PDF; the post-processor pass is a pure function on that file.

Reference: PR #130 (Leprohon `transcribe_chunk.py`) is the prototype this method mirrors — same thesis (rebuild structural metadata that the OCR flatten loses), source-specific implementation.

### Structured extraction — three parallel subagents

The single OCR chunk is read by three independent Claude Code general-purpose subagents (**sonnet model**) in parallel, each with the identical prompt committed to `prompt.md`. Each writes JSONL to a distinct file under the agent directory (default `<source_dir>/raw/`, overridable via `--agent-dir` / `BECKERATH_AGENT_DIR`):

- Agent A → `<agent_dir>/agent-a.jsonl`
- Agent B → `<agent_dir>/agent-b.jsonl`
- Agent C → `<agent_dir>/agent-c.jsonl`

The three-subagent protocol absorbs stochastic transcription drift on the source's error-prone micro-features: slash-separated alternative dates (`3032/2982`), italic Horus-name parentheticals with non-ASCII diacritics (`-rê`, `-rî`, `-ê`, `-â`, `-â`), `etwa`/`ca.` approximate prefixes, and the Egyptian-vs-Greek name pair format (`Schoschenq I. (Sesonchis)`).

### Merge

```
cd pipeline && uv run python pipeline/authority/sources/beckerath-1997-chronologie/merge.py
```

`merge.py` groups rows by `beckerath_id`, takes a per-field majority vote, writes `reconciled.jsonl` (committed), and writes `merge-disagreements.txt` (committed) listing every row whose fields didn't unanimously agree. The merge is pure Python with no LLM calls; re-running on identical agent outputs produces byte-identical results.

`merge.py` is structurally the Kitchen-tipe merge with three adaptations:

- `kitchen_id` → `beckerath_id` throughout.
- The `_sort_key` reads `dynasty`, `sub_line`, and `sequence_in_dynasty` directly off each row (Beckerath uses pure `{dyn:02}.{seq:02}` IDs without compound prefix encoding) and orders rows by `(dynasty_int, sub_line_rank, sequence)`. The `sub_line` rank places `null` (main line) first and falls back to alphabetical for non-null values.
- `DEFAULT_AGENT_DIR` points at this source dir's `raw/`.

Sentinel-null normalisation (`"none"`, `"-"`, `"—"`, `"n/a"`, etc. → `null`) is retained verbatim from Kitchen-tipe.

### Review

Per ADR-017 step 6:

- **LLM review (planned for this source):** after the 3-subagent merge, the `egyptologist-reviewer` Claude Code subagent walks every entry in `merge-disagreements.txt`, cross-checks against the PDF, and flags rows where the majority vote is wrong. The main agent applies flagged corrections to `reconciled.jsonl` via a committed override snippet in `fix_rows.py` and records each change in `merge-disagreements.txt` under `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED`. **This is an LLM checking an LLM.** Better than unreviewed merge output, but not scholarly validation.
- **Human review (required, NOT yet done on this source):** an actual Egyptologist reads a sample of king rows against Beckerath's printed PDF and signs off. Until that happens, this extract is **provisional**.

## Audit trail

- PDF (SHA-256 pinned below; not committed) → JPEG renders at `$TMPDIR/beckerath_scan/scan-105.jpg` … `scan-109.jpg` (regenerable via `pdftoppm -r 100 -f 105 -l 109`)
- JPEG renders → `raw/chunk-p105-p109.md` (Claude Code subagent OCR; not committed, per-transcriber regenerable)
- `raw/chunk-p105-p109.md` → three per-extraction-agent JSONLs at `raw/agent-{a,b,c}.jsonl` (Claude Code subagents; non-deterministic; not committed)
- three per-agent JSONLs → `reconciled.jsonl` (deterministic merge, committed)
- `merge-disagreements.txt` (committed) lists every field where extraction agents disagreed plus the majority-vote resolution and the LLM reviewer's overrides.

## PDF hash pinning

Source PDF SHA-256: `f407eb4123872d875cb80590a2e840a50069c3596b06f79146a13e170968ca1c`. A reviewer re-running the pipeline against a PDF with a different hash should not expect byte-for-byte output reproduction; model outputs are stochastic, and the committed `reconciled.jsonl` is the source of truth.

## Physical vs printed pages

This PDF is a **double-page-spread** scan: each physical PDF page renders two facing book pages side-by-side (e.g. PDF p105 contains book pp. 186 left / 187 right). Anhang A starts on the right side of PDF p105 (book p187, the title `A. CHRONOLOGISCHE ÜBERSICHT ÜBER DIE GESCHICHTE ALTÄGYPTENS`) and continues through PDF p108 (book pp 192/193). The *Supplement zu A* runs from book p193 (right of PDF p108) through book p194 (left of PDF p109).

Per ADR-017, `reconciled.jsonl` cites the **physical PDF page range** (`"105-109"`) per row — a reviewer opens the PDF at physical pp 105-109 to verify any row; printed page numbers 186-194 are preserved inline in `raw/chunk-p105-p109.md` for scholarly cross-reference.
