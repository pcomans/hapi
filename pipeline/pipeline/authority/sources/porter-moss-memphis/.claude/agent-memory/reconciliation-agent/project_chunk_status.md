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

## Chunk 36 (Abûsîr, PM III.1 2nd ed. 1974 pp.324-350) — 2026-07-04

Prepared (not merged — merge.py is the parent/egyptologist's to run) `tomb_id_corrections-chunk36.json` (4 entries: agent B keyed 4 MK-necropolis rows on the excavator's Schäfer mR-number — `ABU-HarshefhotpmR6/mR8/mR11/mR13` — where A/C used PM's own bracketed-ordinal `[I]`/`[II]` disambiguator or the bare headword; corrected to A/C's 2/3 canonical tomb_id) and a **standalone** `chunk36-overrides.json` (29 entries — the task explicitly forbade touching the shared `tie-break-overrides.json`; 28 `notes_from_pm` + 1 `occupant_alt_names`). Zero unresolved ties remained after both files applied (verified via `_majority`-mirroring script).

**Why it matters:** once `tomb_id_corrections-<chunk>.json` is applied via `pre_merge.py`, a field that looked like a 1/1/1 tie *before* correction (when the mismatched-tomb_id agent's row wasn't even in the same key-group) can resolve to a clean 2/1 **majority with no override needed at all** — e.g. chunk36's `occupant_name` for the Harshefhotp rows. Always re-run the tie-enumeration script *after* `pre_merge.py`, not before; enumerating on raw uncorrected files overstates the tie count and risks writing unneeded/wrong overrides.

**How to apply:** For future chunks with a per-chunk standalone overrides file (rather than appending to the shared `tie-break-overrides.json`), confirm with the parent agent whether merge.py will be pointed at a merged view of both files, or whether the parent manually appends the standalone entries — this agent's job stops at producing a verified-complete, verified-verbatim standalone file plus the report; it does not touch the shared override file or run `merge.py` itself.
