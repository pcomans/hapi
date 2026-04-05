# ADR-007: Origin Site as First-Class Entity with Hierarchy

## Status
Accepted

## Context
The product's core value proposition is virtual reunification — showing artifacts from the same original context across museums. Origin sites need structure beyond free text.

## Decision
Sites (Karnak, Deir el-Bahri, Amarna) have their own table with coordinates, Pleiades IDs, alternate names, and a parent-child hierarchy: Egypt > Thebes > Western Thebes > Valley of the Kings > KV34.

Artifacts with vague provenance (e.g., "Thebes") are assigned to the broadest matching site node. No separate `origin_region` field — the hierarchy handles varying specificity.

## Consequences
- Enables site-based search: "everything from Thebes" returns artifacts from all sub-sites
- Enables map view: sites have coordinates
- Enables companion piece matching: artifacts sharing a site node are candidates
- Requires curating ~50-100 major sites upfront (Pleiades IDs, parent-child relationships)
- Tier C matching ("Explore more from this area") works by matching at higher hierarchy levels
