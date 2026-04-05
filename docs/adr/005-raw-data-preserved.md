# ADR-005: Raw Museum Data Preserved Verbatim

## Status
Accepted

## Context
Museum APIs return heterogeneous JSON/CSV. The canonical schema will evolve as more museums are added and normalization improves.

## Decision
Store each museum's API response byte-for-byte in a per-museum raw table. Mappers read from raw storage, not directly from APIs.

## Consequences
- Mappers can be re-run as the canonical schema evolves without re-fetching from APIs
- Provides an audit trail for debugging normalization issues ("why did this artifact map to the wrong site?")
- Raw tables grow with each museum but are append-only and rarely queried directly
- Decouples ingest frequency (API rate limits, availability) from normalization frequency
