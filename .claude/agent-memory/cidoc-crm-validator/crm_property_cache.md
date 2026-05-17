# CIDOC CRM 7.1.3 — Property cache

Source: https://cidoc-crm.org/html/cidoc_crm_v7.1.3.html and RDFS at /rdfs/7.1.3/

| P# | Name | Domain | Range | Notes |
|---|---|---|---|---|
| P14 | carried out by | **E7 Activity** | **E39 Actor** | E13 IS-A E7, so P14 attaches to E13 by inheritance. Range is E39 (not E31). |
| P70 | documents | E31 Document | E1 CRM Entity | Inverse P70i "is documented in" attaches FROM any E1 TO E31. |
| P82  | at some time within | E2 Temporal Entity | E61 Time Primitive | (note: domain widened from E52 in earlier versions; in 7.1.3 the original P82 retains range E61) |
| P82a | begin of the begin | E52 Time-Span | rdfs:Literal (xsd:dateTime) | Subproperty of P82. Real in 7.1.3. |
| P82b | end of the end | E52 Time-Span | rdfs:Literal (xsd:dateTime) | Subproperty of P82. Real in 7.1.3. |
| P81  | ongoing throughout | E2 Temporal Entity | E52 Time-Span | |
| P81a | end of the begin | E52 Time-Span | rdfs:Literal (xsd:dateTime) | |
| P81b | begin of the end | E52 Time-Span | rdfs:Literal (xsd:dateTime) | |
| P90  | has value | E54 Dimension | E60 Number | |
| P91  | has unit | E54 Dimension | E58 Measurement Unit | |
| P140 | assigned attribute to | E13 Attribute Assignment | E1 CRM Entity | |
| P141 | assigned | E13 Attribute Assignment | **E1 CRM Entity** | Range is E1 — literals are NOT in range. |
| P177 | assigned property of type | E13 Attribute Assignment | E55 Type | |
| P190 | has symbolic content | **E90 Symbolic Object** | E62 String / xsd:string | E41 Appellation IS-A E90, so applies via inheritance. |
