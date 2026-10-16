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
                                 # Leprohon's plain "Ahmose III" for Amasis is his own count too, but
                                 # no usual count has an Ahmose III, so it names no other king.
                                 ("Ahmose III", "cluster-beckerath-26.05", "raw_exact"),
                                 ("Amasis", "cluster-beckerath-26.05", "raw_exact")):
        found = kings.resolve(name)
        assert (found["status"], found["target_ids"], found["resolution_method"]) == ("resolved", [target], method), name
        assert "counted_otherwise" not in found


def test_the_committed_369_measurement_is_of_361s_ledger_and_consistent() -> None:
    """`docs/evaluations/resolver-gaps-369/results/resolver-change.json` measures #361's frozen
    ledger against the tree #361 froze (its `compare_arms.BASE_COMMIT`), and its counts agree
    with its listed changes."""
    import json
    from pathlib import Path

    evaluations = Path(__file__).resolve().parents[2] / "docs/evaluations"
    result = json.loads((evaluations / "resolver-gaps-369/results/resolver-change.json").read_text(encoding="utf-8"))
    ledger_diff = json.loads((evaluations / "ruler-reregistration-2026-10-15/results/ledger-diff.json").read_text(
        encoding="utf-8"))
    script = (evaluations / "resolver-gaps-369/scripts/measure_resolver_change.py").read_text(encoding="utf-8")
    assert result["ledger_gzip_sha256"] == ledger_diff["ledger_gzip_sha256"]
    assert f'BASE_COMMIT = "{result["base_commit"]}"' in script
    compare_arms = (evaluations / "ruler-reregistration-2026-10-15/scripts/compare_arms.py").read_text(encoding="utf-8")
    assert f'BASE_COMMIT = "{result["base_commit"]}"' in compare_arms
    assert f'LEDGER_SHA256 = "{result["ledger_gzip_sha256"]}"' in script
    cued = result["royal_woman_cued_mentions"]
    assert (cued["count"], cued["changed"], len(cued["changes"])) == (194, 11, 11)
    resolved = [(c["artifact_id"], c["after"]["target_ids"], c["after"]["context_rule"]) for c in cued["changes"]
                if c["before"]["status"] != c["after"]["status"]]
    assert resolved == [("brooklyn-3634", ["dodson_hilton:Ahmes B"], "family"),
                        ("met-566763", ["dodson_hilton:Ahmes B"], "family")]
    # The other nine stay ambiguous and name a subset of the women they named before.
    narrowed = [c for c in cued["changes"] if c["before"]["status"] == c["after"]["status"]]
    assert len(narrowed) == 9 and all(
        c["after"]["status"] == "ambiguous" and set(c["after"]["target_ids"]) < set(c["before"]["target_ids"])
        for c in narrowed)
    assert "brooklyn-3599" in {c["artifact_id"] for c in narrowed}  # #361's Neferu d
    assert result["unread_kin"] == {"cued_mentions_with_unread_kin_names": 2,
                                    "of_which_a_name_resolves_among_the_kings": 2,
                                    "results_reading_them_would_change": []}
    assert result["dynasty_values"] == {"distinct": 696, "newly_read_as_one_dynasty": 45, "read_differently": 0,
                                        "records_newly_read": 217}
    assert (result["king_mention_texts"], result["dh_family_names"]) == (
        {"changed": 0, "distinct": 232}, {"changed": 0, "distinct": 102})
