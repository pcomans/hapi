"""Storage-neutral ADR-018 claim graph prototype.

ADR-018 deliberately defers the storage decision. This module sketches the
loader boundary that both Postgres and Neo4j implementations can share:
source rows become per-source entity nodes plus E13 statement nodes, and
shortcut triples are emitted only through the predicate registry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


AUTHORITY_ROOT = Path(__file__).parent
DEFAULT_REGISTRY_PATH = AUTHORITY_ROOT / "predicate_registry.json"

CRM = "http://www.cidoc-crm.org/cidoc-crm/"
CRMDIG = "http://www.cidoc-crm.org/extensions/crmdig/"
HAPI = "https://pcomans.github.io/hapi-crm#"

P140 = f"{CRM}P140_assigned_attribute_to"
P141 = f"{CRM}P141_assigned"
P177 = f"{CRM}P177_assigned_property_of_type"
P14 = f"{CRM}P14_carried_out_by"
P70I = f"{CRM}P70i_is_documented_in"


@dataclass(frozen=True)
class PredicateRegistryEntry:
    id: str
    label: str
    subject_class: str
    value_class: str
    crm_nearest: str | None
    is_symmetric: bool
    derived: bool
    p177_target: bool
    emit_shortcut: bool


@dataclass(frozen=True)
class AuthorityNode:
    id: str
    classes: tuple[str, ...]
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Statement:
    id: str
    subject_id: str
    predicate_id: str
    value_id: str
    actor_id: str | None
    document_id: str | None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Triple:
    subject: str
    predicate: str
    object: str


@dataclass
class ClaimGraph:
    nodes: dict[str, AuthorityNode] = field(default_factory=dict)
    statements: dict[str, Statement] = field(default_factory=dict)

    def add_node(self, node: AuthorityNode) -> None:
        existing = self.nodes.get(node.id)
        if existing is not None and existing != node:
            raise ValueError(f"Conflicting node definition for {node.id}")
        self.nodes[node.id] = node

    def add_statement(self, statement: Statement, registry: "PredicateRegistry") -> None:
        registry.require_p177_target(statement.predicate_id)
        if statement.subject_id not in self.nodes:
            raise ValueError(f"Statement {statement.id} has unknown subject {statement.subject_id}")
        if statement.value_id not in self.nodes:
            raise ValueError(f"Statement {statement.id} has unknown value {statement.value_id}")
        if statement.actor_id is not None and statement.actor_id not in self.nodes:
            raise ValueError(f"Statement {statement.id} has unknown actor {statement.actor_id}")
        if statement.document_id is not None and statement.document_id not in self.nodes:
            raise ValueError(f"Statement {statement.id} has unknown document {statement.document_id}")
        existing = self.statements.get(statement.id)
        if existing is not None and existing != statement:
            raise ValueError(f"Conflicting statement definition for {statement.id}")
        self.statements[statement.id] = statement


class PredicateRegistry:
    def __init__(self, entries: Iterable[PredicateRegistryEntry]) -> None:
        entries_list = list(entries)
        self.entries = {entry.id: entry for entry in entries_list}
        if len(self.entries) != len(entries_list):
            raise ValueError("Duplicate predicate registry id")
        for entry in self.entries.values():
            expected_p177_target = not entry.derived
            if entry.p177_target != expected_p177_target:
                raise ValueError(
                    f"{entry.id}: p177_target must equal not derived within registry scope"
                )
            if entry.derived and entry.emit_shortcut:
                raise ValueError(f"{entry.id}: derived predicates cannot emit shortcuts")
            if not entry.p177_target and entry.emit_shortcut:
                raise ValueError(f"{entry.id}: non-P177 predicates cannot emit shortcuts")

    @classmethod
    def load(cls, path: Path = DEFAULT_REGISTRY_PATH) -> "PredicateRegistry":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(PredicateRegistryEntry(**entry) for entry in data)

    def require_p177_target(self, predicate_id: str) -> PredicateRegistryEntry:
        entry = self.entries.get(predicate_id)
        if entry is None:
            raise ValueError(f"Unregistered predicate {predicate_id}")
        if not entry.p177_target:
            raise ValueError(f"Predicate {predicate_id} is not permitted as a P177 target")
        return entry


def predicate_uri(predicate_id: str) -> str:
    prefix, local = predicate_id.split(":", 1)
    if prefix != "hapi":
        raise ValueError(f"Unsupported predicate namespace {prefix!r}")
    return f"{HAPI}{local}"


def source_document_node(source_id: str, citation: dict[str, Any]) -> AuthorityNode:
    doc_key = citation.get("book") or citation.get("edition") or source_id
    safe_key = str(doc_key).lower().replace(" ", "_").replace(".", "")
    return AuthorityNode(
        id=f"document:{source_id}:{safe_key}",
        classes=("E31_Document",),
        properties={"source_id": source_id, "citation": citation},
    )


def source_actor_node(source_id: str) -> AuthorityNode:
    return AuthorityNode(
        id=f"actor:{source_id}",
        classes=("E74_Group",),
        properties={"label": source_id},
    )


def leprohon_ruler_projection(row: dict[str, Any], registry: PredicateRegistry) -> ClaimGraph:
    """Project one Leprohon ruler row into the ADR-018 E13 pattern."""
    graph = ClaimGraph()
    source_id = "leprohon-2013-titulary"
    row_id = row["leprohon_id"]
    ruler_id = f"ruler:{source_id}:{row_id}"
    document = source_document_node(source_id, row["source_citation"])
    actor = source_actor_node(source_id)

    graph.add_node(document)
    graph.add_node(actor)
    graph.add_node(
        AuthorityNode(
            id=ruler_id,
            classes=("E21_Person",),
            properties={"source_id": source_id, "source_row_id": row_id},
        )
    )

    display_name_id = f"appellation:{source_id}:{row_id}:display"
    graph.add_node(
        AuthorityNode(
            id=display_name_id,
            classes=("E41_Appellation",),
            properties={"value": row["display_name"], "kind": "display_name"},
        )
    )
    graph.add_statement(
        Statement(
            id=f"statement:{source_id}:{row_id}:display_name",
            subject_id=ruler_id,
            predicate_id="hapi:display_name",
            value_id=display_name_id,
            actor_id=actor.id,
            document_id=document.id,
        ),
        registry,
    )

    if row.get("dynasty_number") is not None:
        dynasty_id = f"dynasty:{row['dynasty_number']}"
        graph.add_node(
            AuthorityNode(
                id=dynasty_id,
                classes=("E4_Period",),
                properties={
                    "number": row["dynasty_number"],
                    "label": row.get("dynasty_label"),
                },
            )
        )
        graph.add_statement(
            Statement(
                id=f"statement:{source_id}:{row_id}:in_dynastic_period",
                subject_id=ruler_id,
                predicate_id="hapi:in_dynastic_period",
                value_id=dynasty_id,
                actor_id=actor.id,
                document_id=document.id,
            ),
            registry,
        )

    for index, horus_name in enumerate(row.get("horus_names", []), start=1):
        horus_id = f"appellation:{source_id}:{row_id}:horus:{index}"
        graph.add_node(
            AuthorityNode(
                id=horus_id,
                classes=("E41_Appellation",),
                properties={
                    "kind": "horus_name",
                    "transliteration": horus_name.get("transliteration"),
                    "anglicised": horus_name.get("anglicised"),
                    "translation": horus_name.get("translation"),
                    "source_note": horus_name.get("source_note"),
                },
            )
        )
        graph.add_statement(
            Statement(
                id=f"statement:{source_id}:{row_id}:horus_name:{index}",
                subject_id=ruler_id,
                predicate_id="hapi:horus_name",
                value_id=horus_id,
                actor_id=actor.id,
                document_id=document.id,
            ),
            registry,
        )

    return graph


def strict_rdf_triples(graph: ClaimGraph, registry: PredicateRegistry) -> list[Triple]:
    """Emit the ADR-018 reification spine plus registered shortcut triples."""
    triples: list[Triple] = []
    for statement in graph.statements.values():
        statement_node = statement.id
        predicate_node = predicate_uri(statement.predicate_id)
        triples.extend(
            [
                Triple(statement_node, P140, statement.subject_id),
                Triple(statement_node, P141, statement.value_id),
                Triple(statement_node, P177, predicate_node),
            ]
        )
        if statement.actor_id is not None:
            triples.append(Triple(statement_node, P14, statement.actor_id))
        if statement.document_id is not None:
            triples.append(Triple(statement_node, P70I, statement.document_id))
        if registry.entries[statement.predicate_id].emit_shortcut:
            triples.append(Triple(statement.subject_id, predicate_node, statement.value_id))
    return triples
