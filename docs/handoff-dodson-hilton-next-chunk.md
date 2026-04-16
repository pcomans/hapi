# Handoff — Dodson-Hilton next chunk (earlier chapters)

**Written 2026-04-16** by the agent who shipped the Ramesside chunk (PR TBD — 170 rows across House of Ramesses + Feud of the Ramessides + Decline of the Ramessides Brief Lives). Three D&H chunks have now landed, closing chapter 3 (the New Kingdom). The remaining scope is chapters 1, 2, 4, and 5.

Pick this up when the user asks to continue the Dodson-Hilton transcription series. For generic Phase 0 source onboarding, see `docs/playbook-phase-0-ocr-transcription.md`. This handoff **supersedes** the playbook where they disagree — the multi-chunk-source and cross-section-duplicate patterns promoted from chunks 1–3 should be followed verbatim.

---

## Current state on `main` (verify before starting)

- **Dodson-Hilton source directory:** `pipeline/pipeline/authority/sources/dodson-hilton-queens/`
- **Landed chunks (270 rows total, all in chapter 3):**
  - Chunk 1 — Pre-Amarna "Power and the Glory" Brief Lives (printed pp. 137–141, physical pp. 126–130). 59 rows. PR #37, merged.
  - Chunk 2 — Amarna Interlude Brief Lives (printed pp. 154–157, physical pp. 142–145). 41 rows. PR #38, merged.
  - Chunk 3 — Ramesside Brief Lives (three sub-blocks at printed pp. 170–175, 182–183, 192–194 / physical pp. 157–162, 169–170, 178–180). 170 rows. PR TBD.
