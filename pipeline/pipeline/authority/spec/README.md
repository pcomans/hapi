# CIDOC CRM 7.1.3 — vendored spec

`cidoc_crm_v7.1.3.html` is the CIDOC Conceptual Reference Model v7.1.3 class-and-property declarations page, vendored in-repo as the single source of truth for CRM validation in this project.

- **Source:** `https://cidoc-crm.org/html/cidoc_crm_v7.1.3.html`, retrieved 2026-05-17.
- **License:** CC-BY 4.0 (https://creativecommons.org/licenses/by/4.0/legalcode). Attribution lives in the file header.
- **Authoritative release page:** `https://cidoc-crm.org/Version/version-7.1.3`.

## Caveats

The file references external CSS, JS (jquery, select2, cytoscape, fontawesome), and decorative diagrams at `./version_images/...`. These affect *browser rendering* only; the class and property declarations — domains, ranges, scope notes, examples — are all in the HTML markup itself. Agents using `grep`, `Read`, or other text tools see the full content.

**Do not WebFetch this file.** WebFetch's summarisation silently drops content — subproperties P82a, P82b, P81a, P81b were dropped from summaries in earlier validation runs. Read it locally or grep it directly.

CIDOC-SIG also publishes an RDFS implementation derived from this release by an automated algorithm. We do not vendor it: its own preamble disclaims authority ("NOT a definition of the CIDOC CRM"), and encoding rule 3 collapses primitive-value classes (E60/E61/E62/E94/E95) to `rdfs:Literal`, which is a misleading lookup answer when the model means the conceptual class. The HTML preserves the conceptual ranges and scope notes that make the model honest.

## Pin discipline

The CRM version pin is set by ADR-018. To move to a new release: in the same commit, (a) update the ADR's version pin, (b) replace this file with the new-version counterpart, (c) update the source URL and retrieval date above. Do not leave the vendored spec and the ADR pin out of sync.
