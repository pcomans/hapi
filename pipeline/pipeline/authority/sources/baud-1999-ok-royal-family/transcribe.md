# Baud 1999 — transcription method

Implements ADR-017 (Phase-0 scan-only scholarly source) with the
playbook's prose-direct-to-extractors variant — NO `raw/chunk-*.md`
prose OCR is committed. The three independent extraction subagents
read the PDF directly via the Claude Code `Read` tool, each against
the SHA-pinned source files in `proprietary/books/`:

- Vol. 1 PDF SHA-256:
  `7913623545deb56697506c703f261445d3c029a8f0712474796629670d2f302a`
  (Not read for this authority — narrative chapters only; out of scope.)
- Vol. 2 PDF SHA-256:
  `8768536a13fb5428d8ec7fbd96263d028aabb557a5411e7f796cad99ed6881cb`
  — This is the corpus source.

All downstream stages (3-subagent extraction, merge, LLM reviewer
pass, `fix_rows.py`) run on Claude Opus 4.6+. No OCR tier-2 / tier-3
fallback is used for this source: the PDF is text-layer-indexable via
the harness `Read` tool directly, so no OCR step is needed at all.

## Chunk plan

Main *Corpus* entries `[1]`–`[282]` occupy vol.2 physical pages 19–244
(printed pp. 395–627). That's ~226 physical pages, ~1.3 entries per
page, ~282 total entries. One PR at the full scope is infeasible
(large prose surface, unstable extraction quality, long review
cycles), so this source lands as multiple PRs per the playbook's
"multi-chunk source pattern".

Chunk boundaries are chosen by physical-page range — **not by
dynasty**, because Baud orders the corpus alphabetically by
Egyptian transliteration of the headword. Entries for Dyns 3–6 are
interleaved throughout, so dynasty-based chunking would require a
full extraction pass first. Page-range chunks extract cleanly.

| Chunk suffix   | Vol.2 physical pages | Corpus entries (approx.) | PR status |
|----------------|----------------------|---------------------------|-----------|
| `-chunk1`      | 19–40                | `[1]`–`[~25]`             | **this PR** |
| `-chunk2`      | 41–70                | ~`[26]`–`[~60]`           | follow-up  |
| `-chunk3`      | 71–100               | ~`[61]`–`[~95]`           | follow-up  |
| `-chunk4`      | 101–130              | ~`[96]`–`[~130]`          | follow-up  |
| `-chunk5`      | 131–165              | ~`[131]`–`[~165]`         | follow-up  |
| `-chunk6`      | 166–200              | ~`[166]`–`[~205]`         | follow-up  |
| `-chunk7`      | 201–244              | ~`[206]`–`[282]`          | follow-up  |

Exact `[N]` boundaries are set per chunk at extraction time (the
first `[N]` that starts AFTER the previous chunk's last complete
entry). The handoff doc `docs/handoff-baud-next-chunk.md` picks up
from the last `baud_id` landed in the previous PR.

## Pipeline (per chunk)

1. **PDF direct read.** Three independent extraction subagents are
   spawned in parallel. Each reads vol.2 of the PDF for the chunk's
   page range via `Read(pages:"<start>-<end>")` and writes structured
   JSONL to `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/raw/agent-{a,b,c}-<chunk-suffix>.jsonl`.
   The extraction prompt is `prompt-<chunk-suffix>.md` (or
   `prompt.md` for chunk 1 per the playbook convention).
2. **Deterministic merge.**
   `uv run python pipeline/authority/sources/baud-1999-ok-royal-family/merge.py`
   unions the three agents' per-chunk JSONL outputs, majority-votes
   each field, writes `reconciled.jsonl` and `merge-disagreements.txt`.
3. **LLM reviewer.** Spawn `egyptologist-reviewer` on the reconciled
   JSONL with the vol.2 PDF and the chunk's page range. Reviewer
   returns a structured error report keyed on `baud_id`.
