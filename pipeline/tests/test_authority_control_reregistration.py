"""#337 re-registration (2026-10-11): per-case review protocol, consensus, scorer decision rule."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EVALUATION = ROOT / "docs" / "evaluations" / "authority-independent-control-2026-10-11"
SCRIPTS = EVALUATION / "scripts"


def _load(name: str, filename: str):
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


protocol = _load("review_protocol", "review_protocol.py")
scorer = _load("_reregistration_score_review", "score_review.py")
queue_builder = _load("_reregistration_build_review_queue", "build_review_queue.py")
runner = _load("_reregistration_run_harness_review", "run_harness_review.py")

HASH_1 = "1" * 64
HASH_2 = "2" * 64


def stage_1_case(case_id: str, evidence_sha256: str) -> dict:
    return {
        "case_id": case_id,
        "evidence_sha256": evidence_sha256,
        "entity_type": "site",
        "museum_pair": ["met", "brooklyn"],
        "sides": {"met": [{"representative_exact_mention": "Abydos"}],
                  "brooklyn": [{"representative_exact_mention": "Abydos"}]},
    }


def events(answer: dict | str, *, search_url: str = "https://www.metmuseum.org/art/collection/search/1",
           api_key_source: str = "none", tools: tuple[str, ...] = ("WebFetch", "WebSearch"),
           model: str = "claude-sonnet-5-5") -> list[dict]:
    text = answer if isinstance(answer, str) else json.dumps(answer)
    return [
        {"type": "system", "subtype": "init", "model": model, "apiKeySource": api_key_source,
         "tools": list(tools), "mcp_servers": []},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "WebSearch", "input": {"query": "Abydos"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1"}]},
         "tool_use_result": {"results": [{"content": [{"title": "Abydos", "url": search_url}]}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}},
        {"type": "result", "usage": {"output_tokens": 10}, "total_cost_usd": 0.5},
    ]


def review_answer(case: dict, same: str, useful: str) -> dict:
    return {
        "case_id": case["case_id"], "evidence_sha256": case["evidence_sha256"],
        "same_entity": same, "useful_granularity": useful, "reasoning": f"{same}/{useful}",
        "citations": ["https://www.metmuseum.org/art/collection/search/1"],
        "artifact_exceptions": [],
    }


def write_attempt(directory: Path, role_name: str, case: dict, n: int, answer, **extra) -> Path:
    role = protocol.ROLES[role_name]
    inputs = protocol.role_inputs(role)
    record = {
        "case_id": case["case_id"],
        "evidence_sha256": case["evidence_sha256"],
        "system_prompt": inputs["system_prompt"],
        "user_content": protocol.compose_user_content(case, inputs["prompt"], inputs["schema"]),
        "events": events(answer),
        **extra,
    }
    if "failure" not in extra:
        shown = protocol.reviewer_research(directory.parent, case, role) if role.reconciler else None
        record = protocol.validate(record, case, role, inputs["schema"], shown)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{case['case_id']}.attempt-{n}.json"
    protocol.write_atomic(path, record)
    return path


def test_validate_extracts_the_decision_and_research_from_events() -> None:
    case = stage_1_case("review-unit-001", HASH_1)
    role = protocol.ROLES["stage_1_reviewer"]
    schema = protocol.role_inputs(role)["schema"]
    answer = review_answer(case, "same_entity", "useful")
    record = protocol.validate({"events": events("Wrapping up.\n" + json.dumps(answer))}, case, role, schema)
    assert record["decision"] == answer
    assert record["note_before_answer"] == "Wrapping up."
    assert record["served_model"] == "claude-sonnet-5-5"
    assert record["auth"] == "none"
    assert record["web_searches"] == ["Abydos"]
    assert record["web_search_results"] == [
        {"title": "Abydos", "url": "https://www.metmuseum.org/art/collection/search/1"}
    ]
    assert record["web_fetches"] == []
    assert record["usage"] == {"output_tokens": 10}
    assert record["notional_cost_usd"] == 0.5
    assert "failure" not in record


@pytest.mark.parametrize(
    ("kwargs", "mutate", "failure"),
    [
        ({"api_key_source": "ANTHROPIC_API_KEY"}, None, "API-key auth would bill this call: 'ANTHROPIC_API_KEY'"),
        ({"tools": ("WebFetch", "WebSearch", "Bash")}, None, "unexpected tools ['WebFetch', 'WebSearch', 'Bash'] or MCP servers []"),
        ({"model": "claude-opus-5-5"}, None, "served model 'claude-opus-5-5', not 'claude-sonnet-5-5'"),
        ({"search_url": "https://www.wikidata.org/wiki/Q1"}, None, "blocked domain used: ['https://www.wikidata.org/wiki/Q1']"),
        ({}, {"case_id": "review-unit-002"}, "decision does not echo the case ID and evidence hash exactly"),
        ({}, {"same_entity": "probably"}, None),
        ({}, {"citations": ["https://github.com/pcomans/hapi"]}, "blocked domain used: ['https://github.com/pcomans/hapi']"),
    ],
)
def test_validate_fails_loud(kwargs: dict, mutate: dict | None, failure: str | None) -> None:
    case = stage_1_case("review-unit-001", HASH_1)
    role = protocol.ROLES["stage_1_reviewer"]
    schema = protocol.role_inputs(role)["schema"]
    answer = {**review_answer(case, "same_entity", "useful"), **(mutate or {})}
    record = protocol.validate({"events": events(answer, **kwargs)}, case, role, schema)
    assert "decision" not in record
    if failure is None:
        assert record["failure"].startswith("invalid decision: ValidationError: 'probably' is not one of")
    else:
        assert record["failure"] == failure


def test_reconciler_must_resolve_exactly_the_disputed_questions() -> None:
    case = stage_1_case("review-unit-001", HASH_1)
    item = {"case_id": case["case_id"], "evidence_sha256": HASH_1, "case": case,
            "disputed_questions": ["useful_granularity"], "reviews": []}
    role = protocol.ROLES["stage_1_reconciler"]
    schema = protocol.role_inputs(role)["schema"]
    resolution = {"outcome": "too_broad", "rationale": "r", "citations": ["https://www.metmuseum.org/art/collection/search/1"]}
    wrong = {"case_id": case["case_id"], "evidence_sha256": HASH_1, "artifact_exceptions": [],
             "resolutions": {"same_entity": {**resolution, "outcome": "same_entity"},
                             "useful_granularity": resolution}}
    record = protocol.validate({"events": events(wrong)}, item, role, schema, set())
    assert record["failure"] == (
        "invalid decision: resolves ['same_entity', 'useful_granularity'], "
        "not the disputed questions ['useful_granularity']"
    )
    right = {**wrong, "resolutions": {"useful_granularity": resolution}}
    assert protocol.validate({"events": events(right)}, item, role, schema, set())["decision"] == right


def test_model_input_refuses_private_keys() -> None:
    case = {**stage_1_case("review-unit-001", HASH_1), "transition_class": "retained_control"}
    with pytest.raises(protocol.ProtocolFailure, match=r"private keys: \['\$.transition_class'\]"):
        protocol.compose_user_content(case, "prompt", {})


def _stage_1_records(tmp_path: Path) -> tuple[Path, Path, dict, dict]:
    agree = stage_1_case("review-unit-001", HASH_1)
    dispute = stage_1_case("review-unit-002", HASH_2)
    queue = {"cases": [dispute, agree]}
    queue_path = tmp_path / "stage-1-queue.json"
    queue_path.write_text(json.dumps(queue))
    records = tmp_path / "stage-1"
    write_attempt(records / "reviewer-A", "stage_1_reviewer", agree, 1, review_answer(agree, "same_entity", "useful"))
    write_attempt(records / "reviewer-B", "stage_1_reviewer", agree, 1, review_answer(agree, "same_entity", "useful"))
    write_attempt(records / "reviewer-A", "stage_1_reviewer", dispute, 1, review_answer(dispute, "same_entity", "useful"))
    write_attempt(records / "reviewer-B", "stage_1_reviewer", dispute, 1, review_answer(dispute, "same_entity", "too_broad"))
    return queue_path, records, agree, dispute


def test_consensus_is_agreement_or_cited_override_and_fails_without_one(tmp_path: Path) -> None:
    queue_path, records, agree, dispute = _stage_1_records(tmp_path)
    reconcile = protocol.reconciliation_queue("1", json.loads(queue_path.read_text()), records)
    assert [item["case_id"] for item in reconcile["cases"]] == ["review-unit-002"]
    item = reconcile["cases"][0]
    assert item["disputed_questions"] == ["useful_granularity"]
    assert item["case"] == dispute
    assert sorted(r["useful_granularity"] for r in item["reviews"]) == ["too_broad", "useful"]
    assert [r["label"] for r in item["reviews"]] == ["review-1", "review-2"]
    assert all(set(r) == {"label", "same_entity", "useful_granularity", "reasoning", "citations",
                          "artifact_exceptions"} for r in item["reviews"])

    with pytest.raises(protocol.ProtocolFailure, match="no record for review-unit-002"):
        protocol.build_consensus("1", queue_path, records)

    resolution = {"outcome": "too_broad", "rationale": "Region, not a site.",
                  "citations": ["https://www.metmuseum.org/art/collection/search/1"]}
    override = write_attempt(records / "reconciler", "stage_1_reconciler", item, 1, {
        "case_id": "review-unit-002", "evidence_sha256": HASH_2, "artifact_exceptions": [],
        "resolutions": {"useful_granularity": resolution},
    })
    consensus = protocol.build_consensus("1", queue_path, records)
    sha = lambda label, case: protocol.sha256_path(records / f"reviewer-{label}" / f"{case}.attempt-1.json")
    assert consensus["stage"] == "1"
    assert consensus["queue_sha256"] == protocol.sha256_path(queue_path)
    assert consensus["roles"]["stage_1_reconciler"]["prompt"] == {
        "path": "stage-1-reconciler-v3.txt",
        "sha256": protocol.sha256_path(protocol.ROLES["stage_1_reconciler"].prompt),
    }
    agreed, disputed = consensus["decisions"]
    assert agreed["case_id"] == "review-unit-001"
    assert (agreed["same_entity"], agreed["useful_granularity"]) == ("same_entity", "useful")
    assert agreed["field_resolutions"]["useful_granularity"] == {
        "method": "agreement",
        "source_outcomes": sorted(
            [{"review_sha256": sha("A", "review-unit-001"), "outcome": "useful"},
             {"review_sha256": sha("B", "review-unit-001"), "outcome": "useful"}],
            key=lambda s: s["review_sha256"]),
    }
    assert (disputed["same_entity"], disputed["useful_granularity"]) == ("same_entity", "too_broad")
    assert disputed["field_resolutions"]["same_entity"]["method"] == "agreement"
    assert disputed["field_resolutions"]["useful_granularity"] == {
        "method": "explicit_cited_override",
        "source_outcomes": sorted(
            [{"review_sha256": sha("A", "review-unit-002"), "outcome": "useful"},
             {"review_sha256": sha("B", "review-unit-002"), "outcome": "too_broad"}],
            key=lambda s: s["review_sha256"]),
        "reconciler_record_sha256": protocol.sha256_path(override),
        "rationale": "Region, not a site.",
        "citations": ["https://www.metmuseum.org/art/collection/search/1"],
    }

    frozen = tmp_path / "consensus.json"
    protocol.write_new(frozen, consensus)
    assert protocol.verify_consensus("1", frozen, queue_path, records) == consensus
    with pytest.raises(protocol.ProtocolFailure, match="never overwritten"):
        protocol.write_new(frozen, consensus)
    tampered = copy.deepcopy(consensus)
    tampered["decisions"][1]["useful_granularity"] = "useful"
    frozen.write_text(json.dumps(tampered))
    with pytest.raises(protocol.ProtocolFailure, match="is not the consensus of the stored Stage 1 records"):
        protocol.verify_consensus("1", frozen, queue_path, records)


def test_decided_record_counts_a_recheck_as_its_source_call_and_rejects_two_calls(tmp_path: Path) -> None:
    case = stage_1_case("review-unit-001", HASH_1)
    directory = tmp_path / "reviewer-A"
    role = protocol.ROLES["stage_1_reviewer"]
    inputs = protocol.role_inputs(role)
    answer = review_answer(case, "different_entity", "too_broad")
    write_attempt(directory, "stage_1_reviewer", case, 1, answer, failure="invalid decision: old rule")
    recheck = write_attempt(directory, "stage_1_reviewer", case, 2, answer,
                            revalidated_from=f"{case['case_id']}.attempt-1.json")
    sha, record = protocol.decided_record(directory, case, role, inputs)
    assert sha == protocol.sha256_path(recheck)
    assert record["decision"] == answer
    assert record["revalidated_from"] == "review-unit-001.attempt-1.json"

    write_attempt(directory, "stage_1_reviewer", case, 3, answer)
    with pytest.raises(protocol.ProtocolFailure, match=r"valid calls \['review-unit-001.attempt-1.json', "
                       r"'review-unit-001.attempt-3.json'\]"):
        protocol.decided_record(directory, case, role, inputs)


def test_decided_record_rejects_a_record_composed_from_another_prompt(tmp_path: Path) -> None:
    case = stage_1_case("review-unit-001", HASH_1)
    path = write_attempt(tmp_path, "stage_1_reviewer", case, 1, review_answer(case, "same_entity", "useful"))
    stored = json.loads(path.read_text())
    stored["user_content"] = stored["user_content"].replace("Role:", "Role (edited):", 1)
    path.write_text(json.dumps(stored))
    role = protocol.ROLES["stage_1_reviewer"]
    with pytest.raises(protocol.ProtocolFailure, match="not composed from the current prompt"):
        protocol.decided_record(tmp_path, case, role, protocol.role_inputs(role))


def joined_case(transition: str, category: str, entity: str = "site", pair=("met", "brooklyn")) -> dict:
    return {"transition_class": transition, "decision_category": category,
            "entity_type": entity, "museum_pair": list(pair)}


A, B, C, D, E, F = scorer.PRIMARY_CATEGORIES
OK = "calibration_control_same_useful_exact_target"
UNCERTAIN = "calibration_control_uncertainty"
GAIN, LOSS, CONTROL = "authority_only_transition", "literal_only_transition", "retained_control"


def test_decision_rule_calibration_boundary_is_more_than_twenty_percent() -> None:
    transitions = [joined_case(GAIN, A), joined_case(GAIN, A), joined_case(LOSS, E)]
    at_limit = [joined_case(CONTROL, OK)] * 4 + [joined_case(CONTROL, UNCERTAIN)] + transitions
    result = scorer.decision_rule(at_limit)
    assert result["calibration"] == {"retained_controls": 5, "uncertain_or_wrong": 1, "passed": True}
    assert result["verdict"] == "CONTINUE"
    over = [joined_case(CONTROL, OK)] * 3 + [joined_case(CONTROL, UNCERTAIN)] * 2 + transitions
    result = scorer.decision_rule(over)
    assert result["calibration"] == {"retained_controls": 5, "uncertain_or_wrong": 2, "passed": False}
    assert result["verdict"] == "INCONCLUSIVE"
    assert result["qualifying_scopes"] == []


def test_decision_rule_safety_redesigns_on_two_b_or_more_than_ten_percent() -> None:
    controls = [joined_case(CONTROL, OK)] * 10
    one_b_of_ten = [joined_case(GAIN, B)] + [joined_case(GAIN, A)] * 9 + [joined_case(LOSS, E)] * 3
    result = scorer.decision_rule(controls + one_b_of_ten)
    assert result["safety"] == {"b": 1, "authority_gains": 10,
                                "unsafe_scopes": ["site__met__brooklyn"], "passed": True}
    # The only scope has a b, so it cannot qualify.
    assert result["scopes"]["site__met__brooklyn"]["qualifies"] is False
    assert result["verdict"] == "STOP"
    one_b_of_nine = [joined_case(GAIN, B)] + [joined_case(GAIN, A)] * 8
    result = scorer.decision_rule(controls + one_b_of_nine)
    assert result["safety"]["passed"] is False
    assert result["verdict"] == "REDESIGN"
    two_b = [joined_case(GAIN, B), joined_case(GAIN, B, "ruler")] + [joined_case(GAIN, A)] * 30
    result = scorer.decision_rule(controls + two_b)
    assert result["safety"]["unsafe_scopes"] == ["ruler__met__brooklyn", "site__met__brooklyn"]
    assert result["verdict"] == "REDESIGN"


def test_decision_rule_utility_lists_only_qualifying_scopes() -> None:
    controls = [joined_case(CONTROL, OK)] * 10
    qualifies = [joined_case(GAIN, A), joined_case(LOSS, E), joined_case(LOSS, D), joined_case(GAIN, F)]
    too_few = [joined_case(GAIN, A, "ruler"), joined_case(GAIN, A, "ruler")]
    loses = [joined_case(GAIN, A, pair=("met", "harvard"))] + [
        joined_case(LOSS, D, pair=("met", "harvard"))] * 2 + [joined_case(LOSS, E, pair=("met", "harvard"))]
    uncertain = [joined_case(GAIN, A, pair=("brooklyn", "harvard"))] * 3 + [
        joined_case(GAIN, F, pair=("brooklyn", "harvard"))] * 2
    result = scorer.decision_rule(controls + qualifies + too_few + loses + uncertain)
    assert result["scopes"] == {
        "ruler__met__brooklyn": {"a": 2, "b": 0, "c": 0, "d": 0, "e": 0, "f": 0,
                                 "changed": 2, "decided": 2, "qualifies": False},
        "site__brooklyn__harvard": {"a": 3, "b": 0, "c": 0, "d": 0, "e": 0, "f": 2,
                                    "changed": 5, "decided": 3, "qualifies": False},
        "site__met__brooklyn": {"a": 1, "b": 0, "c": 0, "d": 1, "e": 1, "f": 1,
                                "changed": 4, "decided": 3, "qualifies": True},
        "site__met__harvard": {"a": 1, "b": 0, "c": 0, "d": 2, "e": 1, "f": 0,
                               "changed": 4, "decided": 4, "qualifies": False},
    }
    assert result["totals"] == {"a": 7, "b": 0, "c": 0, "d": 3, "e": 2, "f": 3}
    assert result["qualifying_scopes"] == ["site__met__brooklyn"]
    assert result["verdict"] == "CONTINUE"


def test_released_stage_2_case_carries_evidence_target_and_no_private_binding() -> None:
    stage_1 = {**stage_1_case("review-unit-007", HASH_1), "questions": {"same_entity": {}}}
    custodian = {
        "case_id": "case-004", "stage_1_review_unit_id": "review-unit-007", "evidence_sha256": HASH_1,
        "proposed_target": {"target_id": "cluster-x", "target_label": "Senusret III", "target_metadata": {
            "entity_type": "ruler", "member_ids": ["beckerath-12.05"], "source_ids": ["beckerath"],
            "name_claim_ids": ["stmt-1"], "label_count_including_duplicates": 26}},
        "question": "Exact?", "allowed_outcomes": ["exact_identity", "different_identity", "insufficient_evidence"],
    }
    released = queue_builder.released_stage_2_case(custodian, stage_1)
    assert released == {
        "case_id": "case-004", "evidence_sha256": HASH_1, "entity_type": "site",
        "museum_pair": ["met", "brooklyn"], "sides": stage_1["sides"],
        "proposed_target": {"target_id": "cluster-x", "target_label": "Senusret III", "target_metadata": {
            "entity_type": "ruler", "member_ids": ["beckerath-12.05"], "source_ids": ["beckerath"]}},
        "question": "Exact?",
        "allowed_outcomes": ["exact_identity", "different_identity", "insufficient_evidence"],
    }
    assert protocol.forbidden_keys(released) == []


def test_scorer_requires_the_reviewed_stage_2_queue_to_be_the_release_of_the_custodian() -> None:
    stage_1 = {**stage_1_case("review-unit-007", HASH_1), "questions": {"same_entity": {}}}
    custodian = {
        "review_protocol": {"protocol_version": "x"},
        "cases": [{
            "case_id": "case-004", "stage_1_review_unit_id": "review-unit-007", "evidence_sha256": HASH_1,
            "proposed_target": {"target_id": "cluster-x", "target_label": "Senusret III", "target_metadata": {
                "entity_type": "ruler", "member_ids": ["beckerath-12.05"], "source_ids": ["beckerath"]}},
            "question": "Exact?", "allowed_outcomes": ["exact_identity", "different_identity", "insufficient_evidence"],
        }],
    }
    hashes = {"stage_1_queue_sha256": HASH_1, "consensus_sha256": HASH_2, "custodian_sha256": "3" * 64}
    released = queue_builder.released_stage_2_queue({"cases": [stage_1]}, custodian, **hashes)
    scorer.verify_stage_2_release(ROOT, released, {"cases": [stage_1]}, custodian, **hashes)
    for edit in (
        lambda q: q["cases"][0]["proposed_target"].update(target_label="Senusret II"),
        lambda q: q["cases"][0]["proposed_target"]["target_metadata"]["member_ids"].append("kitchen-12.04"),
        lambda q: q.update(frozen_stage_1_consensus_sha256="4" * 64),
    ):
        edited = copy.deepcopy(released)
        edit(edited)
        with pytest.raises(ValueError, match="Stage 2 queue is not the release of the bound custodian"):
            scorer.verify_stage_2_release(ROOT, edited, {"cases": [stage_1]}, custodian, **hashes)


def test_every_judgment_must_cite_a_source_the_record_shows_was_consulted() -> None:
    case = {**stage_1_case("review-unit-001", HASH_1), "sides": {
        "met": [{"source_url": "https://www.metmuseum.org/art/collection/search/7"}],
        "brooklyn": [{"representative_exact_mention": "Abydos"}]}}
    role = protocol.ROLES["stage_1_reviewer"]
    schema = protocol.role_inputs(role)["schema"]
    base = review_answer(case, "same_entity", "useful")
    unseen = "https://www.metmuseum.org/toah/works-of-art/14.6.179"

    only_unseen = protocol.validate({"events": events({**base, "citations": [unseen]})}, case, role, schema)
    assert "decision" not in only_unseen
    assert only_unseen["failure"] == "judgment cites no consulted source"
    assert only_unseen["unconsulted_citations"] == [unseen]

    # A search result (query and www. ignored) or a URL of the shown case evidence is consulted;
    # an extra unconsulted citation is recorded but does not void the judgment.
    for citations in (
        ["https://metmuseum.org/art/collection/search/1/?position=0", unseen],
        ["https://www.metmuseum.org/art/collection/search/7"],
    ):
        record = protocol.validate({"events": events({**base, "citations": citations})}, case, role, schema)
        assert record["decision"]["citations"] == citations
        assert record["unconsulted_citations"] == sorted({unseen} & set(citations))


def test_a_reconciler_resolution_cites_only_consulted_sources_its_own_or_a_shown_reviews() -> None:
    case = stage_1_case("review-unit-001", HASH_1)
    item = {"case_id": case["case_id"], "evidence_sha256": HASH_1, "case": case,
            "disputed_questions": ["useful_granularity"], "reviews": []}
    role = protocol.ROLES["stage_1_reconciler"]
    schema = protocol.role_inputs(role)["schema"]
    searched = "https://www.metmuseum.org/art/collection/search/1"
    fetched_by_a_review = "https://collectionapi.metmuseum.org/public/collection/v1/objects/543936"

    def answer(citations):
        return {"case_id": case["case_id"], "evidence_sha256": HASH_1, "artifact_exceptions": [],
                "resolutions": {"useful_granularity": {"outcome": "too_broad", "rationale": "r",
                                                       "citations": citations}}}

    # One consulted citation is not enough for an override: its citations reach the consensus.
    record = protocol.validate({"events": events(answer([searched, fetched_by_a_review]))}, item, role, schema, set())
    assert record["failure"] == "resolution cites an unconsulted source: ['useful_granularity']"
    assert record["unconsulted_citations"] == [fetched_by_a_review]
    shown = {protocol._page(fetched_by_a_review)}
    record = protocol.validate({"events": events(answer([searched, fetched_by_a_review]))}, item, role, schema, shown)
    assert record["decision"] == answer([searched, fetched_by_a_review])
    assert record["unconsulted_citations"] == []
    with pytest.raises(protocol.ProtocolFailure, match="shown_research is required for a reconciler only"):
        protocol.validate({"events": events(answer([searched]))}, item, role, schema)
    with pytest.raises(protocol.ProtocolFailure, match="shown_research is required for a reconciler only"):
        protocol.validate({"events": events(review_answer(case, "same_entity", "useful"))}, case,
                          protocol.ROLES["stage_1_reviewer"], schema, set())


def test_committed_citation_support_matches_the_scored_queues() -> None:
    results = EVALUATION / "results"
    support = json.loads((results / "real-citation-support.json").read_text())
    score = json.loads((results / "real-adjudicated-score.json").read_text())
    stage_1, stage_2 = support["stages"]
    assert (stage_1["stage"], stage_1["queue_sha256"]) == ("1", score["input_hashes"]["stage_1_queue"])
    assert (stage_2["stage"], stage_2["queue_sha256"]) == ("2", score["input_hashes"]["stage_2_queue"])
    assert [s["deciding_calls"] for s in support["stages"]] == [219, 132]
    assert [s["judgments_by_support"] for s in support["stages"]] == [
        {"research": 219, "case_evidence_only": 1}, {"research": 132, "case_evidence_only": 0}]
    listed = [(s["stage"], u["case_id"], u["role"], u["url"]) for s in support["stages"] for u in s["unconsulted_citations"]]
    assert listed == [
        ("1", "review-unit-050", "reviewer-B", "https://www.metmuseum.org/departments/egyptian-art/research"),
        ("1", "review-unit-055", "reviewer-A", "https://www.metmuseum.org/perspectives/from-the-vaults-fayum-funerary-portraits"),
        ("1", "review-unit-077", "reviewer-A", "https://whc.unesco.org/en/list/295/"),
        ("1", "review-unit-080", "reviewer-A", "https://www.metmuseum.org/art/collection/search/549625"),
        ("1", "review-unit-104", "reviewer-B", "https://whc.unesco.org/en/list/87"),
        ("2", "case-065", "reviewer-B", "https://www.metmuseum.org/art/collection/search/549625"),
        ("2", "case-071", "reviewer-A", "https://www.metmuseum.org/perspectives/malqata-excavation"),
    ]
    assert all(len(u["record_sha256"]) == 64 for s in support["stages"] for u in s["unconsulted_citations"])


def test_committed_digest_binds_every_current_protocol_file() -> None:
    digest = json.loads((EVALUATION / "results" / "real-review-population-digest.json").read_text())
    bindings = digest["input_hashes"]["review_protocol"]
    assert bindings == queue_builder.review_protocol_inputs(ROOT)
    assert sorted(bindings["prompts"]) == [
        "stage_1_reconciler", "stage_1_reviewer", "stage_2_reconciler", "stage_2_reviewer",
    ]
    assert bindings["prompts"]["stage_2_reviewer"]["path"] == (
        "docs/evaluations/authority-independent-control-2026-10-11/prompts/stage-2-reviewer-v3.txt"
    )


def test_a_tool_call_refused_by_the_session_limit_makes_the_call_a_stop_not_a_decision(tmp_path: Path) -> None:
    case = stage_1_case("review-unit-001", HASH_1)
    role = protocol.ROLES["stage_1_reviewer"]
    inputs = protocol.role_inputs(role)
    stream = events(review_answer(case, "same_entity", "useful"))
    refused = {"type": "user", "message": {"content": [{
        "type": "tool_result", "tool_use_id": "t2", "is_error": True,
        "content": "You've hit your session limit · resets 5:10am (UTC)"}]}}
    stream.insert(3, {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t2", "name": "WebFetch", "input": {"url": "https://example.org/x"}}]}})
    stream.insert(4, refused)
    record = protocol.validate({"events": stream}, case, role, inputs["schema"])
    assert record["failure"] == "Claude Code session limit during research: 1 tool call(s) refused"
    assert "decision" not in record

    # A stored decision formed under such a refusal no longer counts once re-checked.
    path = tmp_path / "review-unit-001.attempt-1.json"
    protocol.write_atomic(path, {
        "case_id": case["case_id"], "evidence_sha256": HASH_1, "system_prompt": inputs["system_prompt"],
        "user_content": protocol.compose_user_content(case, inputs["prompt"], inputs["schema"]),
        "events": stream, "decision": review_answer(case, "same_entity", "useful"),
    })
    with pytest.raises(protocol.ProtocolFailure, match="stored outcome differs from its re-check"):
        protocol.decided_record(tmp_path, case, role, inputs)


def test_committed_score_verdict_follows_from_its_own_counts() -> None:
    score = json.loads((EVALUATION / "results" / "real-adjudicated-score.json").read_text())
    rule = score["decision_rule"]
    letters = {category[0]: category for category in scorer.PRIMARY_CATEGORIES}
    joined = [
        joined_case(CONTROL, category)
        for category, count in score["calibration_control_counts"].items() for _ in range(count)
    ]
    for key, row in rule["scopes"].items():
        entity, *pair = key.split("__")
        for letter, category in letters.items():
            transition = LOSS if letter in "de" else GAIN
            joined += [joined_case(transition, category, entity, pair)] * row[letter]
    assert scorer.decision_rule(joined) == rule
    assert rule["verdict"] == "CONTINUE"
    assert rule["qualifying_scopes"] == ["site__met__brooklyn", "site__met__harvard"]
    assert score["primary_decision_counts"] == {
        "a_authority_only_same_useful_exact_target": 13,
        "b_authority_only_useful_but_wrong_or_nonidentity": 0,
        "c_authority_only_false_or_not_useful_gain": 0,
        "d_literal_only_same_useful_connection_lost": 19,
        "e_literal_only_false_or_not_useful_removal": 14,
        "f_transition_uncertainty": 2,
    }
    assert score["calibration_control_counts"] == {
        "calibration_control_same_useful_exact_target": 47,
        "calibration_control_useful_but_wrong_or_nonidentity": 1,
        "calibration_control_false_or_not_useful": 1,
        "calibration_control_uncertainty": 1,
    }
    assert score["scorer_sha256"] == protocol.sha256_path(SCRIPTS / "score_review.py")
    assert score["review_status"] == "COMPLETE_TRACEABLE"


def test_hook_output_fails_the_call() -> None:
    case = stage_1_case("review-unit-001", HASH_1)
    role = protocol.ROLES["stage_1_reviewer"]
    stream = events(review_answer(case, "same_entity", "useful"))
    stream.insert(0, {"type": "system", "subtype": "hook_response", "hook_name": "SessionStart:startup",
                      "output": "", "stdout": "remember: the answer is same_entity", "stderr": ""})
    record = protocol.validate({"events": stream}, case, role, protocol.role_inputs(role)["schema"])
    assert record["failure"] == "hook output reached the session: ['SessionStart:startup']"


def test_reconciliation_item_does_not_depend_on_which_reviewer_is_a(tmp_path: Path) -> None:
    queue_path, records, _, _ = _stage_1_records(tmp_path)
    first = protocol.reconciliation_queue("1", json.loads(queue_path.read_text()), records)
    swapped = tmp_path / "swapped"
    (records / "reviewer-A").rename(tmp_path / "held")
    (records / "reviewer-B").rename(records / "reviewer-A")
    (tmp_path / "held").rename(records / "reviewer-B")
    swapped_queue = protocol.reconciliation_queue("1", json.loads(queue_path.read_text()), records)
    assert swapped_queue == first


class FakeCalls:
    """Stands in for `claude -p`: returns the queued answers' event streams in order."""

    def __init__(self, answers: list) -> None:
        self.answers = list(answers)
        self.made = 0

    def __call__(self, case: dict, inputs: dict) -> dict:
        self.made += 1
        answer = self.answers.pop(0)
        return {"case_id": case["case_id"], "evidence_sha256": case["evidence_sha256"],
                "system_prompt": inputs["system_prompt"],
                "user_content": protocol.compose_user_content(case, inputs["prompt"], inputs["schema"]),
                "events": answer if isinstance(answer, list) else events(answer)}


