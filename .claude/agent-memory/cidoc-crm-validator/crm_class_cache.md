# CIDOC CRM 7.1.3 — Class cache

Source: https://cidoc-crm.org/html/cidoc_crm_v7.1.3.html (single-page HTML, RDFS at /rdfs/7.1.3/CIDOC_CRM_v7.1.3.rdf)
Pinned by Hapi in ADR-018.

| Class | Name | SubClassOf chain | Notes |
|---|---|---|---|
| E1  | CRM Entity | (root) | |
| E2  | Temporal Entity | E1 | |
| E4  | Period | E2, E92 Spacetime Volume | Superclass of E5 Event |
| E5  | Event | E4 | |
| E7  | Activity | E5 → E4 → E2 → E1 | |
| E13 | Attribute Assignment | E7 → E5 → E4 → E2 → E1 | The reified-assertion class. Inherits P14 from E7. |
| E18 | Physical Thing | E72 → E1 | |
| E21 | Person | E20 Biological Object, **E39 Actor** | Subclass of E39 — key for P14 range. |
| E26 | Physical Feature | E18 | |
| E27 | Site | E26 → E18 → E72 → E1 | Physical archaeological place. |
| E28 | Conceptual Object | E71 → E77 → E1 | |
| E31 | Document | E73 Information Object → E89 Propositional Object → E28 Conceptual Object → E71 Human-Made Thing → E77 → E1 | **NOT a subclass of E39 Actor.** |
| E33 | Linguistic Object | E73 Information Object → E89 → E28 → E71 → E70 → E77 → E1 | Used in deviation #5 round-trip mapping (alongside E73). |
| E39 | Actor | E77 Persistent Item → E1 | Direct subclasses: E21 Person, E74 Group. |
| E41 | Appellation | E90 Symbolic Object → E73 Information Object → E28 → E71 → E1 | P190 reachable via inheritance from E90. |
| E42 | Identifier | E41 Appellation → E90 → E73 → E28 → E71 → E1 (per RDFS); HTML page lists parent as E90 Symbolic Object | Used in deviation #5 round-trip mapping for page citations. Both parents reachable; inherits from E90 either way. |
| E52 | Time-Span | E1 (direct) | Has P82a/P82b as begin/end value-bearing subproperties. |
| E54 | Dimension | E1 (direct) | P90 has value (→ E60 Number); P91 has unit (→ E58 Measurement Unit). |
| E55 | Type | E28 → E71 → E77 → E1 | The class for the predicate registry. |
| E58 | Measurement Unit | E55 Type | |
| E60 | Number | E59 Primitive Value → E1 | |
| E62 | String | E59 Primitive Value → E1 | |
| E73 | Information Object | E89, E28, E71, E77, E1 | Superclass of E31 and E90. |
| E74 | Group | **E39 Actor** → E77 → E1 | |
| E77 | Persistent Item | E1 | |
| E89 | Propositional Object | E28 → E71 → E77 → E1 | |
| E90 | Symbolic Object | E73, E28, E71, E77, E1 | Domain of P190. |
