# ADR-018: Authority Layer as Source-Attributed Claim Graph

## Status
Proposed

## Context

The authority layer (rulers, dynasties, periods, sites, and their interrelationships) currently consists of per-source `reconciled.jsonl` files at `pipeline/pipeline/authority/sources/<source>/reconciled.jsonl`, each row representing one ruler / queen / tomb / site as recorded by that source. ADR-012 commits the source list (Leprohon, Beckerath, Dodson-Hilton, Porter-Moss, Kitchen, pharaoh.se); the Phase 0 playbook produces one `reconciled.jsonl` per source via a 3-agent extraction + reconciliation pipeline. No consolidated cross-source layer exists yet — the design of that layer is the subject of this ADR.

Four problems with the current shape have surfaced as the layer approaches completion:

1. **The naive path to a consolidated authority silently picks winners across sources.** Phase 0 reconciliation today is per-source: each `reconciled.jsonl` resolves *intra-source* agent disagreement per Rule 2 (unanimity, majority, explicit override in `tie-break-overrides.json`, or documented deterministic policy). The cross-source consolidation step does not exist yet. The straightforward implementation — load all the `reconciled.jsonl` files, key by ruler, collapse to one row per ruler — would force a choice when Leprohon and Dodson-Hilton disagree on a reign date. One would be dropped, silently, with no Rule-2 path: no agent vote applies across sources; no override file exists at the cross-source layer; no deterministic resolution policy is committed. This ADR specifies the consolidated layer precisely so that collapse never happens. It is also bad scholarship to begin with — Egyptological disagreement is normal content to expose, not vandalism to resolve.

2. **Domain relationships aren't first-class.** Co-regency, succession, "buried in," "shares tomb with," dynastic family — these are graph-shaped facts squashed into flat fields (`ruler_ids: []` arrays for joint reigns) or implicit conventions. Adding a new relationship type requires a schema change.

3. **Provenance is implicit.** Each authority file traces to a source as a whole, but individual *facts* don't carry per-claim citations. The reviewer-cited rationale in `tie-break-overrides.json` (1,847 lines for Leprohon alone) sits structurally disconnected from the reconciled rows it justifies.

4. **The matching pipeline (Phase B) needs richer queries against authority.** ADR-009's Stage 2 fuzzy fallback is "Haiku triage with artifact context" without specifying a mechanism. Constraint-narrowed matching — "find Dynasty 18 rulers whose original burial is KV43" against an unknown name — requires structured graph queries that flat JSON can't serve cheaply. It also requires the authority layer to encode different tomb relationships (owner, original burial, secondary cache) as distinct predicates rather than a single ambiguous `buried_in`.

A pilot load of Leprohon (395 rows) + Beckerath (174 rows, 166 non-marker) into Neo4j Aura (May 2026) confirmed qualitatively that exact name overlap across sources is sparse: Leprohon's English forms ("Amenhotep III", "Thutmose III") and Beckerath's German forms ("Amenophis III.", "Tuthmosis III.") name the same rulers differently. Cross-source identity is a substantive scholarly claim, not a string-equality coincidence.

## Decision

The authority layer is modeled as a **source-attributed claim graph** following the CIDOC CRM E13 Attribute Assignment pattern. Every fact about an authority entity is reified as an E13 Statement node connecting subject to value, carrying the actor that performed the assignment and the document that records it. Disagreements between sources are preserved as parallel Statements, not collapsed at reconciliation time.

### CIDOC alignment

**Conformance target: CIDOC CRM 7.1.3 + CRMdig 5.0.** Both specifications, in their conceptual *and* official RDFS-encoding forms, are normative. The graph emits data that is valid under both specs to any conformant reader. A strict reader that has not loaded the Hapi extension manifest treats Hapi-namespaced triples as unrecognised URIs and does not reason on them (silent retention without interpretation). A reader that *has* loaded the manifest applies its `rdfs:subClassOf` / `rdfs:subPropertyOf` declarations and interprets Hapi terms through their declared CRM/CRMdig parents. Both reader modes are valid; the graph data is identical in either case. See the Hapi extension manifest section below.

Both specifications are vendored in-repo at `pipeline/pipeline/authority/spec/` (see the README in that directory):

| Specification | Version | Authoritative release | Vendored |
|---|---|---|---|
| Core CIDOC CRM | 7.1.3 | https://cidoc-crm.org/Version/version-7.1.3 | `cidoc_crm_v7.1.3.html` + `cidoc_crm_v7.1.3.rdf` |
| CRMdig (digital-provenance extension) | 5.0 | https://cidoc-crm.org/crmdig/ModelVersion/crmdig-v5.0 | `crmdig_v5.0.html` + `crmdig_v5.0.rdf` |

For each, the HTML release is the semantic authority (scope notes, conceptual ranges); the RDFS encoding is the syntactic authority for what's actually emitted (`rdfs:domain`, `rdfs:range`, IS-A chains, including RDFS-only refinements like P82a/P82b that the conceptual document doesn't enumerate). They rarely disagree; when they do, the HTML wins on semantic intent and the RDFS wins on syntactic encoding. Pin moves are atomic — replacing a vendored file and bumping the pin happen in the same commit.

**Why CRMdig.** The matcher provenance use-case (a piece of software runs against input data and produces output assertions) is exactly what CRMdig's D-class hierarchy was built for. Modelling matcher runs with core CRM alone forced either an awkward fit (treating software as `E74 Group`) or a real deviation (`:Matcher` as a non-CRM node). CRMdig has purpose-built classes (D3 Formal Derivation, D10 Software Execution, D14 Software, D1 Digital Object) that fit natively. Adopting CRMdig retires those workarounds.

#### Node-type mapping from Hapi labels to CRM / CRMdig classes

