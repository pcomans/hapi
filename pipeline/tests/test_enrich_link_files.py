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
from pipeline.enrich.inputs import normalized
from pipeline.enrich.mentions import extract_all_mentions

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_enrich_mentions import EXTRA, MAPPERS, corpus  # noqa: E402  (the museum fixtures as a corpus)
from test_structure import _implemented_museums  # noqa: E402

THEBES = "idai:2042921"


@pytest.fixture(scope="module")
def authority() -> al.Authority:
    return al.load_authority()


@pytest.fixture(scope="module")
def inputs():
    """The fixture corpus as the normalize step leaves the tables (Brooklyn keeps only Egyptian
    records)."""
    _, raw = corpus(EXTRA)
    return normalized(raw), raw


def links(run: Path, mode: str = "authority") -> list[dict]:
    return lf.read_rows(run / f"links-{mode}.ndjson.gz")


def test_a_run_writes_both_modes_and_a_manifest_that_inventories_what_is_not_resolved(inputs, authority, tmp_path) -> None:
    canonical, raw = inputs
    manifest = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    run = tmp_path / manifest["run_id"]
    assert (tmp_path / lf.CURRENT).read_text() == manifest["run_id"] + "\n"
    assert sorted(p.name for p in run.iterdir()) == [
        "links-authority.ndjson.gz", "links-literal.ndjson.gz", "manifest.json", "mentions.ndjson.gz",
        "resolutions-authority.ndjson.gz", "resolutions-literal.ndjson.gz"]
    assert {name: f["rows"] for name, f in manifest["files"].items()} == {
        "links-authority.ndjson.gz": 14, "links-literal.ndjson.gz": 48, "mentions.ndjson.gz": 59,
        "resolutions-authority.ndjson.gz": 59, "resolutions-literal.ndjson.gz": 59}
    assert manifest["canonical_rows_set_aside"] == []
    assert manifest["run_id"] == lf.manifest_digest(manifest)
    assert (manifest["records"], manifest["inputs_sha256"], manifest["writer_sha256"]) == (
        len(canonical), lf.input_digest(canonical, raw), hashlib.sha256(Path(lf.__file__).read_bytes()).hexdigest())
    assert manifest["snapshots"] == {"authority": authority.snapshot, "literal": al.snapshot("literal")}
    assert manifest["extraction"] == extract_all_mentions(canonical, raw)[1]
    assert {k: manifest["extraction"][k] for k in ("records_scanned", "mentions")} == {"records_scanned": 17, "mentions": 59}
    assert manifest["outcomes"]["authority"] == {
        "excavation|abstained|unsupported:excavation": 4, "ruler|abstained|expression:multi_or_range": 5,
        "ruler|abstained|expression:uncertain_identity": 1, "ruler|resolved|": 4,
        "ruler|unmatched|authority_unmatched": 1, "site|resolved|": 9, "site|unmatched|authority_unmatched": 33,
        "temple|abstained|unsupported:temple": 1, "tomb_monument|resolved|": 1}
    assert manifest["inventory"] == {
        "unsupported": {"excavation": {"reason": "no committed canonical excavation authority", "mentions": 4},
                        "temple": {"reason": "no committed canonical temple authority", "mentions": 1}},
        "unevaluated_scopes": {
            "ruler": [["met", "harvard"], ["brooklyn", "harvard"], ["met", "cleveland"], ["brooklyn", "cleveland"],
                      ["harvard", "cleveland"]],
            "site": [["met", "cleveland"], ["brooklyn", "cleveland"], ["harvard", "cleveland"]],
            "tomb_monument": [["met", "brooklyn"], ["met", "harvard"], ["brooklyn", "harvard"], ["met", "cleveland"],
                              ["brooklyn", "cleveland"], ["harvard", "cleveland"]]},
    }
    for name, f in manifest["files"].items():
        assert lf.content_sha256(name, (run / name).read_bytes()) == f["content_sha256"]
    assert json.loads((run / "manifest.json").read_text()) == manifest
    # The files hold exactly what the step makes, row for row.
    found, _ = extract_all_mentions(canonical, raw)
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
    first = lf.write_run(tmp_path / "a", lambda: (canonical, raw), authority)
    second = lf.write_run(tmp_path / "b", lambda: (list(reversed(canonical)), raw), authority)
    assert first == second
    for name in first["files"]:
        assert (tmp_path / "a" / first["run_id"] / name).read_bytes() == (tmp_path / "b" / first["run_id"] / name).read_bytes()
    # Again into the same root: checked, not rewritten, and no diff.
    assert lf.write_run(tmp_path / "a", lambda: (canonical, raw), authority) == first
    assert not (tmp_path / "a" / "diffs").exists()


