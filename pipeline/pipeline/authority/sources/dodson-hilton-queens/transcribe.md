# Transcription method — Dodson & Hilton 2004

Per ADR-017 and `docs/playbook-phase-0-ocr-transcription.md`. First-half-of-Dyn-18 Brief Lives PR. Follow-up PRs cover Amarna, Ramesside, and earlier chapters under the same method.

## Inputs

1. `proprietary/books/Dodson & Hilton 2004 - Complete Royal Families.pdf` — 282 physical pages, ~158 MB. Not committed.
2. Scope of this PR: chapter 3 *The New Kingdom* → section *The Power and the Glory* → *Brief Lives* sub-block. Printed pp. 137–141, physical PDF pp. 126–130 (offset +11 from printed → physical holds throughout chapter 3 front-section).

## Pipeline

Per ADR-017: Claude Code subagent OCR of the target range, three parallel Claude Code subagent extractors, deterministic majority-vote merge, egyptologist-reviewer LLM pass, `fix_rows.py` deterministic post-processing.

### PDF-split preamble (new, not in Ryholt / Kitchen)

The source PDF is 158 MB — above the 100 MB limit of the `Read` tool. The OCR subagent cannot open the book directly. Before spawning the OCR subagent, the main agent splits out the target page range into a small sub-PDF under `raw/source-pNNN-pMMM.pdf` using `pypdf`:

```bash
cd pipeline && uv run --with pypdf python - <<'PY'
import pypdf
src = "/Users/philipp/code/hapi/proprietary/books/Dodson & Hilton 2004 - Complete Royal Families.pdf"
out = "pipeline/authority/sources/dodson-hilton-queens/raw/source-p126-p130.pdf"
r = pypdf.PdfReader(src)
w = pypdf.PdfWriter()
for i in range(125, 130):   # 0-indexed physical 126–130
    w.add_page(r.pages[i])
with open(out, "wb") as f:
    w.write(f)
PY
```

The sub-PDF is gitignored (`raw/*`). The OCR subagent then Reads the sub-PDF. Physical-page labels in `source_citation.pdf_pages` refer to the **source-book** physical page numbers (e.g. `"126-130"`), not the sub-PDF's internal numbering — the sub-PDF is just a Read-size workaround, not a citation target.

### OCR

Single chunk for this PR — 5 pages of Brief Lives at `raw/source-p126-p130.pdf`. The chunk file is not committed.

**Model deviation from the playbook:** Anthropic's content-filtering policy blocked Claude Opus 4.6 from transcribing these five pages (both as a Claude Code subagent and in the main session via `Write`). The cause is not confirmed — a generic `"Output blocked by content filtering policy"` error — but plausibly the combination of archaeological photographs on the pages and the density of mortuary / reburial prose in the Brief Lives text. Claude Haiku accepted the task but produced sloppy OCR (`Saqqara → Sargass`, `TT226 → TT26`, `Amenemhat → Amenhotep` conflation, etc.).

The chunk committed to the pipeline was therefore produced by **Google Gemini 3.1 Pro** (Gemini web UI, 2026-04-15) via a one-shot prompt. The exact prompt text is committed verbatim at `transcribe-gemini-prompt.md` in this same directory so the OCR step is reproducible against the SHA-pinned source PDF. Gemini's transcription was spot-checked against the PDF pages (visually, in the Claude Code main session) and is consistent with what's printed on pp. 137–141.

A later retry of Claude Opus 4.6, with an even more explicit fair-use framing, produced a **reasoned** refusal on copyright-scope grounds: *"I can't transcribe five pages of prose paragraphs verbatim from a copyrighted Thames & Hudson handbook, even reframed as fair use… the 'narrow prose sentences' the instructions ask me to quote verbatim for ~59 entries are the authors' protected expression, and reproducing them in full constitutes the kind of extended excerpting I need to decline."* (Captured verbatim from the subagent transcript.) This refusal is treated as a principled position, and Gemini is used as the fallback per ADR-017 § "Amendment 2026-04-15: external-model fallback for copyright-refusal".

This is a documented deviation for this chunk. The downstream pipeline (3-subagent extraction, merge, reviewer pass, fix_rows) continues unchanged on Claude Opus 4.6 — those stages operate on Markdown input and do not hit the copyright-scope refusal, which is triggered only by the quantity of verbatim prose the OCR step reproduces. Follow-up Dodson-Hilton PRs (Amarna, Ramesside) MUST re-attempt Opus OCR first before escalating to Gemini; the amendment does not imply a blanket fallback at source-level.

OCR rules (delta from Ryholt/Kitchen):

