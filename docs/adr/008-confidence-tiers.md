# ADR-008: Confidence Tiers for Companion Piece Matching

## Status
Accepted

## Context
Cross-museum virtual reunification is the long-term vision, but false matches destroy user trust. Not all matches are equal — a shared excavation ID is much stronger evidence than being from the same broad region.

## Decision
Three explicit confidence tiers with distinct UI labels:

- **Tier A (strong):** Shared excavation ID, tomb/temple ID, or explicit "part of same set" — displayed as "Companion pieces"
- **Tier B (medium):** Same normalized origin site + overlapping date range + related object type — displayed as "Related artifacts"
- **Tier C (weak):** Same broad region (high-level site hierarchy node) — displayed as "Explore more from this area"

## Consequences
- The UI never implies certainty the data doesn't support
- Tier labels are user-facing and must be consistent across the app
- Schema includes `excavation_id` and `tomb_temple_id` fields specifically to enable Tier A matching
- Tier C relies on the site hierarchy (ADR-007) rather than a separate region field
- Matching logic and tier assignment are implemented in the web app query layer, not in the pipeline
