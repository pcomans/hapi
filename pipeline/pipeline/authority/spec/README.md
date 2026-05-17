# CIDOC CRM 7.1.3 — vendored spec

`cidoc_crm_v7.1.3.rdf` is the CIDOC Conceptual Reference Model v7.1.3 RDFS implementation, vendored in-repo to serve as the single source of truth for CRM syntactic validation (class existence, property existence, domain/range, IS-A chains).

- **Source:** `https://cidoc-crm.org/rdfs/7.1.3/CIDOC_CRM_v7.1.3.rdf`, retrieved 2026-05-17.
- **License:** CC-BY 4.0 (https://creativecommons.org/licenses/by/4.0/legalcode). Attribution lives in the file's `<owl:Ontology>` header.
- **Authoritative release (model definition, not this file):** `https://cidoc-crm.org/Version/version-7.1.3`.

Per the file's own preamble: *"this is NOT a definition of the CIDOC CRM, but a CIDOC CRM compatible implementation of an RDF Schema derived from the authoritative release ... by an automated algorithm."*

## Which file for what

| Concern | File |
|---|---|
| Syntactic validation (does P82a exist? what's its `rdfs:domain`?) | This vendored RDF |
| Semantic intent (what does P82a *mean*? what's its conceptual range?) | The release URL above |
| Encoding-rule awareness (e.g. rule 3: E60/E61/E62/E94/E95 collapsed to `rdfs:Literal`) | This file's preamble |

## Pin discipline

The CRM version pin is set by ADR-018. When the pin moves to a new release, replace this file in the same commit that updates the ADR's version pin — do not leave the vendored spec and the ADR pin out of sync.
