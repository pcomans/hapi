# ADR-001: Python Pipeline + TypeScript Frontend

## Status
Accepted

## Context
The project has two distinct workloads: a data pipeline (parsing heterogeneous museum JSON/CSV, fuzzy string matching, SPARQL queries, hierarchical site normalization) and a web application (interactive search, maps, faceted filters, server-rendered pages). A single-language approach was considered.

## Decision
Use Python for the pipeline and TypeScript/Next.js for the frontend. The two systems share no code; they communicate through Postgres and Typesense.

## Consequences
- Python's ecosystem (rapidfuzz, SPARQLWrapper, pandas-like transforms) is materially better for data munging
- Next.js/React is the natural choice for an interactive web app with maps, faceted search, and SSR
- Two languages means two build systems, two CI jobs, and context switching for the developer/agent
- The boundary is clean: Postgres and Typesense are language-agnostic interfaces
- The pipeline owns the Postgres schema (SQLAlchemy + Alembic migrations). The web app introspects from the live DB via `drizzle-kit introspect`. See ADR-011.
