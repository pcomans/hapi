# Code Review Sweep 2026 — Leprohon 2013 Titulary

## P1

- `stage_suffix` is knowingly overloaded for queen-consort rows, and the test suite locks in the overload instead of forcing a schema fix. `README.md:123` defines `stage_suffix` as same-king titulary stages, then documents that chunk 14 also uses it for distinct queen-consorts and tells consumers to treat one field as two meanings until a future PR. `transcribe.md:113` repeats that this was a P1 deferred item, and `pipeline/tests/test_sources_leprohon_titulary.py:1438` asserts the overloaded `"a"` values for Arsinoe II / Berenike II / Cleopatra I / Cleopatra II. This violates Rule 12 and creates a real downstream ambiguity: a Phase-A consumer cannot determine from structured fields whether `leprohon-33.05a` is Cleopatra I as a distinct person or a stage of Ptolemy V. Fix by adding a structured discriminator (`row_type`, `consort_of`, or equivalent) now, migrating these rows/tests, and reserving `stage_suffix` for actual same-person stages.

## P2

- `merge.py` accepts rows found by only one of the three extraction agents. In `merge.py:235-243`, when `len(present) < 2`, the code appends the singleton row to `reconciled.jsonl` and merely records `"kept it"` in `merge-disagreements.txt`. For an authoritative fact source, a 1/3 row is exactly the kind of extraction drift Rule 2 should make loud, not a fact to preserve. This can admit hallucinated or mis-scoped rows if one agent invents an entry and the other two omit it. The merge should raise for singleton rows unless an explicit reviewed override list names the row, and tests should cover this behavior with synthetic agent files.

- Known row-level absence notes are still committed in per-name `source_note` fields for Late Period rows. `fix_rows.py:824-838` correctly explains that `"Two Ladies and Golden Horus names: none known"` is row-level absence metadata and not a name-entry source note, but then explicitly leaves the identical pattern in `leprohon-27.02` and `leprohon-29.02` as follow-up work. The committed data still has those strings in `reconciled.jsonl:354` and `reconciled.jsonl:362`. This is a Rule 12 issue and a Rule 3 gap: chunk 14 got spot corrections, but there is no global invariant forbidding row-level absence prose in `source_note`. Add deterministic cleanup or a schema field for row notes, and add a test that rejects these absence phrases in all name-entry `source_note` values.

## P3

- `fix_rows.py` uses `assert` for correction-path validation in `_set_by_path` (`fix_rows.py:929-956`). These are intended as loud correction failures, but Python can strip assertions under `-O`, turning validation into weaker runtime behavior. Replace with explicit `TypeError` / `KeyError` / `IndexError` raises so correction application remains loud regardless of interpreter flags.