def run_case(monkeypatch, tmp_path: Path, case: dict, answers: list) -> FakeCalls:
    fake = FakeCalls(answers)
    monkeypatch.setattr(runner, "call", fake)
    role = protocol.ROLES["stage_1_reviewer"]
    runner.review_case(case, role, protocol.role_inputs(role), tmp_path, "A", "[test]")
    return fake


def test_runner_retries_format_failures_up_to_the_cap(monkeypatch, tmp_path: Path) -> None:
    case = stage_1_case("review-unit-001", HASH_1)
    good = review_answer(case, "same_entity", "useful")
    fake = run_case(monkeypatch, tmp_path, case, ["not json", {**good, "case_id": "x"}, good])
    assert fake.made == 3
    stored = [json.loads((tmp_path / f"review-unit-001.attempt-{n}.json").read_text()) for n in (1, 2, 3)]
    assert stored[0]["failure"].startswith("invalid decision: JSONDecodeError")
    assert stored[1]["failure"] == "decision does not echo the case ID and evidence hash exactly"
    assert stored[2]["decision"] == good
    assert [r["attempt"] for r in stored] == [1, 2, 3]
    # A decided case is not called again.
    assert run_case(monkeypatch, tmp_path, case, []).made == 0

    other = stage_1_case("review-unit-002", HASH_2)
    with pytest.raises(protocol.ProtocolFailure, match="no valid answer in 3 attempts"):
        run_case(monkeypatch, tmp_path, other, ["bad", "bad", "bad", "bad"])
    assert sorted(p.name for p in tmp_path.glob("review-unit-002.*")) == [
        "review-unit-002.attempt-1.json", "review-unit-002.attempt-2.json", "review-unit-002.attempt-3.json",
    ]


