# Per-museum ruler test — decision rule

**Approved by the project owner on 2026-10-17, before any model judged any case.** The owner chose
each point marked below in plain-language questions the same day, and then approved running it.
Two parts were added after the code review and approved by the owner the same day, also before
any case was judged: the twin condition and floor in rule 1, and "Calls that give no answer".

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
   museum decided. Only decoys whose real twin (the same records shown with their own target)
   was confirmed count: a decoy is surely a wrong ruler only if its twin is the right one. The
   others are reported and set aside from the calibration. Fewer than 15 counted decoys also
   makes the result INCONCLUSIVE (owner's choice, 2026-10-17).
2. **Wrong links → the museum fails.** A museum with any wrong link fails (owner's choice,
   2026-10-17: "No wrong links"). Every wrong link found is a specific error to fix.
3. **Otherwise the museum passes.** Unconfirmed links (the pages a reviewer could open did not
   settle the link either way) are reported per museum, in units and records, and decide nothing
   (owner's choice, 2026-10-17: "Don't count them").
4. **Misses never fail a museum.** They are reported as a fix list (owner's choice, 2026-10-17),
   with the rulers the reviewers named. Only the outcome (`one_ruler` or not) is reconciled. When
   both reviewers find one ruler, the fix list gives both names as they wrote them, unreconciled;
   each fix is researched and sourced on its own before it reaches the authority.

## Calls that give no answer

- **A call that read nothing.** A call in which every `open_page` call returned an error, and
  none a page, decides nothing and is retried, like a malformed answer (#384).
- **No answer after three tries.** A reviewer or reconciler with no valid answer in three
  retryable calls gives none. A case missing a review, or whose disputed question the
  reconciler could not answer, is settled as `insufficient_evidence` (`no_valid_review`,
  `no_valid_reconciliation`): an unconfirmed link, an unconfirmed miss, or a decoy not
  rejected. The run goes on.
- **A call that stops the run** (a wrong release, model or billing) holds no decision. It may be
  set aside only by an entry in the committed ledger (`set-asides.json`), which names the call,
  its hash, the reason, who decided and when. The README discloses every entry. A call with a
  decision is never set aside, and no stored attempt is ever moved or removed (the scorer
  requires attempts numbered 1..n).

## What the decoys do and do not show

Every decoy is the easiest kind of wrong ruler: the same name with another regnal number. Passing
the calibration shows the reviewers reject such a ruler. It does not show they catch subtler
wrong links (an alias of another ruler, a differently numbered label), and the share of decoys
caught is not an estimate of how often real links are wrong.

## What the outcome changes

Nothing in production, by itself. A museum that passes is one in which the review found no wrong
link; since unconfirmed links decide nothing, that holds even for a museum none of whose links
could be confirmed, and the score reports how many were. Brooklyn and Harvard have no decoys of
their own, so the calibration says nothing about the review of those two museums in particular.
A museum that fails has a list of wrong links to fix, and is tested again after the fix.
