# MVP Task List

Tasks to reach MVP (PRD Milestones 1–4). Each task is independent enough for a single agent session. Tasks are ordered by dependency — later tasks depend on earlier ones.

## Milestone 1: Ingestion + Mappers

Ingest real museum data first, then build mappers against it. Authority data comes later — it should be informed by what the museums actually say, not built in a vacuum.

### 1.1 Alembic migration for initial schema

Run `uv run alembic revision --autogenerate -m "initial schema"` and `uv run alembic upgrade head` to create the actual database tables. Verify all tables exist in the `catalog` schema. This must happen before any ingest or mapper work.

### 1.2 Met ingest asset

Create `pipeline/assets/ingest/met.py` — Dagster asset that fetches all Egyptian Art object IDs (`departmentIds=10`) then fetches each object record, storing raw JSON verbatim in `raw_met` table. Handle the Met's pattern: one call returns ~26k IDs, then individual fetches per object. Respect 80 req/sec rate limit. Must be idempotent (re-run overwrites).

### 1.3 Met fixtures and mapper

Save 3–5 real Met API responses to `tests/fixtures/met/`. Choose: one richly catalogued object (full geography, reign, dates), one sparse record (minimal fields), one with ambiguous provenance ("Said to be from"), one with a co-regency or unusual reign field, one with no image.

Create `pipeline/assets/normalize/met.py` implementing `MapperProtocol`. Map Met fields to `CanonicalArtifact`: `objectID` → `id`, `title`, `objectName` → `object_type`, structured geography fields → `origin_site_raw` (preserve `geographyType` for provenance confidence), `period`, `dynasty`, `reign` → `ruler_display_name`, `objectBeginDate`/`objectEndDate` → `date_start`/`date_end`, `primaryImage` → `image_url`, etc. Parse date strings like "ca. 1479-1425 B.C." into integer ranges. Handle `reign` field containing period info instead of ruler names.

Write `tests/test_mappers/test_met.py` asserting specific mapped field values for each fixture.

### 1.4 Brooklyn ingest asset

Create `pipeline/assets/ingest/brooklyn.py` — Dagster asset that fetches Brooklyn Museum Egyptian collection via their API, storing raw JSON in `raw_brooklyn` table. Requires API key from environment. Determine pagination and rate limit behavior during implementation.

### 1.5 Brooklyn fixtures and mapper

Save 3–5 real Brooklyn API responses to `tests/fixtures/brooklyn/`. Create `pipeline/assets/normalize/brooklyn.py` implementing `MapperProtocol`. Map Brooklyn's field structure to `CanonicalArtifact`. Field names differ from the Met — this is the first real normalization stress test. Document any fields that don't map cleanly in the mapper's docstring. Write `tests/test_mappers/test_brooklyn.py` with specific value assertions.

### 1.6 Harvard ingest asset

Create `pipeline/assets/ingest/harvard.py` — Dagster asset that fetches Harvard Art Museums Egyptian collection, storing raw JSON in `raw_harvard` table. Requires API key. Determine collection size and filter strategy during implementation (classification filter may need tuning to exclude Egyptianizing non-Egyptian pieces).

### 1.7 Harvard fixtures and mapper

Save 3–5 real Harvard API responses to `tests/fixtures/harvard/`. Create `pipeline/assets/normalize/harvard.py` implementing `MapperProtocol`. Third normalization test case — three different data shapes mapping to one canonical schema. Harvard excavation records (Reisner at Giza) may have unusually detailed provenance. Write `tests/test_mappers/test_harvard.py`.

### 1.8 Dagster definitions wiring

Update `pipeline/definitions.py` to register all ingest and normalize assets with proper resource configuration (database connection, API keys from environment). Verify `dagster dev` launches and shows the asset graph.

## Milestone 2: Authority Data + Enrichment

Authority files are built from the real data ingested in Milestone 1. Analyze what ruler names, site names, and period labels actually appear across all three sources before writing the authority files.

### 2.1 Analyze ingested data for authority seeding

Query all normalized artifacts to extract distinct values for `ruler_display_name`, `origin_site_raw`, `period`, and `dynasty` across all three museums. Group by frequency. This analysis drives what goes into the authority files — real museum data, not guesses.

### 2.2 Authority data: rulers

Create `pipeline/pipeline/authority/rulers.json` with canonical Egyptian ruler entries. Each entry needs: canonical ID, display name, variant names array (personal name, throne name, Greek form, modern variants), dynasty, approximate date range (start/end BCE), and Wikidata ID. Seed from Wikidata SPARQL query for pharaohs (Q37011), but validate variants against the actual ruler names found in 2.1. Cover all dynasties — users search for Ramesses II as often as Thutmose III. ~200-300 entries minimum.

### 2.3 Authority data: sites

Create `pipeline/pipeline/authority/sites.json` with a curated hierarchy for the top 50–100 Egyptian sites. Each entry needs: canonical ID, display name, alternate names array, Pleiades ID, coordinates (lat/lng), parent site ID (for hierarchy: Egypt > Thebes > Western Thebes > Valley of the Kings > KV34), and Wikidata ID. Source from Pleiades gazetteer + Wikidata P131 (located in) for containment chains. Validate alternate names against the actual site names found in 2.1.

