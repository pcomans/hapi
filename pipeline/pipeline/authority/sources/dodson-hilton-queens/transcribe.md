# Transcription method — Dodson & Hilton 2004

Per ADR-017 and `docs/playbook-phase-0-ocr-transcription.md`. Seven chunks landed so far (Power-and-Glory, Amarna Interlude, Ramesside sub-blocks, Head of the South, Seizers of the Two Lands, Kings and Commoners, The Founders); further chunks (remaining chapters 1 OK, 2 SIP Dyn 14-17, 4 3IP, 5 LP/Ptolemaic) follow the same method.

## Inputs

1. `proprietary/books/Dodson & Hilton 2004 - Complete Royal Families.pdf` — 282 physical pages, ~151 MB. Not committed.
2. Scope:
   - **Chunk 1 (PR #37, merged):** chapter 3 *The New Kingdom* → section *The Power and the Glory* → *Brief Lives* sub-block. Printed pp. 137–141, physical PDF pp. 126–130 (offset +11). `pdf_pages: "126-130"` on every row.
   - **Chunk 2 (PR #38, merged):** chapter 3 *The New Kingdom* → section *The Amarna Interlude* → *Brief Lives* sub-block. Printed pp. 154–157, physical PDF pp. 142–145 (offset +12). `pdf_pages: "142-145"` on every row. Narrative prose pp. 142–153 NOT extracted.
   - **Chunk 3 (merged) — three sub-blocks:**
     - *The House of Ramesses* — Brief Lives. Printed pp. 170–175, physical PDF pp. 157–162 (offset +13). `pdf_pages: "157-162"` on every row. Narrative prose pp. 158–169 NOT extracted.
     - *The Feud of the Ramessides* — Brief Lives. Printed pp. 182–183, physical PDF pp. 169–170 (offset +13). `pdf_pages: "169-170"`. Narrative prose pp. 176–181 NOT extracted.
     - *The Decline of the Ramessides* — Brief Lives + Unplaced sub-section. Printed pp. 192–194, physical PDF pp. 178–180 (offset +14). `pdf_pages: "178-180"`. Narrative prose pp. 184–191 NOT extracted. Unplaced sub-block (`Anuketemheb`, `Taiay`) sits at the bottom of printed p. 194, under its own `Unplaced` sub-heading.
   - **Chunk 4 (merged) — Head of the South:** chapter 2 *The 1st Intermediate Period, the Middle Kingdom and 2nd Intermediate Period* → section *The Head of the South* → *Brief Lives* sub-block + trailing *Unplaced*. Printed pp. 88–89, physical PDF pp. 81–82 (offset +7). `pdf_pages: "81-82"` on every row. Covers the 11th Dynasty transition — Mentuhotep II's Deir el-Bahari mortuary-chapel wives (Ashayet, Henhenet, Kawit, Kemsit, Sadhe), plus the Inyotef-line kinship web (Iah, Neferu I, Neferu II, Inyotef A the nomarch) and trailing Unplaced `Neferkayet`. Narrative prose for the 11th Dyn chapter body (printed pp. 81–87) NOT extracted.
   - **Chunk 5 (merged) — Seizers of the Two Lands:** chapter 2 → section *Seizers of the Two Lands* → *Brief Lives* sub-block + trailing *Unplaced*. Printed pp. 96–99, physical PDF pp. 88–91 (offset +8). `pdf_pages: "88-91"` on every row. Covers the full 12th Dynasty Middle Kingdom proper (Amenemhat I → Sobkneferu), 45 placed + 3 Unplaced (`Didit`, `Neferet Q`, `Sithathor Q`, all sisters-of-unknown-kings). Flagship entries: `Neferuptah B` (potential female-king-before-premature-death with a cartouche), `Sobkneferu` (later-female-king), the `Khnemet` / `Khnemetneferhedjet I Weret` / `Khnemetneferhedjet II Weret` / `Khnemetneferhedjet A` homonym cluster, and five lacuna-bearing `dh_id`s (`Khnemet[...]`, `Nensed[...]`, `Sit[...]JA`, `[...]12A`, `[...]12B`). Narrative prose for the 12th Dyn chapter body and intervening pages (printed pp. 90–95) NOT extracted.
   - **Chunk 6 (merged) — Kings and Commoners:** chapter 2 → section *Kings and Commoners* → *Brief Lives* sub-block + trailing *Unplaced*. Printed pp. 108–113, physical PDF pp. 98–103 (offset +10, no mid-chunk drift within the Brief Lives sub-block). `pdf_pages: "98-103"` on every row. Covers the 13th Dynasty at the start of the Second Intermediate Period (Sobkhotep I–VII, Neferhotep I, Iy + extended-family commoners), 91 placed + 17 Unplaced (`Ahhotepti` through `[...]djeb` — sisters/daughters/sons/wives of unknown kings, clustering around the post-Dyn-13 royal-family lacuna). Printed page 110 / physical page 100 is a full-bleed photograph of the Black Pyramid at Dahshur with zero Brief Lives entries; the chunk file's page-header sequence skips 110. Introduces the first **cross-dynasty cross-section duplicate**: `Hetepti` (KM; M2L; UWC) has her full Brief Life in the Seizers chunk (Dyn 12) and a single-line stub `See previous section.` here (Dyn 13), because D&H treats her as a Dyn-12-mother-of-Amenemhat-IV individual but also wants to flag her presence at the 13-Dyn boundary for cross-reference. The composite `(dh_id, sub_period)` key handles this cleanly; the Seizers row carries the full kinship data, the Kings-and-Commoners row is a stub with notes-only. Narrative prose for the 13th Dyn chapter body and intervening pages (printed pp. 100–107) NOT extracted.
   - **Chunk 7 (this PR) — The Founders:** chapter 1 → section *The Founders* → *Brief Lives* sub-block + trailing *Unplaced*. Printed pp. 48–49, physical PDF pp. 44–45 (offset +4, no mid-chunk drift). `pdf_pages: "44-45"` on every row. Covers the 1st, 2nd and 3rd Dynasties (Early Dynastic Period) — D&H's section title lists all three dynasties jointly. 15 placed + 11 Unplaced = 26 rows; the smallest Brief Lives sub-block in D&H. Flagship entries: the 1st-Dyn royal wives (`Benerib` wife of Hor-Aha, `Herneith` probable wife of Djer, `Neithhotep A` the earliest named royal lady tied to the Naqada tomb, `Meryetneith A` mother of Den who holds a stela without serekh), the 2nd-Dyn wife `Nymaathap A` (wife of Khasekhemwy; her posthumous cult is referred to in Metjen's early-4th-Dynasty tomb at Saqqara), and the 3rd-Dyn wife `Hotephirnebty` (wife of Djoser). `Nymaathap A`'s prose wraps across the p. 48/49 print boundary — Gemini's OCR dropped the continuation `"4th Dynasty tomb of Metjen at Saqqara (LS6)."` at the top of p. 49, which `transform_founders.py` restores pre-extraction. Per-row dynasty assignment is coarse (`dynasty: 1` for every row) with D&H's section placement as authoritative; Phase A refines per-individual dynasty from the `notes` cues (`Shepsetipet`'s notes explicitly say `"2nd Dynasty"`; `Redji`'s notes explicitly say `"3rd Dynasty"`). Narrative prose for the Ch 1 Early Dynastic chapter body (printed pp. 44–47) NOT extracted.

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

**Chunk 2 (Amarna Interlude, PR #38):** 4 pages of Brief Lives at `raw/source-p142-p145.pdf`. Extracted via the same `pypdf` one-shot (0-indexed physical pages 141–144 inclusive; see PDF-split preamble above).

**Chunk 2 OCR — Claude Opus 4.6 succeeded.** Per the ADR-017 § "Amendment 2026-04-15" requirement to re-attempt Opus OCR before escalating to Gemini, the Amarna chunk was OCR'd by Claude Opus 4.6 in the main session (not a subagent) on 2026-04-15. Unlike chunk 1 — where both a Claude Code subagent and a main-session attempt were blocked, and a later retry produced a principled copyright-scope refusal — the Amarna main-session attempt produced the OCR markdown without a block or refusal. The likely contributing factors are smaller chunk size (4 pages vs 5), lower density of mortuary / reburial prose compared to the Thutmoside Brief Lives, and main-session context that fully surfaced the ADR-017 scholarly-extraction framing. The Amarna chunk therefore follows the original ADR-017 step 1 path (Claude Opus 4.6 OCR with no external-model fallback).

**Chunk 3 OCR — Claude Opus 4.7 (1M context) subagents succeeded across all three sub-blocks.** Per the ADR-017 amendment, the default path is a Claude Code OCR subagent on the latest Opus. All three Ramesside sub-blocks (House 6pp, Feud 2pp, Decline 3pp) were OCR'd by parallel Claude Opus 4.7 subagents on 2026-04-16 with a fair-use scholarly-extraction framing. No refusal, no block. Outputs: `raw/chunk-p157-p162.md` (~126 entries), `raw/chunk-p169-p170.md` (10 entries), `raw/chunk-p178-p180.md` (35 entries). This restores the playbook default (subagent OCR) — chunk 2's main-session deviation was specific to chunk 2.

**Chunk 4 OCR — Claude Opus 4.7 (1M context) main-session pass succeeded.** Head of the South is a small 2-page sub-block (printed pp. 88–89 / physical 81–82); OCR was performed by Claude Opus 4.7 in the main session on 2026-04-16 with the same scholarly-extraction framing as chunk 3. Output: `raw/chunk-p81-p82.md` (13 entries — 12 placed + 1 Unplaced `Neferkayet`). No refusal, no block. The main-session (rather than subagent) path was used here only because the PDF-split sub-PDF `raw/source-p81-p82.pdf` was already on disk and the main session was already in the Read-context for downstream scoping work — it would otherwise be a subagent call per the playbook default. The three extraction subagents (agent-{a,b,c}-headofsouth.jsonl) ran against a rule-based `prompt-headofsouth.md` (no per-row answer enumeration — re-written and re-run after the first attempt leaked per-row values; see `merge-disagreements.txt` for the resulting genuine field-level disagreement on `Inyotef A.children_names` probability-hedge wording, resolved 2-1 by majority vote in favour of `"Mentuhotep I (probably)"`).

**Chunk 5 OCR — Google Gemini 3.1 Pro (web UI paste) after both subagent AND main-session Opus were content-filter-refused.** Seizers of the Two Lands is a 4-page sub-block (printed pp. 96–99 / physical 88–91); the Claude Code subagent OCR refused with `"Output blocked by content filtering policy"` (same pattern as chunk 1 Power and Glory), and the main-session Claude Opus 4.7 Read → Write chunk-file attempt also did not produce output (the Read surfaced all 4 pages to the session but the downstream Write of the transcribed prose was not attempted by the time the user manually escalated to Gemini). Per ADR-017 § "Amendment 2026-04-15: external-model fallback for copyright-refusal", the user performed the Gemini paste via the Gemini 3.1 Pro web UI using the verbatim prompt at `transcribe-gemini-prompt.md`, saving the result to `/Users/philipp/Downloads/source-p88-p91.txt`. The main-session Opus then moved the text into `raw/chunk-p88-p91.md`, fixing two post-OCR issues: (a) Gemini flattened D&H's bold-italic typography for females to plain bold, so the chunk file was main-session-edited to restore `***Name***` for every female entry (inferred from role codes and prose pronouns — wife/daughter/mother-of clauses → female; son/nomarch/GF → male); and (b) page headers (`## p. 96` etc.) were added to match the other chunks' chunk-file structure. The three extraction subagents (agent-{a,b,c}-seizers.jsonl) ran against a rule-based `prompt-seizers.md` — no per-row answer enumeration. `merge-disagreements.txt` records the genuine field-level disagreements resolved by majority vote (mostly `hedge` prose-wording variations on `spouse_names` / `father_name` strings for hedged-relative entries).

**External-model fallback note.** Gemini 3.1 Pro's daily quota was hit on 2026-04-19 for the parallel `/gemini review` path on open PRs; Gemini web UI paste OCR remained available (a separate quota). For future chunks where the same refusal pattern surfaces, the fallback order remains (1) subagent OCR → (2) Claude Opus 4.7 main-session Read+Write → (3) user manual Gemini paste per this chunk's precedent.

**Chunk 7 OCR — user-assisted Gemini 3.1 Pro paste, chosen pre-emptively.** The Founders chunk is a small 2-page sub-block (printed pp. 48–49 / physical 44–45) but given the content-filter pattern observed on chunks 5 and 6, the Gemini-paste path was chosen pre-emptively without attempting subagent OCR or main-session Write first. Gemini's output unlike chunks 5 and 6 **preserved D&H's bold-italic-for-females typography correctly**, so no main-session typography restoration was needed. Main-session post-processing via the committed `transform_founders.py` script handled: (a) prepending the standard H1 title + OCR-header block; (b) inserting page headers `## p. 48` and `## p. 49` at entry boundaries; (c) upgrading the bare `## Brief Lives` / `### Unplaced` markdown headings to the D&H-styled dotted variants; (d) **restoring Nymaathap A's page-break continuation** — D&H's prose for her wraps across the p. 48/49 print boundary ending with `"referred to in the early-"` on p. 48 col 3 and continuing with `"4th Dynasty tomb of Metjen at Saqqara (LS6)."` at the top of p. 49 col 1 before Perneb's entry. Gemini's OCR dropped the continuation entirely; main-session Read on the source PDF recovered it and the transform script hard-codes the joined complete paragraph (resolving the soft-hyphen line-break artefact to a plain space between `"early"` and `"4th"`); and (e) appending the standard `## Row count` footer. The three extraction subagents then ran against a rule-based `prompt-founders.md` that implements the **role-code-first sex inference** rule established in chunk 6; all three agents independently reported zero typography tiebreakers used on the 26 rows (role-code + prose-kinship resolved every entry including the four roleless entries Batirytes, Benerib, Khenthap, Serethor). `merge-disagreements.txt` shows genuine prose-wording disagreements resolved by vote. Post-merge corrections in `fix_rows.py` (`FOUNDERS_CORRECTIONS`) refine `dynasty` to 2 or 3 for the four Unplaced rows whose notes prose explicitly contradicts the chunk-default `dynasty: 1` from D&H's joint-dynasty section placement (`Shepsetipet`, `Sitba`, `Syhefernerer` → Dyn 2 per their `"2nd Dynasty;"` opener; `Redji` → Dyn 3 per her `"dated stylistically to the 3rd Dynasty."` closer). No `notes`-field corrections are needed on this chunk because the soft-hyphen resolution happens in the single pre-extraction layer (`transform_founders.py`) and the agents read the already-corrected text; `diff_founders.py` verifies byte-equivalence between the corrected chunk file and the reconciled rows.

**Chunk 6 OCR — user-assisted Gemini 3.1 Pro paste after subagent AND main-session Write were content-filter-refused.** Kings and Commoners is the largest Ch 2 sub-block at 6 physical pages / 108 entries (printed pp. 108–113 / physical 98–103). Same refusal pattern as chunk 5: Claude Code subagent OCR refused with `"Output blocked by content filtering policy"`; the main-session Claude Opus 4.7 Read surfaced all 6 pages but the downstream Write of the transcribed prose into `raw/chunk-p98-p103.md` was itself content-filter-blocked. Per the user's offer on 2026-04-19, the paste-through-Gemini-web-UI fallback activated: user opened `raw/source-p98-p103.pdf` + `transcribe-gemini-prompt.md`, pasted into Gemini 3.1 Pro, saved output to `/Users/philipp/Downloads/source-p98-p103.txt`. Main-session post-processing then transformed the Gemini output via a dedicated Python script (`/tmp/claude/transform_kc.py` — ephemeral, not committed) that (a) restored `***Name***` bold-italic for the 62 female entries (males derived from role codes + prose-kinship verbs plus a pre-committed male list of 44 entries); (b) inserted the 5 `## p. NNN` page headers at the correct entry boundaries (p. 108, 109, 111, 112, 113 — no p. 110 because physical page 100 is photo-only); (c) fixed five systematic OCR drifts Gemini introduced (`luhetibu → Iuhetibu` across 4 entries + cross-references; `ly → Iy` primary entry + many cross-refs; `laib → Iaib` cross-reference; `Nedjesankh-lu → Nedjesankh-Iu` in Hatshepsut C's notes; `Neferhotep 1 → Neferhotep I` in Kemi A/B notes — Gemini rendered D&H's capital-I as lowercase-l and Roman-numeral I as digit 1 in specific positions); and (d) appended the standard row-count footer. The three extraction subagents (agent-{a,b,c}-kingsandcommoners.jsonl) then ran against a rule-based `prompt-kingsandcommoners.md` that implements the **role-code-first sex inference** rule per the Seizers PR's code-reviewer MEDIUM feedback — typography is now the last-resort tiebreaker only when both role-code and prose-kinship signals are absent. All three agents independently reported zero typography tiebreakers used on this chunk's 108 rows; `merge-disagreements.txt` records the genuine prose-wording disagreements on hedged-spouse fields (e.g. `Iy.spouse_names` — two agents emitted `(either) (probably)` / one emitted `(either, probable)`; majority vote picked `(either) (probably)`).

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

Each chunk's OCR markdown is fed to three independent extraction subagents running the identical chunk-specific prompt. Each subagent writes JSONL to `<agent_dir>/agent-{a,b,c}-<chunk_suffix>.jsonl` (hyphen between the agent-tag and the chunk suffix — `merge.py._load_agent_chunks` matches the glob `agent-{tag}-*.jsonl`) where `<agent_dir>` defaults to `<source_dir>/raw/` — the same sandbox-writable path rule that Kitchen adopted. Chunk files:

| Chunk | Prompt | Agent outputs | Expected rows |
|---|---|---|---|
| Power and Glory (p126–p130) | `prompt.md` | `agent-{a,b,c}-power.jsonl` | 59 |
| Amarna Interlude (p142–p145) | `prompt-amarna.md` | `agent-{a,b,c}-amarna.jsonl` | 41 |
| Ramesside (p157–p162 + p169–p170 + p178–p180) | `prompt-ramesside.md` | `agent-{a,b,c}-ramesside.jsonl` | 170 |

`merge.py` discovers all `agent-{tag}-*.jsonl` files per agent tag, unions their rows, then majority-votes per-field across the three agents' unified dicts. The primary key is the composite `(dh_id, sub_period)` — `dh_id` alone is not unique across the full reconciled file because D&H occasionally lists the same individual under two Brief Lives sub-sections (chunk 3 introduced this case with `Takhat A` and `Isetneferet C`; see README § Schema). Adding a future chunk (earlier chapters) is still just another prompt file + another triple of `agent-{a,b,c}-<suffix>.jsonl` output files; `merge.py` does not need to know about it in advance.

**The Ramesside PR retired the legacy unsuffixed filenames.** Originally Pre-Amarna rows lived in `agent-{a,b,c}.jsonl` (no suffix) and follow-up chunks added `-amarna`/`-ramesside` suffixes. The Ramesside PR renamed Pre-Amarna raw files to `-power` and dropped the base-unsuffixed branch in `_load_agent_chunks`. Every chunk from here on carries an explicit chunk suffix.

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

**Head of the South chunk offset (chapter 2, 11th Dynasty).** The offset earlier in the book is `+7` at the Head of the South Brief Lives sub-block — considerably smaller than Ch 3's `+11→+14` range because fewer genealogical-chart-spread scan anomalies have accumulated by that point. The `+7` offset is uniform across the Brief Lives sub-block's two pages (printed 88–89 / physical 81–82). No mid-chunk drift.

**Head of South chunk verification points:**
- Physical p. 81 = printed p. 88 (offset +7; start of Brief Lives)
- Physical p. 82 = printed p. 89 (offset +7; end of Brief Lives + Unplaced `Neferkayet`)
- Physical p. 83 = printed p. 90 (offset +7; outside chunk scope — next section "The Great Domain")

**Seizers of the Two Lands chunk offset (chapter 2, 12th Dynasty).** The offset drifts from `+7` (Head of South boundary at printed p. 89) to `+8` by the time the Seizers Brief Lives sub-block opens at printed p. 96 / physical p. 88. The drift is the +1 absorbed by a 2-page genealogical-chart spread at some point between printed pp. 90–95 (the 12th Dyn / Amenemhat chart, or similar) captured as a single physical page in the scan. The `+8` offset is uniform across the Seizers Brief Lives sub-block's four pages (printed 96–99 / physical 88–91). No mid-chunk drift within Seizers.

**Seizers chunk verification points:**
- Physical p. 88 = printed p. 96 (offset +8; start of Brief Lives — "Seizers of the Two Lands" section heading)
- Physical p. 91 = printed p. 99 (offset +8; end of Brief Lives + Unplaced `Didit` / `Neferet Q` / `Sithathor Q`)

**Kings and Commoners chunk offset (chapter 2, 13th Dynasty).** The offset drifts from `+8` (Seizers boundary at printed p. 99) to `+10` by the time the Kings and Commoners Brief Lives sub-block opens at printed p. 108 / physical p. 98. The drift is +2 absorbed by two 2-page genealogical-chart spreads between printed pp. 100–107 (the 13th Dyn / Sobkhotep chart, or similar) captured as single physical pages in the scan. The `+10` offset is uniform across the Kings and Commoners Brief Lives sub-block's six pages (printed 108–113 / physical 98–103). No mid-chunk drift within the chunk.

**Kings and Commoners chunk verification points:**
- Physical p. 98 = printed p. 108 (offset +10; start of Brief Lives — "Kings and Commoners" section heading)
- Physical p. 100 = printed p. 110 (offset +10; full-bleed photograph of the Black Pyramid at Dahshur — no Brief Lives entries on this page, so the chunk file's page-header sequence skips `## p. 110`)
- Physical p. 103 = printed p. 113 (offset +10; end of Brief Lives + Unplaced `Ahhotepti` through `[...]djeb`)

The offset continues to drift (incrementally, through the later-SIP / Dyn 17 Brief Lives sub-blocks yet to be extracted) before reaching the Ch 3 `+11`. Each Ch 2 follow-up chunk must re-verify the offset at its own boundaries.

**The Founders chunk offset (chapter 1, Dyn 1/2/3 — Early Dynastic).** The earliest chapter in D&H, so offset is small: `+4` at the Brief Lives sub-block boundaries. The offset is uniform across the Brief Lives sub-block's two pages (printed 48–49 / physical 44–45). No mid-chunk drift.

**Founders chunk verification points:**
- Physical p. 44 = printed p. 48 (offset +4; start of Brief Lives — "The Founders" section heading)
- Physical p. 45 = printed p. 49 (offset +4; end of Brief Lives + Unplaced `Khnemetptah` through `Wadjetefni`)

Offset grows monotonically forward in the book: Founders `+4` → Head of South `+7` → Seizers `+8` → Kings and Commoners `+10` → Ch 3 `+11→+14`. The drift is driven by 2-page genealogical-chart spreads scanned as single physical pages; each such anomaly adds `+1` to the offset.

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
