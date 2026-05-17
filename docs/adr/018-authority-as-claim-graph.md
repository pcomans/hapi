# ADR-018: Authority Layer as Source-Attributed Claim Graph

## Status
Proposed

## Context

The authority layer (rulers, dynasties, periods, sites, and their interrelationships) is currently shaped as flat per-entity JSON files: `rulers.json` carries one row per ruler with a `display_name`, `dynasty_id`, `dates`, `titulary`, `aliases`. ADR-012 commits the source list (Leprohon, Beckerath, Dodson-Hilton, Porter-Moss, pharaoh.se); the Phase 0 playbook produces one `reconciled.jsonl` per source by a 3-agent extraction + reconciliation pipeline.

Four problems with the current shape have surfaced as the layer approaches completion:

1. **Reconciliation silently picks winners across sources.** When Leprohon and Dodson-Hilton disagree on a reign date, one is dropped. The Phase 0 reconciliation step produces a single "winning" value, baked into one entity per ruler. This violates Rule 2 (no silent arbitrary picks) at the cross-source layer: the resolution rule isn't documented as deterministic. It is also bad scholarship — Egyptological disagreement is normal content to expose, not vandalism to resolve.

2. **Domain relationships aren't first-class.** Co-regency, succession, "buried in," "shares tomb with," dynastic family — these are graph-shaped facts squashed into flat fields (`ruler_ids: []` arrays for joint reigns) or implicit conventions. Adding a new relationship type requires a schema change.

3. **Provenance is implicit.** Each authority file traces to a source as a whole, but individual *facts* don't carry per-claim citations. The reviewer-cited rationale in `tie-break-overrides.json` (1,847 lines for Leprohon alone) sits structurally disconnected from the reconciled rows it justifies.

4. **The matching pipeline (Phase B) needs richer queries against authority.** ADR-009's Stage 2 fuzzy fallback is "Haiku triage with artifact context" without specifying a mechanism. Constraint-narrowed matching — "find rulers buried in KV34 in Dynasty 18" against an unknown name — requires structured graph queries that flat JSON can't serve cheaply.

A pilot load of Leprohon (395 rows) + Beckerath (166 rows) into Neo4j Aura (May 2026) confirmed: of ~166 potential cross-source ruler overlaps, only 11 match exactly after light normalization. Leprohon's English forms ("Amenhotep III", "Thutmose III") and Beckerath's German forms ("Amenophis III.", "Tuthmosis III.") name the same rulers differently. Cross-source identity is a substantive scholarly claim, not a string-equality coincidence.

## Decision

The authority layer is modeled as a **source-attributed claim graph** following the CIDOC CRM E13 Attribute Assignment pattern. Every fact about an authority entity is reified as a Statement node connecting subject to value, carrying the source that asserted it. Disagreements between sources are preserved as parallel Statements, not collapsed at reconciliation time.

### Core principles

