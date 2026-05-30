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

The authority layer is modeled as a **source-attributed claim graph** following the CIDOC CRM E13 Attribute Assignment pattern. Every fact about an authority entity is reified as an E13 Statement node carrying the universally-required `P140` (subject) / `P141` (value) / `P177` (predicate type) spine, plus a provenance shape that varies by claim kind. **Human-documentary claims** additionally carry `P14_carried_out_by → E39 Actor` (the scholar or curatorial body) plus `P70i_is_documented_in → E31 Document` (the publication or decision batch). **Machine-derived claims** (matcher-derived candidate identity claims and the stage-2 LLM-reviewer verdicts that gate them) instead carry `hapi:derived_by_run → :MatcherRun:D10` to the CRMdig Software Execution that produced them; they never carry P14 or P70i (matcher provenance is algorithmic, not documentary, and the design has no human-review step). Disagreements between sources are preserved as parallel Statements, not collapsed at reconciliation time.

### CIDOC alignment

**Conformance target: CIDOC CRM 7.1.3 + CRMdig 5.0.** Both specifications, in their conceptual *and* official RDFS-encoding forms, are normative for Hapi. Precise picture in three parts:

1. **CIDOC CRM is a conceptual model; the conformance contract is at the conceptual level, not at the storage layer.** CIDOC explicitly names RDF, relational, object-oriented, JSON-LD, XML, and OWL as valid encodings — any formal encoding that preserves CRM classes, properties, and inheritance is conformant, provided a deterministic lossless transform to a standard encoding exists. The CIDOC RDFS file's own preamble disclaims authority on encoding ("not a definition of the CIDOC CRM, but a compatible implementation of an RDF Schema") for precisely this reason.
2. **Hapi's property graph is a CIDOC-compatible internal encoding of a CIDOC/CRMdig + Hapi-extension conceptual graph; the strict CIDOC RDF serialisation is the export.** The in-store encoding uses property-graph idioms (literals as node attributes, type tags as inline strings, edge properties for citation locators) for compactness. The strict-RDF export materialises the canonical CIDOC RDF triples; the loader specification owns the deterministic, lossless mapping. **The store is CIDOC-conformant by design**, not by export — the export emits a different *syntax* for the same conceptual content. Encoding conventions are documented in the "Property-graph encoding conventions and CIDOC RDF serialisation mappings" section below; the (currently empty) "Conceptual deviations from CRM/CRMdig" subsection is the contract for what a real conceptual departure would look like if one were ever introduced.
3. **Hapi extensions need the manifest to be interpretable.** A strict reader that has loaded `hapi_extension.rdf` alongside the CRM and CRMdig RDFS files applies its `rdfs:subClassOf` / `rdfs:subPropertyOf` declarations and interprets Hapi-extended terms (`hapi:MatcherRun`, `hapi:derived_by_run`, `hapi:same_entity_as`) through their declared CRM/CRMdig parents. A strict reader that has *not* loaded the manifest retains those Hapi-namespaced triples opaquely — it sees them as unrecognised URIs and does not reason on them. **Hapi predicates without a declared `subPropertyOf` remain opaque to CRM/CRMdig vocabulary** even with the manifest loaded — the manifest documents their existence but doesn't relate them to any CIDOC vocabulary. This is independent of OWL typing: e.g. `hapi:shares_tomb_with` is declared `owl:SymmetricProperty`, which an OWL-aware reader uses to infer the inverse direction (a non-CIDOC behavior), but the predicate still has no CIDOC interpretation because it carries no `subPropertyOf` declaration. CIDOC-opacity and OWL-behavior are independent properties of a Hapi predicate.

The graph data itself is identical across reader configurations; what differs is the interpretation. See the Hapi extension manifest section below for the manifest contents.

Both specifications are vendored in-repo at `pipeline/pipeline/authority/spec/` (see the README in that directory):

| Specification | Version | Authoritative release | Vendored |
|---|---|---|---|
| Core CIDOC CRM | 7.1.3 | https://cidoc-crm.org/Version/version-7.1.3 | `cidoc_crm_v7.1.3.html` + `cidoc_crm_v7.1.3.rdf` |
| CRMdig (digital-provenance extension) | 5.0 | https://cidoc-crm.org/crmdig/ModelVersion/crmdig-v5.0 | `crmdig_v5.0.html` + `crmdig_v5.0.rdf` |

For each, the HTML release is the semantic authority (scope notes, conceptual ranges); the RDFS encoding is the syntactic authority for what's actually emitted (`rdfs:domain`, `rdfs:range`, IS-A chains, including RDFS-only refinements like P82a/P82b that the conceptual document doesn't enumerate). They rarely disagree; when they do, the HTML wins on semantic intent and the RDFS wins on syntactic encoding. Pin moves are atomic — replacing a vendored file and bumping the pin happen in the same commit.

**Why CRMdig.** The matcher provenance use-case (a piece of software runs against input data and produces output assertions) is exactly what CRMdig's D-class hierarchy was built for. Modelling matcher runs with core CRM alone forced either an awkward fit (treating software as `E74 Group`) or a real deviation (`:Matcher` as a non-CRM node). CRMdig has purpose-built classes (D10 Software Execution, D14 Software, D1 Digital Object) that fit natively. Adopting CRMdig retires those workarounds.

