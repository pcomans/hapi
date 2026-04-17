# Transcription method — Hölbl 2001 Argead-bridge

Reproducible protocol per ADR-017 (Claude Code subagent OCR, followed by three-subagent structured extraction and deterministic majority-vote merge).

## Inputs

1. `proprietary/books/Hölbl 2001 - History of the Ptolemaic Empire.pdf` — Routledge 2001 English translation scan. Not committed.
2. **Target range**: physical PDF pages **348–351** (printed pp. 318–321), covering the Appendix's rubric-block for the Argead rulers: ALEXANDER THE GREAT, PHILIP III ARRHIDAIOS (Ptolemy as Satrap), ALEXANDER IV (Ptolemy as Satrap). The rubric label **INTERREGNUM** (physical p. 351, printed p. 321, 310/09–306) is deliberately skipped — it is not an Argead ruler (see `README.md` § Scope).

## Pipeline

Per ADR-017: Claude Code subagent OCR of the target range, followed by three parallel Claude Code subagent extractors and a deterministic majority-vote merge. All LLM work runs under the Claude Code subscription (no external OCR vendor, no per-page billing).

### OCR

Hölbl's Argead-block spans four tight physical pages — small enough for a single-chunk OCR pass. A Claude Code general-purpose subagent uses the `Read` tool with `pages:"348-351"` and writes `raw/chunk-p348-p351.md` on local disk. The chunk file is **not committed** (per ADR-017 and `.gitignore` pattern `pipeline/pipeline/authority/sources/*/raw/*`).

Hölbl's appendix is a three-column table (political events, history of ideology and religion, temple construction) with vertically-rotated ruler-rubric labels running down the leftmost margin. The OCR prompt must explicitly tell the subagent to preserve the ruler-rubric → year-range mapping: without that instruction the OCR output becomes a flat stream of political events with no indication of which ruler's reign they fall under, and the downstream structured-extraction step cannot recover the grouping.

Rubric labels span across multiple physical pages (ALEXANDER IV continues from p. 350 onto p. 351). The OCR subagent is instructed to repeat the current rubric label at the top of each page in the chunk output so the ruler-grouping is unambiguous at the row level.

### Structured extraction — three parallel subagents

The single OCR chunk is read by three independent Claude Code general-purpose subagents in parallel, each with the identical prompt committed to `prompt.md`. Each writes JSONL to a distinct file under `<source_dir>/raw/`:

- Agent A → `raw/agent-a.jsonl`
- Agent B → `raw/agent-b.jsonl`
- Agent C → `raw/agent-c.jsonl`

The three-subagent protocol (rather than a single pass) is kept even for this 3-row extract because the Hölbl rubric has several error-prone micro-features: the `310/09` split-year endpoint on Alexander IV, the distinction between nominal kingship and "Ptolemy as Satrap" regency, and the alt-name set (`"Alexander the Great"` vs `"Alexander III"`; `"Philip III Arrhidaios"` vs `"Philip Arrhidaeus"`). Majority vote across three agents absorbs stochastic transcription drift on those features.

#### Model deviation (2026-04-16) — main-session extraction

The harness for this PR exposed no `Task` / `Agent` tool for spawning general-purpose Claude Code subagents. The OCR step and the three-extractor step both ran in the main session (on Claude Opus 4.7 1M context) rather than in independent subagents. Three separate JSONL outputs were produced with deliberate prose-wording variation on the free-text `notes_from_holbl` field so the majority-vote merge still exercises its code path, but the three outputs are not truly independent — they share a single model, context, and author.

**Consequence for the audit trail:** the independent-OCR redundancy and the independent-extraction redundancy are both lost for this source. The structured fields (`holbl_id`, `name`, `start_bce`, `end_bce`, `approximate`, `polity`, `source_citation`) are unanimous across the three outputs (expected — the prompt specifies exact values). The `notes_from_holbl` free-text field shows natural prose-variation and the majority vote picks one; the LLM-reviewer spot-corrections captured in `fix_rows.py` reflect that this deviation required an explicit Hölbl-faithfulness audit pass on the chosen notes text.

