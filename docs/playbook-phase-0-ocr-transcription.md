# Phase 0 OCR-transcription playbook

Step-by-step protocol for landing a new scan-only scholarly source under `pipeline/pipeline/authority/sources/<source>/`. Implements ADR-017 (Claude Code subagent OCR + 3-subagent structured extraction + deterministic merge + LLM review + optional deterministic post-processing).

**Reference implementations:**
- Ryholt 1997 SIP (`sources/ryholt-1997-sip/`) — large catalogue (81 pages, 157 rows, complex prose with Egyptological transliteration).
- Kitchen 1996 TIPE (`sources/kitchen-tipe/`) — small tabular extract (4 pages, 60 rows, BCE-date arithmetic + compound ID prefixes + deterministic post-processing).
- Dodson-Hilton 2004 queens (`sources/dodson-hilton-queens/`) — **multi-chunk source**, one directory with per-chunk prompts, per-chunk agent outputs, and a union-across-chunks `merge.py`. Chunks landed so far: Pre-Amarna Brief Lives (PR #37, 59 rows) and Amarna Interlude Brief Lives (PR #38, 41 rows). Copy this pattern when your source will land across multiple PRs that share one source directory — see § "Multi-chunk source pattern" below.

Copy whichever reference is structurally closer to your source, then adapt. Do not reinvent the pipeline.

## Before you start

1. **Confirm the source has a local PDF** under `proprietary/books/` (gitignored). Get its SHA-256 with `shasum -a 256 <path>` — pin it in both `README.md` and `transcribe.md`.
2. **Read the handoff doc** for this specific source if one exists (`docs/handoff-source-N-<name>.md`) and `docs/handoff-phase-0-transcription.md`. The per-source handoff supersedes the generic plan where they disagree.
3. **Read the constitutional rules in `CLAUDE.md`.** Especially rule 1 (scholar), rule 5 (tests assert values), rule 6 (raw data sacred), rule 12 (existing violations don't justify new ones).
4. **Branch off main**: `git checkout main && git pull && git checkout -b feat/source-<short-name>`.

## Rights policy

Phase 0 source work extracts factual data from copyrighted scholarly books. Two layers of protection keep this clean. **Scope:** this rights policy governs transcription-based Phase-0 sources — directories under `pipeline/pipeline/authority/sources/` that hold a `transcribe.md` at source-dir root. Web-scrape sources (pharaoh.se), third-party gazetteer mirrors (iDAI), and already-structured reference data (HKW) have different rights models and document their own per-source posture in their own `README.md`.

**Layer 1 — the PDF is never committed.** The book lives in `proprietary/books/` (gitignored) and stays there. `README.md` and `transcribe.md` reference it by citation + SHA-256, but the source object itself is never redistributed through this repo. This removes the clearest copyright exposure.

**Layer 2 — only transformative/derivative work is committed, and nothing under `raw/` ever is.** `raw/` is gitignored wholesale at the repo root (`pipeline/pipeline/authority/sources/*/raw/*` + `!pipeline/pipeline/authority/sources/*/raw/.gitkeep`); per-agent JSONLs and per-chunk OCR markdown are working state, not deliverables. Committed artifacts live at the source-dir root (next to `README.md`), never under `raw/`, and fall into two safe categories:

- **Reconciled structured-extraction JSONL** — `reconciled.jsonl`, produced by the 3-subagent merge. The primary content is facts (names, dates, dynasty IDs, titulary strings). Short prose fragments — the author's hedges, parenthetical cross-references, explicit "probably" / "perhaps" scoping — are preserved verbatim in fields like `notes` when dropping them would lose the attested fact (e.g. Dodson-Hilton's `notes` carries sentence-length fragments from the Brief Lives entries). This is still a fact-level extract, not a prose transcription, because the per-row budget is a sentence or two and the extract as a whole is not a substitute for the source: a reader of `reconciled.jsonl` cannot reconstruct the source chapter. The project's working legal posture treats the reconciled output as a transformative derivative: US copyright law has held raw facts uncopyrightable since *Feist v. Rural* (499 U.S. 340, 1991), and the project reads the UK/EU *sui generis* database right as not reaching fact-level extractions of the sort committed here. This is the project's working assumption, not a legal opinion — a jurisdiction-specific question for a specific source goes in the source `README.md`.
- **Hand transcriptions of tabular content** — a text or CSV file at source-dir root (e.g. `chapter-banners.txt` alongside `reconciled.jsonl`), used when the source section is itself a table (HKW chronology, Kitchen Tables 1/3/4, Shaw chapter banners, Beckerath king-tables, Porter-Moss tomb indexes). Transcribing a table is fact extraction. Do **not** place these under `raw/` — the gitignore comment pins the source-dir-root location explicitly.

**What is not safe to commit:** verbatim prose OCR of narrative-prose sources (Dodson-Hilton Brief Lives, Baud prosopographical paragraphs, Porter-Moss tomb *descriptions*). Running OCR against a prose source is fine as an internal pipeline step, but the OCR chunk MUST NOT be committed. Feed the PDF directly to the extraction subagents and commit only `reconciled.jsonl`. The root `.gitignore` patterns `pipeline/pipeline/authority/sources/*/raw/*` + `!pipeline/pipeline/authority/sources/*/raw/.gitkeep` are the mechanical default, and `cd pipeline && uv run pytest tests/test_structure.py::test_no_tracked_files_under_raw_for_phase0_sources` backstops them by failing CI if any Phase-0 source commits a non-`.gitkeep` file under `raw/`. Do not relax either. A `git add -f` that bypasses the gitignore still gets caught by the test.

**"Rights verification" per `docs/mvp-tasks.md` is satisfied by choosing the derived-extract path.** Tasks that call out rights verification (Porter-Moss I, Porter-Moss III, Manetho) ask *either* for an explicit redistribution-license basis *or* for the decision to commit only a derived extract. The derived-extract path is this project's default and the documented basis for every Phase 0 source landed so far. The default does not override a *source-specific* documented licence: Porter-Moss scans are redistributed by the Griffith Institute under explicit licence terms (see `docs/handoff-phase-0-transcription.md`), and the PM source `README.md` must still record those terms alongside the derived-extract framing.

**Interpretive facts are still facts, but cite them as such.** Two of the named corpora carry facts that are *also* the author's scholarly judgment: Baud's BdE 126 prosopographical entries weave factual headwords (name, filiation, attested titles) with Baud's own attributions and skepticism — extracted facts should be attributed in `source_note` (e.g. `"per Baud 1999 §X"`) rather than flattened to bare givens. Beckerath's MÄS-49 numbering scheme is likewise his expression — carry it as `beckerath_number`, do not paraphrase his commentary. A source README that calls out which of its extracted fields are author-attributions is the right place to land the distinction.

**What the source `README.md` rights statement must record:**
- Citation and edition, PDF SHA-256.
- "Source PDF held in `proprietary/books/<filename>`, not committed."
- What's extracted (facts / tabular data) vs what is deliberately NOT extracted (narrative prose, illustrations).
- Basis: transformative scholarly extraction for a cross-museum provenance index; the project's working assumption is that the committed extract is a fact compilation rather than a derivative of the source's protectable expression; PDF never redistributed. Per-source edition / jurisdiction notes go here when they are materially different from this default (e.g. a source under an explicit licence, a source with a live jurisdictional question, or extracts whose "fact" layer is entangled with the author's scholarly judgment).

## Step 1 — scaffold the source directory

Create `pipeline/pipeline/authority/sources/<source>/` with:

- `README.md` — citation, PDF SHA, scope (in/out), schema + field semantics, rights statement, known gaps. Explicitly list anything you are NOT extracting and why.
- `transcribe.md` — method per ADR-017, target physical-page range, pipeline (OCR → 3-subagent → merge → review → post-processing), PDF hash pin.
- `prompt.md` — the identical prompt fed to all three extraction subagents. Names the book, enumerates schema fields, lists row-format edge cases, specifies the `<agent_dir>` output paths.
- `merge.py` — copied and adapted from Kitchen (post-PR #155 canonical). Renames the primary ID field (`kitchen_id` → `<source>_id`), adjusts `_sort_key` for the source's ID scheme, sets `DEFAULT_AGENT_DIR` to `Path(__file__).parent / "raw"`. The canonical merge.py carries rule-2 (no silent first-seen-pick) enforcement: `_majority` requires keyword-only `<id>`/`field`, raises on uncovered ties, looks up `tie-break-overrides.json` first. See § "Canonical merge.py shape" below for the full machinery.
- `tie-break-overrides.json` — empty `{}` initially. Authoritative resolutions for ties keyed by `"<id>|<field>"`; each value is `{"value": ..., "rationale": "..."}` with a printed-source citation. Loader validates: top-level dict, both halves of key non-empty, value is dict with `value` + `rationale` keys.
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
- Has a refusal-framing paragraph: "fair-use scholarly extraction for a private research repository under contract with a credentialed Egyptologist user. The transcription is not redistributed." Claude Opus 4.6 has declined bulk transcription at least once (Ryholt); the framing resolves it.

For multi-chunk targets (e.g. Ryholt's 81 pages), spawn one subagent per 5-physical-page chunk in parallel. For small targets (≤ 10 pages) a single chunk is fine, but still use a subagent rather than transcribing inline in the main session — doing it yourself breaks the audit trail and removes the independent-OCR redundancy.

**Common gotcha:** the harness sandbox may deny the main session's inline inference. If your OCR subagent refuses, reframe the prompt.

**ADR-017 amendment (2026-04-15) — external-model fallback.** Claude Opus 4.6 declined OCR on Dodson-Hilton chunk 1 (p126–p130) with a reasoned copyright-scope refusal. ADR-017 is amended to allow a single per-chunk fallback to Gemini 3.1 Pro when Opus refuses; the amendment has constraints:
- The Gemini prompt is committed verbatim at `<source_dir>/transcribe-gemini-prompt.md` for reproducibility. The Gemini model version is pinned in `transcribe.md`.
- Every downstream stage (3-subagent extraction, merge, reviewer pass, fix_rows) continues to run on Claude Opus 4.6 — only the OCR step uses Gemini.
- Each chunk must re-attempt Opus OCR first before escalating. Dodson-Hilton chunk 2 (p142–p145) succeeded on main-session Opus after chunk 1 had refused; each chunk is independent.
- Document the deviation in `transcribe.md` § "Model deviation" with the refusal transcript.

**Main-session OCR as a sanctioned exception.** The playbook's default is a subagent OCR pass, but when (a) the OCR subagent hits content filtering and (b) the main session can Read the PDF pages itself and produce faithful verbatim prose, main-session OCR is acceptable. This was the chunk-2 path on Dodson-Hilton (PR #38). Record the deviation in `transcribe.md` so the audit trail reflects what actually ran — do not pretend a subagent produced it.

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
- Majority-votes per field across the three agents (sentinel strings like `"none"` / `"-"` / `"null"` normalise to `null`).
- Writes every non-unanimous row to `merge-disagreements.txt` for audit (fields sorted for determinism per issue #142).
- **Raises loudly on uncovered ties** (constitutional rule 2): if 1/1/1 across three agents OR 1/1 when one agent missed the row, and no `tie-break-overrides.json` entry exists, `_majority` raises `ValueError` naming the row × field + every distinct candidate. The merge does NOT silently first-seen-pick.

The first run on a fresh source typically raises on a handful of ties. Each raise is a row × field decision the data needs you to make:
1. Read the printed PDF at the cited row to determine the correct value.
2. Add an entry to `tie-break-overrides.json` keyed `"<id>|<field>"`, with `value` set to the correct value and `rationale` citing the printed page (book p<N> + scan-NNN-{left,right} if applicable).
3. Re-run merge.py. The next raise (if any) surfaces; iterate.

When the merge runs cleanly, every reconciled value traces to either (a) genuine multi-agent agreement, (b) a real majority, or (c) an explicit cited override — per constitutional rule 6.

Review the disagreements file visually. A few non-tied disagreements are normal (typographic drift). Many disagreements on the same field across many rows indicates a prompt ambiguity — fix `prompt.md` and re-run the extraction before proceeding.

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

Two test files per source:

1. **`pipeline/tests/test_sources_<source>.py`** — 10–20 value-assertion tests. Per rule 5, every populated field on at least one fully-filled row must be asserted. Tests to include:

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

2. **`pipeline/tests/test_<source>_merge_tie_break.py`** — unit tests pinning the rule-2 enforcement machinery. Copy from `test_kitchen_merge_tie_break.py` (post-PR #155 canonical). 16+ tests covering:

- `_majority` unanimous / clear majority / 1/1 partial-row / 1/1/1 tie / sentinel-null collapse / keyword-only `<id>`/`field` signature.
- Override resolution paths: 1/1/1 tie + override → override value; 1/1 tie + override → override value; tie without override → raise with diagnostic listing every candidate.
- Override-loader schema validation: top-level dict, `|` separator present, both halves non-empty, value is dict, value carries `value` + `rationale` keys.
- `SENTINEL_NULL_STRINGS` includes `"null"` (Leprohon parity per PR #146 P1.3).
- Override `value` passes through `_deep_normalise` (Gemini PR #155 round-2 parity).
- On-disk pin tests: for every `tie-break-overrides.json` entry, assert reconciled.jsonl carries the resolved value (catches silent regression if someone removes an override).
- A meta-test `test_post_fix_rows_pipeline_determinism` (per PR #161, closes the constitutional rule 3 gap on the override → fix_rows multi-file convention): pin the FINAL post-fix-rows reconciled.jsonl value for every tie-break override row × field with coverage sanity-checks.

Run: `cd pipeline && uv run pytest tests/test_sources_<source>.py tests/test_<source>_merge_tie_break.py -v`.
Then run the full suite: `uv run pytest`. If any unrelated test fails, fix it — do not merge a red tree.

## Step 9 — update `docs/mvp-tasks.md`

Strike through the source bullet (`~~**Source name**~~ ✅`), add the row count, the relative path to `reconciled.jsonl`, and the PR number (post-open). If the bullet's framing was "multi-source in one slot" and your PR covers only one of those sources, rewrite the bullet to reflect the per-source separation and note that the others land in follow-up PRs.

## Step 10 — commit, push, open PR

Stage files **explicitly by name** — never `git add .` or `git add -A`. The `raw/` contents must not be committed; `.gitignore` patterns cover them but verifying manually is cheap insurance.

Expected committed files per source (13-ish):
- `.gitignore` (if you extended the ignore pattern)
- `docs/mvp-tasks.md`
- `pipeline/pipeline/authority/sources/<source>/README.md`
- `pipeline/pipeline/authority/sources/<source>/transcribe.md`
- `pipeline/pipeline/authority/sources/<source>/prompt.md`
- `pipeline/pipeline/authority/sources/<source>/merge.py`
- `pipeline/pipeline/authority/sources/<source>/fix_rows.py`
- `pipeline/pipeline/authority/sources/<source>/tie-break-overrides.json` (initially `{}` if no ties; populated as ties surface)
- `pipeline/pipeline/authority/sources/<source>/reconciled.jsonl`
- `pipeline/pipeline/authority/sources/<source>/merge-disagreements.txt`
- `pipeline/pipeline/authority/sources/<source>/raw/.gitkeep` (keeps the dir tracked; everything else under `raw/` is ignored via the root `.gitignore`'s `pipeline/pipeline/authority/sources/*/raw/*` pattern)
- `pipeline/tests/test_sources_<source>.py`
- `pipeline/tests/test_<source>_merge_tie_break.py`

**Deterministic JSONL output.** Write `reconciled.jsonl` with `json.dumps(..., sort_keys=True)` in both `merge.py` and `fix_rows.py`. Without sorted keys, Python's dict iteration order makes the file re-shuffle on every re-run even when values are identical — spurious diffs pollute the PR and make the authority file look unstable.

PR title: `feat: transcribe <Book short name> → sources/<source>`.

PR body follows the Ryholt PR (#34) template: rights verification, scope, known gaps, test plan, explicit LLM-vs-human labelling ("an actual Egyptologist sign-off pass has NOT been performed").

Then per `CLAUDE.md` PR workflow:
1. Gemini Code Assist auto-reviews new PRs within ~5 minutes — no explicit trigger on PR creation. On subsequent pushes, post `/gemini review` via `gh pr comment <N> --body "/gemini review"` to request a fresh review.
2. **Arm a `Monitor` via the `/watch-pr-reviews` skill.** Reviews land minutes after the trigger. Sitting idle waiting for the review (or worse, waiting for the user to prompt "look at review comments") breaks the workflow. The Monitor-pattern emits one in-chat notification on the terminal state:
   - Success: a Gemini Code Assist review whose `commit_id` matches the current HEAD.
   - Timeout: no new review in 15 min → verify manually via `curl -H "Authorization: token $(gh auth token)" .../pulls/<N>/reviews`; timeout is not acceptance.
   
   See `CLAUDE.md` § "Pull request workflow" step 2 and `.claude/skills/watch-pr-reviews/` for the exact invocation. Filtering on `commit_id == <HEAD>` catches multi-round reviews (reviewers occasionally submit review #2 minutes after #1) without re-surfacing stale reviews of previous commits. Re-arm on each subsequent push so the next push's re-review also gets caught.
3. Spawn `code-reviewer` and `egyptologist-reviewer` subagents in parallel on the PR — they run in the background via `Agent` with `run_in_background: true` and auto-notify on completion (no Monitor needed for those; `Agent` handles it natively).
4. Before replying to any review batch, invoke `scope-accountability-enforcer` once, then prefix each `gh pr comment` with `SCOPE_CHECKED=1`.
5. Poll `gh pr checks <N> --watch` until green. Fix any red check before moving on.

**Reviewer-subagents return reviews inline, not to the PR.** Neither `code-reviewer` nor `egyptologist-reviewer` has `Bash` / `gh` access in the current harness, so they return their review as the final message rather than posting it. Do one of:
- Read the review yourself, apply the fixes in a new commit, and paste the review into the PR thread as a reference if useful.
- Take the review body and post it via `gh pr review <N> --comment --body-file -` (heredoc piped from the commit message).

Either way, **give the review serious weight** even if it lands inline — the review was asked for; if the code-reviewer finds a rule 2 or rule 5 violation, fix it before merging.

## Step 11 — post-PR review-pass cycle

The review cycle almost always surfaces something. Common real findings from the first Ryholt + Kitchen cycles:

- **Rule 2 defensive guards sneak in.** `if x is None: return None` or `if s > e: return None` with a "should never happen" comment is the exact pattern the constitution prohibits. Raise loudly. The reviewer catches this reliably.
- **Rule 5 partial-field assertions.** A "themed" test on one row (e.g. "test the doubtful flag on Shoshenq VI") typically asserts 3–4 fields. If the fixture populates 12, assert 12. Rule 5 is about the bug those missing 8 assertions would have hidden.
- **Symmetry tests that don't actually check.** A symmetry invariant (`X.concurrent ∋ Y ⇒ Y.concurrent ∋ X`) is weak — stale-but-symmetric lists pass it. Re-derive the expected values from the authoritative source (start/end dates + overlap rule) and assert equality. Import the computation from `fix_rows.py` so drift breaks the test.
- **README prose quotations of the extract.** If the README quotes an extract value inline (e.g. "Harsiese, Hedjkheperre Setepenre"), that quotation is a second source of truth and will drift. Either delete the quote or lock it in with a test. Egyptologist-reviewer catches these.
- **Fragile gitignore patterns.** Listing specific filename patterns (e.g. `pipeline/pipeline/authority/sources/*/raw/chunk-*.md`, `.../raw/agent-*.jsonl`) means any new file the subagent drops into `raw/` becomes committable. Prefer the wildcard form the repo root uses: `pipeline/pipeline/authority/sources/*/raw/*` + `!pipeline/pipeline/authority/sources/*/raw/.gitkeep`.

Apply the fixes in a fresh commit (`fix(<source>): address <reviewer> first pass`), re-run tests, push. Poll CI and the review threads for a second round.

## Step 11.5 — risk-driven automated checks

The LLM reviewers (especially `egyptologist-reviewer`) reliably flag *categories* of failure mode, not just individual rows: "lacuna preservation", "hedge promotion in Unplaced rows", "Syrian-extraction trio cross-refs", and so on. Treating each of those as a row-by-row to-do for the human reviewer is the wrong loop — it burns scarce human attention to confirm negatives. Each category is mechanically detectable on the reconciled JSONL.

For every category a reviewer flags (in this PR or a previous one), implement one validation over the source's `reconciled.jsonl`. The implementation vehicle varies per source:

- Sources whose transcription is **committed in the repo** (whatever the file format — `raw/*.md`, `raw/*.csv`, hand-typed CSVs shipped alongside `reconciled.jsonl`) can wire a `diff_<chunk>.py` script that compares reconciled values against the committed transcription. The diff script itself is always committed; it's the transcription-input side of the diff that varies.
- Sources whose transcription is **gitignored for copyright reasons under ADR-017** (Dodson-Hilton's `raw/chunk-*.md` and any future source that OCRs a copyrighted scholarly book) still ship a committed `diff_<chunk>.py`, but the diff can only run on the machine that has the `raw/chunk-*.md` files locally (i.e. the agent that ran the OCR step for that PR). The diff is a **pre-commit / pre-review gate**: the committing agent runs the diff, pastes a clean run (or the row list + explanation of any intentional divergence) into the PR body or `reviewer-notes-<chunk>.md`, and only then commits. This degrades CI-reproducibility to *agent-attested-clean* rather than *CI-verified-clean*, but preserves the content-validation signal because the committed `reconciled.jsonl` has demonstrably been diff'd against the OCR before landing. A reviewer who wants to re-verify re-runs the OCR step locally against the SHA-pinned source PDF and re-runs the diff — the OCR output is reproducible, just not committable.
- Sources that ship **only `reconciled.jsonl`** (some single-shot extracts with no diffable intermediate) use a `validate.py` or test fixture asserting against `reconciled.jsonl` directly.

`diff_power.py` and `diff_ramesside.py` are example patterns for the gitignored-transcription case; they are not a required filename for every source. The check inventory grows monotonically as new sources surface new conventions; checks ported from a previous source's script are free.

**Current inventory** (extend as new categories surface). Items marked **[T]** require a committed transcription artifact and are skipped on sources without one; items marked **[R]** apply to any source with a `reconciled.jsonl`.

0. **[T] Baseline transcription diff.** For every reconciled row, the row's structured fields (whatever those are for this source — `roles`/`notes` for Dodson-Hilton, `start_bce`/`end_bce`/`length_of_reign_years` for Kitchen, etc.) match the corresponding header tuple and prose block parsed from the transcription, after schema-appropriate normalization (whitespace, markdown stripping, set semantics for unordered tuples). This is the foundation `diff_<chunk>.py` must implement before any other check is meaningful for D-H-style chunked sources. When the transcription file itself is gitignored under ADR-017 (copyright), the `diff_<chunk>.py` script is still committed and runs locally — see the three-way vehicle list above for how this preserves the content-validation signal despite degraded CI-reproducibility. References: `pipeline/pipeline/authority/sources/dodson-hilton-queens/diff_power.py` and `diff_ramesside.py`.
1a. **[R] Lacuna-marker consistency within the reconciled row.** If the source `id` field (`dh_id`, `kitchen_id`, `ryholt_id`, etc.) contains `[?]`, `[ka?]`, leading `[...]`, or similar bracketed lacuna markers, the reconciled row's display name must preserve the same marker; likewise, a lacuna marker in the display name but not the id is a failure. This is the repo-checkable regex variant that works on `reconciled.jsonl` alone.
1b. **[T] Lacuna preservation against transcription/source page.** For sources with a committed transcription artifact (or another reviewable source-page reference), any bracketed lacuna marker present in the transcription headword or original page must appear verbatim in the reconciled row's id and display name. Use this when source text is available; otherwise item 1a is the only mechanically enforceable lacuna check.
2. **[R] Hedge preservation on relationship fields.** Run only when a hedge word ("probable", "probably", "perhaps", "possibly") appears within ~6 tokens of a relationship-domain noun (`father|mother|son|daughter|wife|husband|spouse|child|parent`) in the row's narrative `notes` field. Match the hedge to the *target* field by the noun: "perhaps the mother of X" must produce a parenthesised hedge in `children_names` for the subject row (whose mother-of relationship is to X), not in `mother_name`. "Probably a son of Y" must produce a parenthesised hedge in `father_name` for the subject row. Promotion of such a hedged claim to a hard claim (no parens) is the signature failure. Skip notes hedges that have no relationship-domain noun in the window ("perhaps owned a tomb at Thebes" is not a relationship hedge). Applies to any source with relationship fields and a narrative notes field.
3. **[R] Unplaced parentage.** Rows whose source flags them as unplaced (`unplaced=True` for D-H, equivalent flags for other sources) must have null relationship fields *unless* `notes` contains a placeholder phrase (`"a king of the Nth Dynasty"`, `"a king of the mid-Nth Dynasty"`). Placeholder captures are routed to a Phase A design queue (whether the placeholder string belongs in a structured field is a curation decision), not flagged as extraction errors.
4. **[T] Role-tuple fidelity.** Only for sources where the transcription header carries an explicit role/title tuple that maps to a structured `roles` field (Dodson-Hilton; some queen lists). Sorted reconciled `roles` equals sorted role tuple parsed from the transcription header. Implicit in item 0's diff; make it an explicit per-row assertion so the failure message names the row, not the chunk.
5. **[T] A/B/C disambiguator drift.** Only for sources where homonym disambiguators are encoded as a single-letter or numeric suffix in the transcription headword (`Ahmose B`, `Tiye A`, `Mutnodjmet Q`). The same suffix must survive into the reconciled row's id and display name. Bidirectional check: a suffix in JSON not in the OCR is also a failure. Highest-value check for Dodson-Hilton specifically.
6. **[R] Dynasty-boundary attribution.** When a row has both a `dynasty` value and a `spouse_names` or `children_names` reference resolvable in the ruler authority, flag any case where the row's `dynasty` differs from the dynasty of the resolved spouse / child. Examples that bite: Tetisheri, Ahhotep I, Tausret, Ankhesenamun. (Until the ruler authority lands in Phase A, this check runs in advisory mode only — flags become a manual review item rather than a blocking failure.)
7. **[T] Greek/demotic alias when both forms are printed.** Only for rows where the OCR transcription (or another pinned authoritative raw reference for that row) explicitly shows both an Egyptian/demotic form and a Greek-form variant, the reconciled row must preserve at least one Greek-form variant in `alt_names`. Examples: Berenike/Berenice, Arsinoe/Arsinoë, Cleopatra-with-numeral. Failure mode: extractors lift only the Egyptian form from a Ptolemaic-era source even when both forms are printed. Do **not** fail rows solely because they are dated after ~525 BCE if the source artifact does not itself attest a Greek-form alias.
8. **[R] Prenomen/nomen swap in spouse references.** When a queen's husband is rendered in the source by his cartouche text (prenomen, e.g. "Menkheperre"), the extractor must rewrite to the nomen form used in the ruler authority ("Thutmose III") before populating `spouse_names`. Phase A dependency: this check requires the ruler authority to exist for resolution. Until then, run in advisory mode — flag any `spouse_names` entry matching a known prenomen pattern (`-re`, `-kheperre`, `-maatre`, etc.) as a manual review item rather than a blocking failure.
9. **[T] Agent-corrected OCR typo.** When the baseline diff (item 0) finds a single short-phrase mismatch where reconciled is closer to plausible English than transcription, route it to a *transcription-fix queue* rather than an extraction-fix queue. (Reference example: Dodson-Hilton Power chunk Tiaa A `"including:"` → `"including a"` — three extraction agents independently corrected an OCR typo in `chunk-p126-p130.md`.) The diff is real but the fix belongs to the transcription, not the row. **Action on this queue depends on whether the transcription is committed:** for sources with committed transcription, the same agent / OCR pass rewrites the offending line in place in the transcription file and lands a `fix(<source>): correct chunk-<chunk> OCR typo` commit; the diff then re-runs and the row should match. For sources where the transcription is gitignored under ADR-017 (Dodson-Hilton), the rewrite happens in the local `raw/chunk-*.md` file (not committed), and the transcription-side correction is instead captured as a `RAMESSIDE_CORRECTIONS`-style entry (or the equivalent `<chunk>_CORRECTIONS` list) in `fix_rows.py` so the row-side fix is repeatable from `reconciled.jsonl` alone.

The human review in Step 12 is invoked only when (a) any check above fails, (b) a small fidelity-drift random sample needs walking against the printed PDF, or (c) the LLM egyptologist-reviewer flags a category not yet in the inventory — in which case Step 12 is the one-time human pass that validates the new category before it is added as a check for all future chunks.

Reference: Dodson-Hilton Power chunk's `human-review-2026-04-15-power.md` documents the four-layer methodology this section was derived from. Layer 1 (notes/roles diff via `diff_power.py`) seeded item 0; Layers 2b (targeted hedge-risk spot-check) and 2c (algorithmic Unplaced audit) became items 2 and 3; items 5–8 were contributed by the egyptologist-reviewer on PR #41 from cross-source experience.

## Step 12 — human Egyptologist sign-off (ADR-017 step 6)

Step 11.5 reduces the human's surface area to: any row that fails an automated check, plus a small (~3-row) random sample for transcription-vs-PDF fidelity drift, plus any new category the LLM egyptologist-reviewer flagged that isn't yet in the Step 11.5 inventory. The remainder of the chunk is signed off algorithmically.

Every extract is still **provisional** at the chunk level until that residual human pass runs. The LLM `egyptologist-reviewer` does NOT satisfy this — ADR-017 explicitly treats human review as a separate layer ("LLM checking an LLM" is labelled as such). Step 11.5 raises the floor; it does not eliminate the human step.

When the human review happens (post-merge is fine), log it in `<source_dir>/human-review-<YYYY-MM-DD>.md` for single-chunk sources, or `<source_dir>/human-review-<YYYY-MM-DD>-<chunk>.md` for multi-chunk sources (e.g. `human-review-2026-05-10-ramesside.md`). The chunk-suffixed form serves two purposes: it disambiguates same-day reviews when multiple chunks are signed off on one session, and it makes the file-listing a self-documenting chunk-audit index. Do NOT use the chunk suffix for single-chunk sources — the un-suffixed form is simpler and the handoff path explicitly reserves the bare date form for those.

The log's body is the same regardless of suffix convention:

1. **Reviewer name** and date.
2. **Rows sampled** — which IDs / pages they actually walked. Be explicit that un-sampled rows remain provisional at the chunk level.
3. **Verdict per row** — correct / needs-fix / deferred. Deferred-items belong on the "outstanding architectural questions" list in the source `README.md` or the project-level memory, not in the audit log itself.
4. **Consequence statement** — "the N reviewed rows are no longer provisional for Phase A authority curation purposes; the remaining M un-sampled rows remain provisional."

Reference: Dodson-Hilton's `human-review-2026-04-15.md` (first human sign-off logged on a Dodson-Hilton chunk — Amarna Interlude; single-chunk naming at that time because the suffix convention wasn't formalised yet, but subsequent Dodson-Hilton reviews must use the `-<chunk>` suffix). Seven high-leverage Amarna rows sampled (Tutankhuaten, Kiya, Meryetaten, Mutnodjmet A/Q, Nefertiti, Ankhesenpaaten, lacuna-group entries) — six validated clean, one (Nefertiti.children_names semantics) deferred as a source-wide architectural question.

---

## Multi-chunk source pattern

Some sources land across multiple PRs that share one source directory (Dodson-Hilton is the reference: Pre-Amarna chunk via PR #37, Amarna chunk via PR #38, Ramesside + Earlier chapters to follow). The pattern extends Steps 1–11 with:

### Per-chunk prompt files

- First chunk: `<source_dir>/prompt.md` (matches single-chunk convention).
- Follow-up chunks: `<source_dir>/prompt-<suffix>.md` where `<suffix>` names the chunk (`prompt-amarna.md`, `prompt-ramesside.md`). Each prompt is chunk-specific — schema references, sub-period string, parsing-hazards section, expected row count — because D-H's chapter structure makes cross-chunk prompts unwieldy.

### Per-chunk agent outputs

- First chunk: `raw/agent-{a,b,c}.jsonl` (matches single-chunk convention).
- Follow-up chunks: `raw/agent-{a,b,c}-<suffix>.jsonl` (`agent-a-amarna.jsonl`, etc.).
- Gitignored via the existing root `pipeline/pipeline/authority/sources/*/raw/*` pattern — no gitignore changes needed.

### `merge.py` union-across-chunks

Each agent tag's rows are collected across all matching files per tag before the majority-vote step. The pattern below is generic — rename `<source>_id` to your source's actual primary-key field (D-H uses `dh_id`, Ryholt uses `ryholt_id`, Kitchen uses `kitchen_id`) before copying. Error-message text mentioning the source by name is illustrative, not load-bearing.

```python
def _load_agent_chunks(agent_dir: Path, tag: str) -> dict[str, dict]:
    base = agent_dir / f"agent-{tag}.jsonl"
    chunks = sorted(agent_dir.glob(f"agent-{tag}-*.jsonl"))
    files = ([base] if base.exists() else []) + chunks
    # ... (empty-files early return omitted for brevity; see merge.py on main)
    combined: dict[str, dict] = {}
    source_of: dict[str, Path] = {}
    for p in files:
        rows = _load(p)
        for primary_id, row in rows.items():  # rename to <source>_id in your copy
            if primary_id in combined:
                raise ValueError(
                    f"Duplicate {primary_id!r} across chunk files: "
                    f"first in {source_of[primary_id]}, again in {p}"
                )
            combined[primary_id] = row
            source_of[primary_id] = p
    return combined
```

Cross-chunk ID collisions raise loudly — within one source, the primary-ID scheme (D&H disambiguator letters like `Ahmes A` / `Ahmes B`, Kitchen prefix-numbers like `21H`/`24E`) is meant to be globally unique. A collision means an extraction bug, not a legitimate homonym.

### Sort-key for lacuna-prefixed IDs

Names starting with `[` (e.g. `[...]18A–H`, `[...]pentepkau`) or `–` (en-dash, e.g. `–18P`, `–18Q`) must NOT be sorted by default ASCII/Unicode order — `[` sorts before every letter (lands at top of file) and `–` sorts after every letter (scatters at end). Use a secondary bin:

```python
LACUNA_PREFIXES: tuple[str, ...] = ("[", "–")

def _sort_key(dh_id: str) -> tuple[int, int, str]:
    top_bin = 1 if dh_id in unplaced_ids else 0
    sub_bin = 1 if dh_id.startswith(LACUNA_PREFIXES) else 0
    return (top_bin, sub_bin, dh_id.lower())
```

Lacuna-prefixed entries sort last *within* each top-level bin (placed / unplaced), matching D&H's own layout. Caught as a latent bug on PR #38 when the Amarna chunk added 5 lacuna rows to a source whose Pre-Amarna chunk had only 1. Add a `test_lacuna_prefixed_ids_sort_last_within_each_bin` regression test.

### Page-offset drift in multi-page chunks

Cite physical pages, never printed pages. But within a single chunk the physical-to-printed offset may shift due to scan-order anomalies: two-page chart spreads captured as a single PDF page, foldouts, part-boundary blank pages. Dodson-Hilton chunk 2 has the offset drift from +11 (printed 142–143) to +12 (printed 147+) because a printed-144-145 spread was scanned as a single page with printed-146 placed before it. Re-verify the offset at the chunk's FIRST and LAST printed pages; log the drift path in `transcribe.md`.

### fix_rows.py gains per-chunk sections

The `SPOT_CORRECTIONS` list grows across chunks. When it doubles (~5 → 10 entries), split into per-chunk lists (`POWER_CORRECTIONS`, `AMARNA_CORRECTIONS`, `RAMESSIDE_CORRECTIONS`) and concatenate into a single flat `SPOT_CORRECTIONS` — better readability without changing the runtime behavior.

### Test file gains per-chunk constants

Multi-chunk sources need per-chunk `SUB_PERIOD_<CHUNK>` and `CITATION_<CHUNK>` constants in the test file. Initially, keep unqualified `SUB_PERIOD = SUB_PERIOD_POWER` / `CITATION = CITATION_POWER` compat aliases so the first-chunk tests stay untouched. When you add a third chunk, drop the aliases and inline-replace in the first-chunk tests — the compat aliases become actively misleading once three or more sub-periods exist.

### Do NOT re-run the 3-agent extraction after a prompt fix

Hard-learned on PR #38. After the PR reviewer flagged two prompt contradictions (casing, lacuna-tail editorials), re-running the 3 extraction subagents with the corrected prompt produced identical output on the prompt-fix-targeted cases but LOST quality on 8 other rows — dropped hedges ("Akhenaten (or Smenkhkare)", "(conceivably)", "(probable)", "If she were the mother of X"), dropped cross-entry inferences, and swapped "perhaps" to "possibly" in one hedged phrase. LLM-extraction variance touches fields the prompt never addressed.

Use surgical `fix_rows.py` overrides on the first-run agent JSONL instead. Before any re-run experiment, copy `.bak` versions of `agent-{a,b,c}-<suffix>.jsonl` so you can revert. The committed `reconciled.jsonl` reflects the first run + accumulated `fix_rows` corrections; don't trade that for a second run's different drift.

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
- **OCR decision tree (supersedes the pre-2026-04-15 "never swap OCR vendors" rule).** The default is still an OCR subagent running on Claude Opus 4.6. If that refuses, retry with a reframed prompt (fair-use scholarly extraction for a private research repo). Only if re-framing also fails, escalate:
  1. **Tier 1 — OCR subagent on Opus 4.6** (default). Content filtering is the most common failure mode; reframing resolves it most of the time (see Ryholt).
  2. **Tier 2 — Main-session Opus 4.6.** A sanctioned exception when (a) the subagent hits content filtering on a bounded chunk AND (b) the main session can Read the PDF pages and transcribe them itself. D-H chunk 2 followed this path. Record the deviation in `transcribe.md` — do not pretend a subagent produced the chunk. The downside is the loss of independent-OCR redundancy, which is why tier 1 remains the default; but the 3-subagent EXTRACTION step (that comes after OCR) provides its own majority-vote redundancy, so losing independence at the OCR layer is not catastrophic for a single chunk.
  3. **Tier 3 — Gemini 3.1 Pro (per-chunk fallback, per ADR-017 amendment 2026-04-15).** Only when both tiers 1 and 2 refuse. Commit the Gemini prompt verbatim at `<source_dir>/transcribe-gemini-prompt.md`; pin the Gemini model version in `transcribe.md`; keep every downstream stage (3-subagent extraction, merge, reviewer, fix_rows) on Opus 4.6. D-H chunk 1 followed this path. The amendment is per-chunk, not source-wide: follow-up chunks of the same source must re-attempt tier 1 from scratch.
  
  The original reason the rule was "never swap vendors" is still valid: vendor-swapping mid-chunk pipeline causes downstream inconsistency (different OCRs make different systematic errors on transliteration, layout, and proper-noun diacritics). The amendment allows the swap only at the OCR layer, only for chunks where Opus genuinely refuses, and never in the extraction / review / post-processing layers that consume the OCR output. That's the constraint that preserves the rule's original intent.
- **Network / DNS flakes push-time.** If `git push` fails with `Could not resolve host` or `CONNECT tunnel failed 502`, retry. If retries fail, schedule a wakeup (`ScheduleWakeup` with ~120s) to come back to it — don't block your session on transient network issues.
- **The git push hook requires `TASK_LIST_UPDATED=1`** when `docs/mvp-tasks.md` is in the commit. Prefix with it or the pre-push hook blocks.
- **Feature-branch policy.** Never push to main. Always create a `feat/source-<name>` branch off main and open a PR. See `feedback_branch_pr.md`.
- **Do NOT commit `.claude/agent-memory/`.** The `code-reviewer` Claude Code subagent writes local memory files under `.claude/agent-memory/` when it runs. These appear as untracked files after a review cycle. They are NOT project files and must not be staged. Stage explicitly by name (`git add pipeline/pipeline/authority/sources/<source>/ pipeline/tests/test_sources_<source>.py`) and never use `git add -A` or `git add .`. If you see `.claude/agent-memory/` in `git status`, it is safe to leave untracked; gitignoring it globally is a separate hygiene task.

## Canonical merge.py shape

Post-PR #155 (Kitchen) is canonical; Ryholt PR #157 / Beckerath PR #146 / Porter-Moss PR #151 / Leprohon PR #128 are all aligned. When scaffolding a new source's merge.py, copy from `pipeline/pipeline/authority/sources/kitchen-tipe/merge.py` and adapt these source-specific pieces:

1. Primary-ID symbol throughout: the row-key field name is `kitchen_id` → `<source>_id` (e.g. `beckerath_id`, `ryholt_id`, `tomb_id`). The `_majority` parameter (`kid` in Kitchen) is a short abbreviation conventionally renamed to match the source's primary-ID short form (`bid` in Beckerath, `rid` in Ryholt, `tid` in PM, `lid` in Leprohon) — internal-only naming, but matching the source's other functions makes diffs across the family cleaner. Keyword-only signature is required regardless of name (constitutional rule 10).
2. `_sort_key` for the source's ID scheme.
3. `DEFAULT_AGENT_DIR = SOURCE_DIR / "raw"`.

Keep verbatim (source-agnostic):

- `SENTINEL_NULL_STRINGS = frozenset({"none", "-", "—", "n/a", "na", "unknown", "null"})` — the `"null"` entry is parity with Leprohon (PR #146 P1.3); a `(None, "null")` pair must collapse to a single vote.
- `_normalise_value` + `_deep_normalise` — sentinel-null collapse, recursive across dicts and lists so a `{"page": "-"}` vs `{"page": null}` agent diff doesn't register as a tie.
- `_normalise_for_merge` — pre-merge canonicalisation hook. Default is a stub returning a shallow copy. Leprohon implements MdC → IFAO transliteration normalisation here for translit sub-fields; other sources currently have no normalisation candidates but the hook is the extension point if a future re-extraction surfaces encoding-style ties.
- `_load_overrides` — JSON loader with strict validation: `isinstance(raw, dict)` at root, `|` separator in every key, both halves non-empty, every value is a dict carrying `value` + `rationale` keys. UTF-8 encoding on `read_text` (override values can carry Egyptian diacritics).
- `_majority` signature and body — keyword-only `<id>`/`field` (constitutional rule 10: no Optional fallback for "legacy callers"); returns the tuple `(chosen_value, top_count)` (the count is used by the disagreement-report writer); deep-normalise input; tie detection via `len(most) >= 2 and most[0][1] == most[1][1]`; lookup `TIE_BREAK_OVERRIDES.get((id, field))` on tie; if hit, return `(_deep_normalise(override["value"]), top_count)` (Gemini PR #155 round-2 parity for the value); if miss, raise with diagnostic listing every distinct candidate.
- `main()` loop: the per-row loop sorts `all_fields` (incidental fix to issue #142 — deterministic merge-disagreements.txt across re-runs) and passes `<id>=<id>, field=field` to `_majority`. Apply `_normalise_for_merge` to each agent's row before the per-field loop.

The override file `tie-break-overrides.json` ships empty `{}` initially. Each tie that surfaces during the first merge run gets:
1. An entry keyed `"<id>|<field>"`, value `{"value": <correct>, "rationale": "<printed-source-citation>"}`.
2. A corresponding test pin in `test_<source>_merge_tie_break.py` asserting the resolved value on disk.
3. A re-run of merge.py to apply.

Iterate until the merge runs cleanly. The override table is the authority's audit trail for every reconciled value that didn't trace to genuine multi-agent agreement.

For sources where the egyptologist post-merge sweep (Step 6) flags row-level corrections that aren't tie-breaks but rather post-merge editorial passes (e.g. Greek-alias-in-parens splits, underdot diacritic restoration, Bibl. ribbon completion), those land in `fix_rows.py`, NOT in `tie-break-overrides.json`. The two files have distinct contracts:

- **`tie-break-overrides.json`** = pre-fix-rows resolution of an ambiguous merge result. Pins agent-extractable values that the 3-agent vote couldn't resolve.
- **`fix_rows.py`** = post-merge editorial corrections that DON'T fit the 3-agent extraction format. Recomputed deterministic fields (Kitchen's `concurrent_with_kings`), printed-source corrections that supersede the verbatim agent extraction, cross-row editorial annotations.

Per constitutional rule 3 (deterministic enforcement over convention), the override → fix_rows interaction is locked by `test_post_fix_rows_pipeline_determinism` per source: pin the FINAL post-fix-rows reconciled value for every override row × field. The pins serve as a tripwire when EITHER file changes the result. See PR #161 for the canonical implementation.
