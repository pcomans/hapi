# Product Requirements Document: Egyptian Artifacts Index

## Problem Statement

An estimated 2 million artifacts from ancient Egypt are scattered across approximately 850 public collections in 69 countries. There is no unified, searchable database that allows a user to discover where artifacts from a specific site, ruler, or period ended up worldwide. Existing resources are either museum-specific (the Met, the Louvre), region-limited (Europeana), or too sparse to be useful (the Global Egyptian Museum, with ~15,000 of 2 million objects catalogued).

The core problem can be summarized as: **artifacts that once belonged together — in a temple, a tomb, a palace — are now separated across the world, and there is no tool that virtually reunifies them.**

The closest prior effort was Cleo, an AI-powered Egyptology platform developed by the Dutch social enterprise Aincient, which aggregated ~45,000 objects from four museums (Met, Brooklyn Museum, Walters Art Museum, National Museum of Antiquities in Leiden). Cleo launched in 2018 and was terminated in summer 2025 after seven years of service. Cleo focused on cross-collection search and AI image matching, but did not emphasize origin-site-based virtual reunification. Its shutdown confirms both the demand for this type of tool and the difficulty of sustaining it. See “Existing Landscape” in Implementation Notes for a full analysis of what killed Cleo and the lessons for this project.

## Product Vision

A searchable, cross-museum index of Egyptian artifacts that lets users explore what was taken from a given site, who has it now, and what companion pieces exist in other collections. The product frames dispersed artifacts through the lens of their original context — where they came from — rather than where they ended up.

## Target Persona: The Engaged Amateur

Members of communities like the History of Egypt Podcast Discord (~200 active members). These are people who:

- Listen to Egyptology podcasts, read popular books on ancient Egypt, and visit museum Egyptian collections when traveling
- Are curious and knowledgeable but not academic — they know who Thutmose III is but don’t read hieratic
- Want to go deeper than a museum label but don’t need full scholarly apparatus
- May be visiting Egyptian sites or museums and want in-the-moment context

They are **not** professional Egyptologists, curators, or provenance researchers (though the underlying data platform should not preclude serving those users later).

## User Stories

### US-1: Discover by Place of Origin

*“I want to see all known artifacts from Karnak so I can understand what was taken and where it went.”*

The user enters a site name (Karnak, Deir el-Bahri, Amarna, Valley of the Kings) and sees a list of artifacts from that site across all indexed museums, with images, current museum location, and basic description.

### US-2: Discover by Ruler or Period

*“I want to see artifacts from the reign of Thutmose III across all museums.”*

The user searches or filters by ruler name, dynasty, or period. The system normalizes variant references — “Thutmose III,” “Menkheperre,” “18th Dynasty,” “New Kingdom” — so that all relevant results appear regardless of how the source museum catalogued them.

### US-3: Find Companion Pieces (The “Missing Pieces” Use Case)

*“I’m at a museum looking at an artifact. I want to see related pieces from the same site, tomb, or temple that are in other museums.”*

The user finds or navigates to a specific artifact and sees other objects from the same original context (same tomb, same temple, same excavation) that are now in different institutions. This is the long-term vision — virtual reunification. In v1, the system shows related candidates with tiered confidence and clear explanations of why items were matched. The UI never implies certainty the data doesn’t support.

### US-4: Explore a Museum’s Egyptian Collection with Better Filters

*“I’m visiting the Met next month. Show me their 18th Dynasty collection filtered by ruler.”*

The user selects a museum and browses its Egyptian holdings using Egyptology-native filters (dynasty, ruler, site of origin, object type) that the museum’s own website may not offer.

### US-5: Map View

*“I want to see on a map where artifacts from Amarna ended up worldwide.”*

The user views a geographic visualization showing which museums hold artifacts from a given site, with counts and the ability to drill into specific objects.

## MVP Scope

### Design Principle

The normalization layer — mapping heterogeneous museum data into a consistent, Egyptology-native schema — is the core technical challenge and the core product value. v1 must include multiple museums to ensure the normalization design is tested against real-world data diversity, not just one clean source.

