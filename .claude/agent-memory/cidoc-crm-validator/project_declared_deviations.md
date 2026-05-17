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

4. **P82a/P82b values stored as inlined signed integer years rather than `xsd:dateTime` literals.**
   - Rationale: Strict CRM 7.1.3 (per the RDFS) declares P82a/P82b with range `rdfs:Literal` (effectively `xsd:dateTime`). The property-graph encoding stores year boundaries as signed integers on the `:TimeSpan:E52` node together with a `calendar` field.
   - Containment: limited to `:TimeSpan:E52` nodes; the rest of the model uses P82a/P82b conceptually but does not store other date forms in the graph.
   - Round-trip mapping: each integer N expands to xsd:dateTime `<N>-01-01T00:00:00Z` (begin-of-year for P82a) or `<N>-12-31T23:59:59Z` (end-of-year for P82b).
   - Assessment (2026-05-17): Newly declared; previously a soft issue under the old taxonomy. Now properly declared per the no-soft-issues rule.

5. **Citation properties (`cited_page`, `cited_pdf_page`) on the `P70i_is_documented_in` edge.**
   - Rationale: Strict CRM 7.1.3 has no `.1` sub-property of P70 for page citations. Strictly conformant encoding requires reifying each cited passage as an E73 Information Object with an E42 Identifier for the page; that adds an intermediate node per citation.
   - Containment: limited to the `P70i_is_documented_in` edge; no other property in the model is sub-typed with `.1` properties.
   - Round-trip mapping: each citation-bearing edge expands at export time into an intermediate `:E73 Information Object` carrying `cited_page`/`cited_pdf_page` as `:E42 Identifier` references, with the E13 → E31 link routed through the E73.
   - Assessment (2026-05-17): Newly declared; previously a soft issue under the old taxonomy. Now properly declared per the no-soft-issues rule.

## Implicit deviation noted but not separately listed in ADR-018

- **MatcherRun pattern.** The schema sketch introduces `:MatcherRun` as a separate node holding reproducibility metadata, with edges `hapi:derived_by` (E13 → MatcherRun) and `hapi:uses_matcher` (MatcherRun → Matcher). This composes on top of deviation #1 (`:Matcher` is non-CRM) and inherits its justification. Not a separate deviation, but worth tracking as a refinement.

## Taxonomy note (2026-05-17 update)

The validator brief no longer recognises "soft issues." Every CRM spec violation is binary: declared deviation (per the four properties above — rationale, containment, round-trip mapping, assessment) → clean by deviation, or undeclared → hard error. Pre-update findings filed under "soft issue" must be either promoted to declared deviations or filed as hard errors.
