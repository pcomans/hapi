"""Constraint-narrowed generator tests (ADR-018 § Implications for matching).

The deterministic parts (graph-constraint narrowing + candidate emission + verdict
approval) are tested offline with an injected pick_fn. The live LLM pick is
exercised separately (test_live_reviewer_integration covers the SDK boundary).
No surface-string metric is used to accept a match (ADR-009).
"""

from __future__ import annotations

import pytest

from pipeline.authority.graph.loader import load_poc_graph
from pipeline.authority.graph.matcher.constraint_narrowed import (
    generate_candidates,
    narrowed_sets,
    review_narrowed,
)
from pipeline.authority.graph.verdicts import (
    VERDICT_APPROVED,
    emit_shortcuts,
    tip_verdict,
    verdict_outcome,
)


@pytest.fixture
def graph():
    return load_poc_graph()


def test_narrowing_is_same_dynasty_only(graph):
    narrowed = narrowed_sets(graph, dynasty=18)
    # 17 Leprohon Dynasty-18 rulers, each narrowed to the 15 Beckerath Dynasty-18.
    assert len(narrowed) == 17
    assert all(len(v) == 15 for v in narrowed.values())
    # Every right candidate is genuinely Dynasty 18 (structured narrowing, not names).
    d18_beckerath = {
        n.id for n in graph.nodes_of_class("E21")
        if n.props.get("source") == "beckerath"
        and any(
            e.predicate == "P141_assigned"
            and graph.node(e.object_id).props.get("number") == 18
            for e in graph.out_edges(f"stmt::{n.id}::in_dynastic_period")
        )
    }
    for rights in narrowed.values():
        assert set(rights) == d18_beckerath


def test_generate_emits_candidate_e13s_with_machine_provenance(graph):
    narrowed = narrowed_sets(graph, dynasty=18)
    cand_map = generate_candidates(graph, narrowed)
    total = sum(len(v) for v in cand_map.values())
    assert total == 17 * 15
    sample = next(iter(cand_map.values()))[0]
    preds = {e.predicate for e in graph.out_edges(sample)}
    assert "P177_assigned_property_of_type" in preds
    assert "hapi:derived_by_run" in preds   # machine-derived
    assert "P14_carried_out_by" not in preds  # not human-documentary


def test_pick_approves_chosen_candidate_and_gates_shortcut(graph):
    narrowed = narrowed_sets(graph, dynasty=18)
    cand_map = generate_candidates(graph, narrowed)

    # Stub pick: match Amenhotep III → Amenophis III. by id; abstain otherwise.
    def pick_fn(left, rights):
        if left["ruler_id"] == "leprohon::leprohon-18.09":
            return {"choice": "beckerath::18.09", "reasoning": "stub"}
        return {"choice": None, "reasoning": "stub abstain"}

    matches = review_narrowed(graph, cand_map, pick_fn=pick_fn)
    assert matches == [("leprohon::leprohon-18.09", "beckerath::18.09")]

    chosen = "stmt::cn::leprohon::leprohon-18.09::beckerath::05.09".replace("05.09", "18.09")
    assert verdict_outcome(graph, tip_verdict(graph, chosen)) == VERDICT_APPROVED
    # Approved tip → gated shortcut emitted between the two rulers.
    added = emit_shortcuts(graph)
    assert any(
        e.predicate == "hapi:same_entity_as"
        and e.subject_id == "leprohon::leprohon-18.09"
        and e.object_id == "beckerath::18.09"
        for e in added
    )
