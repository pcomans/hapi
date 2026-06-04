"""Substrate-neutral intermediate representation (IR) of the ADR-018 claim graph.

The IR is a typed property graph: CRM/CRMdig-classed nodes, predicate-typed edges,
inlined literals/attributes on nodes, and edge properties. It is the single
canonical artifact of the authority layer; every storage adapter (relational,
Neo4j, AGE, strict-RDF) is a deterministic serialisation OF this IR, and the
strict-RDF adapter's round-trip is what proves the inlining conventions lossless.

Design rules (mirroring ADR-018):
- A node's ``crm_classes`` are CIDOC/CRMdig class *local names* (e.g. ``"E13"``,
  ``"E21"``, ``"D10"``). Multi-typing is allowed (e.g. ``["E33", "E41"]`` for a
  language-bearing appellation) per encoding convention #2.
- Literals never become E1 values: they are inlined as node ``props`` on the
  value-bearing entity (E41 ``symbolic_content``, E52 ``begin_of_the_begin`` ...),
  per ADR-018 principle 5 + encoding conventions #1/#3.
- An edge ``predicate`` is either a CIDOC/CRMdig property local name
  (``"P140_assigned_attribute_to"``) or a hapi-namespaced predicate
  (``"hapi:derived_by_run"``). The P177 *target* is a separate ``:E55 Type`` node.

No defensive programming (Constitutional rule 2): structural violations raise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Node:
    """A typed node in the claim graph.

    ``id`` is a stable, deterministic key (so re-loads are idempotent and adapters
    can MERGE rather than duplicate). ``crm_classes`` is a non-empty, ordered list
    of CIDOC/CRMdig class local names. ``props`` holds inlined literals/attributes.
    ``hapi_label`` is the optional Hapi node label (``"Ruler"``, ``"Statement"``,
    ``"MatcherRun"`` ...) used purely for readability in graph adapters.
    """

    id: str
    crm_classes: tuple[str, ...]
    props: dict[str, Any] = field(default_factory=dict)
    hapi_label: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Node.id must be a non-empty string")
        if not self.crm_classes:
            raise ValueError(f"Node {self.id!r} must carry at least one CRM class")
        for cls in self.crm_classes:
            # Local names only; full URIs are resolved by the cidoc_spec catalogue.
            if cls.startswith("http") or "/" in cls:
                raise ValueError(
                    f"Node {self.id!r} crm_classes must be local names, got {cls!r}"
                )


@dataclass(frozen=True)
class Edge:
    """A directed, predicate-typed edge between two nodes.

    ``predicate`` is a property local name (CIDOC/CRMdig) or a ``hapi:``-prefixed
    predicate. ``props`` carries edge-level attributes — notably the ``cited_page``
    / ``cited_pdf_page`` locators on a ``P70i_is_documented_in`` edge (encoding
    convention #4).
    """

    subject_id: str
    predicate: str
    object_id: str
    props: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (self.subject_id and self.object_id and self.predicate):
            raise ValueError("Edge requires subject_id, predicate, and object_id")


class ClaimGraph:
    """A collection of nodes + edges with referential-integrity enforcement.

    Adding an edge whose endpoints are not present raises (Constitutional rule 2 —
    no dangling references silently tolerated). ``add_node`` is idempotent on
    identical re-adds but raises on a conflicting redefinition of the same id, so
    two loaders cannot silently clobber each other's node.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: list[Edge] = []

    # -- construction -------------------------------------------------------
    def add_node(self, node: Node) -> Node:
        existing = self._nodes.get(node.id)
        if existing is not None:
            if existing != node:
                raise ValueError(
                    f"Conflicting redefinition of node {node.id!r}: "
                    f"{existing!r} != {node!r}"
                )
            return existing
        self._nodes[node.id] = node
        return node

    def add_edge(self, edge: Edge) -> Edge:
        if edge.subject_id not in self._nodes:
            raise ValueError(
                f"Edge subject {edge.subject_id!r} not in graph "
                f"(predicate {edge.predicate!r})"
            )
        if edge.object_id not in self._nodes:
            raise ValueError(
                f"Edge object {edge.object_id!r} not in graph "
                f"(predicate {edge.predicate!r})"
            )
        self._edges.append(edge)
        return edge

    # -- access -------------------------------------------------------------
    @property
    def nodes(self) -> list[Node]:
        return list(self._nodes.values())

    @property
    def edges(self) -> list[Edge]:
        return list(self._edges)

    def node(self, node_id: str) -> Node:
        if node_id not in self._nodes:
            raise KeyError(f"No node {node_id!r} in graph")
        return self._nodes[node_id]

    def nodes_of_class(self, crm_class: str) -> list[Node]:
        return [n for n in self._nodes.values() if crm_class in n.crm_classes]

    def edges_with_predicate(self, predicate: str) -> list[Edge]:
        return [e for e in self._edges if e.predicate == predicate]

    def out_edges(self, node_id: str) -> list[Edge]:
        return [e for e in self._edges if e.subject_id == node_id]

    def __len__(self) -> int:
        return len(self._nodes)

    def __repr__(self) -> str:
        return f"ClaimGraph(nodes={len(self._nodes)}, edges={len(self._edges)})"