def test_a_run_that_differs_from_its_files_on_disk_fails_loud_and_says_how(inputs, authority, tmp_path) -> None:
    canonical, raw = inputs
    manifest = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    run = tmp_path / manifest["run_id"]
    good = (run / "links-authority.ndjson.gz").read_bytes()
    (run / "links-authority.ndjson.gz").write_bytes(lf.gzip_rows([]))
    with pytest.raises(ValueError, match="links-authority.ndjson.gz is not what that run wrote"):
        lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    (run / "links-authority.ndjson.gz").write_bytes(good)
    manifest_bytes = (run / "manifest.json").read_bytes()
    (run / "manifest.json").write_text(json.dumps({**json.loads(manifest_bytes), "records": 1}))
    with pytest.raises(ValueError, match="manifest.json was changed after it was written"):
        lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    (run / "manifest.json").unlink()
    with pytest.raises(ValueError, match="has no manifest.json"):
        lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    (run / "manifest.json").write_bytes(manifest_bytes)
    (run / "stray.txt").write_text("x")
    with pytest.raises(ValueError, match="not the files its manifest names"):
        lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    (run / "stray.txt").unlink()
    (tmp_path / lf.CURRENT).write_text("")
    with pytest.raises(ValueError, match="CURRENT names '', which is not a run"):
        lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    (tmp_path / lf.CURRENT).write_text("f" * 64 + "\n")
    with pytest.raises(ValueError, match="CURRENT names 'f{64}', which is not a run"):
        lf.write_run(tmp_path, lambda: (canonical, raw), authority)


def test_a_run_interrupted_mid_write_leaves_no_run_and_the_next_run_clears_it(inputs, authority, tmp_path, monkeypatch) -> None:
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
        lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    monkeypatch.setattr(Path, "write_bytes", real)
    (scratch,) = [p.name for p in tmp_path.iterdir() if p.name.endswith(".partial")]
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([lf.LOCK, scratch])
    # The retry reads other inputs (the tables changed meanwhile), so another run id: the dead
    # run's scratch directory is removed all the same.
    raw2 = copy.deepcopy(raw)
    raw2["met"]["900001"]["title"] = "Scarab"
    manifest = lf.write_run(tmp_path, lambda: (normalized(raw2), raw2), authority)
    assert scratch != f".{manifest['run_id']}.partial"
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([lf.LOCK, lf.CURRENT, manifest["run_id"]])
    assert len(list((tmp_path / manifest["run_id"]).iterdir())) == 6


def test_two_interpreters_with_different_hash_seeds_write_the_same_run(tmp_path) -> None:
    """Determinism across processes: string-set ordering varies with PYTHONHASHSEED."""
    code = ("import sys, json; from pathlib import Path; sys.path.insert(0, 'tests'); "
            "from test_enrich_mentions import corpus, EXTRA; from pipeline.enrich import link_files as lf; "
            "from pipeline.enrich.inputs import normalized; "
            "_, r = corpus(EXTRA); print(json.dumps(lf.write_run(Path(sys.argv[1]), lambda: (normalized(r), r))))")
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
    first = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    before = {(l["artifact_id"], l["target_id"]) for l in links(tmp_path / first["run_id"])}
    assert {("met-546960", THEBES), ("brooklyn-4035", "idai:2042907"), ("met-900001", "dodson_hilton:Ahmes B")} <= before

    # The authority withdraws Thebes; a record is gone; another's royal-woman mention is gone.
    rows = [r for r in resolver.load_jsonl(resolver.IDAI) if r.get("id") != THEBES]
    withdrawn = replace(authority, sites=resolver.build_site_resolver(rows)[0],
                        snapshot={**authority.snapshot, "resolver_version": "thebes-withdrawn"})
    raw2 = copy.deepcopy(raw)
    del raw2["brooklyn"]["4035"]
    raw2["met"]["900001"]["title"] = "Scarab"
    canonical2 = normalized(raw2)
    second = lf.write_run(tmp_path, lambda: (canonical2, raw2), withdrawn)
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
    assert lf.write_run(tmp_path, lambda: (canonical, raw), authority) == first
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
    first = lf.write_run(tmp_path, lambda: (normalized(raw1), raw1), authority)
    king = next(l for l in links(tmp_path / first["run_id"]) if l["target_id"] == "cluster-beckerath-18.09"
                and l["artifact_id"] == "met-900001")
    assert len(king["mention_ids"]) == 2
    second = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    diff = json.loads((tmp_path / "diffs" / f"{first['run_id']}-to-{second['run_id']}.json").read_text())
    (title_mention,) = set(king["mention_ids"]) - {
        l for l in next(l for l in links(tmp_path / second["run_id"]) if l["target_id"] == "cluster-beckerath-18.09"
                        and l["artifact_id"] == "met-900001")["mention_ids"]}
    changed = [c for c in diff["authority"]["changed"] if c["target_id"] == "cluster-beckerath-18.09"]
    assert changed == [{"artifact_id": "met-900001", "museum": "met", "entity_type": "ruler",
                        "target_id": "cluster-beckerath-18.09", "previous_mention_ids": king["mention_ids"],
                        "mention_ids": sorted(set(king["mention_ids"]) - {title_mention}),
                        "previous_evidence_roles": ["catalogued_reign", "explicit_royal_text_cue"],
                        "evidence_roles": ["catalogued_reign"],
                        "lost": [{"mention_id": title_mention, "status": "gone"}]}]
    assert all(l["target_id"] != "cluster-beckerath-18.09" for l in diff["authority"]["removed"])


