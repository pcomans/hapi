# Code Review Sweep — 2026-04-23

## P1

- `reconciled.jsonl:29`, `reconciled.jsonl:30`, `reconciled.jsonl:57` still over-assert `roles: ["king's eldest son of his body"]` without the later enforced title evidence. The source’s own correction rule, documented repeatedly in `fix_rows.py` and prompts, requires BOTH `smsw` and `nj ẖt.f` in the same title string for this role. `baud-29` and `baud-30` have only `zꜣ nswt smsw`; `baud-57` has `zꜣ nswt nj ẖt.f mrjj.f` and `zꜣ nswt smsw` as separate titles. This is the same systemic over-claim fixed for many chunk-2/4/5/7 rows, but these rows were missed. It violates Rule 1 by promoting a role beyond the cited titulary, and Rule 3 because no deterministic invariant catches the pattern across all rows.

## P2

- `pipeline/tests/test_sources_baud_ok_royal_family.py:498` is the last full populated-row fixture, and it only covers chunk 2 (`baud-68`). Chunks 3-7 have documented sampled/flagship rows in `human-review-2026-04-18-chunk3.md` through `chunk7.md` (`baud-83`, `baud-144`, `baud-162`, `baud-230`, `baud-282`, plus sampled subentries), but those rows are not value-pinned field-by-field in tests. Later tests only check broad invariants and a few chunk-1/2 regressions. This falls short of Rule 5 for the merged seven-chunk source: high-risk corrections in chunks 3-7 can drift while row count, citation shape, and role vocabulary tests still pass.

- `pipeline/tests/test_sources_baud_ok_royal_family.py:215` bounds role vocabulary but does not enforce role-to-title derivation. The current `king's eldest son of his body` leak above demonstrates the gap: the vocabulary test accepts the role string even when `titles_from_baud` lacks the required supporting title. Add deterministic assertions for recurring derived roles, at minimum the eldest-son conjunction rule and the negative female `zꜣt nswt ... smst` cases that drove chunk-5 corrections. This is Rule 3 coverage, not just a value fixture.

## P3

- `README.md:31` still describes chunks 3-7 as `future`, and `README.md:99` says the reviewer walked only the chunk-1 extract. The directory now contains prompts, human-review files, corrections, and reconciled rows for all seven chunks. The stale provenance summary is easy to misread during future audits and weakens Rule 1 traceability even though row-level citations are present.

- `README.md:67` still defines `baud_id` as `baud-<N>` only, while `merge.py:13` and the committed rows support letter suffixes such as `baud-60a`, `baud-94b`, and `baud-206a`. This is a schema-doc drift issue rather than an immediate data failure, but it should be corrected so new prompts/tests do not copy the older integer-only rule.
