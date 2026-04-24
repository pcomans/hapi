# Code Review Sweep — Ryholt 1997 SIP

## P1

- `merge.py` accepts no-majority field votes and commits an arbitrary agent-order winner. In `_majority()`, `Counter.most_common(1)` plus the first matching normalized value means a 1/1/1 split is treated as a chosen value instead of a loud failure (`merge.py:89-104`, used at `merge.py:157-160`). This already leaked into the committed data: `merge-disagreements.txt:112-114` shows all three agents disagreed on `15.3` `nomen_transliterated`, and `reconciled.jsonl:99` kept agent A's string with raw markdown emphasis (`s-k-r-ḥ-r* ... *sꜣ-rꜥ`) and without agent B's extra `ḥqꜣ-ḫꜣswt` clause. That violates Rule 1/2/3: a contested authoritative fact with no majority is silently selected rather than forced into an explicit, cited override. Make no-majority fields fail the merge unless listed in a deterministic corrections table, then pin the corrected value in tests.

## P2

- Single-agent rows are kept instead of rejected. If only one extractor emits an ID, `merge.py:149-152` appends that row to `reconciled.jsonl` and merely writes "only 1/3 agents found this entry (kept it)" to the disagreement report. A one-agent-only row has no majority and is exactly where hallucinated or mis-split rows should be loud-failed. This is Rule 2/3 sensitive even if the current committed report does not contain such rows: the script defines the reproducible method for this source, and re-runs can admit unsupported rows. Require at least 2/3 presence for every row, or require an explicit correction/rename entry with a source citation.

- The tests do not satisfy the stated Rule 5 "all populated fields" contract for sampled rows. Only `13.1` pins every populated field. `test_khendjer_file_13_22` checks six fields but omits populated fields visible in `reconciled.jsonl` (`dynasty`, `sequence_in_dynasty`, `sequence_suffix`, `nebty_name_transliterated`, `nomen_transliterated`, `concurrent_with`, `source_citation`, etc.; `test_sources_ryholt_sip.py:81-89`). `test_sakir_har_15_3_no_prenomen` omits `date_bce_end`, `concurrent_with`, `nebty_name_transliterated`, `golden_horus_name_transliterated`, `nomen_transliterated`, and citation (`test_sources_ryholt_sip.py:92-105`), which is why the markdown-contaminated `nomen_transliterated` value was not caught. Expand each sampled-row test to assert every populated field, especially reviewer-overridden rows.

## P3

- `test_nebmaatre_file_17_a_letter_suffix` contains a defensive grandfather clause instead of a pinned value: `assert r["sequence_in_dynasty"] == 0 or r["sequence_in_dynasty"] is None or isinstance(r["sequence_in_dynasty"], int)` (`test_sources_ryholt_sip.py:175-178`). The last disjunct accepts any integer, so a regression to `9` or `999` would pass. This conflicts with Rule 5 and Rule 12. Pin the intended representation for letter-only suffix rows, probably `None` given the committed row.

- The row-count test uses a tolerance band (`150 <= len(rows) <= 170`) even though the test comment names `157` as the reference value (`test_sources_ryholt_sip.py:32-41`). For this source, row count is a key guard against skipped `Appellation` entries and duplicated suffix rows; allowing ±20 rows weakens deterministic enforcement. Pin `len(rows) == 157` unless a future source update deliberately changes the extract and updates the expected value with a review note.
