"""The claim-graph king authority's one added rule (#369): a bracketed numeral that the same
king also bears under a different plain numeral is a source's own count, not the usual one."""

from __future__ import annotations

import pytest

from pipeline.authority.graph_kings import GraphKings, counted_otherwise


@pytest.fixture(scope="module")
def kings() -> GraphKings:
    return GraphKings()


def test_a_bracketed_numeral_is_counted_otherwise_only_against_a_different_plain_one() -> None:
    assert counted_otherwise({"Ahmose (II)", "Ahmose I", "Amosis I.", "Iah mesu"}) == {"Ahmose (II)"}
    # A bracketed count that agrees with the plain one, or that stands alone, is kept.
    assert counted_otherwise({"Merenre (I)", "Merenre I"}) == set()
    assert counted_otherwise({"Merenre (I)", "Nemtyemsaf"}) == set()
    # The plain numeral of another name does not count.
    assert counted_otherwise({"Senakhtenre Ahmose (I)", "Ahmose II"}) == set()
    assert counted_otherwise({"Khety (VI)", "Khety (VII)"}) == set()


def test_the_graph_counts_one_name_otherwise_and_ahmose_ii_no_longer_reaches_ahmose_i(kings) -> None:
    """Leprohon's Dynasty 18 founder is "Ahmose (II)"; pharaoh.se's is "Ahmose I". A museum's
    "Ahmose II" is Amasis, whom no label of the graph calls that, so it stays unmatched."""
    assert {t: v for t, v in kings._counted_otherwise.items() if v} == {"cluster-beckerath-18.01": {"Ahmose (II)"}}
    found = kings.resolve("Ahmose II")
    assert (found["status"], found["target_ids"], found["resolution_method"], found["counted_otherwise"]) == (
        "unmatched", [], None, ["cluster-beckerath-18.01"])
    assert found["normalized_keys"] == ["ahmoseii"]
    for name, target, method in (("Ahmose I", "cluster-beckerath-18.01", "raw_exact"),
                                 ("Ahmose (II)", "cluster-beckerath-18.01", "raw_exact"),
                                 ("Merenre I", "cluster-beckerath-06.04", "committed_normalized"),
                                 ("Ahmose III", "cluster-beckerath-26.05", "raw_exact"),
                                 ("Amasis", "cluster-beckerath-26.05", "raw_exact")):
        found = kings.resolve(name)
        assert (found["status"], found["target_ids"], found["resolution_method"]) == ("resolved", [target], method), name
        assert "counted_otherwise" not in found