def test_runner_does_not_resume_a_stopped_case_but_resumes_a_session_limit(monkeypatch, tmp_path: Path) -> None:
    case = stage_1_case("review-unit-001", HASH_1)
    good = review_answer(case, "same_entity", "useful")
    no_research = events(good)[:1] + events(good)[3:]
    with pytest.raises(protocol.ProtocolFailure, match="case decided without a search result"):
        run_case(monkeypatch, tmp_path, case, [no_research])
    with pytest.raises(protocol.ProtocolFailure, match="not resumed automatically"):
        run_case(monkeypatch, tmp_path, case, [good])

    limited = stage_1_case("review-unit-002", HASH_2)
    stop = events("You've hit your session limit · resets 5:10am (UTC)")
    with pytest.raises(protocol.ProtocolFailure, match="Claude Code session limit"):
        run_case(monkeypatch, tmp_path, limited, [stop])
    fake = run_case(monkeypatch, tmp_path, limited, [review_answer(limited, "same_entity", "useful")])
    assert fake.made == 1
    assert "decision" in json.loads((tmp_path / "review-unit-002.attempt-2.json").read_text())


def test_runner_writes_a_recheck_when_a_stored_decision_no_longer_stands(monkeypatch, tmp_path: Path) -> None:
    case = stage_1_case("review-unit-001", HASH_1)
    role = protocol.ROLES["stage_1_reviewer"]
    inputs = protocol.role_inputs(role)
    stream = events(review_answer(case, "same_entity", "useful"))
    stream[2]["tool_use_result"]["results"][0]["content"][0]["url"] = "https://www.wikidata.org/wiki/Q1"
    protocol.write_atomic(tmp_path / "review-unit-001.attempt-1.json", {
        "case_id": case["case_id"], "evidence_sha256": HASH_1, "system_prompt": inputs["system_prompt"],
        "user_content": protocol.compose_user_content(case, inputs["prompt"], inputs["schema"]),
        "events": stream, "decision": review_answer(case, "same_entity", "useful"),
    })
    fake = run_case(monkeypatch, tmp_path, case, [review_answer(case, "different_entity", "too_broad")])
    assert fake.made == 1
    recheck = json.loads((tmp_path / "review-unit-001.attempt-2.json").read_text())
    assert recheck["revalidated_from"] == "review-unit-001.attempt-1.json"
    assert recheck["failure"] == "blocked domain used: ['https://www.wikidata.org/wiki/Q1']"
    sha, record = protocol.decided_record(tmp_path, case, role, inputs)
    assert sha == protocol.sha256_path(tmp_path / "review-unit-001.attempt-3.json")
    assert record["decision"]["same_entity"] == "different_entity"


