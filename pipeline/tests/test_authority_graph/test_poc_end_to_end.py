"""End-to-end POC integration test (ADR-018 vertical slice).

Exercises the whole pipeline in one shot and asserts the headline outcomes:
both sources loaded uncollapsed, deterministic matches proposed, verdicts
approved, gated shortcuts emitted, and a lossless strict-RDF export.
"""

from __future__ import annotations

import pytest

from pipeline.authority.graph.adapters import rdf_adapter
from pipeline.authority.graph.poc import build_poc_graph, summarize
from pipeline.authority.graph.resolution import resolve_display_name
from pipeline.authority.graph.verdicts import (
    VERDICT_APPROVED,
    tip_verdict,
    verdict_outcome,
)

UNAS_MATCH = "stmt::match::leprohon::leprohon-5.09::beckerath::05.09"


@pytest.fixture(scope="module")
def poc():
    return build_poc_graph()


def test_headline_counts(poc):
    s = summarize(poc)
    # 395 Leprohon + 166 Beckerath rulers + 2 scholar E21 Persons (Leprohon, von Beckerath).
    assert s["rulers"] == 563
    assert s["statements"] > 1600
    # All 11 deterministic candidates were curator-approved → 11 shortcuts.
    assert s["same_entity_shortcuts"] == 11


def test_cross_source_identity_is_data_not_collapse(poc):
    # The two source rulers still exist as distinct nodes...
    assert poc.node("leprohon::leprohon-5.09").props["source"] == "leprohon"
    assert poc.node("beckerath::05.09").props["source"] == "beckerath"
    # ...linked by an APPROVED same_entity_as claim → a queryable shortcut.
    assert verdict_outcome(poc, tip_verdict(poc, UNAS_MATCH)) == VERDICT_APPROVED
    shortcut = [
        e for e in poc.edges_with_predicate("hapi:same_entity_as")
        if e.subject_id == "leprohon::leprohon-5.09" and e.object_id == "beckerath::05.09"
    ]
    assert len(shortcut) == 1


def test_resolution_surfaces_curator_value(poc):
    assert resolve_display_name(poc, "leprohon::leprohon-18.09") == "Amenhotep III"


def test_full_graph_round_trips_losslessly(poc):
    back = rdf_adapter.from_rdf(rdf_adapter.to_rdf(poc))
    assert len(back.nodes) == len(poc.nodes)
    assert len(back.edges) == len(poc.edges)


def test_reviewer_path_also_works(poc):
    # Building via the stage-2 reviewer path (stubbed) approves Unas too.
    g = build_poc_graph(
        review_fn=lambda ctx: {
            "outcome": "approved" if ctx["left"]["display_name"] == ctx["right"]["display_name"]
            else "escalate",
            "confidence": 1.0,
            "reasoning": "stub",
        }
    )
    assert verdict_outcome(g, tip_verdict(g, UNAS_MATCH)) == VERDICT_APPROVED
