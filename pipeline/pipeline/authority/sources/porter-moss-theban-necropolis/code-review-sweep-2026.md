# Code Review Sweep — Porter & Moss Theban Necropolis

Scope: full source directory plus `pipeline/tests/test_sources_porter_moss_theban_necropolis.py`, cross-checked against `code-review-chunk7.md`, `code-review-chunk8.md`, `reviewer-notes-chunk7.md`, and `reviewer-notes-chunk8.md`. Findings below avoid re-raising the already-fixed chunk-7/8 issues.

## P2 — chunk-1 tests still do not value-pin every populated row

`pipeline/tests/test_sources_porter_moss_theban_necropolis.py:487-613` uses three full-row examples plus a few thematic assertions and explicitly says those examples "Together ... cover every populated-field shape per rule 5." That is not the same as asserting every populated row value. Several committed rows in `reconciled.jsonl` have mappable values that are not directly value-pinned: `KV2` (`occupant_name="Ramesses IV"`, page 497), `KV6` (`Ramesses IX`, page 501), `KV10` (`Amenmesse`, `notes_from_pm="Inaccessible after Corridor B."`, page 517), and chunk-2 rows `KV15`/`KV16` (`Sethos II`, `Ramesses I`, pages 532/534). A regression changing KV10's note or KV2/KV6/KV15/KV16 names would still pass the present tests because only row-count/shape/chunk-wide invariants cover them.

This violates CLAUDE.md rule 5's fixture discipline: every populated field on every fixture-class row needs a value assertion, not representative-shape coverage. Add per-row full assertions for the unpinned KV rows, or replace the flagship-style tests with a data table that exact-matches all fields for chunks 1-2.

## P2 — chunk-7 prompt still contains stale answer guidance that conflicts with the fixed extract

`prompt-chunk-7-south-west-valleys-dra-abu-el-naga.md:158-164` lists per-tomb role answers, including stale pre-review guidance: `ʿAhmose son of Seqenenre, ʿAhhor → "Royal Family"`. The landed extract, reviewer notes, and tests now correctly use `DAN-Aqhor` with `occupant_role="Official"` because PM's "Royal acquaintance" is a courtier title. The same prompt also says at line 193 that no chunk-7 tombs are expected to be `Unfinished`, while the fixed extract and test suite correctly set `DAN-MentuhotpSankhibtaui.is_unfinished=true`.

This is not the already-filed chunk-7 prefix/test issue or chunk-8 answer-leak issue. It is a remaining reproducibility risk in the committed prompt: a fresh three-agent extraction from the documented prompt is biased toward known-wrong values, then relies on `fix_rows.py` to repair them after review. Per CLAUDE.md rules 1/7 and the source's own prompt-discipline policy, replace tomb-specific answer bullets with field rules tied to headword evidence.

## P3 — source docs still carry pre-fix names/diacritics

The README/transcription audit trail is partially stale after the chunk-7/8 fixups. `README.md:110-114` still describes chunk 7 using `DAN-AhmosiNefertari`, "Ahmose-Nefertari", "Djehuti", and "Ahhor", even though the landed ids/data are `DAN-AhmosiNefertere`, `DAN-MentuhotpIWifeOfDjhuti`, and `DAN-Aqhor`. `README.md:114` also says QV47 was corrected to `Sit-dḥout`, but `reconciled.jsonl:47` and the tests pin the reviewer-restored underdot-D spelling `Sit-ḍḥout`. `transcribe.md:65` still uses `DAN-KamoseWadjkheperre` as the descriptor example, despite the later rename to `DAN-KamosiWazkheperre`.

The JSONL/tests are correct, so this is documentation drift rather than data corruption. Still, these files are the reproducibility/audit trail for rule 1; leaving old spellings beside fixed rows invites future agents to reintroduce already-reviewed mistakes.
