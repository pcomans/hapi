"""The authority links written as versioned files (#338 step 2): a run is a function of its
inputs and code, byte for byte; a withdrawn decision removes its link, and the diff says why."""

from __future__ import annotations

import copy
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from pipeline.authority import resolver
from pipeline.enrich import authority_links as al, link_files as lf
from pipeline.enrich.mentions import extract_mentions

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_enrich_mentions import EXTRA, MAPPERS, corpus  # noqa: E402  (the museum fixtures as a corpus)
from test_structure import _implemented_museums  # noqa: E402

THEBES = "idai:2042921"


@pytest.fixture(scope="module")
def authority() -> al.Authority:
    return al.load_authority()


@pytest.fixture(scope="module")
def inputs():
    return corpus(EXTRA)


def links(run: Path, mode: str = "authority") -> list[dict]:
    return lf.read_rows(run / f"links-{mode}.ndjson.gz")


def test_a_run_writes_both_modes_and_a_manifest_that_inventories_what_is_not_resolved(inputs, authority, tmp_path) -> None:
    canonical, raw = inputs
    manifest = lf.write_run(canonical, raw, tmp_path, authority)
    run = tmp_path / manifest["run_id"]
    assert (tmp_path / lf.CURRENT).read_text() == manifest["run_id"] + "\n"
    assert sorted(p.name for p in run.iterdir()) == [
        "links-authority.ndjson.gz", "links-literal.ndjson.gz", "manifest.json", "mentions.ndjson.gz",
        "resolutions-authority.ndjson.gz", "resolutions-literal.ndjson.gz"]
    assert {name: f["rows"] for name, f in manifest["files"].items()} == {
        "links-authority.ndjson.gz": 14, "links-literal.ndjson.gz": 49, "mentions.ndjson.gz": 60,
        "resolutions-authority.ndjson.gz": 60, "resolutions-literal.ndjson.gz": 60}
    assert (manifest["records"], manifest["inputs_sha256"], manifest["writer_sha256"]) == (
        len(canonical), lf.input_digest(canonical, raw), lf.hashlib.sha256(Path(lf.__file__).read_bytes()).hexdigest())
    assert manifest["snapshots"] == {"authority": authority.snapshot, "literal": al.snapshot("literal")}
    assert manifest["outcomes"]["authority"] == {
        "excavation|abstained|unsupported:excavation": 4, "ruler|abstained|expression:multi_or_range": 5,
        "ruler|abstained|expression:uncertain_identity": 1, "ruler|resolved|": 4,
        "ruler|unmatched|authority_unmatched": 1, "site|resolved|": 9, "site|unmatched|authority_unmatched": 34,
        "temple|abstained|unsupported:temple": 1, "tomb_monument|resolved|": 1}
    assert manifest["inventory"] == {
        "unsupported": {"excavation": {"reason": "no committed canonical excavation authority", "mentions": 4},
                        "temple": {"reason": "no committed canonical temple authority", "mentions": 1}},
        "unevaluated_scopes": {"ruler": [["met", "harvard"], ["brooklyn", "harvard"]], "site": [],
                               "tomb_monument": [["met", "brooklyn"], ["met", "harvard"], ["brooklyn", "harvard"]]},
    }
    for name, f in manifest["files"].items():
        assert lf.hashlib.sha256((run / name).read_bytes()).hexdigest() == f["sha256"]
    assert json.loads((run / "manifest.json").read_text()) == manifest
    # Queens are typed apart from kings; a woman who reigned is her king.
    kinds = {(l["artifact_id"], l["target_id"]): l["target_kind"] for l in links(run)}
    assert kinds[("met-900001", "dodson_hilton:Ahmes B")] == "royal_woman"
    assert kinds[("met-900001", "cluster-beckerath-18.09")] == "king"
    assert kinds[("met-900001", "pm_theban:KV62")] == "tomb"
    assert kinds[("met-900001", THEBES)] == "site"
    assert kinds[("harvard-289668", "leprohon-leprohon-33.02a")] == "king"
    assert {l["target_kind"] for l in links(run, "literal")} == {"literal"}
    assert {l["relation"] for l in links(run) + links(run, "literal")} == {"identity"}


