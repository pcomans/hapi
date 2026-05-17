# CIDOC CRM 7.1.3 — Property cache

Source: RDFS at https://cidoc-crm.org/rdfs/7.1.3/CIDOC_CRM_v7.1.3.rdf (machine-readable check, primary), with conceptual range from the release at https://cidoc-crm.org/Version/version-7.1.3 (authoritative model definition) noted in the "Conceptual range" column where relevant.

Encoding note from the RDFS preamble (rule 3): E60 Number, E61 Time Primitive, E62 String, E94 Space Primitive, E95 Spacetime Primitive are collapsed to `rdfs:Literal` in the RDFS encoding. The conceptual range from the release definition is what the model *means*; the RDFS range is what an automated checker sees. Both are correct — and below the RDFS-emitted range is the authoritative column for syntactic validation.

| P# | Name | RDFS domain | RDFS range | Conceptual range (release) | Notes |
|---|---|---|---|---|---|
| P3   | has note | E1 CRM Entity | rdfs:Literal | E62 String | Available on every CRM entity; valid attachment point for unstructured annotation. |
| P14  | carried out by | E7 Activity | E39 Actor | E39 Actor | E13 IS-A E7, so P14 attaches to E13 by inheritance. Range is E39 (E21 Person and E74 Group are valid by subsumption; E31 Document is NOT). |
| P67  | refers to | **E89 Propositional Object** | E1 CRM Entity | E1 CRM Entity | Domain is E89 — E13 IS-A E7, NOT a subclass of E89, so P67 cannot originate from E13 directly. E31 Document, E33 Linguistic Object, and E73 Information Object all IS-A E89. |
| P70  | documents | E31 Document | E1 CRM Entity | E1 CRM Entity | Inverse: P70i_is_documented_in has domain E1, range E31. |
| P81  | ongoing throughout | E52 Time-Span | rdfs:Literal | E61 Time Primitive | RDFS encoding rule 3 collapses E61 to rdfs:Literal. |
| P81a | end of the begin | E52 Time-Span | rdfs:Literal | E61 Time Primitive | Subproperty of P81. Confirmed present in 7.1.3 RDFS. |
| P81b | begin of the end | E52 Time-Span | rdfs:Literal | E61 Time Primitive | Subproperty of P81. |
| P82  | at some time within | E52 Time-Span | rdfs:Literal | E61 Time Primitive | |
| P82a | begin of the begin | E52 Time-Span | rdfs:Literal | E61 Time Primitive | Subproperty of P82. Confirmed present in 7.1.3 RDFS. |
| P82b | end of the end | E52 Time-Span | rdfs:Literal | E61 Time Primitive | Subproperty of P82. |
| P90  | has value | E54 Dimension | rdfs:Literal | E60 Number | RDFS encoding rule 3 collapses E60 to rdfs:Literal. |
| P91  | has unit | E54 Dimension | E58 Measurement Unit | E58 Measurement Unit | E58 IS-A E55 Type. |
| P129 | is about | E89 Propositional Object | E1 CRM Entity | E1 CRM Entity | Subproperty of P67. |
| P140 | assigned attribute to | E13 Attribute Assignment | E1 CRM Entity | E1 CRM Entity | |
| P141 | assigned | E13 Attribute Assignment | **E1 CRM Entity** | E1 CRM Entity | Range is E1 — literals are NOT in range. Wrap literals in a value-bearing entity (E41 Appellation, E52 Time-Span, E54 Dimension). |
| P148 | has component | **E89 Propositional Object** | E89 Propositional Object | E89 → E89 | E31 IS-A E73 IS-A E89, so an E31-to-E31 component edge is valid by subsumption. |
| P177 | assigned property of type | E13 Attribute Assignment | E55 Type | E55 Type | The predicate registry catalogue. |
| P190 | has symbolic content | **E90 Symbolic Object** | rdfs:Literal | E62 String | RDFS encoding rule 3 collapses E62 to rdfs:Literal. E41 Appellation IS-A E90, so applies via inheritance. |

Verified against the RDF on 2026-05-17 via `curl https://cidoc-crm.org/rdfs/7.1.3/CIDOC_CRM_v7.1.3.rdf | grep` of each property's rdf:Property block. Cache invalidates when the CRM pin moves.
