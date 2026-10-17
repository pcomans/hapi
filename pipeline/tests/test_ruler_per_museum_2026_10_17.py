"""Per-museum ruler test (2026-10-17): each museum's ruler links judged against the authority,
with decoys as calibration. Tests run against the evaluation's own scripts."""

from __future__ import annotations

import gzip
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
EVALUATION = ROOT / "docs" / "evaluations" / "ruler-per-museum-2026-10-17"
SCRIPTS = EVALUATION / "scripts"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# The scripts import `review_protocol` by name, as other registrations' do; this one's copy is
# in place only while its scripts load, and the previous one is restored after.
_previous = sys.modules.pop("review_protocol", None)
sys.path.insert(0, str(SCRIPTS))
try:
    protocol = _load("review_protocol", "review_protocol.py")
    runner = _load("_ruler_per_museum_runner", "run_harness_review.py")
    builder = _load("_ruler_per_museum_build_queue", "build_queue.py")
    scorer = _load("_ruler_per_museum_score", "score.py")
    make_run = _load("_ruler_per_museum_make_run", "make_run.py")
finally:
    sys.path.remove(str(SCRIPTS))
    sys.modules.pop("review_protocol", None)
    if _previous is not None:
        sys.modules["review_protocol"] = _previous

OPENED = "https://www.metmuseum.org/art/collection/search/1"


def opened_page(url: str = OPENED) -> dict:
    return {"requested_url": url, "final_url": url, "status": 200, "title": "Object", "loaded": True,
            "text": "Object record", "text_truncated": False, "browser": "local",
            "browser_version": protocol.CHROMIUM_VERSION, "load_event": True}


def events(answer: dict, opens: tuple = (opened_page(),), session_id: str = "session-1") -> list[dict]:
    """A stored call's event stream: one `open_page` call per entry of `opens` (a page record, or
    an error string for a call the tool failed), then the answer."""
    stream = [{"type": "system", "subtype": "init", "model": protocol.SERVED_MODEL,
               "claude_code_version": protocol.CLAUDE_CODE_VERSION, "apiKeySource": "none",
               "tools": list(protocol.TOOLS), "session_id": session_id,
               "mcp_servers": [{"name": protocol.OPEN_PAGE_SERVER, "status": "connected"}]}]
    for n, page in enumerate(opens):
        error = isinstance(page, str)
        stream += [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": f"o{n}", "name": protocol.OPEN_PAGE_TOOL,
                 "input": {"url": OPENED if error else page["requested_url"]}}]}},
            {"type": "user", "message": {"content": [{
                "type": "tool_result", "tool_use_id": f"o{n}", "is_error": error,
                "content": page if error else json.dumps(page)}]}},
        ]
    return stream + [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": json.dumps(answer)}]}},
        {"type": "result", "subtype": "success", "is_error": False, "usage": {"output_tokens": 10}, "total_cost_usd": 0.5},
    ]


LINK_CASE = {"case_id": "link-001", "evidence_sha256": "1" * 64, "entity_type": "ruler",
             "evidence": {"museum": "met", "mention_text": "Senwosret I", "record_texts": []},
             "proposed_target": {"target_id": "cluster-beckerath-12.02", "target_label": "Senusret I", "target_metadata": {}},
             "question": builder.LINK_QUESTION, "allowed_outcomes": list(builder.LINK_OUTCOMES)}
MISS_CASE = {"case_id": "miss-001", "evidence_sha256": "2" * 64, "entity_type": "ruler",
             "evidence": {"museum": "met", "mention_text": "Djoser", "record_texts": []},
             "question": builder.MISS_QUESTION, "allowed_outcomes": list(builder.MISS_OUTCOMES)}


def validate(case: dict, role_name: str, answer: dict, opens: tuple = (opened_page(),)) -> dict:
    role = protocol.ROLES[role_name]
    return protocol.validate({"events": events(answer, opens), "exit_code": 0}, case, role, protocol.read_json(role.schema))


# The runner (#384).

