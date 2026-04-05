# Hapi — Egyptian Artifacts Index

A cross-museum searchable index of Egyptian artifacts, organized by origin site.

## Architecture

Two independent systems communicate through Postgres and Typesense:

- **Pipeline** (Python / Dagster): `pipeline/` — ingests museum API data, normalizes to a canonical schema, enriches with authority data, syncs to search index
- **Web app** (TypeScript / Next.js): `web/` — search, browse, filter, map view over the indexed data
- **Schema ownership**: The pipeline owns the DB schema (SQLAlchemy + Alembic). The web app introspects from the live DB via `drizzle-kit introspect` to generate its TypeScript types. See ADR-011.

## Key commands

```bash
# Pipeline
cd pipeline && uv sync                 # Install Python deps
cd pipeline && uv run pytest           # Run pipeline tests
cd pipeline && uv run dagster dev      # Launch Dagster UI
cd pipeline && uv run alembic upgrade head  # Run DB migrations

# Web
cd web && pnpm install                 # Install JS deps
cd web && pnpm dev                     # Dev server
cd web && pnpm test                    # Run tests
cd web && pnpm lint                    # Lint
cd web && pnpm typecheck               # Type check
cd web && pnpm drizzle-kit introspect  # Regenerate schema.ts from DB

# Infrastructure
docker compose up -d                   # Postgres + Typesense
```

## Rules

1. **Pipeline owns the schema.** DB table definitions live in `pipeline/pipeline/types/models.py`. To change the schema: update the SQLAlchemy model → update the Pydantic model → create an Alembic migration → re-introspect Drizzle → commit all together.
2. **Every mapper has tests.** Every Dagster mapper asset must have corresponding tests using real fixture data in `pipeline/tests/fixtures/`. No mocks for museum data shapes.
3. **Mappers implement the protocol.** Every museum mapper must implement `MapperProtocol` defined in `pipeline/pipeline/types/protocol.py`.
4. **License before image.** Never embed an image URL directly in the UI. Always check the `license` field on the artifact record to determine rendering: embed, thumbnail, or link-out.
5. **Authority list, not hardcoded values.** Ruler and site matching always goes through the authority data in `pipeline/pipeline/authority/`. Never hardcode ruler names, dynasty labels, or site names in mapper code.
6. **Fields are nullable.** All fields in the canonical schema are optional except `id`, `source_museum`, and `source_url`. Sparse records are valid. The UI omits missing fields gracefully.

## Verification commands

Run the appropriate commands after any change:

| What changed | Run |
|---|---|
| Any pipeline code | `cd pipeline && uv run pytest` |
| A mapper | `cd pipeline && uv run pytest tests/test_mappers/` |
| SQLAlchemy models | `cd pipeline && uv run alembic revision --autogenerate -m "desc"` then `uv run alembic upgrade head` then `cd ../web && pnpm drizzle-kit introspect && pnpm typecheck` |
| Any web code | `cd web && pnpm typecheck && pnpm lint` |
| Web components | `cd web && pnpm test` |
| Anything before commit | `cd pipeline && uv run pytest && cd ../web && pnpm typecheck && pnpm lint` |

## Deeper docs

- Architecture decisions: `docs/adr/` (individual decision records)
- Product requirements: `docs/prd.md`
- Harness engineering approach: `docs/harness.md`
- Per-museum API notes and quirks: `docs/museum-sources/`