| Hapi label              | Class                          | Notes |
|-------------------------|--------------------------------|-------|
| `:Ruler`                | E21 Person                     | One node per source row, each treated as a **competing E21 identity hypothesis** about a real historical person. CRM 7.1.3's E21 scope note permits multiple instances when identity across sources is doubtful; that is exactly the situation here. `:Ruler` nodes are person-claims, not source-record proxies — `hapi:same_entity_as` claims resolve them into clusters as evidence accumulates. No canonical Person is materialised at load time. |
| `:Site`                 | E27 Site                       | Physical archaeological place. |
| `:Dynasty`              | E4 Period                      | The Egyptological dynastic period bucket — a chronological band, not a ruling family/house and not a contemporary social institution. Numbered dynasties 1–31 derive from Manetho's tradition; Dynasty 0 is a 20th-century scholarly periodisation grouping pre-unification kings (Narmer-precursors). Both are covered here as Egyptological constructs. Membership is via `hapi:in_dynastic_period` (chronological). Family-lineage and ruling-house modelling are out of scope; if needed they get their own predicate(s) targeting `:E74 Group`. |
| `:Statement`            | E13 Attribute Assignment       | Each claim is its own E13. |
| `:Person`               | E21 Person                     | A scholar or human curator (the actor of an E13). |
| `:Group`                | E74 Group                      | Curatorial bodies, learned societies. |
| `:Document`             | E31 Document                   | Publications, decision-batch records, authority releases. |
| `:Appellation`          | E41 Appellation                | Name-shaped value entity; literal accessed via P190. Type-classified via `P2_has_type → :E55 Type`. |
| `:TimeSpan`             | E52 Time-Span                  | Date-shaped value entity. Conceptual CRM uses P81 / P82 (range E61 Time Primitive); the RDFS implementation refines them to P81a / P81b / P82a / P82b with `rdfs:Literal` range. The property-graph stores boundary literals on the node; exports use the RDFS refinements. See deviation #3. |
| `:Dimension`            | E54 Dimension                  | Numeric measurement; P90 / P91. |
| `:Type`                 | E55 Type                       | The predicate registry; targets of P177. |
| `:MatcherRun`           | **D3 Formal Derivation** *(CRMdig)* | The specific execution of a matcher: deterministic algorithm runs over input data, producing derived output. IS-A chain: D3 ⊂ D10 Software Execution ⊂ D7 Digital Machine Event ⊂ E11 Modification & E65 Creation ⊂ E7 Activity. Carries run-reproducibility metadata as Hapi-namespaced properties (run_id, parameters_hash, reviewer_status, etc.). |
| `:MatcherAlgorithm`     | **D14 Software** *(CRMdig)* | The matcher algorithm definition (e.g. `normalized_name_v1`): the code/procedure that gets executed. IS-A chain: D14 ⊂ D1 Digital Object ⊂ E73 Information Object. Long-lived; many `:MatcherRun` instances reference one `:MatcherAlgorithm`. |
| `:SourceData`           | **D1 Digital Object** *(CRMdig)* | A reconciled.jsonl file (or other digital input) consumed by a matcher run. IS-A chain: D1 ⊂ E73 Information Object. |

#### Edge spine

Every E13 Statement carries a universally-required triad — P140 (subject), P141 (value), P177 (predicate type) — plus provenance edges that vary by claim type. **Human-documentary** claims carry P14 (actor) + P70i (document); **matcher-derived** claims carry `hapi:derived_by_run → :D3` (the derivation run that produced them). P70i remains optional on matcher-derived claims until a reviewer attaches a documentary anchor.

| Edge                                  | Specification | Domain | Range | Purpose |
|---------------------------------------|---------------|--------|-------|---------|
| `P140_assigned_attribute_to`          | core CRM      | E13    | E1    | Subject of the claim. |
| `P141_assigned`                       | core CRM      | E13    | E1    | Value of the claim (always an E1 entity, never a literal). |
| `P177_assigned_property_of_type`      | core CRM      | E13    | E55   | Predicate type (which kind of property this E13 assigns). |
| `P14_carried_out_by`                  | core CRM      | E7 (attaches to E13 by inheritance) | E39 | Human actor for human-attributed claims. |
| `P70i_is_documented_in`               | core CRM      | E1 (attaches to E13 by inheritance) | E31 | Documentary anchor; carries `cited_page` / `cited_pdf_page` as edge properties. |
| `hapi:derived_by_run`                 | Hapi extension (subPropertyOf P15_was_influenced_by) | E13 | D3 Formal Derivation | The matcher run that produced this assignment. |
| `L21_used_as_derivation_source`       | CRMdig        | D3     | D1    | The source data file the matcher consumed. |
| `L22_created_derivative`              | CRMdig        | D3     | D1    | The output data the matcher produced. |
| `L23_used_software_or_firmware`       | CRMdig (inherited from D7) | D7 (attaches to D3 by inheritance) | D14 | The matcher algorithm. |

#### Hapi extension manifest

The `hapi:` prefix used throughout this ADR resolves to the namespace `https://github.com/pcomans/hapi/ns/extension#`. The full extension manifest — `rdfs:subClassOf` / `rdfs:subPropertyOf` declarations and free-standing Hapi predicate declarations — is committed at `pipeline/pipeline/authority/hapi_extension.rdf`. The declarations are the standard CIDOC extension idiom (every official extension, including CRMdig itself, uses the same `subClassOf` / `subPropertyOf` mechanism to relate to core CRM). They are **not deviations**.

**Two reader modes, two outcomes — clarified explicitly:**

| Reader configuration | What happens to Hapi-namespaced triples |
|---|---|
| Strict CRM/CRMdig reader that has NOT loaded `hapi_extension.rdf` | Hapi terms are unrecognised URIs. The reader retains the triples but does not infer anything from them — IS-A propagation, subPropertyOf rewriting, and class-hierarchy queries that target CRM/CRMdig terms simply do not surface the Hapi-typed entities. Genuinely "silently ignored." |
| Reader that has loaded `hapi_extension.rdf` (alongside the CRM and CRMdig RDFS files) | An RDFS reasoner applies the manifest's declarations. Every `hapi:MatcherRun` is now also typed as `crmdig:D3 Formal Derivation` (and transitively as E7 Activity, E1 CRM Entity, etc.); every `hapi:derived_by_run` edge is now also a `crm:P15_was_influenced_by` edge. Hapi terms become discoverable through CRM/CRMdig queries. Free-standing Hapi predicates (those without a declared `subPropertyOf`) remain opaque even with the manifest loaded — the manifest documents their existence but doesn't relate them to CRM vocabulary. |

Both modes are valid. The graph data itself is identical in either case; what differs is the reader's interpretive layer. Hapi never relies on the manifest being loaded for correctness — but loading it unlocks the full interop story.

