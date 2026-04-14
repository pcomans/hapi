# Architecture

## System overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Raw Storage (per museum)                   │
│  Met: JSON/CSV  │  Brooklyn: JSON  │  Harvard: JSON          │
└────────┬────────┴────────┬─────────┴────────┬────────────────┘
         │                 │                  │
    ┌────▼────┐     ┌──────▼─────┐    ┌───────▼──────┐
    │Met Mapper│     │Brooklyn    │    │Harvard       │
    │         │     │Mapper      │    │Mapper        │
    └────┬────┘     └─────┬──────┘    └──────┬───────┘
         │                │                  │
         ▼                ▼                  ▼
┌──────────────────────────────────────────────────────────────┐
│              Canonical Store (Postgres)                       │
│  (normalized fields, authority-linked, license per record)   │
└───────────────────────────┬──────────────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │ Enrichment Layer │
                   │ (ruler authority │
                   │  list, site      │
                   │  hierarchy,      │
                   │  period/dynasty) │
                   └────────┬────────┘
                            │
                     ┌──────▼──────┐
                     │  Typesense  │
                     │  (search)   │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │  Next.js    │
                     │  (web app)  │
                     └─────────────┘
```

## Architecture Decision Records

All architectural decisions are documented individually in `docs/adr/`. See the [ADR index](adr/README.md) for the full list.

Key decisions:
- [ADR-001](adr/001-two-languages.md): Python pipeline + TypeScript frontend
- [ADR-002](adr/002-dagster-orchestration.md): Dagster for pipeline orchestration
- [ADR-006](adr/006-one-mapper-per-museum.md): One mapper per museum, no universal parser
- [ADR-007](adr/007-origin-site-first-class.md): Origin site as first-class entity with hierarchy
- [ADR-011](adr/011-schema-ownership.md): Pipeline owns DB schema, Drizzle introspects

## What is NOT in this architecture

- No user accounts, authentication, or saved state
- No image storage — images loaded from museum CDNs or linked out, depending on license
- No AI/ML features (visual similarity, auto-classification)
- No real-time sync — pipeline runs periodically, not continuously
