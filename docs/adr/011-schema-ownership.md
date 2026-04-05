# ADR-011: Pipeline Owns DB Schema, Drizzle Introspects

## Status
Accepted (supersedes the `shared/schema.json` approach)

## Context
The original plan used `shared/schema.json` as a language-neutral contract between the Python pipeline and TypeScript web app, with CI tests verifying both Pydantic models and Drizzle schema conformed to it. In practice, this created three representations of the same data (JSON Schema, Pydantic, Drizzle) that all had to stay in sync manually.

The real contract between pipeline and web is the Postgres table itself — both sides read from and write to the same database. A separate JSON Schema file was documentation pretending to be enforcement.

## Decision
The pipeline (SQLAlchemy) owns the database schema. Alembic manages migrations. The web app (Drizzle) introspects from the live database to generate its TypeScript types.

### Data flow
```
SQLAlchemy models (pipeline/types/models.py)
    → Alembic migrations
        → Postgres tables
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

If the pipeline changes a column and the developer doesn't regenerate Drizzle's schema.ts, the web typecheck fails (the generated types won't match what the code expects).

## Consequences
- `shared/schema.json` is removed — no more three-way sync problem
- One source of truth: SQLAlchemy table definitions in `pipeline/pipeline/types/models.py`
- The Pydantic `CanonicalArtifact` model remains for validation/serialization in pipeline code. A structural test verifies its fields match the SQLAlchemy table columns.
- Drizzle schema is generated, not hand-written — zero manual sync on the TypeScript side
- Both CI jobs need a Postgres service container to run migrations
- Adding a field means: update SQLAlchemy model → update Pydantic model → create Alembic migration → re-introspect Drizzle → commit all together
