"""Reasoning (WHY) field + edge-persistence tests (ADR-020).

Reasoning is hard-capped at 1024 chars (soft target 256 set in the prompts) and
stored on the verdict-E13; matcher decisions persist to disk so a run is
disk-evaluable without re-spending tokens.
"""

from __future__ import annotations

import pytest

from pipeline.authority.graph.benchmark.persist import (
    dump_same_entity_edges,
    load_same_entity_edges,
)
from pipeline.authority.graph.ir import ClaimGraph, Node
from pipeline.authority.graph.loader import load_poc_graph
from pipeline.authority.graph.matcher.stage1_deterministic import run_stage1_matcher
from pipeline.authority.graph.verdicts import (
    REASONING_HARD_LIMIT,
    VERDICT_APPROVED,
    add_verdict,
    clamp_reasoning,
    tip_verdict,
)

UNAS = "stmt::match::leprohon::leprohon-5.09::beckerath::05.09"
TETI = "stmt::match::leprohon::leprohon-6.01::beckerath::06.01"


def test_clamp_short_reasoning_unchanged():
    assert clamp_reasoning("Both denote Unas, Dynasty 5.") == "Both denote Unas, Dynasty 5."
    assert clamp_reasoning(None) is None


def test_clamp_hard_limit():
    long = "x" * 5000
    out = clamp_reasoning(long)
    assert len(out) == REASONING_HARD_LIMIT
    assert out.endswith("…")


@pytest.fixture
def matched():
    g = load_poc_graph()
    run_stage1_matcher(g)
    g.add_node(Node("group::hapi_curatorial", ("E74",), {"name": "Hapi curatorial body"}, "Group"))
    g.add_node(Node("document::curator_2026_05", ("E31",),
                    {"kind": "curator_decision_batch", "decided_at": "2026-05-17"}, "Document"))
    return g


def test_reasoning_stored_on_verdict(matched):
    add_verdict(matched, matcher_stmt_id=UNAS, outcome=VERDICT_APPROVED,
                verdict_id="verdict::unas",
                curator_actor="group::hapi_curatorial",
                curator_document="document::curator_2026_05",
                reasoning="Identical name 'Unas', Dynasty 5 — same king.")
    tip = tip_verdict(matched, UNAS)
    assert matched.node(tip).props["reasoning"] == "Identical name 'Unas', Dynasty 5 — same king."


def test_reasoning_clamped_when_stored(matched):
    add_verdict(matched, matcher_stmt_id=UNAS, outcome=VERDICT_APPROVED,
                verdict_id="verdict::unas",
                curator_actor="group::hapi_curatorial",
                curator_document="document::curator_2026_05",
                reasoning="y" * 5000)
    tip = tip_verdict(matched, UNAS)
    assert len(matched.node(tip).props["reasoning"]) == REASONING_HARD_LIMIT


def test_dump_and_load_round_trip(matched):
    add_verdict(matched, matcher_stmt_id=UNAS, outcome=VERDICT_APPROVED,
                verdict_id="verdict::unas",
                curator_actor="group::hapi_curatorial",
                curator_document="document::curator_2026_05",
                reasoning="same king")
    records = dump_same_entity_edges(matched)
    unas_rec = [r for r in records if r["claim"] == UNAS]
    assert len(unas_rec) == 1
    assert unas_rec[0]["outcome"] == VERDICT_APPROVED
    assert unas_rec[0]["reasoning"] == "same king"
    # Teti has no verdict → pending (outcome None) → not loaded as an edge.
    teti_rec = [r for r in records if r["claim"] == TETI][0]
    assert teti_rec["outcome"] is None

    # Reload approved edges into a fresh graph (disk-evaluable, no API).
    g2 = load_poc_graph()
    n = load_same_entity_edges(g2, records)
    assert n == 1  # only the approved Unas link
    assert any(
        e.predicate == "hapi:same_entity_as"
        and e.subject_id == "leprohon::leprohon-5.09"
        for e in g2.edges_with_predicate("hapi:same_entity_as")
    )