### In Scope (v1)

- Ingest Egyptian collection data from three museums with different data shapes:
  - **Metropolitan Museum of Art** (REST API + CSV, CC0, English, structured Egyptology fields)
  - **Brooklyn Museum** (REST API, CC BY-NC-ND, English, different field conventions)
  - **Harvard Art Museums** (REST API, non-commercial, English, different field conventions)
- Store raw museum data in its native format per source
- Build a per-source mapper that normalizes into a common schema with first-class fields for: site of origin, ruler/reign, dynasty, period, object type, material, current museum, current location/gallery, image URL, source museum URL
- Build an authority list for Egyptian rulers and periods that maps variant names and date ranges
- Rights-aware rendering: each record carries a license field; the UI checks it to decide whether to embed the image, show a thumbnail, or link out to the museum page
- Web application (responsive/mobile-friendly) with:
  - Text search across all normalized fields
  - Filter by: site of origin, ruler, dynasty, object type, museum
  - List and grid views with artifact images (where licensing permits)
  - Artifact detail page with link back to source museum
  - Map view showing geographic distribution of results
  - “Related candidates” view: given an artifact, show other objects from the same origin site, with match explanation (e.g., “matched on excavation site: Deir el-Bahri”)

### Companion Pieces: Confidence Tiers

Cross-museum virtual reunification is the long-term vision, but it requires strong shared identifiers to avoid false matches that destroy trust. v1 implements tiered matching:

- **Tier A (strong):** Shared excavation ID, shared tomb/temple ID, or explicit “part of same set” — displayed as “Companion pieces”
- **Tier B (medium):** Same normalized origin site + overlapping date range + related object type — displayed as “Related artifacts”
- **Tier C (weak):** Same broad region only (e.g., “Thebes”) — displayed as “Explore more from this area,” never as “companion pieces”

### In Scope (v1.1 — fast follow)

- Add Louvre Egyptian Antiquities collection (JSON endpoint, French data)
- Add British Museum Egyptian collection (SPARQL/RDF)
- These introduce language normalization and ontology mapping challenges that are deliberately deferred from v1

### Out of Scope (for now)

- Visual similarity search (photograph an artifact, find matches)
- Scholarly/research tools (bibliography, provenance chains, CIDOC-CRM compliance)
- User accounts, saved searches, or curated collections
- Content beyond artifact metadata (articles, timelines, educational material)
- Non-Egyptian collections
- Mobile native app (responsive web is sufficient for v1)
- Monetization (the product is non-commercial for the foreseeable future; this avoids licensing conflicts with CC BY-NC sources)

## Technical Architecture

### Data Layer

```
┌──────────────────────────────────────────────────────────────┐
│                    Raw Storage (per museum)                   │
│  Met: JSON/CSV  │  Brooklyn: JSON  │  Harvard: JSON          │
└────────┬────────┴────────┬─────────┴────────┬────────────────┘
         │                 │                  │
    ┌────▼────┐     ┌──────▼─────┐    ┌───────▼──────┐
    │Met Mapper│     │Brooklyn    │    │Harvard       │
    │         │     │Mapper      │    │Mapper        │
    └────┬────┘     └─────┬──────┘    └──────┬───────┘
         │                │                  │
         ▼                ▼                  ▼
┌──────────────────────────────────────────────────────────────┐
│              Common Schema / Canonical Store                  │
│  (normalized fields, authority-linked, license per record)   │
└───────────────────────────┬──────────────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │ Enrichment Layer │
                   │ (ruler authority │
                   │  list, Wikidata  │
                   │  IDs, site       │
                   │  geocoding)      │
                   └────────┬────────┘
                            │
                     ┌──────▼──────┐
                     │   Search    │
                     │   Index     │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │   Web App   │
                     └─────────────┘
```

### Key Architectural Decisions