def test_the_browser_server_runs_on_the_runs_own_display_not_one_per_call() -> None:
    config = json.loads(runner.MCP_CONFIG)["mcpServers"][protocol.OPEN_PAGE_SERVER]
    assert config == {"command": sys.executable, "args": [str(protocol.OPEN_PAGE_SERVER_PATH)]}
    assert "xvfb-run" not in runner.MCP_CONFIG


def test_the_runner_calls_the_pinned_release_with_auto_update_off() -> None:
    assert runner.CLAUDE_BINARY == Path.home() / ".local/share/claude/versions" / "2.1.302"
    assert protocol.CLAUDE_CODE_VERSION == "2.1.302"
    argv = runner.command("system", "user")
    assert argv[:3] == [str(runner.CLAUDE_BINARY), "-p", "user"]
    source = (SCRIPTS / "run_harness_review.py").read_text()
    assert 'env["DISABLE_AUTOUPDATER"] = "1"' in source


@pytest.mark.skipif(shutil.which("Xvfb") is None, reason="needs Xvfb")
def test_the_virtual_display_is_stopped_when_the_run_ends() -> None:
    with pytest.raises(RuntimeError, match="the run failed"):
        with runner.virtual_display() as xvfb:
            assert runner.os.environ["DISPLAY"].removeprefix(":").isdigit()
            assert xvfb.poll() is None
            raise RuntimeError("the run failed")
    assert xvfb.poll() is not None


def test_a_call_whose_browser_tool_failed_is_retried_not_a_decision() -> None:
    answer = {"case_id": "link-001", "canonical_identity": "insufficient_evidence", "reasoning": "nothing loaded",
              "citations": []}
    record = validate(LINK_CASE, "link_reviewer", answer, opens=("Error executing tool open_page",))
    assert "decision" not in record
    assert record["failure"] == (f"{protocol.BROWSER_TOOL_FAILURE} 1 open_page call(s) returned an error: "
                                 f"['{OPENED}']")
    assert record["failure"].startswith(runner.FORMAT_FAILURES)


# Roles, prompts and schemas.

def test_the_roles_are_the_link_and_miss_questions() -> None:
    assert protocol.STAGE_FIELDS == {"link": ("canonical_identity",), "miss": ("names_one_ruler",)}
    assert {name: (role.prompt.name, role.schema.name, role.reconciler) for name, role in protocol.ROLES.items()} == {
        "link_reviewer": ("link-reviewer-v1.txt", "link-reviewer-case-v1.schema.json", False),
        "link_reconciler": ("link-reconciler-v1.txt", "link-reconciler-case-v1.schema.json", True),
        "miss_reviewer": ("miss-reviewer-v1.txt", "miss-reviewer-case-v1.schema.json", False),
        "miss_reconciler": ("miss-reconciler-v1.txt", "miss-reconciler-case-v1.schema.json", True),
    }
    for role in protocol.ROLES.values():
        prompt = role.prompt.read_text()
        assert "decoy" not in prompt.casefold() and "Senusret" not in prompt
        assert "UNESCO" not in prompt and "entity at the level" not in prompt


def test_a_link_review_is_validated_with_its_citation() -> None:
    answer = {"case_id": "link-001", "canonical_identity": "exact_identity", "reasoning": "r", "citations": [OPENED]}
    assert validate(LINK_CASE, "link_reviewer", answer)["decision"] == answer


def test_a_miss_review_names_a_ruler_only_when_it_finds_one() -> None:
    one = {"case_id": "miss-001", "names_one_ruler": "one_ruler", "ruler": "Djoser", "reasoning": "r", "citations": [OPENED]}
    assert validate(MISS_CASE, "miss_reviewer", one)["decision"] == one
    for bad, why in (({**one, "ruler": ""}, "should be non-empty"),
                     ({**one, "names_one_ruler": "not_one_ruler"}, "is expected to be empty"),
                     ({**one, "citations": []}, "should be non-empty")):
        record = validate(MISS_CASE, "miss_reviewer", bad)
        assert record["failure"].startswith("invalid decision: ValidationError") and why in record["failure"]
    none = {**one, "names_one_ruler": "insufficient_evidence", "ruler": "", "citations": [OPENED]}
    assert validate(MISS_CASE, "miss_reviewer", none)["decision"] == none