### 2.4 Ruler enrichment asset

Create `pipeline/assets/enrich/rulers.py` — Dagster asset that reads all canonical artifacts, matches `ruler_display_name` against the authority file's variant arrays (exact match first, fuzzy fallback to review queue per ADR-009), and writes `ruler_id` back to the artifacts table.

### 2.5 Site enrichment asset

Create `pipeline/assets/enrich/sites.py` — Dagster asset that reads `origin_site_raw` from all artifacts, matches against site authority file variant names (exact first, fuzzy to review queue), and writes `origin_site_id` and `origin_site_display_name` back. Must handle the hierarchy: an artifact tagged "Valley of the Kings" should also be discoverable under "Thebes" and "Western Thebes".

### 2.6 Review queue triage asset

Create `pipeline/assets/quality/review_queue_triage.py` — Dagster asset that processes pending fuzzy match reviews using an LLM (Haiku). Per ADR-009: fetch artifact + authority entry, ask LLM if the match is correct, write APPROVED/REJECTED/UNCERTAIN status. Approved variants get added to authority files.

### 2.7 Dagster asset checks

Implement `@asset_check` decorators per ADR-010 Layer 1: ingest completeness (record count vs API total), normalization validity (date ranges, enum values), authority coverage (unmatched value frequency), cross-museum site consistency. Emit coverage metrics as asset metadata.

### 2.8 LLM data audit asset

Create `pipeline/assets/quality/llm_audit.py` — Dagster asset that samples records and uses Haiku for semantic audit, batch anomaly detection, and authority variant suggestions per ADR-010 Layer 2.

## Milestone 3: Search + Web UX

### 3.1 Typesense sync asset

Create `pipeline/assets/index/sync_search.py` — Dagster asset that syncs all enriched canonical artifacts to the Typesense search index. Define the Typesense collection schema with appropriate field types (string, int32, float, geopoint for site coordinates). Must be idempotent.

### 3.2 Drizzle schema introspection

After pipeline migrations are in place, run `pnpm drizzle-kit introspect` in `web/` to generate `src/lib/db/schema.ts`. Install Drizzle ORM dependencies (`drizzle-orm`, `drizzle-kit`, `postgres`). Commit the generated schema.

### 3.3 Database and Typesense client setup

Create `web/src/lib/db/index.ts` (Drizzle client) and `web/src/lib/search/index.ts` (Typesense client, server-side only). Configure from environment variables.

### 3.4 Search API route

Create `web/src/app/api/search/route.ts` — Next.js API route that proxies search requests to Typesense. Accept query string, filters (site, ruler, dynasty, object type, museum), pagination. Return typed results.

### 3.5 License-aware image component

Create a shared component that renders artifact images based on the `license` field: embed for CC0, embed with attribution for CC-BY-NC-ND, placeholder with link-out for unknown/restrictive. This is a legal requirement — write component tests that verify correct rendering for each license type.

### 3.6 Search landing page (`/`)

Build the main search page: search bar, faceted filters (site of origin, ruler, dynasty, object type, museum), results in list/grid view with artifact images (via license-aware component), pagination. Filters show counts to avoid empty results. Server-rendered for SEO.

### 3.7 Artifact detail page (`/artifact/[id]`)

Build the detail page: full artifact info, image (license-aware), link back to source museum, match explanation for provenance data, and related candidates section (Tier A/B/C per ADR-008 with clear confidence labels).

### 3.8 Site page (`/site/[id]`)

Build the site page: all artifacts from an origin site across all museums, with the site hierarchy visible (e.g., "Valley of the Kings > Western Thebes > Thebes"). Filters for narrowing within the site's artifacts.

### 3.9 Museum page (`/museum/[id]`)

Build the museum browsing page: a museum's Egyptian holdings with Egyptology-native filters (dynasty, ruler, site of origin, object type) that the museum's own site may not offer.

### 3.10 Map view (`/map`)

Geographic visualization showing which museums hold artifacts from a given site. Click a site marker to see counts by museum and drill into specific objects. Use Leaflet or MapLibre.

### 3.11 Related candidates logic

Implement companion piece matching per ADR-008 confidence tiers: Tier A (shared excavation/tomb/temple ID), Tier B (same site + overlapping dates + related type), Tier C (same broad region). Display with clear labels — never imply certainty the data doesn't support.

### 3.12 Visual regression and E2E tests

Set up Playwright for deterministic E2E tests: search returns results, filters work, detail pages load, license rendering is correct (DOM assertions for img vs link based on license). Add `toHaveScreenshot()` visual regression at desktop + mobile viewports.

## Milestone 4: Beta Launch

### 4.1 Production deployment

Deploy pipeline (Dagster), web (Next.js), Postgres, and Typesense. Configure production environment variables, database credentials, API keys. Set up the `catalog` and `web` Postgres schemas.

### 4.2 Initial pipeline run

Execute full pipeline against live museum APIs: ingest all three museums, normalize, enrich, sync to Typesense. Record coverage stats: total artifacts, % with mapped ruler, % with mapped site, % with image.

### 4.3 Basic analytics

Add lightweight analytics to measure engagement: page views, search queries, filter usage. Keep it minimal — no user tracking beyond aggregate counts.
