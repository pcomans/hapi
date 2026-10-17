# Per-museum ruler test — decision rule

**Status: DRAFT.** The project owner chose its main points on 2026-10-17 (below). No model judges
any case before the owner approves the whole file; the approval and its date will be recorded here.

## What is judged

Each museum's ruler links to the authority, on their own: no museum pairs and no plain-text
baseline (owner, 2026-10-17: "what we should be doing is matching each museum against the
authority layer"). Cross-museum matches follow from shared authority rulers.

- **Link cases.** Every distinct link the authority makes (a mention text and the ruler it
  resolved to, with every record that carries it). The question: is that ruler the one the
  records name? Outcomes: `exact_identity` (confirmed), `different_identity` (a **wrong link**),
  `insufficient_evidence` (unconfirmed).
- **Miss cases.** Every distinct mention text the authority left unmatched or ambiguous. The
  question: do the records name one specific ruler with it? Outcomes: `one_ruler` (a **miss**),
  `not_one_ruler`, `insufficient_evidence`.
- **Decoys.** 20 link cases shown with a wrong ruler: another ruler of the same name and a
  different regnal number. The reviewers are not told decoys exist.

Each case is judged by two independent reviewers and, where they disagree, a reconciler, as in
the earlier registrations (`scripts/review_protocol.py`).

## Rule

Applied in this order (`scripts/score.py`):

1. **Calibration → INCONCLUSIVE.** If the review fails to reject more than 1 in 5 decoys (a decoy
   judged anything but `different_identity`), the result is INCONCLUSIVE: reported, with no
   museum decided.
2. **Wrong links → the museum fails.** A museum with any wrong link fails (owner's choice,
   2026-10-17: "No wrong links"). Every wrong link found is a specific error to fix.
3. **Unconfirmed links.** A museum with no wrong link passes when its unconfirmed links cover at
   most 1 in 10 of its linked records. Otherwise its outcome is `unconfirmed`: no wrong link
   found, but too much left undecided to call it a pass.
4. **Misses never fail a museum.** They are reported as a fix list (owner's choice, 2026-10-17),
   with the rulers the reviewers named. Only the outcome (`one_ruler` or not) is reconciled. When
   both reviewers find one ruler, the fix list gives both names as they wrote them, unreconciled;
   each fix is researched and sourced on its own before it reaches the authority.

## What the decoys do and do not show

Every decoy is the easiest kind of wrong ruler: the same name with another regnal number. Passing
the calibration shows the reviewers reject such a ruler. It does not show they catch subtler
wrong links (an alias of another ruler, a differently numbered label), and the share of decoys
caught is not an estimate of how often real links are wrong.

## What the outcome changes

Nothing in production, by itself. A museum that passes has links reviewers confirmed; a museum
that fails has a list of wrong links to fix, and is tested again after the fix.
