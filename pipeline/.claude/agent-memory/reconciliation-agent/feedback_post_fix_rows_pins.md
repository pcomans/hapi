---
name: post_fix_rows_pins
description: Every new tie-break-override entry requires a matching post-fix-rows pin in test_porter_moss_merge_tie_break.py
type: feedback
---

After adding any new entry to `tie-break-overrides.json`, you must also add a matching entry to the `EXPECTED` dict in `tests/test_porter_moss_merge_tie_break.py::test_post_fix_rows_pipeline_determinism`. The value to pin is the FINAL post-fix-rows value (not the override value, if CHUNK_CORRECTIONS mutates it further).

**Why:** The test asserts that every override key has a corresponding post-fix-rows pin. Missing a pin causes a loud test failure.

**How to apply:** After running fix_rows.py, `python3 -c "..."` to read the exact final value from reconciled.jsonl, then pin that value verbatim in EXPECTED.
