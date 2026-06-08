"""Cannot-link constraints + guarded clustering (advisor P1/P2, ADR-020 guard).

Asserts the deterministic precision guards: regnal-numeral mismatch, disjoint
reign spans, same-source-distinct rows (with phase-sibling + documentary
exemptions), and that guarded clustering refuses the offending merges while
keeping legitimate phase splits together.
"""

from __future__ import annotations

from pipeline.authority.graph.ir import ClaimGraph, Edge, Node
from pipeline.authority.graph.matcher.constraints import (
    cannot_link,
    documentary_same_entity_pairs,
    regnal_number,
)
from pipeline.authority.graph.poc import guarded_same_entity_clusters


def _ruler(g, rid, name, *, source, source_id, reign=None):
    g.add_node(Node(rid, ("E21",), {"source": source, "source_id": source_id}, "Ruler"))
    g.add_node(Node(f"appellation::{rid}::display_name", ("E41",),
                    {"symbolic_content": name, "appellation_kind": "display_name"}, "Appellation"))
    if reign is not None:
        g.add_node(Node(f"timespan::{rid}::reign", ("E52",),
                        {"begin_of_the_begin": reign[0], "end_of_the_end": reign[1],
                         "calendar": "astronomical_year"}, "TimeSpan"))


def test_regnal_number_parsing():
    assert regnal_number("Osorkon II.") == 2
    assert regnal_number("Ramesses XI") == 11
    assert regnal_number("Iry-Hor") is None
    assert regnal_number("Iuput I") == 1


def test_regnal_mismatch_cannot_link():
    g = ClaimGraph()
    _ruler(g, "a", "Iuput I", source="leprohon", source_id="lep-23.01")
    _ruler(g, "b", "Iuput II", source="beckerath", source_id="bec-23.05")
    assert "regnal-number mismatch" in cannot_link(g, "a", "b")
    # Same numeral (or one missing) → not blocked on this rule.
    _ruler(g, "c", "Iuput I", source="kitchen", source_id="k-23.01")
    assert cannot_link(g, "a", "c") is None


def test_disjoint_reign_cannot_link():
    g = ClaimGraph()
    _ruler(g, "a", "Nebka", source="beckerath", source_id="b1", reign=(-2700, -2680))
    _ruler(g, "b", "Khasekhemwy", source="kitchen", source_id="k1", reign=(-2600, -2580))
    assert "disjoint reign spans" in cannot_link(g, "a", "b")
    # Overlapping spans → not blocked.
    _ruler(g, "c", "Nebka", source="kitchen", source_id="k2", reign=(-2705, -2690))
    assert cannot_link(g, "a", "c") is None


def test_same_source_distinct_rows_cannot_link():
    g = ClaimGraph()
    _ruler(g, "x", "Pinudjem I", source="kitchen", source_id="21H.03")
    _ruler(g, "y", "Menkheperre", source="kitchen", source_id="21H.05")
    assert "same-source" in cannot_link(g, "x", "y")


def test_phase_siblings_exempt():
    # Leprohon stage-suffix rows (same id stem) are the same person → not blocked.
    g = ClaimGraph()
    _ruler(g, "a", "Amenhotep IV (Regnal Years 1 to 5)", source="leprohon", source_id="leprohon-18.10a")
    _ruler(g, "b", "Akhenaten (Regnal Years 5 to 17)", source="leprohon", source_id="leprohon-18.10b")
    assert cannot_link(g, "a", "b") is None


def test_documentary_link_exempt():
    # Kitchen same_person_as (documentary same_entity_as) exempts same-source rows.
    g = ClaimGraph()
    _ruler(g, "p1", "Pinudjem I", source="kitchen", source_id="21H.03")
    _ruler(g, "p2", "Pinudjem I", source="kitchen", source_id="21H.04")
    g.add_node(Node("type::hapi:same_entity_as", ("E55",), {"id": "hapi:same_entity_as"}, "Type"))
    g.add_node(Node("person::kitchen_ka", ("E21",), {"full_name": "K. Kitchen"}, "Person"))
    g.add_node(Node("document::kitchen_1996", ("E31",), {"kind": "publication"}, "Document"))
    g.add_node(Node("stmt::doc", ("E13",), {}, "Statement"))
    g.add_edge(Edge("stmt::doc", "P140_assigned_attribute_to", "p1"))
    g.add_edge(Edge("stmt::doc", "P141_assigned", "p2"))
    g.add_edge(Edge("stmt::doc", "P177_assigned_property_of_type", "type::hapi:same_entity_as"))
    g.add_edge(Edge("stmt::doc", "P14_carried_out_by", "person::kitchen_ka"))
    g.add_edge(Edge("stmt::doc", "P70i_is_documented_in", "document::kitchen_1996"))
    doc_pairs = documentary_same_entity_pairs(g)
    assert doc_pairs == {frozenset(("p1", "p2"))}
    assert cannot_link(g, "p1", "p2", doc_pairs=doc_pairs) is None


def test_guarded_clustering_refuses_bad_same_source_merge():
    # A bad matcher edge would transitively merge two distinct same-source rows.
    g = ClaimGraph()
    _ruler(g, "lep::pin", "Pinudjem I", source="leprohon", source_id="lep-21.03")
    _ruler(g, "lep::menk", "Menkheperre", source="leprohon", source_id="lep-21.05")
    _ruler(g, "bec::pin", "Pinudjem I", source="beckerath", source_id="bec-21.03")
    # bec::pin correctly matches lep::pin; a BAD edge also links bec::pin to lep::menk.
    g.add_edge(Edge("lep::pin", "hapi:same_entity_as", "bec::pin"))
    g.add_edge(Edge("bec::pin", "hapi:same_entity_as", "lep::menk"))
    clusters, conflicts = guarded_same_entity_clusters(g)
    # The two Leprohon rows must NOT end up in one cluster.
    for c in clusters:
        assert not ({"lep::pin", "lep::menk"} <= c)
    assert any("same-source" in r for _, _, r in conflicts)


def test_guarded_clustering_keeps_phase_siblings_together():
    g = ClaimGraph()
    _ruler(g, "lep::a", "Amenhotep IV", source="leprohon", source_id="leprohon-18.10a")
    _ruler(g, "lep::b", "Akhenaten", source="leprohon", source_id="leprohon-18.10b")
    _ruler(g, "bec::akh", "Amenophis IV", source="beckerath", source_id="bec-18.10")
    g.add_edge(Edge("lep::a", "hapi:same_entity_as", "bec::akh"))
    g.add_edge(Edge("lep::b", "hapi:same_entity_as", "bec::akh"))
    clusters, conflicts = guarded_same_entity_clusters(g)
    assert len(clusters) == 1
    assert clusters[0] == frozenset({"lep::a", "lep::b", "bec::akh"})
    assert conflicts == []
