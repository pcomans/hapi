# Code Review Sweep — 2026

## P2

- `fix_rows.py` no longer preserves the full applied-override audit trail after an idempotent rerun. The main loop skips any correction whose `old_val == new_val` (`fix_rows.py:379-381`), then rewrites the whole `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED` section from only `override_log` (`fix_rows.py:393-410`). In the current committed `merge-disagreements.txt`, that section lists only the later Seizers fixes (`Ameny A`, `Didit`), while the earlier Power / Amarna / Ramesside / Founders corrections that are still encoded in `SPOT_CORRECTIONS` and already present in `reconciled.jsonl` are omitted. This violates Rule 1 traceability as documented in the README/transcribe method: every reviewer-applied correction is supposed to be recorded in the committed disagreement log. Fix by logging every `SPOT_CORRECTIONS` entry with both an `already matched`/`changed` status, or by rebuilding the override section from the correction table rather than from changed rows only.

- `fix_rows.py` applies corrections to arbitrary field names without schema validation. A typo in the correction tuple's `field` value takes `old_val = row.get(field)` (`fix_rows.py:379`) and then writes `row[field] = new_val` (`fix_rows.py:387`), creating a new JSON key instead of failing. The full-row tests currently catch schema drift in committed data, but the correction script itself violates Rule 2/3 by silently accepting malformed correction instructions during the critical post-merge path. Add a `SCHEMA_FIELDS` set and raise if `field not in SCHEMA_FIELDS`; also consider rejecting duplicate `(dh_id, sub_period, field)` correction targets before mutation.

## P3

- The Founders extraction prompt and transform header still say per-row dynasty refinement is deferred to Phase A and every row should emit `dynasty: 1` (`prompt-founders.md:66`; `transform_founders.py` header text). The committed source now intentionally refines four Founders rows to dynasties 2/3 in `FOUNDERS_CORRECTIONS` (`fix_rows.py:257-304`), and the tests assert those refined values. The data and tests are coherent, but the prompt/provenance docs are stale and can mislead anyone reproducing the chunk from the committed workflow. Update those texts to say extraction starts with chunk-default dynasty 1, then `fix_rows.py` deterministically refines rows with explicit on-row dynasty evidence.

- `diff_power.py` reports mismatches but never exits non-zero, unlike the later diff scripts (`diff_ramesside.py`, `diff_kingsandcommoners.py`, `diff_founders.py`). If used as a Step 11.5 gate, a dirty Power transcription diff can scroll by while automation still succeeds, weakening Rule 3 deterministic enforcement. Return a failure status when mismatches, unmatched rows, or missing-in-reconciled entries are present.

## Notes

No P1 data-loss issue found in the committed `reconciled.jsonl`: schema keys are complete, `(dh_id, sub_period)` keys are unique, citations align with chunk ranges, and the dedicated test file has full-row value assertions across the source.
