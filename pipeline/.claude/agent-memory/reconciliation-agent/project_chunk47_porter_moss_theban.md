---
name: project_chunk47_porter_moss_theban
description: Chunk 47 (TT381–TT390) merged, fixed, and reviewed; 465 rows total; 3 tie-breaks (all PDF-confirmed agent-A pins); 2 DERIVER_OVERRIDES; 3 CHUNK47_CORRECTIONS.
metadata:
  type: project
---

Chunk 47 (TT381–TT390) reconciled, fixed, and review-corrected. Total rows: 465.

**Why:** Ongoing Phase-0 PM I.1 Theban Necropolis transcription pipeline.
**How to apply:** Reference for next chunk (48 = TT391–TT400).

## Final state after PR #294 round-1 reviewer corrections

The merge-time picks below were superseded by review-cycle PDF verification. The values now pinned in `tie-break-overrides.json` reflect what PM actually prints on the printed page (PDF-confirmed at PR #294 round 1 by both Gemini and the egyptologist reviewer).

## Tie-break overrides added (3, all post-review-confirmed)

1. `TT381|notes_from_pm` — 1/1/1 on statue-sentence inclusion + CAPS + macrons. **Pin agent A** including `Headless statue of Amenemōnet.` (PM body content), CAPS form `AMENEMŌNET` for the `Perhaps` clause, AND macrons preserved (macron-Ō on the CAPS form + macron-ō on the body-prose form, both per PDF p.453 — egyptologist P1 F2 PR #294 round 1).

2. `TT386|notes_from_pm` — 1/1/1 on Wilkinson parenthetical inclusion + site-name spelling. **Pin agent A's `Mináfed`** (acute á; B dropped parenthetical, C OCR-misread as `Mimifed`). PDF p.437 confirmed `Mináfed` per egyptologist P1 F1 PR #294 round 1.

3. `TT389|notes_from_pm` — 1/1/1 on OCR-garbled priest-title cluster (`snulj-priest`, `lz.rk-priest`). **Pin agent A's `smtj-priest` + `ḥsk-priest` + macron-bearing `Amenemōnet`** — PDF p.440 confirmed at PR #294 round 1. The initial merge-time `snwḥ`/`ḥrk` plausibility-decode was wrong; Gemini-#294 round 1 correctly pushed for direct-PDF-pin in tie-break (single source of truth, no redundant CHUNK47_CORRECTIONS).

## CHUNK47_CORRECTIONS (3)

1. `TT388 occupant_role → "Unknown"` — sentinel-null collapse pattern (same as TT371–TT379 in chunk-46).
2. `TT390 notes_from_pm` — restored `Amūn` macron (B+C 2/1 majority chose `Amon`; agent A was PM-faithful).
3. `TT382 notes_from_pm` — restored circumflex on `harîm` (B+C 2/1 majority dropped to `harim`; egyptologist P1 F3 PR #294 round 1 PDF p.435 verified).

## DERIVER_OVERRIDES (2)

- `TT385 attribution_certainty → "attested"` — `(Perhaps brother of Nebsumenu, tomb 183.)` is a kinship clause (secondary), not a primary-occupant identity hedge. Same pattern as TT340/TT346.
- `TT388 is_uninscribed → True` — PM's `No texts. Saite.` is the semantic equivalent of `uninscribed` per the TT115 chunk-20 precedent (code-reviewer P1 PR #294 round 1).

## Lessons learned (post-mortem of PR #294 round-1 cycle)

1. **Trust PDF over OCR/agent-majority.** TT389 burnt one round-1 review cycle because the reconciliation agent chose B+C majority on OCR-opaque priest titles instead of agent A's PDF-faithful reading. Always verify against the printed page when the cluster is opaque.
2. **Pin PDF-confirmed values DIRECTLY in tie-break, don't double-track via CHUNK*_CORRECTIONS.** Gemini's TT389 architectural simplification (single source of truth) was right.
3. **Same-chunk diacritic consistency check.** TT381 macron drift was the lone outlier within the same chunk where TT389/TT390 preserved macrons — catchable by `grep` for macron-stripped names that match macron-preserved patterns elsewhere in chunk.

## Other notes

- TT381 `is_uninscribed=True` (deriver fires correctly on "Uninscribed" in notes).
- TT381 `attribution_certainty=uncertain` (deriver fires correctly on "Perhaps").
- `test_182_uninscribed_canonical_set` updated to include TT381 + TT388.
- `test_182_uncertain_attribution_canonical_set` updated to include TT381.
- Row count test updated: `test_chunk47_row_count` asserts 465.
- 2152 tests pass.
