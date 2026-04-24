# Code Review — `baud-1999-ok-royal-family` (retrospective sweep, 2026-04-24)

Source reviewed by `code-reviewer` subagent as part of the Phase-0 sweep audit
(see `docs/handoff-sweep-audit-2026.md`). The source was merged in a prior PR
without running a code-reviewer subagent during the cycle (policy from
`feedback_pr_reviewers.md` was memory-only, not enforced by a hook — fixed in
session-2026-04-23).

Note on provenance: the subagent returned findings inline (its own
system-reminder forbade writing `.md` analysis files); the coordinator persisted
the text to this file verbatim per the sweep-doc deliverable spec.

## P1 — must-fix

**Rule 5 violation: `test_roles_vocabulary_is_bounded` is the only enforcement of the most heavily-corrected field in the source.** The `fix_rows.py` corrections lists are dominated by `roles` fixes — every chunk has systemic `roles` over/under-extraction. Yet apart from ~10 hand-pinned regression rows (`baud-10/20/25/28/34/36/40/42/43/57/62/64/68`), the *other ~270 rows* have no assertion on their `roles` list. Every populated field on every row needs a pinned value (constitutional rule 5), and `roles` is precisely the field where extraction drift has been caught repeatedly. A `ROLES_PER_ROW = {baud_id: [...]}` dict covering all 289 rows, diffed against reconciled.jsonl, is the rule-3 enforcement. Same structural gap applies to `titles_from_baud`, `name_egyptian`, `date_attested`, `spouse_names`, `children_names`, `father_name`, `mother_name`, `notes_from_baud` — only the two flagship rows (`baud-3`, `baud-37`, `baud-68`) pin all fields. This is "themed-subset testing" that rule 5 explicitly forbids.

**Rule 3 violation: the "smsw + nj ẖt.f in same title string" invariant is enforced by after-the-fact `CHUNK*_CORRECTIONS` rationale text, not a test.** `fix_rows.py` has 20+ corrections applying this rule across chunks 2/3/4/5/7. A function `_row_claims_eldest_son_without_smsw_conjunction(row) → bool` run over every row as a test would mechanically catch the next offender. Currently the rule exists only as repeated prose in rationale strings — this is textbook rule-3 violation ("rule that exists only in markdown is a suggestion"). Same applies to the "female zꜣt nswt → never `king's eldest son of his body`" rule (chunk-5 rationale, 4+ occurrences).

**Rule 3 violation: fallback-codepoint ban is tested on `name_egyptian` and `titles_from_baud` only.** `_TRANSLIT_NORMALIZE` runs recursively over every string field; a reviewer correction whose `new_value` slipped a raw `ˁ` / `ɛ` / `ɜ` into `notes_from_baud` / `monument` / `mother_name` would pass CI. The test should walk every string leaf recursively, not two named fields. (Checked the current file — no leaks today, but the guard is partial.)

**Rule 12 violation: chunk-1 provisional-vocab grandfather.** `CHUNK1_BACKFILL` and the README "Known gaps" section explicitly say chunk-1 rows were left with empty `roles` pending later vocab expansion. The rows landed that way and were only retroactively backfilled in PR #57. This is the "chunks 1–5 did X, chunks 6+ do Z" shape — the chunk-1 PR accepted an incomplete mapping because the vocab wasn't ready. The honest rule-12 compliant path would have been to extend the vocab *in the chunk-1 PR* once `jmj-r prw msw nswt` was encountered. Flag for the Phase-A postmortem; don't retrofit.

## P2 — should-fix

**`fix_rows.py` `CHUNK2_CORRECTIONS` `baud-66` restores `(?)` based on a reviewer rationale that does not name a specific reviewer-notes file line.** The rationale says "the literal question mark is Baud's own hedge" but doesn't cite which reviewer pass or notes file committed the observation. Per the `fix_rows_unattributed_restoration` policy, rationale must name a reviewer-notes file line. Same pattern in `baud-76` (`(?)` spouse) and chunk-3 `baud-94`. Corrections that paraphrase Baud directly from the PDF without reviewer-notes backing read as "the agent decided" rather than "the reviewer pass flagged."

**Rule 2 concern: `merge.py` `_majority` silently picks the first-occurring value on a 1/1/1 three-way disagreement** (`most_common(1)[0]` returns arbitrary winner). No loud-fail on "no majority"; `merge-disagreements.txt` logs it but CI doesn't gate on unresolved three-way splits. A three-way disagreement on a load-bearing field (e.g. `dynasty`) is a rule-2 "prefer loud failure" candidate — at minimum a test asserting `merge-disagreements.txt` contains zero three-way splits on the locked fields.

**Rule 1 spot-check — mostly clean, one borderline case.** Spot-checked baud-1, baud-20, baud-98, baud-101a, baud-164, baud-205. Every row's `source_citation` resolves to Baud's own corpus-entry bracket number + a chunk pdf-page range. `notes_from_baud` fragments on baud-164, baud-205 are short (≤ 2 sentences, rights-policy compliant). One borderline: **baud-102 `notes_from_baud` contains the substring `"Note: smsw absent, pas de king's eldest son."`** — that is reviewer commentary, not Baud's prose. It traces to a `roles` judgment, not an attested fact in the source. Move the reviewer note to `fix_rows.py` rationale (or a sibling audit field); don't embed it in the `notes_from_baud` string that claims to be Baud-sourced.

## P3 — nits

- `test_all_corrections_includes_every_chunk_list` aggregates via object-identity (`lst in aggregator`). Safe today but brittle — rewriting a list via list-comp would pass the name-shape check but fail identity. Use name-set comparison.
- `test_tomb_designation_shape_when_populated` asserts only whitespace/non-empty. A regex for the documented shapes (`^G \d+$`, `^D \d+$`, `^LG \d+$`, or freeform) would deliver the rule-5 value-pinning the docstring promises.
- `SPOT_CORRECTIONS = sum(ALL_CORRECTIONS, [])` builds a new list each import; fine, but the `_seen` duplicate-check runs at module import time. Move to `main()` or a test so a broken duplicate doesn't break `from fix_rows import ...` in unrelated tests.

## Relevant paths

- `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/fix_rows.py`
- `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/merge.py`
- `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/reconciled.jsonl` (line 106 for baud-102 embedded-reviewer-note)
- `pipeline/tests/test_sources_baud_ok_royal_family.py`
