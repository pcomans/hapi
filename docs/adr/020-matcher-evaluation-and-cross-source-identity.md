# ADR-020: Authority matcher evaluation & cross-source identity ground truth

## Status
Proposed

## Context

The authority claim graph (ADR-018) links per-source ruler records across sources
with `hapi:same_entity_as`. As soon as a matcher produces those links we need to
know how good they are — precision and recall — and that requires a *ground
truth*. A POC over Leprohon + Beckerath + Kitchen surfaced three findings that
this ADR records so they survive beyond any single experiment:

1. **"Coverage" is not recall.** The POC reported "88% of Beckerath rulers got a
   match." That number silently assumes every match is correct, so it is an upper
   bound inflated by every false positive — not recall. A concrete false positive
   was found: a transitive cluster merged **Pinudjem I** with **Menkheperre**
   (distinct father/son 21st-Dynasty Theban figures). Without a labelled gold set
   you cannot separate true positives from false positives, so you cannot compute
   precision or recall at all.

2. **Cross-source identity is absent from any single source — structurally.** This
   is not incidental: it is *why* ADR-018 calls cross-source identity "a
   substantive scholarly claim, not a string-equality coincidence." A source
   states its own rulers and, at most, its own *intra-source* identities. It never
   states "my row X is the same person as that other publication's row Y." So no
   single committed source can serve as the cross-source gold standard.

3. **Surface-string metrics are the wrong tool** (already decided in ADR-009:
   edit distance and token overlap are anti-correlated with identity for Egyptian
   royal names). They are excluded from the *acceptance* path here too.

## Decision

### 1. Intra-source identity is loaded as source-attributed `hapi:same_entity_as`

Where a source records its own internal same-person assertions — e.g. Kitchen's
`same_person_as` field, which links Kitchen rows that denote one king listed
twice (Pinudjem I `21H.03`↔`21H.04`; Tefnakht I `24.01`↔`24E.04`) — those are
loaded as `hapi:same_entity_as` claims **attributed to the source itself**
(human-documentary shape: `P14_carried_out_by` → the scholar, `P70i_is_documented_in`
→ the publication). They carry **no** `hapi:derived_by_run`: they are documentary,
not matcher-derived. This is the ADR-018 distinction made concrete — the presence
or absence of `P14` vs `hapi:derived_by_run` tells a reader whether an identity
link is *attested by a source* or *proposed by an algorithm*.

### 2. Cross-source ground truth requires adjudication or an external crosswalk

Because cross-source identity is in no single source (finding 2), the gold
standard for *cross-source* matching must come from one of:
- **human curatorial adjudication** (committed, cited — the ADR-018 / Rule-1 shape), or
- an **external identity crosswalk** — but a crosswalk qualifies as **gold only if
  it is independently curated and provenance-qualified** (each link carries its
  own cited basis). A crowd-aggregated crosswalk derived from the same scholarly
  sources is **silver, not gold** (see decision 5). **Wikidata specifically is
  silver**, never the committed gold set.

No source's own fields (including `same_person_as`) can fill this role — they are
the wrong axis (intra-source).

### 3. Evaluation uses precision / recall / B-cubed against a committed gold set

Two metric families are reported, and **must not be conflated** — collapsing them
recreates the "coverage is not recall" error this ADR exists to prevent:

- **End-to-end metrics (the headline).** Denominator is the **full gold set** of
  same-entity links among the evaluable entities. Every gold link the system does
  not surface counts against recall — *whether it was wrongly rejected, never
  proposed, or left unresolved by an abstention/escalation*. Abstentions are
  **not** removed from the denominator here: an unresolved gold link is a false
  negative (pairwise) / under-merge (B-cubed). This is the number that may be
  reported as the system's recall.
- **Selective-automation metrics (clearly labelled, never the headline recall).**
  Restricted to the links the system actually *decided* (abstentions excluded),
  measuring the quality of what was auto-resolved, reported **alongside an explicit
  abstention/escalation rate**. Useful for tuning the decide-vs-escalate threshold;
  misleading if presented as overall recall.

Both families use **pairwise** TP/FP/FN → P/R/F1 and, because identity is an
equivalence relation over clusters, **B-cubed** (or CEAF) P/R, which correctly
penalise *over-merge* (the Pinudjem/Menkheperre case) and *under-merge* (missed
cross-spelling). Metrics are reported **per stage** (exact matcher vs LLM pick vs
final clusters). The harness computes the end-to-end family by default.

### 4. Intra-source `same_person_as` is a source-consistency constraint (not gold)

Loaded intra-source identities (decision 1) are **source-faithfulness /
consistency evidence**, not gold truth — consistent with ADR-018, which treats
documentary claims as *attributed claims*, never automatic truth. Concretely they
give a **free under-merge consistency check**: any clustering that *separates* a
`same_person_as` pair contradicts the source and is wrong, with no adjudication or
external data needed. They do **not** establish that a merge is *correct*.

Note the open-world limit: Kitchen asserting `21H.03`==`21H.04` is positive
evidence those two rows corefer, but Kitchen's *silence* on Pinudjem vs
Menkheperre is **not** itself proof they differ (the field is not documented as
closed-world complete). The evidence that the Pinudjem/Menkheperre merge (finding
1) is wrong is external: they are separate Kitchen rows with no asserted identity
*and* carry distinct Wikidata QIDs — not the absence of a `same_person_as` link
alone.

### 5. Tiered ground-truth strategy (cost vs rigor)

1. **Silver (Wikidata)** — align rows to QIDs, treat same-QID as truth. Cheap,
   directional, and already catches the Pinudjem/Menkheperre merge (distinct QIDs).
2. **Silver + adjudicate disagreements** — human reviews only matcher↔Wikidata
   deltas; upgrades the contested cases at a fraction of full-labelling cost.
3. **Committed gold** — scholar-curated, per-link provenance; required only for
   authority-grade / citable numbers (Constitutional rule 1).

**Wikidata is a silver standard, never gold.** It is (a) not independent — it is
derived from Wikipedia and from the same scholarly sources (Beckerath, Leprohon,
Kitchen), so grading against it risks measuring agreement-with-Wikidata, and (b)
least reliable on exactly the contested identities (Aha/Menes, Smenkhkare/
Neferneferuaten, Pinudjem/Menkheperre) that drive matcher error.

## Consequences

- **Never report coverage as recall.** Coverage is an upper bound; real precision/
  recall require a gold set.
- **Transitive clustering needs a contradictory-merge guard.** Connected components
  over pairwise links can conflate distinct people; clustering must detect/block
  contradictory merges or route them to escalation before clusters become
  authority data.
- **Intra-source identity must be loaded** (not discarded) so its consistency
  constraints and provenance distinction are available.
- The matcher-evaluation harness (`evaluate.py`) and any committed gold set are a
  follow-up; this ADR fixes the method and the ground-truth semantics.

## Relationship to other ADRs
- **ADR-009** (fuzzy review queue): excludes surface-string metrics from acceptance;
  this ADR builds the evaluation around that and the ADR-018 graph.
- **ADR-018** (claim graph): defines the `hapi:same_entity_as` shapes (source-
  attributed vs matcher-derived) this ADR's intra-source loading and evaluation
  rely on.
