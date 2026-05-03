# Revise priors: Beckerath 1997 titulary migration dropped legacy data — fix_rows.py is not "correct"

- **Date**: 2026-05-03T16:48:08Z
- **Agent**: general-purpose (subagent for issue #179)
- **Triggered by**: Task to migrate `pipeline/tests/test_sources_beckerath_1997_chronologie.py` from legacy `egyptian_titulary` (scalar) + `egyptian_titulary_kind` (scalar) to new `egyptian_titularies: list[{name,kind,when}]` plus `name_variants` and typed flags.

## Scope

Migrating ~13 failing tests in `pipeline/tests/test_sources_beckerath_1997_chronologie.py` to the new schema and adding 9 closure tests (typed-flag presence, kind vocab, dynasty-marker / anti-king / existence-uncertain canonical sets, the three structural anchors 03.02 split / 19.07 temporal / 15.05 slash alternatives, and a legacy-scalars-dropped negative test).

The task statement asserts: *"Don't change any code outside the test file. The fix_rows.py and reconciled.jsonl are correct."*

## Assumption suspected

That `fix_rows.py` correctly migrated all rows from the legacy scalars to the new list shape. **It did not.** It dropped `egyptian_titulary` from the rows but did not back-populate `egyptian_titularies` for many rows whose old scalar held real Beckerath data. Same for `name_variants` — paren-stripping happens on `name` but the stripped content is not recorded.

## Evidence

`pipeline/authority/sources/beckerath-1997-chronologie/reconciled.jsonl` inspected row-by-row:

**Rows the task's migration table (and existing tests) say have specific titularies, but actual data shows `egyptian_titularies: []`:**

| beckerath_id | task / old test says | actual `egyptian_titularies` |
|---|---|---|
| 01.01 Menes | `[{name:"Hor Aha",kind:"horus_name"}]` | `[]` |
| 06.03 Pepi I | `[Phios nomen, Meri-rê prenomen]` | `[]` |
| 15.05 Apophis | 2 prenomen entries (slash split A-qen-en-rê / A-user-rê) | `[]` |
| 18.02 Amenophis I | `[Djeser-ka-rê prenomen]` | `[]` |
| 18.10 Akhenaten | implies non-empty (`Nefer-cheprurê wa-en-rê`) | `[]` |
| 25.05 Taharqo | `[Tarakos nomen, Chu-nefertem-rê prenomen]` | `[]` |
| 26.01 Psametik I | implies non-empty (`Wah-ib-rê` prenomen) | `[]` |
| 26.04 Apries | implies non-empty | `[]` |
| 31.04 Chababasch | implies non-empty (`Senen-sotep-en-ptah` prenomen) | `[]` |
| 22.06 Schoschenq III | (legacy stored in `prenomen` only — OK; new shape skipped titulary) | `[]` (but `prenomen` field is populated) |

Rows that DID migrate cleanly: 03.02 (Djoser split nomen+horus_name), 04.01, 04.07, 05.01–05.09 (Dyn 5), 06.01, 06.04 Nemti-em-saf, 06.06, 15.04 Chajan (`[Iannas nomen, Se'user-en-rê prenomen]` — note: NOT `Iannas/Se'user-en-rê` as the old test pin would imply), 19.07 Si-ptah (the `anfangs/später` temporal split), 21.02, 26.02 Nekaw (`[Nekôs nomen, Nechaô nomen, Uhem-ib-rê prenomen]` — three entries), 26.05 Amosis II (`[Amasis nomen, Chnem-ib-rê prenomen]`), 28.01 Amyrtaios (`[Amen-ir-di-su nomen]`), 29.02 Achoris (`[Hagor nomen, Chnem-maat-rê prenomen]`), 29.03 Psamuthis (`[Pe-sche[re-n-]mut nomen, User-rê prenomen]`), 30.01 Nektanebês, 30.02 Teôs, 30.03 Nektanebôs.

So fix_rows.py back-populated some rows but not others. The pattern looks like: rows in the comprehensive Late-Period sweep (`test_late_period_adjacent_half_split_sweep`, `test_dyn29_dyn30_greek_egyptian_pair_split`) were migrated; the older single-row pin overrides (Menes/Hor Aha, Apophis/slash, Taharqo/mixed, Apries, Akhenaten, Chababasch, Psametik I, Amenophis I) were not.

**`name_variants` is empty on all 174 rows.** The task says 12.01 Ammenemes I and 18.02 Amenophis I should have non-empty `name_variants` extracted from the legacy paren content (`Amen-em-hat`, `Amen-hotpe`). Actual: 0/174 rows populated. The `name` field is already stripped (`"Ammenemes I."`, `"Amenophis I."`) but the variants are gone.

**Anti-king count slip in task wording.** Task says "the 7 rows whose notes mention Gegenkönig" then enumerates 5 + 22.07 = 6. Data shows exactly 6: `{02.09, 02.10, 11.07, 22.07, 29.03, 31.04}`. Just a counting slip in the prompt; not a real conflict.

## Decision needed from user

Two paths, mutually exclusive:

**(a) Fix fix_rows.py first** — back-populate `egyptian_titularies` from the legacy scalars (preserve the rule-1 source-fidelity invariant: `Hor Aha` is a real Beckerath fact about Menes; dropping it is data loss), record `name_variants` during paren-stripping, regenerate reconciled.jsonl via Dagster, **then** migrate the tests. This contradicts the task's "don't change any code outside the test file" constraint but honours the constitutional rule "data is sacred". Estimated extra scope: 1 fix_rows.py edit pass + 1 Dagster materialise + then the test migration.

**(b) Migrate tests only against the rows that did migrate** — drop the `01.01 Menes/Hor Aha` pin, the `15.05 Apophis slash alternatives` anchor (no data to anchor on), the `25.05 Taharqo mixed` assertion, the `26.01 Psametik I/Wah-ib-rê` pin, the `26.04 Apries`, `18.02 Amenophis I/Djeser-ka-rê`, `18.10 Akhenaten/Nefer-cheprurê`, `31.04 Chababasch/Senen-sotep-en-ptah` pins, `12.01 Ammenemes I/Amen-em-hat name_variants`, and weaken `test_compound_titulary_implies_mixed_kind` (the legacy `Tarakos, Chu-nefertem-rê`-style pins all evaporate). Open a follow-up issue tracking the dropped-data rows. The new closure tests would need to be weakened to match: `test_179_15_05_apophis_slash_alternatives` removed; the typed-flag-presence and kind-vocab tests remain useful.

## Recommendation

**Path (a).** Locking `egyptian_titularies: []` into tests for Menes/Apophis/Taharqo/Akhenaten/etc. would freeze a real data-loss regression as an invariant — the next agent who reads these tests will assume the empty state is correct. Per CLAUDE.md rule 6 ("data is sacred — reconciled artefacts are not authority data; they are slop") and rule 5 ("tests assert values, not absence of errors"), the right move is to fix the source of the data loss before pinning tests on top of it.

If the user prefers (b) for time-pressure reasons, the follow-up issue must be opened in the same session, the tests must include explicit `# TODO(#NNN)` comments at every weakened assertion site, and `feedback_revise_priors_design.md` should be updated to reflect that "fix_rows.py is correct" was a load-bearing prior that turned out to be wrong.

The marker file is at `.claude/revise-priors/1777826888-beckerath-1997-titulary-data-loss.md`. Push/commit/PR/merge are now blocked until the user resolves this.
