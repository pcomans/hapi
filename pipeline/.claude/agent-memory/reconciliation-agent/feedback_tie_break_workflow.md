---
name: tie_break_workflow
description: Always run merge.py first before writing override entries; let ValueError surface the exact tie candidates
type: feedback
---

Always run `merge.py` first — do NOT pre-write overrides based on the parent's "known disagreements" list. The 2/1 majority cases (like TT64 occupant_name) resolve without any override; only actual 1/1/1 ties (which merge.py raises on) need an entry in tie-break-overrides.json.

**Why:** The parent agent's disagreement summary lists all differences including majority-resolved ones. Pre-writing overrides for majority cases wastes time and risks adding incorrect entries.

**How to apply:** Iterate: run merge.py → capture ValueError message (it includes exact candidates) → write override → repeat until clean exit.