- **Human review logged:** `human-review-2026-04-15-power.md`, `human-review-2026-04-15.md` (Amarna). Ramesside human review pending (a larger ~10–15-row sample is scheduled post-merge per the PR #39 egyptologist-reviewer recommendation).
- **Primary key is composite** `(dh_id, sub_period)` — introduced in chunk 3 because D&H lists Takhat A, Isetneferet C, and Ramesses C under two Brief Lives sub-sections each. Future chunks will probably encounter more such cases (especially in the OK chapters where Baud 1999's coverage overlaps D&H).

---

## Target for the next chunk

**Remaining scope: chapters 1, 2, 4, and 5 Brief Lives sub-blocks.**

| Chapter | Section | Expected rows | Notes |
|---|---|---|---|
| 1 | Early Dynastic (Dyns 0 / 1 / 2) | ~30–50 | D&H's Dyn 0 list is less authoritative than Dreyer 1998; cross-check. |
| 1 | Old Kingdom (Dyns 3 / 4 / 5 / 6) | ~80–120 | D&H's OK coverage is known-weaker than Baud 1999. Prefer Baud for the OK canonical queens; D&H rows can still land as a cross-reference layer. |
| 1 | "Unplaced — OK / ED" | varies | Check for a trailing Unplaced sub-block. |
| 2 | First Intermediate Period (Dyns 7 / 8 / 9 / 10 / 11) | sparse | D&H's FIP coverage is thin. |
| 2 | Middle Kingdom (Dyns 11 / 12) | ~60–100 | MK queens (Nefru, Mereret, Khnemetneferhedjet I/II, Weret) — well-attested. |
| 2 | Second Intermediate Period (Dyns 13 / 14 / 15 / 16 / 17) | ~40–80 | Ryholt 1997 has more authority here; D&H rows are a cross-reference. |
| 4 | Third Intermediate Period (Dyns 21 / 22 / 23 / 24 / 25) | ~80–120 | Kitchen 1996 TIP + Kitchen 2009 revisions are the authority; D&H provides family-tree context. |
| 5 | Late Period (Dyns 26–31) | ~40–60 | Thin but structured. |
| 5 | Ptolemaic | ~20 | Overlaps `wikipedia-ptolemaic` and `holbl-2001-argead`; cross-reference. |

**Ship one chapter per PR** — chapter 1 is the biggest and should probably split further (OK is a natural sub-chunk given Baud overlap). Don't try to bundle chapters 1–5 into a single PR. The Ramesside PR's ~170-row scale is the upper-bound comfortable size.

---

## Step-by-step plan (for whichever chapter you take next)

### 1. Scope the Brief Lives sub-blocks in the source PDF

- Source PDF: `proprietary/books/Dodson & Hilton 2004 - Complete Royal Families.pdf` (gitignored). SHA pinned in `README.md` and `transcribe.md`: `e636c49f3d0b5b6c6ec072cc6e7af9d605caf52d438c55cd84da9de7b07008a0`.
- Each chapter has ONE Brief Lives sub-block (sometimes with a trailing Unplaced sub-block), typically at the end of the chapter's page range. Verify by extracting a scoping sub-PDF and scanning for the `Brief Lives ●●●●` / `Males in bold, females in bold italic.` header.
- **Re-verify the physical-to-printed offset at both ends of the chunk.** Each two-page genealogical-chart spread captured as a single physical PDF page adds +1 to the offset. Chunk 2 saw one drift (+11 → +12). Chunk 3 saw two (+12 → +13 at printed 160–161 / physical 148, and +13 → +14 at printed 186–187 / physical 173). Earlier chapters may have similar or more.
- Extract a `raw/source-p<start>-p<end>.pdf` per sub-block using the `pypdf` one-shot in `transcribe.md`. Non-contiguous sub-blocks get separate sub-PDFs (chunk 3 pattern: three separate PDFs for the three Ramesside sub-blocks).

### 2. Write `prompt-<chapter>.md`

Copy the structure from `prompt-ramesside.md` — it's the most complete prompt with the composite-key rules and cross-section-duplicate guidance. Adjust:

- Input chunk-file paths.
- `sub_period` enumeration for the chapter's Brief Lives sub-sections.
- `dynasty` assignments per sub_period.
- Role codes. The D&H role-code repertoire is stable — all previously-seen codes are listed in `README.md` § Schema `roles`. Chapter 1 (OK / ED) may introduce new codes for OK-specific roles (e.g. Chief of the Khent, Sole Friend); preserve verbatim. Phase A's code glossary handles expansion.
- Chapter-specific parsing hazards (name-change slashes, multi-generation homonym clusters, etc.).
- **Cross-section duplicates warning** — this is a known issue for this source. Tell agents to flag any `dh_id` they see under two sub-sections in their final report. Do NOT change the schema — the composite `(dh_id, sub_period)` key handles these.

### 3. OCR via the Phase-0 pipeline

- Attempt a Claude Opus OCR subagent first (default playbook path). Claude Opus 4.7 (1M context) subagents succeeded on all three Ramesside sub-blocks in parallel on 2026-04-16 with a fair-use-framed prompt — template the same framing. See the Ramesside OCR subagent prompts in git log for a working model.
- If OCR refuses, re-attempt in main session, then escalate to Gemini 3.1 Pro per ADR-017's amendment. `transcribe-gemini-prompt.md` is the verbatim Gemini prompt used on chunk 1; adapt for the new chunk.
- OCR output format: match `raw/chunk-p157-p162.md` (chunk 3 House of Ramesses). H1 title, short header with page range / OCR method / photo-caption disclosure, H2 per printed page, entries as paragraphs in column-order reading, male names bold / female names bold-italic, role-code parentheses verbatim, footnote superscripts inline, photo captions omitted.

### 4. Spawn 3 extraction subagents in parallel

Same pattern as chunk 3. Each reads the new prompt + the new chunk file(s) and writes `agent-{a|b|c}-<chapter>.jsonl` under `raw/`. Rate-limit note: when a long-running parallel run hits the 3pm-PT limit, subagent files are on disk even if the "report" response gets truncated. Check files before respawning.

**Before spawning:** copy `.bak` versions of chunks 1–3's agent JSONLs. Chunk 3 introduced the habit of backing up before any re-extraction; keep it.

### 5. merge.py and fix_rows.py are ready as-is

The composite-key machinery landed with chunk 3 and handles cross-section duplicates. Chunk 4 just needs:
- A new per-chapter section in `fix_rows.py` (e.g. `EARLY_DYNASTIC_CORRECTIONS: list[tuple[str, str, str, object, str]] = [...]`) concatenated into `SPOT_CORRECTIONS`.
- No merge.py changes expected unless the source PDF has a new edge case.

### 6. Run `fix_rows.py` — apply egyptologist-reviewer's corrections

Corrections come from two stages:
1. Main-agent cross-check against the OCR chunk file (editorial tails, slash-split artifacts).
2. `egyptologist-reviewer` Claude Code subagent walking `reconciled.jsonl` against the source PDF (casing, hedge loss, verbatim-prose drift, cross-entry inference over-reach).

The egyptologist-reviewer writes corrections directly into `fix_rows.py`'s new chapter CORRECTIONS list when high-confidence, or to `reviewer-notes-<chapter>.md` for medium-confidence flags. Main agent applies the latter manually.

### 7. Write tests

- New rule-5 full-row fixtures for every new row. Use the generator pattern at `/tmp/claude/gen_*_fixtures.py` — chunk 3 used `gen_ramesside_fixtures.py` which reads `reconciled.jsonl`, sorts by sub_period then alphabetically, and emits `_assert_full_row(...)` blocks. Delete the generator before committing.
- Update invariants in `tests/test_sources_dodson_hilton_queens.py`:
  - `test_row_count` — add the chapter's row count.
  - `test_row_counts_per_chunk` — add entries for each new sub_period.
  - `test_every_row_has_complete_citation` — add the chapter's CITATION_* constant.
  - `test_dynasty_per_chunk` — add the chapter's sub_period → dynasty mapping.
  - `test_unplaced_set_is_the_expected_ids` — add any new Unplaced ids.
  - `test_unplaced_rows_sort_last_in_reconciled_jsonl` — update the trailing-row count.
  - `test_lacuna_prefixed_ids_sort_last_within_each_bin` — update the placed-row count.
  - `test_role_code_set_spans_the_known_codes` — add new codes.
  - `test_kings_cross_referenced_in_bold_caps_not_extracted_as_entries` — add new regnal-name CROSS-REFERENCES.
  - `CROSS_SECTION_DUPLICATE_IDS` — add any new cross-section duplicates the chapter introduces.

### 8. Update docs

- `README.md` — add the chapter's row to the scope table; extend `sub_period` semantics.
- `transcribe.md` — add the chapter's offset verification points + OCR method used.
- `docs/mvp-tasks.md` — strike through the chapter's bullet with row count + PR number.
- `docs/handoff-dodson-hilton-next-chunk.md` (this file) — update to point at the next chapter, or delete if the Dodson-Hilton series is complete.

### 9. PR, reviewers, CI

Standard Phase 0 workflow per `CLAUDE.md` § "Pull request workflow":
1. Push branch, open PR, request Copilot review via API.
2. Spawn `code-reviewer` and `egyptologist-reviewer` subagents in parallel after Copilot posts.
3. Invoke `scope-accountability-enforcer` before replying to any review batch; prefix replies with `SCOPE_CHECKED=1`.
4. Poll `gh pr checks <N> --watch` until green.

### 10. After merge: log human review

Sample 10–15 rows for egyptologist spot-check. Cover:
- Any cross-section duplicates the chapter introduces (each of the two rows gets a separate sample).
- Any disambiguation-density hot spots (chapter 1 OK: Hetepheres I / II / III / IV; chapter 4 TIP: multiple Shoshenqs; chapter 5 LP: Nitocris / Ankhnesneferibre).
- At least one lacuna-prefixed entry.
- At least one Unplaced entry (if the chapter has them).
- At least one role with a novel role code.

Log in `human-review-<YYYY-MM-DD>-<chapter>.md`. Mark remaining un-sampled rows as provisional at chunk level.

---

## Known traps (learned on chunks 1–3)

1. **Do NOT re-run the 3-agent extraction after a prompt fix.** Re-running loses quality on fields the prompt never targeted. Use `fix_rows.py` for surgical corrections instead. See the playbook's "Do NOT re-run the 3-agent extraction after a prompt fix" section for the concrete PR #38 regression.
2. **Scan-order anomalies shift the physical-to-printed offset mid-chunk.** Verify at both ends of every chunk; document the drift path in `transcribe.md`. Each two-page chart spread captured as one physical page adds +1 to the offset.
3. **Cross-section duplicates are legitimate.** Do NOT merge them or drop them. Each Brief Lives entry is its own row; the composite `(dh_id, sub_period)` key preserves both. D&H uses this pattern when an individual's family role spans two sub-sections (e.g. Takhat A is both daughter-of-Ramesses-II in House of Ramesses and wife-of-Sety-II in Feud).
4. **Letter-suffix reuse across sub-sections is also legitimate.** Ramesses C in House of Ramesses (grandson of Ramesses II) is a DIFFERENT individual from Ramesses C in Decline of Ramessides (son of Ramesses III, later Ramesses IV). D&H re-scopes letter suffixes per chapter's family tree. Composite key handles this.
5. **Agent JSONL files stay under `raw/` and are gitignored.** Stage explicitly by filename when committing; never `git add -A`. The `code-reviewer` subagent writes local memory under `.claude/agent-memory/` that must NOT be staged.
6. **The pre-push hook requires `TASK_LIST_UPDATED=1`** when `docs/mvp-tasks.md` is in the commit. Prefix with it or the hook blocks.
7. **`gh pr create` may hit TLS sandbox errors.** Retry with `dangerouslyDisableSandbox: true` on that specific call — sandbox-restricted networking blocks GitHub's GraphQL endpoint in some configurations. Do not swap to other tools.
8. **The legacy unsuffixed `agent-{a,b,c}.jsonl` filename pattern was retired in chunk 3.** Every chunk from now on carries an explicit suffix (`-power`, `-amarna`, `-ramesside`, `-ed_ok`, etc.). `merge.py`'s `_load_agent_chunks` only matches `agent-{tag}-*.jsonl` now.

---

## Non-goals for the next chunk

- Do NOT pick up the Phase A authority-curation work — Phase 0 must be complete first (Porter-Moss I and III, Baud 1999 OK, and the remaining D&H chapters are the last hard blockers).
- Do NOT re-open the parent→child denormalization question. It's deferred to Phase A and the decision must be made consistently across all Phase 0 sources; making it per-source creates drift.
- Do NOT re-run chunks 1–3's extraction subagents. Their `reconciled.jsonl` values are committed; chunk-level diffs from an unnecessary re-run will pollute the next PR.
- Do NOT start on a second chapter in the same PR. One chapter per PR keeps review surface-area tractable.

---

## Memory pointers

- Project-level memory: in a Claude Code session, the per-project agent memory lives under `~/.claude/projects/<project-slug>/memory/` on macOS. Look for `project_current_pr_state.md` there — it has the authoritative list of what's landed vs pending. The exact path varies by environment; a fresh Claude Code session on this repo will surface it automatically via auto-memory loading.
- User feedback rules: `feedback_autonomy.md`, `feedback_branch_pr.md`, `feedback_push_after_commit.md`, `feedback_pr_review_replies.md`, `feedback_ci_failures.md`, `feedback_copilot_review.md`, `feedback_pr_reviewers.md` — read all of them before starting. They reflect specific patterns the user has corrected in prior sessions.
- Constitutional rules: `CLAUDE.md` rules 1–12 are non-negotiable. Especially rule 1 (scholarly traceability), rule 5 (tests assert values), rule 6 (raw data sacred), rule 12 (existing violations don't justify new ones).

Good luck. The pattern is well-established across three chunks now; chapter-per-PR should be a clean pass if the source PDF is readable and the OCR doesn't refuse.
