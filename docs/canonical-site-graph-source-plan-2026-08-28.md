# Canonical site graph: source research and acquisition plan

**Date:** 2026-08-28  
**Decision:** Hapi should own the canonical identifiers and graph. iDAI.gazetteer should remain the scholarly backbone, but no external gazetteer is complete enough to be the graph by itself. Open external sources should contribute provenance-bearing claims, aliases, hierarchy, coordinates, and cross-identifiers; museum strings should become reviewed local terms rather than silently creating identities.

## Why the existing decision is not enough

ADR-012 selected iDAI as the sole site authority after a 29/30 spot check. The real-corpus linkability run changes the evidence:

- The committed file has 1,000 filtered iDAI rows, but 566 refer to parents absent from that file. This is not a closed graph.
- `Egypt` is unmatched on 29,964 artifacts across the three museums because the root was filtered out.
- High-volume museum terms are finer or differently organized than the extract: `Memphite Region` (4,634 artifacts), `Lisht North` (3,006), `Palace of Amenhotep III` (1,518), `Southern Asasif` (1,359), and `Temple of Hatshepsut` (570).
- Broad nodes create misleading connectivity: Thebes alone touches 11,656 of the 15,595 artifacts that currently have a cross-museum route.
- Findspot and production place must remain separate artifact relations under ADR-015. A shared place identity must not erase the museum field's role.

The earlier source research was useful, but its question was “which single authority should we use?” The corpus shows that the correct question is “which claims from which sources should compose a canonical Hapi node?”

## Source roles

