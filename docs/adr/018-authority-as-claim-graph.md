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

A pilot load of Leprohon (395 rows) + Beckerath (174 rows, 166 non-marker) into Neo4j Aura (May 2026) confirmed qualitatively that exact name overlap across sources is sparse — single-digit counts under naive lowercase match, low double-digit counts under light punctuation/diacritic normalisation, with the exact number depending sensitively on the normalisation choice. Leprohon's English forms ("Amenhotep III", "Thutmose III") and Beckerath's German forms ("Amenophis III.", "Tuthmosis III.") name the same rulers differently. Cross-source identity is a substantive scholarly claim, not a string-equality coincidence.

A reproducible pilot script (`pipeline/scripts/pilot_cross_source_overlap.py`) with documented normalisation steps and exclusion criteria is a prerequisite for promoting this ADR from Proposed → Accepted; until that script is committed, the specific overlap count is omitted from this ADR as unsourced.

## Decision

The authority layer is modeled as a **source-attributed claim graph** following the CIDOC CRM E13 Attribute Assignment pattern. Every fact about an authority entity is reified as an E13 Statement node connecting subject to value, carrying the actor that performed the assignment and the document that records it. Disagreements between sources are preserved as parallel Statements, not collapsed at reconciliation time.

### CIDOC CRM alignment

