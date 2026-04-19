# Transcription method — Hölbl 2001, Appendix (Argead bridge)

Reproducible protocol per ADR-017 (Claude Code subagent OCR, followed by three-subagent structured extraction and deterministic majority-vote merge).

## Inputs

1. `proprietary/books/Hölbl 2001 - History of the Ptolemaic Empire.pdf` — scanned Routledge 2001 English translation. Not committed to the repo.
2. **Target range**: physical PDF pages **349–351** (printed pp. 320–322), covering the first three reign banners of the Appendix (Alexander the Great → Philip III Arrhidaios → Alexander IV, 332–310 BCE). The Appendix as a whole spans physical pp. 347–378 (printed pp. 318–353); everything after the Alexander IV banner (Interregnum, Ptolemy I, Ptolemies II–XV) is deliberately excluded — those rulers are covered by pharaoh.se, and duplicating them here would create cross-source drift.

## Pipeline

Per ADR-017: Claude Code subagent OCR of the target range, followed by three parallel Claude Code subagent extractors and a deterministic majority-vote merge. All LLM work runs under the Claude Code subscription (no external OCR vendor).

### OCR

The three-page target range is small enough for a single-chunk OCR pass. A Claude Code general-purpose subagent uses the `Read` tool with `pages:"349-351"` and writes `raw/chunk-p349-p351.md` on local disk. The chunk file is **not committed** (per ADR-017 and `.gitignore` pattern `pipeline/pipeline/authority/sources/*/raw/*`).

The OCR output preserves Hölbl's four-column layout (Year | Political events | Ideology/religion | Temples) as Markdown tables, and records the rotated-90° reign banners from the leftmost column as section sub-headers so a reviewer can see which banner spans which year rows. Running headers ("Appendix", "Overview of the events discussed…") are preserved inline.

### Structured extraction — three parallel subagents

The single OCR chunk is read by three independent Claude Code general-purpose subagents in parallel, each with the identical prompt committed to `prompt.md`. Each writes JSONL to a distinct file under the agent directory (default `<source_dir>/raw/`, overridable via `--agent-dir` / `HOLBL_AGENT_DIR`):

- Agent A → `<agent_dir>/agent-a.jsonl`
- Agent B → `<agent_dir>/agent-b.jsonl`
- Agent C → `<agent_dir>/agent-c.jsonl`

The three-subagent protocol is kept even for this three-row source because (a) it enforces the invariant that the structured fields (`holbl_id`, `display`, `start_year`, `end_year`, `approximate`, `page`) must be reproduced identically by ≥2 of 3 agents for majority vote to converge, and (b) it's cheap — running the prompt three times on a three-page chunk takes seconds. For this extract all three agents converged unanimously on every structured field; only the prose `note` cells differed in wording.

### Merge

```
cd pipeline && uv run python pipeline/authority/sources/holbl-2001-argead/merge.py
```

`merge.py` groups rows by `holbl_id`, takes a per-field majority vote, writes `reconciled.jsonl` (committed), and writes `merge-disagreements.txt` (committed) listing every row whose fields didn't unanimously agree. The merge is pure Python with no LLM calls; re-running on identical agent outputs produces byte-identical results.

`merge.py` is structurally the `kitchen-tipe/merge.py` with three adaptations:

- `kitchen_id` → `holbl_id` throughout.
- `STREAM_ORDER` collapses to a single entry `{"argead": (0, 0)}` — all three rows share the `argead` prefix, so the sort key degenerates to sequence order (`argead.01` < `argead.02` < `argead.03`).
- `DEFAULT_AGENT_DIR` and the environment-variable name (`HOLBL_AGENT_DIR`) are source-specific.

Sentinel-null normalisation (`"none"`, `"-"`, `"n/a"`, etc. → `null`) is retained verbatim from the kitchen-tipe merge; for this extract it doesn't fire (no sentinel strings appear in any agent's output), but it is kept as a defensive invariant.

### Post-processing (`fix_rows.py`) — not needed for this source

This extract does not include a `fix_rows.py` script. Compared with kitchen-tipe (where `fix_rows.py` recomputes `concurrent_with_kings` from interval arithmetic) or porter-moss-theban-necropolis (where per-chunk typo fixes land there), this source has no derived fields that need deterministic recomputation and no LLM-reviewer-flagged corrections to apply. The three-row merge is the final form.

### Review (LLM, then human — honestly labelled)

