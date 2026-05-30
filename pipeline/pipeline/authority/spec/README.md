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

Both are CRM-SIG-issued artifacts. Hapi-specific additions on top of the two specs are declared in a separate manifest at `../hapi_extension.rdf`, in two structurally different shapes: (a) `rdfs:subClassOf` / `rdfs:subPropertyOf` narrowing declarations plus `owl:SymmetricProperty` typing on the two symmetric Hapi predicates (the standard CIDOC extension idiom — same as how CRMdig itself extends core CRM); and (b) free-standing `rdf:Property` / `rdfs:Class` declarations for project vocabulary that has no clean CRM/CRMdig parent (the tomb predicates, `hapi:in_dynastic_period`, `hapi:matcher_review_verdict`, `hapi:supersedes`, etc.) — CIDOC's open extension model permits this shape but those predicates are intentionally CIDOC-opaque (no `subPropertyOf` declaration means no CRM/CRMdig term to interpret through). Reader behaviour for Hapi-namespaced triples depends on what the reader has loaded and which reasoner it applies:

- **Reader has NOT loaded the manifest** — Hapi-namespaced triples are unrecognised URIs; the reader retains them but does not reason on them.
- **Reader has loaded the manifest + applies an RDFS reasoner** — interprets Hapi-extended terms through their declared CRM/CRMdig parents (e.g. `hapi:MatcherRun` is also typed as `crmdig:D10 Software Execution`; `hapi:derived_by_run` is also `crm:P15_was_influenced_by`; `hapi:same_entity_as` is also `crmdig:L54_is_same_as`). RDFS reasoning does NOT infer property symmetry, so the OWL declarations are effectively no-ops on this reader.
- **Reader has loaded the manifest + applies an OWL-aware reasoner** — additionally applies the manifest's `owl:SymmetricProperty` declarations (currently on `hapi:same_entity_as` and `hapi:shares_tomb_with`) and infers the inverse direction of each symmetric edge automatically.

**CIDOC-opacity and OWL-behavior are independent.** Predicates without a declared `rdfs:subPropertyOf` remain opaque to CRM/CRMdig vocabulary even with the manifest loaded — OWL typing may add non-CIDOC behavior (such as symmetry inference for `owl:SymmetricProperty`), but it does not add CIDOC interpretation. `hapi:shares_tomb_with` is OWL-symmetric but CIDOC-opaque; the tomb-context predicates (`tomb_owner`, `original_burial_in`, `cache_context_at`) are both CIDOC-opaque and OWL-untyped. See ADR-018 for the full conformance picture.

## Which file for what

| Concern | File |
|---|---|
| "What does P82 *mean*?" | core CRM HTML |
| "Does P82a exist? What's its `rdfs:range`?" | core CRM RDFS |
| "What does D3 Formal Derivation *mean*? Examples?" | CRMdig HTML |
| "What's L21's range? Is D10 IS-A D7?" | CRMdig RDFS |
| Project encoding conventions (with CIDOC RDF serialisation mappings), conceptual deviations (currently none), and Hapi extensions | `docs/adr/018-authority-as-claim-graph.md` |

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

## CRMsci import — carve-out

CRMdig 5.0's RDFS file declares `owl:imports rdf:resource="http://www.cidoc-crm.org/extensions/crmsci/3.2/"` and uses CRMsci classes in a small number of places — specifically D11 Digital Measurement Event (`subClassOf S21_Measurement`) and a handful of measurement-related L-properties.

**Hapi uses a CRMdig subset that does not touch CRMsci-dependent classes.** Our consumed classes (D1, D7, D10, D14) and properties (L10, L11, L23, L54) have IS-A chains and domain/range references that go directly to core CRM (E1, E11, E65, E73) without traversing any CRMsci class. L54_is_same_as has domain and range E1 CRM Entity — no CRMsci dependency. We therefore do not vendor CRMsci 3.2.

If a future Hapi feature requires CRMdig classes/properties that *do* depend on CRMsci (e.g. D11 for measurement events, or O24 for measurement provenance), the carve-out becomes invalid and CRMsci 3.2 must be vendored alongside the existing files. The `cidoc-crm-validator` subagent enforces this: any use of a CRMsci-dependent class/property when CRMsci is not vendored is a hard error.