(CRMdig also has a tighter class, D3 Formal Derivation, for derivations that produce a "different form" of the same digital object — colour corrections, resizing, format conversions. We use D10 not D3 because a matcher producing identity assertions is not producing a "version of" the source data, it's producing different *information*. D10 Software Execution is the correct general parent.)

#### Node-type mapping from Hapi labels to CRM / CRMdig classes

| Hapi label              | Class                          | Notes |
|-------------------------|--------------------------------|-------|
| `:Ruler`                | E21 Person                     | **Deliberate Hapi row-level projection.** One node per source row, regardless of whether the source asserts the rows are same-person (Leprohon's two-phase Akhenaten entries) or whether identity across sources is genuinely doubtful. Both cases produce per-source-row E21 nodes; `hapi:same_entity_as` Statements then connect them — attributed to the source itself (intra-source same-person assertions) or to a matcher / curator (cross-source identity claims). This is a row-faithful projection convention, not a CIDOC mandate — CIDOC's E21 scope permits multiple E21 instances when identity is doubtful, but the phase-row case is not identity doubt and we use the same shape there anyway because preserving source-row structure outweighs collapsing intra-source same-person at load time. No canonical Person is materialised at load time. |
| `:Site`                 | E27 Site                       | Physical archaeological place. |
| `:Dynasty`              | E4 Period                      | The Egyptological dynastic period bucket — a chronological band, not a ruling family/house and not a contemporary social institution. Numbered dynasties 1–31 derive from Manetho's tradition; Dynasty 0 is a 20th-century scholarly periodisation grouping pre-unification kings (Narmer-precursors). Both are covered here as Egyptological constructs. Membership is via `hapi:in_dynastic_period` (chronological). Family-lineage and ruling-house modelling are out of scope; if needed they get their own predicate(s) targeting `:E74 Group`. |
| `:Statement`            | E13 Attribute Assignment       | Each claim is its own E13. |
| `:Person`               | E21 Person                     | A scholar or human curator (the actor of an E13). |
| `:Group`                | E74 Group                      | Curatorial bodies, learned societies. |
| `:Document`             | E31 Document                   | Publications, decision-batch records, authority releases. |
| `:Appellation`          | E41 Appellation                | Name-shaped value entity; literal accessed via P190. Type-classified via `P2_has_type → :E55 Type`. |
| `:TimeSpan`             | E52 Time-Span                  | Date-shaped value entity. Conceptual CRM uses P81 / P82 (range E61 Time Primitive); the RDFS implementation refines them to P81a / P81b / P82a / P82b with `rdfs:Literal` range. The property-graph stores boundary literals on the node; exports use the RDFS refinements. See encoding convention #3. |
| `:Dimension`            | E54 Dimension                  | Numeric measurement; P90 / P91. |
| `:Type`                 | E55 Type                       | The predicate registry; targets of P177. |
| `:MatcherRun`           | **D10 Software Execution** *(CRMdig)* | The specific execution of a software run: deterministic matcher OR LLM reviewer — both are D10 instances. IS-A chain: D10 ⊂ D7 Digital Machine Event ⊂ E11 Modification & E65 Creation ⊂ E7 Activity. (Not D3 Formal Derivation — D3's scope is restricted to derivations producing a "different form" of the same digital object; matcher output is different *information*, not a different form.) Carries run-reproducibility metadata as Hapi-namespaced properties (run_id, parameters_hash, started_at, completed_at). No verdict / review fields on MatcherRun itself — verdicts are their own E13s pointing at the matcher's E13 via P140 (see schema sketch case 4b). |
| `:MatcherAlgorithm`     | **D14 Software** *(CRMdig)* | The matcher algorithm definition (e.g. `normalized_name_v1`): the code/procedure that gets executed. IS-A chain: D14 ⊂ D1 Digital Object ⊂ E73 Information Object. Long-lived; many `:MatcherRun` instances reference one `:MatcherAlgorithm`. |
| `:SourceData`           | **D1 Digital Object** *(CRMdig)* | A reconciled.jsonl file (or other digital input) consumed by a matcher run. IS-A chain: D1 ⊂ E73 Information Object. |

#### Edge spine

Every E13 Statement carries a universally-required triad — P140 (subject), P141 (value), P177 (predicate type) — plus provenance edges that vary by claim type. **Human-documentary** claims carry P14 (actor) + P70i (document); **matcher-derived** claims carry `hapi:derived_by_run → :D10` (the Software Execution that produced them) and don't carry P70i (matchers don't have documentary anchors — their provenance is algorithmic). Confidence on the matcher's E13 is informational, not gating. Matcher-derived claims are produced by a **two-stage pipeline**: a deterministic stage-1 matcher emits candidate E13s, and a stage-2 LLM reviewer evaluates each candidate and emits a verdict — itself an E13 whose P140 subject IS the matcher's E13 (see schema sketch case 4b). Verdicts form a linear supersession chain over `hapi:supersedes` edges; downstream effects (specifically the shortcut-triple emission for manifest interop) are gated on the unique tip of that chain having P141 = `hapi:verdict_approved`.

| Edge                                  | Specification | Domain | Range | Purpose |
|---------------------------------------|---------------|--------|-------|---------|
| `P140_assigned_attribute_to`          | core CRM      | E13    | E1    | Subject of the claim. |
| `P141_assigned`                       | core CRM      | E13    | E1    | Value of the claim (always an E1 entity, never a literal). |
| `P177_assigned_property_of_type`      | core CRM      | E13    | E55   | Predicate type (which kind of property this E13 assigns). |
| `P14_carried_out_by`                  | core CRM      | E7 (attaches to E13 by inheritance) | E39 | Human actor for human-attributed claims. |
| `P70i_is_documented_in`               | core CRM      | E1 (attaches to E13 by inheritance) | E31 | Documentary anchor; carries `cited_page` / `cited_pdf_page` as edge properties. |
| `hapi:derived_by_run`                 | Hapi extension (subPropertyOf P15_was_influenced_by) | E13 | D10 Software Execution | The matcher run that produced this assignment. |
| `L10_had_input`                       | CRMdig        | D7 (attaches to D10 by inheritance) | D1 | The source data file the matcher consumed. |
| `L11_had_output`                      | CRMdig        | D7 (attaches to D10 by inheritance) | D1 | The output data the matcher produced. |
| `L23_used_software_or_firmware`       | CRMdig        | D7 (attaches to D10 by inheritance) | D14 | The matcher algorithm. |

#### Hapi extension manifest

The `hapi:` prefix used throughout this ADR resolves to the namespace `https://pcomans.github.io/hapi-crm#`. The full extension manifest is committed at `pipeline/pipeline/authority/hapi_extension.rdf`. It contains three structurally distinct kinds of declaration:

- **`rdfs:subClassOf` / `rdfs:subPropertyOf` narrowing declarations.** These are the standard CIDOC extension idiom — every official extension, including CRMdig itself, uses the same `subClassOf` / `subPropertyOf` mechanism to relate to core CRM. They are **not deviations** from CIDOC.
- **Free-standing Hapi predicate declarations** (the ones with no `rdfs:subPropertyOf` to a CRM/CRMdig parent). These are **project vocabulary, CIDOC-opaque** unless and until a future round identifies a CRM/CRMdig superproperty to tie them to. CIDOC's open extension model permits this shape (extensions are free to introduce new predicates without subsumption), but does not make it the "CIDOC extension idiom" — calling it that would overstate. The CIDOC-opacity is explicitly acknowledged in the three-reader-mode framing below and in each free-standing predicate's manifest comment.
- **Controlled-vocabulary E55 Type instances** (the verdict outcomes `hapi:verdict_approved` / `_rejected` / `_retracted`, declared via `<rdf:Description rdf:about="#..."><rdf:type rdf:resource=".../E55_Type"/>`). These are NOT predicates and NOT free-standing project vocabulary without a CIDOC parent — they are CIDOC vocabulary **instances**, typed directly under CIDOC's E55 Type class. CIDOC-interpretable as instances of E55 Type via the explicit `rdf:type` assertion. Used as P141 values (never P177 targets, never relation predicates).

**Shortcut triple emission for manifest interop.** Every E13 Statement reification this ADR specifies — `(:E13) -P140-> (subject)`, `(:E13) -P141-> (value)`, `(:E13) -P177-> (:E55_Type {id: 'hapi:<predicate>'})` — captures *who/where/why* the claim came to be, but the reification on its own is **not** a `(subject, hapi:<predicate>, value)` triple. RDFS / OWL inference operates on existing triples, so the manifest's `rdfs:subPropertyOf` declaration on `hapi:<predicate>` cannot fire against an E13 reification; there is no `(subject, hapi:<predicate>, value)` triple in the graph for it to rewrite. (`hapi:<predicate>` is a metavariable in this paragraph — read it as "whatever specific hapi-namespaced predicate URI is recorded in this E13's P177 → :E55 Type target", e.g. `hapi:same_entity_as`, `hapi:matcher_review_verdict`. The angle brackets are not part of any actual URI.)

To make the manifest-loaded interop story actually work, the loader / strict-RDF export emits **two triples per claim** for any predicate registered with `emit_shortcut: true` (see "Predicate registry" section): the full E13 reification *and* a direct shortcut triple `(subject) hapi:<predicate> (value)` between the E13's P140 subject and P141 value. The reification carries provenance; the shortcut carries the queryable relationship.

**Shortcut-emission scope is governed by the registry's `emit_shortcut` field.** Default is `true` for primary P177-target predicates (`p177_target: true`) — the matching queries documented in the "Implications for matching" section traverse direct edges like `hapi:original_burial_in` and `hapi:in_dynastic_period`, and rely on these shortcuts being materialised so the queries don't have to walk through E13/P140/P141/P177 reifications. Set `false` per-predicate when the P141 value is a vocabulary-internal E55 instance that downstream consumers don't query against directly (the canonical case: `hapi:matcher_review_verdict`, whose P141 values are the verdict-outcome E55 Types — querying "give me all things pointing at `hapi:verdict_approved`" is not a useful question; the verdict-E13 reification is what consumers traverse). **Verdict-E13s never emit shortcuts** — the `hapi:matcher_review_verdict` registry entry carries `emit_shortcut: false` — both because their P141 vocabulary isn't a useful query target AND because emitting a `(matcher_claim) hapi:matcher_review_verdict verdict_approved` shortcut would recurse the matcher-derived-claims gating rule (matcher claims gate on an approved verdict-E13 tip; if verdict-E13s themselves emitted gated shortcuts, the gating would loop). Derived / query-only predicates (`p177_target: false`) are NOT eligible for `emit_shortcut: true` at all — they have no E13 reifications to emit shortcuts FROM; their triples come from the query definition directly.

**Matcher-derived claims gate shortcut emission on review verdict.** For human-attested E13s (P14 → E39 Actor) the shortcut emits unconditionally. For matcher-derived E13s (`hapi:derived_by_run → :D10`) the shortcut emits only when the **unique tip of the verdict supersession chain** for the matcher's E13 has `P141 = :E55 Type {id: 'hapi:verdict_approved'}`. The tip is the verdict-E13 that has no incoming `hapi:supersedes` edge from any other verdict-E13 covering the same matcher's E13. A matcher's E13 with no verdict at all has no tip and therefore no shortcut emission; "pending" is the absence of a verdict, not a verdict outcome. Rejected and retracted verdict outcomes also do not cause shortcut emission. The matcher's E13 is never mutated; revisiting a verdict produces a NEW verdict-E13 that carries `hapi:supersedes` to the previous tip, making the new verdict the new tip. **Supersession is not based on `started_at`.** Chain integrity is enforced by **three** complementary load-time constraints — all three required for the "unique linear chain with one tip" property to hold: (i) **unique successor per predecessor** — each verdict-E13 has at most one incoming `hapi:supersedes` (forks are a hard load error); (ii) **unique root per matcher-claim** — at most one verdict-E13 covering a given matcher-claim has no outgoing `hapi:supersedes` (multiple "first verdicts" on the same matcher-claim are a hard load error); (iii) **insert-time tip-only rule** — a non-root verdict-E13 inserted at time T must point its `hapi:supersedes` edge at the current chain tip at time T (the verdict-E13 covering the same matcher-claim that has no incoming `hapi:supersedes` at T); inserting a non-root verdict that supersedes a non-tip (mid-chain) verdict is a hard load error. Constraint (iii) is what closes the cycle-and-disconnected-component gap: constraints (i)+(ii) alone permit a cycle (e.g. A→B→C→A — every node has exactly one in-edge and one out-edge so neither (i) nor (ii) fires, but the chain has no root and no tip), which would silently leave the matcher-claim's "current verdict" undefined; (iii) ensures new edges always attach to the tip, so the chain stays a single linear sequence with one root and one tip. `started_at` / `completed_at` remain on the reviewer's `:D10` as reproducibility metadata, never as supersession state. This is how the two-stage pipeline composes with the manifest-interop story: matcher proposals exist in the graph (as full E13 reifications) regardless of verdict; only the approved tip of the supersession chain materialises the direct edge that downstream consumers query against.

This dual-emission pattern is **a Hapi-defined export rule inspired by CIDOC shortcut examples**, not a CRM-defined shortcut itself. CIDOC defines specific shortcut properties with formal FOL semantics — one worked example is P2 has type, whose scope note documents it as *"a shortcut for the path from E1 CRM Entity through P41i was classified by, E17 Type Assignment, P42 assigned to E55 Type"* (`pipeline/pipeline/authority/spec/cidoc_crm_v7.1.3.html#P2`). The long form (E1 ← P41i ← E17 Type Assignment → P42 → E55 Type) is the reified form; P2 itself is CIDOC's named shortcut between the endpoints. Hapi's E13 + P140/P141/P177 reification shares an *assignment spine* with that example (E17 ⊂ E13, so the chains have a common Attribute-Assignment ancestor), but Hapi's pattern is generic over any P177-target predicate rather than specific to P2's E17 chain — so this is structural inspiration, not the same construct. CIDOC pre-defined P2 as the named shortcut for one specific case with FOL semantics; Hapi is materialising analogous direct edges for our open-ended set of `hapi:` predicates assigned via P177. The specific shortcut properties (`hapi:same_entity_as`, etc.) are Hapi-defined, not CRM-defined.

The shortcut triple is what an RDFS reasoner rewrites via `subPropertyOf` inference into the parent property (e.g. `crmdig:L54_is_same_as` for `hapi:same_entity_as`); the E13 itself is not the inference target.

Predicates that do **not** play the P140-subject → P141-value relation role do not need dual emission — they are already direct triples on the E13 itself. `hapi:derived_by_run` (E13 → :MatcherRun) is in this category: the `(:E13) -hapi:derived_by_run-> (:MatcherRun)` triple exists in the graph as written, and the manifest's `rdfs:subPropertyOf P15_was_influenced_by` declaration rewrites it natively. Schema sketches in this ADR show only the E13 form for these; the per-predicate `emit_shortcut` registry field governs the shortcut-triple decision for P140→P141 relation predicates.

**Three reader modes, three outcomes — clarified explicitly:**

| Reader configuration | What happens to Hapi-namespaced triples |
|---|---|
| Strict CRM/CRMdig reader that has NOT loaded `hapi_extension.rdf` | Hapi terms are unrecognised URIs. The reader retains the triples but does not infer anything from them — IS-A propagation, subPropertyOf rewriting, and class-hierarchy queries that target CRM/CRMdig terms simply do not surface the Hapi-typed entities. Genuinely "silently ignored." |
| Reader that has loaded the manifest + applies an RDFS reasoner | The reasoner applies the manifest's `subClassOf` / `subPropertyOf` declarations: every `hapi:MatcherRun` is now also typed as `crmdig:D10 Software Execution` (and transitively as D7 Digital Machine Event, E11 Modification / E65 Creation, E7 Activity, E1 CRM Entity); every `hapi:derived_by_run` edge is now also a `crm:P15_was_influenced_by` edge; every `hapi:same_entity_as` edge is now also a `crmdig:L54_is_same_as` edge. RDFS reasoning does **not** infer property symmetry, so the manifest's `owl:SymmetricProperty` declarations are effectively no-ops on this reader — symmetry on `hapi:same_entity_as` and `hapi:shares_tomb_with` is enforced at the application layer (predicate registry) when only RDFS reasoning is available. |
| Reader that has loaded the manifest + applies an OWL-aware reasoner | Same as the RDFS row above, **plus** the reasoner applies the manifest's `owl:SymmetricProperty` declarations (currently on `hapi:same_entity_as` and `hapi:shares_tomb_with`) and infers the inverse direction of each symmetric edge automatically. Note that OWL symmetry is a non-CIDOC behavior — `hapi:same_entity_as` gets both CIDOC interpretation (via L54) and OWL symmetry, while `hapi:shares_tomb_with` gets only OWL symmetry (no CIDOC interpretation, because it has no `subPropertyOf`). |

**CIDOC-opacity and OWL-behavior are independent.** A Hapi predicate without a declared `rdfs:subPropertyOf` remains opaque to CRM/CRMdig vocabulary regardless of OWL typing — the manifest documents its existence but doesn't relate it to any CIDOC term. OWL typing (like `owl:SymmetricProperty`) adds non-CIDOC behavior that an OWL-aware reader can use; it does not add CIDOC interpretation. `hapi:shares_tomb_with` is the current example of an OWL-typed but CIDOC-opaque predicate; the tomb-context predicates (`tomb_owner`, `original_burial_in`, `cache_context_at`) are both CIDOC-opaque and OWL-untyped.

All three modes are valid. The graph data itself is identical across reader configurations; what differs is the reader's interpretive layer. Hapi never relies on the manifest being loaded for correctness — but loading it unlocks progressively more of the interop story.

Manifest excerpt (the full file is the citable contract):

```turtle
# Hapi extension manifest excerpt — see pipeline/pipeline/authority/hapi_extension.rdf for the full file
# Every Hapi-namespaced class and predicate referenced anywhere in this ADR MUST appear in that file,
# with either a sound subClassOf/subPropertyOf declaration or an explicit free-standing declaration
# (with comment) when no CRM superclass/superproperty fits. Unmanifested terms are rejected by the
# cidoc-crm-validator subagent.

@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .
@prefix hapi:    <https://pcomans.github.io/hapi-crm#> .
@prefix crm:     <http://www.cidoc-crm.org/cidoc-crm/> .
@prefix crmdig:  <http://www.cidoc-crm.org/extensions/crmdig/> .

# Classes
hapi:MatcherRun         rdfs:subClassOf  crmdig:D10_Software_Execution .
hapi:MatcherAlgorithm   rdfs:subClassOf  crmdig:D14_Software         .
hapi:SourceData         rdfs:subClassOf  crmdig:D1_Digital_Object    .

# Properties — Hapi-namespaced for readability, declared as subproperties of real CRM/CRMdig properties
hapi:derived_by_run     rdfs:subPropertyOf crm:P15_was_influenced_by  .  # E13 → hapi:MatcherRun
hapi:same_entity_as     rdfs:subPropertyOf crmdig:L54_is_same_as       .  # E1 ↔ E1
hapi:same_entity_as     rdf:type           owl:SymmetricProperty       .  # OWL-reasoner inferred inverse
hapi:shares_tomb_with   rdf:type           owl:SymmetricProperty       .  # E21 ↔ E21 (Ruler ↔ Ruler); DERIVED predicate, not loadable as a primary claim — see ADR text below

# P177-target predicates are ALSO typed as crm:E55_Type (RDF punning — see paragraph below).
# This is required because CIDOC P177's range is E55 Type: a URI used as a P177 target must
# carry crm:E55_Type typing or the triple is malformed CIDOC. Excerpt:
hapi:same_entity_as          rdf:type crm:E55_Type .   # also used as P177 value
hapi:matcher_review_verdict  rdf:type crm:E55_Type .   # also used as P177 value
# ... (every claim-predicate URI in the manifest carries the same dual typing)
```

**P177-target predicates are typed as both `rdf:Property` AND `crm:E55_Type` (RDF "punning").** CIDOC `P177_assigned_property_of_type` has range `E55 Type` (`pipeline/pipeline/authority/spec/cidoc_crm_v7.1.3.rdf` — search for `P177`), so any URI used as a P177 value must carry `crm:E55_Type` typing or the triple is malformed CIDOC. The same URI is also a hapi predicate (it carries the relation between subject and value in the shortcut-triple emission), which requires `rdf:Property` typing. RDF / OWL 2 permit the same URI to carry both type assertions ("punning"). **This is a Hapi-manifest pattern, not a CIDOC-prescribed one** — CIDOC CRM 7.1.3 + CRMdig 5.0 don't document or prescribe punning specifically; CIDOC's requirement is just that a P177 value carries E55_Type typing, and Hapi's downstream modelling choice is to use punning rather than mint two parallel URIs per claim predicate. The manifest declares every claim-predicate URI with both `rdf:type rdf:Property` (implicitly via the `<rdf:Property>` element) and `rdf:type crm:E55_Type` (explicit). Three exemption cases — URIs that get one typing but not the other:

- **Verdict-outcome E55 Types** (`hapi:verdict_approved`, `hapi:verdict_rejected`, `hapi:verdict_retracted`): pure `crm:E55_Type` instances (vocabulary values used as P141 values, never P177 targets and never relation predicates), so they carry only `crm:E55_Type` typing.
- **E13-internal direct edges** (`hapi:derived_by_run`, `hapi:supersedes`): never appear as P177 targets — they are direct edges between an E13 and its provenance node / between two E13s in a supersession chain — so they carry only `rdf:Property` typing.
- **Derived / query-only predicates** (`hapi:shares_tomb_with`): never appear as P177 targets in the persisted graph because the loader REJECTS direct E13 reifications of them; they exist only as raw query-output triples between domain entities, materialised by the query definition from the underlying primary E13s (`hapi:original_burial_in` / `hapi:cache_context_at` in this case — each of which DOES carry P177/E55 typing as a normal P177-target predicate). The derived edge is a projection of those underlying claims, not a fresh claim with its own provenance — provenance lives on the underlying E13s. So `hapi:shares_tomb_with` carries only `rdf:Property` + `owl:SymmetricProperty` typing, NOT `crm:E55_Type`. This avoids the contradiction of an E13 claim that has no provenance edge of its own (principle 1 requires every E13 claim to carry provenance; derived edges are not E13 claims).

Hapi predicates that don't have a clean CRM/CRMdig superproperty AND that ARE P177-target predicates in the predicate registry (`hapi:in_dynastic_period`, `hapi:tomb_owner`, `hapi:original_burial_in`, `hapi:cache_context_at`, `hapi:display_name`, `hapi:reign_period`, `hapi:horus_name`, `hapi:matcher_review_verdict`) live in the manifest as plain `rdf:Property` declarations punned with `crm:E55_Type` so they can serve as P177 targets, and as `:E55 Type` instances in the predicate registry. Tightening these to real `rdfs:subPropertyOf` declarations is a follow-up Egyptological + CRM-modelling cross-cut. For `hapi:matcher_review_verdict` specifically, the closest CRMdig affinity is `crmdig:L43_annotates` (a `subPropertyOf P129_is_about` whose conceptual intent — an annotation object asserting something about another CRM entity — closely parallels a reviewer's verdict on a matcher's E13). The reason it is NOT declared `rdfs:subPropertyOf crmdig:L43_annotates` is a domain conflict: L43's `rdfs:domain` is `D29 Annotation Object`, and our verdict-E13 is an E13 Attribute Assignment, not a D29 — declaring subPropertyOf would escape L43's domain, violating the "narrow not violate" rule. The affinity is documented via `crm_nearest: 'crmdig:L43_annotates'` in the predicate registry only (documentation-level, no inference effect). D29 / D30 / L43 remain documentation-only references; they are NOT added to the consumed CRMdig subset (still D1, D7, D10, D14 + L10, L11, L23, L54). **`hapi:supersedes` is separate from this list** — it is a direct E13→E13 relation, never a P177 target, so it is declared as `rdf:Property` only (no E55_Type punning). No CRM superproperty fits the "this E13 replaces that E13" semantic either (P130 / P132 are about similarity / overlap, not replacement); it is free-standing in the same modelling sense as the P177-target predicates above, but does not appear as a `:E55 Type` instance in the predicate registry.

`hapi:shares_tomb_with` is **not** in that follow-up bucket. It is registered as a **derived / query-only predicate**: the edge encodes neither the shared Site nor the burial context (primary burial vs cache), so asserting it directly would lose the very context the rest of the model exists to preserve. The loader REJECTS direct assertions of `hapi:shares_tomb_with` from any source; the source's actual statement (e.g. "King X and Queen Y in KV35") is emitted as the two corresponding `original_burial_in` / `cache_context_at` claims, and `hapi:shares_tomb_with` is materialised at query time by intersecting two rulers' **actual-burial site sets** — *only* the burial predicates `hapi:original_burial_in` and `hapi:cache_context_at`. `hapi:tomb_owner` is commissioning/ownership, not interment, and is **not** a derivation source for `hapi:shares_tomb_with` (a king who commissioned a tomb but was never interred there should not be inferred as "buried with" anyone subsequently interred in it). The predicate registry carries a `derived: true` flag for this case (see Predicate registry section below).

#### Property-graph encoding conventions and CIDOC RDF serialisation mappings

The four entries below document Hapi's choices for how the conceptual CIDOC/CRMdig model is laid out in the property-graph store. **None of them is a conceptual deviation** — each preserves CIDOC's class/property/inheritance semantics, and each has a deterministic, lossless mapping to a strict-RDF CIDOC serialisation (the export shape). The mappings are mechanical; the loader specification owns them. A reviewer auditing CIDOC conformance can verify either the in-store encoding directly (with the mappings in hand) or the strict-RDF export — both encode the same conceptual content.

Anything else in the model that violates CIDOC's conceptual model without being listed in the "Conceptual deviations from CRM/CRMdig" subsection below is a bug. The taxonomy is binary: encoding convention with a documented round-trip mapping → clean; conceptual departure → declared deviation requiring its own justification. There is no "minor deviation" or "soft issue" category.

1. **Property-graph inlining of value-entity literals.** Strict CRM stores literals on value entities via P190 (E41 → E62 String), P90 (E54 → E60 Number), etc. The property-graph encoding inlines these as direct properties on the value-entity node (`:E41 Appellation {symbolic_content: 'wnis'}`). The mapping is mechanical and round-trippable to a strict CRM/RDF export.
2. **Property-graph inlining of structural attributes beyond value literals.** Inline `:E55 Type` tags (`appellation_kind: 'horus_name'`), inline `:E31 Document` properties (`kind`, `citation`, `year`, `language`, `rationale`), and inline `:E31` identifying labels on `:Dynasty:E4 Period` (`number`, `beckerath_label`, `leprohon_chapter`). Round-trip mappings, per attribute kind:
   - **Type tags** (`appellation_kind`, etc.): `P2_has_type → :E55 Type`. The inline value must resolve 1:1 to a registered `:E55 Type` instance via the predicate registry's type catalogue (a fixed mapping table committed alongside the loader). An unregistered inline type tag fails the load.
   - **Identifying labels** on `:Dynasty:E4 Period` (`number`, `beckerath_label`, `leprohon_chapter`): `P1_is_identified_by → :E41 Appellation`, with each label distinguished by `P2_has_type → :E55 Type` (`type='beckerath-label'`, `type='leprohon-chapter'`, etc.).
   - **Free-text notes** (`rationale`, `citation`): `P3_has_note → :E62 String`.
   - **`year` / `decided_at` on `:E31 Document` instances** (temporal markers): `:E65 Creation + P4_has_time-span → :E52 Time-Span`. P94's range is E28 Conceptual Object; E31 ⊂ E73 ⊂ E89 ⊂ E28, so E65 fits documents. Temporal markers on other Persistent Item kinds (if ever introduced) require the event class appropriate to that kind (E12 Production for human-made things, E67/E69 Birth/Death for persons, E63 Beginning of Existence as the general parent) — a per-kind decision when the case arises.
   - **`language` on `:E31 Document` instances** needs special care. `P72_has_language` has `rdfs:domain E33 Linguistic Object`, NOT E31. Round-trip: any `:E31 Document` that carries a `language` field is **multi-typed as `:E31 ⊕ :E33`** at export — both are direct `subClassOf E73 Information Object` and are sibling classes (no IS-A relationship between them), so CIDOC permits the dual typing. Once the document carries the E33 typing, `P72_has_language → :E56 Language` attaches natively to its E33 view. (The loader emits the E33 type assertion + the P72 edge together when `language` is present; documents without a `language` field stay single-typed `:E31`.)
   - **`language` on `:E41 Appellation` instances** uses the same shape under CIDOC's pre-canonicalised multi-inheritance class: any `:E41` carrying a `language` field is **multi-typed as `:E33_E41_Linguistic_Appellation`** at export (a class the CIDOC RDFS ships specifically for this case — declared as `subClassOf E33 Linguistic Object` AND `subClassOf E41 Appellation`). `P72_has_language → :E56 Language` then attaches via the E33 inheritance. The loader emits the multi-typed class + the P72 edge together when `language` is present on an appellation; appellations without `language` stay single-typed `:E41`.
   - **`kind` on `:E31 Document` instances** (e.g. `kind: 'publication'` vs `kind: 'curator_decision_batch'`): `P2_has_type → :E55 Type` via the document-kind sub-catalogue of the predicate registry's type table.

   Mechanical; loader specification owns the canonical expansions.
3. **Time-Span boundary literals stored directly on the `:E52 Time-Span` node.** The conceptual CRM 7.1.3 model declares P81 / P82 (E52 → E61 Time Primitive); it does not declare conceptual P81a / P81b / P82a / P82b. Those four are introduced *only* by the RDFS implementation as refinements that emit `rdfs:Literal`. The property-graph stores year boundaries as signed integers directly on the `:E52` node (`begin_of_the_begin: -2375`, `end_of_the_end: -2345`) plus an explicit `calendar` property pinning the year-numbering convention. Round-trip at the conceptual level: literals serialise into E61 Time Primitive value entities linked via P81 / P82. Round-trip at the RDFS-implementation level: same literals serialise into P81a / P81b / P82a / P82b refinements. Lexical form (XML Schema 1.1 expanded-year vs ISO 8601 extended astronomical-year vs other) is a **Hapi convention** pinned in the loader specification — neither CRM nor CRMdig mandates a specific form, particularly for BCE years where conventions disagree.
4. **Citation-evidence properties (`cited_page`, `cited_pdf_page`) carried on the `P70i_is_documented_in` edge itself.** Strict CRM has no `.1` sub-property of P70 for page-level citation; the edge-property idiom is a Hapi compactness choice. When at least one locator field is non-null, the round-trip materialises the page-level documentary content as its own `:E31 Document`; when both are null, no page-level sub-document is materialised and P70i points at the publication-level `:E31` directly. Three rules govern the canonical locator identity for the non-trivial case (required for lossless round-trip):
   - **Canonical locator key.** Each per-page `:E31` node is keyed by the full `(publication, cited_page, cited_pdf_page)` tuple — NOT just `(publication, page)` — with nulls included. This prevents the two pathological collisions: same printed page with different PDF pages (e.g. front-matter pagination differs from printed-page numbering), and same PDF page with different printed pages (facing-page spreads). It also prevents a partial-page claim from colliding with a full-page claim: `(publication, 'p. 115', NULL)` and `(publication, 'p. 115', 127)` are distinct keys. One `:E31` per distinct locator tuple, with bounded growth. The physical printed page is not itself an E31 (a printed sheet is closer to E22 Human-Made Object); what's typed as `:E31` is the propositional/documentary content carried at that page location, in the same sense that the publication-level `:E31` names the publication's documentary content, not its physical binding.
   - **One identifier per non-null locator field.** Each non-null locator becomes its own `P1_is_identified_by → :E42 Identifier` edge, with `P2_has_type → :E55 Type` distinguishing the kind:
     - `:E42 Identifier {value: 'p. 115'}` typed `printed-page-locator` (emitted iff `cited_page` is non-null)
     - `:E42 Identifier {value: '127'}` typed `pdf-page-locator` (emitted iff `cited_pdf_page` is non-null)

     A claim with only `cited_page` set yields a per-page `:E31` carrying one identifier; a claim with both set yields one carrying two; a claim with neither doesn't materialise a per-page `:E31` at all. P1 has domain E1 and range E41; E42 IS-A E41, so the range conforms by subsumption. No null identifiers are ever emitted.
   - **Parent-publication link.** `P148i_is_component_of → :E31 Document {publication}`. P148 has domain and range E89 Propositional Object; E31 IS-A E73 IS-A E89, so both endpoints conform.

   The original `(:Statement:E13) -[:P70i_is_documented_in]-> (:E31 Document {publication})` rewrites to point at the page-level `:E31` instead of the publication-level one when one was materialised. **P70i's range stays E31** — no rerouting through E73/E33 required.

   All four cases round-trip losslessly: (i) both locators present and distinct between two claims → two distinct `:E31` sub-documents distinguished by whichever identifier differs; (ii) one locator present, the other null → per-page `:E31` with the single non-null identifier, distinct from any same-publication claim that supplies both; (iii) both locators absent → no per-page `:E31` materialised, P70i points at the publication; (iv) two claims with identical `(publication, cited_page, cited_pdf_page)` tuples → share the same per-page `:E31` (correctly, since they cite the same location). The loader specification owns the rule.

#### Conceptual deviations from CRM/CRMdig

**None currently.**

This subsection exists as a contract. A real conceptual deviation would be a claim that doesn't round-trip to a CIDOC-compatible shape — e.g., using `P140_assigned_attribute_to` with a value whose type isn't in P140's E1 range, asserting an IS-A relationship CIDOC's class hierarchy doesn't permit, or attaching a CRM property to a node outside its declared domain by inheritance. Each such case would land here with its own clear-label / justification / containment / round-trip-mapping discipline (the same four-property contract that gates encoding conventions above).

The previous version of this ADR listed `:Matcher not E39 Actor` as a deviation in this category. That deviation is **retired** by adopting CRMdig — matcher runs are now `:D10 Software Execution`, algorithms are `:D14 Software`, and the connection from E13 to the run is `hapi:derived_by_run rdfs:subPropertyOf P15_was_influenced_by`. There are currently no other conceptual departures.

**Hapi free-standing predicates** (declared in `hapi_extension.rdf` without `rdfs:subPropertyOf` to a CRM/CRMdig parent) are **NOT** in this category. They are project vocabulary that CIDOC's open extension model permits — but they are NOT instances of the standard CIDOC extension idiom (which is `rdfs:subClassOf` / `rdfs:subPropertyOf` narrowing within a parent's domain and range; see shape (a) in the three-shape manifest framing at the start of this section, and shape (c) for controlled-vocabulary E55 Type instances which are also distinct from these free-standing predicates). The free-standing predicates are CIDOC-opaque: a reader with the manifest loaded sees the URI and its declared domain / range but cannot interpret the predicate through any CRM/CRMdig term, because none is declared. That CIDOC-opacity is documented in the three-reader-mode framing and the manifest's per-predicate comments. It is not a deviation — the open extension model accepts free-standing predicates — but it is also not the same as a parent-narrowed extension, which strict CIDOC readers running RDFS reasoning CAN interpret through their declared parents. Tightening a free-standing predicate into a parent-narrowed one (when a suitable CRM/CRMdig superproperty is identified) is the deferred follow-up in the "Explicitly deferred to follow-up ADRs" section.

The current free-standing set divides into three structurally distinct sub-categories (counts are normative and update with the manifest, not standalone prose):

- **Primary P177-target free-standing predicates (currently eight):** `hapi:in_dynastic_period`, `hapi:tomb_owner`, `hapi:original_burial_in`, `hapi:cache_context_at`, `hapi:display_name`, `hapi:reign_period`, `hapi:horus_name`, `hapi:matcher_review_verdict`. Each is dually typed as `rdf:Property` + `crm:E55_Type` (punning) so it can serve as a P177 value on E13 reifications and emit shortcut triples per the registry's `emit_shortcut` field.
- **Derived / query-only free-standing predicate (currently one):** `hapi:shares_tomb_with`. NOT a P177 target (no `crm:E55_Type` punning); exists only as raw query-output triples between domain entities. Provenance lives on the underlying primary E13s, not on the derived edge. Loader REJECTS direct E13 reifications.
- **E13-internal direct-edge free-standing predicate (currently one):** `hapi:supersedes`. NOT a P177 target either; a direct E13 → E13 relation expressing chain supersession between verdict-E13s. Carries no `crm:E55_Type` typing.

The remaining two manifest-declared predicates (`hapi:derived_by_run rdfs:subPropertyOf crm:P15_was_influenced_by` and `hapi:same_entity_as rdfs:subPropertyOf crmdig:L54_is_same_as`) are NOT free-standing — they're subPropertyOf-narrowed CIDOC extensions, included here only for inventory completeness. Adding a tighter `rdfs:subPropertyOf` to any of the free-standing predicates above (when a suitable parent is identified) moves that entry out of the free-standing bucket without changing what it does in the model.

### Core principles

1. **Every claim has a provenance edge.** No fact lives in the graph without an attribution to how the claim came to be. Two distinct provenance shapes:

   - **Human-documentary** (scholarly attribution). Two CIDOC-distinct parts:
     - **The actor who performed the attribute assignment** — an E39 Actor (E21 Person for an individual scholar or curator; E74 Group for a curatorial body or society). Attached via `P14_carried_out_by`.
     - **The documentary source where the claim is recorded** — an E31 Document (a publication, an authority release, a curator-decision record). Attached via `P70i_is_documented_in`, with page citations carried as properties of that edge.

     For a Leprohon claim, the actor is the scholar Ronald J. Leprohon (`:E21 Person`) and the document is the 2013 book *The Great Name: Ancient Egyptian Royal Titulary* (`:E31 Document`). A publication is not itself an actor in CIDOC — E39 Actor requires capacity for intentional action — so publication nodes are documents, never actors.

   - **Machine-derived** (matcher / alias-expander / derivation rule output). One CRMdig-typed chain:
     - **The derivation run** that produced the Statement — a `:D10 Software Execution` (CRMdig 5.0). Attached via `hapi:derived_by_run` (declared `rdfs:subPropertyOf crm:P15_was_influenced_by` so strict CIDOC readers that have loaded the Hapi extension manifest interpret it as "this E13 was influenced by this E7 Activity").
     - **The algorithm used** — a `:D14 Software` referenced from the run via `crmdig:L23_used_software_or_firmware`.
     - **The source data consumed** — one or more `:D1 Digital Object` references via `crmdig:L10_had_input`.
     - **The derived output data** — a `:D1 Digital Object` reference via `crmdig:L11_had_output`.

     A hapi match is *not* a scholarly association: the difference between them is structural in CIDOC terms. Human claims carry `P14 → E39` (an actor attesting); matcher claims carry `hapi:derived_by_run → :MatcherRun` (a derivation event that produced the claim). The presence vs absence of P14 is directly observable from the data — even a strict reader without the Hapi extension manifest loaded can tell the two shapes apart at that structural level. What the strict-without-manifest reader cannot do is interpret the matcher-side semantics: `hapi:derived_by_run` is just an unknown predicate URI to them, and `:MatcherRun` is just an unknown class. A reader that loads the manifest gets full semantic interpretation through the declared `subPropertyOf` / `subClassOf` parents.

   Matcher-derived claims don't carry `P70i_is_documented_in` — matcher provenance is algorithmic, not documentary, and there is no human-review step that would attach a document anchor. (Matcher claims are evaluated by a stage-2 LLM reviewer; the reviewer's verdict is recorded as a separate E13 pointing at the matcher's E13, not as a P70i edge on the matcher's E13. See principle on the two-stage pipeline below and the schema sketch case 4b.) Human claims always carry both P14 and P70i — page-level metadata on P70i is optional but the documentary anchor itself is required.

