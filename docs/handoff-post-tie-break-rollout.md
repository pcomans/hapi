# Handoff — post tie-break rollout (2026-04-29)

**TL;DR.** The cross-source rule-2 enforcement rollout is structurally complete: all 5 ingested Phase-0 sources (Leprohon, Beckerath, Porter-Moss I.2, Kitchen-TIPE, Ryholt SIP) now raise loudly on uncovered ties via `tie-break-overrides.json`; cross-source loader parity is in place; a deterministic CI gate locks the override → fix_rows pipeline on Porter-Moss; the playbook has been updated with the canonical merge.py shape so future onboardings inherit the pattern. **No urgent follow-up.** What remains is small grind work, schema work, or net-new Phase-0 onboarding — none time-sensitive.

## What shipped this session (11 PRs)

| PR | Closes | What |
|---|---|---|
| #146 | #144 | Beckerath rule-2 enforcement |
| #148 | #147 | Beckerath Dyn 29-30 fix_rows split (Greek-alias + prenomen pair) |
| #151 | #145 | Porter-Moss rule-2 enforcement |
| #155 | #136 | Kitchen rule-2 enforcement |
| #156 | #149, #154 | Beckerath negative-class discriminator test + cross-source loader parity (Beckerath/Leprohon/PM): UTF-8, empty-half check, value-shape validation, deep-normalise on override value |
| #157 | #133 | Ryholt rule-2 enforcement |
| #159 | #158 | Cross-source `isinstance(raw, dict)` top-level check on `_load_overrides` |
| #160 | #150 | Beckerath Late Period adjacent-row sweep (28.01, 26.02, 26.05, 29.02 — 15.04-style splits) |
| #161 | #152 partial | Porter-Moss `test_post_fix_rows_pipeline_determinism` — pins the FINAL post-fix-rows value for every override row × field, with coverage sanity-checks |
| #162 | — | Playbook documents canonical merge.py shape + override-vs-fix_rows contract |

`main` HEAD as of session end: `1cda367c`. 1280+ tests pass.

## What "rule-2 enforcement" means here

Each source's `merge.py` previously used `Counter.most_common(1)[0]` which silently first-seen-picked at any tie — a constitutional-rule-2 violation (the value depends on Python `dict` insertion order which depends on `os.listdir` etc., so the reconciled output is non-reproducible). Each rollout PR replaced this with option-(a) enforcement:

- `_majority` requires keyword-only `<id>`/`field` args (rule 10 — no Optional fallback).
- Detect tie via `len(most) >= 2 and most[0][1] == most[1][1]`; covers 1/1/1 (3 distinct) and 1/1 (one agent missed the row).
- On tie, look up `(<id>, field)` in `TIE_BREAK_OVERRIDES`. Hit → return `(_deep_normalise(override["value"]), top_count)`. Miss → raise `ValueError` listing every distinct candidate so the next agent has the data to add an override.
- Override value passes through `_deep_normalise` for parity with majority-vote values (sentinel-null collapse).

The override file format is `{"<id>|<field>": {"value": ..., "rationale": "..."}}`. Loader validates: top-level dict, `|` separator, both halves non-empty, value is dict carrying `value` + `rationale`. UTF-8 encoding (override values can carry Egyptian diacritics).

## Canonical reference

**Kitchen** (`pipeline/pipeline/authority/sources/kitchen-tipe/merge.py`) is post-#155 canonical. When scaffolding a new source, copy from Kitchen and adapt source-specific pieces only:

1. Primary-ID symbol: `kitchen_id` → `<source>_id`. The `_majority` parameter is the source's short form (`bid` / `rid` / `tid` / `lid`).
2. `_sort_key` for the source's ID scheme.
3. `DEFAULT_AGENT_DIR = SOURCE_DIR / "raw"`.

Verbatim from Kitchen: `SENTINEL_NULL_STRINGS` (including `"null"`), `_normalise_value` + `_deep_normalise`, `_normalise_for_merge` stub, `_load_overrides` with all validation, `_majority` body, sorted-fields in `main()`, the override → fix_rows-mutation contract.

