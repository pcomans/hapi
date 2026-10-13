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
   edit distance and token overlap are *uncorrelated* with identity for Egyptian
   royal names — and sometimes inverted, e.g. "Thutmose III" vs "Tuthmosis").
   They are excluded from the *acceptance* path here too.

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

**The gold set is a closed-world evaluation fixture, not a loose list of positive
links.** It is defined over a *named, enumerated entity universe* (the specific
records in scope) as a set of *adjudicated equivalence classes*. Within that
universe every pair is therefore decided: **gold-positive** iff both records are
in the same class (the gold positives are the transitive closure of the classes),
**gold-negative** otherwise. Records that are unknown or unadjudicated are
**excluded from the universe entirely** (never scored) — so a predicted pair is
never counted as a false positive merely for being unadjudicated, and B-cubed's
singleton/negative side is well-defined (an unmatched in-universe record is its
own singleton class). **Universe-boundary scoring is explicit:** the matcher runs
on the full corpus, so predicted clusters are *projected onto the universe* before
scoring — a predicted link straddling the boundary (one in-universe, one
out-of-universe record) is not scored. The documented blind spot of this projection
is that an over-merge into an *out-of-universe* homonym is invisible to the fixture
(documented, not silent — it is a reason to widen the universe, not to score
differently). The Wikidata *silver* fixture realises this with the
universe = records that align to a QID and the classes = QID groups; the committed
*gold* fixture realises it as human-adjudicated equivalence classes, with
per-class provenance, over an enumerated record set.

