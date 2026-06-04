"""Stage-2 reviewer tests (ADR-018 schema 4b).

The live SDK boundary is injected (review_fn) so the graph wiring, verdict
emission, and human-escalation path are tested deterministically offline. A
separate test asserts the real path raises loudly without an API key.
"""

from __future__ import annotations

import pytest

from pipeline.authority.graph.loader import load_poc_graph
from pipeline.authority.graph.matcher.stage1_deterministic import run_stage1_matcher
from pipeline.authority.graph.matcher.stage2_reviewer import (
    candidate_context,
    run_stage2_reviewer,
)
from pipeline.authority.graph.verdicts import (
    VERDICT_APPROVED,
    emit_shortcuts,
    tip_verdict,
    verdict_outcome,
)

UNAS_MATCH = "stmt::match::leprohon::leprohon-5.09::beckerath::05.09"
TETI_MATCH = "stmt::match::leprohon::leprohon-6.01::beckerath::06.01"


@pytest.fixture
def matched():
    g = load_poc_graph()
    cands = run_stage1_matcher(g)
    return g, cands


def test_candidate_context_describes_both_sides(matched):
    g, _ = matched
    ctx = candidate_context(g, UNAS_MATCH)
    assert ctx["left"]["display_name"] == "Unas"
    assert ctx["left"]["dynasty"] == 5
    assert ctx["left"]["source"] == "leprohon"
    assert ctx["right"]["display_name"] == "Unas"
    assert ctx["right"]["source"] == "beckerath"


def test_reviewer_emits_verdicts_and_escalates(matched):
    g, cands = matched

    # Stub the LLM boundary: approve Unas, reject Teti, escalate the rest.
    def review_fn(context):
        sid = context["matcher_stmt_id"]
        if sid == UNAS_MATCH:
            return {"outcome": "approved", "confidence": 0.97, "reasoning": "same"}
        if sid == TETI_MATCH:
            return {"outcome": "rejected", "confidence": 0.9, "reasoning": "diff"}
        return {"outcome": "escalate", "confidence": 0.4, "reasoning": "unsure"}

    verdicts, escalations = run_stage2_reviewer(g, cands, review_fn=review_fn)
    # Two decided (approve + reject), the remaining nine escalated to a human.
    assert len(verdicts) == 2
    assert len(escalations) == 9
    # Approved Unas → tip is approved → shortcut emitted.
    assert verdict_outcome(g, tip_verdict(g, UNAS_MATCH)) == VERDICT_APPROVED
    added = emit_shortcuts(g)
    assert any(
        e.predicate == "hapi:same_entity_as"
        and e.subject_id == "leprohon::leprohon-5.09"
        for e in added
    )
    # Escalated candidates have NO verdict → no tip → no shortcut for them.
    assert tip_verdict(g, "stmt::match::leprohon::leprohon-22.02::beckerath::22.02") is None


def test_reviewer_provenance_chain(matched):
    g, cands = matched
    run_stage2_reviewer(
        g,
        [UNAS_MATCH],
        review_fn=lambda c: {"outcome": "approved", "confidence": 1.0, "reasoning": "x"},
        model_snapshot="claude-opus-4-8-stub",
    )
    verdict = tip_verdict(g, UNAS_MATCH)
    run_edge = [e for e in g.out_edges(verdict) if e.predicate == "hapi:derived_by_run"][0]
    run = g.node(run_edge.object_id)
    assert "D10" in run.crm_classes
    by_pred = {}
    for e in g.out_edges(run.id):
        by_pred.setdefault(e.predicate, []).append(e.object_id)
    algo = g.node(by_pred["L23_used_software_or_firmware"][0])
    assert algo.props["model_id"] == "claude-opus-4-8"
    assert algo.props["model_snapshot"] == "claude-opus-4-8-stub"
    assert len(by_pred["L10_had_input"]) == 1
    assert len(by_pred["L11_had_output"]) == 1


def test_live_review_raises_without_api_key(matched, monkeypatch):
    g, cands = matched
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # No review_fn → the real SDK path, which must raise loudly without a key.
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        run_stage2_reviewer(g, [UNAS_MATCH])