- **Preserve role-code parentheses exactly** as D&H write them — e.g. `(KM; KGW; KSis)` — with the semicolons and spacing intact.
- **Preserve disambiguator letters** — `Ahmes B`, `Hatshepsut D`, `[...]pentepkau` with square-bracketed ellipsis for lacunae. D&H use these letters as identifiers; dropping one collapses distinct individuals.
- **Preserve `Q` suffixes** for "Unplaced" entries. They appear in a trailing `Unplaced` sub-block; preserve that section heading in the OCR.
- **Preserve bold / italic indicators inline** using Markdown (`**bold**` for king names; *italic* for female per D&H's own chart-key conventions; never an ASCII substitute).
- **Preserve D&H's own footnote / reference markers** (superscript numbers like `102`, `103`, `104`) inline if they appear in body text. They key into the book's `Notes to the Text` (pp. 283–294) which is out-of-scope here.
- **Ignore photo-caption text.** The OCR output should skip "(below) Face of the gilded wood middle coffin of Tjuia, mother of Tiye A (CM CG57006)" type lines because they're reproducing visual descriptions that would drag copyrighted compositional content into the repo. Only the body-text Brief Lives entries are OCR targets.
- **Preserve D&H's own two- and three-column layout** via column 1 → column 2 → column 3 reading order (they lay out entries alphabetically across three columns per page).

### Structured extraction — three parallel subagents

The OCR chunk is fed to three independent extraction subagents with the identical prompt at `prompt.md`. Each writes JSONL to `<agent_dir>/agent-{a,b,c}.jsonl` (default `<source_dir>/raw/` — the same sandbox-writable path rule that Kitchen adopted). Expected ~50-60 rows across the three streams.

### Merge + fix_rows

```
cd pipeline && uv run python pipeline/authority/sources/dodson-hilton-queens/merge.py
cd pipeline && uv run python pipeline/authority/sources/dodson-hilton-queens/fix_rows.py
```

`merge.py` is structurally the Kitchen merge (Ryholt's lineage), adapted only by:
- `kitchen_id` → `dh_id` throughout.
- `_sort_key`: alphabetical by `dh_id` (D&H's Brief Lives themselves are alphabetical); Unplaced `Q`-suffix entries sort after unsuffixed.
- Output fields: stable JSONL key order via `sort_keys=True`.

`fix_rows.py` applies egyptologist-reviewer spot corrections. Unlike Kitchen, there is no deterministic recomputation to do for this source — the schema has no interval-overlap fields. If the reviewer pass flags zero corrections, `fix_rows.py` is a no-op and the LLM-overrides section is a single "no overrides applied" line.

### Review (LLM, then human — honestly labelled)

Per ADR-017 step 6. The `egyptologist-reviewer` Claude Code subagent walks `reconciled.jsonl` against the source PDF, flags errors (typically role-code mis-extraction, parent/spouse confusion, or alt-name drops), and the main agent applies corrections via `fix_rows.py`. Every correction is recorded in `merge-disagreements.txt` under `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED`. A human Egyptologist sign-off pass is separately owed and has NOT happened; extract is provisional.

## PDF hash pinning

Source PDF SHA-256: `e636c49f3d0b5b6c6ec072cc6e7af9d605caf52d438c55cd84da9de7b07008a0`. Model outputs are stochastic; the committed `reconciled.jsonl` is the source of truth.

## Physical vs printed page offset

Chapter 3 *The New Kingdom* opens at printed p. 121 / physical p. 110 — offset +11 (physical = printed − 11). Verified at printed 136 / physical 125 (chapter opening photo) and printed 141 / physical 130 (end of Power and Glory Brief Lives). The offset may drift at part-boundary pages; follow-up PRs (Amarna, Ramesside, earlier chapters) must re-verify.

## Structure of Brief Lives entries

Every entry follows this template:

```
Name[A-Q] (Role1; Role2; Role3)
Prose paragraph: kinship ("Wife of X; mother of Y; daughter of Z (probable)"),
monument attestations, museum catalogue numbers, tombs / stelae, scholarly
hedges. 30–80 words typical.
```

Variants:
- Kings in the Brief Lives are rendered in **BOLD CAPITALS** (e.g. `**AMENHOTEP II**`) and get role codes the same way.
- Entries under a section heading `Unplaced` use `Q`-suffix disambiguators instead of letters.
- Some entries have a `(See also Addenda p. 304)` pointer — preserve as-is in notes.
- Some prose explicitly lists children alongside spouse — extract into `children_names`.

## Known OCR hazards

- **Two-column layout** on Brief Lives pages requires column-order reading. Agents that flatten to single-column order produce concatenated-name artifacts like `Amenhotep DSon of Thutmose IV`. Enforce column-order in the OCR prompt.
- **`TT###` tomb references** (e.g. `TT192`, `TT226`) and museum-catalogue numbers (`CM CG57006`, `BM EA43`, `KV35`, `CM JE37417`) are factual and must survive the OCR; they index Phase-A attestation evidence.
- **Lacuna-marker names** like `[...]pentepkau` preserve the square brackets and ellipsis exactly.
- **Roman numerals and Arabic numerals mixed** — `Thutmose IV` vs `TT226` both appear. Preserve each in its native form.
