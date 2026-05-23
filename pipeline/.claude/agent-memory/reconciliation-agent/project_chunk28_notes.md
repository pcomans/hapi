---
name: project_chunk28_notes
description: Chunk-28 PM Memphis reconciliation notes — MAR- prefix handling, tomb_id fixes, substantive flags
metadata:
  type: project
---

Chunk-28 (PM III.2 pp. 490-507): 27 rows — 6 MAR- (Mariette letter-coded), 4 LS (Lepsius), 17 SAQ- (descriptor). Merged and fixed successfully.

**Why:** Needed to track the MAR- prefix decision and two tomb_id corrections for future chunks.

**How to apply:** Reference when chunk-29+ introduces more MAR- descriptor rows.

## MAR- prefix sort order decision

`"MAR-"` was NOT added as a separate key to AREA_ORDER. `test_prefix_vocabulary_consistent` extracts the prefix from both `MAR<N>` (numbered) and `MAR-B15` (descriptor) as `"MAR"` — adding a `"MAR-"` key would cause the test to fail (declared but unused key). Both series sort under `"MAR": 15`. Descriptor MAR- rows sort before numbered MAR<N> rows within the family (descriptor num=0 < numbered). Parent's "slot 16" for MAR- is aspirational; test constraint blocks it.

## Tomb_id corrections made to agent JSONL files

Two agent JSONL files were corrected before merge (raw extraction errors, not substantive):
1. `agent-b-chunk28.jsonl`: `SAQ-AnonNearNo39EarlyDynV` → `SAQ-AnonNearNo39` (2/3 majority on shorter form)
2. `agent-a-chunk28.jsonl`: `SAQ-Ptahmackheru` → `SAQ-Ptahmakheru` (OCR error: "mack" for "makh"; 2/3 majority)

## Substantive disagreement flagged for egyptologist

`MAR-B7|co_occupants`: three different readings of wife's name — agent-a "Ḥatḥormḥer", agent-b "Ḥatḥormnufer", agent-c "Ḥatḥormnefer". Override selected "Ḥatḥormnefer" (agent-c) as interim. Verify against PM III.2 p. 490.

## Cosmetic disagreement noted

`SAQ-Kaemhest` notes_from_pm: 2/1 majority chose `mdḥ`; minority (agent-a) has PM-faithful `mḏḥ`. Egyptologist may want to correct to `mḏḥ` via CHUNK28_CORRECTIONS.

## Overrides added: 22 entries in tie-break-overrides.json
All for notes_from_pm (17 rows) + 2 co_occupant_roles + 1 co_occupants
