"""3-way same_entity_as clustering tests (Leprohon + Beckerath + Kitchen).

Demonstrates cross-source identity as data: a ruler attested in all three sources
forms a 3-source cluster over approved same_entity_as edges — built with the
exact (stage-1) matcher only, no API. Asserts concrete values (rule 5).
"""

from __future__ import annotations

import pytest

from pipeline.authority.graph.loader import load_kitchen, load_poc_graph_3way
from pipeline.authority.graph.poc import build_3way_graph, same_entity_clusters


def test_kitchen_loads_with_claims():
    g = load_poc_graph_3way()
    kitchen = [n for n in g.nodes_of_class("E21") if n.props.get("source") == "kitchen"]
    assert len(kitchen) == 60
    # Ramesses XI (kitchen 20.01): display name + dynasty + reign span.
    assert g.node("appellation::kitchen::20.01::display_name").props["symbolic_content"] == "Ramesses XI"
    ts = g.node("timespan::kitchen::20.01::reign")
    # end_bce -1069, length 29 → begin -1098.
    assert ts.props["end_of_the_end"] == -1069
    assert ts.props["begin_of_the_begin"] == -1098


def test_kitchen_provenance_is_kitchen_not_other_source():
    g = load_poc_graph_3way()
    stmt = "stmt::kitchen::20.01::display_name"
    p14 = [e for e in g.out_edges(stmt) if e.predicate == "P14_carried_out_by"][0]
    p70i = [e for e in g.out_edges(stmt) if e.predicate == "P70i_is_documented_in"][0]
    assert p14.object_id == "person::kitchen_ka"
    assert p70i.object_id == "document::kitchen_1996"


@pytest.fixture(scope="module")
def threeway_graph():
    return build_3way_graph()


def test_osorkon_i_forms_a_three_source_cluster(threeway_graph):
    clusters = same_entity_clusters(threeway_graph)
    osorkon_i = [c for c in clusters if "kitchen::22.02" in c]
    assert len(osorkon_i) == 1
    assert osorkon_i[0] == frozenset(
        {"kitchen::22.02", "leprohon::leprohon-22.02", "beckerath::22.02"}
    )


def test_clusters_span_three_sources(threeway_graph):
    clusters = same_entity_clusters(threeway_graph)
    threeway = [c for c in clusters if len({m.split("::")[0] for m in c}) == 3]
    # Osorkon I and Osorkon II are clean exact-match 3-source clusters.
    assert len(threeway) >= 2
    names = {
        frozenset(m.split("::")[0] for m in c) for c in threeway
    }
    assert names == {frozenset({"leprohon", "beckerath", "kitchen"})}


def test_load_poc_graph_unchanged_without_kitchen():
    # The 2-source build must be unaffected (existing tests rely on 563).
    from pipeline.authority.graph.loader import load_poc_graph
    g = load_poc_graph()
    assert len([n for n in g.nodes_of_class("E21") if n.props.get("source") == "kitchen"]) == 0