def test_a_recheck_must_carry_its_source_calls_events(tmp_path: Path) -> None:
    case = stage_1_case("review-unit-001", HASH_1)
    role = protocol.ROLES["stage_1_reviewer"]
    write_attempt(tmp_path, "stage_1_reviewer", case, 1, "not json", failure="invalid decision: x")
    write_attempt(tmp_path, "stage_1_reviewer", case, 2, review_answer(case, "same_entity", "useful"),
                  revalidated_from="review-unit-001.attempt-1.json")
    with pytest.raises(protocol.ProtocolFailure, match="a re-check whose events are not those of"):
        protocol.decided_record(tmp_path, case, role, protocol.role_inputs(role))


def node(same: str, useful: str) -> dict:
    return {"stage_1": {"same_entity": same, "useful_granularity": useful}}


@pytest.mark.parametrize(
    ("transition", "stage_1", "stage_2", "category"),
    [
        (GAIN, ("same_entity", "useful"), "exact_identity", A),
        (GAIN, ("same_entity", "useful"), "different_identity", B),
        (GAIN, ("different_entity", "useful"), "exact_identity", B),
        (GAIN, ("same_entity", "too_broad"), "exact_identity", C),
        # Frozen behaviour (README, case-067): an agreed different-entity pair whose
        # granularity is insufficient_evidence is labelled f, not b.
        (GAIN, ("different_entity", "insufficient_evidence"), "different_identity", F),
        (GAIN, ("same_entity", "useful"), "insufficient_evidence", F),
        (LOSS, ("same_entity", "useful"), None, D),
        (LOSS, ("same_entity", "too_broad"), None, E),
        (LOSS, ("different_entity", "too_broad"), None, E),
        (LOSS, ("insufficient_evidence", "insufficient_evidence"), None, F),
        (CONTROL, ("same_entity", "useful"), "exact_identity", OK),
        (CONTROL, ("same_entity", "useful"), "different_identity", "calibration_control_useful_but_wrong_or_nonidentity"),
        (CONTROL, ("same_entity", "too_broad"), "exact_identity", "calibration_control_false_or_not_useful"),
        (CONTROL, ("insufficient_evidence", "insufficient_evidence"), "insufficient_evidence", UNCERTAIN),
    ],
)
def test_classify_case(transition: str, stage_1: tuple, stage_2: str | None, category: str) -> None:
    native = "literal" if transition == LOSS else "authority"
    case = {"transition_class": transition, "arm_native": {native: {"nodes": [node(*stage_1)]}},
            "stage_2": None if stage_2 is None else {"canonical_identity": stage_2}}
    assert scorer.classify_case(case) == category


def test_decision_rule_refuses_an_empty_control_set() -> None:
    with pytest.raises(ValueError, match="no retained controls"):
        scorer.decision_rule([joined_case(GAIN, A)])


def test_committed_results_bind_each_other() -> None:
    results = EVALUATION / "results"
    digest = json.loads((results / "real-review-population-digest.json").read_text())
    score = json.loads((results / "real-adjudicated-score.json").read_text())
    assert digest["review"] == {
        "protocol_manifest_sha256": protocol.sha256_path(results / "real-review-protocol-manifest.json")
    }
    assert score["input_hashes"]["review_population_digest"] == protocol.sha256_path(
        results / "real-review-population-digest.json"
    )
    manifest = json.loads((results / "real-review-protocol-manifest.json").read_text())
    assert manifest["protocol_inputs"] == digest["input_hashes"]["review_protocol"]


def test_audited_prompt_hashes_match_the_prompts_that_run() -> None:
    audit = (EVALUATION / "prompt-audit-2026-10-11.md").read_text()
    table = audit[audit.index("## Audited prompt bytes"):]
    for name, role in protocol.ROLES.items():
        assert f"| `{role.prompt.name}` | `{protocol.sha256_path(role.prompt)}` |" in table, name
