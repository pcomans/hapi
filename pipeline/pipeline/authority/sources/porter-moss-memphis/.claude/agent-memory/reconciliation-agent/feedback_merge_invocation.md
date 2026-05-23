---
name: feedback_merge_invocation
description: merge.py takes no chunk-number argument — invoke without args; it processes all chunks via glob
metadata:
  type: feedback
---

`merge.py` does not accept a chunk number positional argument. Passing `8` causes an argparse error. Correct invocation from `pipeline/`:

```
uv run python pipeline/authority/sources/porter-moss-memphis/merge.py
```

It reads all `agent-{a,b,c}*.jsonl` and `agent-{a,b,c}-chunk<N>.jsonl` files from the `raw/` dir automatically.

**Why:** merge.py is designed as a full-source merge (all chunks) to produce a unified `reconciled.jsonl`. The chunk-number concept lives only in the filename convention for the raw files.

**How to apply:** When instructed to "run merge for chunk N", run without the number; the new chunk's files are picked up by the glob.