1. **Every claim has a provenance edge.** No fact lives in the graph without an attribution to who made the claim. Publications and human curators are CIDOC `:Source` nodes (E39 Actor), attributed via `P14_carried_out_by`. Automated processes — matchers, alias-expanders, derivation rules — are `:Matcher` nodes (non-CIDOC; outside the E39 Actor hierarchy because they aren't agents in the CIDOC sense), attributed via a Hapi-namespaced `hapi:derived_by` edge. The edge type itself encodes the trust difference: a Statement with `P14_carried_out_by → :Source` carries human-scholarly weight; a Statement with `hapi:derived_by → :Matcher` carries computational-derivation weight. UI, search index, and review workflows can filter by edge type without parsing a `type` property.

2. **Cross-source disagreements are preserved.** When Leprohon claims reign-start −1390 and Dodson-Hilton claims −1391 for the same ruler, two Statements with the same predicate and different values coexist, each tracing to its source. Reconciliation does not pick a winner at the data layer. The resolution policy (which one a downstream consumer sees) is per-predicate and lives outside the graph — see principle 7.

3. **Per-agent disagreements are extraction artifacts, not data.** The 3-arbiter blind-extraction process is a quality gate on faithfulness to the source. If agents disagree, the source-chunk is iterated (re-extract, re-prompt, human page read) until convergence. Agent-level structure must never appear in the graph — it is pipeline scaffolding.

4. **Open schema, enforced registry.** Predicates and relationship types are *data*, not DDL. Adding `hapi:shares_tomb_with` is an INSERT into the predicate registry, not a migration. The registry is the verify-before-create enforcement point: every Statement's `predicate` is FK-validated against it (Rule 3 — deterministic enforcement over convention). No agent or contributor invents a predicate; a new one is proposed against the registry, reviewed for overlap with existing predicates, and added once.

5. **Statement values are literal OR entity references.** A claim like "Narmer's Horus name is 'nar mer'" stores the value as a literal property on the Statement. A claim like "Narmer belongs to Dynasty 0" stores the value as a `P141_assigned` edge from Statement to the Dynasty node. This is exactly CIDOC's P141 design — P141 accepts either a Literal or any E1 CRM Entity reference. Entity-valued claims enable graph traversal ("show me every claim that touches Dynasty 0"); literal-valued claims keep self-contained scalars (names, dates, transliterations) compact.

6. **Identity across sources is itself a claim — no canonical Person at load time.** Each source's row is stored as its own per-source entity node (`:Ruler`, `:Site`, etc.), keyed by source + source-row-id. Cross-source co-reference ("Leprohon's row for Unas is the same person as Beckerath's row for Unas") is modeled as a Statement with predicate `hapi:same_entity_as`, `P141_assigned` pointing at the other entity, and a provenance edge attributing the claim — `P14_carried_out_by` for a human curator decision, `hapi:derived_by` for an automated matcher. **The loader makes no identity commitments.** Identity is data the matching pipeline produces over time, with full provenance. A canonical-person view can be derived later from `same_entity_as` clusters if query ergonomics demand it (see Consequences); the storage layer is per-source records, not collapsed persons.

7. **Resolution policy is per-predicate, fail-loud by default.** When a downstream consumer (UI, search index, enrich asset) needs a single value and the graph carries competing claims, a per-predicate resolution rule decides which to surface (e.g. "for `reign_start_bce`, Beckerath > Hornung > Leprohon"; "for `display_name`, prefer the curator-decision Source"). If no rule is committed for a predicate, the query **fails loud** — the consumer must specify a rule or accept the full claim set. This aligns with Rule 2: no silent arbitrary picks; every resolution traces to a documented policy.

### Schema sketch

Predicates use CIDOC CRM property IDs as primary identifiers (`P14_carried_out_by`, `P140_assigned_attribute_to`, `P141_assigned`) where the CIDOC standard has a clean fit. Hapi-domain predicates use a `hapi:` namespace (`hapi:same_entity_as`, `hapi:buried_in`, `hapi:derived_by`) where CIDOC has no direct equivalent. The predicate registry carries CIDOC IDs natively; Hapi predicates carry a `crm_nearest` field linking to the closest CIDOC property for interop reference, when one exists.

CIDOC edge directions are preserved. CIDOC's E13 is the Statement; P140 goes Statement → subject, P141 goes Statement → value, P14 goes Statement → Source actor.

```
// Per-source entity node (one per source row, no canonical Person)
(:Ruler {key: 'leprohon::leprohon-5.07', source: 'leprohon', display_name: 'Unas', ...})

// A literal-valued claim about that Ruler, attributed to a publication
(:Statement {
    predicate: 'hapi:horus_name',
    value: 'wnis'                         ← literal, lives on Statement node
})
  -[:P140_assigned_attribute_to]-> (:Ruler {leprohon::leprohon-5.07})
  -[:P14_carried_out_by {cited_page, cited_pdf_page}]-> (:Source {id: 'leprohon_2013'})

// An entity-valued claim — dynasty membership pointing at the Dynasty node
(:Statement {predicate: 'hapi:belongs_to_dynasty'})
  -[:P140_assigned_attribute_to]-> (:Ruler {leprohon::leprohon-5.07})
  -[:P141_assigned]->              (:Dynasty {number: 5})
  -[:P14_carried_out_by]->         (:Source {id: 'leprohon_2013'})

// Cross-source identity claim, attributed to an automated matcher
(:Statement {predicate: 'hapi:same_entity_as', confidence: 0.94})
  -[:P140_assigned_attribute_to]-> (:Ruler {leprohon::leprohon-5.07})
  -[:P141_assigned]->              (:Ruler {beckerath::05.07})
  -[:hapi:derived_by]->            (:Matcher {id: 'normalized_name_v1', version: '0.1.0', method: 'name+dynasty'})

// Backbone reference nodes — shared across sources
(:Dynasty {number, beckerath_label, leprohon_chapter})
(:Period  {id})
(:Site    {id})

// Source kinds (CIDOC E39 Actor)
(:Source {id: 'leprohon_2013',         type: 'publication', citation, year, language})
(:Source {id: 'hapi_curator_2026_05',  type: 'curator_decision', curator, decided_at, rationale})

// Matcher kinds (Hapi-only; outside CIDOC E39)
(:Matcher {id, version, algorithm, hyperparameters_json})
```

Page-level citation lives as properties on the `P14_carried_out_by` edge (not on the Statement node) — same place CIDOC E13 carries P3 `has_note` and P4 `has_time-span`.

### Predicate registry

Predicates form a committed registry (`pipeline/pipeline/authority/predicates.json` or equivalent) listing each predicate with: name, CIDOC equivalent (where applicable), description, allowed subject types, allowed object types, value type (literal or entity). The registry is the FK target for every Statement. Adding a new predicate requires a review against existing predicates to avoid `buried_in` / `interred_at` / `tomb_location` vocabulary drift. CIDOC properties are referenced as `P14`, `P140`, `P141`, etc. directly; Hapi-specific predicates use the `hapi:` prefix and carry a `crm_nearest` link to the closest CIDOC property when one exists.

### What this does not decide

- **Storage technology** — Postgres (with relational encoding of the graph, or with the Apache AGE extension) and Neo4j (self-hosted Community or Aura managed) are the two viable candidates. A separate ADR will resolve this based on the pilot evidence accumulated under this model. Until then, the conceptual model is binding; the storage substrate is open.
- **Migration of ADR-016 (Conventional English Display Form)** — ADR-016 currently mandates a single canonical display name per ruler in `rulers.json`. In the claim-graph model that file doesn't exist; per-source `display_name` Statements live as data. Where the canonical English form lives (curator-decision Source, derived rule, or pure UI-side rendering) is a follow-up decision that will likely supersede part of ADR-016.
- **Per-predicate resolution policies** — the *default* is fail-loud (principle 7). The *committed* per-predicate rules (which Source wins for `reign_start_bce`, etc.) are a registry that grows alongside the graph; a follow-up ADR will define the registry's location and review process.
- **Phase C feedback cadence** — when an approved fuzzy match in the review queue produces a new alias, when does the alias get added as a claim? Per-approval, batched, or blocked until a Phase B pass completes? Tracked in #221.

## Storage candidates (deferred)

Two viable candidates, evaluated against the model above. A follow-up ADR will choose between them.

### Postgres (relational encoding or with Apache AGE)

- **Pro:** ADR-004 + ADR-011 already commit Postgres as canonical store. SQLAlchemy + Alembic + Drizzle introspection toolchain is already wired up. Artifacts (millions, property-heavy, search-driven) stay in Postgres; authority graph in the same database keeps artifact ↔ authority joins as single-DB SQL. No new ops surface. Apache 2.0 license, no per-GB pricing.
- **Pro:** Predicates-as-rows pattern gives FK-enforced verify-before-create with zero migrations per new predicate.
- **Con:** Multi-hop graph traversals are recursive CTEs (workable for 1–2 hops, ugly at depth). No native graph visualization (Bloom-equivalent).
- **AGE variant:** First-class Cypher inside Postgres; trades native graph storage performance at depth + `pg_upgrade` friction.

### Neo4j (Aura managed or self-hosted Community)

- **Pro:** Native graph storage = O(1) per traversal hop. CIDOC CRM has a published Neo4j implementation (`diging/cidoc-crm-neo4j`) and a substantial heritage-research community using exactly this pattern. Cypher is more readable than SQL for the queries we'd actually write. Graph Data Science library gives node embeddings + similarity + community detection natively (relevant for constraint-narrowed matching, ADR-009 Stage 2).
- **Pro:** Aura Free tier (200K nodes / 400K relationships) fits the authority layer comfortably and lets the pilot run at zero cost.
- **Con:** Dual-store with Postgres-resident artifacts violates Rule 4 head-on; every match operation becomes a cross-system call. Aura Professional pricing is real money (~$25K–$50K/year at production memory sizing). Community Edition AGPLv3 + restrictive additional terms are murky for a public artifact index. Drizzle / SQLAlchemy / Alembic don't apply.

The trade hinges on whether artifacts move into the graph (architecturally cleanest but expensive and reverses ADR-004) or stay in Postgres (introduces the dual-store cost). The choice ADR will resolve this.

## Implications for matching (ADR-009)

The graph reshapes Stage 2 of the matching algorithm. Today: fuzzy string distance over all aliases, with Haiku triage for context. With this model: **constraint-narrow the candidate set via graph queries, then match name against the narrowed set.** For an artifact carrying "Princess Bubblegum, KV34, Dynasty 18," the graph answers "rulers where `buried_in = KV34 AND dynasty = 18`" with a small candidate set (often size 1); name matching reduces to that set rather than the full authority. The Haiku step becomes a fallback for genuinely ambiguous cases, not the primary disambiguation mechanism.

A follow-up ADR will revise ADR-009 to specify the constraint-narrowed algorithm in detail once storage tech is decided.

## Consequences

- **Phase 0 output shape changes.** Sources still produce `reconciled.jsonl`, but the downstream loader emits per-source Statements, not reconciled per-entity rows. The 3-agent extraction step's job is unchanged (faithful capture of the source); the convergence rate becomes a quality gate — rows where agents diverge are flagged for re-extraction, not silently tie-broken.
- **Reconciliation semantics change.** "Reconciliation" no longer means "pick one value across sources"; it means "load all sources' claims into the graph and let the resolution policy (per-predicate, per-consumer) decide what to surface." The current `tie-break-overrides.json` becomes Statement-level reviewer rationale with citation metadata, joined to the Statements it justifies.
- **Disagreements become first-class artifacts.** The UI can honestly show "1353–1336 BCE (Leprohon 2013) / 1352–1335 BCE (Dodson-Hilton 2010)" instead of pretending certainty it doesn't have. Authority disagreements appear in search snippets, hover cards, and the artifact detail page.
- **Cross-source identity becomes data, not a structural primitive.** Adding a new source (Hornung, Kitchen, Ryholt) does not require re-curation of existing entities. It adds per-source nodes that get linked to existing nodes via `hapi:same_entity_as` Statements — automated (matcher-attributed) where confident, queued for human review (curator-attributed when approved) otherwise. A canonical-person view, if needed, can be derived from `same_entity_as` clusters as a materialized view; the source of truth remains the per-source nodes plus their identity claims.
- **The predicate registry becomes the vocabulary contract.** Any new relationship type proposed by an agent, a Phase 0 chunk, or a contributor must be reviewed against the registry. The CI check is FK-enforced at the DB layer; convention is not enough.
- **Citation network becomes queryable.** The 793 citation tokens currently buried as text inside Leprohon's `source_note` fields (referencing Beckerath 1999, Gauthier 1907, Wilkinson 2000, etc.) become REFERENCES edges from Statements to Citation nodes, queryable as "claims about Akhenaten that cite Wilkinson" or "what does Leprohon cite that we have no authority data for."
- **`attested_in` becomes the bridge to artifacts.** The 658 attestation entries currently nested inside name qualifiers become explicit edges from Name Statements to Inscription / Artifact nodes, linking the authority layer to the museum layer at the data level.
- **Temporal phases gain structure.** Leprohon's split of Akhenaten into "Amenhotep IV (Regnal Years 1 to 5)" + "Akhenaten (Regnal Years 5 to 17)" becomes one Person with two NamingPhase Records connected by `:WAS_KNOWN_AS` edges with year-range qualifiers. Beckerath's single "Amenophis IV. Ach-en-aten" row attaches to the same Person. The "same person, different naming period" structure is no longer flattened.
- **The storage decision is the gating follow-up.** Until ADR-019 (or the storage ADR, whatever number it lands at) is resolved, no production graph build can start. A Phase 0 → graph loader can be sketched against either substrate.
