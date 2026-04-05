# ADR-003: Typesense over Elasticsearch

## Status
Accepted

## Context
The web app needs full-text search with typo tolerance, faceted filtering, and geo-search for the map view. Elasticsearch and Typesense were the main contenders.

## Decision
Use Typesense.

## Consequences
- Typesense provides typo-tolerant search, faceted filtering, and geo-search in a single binary (no JVM)
- At the expected scale (O(1M) artifacts), Typesense handles the load trivially
- Simpler operationally than Elasticsearch — fewer knobs, less tuning required
- If we outgrow Typesense, the search abstraction is thin enough to swap for Elasticsearch later
- Elasticsearch's synonym expansion and `more_like_this` queries would be useful for companion matching but are not essential for v1
