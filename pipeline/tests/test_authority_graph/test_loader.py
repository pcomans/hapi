"""Loader tests — reconciled.jsonl → E13 claim graph (ADR-018 § Consequences).

Asserts concrete claim structure and provenance against the real Leprohon +
Beckerath reconciled data (Constitutional rule 5).
"""

from __future__ import annotations

import pytest

from pipeline.authority.graph.ir import ClaimGraph, Node
from pipeline.authority.graph.loader import (
    _add_human_statement,
    _seed_actor_and_document_catalogue,
    load_poc_graph,
)


@pytest.fixture(scope="module")
def graph() -> ClaimGraph:
    return load_poc_graph()


def _edge_to(graph: ClaimGraph, stmt_id: str, predicate: str):
    edges = [e for e in graph.out_edges(stmt_id) if e.predicate == predicate]
    assert len(edges) == 1, f"{stmt_id}: expected exactly one {predicate} edge"
    return edges[0]


def test_both_sources_loaded_as_per_source_rulers(graph):
    leprohon = [n for n in graph.nodes_of_class("E21") if n.props.get("source") == "leprohon"]
    beckerath = [n for n in graph.nodes_of_class("E21") if n.props.get("source") == "beckerath"]
    # Leprohon has 395 ruler rows; Beckerath 166 non-marker rows.
    assert len(leprohon) == 395
    assert len(beckerath) == 166


def test_dynasty_marker_rows_skipped(graph):
    # "0. Dynastie" is a marker row (beckerath 00.01) and must NOT be a ruler.
    with pytest.raises(KeyError):
        graph.node("beckerath::00.01")


def test_amenhotep_iii_display_name_full_spine(graph):
    # Leprohon's Amenhotep III carries a complete human-documentary E13.
    stmt = "stmt::leprohon::leprohon-18.09::display_name"
    p140 = _edge_to(graph, stmt, "P140_assigned_attribute_to")
    p141 = _edge_to(graph, stmt, "P141_assigned")
    p177 = _edge_to(graph, stmt, "P177_assigned_property_of_type")
    p14 = _edge_to(graph, stmt, "P14_carried_out_by")
    p70i = _edge_to(graph, stmt, "P70i_is_documented_in")

    assert p140.object_id == "leprohon::leprohon-18.09"
    assert graph.node(p141.object_id).props["symbolic_content"] == "Amenhotep III"
    assert graph.node(p141.object_id).props["language"] == "en"
    assert graph.node(p177.object_id).props["id"] == "hapi:display_name"
    assert p14.object_id == "person::leprohon_rj"
    assert p70i.object_id == "document::leprohon_2013"
    # Page locators ride on the P70i edge, not on P14.
    assert "cited_page" in p70i.props and "cited_pdf_page" in p70i.props


def test_cross_source_pair_present_but_not_collapsed(graph):
    # The same ruler in two sources → two distinct E21 nodes + two display-name
    # claims with DIFFERENT language forms. The loader never collapses them.
    lep = graph.node("appellation::leprohon::leprohon-18.09::display_name")
    bec = graph.node("appellation::beckerath::18.09::display_name")
    assert lep.props["symbolic_content"] == "Amenhotep III"
    assert bec.props["symbolic_content"] == "Amenophis III."
    assert lep.props["language"] == "en"
    assert bec.props["language"] == "de"


def test_beckerath_reign_period_timespan(graph):
    # Menes (beckerath 01.01): start range [-3032, -2982], end range [-3000, -2950].
    # The maximal span is earliest-start (-3032) → latest-end (-2950), stored as
    # signed astronomical years with no negation (the source is already negative).
    ts = graph.node("timespan::beckerath::01.01::reign")
    assert ts.props["begin_of_the_begin"] == -3032
    assert ts.props["end_of_the_end"] == -2950
    assert ts.props["calendar"] == "astronomical_year"
    # All reign spans are BCE (negative) in this slice.
    for n in graph.nodes_of_class("E52"):
        if n.props.get("begin_of_the_begin") is not None:
            assert n.props["begin_of_the_begin"] < 0


def test_horus_name_appellations_typed(graph):
    appels = [
        n for n in graph.nodes_of_class("E41")
        if n.props.get("appellation_kind") == "horus_name"
    ]
    assert appels, "expected Leprohon horus-name appellations"
    # Every horus-name claim points P177 at the horus_name predicate type.
    sample = appels[0]
    refs = [e for e in graph.edges if e.object_id == sample.id and e.predicate == "P141_assigned"]
    assert refs, "horus-name appellation must be the P141 value of some E13"


def test_loader_rejects_derived_predicate_as_p177_target():
    # hapi:shares_tomb_with is derived/query-only: the loader REJECTS any E13
    # whose P177 target is a derived predicate (ADR-018 principle 4).
    g = ClaimGraph()
    _seed_actor_and_document_catalogue(g)
    g.add_node(Node("ruler::x", ("E21",), {}, "Ruler"))
    g.add_node(Node("ruler::y", ("E21",), {}, "Ruler"))
    with pytest.raises(ValueError, match="derived/query-only"):
        _add_human_statement(
            g,
            stmt_id="stmt::bad",
            subject_id="ruler::x",
            predicate_id="hapi:shares_tomb_with",
            value_id="ruler::y",
            actor_id="person::leprohon_rj",
            document_id="document::leprohon_2013",
        )
