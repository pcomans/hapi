"""Neo4j adapter: write the graph + run a constraint-narrowing Cypher query.

Skips automatically when Neo4j is not reachable.
"""

from __future__ import annotations

import pytest

from pipeline.authority.graph.adapters import neo4j_adapter as neo
from pipeline.authority.graph.ir import ClaimGraph, Node
from pipeline.authority.graph.loader import load_poc_graph
from pipeline.authority.graph.matcher.stage1_deterministic import run_stage1_matcher
from pipeline.authority.graph.verdicts import VERDICT_APPROVED, add_verdict, emit_shortcuts

UNAS_MATCH = "stmt::match::leprohon::leprohon-5.09::beckerath::05.09"


def _full_graph() -> ClaimGraph:
    g = load_poc_graph()
    run_stage1_matcher(g)
    g.add_node(Node("group::hapi_curatorial", ("E74",), {"name": "Hapi curatorial body"}, "Group"))
    g.add_node(Node("document::curator_2026_05", ("E31",),
                    {"kind": "curator_decision_batch", "decided_at": "2026-05-17"}, "Document"))
    add_verdict(g, matcher_stmt_id=UNAS_MATCH, outcome=VERDICT_APPROVED,
                verdict_id="verdict::unas::1",
                curator_actor="group::hapi_curatorial",
                curator_document="document::curator_2026_05")
    emit_shortcuts(g)
    return g


@pytest.fixture(scope="module")
def driver():
    try:
        drv = neo.get_driver()
        drv.verify_connectivity()
    except Exception as exc:  # noqa: BLE001 - any connectivity failure → skip
        pytest.skip(f"Neo4j not reachable: {exc}")
        return
    yield drv
    drv.close()


@pytest.fixture(scope="module")
def loaded(driver):
    counts = neo.write_graph(driver, _full_graph())
    return driver, counts


def test_rel_type_sanitization():
    assert neo._rel_type("hapi:same_entity_as") == "HAPI_SAME_ENTITY_AS"
    assert neo._rel_type("P140_assigned_attribute_to") == "P140_ASSIGNED_ATTRIBUTE_TO"


def test_write_graph_counts(loaded):
    _, counts = loaded
    assert counts["nodes"] == 3358
    assert counts["rels"] == 9942


def test_constraint_narrowing_dynasty_18(loaded):
    driver, _ = loaded
    ids = neo.rulers_in_dynasty(driver, 18)
    # Both sources' Dynasty-18 rulers are present, not collapsed.
    assert "leprohon::leprohon-18.09" in ids   # Amenhotep III (Leprohon)
    assert "beckerath::18.09" in ids           # Amenophis III. (Beckerath)
    # Every returned id is a Dynasty-18 ruler from one of the two sources.
    assert all(i.startswith(("leprohon::", "beckerath::")) for i in ids)


def test_approved_same_entity_shortcut_traversable(loaded):
    driver, _ = loaded
    with driver.session() as session:
        rec = session.run(
            "MATCH (a:E21 {_nid:'leprohon::leprohon-5.09'})"
            "-[e:HAPI_SAME_ENTITY_AS]->(b:E21 {_nid:'beckerath::05.09'}) "
            "RETURN e.predicate AS p"
        ).single()
    assert rec is not None
    assert rec["p"] == "hapi:same_entity_as"