1. **Raw data is preserved verbatim.** Each museum’s data is stored in its original format. Translators can be re-run as the common schema evolves without re-fetching.
1. **One mapper per source.** Each museum gets its own ingestion script and its own translator. No attempt to build a universal parser.
1. **The common schema is Egyptology-native.** Period, dynasty, and ruler are first-class fields, not free text. An authority list maps variant names (“Thutmose III” / “Tuthmosis III” / “Menkheperre”) and date ranges to canonical identifiers.
1. **Origin site is a first-class entity.** Sites (Karnak, Deir el-Bahri, Amarna) have their own records with coordinates, enabling the map view and the companion-pieces query.

### Data Sources

**v1 Sources (all English, all REST APIs — chosen to stress-test normalization without introducing language/ontology complexity)**

|Museum                    |Size (Egyptian)               |Access Method          |Format    |License                       |
|--------------------------|------------------------------|-----------------------|----------|------------------------------|
|Metropolitan Museum of Art|~26,000 Egyptian objects      |REST API + CSV dump    |JSON / CSV|CC0 (unrestricted)            |
|Brooklyn Museum           |~3,000+ Egyptian objects      |REST API               |JSON      |CC BY-NC-ND (images)          |
|Harvard Art Museums       |Egyptian collection (size TBD)|REST API (key required)|JSON      |Non-commercial educational use|

**v1.1 Sources (introduce language and ontology challenges)**

|Museum        |Size (Egyptian)          |Access Method                           |Format    |License                                                                          |
|--------------|-------------------------|----------------------------------------|----------|---------------------------------------------------------------------------------|
|Louvre        |Egyptian Antiquities dept|Append .json to URL + CSV export        |JSON / CSV|Non-commercial educational/scientific use with credit; commercial requires RMN-GP|
|British Museum|~100,000 Egyptian objects|SPARQL endpoint + CSV export (10k limit)|RDF / CSV |CC BY-NC-SA 4.0 (images); non-commercial research (data)                         |

## Success Metrics

- **Coverage:** Number of artifacts indexed, number of unique origin sites represented
- **Engagement:** Beta users from the podcast Discord who return within 7 days
- **Query satisfaction:** Can a user successfully answer “where are the artifacts from [site X]?” — measured qualitatively through beta feedback
- **Companion piece discovery:** Number of artifacts that have at least one companion piece in a different museum in the index

## Resolved Design Decisions

**Authority list for rulers and periods:** Broad coverage from day one is required — users will search for Ramesses II as often as Thutmose III. The authority list will be sourced from Wikidata (SPARQL query for all pharaohs, CC0 licensed), enriched with the Met’s own chronology and validated against the scholarly standard (Hornung, Krauss & Warburton 2006). Each ruler entry must map all name variants: personal name, throne name (prenomen), Greek forms, and modern spelling variants. Date ranges should be stored as approximate and note which chronology is followed. Egyptian chronology is contested for early dynasties — acknowledge the uncertainty rather than pretending to resolve it.

**Vague or missing origin-site data:** Handle via a hierarchical site model (Egypt > Thebes > Western Thebes > Valley of the Kings > KV34). Artifacts are stored at the most specific level available, and searches at a higher level return everything below. The site taxonomy will use Pleiades gazetteer IDs as canonical identifiers (CC-BY, with coordinates and alternate names), supplemented by a custom parent-child hierarchy layer for key Egyptian sites. Wikidata “located in” (P131) properties can supplement Pleiades for containment relationships. For the MVP, approximately 50–100 key sites need to be properly structured — the major necropolises, temple complexes, and cities.

**Licensing:** The Met (CC0) has zero restrictions — metadata and public domain images can be used however we want. The British Museum images are CC BY-NC-SA 4.0 (non-commercial with attribution). The Louvre permits non-commercial reuse for educational/scientific purposes with credit; commercial/editorial reuse requires contacting RMN-Grand Palais. The Museo Egizio is shifting toward CC0/CC BY. Egyptian museums in Cairo/Giza have no open data policy. The data model must track license per source museum so the UI knows what it can display (full image, thumbnail only, or link-back only).

**Beta launch strategy:** Open from launch, seeded through the History of Egypt Podcast Discord. No invite gate — it adds friction for no benefit. The Discord is the primary feedback channel.

