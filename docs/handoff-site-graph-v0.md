# Handoff: authority-layer pressure test & site graph v0

_Snapshot: 2026-09-28. Supersedes the root-level `HANDOFF.md` (now removed)._

Read this before touching issues #326–#337, the claim graph, or the
`docs/evaluations/` trees. It exists so a session with zero memory of prior
work can pick this up correctly — it captures not just current status, but
**why** each dependency and decision is what it is, which the issue tracker
alone can't show.

## Origin

On 2026-08-28, the ask that started all of this: Hapi had spent months
building a scholarly authority layer (the claim graph) and a matcher, but
**nobody had checked whether either actually helps match museum records
across the three ingested museums (Met, Brooklyn, Harvard; 36,245 artifacts)**.
Two rounds of pressure-testing followed, tracked under epic
[#326](https://github.com/pcomans/hapi/issues/326).

## Round 1 (2026-08-27/28) — "can it link anything at all?" — answered

Committed at `docs/evaluations/hapi-linkability-mvp-2026-08-28/`. A
deterministic resolver run once, cold, over the real corpus.

**Verdict: not sufficiently linkable for production, all-three-museum
enrichment.** Only 47% of artifacts link to any authority node at all; ruler
matching barely functions outside the Met (Brooklyn 6 artifacts, Harvard 3,
by ruler); site connectivity is real but dangerously concentrated (Thebes
alone is 75% of cross-museum discovery routes); temple and excavation
entities have zero canonical targets; a 46-case review sample found 2 real
false links (the Brooklyn "Maatkare" homonym — linked to Hatshepsut, but the
object actually names a much later Dynasty 21 princess of the same name).

Recommendation at the time: don't scale the authority layer yet; ship a
narrow shadow-mode prototype (exact site aliases + Met Porter–Moss tomb
codes); reconcile ruler clusters and build a real site graph first. That
recommendation produced epic #326's ten-issue plan.

## Round 2 (2026-09-13/15) — "does it beat plain string matching?" — mechanically negative, verdict still blocked

Issue [#337](https://github.com/pcomans/hapi/issues/337) ran a direct A/B: a
**literal arm** (group by exact text, no authority involved) vs. the
**authority arm** (the current reconciled resolver), over one frozen,
authority-independent mention ledger (148,871 rows). PR #339 built the
harness; PR #340 (below) fixed a gap in its traceability protocol.

**The literal arm currently produces far more shared records than the
authority arm on every museum** (Met 27,330 vs 14,411; Brooklyn 2,894 vs
1,154; Harvard 534 vs 7). This looks backwards for a system built to
reconcile scholarly disagreement, but it isn't a design failure — it's
**discipline**. The authority resolver refuses to link when it can't
confidently pick one target (constitutional rule 2: no silent arbitrary
picks), and it hits that wall constantly today for two concrete, measured
reasons:

1. **The claim graph itself isn't reconciled yet.** Common ruler names
   (Amenhotep III: 2,750 artifacts, Akhenaten: 917, Ramesses II: 518) still
   have multiple unmerged scholarly-source nodes in the claim graph. The
   resolver sees several candidate targets, can't pick one, and abstains.
   Literal matching doesn't care — it just sees one string.
2. **The site graph has real coverage gaps.** "Egypt" — the single most
   common shared term across all three museums — is unmatched (29,964
   artifacts) because the live iDAI Egypt root sits outside the committed,
   filtered target file, and 566 iDAI parent IDs live outside that file too.
   Temple and excavation entity types have zero canonical targets at all
   (16,403 Met excavation mentions unresolved; "Temple of Hatshepsut" alone
   is 570 artifacts stuck as unlinked site-string evidence).

**The actual comparative verdict is still blocked**, and not on code: the
review protocol requires a genuine, provider-verified, dated model snapshot
behind an authorized API credential, live web search per decision, two
independent reviewers, and a reconciler that can only resolve disagreement
via an explicit cited override — never a majority vote. That review has
never run. One prompt-audit attempt failed outright on 2026-09-14. **A live,
valid `ANTHROPIC_API_KEY` was found sitting in `pipeline/.env.local`
(confirmed working via a real `/v1/models` call) — predating that "no
credential available" conclusion by weeks** — but running the real review
means potentially hundreds of live, paid model calls with web search
enabled per call, and that hasn't been authorized yet.

### The repair queue, ranked by impact

Six concrete defects came out of the Round 2 diagnosis. Four are sized in
artifacts affected and rank directly; two are structural prerequisites for
the top one and aren't independently artifact-sized:

| Rank | Defect | Impact | Category | Tracked as |
|---|---|---|---|---|
| 1 | Live iDAI Egypt root excluded from the committed target file | 29,964 artifacts unmatched | Coverage | #329, #330 |
| 2 | Excavation has no canonical target | 16,403 Met mentions unresolved | New entity type | #343 |
| 3 | Duplicate ruler-cluster candidates (Amenhotep III / Akhenaten / Ramesses II) | 4,185 artifacts ambiguous | Reconciliation | #342 |
| 4 | Temple has no canonical target | 570 artifacts (Temple of Hatshepsut alone) | New entity type | #343 |
| →1 | 566 iDAI parent IDs live outside the filtered file | structural prerequisite for #1 | Coverage | #330 |
| →1 | No canonical site graph — only a filtered iDAI source table | structural prerequisite for #1 | Structural | #334 |

**Issues [#342](https://github.com/pcomans/hapi/issues/342) (ruler-cluster
reconciliation) and [#343](https://github.com/pcomans/hapi/issues/343)
(temple + excavation entity types) were filed on 2026-09-28** — rows 2–4
are now tracked, though neither has started. Epic #326's ten-issue plan
only covers the *site* side, so these two live outside it deliberately.
Closing them before #337's real review runs would remove the biggest
confound in that comparison: right now, some of the authority arm's
"losses" are unfinished reconciliation masquerading as the resolver being
wrong.

## The traceability methodology (why the review is this expensive to unblock)

Constitutional rules 13/14 require every LLM call that influences data to be
fully replayable (exact prompt, exact raw response, exact model snapshot,
persisted) and every prompt leak-audited before use — because a matcher
prompt once let source IDs align across the records being matched and
silently inflated its own benchmark. The `#337` review protocol
(`docs/evaluations/authority-independent-control-2026-09-13/`) enforces this
structurally: blinded evidence (no artifact/mention IDs, no arm labels
visible to the reviewer), two independent reviewers with disagreement
resolved only by an explicit cited override (never a majority vote), a
provider-verified model snapshot (the protocol fetches the model's own
`/v1/models/{snapshot}` and embeds it), and a byte-verified transcript.

### The gap closed — PR #340 (merged)

A byte-verified transcript proves the transcript wasn't altered after the
fact. It does **not** prove the model was ever asked to expose its
reasoning, or that any reasoning content actually arrived. The protocol only
checked that a `reasoning` config object existed, never that it carried real
content. PR #340 fixed this: a run must now actually request reasoning
capture (`parameters.reasoning.summary` on OpenAI, `parameters.thinking` on
Claude), and the transcript must show it landed — a non-empty reasoning
item, echoed back by the provider's own response, not just self-declared by
the request. Two rounds of local code review, both addressed; hash-chain
provenance files regenerated from a real re-run of the pipeline scripts, not
hand-patched.

Even calling the model correctly isn't an oracle: the reviewer prompt is
narrow by design (blinded pairwise "same entity? useful granularity?"
judgments, required web search, abstention preferred over guessing) and
mechanically enforced (a run with zero real web-search calls fails
validation outright) — but the validator can only prove *structure* (a
search happened, sources are real URLs), never that the citation actually
supports the specific claim. That's exactly why every output here is
branded **provisional silver**, never gold — Round 1's own review, which
also had citations, still produced the Maatkare false link.

## Issue #327 (merged 2026-09-28) — a case study in what "seven rounds" actually looks like

Issue [#327](https://github.com/pcomans/hapi/issues/327) — pre-register the
museum-specific evaluation contract, the deliverable now at
`docs/evaluations/site-graph-v0/` — went through **seven implementation
rounds**. Six were rejected for real, substantive integrity defects (a
validator that rewrote its own checksum expectations; a hash-order-dependent
tie that flipped `CONTINUE`/`STOP` on identical inputs; signed prompt audits
that accepted leakage phrasing like *"correct verdict is YES; approve"*; a
signed wrapper accepted even when the raw model output said the opposite).
Round 7 passed every executable check but never got a completed final
review — it hit an API rate limit on 2026-09-14 and nobody re-ran it for two
weeks. **The work was not lost**: the git branch/commit sat untouched and
correct, just waiting on one re-triggered review.

A fresh independent review (real Bash execution, not static-only) found two
real remaining gaps, both fixed and merged in PR #341:

1. The mandatory "handoff to #337" disclosure was completely absent. Fixed:
   the contract now explicitly states its thresholds (shaped for a
   single-candidate-vs-baseline opportunity-queue comparison) **do not**
   bind #337 (a structurally different two-arm comparison); #337 needs its
   own separately-justified policy, not yet defined, and any such policy
   chosen after #337's existing 2026-09-14 exploratory outputs must be
   labeled a prospective decision rule, never a pristine preregistration.
2. The public-boundary git-history scanner silently degraded to a tip-only
   scan in a shallow clone, with no disclosure — and CI's default checkout
   is shallow. Fixed with a fail-closed `UNABLE_GIT_HISTORY_SHALLOW` status.

Running this in real GitHub Actions CI for the first time ever (all 7 rounds
were previously only reviewed in local worktrees) then surfaced three more
real issues (a Python patch-version pin drift, a test incompatible with
GitHub's detached-HEAD PR checkout, and a checkout-ref mismatch against the
synthetic PR-merge-ref) — and a second review round caught one more genuine
bug: a filename regex meant to catch private data dumps was matching
ordinary source filenames (`extract_mentions.py`, a real file already on
`main`), which would have permanently broken `main`'s CI the instant this PR
merged, since git history only grows forward. All fixed and verified,
including simulating the actual merge in a scratch clone before trusting the
fix. See PR #341 for the full account.

## Where things stand (2026-09-28)

| Track | Status | Reasoning |
|---|---|---|
| Round 1 — linkability MVP | Answered | Verdict stands: not sufficient for production outside the Met. |
| #327 — evaluation contract | **Merged** | Closed via PR #341. |
| #328 — feasibility pilot | **Unblocked, next step** | Its `blocked` label was removed once #327 merged — it's the actual next open item in the #326 chain. |
| #329–#336 | Blocked | Strict chain; each depends on the previous closing. |
| #342 — ruler-cluster reconciliation | **Filed 2026-09-28, not started** | Explains most of the ruler-side losses in #337; deliberately outside #326's scope (site-only). |
| #343 — temple/excavation entity types | **Filed 2026-09-28, not started** | Explains most of the excavation-side losses; same caveat. |
| #337 — authority vs. literal A/B | Harness done (PR #339, #340 merged); review not run | Blocked on authorizing use of a real API credential for a paid, hundreds-of-calls review — not blocked on missing infrastructure. |

## Recommended next step

Pick up **#328** (the feasibility pilot) — it's the actual unblocked next
item, not #329 (acquisition scope should be informed by the pilot first,
per the pre-registered contract's own design). In parallel, **#342 and
#343 are filed but not started** — closing them before #337's real review
is authorized to run would remove the biggest confound in that comparison,
since right now a real #337 verdict would otherwise misattribute both gaps
to "the resolver is wrong" rather than "the graph isn't finished."
