"""Verdict-chain + shortcut-emission tests (ADR-018 schema 4b, §Shortcut emission).

Covers the three chain-integrity constraints (fork / multi-root / mid-chain),
the verdict-gated shortcut emission for matcher claims, and the unconditional
shortcut emission for human-documentary claims.
"""

from __future__ import annotations

import pytest

from pipeline.authority.graph.ir import ClaimGraph, Node
from pipeline.authority.graph.loader import load_poc_graph
from pipeline.authority.graph.matcher.stage1_deterministic import run_stage1_matcher
from pipeline.authority.graph.verdicts import (
    VERDICT_APPROVED,
    VERDICT_REJECTED,
    VERDICT_RETRACTED,
    VerdictError,
    add_verdict,
    emit_shortcuts,
    tip_verdict,
    verdict_outcome,
)

UNAS_MATCH = "stmt::match::leprohon::leprohon-5.09::beckerath::05.09"


def _curator_seed(g: ClaimGraph) -> None:
    g.add_node(Node("group::hapi_curatorial", ("E74",), {"name": "Hapi curatorial body"}, "Group"))
    g.add_node(
        Node(
            "document::curator_2026_05",
            ("E31",),
            {"kind": "curator_decision_batch", "decided_at": "2026-05-17"},
            "Document",
        )
    )


@pytest.fixture
def matched():
    g = load_poc_graph()
    run_stage1_matcher(g)
    _curator_seed(g)
    return g


def _approve(g, verdict_id="verdict::unas::1", supersedes=None):
    return add_verdict(
        g,
        matcher_stmt_id=UNAS_MATCH,
        outcome=VERDICT_APPROVED,
        verdict_id=verdict_id,
        curator_actor="group::hapi_curatorial",
        curator_document="document::curator_2026_05",
        supersedes=supersedes,
    )


# -- gating ----------------------------------------------------------------
def test_no_verdict_means_no_same_entity_shortcut(matched):
    added = emit_shortcuts(matched)
    same_entity = [e for e in added if e.predicate == "hapi:same_entity_as"]
    assert same_entity == []  # candidate has no verdict → gated out


def test_approved_tip_emits_same_entity_shortcut(matched):
    _approve(matched)
    assert verdict_outcome(matched, tip_verdict(matched, UNAS_MATCH)) == VERDICT_APPROVED
    added = emit_shortcuts(matched)
    shortcut = [
        e for e in added
        if e.predicate == "hapi:same_entity_as"
        and e.subject_id == "leprohon::leprohon-5.09"
        and e.object_id == "beckerath::05.09"
    ]
    assert len(shortcut) == 1


def test_rejected_tip_does_not_emit_shortcut(matched):
    add_verdict(
        matched,
        matcher_stmt_id=UNAS_MATCH,
        outcome=VERDICT_REJECTED,
        verdict_id="verdict::unas::reject",
        curator_actor="group::hapi_curatorial",
        curator_document="document::curator_2026_05",
    )
    added = emit_shortcuts(matched)
    assert [e for e in added if e.predicate == "hapi:same_entity_as"] == []


def test_human_documentary_claims_emit_unconditionally(matched):
    # display_name is human-documentary → shortcut regardless of any verdict.
    added = emit_shortcuts(matched)
    disp = [
        e for e in added
        if e.predicate == "hapi:display_name"
        and e.subject_id == "leprohon::leprohon-18.09"
    ]
    assert len(disp) == 1


# -- chain integrity -------------------------------------------------------
def test_constraint_b_unique_root(matched):
    _approve(matched, verdict_id="verdict::unas::1")
    with pytest.raises(VerdictError, match="already has a root verdict"):
        _approve(matched, verdict_id="verdict::unas::2")  # second root → reject