Manifest excerpt (the full file is the citable contract):

```turtle
# Hapi extension manifest excerpt — see pipeline/pipeline/authority/hapi_extension.rdf for the full file
# Every Hapi-namespaced class and predicate referenced anywhere in this ADR MUST appear in that file,
# with either a sound subClassOf/subPropertyOf declaration or an explicit free-standing declaration
# (with comment) when no CRM superclass/superproperty fits. Unmanifested terms are rejected by the
# cidoc-crm-validator subagent.

@prefix hapi:    <https://github.com/pcomans/hapi/ns/extension#> .
@prefix crm:     <http://www.cidoc-crm.org/cidoc-crm/> .
@prefix crmdig:  <http://www.cidoc-crm.org/extensions/crmdig/> .

# Classes
hapi:MatcherRun         rdfs:subClassOf  crmdig:D3_Formal_Derivation .
hapi:MatcherAlgorithm   rdfs:subClassOf  crmdig:D14_Software         .
hapi:SourceData         rdfs:subClassOf  crmdig:D1_Digital_Object    .

# Properties — Hapi-namespaced for readability, declared as subproperties of real CRM/CRMdig properties
hapi:derived_by_run     rdfs:subPropertyOf crm:P15_was_influenced_by  .  # E13 → hapi:MatcherRun
```

Hapi predicates that don't have a clean CRM superproperty (`hapi:same_entity_as`, `hapi:in_dynastic_period`, `hapi:tomb_owner`, etc.) live in the manifest as plain `rdf:Property` declarations and as `:E55 Type` instances in the predicate registry. The registry's `crm_nearest` field documents the closest CRM property for human reviewers, where one exists. Tightening these to real `rdfs:subPropertyOf` declarations is a follow-up Egyptological + CRM-modelling cross-cut.

#### Declared deviations from strict CRM + CRMdig

Conscious choices, each justified, contained, and with a documented round-trip mapping. Anything else in the model that violates either spec without being listed here is a bug — there is no "minor deviation" or "soft issue" category.

1. **Property-graph inlining of value-entity literals.** Strict CRM stores literals on value entities via P190 (E41 → E62 String), P90 (E54 → E60 Number), etc. The property-graph encoding inlines these as direct properties on the value-entity node (`:E41 Appellation {symbolic_content: 'wnis'}`). The mapping is mechanical and round-trippable to a strict CRM/RDF export.
2. **Property-graph inlining of structural attributes beyond value literals.** The same compactness choice extends to typing edges (`P2_has_type` represented inline as `appellation_kind: 'horus_name'`), Document properties (`kind`, `citation`, `year`, `language`, `rationale` represented inline rather than as separate typed nodes), and `:E31` identifying labels (`number`, `beckerath_label`, `leprohon_chapter` on `:Dynasty:E4 Period`). Round-trip mapping: each inline attribute expands at strict-RDF export to its canonical CRM form — `P2 → :E55 Type` for type properties; `P1_is_identified_by → :E41 Appellation` for identifying labels; `:E65 Creation + :E52 Time-Span` for temporal markers on Persistent Items; `P3_has_note → :E62 String` for free-text. Mechanical; loader specification owns the canonical expansions.
3. **Time-Span boundary literals stored directly on the `:E52 Time-Span` node.** The conceptual CRM 7.1.3 model declares P81 / P82 (E52 → E61 Time Primitive); it does not declare conceptual P81a / P81b / P82a / P82b. Those four are introduced *only* by the RDFS implementation as refinements that emit `rdfs:Literal`. The property-graph stores year boundaries as signed integers directly on the `:E52` node (`begin_of_the_begin: -2375`, `end_of_the_end: -2345`) plus an explicit `calendar` property pinning the year-numbering convention. Round-trip at the conceptual level: literals serialise into E61 Time Primitive value entities linked via P81 / P82. Round-trip at the RDFS-implementation level: same literals serialise into P81a / P81b / P82a / P82b refinements. Lexical form (XML Schema 1.1 expanded-year vs ISO 8601 extended astronomical-year vs other) is a **Hapi convention** pinned in the loader specification — neither CRM nor CRMdig mandates a specific form, particularly for BCE years where conventions disagree.
4. **Citation-evidence properties (`cited_page`, `cited_pdf_page`) carried on the `P70i_is_documented_in` edge itself.** Strict CRM has no `.1` sub-property of P70 for page-level citation; the edge-property idiom is a Hapi compactness choice. Round-trip mapping at strict-RDF export — every property's domain and range stays satisfied:
   - For each distinct (publication, page) pair, materialise the **page-level documentary content** as its own `:E31 Document` (e.g. `:E31 Document {id: 'leprohon_2013_p115'}`). The physical printed page is not itself an E31 (a printed sheet is closer to E22 Human-Made Object); what's typed as `:E31` is the propositional/documentary content carried at that page location, in the same sense that the publication-level `:E31` names the publication's documentary content, not its physical binding. The distinction matters for the museum-side layer where physical objects and their carried information are separately typed.
   - Bind the page-level `:E31` to its parent publication via `P148i_is_component_of → :E31 Document {id: 'leprohon_2013'}`. P148 has domain and range E89 Propositional Object; E31 IS-A E73 IS-A E89, so both endpoints conform by subsumption.
   - Identify the page-level `:E31` via `P1_is_identified_by → :E42 Identifier {value: 'p. 115'}`. P1 has domain E1 and range E41; E42 IS-A E41, so the range conforms by subsumption.
   - Rewrite the original `(:Statement:E13) -[:P70i_is_documented_in]-> (:E31 Document {publication})` to point at the page-level `:E31` instead of the publication-level one. **P70i's range stays E31** — no rerouting through E73/E33 required.

   The mapping is mechanical; the loader specification owns it. One `:E31` node is added per distinct cited page (not per citation), giving bounded growth.

(The previous version of this ADR also listed `:Matcher not E39 Actor` as a deviation. That deviation is **retired** by adopting CRMdig — matcher runs are now `:D3 Formal Derivation`, algorithms are `:D14 Software`, and the connection from E13 to the run is `hapi:derived_by_run rdfs:subPropertyOf P15_was_influenced_by`. None of these require a deviation.)

### Core principles

