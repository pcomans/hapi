"""Stage-1 deterministic matcher tests (ADR-018 schema sketch 4a).

Asserts the matcher's candidates and — critically — the machine-derived
provenance shape: derived_by_run present, P14/P70i ABSENT, full CRMdig
D10→D14/D1 chain.
"""

from __future__ import annotations

import pytest

from pipeline.authority.graph.loader import load_poc_graph
from pipeline.authority.graph.matcher.stage1_deterministic import (
    normalize_name,
    run_stage1_matcher,
)


@pytest.fixture(scope="module")
def matched_graph():
    g = load_poc_graph()
    candidates = run_stage1_matcher(g)
    return g, candidates


def test_normalize_name_strips_diacritics_and_punctuation():
    assert normalize_name("Osorkon I.") == normalize_name("Osorkon I")
    assert normalize_name("Amenophis III.") == frozenset({"amenophis", "iii"})
    assert normalize_name("Miëbis") == frozenset({"miebis"})


def test_matcher_is_deterministic_and_finds_known_pairs(matched_graph):
    _, candidates = matched_graph
    assert len(candidates) == 11  # deterministic on the committed slice
    # Unas (Leprohon 5.09) ↔ Unas (Beckerath 05.09) is among them.
    assert "stmt::match::leprohon::leprohon-5.09::beckerath::05.09" in candidates


def test_candidate_has_machine_derived_shape_not_documentary(matched_graph):
    g, _ = matched_graph
    stmt = "stmt::match::leprohon::leprohon-5.09::beckerath::05.09"
    preds = {e.predicate for e in g.out_edges(stmt)}
    # Spine + derived_by_run present.
    assert "P140_assigned_attribute_to" in preds
    assert "P141_assigned" in preds
    assert "P177_assigned_property_of_type" in preds
    assert "hapi:derived_by_run" in preds
    # Machine claims NEVER carry P14 or P70i (loader contract).
    assert "P14_carried_out_by" not in preds
    assert "P70i_is_documented_in" not in preds
    # P177 target is the same_entity_as predicate type.
    p177 = [e for e in g.out_edges(stmt) if e.predicate == "P177_assigned_property_of_type"][0]
    assert g.node(p177.object_id).props["id"] == "hapi:same_entity_as"


def test_d10_run_has_full_crmdig_chain(matched_graph):
    g, _ = matched_graph
    stmt = "stmt::match::leprohon::leprohon-5.09::beckerath::05.09"
    run_edge = [e for e in g.out_edges(stmt) if e.predicate == "hapi:derived_by_run"][0]
    run = g.node(run_edge.object_id)
    assert "D10" in run.crm_classes
    assert run.props["parameters_hash"].startswith("sha256:")
    out_edges = g.out_edges(run.id)
    by_pred: dict[str, list[str]] = {}
    for e in out_edges:
        by_pred.setdefault(e.predicate, []).append(e.object_id)
    # D14 algorithm via L23.
    assert len(by_pred["L23_used_software_or_firmware"]) == 1
    assert "D14" in g.node(by_pred["L23_used_software_or_firmware"][0]).crm_classes
    # Two D1 inputs (the two reconciled.jsonl) via L10; one D1 output via L11.
    assert len(by_pred["L10_had_input"]) == 2
    assert len(by_pred["L11_had_output"]) == 1
    for did in by_pred["L10_had_input"] + by_pred["L11_had_output"]:
        assert "D1" in g.node(did).crm_classes
