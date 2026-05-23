---
name: Glob path resolution for this repo
description: Glob returns relative paths from its path param; for hapi pipeline authority sources use pipeline/pipeline/ double-prefix in absolute paths
type: feedback
---

When calling Glob with `path=/Users/philipp/code/hapi`, results like `pipeline/authority/sources/porter-moss-theban-necropolis/reconciled.jsonl` look like they'd be at `/Users/philipp/code/hapi/pipeline/authority/sources/...` — but that path doesn't exist.

The actual absolute path requires the double `pipeline/pipeline/` prefix: `/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/reconciled.jsonl`

**Why:** The `pipeline/` directory in the repo root is the Python package root (with its own `pipeline/` subdirectory inside it). The Glob tool with `path=/Users/philipp/code/hapi` finds files relative to the repo root, showing them as `pipeline/authority/...` relative to cwd `/Users/philipp/code/hapi/pipeline`, NOT relative to the `path` parameter. This causes a double-pipeline confusion.

**How to apply:** Whenever constructing absolute paths for authority source files from glob results, prepend `/Users/philipp/code/hapi/pipeline/` to what glob shows as `pipeline/authority/...`. Or equivalently: use path `/Users/philipp/code/hapi/pipeline/pipeline` in Glob calls for authority sources.
