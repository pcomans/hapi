# Handoff — Dodson-Hilton next chunk (Ramesside Brief Lives)

**Written 2026-04-15** by the agent who shipped PR #37 (Pre-Amarna, 59 rows) and PR #38 (Amarna Interlude, 41 rows). Pick this up when the user asks to continue the Dodson-Hilton transcription series, or when a fresh session needs to pick up Phase 0 authority work and has spare review budget.

This doc is specific to D-H chunk 3 (Ramesside). For generic Phase 0 source onboarding, see `docs/playbook-phase-0-ocr-transcription.md`. This handoff **supersedes** the playbook where they disagree (the multi-chunk-source pattern sections in the playbook were promoted from this very handoff; future agents should read both).

---

## Current state on `main` (verify before starting)

- **Dodson-Hilton source directory:** `pipeline/pipeline/authority/sources/dodson-hilton-queens/`
- **Landed chunks (100 rows total):**
  - Chunk 1 (Pre-Amarna "Power and the Glory" Brief Lives) — printed pp. 137–141, physical pp. 126–130. 59 rows. PR #37, merged.
  - Chunk 2 (Amarna Interlude Brief Lives) — printed pp. 154–157, physical pp. 142–145. 41 rows. PR #38, merged.
- **Human review logged:** `pipeline/pipeline/authority/sources/dodson-hilton-queens/human-review-2026-04-15.md`. Seven Amarna rows validated non-provisional; one (Nefertiti.children_names) deferred source-wide. Pre-Amarna rows + remaining 34 Amarna rows are still provisional at chunk level.
- **Outstanding architectural question (deferred to Phase A, NOT to this PR):** parent→child denormalization in `children_names`. Keep current mixed pattern (own-entry prose + a small set of cross-entry inferences for Shuttarna II→Gilukhipa, Tushratta→Tadukhipa) unless the user explicitly re-opens this.

---

## Target for this chunk

**Chunk 3 — House of Ramesses / Feud of the Ramessides / Decline of the Ramessides Brief Lives.** Printed pp. 158–194. Dynasty 19 and 20 prosopography — Nefertari, Isetnofret, Tausret, the multiple Ramesses, Merenptah, Sety I/II, and the Dyn-20 succession. Expected row count: ~60–80 Brief Lives entries across three sub-sections.

**Schema:** identical to chunks 1 and 2 (same book, same schema). The existing `README.md` schema section is authoritative; extend the `sub_period` enumeration with the three Dyn-19/20 sub-section titles as D&H prints them.

---

## Step-by-step plan

### 1. Scope the Brief Lives sub-blocks in the source PDF

- Source PDF: `proprietary/books/Dodson & Hilton 2004 - Complete Royal Families.pdf` (gitignored). SHA pinned in `README.md` and `transcribe.md`.
- Open it with `Read` (`pages:"N-M"`) to find where each section's Brief Lives sub-block starts. The narrative "Historical Background + Royal Family + End of the [section]" prose is NOT transcribed — only the Brief Lives sub-block (lettered roles, alphabetical, 30–80-word prose per entry).
- On chunks 1 and 2, the Brief Lives sub-block sat at the END of each section's page range. Expect the same for Ramesside.
- **Re-verify the physical-to-printed page offset at the first and last printed pages of each sub-block.** Chunk 2 saw a +11 → +12 drift mid-chunk due to a two-page chart spread. Ramesside may have similar.
- Extract a `raw/source-p<start>-p<end>.pdf` per sub-block (three sub-PDFs if the three sub-sections have separate Brief Lives blocks; one sub-PDF if they share). Use the same `pypdf` one-shot as in chunk 2's `transcribe.md`.

### 2. Write `prompt-ramesside.md`

Copy `prompt-amarna.md` and adjust:

- Input path: `raw/chunk-p<start>-p<end>.md` — update to the new chunk range.
- Output path: `agent-{a|b|c}-ramesside.jsonl`.
- `sub_period` — enumerate the three D&H sub-section titles verbatim. A Brief Lives entry belongs to exactly one sub-section; the OCR must preserve the sub-section heading so agents can attribute correctly. If D&H groups all three sub-sections' Brief Lives into one alphabetical run at the end of printed p. 194 (mirroring the Pre-Amarna layout), the three sub-sections collapse into one alphabetical block and every row's `sub_period` reflects its dynastic placement. If D&H gives each sub-section its own Brief Lives sub-block mid-chapter, preserve the tri-partite structure.
- Role codes — Ramesside era has some codes chunks 1 and 2 did not exercise. Examples to watch (not exhaustive — enumerate from the actual PDF): `LuWA` (Lady of the Two Lands), `CPR` (Crown Prince, possibly), `KD` vs `KDB` distinction may matter, `PA` (Prophet of Amun) variants, military titles (`Genmo`, `Captain of the Troops`, `OMC`). Preserve codes verbatim; Phase A owns the glossary.
- Parsing hazards — specifically list:
  - Ramesses II's many wives (Nefertari, Isetnofret, Bintanath, Meryetamun, Nebettawy, Henutmire, plus the three Hittite princesses) — each is a separate row; D&H flags some as possibly-identical (e.g. Meryetamun vs Meryetamun D). Do NOT conflate.
  - Disambiguator letters get used heavily — `Ramesses` alone has a dozen Brief Lives entries across Dyn 19/20 (some are kings, some are king's sons). Each gets a letter suffix.
  - Tausret's role as regent/king. She is a Brief Lives entry; she is also in pharaoh.se; this row is the D&H-authorial view of her as queen-became-king.
  - Bay / Irsu — included or not per D&H's authorship call. Follow the PDF.
- Row-count expectation: ~60–80. If the three sub-sections each have their own Brief Lives block, the total adds up; if one consolidated block, read the block count.
- **Slash-shorthand guidance** — the corrected version of the `alt_names` and lacuna-group rules from the post-Copilot `prompt-amarna.md`. Do NOT revert these.

### 3. Re-attempt Claude Opus 4.6 OCR per ADR-017 amendment

Try a general-purpose subagent first. If it refuses (chunk 1 pattern), re-attempt main-session Opus 4.6 (chunk 2 pattern, worked for the Amarna 4 pages). Only if BOTH refuse, fall back to Gemini 3.1 Pro with the prompt at `transcribe-gemini-prompt.md` — the amendment requires the re-attempt, not just re-use of the fallback.

Document whichever path worked in `transcribe.md` § "Model deviation" for chunk 3. Do NOT edit chunks 1 or 2's deviation notes.

### 4. Spawn 3 extraction subagents in parallel

Same pattern as chunk 2. Each reads `prompt-ramesside.md` + `chunk-p<start>-p<end>.md` and writes `agent-{a|b|c}-ramesside.jsonl`. Rate-limit note: PR #38's first run hit the 3pm-PT limit right at agent-completion; if this happens again, the agent files are on disk even if the subagent's "report" response gets truncated. Check the files before respawning.

**Before spawning:** copy `.bak` versions of chunks 1 and 2's `agent-*-*.jsonl` files. Multi-chunk re-extraction risk is real; you want the ability to revert if anything corrupts.

### 5. Adapt `merge.py` — likely zero changes needed

`merge.py` already globs `agent-{tag}-*.jsonl`; adding a third chunk is zero code change. Cross-chunk `dh_id` collisions will raise loudly — D&H's disambiguator letters make cross-chunk homonyms impossible within one source, so a collision is an extraction bug not a legitimate homonym.

**Recommended one-time cleanups for this chunk's PR (deferred from PR #38 per code-reviewer scope):**

- Rename Pre-Amarna raw files `agent-{a,b,c}.jsonl` → `agent-{a,b,c}-power.jsonl`. Drop the base-unsuffixed-filename branch in `_load_agent_chunks`. The rename is a no-op because the files live under `raw/` (gitignored) — re-extract Pre-Amarna from existing OCR if needed, or just rename on disk.
- Split `SPOT_CORRECTIONS` into per-chunk lists (`POWER_CORRECTIONS`, `AMARNA_CORRECTIONS`, `RAMESSIDE_CORRECTIONS`) concatenated into the top-level list. Readability win, zero behavior change.
- Drop `SUB_PERIOD = SUB_PERIOD_POWER` / `CITATION = CITATION_POWER` compat aliases in the test file; inline-replace in the 12 Pre-Amarna test fixtures.

### 6. Run `fix_rows.py` — expect ~5–10 new entries

Chunk 3 corrections will be a mix of:
- **Expected drift categories** (same as chunks 1 and 2): verbatim-prose hedge loss, allcaps-vs-titlecase on regnal alt_names, occasional cross-reference in `alt_names` instead of `notes`.
- **Chunk-3-specific drift** unpredictable from the chunk-1 and chunk-2 experience. The Ramesside era has heavier naming overlap (many Ramesses princes named for their grandfathers) and more contested identities — expect Mutnodjmet-A-vs-Q-style hedging on several pairs.

The main-agent review pass (cross-check reconciled.jsonl against the OCR chunk yourself) + egyptologist-reviewer subagent pass will surface the corrections.

### 7. Write tests

Every new row gets a rule-5 full-row fixture. Update invariants:

- `test_row_count` → 100 + N (where N is chunk-3 row count).
- `test_row_counts_per_chunk` → add the new sub_period key(s) and value(s).
- `test_every_row_has_complete_citation` citations dict gets new entries.
- `test_role_code_set_spans_the_known_codes` — add any new chunk-3 role codes asserted-present.
- `test_lacuna_prefixed_ids_sort_last_within_each_bin` — update expected counts. Verify chunk 3 introduces zero new lacuna entries (if it does, adjust).

Use the generator script approach: a one-shot Python script that reads `reconciled.jsonl`, filters for the new `sub_period`, and emits test function bodies. See PR #38 commit `8446a61` for the generator pattern; delete the generator before committing.

### 8. Update docs

- `README.md` — extend the scope table with chunk 3; update `sub_period` field-semantics to list all three Dyn-19/20 sub-section titles.
- `transcribe.md` — add chunk 3 scope, page offset re-verification, OCR method used.
- `docs/mvp-tasks.md` — strike through the Dodson-Hilton "House of Ramesses" bullet and add row count + PR number.
- `docs/handoff-dodson-hilton-next-chunk.md` (this file) — update to point at the earlier-chapters chunk as the next target, or delete if all chunks are complete.

### 9. PR, reviewers, CI

Standard Phase 0 workflow per `CLAUDE.md` § "Pull request workflow":
1. Push branch, open PR, request Copilot review via API.
2. Spawn `code-reviewer` and `egyptologist-reviewer` subagents in parallel.
3. Invoke `scope-accountability-enforcer` before replying to any review batch; prefix replies with `SCOPE_CHECKED=1`.
4. Poll `gh pr checks <N> --watch` until green.

### 10. After merge: log human review

Repeat the PR #38 pattern. Walk ~5–10 Ramesside rows with the user against the PDF, log in `pipeline/pipeline/authority/sources/dodson-hilton-queens/human-review-<YYYY-MM-DD>-ramesside.md`. Mark remaining un-sampled rows as provisional at chunk level. Do NOT alter chunks 1 or 2's existing human-review files.

---

## Known traps (learned on chunks 1 and 2)

1. **Do NOT re-run the 3-agent extraction after a prompt fix.** Re-running loses quality on fields the prompt never targeted. Use `fix_rows.py` for surgical corrections instead. See the playbook's "Do NOT re-run the 3-agent extraction after a prompt fix" section for the concrete PR #38 regression.
2. **Scan-order anomalies shift the physical-to-printed offset mid-chunk.** Verify at both ends of the chunk; document the drift path in `transcribe.md`.
3. **Copilot catches sort-key bugs when the chunk introduces the first rows in a new prefix class.** Chunk 3 is likely to exercise the existing lacuna bin (if Ramesside has lacuna entries) but may also introduce entries that sort strangely under case-insensitive alphabetical. If names contain accented characters (`é`, `ā`) or Greek letters, check the sort ordering empirically.
4. **Agent JSONL files stay under `raw/` and are gitignored.** Stage explicitly by filename when committing; never `git add -A`. The `code-reviewer` subagent writes local memory under `.claude/agent-memory/` that must NOT be staged.
5. **The pre-push hook requires `TASK_LIST_UPDATED=1`** when `docs/mvp-tasks.md` is in the commit. Prefix with it or the hook blocks.
6. **`gh pr create` may hit TLS sandbox errors.** Retry with `dangerouslyDisableSandbox: true` on that specific call — sandbox-restricted networking blocks GitHub's GraphQL endpoint in some configurations. Do not swap to other tools.

---

## Non-goals for this chunk

- Do NOT pick up the Phase A authority-curation work — Phase 0 must be complete first (Porter-Moss I and III, Baud 1999 OK, and the earlier Dodson-Hilton chapters are the last hard blockers).
- Do NOT re-open the parent→child denormalization question. It's deferred to Phase A and the decision must be made consistently across all Phase 0 sources; making it per-source creates drift.
- Do NOT re-run chunks 1 or 2's extraction subagents. Their `reconciled.jsonl` values are committed; chunk-level diffs from an unnecessary re-run will pollute this PR.
- Do NOT start on the earlier-chapters chunk in the same PR. One chunk per PR keeps review surface-area tractable.

---

## Memory pointers

- Project-level memory: `/Users/philipp/.claude/projects/-Users-philipp-code-hapi/memory/project_current_pr_state.md` has the authoritative list of what's landed vs pending.
- User feedback rules: `feedback_autonomy.md`, `feedback_branch_pr.md`, `feedback_push_after_commit.md`, `feedback_pr_review_replies.md`, `feedback_ci_failures.md`, `feedback_copilot_review.md`, `feedback_pr_reviewers.md` — read all of them before starting. They reflect specific patterns the user has corrected in prior sessions.
- Constitutional rules: `CLAUDE.md` rules 1–12 are non-negotiable. Especially rule 1 (scholarly traceability), rule 5 (tests assert values), rule 6 (raw data sacred), rule 12 (existing violations don't justify new ones).

Good luck. The pattern is well-established now; chunk 3 should be a clean ~half-day pass if the source PDF is readable and the OCR doesn't refuse.