`docs/playbook-phase-0-ocr-transcription.md` § "Canonical merge.py shape" walks through this in detail (added in PR #162).

## Open issues, ranked

### Small grind work — nice-to-have, fresh session preferred

- **#152 — 5 PM P2 corrections + P3 adjacent sweep.** Each row-correction needs a careful printed-source read of PM I.2 PDF. Tedious; high error rate when tired. Specific items:
  - KV42 paraphrase of `(?)` headword marker (rule-1 provenance gap).
  - SWV-HatshepsutSouth mid-sentence truncation (drops `quartzite, in Cairo Mus. Ent. 47032`).
  - DAN-AhmosiHenutempet drops `formerly in possession of Castellari`.
  - DAN-AntefSekhemreHeruhirmaet picks farther-from-print agent variant; relies on fix_rows for `Ḥ` underdot.
  - DAN-Aqhor rationale flags only `Ḳ` underdot but PM prints `ʿAḲ-ḤOR` with two underdots.
  - P3 sweep: PM pp 603-605 + p 759 for similar diacritic-loss / fix_rows-delegation pattern.
- **Issue #158 partial — `sort_keys=True` on Ryholt's `OUT.write_text`.** Deferred from #157 because regenerating Ryholt's reconciled.jsonl byte-for-byte requires `raw/agent-{a,b,c}.jsonl` which aren't on disk in this session. Trivial code change once those files are regenerable.

### Multi-component schema work — careful, not tired

- **#153 — `notes_footnote` schema split.** PM QV74 has a footnote-1 genealogy (Wife/mother/daughter of Ramesses IV with Gauthier/Černý/Seele citations) that was previously synthesized into `notes_from_pm` — a rule-1 provenance violation. PR #151 dropped the synthesis; the genealogy data is currently lost. Restoring it requires:
  1. Pydantic model addition in `pipeline/types/canonical.py`.
  2. SQLAlchemy column in `pipeline/types/models.py`.
  3. Alembic migration.
  4. `cd web && pnpm drizzle-kit introspect` to regen the TypeScript types.
  5. Commit all together (per CLAUDE.md "These schemas must stay in sync").
  6. Sweep all 5 sources for similar main-text-vs-footnote conflations now that the schema supports them.

### Big strategic work — needs token budget + fresh decision

- **#134 Baud OK Royal Family** (Famille royale AE vol 1 + vol 2). PDFs in iCloud, symlinked. Source has NO `raw/`, NO `reconciled.jsonl` — never ingested. Full Phase-0 onboarding required (OCR via Dagster, 3-agent extraction, merge, fix_rows, tests, reviewers). ~3-4h substantive work + token cost.
- **#135 Dodson-Hilton Royal Families** (Complete Royal Families). Same shape as Baud — never ingested, full Phase-0 onboarding. Per `docs/handoff-dodson-hilton-next-chunk.md` for chunk continuation conventions.

The original cross-source rollout queue treated these as "tie-break propagation"; that framing was wrong — they're full Phase-0 ingestion projects, not code edits. Tracked per-source so a fresh agent can scope properly.

## Important conventions / pitfalls to inherit

- **PDF preflight before any source-touching PR.** First step on any tie-break / fix_rows / merge-stage PR: `ls /Users/philipp/code/hapi/proprietary/books/ | grep -i <source>`. PDF absent → STOP + AskUserQuestion BEFORE writing code. Saved as `feedback_pdf_preflight.md` after I started PR #155 (Kitchen) without checking.
- **`proprietary/books/` is now a symlink to iCloud** (`/Users/philipp/Library/Mobile Documents/com~apple~CloudDocs/Hapi/proprietary/books`). 16 PDFs reachable: Beckerath 1997 + 1999, Leprohon 2013, PM I + I.2 + III + III.2, Kitchen 1996, Ryholt 1997, Baud 1999 vol 1+2, Dodson-Hilton 2004, Aston 2009, Hölbl 2001, Hornung-Krauss-Warburton 2006, Shaw 2000.
- **Run BOTH reviewers on every PR. No exceptions.** `feedback_pr_reviewers.md` was tightened on 2026-04-29 after I skipped both on PR #148 (small change + Gemini clean) — that judgment was rejected. The rule is unconditional: code-reviewer + egyptologist-reviewer in parallel after `gh pr create`, regardless of PR size.
- **`tie-break-overrides.json` is the audit trail, not just config.** Every entry's `rationale` MUST cite a printed page or scan reference. Loader rejects entries missing structured citations. The override file is THE record of "this reconciled value didn't trace to multi-agent agreement; here's why we resolved it this way" — constitutional rule 6.
- **`fix_rows.py` and `tie-break-overrides.json` have distinct contracts.** Override = pre-fix-rows resolution of merge ambiguity. fix_rows = post-merge editorial corrections (Greek-alias splits, underdot restoration, deterministic recomputation a-la Kitchen's `_compute_concurrency`). The deterministic CI test in PR #161 (PM only currently) locks the interaction; copy that test pattern when adding/updating overrides on other sources.
- **Egyptologist prior pass is not a free pass.** Reviewers can find new issues on the same row in successive PRs. PR #146 round-1 egyptologist found 4 P1s (KV39 truncation, QV47 wrong consonant `ḍ`/`ḏ`, QV74 main-text/footnote conflation, DAN-Mentuhotp wrong consonant `Ḍ`/`Ḏ`). All were genuine wrong-data risks that reviewer-clean Gemini missed. Don't degrade to OLD-vs-NEW reconciled diff — `feedback_egyptologist_diff_requires_printed_source.md`.

## Rollout queue completion state

The original handoff (`docs/handoff-leprohon-tie-break.md` etc.) treated all 6 remaining sources as code-edit propagation. That was wrong:

- **Kitchen / Ryholt / Beckerath / Porter-Moss / Leprohon** — were code-edit propagation. ✅ Done.
- **Baud / Dodson-Hilton** — never ingested. Phase-0 onboarding. Different shape entirely.

A fresh agent should NOT continue the "rollout queue" framing for Baud / Dodson-Hilton; treat each as a standalone Phase-0 onboarding project per `docs/playbook-phase-0-ocr-transcription.md` (which now includes the rule-2 enforcement built into the canonical merge.py shape, so they'll start correct).

## What "all reviewer P1s addressed" actually means

Each PR went through 1-4 rounds of Gemini, plus per-PR code-reviewer + egyptologist-reviewer. Substantive findings that required real fixes:

- **PR #146**: 3 P1 from code-reviewer (empty-bid/field check, `null` sentinel, Dyn 29-30 rationale text). 4 P1 from egyptologist (KV39/QV47/QV74/DAN-Mentuhotp wrong-data). All addressed.
- **PR #148**: retroactive review surfaced 2 P2 + 1 P3 adjacent rows (28.01/29.02/26.02/26.05) → tracked as #150, shipped via PR #160.
- **PR #155**: Gemini found `_load_overrides` value-shape validation gap (round-1) and override deep-normalise gap (round-2). Egyptologist verified all 4 Kitchen overrides match printed Table 1.
- **PR #157**: Gemini round-1 found top-level dict check gap; code-reviewer found `DEFAULT_AGENT_DIR` portability bug.
- **PR #160**: Gemini rounds 1-3 caught factual semantic errors (Greek vs Egyptian inversions in comments). Egyptologist verified all 4 final values against PM I.2 p192.

Pattern to internalise: even after a clean local-reviewer pass, Gemini's iteration often finds real issues on subsequent rounds. Don't merge after one clean Gemini round if there's reasonable expectation of further iteration; do merge per `feedback_review_round_diminishing_returns.md` if later rounds only narrow on the same artifact.

## Memory rules added/tightened this session

- `feedback_pdf_preflight.md` (new) — `ls proprietary/books/` is the FIRST step on source-touching PRs.
- `feedback_pr_reviewers.md` (tightened) — both reviewers run on every PR no exceptions.

## Where things live

- Source code: `pipeline/pipeline/authority/sources/<source>/merge.py` + `tie-break-overrides.json` + `fix_rows.py`.
- Tests: `pipeline/tests/test_<source>_merge_tie_break.py` (enforcer machinery + on-disk pins) + `pipeline/tests/test_sources_<source>.py` (value assertions).
- Reviews from this session: `/tmp/claude-501/code-reviewer-review-pr*.md` and `/tmp/claude-501/egyptologist-review-pr*.md` (local only; not committed).
- Playbook: `docs/playbook-phase-0-ocr-transcription.md` (post-#162).

## Recommendation for fresh-session pickup

1. Read `docs/playbook-phase-0-ocr-transcription.md` end-to-end — it now reflects the canonical shape.
2. Pick #134 Baud OR #135 Dodson-Hilton OR #153 schema split based on what the user wants. Don't try to do both Baud and Dodson-Hilton in one session.
3. If user asks for "more rollout work": re-read the per-issue check above. The remaining issues are genuinely smaller / different shapes — don't pretend they're the same project.
4. Apply `feedback_pdf_preflight.md` as the FIRST step. Apply `feedback_pr_reviewers.md` (both reviewers, no exceptions) for every PR.
