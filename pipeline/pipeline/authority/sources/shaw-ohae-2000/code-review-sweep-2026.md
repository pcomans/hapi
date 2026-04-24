# Code Review Sweep - 2026

Retrospective review of `pipeline/pipeline/authority/sources/shaw-ohae-2000/` against `CLAUDE.md` rules 1, 2, 3, 5, and 12. Read `README.md`, `transcribe.md`, `chapter-banners.txt`, `reconciled.jsonl`, and `pipeline/tests/test_sources_shaw_ohae.py`. This source has no `prompt.md`, chunk prompts, `merge.py`, `fix_rows.py`, or prior local reviewer-note/code-review files; multi-chunk `ALL_CORRECTIONS` / `ALL_RENAMES` validation is not applicable.

## Findings

### P2 - Chapter 3 row cites only the banner page, but `sub_periods` facts come from pp. 42-43

`reconciled.jsonl` line 2 records Naqada I/II sub-period date facts, but its only row-level citation is `{"page": 41, ...}`. The source docs explicitly state those sub-period facts are from Midant-Reynes pp. 42-43 (`chapter-banners.txt` lines 40-44; `transcribe.md` lines 21-24; `README.md` lines 56 and 68), while p. 41 is only the chapter banner. The test currently pins this incomplete citation in `test_naqada_period_row_with_subperiods` by asserting `{"page": 41, ...}`.

This violates Rule 1 because the authoritative row contains facts whose cited page does not identify their actual source page. It also weakens downstream auditability: a consumer looking only at `reconciled.jsonl` would be sent to the banner, not the pages containing the Naqada I/II intervals. Fix by carrying field-level citation for `sub_periods` or expanding the row citation schema to include both the banner page and the sub-period pages, then update the test to pin that richer citation.

### P2 - `source_note` imports unsupported sub-period date facts for chapter 10

`reconciled.jsonl` line 9 says the composite chapter covers “Amarna Period (Akhenaten-era, c.1352-1336)” and “Ramesside Period (Dyns 19-20, c.1295-1069).” The same source documentation says those narrower Amarna/Ramesside boundaries are not stated in Shaw's chapter banners or opening paragraphs and require another source (`README.md` line 76). The committed source evidence for chapter 10 only supports the combined banner range `c.1352-1069 bc` (`chapter-banners.txt` lines 120-127).

This is a Rule 1 problem: these dates are authoritative facts inside the authority-layer row, but they are neither Shaw-extracted nor separately cited to HKW or another committed source. The note should either remove the unsupported date ranges and keep only the Shaw-supported composition warning, or split/cite those facts to a separate authority source instead of embedding them in this Shaw extract.

### P3 - Tests do not value-pin every row's populated fields

`pipeline/tests/test_sources_shaw_ohae.py` samples five rows for full value assertions: chapters 2, 3, 5, 12, and 15. The remaining populated rows, including chapters 4, 6, 7, 8, 9, 10, 13, and 14, are only partially covered by row count, chapter set, citation-shape checks, and the source-note presence test. Exact `period_name`, `chapter_title`, date ranges, qualifiers, empty `sub_periods`, pages, and the three `source_note` strings are not value-pinned for those rows.

That falls short of Rule 5 and Rule 3 for this small 13-row authority file: future edits could silently corrupt dates like chapter 7's `-2055/-1650`, chapter 13's `-664/-332`, or the chapter 4/9/10 notes while tests remain green. Add a parameterized expected-row table asserting every populated field for all 13 rows, including absence of `source_note` where applicable and exact note text where retained.
