# Project-declared deviations from strict CIDOC CRM 7.1.3

Tracks every deviation Hapi has explicitly declared in an ADR or predicate-registry entry. Each entry must have: rationale, containment, round-trip mapping to strict CRM/RDF, and an assessment date.

## ADR-018: Authority Layer as Source-Attributed Claim Graph

Section: "Declared deviations from strict CRM 7.1.3" (now five entries as of c.f. HEAD; previously three).

1. **`:Matcher` is not E39 Actor.**
   - Rationale: CRM core has no clean class for software agents; CRMdig's D7 Digital Machine Event is an extension, not core.
   - Containment: Automated-derivation provenance attaches via `hapi:derived_by`, not P14. Trust signal lives in the edge type so consumers can filter without parsing actor properties.
   - Round-trip mapping: under a CRMdig export, `:Matcher` maps to D7 Digital Machine Event and `:MatcherRun` to a specific D-class subclass; under a core-CRM-only export, the matcher provenance becomes an E73 Information Object annotation on the E13.
   - Assessment (2026-05-17): Real deviation, properly contained.

2. **Property-graph inlining of value-entity literals.**
   - Rationale: Strict CRM stores literals on value entities via P190 (E41 → E62 String), P90 (E54 → E60 Number). The property-graph encoding inlines as direct properties on the value-entity node.
   - Containment: Mapping is mechanical and round-trippable to strict CRM/RDF export.
   - Round-trip mapping: each inlined literal property expands to a P190/P90 edge from the value-entity to an E62/E60 literal node.
   - Assessment (2026-05-17): Real deviation, properly contained.

3. **`hapi:` namespace predicates where CRM has no clean fit.**
   - Examples: `hapi:same_entity_as`, `hapi:buried_in`, `hapi:tomb_owner`, `hapi:original_burial_in`, `hapi:cache_context_at`, `hapi:shares_tomb_with`, `hapi:derived_by`.
   - Rationale: CRM has no clean property for these heritage-domain relations.
   - Containment: Each entry in the predicate registry carries a `crm_nearest` field pointing at the nearest CIDOC property.
   - Round-trip mapping: at strict-RDF export, each `hapi:` predicate maps either to its `crm_nearest` (lossy) or to a named extension property (lossless if the receiving system speaks the extension).
   - Assessment (2026-05-17): Real deviation, properly contained.

4. **P82a/P82b values stored as inlined signed integer years.**
   - Rationale: The RDFS at https://cidoc-crm.org/rdfs/7.1.3/CIDOC_CRM_v7.1.3.rdf declares P82a/P82b with range `rdfs:Literal` (encoding rule 3 collapses the conceptual E61 Time Primitive to `rdfs:Literal`). The RDFS imposes no specific lexical form. The property-graph encoding stores year boundaries as signed integers on the `:TimeSpan:E52` node together with an explicit `calendar` field.
   - Containment: limited to `:TimeSpan:E52` nodes.
   - Round-trip mapping: each `(integer, calendar)` pair serialises to a string `rdfs:Literal` in a Hapi-defined lexical form pinned by the loader specification. **This is a Hapi convention layered on CRM's `rdfs:Literal` range, NOT a CRM-mandated form.** BCE-year serialisation in particular is delicate (XML Schema 1.1 expanded-year, ISO 8601 astronomical, `xsd:dateTime` all differ on negative years); the loader pins one explicitly.
   - Assessment (2026-05-17): Corrected this revision. Previously claimed `xsd:dateTime` round-trip as if it were CRM-standard — that claim was overconfident. The RDFS only requires `rdfs:Literal`; the lexical form is Hapi-defined.

5. **Citation properties (`cited_page`, `cited_pdf_page`) on the `P70i_is_documented_in` edge.**
   - Rationale: Strict CRM 7.1.3 has no `.1` sub-property of P70 for page citations. The edge-property idiom is a Hapi compactness choice.
   - Containment: limited to the `P70i_is_documented_in` edge.
   - Round-trip mapping (every property's domain/range satisfied):
     - For each distinct (publication, page) pair, materialise the page as its own `:E31 Document` (e.g. `leprohon_2013_p115`).
     - Bind page-level E31 to publication-level E31 via `P148i_is_component_of` (P148 domain and range are E89 Propositional Object; E31 IS-A E73 IS-A E89, so both ends valid by subsumption).
     - Identify the page-level E31 via `P1_is_identified_by → :E42 Identifier {value: 'p. 115'}` (P1 domain E1, range E41; E42 IS-A E41 by subsumption).
     - Rewrite the original E13 → P70i → publication-level E31 to point at the page-level E31 instead. **P70i's range stays E31 throughout** — no rerouting through E73/E33 is required.
   - Assessment (2026-05-17): Corrected this revision. Previously the mapping said "route the E13 → E31 link through an intermediate E73," which would have broken P70i's E31 range constraint. Sub-E31 component pattern keeps P70i's range satisfied at every step.

## Implicit deviation noted but not separately listed in ADR-018

- **MatcherRun pattern.** The schema sketch introduces `:MatcherRun` as a separate node holding reproducibility metadata, with edges `hapi:derived_by` (E13 → MatcherRun) and `hapi:uses_matcher` (MatcherRun → Matcher). This composes on top of deviation #1 (`:Matcher` is non-CRM) and inherits its justification. Not a separate deviation, but worth tracking as a refinement.

## Taxonomy note (2026-05-17 update)

The validator brief no longer recognises "soft issues." Every CRM spec violation is binary: declared deviation (per the four properties above — rationale, containment, round-trip mapping, assessment) → clean by deviation, or undeclared → hard error. Pre-update findings filed under "soft issue" must be either promoted to declared deviations or filed as hard errors.