2. **Cross-source disagreements are preserved.** When Leprohon claims reign-start −1390 and Dodson-Hilton claims −1391 for the same ruler, two Statements with the same predicate and different values coexist, each tracing to its source. Reconciliation does not pick a winner at the data layer. The resolution policy (which one a downstream consumer sees) is per-predicate and lives outside the graph — see principle 7.

3. **Per-agent disagreements are extraction artifacts, not data.** The 3-arbiter blind-extraction process is a quality gate on faithfulness to the source. Per CLAUDE.md Rule 2, agent disagreement resolves to exactly one of: (a) unanimity, (b) a real majority (>50%), (c) an explicit per-row override committed in the source's `tie-break-overrides.json` with cited rationale, or (d) a deterministic policy documented in code or the source's README. Anything else fails loud — not all disagreements naturally converge, which is exactly why `tie-break-overrides.json` exists per source. Whichever resolution applies, what loads as an E13 Statement is the *resolved* value, attributed to the publication (`P14_carried_out_by` → the scholar; `P70i_is_documented_in` → the publication). Agent-level structure never appears in the graph — it is pipeline scaffolding.

4. **Open schema, enforced registry.** **P177-target claim predicates** are *data*, not DDL. Adding `hapi:shares_tomb_with` (a derived predicate) or `hapi:matcher_review_verdict` (a primary P177-target predicate) is in either case an INSERT into the predicate registry, not a migration. The registry is the verify-before-create enforcement point with two distinct rules depending on the entry's `p177_target` field (see "Predicate registry" below): for primary predicates (`p177_target: true`), the corresponding `:E55 Type` instance is materialised and the P177 column FK-references it — an E13 whose P177 target does not resolve to a registered primary-predicate `:E55 Type` fails the load. For derived predicates (`p177_target: false`), no `:E55 Type` is materialised; the loader REJECTS any E13 reification whose P177 target is a derived predicate. Both rules are Rule-3 deterministic enforcement. **Non-P177-target manifest-declared terms** (E13-internal direct edges like `hapi:derived_by_run` and `hapi:supersedes`; controlled-vocabulary E55 Type instances like the verdict outcomes) follow a separate manifest-only path — added by editing `hapi_extension.rdf`, validated by the cidoc-crm-validator subagent at PR time, not the registry. No agent or contributor invents any of these terms; new ones are proposed against the appropriate path (registry for claim predicates, manifest for the other two shapes), reviewed for overlap with existing terms, and added once.

