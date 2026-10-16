"""The authority links written as versioned files (#338 step 2): a run is a function of its
inputs and code, byte for byte; a withdrawn decision removes its link, and the diff says why."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import subprocess
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
        len(canonical), lf.input_digest(canonical, raw), hashlib.sha256(Path(lf.__file__).read_bytes()).hexdigest())
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
        assert lf.content_sha256(name, (run / name).read_bytes()) == f["content_sha256"]
    assert json.loads((run / "manifest.json").read_text()) == manifest
    # The files hold exactly what the step makes, row for row.
    found, _ = extract_mentions(canonical, raw)
    assert lf.read_rows(run / "mentions.ndjson.gz") == found
    for mode in al.MODES:
        resolutions = lf.typed(al.resolve_mentions(found, mode, authority if mode == "authority" else None))
        assert lf.read_rows(run / f"resolutions-{mode}.ndjson.gz") == resolutions
        assert lf.read_rows(run / f"links-{mode}.ndjson.gz") == lf.typed_links(al.build_links(resolutions), resolutions)
    version = authority.snapshot["resolver_version"]
    rows = lf.read_rows(run / "resolutions-authority.ndjson.gz")
    reign = next(r for r in rows if r["artifact_id"] == "met-900001" and r["field_path"] == "reign")
    assert reign == {
        "artifact_id": "met-900001", "authority": "kings", "entity_type": "ruler", "evidence_role": "catalogued_reign",
        "field_path": "reign", "mention_id": reign["mention_id"], "mention_text": "Amenhotep III", "mode": "authority",
        "museum": "met", "reason": None, "resolver_version": version, "status": "resolved",
        "target_ids": ["cluster-beckerath-18.09"], "target_kind": "king",
        "resolution": {"authority": "kings", "context_rule": None, "normalized_keys": ["amenhotepiii"],
                       "raw_exact_status": "unique", "raw_exact_target_ids": ["cluster-beckerath-18.09"],
                       "resolution_method": "raw_exact", "status": "resolved", "target_ids": ["cluster-beckerath-18.09"]}}
    egypt = next(r for r in rows if r["artifact_id"] == "brooklyn-118436" and r["mention_text"] == "Egypt")
    assert {k: egypt[k] for k in ("status", "reason", "target_ids", "target_kind", "resolution")} == {
        "status": "unmatched", "reason": "authority_unmatched", "target_ids": [], "target_kind": None,
        "resolution": {"authority": "idai", "normalized_keys": ["egypt"], "raw_exact_status": "unmatched",
                       "raw_exact_target_ids": [], "resolution_method": None, "status": "unmatched", "target_ids": []}}
    tomb = next(l for l in links(run) if l["target_id"] == "pm_theban:KV62")
    assert tomb == {"artifact_id": "met-900001", "entity_type": "tomb_monument", "evidence_roles": ["From Egypt:subregion"],
                    "mention_ids": tomb["mention_ids"], "mode": "authority", "museum": "met", "relation": "identity",
                    "resolver_version": version, "target_id": "pm_theban:KV62", "target_kind": "tomb"}
    assert len(tomb["mention_ids"]) == 1 and tomb["mention_ids"][0].startswith("mention-")
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


def test_a_run_that_differs_from_its_files_on_disk_fails_loud_and_says_how(inputs, authority, tmp_path) -> None:
    canonical, raw = inputs
    manifest = lf.write_run(canonical, raw, tmp_path, authority)
    run = tmp_path / manifest["run_id"]
    good = (run / "links-authority.ndjson.gz").read_bytes()
    (run / "links-authority.ndjson.gz").write_bytes(lf.gzip_rows([]))
    with pytest.raises(ValueError, match="links-authority.ndjson.gz differs from a re-run"):
        lf.write_run(canonical, raw, tmp_path, authority)
    (run / "links-authority.ndjson.gz").write_bytes(good)
    manifest_bytes = (run / "manifest.json").read_bytes()
    (run / "manifest.json").unlink()
    with pytest.raises(ValueError, match="lacks manifest.json: it was changed after it was written"):
        lf.write_run(canonical, raw, tmp_path, authority)
    (run / "manifest.json").write_bytes(manifest_bytes)
    (run / "stray.txt").write_text("x")
    with pytest.raises(ValueError, match="holds files a run does not write"):
        lf.write_run(canonical, raw, tmp_path, authority)
    (run / "stray.txt").unlink()
    (tmp_path / lf.CURRENT).write_text("")
    with pytest.raises(ValueError, match="CURRENT names '', which is not a run"):
        lf.write_run(canonical, raw, tmp_path, authority)


def test_a_run_interrupted_mid_write_leaves_no_run_and_the_next_run_completes(inputs, authority, tmp_path, monkeypatch) -> None:
    canonical, raw = inputs
    real = Path.write_bytes
    calls = []

    def crash(self, data):
        calls.append(self.name)
        if len(calls) == 3:
            raise OSError("disk full")
        return real(self, data)
    monkeypatch.setattr(Path, "write_bytes", crash)
    with pytest.raises(OSError, match="disk full"):
        lf.write_run(canonical, raw, tmp_path, authority)
    monkeypatch.setattr(Path, "write_bytes", real)
    assert [p.name for p in tmp_path.iterdir() if not p.name.startswith(".")] == []
    manifest = lf.write_run(canonical, raw, tmp_path, authority)
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([lf.LOCK, lf.CURRENT, manifest["run_id"]])
    assert len(list((tmp_path / manifest["run_id"]).iterdir())) == 6


def test_two_interpreters_with_different_hash_seeds_write_the_same_run(tmp_path) -> None:
    """Determinism across processes: string-set ordering varies with PYTHONHASHSEED."""
    code = ("import sys, json; from pathlib import Path; sys.path.insert(0, 'tests'); "
            "from test_enrich_mentions import corpus, EXTRA; from pipeline.enrich import link_files as lf; "
            "c, r = corpus(EXTRA); print(json.dumps(lf.write_run(c, r, Path(sys.argv[1]))))")
    manifests = []
    for seed in ("1", "2"):
        out = subprocess.run([sys.executable, "-c", code, str(tmp_path / seed)], check=True, capture_output=True,
                             text=True, cwd=al.REPO / "pipeline", env={**os.environ, "PYTHONHASHSEED": seed})
        manifests.append(json.loads(out.stdout))
    assert manifests[0] == manifests[1]
    run = manifests[0]["run_id"]
    for name in manifests[0]["files"]:
        a, b = (tmp_path / "1" / run / name).read_bytes(), (tmp_path / "2" / run / name).read_bytes()
        assert lf.content_sha256(name, a) == lf.content_sha256(name, b)


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
    assert diff["authority"]["changed"] == []
    # Going back to the first inputs makes the first run current again, with its own diff.
    assert lf.write_run(canonical, raw, tmp_path, authority) == first
    assert (tmp_path / lf.CURRENT).read_text() == first["run_id"] + "\n"
    back = json.loads((tmp_path / "diffs" / f"{second['run_id']}-to-{first['run_id']}.json").read_text())
    assert sorted((a["artifact_id"], a["target_id"]) for a in back["authority"]["added"]) == sorted(removed)
    assert (back["authority"]["removed"], back["authority"]["changed"]) == ([], [])
    assert sorted((a["artifact_id"], a["entity_type"]) for a in back["literal"]["added"]) == sorted(
        (r["artifact_id"], r["entity_type"]) for r in diff["literal"]["removed"])
    assert (back["literal"]["removed"], back["literal"]["changed"]) == ([], [])


def test_a_mention_withdrawn_from_a_link_another_still_makes_is_a_change(inputs, authority, tmp_path) -> None:
    canonical, raw = inputs
    raw1 = copy.deepcopy(raw)
    raw1["met"]["900001"]["title"] = "Relief of King Amenhotep III"
    first = lf.write_run(canonical, raw1, tmp_path, authority)
    king = next(l for l in links(tmp_path / first["run_id"]) if l["target_id"] == "cluster-beckerath-18.09"
                and l["artifact_id"] == "met-900001")
    assert len(king["mention_ids"]) == 2
    second = lf.write_run(canonical, raw, tmp_path, authority)
    diff = json.loads((tmp_path / "diffs" / f"{first['run_id']}-to-{second['run_id']}.json").read_text())
    (title_mention,) = set(king["mention_ids"]) - {
        l for l in next(l for l in links(tmp_path / second["run_id"]) if l["target_id"] == "cluster-beckerath-18.09"
                        and l["artifact_id"] == "met-900001")["mention_ids"]}
    changed = [c for c in diff["authority"]["changed"] if c["target_id"] == "cluster-beckerath-18.09"]
    assert changed == [{"artifact_id": "met-900001", "museum": "met", "entity_type": "ruler",
                        "target_id": "cluster-beckerath-18.09", "previous_mention_ids": king["mention_ids"],
                        "mention_ids": sorted(set(king["mention_ids"]) - {title_mention}),
                        "lost": [{"mention_id": title_mention, "status": "gone"}]}]
    assert all(l["target_id"] != "cluster-beckerath-18.09" for l in diff["authority"]["removed"])


def test_every_museum_has_a_field_inventory_the_extractor_reads() -> None:
    """Each museum with an ingest asset (`test_structure`) has its evidence fields named in
    `extract_mentions`; its fixtures give mentions from exactly these fields. (A museum without
    an inventory fails loud there, on the lookup of its ruler fields.)"""
    assert {s.value for s in _implemented_museums()} == set(MAPPERS)
    canonical, raw = corpus()
    found, _ = extract_mentions(canonical, raw)
    paths = {museum: sorted({m["field_path"] for m in found if m["museum"] == museum}) for museum in MAPPERS}
    assert paths == {"met": ["country", "excavation", "locale", "locus", "region", "reign", "subregion", "title"],
                     "brooklyn": ["geographicalLocations[0].name"], "harvard": ["places[0].displayname", "title"]}
    with pytest.raises(KeyError, match="louvre"):
        extract_mentions([{**canonical[0], "source_museum": "louvre"}], {"louvre": {canonical[0]["source_id"]: {}}})


def test_a_run_while_another_holds_the_root_fails_loud_and_changes_nothing(inputs, authority, tmp_path) -> None:
    canonical, raw = inputs
    first = lf.write_run(canonical, raw, tmp_path, authority)
    raw2 = copy.deepcopy(raw)
    raw2["met"]["900001"]["title"] = "Scarab"
    before = sorted(p.name for p in tmp_path.iterdir())
    with open(tmp_path / lf.LOCK, "a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="another run holds .*runs under one root must not overlap"):
            lf.write_run(canonical, raw2, tmp_path, authority)
        fcntl.flock(handle, fcntl.LOCK_UN)
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    assert (tmp_path / lf.CURRENT).read_text() == first["run_id"] + "\n"
    # Released, the next run goes ahead.
    assert lf.write_run(canonical, raw2, tmp_path, authority)["run_id"] != first["run_id"]