**Universe composition is itself a reviewed artifact, not a by-product of candidate
generation.** If the universe is assembled only from records that name-similarity
already links, it under-tests exactly the adversarial cases that drive real matcher
error, and a high B-cubed precision becomes an artifact of a friendly universe
rather than a property of the matcher. The gold universe must therefore deliberately
seed the known **homonym traps as *distinct* classes** — Egyptian royal naming
reuses prenomina across distant individuals. The seed list **must be generated by a
committed query over the source files**, not hand-recalled (Rule 1): the Menkheperre
count below was itself revised from "three-way" only after querying the committed
data, which is exactly the failure mode this paragraph guards against. Verifying
against the committed sources, the traps include at minimum: **Menkheperre** — **at
least three solidly distinct bearers** (Thutmose III (Dyn 18); the Dynasty-21 High
Priest Menkheperre; and **Necho I** (Dyn 24/26, prenomen `Menkheperre` in Kitchen /
`Men kheper Ra` in pharaoh-se)) **and two further contested bearers** (**Ini**, Dyn 22,
whom Beckerath gives `Men-cheper-rê (?)` — flagged uncertain; and **Piye**, to whom
Leprohon assigns Menkheperre while Kitchen lists Piankhy's prenomens as
`Usimare`/`Sneferre` and does not record Menkheperre for him — the sources do not agree
he carried it) — the contestation is itself part of what the universe must represent.
**The two contested attributions are not independent: both hinge on one object, Stela
Louvre C100** — Leprohon's `men kheper ra` for Piye is a variant throne name from that
stela, whose attribution Jansen-Winkeln gives "with some hesitation" to King Iny, per
Leprohon's own source note. **When contested cases share an evidentiary basis, the gold
set's per-class provenance must cite the shared object and document the classes as
linked** — classes that stand or fall together must not be scoreable as independent
successes, or a matcher can pass one and fail the other with nobody noticing they rest
on the same disputed reading. Louvre C100 is the worked example; **Nebmaatre**
(Amenhotep III / Ramesses VI, plus a standalone king *Nebmaatre* attested in the
committed data — at least three-way); the **Usermaatre** cluster (Ramesses II plus
several TIP kings); the **Sekhemre-\*** compounds (Dynasty 13/16/17); and same-name
father/son, grandfather/grandson, and predecessor/successor runs (Pinedjem I/II —
grandfather/grandson via Menkheperre, *not* father/son — Osorkon I–IV, Takelot I–III,
Sobekhotep I–VIII); and — a structurally distinct trap *kind* — **traditional-name vs
archaeological-name identity**: Beckerath opens Dynasty 1 with a row named `Menes`
(the Manethonian tradition-name, sequence 1), while Leprohon carries `Narmer` and
`Aha` as *separate* rows, and Leprohon's own Narmer source note records the
century-old dispute over which archaeological king Menes is ("Narmer is possibly the
King Menes … although some scholars equate the Horus Aha with Menes"). Verified in
the committed data. Unlike the homonym traps (one prenomen, many kings), this is one
tradition-name contested between two archaeological kings, and there is no
gold-positive answer: **the fixture must assert that the matcher escalates Beckerath's
Menes rather than linking it to either candidate** — the canonical case where the
correct output is a refusal, exercising the doubt → escalation policy of decision 6
end-to-end. **Symmetrically, the universe must also seed known hard
*positives*** — cross-convention / cross-numeral true matches (Leprohon "Ahmose III"
↔ Beckerath "Amosis II."; "Tuthmosis III." ↔ "Thutmose III"; dynasty-divergent TIP
pairs such as Takelot III) — or end-to-end *recall* is measured on easy links and
inflated the same way coverage inflated recall.

Two metric families are reported, and **must not be conflated** — collapsing them
recreates the "coverage is not recall" error this ADR exists to prevent:

- **End-to-end metrics (the headline).** Denominator is **all gold-positive pairs**
  (the transitive closure of the gold equivalence classes) over the closed
  universe. Every gold link the system does
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
cross-spelling). Metrics are reported **per decision stage**; the *stage taxonomy*
is owned by the matcher architecture (#306) — e.g. deterministic accepts vs
escalation-resolved vs final clusters — not fixed here. The harness computes the
end-to-end family by default.

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
2. **Silver + adjudicate disagreements** — human reviews of only the matcher↔Wikidata
   deltas; upgrades the contested cases at a fraction of full-labelling cost. Output
   is **silver-adjudicated, still not gold**: cases where matcher *and* Wikidata agree
   but are both wrong are never surfaced for review — and correlated error is likely
   precisely because of the non-independence noted in (a) below.
3. **Committed gold** — scholar-curated **equivalence classes over an enumerated
   record universe** (a closed-world fixture per decision 3), with per-class
   provenance; required only for authority-grade / citable numbers (Rule 1).

**Wikidata is a silver standard, never gold.** It is (a) not independent — it is
derived from Wikipedia and from the same scholarly sources (Beckerath, Leprohon,
Kitchen), so grading against it risks measuring agreement-with-Wikidata, and (b)
least reliable on exactly the contested identities (Aha/Menes, Smenkhkare/
Neferneferuaten, Pinudjem/Menkheperre) that drive matcher error.

### 6. Matching is precision-first: a missing merge beats a false merge

**For cross-source matching, a false merge (conflating two distinct rulers) is
worse than a missed merge (failing to link two records that are the same).** The
matcher optimises **precision**; recall shortfalls are acceptable and are
expressed as **escalations, not guesses.**

Rationale: a false merge corrupts authority data — a wrong identity propagates to
every artifact, date, and relationship attached to the cluster, and is hard to
detect downstream (per ADR-018, reconciled data is sacred; a wrong identity claim
is slop). A missed merge is visible (two records simply stay separate) and
recoverable later. The asymmetry is real, so the policy is asymmetric.

Consequences for the matcher — **policy and structured constraints, not
implementation.** The matcher *architecture* — candidate generation / blocking,
the decision rule (per-pair resolution vs a global reject-by-default solver), and
whether a model sits *in* or *out of* the decision path — is specified separately
and is under active reconsideration: see issue
[#306](https://github.com/pcomans/hapi/issues/306) ("Matcher rearchitecture: cross-
source ruler identity as a cited claim-graph alignment, not per-pair LLM picking").
This ADR fixes the policy and the constraints below; it does **not** settle the
resolution mechanism (the POC's `poc.resolve_matches` is one implementation, not
the ratified design).
- **Corroborate-or-escalate acceptance.** A matcher-derived `hapi:same_entity_as`
  is auto-approved only when a *structured* signal corroborates the name judgment;
  name agreement alone is **not** sufficient to accept — it routes to escalation.
  The corroborator is **prenomen (throne-name) match as the *primary* signal** — or,
  for the **earliest dynasties**, where the Re-formed prenomen has not yet stabilised
  and the cartouche-name fields are absent or convention-divergent in the sources
  (Leprohon records *no* throne name for Narmer or for Djoser; Den's nsw-bity name
  `Khasety` is filed inconsistently across sources), **Horus-name match** — the
  primary identifier of that era — plays the corroborating role, with dynasty /
  reign-overlap as secondary support only. (This is a narrow early-dynastic carve-out,
  not a blanket "Dyn 0–4" rule: by the Old Kingdom the throne-name fields are populated
  and discriminating — Leprohon gives the Dynasty-4 kings `senefer wi`, `khu.ef wi`,
  `kha.ef ra`, `men kau ra` — so the prenomen predicate carries from there.) Shared dynasty and
  matching regnal numeral are the two *weakest* signals for exactly these sources
  and must not be load-bearing: TIP dynasty assignments disagree **in the committed
  data** (Takelot III is Dynasty 22 in Beckerath but Dynasty 23 in Kitchen), so a
  predicate requiring dynasty agreement systematically routes true TIP matches to
  escalation; and regnal numerals are convention-relative (Ryholt renumbered the
  Dynasty-13 Sobekhoteps against Beckerath, so a matching numeral on two
  "Sobekhotep II" rows from different conventions can be *anti*-corroborating, while
  reign-overlap-AND-dynasty actively endorses the adjacent-homonym / co-regent
  false-positive profile the guard exists to catch). The prenomen
  (`khnum ib ra` uniquely fixes Amasis; prenomen compounds are the only stable
  discriminator across the Sobekhoteps) carries the identity. Critically, this
  prenomen/Horus match must run on a **deterministically normalized** form: the
  committed sources spell one throne name `Chnem-ib-rê` (Beckerath) vs `khnum ib ra`
  (Leprohon), so without a committed cross-convention normalization table the
  promoted "structured signal" silently inherits the very surface-string-matching
  problem (ADR-009) it was meant to escape. Two further constraints on the
  match predicate are **fixed here as policy** — both forced by the committed
  data: (i) **the normalization table and the matcher bind to the structured
  titulary fields** (`prenomens[]`, `throne_names[]` and their per-variant
  entries), never to scalar display fields — Kitchen's scalar `prenomen` for
  Piankhy is the literal string `"Usimare, then Sneferre"`, a rendering for
  human readers, not a name; a matcher fed display fields compares garbage.
  (ii) **The prenomen/Horus match is set-valued**: two records corroborate when
  their normalized *attested-variant sets intersect*, never by comparing one
  designated name per record — kings hold multiple prenomina over a lifetime
  (Piankhy carries `Usimare` then `Sneferre` in Kitchen, plus a variant
  `men kheper ra` in Leprohon), so a scalar comparator would *anti*-corroborate
  true matches and silently depress recall through the escalation path.
  *(Spec follow-up: that normalization
  table, plus the prenomen/Horus-match predicate and a committed homonym exception
  list — see decision 3 — for the cases where one prenomen is shared across distinct
  kings: Menkheperre, Nebmaatre, the Usermaatre cluster, the Sekhemre-\* compounds.
  Scoped by dynasty in the 2026-10-10 amendment, item 5.)*
- **Structured cannot-link / escalation constraints.** Identity decisions must
  honour deterministic structured discriminators (never surface-string similarity,
  ADR-009). *How* these are applied — as guards over a pairwise-edge graph (the
  POC's approach) or as first-class constraints in a global, reject-by-default
  solver — is the architecture question deferred to #306; the constraints
  themselves are policy:
  - **Same-source distinctness:** two rows from one source are presumptively
    different people unless the source links them (documentary `same_person_as`) or
    they are stage-suffix phase siblings of one record.
  - *(Superseded for large gaps by the 2026-10-10 amendment, item 1.)* **Reign-span disjointness** is a discriminator **only within a single
    chronological framework** (a source never dates one person to two disjoint
    spans); cross-framework it must **escalate, not block**, on a period-scaled
    tolerance, because absolute chronology is framework-relative and the divergence
    grows with antiquity (Beckerath opens Dynasty 1 ~3032 BCE vs Hornung–Krauss–
    Warburton ~2900 — a ~century offset on the same kings).
  - *(Refined by the 2026-10-10 amendment, item 6.)* **Uniqueness:** if two *distinct* rulers from one source both claim a single
    target (and aren't the same person), the clash **escalates** — never resolved by
    an order-dependent "incumbent" (catches the Ninetjer/Nebre → Kaiëchós error).
  - **Regnal-number divergence escalates, never blocks.** Numbering is
    convention-relative and **cuts both ways**: a numeral can *mismatch* on one king
    (Leprohon's `"Ahmose III"` (`leprohon-26.05`) = Beckerath's `"Amosis II."` = the
    Dynasty 26 king Amasis, throne name Khnemibre) and *match* on two different kings
    (the Dynasty-13 Sobekhoteps under Ryholt vs Beckerath) — so a matching numeral is
    not safe as accepting corroboration either.
- **Doubt → escalation, never a guess.** Held-apart conflicts, uniqueness clashes,
  regnal mismatches, and uncorroborated picks go to the human/curator queue via the
  verdict/supersession path; they do **not** become accepted links and are **not**
  silently dropped. *(Follow-up: the escalation-queue contract.)*
- **A name-only match is confirmed by external documented evidence, never by a model
  assertion.** When two records share only a name and have no prenomen/Horus corroborator,
  the pair escalates (above) and may be promoted to an accepted `hapi:same_entity_as`
  **only** by a curator attaching external, citable evidence for the identification — a
  published scholarly equation (e.g. the Manetho Hellenised-name crosswalk behind
  `Usaphais` = Den, `Semempses` = Semerkhet, `Sethenes` = Senedj), captured as a source on
  disk with its citation. A model stating "these are the same" from its own memory is **not
  admissible**: per Rule 1, "the model knows" is not a source, and a name-only approval is
  traceable to nothing in the committed records. The claim-graph implementation therefore
  escalates every name-only candidate **deterministically, without spending a reviewer call
  on it** — a live reviewer's "approved" on a name-only pair could rest only on unsourced
  world knowledge, so it is never solicited. Confirmation requires a documented source and a
  web-search / literature check by a human, then a cited override.
- **Ground every judgment in the full record, not the display name** — dynasty,
  reign span, prenomen/throne names, full titulary, source. Whether a model-assisted
  judgment sits *in* the decision path or only drafts cited evidence *behind a
  deterministic gate* is a matcher-architecture question (#306); either way the
  judgment must rest on the structured record, never the name alone. *(The POC's
  constraint-narrowed pick passes only the display name — a known limitation that
  the #306 redesign closes by construction.)*
- **Reasoning capture (Constitutional Rule 13).** Any model-assisted step — wherever
  #306 places it, *in* the decision path or *behind* a deterministic gate — must
  persist its complete interaction (model id as requested and as served with any build
  information the provider reports, parameters, the exact prompt/input, the full raw
  response, the thinking transcript, and every source used at runtime, verbatim), linked
  to the decision it produced. This policy holds regardless of the architecture #306
  settles on. An LLM call cannot be re-executed to reproduce a decision — not with a dated
  model id, not with web search in the loop — so what must be re-readable is the record:
  the thinking and the sources show what the model saw and why it decided (Rule 1: "the
  model knows" is not a source). *(Revised 2026-10-11 with Rule 13; the earlier "dated
  snapshot" requirement is withdrawn.)*
- **Metrics:** precision is the primary reported number; recall is secondary and is
  always reported with the abstention/escalation rate (per decision 3).

## Consequences

- **Never report coverage as recall.** Coverage is an upper bound; real precision/
  recall require a gold set.
- **Pairwise links must never become unsourced merges.** However identity
  decisions are computed, two distinct people must not be silently conflated;
  contradictions are surfaced and escalated before any cluster becomes authority
  data. (Whether this is enforced as a guard over a pairwise-edge graph or as
  constraints inside a global solver is the matcher-architecture question — #306.)
- **Intra-source identity must be loaded** (not discarded) so its consistency
  constraints and provenance distinction are available.
- The evaluation harness (its location and entry-point owned by #306) and any
  committed gold set are a follow-up; this ADR fixes the evaluation method, the
  ground-truth semantics, and the matching policy — **not** the matcher architecture,
  which is #306.

## Relationship to other ADRs
- **ADR-009** (fuzzy review queue): excludes surface-string metrics from acceptance;
  this ADR builds the evaluation around that and the ADR-018 graph.
- **ADR-018** (claim graph): defines the `hapi:same_entity_as` shapes (source-
  attributed vs matcher-derived) this ADR's intra-source loading and evaluation
  rely on. This ADR also **extends** ADR-018's verdict chain to **human/curator
  verdicts** (the human-documentary `P14_carried_out_by` shape) via the §6
  escalation queue, superseding ADR-018's "the design has no human-review step" note:
  escalated matches are resolved by a cited curator verdict, not silently dropped.
- **Issue [#306](https://github.com/pcomans/hapi/issues/306)** (matcher
  rearchitecture): owns the matcher *implementation* — candidate generation /
  blocking, the decision rule, and the LLM's placement — which this ADR deliberately
  leaves open. ADR-020 is the evaluation + ground-truth + matching-policy record;
  #306 is the design. A reader should not take the POC's per-pair resolution /
  connected-components mechanics as the settled architecture.

## Amendment 2026-10-10 — ruler-cluster reconciliation (#342)

Issue [#342](https://github.com/pcomans/hapi/issues/342) found the three highest-frequency
ambiguous ruler clusters (Amenhotep III, Akhenaten, Ramesses II; ~4,200 museum artifacts)
abstaining for reasons the committed data itself resolves. The project owner decided the
following on 2026-10-10; review corrections are folded in (2026-10-11). Each rule is
implemented in `pipeline/authority/claimgraph/` and pinned by
`pipeline/tests/test_claimgraph_ruler_reconciliation.py`.

1. **Era gate — supersedes "Reign-span disjointness … must escalate, not block" for large
   gaps.** A candidate pair is **rejected** by a committed deterministic verdict rule,
   before any LLM call, when (a) the reign starts differ by at least 200 years AND by more
   than the period-scaled cross-chronology tolerance (`150 + |BCE|/20` years — the same
   tolerance as the far-apart escalation hint, so there is one chronology rule), or (b)
   the dynasty numbers are more than one apart and the two dynasties do not fall in the
   same *contested numbering band*: Dynasties 6–10 (von Beckerath's unplaced kings of the
   Dyn 8 era — Handbuch 1999, 70–71, a–h — are Leprohon's "Dynasty 8a" but filed by
   pharaoh.se under Dynasty 10, pharaoh.se's own placement rather than a scholarly
   renumbering; Ryholt derives the Turin list's Neith-iqerti, Leprohon's Dyn 6 entry, from
   Netjerkare Siptah, pharaoh.se's Dyn 8), 13–17 (Ryholt vs Beckerath), and 21–26 (Takelot
   III Dyn 22 Beckerath / Dyn 23 Kitchen; Necho I Dyn 24 Kitchen / Dyn 26 Leprohon). Absent
   era evidence never rejects. Evidence: no link approved before the rebuild fails the
   gate, and **every pair the gate rejects is listed** in
   `docs/evaluations/ruler-cluster-reconciliation-342/results/era-rejected.json` (all 448,
   test-pinned), each tagged with the earlier graph's verdict for it, and reviewed per
   `era-rejected-review.md`. The first version of the gate omitted the Dyn 6–10 band and
   rejected seven genuine same-king pairs (Wadjkare, Sekhemkare, Imhotep, Hotep, Khui, Isu,
   Iytjenu); review caught it before merge. (The eighth king of that series, Leprohon's
   Iti / pharaoh.se's Ity, is never a candidate: `iti` and `ity` do not match.)
2. **Sources' own identity statements join clusters** (stage-suffix phase siblings were
   already policy under "Same-source distinctness"; now loaded). Leprohon rows with
   `stage_suffix` set and `printed_under` null are one person per the source README's
   reading rule (2) — Amenhotep IV / Akhenaten, Mentuhotep II a–c, Amenemhat I a–b,
   Thutmose III a–b — and, with Kitchen's `same_person_as` pairs (decision 1), contribute
   `intra_source` edges to clusters. The Chapter-X consort sub-entries are never linked.
3. **Added epithets are not names.** An entry the source records as an epithet *added to*
   a name is published under its own claim predicate (`hapi:prenomen_epithet`,
   `hapi:nomen_epithet`, `hapi:horus_name_epithet`; ADR-018 manifest), shown to the
   reviewer on its own line, and never matches on its own. For matching only, the
   source's primary throne name is also matched together with each added throne-name
   epithet, as the compound cartouche (Leprohon's `wsr mꜣꜥt rꜥ` + `stp.n rꜥ` = the
   *Usermaatre-setepenre* Beckerath and pharaoh.se print). Variant throne names and birth
   names are never compounded: an epithet is not attested with every variant, and birth
   name + epithet can spell another king's nomen (Amenhotep II + ḥqꜣ wꜣst).
4. **Fragmentary names never corroborate.** A throne or Horus name in which the source
   marks a gap (`///`, `//`, `...`, `[..]`, `[...]`) is excluded from the corroborating
   keys; such pairs stay name-only and escalate. With the gap stripped, `Senefer[...]re`
   would key to Piye's complete Sneferre.
5. **The homonym exception list is scoped by dynasty.** A shared reused throne name is
   *unambiguous for a pair* when both records carry the same dynasty, outside the bands
   where a shared dynasty number is unreliable — 8–10 (Leprohon files all Herakleopolitan
   kings as Dyn 9 where pharaoh.se splits them between 9 and 10, and pharaoh.se's Dyn 10
   also holds the Dyn 8-era unplaced kings), 13–17 and 21–26 — and no other
   *person* from either source bears that name in that dynasty (a source's own stage rows
   are one bearer; a bearer with no dynasty does not block, because its own pairs stay
   trapped). The pair stops being forced to escalate when ANY shared reused name is
   unambiguous for it — Thutmose III's full Menkheperre is, though the vowel-less skeleton
   it shares with Thutmose IV's Menkheperure is not — and is still judged by the reviewer.
   *(Refines decision 3's homonym exception list above.)*
6. **A uniqueness clash resolves to the sole same-dynasty target** when exactly one
   competing target shares the record's dynasty outside the bands of item 5 and every
   other target has a known, different dynasty; otherwise the whole clash escalates as
   before. Two rows the other source declares one person are one target, not a clash.
7. **Model-decided identity.** Contrary to #306's "no LLM in the decision path", the
   reviewer model decides corroborated pairs, and the deterministic guards above still
   override it. The reviewer for the #342 rebuild is DeepSeek V4.1 Flash through the
   Vercel AI Gateway, with maximum reasoning effort *requested* (the provider does not
   report the effort it applied), pinned to DeepSeek's own endpoint with fallback disabled;
   every response is checked to have been served there and is persisted in full,
   reasoning included (Rule 13). The model id is an alias with **no dated snapshot**; each
   interaction records DeepSeek's reported serving build (`systemFingerprint`) with it, and
   a committed test requires one build per run. *(2026-10-11: no revisit is needed — Rule
   13 no longer asks for a dated snapshot, since no LLM call can be re-executed to
   reproduce a decision; the persisted thinking and inputs are the record.)* *(Added
   2026-10-11:)* Because such a run is not "completely determined by its digital input",
   it is typed `hapi:LLMReviewerRun` (CRMdig D7), not D10 (ADR-018 amendment 2026-10-11).

## Amendment 2026-10-12 — working off the escalation queue

The #337 re-registration lost correct ruler matches that plain text makes (Apries,
Userkaf, Psusennes I) because the graph kept one king's records from different sources
apart. The audit in `docs/evaluations/ruler-escalation-queue/` found 974 parked pairs
against 354 approved links, 735 of them `name_only` and never reviewed: 302 of the 1,159
ruler records carry no throne or Horus name at all (Kitchen 34 of 60), so the
corroborate-or-escalate rule of decision 6 could never accept them, and nothing ever
worked the queue off. The project owner approved working it off on 2026-10-12. Each rule
below only sends a pair to the reviewer; none approves by itself, and the deterministic
policy (`--deterministic`) still escalates every pair the rules newly reach.

1. **Same name in the same dynasty goes to the reviewer** (`name_dynasty`), when the two
   records share a king name, carry the same dynasty number and no conflicting regnal
   number (one missing is not a conflict; regnal numbers are read from the display name,
   including Leprohon's own "(I)" numbering and stage-suffixed "III (a)"). *Refines
   decision 6*, which made shared dynasty and regnal numeral non-load-bearing: they still
   never carry a merge alone. When a record has no throne and no Horus name, approval is
   **enforced in code** (`matcher.king_name_route_corroborated`, applied in `verdicts.finalize`): both reign windows
   known and overlapping by at least half the shorter, and the same regnal number or none
   on both; any other approval is downgraded to an escalation, and a pair blocked this way
   (`Candidate.king_name_route_blocked`) is never a rival in a uniqueness clash. Excluded in Dynasties
   13–17, where a matching regnal number on a shared name can name different kings
   (Ryholt's Sobekhotep renumbering). The same can happen later: Beckerath's Schoschenq IV
   (Usermaatre) and pharaoh.se's Shoshenq IV (Hedjkheperre, whose Shoshenq VI was
   "previously known as Shoshenq IV") are different Dyn 22 kings, and the window rule
   does not separate them: Beckerath gives −800..−790, pharaoh.se −798..−785, the same
   numeral. Both records carry throne names, so the reviewer compared those and rejected
   the pair. For a record without titulary in such a case the reviewer is the only
   defence. Excluding Dyn 21–24 from the basis was measured and not adopted: it costs
   312 resolved mentions, Psusennes I alone 309 (`results/alternative-exclude-dyn-21-24/`).
   Refusing a name whose regnal-number set differs between sources was not measured; it
   would block Psusennes I the same way, since Beckerath also lists an unnumbered High
   Priest "Psusennes" and Kitchen only I. The project owner accepted the risk on 2026-10-12: two kings with the
   same name, number, dynasty and reign may be merged, which only more data can resolve;
   to be revisited if it occurs. A disagreeing
   dynasty number (the Third Intermediate Period cases of decision 6) withholds the
   basis, which can only miss a match, never make a false one.
2. **A Horus name corroborates beyond Dynasty 3 only with a shared king name.** Later
   Horus names are widely reused (Kanakht-meryre: Thutmose III, Sety I, Ramesses II,
   Sety II), so a shared Horus name alone stays `name_only`; together with the same king
   name and no conflicting regnal number it goes to the reviewer (Ramesses III's
   Kanakht-aanesyt; never Sety I against Sety II). In Dyn 0–3 the
   early-dynastic carve-out of decision 6 is unchanged.
3. **A homonym-list key that is only a skeleton collision does not trap.** When no listed
   key is shared as spelled (each is a collision of the vowel-less skeleton) and the pair
   shares a throne name as spelled that is not listed: Thutmose IV's Menkheperure folds
   to Thutmose III's listed Menkheperre. A listed name shared in full stays trapped, even
   beside an unlisted compound of it (Shabaka's Neferkare and Neferkare-meryamun).
   *Refines amendment 2026-10-10, item 5.*
4. **A uniqueness clash resolves to the target matched through both primary throne
   names** when exactly one competing target is, and every other matches only through a
   secondary variant or through no throne name at all (a Horus or king name), with no
   rival of unknown dynasty (a source's first-listed throne name is its primary form):
   pharaoh.se's Amenhotep II lists the variant Aakheperuenre, whose skeleton is Thutmose
   II's Aakheperenre. *Refines amendment 2026-10-10, item 6.*

5. **A rejection cannot rest on a reading the source marks uncertain.** When the reviewer
   rejects a pair and either record carries a name its source flags as an uncertain
   reading (Ryholt's `is_uncertain_attribution`, e.g. 17.7 "Siamun (?)"), a code guard
   escalates it instead, so the pair stays in the queue rather than being recorded as two
   kings. Like the other guards it only downgrades; the reviewer is not told. Ryholt is
   the only source with a typed flag; Beckerath, Kitchen, Leprohon and pharaoh.se print "(?)" in
   name strings without one, and their loaders declare an empty set until the flag is
   added upstream (not sniffed from strings in the matcher).

The live reviewer may approve a `name_dynasty` pair while the deterministic policy
escalates it; that is intended (decision 7 of the 2026-10-10 amendment: the reviewer
decides, the guards only downgrade). An edge's `basis` records why the matcher sent the
pair to the reviewer, not which policy route the reviewer approved it by: `name_dynasty`
means the pair shares no throne or Horus name *as normalised*, and the records may still
carry throne names the normaliser does not equate (Beckerath's German transcriptions,
"User-maat-rê" against "Usimare"). The reviewer weighs those under its throne-name route.
Its king-name-only route applies only when at least one record has no throne and no Horus
name at all; the code guard of item 1 enforces the window and numeral conditions there,
stricter than the prompt's "allowing a few decades' offset", so an approval resting on a
model's knowledge rather than the record fields is downgraded (Rule 1). A pair whose
regnal numeral appears in one record only is therefore never approved by that route: a
missed merge by policy, not a recall loss of the reviewer. On
the throne-name route an offset or unknown window, or a numeral differing only by
numbering scheme, does not by itself escalate (sources follow different chronologies);
the first policy text applied these checks to every route and lost 97 correct links,
which is why the routes are now separate. The policy text was leak-audited before each
rebuild (`docs/evaluations/ruler-escalation-queue/prompt-audit-2026-10-12.md`).
Every merge the rebuild adds is listed for review, as in #342. A `name_only` pair is
escalated ahead of the resumable verdict cache, so a verdict reviewed under an earlier
matcher that gave the pair a basis cannot survive the basis being withdrawn.
