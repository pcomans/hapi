# Hapi — Egyptian Artifacts Index

A cross-museum searchable index of Egyptian artifacts, organized by origin site.

## Architecture

Two independent systems communicate through Postgres and Typesense:

- **Pipeline** (Python / Dagster): `pipeline/` — ingests museum API data, normalizes to a canonical schema, enriches with authority data, syncs to search index
- **Web app** (TypeScript / Next.js): `web/` — search, browse, filter, map view over the indexed data
- **Shared contract**: `shared/schema.json` — the canonical artifact schema. Both Pydantic models (pipeline) and Drizzle schema (web) derive from this file.

## Key commands

```bash
# Pipeline
cd pipeline && uv sync                 # Install Python deps
cd pipeline && uv run pytest           # Run pipeline tests
cd pipeline && uv run dagster dev      # Launch Dagster UI

# Web
cd web && pnpm install                 # Install JS deps
cd web && pnpm dev                     # Dev server
cd web && pnpm test                    # Run tests
cd web && pnpm lint                    # Lint
cd web && pnpm typecheck               # Type check

# Infrastructure
docker compose up -d                   # Postgres + Typesense
```

## Rules

1. **Schema is the contract.** Never modify `shared/schema.json` without updating BOTH the Pydantic models in `pipeline/pipeline/types/canonical.py` AND the Drizzle schema in `web/src/lib/db/schema.ts`. A CI test verifies consistency.
2. **Every mapper has tests.** Every Dagster mapper asset must have corresponding tests using real fixture data in `pipeline/tests/fixtures/`. No mocks for museum data shapes.
3. **Mappers implement the protocol.** Every museum mapper must implement `MapperProtocol` defined in `pipeline/pipeline/types/protocol.py`.
4. **License before image.** Never embed an image URL directly in the UI. Always check the `license` field on the artifact record to determine rendering: embed, thumbnail, or link-out.
5. **Authority list, not hardcoded values.** Ruler and site matching always goes through the authority data in `pipeline/pipeline/authority/`. Never hardcode ruler names, dynasty labels, or site names in mapper code.
6. **Fields are nullable.** All fields in the canonical schema are optional except `id`, `source_museum`, and `source_url`. Sparse records are valid. The UI omits missing fields gracefully.

## Deeper docs

- Architecture decisions and rationale: `docs/architecture.md`
- Product requirements: `docs/prd.md`
- Per-museum API notes and quirks: `docs/museum-sources/`
- Canonical schema (source of truth): `shared/schema.json`
