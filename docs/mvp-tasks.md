# MVP Task List

Tasks to reach MVP (PRD Milestones 1–5). Each task is scoped for a single agent session. Tasks are ordered by dependency — later tasks depend on earlier ones.

The guiding principle: **one museum end-to-end before adding complexity.** The Met is the vertical slice that validates the entire pipeline. Brooklyn and Harvard stress-test normalization. Authority data is built from real ingested data, not guesses.

## Milestone 1: Met Vertical Slice

Take the Met from raw API to search results on screen. This validates the entire stack — schema, ingest, mapper, search index, web — before adding other museums.

### 1.1 Alembic migration for initial schema

Run `uv run alembic revision --autogenerate -m "initial schema"` and `uv run alembic upgrade head` to create the actual database tables. Verify all tables exist in the `catalog` schema. This must happen before any ingest or mapper work.

### 1.2 Met fixtures

Save 3–5 real Met API responses to `tests/fixtures/met/` by calling the API directly. Choose: one richly catalogued object (full geography, reign, dates), one sparse record (minimal fields), one with ambiguous provenance ("Said to be from"), one with a co-regency or unusual reign field, one with no image. These fixtures drive all mapper development.

### 1.3 Met mapper + tests

Create `pipeline/assets/normalize/met.py` implementing `MapperProtocol`. Map Met fields to `CanonicalArtifact`: `objectID` → `id`, `title`, `objectName` → `object_type`, structured geography fields → `origin_site_raw` (preserve `geographyType` for provenance confidence), `period`, `dynasty`, `reign` → `ruler_display_name`, `objectBeginDate`/`objectEndDate` → `date_start`/`date_end`, `primaryImage` → `image_url`, etc. Parse date strings like "ca. 1479-1425 B.C." into integer ranges. Handle `reign` field containing period info instead of ruler names.

Write `tests/test_mappers/test_met.py` asserting specific mapped field values for each fixture.

### 1.4 Met ingest asset

Create `pipeline/assets/ingest/met.py` — Dagster asset that fetches all Egyptian Art object IDs (`departmentIds=10`) then fetches each object record, storing raw JSON verbatim in `raw_met` table. Handle the Met's pattern: one call returns ~26k IDs, then individual fetches per object. Respect 80 req/sec rate limit. Must be idempotent (re-run overwrites).

### 1.5 Dagster definitions wiring (Met)

Update `pipeline/definitions.py` to register Met ingest and normalize assets with proper resource configuration (database connection from environment). Verify `dagster dev` launches and shows the Met asset graph.

### 1.6 Typesense sync asset

Create `pipeline/assets/index/sync_search.py` — Dagster asset that syncs all canonical artifacts to the Typesense search index. Define the Typesense collection schema with appropriate field types (string, int32, float, geopoint for site coordinates). Must be idempotent.

### 1.7 Drizzle setup + schema introspection

Install Drizzle ORM dependencies (`drizzle-orm`, `drizzle-kit`, `postgres`) in `web/`. Run `pnpm drizzle-kit introspect` to generate `src/lib/db/schema.ts` from the live database. Create `web/src/lib/db/index.ts` (Drizzle client). Commit the generated schema.

### 1.8 Search API route + Typesense client

Create `web/src/lib/search/index.ts` (Typesense client, server-side only). Create `web/src/app/api/search/route.ts` — Next.js API route that proxies search requests to Typesense. Accept query string, filters (site, ruler, dynasty, object type, museum), pagination. Return typed results.

### 1.9 License-aware image component

Create a shared component that renders artifact images based on the `license` field: embed for CC0, embed with attribution for CC-BY-NC-ND, placeholder with link-out for unknown/restrictive. This is a legal requirement — write component tests that verify correct rendering for each license type.

### 1.10 Search landing page (`/`)