def test_a_miss_reconciler_sees_each_reviews_named_ruler(tmp_path: Path) -> None:
    for label, (outcome, ruler) in zip(protocol.REVIEWERS, (("one_ruler", "Djoser"), ("insufficient_evidence", ""))):
        directory = tmp_path / f"reviewer-{label}"
        directory.mkdir()
        role = protocol.ROLES["miss_reviewer"]
        inputs = protocol.role_inputs(role)
        answer = {"case_id": "miss-001", "names_one_ruler": outcome, "ruler": ruler, "reasoning": label, "citations": [OPENED]}
        record = {"case_id": "miss-001", "system_prompt": inputs["system_prompt"],
                  "user_content": protocol.compose_user_content(MISS_CASE, inputs["prompt"], inputs["schema"], inputs["citable_sources"]),
                  "run_bindings": protocol.run_bindings(), "exit_code": 0, "events": events(answer, session_id=label)}
        record = protocol.validate(record, MISS_CASE, role, inputs["schema"])
        protocol.write_new(directory / "miss-001.attempt-1.json", record)
    queue = protocol.reconciliation_queue("miss", {"cases": [MISS_CASE]}, tmp_path)
    [item] = queue["cases"]
    assert item["disputed_questions"] == ["names_one_ruler"]
    assert sorted((r["names_one_ruler"], r["ruler"]) for r in item["reviews"]) == [
        ("insufficient_evidence", ""), ("one_ruler", "Djoser")]
    assert sorted(item["reviews"][0]) == ["citations", "label", "names_one_ruler", "reasoning", "ruler"]


# The queue builder.

CATALOG = {
    "k-12.02": {"label": "Senusret I"}, "k-12.04": {"label": "Senusret II"}, "k-12.05": {"label": "Senusret III"},
    "k-03.02": {"label": "Djoser"}, "k-26.03": {"label": "Psametik II."}, "k-26.06": {"label": "Psametik III."},
    "w-ahmes": {"label": "Ahmes B"},
}


def test_a_decoy_is_another_ruler_of_the_same_name_and_another_number() -> None:
    assert builder.decoy_target("k-12.02", CATALOG) in {"k-12.04", "k-12.05"}
    assert builder.decoy_target("k-26.03", CATALOG) == "k-26.06"
    assert builder.decoy_target("k-03.02", CATALOG) is None   # no number
    assert builder.decoy_target("w-ahmes", CATALOG) is None   # a royal woman's letter is no number
    picks = {builder.decoy_target("k-12.05", CATALOG) for _ in range(3)}
    assert len(picks) == 1  # seeded, not random


def test_too_few_decoy_candidates_fail_loud() -> None:
    units = [{"unit_id": "unit-a", "resolved_target_ids": ["k-03.02"]}]
    with pytest.raises(ValueError, match="only 0 link units have a decoy target"):
        builder.choose_decoys(units, CATALOG)


def test_record_texts_group_records_by_their_field_texts() -> None:
    rows = [{"artifact_id": f"met-{n}", "field_path": "reign", "field_value": "reign of Djoser"} for n in range(7)]
    rows.append({"artifact_id": "met-9", "field_path": "title", "field_value": "Statue of Djoser"})
    urls = {f"met-{n}": f"https://www.metmuseum.org/art/collection/search/{n}" for n in range(10)}
    entries = builder.record_texts(rows, urls)
    by_text = {e["fields"][0]["field_text"]: e for e in entries}
    assert {t: e["record_count"] for t, e in by_text.items()} == {"reign of Djoser": 7, "Statue of Djoser": 1}
    assert len(by_text["reign of Djoser"]["example_record_urls"]) == builder.EXAMPLE_URLS_PER_TEXT
    assert by_text["Statue of Djoser"]["example_record_urls"] == [urls["met-9"]]


def test_a_case_carrying_a_private_key_is_refused() -> None:
    assert protocol.forbidden_keys({"case_id": "x", "decoy": True, "evidence": {"artifact_ids": []}}) == [
        "$.decoy", "$.evidence.artifact_ids"]
    with pytest.raises(protocol.ProtocolFailure, match="model input carries private keys"):
        protocol.compose_user_content({**LINK_CASE, "unit_kind": "decoy"}, "p", {}, "s")