def test_every_museum_has_a_field_inventory_the_extractor_reads() -> None:
    """Each museum with an ingest asset (`test_structure`) has its evidence fields named in
    `extract_all_mentions`; its fixtures give mentions from exactly these fields. (A museum without
    an inventory fails loud there, on the lookup of its ruler fields.)"""
    assert {s.value for s in _implemented_museums()} == set(MAPPERS) | {"cleveland"}
    canonical, raw = corpus(with_cleveland=True)
    found, _ = extract_all_mentions(canonical, raw)
    paths = {museum: sorted({m["field_path"] for m in found if m["museum"] == museum}) for museum in (*MAPPERS, "cleveland")}
    assert paths == {"met": ["country", "excavation", "locale", "locus", "region", "reign", "subregion", "title"],
                     "brooklyn": ["geographicalLocations[0].name"], "harvard": ["places[0].displayname", "title"],
                     "cleveland": ["culture[0]"]}
    with pytest.raises(KeyError, match="louvre"):
        extract_all_mentions([{**canonical[0], "source_museum": "louvre"}], {"louvre": {canonical[0]["source_id"]: {}}})


def test_a_run_while_another_holds_the_root_fails_loud_and_changes_nothing(inputs, authority, tmp_path) -> None:
    canonical, raw = inputs
    first = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    raw2 = copy.deepcopy(raw)
    raw2["met"]["900001"]["title"] = "Scarab"
    before = sorted(p.name for p in tmp_path.iterdir())
    with open(tmp_path / lf.LOCK, "a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="another run holds .*runs under one root must not overlap"):
            lf.write_run(tmp_path, lambda: (normalized(raw2), raw2), authority)
        fcntl.flock(handle, fcntl.LOCK_UN)
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    assert (tmp_path / lf.CURRENT).read_text() == first["run_id"] + "\n"
    # Released, the next run goes ahead.
    assert lf.write_run(tmp_path, lambda: (normalized(raw2), raw2), authority)["run_id"] != first["run_id"]


def test_a_previous_run_whose_links_were_changed_is_not_diffed_against(inputs, authority, tmp_path) -> None:
    canonical, raw = inputs
    first = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    path = tmp_path / first["run_id"] / "links-authority.ndjson.gz"
    path.write_bytes(lf.gzip_rows(lf.read_rows(path)[1:]))
    raw2 = copy.deepcopy(raw)
    raw2["met"]["900001"]["title"] = "Scarab"
    with pytest.raises(ValueError, match="links-authority.ndjson.gz is not what that run wrote"):
        lf.write_run(tmp_path, lambda: (normalized(raw2), raw2), authority)
    assert (tmp_path / lf.CURRENT).read_text() == first["run_id"] + "\n"
    assert not (tmp_path / "diffs").exists()
    assert sorted(p.name for p in tmp_path.iterdir() if not p.name.startswith(".")) == sorted([lf.CURRENT, first["run_id"]])


def lock_held(root: Path) -> bool:
    with open(root / lf.LOCK, "a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle, fcntl.LOCK_UN)
        return False


class RecordingConnection:
    """A stand-in for the asset's database connection, over the fixture corpus as the tables
    hold it (canonical rows; raw payloads as JSON text keyed by object id). It records, at each
    read, whether the run lock is held, which transaction it is in and its isolation level."""

    def __init__(self, tables: dict[str, list[dict]], root: Path, log: list) -> None:
        self.tables, self.root, self.log = tables, root, log
        self.isolation, self.transaction, self.transactions = None, None, 0

    def execution_options(self, isolation_level=None, **_):
        self.isolation = isolation_level
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def begin(self):
        conn = self

        class Transaction:
            def __enter__(self):
                conn.transactions += 1
                conn.transaction = conn.transactions

            def __exit__(self, *exc):
                conn.transaction = None
                return False
        return Transaction()

    def execute(self, statement):
        (table,) = statement.get_final_froms()
        self.log.append(("read", table.name, lock_held(self.root), self.transaction, self.isolation))
        rows = self.tables[table.name]

        class Result:
            def mappings(self):
                return rows
        return Result()


def test_the_asset_reads_its_inputs_under_the_lock_from_one_snapshot(inputs, authority, tmp_path, monkeypatch) -> None:
    """The asset cannot reach a database here; over a recording connection it reads every table
    in one REPEATABLE READ transaction, with the run lock held, and writes the run its inputs
    make. (That PostgreSQL gives that transaction one snapshot is PostgreSQL's to keep; that all
    reads are in it is pinned here.)"""
    from dagster import build_asset_context
    from pipeline.assets.enrich import authority_links_asset as asset
    from pipeline.resources import DatabaseResource

    canonical, raw = inputs
    tables = {"artifacts": canonical, **{f"raw_{museum}": [{"object_id": source_id, "data": json.dumps(payload)}
                                                          for source_id, payload in rows.items()]
                                         for museum, rows in raw.items()}}
    root = tmp_path / "asset"
    log: list = []
    connections: list[RecordingConnection] = []

    class Engine:
        def connect(self):
            connections.append(RecordingConnection(tables, root, log))
            return connections[-1]

    class Database(DatabaseResource):
        def get_engine(self):
            return Engine()

    monkeypatch.setattr(lf.authority_links, "load_authority", lambda: authority)
    monkeypatch.setenv("HAPI_AUTHORITY_LINKS_DIR", str(root))
    context = build_asset_context()
    asset.authority_links(context=context, database=Database())

    (conn,) = connections
    assert conn.transactions == 1
    assert log == [("read", name, True, 1, "REPEATABLE READ")
                   for name in ("artifacts", "raw_met", "raw_brooklyn", "raw_harvard", "raw_cleveland")]
    assert not lock_held(root)
    expected = lf.write_run(tmp_path / "direct", lambda: (canonical, raw), authority)
    assert (root / lf.CURRENT).read_text() == expected["run_id"] + "\n"
    assert json.loads((root / expected["run_id"] / "manifest.json").read_text()) == expected
    assert context.get_output_metadata("result") == {
        "run_id": expected["run_id"], "records": 17, "canonical_rows_set_aside": [],
        "links_authority": expected["files"]["links-authority.ndjson.gz"]["rows"],
        "links_literal": expected["files"]["links-literal.ndjson.gz"]["rows"]}


def test_a_diff_is_published_only_if_its_run_became_current(inputs, authority, tmp_path, monkeypatch) -> None:
    canonical, raw = inputs
    a = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    raw_b, raw_c = copy.deepcopy(raw), copy.deepcopy(raw)
    raw_b["met"]["900001"]["title"] = "Scarab"
    raw_c["met"]["900001"]["title"] = "Amulet"
    real_replace, real_rename = os.replace, os.rename

    # The process dies before CURRENT is replaced: B never became current.
    def die_on_current(src, dst):
        if Path(dst).name == lf.CURRENT:
            raise OSError("killed")
        return real_replace(src, dst)
    monkeypatch.setattr(lf.os, "replace", die_on_current)
    with pytest.raises(OSError, match="killed"):
        lf.write_run(tmp_path, lambda: (normalized(raw_b), raw_b), authority)
    monkeypatch.setattr(lf.os, "replace", real_replace)
    assert (tmp_path / lf.CURRENT).read_text() == a["run_id"] + "\n"
    (stale,) = [p.name for p in (tmp_path / "diffs").iterdir()]
    assert stale.startswith(f".{a['run_id']}-to-") and stale.endswith(".json.partial")
    c = lf.write_run(tmp_path, lambda: (normalized(raw_c), raw_c), authority)
    assert sorted(p.name for p in (tmp_path / "diffs").iterdir()) == [f"{a['run_id']}-to-{c['run_id']}.json"]

    # The process dies after CURRENT is replaced, before the diff takes its name: it did happen.
    def die_on_diff(src, dst):
        if Path(dst).parent.name == "diffs" and Path(dst).name.endswith(".json"):
            raise OSError("killed")
        return real_rename(src, dst)
    monkeypatch.setattr(lf.os, "rename", die_on_diff)
    with pytest.raises(OSError, match="killed"):
        lf.write_run(tmp_path, lambda: (normalized(raw_b), raw_b), authority)
    monkeypatch.setattr(lf.os, "rename", real_rename)
    b_id = (tmp_path / lf.CURRENT).read_text().strip()
    assert b_id != c["run_id"]
    assert sorted(p.name for p in (tmp_path / "diffs").iterdir()) == sorted([
        f"{a['run_id']}-to-{c['run_id']}.json", f".{c['run_id']}-to-{b_id}.json.partial"])
    pending = json.loads((tmp_path / "diffs" / f".{c['run_id']}-to-{b_id}.json.partial").read_text())
    lf.write_run(tmp_path, lambda: (normalized(raw_b), raw_b), authority)  # the same run: no new diff, the pending one settles
    assert sorted(p.name for p in (tmp_path / "diffs").iterdir()) == sorted([
        f"{a['run_id']}-to-{c['run_id']}.json", f"{c['run_id']}-to-{b_id}.json"])
    published = json.loads((tmp_path / "diffs" / f"{c['run_id']}-to-{b_id}.json").read_text())
    assert published == pending and (published["previous_run"], published["run"]) == (c["run_id"], b_id)
    # The same transition made cleanly gives the same diff.
    clean = tmp_path / "clean"
    lf.write_run(clean, lambda: (normalized(raw_c), raw_c), authority)
    lf.write_run(clean, lambda: (normalized(raw_b), raw_b), authority)
    assert json.loads((clean / "diffs" / f"{c['run_id']}-to-{b_id}.json").read_text()) == published


def test_a_run_that_fails_its_checks_leaves_a_pending_diff_as_it_was(inputs, authority, tmp_path) -> None:
    canonical, raw = inputs
    a = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    raw_b = copy.deepcopy(raw)
    raw_b["met"]["900001"]["title"] = "Scarab"
    b = lf.write_run(tmp_path, lambda: (normalized(raw_b), raw_b), authority)
    # As a run that died after its commit leaves it.
    final = tmp_path / "diffs" / f"{a['run_id']}-to-{b['run_id']}.json"
    pending = final.with_name(f".{final.name}.partial")
    final.rename(pending)
    data = pending.read_bytes()
    (tmp_path / lf.CURRENT).write_text("")
    with pytest.raises(ValueError, match="which is not a run"):
        lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    assert pending.read_bytes() == data and not final.exists()
    (tmp_path / lf.CURRENT).write_text(b["run_id"] + "\n")
    path = tmp_path / b["run_id"] / "links-authority.ndjson.gz"
    good = path.read_bytes()
    path.write_bytes(lf.gzip_rows(lf.read_rows(path)[1:]))
    with pytest.raises(ValueError, match="is not what that run wrote"):
        lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    assert pending.read_bytes() == data and not final.exists()
    path.write_bytes(good)
    # A retry of the current run itself (no diff of its own) whose files were changed: its own
    # directory fails the check before the pending diff is settled.
    path.write_bytes(lf.gzip_rows(lf.read_rows(path)[1:]))
    with pytest.raises(ValueError, match="links-authority.ndjson.gz is not what that run wrote"):
        lf.write_run(tmp_path, lambda: (normalized(raw_b), raw_b), authority)
    assert pending.read_bytes() == data and not final.exists()
    path.write_bytes(good)
    lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    assert final.read_bytes() == data and not pending.exists()


def test_a_pending_diff_this_module_did_not_write_fails_loud(inputs, authority, tmp_path) -> None:
    canonical, raw = inputs
    current = lf.write_run(tmp_path, lambda: (canonical, raw), authority)["run_id"]
    (tmp_path / "diffs").mkdir()
    (tmp_path / "diffs" / ".notes.partial").write_text("x")
    raw_b = copy.deepcopy(raw)
    raw_b["met"]["900001"]["title"] = "Scarab"
    with pytest.raises(ValueError, match="is not a pending diff this module writes"):
        lf.write_run(tmp_path, lambda: (normalized(raw_b), raw_b), authority)
    (tmp_path / "diffs" / ".notes.partial").unlink()
    # A diff to publish (its run is current) whose content names other runs.
    (tmp_path / "diffs" / f".{'a' * 64}-to-{current}.json.partial").write_text(
        json.dumps({"previous_run": "c" * 64, "run": current}))
    with pytest.raises(ValueError, match=f"holds the diff of c{{64}} to {current}"):
        lf.write_run(tmp_path, lambda: (normalized(raw_b), raw_b), authority)


def test_a_pending_diff_cut_short_by_a_killed_process_never_blocks_the_root(inputs, authority, tmp_path) -> None:
    """A run killed while writing its pending diff left a `.writing` file; one killed before
    the commit may also have left an unreadable pending diff of a run that never became current.
    Both are discarded unread."""
    canonical, raw = inputs
    a = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    (tmp_path / "diffs").mkdir()
    (tmp_path / "diffs" / f".{a['run_id']}-to-{'b' * 64}.json.partial.writing").write_text('{"previous_')
    (tmp_path / "diffs" / f".{a['run_id']}-to-{'c' * 64}.json.partial").write_text('{"previous_')
    raw_b = copy.deepcopy(raw)
    raw_b["met"]["900001"]["title"] = "Scarab"
    b = lf.write_run(tmp_path, lambda: (normalized(raw_b), raw_b), authority)
    assert sorted(p.name for p in (tmp_path / "diffs").iterdir()) == [f"{a['run_id']}-to-{b['run_id']}.json"]


def test_a_damaged_previous_run_is_not_accepted_as_history(inputs, authority, tmp_path) -> None:
    canonical, raw = inputs
    a = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    run = tmp_path / a["run_id"]
    raw_b = copy.deepcopy(raw)
    raw_b["met"]["900001"]["title"] = "Scarab"
    for damage, message in ((lambda: (run / "mentions.ndjson.gz").write_bytes(lf.gzip_rows([])),
                             "mentions.ndjson.gz is not what that run wrote"),
                            (lambda: (run / "resolutions-literal.ndjson.gz").unlink(), "not the files its manifest names"),
                            (lambda: (run / "notes.txt").write_text("x"), "not the files its manifest names"),
                            (lambda: (run / "manifest.json").write_text(json.dumps(
                                {**json.loads((run / "manifest.json").read_text()), "run_id": "f" * 64})),
                             "holds the manifest of run f{64}"),
                            (lambda: (run / "manifest.json").write_text(json.dumps(
                                {**json.loads((run / "manifest.json").read_text()), "records": 1})),
                             "manifest.json was changed after it was written"),
                            (lambda: (run / "manifest.json").unlink(), "has no manifest.json")):
        saved = {p.name: p.read_bytes() for p in run.iterdir()}
        damage()
        with pytest.raises(ValueError, match=message):
            lf.write_run(tmp_path, lambda: (normalized(raw_b), raw_b), authority)
        assert (tmp_path / lf.CURRENT).read_text() == a["run_id"] + "\n"
        assert sorted(p.name for p in tmp_path.iterdir() if not p.name.startswith(".")) == sorted(
            [lf.CURRENT, a["run_id"]])
        for p in run.iterdir():
            p.unlink()
        for name, data in saved.items():
            (run / name).write_bytes(data)


def test_an_evidence_role_change_alone_is_a_change(inputs, authority, tmp_path) -> None:
    """The role is not part of a mention's id: a record can move its place from one role to
    another with the same text and span, and the link's evidence changes."""
    canonical, raw = inputs
    first = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    raw2 = copy.deepcopy(raw)
    raw2["met"]["900001"]["geographyType"] = "Findspot"
    second = lf.write_run(tmp_path, lambda: (normalized(raw2), raw2), authority)
    diff = json.loads((tmp_path / "diffs" / f"{first['run_id']}-to-{second['run_id']}.json").read_text())
    thebes = [c for c in diff["authority"]["changed"] if c["target_id"] == THEBES and c["artifact_id"] == "met-900001"]
    assert thebes == [{"artifact_id": "met-900001", "museum": "met", "entity_type": "site", "target_id": THEBES,
                       "previous_evidence_roles": ["From Egypt:subregion"], "evidence_roles": ["Findspot:subregion"],
                       "lost": []}]
    assert (diff["authority"]["added"], diff["authority"]["removed"]) == ([], [])


def test_inputs_that_are_not_one_pipeline_generation_are_refused(inputs, authority, tmp_path) -> None:
    from pipeline.enrich.inputs import check_inputs
    canonical, raw = inputs
    assert check_inputs(canonical, raw) == (canonical, [])
    # A raw payload re-ingested after its canonical row was written.
    raw2 = copy.deepcopy(raw)
    raw2["met"]["900001"]["title"] = "Scarab"
    with pytest.raises(ValueError, match=r"1 canonical rows are not what the normalize step makes .*'met-900001'"):
        lf.write_run(tmp_path, lambda: (canonical, raw2), authority)
    assert not (tmp_path / lf.CURRENT).exists()
    # A raw row ingested and not normalized yet; a canonical row with no raw payload.
    raw3 = copy.deepcopy(raw)
    raw3["met"]["999999"] = {**raw["met"]["900001"], "objectID": 999999}
    with pytest.raises(ValueError, match=r"1 raw rows are not normalized yet \(e.g. \['met:999999'\]\)"):
        check_inputs(canonical, raw3)
    raw4 = copy.deepcopy(raw)
    del raw4["met"]["900001"]
    with pytest.raises(ValueError, match=r"1 canonical rows have no raw payload"):
        check_inputs(canonical, raw4)



def test_a_canonical_row_the_normalize_step_no_longer_makes_is_set_aside_and_listed(inputs, authority, tmp_path) -> None:
    """A Brooklyn object re-ingested as not Egyptian keeps its old canonical row: the normalize
    assets never delete (#374). It is not the step's output, so a run leaves it out and says so,
    rather than refusing every run until someone deletes it."""
    from pipeline.enrich.inputs import check_inputs
    canonical, raw = inputs
    _, full = corpus(EXTRA)
    leftover = [r for r in corpus(EXTRA)[0] if r["id"] == "brooklyn-3198"]
    assert check_inputs(canonical + leftover, full) == (canonical, ["brooklyn-3198"])
    manifest = lf.write_run(tmp_path, lambda: (canonical + leftover, full), authority)
    assert (manifest["canonical_rows_set_aside"], manifest["records"]) == (["brooklyn-3198"], len(canonical))
    run = tmp_path / manifest["run_id"]
    assert "brooklyn-3198" not in {m["artifact_id"] for m in lf.read_rows(run / "mentions.ndjson.gz")}
    # The leftover row deleted (by hand, or by #374's fix): another run, not a collision with
    # this one, and no link moves. And back again.
    cleaned = lf.write_run(tmp_path, lambda: (canonical, full), authority)
    assert cleaned["run_id"] != manifest["run_id"] and cleaned["canonical_rows_set_aside"] == []
    assert (tmp_path / lf.CURRENT).read_text() == cleaned["run_id"] + "\n"
    diff = json.loads((tmp_path / "diffs" / f"{manifest['run_id']}-to-{cleaned['run_id']}.json").read_text())
    for mode in al.MODES:
        assert (diff[mode]["added"], diff[mode]["removed"], diff[mode]["changed"]) == ([], [], [])
    assert lf.write_run(tmp_path, lambda: (canonical + leftover, full), authority) == manifest


def test_the_links_of_a_record_set_aside_are_removed_as_set_aside_not_gone(inputs, authority, tmp_path) -> None:
    """A Brooklyn record re-ingested as not Egyptian keeps its old canonical row (#374): its
    links go, and the diff says it was set aside, not that the record is gone."""
    canonical, raw = inputs
    first = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    assert any(l["artifact_id"] == "brooklyn-118436" for l in links(tmp_path / first["run_id"]))
    raw2 = copy.deepcopy(raw)
    raw2["brooklyn"]["118436"]["constituents"] = [
        *(c for c in raw2["brooklyn"]["118436"].get("constituents") or [] if c.get("role") != "Culture"),
        {"name": "Roman", "role": "Culture"}]
    second = lf.write_run(tmp_path, lambda: (canonical, raw2), authority)
    assert second["canonical_rows_set_aside"] == ["brooklyn-118436"]
    diff = json.loads((tmp_path / "diffs" / f"{first['run_id']}-to-{second['run_id']}.json").read_text())
    for mode in al.MODES:
        gone = [r for r in diff[mode]["removed"] if r["artifact_id"] == "brooklyn-118436"]
        assert gone and {r["why"] for r in gone} == {"set_aside"}, mode


def test_the_normalizers_are_the_normalize_assets() -> None:
    from pipeline.assets.normalize import brooklyn_asset, cleveland_asset, harvard_asset, met_asset
    from pipeline.enrich.inputs import NORMALIZERS
    assert NORMALIZERS["met"] == (met_asset.MetMapper, None) and NORMALIZERS["harvard"] == (harvard_asset.HarvardMapper, None)
    assert NORMALIZERS["brooklyn"] == (brooklyn_asset.BrooklynMapper, brooklyn_asset.is_egyptian)
    assert NORMALIZERS["cleveland"] == (cleveland_asset.ClevelandMapper, cleveland_asset.is_egyptian)
    assert not hasattr(met_asset, "is_egyptian") and not hasattr(harvard_asset, "is_egyptian")
    assert set(NORMALIZERS) == {s.value for s in _implemented_museums()}


def test_every_link_field_but_the_key_and_three_is_diffed(inputs, authority, tmp_path) -> None:
    """A link's fields are pinned, so a new one must be diffed or excluded on purpose; a change
    to any diffed field, the relation and the target kind included, is a change."""
    canonical, raw = inputs
    manifest = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    (one,) = [l for l in links(tmp_path / manifest["run_id"]) if l["target_id"] == "pm_theban:KV62"]
    assert sorted(one) == sorted(lf.LINK_KEY + lf.NOT_DIFFED + (
        "relation", "target_kind", "mention_ids", "evidence_roles"))
    for field, value in (("relation", "close_match"), ("target_kind", "site"), ("evidence_roles", ["x"])):
        diff = lf.diff_links([one], [{**one, field: value}], [], {one["artifact_id"]})
        assert diff["changed"] == [{**{f: one[f] for f in ("artifact_id", "museum", "entity_type", "target_id")},
                                    f"previous_{field}": one[field], field: value, "lost": []}], field
        assert (diff["kept"], diff["added"], diff["removed"]) == (0, [], [])
    # A field a later writer adds, or drops, is a change, without a value invented for the side
    # that lacks it.
    added_field = lf.diff_links([one], [{**one, "certainty": "high"}], [], {one["artifact_id"]})["changed"]
    assert added_field == [{**{f: one[f] for f in ("artifact_id", "museum", "entity_type", "target_id")},
                            "certainty": "high", "fields_only_after": ["certainty"], "lost": []}]
    dropped = {k: v for k, v in one.items() if k != "target_kind"}
    dropped_field = lf.diff_links([one], [dropped], [], {one["artifact_id"]})["changed"]
    assert dropped_field == [{**{f: one[f] for f in ("artifact_id", "museum", "entity_type", "target_id")},
                              "previous_target_kind": "tomb", "fields_only_before": ["target_kind"], "lost": []}]
    unchanged = lf.diff_links([one], [{**one, "resolver_version": "other", "mode": "authority"}], [], {one["artifact_id"]})
    assert (unchanged["kept"], unchanged["changed"]) == (1, [])


def test_a_malformed_pending_diff_fails_the_run_before_any_pending_diff_is_touched(inputs, authority, tmp_path) -> None:
    canonical, raw = inputs
    a = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    raw_b = copy.deepcopy(raw)
    raw_b["met"]["900001"]["title"] = "Scarab"
    b = lf.write_run(tmp_path, lambda: (normalized(raw_b), raw_b), authority)
    final = tmp_path / "diffs" / f"{a['run_id']}-to-{b['run_id']}.json"
    pending = final.with_name(f".{final.name}.partial")
    final.rename(pending)
    data = pending.read_bytes()
    (tmp_path / "diffs" / ".zz-notes.partial").write_text("x")
    with pytest.raises(ValueError, match="is not a pending diff this module writes"):
        lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    assert pending.read_bytes() == data and not final.exists()


def test_a_run_killed_while_naming_its_pending_diff_leaves_only_the_writing_file(inputs, authority, tmp_path, monkeypatch) -> None:
    """The write order itself: the pending diff is written as `.writing` and named after, so a
    process killed in between leaves only that file, CURRENT unmoved, and the next run discards it."""
    canonical, raw = inputs
    a = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    raw_b = copy.deepcopy(raw)
    raw_b["met"]["900001"]["title"] = "Scarab"
    real = os.rename

    def die_naming(src, dst):
        if Path(src).name.endswith(".writing"):
            raise OSError("killed")
        return real(src, dst)
    monkeypatch.setattr(lf.os, "rename", die_naming)
    with pytest.raises(OSError, match="killed"):
        lf.write_run(tmp_path, lambda: (normalized(raw_b), raw_b), authority)
    monkeypatch.setattr(lf.os, "rename", real)
    (left,) = [p.name for p in (tmp_path / "diffs").iterdir()]
    assert left.startswith(f".{a['run_id']}-to-") and left.endswith(".json.partial.writing")
    assert (tmp_path / lf.CURRENT).read_text() == a["run_id"] + "\n"
    raw_c = copy.deepcopy(raw)
    raw_c["met"]["900001"]["title"] = "Amulet"
    c = lf.write_run(tmp_path, lambda: (normalized(raw_c), raw_c), authority)
    assert sorted(p.name for p in (tmp_path / "diffs").iterdir()) == [f"{a['run_id']}-to-{c['run_id']}.json"]


def test_a_change_the_mapper_cannot_see_passes_the_input_check(inputs) -> None:
    """The known gap (#375): a raw field the extractor reads but the mapper does not map
    (Harvard `labeltext`) changes without the canonical row changing, so the check cannot tell a
    re-ingest under way. #375's complete-ingest marker is to close it; this test then changes."""
    from pipeline.enrich.inputs import check_inputs
    canonical, raw = inputs
    raw2 = copy.deepcopy(raw)
    (source_id,) = [s for s in raw2["harvard"] if s == "303839"]
    raw2["harvard"][source_id]["labeltext"] = "Relief of King Amenhotep III, re-ingested"
    assert check_inputs(canonical, raw2) == (canonical, [])


def test_a_run_with_cleveland_links_its_catalogued_reigns(authority, tmp_path) -> None:
    """Cleveland's fixtures through a whole run: its reign mentions resolve and link as the Met's
    do. "Amenhotep III" joins the Met's record of the same name in both modes; "Tuthmosis III"
    (the Met writes "Thutmose III") links to a king in the authority mode only through the
    authority, and in the literal mode to its own text."""
    _, raw = corpus(EXTRA, with_cleveland=True)
    canonical = normalized(raw)
    manifest = lf.write_run(tmp_path, lambda: (canonical, raw), authority)
    assert manifest["canonical_rows_set_aside"] == []
    run = tmp_path / manifest["run_id"]

    def ruler_links(mode: str, artifact_id: str) -> list[dict]:
        return [l for l in links(run, mode) if l["artifact_id"] == artifact_id and l["entity_type"] == "ruler"]

    # Amenhotep III is von Beckerath's 18.09, Thutmose III his 18.06; met-900001's reign is
    # "reign of Amenhotep III" (EXTRA).
    assert [(l["target_id"], l["target_kind"]) for l in ruler_links("authority", "cleveland-130133")] == [
        ("cluster-beckerath-18.09", "king")]
    assert ("cluster-beckerath-18.09", "king") in {(l["target_id"], l["target_kind"]) for l in ruler_links("authority", "met-900001")}
    assert [(l["target_id"], l["target_kind"]) for l in ruler_links("authority", "cleveland-101390")] == [
        ("cluster-beckerath-18.06", "king")]
    (amenhotep,) = ruler_links("literal", "cleveland-130133")
    assert amenhotep["target_kind"] == "literal"
    assert amenhotep["target_id"] in {l["target_id"] for l in ruler_links("literal", "met-900001")}
    (tuthmosis,) = ruler_links("literal", "cleveland-101390")
    assert tuthmosis["target_kind"] == "literal" and tuthmosis["target_id"] not in {
        l["target_id"] for l in links(run, "literal") if l["museum"] != "cleveland"}
    # Only the two catalogued reigns link: Cleveland's sites are not read yet, and the forgery and
    # the Near Eastern record are not the normalize step's output.
    for mode in al.MODES:
        assert sorted((l["artifact_id"], l["entity_type"]) for l in links(run, mode) if l["museum"] == "cleveland") == [
            ("cleveland-101390", "ruler"), ("cleveland-130133", "ruler")], mode
