# Weak-sign key: hill-climb on the TLA names (protocol v2, 2026-10-15)

The royal-women resolver's third tier (`pipeline/pipeline/authority/weak_sign_skeleton.py`)
matches spellings of one name across conventions. The protocol is `PROTOCOL.md`, committed
(af905e7) before any v2 measurement. Two later harness changes: 99ec9fb fixed module loading,
before any measurement; 1590c17 corrected the merge count to distinct names, after the run
("Correction after the run" below). A first climb (v1) was withdrawn on review; why, and
what it changed, is in `PROTOCOL.md`.

## Result

Recall and coverage by split, and strict strong merges over the whole set (names):

| Key | Train recall | Val recall | Train cov. | Val cov. | Strict merges | Fold-aware | Decision |
|---|---|---|---|---|---|---|---|
| v2-0 baseline | 80.64% | 82.89% | 72.00% | 70.67% | 246 | 218 | — |
| v2-1 C1: j weak in transliterations | 85.48% | 86.14% | 72.00% | 70.67% | 244 | 216 | **accepted** |
| v2-2 C2: z as s | 86.79% | 86.87% | 71.98% | 70.67% | 283 | 255 | rejected: merges rise |
| v2-3 C3: ṯ as t | 88.06% | 88.79% | 72.00% | 70.67% | 263 | 235 | rejected: merges rise |
| v2-4 C4: no c/q as k | 84.93% | 85.99% | 72.00% | 70.67% | 226 | 198 | rejected: recall falls |

**The protocol accepted v2-1. The committed key is v2-4, by the project owner's decision
(2026-10-15).**
- **Why.** The code review of the climb showed that C4, the removal of c/q → k, could not pass
  the acceptance rule, since removing a fold never raises recall. Read the other way, as an
  addition to v2-4, c/q → k fails the rule as z/s and ṯ/t do: strict merges rise 226 → 244
  for half a point of recall. The owner dropped it. The Ptolemaic queens' Greek and Latin
  spellings (Kleopatra, Berenice) are to meet through cited alternative names instead.
- **A test checks this.** v2-4's code is the committed key's, and the acceptance rule rejects
  v2-1 against v2-4.

**Held-out check:** the claim graph's king spellings.
- Scored once for v2-0 and v2-1: 51.46% (106 of 206 pairs) each.
- v2-4 was scored after the decision, so it is reported, not used to choose: 50.97% (105 of
  206).
- C1 cannot change this figure: king display names are English, with no transliteration sign.
- 30 keys are shared between clusters, mostly homonymous kings (Amenhotep, Ramesses).
- The low absolute recall reflects clusters whose sources give different names (throne name
  against birth name) or Greek forms, which no spelling key joins.

**TLA test split** (spent by v1, so not held-out figures): 82.64% for v2-0, 86.46% for v2-1,
85.83% for v2-4.

**Correction after the run (Codex review of PR #365).**
- **The bug.** The harness counted group memberships, not distinct names. A name can sit in
  several groups when its renderings key apart; `mnṯwḥtpw` sat in three. So the strict and
  fold-aware merge counts were inflated.
- **The fix.** `measure.py` now counts distinct names, as PROTOCOL.md defines the metric, and
  every result was regenerated. The table above shows the corrected counts.
- **The effect.** No decision changed. Reading the two tables, the acceptance rule gives the
  same verdict for every candidate under both counts; the test re-applies it to the corrected
  counts. C1's margin over the baseline narrowed from 8 names to 2. The counts as first
  reported were:

  | Key | Strict | Fold-aware |
  |---|---|---|
  | v2-0 | 260 | 229 |
  | v2-1 | 252 | 224 |
  | v2-2 | 293 | 265 |
  | v2-3 | 270 | 242 |
  | v2-4 | 234 | 206 |

## Limits of this climb (from its code and egyptologist reviews)

- **The acceptance rule is asymmetric.** It requires train recall to rise, so it can admit a
  fold but never remove one. Rules already in the baseline were never tested by it. That is how
  c/q → k survived the run; it was settled by the owner's decision above.
- **C1's evidence is not independent.** C1 is v1's adopted step, and its effect was known
  before v2. v2 splits by a salted name hash while v1 split by lemma, so about 60% of v2's
  validation and test names were in v1's train split. The held-out set cannot see C1. C1 rests
  on the transliteration convention (ṯ and ḏ are letters of their own), not on uncontaminated
  measurement.
- **C1's trigger is narrow.** It fires only on ꜣ, ꜥ, ꞽ, =, ⸗ or i̯. 1,583 TLA transliterations
  have none of these, and 121 of them keep t + j or d + j as ṯ/ḏ (`Nfr.t-jy.tj`, Nefertiti).
  The trigger also reads the whole text, so an English Dj beside a transliteration loses its
  ḏ. Both limits are pinned in tests. Part of C3's recall gain was these misses being repaired.
  A wider trigger is a candidate for a later protocol.
- **The merge metric has blind spots.**
  - Its "name" is the strict transliteration, so two TLA spellings of one name (Arsinoe
    `jrzjnt` and `ꜣrsjnt`) count as a merge. That biases it against any fold of an
    orthographic variant.
  - Its strong skeleton drops w, j, y and a final t, so it cannot see merges like
    Neferu/Neferet.
  - It counts over thousands of private and divine TLA names, not the 255 keyed D&H women.
- **"A key shared by different names never resolves" holds only within D&H.** `DIFFERENT_NAMES`
  lists collisions among D&H's own women. A museum name outside D&H can still meet a D&H
  woman's key: "Isetweret" (ꜣst-) and D&H's Sitre A (zꜣt-) both key `str`. The gates bound
  this: a three-consonant key needs a named family king, and a contradicting dynasty is
  refused. A test pins it.
- **Commit order is consistent with "protocol before measurement", not proof of it.**
  - Order: af905e7 → 99ec9fb → a7af450 (results), then the post-run correction 1590c17.
  - Git cannot rule out a run from an uncommitted tree.
  - The harness at af905e7 could not load its normalizer until 99ec9fb, which weakly
    supports "no earlier run".

## Files

- `PROTOCOL.md`: the protocol.
- `measure.py`: the harness.
- `normalize_frozen.py`: the normalizer every key is measured with.
- `keys/`: each key as measured.
- `results/`:
  - each candidate's metrics, the key it was measured against, and the decision;
  - `held-out-king-spellings.json`;
  - `tla-test-split-not-held-out.json`.

`pipeline/tests/test_weak_sign_key_hillclimb.py` rebuilds every result from its key and the
frozen normalizer, re-applies the acceptance rule, and checks that v2-4 (the owner's
decision, above) is the committed key's code.