| Source | What it can supply | Terms / access | Decision |
|---|---|---|---|
| **iDAI.gazetteer** | Egyptological site backbone, multilingual labels, types, coordinates, parents, Pleiades/GeoNames/GND/Arachne cross-references | Current Hapi acquisition records CC BY 4.0 and REST JSON without authentication | **Primary seed.** Acquire the full Egypt descendant set plus transitive parents; do not repeat the site-type filter that broke closure. |
| **Pleiades** | Scholarly ancient-place identities, names, locations, temporal attestations, connections, stable URIs | CC BY 3.0; current and quarterly JSON/RDF/KML dumps; online records remain canonical ([downloads](https://pleiades.stoa.org/downloads)) | **Primary crosswalk/enrichment.** Import Egypt-relevant records reached from iDAI cross-references and reviewed gap candidates, with source attribution. Do not assume identical granularity. |
| **Getty TGN** | Modern/historical geographic hierarchy, multilingual names, place types, coordinates | ODC-By 1.0; individual LOD records and monthly N-Triples releases ([Getty LOD](https://www.getty.edu/research/tools/vocabularies/lod/index.html)) | **Administrative and alias enrichment.** Useful for country/region/settlement closure, not tomb or monument truth. |
| **GeoNames** | Modern geography, alternate names, hierarchy, coordinates | CC BY; downloadable dumps and services; commercial reuse allowed; supplied “as is” ([export terms](https://www.geonames.org/export/)) | **Modern bridge only.** Use cross-identifiers and parent geography; never let crowd-edited GeoNames overwrite archaeological identity. |
| **Wikidata** | Broad aliases, coordinates and outbound IDs; often has individual monuments and tombs | CC0; entity APIs, SPARQL, and dumps ([data access](https://www.wikidata.org/wiki/Wikidata%3AData_access/en)) | **Candidate generator and silver crosswalk, not truth.** Every accepted identity or hierarchy edge needs corroboration or explicit review. |
| **Porter–Moss registers already in Hapi** | Tomb, temple, cemetery, monument, and locality structure at museum-relevant granularity with page citations | Copyrighted scholarship may be cited; source text is not redistributable wholesale | **Specialist child nodes.** Attach existing Theban and Memphite register entities beneath site nodes. Extend volumes only through the established citation-preserving extraction process and rights review. |
| **Trismegistos Places** | Ancient names, languages, dates, coordinates, attestations, TM IDs; especially strong for text-bearing places | Custom CSV/JSON dump; CC BY-SA ([data dump and terms](https://www.trismegistos.org/dataservices/tabledump/)) | **Optional claim source after license design review.** It is text/papyrology-oriented and can collapse archaeological subdivisions; do not use it as the node backbone. |
| **World Historical Gazetteer** | Reconciliation across WHG, GeoNames, TGN, Wikidata, OSM, Pleiades; typed candidates and aliases | Tokened reconciliation API; responses retain per-source terms, while the WHG aggregate is CC BY-NC ([API](https://docs.whgazetteer.org/content/technical/apis.html), [licences](https://whgazetteer.org/licenses/)) | **Research/reconciliation tool only.** Query permissive upstream namespaces directly for committed data. Do not ingest the aggregate into the commercial-neutral core. |
| **PAThs** | Coptic/Late Antique places and some TM bridges | Non-commercial/share-alike terms; period focus does not match most corpus needs | **Exclude from core.** Revisit only for a separately licensed Coptic research layer. |
| **TopBib / Artefacts of Excavation** | Egyptological topographic bibliography and some structured TM/TLA links | No reusable bulk license found for TopBib; related Artefacts material is CC BY-NC-SA and forbids substantial reproduction without permission ([permissions](https://egyptartefacts.griffith.ox.ac.uk/copyright-and-permissions/)) | **Reference or partnership target, not ingest.** Ask the Griffith Institute for an export and explicit rights if its crosswalks become necessary. |
| **EAMENA and Egypt's official monument portal** | Heritage-place records, controlled fields, geometries, official monument descriptions | Useful public interfaces exist, but this review did not establish reusable bulk terms/API coverage | **Hard license/access gate.** Do not scrape or import until written terms and export access are established. |

There is no evidence that any one of these sources covers the actual museum vocabulary well enough to replace Hapi curation. In particular, availability of an API or a name hit is not evidence of correct identity.

## The canonical model

Create stable Hapi IDs independent of every provider. Each node should carry:

- typed class: country, historical region, modern region, settlement, archaeological site, cemetery, monument complex, temple, palace, tomb, or other controlled type;
- preferred display label plus language-, script-, period-, and source-qualified aliases;
- `contained_in` and other spatial relationships as source-attributed claims, allowing competing or time-scoped assertions rather than overwriting them;
- coordinates or geometry with source, precision/uncertainty, and date accessed;
- external identifiers as reviewed equivalence or close-match claims, not automatic merges;
- source citations and license/attribution metadata on every imported claim;
- museum-local expressions with field path, role, normalization, review status, and supporting artifact count.

Artifacts then have typed edges to nodes: `found_at`, `made_at`, `excavated_by/from_context`, and `mentions`. Tombs and temples can be child place nodes, but excavation campaigns/loci may need a separate event/context entity rather than being forced into the place hierarchy.

## Acquisition and pressure-test sequence

### 1. Repair the backbone

Acquire all iDAI Egypt descendants and the transitive parent closure. Preserve the raw response, retrieval date, upstream ID, and license notice. Validate that every non-root `contained_in` target exists. This should immediately fix the `Egypt` failure and make the hierarchy structurally testable, but it must not be reported as an accuracy improvement until the corpus is rerun.

### 2. Build a weighted gap queue from the corpus

Use `top_gaps.json`, not an encyclopedia wish list. Start with enough distinct terms to cover at least 80% of currently unmatched site-bearing artifacts, while stratifying across Met, Brooklyn, and Harvard so Met volume does not erase the smaller museums. For each term, classify it as:

1. alias of an existing node;
2. child/sibling node missing from iDAI;
3. compound path requiring multiple nodes;
4. non-place contextual term such as “Cemetery”;
5. ambiguous or insufficient evidence; or
6. wrong extraction/field-role interpretation.

Do not create a node merely because a museum emitted a string.

### 3. Enrich candidates in a controlled order

For each gap, follow iDAI cross-references first, then Pleiades, TGN/GeoNames for geographic context, Wikidata as discovery, and the relevant Porter–Moss register for monument-level evidence. Record disagreements. Use Trismegistos only after deciding how CC BY-SA claims will be isolated and redistributed.

### 4. Create a small reviewed graph slice

The MVP is not “all Egyptian sites.” It is a versioned, reviewed graph slice containing:

- complete country/region/site ancestry for every selected node;
- the 25–50 highest-impact distinct gap terms across all museums;
- current iDAI matches involved in those paths;
- Porter–Moss monument children relevant to those records;
- explicit museum-local aliases and artifact edge roles.

Two reviewers should adjudicate identity, parentage, entity type, and alias scope independently for the risky or ambiguous cases. Disagreement is retained as unresolved; it is not forced into a merge.

### 5. Rerun exactly the same benchmark

Freeze the corpus and extractor. Change only the authority graph adapter, then compare against the archived baseline:

- link rate by museum, entity type, and source field;
- unique artifacts and nodes gaining links;
- cross-museum nodes and concentration (especially whether Thebes' 74.74% dominance falls);
- ambiguous and unmatched counts;
- false-link review on both newly linked and unchanged links;
- hierarchy integrity and provenance completeness.

The decision gate is a materially larger, less concentrated cross-museum graph with reviewed error rates acceptable for shadow mode. Raw link-rate growth alone is not success: adding `Egypt` will inflate coverage without improving useful discovery.

## Immediate build recommendation

Implement **site graph slice v0**, not a general multi-source ingestion platform:

1. full iDAI Egypt ancestor closure;
2. Hapi node/claim schema with source-qualified aliases and relationships;
3. a weighted 25–50-term three-museum adjudication queue;
4. Pleiades/TGN/GeoNames/Wikidata crosswalk adapters limited to that queue;
5. attachment of existing Porter–Moss nodes;
6. unchanged full-corpus rerun plus blinded human review.

This answers the practical question within weeks: whether better canonical place structure creates useful cross-museum discovery. It also produces durable graph data without pretending that an external gazetteer, an LLM, or a name match is ground truth.

## Research limits

- No human gold standard exists. Web and source alignment can produce candidates and provisional silver evidence, not truth.
- This research did not ingest candidate bulk datasets or claim coverage numbers for them. Coverage must be measured against the frozen corpus after acquisition.
- EAMENA, the Egyptian Ministry portal, and TopBib remain blocked on explicit reusable data terms or export access; absence of a discovered license is not permission.
- Trismegistos and WHG introduce share-alike/non-commercial constraints that require an architectural or legal decision before their aggregate data enters Hapi.

