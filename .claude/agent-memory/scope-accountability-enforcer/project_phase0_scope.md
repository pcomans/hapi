---
name: Phase-0 extraction chunk PR scope boundaries
description: What is in-scope vs legitimately deferrable when auditing a Phase-0 source chunk PR (Leprohon, Dodson-Hilton, etc.)
type: project
---

Phase-0 chunk PRs (e.g., Leprohon chunk N, Dodson-Hilton chunk N) have a well-defined scope envelope.

**In-scope (must be fixed in the chunk PR):**
- Prompt answer-leaks in the chunk's own `prompt-*.md` (violates rule 1 + `feedback_phase0_prompt_no_answers.md`)
- Unattributed `fix_rows` / `*_CORRECTIONS` overrides introduced by this chunk (violates rule 1 — every authoritative fact needs a traced source)
- Chunk-local data errors surfaced by egyptologist-reviewer against the PDF
- Any new entries the chunk would add to a cross-cutting exception list (e.g., title-case exceptions) — if the chunk causes growth, that growth is a chunk-local bug
- The chunk's own test fixtures and mappers

**Legitimately deferrable (structural / cross-cutting, not caused by this chunk):**
- Redesigning cross-chunk invariant tests that have accreted exceptions across many prior chunks (e.g., `test_headword_display_names_are_title_cased` anchoring to pypdf source instead of casing heuristic). Only legitimate if this chunk does not add new exceptions.
- Rewriting the 3-agent extraction protocol itself
- Moving authority data between sources

**Why:** Phase-0 chunks are bite-sized units of scholarly extraction; bundling a test-architecture refactor into every chunk PR would be unreviewable. But the bar for deferral is that the chunk did not cause or grow the problem.

**How to apply:** When a main agent defers a test/architecture finding, verify (a) the chunk is not the cause of growth, and (b) a concrete follow-up artifact is recorded (mvp-tasks entry or issue), not just "we'll get to it."