5. **All Statement values are E1 CRM Entity references; literals live on value-bearing entities.** `P141_assigned` has range E1 CRM Entity in CRM 7.1.3 — literals are not E1. The Hapi model is faithful to this:
   - A name claim like "Narmer's Horus name is 'nar mer'" assigns an `:E41 Appellation` value entity that carries the literal as a property accessed via `P190_has_symbolic_content`.
   - A reign-date claim assigns an `:E52 Time-Span` value entity that carries boundary literals on the node. Conceptual CRM models the span via P81 ongoing throughout / P82 at some time within (both E52 → E61 Time Primitive); the property-graph stores the boundaries directly, exporting to the RDFS-implementation refinements P81a / P81b / P82a / P82b at strict-RDF time (see encoding convention #3).
   - A numeric measurement assigns an `:E54 Dimension` carrying `P90_has_value` and `P91_has_unit`.
   - An entity-period claim like "Narmer is dated to Dynasty 0" assigns the Dynasty (`:E4 Period`) node directly via `hapi:in_dynastic_period`.

   The property-graph encoding inlines the CIDOC-property values (`symbolic_content`, `value`, `begin`, `end`) as properties of the value-entity node, rather than as separate string-literal nodes. The value-entity layer is what makes graph traversal uniform: "show me every claim that touches Dynasty 0" traverses through `P141_assigned`; "show me every appellation containing 'wnis'" indexes through `:E41 Appellation` nodes regardless of which Statement assigned them.

6. **Identity across sources is itself a claim — no canonical Person at load time.** Each source's row is stored as its own per-source entity node (`:Ruler`, `:Site`, etc.), keyed by source + source-row-id. Same-entity assertions ("Leprohon's row for Unas is the same person as Beckerath's row for Unas") are modelled as Statements with predicate `hapi:same_entity_as`, `P141_assigned` pointing at the other entity, and a provenance edge attributing the claim — `P14_carried_out_by` + `P70i_is_documented_in` for a human curator decision or a source-asserted identification, `hapi:derived_by_run → :D10 Software Execution` for an automated matcher. The mechanism is uniform across two distinct cases: (a) cross-source identity hypotheses (one source's Unas vs another's Unas — genuinely uncertain), and (b) intra-source phase aliasing (Leprohon's two rows for Akhenaten as Amenhotep IV + Akhenaten — same person across naming phases, source-asserted). The framing is "per-source-row + same-entity claims that link the cluster" in both cases; "identity hypothesis" is one motivation, "naming-phase aliasing" is another. **The loader makes no identity commitments.** Identity is data the matching pipeline produces over time, with full provenance. A canonical-person view can be derived later from `same_entity_as` clusters if query ergonomics demand it (see Consequences); the storage layer is per-source records, not collapsed persons.

