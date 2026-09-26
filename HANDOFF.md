# Handoff: claim-graph / authority-layer pressure test

_Snapshot: 2026-09-26._

## Origin

On 2026-08-28, after a Falconer lookup on the Hapi project, the ask was:
we've built an authority layer and a matching layer, but we don't know if
either actually helps match museum records — investigate, pressure-test what
exists, and decide what to build next. That produced two rounds of work,
tracked in epic [#326](https://github.com/pcomans/hapi/issues/326).

## Round 1 (2026-08-27/28) — linkability MVP: **answered**

Committed at `docs/evaluations/hapi-linkability-mvp-2026-08-28/`. Ran a real
benchmark over the full 36,245-artifact corpus (Met, Brooklyn, Harvard).

**Result: the current authority layer is not sufficiently linkable for
production, all-three-museum enrichment.**

- Only 47% of artifacts (17,063/36,245) link to any authority node at all —
  Met 56%, Harvard 37%, Brooklyn 16%.
- Ruler matching barely works outside the Met: Brooklyn linked only 6
  artifacts by ruler, Harvard 3, vs. Met's 3,879.
- Cross-museum connectivity is dominated by broad nodes — `Thebes` alone
  touches 75% of all cross-museum-discoverable artifacts.
- Temple and excavation entities have zero canonical authority targets —
  hard blocked, not just weak.
- A frozen 46-case provisional review found 2 outright false links (e.g. a
  Brooklyn "Maatkare" wrongly linked to Hatshepsut instead of a distinct,
  later princess of the same name).

**Decision:** don't scale up the authority layer yet. At most ship a narrow
shadow-mode prototype (exact site aliases + Met Porter–Moss tomb codes);
fix ruler-cluster reconciliation and build a real canonical site graph
first. This became epic #326 with a 10-issue plan (#327–336, plus #337).

## Round 2 (2026-09-13/15) — authority-vs-literal A/B: **blocked**

Issue [#337](https://github.com/pcomans/hapi/issues/337) asked the sharper
question: does the authority-assisted resolver actually beat a plain
literal-string-matching baseline? [PR #339](https://github.com/pcomans/hapi/pull/339)
(merged) built the full comparison harness at
`docs/evaluations/authority-independent-control-2026-09-13/` — but stopped
short of a verdict:

> Review status: NOT_RUN. Quality conclusion: NOT_AVAILABLE.
> Execution readiness: BLOCKED.

**Why:** the review/adjudication stage requires a pinned, provider-documented
LLM snapshot behind an authorized API key. Neither is available in this
environment — no `ANTHROPIC_API_KEY`/`apiKeyHelper`, no OpenAI key, no dated
snapshot identifier exposed for the model the protocol names
(`gpt-5.6-sol`). One prompt-audit attempt on 2026-09-14 failed outright
before any reviewer ran.

The unreviewed mechanics are suggestive but explicitly not a quality
verdict: the authority arm's shared-record counts are far lower than the
literal arm's on every museum (e.g. Met literal 27,330 shared records vs.
authority arm 14,411), consistent with the literal baseline catching a lot
of broad/likely-junk matches that the authority resolver correctly
abstains from.

## Current state (2026-09-26)

- Issues #326–337 are all still **open** on GitHub; most are tagged
  `blocked`. Nothing has shipped past PR #339.
- The blocker is concrete: a real, pinned LLM reviewer credential needs to
  be wired into this environment before the pressure test can produce an
  actual precision/recall verdict.
- Until that's cleared, the honest answer to "does the authority layer
  help?" is still the Round 1 finding: **probably not yet** — ruler
  matching outside the Met and site specificity remain the two biggest
  gaps.

## Next steps (pick one)

1. Unblock the review step — provision a pinned model snapshot + authorized
   API credential (Anthropic or OpenAI) in this environment so #337's
   review protocol can actually run.
2. Pick up [#327](https://github.com/pcomans/hapi/issues/327) (pre-register
   the museum-specific evaluation contract) — it's the one issue in the
   #326 plan that isn't currently marked `blocked`.
