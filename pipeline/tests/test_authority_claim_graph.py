"""ADR-018 implementation spike tests."""

import json
from pathlib import Path

import pytest

from pipeline.authority.claim_graph import (
    P140,
    P141,
    P177,
    PredicateRegistry,
    Statement,
    leprohon_ruler_projection,
    predicate_uri,
    strict_rdf_triples,
)


AUTHORITY_ROOT = Path(__file__).parent.parent / "pipeline" / "authority"


def _first_leprohon_row() -> dict:
    path = AUTHORITY_ROOT / "sources" / "leprohon-2013-titulary" / "reconciled.jsonl"
    return json.loads(path.read_text(encoding="utf-8").splitlines()[0])


def test_predicate_registry_enforces_adr_018_p177_rules():
    registry = PredicateRegistry.load()

    assert registry.entries["hapi:display_name"].p177_target is True
    assert registry.entries["hapi:display_name"].emit_shortcut is True
    assert registry.entries["hapi:matcher_review_verdict"].p177_target is True
    assert registry.entries["hapi:matcher_review_verdict"].emit_shortcut is False
    assert registry.entries["hapi:shares_tomb_with"].derived is True
    assert registry.entries["hapi:shares_tomb_with"].p177_target is False

    with pytest.raises(ValueError, match="not permitted as a P177 target"):
        registry.require_p177_target("hapi:shares_tomb_with")


def test_leprohon_row_projects_to_per_source_nodes_and_e13_statements():
    registry = PredicateRegistry.load()
    graph = leprohon_ruler_projection(_first_leprohon_row(), registry)

    ruler_id = "ruler:leprohon-2013-titulary:leprohon-0.01"
    assert graph.nodes[ruler_id].classes == ("E21_Person",)
    assert graph.nodes[ruler_id].properties["source_row_id"] == "leprohon-0.01"

    predicates = {statement.predicate_id for statement in graph.statements.values()}
    assert predicates == {
        "hapi:display_name",
        "hapi:in_dynastic_period",
        "hapi:horus_name",
    }
    assert all(statement.actor_id for statement in graph.statements.values())
    assert all(statement.document_id for statement in graph.statements.values())


def test_strict_rdf_export_dual_emits_reification_and_shortcuts():
    registry = PredicateRegistry.load()
    graph = leprohon_ruler_projection(_first_leprohon_row(), registry)

    triples = strict_rdf_triples(graph, registry)
    triple_set = {(triple.subject, triple.predicate, triple.object) for triple in triples}

    display_statement = "statement:leprohon-2013-titulary:leprohon-0.01:display_name"
    display_value = "appellation:leprohon-2013-titulary:leprohon-0.01:display"
    ruler_id = "ruler:leprohon-2013-titulary:leprohon-0.01"
    display_predicate = predicate_uri("hapi:display_name")

    assert (display_statement, P140, ruler_id) in triple_set
    assert (display_statement, P141, display_value) in triple_set
    assert (display_statement, P177, display_predicate) in triple_set
    assert (ruler_id, display_predicate, display_value) in triple_set


def test_graph_rejects_unregistered_or_derived_statement_predicates():
    registry = PredicateRegistry.load()
    graph = leprohon_ruler_projection(_first_leprohon_row(), registry)
    existing_statement = next(iter(graph.statements.values()))

    with pytest.raises(ValueError, match="Unregistered predicate"):
        graph.add_statement(
            Statement(
                id="statement:test:bad",
                subject_id=existing_statement.subject_id,
                predicate_id="hapi:not_in_registry",
                value_id=existing_statement.value_id,
                actor_id=existing_statement.actor_id,
                document_id=existing_statement.document_id,
            ),
            registry,
        )

    with pytest.raises(ValueError, match="not permitted as a P177 target"):
        graph.add_statement(
            Statement(
                id="statement:test:derived",
                subject_id=existing_statement.subject_id,
                predicate_id="hapi:shares_tomb_with",
                value_id=existing_statement.subject_id,
                actor_id=existing_statement.actor_id,
                document_id=existing_statement.document_id,
            ),
            registry,
        )