7. **Resolution policy is per-predicate, fail-loud by default.** When a downstream consumer (UI, search index, enrich asset) needs a single value and the graph carries competing claims, a per-predicate resolution rule decides which to surface (e.g. "for `reign_start_bce`, Beckerath > Hornung > Leprohon"; "for `hapi:display_name`, prefer the Statement whose `P70i_is_documented_in` document has `kind: 'curator_decision_batch'` and the most recent `decided_at`, attributed to the curatorial Group via P14"). If no rule is committed for a predicate, the query **fails loud** — the consumer must specify a rule or accept the full claim set. This aligns with Rule 2: no silent arbitrary picks; every resolution traces to a documented policy.

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

Every claim is an E13 Statement. Edge cardinality depends on claim type. **Human-documentary claims always carry all five canonical edges**: P140 (subject), P141 (value), P177 (predicate type), P14 (actor), and P70i (documentary source). Page-level citation (`cited_page`, `cited_pdf_page`) is *optional metadata* on the P70i edge — the page may be unknown — but the P70i edge itself to the publication-level `:E31 Document` is required. A human-attested claim without a documentary anchor would be an undocumented scholarly claim, which principle 1 forbids. **Matcher-derived claims** replace `P14_carried_out_by` with `hapi:derived_by_run → :MatcherRun:D10` (a CRMdig Software Execution; `hapi:derived_by_run` is `rdfs:subPropertyOf crm:P15_was_influenced_by`) and **never carry `P70i_is_documented_in`** — matcher provenance is algorithmic, not documentary, and there is no human-review step that would attach a document anchor (the design intentionally has no such step). **Review-verdict claims** (stage-2 LLM evaluations of matcher claims; see schema sketch case 4b) have the same matcher-claim shape (no P14, no P70i, `hapi:derived_by_run → :D10` reviewer-run) but their P140-subject is itself an E13 — they are claims-about-claims, recording the reviewer's verdict on the matcher's E13. The `P140` / `P141` / `P177` triad is the universally-required spine for all claims; the only point of variation is the provenance shape — human-documentary (always P14 + P70i) vs machine-derived (always `hapi:derived_by_run`, never P14, never P70i). The P70i edge is **not** optional-on-machine; it is **absent** on machine claims as a loader contract.

| # | Edge                                  | Target type         | Required |
|---|---------------------------------------|---------------------|----------|
| 1 | `P140_assigned_attribute_to`          | the subject entity  | always |
| 2 | `P141_assigned`                       | the value entity    | always (an E1 entity, never a literal) |
| 3 | `P177_assigned_property_of_type`      | `:Type` (E55)       | always — the predicate type |
| 4 | `P14_carried_out_by`                  | `:Person`/`:Group`  | for human-attributed claims |
| 4'| `hapi:derived_by_run`                 | `:MatcherRun:D10`   | for matcher-attributed claims (Hapi extension; `rdfs:subPropertyOf crm:P15_was_influenced_by`). The `:MatcherRun` (CRMdig D10 Software Execution) carries run-reproducibility metadata and references its algorithm (`:MatcherAlgorithm:D14`) via `crmdig:L23_used_software_or_firmware`. |
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
//     stores boundaries directly; export pipelines emit one or the other form. See encoding convention #3.
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

