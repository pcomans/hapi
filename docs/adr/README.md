# Architecture Decision Records

Each file records a single architectural decision: the context, the decision, and the consequences.

| ADR | Decision | Status |
|-----|----------|--------|
| [001](001-two-languages.md) | Python pipeline + TypeScript frontend | Accepted |
| [002](002-dagster-orchestration.md) | Dagster for pipeline orchestration | Accepted |
| [003](003-typesense-search.md) | Typesense over Elasticsearch | Accepted |
| [004](004-postgres-canonical-store.md) | Postgres as canonical store | Accepted |
| [005](005-raw-data-preserved.md) | Raw museum data preserved verbatim | Accepted |
| [006](006-one-mapper-per-museum.md) | One mapper per museum, no universal parser | Accepted |
| [007](007-origin-site-first-class.md) | Origin site as first-class entity with hierarchy | Accepted |
| [008](008-confidence-tiers.md) | Confidence tiers for companion piece matching | Accepted |
| [009](009-review-queue.md) | Fuzzy match review queue with LLM triage | Accepted |
| [010](010-quality-evaluation.md) | Quality evaluation: deterministic checks + LLM layers | Accepted |
| [011](011-schema-ownership.md) | Pipeline owns DB schema, Drizzle introspects | Accepted |
| [012](012-authoritative-sources.md) | Authoritative sources for Egyptian chronology, rulers, and sites | Accepted |
| [013](013-structured-dating-fields.md) | Structured dating fields with qualifier, certainty, relation | Accepted |
| [014](014-exclude-non-ancient-records.md) | Exclude non-ancient records during normalization | Accepted |
| [015](015-findspot-and-production-place.md) | Findspot and production place are separate fields | Accepted |
| [016](016-royal-display-name-anglicized-nomen.md) | Royal display name standard is Conventional English Display Form | Accepted |
| [017](017-ocr-pipeline-for-scan-only-sources.md) | OCR pipeline for scan-only authority sources | Accepted |
| [018](018-authority-as-claim-graph.md) | Authority layer as source-attributed claim graph | Proposed |
| [020](020-matcher-evaluation-and-cross-source-identity.md) | Matcher evaluation & cross-source identity ground truth | Proposed |