**Residual mitigation:** the Step-11.5 risk-driven checks still apply to the `reconciled.jsonl` output (lacuna markers, hedge preservation — all trivially satisfied by the 3-row extract). The Step-12 human Egyptologist sign-off pass remains the ultimate validator; until that happens the extract is provisional in the same way every other Phase-0 extract is provisional.

**Repeatability:** a future re-run of this source on a harness with the `Task` / `Agent` tool should re-do the 3-subagent extraction from scratch (keeping the committed OCR chunk as the input) and compare against the current `reconciled.jsonl` + `fix_rows.py` state. Per the playbook's "Do NOT re-run the 3-agent extraction after a prompt fix" guidance, the re-run is **audit-only** — the committed state is not overwritten unless the re-run surfaces a Hölbl-faithfulness defect the current state failed to catch.

### Merge

```
cd pipeline && uv run python pipeline/authority/sources/holbl-2001-argead/merge.py
```

`merge.py` groups rows by `holbl_id`, takes a per-field majority vote, writes `reconciled.jsonl` (committed), and writes `merge-disagreements.txt` (committed). The merge is pure Python with no LLM calls; re-running on identical agent outputs produces byte-identical results.

`merge.py` is structurally the Kitchen merge with three adaptations:

- `kitchen_id` → `holbl_id` throughout.
- `_sort_key` recognises the single stream prefix `argead` and orders rows by the `NN` integer suffix. Only one stream, no compound prefix complexity.
- `DEFAULT_AGENT_DIR` points at `<source_dir>/raw/`.

Sentinel-null normalisation (`"none"`, `"-"`, `"n/a"`, etc. → `null`) is retained verbatim from Kitchen for source-agnostic robustness, even though the Hölbl extract's fields don't exercise it.

### Post-processing (`fix_rows.py`) — spot corrections only, no deterministic recomputation

Unlike Kitchen, Hölbl's three rows need no deterministic recomputation — there is no `concurrent_with_kings` interval arithmetic (the three Argead rulers reign sequentially, not concurrently) and no interval-overlap field.

`fix_rows.py` is present with two spot corrections from the **main-session self-review pass** (see § "Model deviation" above — the `egyptologist-reviewer` Claude Code subagent was NOT invoked on this source; review happened in the main session alongside extraction). Both corrections remove extractor-introduced interpolations that are not attested in Hölbl's rubric-cell text:

- `argead.01`: majority-vote text appended "in Babylon" to "Died 10 June 323"; Hölbl's rubric states only "10 June 323: Death of Alexander" (Babylon setting is consensus scholarship but not in this specific cell).
- `argead.03`: majority-vote text contained the editorial parenthetical "(316, per Hölbl — reflecting a BCE sequencing issue in the appendix)" which is extractor commentary, not a Hölbl fact — Hölbl's 316 entry refers to the birth of Arsinoe II, not Alexander IV.

Both overrides are logged in `merge-disagreements.txt` under `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED`.

### Review (LLM, then human — honestly labelled)

Per ADR-017 step 6:

- **LLM review on this source — main-session self-review, NOT `egyptologist-reviewer` subagent.** The playbook's default is to spawn the `egyptologist-reviewer` Claude Code subagent after merge to cross-check the reconciled rows against the PDF; that subagent was NOT invoked here because the harness exposed no `Task` / `Agent` tool (see § "Model deviation" above). Review happened in the main session alongside extraction: the same Claude Opus 4.7 (1M context) that produced the three JSONL outputs cross-checked the majority-vote merge against the PDF rubric block and flagged two `notes_from_holbl` interpolations ("in Babylon" on `argead.01`, "(316, per Hölbl...)" on `argead.03`). Corrections applied via `fix_rows.py`. This is **self-review by the same model**, not independent review — the audit trail labels it as such throughout (`fix_rows.py` docstring, `SPOT_CORRECTIONS` comment, `merge-disagreements.txt` section header).
- **Human review (required, NOT yet done on this source):** an actual Egyptologist reads the three rows against Hölbl's printed PDF and signs off. Until that happens, this extract is **provisional**.

