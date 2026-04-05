# Architecture

## System overview

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
│              Canonical Store (Postgres)                       │
│  (normalized fields, authority-linked, license per record)   │
└───────────────────────────┬──────────────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │ Enrichment Layer │
                   │ (ruler authority │
                   │  list, site      │
                   │  hierarchy,      │
                   │  Wikidata IDs)   │
                   └────────┬────────┘
                            │
                     ┌──────▼──────┐
                     │  Typesense  │
                     │  (search)   │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │  Next.js    │
                     │  (web app)  │
                     └─────────────┘
```

## Key decisions and rationale

### Two languages: Python pipeline + TypeScript frontend

The pipeline is data-heavy work: parsing heterogeneous museum JSON/CSV, fuzzy string matching for authority lists, SPARQL queries against Wikidata, hierarchical site normalization. Python's ecosystem (rapidfuzz, SPARQLWrapper, pandas-like transforms) is materially better for this. The frontend is an interactive web app with maps, faceted search, and server-rendered pages — Next.js/React is the natural choice. The two systems share no code; they communicate through Postgres and Typesense.

### Dagster for pipeline orchestration

The pipeline has a natural asset graph (raw data per museum -> normalized records -> enriched records -> search index). Dagster's software-defined asset model maps directly to this. It provides: dependency tracking (re-run just one museum's normalization), observability UI (see what's stale, what failed), and typed I/O contracts between stages. The main alternative was plain scripts — simpler to start but harder for an AI agent to extend consistently. Dagster's structured asset definitions serve as a spec the agent can follow.

### Typesense over Elasticsearch

At the expected scale (~30k-100k artifacts), Typesense provides typo-tolerant full-text search with faceted filtering, geo-search for the map view, and a simple operational model (single binary, no JVM). Elasticsearch is more powerful but operationally heavier and unjustified at this scale. If we outgrow Typesense, the search abstraction is thin enough to swap.

### Postgres as the canonical store

The data is relational: artifacts belong to museums, reference rulers and sites from authority tables, and carry per-record license metadata. ~100k records with structured queries is Postgres's sweet spot. The schema is defined in `shared/schema.json` and implemented via Drizzle (web) and Pydantic/SQLAlchemy (pipeline).

### Raw data preserved verbatim

Each museum's API response is stored in its native format in a per-museum raw table. Mappers can be re-run as the canonical schema evolves without re-fetching from APIs. This also provides an audit trail for debugging normalization issues.

### One mapper per museum, not a universal parser

Museum data formats differ enough that a generic parser would be a leaky abstraction. Each museum gets its own mapper implementing a shared protocol. Adding a museum means writing a new mapper, not modifying a shared one. This is more total code but dramatically safer — changing the Brooklyn mapper cannot break Met normalization.

### Origin site as a first-class entity

Sites (Karnak, Deir el-Bahri, Amarna) have their own table with coordinates, Pleiades IDs, alternate names, and a parent-child hierarchy (Egypt > Thebes > Western Thebes > Valley of the Kings). This enables: site-based search, hierarchical queries ("everything from Thebes" includes sub-sites), map view, and companion piece matching.

### Confidence tiers for companion pieces

Cross-museum matching uses explicit confidence tiers to avoid false matches that destroy trust:
- **Tier A (strong):** Shared excavation ID, tomb ID, or explicit set membership — labeled "Companion pieces"
- **Tier B (medium):** Same normalized origin site + overlapping date range + related type — labeled "Related artifacts"
- **Tier C (weak):** Same broad region — labeled "Explore more from this area"

The UI never implies certainty the data doesn't support.

## What is NOT in this architecture

- No user accounts, authentication, or saved state
- No image storage — images are loaded from museum CDNs or linked out, depending on license
- No AI/ML features (visual similarity, auto-classification)
- No real-time sync — pipeline runs periodically (manually or scheduled), not continuously
