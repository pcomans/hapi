"""Cross-museum matching over a run's links, authority on or off (#338 step 3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.enrich import authority_links as al, cross_museum as cm, link_files as lf


def link(artifact_id: str, entity_type: str, target: str, mode: str = "authority") -> dict:
    return {"artifact_id": artifact_id, "museum": artifact_id.split("-")[0], "entity_type": entity_type,
            "target_id": target, "mode": mode, "relation": "identity", "mention_ids": [f"m-{artifact_id}"],
            "evidence_roles": ["r"], "resolver_version": "v", "target_kind": "x"}


# Authority: met-1 and brooklyn-1 share Thebes (both modes would); met-2 and brooklyn-2 share a
# king that plain text splits (gained); plain text joins met-3 and harvard-3 on a broad literal
# the authority leaves unresolved (lost).
AUTHORITY = [link("met-1", "site", "idai:thebes"), link("brooklyn-1", "site", "idai:thebes"),
             link("met-2", "ruler", "king:horemheb"), link("brooklyn-2", "ruler", "king:horemheb"),
             link("harvard-3", "site", "idai:abydos")]
LITERAL = [link("met-1", "site", "literal:thebes", "literal"), link("brooklyn-1", "site", "literal:thebes", "literal"),
           link("met-2", "ruler", "literal:haremhab", "literal"), link("brooklyn-2", "ruler", "literal:horemheb", "literal"),
           link("met-3", "site", "literal:egypt", "literal"), link("harvard-3", "site", "literal:egypt", "literal")]


@pytest.fixture
def run(tmp_path) -> Path:
    (tmp_path / "links-authority.ndjson.gz").write_bytes(lf.gzip_rows(AUTHORITY))
    (tmp_path / "links-literal.ndjson.gz").write_bytes(lf.gzip_rows(LITERAL))
    return tmp_path


def test_a_record_matches_the_records_of_other_museums_on_its_targets(run) -> None:
    assert cm.matches(cm.load_links(run, "authority"), "met-2") == {
        "ruler": [{"target_id": "king:horemheb", "records": {"brooklyn": ["brooklyn-2"]}}]}
    assert cm.matches(cm.load_links(run, "literal"), "met-2") == {}
    assert cm.matches(cm.load_links(run, "literal"), "met-3") == {
        "site": [{"target_id": "literal:egypt", "records": {"harvard": ["harvard-3"]}}]}
    with pytest.raises(ValueError, match="unknown mode"):
        cm.load_links(run, "fuzzy")


def test_the_report_counts_what_the_authority_gains_and_loses_by_pair_and_type(run) -> None:
    r = cm.report(run)
    assert r["by_museum_pair"]["ruler|met|brooklyn"] == {
        "qualified": True, "shared_targets_authority": 1, "shared_targets_literal": 0,
        "records": {"met": {"connected_authority": 1, "connected_literal": 0, "gained": 1, "lost": 0},
                    "brooklyn": {"connected_authority": 1, "connected_literal": 0, "gained": 1, "lost": 0}},
        "top_target_share": {"authority": {"met": {"1": 1.0, "5": 1.0}, "brooklyn": {"1": 1.0, "5": 1.0}},
                             "literal": {"met": {"1": None, "5": None}, "brooklyn": {"1": None, "5": None}}}}
    assert r["by_museum_pair"]["site|met|brooklyn"]["records"] == {
        "met": {"connected_authority": 1, "connected_literal": 1, "gained": 0, "lost": 0},
        "brooklyn": {"connected_authority": 1, "connected_literal": 1, "gained": 0, "lost": 0}}
    assert r["by_museum_pair"]["site|met|harvard"]["records"] == {
        "met": {"connected_authority": 0, "connected_literal": 1, "gained": 0, "lost": 1},
        "harvard": {"connected_authority": 0, "connected_literal": 1, "gained": 0, "lost": 1}}
    assert r["by_museum_pair"]["ruler|met|harvard"]["qualified"] is False
    assert r["by_museum_pair"]["tomb_monument|met|brooklyn"]["qualified"] is False
    assert set(r["by_museum_pair"]) == {f"{t}|{a}|{b}" for t in al.RESOLVED_TYPES for a, b in al.MUSEUM_PAIRS}
    assert r["by_museum"]["met|site"] == {"authority": {"linked_records": 1, "connected_records": 1},
                                          "literal": {"linked_records": 2, "connected_records": 2}}
    assert r["by_museum"]["harvard|site"] == {"authority": {"linked_records": 1, "connected_records": 0},
                                              "literal": {"linked_records": 1, "connected_records": 1}}
    assert r["connected_records_by_entity_type"] == {
        "ruler": {"authority": 2, "literal": 0}, "site": {"authority": 2, "literal": 4},
        "tomb_monument": {"authority": 0, "literal": 0}}


def test_the_committed_end_to_end_run_is_consistent_and_flags_scopes_as_the_evaluations_did() -> None:
    """`docs/evaluations/authority-bridge-338/results/end-to-end.json`: two runs in two
    interpreters agreed, and each scope is flagged qualified exactly as `QUALIFIED_SCOPES` says."""
    import json
    result = json.loads((al.REPO / "docs/evaluations/authority-bridge-338/results/end-to-end.json").read_text(
        encoding="utf-8"))
    assert result["two_runs"] == {"python_hash_seeds": ["1", "2"], "same_manifest_and_contents": True}
    assert {name: f["rows"] for name, f in result["files"].items()} == {
        "links-authority.ndjson.gz": 48994, "links-literal.ndjson.gz": 127711, "mentions.ndjson.gz": 148964,
        "resolutions-authority.ndjson.gz": 148964, "resolutions-literal.ndjson.gz": 148964}
    pairs = result["matching"]["by_museum_pair"]
    for key, row in pairs.items():
        entity, a, b = key.split("|")
        assert row["qualified"] == ((a, b) in al.QUALIFIED_SCOPES[entity]), key
    assert pairs["ruler|met|brooklyn"]["records"] == {
        "met": {"connected_authority": 1957, "connected_literal": 1981, "gained": 33, "lost": 57},
        "brooklyn": {"connected_authority": 20, "connected_literal": 19, "gained": 2, "lost": 1}}
    assert pairs["site|met|brooklyn"]["records"]["met"] == {
        "connected_authority": 14393, "connected_literal": 27198, "gained": 136, "lost": 12941}
    assert result["matching"]["connected_records_by_entity_type"] == {
        "ruler": {"authority": 1979, "literal": 2002}, "site": {"authority": 15552, "literal": 30622},
        "tomb_monument": {"authority": 0, "literal": 0}}