1. **Every claim has a provenance edge.** No fact lives in the graph without an attribution to how the claim came to be. Two distinct provenance shapes:

   - **Human-documentary** (scholarly attribution). Two CIDOC-distinct parts:
     - **The actor who performed the attribute assignment** — an E39 Actor (E21 Person for an individual scholar or curator; E74 Group for a curatorial body or society). Attached via `P14_carried_out_by`.
     - **The documentary source where the claim is recorded** — an E31 Document (a publication, an authority release, a curator-decision record). Attached via `P70i_is_documented_in`, with page citations carried as properties of that edge.

     For a Leprohon claim, the actor is the scholar Ronald J. Leprohon (`:E21 Person`) and the document is the 2013 book *The Great Name: Ancient Egyptian Royal Titulary* (`:E31 Document`). A publication is not itself an actor in CIDOC — E39 Actor requires capacity for intentional action — so publication nodes are documents, never actors.

   - **Machine-derived** (matcher / alias-expander / derivation rule output). One CRMdig-typed chain:
     - **The derivation run** that produced the Statement — a `:D3 Formal Derivation` (CRMdig 5.0). Attached via `hapi:derived_by_run` (declared `rdfs:subPropertyOf crm:P15_was_influenced_by` so strict CIDOC readers interpret it as "this E13 was influenced by this E7 Activity").
     - **The algorithm used** — a `:D14 Software` referenced from the run via `crmdig:L23_used_software_or_firmware`.
     - **The source data consumed** — one or more `:D1 Digital Object` references via `crmdig:L21_used_as_derivation_source`.
     - **The derived output data** — a `:D1 Digital Object` reference via `crmdig:L22_created_derivative`.

     A hapi match is *not* a scholarly association: the difference between them is structural in CIDOC terms. Human claims carry `P14 → E39` (an actor attesting); matcher claims carry `hapi:derived_by_run → D3` (a derivation event that produced the claim). Strict readers can distinguish the two without knowing Hapi-specific vocabulary, via the presence vs absence of P14 and the IS-A type of the provenance target.

   Matcher claims may lack `P70i_is_documented_in` until a reviewer attaches a documentary anchor; matcher provenance is algorithmic, not documentary. Human claims always carry both P14 and P70i — page-level metadata on P70i is optional but the documentary anchor itself is required.

2. **Cross-source disagreements are preserved.** When Leprohon claims reign-start −1390 and Dodson-Hilton claims −1391 for the same ruler, two Statements with the same predicate and different values coexist, each tracing to its source. Reconciliation does not pick a winner at the data layer. The resolution policy (which one a downstream consumer sees) is per-predicate and lives outside the graph — see principle 7.

3. **Per-agent disagreements are extraction artifacts, not data.** The 3-arbiter blind-extraction process is a quality gate on faithfulness to the source. Per CLAUDE.md Rule 2, agent disagreement resolves to exactly one of: (a) unanimity, (b) a real majority (>50%), (c) an explicit per-row override committed in the source's `tie-break-overrides.json` with cited rationale, or (d) a deterministic policy documented in code or the source's README. Anything else fails loud — not all disagreements naturally converge, which is exactly why `tie-break-overrides.json` exists per source. Whichever resolution applies, what loads as an E13 Statement is the *resolved* value, attributed to the publication (`P14_carried_out_by` → the scholar; `P70i_is_documented_in` → the publication). Agent-level structure never appears in the graph — it is pipeline scaffolding.

4. **Open schema, enforced registry.** Predicates and relationship types are *data*, not DDL. Adding `hapi:shares_tomb_with` is an INSERT into the predicate registry, not a migration. The registry materialises the `:E55 Type` catalogue that every E13's `P177_assigned_property_of_type` edge points at, and is the verify-before-create enforcement point: an E13 whose `P177` target does not resolve to a registered `:E55 Type` fails the load (Rule 3 — deterministic enforcement over convention). No agent or contributor invents a predicate; a new one is proposed against the registry, reviewed for overlap with existing predicates, and added once.

