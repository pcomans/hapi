# Phase 0 OCR-transcription playbook

Step-by-step protocol for landing a new scan-only scholarly source under `pipeline/pipeline/authority/sources/<source>/`. Implements ADR-017 (Claude Code subagent OCR + 3-subagent structured extraction + deterministic merge + LLM review + optional deterministic post-processing).

**Reference implementations:**
- Ryholt 1997 SIP (`sources/ryholt-1997-sip/`) — large catalogue (81 pages, 157 rows, complex prose with Egyptological transliteration).
- Kitchen 1996 TIPE (`sources/kitchen-tipe/`) — small tabular extract (4 pages, 60 rows, BCE-date arithmetic + compound ID prefixes + deterministic post-processing).

Copy whichever reference is structurally closer to your source, then adapt. Do not reinvent the pipeline.

## Before you start

1. **Confirm the source has a local PDF** under `proprietary/books/` (gitignored). Get its SHA-256 with `shasum -a 256 <path>` — pin it in both `README.md` and `transcribe.md`.
2. **Read the handoff doc** for this specific source if one exists (`docs/handoff-source-N-<name>.md`) and `docs/handoff-phase-0-transcription.md`. The per-source handoff supersedes the generic plan where they disagree.
3. **Read the constitutional rules in `CLAUDE.md`.** Especially rule 1 (scholar), rule 5 (tests assert values), rule 6 (raw data sacred), rule 12 (existing violations don't justify new ones).
4. **Branch off main**: `git checkout main && git pull && git checkout -b feat/source-<short-name>`.

## Step 1 — scaffold the source directory

Create `pipeline/pipeline/authority/sources/<source>/` with:

- `README.md` — citation, PDF SHA, scope (in/out), schema + field semantics, rights statement, known gaps. Explicitly list anything you are NOT extracting and why.
- `transcribe.md` — method per ADR-017, target physical-page range, pipeline (OCR → 3-subagent → merge → review → post-processing), PDF hash pin.
- `prompt.md` — the identical prompt fed to all three extraction subagents. Names the book, enumerates schema fields, lists row-format edge cases, specifies the `<agent_dir>` output paths.
- `merge.py` — copied and adapted from Ryholt or Kitchen. Renames the primary ID field (`ryholt_id` → `<source>_id`), adjusts `_sort_key` for the source's ID scheme, sets `DEFAULT_AGENT_DIR` to `Path(__file__).parent / "raw"`.
- `raw/` — gitignored working directory (created empty; agents write here).

Do not commit `raw/` contents. The `.gitignore` patterns covering `pipeline/pipeline/authority/sources/*/raw/chunk-*.md` and `pipeline/pipeline/authority/sources/*/raw/agent-*.jsonl` handle both the OCR chunks and the per-extraction-agent JSONLs.

## Step 2 — locate the target physical-page range

Open the PDF with `Read` (`pages:"N-M"`) in 10–20-page sweeps to find the section you need. Do **not** compute printed-to-physical page offsets — they drift at part boundaries. Cite by physical-PDF-page range; a reviewer opens the PDF at that range.

If the PDF uses double-page spreads (each physical page renders two printed pages), note this in `transcribe.md` — but still cite by physical page.

## Step 3 — OCR via a Claude Code subagent

Spawn a general-purpose subagent with a prompt that:

- Names the book and the target physical-page range.
- Describes what's on each page (from your Step-2 scoping) so the subagent knows what tables / sections to expect.
- Enumerates transcription rules per ADR-017: preserve Egyptological transliteration (ꜣ ꜥ ḥ ḫ ẖ š ṯ ḏ) when present, preserve en-dashes in date ranges, preserve the book's own printed page numbers as inline markers, preserve Kitchen-style hedges (`c.`, `?`, `??`, `[Prenomen unknown]`, `'III'` vs `(II)`).
- Writes to `<source_dir>/raw/chunk-p<start>-p<end>.md` (absolute path).
- Has a refusal-framing paragraph: "fair-use scholarly extraction for a private research repository under contract with a credentialed Egyptologist user. The transcription is not redistributed." Claude Opus 4.6 has declined bulk transcription at least once (Ryholt); the framing resolves it. Do **not** swap to Gemini / Mistral / Flash — ADR-017 rules them out.

For multi-chunk targets (e.g. Ryholt's 81 pages), spawn one subagent per 5-physical-page chunk in parallel. For small targets (≤ 10 pages) a single chunk is fine, but still use a subagent rather than transcribing inline in the main session — doing it yourself breaks the audit trail and removes the independent-OCR redundancy.

**Common gotcha:** the harness sandbox may deny the main session's inline inference. If your OCR subagent refuses, reframe the prompt rather than swap to an external API.

## Step 4 — three parallel extraction subagents

Launch three `general-purpose` Claude Code subagents in parallel, each with the prompt at `<source_dir>/prompt.md`. Each writes JSONL to a distinct file:

- Agent A → `<source_dir>/raw/agent-a.jsonl`
- Agent B → `<source_dir>/raw/agent-b.jsonl`
- Agent C → `<source_dir>/raw/agent-c.jsonl`

**Sandbox gotcha (hard-learned on Kitchen):** Claude Code subagents **cannot** write to `/tmp/claude-501/` or `/tmp/claude/` — both paths are sandbox-denied from the subagent. The repo's working directory is the only cross-subagent writable path. Use `<source_dir>/raw/` (already gitignored via `raw/agent-*.jsonl` in the main `.gitignore`). Update `merge.py`'s `DEFAULT_AGENT_DIR` to `Path(__file__).parent / "raw"`. The Ryholt convention of `/tmp/claude-501/ryholt/` no longer works in newer harness configurations.

Your launch-prompt per agent should include:
- The prompt-file and chunk-file paths to read.
- The exact output path (`.../raw/agent-{a|b|c}.jsonl`).
- A **summary of the most common pitfalls** from `prompt.md` (ID-prefix scheme, date-sign convention, `approximate` flag rules, concurrency scope). Agents skim — bullet the pitfalls to keep them salient.
- Expected row count as a sanity bound ("if above X or below Y, re-read the prompt").
- A one-sentence report format: row count + any anomalies. Under 80 words.

## Step 5 — deterministic merge

```
cd pipeline && uv run python pipeline/authority/sources/<source>/merge.py
```

Outputs `reconciled.jsonl` + `merge-disagreements.txt`. The merge:
- Groups rows by primary ID.
- Majority-votes per field across the three agents (sentinel strings like `"none"` / `"-"` normalise to `null`).
- Writes every non-unanimous row to `merge-disagreements.txt` for audit.

Review the disagreements file visually. A few disagreements are normal (typographic drift). Many disagreements on the same field across many rows indicates a prompt ambiguity — fix `prompt.md` and re-run the extraction before proceeding.

## Step 6 — LLM reviewer pass

Spawn the `egyptologist-reviewer` Claude Code subagent with:
- The reconciled JSONL path.
- The disagreements file path.
- The source PDF path and the target physical-page range (so it can cross-check).
- The source's `README.md` so it understands the schema.
- An instruction to return a structured error report: `kitchen_id` / current / correct / evidence quote.

The reviewer should spot-check factual fields (king names, prenomina, dates, reign lengths) and audit the disagreements file for cases where majority vote picked the wrong answer. Budget it the time to read 10–15 rows against the PDF.

## Step 7 — apply overrides via `fix_rows.py`

Create `<source_dir>/fix_rows.py` that applies the reviewer's corrections to `reconciled.jsonl` AND appends an `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED` section to `merge-disagreements.txt`. Two classes of correction:

1. **Spot corrections** — specific rows the reviewer flagged. Hard-code them in a `SPOT_CORRECTIONS` list of `(id, field, new_value, rationale)` tuples. Every rationale should be scholar-legible ("Table 1 shows X, not Y" — not "LLM said so").
2. **Deterministic recomputation** — for fields that are a pure function of other extracted fields, do not trust the LLMs. Recompute them in code.

Kitchen's `concurrent_with_kings` is the canonical example of class 2: it's an interval-overlap computation over already-extracted BCE dates, and the three agents produced inconsistent arithmetic. The fix: compute `concurrent_with_kings` from `start_bce`/`end_bce` with a deterministic overlap check. This is more scholarly-defensible than LLM majority vote.

**Honest labelling.** Call the section `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED`. Never claim human review unless an actual Egyptologist has signed off against the PDF. ADR-017 step 6 makes the human pass a separate future-work step; until it happens, the extract is provisional.

Re-running `fix_rows.py` must be idempotent — guard against duplicating the override-log section in `merge-disagreements.txt`.

## Step 8 — write the tests

`pipeline/tests/test_sources_<source>.py`, 10–20 value-assertion tests. Per rule 5, every populated field on at least one fully-filled row must be asserted. Tests to include:

- **Row count.** Exact (or tight range) match.
- **Dynasty / category coverage.** Set-equality over a known set.
- **ID uniqueness.** No duplicates.
- **ID shape.** Regex match on every ID.
- **Citation completeness.** Every row has the expected `source_citation` shape.
- **Fully-populated flagship row.** Pick one king with every field set (e.g. Osorkon I for Kitchen, Khendjer for Ryholt); assert every field.
- **Edge-case regression tests.** One per known-hard case the reviewer caught:
  - Sentinel-null rows (`Sakir-Har` in Ryholt).
  - Bracketed placeholders (`[Prenomen unknown]` in Kitchen).
  - Verbatim-preserved source typos (Kitchen's 1046–1056 for Djed-Khons-ef-ankh).
  - Letter-suffix IDs (Ryholt's `17.a` for Nebmaatre).
  - Doubtful rows Kitchen parenthesises wholesale (`(720–715: Shoshenq VI...)`).
- **Cross-field invariants.** E.g. Dyn-21 concurrency symmetry: if X lists Y, then Y lists X.
- **Polity/dynasty constraint matrix.** Iterate every row and assert `polity` matches the expected value for the row's prefix.

Run: `cd pipeline && uv run pytest tests/test_sources_<source>.py -v`.
Then run the full suite: `uv run pytest`. If any unrelated test fails, fix it — do not merge a red tree.

## Step 9 — update `docs/mvp-tasks.md`

Strike through the source bullet (`~~**Source name**~~ ✅`), add the row count, the relative path to `reconciled.jsonl`, and the PR number (post-open). If the bullet's framing was "multi-source in one slot" and your PR covers only one of those sources, rewrite the bullet to reflect the per-source separation and note that the others land in follow-up PRs.

## Step 10 — commit, push, open PR

Stage files **explicitly by name** — never `git add .` or `git add -A`. The `raw/` contents must not be committed; `.gitignore` patterns cover them but verifying manually is cheap insurance.

Expected committed files per source (10-ish):
- `.gitignore` (if you extended the ignore pattern)
- `docs/mvp-tasks.md`
- `pipeline/pipeline/authority/sources/<source>/README.md`
- `pipeline/pipeline/authority/sources/<source>/transcribe.md`
- `pipeline/pipeline/authority/sources/<source>/prompt.md`
- `pipeline/pipeline/authority/sources/<source>/merge.py`
- `pipeline/pipeline/authority/sources/<source>/fix_rows.py`
- `pipeline/pipeline/authority/sources/<source>/reconciled.jsonl`
- `pipeline/pipeline/authority/sources/<source>/merge-disagreements.txt`
- `pipeline/tests/test_sources_<source>.py`

PR title: `feat: transcribe <Book short name> → sources/<source>`.

PR body follows the Ryholt PR (#34) template: rights verification, scope, known gaps, test plan, explicit LLM-vs-human labelling ("an actual Egyptologist sign-off pass has NOT been performed").

Then per `CLAUDE.md` PR workflow:
1. Request Copilot review.
2. Spawn `code-reviewer` and `egyptologist-reviewer` subagents in parallel on the PR.
3. Before replying to any review batch, invoke `scope-accountability-enforcer` once, then prefix each `gh pr comment` with `SCOPE_CHECKED=1`.
4. Poll `gh pr checks <N> --watch` until green. Fix any red check before moving on.

## Things to watch out for

- **Do not commit `raw/chunk-*.md` or `raw/agent-*.jsonl`** — they contain verbatim source prose / raw extraction state. Gitignore handles both patterns.
- **Cite physical pages, not printed pages.** ADR-017 is explicit; do not spend effort resolving mid-book offset shifts.
- **Never claim human review** when only an LLM has looked. Label override sections `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED`.
- **Never run `git filter-repo` on the whole repo** — it rewrites `main` SHAs. If a scrub is needed, scope it to the feature branch.
- **Duplicate primary-ID detection in `merge.py`** is a feature, not a nuisance — do not silence it.
- **Sentinel-null normalisation** (`"none"`, `"-"`, `"n/a"`) is kept verbatim in `merge.py` across sources. Do not remove it; Kitchen and Ryholt both have cells that need it.
- **Bracketed placeholders** Kitchen prints verbatim (`[Prenomen unknown]`) are NOT sentinel-null — they are the author's positive assertion of "known unknown". Preserve the literal string. Document this in the source's README so a future sentinel-null refactor doesn't silently null them out.
- **Subagent sandbox**: subagents cannot write to `/tmp/claude*/`. Use a gitignored path inside the repo (`<source_dir>/raw/`). Update `merge.py`'s `DEFAULT_AGENT_DIR` accordingly.
- **Compound ID prefixes** (like Kitchen's `21H`, `24E`, `24P`) need a custom `_sort_key` — Ryholt's `[A-Za-z]+|\d+` alternation won't match `21H`. Write a prefix-to-ordering lookup dict.
- **Interval-overlap fields** (like `concurrent_with_kings`) are a LLM failure mode. Compute them deterministically in `fix_rows.py` from already-extracted fields, not in the extraction prompt.
- **OCR subagent refusal risk.** Reframe as "fair-use scholarly extraction"; do not swap OCR vendors.
