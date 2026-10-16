"""Cross-museum connections over a run's links, authority on or off (#338 step 3)."""

from __future__ import annotations

import json
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
        "authority": {"brooklyn": 3, "harvard": 1, "met": 6}, "literal": {"brooklyn": 1, "harvard": 1, "met": 2}}


def test_a_damaged_run_or_unknown_museum_or_mode_fails_loud(run, tmp_path) -> None:
    with pytest.raises(ValueError, match="unknown mode"):
        cm.load_links(run, "fuzzy")
    (run / "links-literal.ndjson.gz").write_bytes(lf.gzip_rows(LITERAL[:1]))
    with pytest.raises(ValueError, match="is not what that run wrote"):
        cm.report(run)
    other = write_run(tmp_path / "other", AUTHORITY + [link("louvre-1", "site", "idai:thebes")], LITERAL)
    with pytest.raises(ValueError, match=r"links of museums no pair covers: \['louvre'\]"):
        cm.report(other)


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
        assert row["qualified"] == ((a, b) in al.QUALIFIED_SCOPES[entity]), key


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
    assert proof["places_vs_linkability_adapter"] == {
        "compared": {"site": 113738, "tomb_monument": 4863}, "differ": {"site": [], "tomb_monument": []}}
    assert proof["places_vs_337_literal_arm"]["differ"] == []


def test_the_site_scopes_are_337s_evaluated_population(result) -> None:
    """Every museum's site records connected in each mode equal #337 v10's committed report, so
    the population #337 reviewed is the one the pipeline makes."""
    arms = json.loads((EVALUATIONS / "authority-independent-control-2026-10-11/results/real-run-report.json").read_text(
        encoding="utf-8"))["arms"]
    for arm, mode in (("typed_literal", "literal"), ("current_authority", "authority")):
        for museum in cm.MUSEUMS:
            assert result["matching"]["by_museum"][f"{museum}|site"][mode]["connected_records"] == (
                arms[arm]["per_museum"][museum]["by_entity_type"]["site"]["records_on_shared_useful_nodes"]), (arm, museum)
    assert result["evaluation_headlines"]["337"]["typed_literal"] == result["matching"]["records_on_shared_targets_any_type"]["literal"]
    # Tombs connect nothing in either, so the authority headline's difference from #337's is rulers.
    for museum in cm.MUSEUMS:
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
    assert result["ahmes_b_records"] == {"brooklyn": ["brooklyn-3634"], "met": ["met-547683", "met-566763"]}
    changes = json.loads((EVALUATIONS / "resolver-gaps-369/results/resolver-change.json").read_text(
        encoding="utf-8"))["royal_woman_cued_mentions"]["changes"]
    changed = {c["artifact_id"] for c in changes}
    assert {"brooklyn-3634", "met-566763"} <= changed and "met-547683" not in changed
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
        for a, b in al.MUSEUM_PAIRS:
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
                    # A literal id does not say its type; #337's site ids are those shared now.
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
