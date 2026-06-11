"""Substrate adapters: each serialises the IR ClaimGraph to one backing store.

No substrate is privileged (ADR-018 keeps the storage choice open / ADR-019):
- rdf_adapter:        strict CIDOC RDF (rdflib) + lossless round-trip
- relational_adapter: Postgres relational E13 + the three chain constraints
- neo4j_adapter:      Neo4j property graph (Cypher MERGE)
"""