- **LLM review (not performed on this source):** for the two-source-level reasons above (3 rows, full agent consensus on structured fields, prose-only disagreements), a separate `egyptologist-reviewer` pass over `merge-disagreements.txt` was not run. The committed `merge-disagreements.txt` contains the three prose-note disagreements and the majority-vote resolution (which picks the alphabetically-first agent's prose when all three notes disagree word-for-word).
- **Human review (required, NOT yet done on this source):** an actual Egyptologist reads the three reign-boundary rows against Hölbl's printed Appendix and signs off. Until that happens, this extract is **provisional** per constitutional rule 1. Given the subject matter (three well-documented Macedonian kings with dates that appear identically across every standard Egyptological chronology), the confidence band is high — but the scholarly-validation bar still requires human sign-off.

## Audit trail

- PDF (SHA-256 pinned below; not committed) → `raw/chunk-p349-p351.md` (Claude Code subagent OCR; not committed, regenerable per-transcriber)
- `raw/chunk-p349-p351.md` → three per-extraction-agent JSONLs at `raw/agent-{a,b,c}.jsonl` (or any path passed to `merge.py --agent-dir` / `HOLBL_AGENT_DIR`; Claude Code subagents; non-deterministic; not committed — gitignored via `raw/*`)
- three per-agent JSONLs → `reconciled.jsonl` (deterministic merge, committed)
- `merge-disagreements.txt` (committed) lists every field where extraction agents disagreed plus the majority-vote resolution.

## PDF hash pinning

Source PDF SHA-256: `1a18600cb2c271a907a216304d6eed3f982b07adcccce30c3ded2a12ef6def4b`. A reviewer re-running the pipeline against a PDF with a different hash should not expect byte-for-byte output reproduction; model outputs are stochastic, and the committed `reconciled.jsonl` is the source of truth.

## Physical vs printed pages

This PDF is a one-page-per-physical layout (each physical page renders one printed page of the book). The offset for the Appendix is physical − 29 = printed (physical 349 → printed 320, physical 350 → printed 321, physical 351 → printed 322). Per ADR-017 the `source_citation.pdf_pages` field cites the **physical PDF page range** (`"349-351"`); printed page numbers appear in the book's own bottom-edge numbering for scholarly cross-reference.

## Structure of Hölbl's Appendix (chunked)

**Physical page 349 (printed 320)** — Appendix header + column headers + two reign banners:

- `ALEXANDER THE GREAT` (rotated banner, spans 332 and 323 rows; 332 = invasion / accession, 323 = death at Babylon).
- `PHILIP III ARRHIDAIOS // Ptolemy as Satrap` (rotated banner, spans 323, 322/1, 321/20 rows; continues onto p. 350).

**Physical page 350 (printed 321)** — continuation of Philip III banner, then Alexander IV banner:

- `PHILIP III ARRHIDAIOS // Ptolemy as Satrap` (continues): 320, 319, 319–315, 317 rows. Ends with "Autumn 317: Murder of Philip III Arrhidaios".
- `ALEXANDER IV // Ptolemy as Satrap` (rotated banner, spans 316 through 310/09 rows).

**Physical page 351 (printed 322)** — end of Alexander IV banner + out-of-scope banners (not extracted):

- `ALEXANDER IV // Ptolemy as Satrap` (continues, then ends with "310/309: Murder of Alexander IV by Kassandros").
- `INTERREGNUM // Ptolemy as Satrap` (banner spans 308 through 306 rows) — **OUT OF SCOPE**, not extracted.
- `PTOLEMY I SOTER` (banner spans 305/4 onwards) — **OUT OF SCOPE**, not extracted (pharaoh.se covers Ptolemaic dynasty).

## Compound dates

Hölbl prints the year of Alexander IV's murder as `310/09`, meaning "310 or 309 BCE depending on which calendar convention is applied". We take the **earlier boundary** (`-310`) for `end_year`. This mirrors the convention used elsewhere in the Phase-0 extracts (Ryholt, Kitchen, HKW) for compound `NNN/NN` dates: take the earlier year, and record the compound form verbatim in `note` so a reviewer can audit the choice.

The prose-level alternative (`-309`) is preserved inside the `note` cell (`"ends at 310/09, Murder of Alexander IV by Kassandros"`) so no information is lost.

## Out-of-scope banners (explicit note)

For future iterations of this source: the `INTERREGNUM // Ptolemy as Satrap` and `PTOLEMY I SOTER` banners on physical p. 351 would extend this extract to five rows. They are deliberately omitted because pharaoh.se already carries Ptolemy I Soter (and the rest of the Ptolemaic dynasty). Adding them here would create duplicate rows in Phase A enrichment. The Interregnum (308–306 BCE) is a political interregnum between the end of Argead nominal kingship and Ptolemy's 306 BCE assumption of the Macedonian royal title; if Phase A needs a dedicated row for it, the correct place to add one is here, as an extension of this source — pharaoh.se does not cover the Interregnum.
