# ADR-011: Pipeline Owns DB Schema, Drizzle Introspects, Separate Postgres Schemas

## Status
Accepted

## Context
The pipeline (Python) and web app (TypeScript) both need access to the same artifact data. A shared JSON Schema file would create three representations to keep in sync (JSON Schema, Pydantic, Drizzle). The real contract is the Postgres table itself — both sides read from the same database.

## Decision

### Schema separation

Pipeline and web tables live in the same Postgres database but in separate Postgres schemas (namespaces):

```
hapi (database)
├── catalog.*     — owned by Alembic (Python/SQLAlchemy)
│   ├── artifacts
│   ├── raw_met
│   ├── raw_brooklyn
│   ├── raw_harvard
│   └── fuzzy_match_reviews
│
└── web.*          — owned by Drizzle (TypeScript)
    ├── users (future)
    ├── saved_searches (future)
    └── settings (future)
```

The web app reads from `catalog.*` (read-only) and reads/writes its own `web.*` tables. Both schemas live in one database, so cross-schema joins work natively.

### Schema creation

`docker/init-schemas.sql` creates both schemas on first DB init:
```sql
CREATE SCHEMA IF NOT EXISTS catalog;
CREATE SCHEMA IF NOT EXISTS web;
```

### Pipeline owns the data schema

The pipeline (SQLAlchemy) defines all data tables in `pipeline/pipeline/types/models.py` with `MetaData(schema="catalog")`. Alembic manages migrations, with `version_table_schema="catalog"` so the migration history table also lives in the `catalog` schema.

The web app introspects `catalog.*` via `drizzle-kit introspect` to generate TypeScript types for reading artifact data.

### Web owns its own schema

The web app defines app-specific tables (users, settings, etc.) in its own Drizzle schema with `schema: "web"`. Drizzle migrations manage these independently. The pipeline never touches `web.*`.

### Data flow
```
SQLAlchemy models (pipeline/types/models.py, schema="catalog")
    → Alembic migrations
        → catalog.* tables in Postgres
            → drizzle-kit introspect
                → generated schema.ts (committed to web/src/lib/db/schema.ts)
                    → $inferSelect types used in app code
```

### Development workflow
```bash
# After changing SQLAlchemy models:
cd pipeline && uv run alembic revision --autogenerate -m "description"
cd pipeline && uv run alembic upgrade head
cd web && pnpm drizzle-kit introspect
# Commit both the migration and the regenerated schema.ts
```

### CI verification
```
1. Pipeline job: run alembic upgrade head → run pytest
2. Web job: run pipeline migrations → pnpm typecheck + lint + build
```

## Consequences
- Single source of truth: SQLAlchemy table definitions, no separate schema file to keep in sync
- Clean ownership boundary: pipeline owns `catalog.*`, web owns `web.*`
- The web app's DB user can be `SELECT`-only on `catalog.*` and full access on `web.*` (enforced via Postgres GRANT in production)
- Cross-schema joins work natively (e.g., `web.saved_searches` referencing `catalog.artifacts`)
- Alembic and Drizzle migration histories don't interfere — each tracks its own schema
- Both CI jobs need a Postgres service container with the init script to create schemas
- Adding a catalog field: update SQLAlchemy model → update Pydantic model → create Alembic migration → re-introspect Drizzle → commit all together
- Adding a web-only table: define in Drizzle, run Drizzle migration, no pipeline changes needed