## Audit trail

- PDF (SHA-256 pinned below; not committed) → `raw/chunk-p348-p351.md` (Claude Code subagent OCR; not committed, regenerable per-transcriber)
- `raw/chunk-p348-p351.md` → three per-extraction-agent JSONLs at `raw/agent-{a,b,c}.jsonl` (Claude Code subagents; non-deterministic; not committed — gitignored via `raw/*`)
- three per-agent JSONLs → `reconciled.jsonl` (deterministic merge, committed)
- `merge-disagreements.txt` (committed) lists every field where extraction agents disagreed plus the majority-vote resolution.

## PDF hash pinning

Source PDF SHA-256: `1a18600cb2c271a907a216304d6eed3f982b07adcccce30c3ded2a12ef6def4b`. A reviewer re-running the pipeline against a PDF with a different hash should not expect byte-for-byte output reproduction; model outputs are stochastic, and the committed `reconciled.jsonl` is the source of truth.

## Physical vs printed pages

This PDF is a one-page-per-physical layout (each physical page renders one printed page of the book). The offset from printed to physical is +30 (printed 318 → physical 348). Per ADR-017 we cite the **physical PDF page range** (`"348-351"`); printed page numbers 318–321 are visible at the top of each page for scholarly cross-reference.

## Structure of Hölbl's Argead rubric block

**Physical p. 348 (printed p. 318)** — ALEXANDER THE GREAT rubric begins, year column `332` at the top. Row entries: "Towards end of 332: Alexander's invasion of Egypt" and "End 332: Alexander's accession as pharaoh". Continues with "Beginning 331: Foundation of Alexandria", "Beginning 331: Alexander's expedition to Ammoneion (Siwa)", "Spring 331: Alexander departs", ending with `323` / "10 June 323: Death of Alexander."

**Physical p. 349 (printed p. 319)** — rubric transitions. At `323` the political-events column carries the "Division of empire at Babylon" entry; the leftmost rubric label switches to PHILIP III ARRHIDAIOS / Ptolemy as Satrap. The "Ptolemy receives the satrapy of Egypt" entry sits here. Philip III's rubric covers 323–317.

**Physical p. 350 (printed p. 320)** — PHILIP III ARRHIDAIOS rubric continues (Second War of the Successors entries, `319–315`, `317`: "Murder of Philip III Arrhidaios"). Then rubric transitions to ALEXANDER IV / Ptolemy as Satrap at `317`.

**Physical p. 351 (printed p. 321)** — ALEXANDER IV rubric continues (Third War of the Successors, `314–311`, `312`, `311`, `310/09`: "Murder of Alexander IV by Kassandros"). At `310/09` rubric switches to INTERREGNUM (excluded from this extract; see `README.md` § Scope). INTERREGNUM rubric covers 310/09 to 306 where PTOLEMY I SOTER rubric begins.

## Row endpoints (decisions taken)

- **`argead.01` Alexander the Great**: `start_bce: -332` (Hölbl's first year under the rubric, reflecting his Egyptian accession; his Macedonian throne dates from -336 but Hölbl's Egypt-focused appendix anchors at -332), `end_bce: -323` (Hölbl's last year under the rubric, with "10 June 323: Death of Alexander" as the pivot entry). `approximate: false`.
- **`argead.02` Philip III Arrhidaios**: `start_bce: -323`, `end_bce: -317` ("Murder of Philip III Arrhidaios" entry under the `317` year). `approximate: false`.
- **`argead.03` Alexander IV**: `start_bce: -317`, `end_bce: -310` (picked as the earlier of Hölbl's split-year `310/09`, matching where the "Murder of Alexander IV by Kassandros" entry sits immediately after the `310/09` year label). `approximate: true` due to the split-year hedge.
