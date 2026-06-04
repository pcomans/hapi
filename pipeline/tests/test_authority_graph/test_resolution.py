"""Display-name resolution policy tests (ADR-018 §7, § Display name migration).

The policy prefers the curator-decision-batch claim and fails loud otherwise —
no silent fallback to source-documented claims (Constitutional rule 2).
"""

from __future__ import annotations

import pytest

from pipeline.authority.graph.loader import load_poc_graph
from pipeline.authority.graph.resolution import (
    ResolutionError,
    load_curator_display_names,
    resolve_display_name,
)


@pytest.fixture(scope="module")
def graph_with_curator():
    g = load_poc_graph()
    n = load_curator_display_names(g)
    return g, n


def test_curator_batch_loaded(graph_with_curator):
    _, n = graph_with_curator
    assert n == 5  # five seeded decisions


def test_resolves_to_curator_value_over_source(graph_with_curator):
    g, _ = graph_with_curator
    # Leprohon's source claim is "Amenhotep III"; the curator claim (also
    # "Amenhotep III") is what the policy surfaces — chosen by provenance, not
    # by coincidence of value.
    assert resolve_display_name(g, "leprohon::leprohon-18.09") == "Amenhotep III"
    assert resolve_display_name(g, "leprohon::leprohon-5.09") == "Unas"


def test_fail_loud_when_no_curator_decision(graph_with_curator):
    g, _ = graph_with_curator
    # A Beckerath ruler with only a German source claim and NO curator decision
    # is unrenderable — fail loud, no fallback to the source claim.
    with pytest.raises(ResolutionError, match="fail-loud default"):
        resolve_display_name(g, "beckerath::18.09")


def test_fail_loud_when_only_source_claim_present(graph_with_curator):
    g, _ = graph_with_curator
    # Leprohon ruler not in the curator batch: has a source display_name claim
    # but no curator one → still fails loud (clause 1 requires BOTH the
    # curatorial Group actor AND a curator_decision_batch document).
    with pytest.raises(ResolutionError):
        resolve_display_name(g, "leprohon::leprohon-1.01")