Build the main search page: search bar, faceted filters (site of origin, ruler, dynasty, object type, museum), results in list/grid view with artifact images (via license-aware component), pagination. Filters show counts to avoid empty results. Server-rendered for SEO. At this point, Met data should be searchable end-to-end.

## Milestone 2: Brooklyn + Harvard

Add the other two museums to stress-test normalization across different data shapes. The pipeline, search index, and web already work from Milestone 1.

### 2.1 Brooklyn fixtures + mapper + tests

Save 3–5 real Brooklyn API responses to `tests/fixtures/brooklyn/`. Create `pipeline/assets/normalize/brooklyn.py` implementing `MapperProtocol`. Map Brooklyn's field structure to `CanonicalArtifact`. Field names differ from the Met — this is the first real normalization stress test. Document any fields that don't map cleanly in the mapper's docstring. Write `tests/test_mappers/test_brooklyn.py` with specific value assertions.

### 2.2 Brooklyn ingest asset

Create `pipeline/assets/ingest/brooklyn.py` — Dagster asset that fetches Brooklyn Museum Egyptian collection via their API, storing raw JSON in `raw_brooklyn` table. Requires API key from environment. Determine pagination and rate limit behavior during implementation.

### 2.3 Harvard fixtures + mapper + tests

Save 3–5 real Harvard API responses to `tests/fixtures/harvard/`. Create `pipeline/assets/normalize/harvard.py` implementing `MapperProtocol`. Third normalization test case — three different data shapes mapping to one canonical schema. Harvard excavation records (Reisner at Giza) may have unusually detailed provenance. Write `tests/test_mappers/test_harvard.py`.

### 2.4 Harvard ingest asset

Create `pipeline/assets/ingest/harvard.py` — Dagster asset that fetches Harvard Art Museums Egyptian collection, storing raw JSON in `raw_harvard` table. Requires API key. Determine collection size and filter strategy during implementation (classification filter may need tuning to exclude Egyptianizing non-Egyptian pieces).

### 2.5 Register Brooklyn + Harvard in Dagster

Update `pipeline/definitions.py` to register Brooklyn and Harvard ingest and normalize assets. Verify all three museums appear in the Dagster asset graph.

### 2.6 Schema adjustments (if needed)

After mapping all three museums, assess whether the canonical schema needs new fields or changes. If so: update SQLAlchemy model → update Pydantic model → create Alembic migration → re-introspect Drizzle → commit all together.

## Milestone 3: Authority Data + Enrichment

Authority files are built from real data ingested in Milestones 1–2. Analyze what ruler names, site names, and period labels actually appear across all three sources before writing the authority files.

### 3.1 Analyze ingested data for authority seeding

Query all normalized artifacts to extract distinct values for `ruler_display_name`, `origin_site_raw`, `period`, and `dynasty` across all three museums. Group by frequency. This analysis drives what goes into the authority files — real museum data, not guesses.

### 3.2 Authority data: rulers

Create `pipeline/pipeline/authority/rulers.json` with canonical Egyptian ruler entries. Each entry needs: canonical ID, display name, variant names array (personal name, throne name, Greek form, modern variants), dynasty, approximate date range (start/end BCE), and Wikidata ID. Seed from Wikidata SPARQL query for pharaohs (Q37011), but validate variants against the actual ruler names found in 3.1. Cover all dynasties. ~200-300 entries minimum.

### 3.3 Authority data: sites

Create `pipeline/pipeline/authority/sites.json` with a curated hierarchy for the top 50–100 Egyptian sites. Each entry needs: canonical ID, display name, alternate names array, Pleiades ID, coordinates (lat/lng), parent site ID (for hierarchy: Egypt > Thebes > Western Thebes > Valley of the Kings > KV34), and Wikidata ID. Source from Pleiades gazetteer + Wikidata P131 (located in) for containment chains. Validate alternate names against the actual site names found in 3.1.

### 3.4 Ruler enrichment asset

