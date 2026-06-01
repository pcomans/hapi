"""Storage-neutral ADR-018 claim graph prototype.

ADR-018 deliberately defers the storage decision. This module sketches the
loader boundary that both Postgres and Neo4j implementations can share:
source rows become per-source entity nodes plus E13 statement nodes, and
shortcut triples are emitted only through the predicate registry.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


AUTHORITY_ROOT = Path(__file__).parent
DEFAULT_REGISTRY_PATH = AUTHORITY_ROOT / "predicate_registry.json"
DEFAULT_SOURCES_ROOT = AUTHORITY_ROOT / "sources"
DEFAULT_DUMP_PATH = AUTHORITY_ROOT / "build" / "claim_graph.json"

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

    def merge(self, other: "ClaimGraph", registry: "PredicateRegistry") -> None:
        for node in other.nodes.values():
            self.add_node(node)
        for statement in other.statements.values():
            self.add_statement(statement, registry)

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
    safe_key = slugify(str(doc_key))
    return AuthorityNode(
        id=f"document:{source_id}:{safe_key}",
        classes=("E31_Document",),
        properties={
            "source_id": source_id,
            "label": doc_key,
            "book": citation.get("book"),
            "edition": citation.get("edition"),
        },
    )


def source_actor_node(source_id: str) -> AuthorityNode:
    return AuthorityNode(
        id=f"actor:{source_id}",
        classes=("E74_Group",),
        properties={"label": source_id},
    )


def slugify(value: Any) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "unknown"


def row_identifier(source_id: str, row: dict[str, Any], index: int) -> str:
    for key in (
        "leprohon_id",
        "beckerath_id",
        "ryholt_id",
        "kitchen_id",
        "baud_id",
        "dh_id",
        "slug",
        "id",
        "tomb_id",
    ):
        if row.get(key) is not None:
            return f"{slugify(row[key])}-{index:05d}"
    return f"row-{index:05d}"


def row_entity_kind(row: dict[str, Any]) -> tuple[str, str]:
    if row.get("kind") == "period" or row.get("period_name"):
        return "period", "E4_Period"
    if row.get("kind") == "dynasty" or (
        row.get("number") is not None and row.get("label", "").startswith("Dyn.")
    ):
        return "dynasty", "E4_Period"
    if row.get("kind") == "site" or row.get("tomb_id"):
        return "site", "E27_Site"
    return "ruler", "E21_Person"


def display_value(row: dict[str, Any]) -> str | None:
    for key in (
        "display_name",
        "display",
        "name",
        "name_anglicised",
        "occupant_name",
        "period_name",
        "label",
        "tomb_id",
    ):
        value = row.get(key)
        if value:
            return str(value)
    return None


def dynasty_value(row: dict[str, Any]) -> Any | None:
    for key in ("dynasty_number", "dynasty"):
        value = row.get(key)
        if value is not None:
            return value
    label = row.get("dynasty_label")
    if isinstance(label, str):
        match = re.search(r"\d+", label)
        if match:
            return int(match.group(0))
    return None


def date_bounds(row: dict[str, Any]) -> tuple[Any | None, Any | None]:
    start_keys = ("start_year", "start_bce", "start_bce_low", "date_bce_start")
    end_keys = ("end_year", "end_bce", "end_bce_high", "date_bce_end")
    start = next((row[key] for key in start_keys if row.get(key) is not None), None)
    end = next((row[key] for key in end_keys if row.get(key) is not None), None)
    return start, end


def add_statement_value(
    graph: ClaimGraph,
    registry: PredicateRegistry,
    *,
    source_id: str,
    row_id: str,
    subject_id: str,
    predicate_id: str,
    value_node: AuthorityNode,
    actor_id: str,
    document_id: str,
    suffix: str,
    citation: dict[str, Any],
) -> None:
    graph.add_node(value_node)
    graph.add_statement(
        Statement(
            id=f"statement:{source_id}:{row_id}:{suffix}",
            subject_id=subject_id,
            predicate_id=predicate_id,
            value_id=value_node.id,
            actor_id=actor_id,
            document_id=document_id,
            properties={"source_citation": citation},
        ),
        registry,
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


def project_authority_row(
    source_id: str,
    row: dict[str, Any],
    index: int,
    registry: PredicateRegistry,
) -> ClaimGraph:
    graph = ClaimGraph()
    row_id = row_identifier(source_id, row, index)
    citation = row.get("source_citation") or {"source": source_id}
    document = source_document_node(source_id, citation)
    actor = source_actor_node(source_id)
    entity_kind, entity_class = row_entity_kind(row)
    entity_id = f"{entity_kind}:{source_id}:{row_id}"

    graph.add_node(document)
    graph.add_node(actor)
    graph.add_node(
        AuthorityNode(
            id=entity_id,
            classes=(entity_class,),
            properties={
                "source_id": source_id,
                "source_row_id": row_id,
                "source_index": index,
                "entity_kind": entity_kind,
                "raw_row": row,
            },
        )
    )

    name = display_value(row)
    if entity_class == "E21_Person" and name:
        add_statement_value(
            graph,
            registry,
            source_id=source_id,
            row_id=row_id,
            subject_id=entity_id,
            predicate_id="hapi:display_name",
            value_node=AuthorityNode(
                id=f"appellation:{source_id}:{row_id}:display",
                classes=("E41_Appellation",),
                properties={"value": name, "kind": "display_name"},
            ),
            actor_id=actor.id,
            document_id=document.id,
            suffix="display-name",
            citation=citation,
        )

    dynasty = dynasty_value(row)
    if entity_class == "E21_Person" and dynasty is not None:
        dynasty_key = slugify(dynasty)
        add_statement_value(
            graph,
            registry,
            source_id=source_id,
            row_id=row_id,
            subject_id=entity_id,
            predicate_id="hapi:in_dynastic_period",
            value_node=AuthorityNode(
                id=f"dynasty:{dynasty_key}",
                classes=("E4_Period",),
                properties={"number_or_label": dynasty_key},
            ),
            actor_id=actor.id,
            document_id=document.id,
            suffix="in-dynastic-period",
            citation=citation,
        )

    start, end = date_bounds(row)
    if entity_class == "E21_Person" and (start is not None or end is not None):
        add_statement_value(
            graph,
            registry,
            source_id=source_id,
            row_id=row_id,
            subject_id=entity_id,
            predicate_id="hapi:reign_period",
            value_node=AuthorityNode(
                id=f"timespan:{source_id}:{row_id}:reign",
                classes=("E52_Time-Span",),
                properties={"start_bce": start, "end_bce": end},
            ),
            actor_id=actor.id,
            document_id=document.id,
            suffix="reign-period",
            citation=citation,
        )

    for name_index, horus_name in enumerate(row.get("horus_names") or [], start=1):
        if isinstance(horus_name, str):
            horus_props = {"value": horus_name, "kind": "horus_name"}
        else:
            horus_props = {"kind": "horus_name", **horus_name}
        add_statement_value(
            graph,
            registry,
            source_id=source_id,
            row_id=row_id,
            subject_id=entity_id,
            predicate_id="hapi:horus_name",
            value_node=AuthorityNode(
                id=f"appellation:{source_id}:{row_id}:horus:{name_index}",
                classes=("E41_Appellation",),
                properties=horus_props,
            ),
            actor_id=actor.id,
            document_id=document.id,
            suffix=f"horus-name-{name_index}",
            citation=citation,
        )

    if row.get("tomb_id") and row.get("occupant_name"):
        tomb_id = entity_id
        occupant_id = f"ruler:{source_id}:{row_id}:occupant"
        graph.add_node(
            AuthorityNode(
                id=occupant_id,
                classes=("E21_Person",),
                properties={
                    "source_id": source_id,
                    "source_row_id": row_id,
                    "value": row["occupant_name"],
                    "raw_row": row,
                },
            )
        )
        add_statement_value(
            graph,
            registry,
            source_id=source_id,
            row_id=row_id,
            subject_id=occupant_id,
            predicate_id="hapi:display_name",
            value_node=AuthorityNode(
                id=f"appellation:{source_id}:{row_id}:occupant-display",
                classes=("E41_Appellation",),
                properties={"value": row["occupant_name"], "kind": "display_name"},
            ),
            actor_id=actor.id,
            document_id=document.id,
            suffix="occupant-display-name",
            citation=citation,
        )
        graph.add_statement(
            Statement(
                id=f"statement:{source_id}:{row_id}:original-burial-in",
                subject_id=occupant_id,
                predicate_id="hapi:original_burial_in",
                value_id=tomb_id,
                actor_id=actor.id,
                document_id=document.id,
                properties={"source_citation": citation},
            ),
            registry,
        )

    return graph


def build_authority_graph(
    sources_root: Path = DEFAULT_SOURCES_ROOT,
    registry: PredicateRegistry | None = None,
) -> ClaimGraph:
    registry = registry or PredicateRegistry.load()
    graph = ClaimGraph()
    for source_path in sorted(sources_root.glob("*/reconciled.jsonl")):
        source_id = source_path.parent.name
        with source_path.open(encoding="utf-8") as file:
            for index, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                graph.merge(project_authority_row(source_id, row, index, registry), registry)
    return graph


def graph_dump(graph: ClaimGraph, registry: PredicateRegistry) -> dict[str, Any]:
    triples = strict_rdf_triples(graph, registry)
    return {
        "metadata": {
            "node_count": len(graph.nodes),
            "statement_count": len(graph.statements),
            "triple_count": len(triples),
            "predicate_registry_count": len(registry.entries),
        },
        "predicate_registry": [asdict(entry) for entry in registry.entries.values()],
        "nodes": [asdict(graph.nodes[node_id]) for node_id in sorted(graph.nodes)],
        "statements": [
            asdict(graph.statements[statement_id]) for statement_id in sorted(graph.statements)
        ],
        "triples": [
            asdict(triple)
            for triple in sorted(triples, key=lambda t: (t.subject, t.predicate, t.object))
        ],
    }


def write_authority_graph(
    path: Path = DEFAULT_DUMP_PATH,
    sources_root: Path = DEFAULT_SOURCES_ROOT,
    registry: PredicateRegistry | None = None,
) -> dict[str, Any]:
    registry = registry or PredicateRegistry.load()
    graph = build_authority_graph(sources_root=sources_root, registry=registry)
    dump = graph_dump(graph, registry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dump, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return dump


def main() -> None:
    dump = write_authority_graph()
    print(
        "Wrote authority graph: "
        f"{dump['metadata']['node_count']} nodes, "
        f"{dump['metadata']['statement_count']} statements, "
        f"{dump['metadata']['triple_count']} triples"
    )


if __name__ == "__main__":
    main()
