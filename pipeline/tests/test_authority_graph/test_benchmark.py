"""Wikidata benchmark tests (ADR-020 Tier-1 silver standard).

align() is deterministic against the committed wikidata_pharaohs.json snapshot.
evaluate() is checked on a small synthetic graph so precision/recall/B-cubed and
the false-merge detection are asserted on known values (rule 5).
"""

from __future__ import annotations

from pipeline.authority.graph.benchmark.evaluate import evaluate
from pipeline.authority.graph.benchmark.wikidata import align
from pipeline.authority.graph.ir import ClaimGraph, Edge, Node


# --- alignment against Wikidata's own aliases (committed snapshot) ----------
def test_cross_language_aligns_to_same_qid():
    assert align("Amenhotep III")[0] == align("Amenophis III.")[0] == "Q42606"
    assert align("Tutankhamun")[0] == align("Tut-anch-amun")[0] == "Q12154"


def test_distinct_people_have_distinct_qids():
    # The false-merge case: Pinudjem I and Menkheperre are different QIDs.
    pin, _ = align("Pinudjem I")
    menk, _ = align("Menkheperre")
    assert pin and menk and pin != menk


def test_parenthetical_phase_row_strips_to_match():
    # Leprohon phase rows align via the parenthetical-stripped fallback.
    qid, status = align("Akhenaten (Regnal Years 5 to 17)")
    assert status == "matched" and qid is not None


# --- metrics on a synthetic graph ------------------------------------------
def _ruler(g, rid, name):
    g.add_node(Node(rid, ("E21",), {"source": "x"}, "Ruler"))
    g.add_node(Node(f"appellation::{rid}::display_name", ("E41",),
                    {"symbolic_content": name, "appellation_kind": "display_name"}, "Appellation"))


def test_perfect_match_scores_one():
    g = ClaimGraph()
    _ruler(g, "r::a", "Amenhotep III")   # Q42606
    _ruler(g, "r::b", "Amenophis III.")  # Q42606
    _ruler(g, "r::c", "Tutankhamun")     # Q12154
    g.add_edge(Edge("r::a", "hapi:same_entity_as", "r::b"))  # correct merge
    res = evaluate(g)
    assert res["aligned"] == 3
    assert res["pairwise"] == {"tp": 1, "fp": 0, "fn": 0,
                               "precision": 1.0, "recall": 1.0, "f1": 1.0}


def test_false_merge_is_caught_as_fp():
    g = ClaimGraph()
    _ruler(g, "r::a", "Amenhotep III")   # Q42606
    _ruler(g, "r::c", "Tutankhamun")     # Q12154 — different person
    g.add_edge(Edge("r::a", "hapi:same_entity_as", "r::c"))  # WRONG merge
    res = evaluate(g)
    assert res["pairwise"]["fp"] == 1
    assert res["pairwise"]["precision"] == 0.0
    assert ["Amenhotep III", "Tutankhamun"] in res["false_merges"]


def test_missed_match_is_caught_as_fn():
    g = ClaimGraph()
    _ruler(g, "r::a", "Amenhotep III")   # Q42606
    _ruler(g, "r::b", "Amenophis III.")  # Q42606 — same person, not linked
    res = evaluate(g)  # no same_entity edge
    assert res["pairwise"]["fn"] == 1
    assert res["pairwise"]["recall"] == 0.0
