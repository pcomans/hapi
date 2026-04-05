# ADR-002: Dagster for Pipeline Orchestration

## Status
Accepted

## Context
The pipeline has a natural asset graph: raw data per museum -> normalized records -> enriched records -> search index. Alternatives considered: plain scripts, Trigger.dev (TypeScript), Inngest, Temporal.

## Decision
Use Dagster. Each museum's raw ingest, each mapper, enrichment, and search index sync are modeled as software-defined assets with a dependency graph.

## Consequences
- Dagster's asset model maps directly to the pipeline architecture
- The Dagster UI provides free observability: which museum last ingested, what failed, what's stale
- Dagster's structured asset definitions serve as a spec the AI agent can follow when adding new museums
- Dagster requires Python, reinforcing the two-language split (ADR-001)
- Dagster has operational overhead (webserver + daemon) but is justified because the agent benefits from explicit structure over implicit conventions
- Plain scripts were rejected specifically because 100% of code is AI-written — explicit structure prevents drift across sessions
