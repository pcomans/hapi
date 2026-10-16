# Ruler re-registration with Cleveland and the Walters — frozen decision rule

**Status: DRAFT, awaiting the project owner's approval.** No model judges any case of this
registration before the owner approves this file. The approval and its date will be recorded here.

The rule is #361's (`../ruler-reregistration-2026-10-15/decision-rule.md`): #337 v10's rule, with
#358's correction that a different-entity finding is labelled first. It is unchanged except for
the three points below. This registration scores rulers only, so every scope is rulers × one
museum pair. There are ten pairs: every pair of the Met, Brooklyn, Harvard, Cleveland and the
Walters.

## What differs from #361

1. **Tuned-on records are counted apart.** #369's resolver fixes were found on three records of
   #361's population:
   - the two "Queen Ahmose" records, brooklyn-3634 and met-566763;
   - Queen Neferu, brooklyn-3599.

   Any case whose nodes hold one of them (`tuned_on_records`, in the private answer key) is
   reviewed and labelled like every other case. It is left out of the **registered verdict**:
   rule steps 1 to 3 below run on the other cases only. The same steps run on every case are
   reported beside it (`decision_rule_including_tuned_on_cases`), as a sensitivity check that
   decides nothing.
   - In this population, two cases hold such records, both Met–Brooklyn: the Ahmes B retained
     control and the Neferu literal-only loss.
2. **More pairs, so more scopes.** The rule is applied per scope as before, and a scope still
   needs at least 3 decided cases to qualify. A scope with fewer changed cases than that cannot
   qualify here.
3. **What the verdict changes.**
   - **A scope that qualifies here** is qualified for rulers (`QUALIFIED_SCOPES`).
   - **Met–Brooklyn**, which #361 qualified, keeps that unless this registration finds a **b**
     there (a false merge), which marks it unsafe. Without its tuned-on cases it has too few
     changed cases to qualify again, so this registration cannot confirm it. It can only revoke
     it, by a b.
   - **Any other scope that does not qualify** stays unevaluated if it had fewer than 3 decided
     cases. If it had 3 or more and failed, it is recorded as not qualifying.

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

As in #361, a case whose two sides Stage 1 finds to be **different entities** is a wrong link,
labelled before any uncertainty is considered. An authority gain is then **b**, a literal-only
loss **e**, and a control `calibration_control_useful_but_wrong_or_nonidentity`.

## Rule

Applied in this order to the cases that hold no tuned-on record:

1. **Calibration → INCONCLUSIVE.** If the adjudicated review calls more than 20% of the
   retained (unchanged) control cases uncertain or wrong, the result is INCONCLUSIVE: reported,
   with no decision. "Uncertain or wrong" is any `calibration_control_*` category other than
   `calibration_control_same_useful_exact_target`.
2. **Safety → REDESIGN.** Any **b** in a scope marks that scope unsafe. If **b ≥ 2** overall,
   or **b > 10%** of all authority gains (a + b + c), the verdict is REDESIGN.
3. **Utility → CONTINUE (targeted).** A scope with no **b** qualifies when all of these hold:
   - **a + e > d**;
   - at least **3** decided cases (labels other than f);
   - **f ≤ ⅓** of the scope's changed cases.

   If any scope qualifies, the verdict is CONTINUE, and it lists only the qualifying scopes.
4. **Otherwise → STOP.**

The numbers describe the production resolver's links on the frozen inputs (`results/run-manifest.json`):
#337's corpus of 2026-08-27, and Cleveland's and the Walters' tables as ingested on 2026-10-16.
