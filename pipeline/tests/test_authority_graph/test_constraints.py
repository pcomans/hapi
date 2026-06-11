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
from pipeline.authority.graph.poc import guarded_same_entity_clusters, resolve_matches


def _edge(g, a, b):
    g.add_edge(Edge(a, "hapi:same_entity_as", b))


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


def test_regnal_mismatch_escalates_not_blocks():
    # Regnal mismatch is NOT a hard cannot-link (sources may number a name
    # differently — Ahmose III = Amosis II); it routes to escalation.
    from pipeline.authority.graph.matcher.constraints import regnal_mismatch
    g = ClaimGraph()
    _ruler(g, "a", "Iuput I", source="leprohon", source_id="lep-23.01")
    _ruler(g, "b", "Iuput II", source="beckerath", source_id="bec-23.05")
    assert "regnal-number mismatch" in regnal_mismatch(g, "a", "b")
    assert cannot_link(g, "a", "b") is None  # regnal is no longer a hard block
    # Same numeral (or one missing) → no regnal conflict.
    _ruler(g, "c", "Iuput I", source="kitchen", source_id="k-23.01")
    assert regnal_mismatch(g, "a", "c") is None


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


# --- resolve_matches: escalation (precision-first, order-independent) ---------
def test_resolve_escalates_uniqueness_clash():
    # Two distinct Leprohon kings both claim one Beckerath king (the Nebre/Ninetjer
    # → Kaiëchós error). Both edges escalate; nothing auto-clusters.
    g = ClaimGraph()
    _ruler(g, "lep::nebre", "Nebre", source="leprohon", source_id="lep-2.02")
    _ruler(g, "lep::ninetjer", "Ninetjer", source="leprohon", source_id="lep-2.03")
    _ruler(g, "bec::kaiechos", "Kaiechos", source="beckerath", source_id="bec-2.02")
    _edge(g, "lep::nebre", "bec::kaiechos")
    _edge(g, "lep::ninetjer", "bec::kaiechos")
    clusters, esc = resolve_matches(g)
    assert clusters == []
    pairs = {frozenset((a, b)) for a, b, _ in esc}
    assert frozenset(("lep::nebre", "bec::kaiechos")) in pairs
    assert frozenset(("lep::ninetjer", "bec::kaiechos")) in pairs
    assert all("uniqueness" in r for _, _, r in esc)


def test_resolve_preserves_phase_split_many_to_one():
    # Two Leprohon phase rows (same id stem) → one Beckerath ruler is the SAME
    # person, so it must cluster, not escalate.
    g = ClaimGraph()
    _ruler(g, "lep::a", "Amenhotep IV", source="leprohon", source_id="leprohon-18.10a")
    _ruler(g, "lep::b", "Akhenaten", source="leprohon", source_id="leprohon-18.10b")
    _ruler(g, "bec::akh", "Amenophis IV", source="beckerath", source_id="bec-18.10")
    _edge(g, "lep::a", "bec::akh")
    _edge(g, "lep::b", "bec::akh")
    clusters, esc = resolve_matches(g)
    assert clusters == [frozenset({"lep::a", "lep::b", "bec::akh"})]
    assert esc == []


def test_resolve_escalates_regnal_mismatch():
    g = ClaimGraph()
    _ruler(g, "lep::iuput1", "Iuput I", source="leprohon", source_id="lep-23.01")
    _ruler(g, "bec::auput2", "Auput II", source="beckerath", source_id="bec-23.05")
    _edge(g, "lep::iuput1", "bec::auput2")
    clusters, esc = resolve_matches(g)
    assert clusters == []
    assert any("regnal" in r for _, _, r in esc)


def _triangle_graph():
    # A cross-source triangle: one Leprohon king edge-linked to a Beckerath AND a
    # Kitchen king, where the Beckerath and Kitchen kings are cannot-link (disjoint
    # reigns). The component is internally contradictory.
    g = ClaimGraph()
    _ruler(g, "lep::x", "Sobekhotep", source="leprohon", source_id="lep-13.10")
    _ruler(g, "bec::y", "Sobekhotep II", source="beckerath", source_id="bec-13.05",
           reign=(-1800, -1790))
    _ruler(g, "kit::z", "Sobekhotep", source="kitchen", source_id="kit-13.20",
           reign=(-1700, -1690))
    _edge(g, "lep::x", "bec::y")
    _edge(g, "lep::x", "kit::z")
    return g


def test_resolve_is_order_independent_for_contradictory_triangle():
    # Regression for the order-dependent _guarded_union bug: the cross-source
    # triangle must escalate the WHOLE component (both edges), identically under
    # every edge order — never order-dependently keep one edge and drop the other.
    import itertools

    results = []
    for order in itertools.permutations(["bec::y", "kit::z"]):
        g = ClaimGraph()
        _ruler(g, "lep::x", "Sobekhotep", source="leprohon", source_id="lep-13.10")
        _ruler(g, "bec::y", "Sobekhotep II", source="beckerath", source_id="bec-13.05",
               reign=(-1800, -1790))
        _ruler(g, "kit::z", "Sobekhotep", source="kitchen", source_id="kit-13.20",
               reign=(-1700, -1690))
        for other in order:
            _edge(g, "lep::x", other)
        clusters, esc = resolve_matches(g)
        results.append((clusters, {frozenset((a, b)) for a, b, _ in esc}))
    # Identical outcome regardless of edge order (Rule 2), and BOTH edges escalate.
    assert results[0] == results[1]
    assert results[0][0] == []  # no cluster from a contradictory component
    assert results[0][1] == {
        frozenset(("lep::x", "bec::y")), frozenset(("lep::x", "kit::z"))
    }


def test_sheshonq_iv_homonym_is_a_known_unguarded_collision():
    # Two DIFFERENT kings sharing name + numeral + (assigned) dynasty across
    # sources: the deterministic guards cannot separate them (documented KNOWN GAP
    # in the module docstring). This fixture pins that gap — a future prenomen
    # corroborator should flip cannot_link to a held-apart, at which point this
    # test is updated to assert the block.
    g = ClaimGraph()
    _ruler(g, "lep::sh4", "Sheshonq IV", source="leprohon", source_id="leprohon-22.10")
    _ruler(g, "bec::sh4", "Schoschenq IV.", source="beckerath", source_id="beckerath-22.14")
    # Same numeral → regnal_mismatch is silent; different sources, no reigns → the
    # hard guard is silent too. The collision is NOT auto-detectable today.
    from pipeline.authority.graph.matcher.constraints import regnal_mismatch
    assert regnal_mismatch(g, "lep::sh4", "bec::sh4") is None
    assert cannot_link(g, "lep::sh4", "bec::sh4") is None
