# Code Review — `dodson-hilton-queens` (retrospective sweep, 2026-04-24)

Source reviewed by `code-reviewer` subagent as part of the Phase-0 sweep
audit (see `docs/handoff-sweep-audit-2026.md`). The source was merged in
prior PRs without running a code-reviewer subagent during the cycle
(policy from `feedback_pr_reviewers.md` was memory-only, not enforced by
a hook — fixed in session-2026-04-23).

Note on provenance: the subagent returned findings inline (its
system-reminder forbade writing `.md` analysis files); the coordinator
persisted the text to this file verbatim per the sweep-doc deliverable
spec.

Cross-referenced against `reviewer-notes-ramesside.md` so findings don't
duplicate items already resolved there.

## P1 — blocking

**P1-1. `prompt-ramesside.md` leaks per-row answers (rule 1/7; same pattern as `feedback_phase0_prompt_field_rules`).** Lines 111–121 enumerate per-individual expected values under `Dyn 20 contested queens`, e.g. `Tyti (KD; KSis; KW; KM; GW) — D&H places her as possible wife of Ramesses X, NOT Ramesses III`, `Takhat A (Dyn 19... wife of Sety II, mother of Amenmesse, daughter of Ramesses II)`, `Iset D Ta-Hemdjert (principal wife of Ramesses III, mother of RAMESSES VI)`, `(Dua)tentopet... wife of RAMESSES IV, in QV74`, `Nubkhesbed (KGW) wife of RAMESSES VI, mother of Iset E`, `Henttawy Q (KD; KW; KM)`. These are answer tables, not rules — the 3-subagent vote is theatre for these rows. Retrospective fix: rewrite as detection rules (how to recognise a KGW code cluster, how to spot a compound-name epithet) and drop the per-tomb-ID value enumerations. The merge-disagreements.txt I spot-checked shows zero disagreement on `Tyti`, `Iset D Ta-Hemdjert`, `(Dua)tentopet` — consistent with leakage, not independent convergence.

**P1-2. `fix_rows.py POWER_CORRECTIONS[Tiaa A]` lacks per-entry verifier attribution.** The rationale asserts `"The PDF (p. 140 col 2, Tiaa A entry) reads with the article"` without naming who verified against the printed PDF vs the Gemini text layer, and without a PR# or date. This matches the `feedback_fix_rows_unattributed_restoration` pattern: if the text-layer OCR drops `a`, the restoration is inserting a character the raw layer doesn't show. Module docstring says "egyptologist-reviewer subagent flagged" but that's source-level, not per-correction. Fix: add the subagent-pass PR# / date inline, or back off to the Gemini OCR form.

## P2 — significant

**P2-1. Rule 5 subset violation risk on the test file's scope.** `test_sources_dodson_hilton_queens.py` is 8728 lines with hundreds of `_assert_full_row` calls — good. But a row-count audit against the 465 reconciled rows is needed to confirm every row has a full-row test. The file has explicit per-row tests for Power / Amarna / Ramesside / Head of South / Seizers / Kings and Commoners / Founders full-row cases, but I cannot confirm coverage is 465/465 without a structural test that iterates over `_rows()` and asserts "a `_assert_full_row` fixture exists for this dh_id". Add a `test_every_row_has_a_full_row_fixture` meta-test that introspects the module and fails if any `(dh_id, sub_period)` in reconciled.jsonl isn't covered.

**P2-2. `reviewer-notes-ramesside.md` flag #3 (Hattusilis III spouse_names cross-entry inference) was silently resolved with README update, no explicit sign-off marker.** The README § Schema now describes the generalised symmetric-kinship rule, but the file itself is unchanged from the "worth documenting explicitly" state. Add a one-line resolution stamp to the notes file matching the flag-#1/#2 pattern, or delete the flag.

**P2-3. Sort-order invariant relies on `unplaced` being an input; `_sort_key_for` computes it pre-merge via majority vote (merge.py:219–224).** If all three agents disagree on `unplaced` for a given composite key (1 vote each, with one being the baseline False), the majority rule picks False. This is silently-correct today because `unplaced` is section-boundary-determined and hard to miscategorise, but no test asserts that all three agents agree on `unplaced` for every row. Add an assertion in `_sort_key_for`'s caller, or a test that walks merge-disagreements.txt and fails if `unplaced` ever appears as a disagreement field.

**P2-4. Multi-chunk ALL_CORRECTIONS aggregation not tested.** `fix_rows.py` concatenates POWER_CORRECTIONS + AMARNA_CORRECTIONS + RAMESSIDE_CORRECTIONS + FOUNDERS_CORRECTIONS + SEIZERS_CORRECTIONS into SPOT_CORRECTIONS. There's no test asserting that (a) every correction's target row actually exists in reconciled.jsonl, (b) every correction's `field` is a valid schema field, (c) re-running fix_rows.py is idempotent (the `if old_val == new_val: continue` guard in main() claims idempotence but it's never tested). Add a `test_fix_rows_corrections_are_applicable` that loads SPOT_CORRECTIONS and checks key existence + field validity without mutating state.

## P3 — minor

**P3-1. Ch 5 status untracked.** Task description says "Ch 5 pending" but README § Scope and tests/test_sources_dodson_hilton_queens.py contain no `xfail`, no skip, no TODO. `test_row_count` hard-codes 465 and `test_row_counts_per_chunk` enumerates the 9 `sub_period`s as a closed set. Future Ch 5 / Ch 4 work will need to touch both. Add a module-level comment in the README or test file naming the remaining chapters with their expected chunk names (`Tempering Steel`, etc.) and row-count placeholders. This is housekeeping, not a bug.

**P3-2. `merge.py:209` uses `sys.exit()` on empty-agent case instead of raising.** This violates rule 2 in spirit — it's a silent-ish failure path that doesn't surface a traceback. Replace with `raise RuntimeError(...)`.

**P3-3. Cross-section-duplicate enumeration is hardcoded in two places.** `merge.py:232` derives `duplicated_dh_ids` from Counter over live data, but `test_sources_dodson_hilton_queens.py:192` hardcodes `CROSS_SECTION_DUPLICATE_IDS = {Takhat A, Isetneferet C, Ramesses C, Hetepti}`. Single source of truth: have the test read the live-derived set and assert membership, not redefine.

**P3-4. No rule-12 grandfather violations spotted.** README § Schema acknowledges Ramesside-introduced composite-key phenomena but frames them as genuine D&H-authorial features, not excuses. Good.

## Files referenced

- `pipeline/pipeline/authority/sources/dodson-hilton-queens/README.md`
- `pipeline/pipeline/authority/sources/dodson-hilton-queens/merge.py`
- `pipeline/pipeline/authority/sources/dodson-hilton-queens/fix_rows.py`
- `pipeline/pipeline/authority/sources/dodson-hilton-queens/prompt-ramesside.md`
- `pipeline/pipeline/authority/sources/dodson-hilton-queens/reviewer-notes-ramesside.md`
- `pipeline/pipeline/authority/sources/dodson-hilton-queens/transcribe.md`
- `pipeline/tests/test_sources_dodson_hilton_queens.py`