**Asymmetry between rich and sparse records:** v1 includes three museums with different data richness to test this from day one. All fields in the common schema are nullable — sparse records are displayed with whatever is available. The UI omits missing fields gracefully rather than showing “Unknown” labels. An artifact with just a title, rough provenance, and museum name is still valuable in a cross-museum index. Filters must reflect what the data actually contains; show counts to avoid “empty filter” traps where a facet returns zero results.

## Milestones

This is a solo developer project using Claude Code. Milestones are sequenced so each produces value and reduces risk. No fixed week estimates — ship each milestone when it’s ready, then assess.

**Milestone 1: Ingestion + canonical schema**
Met + Brooklyn + Harvard ingestion, raw storage, common schema definition, ruler/period authority list (seeded from Wikidata, validated against Met chronology). Done when: three sources ingested, mapped to common schema, with coverage stats (% of records with mapped ruler, mapped site, etc.).

**Milestone 2: Origin-site normalization**
Curated hierarchy for top 50–100 Egyptian sites using Pleiades IDs. Map origin fields from all three sources to site hierarchy. Done when: origin-site queries return cross-museum results for at least 10 major sites (Karnak, Deir el-Bahri, Amarna, Valley of the Kings, Giza, Saqqara, etc.).

**Milestone 3: Search + filter UX with rights-aware rendering**
Search index, faceted filters, artifact detail page, match explanation (“origin derived from Met excavation field”), license-aware image display. Done when: a user can search by ruler or site and get correct cross-museum results with appropriate image handling per source.

**Milestone 4: Beta launch + instrumentation**
Deploy, announce in podcast Discord, collect feedback. Basic analytics to measure engagement. Done when: live and receiving user feedback.

**Milestone 5 (optional for v1): Map view + related candidates**
Geographic visualization, tiered companion piece matching. These are valuable but not required for a useful beta.

## Implementation Notes

The following findings were gathered during product research and should inform technical implementation.

### Museum Data Access

The Met provides a REST API (no auth required, 80 req/sec limit) and a full CSV dump on GitHub. Egyptian Art is departmentId 10, containing ~26,000–30,000 objects. The API returns structured geography fields: `geographyType`, `country`, `region`, `subregion`, `locale`, `locus`, `excavation`, and `river` — plus first-class `period`, `dynasty`, and `reign` fields. This is the richest structured source and the right starting point.

The Brooklyn Museum has a REST API returning structured JSON. It was the first art museum to adopt a Creative Commons license (2004). Its Egyptian collection is renowned (3,000+ objects) and includes the Wilbour Library of Egyptology. Images are CC BY-NC-ND. The API’s field structure differs from the Met’s, making it a good normalization test case.

The Harvard Art Museums provide a documented REST API (API key required, free registration). Images are available for non-commercial educational/scholarly use. Collection includes Egyptian material; exact size and field structure need to be confirmed during ingestion.

The Louvre exposes JSON by appending `.json` to any collection URL (e.g., `collections.louvre.fr/ark:/53355/cl010277627.json`). CSV export is available from search results. Data is in French. The JSON schema includes hierarchical thesaurus-based indexes for period, place, material, and denomination.

The British Museum offers a SPARQL endpoint using CIDOC-CRM in RDF, returning XML or JSON. Search results can be downloaded as spreadsheets (up to 10,000 records per export). Coverage is ~100,000 Egyptian objects.

Berlin (Staatliche Museen) has 270,000+ objects on their Collections Online platform, also accessible via museum-digital.de.

The Museo Egizio (Turin) has ~3,000 images online with CC licensing, plus the dedicated Turin Papyrus Online Platform for papyri.

The Grand Egyptian Museum (opened November 2025) and the Egyptian Museum in Cairo have web-based collection browsers but no API, no data export, and no published open data policy.

### Authority Data Sources

