---
name: PM source absolute paths
description: Absolute file paths for Porter-Moss Theban Necropolis source files (not under pipeline/pipeline/authority/sources as the README suggests but under pipeline/pipeline/authority/sources)
type: project
---

The Porter-Moss authority source files live at:
- `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/reconciled.jsonl`
- `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/fix_rows.py`
- `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/merge.py`
- `/Users/philipp/code/hapi/pipeline/tests/test_sources_porter_moss_theban_necropolis.py`

**Why:** The Glob tool returns relative paths from its `path` parameter. With `path=/Users/philipp/code/hapi` the glob shows `pipeline/authority/sources/...` — which looks like it's missing a `pipeline/` prefix. The actual absolute path is `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/...` (the second `pipeline/` is the Python package directory inside the repo).

**How to apply:** Always use the double-`pipeline/pipeline/` prefix when constructing absolute paths to authority source files.
