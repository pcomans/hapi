"""Strict-RDF adapter: lossless round-trip + strict-CIDOC-triple conformance.

The round-trip IR → RDF → IR being equal is the proof that the property-graph
inlining conventions are lossless (ADR-018 § encoding conventions). The strict
triple assertions confirm the export is genuine CIDOC/CRMdig syntax.
"""

from __future__ import annotations

import pytest
from rdflib import RDF, Literal, URIRef

from pipeline.authority.graph.adapters import rdf_adapter as rx
from pipeline.authority.graph.ir import ClaimGraph
from pipeline.authority.graph.loader import load_poc_graph
from pipeline.authority.graph.matcher.stage1_deterministic import run_stage1_matcher
from pipeline.authority.graph.verdicts import (
    VERDICT_APPROVED,
    add_verdict,
    emit_shortcuts,
)
from pipeline.authority.graph.ir import Node

UNAS_MATCH = "stmt::match::leprohon::leprohon-5.09::beckerath::05.09"


def _full_graph() -> ClaimGraph:
    g = load_poc_graph()
    run_stage1_matcher(g)
    g.add_node(Node("group::hapi_curatorial", ("E74",), {"name": "Hapi curatorial body"}, "Group"))
    g.add_node(
        Node("document::curator_2026_05", ("E31",),
             {"kind": "curator_decision_batch", "decided_at": "2026-05-17"}, "Document")
    )
    add_verdict(
        g,
        matcher_stmt_id=UNAS_MATCH,
        outcome=VERDICT_APPROVED,
        verdict_id="verdict::unas::1",
        curator_actor="group::hapi_curatorial",
        curator_document="document::curator_2026_05",
    )
    emit_shortcuts(g)
    return g


def _normalize(g: ClaimGraph):
    nodes = {
        n.id: (frozenset(n.crm_classes), tuple(sorted(n.props.items(), key=lambda kv: kv[0])), n.hapi_label)
        for n in g.nodes
    }
    edges = sorted(
        (e.subject_id, e.predicate, e.object_id, tuple(sorted(e.props.items())))
        for e in g.edges
    )
    return nodes, edges


@pytest.fixture(scope="module")
def full_graph():
    return _full_graph()


def test_round_trip_is_lossless(full_graph):
    rdf = rx.to_rdf(full_graph)
    back = rx.from_rdf(rdf)
    src_nodes, src_edges = _normalize(full_graph)
    rt_nodes, rt_edges = _normalize(back)
    assert rt_nodes == src_nodes
    assert rt_edges == src_edges


def test_round_trip_preserves_counts(full_graph):
    back = rx.from_rdf(rx.to_rdf(full_graph))
    assert len(back.nodes) == len(full_graph.nodes)
    assert len(back.edges) == len(full_graph.edges)


def test_strict_crm_p190_for_appellation(full_graph):
    rdf = rx.to_rdf(full_graph)
    appel = rx._node_uri("appellation::leprohon::leprohon-18.09::display_name")
    p190 = URIRef("http://www.cidoc-crm.org/cidoc-crm/P190_has_symbolic_content")
    assert (appel, p190, Literal("Amenhotep III")) in rdf


def test_strict_crm_timespan_p82a_is_integer(full_graph):
    rdf = rx.to_rdf(full_graph)
    ts = rx._node_uri("timespan::beckerath::01.01::reign")
    p82a = URIRef("http://www.cidoc-crm.org/cidoc-crm/P82a_begin_of_the_begin")
    vals = list(rdf.objects(ts, p82a))
    assert vals == [Literal(-3032)]
    assert vals[0].toPython() == -3032


def test_statement_typed_as_crm_e13(full_graph):
    rdf = rx.to_rdf(full_graph)
    stmt = rx._node_uri("stmt::leprohon::leprohon-18.09::display_name")
    e13 = URIRef("http://www.cidoc-crm.org/cidoc-crm/E13_Attribute_Assignment")
    assert (stmt, RDF.type, e13) in rdf


def test_same_entity_shortcut_uses_hapi_predicate_uri(full_graph):
    # After approval, the gated shortcut is a direct hapi:same_entity_as triple
    # — exactly what an RDFS reasoner rewrites to crmdig:L54_is_same_as.
    rdf = rx.to_rdf(full_graph)
    subj = rx._node_uri("leprohon::leprohon-5.09")
    obj = rx._node_uri("beckerath::05.09")
    pred = URIRef("https://pcomans.github.io/hapi-crm#same_entity_as")
    assert (subj, pred, obj) in rdf


def test_p70i_page_locators_round_trip_via_reification(full_graph):
    # Edge-level cited_page/cited_pdf_page survive the round-trip.
    back = rx.from_rdf(rx.to_rdf(full_graph))
    stmt = "stmt::leprohon::leprohon-18.09::display_name"
    p70i = [e for e in back.out_edges(stmt) if e.predicate == "P70i_is_documented_in"]
    assert len(p70i) == 1
    assert p70i[0].props.get("cited_page") == 102
    assert p70i[0].props.get("cited_pdf_page") == 123
