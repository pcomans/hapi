# Kitchen TIPE Sweep Review — 2026-04-23

## P1

- `README.md:80-82`, `transcribe.md:16`, `transcribe.md:66-73`: the committed authority facts are not traceable to a committed/raw source artifact. The README explicitly says both the PDF and OCR chunk are uncommitted, and `git ls-files` confirms only `.gitkeep` exists under `raw/`. A SHA-256 plus page range helps locate a proprietary scan, but Rule 1 requires authoritative facts to trace to a clear, documented, reproducibly-acquired source on disk. As committed, a reviewer cannot reproduce or audit any row without private local state, and the three agent inputs are also absent. Commit an allowable source artifact, a redacted/table-only transcription, or another reproducible on-disk extraction sufficient to verify each row.

## P2

- `merge.py:155-161`: if only one of three agents emits a `kitchen_id`, the merge keeps that singleton row and merely writes a note to `merge-disagreements.txt`. That is a silent data-admission path for the highest-risk extraction case: no majority and no second witness. Rule 2 wants this to fail loudly, and Rule 3 wants deterministic enforcement rather than convention. The merge should raise on any missing-row disagreement unless a committed, validated override explicitly names the row.

- `pipeline/tests/test_sources_kitchen_tipe.py:38-334`: the tests pin only selected full rows plus broad invariants, leaving many rows’ actual values unasserted. For example, most Dyn. 22, Dyn. 23, Proto-Saite, and Dyn. 26 names, dates, prenomina, lengths, and notes can drift while row count, citation, prefix polity, and empty-concurrency tests still pass. Rule 5 requires value-pinning tests, and this authority source is itself the data product; add an expected map or parametrized full-row assertions for every `kitchen_id` and every populated field.

- `test_sources_kitchen_tipe.py:244-273`: the concurrency regression test imports `fix_rows.py` and recomputes expected values with the same production helper that generated the field. That catches stale JSONL after a helper edit, but it does not independently pin the historically intended concurrency output or catch a bad algorithm change applied consistently to code and data. Keep the recomputation test if useful, but add a literal expected concurrency map for all `20.*`, `21.*`, and `21H.*` rows.

## P3

- `fix_rows.py:77-94`: `_compute_concurrency()` contains defensive `if ti is None` / `if hi is not None` branches even though `interval()` always returns a tuple or raises. These are harmless today, but they encode a silent-skip shape that conflicts with Rule 2 and Rule 12. Remove the unreachable branches so malformed interval data can only raise.

- `merge.py:85-100`: sentinel normalization treats bare `"unknown"` as `None` globally. The comments say bracketed `[Prenomen unknown]` must survive, and current data happens to preserve it, but the rule is field-blind; if an agent emits a literal scholarly `"unknown"` note/name/prenomen, the merge can erase it. Restrict sentinel collapsing to fields where a dash/null placeholder is valid, or require exact source-specific sentinels.
