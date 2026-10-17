"""The production enrichment step (#338): every mention gets one resolution row that says what
it resolved to or why not, and a link joins a record to a target only on resolved mentions."""

from __future__ import annotations

import json
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

from pipeline.authority import resolver, royal_women, tla_links
from pipeline.enrich import authority_links as al
from pipeline.enrich.mentions import make_mention

KING_AMENHOTEP_III = "cluster-beckerath-18.09"
KING_HATSHEPSUT = "cluster-beckerath-18.05"
SITE_THEBES = "idai:2042921"
SITE_DEIR_EL_BAHRI = "idai:2110510"
TOMB_KV62 = "pm_theban:KV62"


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


def no_context(mentions: list[dict]) -> dict[str, dict]:
    """Records that give no dynasty or date: kings resolve by name alone (`king_context`)."""
    return {m["artifact_id"]: {"dynasty": None, "dates": None} for m in mentions}


def by_text(rows: list[dict]) -> dict[tuple[str, str, str], dict]:
    return {(r["artifact_id"], r["field_path"], r["mention_text"]): r for r in rows}


def test_each_mention_gets_one_row_that_says_what_it_resolved_to_or_why_not(authority) -> None:
    rows = al.resolve_mentions(MENTIONS, "authority", authority, no_context(MENTIONS))
    assert [r["mention_id"] for r in rows] == [m["mention_id"] for m in MENTIONS]
    version = authority.snapshot["resolver_version"]
    assert {r["resolver_version"] for r in rows} == {version} and {r["mode"] for r in rows} == {"authority"}
    got = {k: (r["status"], r["reason"], r["authority"], r["target_ids"]) for k, r in by_text(rows).items()}
    assert got == {
        ("met-1", "reign", "Amenhotep III"): ("resolved", None, "kings", [KING_AMENHOTEP_III]),
        ("met-1", "title", "Amenhotep III"): ("resolved", None, "kings", [KING_AMENHOTEP_III]),
        ("met-1", "subregion", "Thebes"): ("resolved", None, "idai", [SITE_THEBES]),
        ("met-2", "title", "Ahmose"): ("resolved", None, "royal_women", ["dodson_hilton:Ahmes B"]),
        ("met-3", "title", "Tiye"): ("ambiguous", "authority_ambiguous", "royal_women", []),
        ("met-4", "locale", "Atlantis"): ("unmatched", "authority_unmatched", "idai", []),
        ("brooklyn-5", "geographicalLocations[0].name", "Deir el-Bahri"): ("resolved", None, "idai", [SITE_DEIR_EL_BAHRI]),
        ("brooklyn-5", "title", "Akhenaten"): ("abstained", "expression:multi_or_range", None, []),
        ("brooklyn-5", "geographicalLocations[0].name", "KV 62"): ("resolved", None, "porter_moss", [TOMB_KV62]),
        ("brooklyn-5", "geographicalLocations[1].name", "Temple of Amun"): ("abstained", "unsupported:temple", None, []),
        ("brooklyn-5", "excavation", "Carter"): ("abstained", "unsupported:excavation", None, []),
    }
    r = by_text(rows)
    # The resolver's own answer is kept whole: the keys it tried, how it chose, what it left.
    assert r["met-1", "subregion", "Thebes"]["resolution"] == {
        "raw_exact_status": "unique", "raw_exact_target_ids": [SITE_THEBES], "normalized_keys": ["thebes"],
        "resolution_method": "raw_exact", "status": "resolved", "target_ids": [SITE_THEBES], "authority": "idai"}
    assert r["brooklyn-5", "geographicalLocations[0].name", "KV 62"]["resolution"] == {
        "raw_exact_status": "unmatched", "raw_exact_target_ids": [], "normalized_keys": ["kv62"],
        "resolution_method": "committed_normalized", "status": "resolved", "target_ids": [TOMB_KV62],
        "authority": "porter_moss"}
    ahmose = r["met-2", "title", "Ahmose"]["resolution"]
    assert {k: ahmose[k] for k in ("resolution_method", "candidate_ids", "context_rule", "stated_kin_king_ids",
                                   "royal_woman_id")} == {
        "resolution_method": "weak_sign_skeleton", "candidate_ids": ["dodson_hilton:Ahmes A", "dodson_hilton:Ahmes B"],
        "context_rule": "family", "stated_kin_king_ids": [KING_HATSHEPSUT], "royal_woman_id": "dodson_hilton:Ahmes B"}
    # Two Dynasty 20 Tiyes: the alternatives the record's dynasty leaves are kept.
    tiye = r["met-3", "title", "Tiye"]["resolution"]
    assert (tiye["status"], tiye["target_ids"], tiye["candidate_ids"]) == (
        "ambiguous", ["dodson_hilton:Tiye B Mereniset", "dodson_hilton:Tiye C"],
        ["dodson_hilton:Tiye A", "dodson_hilton:Tiye B Mereniset", "dodson_hilton:Tiye C"])
    assert r["brooklyn-5", "title", "Akhenaten"]["resolution"] is None
    row = r["met-1", "subregion", "Thebes"]
    assert {k: row[k] for k in ("museum", "entity_type", "evidence_role", "mention_text")} == {
        "museum": "met", "entity_type": "site", "evidence_role": "From Egypt:subregion", "mention_text": "Thebes"}
    assert json.loads(json.dumps(rows)) == rows  # every row is plain JSON, as step 2 writes it