**Rulers:** Wikidata contains structured records for pharaohs queryable via SPARQL (`instance of` pharaoh Q37011). Each item includes alternate names, throne names, dynasty, dates, predecessor/successor, and Wikidata IDs that can link to other datasets. The Met’s own published chronology (based on the Palermo Stone, Abydos Kings List, and Turin Canon) should be used to validate and supplement Wikidata. Egyptian kings had up to five royal names (Horus name, Nebty name, Golden Horus name, prenomen/throne name, nomen/personal name), plus Greek and modern spelling variants — all must map to a single canonical identifier.

**Sites:** Pleiades (pleiades.stoa.org) is a community-built gazetteer of ancient places, CC-BY licensed, with coordinates, alternate names, and data dumps in GeoJSON, KML, and RDF/Turtle. Coverage of Egypt exists but is thinner than Greek/Roman material. Pleiades does not natively provide a parent-child containment hierarchy (e.g., Karnak within Thebes), so this must be built as a custom layer on top. Wikidata’s `located in` (P131) property can help construct containment chains.

**Periods:** The Met’s API uses structured period fields (e.g., “New Kingdom”), dynasty fields (e.g., “Dynasty 18”), and reign fields (e.g., “Thutmose III”). Other museums will use varying conventions. The CIPEG-approved Multilingual Egyptological Thesaurus (MET) is the standard for electronic databases and should inform the common vocabulary.

### Existing Landscape

**Cleo** (cleo.aincient.org): The most directly relevant prior effort. Developed by the Dutch social enterprise Aincient, launched 2018, terminated summer 2025 after seven years. Aggregated ~45,000 objects from four museums (Met, Brooklyn Museum, Walters Art Museum, National Museum of Antiquities in Leiden). Offered text search, AI image search, and location-based search in English and Dutch. Was open source under Apache 2.0. Had plans to expand to 100,000+ objects from nine additional museums and integrate with Trismegistos and UCLA Encyclopedia of Egyptology.

**What killed Cleo:** The sustainability problem was structural. The founder (Heleen Wilbrink, an Egyptologist) quit her banking career to run this full-time as a solo non-technical founder. Development was outsourced to a web agency (Goldmund, Wyldebeast & Wunderliebe), meaning every feature cost real money. Initial funding came from time-limited grants (SIDN Fund, Google Cloud Startup Program). The revenue model (50 free queries/month, then €4.95/100 queries) could not sustain operations given the tiny, price-sensitive target audience. Despite nine additional museums expressing intent to share data, Cleo was still at four museums and 45,000 objects seven years later. A proposed University of Memphis partnership for long-term hosting did not appear to result in sustained funding.

**Lessons for this project:**

- Do not depend on grants or revenue to survive. Build as a low-cost community resource that can run on minimal hosting spend indefinitely.
- The developer being the builder (not outsourcing) changes the economics fundamentally — ongoing cost is hosting, not agency invoices.
- Keep infrastructure costs low enough that the project doesn’t need income. The moment you need revenue to cover cloud bills, you’re on Cleo’s path.
- Ambitious expansion plans (more museums, more languages, AI features) mean nothing if the core product doesn’t sustain itself. Ship small, keep it running.
- Cleo’s code was open source under Apache 2.0 and was shared on GitHub. It may contain useful prior art for museum data ingestion and normalization.

Other efforts:

- **Global Egyptian Museum** (globalegyptianmuseum.org): CIPEG project aiming to catalogue 2M objects from 850 collections. Currently only ~15,000 objects. Not queryable by ruler or origin site in a meaningful way.
- **Google Arts & Culture**: 100,000+ artworks from 2,000+ museum partners. Browsing-oriented, not structured for Egyptology-specific queries.
- **Europeana**: 60M+ digital objects from 4,000+ European institutions. Geographically limited to Europe. Includes books, audio, video — not artifact-focused.
- **Wikidata WikiProject Cultural Heritage**: Aims to interlink GLAM collections worldwide. Powerful but patchy, volunteer-driven, and requires SPARQL expertise to query.
- **Egyptological Museum Search**: Single search point for finding objects by inventory number across major collections. Useful but not filterable by ruler, period, or site.
