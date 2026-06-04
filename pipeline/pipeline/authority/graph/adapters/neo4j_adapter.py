"""Neo4j property-graph adapter (ADR-018 § Storage candidates → Neo4j).

Writes the IR as a native property graph: CRM class codes become node labels,
predicates become relationship types, inlined literals become node/relationship
properties. This is the graph-native target whose first-class multi-hop
traversals back the constraint-narrowed matching the ADR proposes for ADR-009.

Not the lossless adapter (Neo4j drops null-valued properties; the strict-RDF
adapter owns round-trip fidelity). This adapter exists to evaluate graph-native
query ergonomics for the deferred storage decision (ADR-019).
"""

from __future__ import annotations

import os
import re
from collections import defaultdict

from ..ir import ClaimGraph

DEFAULT_URI = "bolt://127.0.0.1:7687"

_SAFE = re.compile(r"[^A-Za-z0-9_]")


def _rel_type(predicate: str) -> str:
    """Map an IR predicate to a valid Cypher relationship type.

    e.g. 'hapi:same_entity_as' → 'HAPI_SAME_ENTITY_AS';
         'P140_assigned_attribute_to' → 'P140_ASSIGNED_ATTRIBUTE_TO'.
    The original predicate is retained as a relationship property.
    """
    return _SAFE.sub("_", predicate).upper()


def get_driver(uri: str | None = None, user: str | None = None, password: str | None = None):
    from neo4j import GraphDatabase

    uri = uri or os.environ.get("HAPI_NEO4J_URI", DEFAULT_URI)
    user = user or os.environ.get("HAPI_NEO4J_USER", "neo4j")
    password = password or os.environ.get("HAPI_NEO4J_PASSWORD", "hapi_poc_pw")
    return GraphDatabase.driver(uri, auth=(user, password))


def _clean_props(props: dict) -> dict:
    # Neo4j cannot store null property values.
    return {k: v for k, v in props.items() if v is not None}


def write_graph(driver, g: ClaimGraph, *, database: str = "neo4j") -> dict[str, int]:
    """Clear and rewrite the graph. Returns node/relationship counts."""
    # Group nodes by their (ordered) class-label set so each batch can use static
    # labels (no APOC needed for dynamic labels).
    by_labels: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for n in g.nodes:
        by_labels[n.crm_classes].append(
            {"id": n.id, "props": _clean_props(n.props), "label": n.hapi_label}
        )
    by_reltype: dict[str, list[dict]] = defaultdict(list)
    for e in g.edges:
        by_reltype[_rel_type(e.predicate)].append(
            {"s": e.subject_id, "o": e.object_id, "props": _clean_props(e.props), "pred": e.predicate}
        )

    with driver.session(database=database) as session:
        session.run("MATCH (n) DETACH DELETE n")
        for labels, rows in by_labels.items():
            label_str = ":".join(labels)
            # Key on _nid (not id): several nodes carry an `id` PROPERTY (the
            # predicate URI on :E55 Type nodes, the algorithm id on :D14) that
            # would otherwise clobber the node-identity key under SET x += props.
            session.run(
                f"UNWIND $rows AS r MERGE (x:{label_str} {{_nid: r.id}}) "
                f"SET x += r.props, x.hapi_label = r.label",
                rows=rows,
            )
        for rel_type, rows in by_reltype.items():
            session.run(
                f"UNWIND $rows AS r MATCH (a {{_nid: r.s}}), (b {{_nid: r.o}}) "
                f"MERGE (a)-[e:{rel_type}]->(b) SET e += r.props, e.predicate = r.pred",
                rows=rows,
            )
        counts = session.run(
            "MATCH (n) WITH count(n) AS nodes "
            "MATCH ()-[r]->() RETURN nodes, count(r) AS rels"
        ).single()
    return {"nodes": counts["nodes"], "rels": counts["rels"]}


def rulers_in_dynasty(driver, dynasty_number: int, *, database: str = "neo4j") -> list[str]:
    """Constraint-narrowing query (ADR-018 § Implications for matching).

    Returns the ids of rulers whose in_dynastic_period claim's value is the given
    Dynasty — the kind of structured narrowing that collapses a candidate set
    before name matching runs.
    """
    with driver.session(database=database) as session:
        result = session.run(
            "MATCH (r:E21)<-[:P140_ASSIGNED_ATTRIBUTE_TO]-(s:E13)"
            "-[:P177_ASSIGNED_PROPERTY_OF_TYPE]->(t:E55 {id: 'hapi:in_dynastic_period'}) "
            "MATCH (s)-[:P141_ASSIGNED]->(d:E4 {number: $n}) "
            "RETURN DISTINCT r._nid AS id ORDER BY id",
            n=dynasty_number,
        )
        return [row["id"] for row in result]
