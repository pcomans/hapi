# CIDOC CRM 7.1.3 + CRMdig 5.0 — vendored specs

Four vendored files, two specifications, two encodings each. All are CRM-SIG-issued and form the in-repo single source of truth for CIDOC validation.

| File | Specification | Encoding | Use for |
|---|---|---|---|
| `cidoc_crm_v7.1.3.html` (1.5 MB) | Core CRM 7.1.3 | Human-readable HTML | Semantic intent — scope notes, conceptual ranges, examples, idiom guidance. The release's class-and-property declarations page. |
| `cidoc_crm_v7.1.3.rdf` (434 KB) | Core CRM 7.1.3 | RDFS implementation | Syntactic check — `rdfs:domain`, `rdfs:range`, IS-A relations as actually emitted. Includes the RDFS-only refinements (P81a/P81b/P82a/P82b) that the conceptual document doesn't enumerate. |
| `crmdig_v5.0.html` (141 KB) | CRMdig 5.0 extension | Human-readable HTML | Digital-provenance class and property declarations — D1 Digital Object, D3 Formal Derivation, D7 Digital Machine Event, D10 Software Execution, D14 Software, and L-properties. |
| `crmdig_v5.0.rdf` (33 KB) | CRMdig 5.0 extension | RDFS implementation | Machine-readable domain/range for the CRMdig classes/properties, plus the IS-A chains back to core CRM. |

## Conformance target

ADR-018 pins both specifications:

- **Conceptual CRM 7.1.3** + its **official RDFS encoding** (the two `cidoc_crm_v7.1.3.*` files)
- **CRMdig 5.0** + its **official RDFS encoding** (the two `crmdig_v5.0.*` files)

Both are CRM-SIG-issued artifacts. The graph emits data that is valid under both; Hapi-namespaced additions on top of that are silently ignored by strict CIDOC/CRMdig readers.

## Which file for what

| Concern | File |
|---|---|
| "What does P82 *mean*?" | core CRM HTML |
| "Does P82a exist? What's its `rdfs:range`?" | core CRM RDFS |
| "What does D3 Formal Derivation *mean*? Examples?" | CRMdig HTML |
| "What's L21's range? Is D10 IS-A D7?" | CRMdig RDFS |
| Project-declared deviations and Hapi extensions | `docs/adr/018-authority-as-claim-graph.md` |

## Provenance

- **Source URLs** (all retrieved 2026-05-17):
  - https://cidoc-crm.org/html/cidoc_crm_v7.1.3.html
  - https://cidoc-crm.org/rdfs/7.1.3/CIDOC_CRM_v7.1.3.rdf
  - https://cidoc-crm.org/extensions/crmdig/html/CRMdig_v5.0.html
  - http://www.cidoc-crm.org/extensions/crmdig/rdfs/5.0/CRMdig_v5.0.rdf
- **License:** CC-BY 4.0 across all four files. Attribution lives in each file's header.
- **Authoritative release pages:**
  - Core CRM: https://cidoc-crm.org/Version/version-7.1.3
  - CRMdig: https://cidoc-crm.org/crmdig/ModelVersion/crmdig-v5.0

The RDFS files' preambles disclaim authority on definition (the HTML release is the canonical model); they are CRM-SIG-issued machine-readable implementations derived from those releases.

## Caveats

The HTML files reference external CSS, JS, and decorative diagrams. Browser rendering uses them; agents reading the files with `Read` or `grep` see the full class/property content and ignore the rendering assets. **Do not WebFetch these files** — WebFetch's summariser silently drops content (it ate P82a/P82b in earlier validation runs). Read or `grep` locally.

## Pin discipline

Version pins set by ADR-018. To move to a new release: in the same commit, (a) update the ADR's version pins for whichever specifications change, (b) replace the corresponding vendored files with new-version counterparts, (c) update the source URLs and retrieval date above. Never leave a vendored spec out of sync with the ADR pin.
