---
name: project_chunk47_porter_moss_theban
description: Chunk 47 (TT381–TT390) merged and fixed; 465 rows total; 3 tie-breaks; 1 DERIVER_OVERRIDE (TT385); 2 CHUNK47_CORRECTIONS; 1 substantive flag (TT389 priest titles).
metadata:
  type: project
---

Chunk 47 (TT381–TT390) reconciled and fixed. Total rows: 465.

**Why:** Ongoing Phase-0 PM I.1 Theban Necropolis transcription pipeline.
**How to apply:** Reference for next chunk (48 = TT391–TT400).

## Tie-break overrides added (3)

1. `TT381|notes_from_pm` — 1/1/1 on statue-sentence inclusion + CAPS on AMENEMONET. Pin agent A's complete form including "Headless statue of Amenemonet." (PM body content, not a citation ribbon). Macron stripped per OCR (no macron in source).

2. `TT386|notes_from_pm` — 1/1/1 on Wilkinson parenthetical inclusion and site-name spelling. A=`Mináfed` (accent), B=dropped parenthetical (wrong), C=`Mimifed` (matches OCR). Pinned C's form + A+C's inclusion.

3. `TT389|notes_from_pm` — 1/1/1 on OCR-garbled priest-title cluster (`snulj-priest`, `lz.rk-priest`). Constructed: B's `snwḥ-priest` (best phonetic decode) + B+C 2/1 `ḥrk-priest` + B+C 2/1 `Amenemonet` (no macron). **SUBSTANTIVE FLAG: priest titles unverified against physical PDF — egyptologist must confirm before reviewer pass.**

## CHUNK47_CORRECTIONS (2)

1. `TT388 occupant_role → "Unknown"` — sentinel-null collapse pattern (same as TT371–TT379 in chunk-46).
2. `TT390 notes_from_pm` — restored `Amūn` macron (B+C 2/1 majority chose `Amon`; A was PM-faithful).

## DERIVER_OVERRIDE (1)

- `TT385 attribution_certainty → "attested"` — `(Perhaps brother of Nebsumenu, tomb 183.)` is a kinship clause (secondary), not a primary-occupant identity hedge. Same pattern as TT340/TT346.

## Substantive disagreements

- **TT389 priest titles** — OCR-decoded `snwḥ-priest` + `ḥrk-priest` are reconstructions, not confirmed against physical PDF p.440. Flag for egyptologist before reviewer pass.

## Other notes

- TT381 `is_uninscribed=True` (deriver fires correctly on "Uninscribed" in notes).
- TT381 `attribution_certainty=uncertain` (deriver fires correctly on "Perhaps").
- `test_182_uninscribed_canonical_set` updated to include TT381.
- `test_182_uncertain_attribution_canonical_set` updated to include TT381.
- Row count test updated: `test_chunk47_row_count` asserts 465.
- 2152 tests pass.