Create `pipeline/assets/enrich/rulers.py` — Dagster asset that reads all canonical artifacts, matches `ruler_display_name` against the authority file's variant arrays (exact match first, fuzzy fallback to review queue per ADR-009), and writes `ruler_id` back to the artifacts table.

### 3.5 Site enrichment asset

Create `pipeline/assets/enrich/sites.py` — Dagster asset that reads `origin_site_raw` from all artifacts, matches against site authority file variant names (exact first, fuzzy to review queue), and writes `origin_site_id` and `origin_site_display_name` back. Must handle the hierarchy: an artifact tagged "Valley of the Kings" should also be discoverable under "Thebes" and "Western Thebes".

### 3.6 Review queue triage asset

Create `pipeline/assets/quality/review_queue_triage.py` — Dagster asset that processes pending fuzzy match reviews using an LLM (Haiku). Per ADR-009: fetch artifact + authority entry, ask LLM if the match is correct, write APPROVED/REJECTED/UNCERTAIN status. Approved variants get added to authority files.

### 3.7 Dagster asset checks

Implement `@asset_check` decorators per ADR-010 Layer 1: ingest completeness (record count vs API total), normalization validity (date ranges, enum values), authority coverage (unmatched value frequency), cross-museum site consistency. Emit coverage metrics as asset metadata.

### 3.8 LLM data audit asset

Create `pipeline/assets/quality/llm_audit.py` — Dagster asset that samples records and uses Haiku for semantic audit, batch anomaly detection, and authority variant suggestions per ADR-010 Layer 2.

## Milestone 4: Full Web UX

Remaining pages beyond the search landing page. The search page already works from Milestone 1.

### 4.1 Artifact detail page (`/artifact/[id]`)

Build the detail page: full artifact info, image (license-aware), link back to source museum, match explanation for provenance data. Related candidates section deferred to Milestone 6.

### 4.2 Site page (`/site/[id]`)

Build the site page: all artifacts from an origin site across all museums, with the site hierarchy visible (e.g., "Valley of the Kings > Western Thebes > Thebes"). Filters for narrowing within the site's artifacts.

### 4.3 Museum page (`/museum/[id]`)

Build the museum browsing page: a museum's Egyptian holdings with Egyptology-native filters (dynasty, ruler, site of origin, object type) that the museum's own site may not offer.

### 4.4 Visual regression and E2E tests

Set up Playwright for deterministic E2E tests: search returns results, filters work, detail pages load, license rendering is correct (DOM assertions for img vs link based on license). Add `toHaveScreenshot()` visual regression at desktop + mobile viewports.

## Milestone 5: Beta Launch

### 5.1 Production deployment

Deploy pipeline (Dagster), web (Next.js), Postgres, and Typesense. Configure production environment variables, database credentials, API keys. Set up the `catalog` and `web` Postgres schemas.

### 5.2 Full pipeline run + coverage stats

Execute full pipeline against live museum APIs: ingest all three museums, normalize, enrich, sync to Typesense. Record coverage stats: total artifacts, % with mapped ruler, % with mapped site, % with image.

### 5.3 Basic analytics

Add lightweight analytics to measure engagement: page views, search queries, filter usage. Keep it minimal — no user tracking beyond aggregate counts.

## Milestone 6 (optional): Map View + Companion Pieces

Valuable but not required for a useful beta (PRD Milestone 5).

### 6.1 Map view (`/map`)

Geographic visualization showing which museums hold artifacts from a given site. Click a site marker to see counts by museum and drill into specific objects. Use Leaflet or MapLibre.

### 6.2 Related candidates logic

Implement companion piece matching per ADR-008 confidence tiers: Tier A (shared excavation/tomb/temple ID), Tier B (same site + overlapping dates + related type), Tier C (same broad region). Display with clear labels — never imply certainty the data doesn't support.

### 6.3 Related candidates on artifact detail page

Add the related candidates section to `/artifact/[id]` using the matching logic from 6.2. Show Tier A/B/C results with clear confidence labels and match explanations.
