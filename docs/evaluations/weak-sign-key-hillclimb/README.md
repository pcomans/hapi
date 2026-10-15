# Weak-sign key: hill-climb on the TLA names (protocol v2, 2026-10-15)

The royal-women resolver's third tier (`pipeline/pipeline/authority/weak_sign_skeleton.py`)
matches spellings of one name across conventions. The protocol is `PROTOCOL.md`, committed
(af905e7) before any v2 measurement; the one later harness change (99ec9fb) fixed module
loading, before any measurement too. A first climb (v1) was withdrawn on review; why, and
what it changed, is in `PROTOCOL.md`.

## Result

Recall and coverage by split, and strict strong merges over the whole set (names):

| Key | Train recall | Val recall | Train cov. | Val cov. | Strict merges | Fold-aware | Decision |
|---|---|---|---|---|---|---|---|
| v2-0 baseline | 80.64% | 82.89% | 72.00% | 70.67% | 260 | 229 | — |
| v2-1 C1: j weak in transliterations | 85.48% | 86.14% | 72.00% | 70.67% | 252 | 224 | **accepted** |
| v2-2 C2: z as s | 86.79% | 86.87% | 71.98% | 70.67% | 293 | 265 | rejected: merges rise |
| v2-3 C3: ṯ as t | 88.06% | 88.79% | 72.00% | 70.67% | 270 | 242 | rejected: merges rise |
| v2-4 C4: no c/q as k | 84.93% | 85.99% | 72.00% | 70.67% | 234 | 206 | rejected: recall falls |

**The final key is v2-1.** Its code is the committed key's (a test checks this). Notes:
- **C4 is a trade-off.** The existing c/q→k rule costs 18 merged names for about half a point
  of recall. The protocol keeps it; the key's docstring records the cost.
- **Held-out check, the claim graph's king spellings, scored once:**
  - recall is 51.46% (106 of 206 pairs) for both baseline and final;
  - 30 keys are shared between clusters, mostly homonymous kings (Amenhotep, Ramesses).
  - C1 cannot change it: king display names are English, with no transliteration sign.
  - The low absolute recall reflects clusters whose sources list different names (throne name
    against birth name) or Greek forms, which no spelling key joins.
- **TLA test split** (spent by v1, so not a held-out figure): 82.64% for the baseline, 86.46%
  for the final key.

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
frozen normalizer, re-applies the acceptance rule, and checks that v2-1 is the committed
key's code.