def test_the_same_inputs_and_code_give_the_same_run_byte_for_byte(inputs, authority, tmp_path) -> None:
    canonical, raw = inputs
    first = lf.write_run(canonical, raw, tmp_path / "a", authority)
    second = lf.write_run(list(reversed(canonical)), raw, tmp_path / "b", authority)
    assert first == second
    for name in first["files"]:
        assert (tmp_path / "a" / first["run_id"] / name).read_bytes() == (tmp_path / "b" / first["run_id"] / name).read_bytes()
    # Again into the same root: checked, not rewritten, and no diff.
    assert lf.write_run(canonical, raw, tmp_path / "a", authority) == first
    assert not (tmp_path / "a" / "diffs").exists()


def test_a_run_that_differs_from_its_files_on_disk_fails_loud(inputs, authority, tmp_path) -> None:
    canonical, raw = inputs
    manifest = lf.write_run(canonical, raw, tmp_path, authority)
    (tmp_path / manifest["run_id"] / "links-authority.ndjson.gz").write_bytes(lf.gzip_rows([]))
    with pytest.raises(ValueError, match="differs from a re-run"):
        lf.write_run(canonical, raw, tmp_path, authority)


def test_a_withdrawn_decision_removes_its_link_and_the_diff_says_why(inputs, authority, tmp_path) -> None:
    canonical, raw = inputs
    first = lf.write_run(canonical, raw, tmp_path, authority)
    before = {(l["artifact_id"], l["target_id"]) for l in links(tmp_path / first["run_id"])}
    assert {("met-546960", THEBES), ("brooklyn-4035", "idai:2042907"), ("met-900001", "dodson_hilton:Ahmes B")} <= before

    # The authority withdraws Thebes; a record is gone; another's royal-woman mention is gone.
    rows = [r for r in resolver.load_jsonl(resolver.IDAI) if r.get("id") != THEBES]
    withdrawn = replace(authority, sites=resolver.build_site_resolver(rows)[0],
                        snapshot={**authority.snapshot, "resolver_version": "thebes-withdrawn"})
    canonical2 = [r for r in canonical if r["id"] != "brooklyn-4035"]
    raw2 = copy.deepcopy(raw)
    raw2["met"]["900001"]["title"] = "Scarab"
    second = lf.write_run(canonical2, raw2, tmp_path, withdrawn)
    assert second["run_id"] != first["run_id"]
    assert (tmp_path / lf.CURRENT).read_text() == second["run_id"] + "\n"
    diff = json.loads((tmp_path / "diffs" / f"{first['run_id']}-to-{second['run_id']}.json").read_text())
    assert (diff["previous_run"], diff["run"]) == (first["run_id"], second["run_id"])
    removed = {(r["artifact_id"], r["target_id"]): r for r in diff["authority"]["removed"]}
    assert sorted(removed) == [("brooklyn-118436", THEBES), ("brooklyn-4035", "idai:2042907"),
                               ("met-546960", THEBES), ("met-900001", "dodson_hilton:Ahmes B"), ("met-900001", THEBES)]
    assert removed[("brooklyn-4035", "idai:2042907")]["why"] == "record_gone"
    assert removed[("met-900001", "dodson_hilton:Ahmes B")]["why"] == "mentions_gone"
    thebes = removed[("met-546960", THEBES)]
    assert (thebes["why"], [(n["status"], n["reason"], n["target_ids"]) for n in thebes["now"]]) == (
        "resolves_otherwise", [("unmatched", "authority_unmatched", [])])
    assert diff["authority"]["added"] == []
    assert diff["authority"]["kept"] == len(before) - 5
    # The literal links lose the gone record's and the gone mention's, and gain the new title's none.
    assert {(r["artifact_id"], r["why"]) for r in diff["literal"]["removed"]} == {
        ("brooklyn-4035", "record_gone"), ("met-900001", "mentions_gone")}
    # Going back to the first inputs makes the first run current again, with its own diff.
    assert lf.write_run(canonical, raw, tmp_path, authority) == first
    back = json.loads((tmp_path / "diffs" / f"{second['run_id']}-to-{first['run_id']}.json").read_text())
    assert sorted((a["artifact_id"], a["target_id"]) for a in back["authority"]["added"]) == sorted(removed)


@pytest.mark.parametrize("museum", sorted(MAPPERS))
def test_every_museum_has_a_field_inventory_the_extractor_reads(museum) -> None:
    """Each museum with an ingest asset (`test_structure`) has its evidence fields named in
    `extract_mentions`: its fixtures yield mentions, of rulers or sites."""
    assert {s.value for s in _implemented_museums()} == set(MAPPERS)
    canonical, raw = corpus()
    found, _ = extract_mentions([r for r in canonical if r["source_museum"] == museum], {museum: raw[museum]})
    assert {m["entity_type"] for m in found} & {"ruler", "site"}