def test_ruler_counts_group_resolutions_by_text_and_target(tmp_path: Path) -> None:
    rows = [
        {"entity_type": "ruler", "museum": "met", "status": "resolved", "mention_text": "Djoser", "target_ids": ["k-03.02"], "artifact_id": "met-1"},
        {"entity_type": "ruler", "museum": "met", "status": "resolved", "mention_text": "Djoser", "target_ids": ["k-03.02"], "artifact_id": "met-2"},
        {"entity_type": "ruler", "museum": "met", "status": "unmatched", "mention_text": "Shabaqo", "target_ids": [], "artifact_id": "met-3"},
        {"entity_type": "ruler", "museum": "met", "status": "ambiguous", "mention_text": "Ahmose", "target_ids": ["a", "b"], "artifact_id": "met-4"},
        {"entity_type": "ruler", "museum": "met", "status": "abstained", "mention_text": "Ramesses II-Merenptah", "target_ids": [], "artifact_id": "met-5"},
        {"entity_type": "site", "museum": "met", "status": "resolved", "mention_text": "Thebes", "target_ids": ["t"], "artifact_id": "met-6"},
    ]
    with gzip.open(tmp_path / "resolutions-authority.ndjson.gz", "wt") as handle:
        handle.writelines(json.dumps(r) + "\n" for r in rows)
    assert make_run.ruler_counts(tmp_path) == {"met": {
        "linked": {"units": 1, "records": 2, "mentions": 2},
        "missed": {"units": 2, "records": 2, "mentions": 2}}}


# The scorer.

def key_case(case_id: str, kind: str, museum: str = "met", records: tuple = ("met-1",)) -> dict:
    return {"case_id": case_id, "unit_kind": kind, "decoy": kind == "decoy", "museum": museum,
            "artifact_ids": list(records)}


def decoys(missed: int, total: int = 20) -> tuple[list[dict], dict[str, str]]:
    key = [key_case(f"d-{n}", "decoy") for n in range(total)]
    return key, {c["case_id"]: ("exact_identity" if n < missed else "different_identity") for n, c in enumerate(key)}


def test_calibration_fails_when_more_than_one_in_five_decoys_are_not_rejected() -> None:
    for missed, passed in ((4, True), (5, False)):
        key, outcomes = decoys(missed)
        result = scorer.tally(key, outcomes, {})
        assert result["calibration"] == {"decoys": 20, "caught": 20 - missed, "missed": missed,
                                         "by_outcome": {"different_identity": 20 - missed, "exact_identity": missed},
                                         "max_missed_share": [1, 5], "passed": passed}


def test_a_museum_with_a_wrong_link_fails_and_unconfirmed_links_decide_nothing() -> None:
    key, outcomes = decoys(0)
    key += [key_case("a", "link", "met", tuple(f"met-{n}" for n in range(10))),
            key_case("b", "link", "met", ("met-10",)),
            key_case("e", "link", "walters", ("walters-1",)),
            key_case("f", "link", "walters", ("walters-2",)),
            key_case("m", "miss", "walters", ("walters-3",))]
    outcomes |= {"a": "exact_identity", "b": "different_identity", "e": "insufficient_evidence",
                 "f": "insufficient_evidence"}
    result = scorer.tally(key, outcomes, {"m": "one_ruler"})
    # Walters has no confirmed link at all, and still passes: unconfirmed links decide nothing.
    assert result["museum_outcomes"] == {"met": "fails", "walters": "passes"}
    assert result["museums"]["met"]["wrong"] == {"units": 1, "records": 1}
    assert result["museums"]["met"]["confirmed"] == {"units": 1, "records": 10}
    assert result["museums"]["walters"]["unconfirmed"] == {"units": 2, "records": 2}
    assert result["museums"]["walters"]["miss"]["names_one_ruler"] == {"units": 1, "records": 1}
    assert scorer.museum_outcomes(result["museums"], False) == {"met": "no_decision", "walters": "no_decision"}


def test_the_decision_rule_is_approved() -> None:
    rule = (EVALUATION / "decision-rule.md").read_text()
    assert rule.startswith("# Per-museum ruler test — decision rule\n\n**Approved by the project owner on 2026-10-17")
    assert "DRAFT" not in rule and '"Don\'t count them"' in rule and '"No wrong links"' in rule


