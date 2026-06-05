"""LIVE stage-2 reviewer integration test (real Anthropic SDK).

Skips unless ANTHROPIC_API_KEY is set, so CI without a key stays green while a
keyed environment exercises the real review path. When it runs, it asserts the
reviewer makes sane calls on unambiguous cases — exact-name cross-source pairs
(Unas==Unas) should be approved, not escalated.
"""

from __future__ import annotations

import os

import pytest

from pipeline.authority.graph.poc import build_poc_graph_live
from pipeline.authority.graph.verdicts import (
    VERDICT_APPROVED,
    tip_verdict,
    verdict_outcome,
)

UNAS_MATCH = "stmt::match::leprohon::leprohon-5.09::beckerath::05.09"

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="live reviewer requires ANTHROPIC_API_KEY",
)


@pytest.fixture(scope="module")
def live():
    graph, verdicts, escalations = build_poc_graph_live()
    return graph, verdicts, escalations


def test_live_reviewer_decides_candidates(live):
    graph, verdicts, escalations = live
    # Every candidate is either decided (verdict) or escalated — none lost.
    assert len(verdicts) + len(escalations) == 11


def test_live_reviewer_approves_exact_name_pair(live):
    graph, _, _ = live
    # Unas (Leprohon) == Unas (Beckerath) is unambiguous; a competent reviewer
    # approves it. (If the live model escalates, that is a signal worth seeing —
    # this assertion documents the expected behaviour on the clearest case.)
    tip = tip_verdict(graph, UNAS_MATCH)
    assert tip is not None, "Unas candidate should be decided, not left pending"
    assert verdict_outcome(graph, tip) == VERDICT_APPROVED
