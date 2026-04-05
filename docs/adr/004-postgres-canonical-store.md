# ADR-004: Postgres as Canonical Store

## Status
Accepted

## Context
The canonical data is relational: artifacts belong to museums, reference rulers and sites from authority tables, and carry per-record license metadata. Scale is O(1M) records.

## Decision
Use PostgreSQL as the canonical store. The pipeline owns the schema via SQLAlchemy + Alembic migrations. The web app introspects from the live DB via Drizzle. See ADR-011.

## Consequences
- Postgres is the right tool for structured relational data at this scale
- Both Drizzle and SQLAlchemy have mature Postgres support
- The site hierarchy (parent-child relationships) maps naturally to relational queries
- No need for a document store, graph database, or NoSQL solution at this scale
- One source of truth (Postgres tables), not three representations to keep in sync
