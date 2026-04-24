# Code review — PR #101 (chunk 8 + chunk-7 ḥ sweep), retrospective pass

Scope: `fix_rows.py` (CHUNK8_CORRECTIONS + retroactive CHUNK7 ḥ entries),
`prompt-chunk-8-qv.md`, `reconciled.jsonl` delta, test additions.
Read against CLAUDE.md constitutional rules, README policy, and existing
chunk conventions.

## P1 — must fix

### 1. `ḥ`-strip policy in `occupant_name` is convention, not enforcement

CLAUDE.md rule 3: "If a rule can be a test, type constraint, or CI check,
it must be." The README's matchable-name-field rule ("strip underdot-H
in `occupant_name`") is currently enforced by three weak surfaces:

- README prose (rule 1: markdown = suggestion);
- per-chunk prompt (drifted between chunk 7 and chunk 8);
- `CHUNK*_CORRECTIONS` patches *after* drift is discovered by a
  reviewer.

That is exactly the failure mode the sweep on this PR was cleaning up.
Chunk 9 will drift the same way unless a module-level invariant pins
it. Add to `tests/test_sources_porter_moss_theban_necropolis.py`:

```python
def test_occupant_name_has_no_underdot_h() -> None:
    """README matchable-name convention: `ḥ` is stripped from occupant_name.
    Ayin `ʿ` and underdot-K `ḳ` are preserved as distinguishing radicals."""
    for r in _rows():
        name = r["occupant_name"]
        if name is not None:
            assert "ḥ" not in name, (r["tomb_id"], name)
            assert "Ḥ" not in name, (r["tomb_id"], name)
```

Five lines. Converts a three-round review into a loud CI failure on
first-agent drift. This is the single highest-value change in the
review.

## P2 — should fix

### 2. Reviewer-restored characters are not test-pinned

Per `feedback_fix_rows_unattributed_restoration.md`, `CHUNK8_CORRECTIONS`
entries that *insert* characters absent from the text layer must be
guarded by tests so a future edit of the tuple cannot silently regress
the reviewer-attributed correction. Two unguarded restorations:

- **QV47** `notes_from_pm = "… Sit-ḍḥout …"` — `ḍ` (U+1E0D) was
  restored against OCR's `gḥ`. `test_chunk8_notes_from_pm_royal_kinship`
  asserts only the `"daughter of Seḳenenreʿ-Taʿa"` substring, not
  `Sit-ḍḥout`.
- **QV74** `notes_from_pm` contains the full restored Tentopet
  filiation footnote (Gauthier / Černý / Seele hedges). QV74 is not
  in `test_chunk8_notes_from_pm_royal_kinship`'s expected dict at all.

Add substring assertions for both. Mirror the chunk-7
`"DAN-MentuhotpIWifeOfDjhuti": "Ḍḥuti"` pattern — it guards exactly
this class of reviewer-inserted diacritic.

### 3. Thematic-coverage gap per rule 5

Rule 5: every fixture test class must assert all mappable fields a
fixture populates. The current chunk-8 tests cover `valley`, `role`,
`is_unfinished`, `page`, `name`, and a notes substring-dict — good
themes — but the following rows have populated `notes_from_pm` values
not asserted anywhere: **QV33** (`"Dyn. XX(?). Buried. (…)"`), **QV46**
(`"(probably), Vizier. Temp. Tuthmosis I. (…)"`), **QV52**
(`"Ramesside. (…)"`), **QV73** (`"Dyn. XX."` substring),
**QV75** (`"A QUEEN, no name. (…)"`).

Either add them to the substring dict in
`test_chunk8_notes_from_pm_royal_kinship` (or a second themed test for
regnal-dating / uninscribed), or add 1–2 flagship per-row tests in the
chunk-1–4 style (QV46 Imhotep Vizier is the natural candidate — first
QV non-royal role + `(probably)` hedge).

## P3 — optional

### 4. Chunk-8 prompt leaks one expected value (line 142)

`prompt-chunk-8-qv.md` line 142: *"QV38 (Queen Sitreʿ, wife of Ramesses I)
has `Unfinished` explicitly in PM's headword — that's a known case."*

Per `feedback_phase0_prompt_no_answers.md` this is the exact shape
(tomb-id-specific expected-value callout) that PR #66/#68/#70 were
flagged for. It's one row, arguably justified as a "known-case"
disambiguation, but it's a crack in the rule-1/7 discipline and the
same reasoning ("just one") is how answer-tables grow. Either drop the
parenthetical (`"Unfinished"` as a literal-word rule is already stated)
or reword to a pure structural hint.

### 5. Retroactive-sweep audit trail is legible but distributed

The 8 chunk-7 `ḥ`-sweep entries are correctly placed in
`CHUNK7_CORRECTIONS` with per-entry `"Gemini round-3 sweep on PR #101"`
rationale, and idempotency/ordering are correct (rename-then-correct
path verified; re-running logs "already matches override"). No change
needed, but worth noting for future retroactive sweeps: a short block
comment at the top of the swept entries (you have one, line 305–311)
is the right pattern — keep doing it.

## Red-flag audit (chunk-7 regressions)

Verified chunk-7 test expectations against the swept values in
`reconciled.jsonl`: `test_chunk7_occupant_names_and_alt_names` and
`test_chunk7_notes_from_pm_populated_rows` were updated in lockstep
with the 8 sweep entries. No orphaned test expectation found. The
sweep did not touch any row whose `occupant_name` lacked `ḥ`
(spot-checked Antef, Hatshepsut-pre-sweep already plain, Neferhotep).

## Positives (do not change)

- `fix_rows.main()` rename-then-correct ordering is correct; corrections
  look up the post-rename `tomb_id`.
- Duplicate-detection loop (`_seen`) catches `(tomb_id, field)`
  collisions — useful guardrail.
- `test_all_corrections_includes_every_chunk_list` +
  `test_all_renames_includes_every_chunk_dict` enforce audit-trail
  aggregation.
- Reviewer-notes-chunk8.md QV38 investigation is a clean example of
  "reviewer saw pre-merge snapshot; no fix needed" — keep that format.

## Summary

One P1 (add the `ḥ`-invariant test), two P2s (pin reviewer-restored
characters, close the rule-5 thematic gap on populated notes). The
retroactive sweep itself is correctly structured; the cost is all on
the *next* chunk unless rule 3 is honored with the invariant test.
