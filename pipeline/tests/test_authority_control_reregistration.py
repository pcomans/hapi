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
        record = protocol.validate(record, case, role, inputs["schema"])
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
    resolution = {"outcome": "too_broad", "rationale": "r", "citations": ["https://example.org/a"]}
    wrong = {"case_id": case["case_id"], "evidence_sha256": HASH_1, "artifact_exceptions": [],
             "resolutions": {"same_entity": {**resolution, "outcome": "same_entity"},
                             "useful_granularity": resolution}}
    record = protocol.validate({"events": events(wrong)}, item, role, schema)
    assert record["failure"] == (
        "invalid decision: resolves ['same_entity', 'useful_granularity'], "
        "not the disputed questions ['useful_granularity']"
    )
    right = {**wrong, "resolutions": {"useful_granularity": resolution}}
    assert protocol.validate({"events": events(right)}, item, role, schema)["decision"] == right


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
                  "citations": ["https://gazetteer.dainst.org/place/1"]}
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
        "citations": ["https://gazetteer.dainst.org/place/1"],
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
