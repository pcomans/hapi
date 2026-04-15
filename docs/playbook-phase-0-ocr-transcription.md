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

Expected committed files per source (11-ish):
- `.gitignore` (if you extended the ignore pattern)
- `docs/mvp-tasks.md`
- `pipeline/pipeline/authority/sources/<source>/README.md`
- `pipeline/pipeline/authority/sources/<source>/transcribe.md`
- `pipeline/pipeline/authority/sources/<source>/prompt.md`
- `pipeline/pipeline/authority/sources/<source>/merge.py`
- `pipeline/pipeline/authority/sources/<source>/fix_rows.py`
- `pipeline/pipeline/authority/sources/<source>/reconciled.jsonl`
- `pipeline/pipeline/authority/sources/<source>/merge-disagreements.txt`
- `pipeline/pipeline/authority/sources/<source>/raw/.gitkeep` (keeps the dir tracked; everything else under `raw/` is ignored via `raw/*`)
- `pipeline/tests/test_sources_<source>.py`

**Deterministic JSONL output.** Write `reconciled.jsonl` with `json.dumps(..., sort_keys=True)` in both `merge.py` and `fix_rows.py`. Without sorted keys, Python's dict iteration order makes the file re-shuffle on every re-run even when values are identical — spurious diffs pollute the PR and make the authority file look unstable.

PR title: `feat: transcribe <Book short name> → sources/<source>`.

PR body follows the Ryholt PR (#34) template: rights verification, scope, known gaps, test plan, explicit LLM-vs-human labelling ("an actual Egyptologist sign-off pass has NOT been performed").

Then per `CLAUDE.md` PR workflow:
1. Request Copilot review (via `gh api` POST to `/pulls/<N>/requested_reviewers`, not `gh pr edit --add-reviewer` which has been flaky).
2. **Arm a `Monitor` for Copilot's re-review.** Copilot lands its review minutes after the push. Sitting idle waiting for the review (or worse, waiting for the user to prompt "look at review comments") breaks the workflow. The Monitor-pattern emits one in-chat notification on the terminal state:
   - Success: a Copilot review whose `commit_id` matches the current HEAD.
   - Timeout: no new review in 15 min → treat as implicit acceptance or ask the user.
   
   See `CLAUDE.md` § "Pull request workflow" step 2 for the exact Monitor invocation. Filtering on `commit_id == <HEAD>` catches multi-round reviews (Copilot occasionally submits review #2 minutes after #1) without re-surfacing stale reviews of previous commits. Re-arm on each subsequent push so the next push's Copilot re-review also gets caught.
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
- **Fragile gitignore patterns.** Listing specific filename patterns (`raw/chunk-*.md`, `raw/agent-*.jsonl`) means any new file the subagent drops into `raw/` becomes committable. Prefer `raw/*` + `!raw/.gitkeep`.

Apply the fixes in a fresh commit (`fix(<source>): address <reviewer> first pass`), re-run tests, push. Poll CI and the review threads for a second round.

## Step 12 — human Egyptologist sign-off (ADR-017 step 6)

Every extract is **provisional** at the chunk level until a human with Egyptology training reads a sample (~5–10 rows) against the source PDF and signs off. The LLM `egyptologist-reviewer` pass does NOT satisfy this — ADR-017 explicitly treats human review as a separate layer ("LLM checking an LLM" is labelled as such).

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
- Gitignored via the existing `raw/*` pattern — no gitignore changes needed.

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

Hard-learned on PR #38. After Copilot flagged two prompt contradictions (casing, lacuna-tail editorials), re-running the 3 extraction subagents with the corrected prompt produced identical output on the prompt-fix-targeted cases but LOST quality on 8 other rows — dropped hedges ("Akhenaten (or Smenkhkare)", "(conceivably)", "(probable)", "If she were the mother of X"), dropped cross-entry inferences, and swapped "perhaps" to "possibly" in one hedged phrase. LLM-extraction variance touches fields the prompt never addressed.

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
