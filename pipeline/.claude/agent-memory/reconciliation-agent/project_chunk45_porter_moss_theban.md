---
name: project_chunk45_porter_moss_theban
description: Chunk 45 (TT361–TT370) merged and fixed; 445 rows; 2 tie-breaks; 2 CHUNK45_CORRECTIONS; 0 DERIVER_OVERRIDES; 0 substantive flags
metadata:
  type: project
---

Chunk 45 (TT361–TT370) merged and fixed; 445 total rows (prior 435 + 10 new).

**Why:** Phase-0 reconciliation of porter-moss-theban-necropolis chunk 45.

**How to apply:** All 10 rows are clean. No egyptologist flags needed.

## Tie-break overrides added (2)

- `TT362|notes_from_pm` — 1/1/1 split on wab-priest romanisation (A=`Wab-priest` no ayin; B=`waʿb-priest` ayin after a; C=`wʿb-priest` no medial-a). Pinned `wʿab-priest` per TT14/TT97/TT100 bar-a-as-ayin-before-a convention.
- `TT368|notes_from_pm` — 1/1/1 split on `called Ḥuy` prefix (A capitalised `Called`; B lowercase `called` verbatim PM p.431; C dropped it entirely). Pinned agent B.

## CHUNK45_CORRECTIONS (2)

- `TT366 notes_from_pm` — restore PM-printed diacritics `harîm` (circumflex î) and `Nebḥepetrēʿ` (macron ē) that A+C majority dropped. PDF p.429 confirms.
- `TT369 notes_from_pm` — restore macron ō on `Taōne(t)` that A+C majority dropped. PDF p.432 confirms. Also notes: `occupant_role=High Priest` from A+B majority is correct (First prophet of Ptaḥ maps to High Priest — Ptaḥ is a major state cult alongside Amun/Re).

## DERIVER_OVERRIDES: 0

No spurious deriver fires — no `(?)`, `usurp`, `uninscribed`, or `probably/perhaps` tokens in any chunk-45 headwords.

## Key decisions

- `TT361 shared_with_tombs=[]` — `(name from tomb 360)` is wife-name provenance, not ownership.
- `TT363 occupant_name=Paraʿemhab` — B+C 2/1 majority (ayin present).
- `TT365 shared_with_tombs=[]` — `For position in court of tomb 296` is positional cross-ref, not ownership (all 3 agents correct).
- `TT370 occupant_name=null, role=Official` — anonymous `A Royal scribe` headword.

## Idempotency: confirmed (MD5 stable across two fix_rows.py runs)

[[project_chunk44_porter_moss_theban]]
