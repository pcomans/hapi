# Project-declared deviations from strict CIDOC CRM 7.1.3

Tracks every deviation Hapi has explicitly declared in an ADR or predicate-registry entry.

## ADR-018: Authority Layer as Source-Attributed Claim Graph

Section: "Declared deviations from strict CRM 7.1.3" (lines 59–63 at HEAD on this run).

1. **`:Matcher` is not E39 Actor.**
   - Rationale: CRM core has no clean class for software agents; CRMdig's D7 Digital Machine Event is an extension, not core.
   - Containment: Automated-derivation provenance attaches via `hapi:derived_by`, not P14. Trust signal lives in the edge type so consumers can filter without parsing actor properties.
   - Assessment (2026-05-17): Real deviation, properly contained.

2. **Property-graph inlining of value-entity literals.**
   - Rationale: Strict CRM stores literals on value entities via P190 (E41 → E62), P90 (E54 → E60), etc. The property-graph encoding inlines as direct properties on the value-entity node.
   - Containment: Mapping is mechanical and round-trippable to strict CRM/RDF export.
   - Assessment (2026-05-17): Real deviation, properly contained. Note: for P82a/P82b this is *less* of a deviation than the ADR implies — those properties' formal RDFS range in 7.1.3 is rdfs:Literal (xsd:dateTime), so inlining them as Time-Span node properties is closer to faithful than to deviant.

3. **`hapi:` namespace predicates where CRM has no clean fit.**
   - Examples: `hapi:same_entity_as`, `hapi:buried_in`, `hapi:shares_tomb_with`, `hapi:derived_by`.
   - Rationale: CRM has no clean property for these heritage-domain relations.
   - Containment: Each entry in the predicate registry carries a `crm_nearest` field pointing at the nearest CIDOC property.
   - Assessment (2026-05-17): Real deviation, properly contained.

## Additional implicit deviation noted but not separately listed in ADR-018

- **MatcherRun pattern.** The schema sketch introduces `:MatcherRun` as a separate node holding reproducibility metadata, with edges `hapi:derived_by` (E13 → MatcherRun) and `hapi:uses_matcher` (MatcherRun → Matcher). This composes on top of deviation #1 (`:Matcher` is non-CRM) and inherits its justification. Not a separate deviation, but worth tracking as a refinement.