# The committed run.

def test_the_committed_run_counts_what_the_test_reviews() -> None:
    manifest = json.loads((EVALUATION / "results/run-manifest.json").read_text())
    assert manifest["schema_version"] == "hapi-ruler-per-museum-2026-10-17-run/1"
    assert manifest["make_run_sha256"] == builder.sha256_path(SCRIPTS / "make_run.py")
    assert manifest["two_runs"]["same_manifest_and_contents"] is True
    assert manifest["ruler_counts"] == {
        "brooklyn": {"linked": {"mentions": 25, "records": 24, "units": 16}, "missed": {"mentions": 37, "records": 33, "units": 25}},
        "cleveland": {"linked": {"mentions": 76, "records": 76, "units": 13}, "missed": {"mentions": 3, "records": 3, "units": 3}},
        "harvard": {"linked": {"mentions": 5, "records": 3, "units": 3}, "missed": {"mentions": 0, "records": 0, "units": 0}},
        "met": {"linked": {"mentions": 8985, "records": 8869, "units": 107}, "missed": {"mentions": 344, "records": 319, "units": 99}},
        "walters": {"linked": {"mentions": 72, "records": 62, "units": 35}, "missed": {"mentions": 50, "records": 49, "units": 34}},
    }


def test_the_committed_population_is_the_runs_and_binds_the_audited_protocol() -> None:
    digest = json.loads((EVALUATION / "results/review-population-digest.json").read_text())
    run = json.loads((EVALUATION / "results/run-manifest.json").read_text())
    assert digest["run_id"] == run["run_id"] and digest["decoy_count"] == 20
    assert digest["builder_sha256"] == builder.sha256_path(SCRIPTS / "build_queue.py")
    assert {m: {"link": c["link"], "miss": c["miss"]} for m, c in digest["population"].items()} == {
        m: {"link": c["linked"]["units"], "miss": c["missed"]["units"]} for m, c in run["ruler_counts"].items()}
    assert {m: c["link_records"] for m, c in digest["population"].items()} == {
        m: c["linked"]["records"] for m, c in run["ruler_counts"].items()}
    assert sum(c["decoy"] for c in digest["population"].values()) == 20
    bound = digest["review_protocol"]
    for binding in [*bound["prompts"].values(), *bound["schemas"].values(),
                    *(v for v in bound.values() if isinstance(v, dict) and "path" in v)]:
        assert builder.sha256_path(ROOT / binding["path"]) == binding["sha256"], binding["path"]


def test_the_prompts_are_the_audited_bytes() -> None:
    audit = (EVALUATION / "prompt-audit-2026-10-17.md").read_text()
    table = dict(line.split(" | ")[0:2] for line in (
        row.strip("| ").replace("`", "") for row in audit.split("## Audited bytes")[1].splitlines()
        if row.startswith("| `")))
    files = sorted(p.relative_to(EVALUATION).as_posix() for p in (
        *EVALUATION.glob("prompts/*.txt"), *EVALUATION.glob("raw-response-contracts/*.json")))
    assert set(files) <= set(table)
    for path, sha in table.items():
        assert builder.sha256_path(EVALUATION / path) == sha, path


def test_every_preflight_page_loaded_before_the_run() -> None:
    """README: the run starts only once every record page the preflight opens has loaded."""
    check = json.loads((EVALUATION / "results/preflight-page-check.json").read_text())
    digest = json.loads((EVALUATION / "results/review-population-digest.json").read_text())
    assert check["queue_sha256"] == {n: digest["output_sha256"][n] for n in ("link-queue.json", "miss-queue.json")}
    pages = check["pages"]
    assert len(pages) == 270 and all(page.get("loaded") is True for page in pages)
    by_host: dict[str, int] = {}
    for page in pages:
        by_host[page["host"]] = by_host.get(page["host"], 0) + 1
    assert by_host == {"brooklynmuseum.org": 55, "clevelandart.org": 44, "harvardartmuseums.org": 3,
                       "metmuseum.org": 60, "purl.thewalters.org": 108}
