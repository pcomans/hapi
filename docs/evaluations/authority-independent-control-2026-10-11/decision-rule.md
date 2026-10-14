# #337 re-registration — frozen decision rule

**Approved by the project owner on 2026-10-11, before any model judged any case of this
registration.** This is a *prospective decision rule* chosen after the 2026-09-14
exploratory outputs of the original registration (`../authority-independent-control-2026-09-13/`),
not a pristine pre-registration; those exploratory outputs were invalid and are not used.

## Labels

Every changed case (an authority-only or literal-only transition) receives one label from the
adjudicated review (`scripts/score_review.py`, `classify_case`):

| Label | Scorer category | Meaning |
|---|---|---|
| a | `a_authority_only_same_useful_exact_target` | authority gain: a correct, useful cross-museum match plain text misses |
| b | `b_authority_only_useful_but_wrong_or_nonidentity` | authority gain: a **wrong** identity (false merge) |
| c | `c_authority_only_false_or_not_useful_gain` | authority gain: not useful |
| d | `d_literal_only_same_useful_connection_lost` | authority loss: lost a correct, useful match plain text makes |
| e | `e_literal_only_false_or_not_useful_removal` | authority loss: removed a match that was wrong or not useful |
| f | `f_transition_uncertainty` | uncertain |

A **scope** is one entity type × one museum pair (e.g. sites, Met–Brooklyn).

## Rule

Applied in this order:

1. **Calibration → INCONCLUSIVE.** If the adjudicated review calls more than 20% of the
   retained (unchanged) control cases uncertain or wrong — any `calibration_control_*`
   category other than `calibration_control_same_useful_exact_target` — the result is
   INCONCLUSIVE: reported, no decision.
2. **Safety → REDESIGN.** Any **b** in a scope marks that scope unsafe. If **b ≥ 2** overall,
   or **b > 10%** of all authority gains (a + b + c), the verdict is REDESIGN.
3. **Utility → CONTINUE (targeted).** A scope with no **b** qualifies when all hold:
   - **a + e > d**;
   - at least **3** decided cases (labels other than f);
   - **f ≤ ⅓** of the scope's changed cases.

   If any scope qualifies, the verdict is CONTINUE, listing only the qualifying scopes.
4. **Otherwise → STOP.**

The numbers describe the current resolver's potential on the frozen ledger, not deployed
pipeline behaviour (#338).