// (4a) STAGE 1 — A cross-source identity claim emitted by the deterministic matcher.
//     No P14 — matcher claims don't have a human actor. Instead:
//       hapi:derived_by_run (rdfs:subPropertyOf P15_was_influenced_by) → :D10 Software Execution (the run)
//       The D10 references its software (:D14) via L23, its inputs (:D1 source data) via L10,
//       and its derived output (:D1) via L11. All CRMdig 5.0, all strict-conformant.
//     We use D10 Software Execution rather than the more specific D3 Formal Derivation — D3's
//     scope is restricted to derivations producing a "different form" of the same digital object
//     (colour corrections, resizing, format conversions). A matcher producing identity assertions
//     is producing different information, not a different form. D10 is the correct general parent.
//     Confidence is a Hapi property of the Statement; the run carries the reproducibility
//     metadata (input commit, parameter hash, timestamps) so any score can be regenerated or
//     rejected by replaying the D10 against its L10 sources. No verdict info on the matcher's
//     E13 itself — the verdict is a separate E13 (case 4b).
(:Statement:E13 matcher-claim {confidence: 0.94})
  -[:P140_assigned_attribute_to]->    (:Ruler {leprohon::leprohon-5.07})
  -[:P141_assigned]->                  (:Ruler {beckerath::05.07})
  -[:P177_assigned_property_of_type]-> (:Type:E55 {id: 'hapi:same_entity_as'})
  -[:hapi:derived_by_run]->            (:MatcherRun:D10 {
                                           run_id:               'matcher_run_2026_05_17T14_22Z',
                                           input_dataset_commit: 'a8f3e9d...',
                                           parameters_hash:      'sha256:7c4...',
                                           started_at:           '2026-05-17T14:22:31Z',
                                           completed_at:         '2026-05-17T14:24:08Z'
                                       })

(:MatcherRun:D10 {matcher_run_2026_05_17T14_22Z})
  -[:L23_used_software_or_firmware]-> (:MatcherAlgorithm:D14 {
                                           id: 'normalized_name_v1',
                                           version: '0.1.0',
                                           algorithm: 'lowercase+strip_diacritics+token_match',
                                           hyperparameters_json: '{"min_dynasty_match": true}'
                                       })
  -[:L10_had_input]->                  (:SourceData:D1 {
                                           path: 'leprohon-2013-titulary/reconciled.jsonl',
                                           git_commit: 'a8f3e9d...'
                                       })
  -[:L10_had_input]->                  (:SourceData:D1 {
                                           path: 'beckerath-1997-chronologie/reconciled.jsonl',
                                           git_commit: 'a8f3e9d...'
                                       })
  -[:L11_had_output]->                 (:SourceData:D1 {
                                           path: 'matcher_outputs/run_2026_05_17T14_22Z.jsonl'
                                       })

// (4b) STAGE 2 — A review verdict from the LLM reviewer evaluating the matcher's E13 above.
//     The verdict is itself an E13. Its P140-subject is the matcher's E13 (E13 ⊂ E1, so P140's E1
//     range is satisfied). Its P141-value is the verdict outcome as an :E55 Type drawn from the
//     verdict-outcome controlled vocabulary (see "Verdict-outcome controlled vocabulary" below).
//     The reviewer's run is itself a :D10 Software Execution — separate run record from the
//     matcher's, paired with its own :D14 reviewer software. The verdict E13 is never mutated;
//     if the reviewer revisits and changes its mind, a NEW verdict-E13 is emitted that carries a
//     hapi:supersedes edge to the previous verdict-E13. The "current verdict" for a matcher's E13
//     is the unique tip of the supersedes chain (the verdict-E13 with no incoming hapi:supersedes
//     from any other verdict-E13 covering the same matcher's E13). Chain integrity is enforced by
//     THREE complementary load-time constraints, all three required for the "unique linear chain
//     with one tip" property to hold: (a) unique successor per predecessor — each verdict-E13 has
//     at most one incoming hapi:supersedes (forks are a hard load error); (b) unique root per
//     matcher-claim — at most one verdict-E13 covering a given matcher-claim has no outgoing
//     hapi:supersedes (multiple "first verdicts" on the same matcher-claim are a hard load error);
//     (c) insert-time tip-only rule — a non-root verdict-E13 must supersede the CURRENT chain tip
//     at insert time, not a mid-chain verdict (this closes the cycle gap that (a)+(b) alone leave
//     open: e.g. A→B→C→A is permitted by (a) and (b) since every node has one in and one out
//     edge and no node is a root; (c) prevents it by requiring C's supersedes to point at the
//     current tip, which is A only at the moment after A is inserted; once B is added, A is no
//     longer the tip). started_at / completed_at remain on the :D10 reviewer-run as informational
//     reproducibility metadata, NOT as the basis of supersession state.
//     The shortcut-emission rule (see §Shortcut triple emission for manifest interop) fires for
//     the matcher's hapi:same_entity_as claim only when the unique tip of the supersedes chain
//     covering the matcher's E13 has P141 → :E55 Type {id: 'hapi:verdict_approved'}.
//
//     Reviewer-run D1 provenance is fuller than a deterministic matcher's: the LLM reviewer's
//     reproducibility audit needs the prompt template, the source-side context that informed the
//     review, and a verdict-serialisation output, NOT just the candidate-claims input file. The
//     example below shows the minimum loadable set; the loader specification owns the per-stage
//     L10/L11 contract.
(:Statement:E13 verdict-claim)
  -[:P140_assigned_attribute_to]->    (:Statement:E13 matcher-claim)        // ← the matcher's E13 above
  -[:P141_assigned]->                  (:Type:E55 {id: 'hapi:verdict_approved'})
  -[:P177_assigned_property_of_type]-> (:Type:E55 {
                                           id:          'hapi:matcher_review_verdict',
                                           crm_nearest: 'crmdig:L43_annotates'    // documents the
                                                                                  // CRMdig conceptual
                                                                                  // affinity without
                                                                                  // expanding the
                                                                                  // consumed subset
                                       })
  -[:hapi:derived_by_run]->            (:MatcherRun:D10 reviewer-run {
                                           run_id:               'reviewer_run_2026_05_17T15_03Z',
                                           input_dataset_commit: 'a8f3e9d...',
                                           parameters_hash:      'sha256:9b2...',
                                           started_at:           '2026-05-17T15:03:11Z',
                                           completed_at:         '2026-05-17T15:08:42Z'
                                       })
  // No hapi:supersedes here — this is the FIRST verdict on the matcher-claim. A later revisit
  // would emit a second verdict-E13 carrying:
  //     -[:hapi:supersedes]-> (:Statement:E13 verdict-claim)    // ← THIS verdict
  // making the second verdict the new tip of the chain.