4. **`fix_rows.py`.** Apply the reviewer's spot corrections; also
   derive `dynasty_min`/`dynasty_max` / `king_father` from
   `datation_raw` / `king` / `father_name`. Idempotent re-run;
   appends `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED` to
   `merge-disagreements.txt`.
5. **Tests.** `pipeline/tests/test_sources_baud_ok_royal_family.py`
   asserts row count, primary-ID shape/uniqueness, per-chunk
   citation, at least one fully-populated flagship row's fields, and
   chunk-specific edge-case regressions.

## Chunk 1 specifics

- Vol.2 physical pages **19–40**.
- Expected corpus entries: `[1]`–`[~25]` (exact upper bound
  confirmed at extraction time; the agents are given an allowable
  range of 20–30 rows).
- The first four printed pages of vol.2 (395–398) are Baud's own
  *Corpus* header — his explanation of the a–h rubric scheme. They
  are NOT extracted. Agents skip them and start at `[1]` on p. 399.
- Includes at least one redirect stub (`[9] Jj-[ḥr?]-nfr. Voir à
  Nfrt-kꜣw II [132]`) and a sprawling multi-page entry (`[17] Jpwt
  Ire`, which runs across vol.2 pp. 37–39). The chunk boundary at
  p. 40 is set AFTER `[17]` completes, so the sprawling-entry
  edge case is in-chunk.
- Flagship fully-populated row for test assertions: `[3] Jḥtj-ḥtp`
  (mastaba G 7650; PM 200-201; Rêkhaef; titles, parenté (spouse
  Mrt-jt.s), divers all present).

## This PR — scaffolding only

**No `reconciled.jsonl` lands in this PR.** This PR lands the
source-directory scaffolding: `README.md`, `transcribe.md`,
`prompt.md`, `merge.py`, `fix_rows.py`, `raw/.gitkeep`, plus the
derived-fields unit tests in `pipeline/tests/test_sources_baud_ok_royal_family.py`
and the handoff doc `docs/handoff-baud-next-chunk.md`.

**Why scaffolding-only.** The authoring agent's Claude Code
session in this PR did not have Task-tool access, so it could not
spawn the three independent extraction subagents required by
ADR-017 / the Phase-0 playbook. Rather than fake a 3-agent run
with three sequential passes from one model instance (which would
fail constitutional rule 1 — methods are deterministic and
reproducible — because single-instance passes have correlated
errors that defeat the majority-vote redundancy), this PR lands
only the infrastructure. The next agent with Task-tool access runs
chunk 1 extraction against this committed prompt / merge / fix_rows
pipeline.

The infrastructure has value on its own:

- The schema design (`baud_id` zero-padded, `redirect_to` stubs,
  `datation_raw` + derived `dynasty_min`/`dynasty_max`, `asterisk`
  flag) is a product of reading 30-odd pages of Baud and is not
  obvious from the Dodson-Hilton / Kitchen templates.
- `merge.py` is multi-chunk-ready from day one; chunk 2 onward
  drops in beside chunk 1 without merge-script changes.
- `fix_rows.py` ships the French-date parser, the OK-king
  `king_father` authority, and redirect-row normalisation — all
  deterministic, all unit-tested.
- The handoff doc explicitly walks the next agent through the
  extraction pipeline with the exact launch-prompt recipe for the
  three subagents.

## Commit discipline

- Commit `prompt.md`, `merge.py`, `fix_rows.py`, `README.md`,
  `transcribe.md`, and `raw/.gitkeep` for this PR. No
  `reconciled.jsonl`, no `merge-disagreements.txt` (they don't
  exist yet — chunk 1 extraction is the next agent's task).
- Do NOT commit `raw/agent-*.jsonl` — they don't exist yet either,
  and future chunks' agent outputs contain Baud prose in notes that
  will be pruned at merge time. Gitignore handles them.
- Do NOT commit any OCR'd prose chunks (`raw/chunk-*.md`) — they
  don't exist for this source. The prose-direct pipeline means
  there is no intermediate prose artifact.
