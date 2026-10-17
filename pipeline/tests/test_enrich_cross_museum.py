"""Cross-museum connections over a run's links, authority on or off (#338 step 3)."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

from pipeline.enrich import authority_links as al, cross_museum as cm, link_files as lf

EVALUATIONS = al.REPO / "docs/evaluations"


def link(artifact_id: str, entity_type: str, target: str, mode: str = "authority") -> dict:
    return {"artifact_id": artifact_id, "museum": artifact_id.split("-")[0], "entity_type": entity_type,
            "target_id": target, "mode": mode, "relation": "identity", "mention_ids": [f"m-{artifact_id}-{target}"],
            "evidence_roles": ["r"], "resolver_version": "v", "target_kind": "x"}


def write_run(root: Path, authority: list[dict], literal: list[dict]) -> Path:
    """A run directory as `link_files` writes one (the manifest digests to its name), holding
    these links."""
    files = {"links-authority.ndjson.gz": lf.gzip_rows(authority), "links-literal.ndjson.gz": lf.gzip_rows(literal)}
    body = {"files": {n: {"content_sha256": lf.content_sha256(n, d), "rows": None} for n, d in files.items()}}
    run_id = lf.manifest_digest(body)
    run = root / run_id
    run.mkdir(parents=True)
    for name, data in files.items():
        (run / name).write_bytes(data)
    (run / "manifest.json").write_text(json.dumps({**body, "run_id": run_id}))
    return run


# Sites: Thebes is shared by all three museums (met-1, met-4, brooklyn-1, harvard-1), Abydos by
# Met and Brooklyn (met-1, met-2, met-5, met-6, brooklyn-2); met-1 carries both. Plain text joins
# met-3 and harvard-3 on a broad literal the authority leaves unresolved, and splits Abydos.
# Rulers: met-7 and brooklyn-7 share a king that plain text spells apart.
AUTHORITY = [link("met-1", "site", "idai:thebes"), link("met-4", "site", "idai:thebes"),
             link("brooklyn-1", "site", "idai:thebes"), link("harvard-1", "site", "idai:thebes"),
             link("met-1", "site", "idai:abydos"), link("met-2", "site", "idai:abydos"),
             link("met-5", "site", "idai:abydos"), link("met-6", "site", "idai:abydos"),
             link("brooklyn-2", "site", "idai:abydos"), link("harvard-3", "site", "idai:saqqara"),
             link("met-7", "ruler", "king:horemheb"), link("brooklyn-7", "ruler", "king:horemheb")]
LITERAL = [link("met-1", "site", "literal:thebes", "literal"), link("brooklyn-1", "site", "literal:thebes", "literal"),
           link("met-2", "site", "literal:abydos", "literal"), link("brooklyn-2", "site", "literal:abydos-1", "literal"),
           link("met-3", "site", "literal:egypt", "literal"), link("harvard-3", "site", "literal:egypt", "literal"),
           link("met-7", "ruler", "literal:haremhab", "literal"), link("brooklyn-7", "ruler", "literal:horemheb", "literal")]


@pytest.fixture
def run(tmp_path) -> Path:
    return write_run(tmp_path, AUTHORITY, LITERAL)


def test_the_report_counts_connections_by_pair_type_and_side(run) -> None:
    r = cm.report(run)
    mb = r["by_museum_pair"]["site|met|brooklyn"]
    assert (mb["qualified"], mb["shared_targets_authority"], mb["shared_targets_literal"]) == (True, 2, 1)
    assert mb["records"] == {
        "met": {"connected_authority": 5, "connected_literal": 1, "gained": 4, "lost": 0},
        "brooklyn": {"connected_authority": 2, "connected_literal": 1, "gained": 1, "lost": 0}}
    # Abydos carries four Met records, Thebes two; one record (met-1) is on both.
    assert mb["top_targets"]["authority"]["met"] == {
        "1": {"target_ids": ["idai:abydos"], "share": 0.8}, "5": {"target_ids": ["idai:abydos", "idai:thebes"], "share": 1.0}}
    assert mb["top_targets"]["authority"]["brooklyn"] == {
        "1": {"target_ids": ["idai:abydos"], "share": 0.5}, "5": {"target_ids": ["idai:abydos", "idai:thebes"], "share": 1.0}}
    assert mb["top_targets"]["literal"]["met"] == {
        "1": {"target_ids": ["literal:thebes"], "share": 1.0}, "5": {"target_ids": ["literal:thebes"], "share": 1.0}}
    mh = r["by_museum_pair"]["site|met|harvard"]
    assert mh["records"] == {
        "met": {"connected_authority": 2, "connected_literal": 1, "gained": 2, "lost": 1},
        "harvard": {"connected_authority": 1, "connected_literal": 1, "gained": 1, "lost": 1}}
    assert r["by_museum_pair"]["ruler|met|brooklyn"]["records"]["met"] == {
        "connected_authority": 1, "connected_literal": 0, "gained": 1, "lost": 0}
    assert r["by_museum_pair"]["ruler|met|harvard"]["qualified"] is False
    assert r["by_museum_pair"]["tomb_monument|met|brooklyn"]["qualified"] is False
    assert set(r["by_museum_pair"]) == {f"{t}|{a}|{b}" for t in al.RESOLVED_TYPES for a, b in al.MUSEUM_PAIRS}
    # A Met record is counted once though it is connected to Brooklyn and to Harvard.
    assert r["by_museum"]["met|site"] == {"authority": {"linked_records": 5, "connected_records": 5},
                                          "literal": {"linked_records": 3, "connected_records": 2}}
    assert r["by_museum"]["harvard|site"] == {"authority": {"linked_records": 2, "connected_records": 1},
                                              "literal": {"linked_records": 1, "connected_records": 1}}
    assert r["records_on_shared_targets_any_type"] == {
        "authority": {"brooklyn": 3, "cleveland": 0, "harvard": 1, "met": 6, "walters": 0},
        "literal": {"brooklyn": 1, "cleveland": 0, "harvard": 1, "met": 2, "walters": 0}}


def test_a_damaged_run_or_unknown_museum_or_mode_fails_loud(run, tmp_path) -> None:
    with pytest.raises(ValueError, match="unknown mode"):
        cm.load_links(run, "fuzzy")
    (run / "links-literal.ndjson.gz").write_bytes(lf.gzip_rows(LITERAL[:1]))
    with pytest.raises(ValueError, match="is not what that run wrote"):
        cm.report(run)
    other = write_run(tmp_path / "other", AUTHORITY + [link("louvre-1", "site", "idai:thebes")], LITERAL)
    with pytest.raises(ValueError, match=r"links of museums no pair covers: \['louvre'\]"):
        cm.report(other)


# The frozen run (end-to-end.json) is of the 2026-08-27 corpus: these museums and pairs. Cleveland
# and the Walters came later (docs/museum-sources/), so tests of that run iterate over these, not
# over today's `MUSEUM_PAIRS`.
FROZEN_MUSEUMS = ("brooklyn", "harvard", "met")
FROZEN_PAIRS = (("met", "brooklyn"), ("met", "harvard"), ("brooklyn", "harvard"))
# Its `qualified` flags are the policy of the code it records (#361's rulers). The 2026-10-16
# re-registration replaced Met–Brooklyn rulers with Met–Walters (`QUALIFIED_SCOPES`); the frozen
# report keeps the flags it was written with.
FROZEN_QUALIFIED = {"site": set(FROZEN_PAIRS), "ruler": {("met", "brooklyn")}, "tomb_monument": set()}


@pytest.fixture(scope="module")
def result() -> dict:
    return json.loads((EVALUATIONS / "authority-bridge-338/results/end-to-end.json").read_text(encoding="utf-8"))


def test_the_end_to_end_run_was_stable_and_of_the_proven_code(result) -> None:
    """Two interpreters wrote the same run, and its resolver versions are the ones the step-1
    proof (`promotion-check.json`) measured against #337 and #361."""
    assert result["run_ids"][0] == result["run_ids"][1]
    assert result["two_runs"] == {"python_hash_seeds": ["1", "2"], "same_manifest_contents_and_report": True}
    promotion = json.loads((EVALUATIONS / "authority-bridge-338/results/promotion-check.json").read_text(encoding="utf-8"))
    assert result["resolver_versions"] == {m: promotion["snapshot"][m]["resolver_version"] for m in al.MODES}
    assert sorted(result["report_sha256"]) == [
        "docs/evaluations/authority-bridge-338/scripts/run_end_to_end.py", "pipeline/pipeline/enrich/cross_museum.py"]
    assert {name: f["rows"] for name, f in result["files"].items()} == {
        "links-authority.ndjson.gz": 48994, "links-literal.ndjson.gz": 127711, "mentions.ndjson.gz": 148964,
        "resolutions-authority.ndjson.gz": 148964, "resolutions-literal.ndjson.gz": 148964}
    for key, row in result["matching"]["by_museum_pair"].items():
        entity, a, b = key.split("|")
        assert row["qualified"] == ((a, b) in FROZEN_QUALIFIED[entity]), key
    assert {t: set(pairs) for t, pairs in al.QUALIFIED_SCOPES.items()} == {
        **FROZEN_QUALIFIED, "ruler": {("met", "walters")}}


