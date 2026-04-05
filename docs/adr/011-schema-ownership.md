# ADR-011: Pipeline Owns DB Schema, Drizzle Introspects, Separate Postgres Schemas

## Status
Accepted (supersedes the `shared/schema.json` approach)

## Context
The original plan used `shared/schema.json` as a language-neutral contract between the Python pipeline and TypeScript web app, with CI tests verifying both Pydantic models and Drizzle schema conformed to it. In practice, this created three representations of the same data (JSON Schema, Pydantic, Drizzle) that all had to stay in sync manually.

The real contract between pipeline and web is the Postgres table itself — both sides read from and write to the same database. A separate JSON Schema file was documentation pretending to be enforcement.

## Decision

### Schema separation

Pipeline and web tables live in the same Postgres database but in separate Postgres schemas (namespaces):

```
hapi (database)
├── pipeline.*     — owned by Alembic (Python/SQLAlchemy)
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

The web app reads from `pipeline.*` (read-only) and reads/writes its own `web.*` tables. Both schemas live in one database, so cross-schema joins work natively.

### Schema creation

`docker/init-schemas.sql` creates both schemas on first DB init:
```sql
CREATE SCHEMA IF NOT EXISTS pipeline;
CREATE SCHEMA IF NOT EXISTS web;
```

### Pipeline owns the data schema

The pipeline (SQLAlchemy) defines all data tables in `pipeline/pipeline/types/models.py` with `MetaData(schema="pipeline")`. Alembic manages migrations, with `version_table_schema="pipeline"` so the migration history table also lives in the `pipeline` schema.

The web app introspects `pipeline.*` via `drizzle-kit introspect` to generate TypeScript types for reading artifact data.

### Web owns its own schema

The web app defines app-specific tables (users, settings, etc.) in its own Drizzle schema with `schema: "web"`. Drizzle migrations manage these independently. The pipeline never touches `web.*`.

### Data flow
```
SQLAlchemy models (pipeline/types/models.py, schema="pipeline")
    → Alembic migrations
        → pipeline.* tables in Postgres
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
- `shared/schema.json` is removed — no more three-way sync problem
- Clean ownership boundary: pipeline owns `pipeline.*`, web owns `web.*`
- The web app's DB user can be `SELECT`-only on `pipeline.*` and full access on `web.*` (enforced via Postgres GRANT in production)
- Cross-schema joins work natively (e.g., `web.saved_searches` referencing `pipeline.artifacts`)
- Alembic and Drizzle migration histories don't interfere — each tracks its own schema
- Both CI jobs need a Postgres service container with the init script to create schemas
- Adding a pipeline field: update SQLAlchemy model → update Pydantic model → create Alembic migration → re-introspect Drizzle → commit all together
- Adding a web-only table: define in Drizzle, run Drizzle migration, no pipeline changes needed
