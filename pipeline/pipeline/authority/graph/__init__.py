"""ADR-018 source-attributed claim graph — substrate-neutral core + adapters.

This package implements the ADR-018 authority claim graph as a substrate-neutral
intermediate representation (`ir.ClaimGraph`) plus swappable adapters (Postgres
relational, Neo4j, strict CIDOC RDF, and — best-effort — Apache AGE). No substrate
is privileged: the IR is the only canonical artifact, so the deferred storage
decision (ADR-019) stays genuinely open and is backed by comparative evidence.

See docs/adr/018-authority-as-claim-graph.md.
"""
