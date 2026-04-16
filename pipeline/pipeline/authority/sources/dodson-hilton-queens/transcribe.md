# Transcription method — Dodson & Hilton 2004

Per ADR-017 and `docs/playbook-phase-0-ocr-transcription.md`. Three chunks landed so far (Power-and-Glory, Amarna Interlude, Ramesside sub-blocks); further chunks (earlier chapters) follow the same method.

## Inputs

1. `proprietary/books/Dodson & Hilton 2004 - Complete Royal Families.pdf` — 282 physical pages, ~151 MB. Not committed.
2. Scope:
   - **Chunk 1 (PR #37, merged):** chapter 3 *The New Kingdom* → section *The Power and the Glory* → *Brief Lives* sub-block. Printed pp. 137–141, physical PDF pp. 126–130 (offset +11). `pdf_pages: "126-130"` on every row.
   - **Chunk 2 (PR #38, merged):** chapter 3 *The New Kingdom* → section *The Amarna Interlude* → *Brief Lives* sub-block. Printed pp. 154–157, physical PDF pp. 142–145 (offset +12). `pdf_pages: "142-145"` on every row. Narrative prose pp. 142–153 NOT extracted.
   - **Chunk 3 (this PR) — three sub-blocks:**
     - *The House of Ramesses* — Brief Lives. Printed pp. 170–175, physical PDF pp. 157–162 (offset +13). `pdf_pages: "157-162"` on every row. Narrative prose pp. 158–169 NOT extracted.
     - *The Feud of the Ramessides* — Brief Lives. Printed pp. 182–183, physical PDF pp. 169–170 (offset +13). `pdf_pages: "169-170"`. Narrative prose pp. 176–181 NOT extracted.
     - *The Decline of the Ramessides* — Brief Lives + Unplaced sub-section. Printed pp. 192–194, physical PDF pp. 178–180 (offset +14). `pdf_pages: "178-180"`. Narrative prose pp. 184–191 NOT extracted. Unplaced sub-block (`Anuketemheb`, `Taiay`) sits at the bottom of printed p. 194, under its own `Unplaced` sub-heading.

## Pipeline

Per ADR-017: Claude Code subagent OCR of the target range, three parallel Claude Code subagent extractors, deterministic majority-vote merge, egyptologist-reviewer LLM pass, `fix_rows.py` deterministic post-processing.

### PDF-split preamble (new, not in Ryholt / Kitchen)

The source PDF is ~151 MB — above the 100 MB limit of the `Read` tool. The OCR subagent cannot open the book directly. Before spawning the OCR subagent, the main agent splits out the target page range into a small sub-PDF under `raw/source-pNNN-pMMM.pdf` using `pypdf`. For chunk 3 the three sub-blocks are non-contiguous (pp. 157–162, 169–170, 178–180), so three separate sub-PDFs are extracted:

```bash
# Run from <repo>/pipeline; path is repo-relative.
uv run --with pypdf python - <<'PY'
import pypdf
src = "../proprietary/books/Dodson & Hilton 2004 - Complete Royal Families.pdf"
r = pypdf.PdfReader(src)
for out_name, phys_range in [
    # Chunk 1 (Power and Glory):        range(125, 130)  # physical 126–130
    # Chunk 2 (Amarna Interlude):       range(141, 145)  # physical 142–145
    ("source-p157-p162.pdf", range(156, 162)),  # Chunk 3 — House of Ramesses
    ("source-p169-p170.pdf", range(168, 170)),  # Chunk 3 — Feud of the Ramessides
    ("source-p178-p180.pdf", range(177, 180)),  # Chunk 3 — Decline of the Ramessides
]:
    w = pypdf.PdfWriter()
    for i in phys_range:
        w.add_page(r.pages[i])
    with open(f"pipeline/authority/sources/dodson-hilton-queens/raw/{out_name}", "wb") as f:
        w.write(f)
PY
```

The sub-PDFs are gitignored (`raw/*`). The source PDF lives under `proprietary/` (repo-level gitignored). Physical-page labels in `source_citation.pdf_pages` refer to the **source-book** physical page numbers (e.g. `"157-162"`), not the sub-PDF's internal numbering — the sub-PDF is just a Read-size workaround, not a citation target.

### OCR

**Chunk 1 (Power and Glory, PR #37):** 5 pages of Brief Lives at `raw/source-p126-p130.pdf`. The chunk file is not committed.

**Chunk 2 (Amarna Interlude, this PR):** 4 pages of Brief Lives at `raw/source-p142-p145.pdf`. Extracted via the same `pypdf` one-shot (0-indexed physical pages 141–144 inclusive; see PDF-split preamble above).

**Chunk 2 OCR — Claude Opus 4.6 succeeded.** Per the ADR-017 § "Amendment 2026-04-15" requirement to re-attempt Opus OCR before escalating to Gemini, the Amarna chunk was OCR'd by Claude Opus 4.6 in the main session (not a subagent) on 2026-04-15. Unlike chunk 1 — where both a Claude Code subagent and a main-session attempt were blocked, and a later retry produced a principled copyright-scope refusal — the Amarna main-session attempt produced the OCR markdown without a block or refusal. The likely contributing factors are smaller chunk size (4 pages vs 5), lower density of mortuary / reburial prose compared to the Thutmoside Brief Lives, and main-session context that fully surfaced the ADR-017 scholarly-extraction framing. The Amarna chunk therefore follows the original ADR-017 step 1 path (Claude Opus 4.6 OCR with no external-model fallback).

**Chunk 3 OCR — Claude Opus 4.7 (1M context) subagents succeeded across all three sub-blocks.** Per the ADR-017 amendment, the default path is a Claude Code OCR subagent on the latest Opus. All three Ramesside sub-blocks (House 6pp, Feud 2pp, Decline 3pp) were OCR'd by parallel Claude Opus 4.7 subagents on 2026-04-16 with a fair-use scholarly-extraction framing. No refusal, no block. Outputs: `raw/chunk-p157-p162.md` (~126 entries), `raw/chunk-p169-p170.md` (10 entries), `raw/chunk-p178-p180.md` (35 entries). This restores the playbook default (subagent OCR) — chunk 2's main-session deviation was specific to chunk 2.

Gemini 3.1 Pro remains the committed fallback for any future chunk where Opus refuses; `transcribe-gemini-prompt.md` is retained verbatim for reproducibility of chunk 1 and any future fallback event.

**Model deviation from the playbook (chunk 1 only):** Anthropic's content-filtering policy blocked Claude Opus 4.6 from transcribing these five pages (both as a Claude Code subagent and in the main session via `Write`). The cause is not confirmed — a generic `"Output blocked by content filtering policy"` error — but plausibly the combination of archaeological photographs on the pages and the density of mortuary / reburial prose in the Brief Lives text. Claude Haiku accepted the task but produced sloppy OCR (`Saqqara → Sargass`, `TT226 → TT26`, `Amenemhat → Amenhotep` conflation, etc.).

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

Each chunk's OCR markdown is fed to three independent extraction subagents running the identical chunk-specific prompt. Each subagent writes JSONL to `<agent_dir>/agent-{a,b,c}<chunk_suffix>.jsonl` where `<agent_dir>` defaults to `<source_dir>/raw/` — the same sandbox-writable path rule that Kitchen adopted. Chunk files:

| Chunk | Prompt | Agent outputs | Expected rows |
|---|---|---|---|
| Power and Glory (p126–p130) | `prompt.md` | `agent-{a,b,c}-power.jsonl` | 59 |
| Amarna Interlude (p142–p145) | `prompt-amarna.md` | `agent-{a,b,c}-amarna.jsonl` | 41 |
| Ramesside (p157–p162 + p169–p170 + p178–p180) | `prompt-ramesside.md` | `agent-{a,b,c}-ramesside.jsonl` | ~171 |

`merge.py` discovers all `agent-{tag}-*.jsonl` files per agent tag, unions their rows, then majority-votes per-field across the three agents' unified dicts. The primary key is the composite `(dh_id, sub_period)` — `dh_id` alone is not unique across the full reconciled file because D&H occasionally lists the same individual under two Brief Lives sub-sections (chunk 3 introduced this case with `Takhat A` and `Isetneferet C`; see README § Schema). Adding a future chunk (earlier chapters) is still just another prompt file + another triple of `agent-{a,b,c}-<suffix>.jsonl` output files; `merge.py` does not need to know about it in advance.

**PR #38 cleanup retired the legacy unsuffixed filenames.** Originally Pre-Amarna rows lived in `agent-{a,b,c}.jsonl` (no suffix) and follow-up chunks added `-amarna`/`-ramesside` suffixes. The Ramesside PR renamed Pre-Amarna raw files to `-power` and dropped the base-unsuffixed branch in `_load_agent_chunks`. Every chunk from here on carries an explicit chunk suffix.

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

Chapter 3 *The New Kingdom* opens at printed p. 121 / physical p. 110 — offset +11 (physical = printed − 11). Verified at printed 136 / physical 125 (chapter opening photo) and printed 141 / physical 130 (end of Power and Glory Brief Lives).

**Amarna chunk offset drift.** The offset is `+11` through printed pp. 142–143 (physical 131–132) but changes to `+12` from printed p. 147 onwards. The cause is a two-page genealogical-chart spread at printed pp. 144–145 that the original scanner captured as a **single** PDF page (physical 134), while placing printed p. 146 before it (physical 133). This is a one-time scan-artifact jump, not a repeat drift — the `+12` offset holds stably from physical 135 through at least physical 146 (printed 158, start of "House of Ramesses"). For the Amarna Brief Lives sub-block specifically (printed pp. 154–157 / physical pp. 142–145), the `+12` offset is uniform. Every follow-up PR must re-verify the offset at both the chunk's first and last printed pages.

**Amarna chunk verification points:**
- Physical p. 131 = printed p. 142 (offset +11; chapter opening, "Historical Background")
- Physical p. 132 = printed p. 143 (offset +11)
- Physical p. 133 = printed p. 146 (scan anomaly)
- Physical p. 134 = printed p. 144–145 spread
- Physical p. 135 = printed p. 147 (offset +12; stable from here)
- Physical p. 142 = printed p. 154 (start of Brief Lives, offset +12)
- Physical p. 145 = printed p. 157 (end of Brief Lives, offset +12)
- Physical p. 146 = printed p. 158 (start of "House of Ramesses", offset +12; outside Amarna scope)

**Ramesside chunk offset drifts.** The +12 offset stable at the start of the Ramesside range shifts twice:

1. **+12 → +13 at printed pp. 160–161 (physical p. 148).** The 19th Dynasty part 1 genealogical-chart spread spans two printed pages but was captured as a single PDF page (a scanner two-page-spread-as-one-page, same pattern as the Amarna chunk's pp. 144–145 anomaly). The offset holds at +13 from physical p. 148 through physical p. 172 (printed p. 185).
2. **+13 → +14 at printed pp. 186–187 (physical p. 173).** The 20th Dynasty genealogical-chart spread has the same single-page-spread capture, shifting the offset again. Holds at +14 from physical p. 174 through the end of the Decline chunk (physical p. 180 = printed p. 194) and continues into the 21st Dynasty section beyond this PR's scope.

**Ramesside chunk verification points:**
- Physical p. 146 = printed p. 158 (start of "House of Ramesses", offset +12)
- Physical p. 147 = printed p. 159 (offset +12)
- Physical p. 148 = printed pp. 160–161 spread (19th Dyn pt 1 chart)
- Physical p. 149 = printed p. 162 (offset +13; stable from here)
- Physical p. 157 = printed p. 170 (start of House Brief Lives, offset +13)
- Physical p. 162 = printed p. 175 (end of House Brief Lives, offset +13)
- Physical p. 169 = printed p. 182 (start of Feud Brief Lives, offset +13)
- Physical p. 170 = printed p. 183 (end of Feud Brief Lives, offset +13)
- Physical p. 173 = printed pp. 186–187 spread (20th Dyn chart)
- Physical p. 174 = printed p. 188 (offset +14; stable from here)
- Physical p. 178 = printed p. 192 (start of Decline Brief Lives, offset +14)
- Physical p. 180 = printed p. 194 (end of Decline Brief Lives + Unplaced, offset +14)

Every follow-up PR must re-verify the offset at both the chunk's first and last printed pages; each two-page chart spread captured as a single physical page adds +1 to the offset.

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
