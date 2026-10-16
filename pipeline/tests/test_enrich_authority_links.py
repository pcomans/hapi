"""The production enrichment step (#338): every mention gets one resolution row that says what
it resolved to or why not, and a link joins a record to a target only on resolved mentions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.authority import resolver, royal_women, tla_links
from pipeline.enrich import authority_links as al
from pipeline.enrich.mentions import make_mention

KING_AMENHOTEP_III = "cluster-beckerath-18.09"
KING_HATSHEPSUT = "cluster-beckerath-18.05"
SITE_THEBES = "idai:2042921"
SITE_DEIR_EL_BAHRI = "idai:2110510"


@pytest.fixture(scope="module")
def authority() -> al.Authority:
    return al.load_authority()


def mention(artifact_id: str, entity_type: str, field_path: str, field_value: str, text: str, *,
            expression: str = "single_identity", role: str = "role", dynasty: str | None = "Dynasty 18") -> dict:
    start = field_value.index(text)
    museum = artifact_id.split("-")[0]
    artifact = {"id": artifact_id, "source_museum": museum, "source_id": artifact_id.split("-")[1], "dynasty": dynasty}
    return make_mention(artifact=artifact, entity_type=entity_type, field_path=field_path, field_value=field_value,
                        start=start, end=start + len(text), extraction_method="test", evidence_role=role,
                        expression_type=expression)


MENTIONS = [
    mention("met-1", "ruler", "reign", "reign of Amenhotep III", "Amenhotep III", role="catalogued_reign"),
    mention("met-1", "ruler", "title", "Relief of King Amenhotep III", "Amenhotep III", role="explicit_royal_text_cue"),
    mention("met-1", "site", "subregion", "Thebes", "Thebes", role="From Egypt:subregion"),
    mention("met-2", "ruler", "title", "Queen Ahmose, Mother of Hatshepsut", "Ahmose", role="explicit_royal_text_cue"),
    mention("met-3", "ruler", "title", "Scarab of Queen Tiye", "Tiye", dynasty="Dynasty 20"),
    mention("met-4", "site", "locale", "Atlantis", "Atlantis"),
    mention("brooklyn-5", "site", "geographicalLocations[0].name", "Deir el-Bahri", "Deir el-Bahri",
            role="Excavation Site"),
    mention("brooklyn-5", "ruler", "title", "Statue of King Akhenaten or Smenkhkare", "Akhenaten",
            expression="multi_or_range"),
    mention("brooklyn-5", "tomb_monument", "geographicalLocations[0].name", "KV 62", "KV 62"),
    mention("brooklyn-5", "temple", "geographicalLocations[1].name", "Temple of Amun", "Temple of Amun"),
    mention("brooklyn-5", "excavation", "excavation", "Carter", "Carter"),
]


def by_text(rows: list[dict]) -> dict[tuple[str, str, str], dict]:
    return {(r["artifact_id"], r["field_path"], r["mention_text"]): r for r in rows}


def test_each_mention_gets_one_row_that_says_what_it_resolved_to_or_why_not(authority) -> None:
    rows = al.resolve_mentions(MENTIONS, "authority", authority)
    assert [r["mention_id"] for r in rows] == [m["mention_id"] for m in MENTIONS]
    version = authority.snapshot["resolver_version"]
    assert {r["resolver_version"] for r in rows} == {version} and {r["mode"] for r in rows} == {"authority"}
    got = {k: {f: r[f] for f in ("status", "reason", "authority", "resolution_method", "target_ids", "candidate_ids",
                                  "context_rule", "stated_kin_king_ids")}
           for k, r in by_text(rows).items()}
    assert got == {
        ("met-1", "reign", "Amenhotep III"): {
            "status": "resolved", "reason": None, "authority": "kings", "resolution_method": "raw_exact",
            "target_ids": [KING_AMENHOTEP_III], "candidate_ids": [], "context_rule": None, "stated_kin_king_ids": []},
        ("met-1", "title", "Amenhotep III"): {
            "status": "resolved", "reason": None, "authority": "kings", "resolution_method": "raw_exact",
            "target_ids": [KING_AMENHOTEP_III], "candidate_ids": [], "context_rule": None, "stated_kin_king_ids": []},
        ("met-1", "subregion", "Thebes"): {
            "status": "resolved", "reason": None, "authority": "idai", "resolution_method": "raw_exact",
            "target_ids": [SITE_THEBES], "candidate_ids": [], "context_rule": None, "stated_kin_king_ids": []},
        # The field's stated kin names her family king (#369).
        ("met-2", "title", "Ahmose"): {
            "status": "resolved", "reason": None, "authority": "royal_women", "resolution_method": "weak_sign_skeleton",
            "target_ids": ["dodson_hilton:Ahmes B"], "candidate_ids": [], "context_rule": "family",
            "stated_kin_king_ids": [KING_HATSHEPSUT]},
        # Two Dynasty 20 Tiyes: ambiguous, the alternatives kept.
        ("met-3", "title", "Tiye"): {
            "status": "ambiguous", "reason": "authority_ambiguous", "authority": "royal_women",
            "resolution_method": "raw_exact", "target_ids": [],
            "candidate_ids": ["dodson_hilton:Tiye B Mereniset", "dodson_hilton:Tiye C"], "context_rule": None,
            "stated_kin_king_ids": []},
        ("met-4", "locale", "Atlantis"): {
            "status": "unmatched", "reason": "authority_unmatched", "authority": "idai", "resolution_method": None,
            "target_ids": [], "candidate_ids": [], "context_rule": None, "stated_kin_king_ids": []},
        ("brooklyn-5", "geographicalLocations[0].name", "Deir el-Bahri"): {
            "status": "resolved", "reason": None, "authority": "idai", "resolution_method": "raw_exact",
            "target_ids": [SITE_DEIR_EL_BAHRI], "candidate_ids": [], "context_rule": None, "stated_kin_king_ids": []},
        ("brooklyn-5", "title", "Akhenaten"): {
            "status": "abstained", "reason": "expression:multi_or_range", "authority": None, "resolution_method": None,
            "target_ids": [], "candidate_ids": [], "context_rule": None, "stated_kin_king_ids": []},
        ("brooklyn-5", "geographicalLocations[0].name", "KV 62"): {
            "status": "abstained", "reason": "unsupported:tomb_monument", "authority": None, "resolution_method": None,
            "target_ids": [], "candidate_ids": [], "context_rule": None, "stated_kin_king_ids": []},
        ("brooklyn-5", "geographicalLocations[1].name", "Temple of Amun"): {
            "status": "abstained", "reason": "unsupported:temple", "authority": None, "resolution_method": None,
            "target_ids": [], "candidate_ids": [], "context_rule": None, "stated_kin_king_ids": []},
        ("brooklyn-5", "excavation", "Carter"): {
            "status": "abstained", "reason": "unsupported:excavation", "authority": None, "resolution_method": None,
            "target_ids": [], "candidate_ids": [], "context_rule": None, "stated_kin_king_ids": []},
    }
    row = by_text(rows)["met-1", "subregion", "Thebes"]
    assert {k: row[k] for k in ("museum", "entity_type", "evidence_role", "mention_text")} == {
        "museum": "met", "entity_type": "site", "evidence_role": "From Egypt:subregion", "mention_text": "Thebes"}


def test_the_literal_mode_is_the_plain_text_baseline() -> None:
    rows = by_text(al.resolve_mentions(MENTIONS, "literal", None))
    reign, title = rows["met-1", "reign", "Amenhotep III"], rows["met-1", "title", "Amenhotep III"]
    assert reign["target_ids"] == title["target_ids"] == [al.literal_target("ruler", "amenhotep  III")]
    assert (reign["status"], reign["resolution_method"], reign["resolver_version"], reign["mode"]) == (
        "resolved", al.LITERAL_METHOD, None, "literal")
    assert rows["met-2", "title", "Ahmose"]["target_ids"] != [al.literal_target("site", "Ahmose")]
    # Abstentions do not depend on the mode.
    assert (rows["brooklyn-5", "title", "Akhenaten"]["status"], rows["brooklyn-5", "title", "Akhenaten"]["reason"]) == (
        "abstained", "expression:multi_or_range")


def test_a_link_joins_a_record_to_a_target_on_its_resolved_mentions(authority) -> None:
    rows = al.resolve_mentions(MENTIONS, "authority", authority)
    version = authority.snapshot["resolver_version"]
    ids = {(r["artifact_id"], r["field_path"], r["mention_text"]): r["mention_id"] for r in rows}
    assert al.build_links(rows) == [
        {"artifact_id": "brooklyn-5", "museum": "brooklyn", "entity_type": "site", "target_id": SITE_DEIR_EL_BAHRI,
         "relation": "identity", "mode": "authority", "resolver_version": version,
         "mention_ids": [ids["brooklyn-5", "geographicalLocations[0].name", "Deir el-Bahri"]],
         "evidence_roles": ["Excavation Site"]},
        {"artifact_id": "met-1", "museum": "met", "entity_type": "ruler", "target_id": KING_AMENHOTEP_III,
         "relation": "identity", "mode": "authority", "resolver_version": version,
         "mention_ids": sorted([ids["met-1", "reign", "Amenhotep III"], ids["met-1", "title", "Amenhotep III"]]),
         "evidence_roles": ["catalogued_reign", "explicit_royal_text_cue"]},
        {"artifact_id": "met-1", "museum": "met", "entity_type": "site", "target_id": SITE_THEBES,
         "relation": "identity", "mode": "authority", "resolver_version": version,
         "mention_ids": [ids["met-1", "subregion", "Thebes"]], "evidence_roles": ["From Egypt:subregion"]},
        {"artifact_id": "met-2", "museum": "met", "entity_type": "ruler", "target_id": "dodson_hilton:Ahmes B",
         "relation": "identity", "mode": "authority", "resolver_version": version,
         "mention_ids": [ids["met-2", "title", "Ahmose"]], "evidence_roles": ["explicit_royal_text_cue"]},
    ]


def test_bad_input_fails_loud(authority) -> None:
    with pytest.raises(ValueError, match="unknown mode"):
        al.resolve_mentions(MENTIONS, "fuzzy", authority)
    with pytest.raises(ValueError, match="needs the authority"):
        al.resolve_mentions(MENTIONS, "authority", None)
    with pytest.raises(ValueError, match="unclassified entity type: dynasty"):
        al.resolve_mentions([{**MENTIONS[0], "entity_type": "dynasty"}], "literal", None)


def test_the_resolver_version_covers_the_files_the_resolution_reads(authority, monkeypatch, tmp_path) -> None:
    files = authority.snapshot["files"]
    for path in (resolver.GRAPH, resolver.IDAI, royal_women.DODSON_HILTON, royal_women.SAME_WOMAN,
                 royal_women.FEMALE_RULERS, tla_links.TLA, tla_links.LINKS_DIR / "decisions.jsonl"):
        assert str(path.relative_to(al.REPO)) in files
    assert len(files) == len(al.SNAPSHOT_FILES) == 15
    # Any file's change changes the version.
    changed = tmp_path / "claim-graph.json"
    changed.write_text(json.dumps({"changed": True}), encoding="utf-8")
    real = al.sha256_path
    monkeypatch.setattr(al, "sha256_path", lambda p: real(changed) if Path(p) == resolver.GRAPH else real(p))
    assert al.authority_snapshot()["resolver_version"] != authority.snapshot["resolver_version"]


def test_the_committed_promotion_check_holds_and_is_of_the_frozen_inputs() -> None:
    """`docs/evaluations/authority-bridge-338/results/promotion-check.json`: the production step
    on the frozen corpus gives #361's mentions and resolutions, but for #369's changes."""
    evaluations = al.REPO / "docs/evaluations"
    result = json.loads((evaluations / "authority-bridge-338/results/promotion-check.json").read_text(encoding="utf-8"))
    ledger = json.loads((evaluations / "ruler-reregistration-2026-10-15/results/ledger-diff.json").read_text(
        encoding="utf-8"))
    changes_369 = json.loads((evaluations / "resolver-gaps-369/results/resolver-change.json").read_text(
        encoding="utf-8"))["royal_woman_cued_mentions"]
    assert result["run_361_files"]["mentions.ndjson.gz"] == ledger["ledger_gzip_sha256"]
    assert result["mentions"] == {"production": 148964, "ledger_361": 148964, "rows_equal": True}
    assert result["rulers_vs_361_authority_arm"] == {
        "compared": 11648, "differ": changes_369["changed"], "differ_outside_369_changed_records": []}
    assert result["sites_vs_linkability_adapter"] == {"compared": 113738, "differ": []}
    assert result["rulers_vs_361_literal_arm"] == {"compared": 11648, "differ": []}