5. **All Statement values are E1 CRM Entity references; literals live on value-bearing entities.** `P141_assigned` has range E1 CRM Entity in CRM 7.1.3 — literals are not E1. The Hapi model is faithful to this:
   - A name claim like "Narmer's Horus name is 'nar mer'" assigns an `:E41 Appellation` value entity that carries the literal as a property accessed via `P190_has_symbolic_content`.
   - A reign-date claim assigns an `:E52 Time-Span` value entity that carries boundary literals on the node. Conceptual CRM models the span via P81 ongoing throughout / P82 at some time within (both E52 → E61 Time Primitive); the property-graph stores the boundaries directly, exporting to the RDFS-implementation refinements P81a / P81b / P82a / P82b at strict-RDF time (see deviation #4).
   - A numeric measurement assigns an `:E54 Dimension` carrying `P90_has_value` and `P91_has_unit`.
   - An entity-period claim like "Narmer is dated to Dynasty 0" assigns the Dynasty (`:E4 Period`) node directly via `hapi:in_dynastic_period`.

   The property-graph encoding inlines the CIDOC-property values (`symbolic_content`, `value`, `begin`, `end`) as properties of the value-entity node, rather than as separate string-literal nodes. The value-entity layer is what makes graph traversal uniform: "show me every claim that touches Dynasty 0" traverses through `P141_assigned`; "show me every appellation containing 'wnis'" indexes through `:E41 Appellation` nodes regardless of which Statement assigned them.

6. **Identity across sources is itself a claim — no canonical Person at load time.** Each source's row is stored as its own per-source entity node (`:Ruler`, `:Site`, etc.), keyed by source + source-row-id. Cross-source co-reference ("Leprohon's row for Unas is the same person as Beckerath's row for Unas") is modelled as a Statement with predicate `hapi:same_entity_as`, `P141_assigned` pointing at the other entity, and a provenance edge attributing the claim — `P14_carried_out_by` + `P70i_is_documented_in` for a human curator decision, `hapi:derived_by_run → :D3 Formal Derivation` for an automated matcher. **The loader makes no identity commitments.** Identity is data the matching pipeline produces over time, with full provenance. A canonical-person view can be derived later from `same_entity_as` clusters if query ergonomics demand it (see Consequences); the storage layer is per-source records, not collapsed persons.

7. **Resolution policy is per-predicate, fail-loud by default.** When a downstream consumer (UI, search index, enrich asset) needs a single value and the graph carries competing claims, a per-predicate resolution rule decides which to surface (e.g. "for `reign_start_bce`, Beckerath > Hornung > Leprohon"; "for `hapi:display_name`, prefer the most recent curator-decision Source"). If no rule is committed for a predicate, the query **fails loud** — the consumer must specify a rule or accept the full claim set. This aligns with Rule 2: no silent arbitrary picks; every resolution traces to a documented policy.

### Display name migration — first concrete application of the resolution policy

The canonical display name (ADR-016 "Conventional English Display Form" — "Khufu" not "Cheops", "Amenhotep III" not "Amenophis III") is the first per-predicate resolution policy committed to the registry. It also serves as the template for future per-predicate policies.

**Model.** All display-name claims — Leprohon's "Amenhotep III", Beckerath's "Amenophis III.", and the curator's canonical choice — share the **same predicate type** (`:E55 Type {id: 'hapi:display_name'}` linked via P177). They are differentiated by their actor + document:
- Leprohon's claim: `P14 → :E21 Person {id: 'leprohon_rj'}` and `P70i → :E31 Document {id: 'leprohon_2013'}`.
- Curator claim: `P14 → :E74 Group {id: 'hapi_curatorial'}` and `P70i → :E31 Document {id: 'hapi_display_names_2026_05', kind: 'curator_decision_batch'}`.

Predicates describe *what* the claim is about; the actor + document describe *who said it where* — keeping the canonical-vs-source-original distinction in provenance rather than predicate preserves the uniform claim model.

**Document granularity.** Curatorial decisions are batched by date: one `:E31 Document {kind: 'curator_decision_batch'}` per batch (`hapi_display_names_2026_05`, `hapi_display_names_2027_q1`, …), each carrying a `decided_at` timestamp and a free-text `rationale`. When a spelling is revised, a new Document is created and the old claim stays attached to its original Document as audit trail.

**Resolution rule for `hapi:display_name`** — both clauses must hold; checking only the document or only the actor is under-specified:
1. Prefer the Statement whose `P14_carried_out_by` is the curatorial Group `:E74 {id: 'hapi_curatorial'}` **AND** whose `P70i_is_documented_in` document has `kind = 'curator_decision_batch'`. Among matching Statements, pick the one whose document has the most recent `decided_at`.
2. Else: **fail loud** — no fallback to publication-documented Statements, no fallback to other actors documented in a curator-decision batch, no fallback to the curatorial Group attaching to a non-curator-decision document.

Consequences of fail-loud: rulers added by a future source-loader before a curator reviews them are unrenderable until the curator decision arrives. This is intentional — the gap surfaces in the review queue immediately, rather than hiding behind a placeholder.

**Migration.** Initial load: a curator-decision-batch document `hapi_display_names_2026_05` is created, citing ADR-016's spelling list as its source of truth. For every ruler with an existing per-source row, one Statement is produced with the canonical Anglicised form (per ADR-016) as its value, `P14_carried_out_by → :E74 Group {id: 'hapi_curatorial'}`, and `P70i_is_documented_in → :E31 Document {id: 'hapi_display_names_2026_05'}`. The seed spelling list lives in version control as `pipeline/pipeline/authority/curator_decisions/hapi_display_names_2026_05.json` (exact path resolved during loader implementation); ADR-016 is cited rather than duplicated.

**Effect on ADR-016.** ADR-016 is partially superseded: the storage shape it implied (a flat `rulers.json` with one canonical display name per row) is replaced by the claim-graph form. The spelling list itself lives on as the migration seed for the initial `hapi_display_names_2026_05` curator-decision-batch document. ADR-016's substantive content — which spelling to prefer for each ruler and why — remains the authoritative reference cited by that document's `rationale` field.

### Schema sketch

Every claim is an E13 Statement. Edge cardinality depends on claim type. **Human-documentary claims always carry all five canonical edges**: P140 (subject), P141 (value), P177 (predicate type), P14 (actor), and P70i (documentary source). Page-level citation (`cited_page`, `cited_pdf_page`) is *optional metadata* on the P70i edge — the page may be unknown — but the P70i edge itself to the publication-level `:E31 Document` is required. A human-attested claim without a documentary anchor would be an undocumented scholarly claim, which principle 1 forbids. **Matcher-derived claims** replace `P14_carried_out_by` with `hapi:derived_by_run → :MatcherRun:D3` (a CRMdig Formal Derivation; `hapi:derived_by_run` is `rdfs:subPropertyOf crm:P15_was_influenced_by`) and may lack `P70i_is_documented_in` until a reviewer attaches a documentary anchor — matcher provenance is algorithmic, not documentary, so the documentary edge appears only when a human curator stamps one on. The `P140` / `P141` / `P177` triad is the universally-required spine for all claims; the human-vs-matcher provenance shape and the optional-on-matcher P70i are the only points of variation.

| # | Edge                                  | Target type         | Required |
|---|---------------------------------------|---------------------|----------|
| 1 | `P140_assigned_attribute_to`          | the subject entity  | always |
| 2 | `P141_assigned`                       | the value entity    | always (an E1 entity, never a literal) |
| 3 | `P177_assigned_property_of_type`      | `:Type` (E55)       | always — the predicate type |
| 4 | `P14_carried_out_by`                  | `:Person`/`:Group`  | for human-attributed claims |
| 4'| `hapi:derived_by_run`                 | `:MatcherRun:D3`    | for matcher-attributed claims (Hapi extension; `rdfs:subPropertyOf crm:P15_was_influenced_by`). The `:MatcherRun` (CRMdig D3 Formal Derivation) carries run-reproducibility metadata and references its algorithm (`:MatcherAlgorithm:D14`) via `crmdig:L23_used_software_or_firmware`. |
| 5 | `P70i_is_documented_in`               | `:Document`         | for claims with a documentary source; carries `cited_page`, `cited_pdf_page` as edge properties |

```
// Per-source ruler node (E21 Person; one per source row, no canonical Person)
(:Ruler:E21_Person {key: 'leprohon::leprohon-5.07', source: 'leprohon', ...})

// (1) A name claim. Value is an E41 Appellation carrying the literal via P190.
//     Actor is Leprohon the scholar (E21 Person); document is leprohon_2013 (E31 Document).
(:Statement:E13)
  -[:P140_assigned_attribute_to]->    (:Ruler {leprohon::leprohon-5.07})
  -[:P141_assigned]->                  (:Appellation:E41 {
                                           symbolic_content: 'wnis',
                                           appellation_kind: 'horus_name'
                                       })
  -[:P177_assigned_property_of_type]-> (:Type:E55 {id: 'hapi:horus_name'})
  -[:P14_carried_out_by]->             (:Person:E21 {id: 'leprohon_rj'})
  -[:P70i_is_documented_in {
        cited_page: 115,
        cited_pdf_page: 142
   }]->                                (:Document:E31 {id: 'leprohon_2013'})

// (2) An entity-valued claim — assigning Unas to the historiographic period bucket "Dynasty 5".
//     Value is the :Dynasty (E4 Period) node directly. Not a family-membership claim; see Dynasty in
//     the node-type table.
(:Statement:E13)
  -[:P140_assigned_attribute_to]->    (:Ruler {leprohon::leprohon-5.07})
  -[:P141_assigned]->                  (:Dynasty:E4_Period {number: 5})
  -[:P177_assigned_property_of_type]-> (:Type:E55 {id: 'hapi:in_dynastic_period'})
  -[:P14_carried_out_by]->             (:Person:E21 {id: 'leprohon_rj'})
  -[:P70i_is_documented_in]->          (:Document:E31 {id: 'leprohon_2013'})

// (3) A reign-date claim. Value is an E52 Time-Span with boundary literals inlined on the node.
//     Conceptual CRM models the span via P81/P82 (E52 → E61 Time Primitive); the RDFS
//     implementation exposes P81a/P81b/P82a/P82b as literal refinements. The property-graph
//     stores boundaries directly; export pipelines emit one or the other form. See deviation #4.
(:Statement:E13)
  -[:P140_assigned_attribute_to]->    (:Ruler {leprohon::leprohon-5.07})
  -[:P141_assigned]->                  (:TimeSpan:E52 {
                                           begin_of_the_begin: -2375,
                                           end_of_the_end: -2345,
                                           calendar: 'astronomical_year'
                                       })
  -[:P177_assigned_property_of_type]-> (:Type:E55 {id: 'hapi:reign_period'})
  -[:P14_carried_out_by]->             (:Person:E21 {id: 'leprohon_rj'})
  -[:P70i_is_documented_in]->          (:Document:E31 {id: 'leprohon_2013'})

// (4) A cross-source identity claim attributed to a matcher run.
//     No P14 — matcher claims don't have a human actor. Instead:
//       hapi:derived_by_run (rdfs:subPropertyOf P15_was_influenced_by) → :D3 Formal Derivation (the run)
//       The D3 references its software (:D14) via L23, its inputs (:D1 source data) via L21,
//       and its derived output (:D1) via L22. All CRMdig 5.0, all strict-conformant.
//     Confidence is a Hapi property of the Statement; the run carries the reproducibility
//     metadata (input commit, parameter hash, timestamp, reviewer status) so any score
//     can be regenerated or rejected by replaying the D3 against its L21 sources.
(:Statement:E13 {confidence: 0.94})
  -[:P140_assigned_attribute_to]->    (:Ruler {leprohon::leprohon-5.07})
  -[:P141_assigned]->                  (:Ruler {beckerath::05.07})
  -[:P177_assigned_property_of_type]-> (:Type:E55 {id: 'hapi:same_entity_as'})
  -[:hapi:derived_by_run]->            (:MatcherRun:D3 {
                                           run_id:               'matcher_run_2026_05_17T14_22Z',
                                           input_dataset_commit: 'a8f3e9d...',
                                           parameters_hash:      'sha256:7c4...',
                                           started_at:           '2026-05-17T14:22:31Z',
                                           completed_at:         '2026-05-17T14:24:08Z',
                                           reviewer_status:      'pending'
                                                                  // pending | approved | rejected | superseded
                                       })

(:MatcherRun:D3 {matcher_run_2026_05_17T14_22Z})
  -[:L23_used_software_or_firmware]-> (:MatcherAlgorithm:D14 {
                                           id: 'normalized_name_v1',
                                           version: '0.1.0',
                                           algorithm: 'lowercase+strip_diacritics+token_match',
                                           hyperparameters_json: '{"min_dynasty_match": true}'
                                       })
  -[:L21_used_as_derivation_source]-> (:SourceData:D1 {
                                           path: 'leprohon-2013-titulary/reconciled.jsonl',
                                           git_commit: 'a8f3e9d...'
                                       })
  -[:L21_used_as_derivation_source]-> (:SourceData:D1 {
                                           path: 'beckerath-1997-chronologie/reconciled.jsonl',
                                           git_commit: 'a8f3e9d...'
                                       })
  -[:L22_created_derivative]->        (:SourceData:D1 {
                                           path: 'matcher_outputs/run_2026_05_17T14_22Z.jsonl'
                                       })

// (5) Curator-decision display name. Actor is the curatorial Group; document is the dated decision batch.
(:Statement:E13)
  -[:P140_assigned_attribute_to]->    (:Ruler {leprohon::leprohon-5.07})
  -[:P141_assigned]->                  (:Appellation:E41 {
                                           symbolic_content: 'Unas',
                                           language: 'en'
                                       })
  -[:P177_assigned_property_of_type]-> (:Type:E55 {id: 'hapi:display_name'})
  -[:P14_carried_out_by]->             (:Group:E74 {id: 'hapi_curatorial'})
  -[:P70i_is_documented_in]->          (:Document:E31 {
                                           id: 'hapi_display_names_2026_05',
                                           kind: 'curator_decision_batch',
                                           decided_at: '2026-05-17'
                                       })

// Backbone reference nodes — shared across sources
(:Dynasty:E4_Period {number, beckerath_label, leprohon_chapter})
(:Site:E27          {id})

// Actor and document catalogues
(:Person:E21   {id: 'leprohon_rj',        full_name: 'Ronald J. Leprohon'})
(:Group:E74    {id: 'hapi_curatorial',    name: 'Hapi curatorial body'})
(:Document:E31 {id: 'leprohon_2013',      kind: 'publication', citation, year, language})
(:Document:E31 {id: 'hapi_display_names_2026_05',
                kind: 'curator_decision_batch',
                decided_at, rationale, supersedes})

// Matcher catalogue and run records (CRMdig classes with Hapi extension labels)
//   :MatcherAlgorithm:D14_Software       — the algorithm definition (long-lived; many runs share one).
//                                          IS-A chain: D14 ⊂ D1 ⊂ E73 Information Object.
//   :MatcherRun:D3_Formal_Derivation     — a specific execution that produced one or more Statements.
//                                          IS-A chain: D3 ⊂ D10 Software Execution ⊂ D7 Digital Machine Event
//                                          ⊂ E11 Modification & E65 Creation ⊂ E7 Activity.
//   :SourceData:D1_Digital_Object        — reconciled.jsonl files or other digital inputs/outputs.
//                                          IS-A chain: D1 ⊂ E73 Information Object.
// Every confidence/score on a derived Statement is reproducible by replaying the
// MatcherRun (D3) against its L21 source files with its parameters_hash.
(:MatcherAlgorithm:D14 {id, version, algorithm, hyperparameters_json})
(:MatcherRun:D3        {run_id, input_dataset_commit, parameters_hash,
                        started_at, completed_at,
                        reviewer_status, reviewer_id, reviewed_at})
(:SourceData:D1        {path, git_commit, ...})
```

Page-level citation lives as properties on the `P70i_is_documented_in` edge, not on the P14 edge — P14 attributes the *act* of assignment to its agent and has no slot for evidence pointers; P70i is the natural CIDOC home for "this assignment is recorded in this document at this page."

### Predicate registry

The predicate registry materialises the E55 Type nodes that every Statement's `P177_assigned_property_of_type` edge points at. It is the FK target for those edges — a Statement with an unregistered predicate fails the load.

The registry is the authoritative vocabulary for the claim graph. Each entry is mandatory in all fields below; missing fields fail validation at registry-load time.

| Field                 | Type                       | Purpose |
|-----------------------|----------------------------|---------|
| `id`                  | string (PK)                | `hapi:<name>` for Hapi predicates; CIDOC P-number (e.g. `P14`) for direct CRM properties |
| `label`               | string                     | human-readable name for review queues and UI |
| `definition`          | string                     | one-paragraph definition of what the predicate means and when it applies |
| `subject_class`       | CIDOC E-class or set       | e.g. `E21 Person` for `hapi:reign_period`; `E27 Site` for `hapi:located_in` |
| `value_class`         | CIDOC E-class or set       | e.g. `E41 Appellation` for `hapi:horus_name`; `E4 Period` for `hapi:in_dynastic_period`; `E21 Person` for `hapi:same_entity_as` |
| `value_cardinality`   | `single` \| `multi`        | whether a subject can have one or many active claims of this predicate |
| `crm_nearest`         | CIDOC P-number \| `null`   | nearest CIDOC property for interop documentation; `null` if no clean fit |
| `is_symmetric`        | bool                       | whether the predicate is symmetric (e.g. `hapi:same_entity_as` is) |
| `notes`               | string \| `null`           | rationale, scope notes, known edge cases |

Adding a new predicate is an INSERT into this registry preceded by a review against existing predicates to avoid `buried_in` / `interred_at` / `tomb_location` vocabulary drift. The registry is committed to version control (`pipeline/pipeline/authority/predicate_registry.json` — exact path resolved during implementation) and validated by a CI test that loads each entry and asserts every required field is populated and that referenced E-classes exist in the class catalogue.

### What this does not decide

- **Storage technology** — Postgres (with relational encoding of the graph, or with the Apache AGE extension) and Neo4j (self-hosted Community or Aura managed) are the two viable candidates. A separate ADR will resolve this based on the pilot evidence accumulated under this model. Until then, the conceptual model is binding; the storage substrate is open.
- **The relational vs property-graph encoding of E13.** Whether Statements are tables with FK columns or first-class graph nodes follows from the storage choice. Both encodings preserve the CIDOC mapping above; specifying the encoding before the storage ADR pre-decides storage.
- **Per-predicate resolution policies beyond `hapi:display_name`** — the *default* is fail-loud (principle 7); the *first concrete policy* is committed above for `hapi:display_name`. Additional per-predicate rules (which document wins for `hapi:reign_start_bce`, `hapi:in_dynastic_period`, etc.) accumulate in the policy registry as downstream consumers demand them. The registry's exact location and review process is a follow-up ADR.
- **Phase C feedback cadence** — when an approved fuzzy match in the review queue produces a new alias, when does the alias get added as a claim? Per-approval, batched, or blocked until a Phase B pass completes? Tracked in #221.

## Storage candidates (deferred)

Two viable candidates, evaluated against the model above. A follow-up ADR will choose between them.

### Postgres (relational encoding or with Apache AGE)

- **Pro:** ADR-004 + ADR-011 already commit Postgres as canonical store. SQLAlchemy + Alembic + Drizzle introspection toolchain is already wired up. Artifacts (millions, property-heavy, search-driven) stay in Postgres; authority graph in the same database keeps artifact ↔ authority joins as single-DB SQL. No new ops surface. Apache 2.0 license, no per-GB pricing.
- **Pro:** Predicates-as-rows pattern gives FK-enforced verify-before-create with zero migrations per new predicate.
- **Con:** Multi-hop graph traversals are recursive CTEs (workable for 1–2 hops, ugly at depth). No native graph visualization (Bloom-equivalent).
- **AGE variant:** First-class Cypher inside Postgres; trades native graph storage performance at depth + `pg_upgrade` friction.

### Neo4j (Aura managed or self-hosted Community)

- **Pro:** Native graph storage; multi-hop traversals are first-class operators rather than recursive CTEs. (Actual per-query performance depends on indexes, node degree, and traversal shape; the storage ADR will compare measured pilot queries on representative authority data.) CIDOC CRM has a published Neo4j implementation (`diging/cidoc-crm-neo4j`) and a substantial heritage-research community using exactly this pattern. Cypher is more readable than SQL for the queries we'd actually write. Graph Data Science library gives node embeddings + similarity + community detection natively (relevant for constraint-narrowed matching, ADR-009 Stage 2).
- **Pro:** Aura Free tier (200K nodes / 400K relationships) fits the authority layer comfortably and lets the pilot run at zero cost.
- **Con:** Dual-store with Postgres-resident artifacts violates Rule 4 head-on; every match operation becomes a cross-system call. Aura Professional pricing is real money (~$25K–$50K/year at production memory sizing). Community Edition AGPLv3 + restrictive additional terms are murky for a public artifact index. Drizzle / SQLAlchemy / Alembic don't apply.

The trade hinges on whether artifacts move into the graph (architecturally cleanest but expensive and reverses ADR-004) or stay in Postgres (introduces the dual-store cost). The choice ADR will resolve this.

## Implications for matching (ADR-009)

The graph reshapes Stage 2 of the matching algorithm. Today: fuzzy string distance over all aliases, with Haiku triage for context. With this model: **constraint-narrow the candidate set via graph queries, then match name against the narrowed set.**

Consider an artifact carrying "Thutmose, KV43, Dynasty 18." Among the four Dynasty 18 Thutmoses (I, II, III, IV), KV43 is securely the tomb Thutmose IV commissioned and was originally buried in. A query against `hapi:original_burial_in = KV43 AND hapi:in_dynastic_period = Dynasty 18` collapses the candidate set to one before name matching runs.

The example also illustrates why tomb references demand careful predicate granularity. "Tomb" is not one relationship: it is at least three, each of which can disagree.

- `hapi:tomb_owner` — the ruler the tomb was commissioned for. Stable across cache reburials.
- `hapi:original_burial_in` — the ruler whose body was first interred there. Usually but not always the same as the owner.
- `hapi:cache_context_at` — the location of a *secondary* burial, typically the Dynasty 21 priestly reburials at KV35 (Amenhotep II's tomb, used as a cache for many other Dynasty 18 and 19 royals) and TT320/DB320 (the Deir el-Bahari royal cache).

A naive `hapi:buried_in` predicate that conflates these three loses information and produces wrong matches: a stela of Ramesses I found in the KV35 cache is not evidence that Ramesses I owned, was originally buried in, or has any primary association with KV35 — it was moved there ~400 years after his death. The open schema accommodates the distinction natively; rigorous matching demands it. The Haiku step becomes a fallback for genuinely ambiguous cases (overlapping co-regencies, post-burial usurpations, ambiguous cache attributions), not the primary disambiguation mechanism.

A follow-up ADR will revise ADR-009 to specify the constraint-narrowed algorithm in detail once storage tech is decided.

## Consequences

- **Phase 0 output shape changes.** Sources still produce `reconciled.jsonl`, but the downstream loader emits per-source E13 Statements, not collapsed per-entity rows. The 3-agent extraction step's job is unchanged (faithful capture of the source); per-row resolution still follows the Rule-2 decision tree (unanimity / majority / `tie-break-overrides.json` / documented policy) — the loader trusts whatever the existing pipeline emits and never re-resolves at the graph layer.
- **Reconciliation semantics change.** "Reconciliation" no longer means "pick one value across sources"; it means "load all sources' claims into the graph and let the resolution policy (per-predicate, per-consumer) decide what to surface." The current `tie-break-overrides.json` becomes **pipeline QA provenance**, not scholarly citation evidence. Tie-break overrides justify *extraction arbitration* (which of the 3 agents' readings of the source was correct), not the source publication's historical claim itself; they sit in a separate QA-provenance layer attached to the loader event or extraction step that produced the Statement, queryable as "how was this Statement produced" rather than "who attested to this Statement." A Statement's scholarly citation chain remains P14 → scholar + P70i → publication; QA provenance lives alongside, never inside, that chain.
- **Disagreements become first-class artifacts.** The UI can honestly show "1353–1336 BCE (Leprohon 2013) / 1352–1335 BCE (Dodson-Hilton 2010)" instead of pretending certainty it doesn't have. Authority disagreements appear in search snippets, hover cards, and the artifact detail page.
- **Cross-source identity becomes data, not a structural primitive.** Adding a new source (Hornung, Kitchen, Ryholt) does not require re-curation of existing entities. It adds per-source nodes that get linked to existing nodes via `hapi:same_entity_as` Statements — derived from a `:D3 Formal Derivation` (matcher-derived, via `hapi:derived_by_run`) where confident, queued for human review (curator-attributed via P14 + P70i) otherwise. A canonical-person view, if needed, can be derived from `same_entity_as` clusters as a materialized view; the source of truth remains the per-source nodes plus their identity claims.
- **The predicate registry becomes the vocabulary contract.** Any new relationship type proposed by an agent, a Phase 0 chunk, or a contributor must be reviewed against the registry. The CI check is FK-enforced at the DB layer; convention is not enough.
- **Citation network becomes queryable.** Citation tokens currently buried as text inside Leprohon's `source_note` fields (referencing Beckerath 1999, Gauthier 1907, Wilkinson 2000, etc.) become explicit edges from Statements to Citation nodes, queryable as "claims about Akhenaten that cite Wilkinson" or "what does Leprohon cite that we have no authority data for."
- **`attested_in` becomes the bridge to artifacts.** Attestation entries currently nested inside Leprohon name qualifiers become explicit edges from Name Statements to Inscription / Artifact nodes, linking the authority layer to the museum layer at the data level.
- **Temporal phases gain structure without canonicalisation.** Leprohon's split of Akhenaten into "Amenhotep IV (Regnal Years 1 to 5)" + "Akhenaten (Regnal Years 5 to 17)" produces two per-source `:Ruler` nodes (two rows in Leprohon, two nodes in the graph). They are linked by a `hapi:same_entity_as` Statement attributed to the source itself — Leprohon's text explicitly identifies the two as a single ruler at different naming phases. Each `:Ruler` carries its own `hapi:reign_period` Statement covering the relevant regnal years. Beckerath's single "Amenophis IV. Ach-en-aten" row becomes a third per-source `:Ruler` node, linked to either of the Leprohon nodes via a separate cross-source `hapi:same_entity_as` Statement (curator-attributed once reviewed; matcher-attributed in the interim). No canonical Person is materialised at load time; the "same person, different naming period" structure is data, not schema.
- **The storage decision is the gating follow-up.** Until ADR-019 (or the storage ADR, whatever number it lands at) is resolved, no production graph build can start. A Phase 0 → graph loader can be sketched against either substrate.