This ADR commits to **CIDOC CRM version 7.1.3** ([definition](https://cidoc-crm.org/html/cidoc_crm_v7.1.3.html)). All class and property identifiers (E-numbers and P-numbers) used in this document refer to that version. A subsequent CRM revision will trigger a follow-up ADR that documents migration deltas; the version is pinned, not floating.

Node-type mapping from Hapi labels to CIDOC classes:

| Hapi label              | CIDOC class                    | Notes |
|-------------------------|--------------------------------|-------|
| `:Ruler`                | E21 Person                     | one node per source row; no canonical Person at load time |
| `:Site`                 | E27 Site                       | physical archaeological place |
| `:Dynasty`              | E4 Period                      | with begin/end E52 Time-Span; membership claims point here |
| `:Statement`            | E13 Attribute Assignment       | each claim is its own E13 |
| `:Person`               | E21 Person                     | a scholar or human curator (the actor of an E13) |
| `:Group`                | E74 Group                      | curatorial bodies, learned societies |
| `:Document`             | E31 Document                   | publications, decision-batch records, authority releases |
| `:Appellation`          | E41 Appellation                | name-shaped value entity; literal accessed via P190 |
| `:TimeSpan`             | E52 Time-Span                  | date-shaped value entity; P82a/P82b for begin/end |
| `:Dimension`            | E54 Dimension                  | numeric measurement; P90/P91 |
| `:Type`                 | E55 Type                       | the predicate registry; targets of P177 |
| `:Matcher`              | *(non-CRM — declared deviation)* | software agents; see deviations below |

Edges use CIDOC property identifiers as primary, with `hapi:` namespace for relations CRM does not cover. The five edges that carry the spine of every claim:

| Edge                                  | CIDOC property               | Domain | Range | Purpose |
|---------------------------------------|------------------------------|--------|-------|---------|
| `P140_assigned_attribute_to`          | P140                         | E13    | E1    | The subject of the claim (the Ruler the fact is about) |
| `P141_assigned`                       | P141                         | E13    | E1    | The value of the claim (always an E1 entity, never a literal) |
| `P177_assigned_property_of_type`      | P177                         | E13    | E55   | The predicate type (which kind of property this E13 assigns) |
| `P14_carried_out_by`                  | P14                          | E13    | E39   | The actor who performed the assignment |
| `P70i_is_documented_in`               | P70 (inverse)                | E13    | E31   | The document where the assignment is recorded; carries `cited_page`, `cited_pdf_page` as edge properties |

**Declared deviations from strict CRM 7.1.3.** These are conscious choices, not oversights; each is justified, contained, and carries a documented round-trip mapping to strict CRM/RDF. They are listed here so the rest of the ADR can use them without re-explaining. Anything else in the model that violates the spec without being listed here is a bug — there is no "minor deviation" or "soft issue" category.

1. **`:Matcher` is not E39 Actor.** CRM has no clean class for software agents (CRMdig's D7 Digital Machine Event is an extension, not core). Automated-derivation provenance attaches via the Hapi-namespaced `hapi:derived_by` edge directly, not via P14. The trust signal lives in the edge type so consumers can filter without parsing actor properties.
2. **Property-graph inlining of value-entity literals.** Strict CRM stores literals on value entities via P190 (E41 → E62 String), P90 (E54 → E60 Number), etc. The property-graph encoding inlines these as direct properties on the value-entity node (`:E41 Appellation {symbolic_content: 'wnis'}`). The mapping is mechanical and round-trippable to a strict CRM/RDF export.
3. **Hapi-namespace predicates where CRM has no clean fit.** Predicates like `hapi:same_entity_as`, `hapi:buried_in`, `hapi:shares_tomb_with`, `hapi:derived_by` live in a `hapi:` namespace. Each entry in the predicate registry (E55 Type) carries a `crm_nearest` field pointing at the nearest CIDOC property for interop documentation, when one exists.
4. **P82a/P82b values stored as inlined signed integer years rather than `xsd:dateTime` literals.** Strict CRM 7.1.3 declares P82a_begin_of_the_begin and P82b_end_of_the_end with range `rdfs:Literal` (in practice `xsd:dateTime`); see the RDFS at https://cidoc-crm.org/rdfs/7.1.3/CIDOC_CRM_v7.1.3.rdf. The property-graph encoding stores year boundaries as signed integers on the `:TimeSpan:E52` node (e.g. `begin_of_the_begin: -2375`) together with an explicit `calendar` property (e.g. `'astronomical_year'`) that pins the year-numbering convention. Round-trip mapping at strict-RDF export: each integer N expands to `xsd:dateTime` `<N>-01-01T00:00:00Z` (begin-of-year for P82a) or `<N>-12-31T23:59:59Z` (end-of-year for P82b). The mapping is mechanical; the loader specification owns it.
5. **Citation-evidence properties (`cited_page`, `cited_pdf_page`) carried on the `P70i_is_documented_in` edge itself.** Strict CRM 7.1.3 has no `.1` sub-property of P70 for page-level citation; the strictly conformant encoding requires reifying each cited passage as an `:E73 Information Object` (or `:E33 Linguistic Object`) bearing the page identifier, then routing the E13 → E31 link through it. The property-graph encoding carries page properties as edge attributes directly, which keeps the graph compact and the citation queryable without an extra hop. Round-trip mapping at strict-RDF export: each citation-bearing edge expands into an intermediate `:E73` node carrying `cited_page` / `cited_pdf_page` as `:E42 Identifier` references, with the E13 → E31 link routed through it. The mapping is mechanical; the loader specification owns it.

### Core principles

1. **Every claim has a provenance edge.** No fact lives in the graph without an attribution to who made the claim. Provenance has two CIDOC-distinct parts:
   - **The actor who performed the attribute assignment** — an E39 Actor (E21 Person for an individual scholar or curator; E74 Group for a curatorial body or society). Attached via `P14_carried_out_by`.
   - **The documentary source where the claim is recorded** — an E31 Document (a publication, an authority release, a curator-decision record). Attached via `P70i_is_documented_in`, with page citations carried as properties of that edge.

   For a Leprohon claim, the actor is the scholar Ronald J. Leprohon (`:E21 Person`) and the document is the 2013 book *The Great Name: Ancient Egyptian Royal Titulary* (`:E31 Document`). A publication is not itself an actor in CIDOC — E39 Actor requires capacity for intentional action — so publication nodes are documents, never actors.

   Automated processes — matchers, alias-expanders, derivation rules — are `:Matcher` nodes attributed via a Hapi-namespaced `hapi:derived_by` edge. This is a **declared deviation from CRM 7.1.3**: CIDOC has no clean E39 subclass for software agents, and Hapi deliberately encodes the trust difference at the edge type. A Statement reached via `P14_carried_out_by → :E21 Person | :E74 Group` carries human-scholarly weight; one reached via `hapi:derived_by → :Matcher` carries computational-derivation weight. UI, search index, and review workflows can filter by edge type without parsing a `type` property.

2. **Cross-source disagreements are preserved.** When Leprohon claims reign-start −1390 and Dodson-Hilton claims −1391 for the same ruler, two Statements with the same predicate and different values coexist, each tracing to its source. Reconciliation does not pick a winner at the data layer. The resolution policy (which one a downstream consumer sees) is per-predicate and lives outside the graph — see principle 7.

3. **Per-agent disagreements are extraction artifacts, not data.** The 3-arbiter blind-extraction process is a quality gate on faithfulness to the source. Per CLAUDE.md Rule 2, agent disagreement resolves to exactly one of: (a) unanimity, (b) a real majority (>50%), (c) an explicit per-row override committed in the source's `tie-break-overrides.json` with cited rationale, or (d) a deterministic policy documented in code or the source's README. Anything else fails loud — not all disagreements naturally converge, which is exactly why `tie-break-overrides.json` exists per source. Whichever resolution applies, what loads as an E13 Statement is the *resolved* value, attributed to the publication (`P14_carried_out_by` → the scholar; `P70i_is_documented_in` → the publication). Agent-level structure never appears in the graph — it is pipeline scaffolding.

4. **Open schema, enforced registry.** Predicates and relationship types are *data*, not DDL. Adding `hapi:shares_tomb_with` is an INSERT into the predicate registry, not a migration. The registry materialises the `:E55 Type` catalogue that every E13's `P177_assigned_property_of_type` edge points at, and is the verify-before-create enforcement point: an E13 whose `P177` target does not resolve to a registered `:E55 Type` fails the load (Rule 3 — deterministic enforcement over convention). No agent or contributor invents a predicate; a new one is proposed against the registry, reviewed for overlap with existing predicates, and added once.

5. **All Statement values are E1 CRM Entity references; literals live on value-bearing entities.** `P141_assigned` has range E1 CRM Entity in CRM 7.1.3 — literals are not E1. The Hapi model is faithful to this:
   - A name claim like "Narmer's Horus name is 'nar mer'" assigns an `:E41 Appellation` value entity that carries the literal as a property accessed via `P190_has_symbolic_content`.
   - A reign-date claim assigns an `:E52 Time-Span` value entity carrying `P82a_begin_of_the_begin` / `P82b_end_of_the_end` properties.
   - A numeric measurement assigns an `:E54 Dimension` carrying `P90_has_value` and `P91_has_unit`.
   - An entity-identity claim like "Narmer belongs to Dynasty 0" assigns the Dynasty (`:E4 Period`) node directly.

   The property-graph encoding inlines the CIDOC-property values (`symbolic_content`, `value`, `begin`, `end`) as properties of the value-entity node, rather than as separate string-literal nodes. The value-entity layer is what makes graph traversal uniform: "show me every claim that touches Dynasty 0" traverses through `P141_assigned`; "show me every appellation containing 'wnis'" indexes through `:E41 Appellation` nodes regardless of which Statement assigned them.

6. **Identity across sources is itself a claim — no canonical Person at load time.** Each source's row is stored as its own per-source entity node (`:Ruler`, `:Site`, etc.), keyed by source + source-row-id. Cross-source co-reference ("Leprohon's row for Unas is the same person as Beckerath's row for Unas") is modeled as a Statement with predicate `hapi:same_entity_as`, `P141_assigned` pointing at the other entity, and a provenance edge attributing the claim — `P14_carried_out_by` for a human curator decision, `hapi:derived_by` for an automated matcher. **The loader makes no identity commitments.** Identity is data the matching pipeline produces over time, with full provenance. A canonical-person view can be derived later from `same_entity_as` clusters if query ergonomics demand it (see Consequences); the storage layer is per-source records, not collapsed persons.

7. **Resolution policy is per-predicate, fail-loud by default.** When a downstream consumer (UI, search index, enrich asset) needs a single value and the graph carries competing claims, a per-predicate resolution rule decides which to surface (e.g. "for `reign_start_bce`, Beckerath > Hornung > Leprohon"; "for `hapi:display_name`, prefer the most recent curator-decision Source"). If no rule is committed for a predicate, the query **fails loud** — the consumer must specify a rule or accept the full claim set. This aligns with Rule 2: no silent arbitrary picks; every resolution traces to a documented policy.

### Display name migration — first concrete application of the resolution policy

The canonical display name (ADR-016 "Conventional English Display Form" — "Khufu" not "Cheops", "Amenhotep III" not "Amenophis III") is the first per-predicate resolution policy committed to the registry. It also serves as the template for future per-predicate policies.

**Model.** All display-name claims — Leprohon's "Amenhotep III", Beckerath's "Amenophis III.", and the curator's canonical choice — share the **same predicate type** (`:E55 Type {id: 'hapi:display_name'}` linked via P177). They are differentiated by their actor + document:
- Leprohon's claim: `P14 → :E21 Person {id: 'leprohon_rj'}` and `P70i → :E31 Document {id: 'leprohon_2013'}`.
- Curator claim: `P14 → :E74 Group {id: 'hapi_curatorial'}` and `P70i → :E31 Document {id: 'hapi_display_names_2026_05', kind: 'curator_decision_batch'}`.

Predicates describe *what* the claim is about; the actor + document describe *who said it where* — keeping the canonical-vs-source-original distinction in provenance rather than predicate preserves the uniform claim model.

**Document granularity.** Curatorial decisions are batched by date: one `:E31 Document {kind: 'curator_decision_batch'}` per batch (`hapi_display_names_2026_05`, `hapi_display_names_2027_q1`, …), each carrying a `decided_at` timestamp and a free-text `rationale`. When a spelling is revised, a new Document is created and the old claim stays attached to its original Document as audit trail.

**Resolution rule for `hapi:display_name`**:
1. Prefer the Statement whose `P70i_is_documented_in` document has `kind = 'curator_decision_batch'` and the most recent `decided_at`.
2. Else: **fail loud** — no fallback to publication-documented Statements.

Consequences of fail-loud: rulers added by a future source-loader before a curator reviews them are unrenderable until the curator decision arrives. This is intentional — the gap surfaces in the review queue immediately, rather than hiding behind a placeholder.

**Migration.** Initial load: a curator-decision-batch document `hapi_display_names_2026_05` is created, citing ADR-016's spelling list as its source of truth. For every ruler with an existing per-source row, one Statement is produced with the canonical Anglicised form (per ADR-016) as its value, `P14_carried_out_by → :E74 Group {id: 'hapi_curatorial'}`, and `P70i_is_documented_in → :E31 Document {id: 'hapi_display_names_2026_05'}`. The seed spelling list lives in version control as `pipeline/pipeline/authority/curator_decisions/hapi_display_names_2026_05.json` (exact path resolved during loader implementation); ADR-016 is cited rather than duplicated.

**Effect on ADR-016.** ADR-016 is partially superseded: the storage shape it implied (a flat `rulers.json` with one canonical display name per row) is replaced by the claim-graph form. The spelling list itself lives on as the migration seed for the initial `hapi_display_names_2026_05` curator-decision-batch document. ADR-016's substantive content — which spelling to prefer for each ruler and why — remains the authoritative reference cited by that document's `rationale` field.

### Schema sketch

Every claim is an E13 Statement carrying exactly five canonical CIDOC edges (with at most one additional `hapi:derived_by` edge for matcher-attributed claims):

| # | Edge                                  | Target type         | Required |
|---|---------------------------------------|---------------------|----------|
| 1 | `P140_assigned_attribute_to`          | the subject entity  | always |
| 2 | `P141_assigned`                       | the value entity    | always (an E1 entity, never a literal) |
| 3 | `P177_assigned_property_of_type`      | `:Type` (E55)       | always — the predicate type |
| 4 | `P14_carried_out_by`                  | `:Person`/`:Group`  | for human-attributed claims |
| 4'| `hapi:derived_by`                     | `:Matcher`          | for matcher-attributed claims (deviation; replaces P14 for software agents) |
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

// (2) An entity-valued claim — dynasty membership. Value is the Dynasty (E4 Period) node directly.
(:Statement:E13)
  -[:P140_assigned_attribute_to]->    (:Ruler {leprohon::leprohon-5.07})
  -[:P141_assigned]->                  (:Dynasty:E4_Period {number: 5})
  -[:P177_assigned_property_of_type]-> (:Type:E55 {id: 'hapi:belongs_to_dynasty'})
  -[:P14_carried_out_by]->             (:Person:E21 {id: 'leprohon_rj'})
  -[:P70i_is_documented_in]->          (:Document:E31 {id: 'leprohon_2013'})

// (3) A reign-date claim. Value is an E52 Time-Span (begin/end via P82a/P82b inlined as props).
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

// (4) A cross-source identity claim attributed to a matcher RUN (declared deviation —
//     no P14 to an E39 Actor; hapi:derived_by points at the :MatcherRun that produced
//     this Statement, which references the algorithm-level :Matcher catalogue entry).
//     Confidence is a property of the Statement; the run carries the reproducibility
//     metadata (input commit, parameter hash, timestamp, reviewer status) so any
//     score can be regenerated or rejected.
(:Statement:E13 {confidence: 0.94})
  -[:P140_assigned_attribute_to]->    (:Ruler {leprohon::leprohon-5.07})
  -[:P141_assigned]->                  (:Ruler {beckerath::05.07})
  -[:P177_assigned_property_of_type]-> (:Type:E55 {id: 'hapi:same_entity_as'})
  -[:hapi:derived_by]->                (:MatcherRun {
                                           run_id:               'matcher_run_2026_05_17T14_22Z',
                                           matcher_id:           'normalized_name_v1',
                                           matcher_version:      '0.1.0',
                                           input_dataset_commit: 'a8f3e9d...',
                                           parameters_hash:      'sha256:7c4...',
                                           started_at:           '2026-05-17T14:22:31Z',
                                           completed_at:         '2026-05-17T14:24:08Z',
                                           reviewer_status:      'pending'
                                                                  // pending | approved | rejected | superseded
                                       })
                                           -[:hapi:uses_matcher]-> (:Matcher {id: 'normalized_name_v1',
                                                                              version: '0.1.0',
                                                                              algorithm: 'lowercase+strip_diacritics+token_match',
                                                                              hyperparameters_json: '{"min_dynasty_match": true}'})

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

// Matcher catalogue and run records (Hapi-only; outside CRM)
//   :Matcher    — the algorithm definition (what code, what version, what hyperparameters)
//   :MatcherRun — a specific execution that produced one or more Statements (when, on what
//                 input commit, with what parameter hash, current reviewer status)
// Every confidence/score on a derived Statement is reproducible by replaying the
// MatcherRun against its input_dataset_commit with its parameters_hash.
(:Matcher    {id, version, algorithm, hyperparameters_json})
(:MatcherRun {run_id, matcher_id, matcher_version,
              input_dataset_commit, parameters_hash,
              started_at, completed_at,
              reviewer_status, reviewer_id, reviewed_at})
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
| `value_class`         | CIDOC E-class or set       | e.g. `E41 Appellation` for `hapi:horus_name`; `E4 Period` for `hapi:belongs_to_dynasty`; `E21 Person` for `hapi:same_entity_as` |
| `value_cardinality`   | `single` \| `multi`        | whether a subject can have one or many active claims of this predicate |
| `crm_nearest`         | CIDOC P-number \| `null`   | nearest CIDOC property for interop documentation; `null` if no clean fit |
| `is_symmetric`        | bool                       | whether the predicate is symmetric (e.g. `hapi:same_entity_as` is) |
| `notes`               | string \| `null`           | rationale, scope notes, known edge cases |

Adding a new predicate is an INSERT into this registry preceded by a review against existing predicates to avoid `buried_in` / `interred_at` / `tomb_location` vocabulary drift. The registry is committed to version control (`pipeline/pipeline/authority/predicate_registry.json` — exact path resolved during implementation) and validated by a CI test that loads each entry and asserts every required field is populated and that referenced E-classes exist in the class catalogue.

### What this does not decide

- **Storage technology** — Postgres (with relational encoding of the graph, or with the Apache AGE extension) and Neo4j (self-hosted Community or Aura managed) are the two viable candidates. A separate ADR will resolve this based on the pilot evidence accumulated under this model. Until then, the conceptual model is binding; the storage substrate is open.
- **The relational vs property-graph encoding of E13.** Whether Statements are tables with FK columns or first-class graph nodes follows from the storage choice. Both encodings preserve the CIDOC mapping above; specifying the encoding before the storage ADR pre-decides storage.
- **Per-predicate resolution policies beyond `hapi:display_name`** — the *default* is fail-loud (principle 7); the *first concrete policy* is committed above for `hapi:display_name`. Additional per-predicate rules (which document wins for `hapi:reign_start_bce`, `hapi:belongs_to_dynasty`, etc.) accumulate in the policy registry as downstream consumers demand them. The registry's exact location and review process is a follow-up ADR.
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

Consider an artifact carrying "Thutmose, KV43, Dynasty 18." Among the four Dynasty 18 Thutmoses (I, II, III, IV), KV43 is securely the tomb Thutmose IV commissioned and was originally buried in. A query against `hapi:original_burial = KV43 AND hapi:dynasty = 18` collapses the candidate set to one before name matching runs.

The example also illustrates why tomb references demand careful predicate granularity. "Tomb" is not one relationship: it is at least three, each of which can disagree.

- `hapi:tomb_owner` — the ruler the tomb was commissioned for. Stable across cache reburials.
- `hapi:original_burial_in` — the ruler whose body was first interred there. Usually but not always the same as the owner.
- `hapi:cache_context_at` — the location of a *secondary* burial, typically the Dynasty 21 priestly reburials at KV35 (Amenhotep II's tomb, used as a cache for many other Dynasty 18 and 19 royals) and TT320/DB320 (the Deir el-Bahari royal cache).

A naive `hapi:buried_in` predicate that conflates these three loses information and produces wrong matches: a stela of Ramesses I found in the KV35 cache is not evidence that Ramesses I owned, was originally buried in, or has any primary association with KV35 — it was moved there ~400 years after his death. The open schema accommodates the distinction natively; rigorous matching demands it. The Haiku step becomes a fallback for genuinely ambiguous cases (overlapping co-regencies, post-burial usurpations, ambiguous cache attributions), not the primary disambiguation mechanism.

A follow-up ADR will revise ADR-009 to specify the constraint-narrowed algorithm in detail once storage tech is decided.

## Consequences

- **Phase 0 output shape changes.** Sources still produce `reconciled.jsonl`, but the downstream loader emits per-source E13 Statements, not collapsed per-entity rows. The 3-agent extraction step's job is unchanged (faithful capture of the source); per-row resolution still follows the Rule-2 decision tree (unanimity / majority / `tie-break-overrides.json` / documented policy) — the loader trusts whatever the existing pipeline emits and never re-resolves at the graph layer.
- **Reconciliation semantics change.** "Reconciliation" no longer means "pick one value across sources"; it means "load all sources' claims into the graph and let the resolution policy (per-predicate, per-consumer) decide what to surface." The current `tie-break-overrides.json` becomes Statement-level reviewer rationale with citation metadata, joined to the Statements it justifies.
- **Disagreements become first-class artifacts.** The UI can honestly show "1353–1336 BCE (Leprohon 2013) / 1352–1335 BCE (Dodson-Hilton 2010)" instead of pretending certainty it doesn't have. Authority disagreements appear in search snippets, hover cards, and the artifact detail page.
- **Cross-source identity becomes data, not a structural primitive.** Adding a new source (Hornung, Kitchen, Ryholt) does not require re-curation of existing entities. It adds per-source nodes that get linked to existing nodes via `hapi:same_entity_as` Statements — automated (matcher-attributed) where confident, queued for human review (curator-attributed when approved) otherwise. A canonical-person view, if needed, can be derived from `same_entity_as` clusters as a materialized view; the source of truth remains the per-source nodes plus their identity claims.
- **The predicate registry becomes the vocabulary contract.** Any new relationship type proposed by an agent, a Phase 0 chunk, or a contributor must be reviewed against the registry. The CI check is FK-enforced at the DB layer; convention is not enough.
- **Citation network becomes queryable.** Citation tokens currently buried as text inside Leprohon's `source_note` fields (referencing Beckerath 1999, Gauthier 1907, Wilkinson 2000, etc.) become explicit edges from Statements to Citation nodes, queryable as "claims about Akhenaten that cite Wilkinson" or "what does Leprohon cite that we have no authority data for." (Specific counts intentionally omitted: a reproducible script for inventorying citation tokens and attestation entries across sources is a Proposed → Accepted prerequisite alongside the cross-source overlap pilot.)
- **`attested_in` becomes the bridge to artifacts.** Attestation entries currently nested inside Leprohon name qualifiers become explicit edges from Name Statements to Inscription / Artifact nodes, linking the authority layer to the museum layer at the data level.
- **Temporal phases gain structure without canonicalisation.** Leprohon's split of Akhenaten into "Amenhotep IV (Regnal Years 1 to 5)" + "Akhenaten (Regnal Years 5 to 17)" produces two per-source `:Ruler` nodes (two rows in Leprohon, two nodes in the graph). They are linked by a `hapi:same_entity_as` Statement attributed to the source itself — Leprohon's text explicitly identifies the two as a single ruler at different naming phases. Each `:Ruler` carries its own `hapi:reign_period` Statement covering the relevant regnal years. Beckerath's single "Amenophis IV. Ach-en-aten" row becomes a third per-source `:Ruler` node, linked to either of the Leprohon nodes via a separate cross-source `hapi:same_entity_as` Statement (curator-attributed once reviewed; matcher-attributed in the interim). No canonical Person is materialised at load time; the "same person, different naming period" structure is data, not schema.
- **The storage decision is the gating follow-up.** Until ADR-019 (or the storage ADR, whatever number it lands at) is resolved, no production graph build can start. A Phase 0 → graph loader can be sketched against either substrate.
