# ADR-004: Postgres as Canonical Store

## Status
Accepted

## Context
The canonical data is relational: artifacts belong to museums, reference rulers and sites from authority tables, and carry per-record license metadata. Scale is ~100k records.

## Decision
Use PostgreSQL as the canonical store. Schema defined in `shared/schema.json`, implemented via Drizzle (web) and Pydantic/SQLAlchemy (pipeline).

## Consequences
- Postgres is the right tool for structured relational data at this scale
- Both Drizzle and SQLAlchemy have mature Postgres support
- The site hierarchy (parent-child relationships) maps naturally to relational queries
- No need for a document store, graph database, or NoSQL solution at this scale
