---
name: feedback_shape4_named_anchor_leak
description: Naming a specific Shape-4 joint tomb by its PM headword in a rule paragraph leaks the answer for that row — use pattern descriptions instead
metadata:
  type: feedback
---

When a special-case rule applies to a Shape-4 joint multi-burial tomb, do NOT anchor the rule using the verbatim PM headword of that specific tomb.

**Why:** Writing "For the `TOMB OF THE PSAMMETHEKS AND KHEDEBNEIT-YERBONI [II]` row specifically:" tells agents (a) that a Shape-4 joint tomb appears in the chunk, (b) its exact PM spelling — answers the agent should derive from reading. Same leak class as per-row answer enumeration.

**How to apply:** Write the rule generically, referencing the structural pattern rather than the specific instance. E.g.: "For any Shape-4 joint multi-burial tomb where the headword has `son of <Mother>` clauses: mothers go in `co_occupants` ONLY if PM explicitly states the mother is buried there; otherwise notes_from_pm only."

First caught in chunk-31 audit (2026-05-19).