(:MatcherRun:D10 reviewer-run)
  -[:L23_used_software_or_firmware]-> (:MatcherAlgorithm:D14 {
                                           id: 'llm_reviewer_v1',
                                           version: '0.1.0',
                                           algorithm: 'claude-opus-4-7-review-prompt',
                                           hyperparameters_json: '{"temperature": 0.1, "seed": 42}',
                                           model_provider: 'anthropic',
                                           model_id:       'claude-opus-4-7',
                                           model_snapshot: 'claude-opus-4-7-20260501'   // dated provider snapshot
                                       })
  -[:L10_had_input]->                  (:SourceData:D1 {
                                           role:        'candidate_claims',
                                           path:        'matcher_outputs/run_2026_05_17T14_22Z.jsonl',
                                           git_commit:  'a8f3e9d...',
                                           sha256:      'sha256:c4d...'
                                       })
  -[:L10_had_input]->                  (:SourceData:D1 {
                                           role:        'prompt_template',
                                           path:        'reviewer_prompts/review_v1.md',
                                           git_commit:  'a8f3e9d...',
                                           sha256:      'sha256:e72...'
                                       })
  -[:L10_had_input]->                  (:SourceData:D1 {
                                           role:        'source_context_snippets',
                                           path:        'reviewer_inputs/run_2026_05_17T15_03Z_context.jsonl',
                                           git_commit:  'a8f3e9d...',
                                           sha256:      'sha256:f19...'
                                                                                // per-candidate source-side
                                                                                // excerpts the LLM saw
                                       })
  -[:L11_had_output]->                 (:SourceData:D1 {
                                           role:        'verdict_serialisation',
                                           path:        'reviewer_outputs/run_2026_05_17T15_03Z_verdicts.jsonl',
                                           sha256:      'sha256:a34...'
                                                                                // raw verdicts + per-verdict
                                                                                // reasoning trace, one row per
                                                                                // input candidate
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
//   :MatcherRun:D10_Software_Execution   — a specific execution that produced one or more Statements.
//                                          IS-A chain: D10 ⊂ D7 Digital Machine Event
//                                          ⊂ E11 Modification & E65 Creation ⊂ E7 Activity.
//                                          (NOT D3 Formal Derivation — D3 is for "version-of"
//                                          derivations like format conversions; matcher output is
//                                          different information, not a different form.)
//   :SourceData:D1_Digital_Object        — reconciled.jsonl files or other digital inputs/outputs.
//                                          IS-A chain: D1 ⊂ E73 Information Object.
// Every confidence/score on a derived Statement is reproducible by replaying the
// MatcherRun (D10) against its L10 input source files with its parameters_hash.
(:MatcherAlgorithm:D14 {id, version, algorithm, hyperparameters_json})
(:MatcherRun:D10       {run_id, input_dataset_commit, parameters_hash,
                        started_at, completed_at})
                       // No reviewer_status / reviewer_id / reviewed_at on MatcherRun — verdicts
                       // are their own E13s (see schema sketch case 4b), not in-place mutations.
(:SourceData:D1        {path, git_commit, ...})
```

Page-level citation lives as properties on the `P70i_is_documented_in` edge, not on the P14 edge — P14 attributes the *act* of assignment to its agent and has no slot for evidence pointers; P70i is the natural CIDOC home for "this assignment is recorded in this document at this page."

### Predicate registry

The predicate registry is the **controlled vocabulary of claim-predicates the loader knows about — scoped strictly to predicates that appear as P177 targets on E13 reifications**. E13-internal direct edges (`hapi:derived_by_run`, `hapi:supersedes`) are NOT in the registry — they are declared in the extension manifest for RDF/OWL interpretation but they never play the P177-target role and so have no registry entry. Verdict-outcome `:E55 Type` instances (`hapi:verdict_approved` etc.) are also outside the registry's scope — they are P141 values, not P177 targets; see the "Verdict-outcome controlled vocabulary" subsection.

Within the registry's P177-target scope, entries divide into two structurally distinct categories, distinguished by the `derived` field:

- **Primary (loadable) predicates** — `derived: false`. Each registry entry materialises an `:E55 Type` node that every E13's `P177_assigned_property_of_type` edge can point at; the `:E55 Type` table is the FK target for the P177 column; a Statement whose P177 target does not resolve to a primary-predicate registry entry fails the load. The corresponding manifest URI carries the `rdf:Property` + `crm:E55_Type` punning. Examples: `hapi:same_entity_as`, `hapi:tomb_owner`, `hapi:original_burial_in`, `hapi:cache_context_at`, `hapi:in_dynastic_period`, `hapi:display_name`, `hapi:reign_period`, `hapi:horus_name`, `hapi:matcher_review_verdict`.
- **Derived / query-only predicates** — `derived: true`. These are still in the registry (for vocabulary control — preventing drift like `buried_in` / `interred_at` / `tomb_location`), but they are NOT materialised as `:E55 Type` instances. The corresponding manifest URI carries `rdf:Property` only (plus `owl:SymmetricProperty` if symmetric). The loader REJECTS any incoming E13 reification whose P177 target is a derived predicate; the predicate exists only as query-output triples materialised by a committed query definition from underlying primary E13s. Provenance lives on those underlying primary E13s, not on the derived edge. Currently one entry: `hapi:shares_tomb_with`.

The registry is the authoritative vocabulary for P177-target predicates in both categories. Each entry is mandatory in all fields below; missing fields fail validation at registry-load time. The `p177_target` field (rule: `p177_target = NOT derived`, scoped within the registry) is what the loader uses to route each entry to the right enforcement path. E13-internal predicates outside the registry get manifest-load validation only — the validator subagent checks that any `hapi:`-namespaced predicate referenced in the ADR or schema sketches is declared in the manifest; what's in the registry is the further P177-target sub-set.

| Field                 | Type                       | Purpose |
|-----------------------|----------------------------|---------|
| `id`                  | string (PK)                | `hapi:<name>` for Hapi predicates; CIDOC P-number (e.g. `P14`) for direct CRM properties |
| `label`               | string                     | human-readable name for review queues and UI |
| `definition`          | string                     | one-paragraph definition of what the predicate means and when it applies |
| `subject_class`       | CIDOC E-class or set       | e.g. `E21 Person` for `hapi:reign_period`; `E27 Site` for some-future-Site-scoped-predicate (`example:located_in` is shown here only as a schema-illustration placeholder, not an actual Hapi predicate). |
| `value_class`         | CIDOC E-class or set       | e.g. `E41 Appellation` for `hapi:horus_name`; `E4 Period` for `hapi:in_dynastic_period`; `E1 CRM Entity` for `hapi:same_entity_as` (the predicate is declared E1↔E1 in the manifest, matching `crmdig:L54_is_same_as`'s domain/range — Hapi `same_entity_as` claims can link `:Ruler` to `:Ruler`, `:Site` to `:Site`, etc., so the narrowest common ancestor is E1, not E21). |
| `value_cardinality`   | `single` \| `multi`        | whether a subject can have one or many active claims of this predicate |
| `crm_nearest`         | CIDOC P-number \| CRMdig L-property \| `null` | nearest CRM-family property for interop documentation. Accepts core CIDOC CRM P-numbers AND CRMdig L-properties (e.g. `L54_is_same_as` for `hapi:same_entity_as`; `L43_annotates` for `hapi:matcher_review_verdict` — documentation-only, NOT a subPropertyOf declaration, since L43's D29 domain doesn't accept E13 subjects). `null` if no clean fit. |
| `is_symmetric`        | bool                       | whether the predicate is symmetric (e.g. `hapi:same_entity_as` is) |
| `derived`             | bool                       | whether the predicate is derived from other claims (loader REJECTS direct assertions) vs loadable as a primary claim from a source. `hapi:shares_tomb_with` is the first derived predicate — it's materialised at query time by intersecting two rulers' actual-burial site sets (only from `hapi:original_burial_in` and `hapi:cache_context_at`; NOT from `hapi:tomb_owner`, which is commissioning rather than interment). Asserting it directly would lose the site/context information. Default `false`. |
| `p177_target`         | bool                       | whether the predicate URI is materialised as an `:E55 Type` instance and serves as a P177 target on E13 reifications. Within the registry's scope (P177-target predicates only), this is derived: `p177_target = NOT derived`. The loader uses this field to decide enforcement: `p177_target = true` entries get FK enforcement of the P177 column against the `:E55 Type` table; `p177_target = false` entries are vocabulary-only with no FK enforcement on the predicate-URI side (the loader REJECTS any E13 reification whose P177 target is one of these). Stored explicitly rather than derived at query time so that downstream consumers reading the registry don't have to re-derive the rule. (E13-internal direct edges like `hapi:derived_by_run` and `hapi:supersedes` are outside the registry entirely, so this field doesn't apply to them — they have no registry entry at all.) |
| `emit_shortcut`       | bool                       | whether the loader emits a direct `(subject) hapi:<predicate> (value)` shortcut triple alongside the E13 reification (see "Shortcut triple emission for manifest interop"). Permitted ONLY when `p177_target: true`; required `false` when `p177_target: false`. Default `true` for primary P177-target predicates (the matching queries traverse the direct edges). Explicitly `false` for `hapi:matcher_review_verdict`: the verdict-E13's P141 vocabulary (the verdict-outcome E55 Types) isn't a useful direct-query target, AND emitting verdict shortcuts would recurse the matcher-derived-claims gating rule. The loader validates this field on registry load: a `p177_target: false` entry with `emit_shortcut: true` is a hard load error. |
| `notes`               | string \| `null`           | rationale, scope notes, known edge cases |

Adding a new **P177-target claim predicate** (the only kind this registry scopes) is an INSERT into this registry preceded by a review against existing predicates to avoid `buried_in` / `interred_at` / `tomb_location` vocabulary drift. The registry is committed to version control (`pipeline/pipeline/authority/predicate_registry.json` — exact path resolved during implementation) and validated by a CI test that loads each entry and asserts every required field is populated and that referenced E-classes exist in the class catalogue. (Adding a new E13-internal direct-edge predicate or a new controlled-vocabulary E55 Type instance follows a different path: directly into the extension manifest, validated by the cidoc-crm-validator subagent at PR time — see principle 4.)

### Verdict-outcome controlled vocabulary

The predicate `hapi:matcher_review_verdict` (P177 type on verdict-E13s, see schema sketch case 4b) takes its P141 value from a **closed three-term vocabulary**. Each term is a separately-declared `:E55 Type` instance — formally declared in the extension manifest as `rdf:type crm:E55_Type`, NOT a magic-string in prose. The loader REJECTS any verdict-E13 whose P141 value isn't one of these three IDs.

| `:E55 Type` id (URI) | label | meaning |
|---|---|---|
| `hapi:verdict_approved` | reviewer approved | the LLM reviewer accepts the matcher's candidate identity claim. The matcher's claim becomes eligible for shortcut-triple emission IF this verdict-E13 is the unique tip of the supersession chain. |
| `hapi:verdict_rejected` | reviewer rejected | the LLM reviewer rejects the matcher's candidate. No shortcut emission. The matcher's E13 remains in the graph (as a candidate-claim record); the verdict is the authoritative reason it isn't materialised. |
| `hapi:verdict_retracted` | reviewer retracted (no current position) | reserved for the explicit "no current position" case — the reviewer is on record as withdrawing a previous verdict without substituting a new substantive one (e.g. the candidate has been removed from the matcher's input set; the reviewer no longer has a position; the basis of the previous verdict no longer holds). Emitted as the P141 value of a NEW verdict-E13 that carries `hapi:supersedes` to the previous tip; the new verdict-E13 becomes the chain's tip. No shortcut emission (tip-outcome ≠ `hapi:verdict_approved`). NOT applied retroactively to a previous tip — the previous tip's recorded outcome stays as recorded; supersession is encoded by the new verdict's `hapi:supersedes` edge. (Renamed from the earlier label `verdict_superseded` — no `hapi:` prefix because that URI was never declared in the manifest; it existed only in a draft revision of this ADR before the rename. A tip-outcome called "superseded" was contradictory, since "superseded" is precisely the structural condition that makes a verdict-E13 NOT the tip. "Retracted" captures the actual semantic — the reviewer is withdrawing a position without substituting a new one.) |

Each of these three `:E55 Type` instances is declared in `pipeline/pipeline/authority/hapi_extension.rdf` as an explicit `<rdf:Description rdf:about="#verdict_..."><rdf:type rdf:resource="...E55_Type"/></rdf:Description>` entry. The supersession edge is the `hapi:supersedes` predicate (separately declared in the manifest), domain `:E13`, range `:E13`, free-standing for now — no clean CRM superproperty was identified; P132_overlaps_with and similar candidates don't fit "this assertion replaces that one" semantics. **Chain integrity requires three complementary load-time constraints**, all three required for the "unique linear chain with one tip" property to hold:

- **(a) unique successor per predecessor.** Each verdict-E13 has at most one incoming `hapi:supersedes`. In Postgres terms: a UNIQUE constraint over the `predecessor_verdict_id` column.
- **(b) unique root per matcher-claim.** At most one verdict-E13 covering a given matcher-claim has no outgoing `hapi:supersedes`. In Postgres terms: a partial UNIQUE constraint over the `(matcher_claim_id) WHERE predecessor_verdict_id IS NULL` predicate.
- **(c) insert-time tip-only rule.** A non-root verdict-E13 inserted at time T must point its `hapi:supersedes` edge at the current chain tip at time T (the verdict-E13 covering the same matcher-claim that has no incoming `hapi:supersedes` at insert time). The loader REJECTS a non-root insert that supersedes a non-tip (mid-chain) verdict-E13. In Postgres terms: a BEFORE-INSERT trigger (or an equivalent transactional application-layer validation inside the loader's insert path) that verifies `predecessor_verdict_id` references a verdict-E13 with zero successors at the moment of the insert. This **cannot** be a plain `CHECK` constraint — Postgres `CHECK` constraints can only inspect columns of the row being checked and cannot query other rows. The trigger or loader-side check needs to run a sub-query of the form `NOT EXISTS (SELECT 1 FROM verdict_e13 WHERE predecessor_verdict_id = NEW.predecessor_verdict_id)` against the same table, which is trigger / application-code territory. The serialisable transaction isolation level (or an equivalent advisory lock on the matcher-claim's chain) is also needed to prevent race conditions where two concurrent inserts each see the predecessor as a tip and both succeed; that's a transactional concern, again outside what a `CHECK` can do.

Constraints (a) and (b) alone are insufficient because they permit cycles — e.g. `A→B→C→A` for the same matcher-claim. Every node in such a cycle has exactly one in-edge and one out-edge (so (a) doesn't fire), and no node has no out-edge (so (b) doesn't fire — there is no root). The cycle would silently leave the matcher-claim's "current verdict" undefined. Constraint (c) closes this gap: new edges always attach to the tip, so the chain remains a single linear sequence with one root and one tip — never a cycle, never disconnected sub-chains.

### What this does not decide

- **Storage technology** — Postgres (with relational encoding of the graph, or with the Apache AGE extension) and Neo4j (self-hosted Community or Aura managed) are the two viable candidates. A separate ADR will resolve this based on the pilot evidence accumulated under this model. Until then, the conceptual model is binding; the storage substrate is open.
- **The relational vs property-graph encoding of E13.** Whether Statements are tables with FK columns or first-class graph nodes follows from the storage choice. Both encodings preserve the CIDOC mapping above; specifying the encoding before the storage ADR pre-decides storage.
- **Per-predicate resolution policies beyond `hapi:display_name`** — the *default* is fail-loud (principle 7); the *first concrete policy* is committed above for `hapi:display_name`. Additional per-predicate rules (which document wins for `hapi:reign_period`, `hapi:in_dynastic_period`, etc., or for finer-grained successors of those that may emerge later) accumulate in the policy registry as downstream consumers demand them. The registry's exact location and review process is a follow-up ADR.
- **Phase C feedback cadence** — when an approved fuzzy match in the review queue produces a new alias, when does the alias get added as a claim? Per-approval, batched, or blocked until a Phase B pass completes? Tracked in #221.

## Storage candidates (deferred)

Two viable candidates, evaluated against the model above. A follow-up ADR will choose between them.

### Postgres (relational encoding or with Apache AGE)

- **Pro:** ADR-004 + ADR-011 already commit Postgres as canonical store. SQLAlchemy + Alembic + Drizzle introspection toolchain is already wired up. Artifacts (millions, property-heavy, search-driven) stay in Postgres; authority graph in the same database keeps artifact ↔ authority joins as single-DB SQL. No new ops surface. Apache 2.0 license, no per-GB pricing.
- **Pro:** Predicates-as-rows pattern gives FK-enforced verify-before-create for primary P177-target predicates (`p177_target: true`) — the `:E55 Type` table is the FK target for the E13.P177 column, with zero migrations per new predicate. Derived / query-only predicates (`p177_target: false`) get the same registry control via loader-side rejection of P177 = derived-predicate-URI assertions (per the bifurcated enforcement story documented in the predicate-registry section and the Implications bullet on registry-as-vocabulary-contract).
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

A naive `example:buried_in` predicate (not a Hapi predicate — shown here only to illustrate the rejected design) that conflates these three loses information and produces wrong matches: a stela of Ramesses I found in the KV35 cache is not evidence that Ramesses I owned, was originally buried in, or has any primary association with KV35 — it was moved there ~400 years after his death. The open schema accommodates the distinction natively; rigorous matching demands it. The Haiku step becomes a fallback for genuinely ambiguous cases (overlapping co-regencies, post-burial usurpations, ambiguous cache attributions), not the primary disambiguation mechanism.

**On the CIDOC status of these predicates.** Three of the four tomb predicates (`hapi:tomb_owner`, `hapi:original_burial_in`, `hapi:cache_context_at`) connect a `:Ruler` (E21 Person) directly to a `:Site` (E27 Site) and are documented as **pragmatic Hapi-domain predicates**, free-standing (no `rdfs:subPropertyOf`) and loadable as primary claims from sources. The fourth, `hapi:shares_tomb_with`, is a symmetric `:Ruler` ↔ `:Ruler` relation declared `owl:SymmetricProperty` in the manifest — but it is a **derived / query-only predicate**, not loadable as a primary claim (see the "free-standing predicates" section above for the rationale: asserting it directly would lose the site and burial-context information the rest of the model exists to preserve). Two things worth noting honestly about the three primary Ruler→Site predicates:

1. **CIDOC core has no clean superproperty for this shape.** The closest candidate, `P53_has_former_or_current_location`, has domain `E18 Physical Thing` (which E21 satisfies via E21 ⊂ E20 ⊂ E19 ⊂ E18) and range `E53 Place` (which E27 Site does *not* satisfy — E27 ⊂ E26 ⊂ E18, not ⊂ E53). A `subPropertyOf P53` declaration would escape P53's range, which the "narrow not violate" rule forbids. So these are genuine domain extensions, not shortcut workarounds.

2. **A Hapi choice from the shapes CIDOC's open extension model permits.** CIDOC permits multiple modelling shapes for relationships like Ruler↔Site burial context — including (a) direct shortcut predicates between domain entities, when the use-case doesn't need fine-grained event provenance, and (b) reification through intermediate event entities (excavation, interment, etc.) when archaeological-stratigraphy queries are central. Hapi uses (a); the matching use-case ("show me artefacts associated with this ruler / this tomb-context") doesn't require (b). The shape (b) alternative is documented in CRMarchaeo, the official CIDOC archaeology extension (https://cidoc-crm.org/crmarchaeo/) — but **CRMarchaeo is NOT vendored in this repo** (see `pipeline/pipeline/authority/spec/README.md`), so this ADR's CRMarchaeo reference is a URL pointer, not an in-tree-validated conformance claim. The conformance contract is strictly the vendored CRM 7.1.3 + CRMdig 5.0 files. If a future Hapi feature needs CRMarchaeo's rigorous archaeological shapes, CRMarchaeo gets vendored alongside (per the README's CRMsci-carve-out pin discipline) and only then does it become part of the conformance argument. Each Hapi tomb predicate captures a structurally distinct relationship (commissioning, primary burial, secondary cache reburial, joint burial — the last between two persons rather than a person and a place); the CRMarchaeo-rigorous shapes for any of these are not sketched here and are out of scope until the vendor decision is made.

If a future use-case requires CRMarchaeo-style stratigraphic querying or commissioner-specific provenance, the richer model can be layered on top — the Hapi predicates here and the rigorous chain coexist.

A follow-up ADR will revise ADR-009 to specify the constraint-narrowed algorithm in detail once storage tech is decided.

## Consequences

- **Phase 0 output shape changes.** Sources still produce `reconciled.jsonl`, but the downstream loader emits per-source E13 Statements, not collapsed per-entity rows. The 3-agent extraction step's job is unchanged (faithful capture of the source); per-row resolution still follows the Rule-2 decision tree (unanimity / majority / `tie-break-overrides.json` / documented policy) — the loader trusts whatever the existing pipeline emits and never re-resolves at the graph layer.
- **Reconciliation semantics change.** "Reconciliation" no longer means "pick one value across sources"; it means "load all sources' claims into the graph and let the resolution policy (per-predicate, per-consumer) decide what to surface." The current `tie-break-overrides.json` becomes **pipeline QA provenance**, not scholarly citation evidence. Tie-break overrides justify *extraction arbitration* (which of the 3 agents' readings of the source was correct), not the source publication's historical claim itself; they sit in a separate QA-provenance layer attached to the loader event or extraction step that produced the Statement, queryable as "how was this Statement produced" rather than "who attested to this Statement." A Statement's scholarly citation chain remains P14 → scholar + P70i → publication; QA provenance lives alongside, never inside, that chain.
- **Disagreements become first-class artifacts.** The UI can honestly show "1353–1336 BCE (Leprohon 2013) / 1352–1335 BCE (Dodson-Hilton 2010)" instead of pretending certainty it doesn't have. Authority disagreements appear in search snippets, hover cards, and the artifact detail page.
- **Cross-source identity becomes data, not a structural primitive.** Adding a new source (Hornung, Kitchen, Ryholt) does not require re-curation of existing entities. It adds per-source nodes that get linked to existing nodes via `hapi:same_entity_as` Statements emitted by the **two-stage matcher pipeline**: a deterministic stage-1 matcher (`:D10 Software Execution`, attached via `hapi:derived_by_run`) produces candidate same-entity-as E13s, and a stage-2 LLM reviewer evaluates each candidate and emits a verdict-E13 pointing at the candidate (see schema sketch case 4b). Downstream consumers see the matcher's identity claim as a queryable direct edge (the shortcut-triple) only when the unique tip of the verdict supersession chain for that candidate has P141 = `hapi:verdict_approved`. A canonical-person view, if needed, can be derived from approved-`same_entity_as` clusters as a materialized view; the source of truth remains the per-source nodes plus their identity claims and the reviewer's verdicts on them. (Human curator attribution via P14 + P70i is reserved for explicitly-curatorial decisions on the same data — e.g. a curator overriding a reviewer verdict — and is a separate provenance shape, not a fallback for matcher claims.)
- **The predicate registry becomes the vocabulary contract for P177-target claim predicates.** Any new claim predicate (primary or derived) proposed by an agent, a Phase 0 chunk, or a contributor must be reviewed against the registry. Enforcement is bifurcated per the registry's `p177_target` field (see "Predicate registry" section): **primary predicates** (`p177_target: true`) are FK-enforced at the DB layer — their `:E55 Type` instances are the FK target for E13.P177, and an E13 with an unregistered P177 target fails the load on the FK constraint. **Derived / query-only predicates** (`p177_target: false`) are registry-validated and explicitly rejected as P177 targets by the loader — the rejection is loader-side application logic, not a DB-level FK (since no `:E55 Type` instance exists to FK against). Non-claim-predicate manifest terms (E13-internal direct edges; controlled-vocabulary E55 Type instances) follow the manifest-only path documented in principle 4 above. In all paths, convention is not enough; enforcement is deterministic and Rule-3-compliant.
- **Citation network becomes queryable.** Citation tokens currently buried as text inside Leprohon's `source_note` fields (referencing Beckerath 1999, Gauthier 1907, Wilkinson 2000, etc.) become explicit edges from Statements to Citation nodes, queryable as "claims about Akhenaten that cite Wilkinson" or "what does Leprohon cite that we have no authority data for."
- **`attested_in` becomes the bridge to artifacts.** Attestation entries currently nested inside Leprohon name qualifiers become explicit edges from Name Statements to Inscription / Artifact nodes, linking the authority layer to the museum layer at the data level.
- **Temporal phases gain structure without canonicalisation.** Leprohon's split of Akhenaten into "Amenhotep IV (Regnal Years 1 to 5)" + "Akhenaten (Regnal Years 5 to 17)" produces two per-source `:Ruler` nodes (two rows in Leprohon, two nodes in the graph). They are linked by a `hapi:same_entity_as` Statement attributed to the source itself — Leprohon's text explicitly identifies the two as a single ruler at different naming phases. Each `:Ruler` carries its own `hapi:reign_period` Statement covering the relevant regnal years. Beckerath's single "Amenophis IV. Ach-en-aten" row becomes a third per-source `:Ruler` node, linked to either of the Leprohon nodes via a separate cross-source `hapi:same_entity_as` Statement emitted by the two-stage matcher pipeline (stage-1 deterministic matcher → stage-2 LLM-reviewer verdict; the shortcut-triple materialises only when the supersession-chain tip is an approved verdict). No canonical Person is materialised at load time; the "same person, different naming period" structure is data, not schema.
- **The storage decision is the gating follow-up.** Until ADR-019 (or the storage ADR, whatever number it lands at) is resolved, no production graph build can start. A Phase 0 → graph loader can be sketched against either substrate.
