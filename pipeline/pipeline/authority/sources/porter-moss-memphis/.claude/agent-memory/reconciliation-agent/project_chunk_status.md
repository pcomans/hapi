---
name: project_chunk_status
description: Porter-Moss Memphis chunk merge completion status and recurring tie-break patterns
metadata:
  type: project
---

As of 2026-05-16, chunks 1–7 are fully merged (10 tie-break overrides in tie-break-overrides.json cover all prior ties). Chunk 8 (33 rows, G2347a–G2423 range) has 6 unresolved 1/1/1 ties blocking merge.

**Why:** Each chunk introduces new rows; merge.py raises on first unresolved tie. The parent/egyptologist must add overrides before merge can proceed.

**How to apply:** Before running merge on a new chunk, check whether the tie-break-overrides.json has coverage for all ties in that chunk's rows. Run the tie-scanning script to identify uncovered ties first.

## Recurring tie patterns seen across chunks

- `notes_from_pm` 1/1/1 ties: most common. Usually caused by (a) ayin normalisation (raised-`a`/`c` → U+02BF), (b) heading vs body boundary disagreement (one agent spills into the next sub-heading), (c) sentence-final period presence, (d) one agent returning null for a sparse row.
- `occupant_name` ties: normalisation of underdot-Ḥ (`meryptaḥ` vs `meryptah`) and capitalisation after hyphen.
- `occupant_alt_names` list ties: typically lowercase-vs-capitalised post-hyphen element.