def test_the_literal_mode_is_the_plain_text_baseline() -> None:
    rows = by_text(al.resolve_mentions(MENTIONS, "literal", None, no_context(MENTIONS)))
    reign, title = rows["met-1", "reign", "Amenhotep III"], rows["met-1", "title", "Amenhotep III"]
    assert reign["target_ids"] == title["target_ids"] == [al.literal_target("ruler", "amenhotep  III")]
    assert (reign["status"], reign["authority"], reign["resolver_version"], reign["mode"], reign["resolution"]) == (
        "resolved", "literal", al.snapshot("literal")["resolver_version"], "literal", None)
    assert rows["met-2", "title", "Ahmose"]["target_ids"] == [al.literal_target("ruler", "Ahmose")]
    assert al.literal_target("ruler", "Ahmose") != al.literal_target("site", "Ahmose")
    assert rows["brooklyn-5", "geographicalLocations[0].name", "KV 62"]["target_ids"] == [
        al.literal_target("tomb_monument", "kv 62")]
    # Abstentions do not depend on the mode.
    assert (rows["brooklyn-5", "title", "Akhenaten"]["status"], rows["brooklyn-5", "title", "Akhenaten"]["reason"]) == (
        "abstained", "expression:multi_or_range")


def test_a_link_joins_a_record_to_a_target_on_its_resolved_mentions(authority) -> None:
    rows = al.resolve_mentions(MENTIONS, "authority", authority, no_context(MENTIONS))
    version = authority.snapshot["resolver_version"]
    ids = {(r["artifact_id"], r["field_path"], r["mention_text"]): r["mention_id"] for r in rows}
    assert al.build_links(rows) == [
        {"artifact_id": "brooklyn-5", "museum": "brooklyn", "entity_type": "site", "target_id": SITE_DEIR_EL_BAHRI,
         "relation": "identity", "mode": "authority", "resolver_version": version,
         "mention_ids": [ids["brooklyn-5", "geographicalLocations[0].name", "Deir el-Bahri"]],
         "evidence_roles": ["Excavation Site"]},
        {"artifact_id": "brooklyn-5", "museum": "brooklyn", "entity_type": "tomb_monument", "target_id": TOMB_KV62,
         "relation": "identity", "mode": "authority", "resolver_version": version,
         "mention_ids": [ids["brooklyn-5", "geographicalLocations[0].name", "KV 62"]], "evidence_roles": ["role"]},
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
        al.resolve_mentions(MENTIONS, "fuzzy", authority, no_context(MENTIONS))
    with pytest.raises(ValueError, match="needs the authority"):
        al.resolve_mentions(MENTIONS, "authority", None, no_context(MENTIONS))
    with pytest.raises(ValueError, match="unclassified entity type: dynasty"):
        al.resolve_mentions([{**MENTIONS[0], "entity_type": "dynasty"}], "literal", None, no_context([{**MENTIONS[0], "entity_type": "dynasty"}]))


def test_the_resolver_version_covers_every_module_and_file_the_resolution_reads(authority) -> None:
    """A fresh interpreter extracts mentions, loads the authority and resolves one mention of
    each resolved type; every `pipeline.authority` and `pipeline.enrich` module it imports and
    every repository file it opens is hashed into the version."""
    code = """
import json, sys
from pathlib import Path
repo = Path.cwd().parent
opened = set()
def hook(event, args):
    if event == "open" and isinstance(args[0], (str, Path)):
        path = Path(args[0]).resolve()
        if path.is_relative_to(repo) and path.suffix not in (".py", ".pyc"):
            opened.add(str(path.relative_to(repo)))
sys.addaudithook(hook)
from pipeline.enrich import mentions, authority_links as al
mentions_ = json.loads(sys.stdin.read())
al.resolve_mentions(mentions_, "authority", al.load_authority(),
                   {m["artifact_id"]: {"dynasty": None, "dates": (-1500, -1400)} for m in mentions_})
modules = sorted(str(Path(m.__file__).relative_to(repo)) for n, m in sys.modules.items()
                 if getattr(m, "__file__", None) and n.startswith(("pipeline.authority", "pipeline.enrich")))
print(json.dumps({"modules": modules, "opened": sorted(opened)}))
"""
    sample = [MENTIONS[0], MENTIONS[2], MENTIONS[3], MENTIONS[8]]  # a king, a site, a queen, a tomb
    out = json.loads(subprocess.run([sys.executable, "-c", code], input=json.dumps(sample), check=True,
                                    capture_output=True, text=True, cwd=al.REPO / "pipeline").stdout)
    files = authority.snapshot["files"]
    assert out["modules"] == sorted(f for f in files if f.endswith(".py"))
    assert out["opened"] == sorted(f for f in files if not f.endswith(".py"))
    assert (authority.snapshot["mode"], authority.snapshot["unicode"]) == ("authority", unicodedata.unidata_version)
    assert sorted(al.snapshot("literal")["files"]) == [
        "pipeline/pipeline/authority/resolver.py", "pipeline/pipeline/enrich/authority_links.py",
        "pipeline/pipeline/enrich/mentions.py"]


def test_the_qualified_scopes_are_the_evaluations_verdicts() -> None:
    """`QUALIFIED_SCOPES` holds the sites #337 published as qualifying
    (`decision_rule.qualifying_scopes`) and the rulers the 2026-10-16 re-registration qualified
    (`scope_dispositions`), which replaced #361's ruler qualification and #337's ruler result.
    Every other scope of a resolved type is unevaluated."""
    evaluations = al.REPO / "docs/evaluations"
    sites = json.loads((evaluations / "authority-independent-control-2026-10-11/results/real-adjudicated-score.json")
                       .read_text(encoding="utf-8"))
    rulers = json.loads((evaluations / "ruler-reregistration-2026-10-16/results/real-adjudicated-score.json")
                        .read_text(encoding="utf-8"))
    assert sites["decision_rule"]["verdict"] == rulers["decision_rule"]["verdict"] == "CONTINUE"
    published = {tuple(scope.split("__")) for scope in sites["decision_rule"]["qualifying_scopes"]
                 if scope.startswith("site__")}
    published |= {tuple(scope.split("__")) for scope, outcome in rulers["scope_dispositions"].items()
                  if outcome == "qualified"}
    ours = {(t, *pair) for t, pairs in al.QUALIFIED_SCOPES.items() for pair in pairs}
    assert ours == published == {("site", "met", "brooklyn"), ("site", "met", "harvard"),
                                 ("site", "brooklyn", "harvard"), ("ruler", "met", "walters")}
    assert set(al.QUALIFIED_SCOPES) == set(al.RESOLVED_TYPES)
    assert all(pair in al.MUSEUM_PAIRS for pairs in al.QUALIFIED_SCOPES.values() for pair in pairs)


def test_the_committed_promotion_check_holds_and_is_of_the_frozen_inputs() -> None:
    """`docs/evaluations/authority-bridge-338/results/promotion-check.json`: the production step
    on the frozen corpus gives #361's mentions and resolutions but for #369's changes, which it
    gives as #369 measured them, and #337's site and tomb resolutions and literal targets. The
    run files it compared against are the ones #361's run manifest pins. (The snapshot it records
    names the code it measured; the live guards against drift are the identity tests.)"""
    evaluations = al.REPO / "docs/evaluations"
    result = json.loads((evaluations / "authority-bridge-338/results/promotion-check.json").read_text(encoding="utf-8"))
    proof = json.loads((evaluations / "ruler-reregistration-2026-10-15/results/real-run-manifest.json").read_text(
        encoding="utf-8"))["identical_mentions_proof"]
    assert result["run_361_files"] == {
        "mentions.ndjson.gz": proof["mention_ledger"]["gzip_sha256"],
        "current-authority-arm.ndjson.gz": proof["current_authority_arm"]["gzip_sha256"],
        "typed-literal-arm.ndjson.gz": proof["typed_literal_arm"]["gzip_sha256"]}
    changes_369 = json.loads((evaluations / "resolver-gaps-369/results/resolver-change.json").read_text(
        encoding="utf-8"))["royal_woman_cued_mentions"]
    assert result["mentions"] == {"production": 148964, "ledger_361": 148964, "rows_equal": True}
    rulers = result["rulers_vs_361_authority_arm"]
    assert (rulers["compared"], len(rulers["differ_as_369_measured"]), rulers["differ_otherwise"]) == (
        11648, changes_369["changed"], [])
    assert result["places_vs_linkability_adapter"] == {
        "compared": {"site": 113738, "tomb_monument": 4863}, "differ": {"site": [], "tomb_monument": []}}
    assert result["rulers_vs_361_literal_arm"] == {"compared": 11648, "differ": []}
    assert result["places_vs_337_literal_arm"] == {"compared": 118601, "differ": []}
    assert set(result["snapshot"]) == {"authority", "literal"}
    check = result["check_inputs"]
    assert (check["canonical_records"], check["passed"]) == (36245, True)
    # It names the code it ran, the whole closure a fresh interpreter loads to import the check
    # (the mappers, the canonical model and source types, the package `__init__`s), and the
    # libraries. (Not compared with the live files: an edit to a mapper must not turn main red;
    # every run re-checks its inputs.)
    assert {"pipeline/pipeline/__init__.py", "pipeline/pipeline/enrich/__init__.py", "pipeline/pipeline/enrich/inputs.py",
            "pipeline/pipeline/assets/__init__.py", "pipeline/pipeline/assets/normalize/__init__.py",
            "pipeline/pipeline/assets/normalize/met.py", "pipeline/pipeline/assets/normalize/brooklyn.py",
            "pipeline/pipeline/assets/normalize/harvard.py", "pipeline/pipeline/types/__init__.py",
            "pipeline/pipeline/types/canonical.py", "pipeline/pipeline/types/sources.py",
            "pipeline/pipeline/types/protocol.py"} <= set(check["code_sha256"])
    assert check["pydantic"] and len(check["uv_lock_sha256"]) == 64