def test_the_site_links_are_337s_record_for_record() -> None:
    """Identity, not only counts: #361's mention ledger holds every #337 v10 mention unchanged and
    adds only royal-woman-cued ruler mentions (`ledger-diff.json`), and the step-1 proof found
    the pipeline's site resolutions and site literal targets equal to #337's own code on every
    one of those mentions (`promotion-check.json`). So every site link, and every record it
    connects, is the one #337 made."""
    ledger = json.loads((EVALUATIONS / "ruler-reregistration-2026-10-15/results/ledger-diff.json").read_text(encoding="utf-8"))
    assert (ledger["lost"], ledger["changed_ignoring_record_dynasty"]) == (0, 0)
    assert sum(ledger["added_by_royal_woman_cue"].values()) == ledger["added"] == 93
    assert ledger["v10_mentions"] + ledger["added"] == ledger["new_mentions"] == 148964
    proof = json.loads((EVALUATIONS / "authority-bridge-338/results/promotion-check.json").read_text(encoding="utf-8"))
    assert proof["mentions"] == {"ledger_361": 148964, "production": 148964, "rows_equal": True}
    assert proof["places_vs_linkability_adapter"] == {
        "compared": {"site": 113738, "tomb_monument": 4863}, "differ": {"site": [], "tomb_monument": []}}
    assert proof["places_vs_337_literal_arm"]["differ"] == []
    # The adapter the proof compared against resolves as #337's did: its resolution code is #337's
    # (the file has changed since only in how it finds its repository), and the gazetteer, the
    # Porter & Moss rows and the normalizer are the bytes #337 pinned.
    adapter = "docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts/run_linkability.py"
    then = subprocess.run(["git", "-C", str(al.REPO), "show", f"97f2e61:{adapter}"], check=True, capture_output=True,
                          text=True).stdout
    arms_337_source = (EVALUATIONS / "authority-independent-control-2026-10-11/scripts/compare_arms.py").read_text(
        encoding="utf-8")
    pinned = re.search(rf'"{re.escape(adapter)}":\s*"([0-9a-f]{{64}})"', arms_337_source).group(1)
    assert hashlib.sha256(then.encode("utf-8")).hexdigest() == pinned  # #337's CURRENT_INPUTS

    def definitions(source: str) -> dict[str, str]:
        return {n.name: ast.dump(n) for n in ast.parse(source).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    now = definitions((al.REPO / adapter).read_text(encoding="utf-8"))
    for name in ("build_site_resolver", "build_pm_resolver", "place_norm", "place_norm_set", "surface_key",
                 "Resolver", "Target", "load_jsonl"):
        assert definitions(then)[name] == now[name], name
    arms_337 = (EVALUATIONS / "authority-independent-control-2026-10-11/scripts/compare_arms.py").read_text(encoding="utf-8")
    files = proof["snapshot"]["authority"]["files"]
    for path in ("pipeline/pipeline/authority/sources/idai-gazetteer/reconciled.jsonl",
                 "pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/reconciled.jsonl",
                 "pipeline/pipeline/authority/sources/porter-moss-memphis/reconciled.jsonl",
                 "pipeline/pipeline/authority/claimgraph/normalize.py"):
        assert f'"{path}":\n        "{files[path]}"' in arms_337, path


def test_the_end_to_end_run_is_of_the_proven_corpus_and_code(result) -> None:
    proof = json.loads((EVALUATIONS / "authority-bridge-338/results/promotion-check.json").read_text(encoding="utf-8"))
    assert result["corpus_archive_sha256"] == proof["corpus_archive_sha256"]
    assert result["resolver_versions"] == {m: proof["snapshot"][m]["resolver_version"] for m in al.MODES}


def test_the_site_scopes_are_337s_evaluated_population(result) -> None:
    """Every museum's site records connected in each mode equal #337 v10's committed report, so
    the population #337 reviewed is the one the pipeline makes."""
    arms = json.loads((EVALUATIONS / "authority-independent-control-2026-10-11/results/real-run-report.json").read_text(
        encoding="utf-8"))["arms"]
    for arm, mode in (("typed_literal", "literal"), ("current_authority", "authority")):
        for museum in FROZEN_MUSEUMS:
            assert result["matching"]["by_museum"][f"{museum}|site"][mode]["connected_records"] == (
                arms[arm]["per_museum"][museum]["by_entity_type"]["site"]["records_on_shared_useful_nodes"]), (arm, museum)
    assert result["evaluation_headlines"]["337"]["typed_literal"] == result["matching"]["records_on_shared_targets_any_type"]["literal"]
    # Tombs connect nothing in either, so the authority headline's difference from #337's is rulers.
    for museum in FROZEN_MUSEUMS:
        for arm, mode in (("typed_literal", "literal"), ("current_authority", "authority")):
            assert result["matching"]["by_museum"][f"{museum}|tomb_monument"][mode]["connected_records"] == (
                arms[arm]["per_museum"][museum]["by_entity_type"]["tomb_monument"]["records_on_shared_useful_nodes"]) == 0


def test_the_ruler_scope_is_361s_population_with_369s_ahmes_b(result) -> None:
    """Met-Brooklyn rulers: plain text is exactly #361's committed arm; the authority is #361's
    with one shared target more, D&H's Ahmes B (#369, tuned on #361's deciding case, unreviewed),
    which turns 2 of #361's reviewed Met losses and 1 Brooklyn loss into connections."""
    report = json.loads((EVALUATIONS / "ruler-reregistration-2026-10-15/results/real-run-report.json").read_text(
        encoding="utf-8"))
    arms, change = report["arms"], report["comparison"]["record_gains_and_losses"]["per_pair"]["met__brooklyn"]
    now = result["matching"]["by_museum_pair"]["ruler|met|brooklyn"]
    literal, authority = arms["typed_literal"]["per_pair"]["met__brooklyn"], arms["current_authority"]["per_pair"]["met__brooklyn"]
    assert (now["shared_targets_literal"], now["records"]["met"]["connected_literal"],
            now["records"]["brooklyn"]["connected_literal"]) == (
        literal["shared_useful_node_count"], literal["records_by_museum_side"]["met"], literal["records_by_museum_side"]["brooklyn"])
    assert (now["shared_targets_authority"], now["records"]["met"]["connected_authority"],
            now["records"]["brooklyn"]["connected_authority"]) == (
        authority["shared_useful_node_count"] + 1, authority["records_by_museum_side"]["met"] + 2,
        authority["records_by_museum_side"]["brooklyn"] + 1)
    for museum, delta in (("met", 2), ("brooklyn", 1)):
        assert now["records"][museum]["gained"] == change[museum]["authority_gained_records"], museum
        assert now["records"][museum]["lost"] == change[museum]["authority_lost_records"] - delta, museum
    # The added target is Ahmes B: it is shared now, and #361's report names it nowhere; every
    # target #361's report lists for the pair (its top 10 per side) is shared now in its arm.
    assert "dodson_hilton:Ahmes B" in now["shared_target_ids"]["authority"]
    assert "Ahmes B" not in json.dumps(report)
    for arm, mode in (("typed_literal", "literal"), ("current_authority", "authority")):
        listed = {t for side in ("met", "brooklyn") for t in
                  arms[arm]["per_pair"]["met__brooklyn"]["concentration_by_museum_side"][side]["top_k"]["10"]["selected_target_ids"]}
        assert listed <= set(now["shared_target_ids"][mode]) - {"dodson_hilton:Ahmes B"}, mode
    # It joins the two Queen Ahmose records (#369's tuned-on change) and met-547683, which #369 did
    # not change (it is not among #369's changed records): it resolved to Ahmes B before, without a
    # Brooklyn record to share her with. Those are the Met +2 and Brooklyn +1.
    # Each is connected through Ahmes B alone and was connected by plain text, so with the
    # authority only growing from #361 (the step-1 proof), these three are exactly the losses
    # that now connect.
    assert result["ahmes_b_records"] == {
        "brooklyn": {"brooklyn-3634": {"other_shared_authority_targets": [], "connected_by_plain_text": True}},
        "met": {"met-547683": {"other_shared_authority_targets": [], "connected_by_plain_text": True},
                "met-566763": {"other_shared_authority_targets": [], "connected_by_plain_text": True}}}
    changes = json.loads((EVALUATIONS / "resolver-gaps-369/results/resolver-change.json").read_text(
        encoding="utf-8"))["royal_woman_cued_mentions"]["changes"]
    changed = {c["artifact_id"] for c in changes}
    assert {"brooklyn-3634", "met-566763"} <= changed and "met-547683" not in changed
    # #369 only adds links: none of its changes was resolved before, and the two that resolve now
    # are the Queen Ahmose records (the rest stay ambiguous, which makes no link).
    assert all(c["before"]["status"] != "resolved" for c in changes)
    assert {c["artifact_id"] for c in changes if c["after"]["status"] == "resolved"} == {"brooklyn-3634", "met-566763"}
    # And the step-1 proof: every other ruler resolution is #361's.
    proof = json.loads((EVALUATIONS / "authority-bridge-338/results/promotion-check.json").read_text(encoding="utf-8"))
    assert (proof["rulers_vs_361_authority_arm"]["differ_otherwise"], len(proof["rulers_vs_361_authority_arm"]["differ_as_369_measured"])) == ([], 11)
    assert proof["rulers_vs_361_literal_arm"]["differ"] == []
    assert result["tuned_on_369"] == ["brooklyn-3599", "brooklyn-3634", "met-566763"]


def test_the_site_top_targets_are_337s(result) -> None:
    """Beyond the counts: each site pair's largest 1 and 5 shared targets, per side and mode, are
    the site targets #337 v10's committed report ranks first."""
    arms = json.loads((EVALUATIONS / "authority-independent-control-2026-10-11/results/real-run-report.json").read_text(
        encoding="utf-8"))["arms"]
    for arm, mode in (("typed_literal", "literal"), ("current_authority", "authority")):
        for a, b in FROZEN_PAIRS:
            theirs = arms[arm]["per_pair"][f"{a}__{b}"]["concentration_by_museum_side"]
            ours = result["matching"]["by_museum_pair"][f"site|{a}|{b}"]["top_targets"][mode]
            for museum in (a, b):
                # #337 ranks a pair's shared targets of every type together; its site targets, in
                # its order, from its top 10.
                ranked = theirs[museum]["top_k"]["10"]["selected_target_ids"]
                shared = result["matching"]["by_museum_pair"][f"site|{a}|{b}"]["shared_target_ids"][mode]
                if mode == "authority":
                    # A site target is an iDAI id: every one #337 ranked must be shared now.
                    sites = [t for t in ranked if t.startswith("idai:")]
                    assert set(sites) <= set(shared), (a, b, museum)
                else:
                    # A literal id hashes its type, so it is of one type; literal links only grew
                    # since #337, so every id #337 ranked is shared now under some type, and the
                    # site ones under site.
                    any_type = {t for e in al.RESOLVED_TYPES
                                for t in result["matching"]["by_museum_pair"][f"{e}|{a}|{b}"]["shared_target_ids"][mode]}
                    assert set(ranked) <= any_type, (a, b, museum)
                    sites = [t for t in ranked if t in shared]
                for k in ("1", "5"):
                    assert ours[museum][k]["target_ids"] == sites[:int(k)], (arm, a, b, museum, k)


def test_the_largest_plain_text_site_targets_are_egypt_and_africa(result) -> None:
    """Bound by the literal target's hash, no museum text committed: plain text's largest Met
    target in Met-Brooklyn and Met-Harvard is "Egypt", Harvard's in Met-Harvard is "Africa"; the
    authority resolves neither."""
    pairs = result["matching"]["by_museum_pair"]
    egypt, africa = al.literal_target("site", "Egypt"), al.literal_target("site", "Africa")
    assert pairs["site|met|brooklyn"]["top_targets"]["literal"]["met"]["1"] == {"target_ids": [egypt], "share": 0.977}
    assert pairs["site|met|brooklyn"]["top_targets"]["literal"]["brooklyn"]["1"]["target_ids"] == [egypt]
    assert pairs["site|met|harvard"]["top_targets"]["literal"]["met"]["1"]["target_ids"] == [egypt]
    assert pairs["site|met|harvard"]["top_targets"]["literal"]["harvard"]["1"] == {"target_ids": [africa], "share": 1.0}
    authority = al.load_authority()
    for place in ("Egypt", "Africa"):
        assert authority.sites.resolve(place, al.resolver.place_norm_set)["status"] == "unmatched", place


def test_the_frozen_run_says_whether_each_qualified_scopes_review_covers_it(result) -> None:
    """Review coverage is a fact about this frozen run, not something `report()` can know of any
    run: the sites' reviews cover it; Met-Brooklyn rulers' does not cover the three records #369's
    Ahmes B connects."""
    assert result["review_coverage"] == {
        "ruler|met|brooklyn": {"qualified_by": "#361", "review_covers_population": False,
                               "unreviewed_connected_records": ["brooklyn-3634", "met-547683", "met-566763"],
                               "by": "links of the mentions resolving differently from #361 removed (step-1 proof)"},
        **{f"site|{a}|{b}": {"qualified_by": "#337 v10", "review_covers_population": True,
                             "unreviewed_connected_records": [], "by": "site links identical to #337's (identity test)"}
           for a, b in FROZEN_PAIRS}}
    # The frozen run's pairs are FROZEN_PAIRS.
    assert {key.split("|", 1)[1] for key in result["matching"]["by_museum_pair"]} == {f"{a}|{b}" for a, b in FROZEN_PAIRS}
    changes = json.loads((EVALUATIONS / "resolver-gaps-369/results/resolver-change.json").read_text(
        encoding="utf-8"))["royal_woman_cued_mentions"]["changes"]
    changed = {c["artifact_id"] for c in changes}
    assert set(result["tuned_on_369"]) <= changed
    connected = {r for records in result["ahmes_b_records"].values() for r in records}
    assert changed & connected <= set(result["review_coverage"]["ruler|met|brooklyn"]["unreviewed_connected_records"])
    # report() itself makes no coverage claim.
    assert all(set(row) == {"qualified", "shared_targets_authority", "shared_targets_literal", "shared_target_ids",
                            "records", "top_targets"} for row in result["matching"]["by_museum_pair"].values())


def test_the_ahmes_b_check_reviewed_the_three_unreviewed_records() -> None:
    """`docs/evaluations/ahmes-b-recheck-2026-10-16`: the check reviewed exactly the records #376
    left unreviewed, and found them one woman, Ahmes B (a check, not evidence for the scope)."""
    check = json.loads((EVALUATIONS / "ahmes-b-recheck-2026-10-16/results/check.json").read_text(encoding="utf-8"))
    result = json.loads((EVALUATIONS / "authority-bridge-338/results/end-to-end.json").read_text(encoding="utf-8"))
    checked = sorted(r for records in check["records_checked"].values() for r in records)
    assert checked == result["review_coverage"]["ruler|met|brooklyn"]["unreviewed_connected_records"]
    assert check["stages"]["1"]["outcome"] == {"same_entity": "same_entity", "useful_granularity": "useful"}
    assert check["stages"]["2"]["outcome"] == {"canonical_identity": "exact_identity"}
    assert check["stages"]["2"]["resolution"]["canonical_identity"]["method"] == "explicit_cited_override"
    assert check["run_id"] == result["run_ids"][0]  # the run whose link it checked


def test_the_database_run_made_the_frozen_run() -> None:
    """`results/database-run.json`: the asset, run against the frozen corpus loaded into a real
    database, made the run end-to-end.json measured (the run id digests the whole manifest)."""
    db = json.loads((EVALUATIONS / "authority-bridge-338/results/database-run.json").read_text(encoding="utf-8"))
    result = json.loads((EVALUATIONS / "authority-bridge-338/results/end-to-end.json").read_text(encoding="utf-8"))
    assert db["run_id"] == result["run_ids"][0]
    # The run's own manifest (committed; it holds hashes, counts and the authority code's reasons,
    # no museum text) digests to that run id, and carries the headline figures.
    manifest = json.loads((EVALUATIONS / "authority-bridge-338/results" / db["manifest"]).read_text(encoding="utf-8"))
    assert lf.manifest_digest(manifest) == manifest["run_id"] == db["run_id"] == db["dagster"]["materialization_metadata"]["run_id"]
    assert (manifest["records"], manifest["canonical_rows_set_aside"]) == (36245, [])
    assert {name: f["rows"] for name, f in manifest["files"].items()} == {name: f["rows"] for name, f in result["files"].items()}
    assert (manifest["files"]["links-authority.ndjson.gz"]["rows"], manifest["files"]["links-literal.ndjson.gz"]["rows"]) == (
        db["dagster"]["materialization_metadata"]["links_authority"], db["dagster"]["materialization_metadata"]["links_literal"])
    assert db["database"]["rows_loaded"] == {"catalog.artifacts": 36245, "catalog.raw_met": 27969,
                                             "catalog.raw_brooklyn": 8832, "catalog.raw_harvard": 722}


def _flat(value, path: str = "") -> dict:
    if isinstance(value, dict):
        return {k: v for key, item in value.items() for k, v in _flat(item, f"{path}/{key}").items()}
    return {path: value}


@pytest.mark.parametrize("rerun, added", [
    ("rerun-after-cleveland", ("cleveland",)),
    ("rerun-after-walters", ("cleveland", "walters")),
])
def test_adding_a_museum_changed_nothing_on_the_frozen_corpus(rerun, added) -> None:
    """`results/<rerun>/`: both proof scripts re-run on the frozen corpus with the code that adds
    a museum (Cleveland, then the Walters). Every figure is the committed one; what differs is only
    what names the code (hashes, resolver versions, run ids, the files whose rows carry the
    resolver version) and the added museums' own rows, all empty: the corpus predates them."""
    results = EVALUATIONS / "authority-bridge-338/results"
    code_named = ("code_sha256", "/files/", "resolver_version", "/run_ids", "/writer_sha256")
    for name in ("promotion-check.json", "end-to-end.json"):
        before = _flat(json.loads((results / name).read_text(encoding="utf-8")))
        after = _flat(json.loads((results / rerun / name).read_text(encoding="utf-8")))
        differ = {k for k in before.keys() | after.keys() if before.get(k) != after.get(k)}
        code = {k for k in differ if any(part in k for part in code_named)}
        differ -= code
        new = {k for k in differ if any(museum in k for museum in added)}
        assert all(after[k] in (0, [], False) for k in new if k in after), name
        assert all(k not in before for k in new), name
        unevaluated = {k for k in differ if k.startswith("/inventory/unevaluated_scopes/")}
        for key in unevaluated:
            assert after[key][:len(before[key])] == before[key]
            assert all(set(pair) & set(added) for pair in after[key][len(before[key]):]), key
        assert differ - new - unevaluated == set(), name
    after = json.loads((results / rerun / "end-to-end.json").read_text(encoding="utf-8"))
    before = json.loads((results / "end-to-end.json").read_text(encoding="utf-8"))
    # The rerun is of the code that adds them: each added museum's pairs are in it (empty), and its
    # input check ran that museum's mapper.
    frozen = {"met", "brooklyn", "harvard"}
    pairs = {(a, b) for key in after["matching"]["by_museum_pair"] for a, b in [key.split("|")[1:]]}
    assert {pair for pair in pairs if set(pair) - frozen} == {
        pair for pair in al.MUSEUM_PAIRS if set(pair) - frozen and set(pair) <= frozen | set(added)}
    promotion = json.loads((results / rerun / "promotion-check.json").read_text(encoding="utf-8"))
    assert {f"pipeline/pipeline/assets/normalize/{museum}.py" for museum in added} <= set(
        promotion["check_inputs"]["code_sha256"])
    # The mention ledger, which carries no resolver version, is byte for byte the same.
    assert after["files"]["mentions.ndjson.gz"] == before["files"]["mentions.ndjson.gz"]
    assert {n: f["rows"] for n, f in after["files"].items()} == {n: f["rows"] for n, f in before["files"].items()}


def test_the_latest_rerun_and_the_museum_profiles_pin_the_same_code() -> None:
    """The committed artifacts made after the Walters was added must describe one version of the
    code they share: the rerun's input check, its resolver snapshot and the two museum profiles
    pin each file they have in common to one hash. (Whether that version is the live code is
    checked when they are made; an edit afterwards leaves them describing the code they record.)"""
    results = EVALUATIONS / "authority-bridge-338/results/rerun-after-king-context"
    promotion = json.loads((results / "promotion-check.json").read_text(encoding="utf-8"))
    pins = [promotion["check_inputs"]["code_sha256"], promotion["snapshot"]["authority"]["files"]]
    for museum in ("cleveland", "walters"):
        profile = EVALUATIONS.parent / "museum-sources" / f"{museum}-profile/profile.json"
        pins.append(json.loads(profile.read_text(encoding="utf-8"))["code_sha256"])
    seen: dict[str, set[str]] = {}
    for pin in pins:
        for path, digest in pin.items():
            seen.setdefault(path, set()).add(digest)
    assert {path: digests for path, digests in seen.items() if len(digests) > 1} == {}
    end_to_end = json.loads((results / "end-to-end.json").read_text(encoding="utf-8"))
    assert end_to_end["resolver_versions"] == {m: promotion["snapshot"][m]["resolver_version"] for m in al.MODES}
    assert {"pipeline/pipeline/enrich/mentions.py", "pipeline/pipeline/assets/normalize/walters.py"} <= {
        path for path in seen if sum(path in pin for pin in pins) > 1}


def test_resolving_kings_in_context_changed_only_what_it_measured() -> None:
    """`results/rerun-after-king-context/`: both proof scripts re-run on the frozen corpus with the
    code that resolves kings in their record's context (`king_context`). Against the previous
    re-run, only the ruler figures the measurement reports changed
    (`king-context-2026-10-17/results/measure.json`), and the ruler scope qualified since (#383);
    every other figure, sites and tombs included, is the same."""
    results = EVALUATIONS / "authority-bridge-338/results"
    code_named = ("code_sha256", "/files/", "resolver_version", "/run_ids", "/writer_sha256", "/run_id",
                  "/report_sha256/")
    expected = {
        "promotion-check.json": {
            "/authority_mode_statuses/ruler:ambiguous": (83, 80),
            "/authority_mode_statuses/ruler:resolved": (9015, 9009),
            "/authority_mode_statuses/ruler:unmatched": (298, 307),
            "/schema_version": ("hapi-338-promotion-check/3", "hapi-338-promotion-check/4"),
        },
        "end-to-end.json": {
            "/matching/by_museum/met|ruler/authority/linked_records": (8869, 8863),
            "/matching/by_museum_pair/ruler|met|brooklyn/qualified": (True, False),
            "/matching/by_museum_pair/ruler|met|walters/qualified": (False, True),
            "/outcomes/authority/ruler|ambiguous|authority_ambiguous": (78, 75),
            "/outcomes/authority/ruler|resolved|": (9015, 9009),
            "/outcomes/authority/ruler|unmatched|record_context_conflict": (None, 9),
        },
    }
    for name, changes in expected.items():
        before = _flat(json.loads((results / "rerun-after-walters" / name).read_text(encoding="utf-8")))
        after = _flat(json.loads((results / "rerun-after-king-context" / name).read_text(encoding="utf-8")))
        differ = {k for k in before.keys() | after.keys() if before.get(k) != after.get(k)
                  and not any(part in k for part in code_named)}
        differ -= {k for k in differ if k.startswith(("/review_coverage/", "/inventory/unevaluated_scopes/ruler",
                                                       "/rulers_vs_361_authority_arm/differ_by_king_context"))}
        assert {k: (before.get(k), after.get(k)) for k in differ} == changes, name
    promotion = json.loads((results / "rerun-after-king-context/promotion-check.json").read_text(encoding="utf-8"))
    rulers = promotion["rulers_vs_361_authority_arm"]
    assert rulers["differ_otherwise"] == []
    assert rulers["differ_as_369_measured"] == json.loads((results / "promotion-check.json").read_text(
        encoding="utf-8"))["rulers_vs_361_authority_arm"]["differ_as_369_measured"]
    # The 12 mentions the measurement counts, and Menkheperre (Met, Dynasty 21), whose candidates
    # the context narrowed from three to two (Necho I dropped) while it stays ambiguous.
    assert len(rulers["differ_by_king_context"]) == 13
    assert promotion["places_vs_linkability_adapter"]["differ"] == {"site": [], "tomb_monument": []}
    assert promotion["rulers_vs_361_literal_arm"]["differ"] == promotion["places_vs_337_literal_arm"]["differ"] == []
    assert promotion["mentions"]["rows_equal"] is True
    end_to_end = json.loads((results / "rerun-after-king-context/end-to-end.json").read_text(encoding="utf-8"))
    assert end_to_end["review_coverage"]["ruler|met|walters"] == {
        "qualified_by": "ruler re-registration 2026-10-16", "unreviewed_connected_records": [],
        "review_covers_population": True, "by": "no records of this pair connected in this run"}
    assert end_to_end["resolver_versions"] == {m: promotion["snapshot"][m]["resolver_version"] for m in al.MODES}
