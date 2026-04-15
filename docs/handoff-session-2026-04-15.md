# Session-end handoff — 2026-04-15

Written at the close of a long working session that landed three PRs:

- **PR #37** — Dodson-Hilton "Power and the Glory" Brief Lives (Pre-Amarna, 59 rows). *Merged earlier in the day by a previous session.*
- **PR #38** — Dodson-Hilton "The Amarna Interlude" Brief Lives (41 rows; 100 combined). First human Egyptologist sign-off on any Dodson-Hilton chunk (six of seven sampled rows validated, one deferred source-wide).
- **PR #39** — Docs: multi-chunk source pattern formalised in the playbook, Monitor pattern for Copilot re-review polling documented in CLAUDE.md, and a targeted handoff for whoever picks up Dodson-Hilton chunk 3 (Ramesside).

Main is clean, 457 tests pass, CI green at merge time. This doc summarises what a fresh session should know before starting the next piece of work.

## Recommended next task — pick one

In rough priority order. The first three are all reasonable; pick based on the user's stated interest or review-cycle capacity.

### A. Dodson-Hilton chunk 3 — Ramesside Brief Lives

Most direct continuation. Everything is primed:
- Targeted step-by-step plan: `docs/handoff-dodson-hilton-next-chunk.md`.
- Multi-chunk `merge.py` already globs `agent-{tag}-*.jsonl` — zero code change needed.
- Prompt-template pattern: copy `prompt-amarna.md` → `prompt-ramesside.md`.
- Expected ~60–80 rows across three D&H sub-sections (House of Ramesses, Feud of the Ramessides, Decline of the Ramessides), printed pp. 158–194.
- Egyptologist-reviewer audit on PR #39 flagged specific parsing hazards for this chunk (Ramesses letter-run 15–20 entries, two Hittite princesses not three, Dyn 20 contested queens — Tyti, Takhat, Iset Ta-Hemdjert, Duatentopet); these are pre-captured in the handoff doc.
- Recommended human-review sample size for this chunk: 10–15 rows (not the Amarna-precedent 5–10) given the disambiguation density.

### B. Baud 1999 OK royal family — new Phase 0 source

The OK analogue of Dodson-Hilton. PDF is at `proprietary/books/Baud 1999 - Famille royale AE vol 1.pdf` + vol 2. This is a larger undertaking than D-H chunk 3 (French-language source, larger scope) and is a hard blocker for Phase A authority curation. If the user wants to widen Phase 0 coverage before returning to D-H, this is the next highest-value source.

Use the updated Phase 0 playbook (`docs/playbook-phase-0-ocr-transcription.md`) — it now covers multi-chunk source patterns, the ADR-017 amendment on Gemini fallback, main-session OCR as a sanctioned exception, the Monitor pattern for Copilot polling, and the Step 12 human-review protocol.

### C. Human review of PR #37 Pre-Amarna rows

Six of seven Amarna rows have been human-signed-off (see `pipeline/pipeline/authority/sources/dodson-hilton-queens/human-review-2026-04-15.md`). All 59 Pre-Amarna rows and the remaining 34 Amarna rows are still provisional. A focused sign-off pass (~5–10 Pre-Amarna rows sampled against the PDF) would de-provisionalise a big block of the extract at low cost. This is the cheapest-to-complete item and adds confidence to downstream Phase A work.

Format: log as `pipeline/pipeline/authority/sources/dodson-hilton-queens/human-review-2026-04-15-power.md` (chunk-suffixed per the Step 12 convention just formalised).

### D. Phase A authority curation — NOT yet

Phase A (`rulers.json`, `sites.json`, `dynasties.json`, `periods.json`) is blocked until Phase 0 is complete. Hard blockers remaining: Porter-Moss I + III (sites), Baud 1999 (OK rulers), at minimum. Do NOT start Phase A in a fresh session unless the user explicitly directs it.

## Session-specific context the next agent should know

1. **Rate limits.** This session hit the 3pm-PT Anthropic rate limit reset mid-work (around the first 3-agent extraction run on PR #38). If you spawn 3 parallel subagents during peak hours, have a `.bak` backup of current agent JSONLs so a partial-completion doesn't corrupt state. The Monitor pattern helps here — you get a completion notification even if the subagent-report message is truncated.

2. **Opus 4.6 main-session OCR worked on D-H chunk 2.** Do NOT default to Gemini for Dodson-Hilton chunks. Per ADR-017 amendment each chunk must re-attempt tier-1 (subagent Opus) + tier-2 (main-session Opus) before escalating to Gemini.

3. **The re-run experiment on PR #38.** We attempted re-running the 3-agent extraction after Copilot flagged two prompt contradictions. Result: cleaner on the prompt-fix-targeted cases but LOST quality on 8 other rows (dropped D&H hedges, dropped cross-entry inferences, "perhaps"→"possibly" drift). Reverted. **Do NOT re-run the 3-agent extraction after a prompt fix — use fix_rows.py for surgical corrections instead.** Captured in the playbook § "Do NOT re-run the 3-agent extraction after a prompt fix" and the chunk-3 handoff.

4. **The Monitor pattern is now the documented Copilot-poll mechanism.** After every push, arm a Monitor watching for Copilot's review of the new HEAD commit. Don't sit idle. CLAUDE.md § "Pull request workflow" step 2 has the exact invocation; `feedback_copilot_review.md` in the per-project memory has it too.

5. **Deferred architectural question on `children_names` denormalization.** User leans toward child→parent only (no parent.children_names duplication). Deferred to Phase A where it must be decided source-wide. Do NOT re-open per-chunk. See `human-review-2026-04-15.md` § "Q5 detail" for the options.

## Pointers

- **Authoritative project instructions:** `CLAUDE.md` (constitutional rules, PR workflow with Monitor pattern, verification commands).
- **Phase 0 playbook:** `docs/playbook-phase-0-ocr-transcription.md` (multi-chunk pattern, OCR decision tree, Step 12 human review, `.claude/agent-memory/` warning).
- **D-H chunk-3 handoff:** `docs/handoff-dodson-hilton-next-chunk.md` (step-by-step for Ramesside).
- **D-H human-review log:** `pipeline/pipeline/authority/sources/dodson-hilton-queens/human-review-2026-04-15.md`.
- **MVP task list:** `docs/mvp-tasks.md` (source-level status + ✅ / 🔜 markers).
- **Memory:** in a Claude Code session, the per-project memory is auto-loaded; `project_current_pr_state.md` has the latest state; `feedback_*.md` files capture prior user corrections.
- **User feedback files to re-read before starting:** `feedback_autonomy.md`, `feedback_branch_pr.md`, `feedback_push_after_commit.md`, `feedback_pr_review_replies.md`, `feedback_ci_failures.md`, `feedback_copilot_review.md`, `feedback_pr_reviewers.md`, `feedback_dagster_only.md`.

## Open loose ends (not blocking)

- `.claude/agent-memory/code-reviewer/` shows up as untracked after reviewer subagents run. Probably wants a global gitignore entry under `.claude/` rather than the per-PR workaround of stage-explicitly-by-filename. Separate hygiene task, not blocking.
- The code-reviewer on PR #38 suggested three chunk-3 cleanups: rename Pre-Amarna raw files to `agent-{a,b,c}-power.jsonl`, drop the base-unsuffixed-filename branch in `merge.py`, drop the `SUB_PERIOD` / `CITATION` compat aliases in the test file. Pick these up when you start the chunk-3 PR.

Good luck. The playbook is fuller now than it was this morning; the next chunk should flow smoothly.
