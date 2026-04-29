# Porter-Moss I.2 post-processor — handoff

**TL;DR.** Beckerath (#131) shipped via PR #139 (`dab13bda`) on 2026-04-28 — the column-drift OCR class for that source is closed. **Porter-Moss I.2 (issue #132) is the next source on the queue per meta-issue #137 ranking** (rank 2, Med-High ROI). Same root failure as Beckerath: three agents read the same garbled input and unanimously emit the same wrong value, so the disagreement log sees nothing. Different *mechanism* (deterministic publisher text-layer noise rather than double-page-spread image-OCR drift), so different fix (Unicode-fixup table, not split-page rendering).

## What's already done

- **Meta-tracking issue #137** ranks all Phase-0 sources by ROI for the Leprohon-#130-style structural-pre-processor rollout.
- **PR #139** shipped Beckerath (#131): split-single-book-page OCR, 35 fix_rows overrides, 174-row reconciled. The egyptologist-diff-against-printed-PDF pattern caught one OCR LLM-autocomplete regression (06.04 `Mer-en-rê` substituted to `Mer-en-ptah`) that the 3-agent merge could not detect.
- **PR #130** (Leprohon prototype) is the methodological blueprint: a `transcribe_chunk.py` post-processor that flattens the text-layer noise BEFORE the 3-agent extraction reads it.

## The blocker (next agent's problem)

PM I.2 input is the **Griffith Institute publisher pypdf text-layer dump**, NOT a Claude Code subagent OCR pass. It's deterministic — same input, same output — but the publisher OCR has reproducible glyph-class noise that the 3 agents can't disambiguate from clean text:

1. `I;I` (capital-I, semicolon, capital-I) → should be `ḥ` (underdot-H). Example: KV36 `Maihirper` renders as `MAI;IIRPER`.
2. `gḥ` → should be `ḍḥ` (underdot-D glyph). Example: QV47 `Sit-ḍḥout` renders as `Sit-gḥout`.
3. `c` → should be `ʿ` (ayin) **only in Egyptian-name positions**. Example: KV55 `Smenkhkarec`. Critically: `c` survives as-is in English place-names (`Cairo`) — context-sensitive replacement.
4. `I Il` / `I_Il` / `I-Il` → should be `III`. Roman-numeral collapse caused by the publisher text layer rendering `III` as `I-space-I-lowercase-l`. Example: KV22 `Amenophis III` becoming `Amenophis II`.
5. Running-header digit garble: `[1st ed. 24]` cross-references render as `1st` / `Ist` / `rst` / `xst` — same source character class, agents argue.
6. Single-digit page-number misreads in running headers (KV15 page 532 vs 533).
7. Footnote/bibliography clusters carry digit-strings that look like page numbers — must NOT be rewritten by the page-number fixer.

**~35 field-disagreements in `merge-disagreements.txt` + ~50 entries in `fix_rows.py`** (the de-facto tie log for this source — many character-class corrections went straight into `fix_rows.py`). **~50-60% of ties are structural-OCR-loss**, sampled in `/tmp/claude/source-triage-2026-04-28.md`.

## What you (the next agent) should do

### 1. Read the existing structure first

The PM source dir has a chunked workflow (Beckerath was a single chunk; PM has multiple). Don't assume the Beckerath layout:

- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/transcribe.md` — current transcription protocol
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/prompt.md` + `prompt-chunk-N-*.md` — per-chunk extraction prompts
- `merge.py`, `fix_rows.py`, `reconciled.jsonl`, `merge-disagreements.txt`
- `raw/` (gitignored chunk text files)

### 2. Build a Unicode-fixup post-processor

Add `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/postprocess.py` (mirror Beckerath's `postprocess.py` pattern: pure function on the chunk text, atomic write, idempotent re-run, `process_chunk(md) -> md` library entrypoint). It should:

1. Apply a context-aware Unicode-fixup table to the pypdf text-layer output BEFORE the 3-agent extraction reads it.
2. Persist the fixup table as a **separately-committed `postprocess-fixups.yaml`** (or `.json`) so future-me can extend it without re-touching the post-processor logic.
3. Wrap footnote / bibliography clusters in a `<bibcite>…</bibcite>` marker so the page-number digit fixer can't accidentally rewrite digits inside citations.
4. Wrap each KV / QV / TT entry block in `<entry id="KV13">…</entry>` so row boundaries can't be lost to line-wrap.
5. Be idempotent (re-running on its own output produces the same output — Beckerath's `_INJECTED_COMMENT_RE` strip-and-re-emit pattern is a working precedent).

**Critical context-sensitivity**: rule (3) above (`c → ʿ`) MUST NOT replace `c` globally. The Griffith Institute text layer mixes English place-names (`Cairo`, `Carter`, `cf.`) with Egyptian transliteration. Either restrict the substitution to within `<entry>` blocks AFTER you've identified Egyptian-name positions, or use a regex that only fires on `c` when adjacent to other transliteration markers (`-`, `'`, end-of-Egyptian-token). Validate with a test case using a PM I.2 chunk that contains BOTH `Cairo` and `Smenkhkare`c`.

### 3. Diff old vs new reconciled.jsonl with the egyptologist subagent

The Beckerath workflow's load-bearing reviewer pass was the **egyptologist-reviewer comparing OLD vs NEW `reconciled.jsonl`** against the printed source. It caught the 06.04 `Mer-en-rê` → `Mer-en-ptah` LLM-autocomplete regression that no other reviewer would have surfaced — the 3-agent merge structurally cannot detect unanimous-but-wrong values, so the diff is the only way to catch them.

For PM, the printed source is `Porter & Moss, Topographical Bibliography I.2 — Theban Necropolis` (Griffith Institute, 2nd ed. 1964 / 1st ed. 1927-1951 depending on chunk). Confirm with the project lead which edition is the truth-source for each chunk before the egyptologist diff.

Spot-check Egyptian-name fields, occupant_name, page citations against the printed PDF on a sample of 15-20 rows scattered across chunks. Same methodology as Beckerath PR #139's egyptologist diff.

### 4. Update fix_rows.py

After the post-processor + re-merge, audit `fix_rows.py`. Many of the ~50 existing entries are character-class corrections that the post-processor now obviates. Drop redundant ones; keep only true-OCR-error overrides; document each surviving override with a scan reference.

Same rules as Beckerath PR #139: every OVERRIDES key has a matching OVERRIDE_LOG rationale; the audit-log writer expands shared notes via `_GREEK_ALIAS_NOTE`-style constants if a rationale repeats; raise on missing OR stale OVERRIDE_LOG entries (constitutional rule 2 — no silent fallbacks).

### 5. Update tests + open the PR

Test expectations to lock:
- Row count (current PM count — confirm before edit)
- Specific Egyptian-name fields fixed by the post-processor (e.g. `KV36 Maihirper`)
- `Smenkhkareʿ` ayin (NOT `Smenkhkarec`)
- `Cairo` survives unchanged (regression test for the context-sensitivity)

Per PR #139 lessons learned:

- **Run `git status` from the repo root before every commit.** PR #139 had 5 commits silently miss the `pipeline/tests/` directory because my shell cwd was at `pipeline/` and `git add pipeline/` was resolving to `pipeline/pipeline/`. CI failed every commit and I dismissed the failures as Gemini "stale cache" before realising my own bug. Run `pwd && git status` before `git add`.
- **Trust the reviewer's reading of the *committed* state over your local-disk view.** When CI fails on something pytest passes locally, your working tree is ahead of git.
- Run `code-reviewer` + `egyptologist-reviewer` subagents in parallel after PR-open. Run the egyptologist diff (old vs new reconciled) explicitly — it's separate from the regular review pass and catches the unanimous-but-wrong class.
- After every push to the PR branch: `/gemini review` (or check Gemini quota first via the curl recipe in CLAUDE.md, fall back to `@codex review` if quota'd). Arm `/watch-pr-reviews` to be notified of incoming review events.

## Out of scope

- **Don't migrate other sources in this PR.** Ryholt #133 and Baud #134 each have separate non-flattener fix paths documented in their issues.
- **Don't change merge.py semantics.** PR #128's tie-break enforcement holds.
- **Don't touch the diacritic-policy strip rules** (`ḥ → h`, etc.). Per issue #132, those are downstream normalisations that already happen post-merge per the schema; track as a separate follow-up if needed.
- **Don't try to evaporate transliteration-school disagreements** via stricter prompts. The 3-agent vote handles real ambiguity correctly; only the deterministic publisher-OCR noise is in scope.

## Risk: what NOT to do

- **Don't apply `c → ʿ` globally.** The Griffith Institute text mixes English with transliteration. Context-sensitivity is mandatory.
- **Don't rewrite digits inside bibliography clusters.** Wrap in `<bibcite>` first.
- **Don't blindly delete existing `fix_rows.py` overrides.** Re-evaluate each against the post-processed merge output. Some may obviate; some may need different correction values; some may surface as still-needed.
- **Don't ship without the egyptologist diff** — the 3-agent merge cannot detect unanimous-but-wrong values; only the printed-PDF cross-check can. PR #139 caught one such regression in a row that pre-merge looked clean.

## Acceptance criteria

- [ ] `postprocess.py` lands as a pure function with a YAML / JSON fixup table; idempotent re-run.
- [ ] `<bibcite>` and `<entry id=...>` markers wrap the relevant blocks.
- [ ] `c → ʿ` substitution context-sensitive — `Cairo` and similar English tokens survive.
- [ ] Re-merged `reconciled.jsonl` validated by egyptologist diff against the printed Griffith Institute PDF on a 15-20 row sample.
- [ ] `fix_rows.py` audit: redundant overrides dropped, surviving overrides re-verified against the printed source, OVERRIDE_LOG complete.
- [ ] All pipeline tests pass; egyptologist-reviewer + code-reviewer + Gemini review on the PR HEAD clean.
- [ ] `git status` confirms no uncommitted edits in `pipeline/tests/` before each push.

## References

- Issue #132 — https://github.com/pcomans/hapi/issues/132 (this work)
- Issue #137 — meta tracking issue
- PR #130 — Leprohon prototype (the post-processor pattern this work mirrors)
- PR #139 — Beckerath OCR redo (`dab13bda`); read `pipeline/pipeline/authority/sources/beckerath-1997-chronologie/postprocess.py` and `transcribe.md` for the file layout / docstring style
- ADR-017 — Phase-0 transcription protocol + escalation tiers
- Triage `/tmp/claude/source-triage-2026-04-28.md` — per-source ROI ranking
- `docs/playbook-phase-0-ocr-transcription.md` — multi-chunk OCR pattern
- Constitutional rule 2 (`CLAUDE.md`) — no silent fallbacks, raise on errors
- Constitutional rule 6 (`CLAUDE.md`) — reconciled data is sacred

## After this: Ryholt SIP (#133)

When PM ships, the next on the queue is Ryholt #133 (rank 3, Med ROI): asterisk-italics-bleed regex + Chronological Table row-column markers. Same methodological pattern. After Ryholt, the remaining sources (Baud, Dodson-Hilton, Kitchen) have non-flattener fix paths documented in their own issues; HKW is out of scope (no 3-agent merge ever ran).