def test_fork_rejected(matched):
    _approve(matched, verdict_id="verdict::unas::1")
    # First supersession is fine (tip → new tip).
    add_verdict(
        matched,
        matcher_stmt_id=UNAS_MATCH,
        outcome=VERDICT_RETRACTED,
        verdict_id="verdict::unas::2",
        curator_actor="group::hapi_curatorial",
        curator_document="document::curator_2026_05",
        supersedes="verdict::unas::1",
    )
    # Second verdict superseding the SAME (now mid-chain) predecessor forks the
    # chain → rejected by the tip-only rule.
    with pytest.raises(VerdictError, match="not the current chain tip"):
        add_verdict(
            matched,
            matcher_stmt_id=UNAS_MATCH,
            outcome=VERDICT_REJECTED,
            verdict_id="verdict::unas::3",
            curator_actor="group::hapi_curatorial",
            curator_document="document::curator_2026_05",
            supersedes="verdict::unas::1",
        )


def test_multi_tip_malformed_chain_detected(matched):
    # A malformed graph with two roots (two tips) for one matcher-claim — the
    # kind of structure the insert API forbids but a fabricated/concurrent write
    # could create — is detected loudly by the tip query, never silently
    # resolved to an arbitrary "current verdict".
    _approve(matched, verdict_id="verdict::unas::1")
    # Fabricate a second root directly in the IR, bypassing add_verdict.
    from pipeline.authority.graph.ir import Edge, Node
    matched.add_node(Node("verdict::unas::rogue", ("E13",), {}, "Statement"))
    matched.add_edge(Edge("verdict::unas::rogue", "P140_assigned_attribute_to", UNAS_MATCH))
    matched.add_edge(Edge("verdict::unas::rogue", "P141_assigned", "type::hapi:verdict_approved"))
    matched.add_edge(Edge("verdict::unas::rogue", "P177_assigned_property_of_type", "type::hapi:matcher_review_verdict"))
    with pytest.raises(VerdictError, match="chain tips"):
        tip_verdict(matched, UNAS_MATCH)


def test_constraint_c_no_mid_chain_supersede(matched):
    _approve(matched, verdict_id="verdict::unas::1")
    add_verdict(
        matched,
        matcher_stmt_id=UNAS_MATCH,
        outcome=VERDICT_RETRACTED,
        verdict_id="verdict::unas::2",
        curator_actor="group::hapi_curatorial",
        curator_document="document::curator_2026_05",
        supersedes="verdict::unas::1",
    )
    # v1 is now mid-chain (v2 superseded it). Superseding v1 again → reject.
    with pytest.raises(VerdictError, match="not the current chain tip"):
        add_verdict(
            matched,
            matcher_stmt_id=UNAS_MATCH,
            outcome=VERDICT_APPROVED,
            verdict_id="verdict::unas::3",
            curator_actor="group::hapi_curatorial",
            curator_document="document::curator_2026_05",
            supersedes="verdict::unas::1",
        )


def test_supersession_moves_the_tip_and_regates(matched):
    # approved → (supersede) retracted: tip becomes retracted, so a fresh
    # emit no longer produces the same_entity shortcut.
    _approve(matched, verdict_id="verdict::unas::1")
    add_verdict(
        matched,
        matcher_stmt_id=UNAS_MATCH,
        outcome=VERDICT_RETRACTED,
        verdict_id="verdict::unas::2",
        curator_actor="group::hapi_curatorial",
        curator_document="document::curator_2026_05",
        supersedes="verdict::unas::1",
    )
    assert verdict_outcome(matched, tip_verdict(matched, UNAS_MATCH)) == VERDICT_RETRACTED
    added = emit_shortcuts(matched)
    assert [e for e in added if e.predicate == "hapi:same_entity_as"] == []


def test_invalid_outcome_rejected(matched):
    with pytest.raises(VerdictError, match="not in the manifest verdict vocabulary"):
        add_verdict(
            matched,
            matcher_stmt_id=UNAS_MATCH,
            outcome="hapi:verdict_maybe",
            verdict_id="verdict::unas::x",
            curator_actor="group::hapi_curatorial",
            curator_document="document::curator_2026_05",
        )
