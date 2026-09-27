from __future__ import annotations

import ast
import copy
import importlib.util
import inspect
import json
import shlex
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / "docs" / "evaluations" / "authority-independent-control-2026-09-13" / "scripts"


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, CONTROL / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


extractor = load_module("authority_independent_extract_mentions", "extract_mentions.py")
comparison = load_module("authority_independent_compare_arms", "compare_arms.py")
rerun = load_module("authority_independent_verify_rerun", "verify_rerun.py")
review_queue = load_module("authority_independent_review_queue", "build_review_queue.py")
review_score = load_module("authority_independent_review_score", "score_review.py")
review_protocol = load_module("authority_independent_review_protocol", "review_protocol.py")
review_wrapper = load_module("authority_independent_review_wrapper", "wrap_review_response.py")


def trace_components(
    role: str, prompt: Path, queue: Path, source_reviews: list[Path] | None = None,
) -> list[tuple[str, Path]]:
    components = [
        ("launcher_system_prompt", review_protocol.launcher_system_prompt_path(role)),
        ("reconciler_prompt" if role.endswith("reconciler") else "review_prompt", prompt),
        ("raw_response_contract", review_protocol.raw_response_contract_path(role)),
        ("review_queue", queue),
    ]
    for index, source in enumerate(
        sorted(source_reviews or [], key=review_protocol.sha256_path), 1
    ):
        components.append((f"source_review_{index}", source))
    return components


def trace_run(tmp_path: Path, request_id: str, role: str) -> dict:
    snapshot = "test-review-model-2026-09-14"
    evidence_path = tmp_path / "provider-snapshot-evidence.json"
    if not evidence_path.exists():
        review_queue.write_json(evidence_path, {
            "schema_version": "hapi-provider-model-snapshot-evidence/1",
            "provider": "openai",
            "requested_model_id": "test-review-model",
            "resolved_snapshot_id": snapshot,
            "source_url": f"https://api.openai.com/v1/models/{snapshot}",
            "retrieved_at": "2026-09-14T00:00:00Z",
            "raw_provider_response": {
                "id": snapshot,
                "object": "model",
                "created": 1_789_344_000,
                "owned_by": "openai",
            },
        })
    parameters = {"temperature": 0, "reasoning": {"effort": "high", "summary": "auto"}}
    system_prompt = review_protocol.launcher_system_prompt_path(role)
    envelope = json.dumps({
        "agent_profile": None,
        "credential_mode": "openai_api_key",
        "input_delivery": "stdin_exact_composed_input_bytes",
        "invocation": "POST https://api.openai.com/v1/responses",
        "model_snapshot": snapshot,
        "parameters": parameters,
        "schema_version": "hapi-authority-control-launcher-envelope/2",
        "system_prompt_sha256": review_protocol.sha256_path(system_prompt),
        "transcript_format": "responses_api_jsonl",
        "transport": "openai_responses_api_jsonl",
    }, sort_keys=True, separators=(",", ":"))
    return {
        "request_id": request_id,
        "transport_session_id": f"response-{request_id}",
        "run_date": "2026-09-14",
        "model_id": "test-review-model",
        "model_snapshot": snapshot,
        "reasoning_effort": "high",
        "parameters": parameters,
        "launcher_transport": "openai_responses_api_jsonl",
        "launcher_system_prompt": {
            "path": str(system_prompt),
            "sha256": review_protocol.sha256_path(system_prompt),
        },
        "provider_snapshot_evidence": {
            "path": str(evidence_path),
            "sha256": review_protocol.sha256_path(evidence_path),
        },
        "launcher_envelope": envelope,
        "launcher_envelope_sha256": review_protocol.sha256_text(envelope),
    }


def trace_transcript(role: str, raw: str, run: dict, composed_sha256: str) -> str:
    system_prompt = review_protocol.launcher_system_prompt_path(role).read_text(
        encoding="utf-8"
    )
    response_id = run["transport_session_id"]
    metadata = {
        "hapi_request_id": run["request_id"],
        "hapi_composed_input_sha256": composed_sha256,
    }
    web_required = role.endswith("reviewer") or (
        role.endswith("reconciler")
        and any(
            resolution.get("method") == "explicit_cited_override"
            for decision in json.loads(raw).get("decisions", [])
            for resolution in decision.get("field_resolutions", {}).values()
        )
    )
    created_at = 1_789_344_000
    tools = [{"type": "web_search"}] if web_required else []
    events = [{
        "type": "hapi.transport.request",
        "transport": run["launcher_transport"],
        "request_id": run["request_id"],
        "transport_session_id": response_id,
        "run_date": run["run_date"],
        "model_id": run["model_id"],
        "model_snapshot": run["model_snapshot"],
        "reasoning_effort": run["reasoning_effort"],
        "parameters": run["parameters"],
        "input_sha256": composed_sha256,
        "system_prompt": system_prompt,
        "system_prompt_sha256": review_protocol.sha256_text(system_prompt),
    }, {
        "type": "response.created",
        "sequence_number": 0,
        "response": {
            "id": response_id,
            "object": "response",
            "created_at": created_at,
            "status": "in_progress",
            "instructions": system_prompt,
            "model": run["model_snapshot"],
            "metadata": metadata,
            "output": [],
            "reasoning": {"effort": run["reasoning_effort"]},
            "tools": tools,
            "usage": None,
        },
    }]
    output = []
    sequence_number = 1
    if web_required:
        web_item = {
            "id": "web-1",
            "type": "web_search_call",
            "status": "completed",
            "action": {
                "type": "search",
                "query": "institutional source",
                "sources": [{"url": "https://www.metmuseum.org/"}],
            },
        }
        events.extend([
            {
                "type": "response.output_item.added",
                "sequence_number": sequence_number,
                "output_index": 0,
                "item": {
                    "id": "web-1", "type": "web_search_call",
                    "status": "in_progress",
                },
            },
            {
                "type": "response.output_item.done",
                "sequence_number": sequence_number + 1,
                "output_index": 0,
                "item": web_item,
            },
        ])
        output.append(web_item)
        sequence_number += 2
    reasoning_item = {
        "id": "reasoning-1",
        "type": "reasoning",
        "summary": [{
            "type": "summary_text",
            "text": "Weighed the museum evidence against the citation rule.",
        }],
    }
    events.extend([
        {
            "type": "response.output_item.added",
            "sequence_number": sequence_number,
            "output_index": len(output),
            "item": {"id": "reasoning-1", "type": "reasoning", "status": "in_progress"},
        },
        {
            "type": "response.output_item.done",
            "sequence_number": sequence_number + 1,
            "output_index": len(output),
            "item": reasoning_item,
        },
    ])
    output.append(reasoning_item)
    sequence_number += 2
    message_index = len(output)
    message_item = {
        "id": "message-1",
        "type": "message",
        "status": "completed",
        "role": "assistant",
        "content": [{"type": "output_text", "text": raw, "annotations": []}],
    }
    events.extend([{
        "type": "response.output_item.added",
        "sequence_number": sequence_number,
        "output_index": message_index,
        "item": {
            "id": "message-1", "type": "message", "status": "in_progress",
            "role": "assistant", "content": [],
        },
    }, {
        "type": "response.output_text.done",
        "sequence_number": sequence_number + 1,
        "item_id": "message-1",
        "output_index": message_index,
        "content_index": 0,
        "text": raw,
    }, {
        "type": "response.output_item.done",
        "sequence_number": sequence_number + 2,
        "output_index": message_index,
        "item": message_item,
    }, {
        "type": "response.completed",
        "sequence_number": sequence_number + 3,
        "response": {
            "id": response_id,
            "object": "response",
            "created_at": created_at,
            "completed_at": created_at + 1,
            "model": run["model_snapshot"],
            "metadata": metadata,
            "status": "completed",
            "error": None,
            "incomplete_details": None,
            "instructions": system_prompt,
            "output": output + [message_item],
            "reasoning": {"effort": run["reasoning_effort"]},
            "tools": tools,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        },
    }])
    return "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n"


def trace_output_fields(role: str, raw: str, run: dict, composed_sha256: str) -> dict:
    """Return synthetic records for unit-testing the persisted transport contract."""
    transcript = trace_transcript(role, raw, run, composed_sha256)
    return {
        "raw_response_contract": {
            "path": str(review_protocol.raw_response_contract_path(role)),
            "sha256": review_protocol.sha256_path(
                review_protocol.raw_response_contract_path(role)
            ),
        },
        "launcher_transcript_format": "responses_api_jsonl",
        "launcher_transcript": transcript,
        "launcher_transcript_sha256": review_protocol.sha256_text(transcript),
        "full_raw_response": raw,
        "full_raw_response_sha256": review_protocol.sha256_text(raw),
    }


def artifact(museum: str, source_id: str) -> dict:
    return {
        "id": f"{museum}:{source_id}",
        "source_museum": museum,
        "source_id": source_id,
    }


def mention(identifier: str, artifact_id: str, museum: str, text: str) -> dict:
    return {
        "mention_id": identifier,
        "artifact_id": artifact_id,
        "museum": museum,
        "entity_type": "site",
        "mention_text": text,
        "expression_type": "single_identity",
    }


def test_extractor_has_no_authority_dependency_or_resolver_parameter() -> None:
    source = (CONTROL / "extract_mentions.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    assert imported_roots <= {
        "__future__", "argparse", "gzip", "hashlib", "io", "json", "re",
        "tarfile", "unicodedata", "collections", "pathlib", "typing",
    }
    for forbidden in ("claim-graph.json", "reconciled.jsonl", "idai", "porter-moss", "keys_for_form"):
        assert forbidden not in source.casefold()
    assert tuple(inspect.signature(extractor.extract_mentions).parameters) == ("canonical", "raw_indexes")
    assert tuple(inspect.signature(extractor.candidate_after_royal_cue).parameters) == ("text", "cue")


def test_extractor_uses_exact_raw_spans_and_types_without_authority() -> None:
    met = artifact("met", "1")
    raw = {
        "reign": " Reign of Amenhotep III ",
        "title": "Plaque of King Amenemhat III wearing a crown",
        "country": "Egypt",
        "region": "Thebes; Deir el-Bahri (Temple of Hatshepsut)",
        "subregion": "",
        "locale": "TT 100",
        "locus": "",
        "geographyType": "From",
        "excavation": " MMA Expedition ",
    }
    rows, diagnostics = extractor.extract_mentions([met], {"met": {"1": raw}})
    assert diagnostics["records_scanned"] == 1
    assert diagnostics["records_with_at_least_one_mention"] == 1
    assert len(rows) == 8
    assert [(row["entity_type"], row["mention_text"]) for row in rows] == [
        ("excavation", "MMA Expedition"),
        ("ruler", "Amenhotep III"),
        ("ruler", "Amenemhat III"),
        ("site", "Egypt"),
        ("site", "Thebes"),
        ("site", "Deir el-Bahri"),
        ("temple", "Deir el-Bahri (Temple of Hatshepsut)"),
        ("tomb_monument", "TT 100"),
    ]
    # The full-component tomb row and explicit-code row would be duplicates, so only one
    # is legitimate. This assertion makes that invariant visible if extraction changes.
    tombs = [row for row in rows if row["entity_type"] == "tomb_monument"]
    assert len({(row["field_path"], row["span_start"], row["span_end"]) for row in tombs}) == 1
    for row in rows:
        assert row["mention_text"] == row["field_value"][row["span_start"]:row["span_end"]]


def test_cued_name_span_is_grammar_bounded_not_authority_bounded() -> None:
    text = "Relief of King Unknownname III wearing a crown"
    cue = next(extractor.ROYAL_CUE.finditer(text))
    candidate, start, end = extractor.candidate_after_royal_cue(text, cue)
    assert candidate == "Unknownname III"
    assert text[start:end] == "Unknownname III"


def test_location_component_split_does_not_cut_parenthetical_aliases() -> None:
    value = "Akhmim (Panopolis, ancient); Egypt"
    assert list(extractor.component_spans(value)) == [
        ("Akhmim (Panopolis, ancient)", 0, 27),
        ("Egypt", 29, 34),
    ]


def test_parenthetical_tomb_component_emits_one_code_mention() -> None:
    met = artifact("met", "tomb")
    raw = {
        "reign": "", "title": "", "country": "", "region": "", "subregion": "",
        "locale": "TT 100 (Tomb of Rekhmire)", "locus": "", "geographyType": "From",
        "excavation": "",
    }
    rows, _diagnostics = extractor.extract_mentions([met], {"met": {"tomb": raw}})
    tombs = [row for row in rows if row["entity_type"] == "tomb_monument"]
    assert [(row["mention_text"], row["span_start"], row["span_end"]) for row in tombs] == [
        ("TT 100", 0, 6)
    ]
    assert [(row["entity_type"], row["mention_text"]) for row in rows] == [
        ("site", "TT 100 (Tomb of Rekhmire)"),
        ("tomb_monument", "TT 100"),
    ]


@pytest.mark.parametrize(
    ("value", "expression", "candidate"),
    [
        ("Reign of Hatshepsut", "single_identity", "Hatshepsut"),
        ("Reigns of Hatshepsut and Thutmose III", "multi_or_range", None),
        ("Possibly the reign of Hatshepsut", "uncertain_identity", None),
        ("after death of Hatshepsut", "unparsed_structured_value", None),
    ],
)
def test_structured_reign_closed_expression_classes(value: str, expression: str, candidate: str | None) -> None:
    actual_expression, actual_candidate, span = extractor.classify_reign_expression(value)
    assert (actual_expression, actual_candidate) == (expression, candidate)
    if candidate is not None:
        assert span is not None and value[slice(*span)] == candidate


def test_literal_arm_is_typed_surface_equality_and_scopes_unavailable_types() -> None:
    rows = [
        mention("m1", "met:1", "met", "  ThEBES  "),
        mention("m2", "brooklyn:1", "brooklyn", "Thebes"),
        {**mention("m3", "met:2", "met", "Temple of X"), "entity_type": "temple"},
        {**mention("m4", "met:3", "met", "Field season"), "entity_type": "excavation"},
    ]
    resolved = comparison.resolve_mentions(rows, "typed_literal")
    assert resolved[0]["target_ids"] == resolved[1]["target_ids"]
    assert resolved[0]["resolution_method"] == "typed_nfc_whitespace_casefold_literal_equality"
    assert resolved[2]["status"] == "abstained"
    assert resolved[2]["reason"] == "authority_unavailable:temple"
    assert resolved[3]["status"] == "abstained"
    assert resolved[3]["reason"] == "authority_unavailable:excavation"


class StubResolver:
    def __init__(self, mapping: dict[str, str | None]):
        self.mapping = mapping

    def resolve(self, text: str, _norm) -> dict:
        target = self.mapping[text]
        return {
            "status": "resolved" if target else "unmatched",
            "target_ids": [target] if target else [],
            "resolution_method": "stub" if target else None,
            "raw_exact_status": "unique" if target else "unmatched",
        }


def test_pair_metrics_record_deltas_and_node_transitions_assert_values() -> None:
    rows = [
        mention("m1", "met:a", "met", "Thebes"),
        mention("m2", "brooklyn:a", "brooklyn", "Thebes"),
        mention("m3", "met:b", "met", "Waset"),
        mention("m4", "brooklyn:b", "brooklyn", "Ancient Thebes"),
        mention("m5", "met:c", "met", "Egypt"),
        mention("m6", "brooklyn:c", "brooklyn", "Egypt"),
    ]
    literal_rows = comparison.resolve_mentions(rows, "typed_literal")
    authority_rows = comparison.resolve_mentions(
        rows,
        "current_authority",
        {"site": (StubResolver({
            "Thebes": "authority:thebes",
            "Waset": "authority:waset",
            "Ancient Thebes": "authority:waset",
            "Egypt": None,
        }), lambda value: {value})},
    )
    literal_links = comparison.build_links(literal_rows)
    authority_links = comparison.build_links(authority_rows)
    counts = {"met": 3, "brooklyn": 3, "harvard": 1}
    literal_metrics, literal_state = comparison.arm_metrics(rows, literal_rows, literal_links, counts)
    authority_metrics, authority_state = comparison.arm_metrics(rows, authority_rows, authority_links, counts)

    assert literal_metrics["per_pair"]["met__brooklyn"]["shared_useful_node_count"] == 2
    assert authority_metrics["per_pair"]["met__brooklyn"]["shared_useful_node_count"] == 2
    assert literal_metrics["per_pair"]["met__brooklyn"]["records_by_museum_side"] == {"met": 2, "brooklyn": 2}
    assert authority_metrics["per_pair"]["met__brooklyn"]["records_by_museum_side"] == {"met": 2, "brooklyn": 2}
    assert literal_metrics["per_pair"]["met__brooklyn"]["concentration_by_museum_side"]["met"]["top_k"]["1"]["unique_record_union_ratio"] == {
        "numerator": 1, "denominator": 2, "value": 0.5,
    }

    deltas = comparison.record_deltas(literal_state, authority_state)
    assert deltas["per_pair"]["met__brooklyn"]["met"] == {
        "authority_gained_records": 1,
        "authority_lost_records": 1,
        "connected_in_both_arms": 1,
        "net_authority_record_change": 0,
    }
    transitions = comparison.node_transitions(
        literal_state, authority_state, literal_rows, authority_rows
    )["per_pair"]["met__brooklyn"]
    assert transitions["literal_shared_nodes_preserved_by_one_common_authority_target"] == 1
    assert transitions["literal_shared_nodes_lost_by_authority"] == 1
    assert transitions["authority_shared_nodes_with_one_common_surface_literal"] == 1
    assert transitions["authority_shared_nodes_created_only_by_cross_literal_authority_consolidation"] == 1


def test_ledger_transport_is_deterministic_and_binds_ordered_mentions(tmp_path: Path) -> None:
    row = {
        "mention_id": "mention-one", "artifact_id": "met:1", "museum": "met",
        "source_id": "1", "entity_type": "site", "field_path": "country",
        "field_value": "Egypt", "span_start": 0, "span_end": 5,
        "mention_text": "Egypt", "extraction_method": "structured_location_component",
        "evidence_role": "From:country", "expression_type": "single_identity",
    }
    first = extractor.write_ledger(tmp_path / "one.gz", [row])
    second = extractor.write_ledger(tmp_path / "two.gz", [row])
    assert first["gzip_sha256"] == second["gzip_sha256"]
    assert first["canonical_uncompressed_sha256"] == second["canonical_uncompressed_sha256"]
    assert first["ordered_mention_ids_sha256"] == second["ordered_mention_ids_sha256"]


def test_frozen_current_resolver_inputs_match_the_registered_base() -> None:
    comparison.verify_current_inputs(ROOT)


def test_current_arm_loads_and_uses_the_committed_resolver() -> None:
    _module, resolvers, catalogs = comparison.load_current_resolvers(ROOT)
    assert {entity: len(rows) for entity, rows in catalogs.items()} == {
        "ruler": 974,
        "site": 1000,
        "tomb_monument": 1357,
    }
    rows = [
        {**mention("ruler", "met:1", "met", "Amenhotep III"), "entity_type": "ruler"},
        mention("site", "met:2", "met", "Thebes"),
        {**mention("tomb", "met:3", "met", "TT 100"), "entity_type": "tomb_monument"},
    ]
    resolved = comparison.resolve_mentions(rows, "current_authority", resolvers)
    assert [(row["status"], row["target_ids"]) for row in resolved] == [
        ("ambiguous", ["leprohon-leprohon-18.09", "pharaoh_se-Amenhotep-III"]),
        ("resolved", ["idai:2042921"]),
        ("resolved", ["pm_theban:TT100"]),
    ]


def test_rerun_proof_rejects_one_changed_output(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    manifest = {
        "inputs": {"mention_ledger": {
            "gzip_sha256": "a" * 64,
            "ordered_mention_ids_sha256": "b" * 64,
        }}
    }
    for name in rerun.FILES:
        value = (json.dumps(manifest) if name == "run-manifest.json" else name).encode()
        (first / name).parent.mkdir(parents=True, exist_ok=True)
        (second / name).parent.mkdir(parents=True, exist_ok=True)
        (first / name).write_bytes(value)
        (second / name).write_bytes(value)
    assert rerun.verify(first, second)["all_registered_files_byte_identical"] is True
    (second / "report.json").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="report.json"):
        rerun.verify(first, second)


def test_stage_1_blinding_check_is_derived_and_detects_hidden_fields() -> None:
    def group(name: str) -> dict:
        return {
            "evidence_group": name,
            "representative_exact_mention": "Place",
            "exact_mention_variants": {"Place": 1},
            "mention_count": 1,
            "distinct_record_count": 1,
            "field_paths": ["place"],
            "evidence_roles": ["from"],
        }

    evidence = {
        "museum_pair": ["met", "brooklyn"],
        "entity_type": "site",
        "sides": {
            "met": [group("side-1-evidence")],
            "brooklyn": [group("side-2-evidence")],
        },
    }
    stage_1 = {
        "cases": [{
            "case_id": "case-001",
            "evidence_sha256": review_queue.canonical_sha256(evidence),
            **evidence,
        }],
    }
    answer_key = {
        "cases": [{
            "proposed_target_id": "idai:hidden",
            "arm_native": {
                "literal": {"nodes": []},
                "authority": {"nodes": [{
                    "target_id": "idai:hidden",
                    "mention_ids_by_side": {
                        "met": ["mention-hidden-a"], "brooklyn": ["mention-hidden-b"],
                    },
                    "artifact_ids_by_side": {
                        "met": ["met:hidden"], "brooklyn": ["brooklyn:hidden"],
                    },
                }]},
            },
        }],
    }
    assert review_queue.stage_1_blinding_check(stage_1, answer_key)["passed"] is True
    leaked = copy.deepcopy(stage_1)
    leaked["cases"][0]["proposed_target_id"] = "idai:hidden"
    check = review_queue.stage_1_blinding_check(leaked, answer_key)
    assert check["passed"] is False
    assert check["forbidden_key_occurrences"] == 1
    assert check["private_identifier_occurrences"] == 1


def test_surface_group_order_cannot_depend_on_hidden_literal_target_ids() -> None:
    mentions = {
        "m1": {
            "mention_text": "Alpha", "artifact_id": "met:1", "field_path": "place",
            "evidence_role": "from",
        },
        "m2": {
            "mention_text": "Beta", "artifact_id": "met:2", "field_path": "place",
            "evidence_role": "from",
        },
    }
    first = {
        "m1": {"status": "resolved", "target_ids": ["literal:z-hidden"]},
        "m2": {"status": "resolved", "target_ids": ["literal:a-hidden"]},
    }
    renamed = {
        "m1": {"status": "resolved", "target_ids": ["literal:a-hidden"]},
        "m2": {"status": "resolved", "target_ids": ["literal:z-hidden"]},
    }
    assert review_queue.surface_groups(["m1", "m2"], mentions, first, 1) == (
        review_queue.surface_groups(["m1", "m2"], mentions, renamed, 1)
    )


def test_traceable_review_protocol_rejects_prompt_leaks_and_uncited_ties(tmp_path: Path) -> None:
    prompt_root = CONTROL.parent / "prompts"
    auditor_prompt = prompt_root / "prompt-auditor-v2.txt"
    reviewer_prompt = prompt_root / "stage-1-reviewer-v2.txt"
    reconciler_prompt = prompt_root / "stage-1-reconciler-v2.txt"
    assert review_protocol.audit_prompt_bytes(reviewer_prompt) == {
        "prompt_sha256": review_protocol.sha256_path(reviewer_prompt),
        "forbidden_snippets": [],
        "passed": True,
    }
    for prompt in sorted(prompt_root.glob("*.txt")):
        assert review_protocol.audit_prompt_bytes(prompt)["passed"], prompt.name
        assert "include the full unedited model response" not in prompt.read_text()
    for prompt in sorted(prompt_root.glob("*-v2.txt")):
        text = prompt.read_text().replace("finite-census", "finite census")
        assert "finite census" in text
        assert "not statistically independent" in text or "not a statistically independent" in text
    leaky_prompt = tmp_path / "leaky.txt"
    leaky_prompt.write_text(reviewer_prompt.read_text() + "\nidai:123\n", encoding="utf-8")
    assert review_protocol.audit_prompt_bytes(leaky_prompt)["passed"] is False

    evidence = {
        "museum_pair": ["met", "brooklyn"],
        "entity_type": "site",
        "sides": {
            "met": [{
                "evidence_group": "side-1-group-01",
                "representative_exact_mention": "Place A",
                "exact_mention_variants": {"Place A": 1},
                "mention_count": 1,
                "distinct_record_count": 1,
                "field_paths": ["place"],
                "evidence_roles": ["from"],
            }],
            "brooklyn": [{
                "evidence_group": "side-2-group-01",
                "representative_exact_mention": "Place B",
                "exact_mention_variants": {"Place B": 1},
                "mention_count": 1,
                "distinct_record_count": 1,
                "field_paths": ["place"],
                "evidence_roles": ["from"],
            }],
        },
    }
    evidence_sha = review_protocol.canonical_sha256(evidence)
    queue = {
        "review_protocol": {
            "role": "stage_1_reviewer",
            "prompt_sha256": review_protocol.sha256_path(reviewer_prompt),
            "raw_response_contract_sha256": review_protocol.sha256_path(
                review_protocol.raw_response_contract_path("stage_1_reviewer")
            ),
        },
        "cases": [{"case_id": "case-001", "evidence_sha256": evidence_sha, **evidence}],
    }
    queue_path = tmp_path / "stage-1-queue.json"
    review_queue.write_json(queue_path, queue)
    assert set(review_protocol.validate_queue(queue_path, "1", reviewer_prompt)) == {"case-001"}
    proxy_queue = copy.deepcopy(queue)
    proxy_queue["cases"][0]["sides"]["brooklyn"][0]["evidence_group"] = "side-1-group-01"
    proxy_evidence = {
        key: proxy_queue["cases"][0][key] for key in ("museum_pair", "entity_type", "sides")
    }
    proxy_queue["cases"][0]["evidence_sha256"] = review_protocol.canonical_sha256(proxy_evidence)
    proxy_path = tmp_path / "proxy-queue.json"
    review_queue.write_json(proxy_path, proxy_queue)
    with pytest.raises(ValueError, match="proxy leak"):
        review_protocol.validate_queue(proxy_path, "1", reviewer_prompt)
    cardinality_proxy = copy.deepcopy(queue)
    cardinality_proxy["cases"][0]["sides"]["met"].append(copy.deepcopy(
        cardinality_proxy["cases"][0]["sides"]["met"][0]
    ))
    cardinality_proxy["cases"][0]["sides"]["met"][1]["evidence_group"] = (
        "side-1-group-02"
    )
    cardinality_evidence = {
        key: cardinality_proxy["cases"][0][key]
        for key in ("museum_pair", "entity_type", "sides")
    }
    cardinality_proxy["cases"][0]["evidence_sha256"] = (
        review_protocol.canonical_sha256(cardinality_evidence)
    )
    cardinality_path = tmp_path / "cardinality-proxy-queue.json"
    review_queue.write_json(cardinality_path, cardinality_proxy)
    with pytest.raises(ValueError, match="cardinality proxy"):
        review_protocol.validate_queue(cardinality_path, "1", reviewer_prompt)

    def model_run(request_id: str, role: str = "stage_1_reviewer") -> dict:
        return trace_run(tmp_path, request_id, role)

    mutable_evidence = tmp_path / "mutable-provider-snapshot.json"
    review_queue.write_json(mutable_evidence, {
        "schema_version": "hapi-provider-model-snapshot-evidence/1",
        "provider": "openai",
        "requested_model_id": "mutable-model",
        "resolved_snapshot_id": "mutable-model",
        "source_url": "https://api.openai.com/v1/models/mutable-model",
        "retrieved_at": "2026-09-14T00:00:00Z",
        "raw_provider_response": {
            "id": "mutable-model", "object": "model", "created": 1,
            "owned_by": "openai",
        },
    })
    with pytest.raises(ValueError, match="distinct dated provider snapshot"):
        review_protocol.validate_provider_snapshot_evidence(
            {
                "path": str(mutable_evidence),
                "sha256": review_protocol.sha256_path(mutable_evidence),
            },
            "mutable-model", "mutable-model", "openai_responses_api_jsonl",
            "test run",
        )

    fake_provider = tmp_path / "fake-provider-snapshot.json"
    review_queue.write_json(fake_provider, {
        "schema_version": "hapi-provider-model-snapshot-evidence/1",
        "provider": "unrelated-provider",
        "requested_model_id": "claimed-model",
        "resolved_snapshot_id": "claimed-model-2026-09-14",
        "source_url": "https://provider.example/self-assertion",
        "retrieved_at": "2026-09-14T00:00:00Z",
        "raw_provider_response": {"anything": "claimed-model-2026-09-14"},
    })
    with pytest.raises(ValueError, match="does not match the launcher transport"):
        review_protocol.validate_provider_snapshot_evidence(
            {"path": str(fake_provider), "sha256": review_protocol.sha256_path(fake_provider)},
            "claimed-model", "claimed-model-2026-09-14",
            "openai_responses_api_jsonl", "fake provider",
        )

    sol_evidence = tmp_path / "sol-provider-snapshot.json"
    review_queue.write_json(sol_evidence, {
        "schema_version": "hapi-provider-model-snapshot-evidence/1",
        "provider": "openai",
        "requested_model_id": "gpt-5.6-sol",
        "resolved_snapshot_id": "gpt-5.6-sol-2026-09-14",
        "source_url": "https://api.openai.com/v1/models/gpt-5.6-sol-2026-09-14",
        "retrieved_at": "2026-09-14T00:00:00Z",
        "raw_provider_response": {
            "id": "gpt-5.6-sol-2026-09-14", "object": "model", "created": 1,
            "owned_by": "openai",
        },
    })
    with pytest.raises(ValueError, match="no provider-pinned immutable snapshot"):
        review_protocol.validate_provider_snapshot_evidence(
            {"path": str(sol_evidence), "sha256": review_protocol.sha256_path(sol_evidence)},
            "gpt-5.6-sol", "gpt-5.6-sol-2026-09-14",
            "openai_responses_api_jsonl", "Sol run",
        )

    codex_run = model_run("unsupported-codex")
    codex_run["launcher_transport"] = "codex_cli_jsonl_with_base_instructions"
    with pytest.raises(ValueError, match="launcher_transport is unsupported"):
        review_protocol.validate_model_run(
            codex_run, "unsupported Codex run", "stage_1_reviewer"
        )
    assert "codex_jsonl" not in review_protocol.TRANSCRIPT_FORMAT_BY_TRANSPORT.values()
    artifact_schema = json.loads(
        (CONTROL.parent / "review-artifact.schema.json").read_text(encoding="utf-8")
    )
    assert "codex_cli_jsonl_with_base_instructions" not in json.dumps(artifact_schema)

    with pytest.raises(ValueError, match="only HTTPS URLs"):
        review_protocol.validate_citations(
            {"citations": ["https://"], "artifact_exceptions": []},
            "empty-host citation",
        )
    with pytest.raises(ValueError, match="invalid source"):
        review_protocol._https_sources(
            [{"url": "https://"}], "empty-host web source"
        )
    assert review_protocol.is_valid_https_url("https://www.metmuseum.org/") is True

    claude_run = model_run("claude-missing-bare", "prompt_auditor")
    claude_snapshot = "claude-test-2026-09-14"
    claude_evidence = tmp_path / "claude-provider-snapshot.json"
    review_queue.write_json(claude_evidence, {
        "schema_version": "hapi-provider-model-snapshot-evidence/1",
        "provider": "anthropic",
        "requested_model_id": "claude-test",
        "resolved_snapshot_id": claude_snapshot,
        "source_url": f"https://api.anthropic.com/v1/models/{claude_snapshot}",
        "retrieved_at": "2026-09-14T00:00:00Z",
        "raw_provider_response": {
            "id": claude_snapshot, "type": "model",
            "created_at": "2026-09-14T00:00:00Z", "display_name": "Claude test",
        },
    })
    system_prompt = review_protocol.launcher_system_prompt_path("prompt_auditor").read_text()
    claude_parameters = {"thinking": {"type": "enabled", "budget_tokens": 4000}}
    claude_envelope = json.dumps({
        "agent_profile": None,
        "credential_mode": "anthropic_api_key",
        "input_delivery": "stdin_exact_composed_input_bytes",
        "invocation": (
            "claude -p --verbose --output-format stream-json "
            f"--model {claude_snapshot} --system-prompt {shlex.quote(system_prompt)} --tools ''"
        ),
        "model_snapshot": claude_snapshot,
        "parameters": claude_parameters,
        "schema_version": "hapi-authority-control-launcher-envelope/2",
        "system_prompt_sha256": review_protocol.sha256_text(system_prompt),
        "transcript_format": "claude_stream_json",
        "transport": "anthropic_cli_bare_stream_json",
    }, sort_keys=True, separators=(",", ":"))
    claude_run.update({
        "model_id": "claude-test",
        "model_snapshot": claude_snapshot,
        "launcher_transport": "anthropic_cli_bare_stream_json",
        "parameters": claude_parameters,
        "provider_snapshot_evidence": {
            "path": str(claude_evidence),
            "sha256": review_protocol.sha256_path(claude_evidence),
        },
        "launcher_envelope": claude_envelope,
        "launcher_envelope_sha256": review_protocol.sha256_text(claude_envelope),
    })
    disabled_thinking_run = copy.deepcopy(claude_run)
    disabled_thinking_run["parameters"] = {"thinking": {"type": "disabled"}}
    disabled_thinking_run["launcher_envelope"] = json.dumps(
        {**json.loads(claude_envelope), "parameters": disabled_thinking_run["parameters"]},
        sort_keys=True, separators=(",", ":"),
    )
    disabled_thinking_run["launcher_envelope_sha256"] = review_protocol.sha256_text(
        disabled_thinking_run["launcher_envelope"]
    )
    with pytest.raises(ValueError, match="must enable extended thinking"):
        review_protocol.validate_model_run(disabled_thinking_run, "Claude run", "prompt_auditor")

    openai_no_summary_run = model_run("openai-no-summary")
    openai_no_summary_run["parameters"] = {"temperature": 0}
    openai_no_summary_run["launcher_envelope"] = json.dumps(
        {**json.loads(openai_no_summary_run["launcher_envelope"]), "parameters": {"temperature": 0}},
        sort_keys=True, separators=(",", ":"),
    )
    openai_no_summary_run["launcher_envelope_sha256"] = review_protocol.sha256_text(
        openai_no_summary_run["launcher_envelope"]
    )
    with pytest.raises(ValueError, match="captured reasoning summary"):
        review_protocol.validate_model_run(openai_no_summary_run, "OpenAI run", "stage_1_reviewer")

    with pytest.raises(ValueError, match="exact bare stream-json"):
        review_protocol.validate_model_run(claude_run, "Claude run", "prompt_auditor")
    valid_claude_envelope = json.loads(claude_envelope)
    valid_claude_envelope["invocation"] = (
        "claude --bare --print --verbose --output-format stream-json "
        f"--model {claude_snapshot} --system-prompt {shlex.quote(system_prompt)} --tools ''"
    )
    claude_run["launcher_envelope"] = json.dumps(
        valid_claude_envelope, sort_keys=True, separators=(",", ":")
    )
    claude_run["launcher_envelope_sha256"] = review_protocol.sha256_text(
        claude_run["launcher_envelope"]
    )
    review_protocol.validate_model_run(claude_run, "Claude run", "prompt_auditor")
    claude_raw = json.dumps({"outcome": "PASS", "findings": []}, sort_keys=True)
    claude_input_sha = "a" * 64
    claude_capture = {
        "type": "hapi.transport.request",
        "transport": claude_run["launcher_transport"],
        "request_id": claude_run["request_id"],
        "transport_session_id": claude_run["transport_session_id"],
        "run_date": claude_run["run_date"],
        "model_id": claude_run["model_id"],
        "model_snapshot": claude_run["model_snapshot"],
        "reasoning_effort": claude_run["reasoning_effort"],
        "parameters": claude_run["parameters"],
        "input_sha256": claude_input_sha,
        "system_prompt": system_prompt,
        "system_prompt_sha256": review_protocol.sha256_text(system_prompt),
    }
    claude_events = [
        claude_capture,
        {
            "type": "system", "subtype": "init",
            "session_id": claude_run["transport_session_id"],
            "model": claude_snapshot,
        },
        {
            "type": "assistant",
            "session_id": claude_run["transport_session_id"],
            "message": {
                "type": "message",
                "role": "assistant",
                "model": claude_snapshot,
                "content": [
                    {
                        "type": "thinking",
                        "thinking": "Weighing the museum evidence against the citation rule.",
                        "signature": "sig-test",
                    },
                    {"type": "text", "text": claude_raw},
                ],
                "stop_reason": "end_turn",
            },
        },
        {
            "type": "result", "subtype": "success", "is_error": False,
            "session_id": claude_run["transport_session_id"],
            "modelUsage": {
                claude_snapshot: {"inputTokens": 1, "outputTokens": 1},
            },
            "num_turns": 1,
            "result": claude_raw,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        },
    ]
    claude_transcript = "\n".join(
        json.dumps(event, sort_keys=True) for event in claude_events
    ) + "\n"
    review_protocol.validate_launcher_transcript(
        "claude_stream_json", claude_transcript, claude_raw, claude_run,
        "prompt_auditor", claude_input_sha, "synthetic Claude contract trace",
    )
    no_thinking_events = copy.deepcopy(claude_events)
    no_thinking_events[2]["message"]["content"] = [
        block for block in no_thinking_events[2]["message"]["content"]
        if block["type"] != "thinking"
    ]
    no_thinking_transcript = "\n".join(
        json.dumps(event, sort_keys=True) for event in no_thinking_events
    ) + "\n"
    with pytest.raises(ValueError, match="lacks captured extended-thinking content"):
        review_protocol.validate_launcher_transcript(
            "claude_stream_json", no_thinking_transcript, claude_raw, claude_run,
            "prompt_auditor", claude_input_sha, "thinking-stripped Claude contract trace",
        )
    skeletal_claude_events = [claude_events[0], claude_events[1], claude_events[-1]]
    skeletal_claude_transcript = "\n".join(
        json.dumps(event, sort_keys=True) for event in skeletal_claude_events
    ) + "\n"
    with pytest.raises(ValueError, match="turn count does not bind assistant events"):
        review_protocol.validate_launcher_transcript(
            "claude_stream_json", skeletal_claude_transcript, claude_raw, claude_run,
            "prompt_auditor", claude_input_sha, "skeletal Claude contract trace",
        )
    bad_system_events = copy.deepcopy(claude_events)
    bad_system_events[0]["system_prompt"] += " hidden"
    bad_system_transcript = "\n".join(
        json.dumps(event, sort_keys=True) for event in bad_system_events
    ) + "\n"
    with pytest.raises(ValueError, match="exact model run and input"):
        review_protocol.validate_launcher_transcript(
            "claude_stream_json", bad_system_transcript, claude_raw, claude_run,
            "prompt_auditor", claude_input_sha, "synthetic Claude contract trace",
        )

    def write_prompt_audit(
        path: Path, subject_input: Path, subject_role: str, request_id: str
    ) -> None:
        raw = json.dumps({"outcome": "PASS", "findings": []}, sort_keys=True)
        run = model_run(request_id, "prompt_auditor")
        composed_sha = review_protocol.composed_input_sha256(
            "prompt_auditor", run["launcher_envelope"], [
                ("launcher_system_prompt", review_protocol.launcher_system_prompt_path("prompt_auditor")),
                ("auditor_prompt", auditor_prompt),
                ("raw_response_contract", review_protocol.raw_response_contract_path("prompt_auditor")),
                ("subject_composed_input", subject_input),
            ]
        )
        review_queue.write_json(path, {
            "schema_version": review_protocol.PROMPT_AUDIT_SCHEMA_VERSION,
            "auditor_run": run,
            "auditor_prompt": {
                "path": str(auditor_prompt),
                "sha256": review_protocol.sha256_path(auditor_prompt),
            },
            "subject_role": subject_role,
            "subject_composed_input": {
                "path": str(subject_input),
                "sha256": review_protocol.sha256_path(subject_input),
            },
            "composed_input_sha256": composed_sha,
            **trace_output_fields("prompt_auditor", raw, run, composed_sha),
            "outcome": "PASS",
            "findings": [],
        })

    reviewer_audit = tmp_path / "reviewer-prompt-audit.json"
    reconciler_audit = tmp_path / "reconciler-prompt-audit.json"
    reviewer_subject_input = tmp_path / "reviewer-subject-input.json"
    reviewer_subject_input.write_bytes(review_protocol.composed_input_bytes(
        "stage_1_reviewer", model_run("subject-reviewer")["launcher_envelope"],
        trace_components("stage_1_reviewer", reviewer_prompt, queue_path),
    ))
    subject_components = {
        component["label"]: component
        for component in json.loads(reviewer_subject_input.read_text())["components"]
    }
    assert subject_components["raw_response_contract"]["utf8"] == (
        review_protocol.raw_response_contract_path("stage_1_reviewer").read_text()
    )
    assert subject_components["launcher_system_prompt"]["utf8"] == (
        review_protocol.launcher_system_prompt_path("stage_1_reviewer").read_text()
    )
    write_prompt_audit(
        reviewer_audit, reviewer_subject_input, "stage_1_reviewer", "audit-reviewer"
    )
    original_queue_bytes = queue_path.read_bytes()
    queue_path.write_bytes(original_queue_bytes + b" ")
    with pytest.raises(ValueError, match="component SHA-256 mismatch"):
        review_protocol.validate_prompt_audit(
            reviewer_audit, auditor_prompt, reviewer_subject_input, "stage_1_reviewer"
        )
    queue_path.write_bytes(original_queue_bytes)

    def write_review(path: Path, useful: str, request_id: str) -> dict:
        decisions = [{
            "case_id": "case-001",
            "evidence_sha256": evidence_sha,
            "same_entity": "same_entity",
            "useful_granularity": useful,
            "reasoning": "The evidence supports this judgment.",
            "citations": ["https://www.metmuseum.org/"],
            "artifact_exceptions": [],
        }]
        raw = json.dumps({"decisions": decisions}, sort_keys=True)
        run = model_run(request_id)
        composed_sha = review_protocol.composed_input_sha256(
            "stage_1_reviewer", run["launcher_envelope"],
            trace_components("stage_1_reviewer", reviewer_prompt, queue_path),
        )
        package = {
            "schema_version": review_protocol.REVIEW_SCHEMA_VERSION,
            "role": "stage_1_reviewer",
            "run": run,
            "prompt": {"path": str(reviewer_prompt), "sha256": review_protocol.sha256_path(reviewer_prompt)},
            "queue": {"path": str(queue_path), "sha256": review_protocol.sha256_path(queue_path)},
            "prompt_audit": {"path": str(reviewer_audit), "sha256": review_protocol.sha256_path(reviewer_audit)},
            "composed_input_sha256": composed_sha,
            **trace_output_fields("stage_1_reviewer", raw, run, composed_sha),
            "decisions": decisions,
        }
        review_queue.write_json(path, package)
        return package

    review_a_path = tmp_path / "review-a.json"
    review_b_path = tmp_path / "review-b.json"
    review_a = write_review(review_a_path, "useful", "review-a")
    review_b = write_review(review_b_path, "too_broad", "review-b")
    assert review_protocol.validate_review_package(
        review_a_path, queue_path, reviewer_prompt, reviewer_audit, auditor_prompt, "1"
    ) == review_a
    no_reasoning_events = list(map(json.loads, review_a["launcher_transcript"].splitlines()))
    for event in no_reasoning_events:
        item = event.get("item")
        if isinstance(item, dict) and item.get("id") == "reasoning-1":
            item["summary"] = []
    for item in no_reasoning_events[-1]["response"]["output"]:
        if item.get("id") == "reasoning-1":
            item["summary"] = []
    no_reasoning_transcript = "\n".join(
        json.dumps(event, sort_keys=True) for event in no_reasoning_events
    ) + "\n"
    with pytest.raises(ValueError, match="captured reasoning summary content"):
        review_protocol.validate_launcher_transcript(
            "responses_api_jsonl", no_reasoning_transcript, review_a["full_raw_response"],
            review_a["run"], "stage_1_reviewer", review_a["composed_input_sha256"],
            "reasoning-stripped transcript", require_web=True,
        )
    fabricated = "\n".join(json.dumps(event) for event in (
        {
            "type": "rollout.started", "base_instructions": system_prompt,
            "request_id": "wrong-request", "model": "wrong-model",
        },
        {"type": "note", "text": "web_search"},
        {
            "type": "rollout.completed", "usage": {},
            "final_agent_message": review_a["full_raw_response"],
            "request_id": "also-wrong",
        },
    )) + "\n"
    with pytest.raises(ValueError, match="request capture"):
        review_protocol.validate_launcher_transcript(
            "responses_api_jsonl", fabricated, review_a["full_raw_response"],
            review_a["run"], "stage_1_reviewer", review_a["composed_input_sha256"],
            "fabricated transcript", require_web=True,
        )
    substring_only_events = list(
        map(json.loads, review_a["launcher_transcript"].splitlines())
    )
    for event in substring_only_events:
        item = event.get("item")
        if isinstance(item, dict) and item.get("id") == "web-1":
            item["type"] = "reasoning"
            item["note"] = "web_search"
    substring_only_events[-1]["response"]["output"][0]["type"] = "reasoning"
    substring_only_events[-1]["response"]["output"][0]["note"] = "web_search"
    substring_only = "\n".join(
        json.dumps(event, sort_keys=True) for event in substring_only_events
    ) + "\n"
    with pytest.raises(ValueError, match="paired Responses web-search"):
        review_protocol.validate_launcher_transcript(
            "responses_api_jsonl", substring_only, review_a["full_raw_response"],
            review_a["run"], "stage_1_reviewer", review_a["composed_input_sha256"],
            "substring-only transcript", require_web=True,
        )
    empty_usage_events = list(
        map(json.loads, review_a["launcher_transcript"].splitlines())
    )
    empty_usage_events[-1]["response"]["usage"] = {}
    empty_usage = "\n".join(
        json.dumps(event, sort_keys=True) for event in empty_usage_events
    ) + "\n"
    with pytest.raises(ValueError, match="usage must be a nonempty object"):
        review_protocol.validate_launcher_transcript(
            "responses_api_jsonl", empty_usage, review_a["full_raw_response"],
            review_a["run"], "stage_1_reviewer", review_a["composed_input_sha256"],
            "empty-usage transcript", require_web=True,
        )
    inconsistent = copy.deepcopy(review_a)
    inconsistent["decisions"][0]["same_entity"] = "different_entity"
    inconsistent_raw = json.dumps({"decisions": inconsistent["decisions"]}, sort_keys=True)
    inconsistent.update(trace_output_fields(
        "stage_1_reviewer", inconsistent_raw, inconsistent["run"],
        inconsistent["composed_input_sha256"],
    ))
    inconsistent_path = tmp_path / "inconsistent-review.json"
    review_queue.write_json(inconsistent_path, inconsistent)
    with pytest.raises(ValueError, match="cannot call a different-entity connection useful"):
        review_protocol.validate_review_package(
            inconsistent_path, queue_path, reviewer_prompt, reviewer_audit,
            auditor_prompt, "1",
        )
    contract_violation = json.loads(review_a["full_raw_response"])
    del contract_violation["decisions"][0]["reasoning"]
    with pytest.raises(ValueError, match="raw-response contract fields"):
        review_protocol.validate_raw_response("stage_1_reviewer", contract_violation)
    tampered_transcript = copy.deepcopy(review_a)
    tampered_transcript["launcher_transcript"] += " "
    tampered_transcript_path = tmp_path / "tampered-transcript.json"
    review_queue.write_json(tampered_transcript_path, tampered_transcript)
    with pytest.raises(ValueError, match="transcript hash mismatch"):
        review_protocol.validate_review_package(
            tampered_transcript_path, queue_path, reviewer_prompt, reviewer_audit,
            auditor_prompt, "1"
        )
    truncated_transcript = copy.deepcopy(review_a)
    truncated_transcript["launcher_transcript"] = "\n".join(
        truncated_transcript["launcher_transcript"].splitlines()[:-1]
    ) + "\n"
    truncated_transcript["launcher_transcript_sha256"] = review_protocol.sha256_text(
        truncated_transcript["launcher_transcript"]
    )
    truncated_transcript_path = tmp_path / "truncated-transcript.json"
    review_queue.write_json(truncated_transcript_path, truncated_transcript)
    with pytest.raises(ValueError, match="truncated"):
        review_protocol.validate_review_package(
            truncated_transcript_path, queue_path, reviewer_prompt, reviewer_audit,
            auditor_prompt, "1"
        )
    missing_trace = copy.deepcopy(review_a)
    del missing_trace["run"]["model_snapshot"]
    missing_trace_path = tmp_path / "missing-trace.json"
    review_queue.write_json(missing_trace_path, missing_trace)
    with pytest.raises(ValueError, match="fields differ"):
        review_protocol.validate_review_package(
            missing_trace_path, queue_path, reviewer_prompt, reviewer_audit,
            auditor_prompt, "1"
        )

    hashes_and_maps = sorted([
        (review_protocol.sha256_path(review_a_path), review_a),
        (review_protocol.sha256_path(review_b_path), review_b),
    ])
    source_outcomes = lambda field: [
        {"review_sha256": digest, "outcome": package["decisions"][0][field]}
        for digest, package in hashes_and_maps
    ]
    consensus_decision = {
        "case_id": "case-001",
        "evidence_sha256": evidence_sha,
        "same_entity": "same_entity",
        "useful_granularity": "useful",
        "field_resolutions": {
            "same_entity": {
                "method": "agreement",
                "source_outcomes": source_outcomes("same_entity"),
                "rationale": "Both reviewers agree.",
                "citations": [],
            },
            "useful_granularity": {
                "method": "agreement",
                "source_outcomes": source_outcomes("useful_granularity"),
                "rationale": "Invalid silent tie selection.",
                "citations": [],
            },
        },
        "reasoning": "The two fields were reconciled independently.",
        "citations": ["https://www.metmuseum.org/"],
        "artifact_exceptions": [],
    }

    ordered_review_paths = sorted(
        (review_a_path, review_b_path), key=review_protocol.sha256_path
    )
    reconciler_subject_input = tmp_path / "reconciler-subject-input.json"
    reconciler_subject_input.write_bytes(review_protocol.composed_input_bytes(
        "stage_1_reconciler",
        model_run("subject-reconciler", "stage_1_reconciler")["launcher_envelope"],
        trace_components(
            "stage_1_reconciler", reconciler_prompt, queue_path,
            list(ordered_review_paths),
        ),
    ))
    write_prompt_audit(
        reconciler_audit, reconciler_subject_input, "stage_1_reconciler",
        "audit-reconciler",
    )
    original_review_bytes = review_a_path.read_bytes()
    review_a_path.write_bytes(original_review_bytes + b" ")
    with pytest.raises(ValueError, match="component SHA-256 mismatch"):
        review_protocol.validate_prompt_audit(
            reconciler_audit, auditor_prompt, reconciler_subject_input,
            "stage_1_reconciler",
        )
    review_a_path.write_bytes(original_review_bytes)

    def write_consensus(path: Path) -> None:
        decisions = [consensus_decision]
        raw = json.dumps({"decisions": decisions}, sort_keys=True)
        run = model_run("consensus", "stage_1_reconciler")
        ordered_reviews = sorted(
            (review_a_path, review_b_path), key=review_protocol.sha256_path
        )
        composed_sha = review_protocol.composed_input_sha256(
            "stage_1_reconciler", run["launcher_envelope"],
            trace_components(
                "stage_1_reconciler", reconciler_prompt, queue_path,
                list(ordered_reviews),
            ),
        )
        review_queue.write_json(path, {
            "schema_version": review_protocol.CONSENSUS_SCHEMA_VERSION,
            "role": "stage_1_reconciler",
            "run": run,
            "prompt": {"path": str(reconciler_prompt), "sha256": review_protocol.sha256_path(reconciler_prompt)},
            "queue": {"path": str(queue_path), "sha256": review_protocol.sha256_path(queue_path)},
            "prompt_audit": {"path": str(reconciler_audit), "sha256": review_protocol.sha256_path(reconciler_audit)},
            "source_reviews": [
                {"path": str(path), "sha256": review_protocol.sha256_path(path)}
                for path in ordered_reviews
            ],
            "composed_input_sha256": composed_sha,
            **trace_output_fields("stage_1_reconciler", raw, run, composed_sha),
            "decisions": decisions,
        })

    consensus_path = tmp_path / "consensus.json"
    write_consensus(consensus_path)
    duplicate_review_path = tmp_path / "review-a-copy.json"
    duplicate_review_path.write_bytes(review_a_path.read_bytes())
    with pytest.raises(ValueError, match="independent artifacts"):
        review_protocol.validate_consensus_package(
            consensus_path, queue_path, reviewer_prompt, reviewer_audit,
            [review_a_path, duplicate_review_path], reconciler_prompt,
            reconciler_audit, auditor_prompt, "1",
        )
    with pytest.raises(ValueError, match="explicit cited override"):
        review_protocol.validate_consensus_package(
            consensus_path, queue_path, reviewer_prompt, reviewer_audit,
            [review_a_path, review_b_path], reconciler_prompt, reconciler_audit,
            auditor_prompt, "1",
        )
    consensus_decision["field_resolutions"]["useful_granularity"].update({
        "method": "explicit_cited_override",
        "rationale": "Independent institutional evidence supports useful granularity.",
        "citations": ["https://www.metmuseum.org/"],
    })
    write_consensus(consensus_path)
    assert review_protocol.validate_consensus_package(
        consensus_path, queue_path, reviewer_prompt, reviewer_audit,
        [review_a_path, review_b_path], reconciler_prompt, reconciler_audit,
        auditor_prompt, "1",
    )["decisions"] == [consensus_decision]


def test_wrapper_validates_before_atomic_no_clobber(tmp_path: Path) -> None:
    sentinel = tmp_path / "review.json"
    sentinel_bytes = b"sacred pre-existing artifact\n"
    sentinel.write_bytes(sentinel_bytes)

    def reject(candidate: Path) -> None:
        assert candidate != sentinel
        assert json.loads(candidate.read_text(encoding="utf-8")) == {"invalid": True}
        raise ValueError("invalid wrapped artifact")

    with pytest.raises(ValueError, match="invalid wrapped artifact"):
        review_wrapper.publish_validated(sentinel, {"invalid": True}, reject)
    assert sentinel.read_bytes() == sentinel_bytes

    absent = tmp_path / "absent.json"
    with pytest.raises(ValueError, match="invalid wrapped artifact"):
        review_wrapper.publish_validated(absent, {"invalid": True}, reject)
    assert not absent.exists()

    published = tmp_path / "published.json"
    review_wrapper.publish_validated(
        published,
        {"valid": True},
        lambda candidate: json.loads(candidate.read_text(encoding="utf-8")),
    )
    published_bytes = published.read_bytes()
    with pytest.raises(FileExistsError, match="refusing to replace"):
        review_wrapper.publish_validated(
            published,
            {"valid": False},
            lambda candidate: json.loads(candidate.read_text(encoding="utf-8")),
        )
    assert published.read_bytes() == published_bytes
    assert list(tmp_path.glob(".*.tmp")) == []


def test_arm_native_accounting_preserves_multiple_literals_and_case_025_shape() -> None:
    def node(
        target: str, met: list[str], brooklyn: list[str],
        same_entity: str = "same_entity", useful: str = "useful",
    ) -> dict:
        return {
            "target_id": target,
            "mention_ids_by_side": {
                "met": [f"mention-{value}" for value in met],
                "brooklyn": [f"mention-{value}" for value in brooklyn],
            },
            "artifact_ids_by_side": {"met": met, "brooklyn": brooklyn},
            "stage_1_review_unit_id": f"review-{target}",
            "stage_1_evidence_sha256": review_protocol.sha256_text(target),
            "stage_1": {
                "same_entity": same_entity,
                "useful_granularity": useful,
            },
        }

    case_025 = {
        "case_id": "case-025",
        "transition_class": "retained_control",
        "museum_pair": ["met", "brooklyn"],
        "entity_type": "site",
        "arm_native": {
            "literal": {"nodes": [node("literal:shared", [f"met-{i}" for i in range(19)], ["brooklyn-1"])]},
            "authority": {"nodes": [node(
                "authority:shared", [f"met-{i}" for i in range(19)],
                [f"brooklyn-{i}" for i in range(1, 5)],
            )]},
        },
        "proposed_target_id": "authority:shared",
        "stage_2": {"canonical_identity": "exact_identity"},
    }
    review_score.validate_native_arms(case_025)
    outcome = review_score.arm_outcomes([case_025])
    assert outcome["useful_nodes_by_arm"] == {
        "literal_baseline": 1, "authority_treatment": 1,
        "net_treatment_minus_baseline": 0,
    }
    assert outcome["by_museum_pair"]["met__brooklyn"]["museum_side_record_sets"][
        "brooklyn"
    ] == {
        "literal_baseline": 1,
        "authority_treatment": 4,
        "authority_only": 3,
        "literal_only": 0,
        "both": 1,
        "net_treatment_minus_baseline": 3,
    }

    case_024 = copy.deepcopy(case_025)
    case_024["case_id"] = "case-024"
    case_024["arm_native"]["literal"]["nodes"] = [
        node("literal:first", ["met-a"], ["brooklyn-a"]),
        node("literal:second", ["met-b"], ["brooklyn-b"]),
    ]
    outcome = review_score.arm_outcomes([case_024, case_025])
    assert outcome["useful_nodes_by_arm"] == {
        "literal_baseline": 3,
        "authority_treatment": 2,
        "net_treatment_minus_baseline": -1,
    }

    wrong_merge = copy.deepcopy(case_024)
    wrong_merge["case_id"] = "wrong-many-literal-merge"
    wrong_merge["arm_native"]["authority"]["nodes"][0]["stage_1"] = {
        "same_entity": "different_entity",
        "useful_granularity": "too_broad",
    }
    outcome = review_score.arm_outcomes([wrong_merge])
    assert outcome["useful_nodes_by_arm"] == {
        "literal_baseline": 2,
        "authority_treatment": 0,
        "net_treatment_minus_baseline": -2,
    }

    distinct_controls = []
    for index in range(9):
        literal_nodes = [
            node(f"literal:{index}:a", [f"met-{index}-a"], [f"brooklyn-{index}-a"])
        ]
        if index == 8:
            literal_nodes.append(
                node(f"literal:{index}:b", [f"met-{index}-b"], [f"brooklyn-{index}-b"])
            )
        authority_node = node(
            f"authority:{index}", [f"met-{index}-a"],
            [f"brooklyn-{index}-authority" if index < 8 else f"brooklyn-{index}-a"],
        )
        control = {
            "case_id": f"distinct-accounting-{index + 1}",
            "transition_class": "retained_control",
            "museum_pair": ["met", "brooklyn"],
            "entity_type": "site",
            "arm_native": {
                "literal": {"nodes": literal_nodes},
                "authority": {"nodes": [authority_node]},
            },
            "proposed_target_id": authority_node["target_id"],
            "stage_2": {"canonical_identity": "exact_identity"},
        }
        review_score.validate_native_arms(control)
        native_nodes = literal_nodes + [authority_node]
        assert len({item["stage_1_review_unit_id"] for item in native_nodes}) == len(native_nodes)
        assert len({item["stage_1_evidence_sha256"] for item in native_nodes}) == len(native_nodes)
        assert all(set(item["stage_1"]) == {"same_entity", "useful_granularity"} for item in native_nodes)
        distinct_controls.append(control)
    nine_outcome = review_score.arm_outcomes(distinct_controls)
    assert nine_outcome["useful_nodes_by_arm"] == {
        "literal_baseline": 10,
        "authority_treatment": 9,
        "net_treatment_minus_baseline": -1,
    }


def test_traceable_score_is_node_native_and_release_is_hash_bound(tmp_path: Path) -> None:
    prompt_root = CONTROL.parent / "prompts"
    auditor_prompt = prompt_root / "prompt-auditor-v2.txt"
    stage_1_reviewer_prompt = prompt_root / "stage-1-reviewer-v2.txt"
    stage_1_reconciler_prompt = prompt_root / "stage-1-reconciler-v2.txt"
    stage_2_reviewer_prompt = prompt_root / "stage-2-reviewer-v2.txt"
    stage_2_reconciler_prompt = prompt_root / "stage-2-reconciler-v2.txt"

    def run(request_id: str, role: str) -> dict:
        return trace_run(tmp_path, request_id, role)

    def evidence(unit_id: str) -> dict:
        pair = ["met", "brooklyn"]
        return {
            "museum_pair": pair,
            "entity_type": "site",
            "sides": {
                museum: [{
                    "evidence_group": f"side-{side}-group-01",
                    "representative_exact_mention": f"Surface {unit_id} {museum}",
                    "exact_mention_variants": {f"Surface {unit_id} {museum}": 1},
                    "mention_count": 1,
                    "distinct_record_count": 1,
                    "field_paths": ["place"],
                    "evidence_roles": ["from"],
                }]
                for side, museum in enumerate(pair, 1)
            },
        }

    unit_outcomes = {
        "unit-a": ("same_entity", "useful"),
        "unit-d": ("same_entity", "useful"),
        "unit-r-literal-1": ("same_entity", "useful"),
        "unit-r-literal-2": ("same_entity", "useful"),
        "unit-r-authority": ("different_entity", "too_broad"),
    }
    evidence_by_unit = {unit: evidence(unit) for unit in unit_outcomes}
    stage_1_queue = {
        "schema_version": "hapi-authority-independent-control-stage-1-review/5",
        "review_protocol": {
            "role": "stage_1_reviewer",
            "prompt_sha256": review_protocol.sha256_path(stage_1_reviewer_prompt),
            "raw_response_contract_sha256": review_protocol.sha256_path(
                review_protocol.raw_response_contract_path("stage_1_reviewer")
            ),
        },
        "cases": [
            {
                "case_id": unit,
                "evidence_sha256": review_protocol.canonical_sha256(value),
                **value,
            }
            for unit, value in evidence_by_unit.items()
        ],
    }
    stage_1_queue_path = tmp_path / "stage-1-queue.json"
    review_queue.write_json(stage_1_queue_path, stage_1_queue)

    def subject_input(
        role: str, prompt: Path, queue: Path, name: str,
        source_reviews: list[Path] | None = None,
    ) -> Path:
        components = trace_components(role, prompt, queue, source_reviews)
        path = tmp_path / f"{name}-subject-input.json"
        path.write_bytes(review_protocol.composed_input_bytes(
            role, run(f"subject-{name}", role)["launcher_envelope"], components
        ))
        return path

    def prompt_audit(subject: Path, subject_role: str, name: str) -> Path:
        path = tmp_path / f"{name}-prompt-audit.json"
        raw = json.dumps({"outcome": "PASS", "findings": []}, sort_keys=True)
        metadata = run(f"audit-{name}", "prompt_auditor")
        composed_sha = review_protocol.composed_input_sha256(
            "prompt_auditor", metadata["launcher_envelope"], [
                ("launcher_system_prompt", review_protocol.launcher_system_prompt_path("prompt_auditor")),
                ("auditor_prompt", auditor_prompt),
                ("raw_response_contract", review_protocol.raw_response_contract_path("prompt_auditor")),
                ("subject_composed_input", subject),
            ]
        )
        review_queue.write_json(path, {
            "schema_version": review_protocol.PROMPT_AUDIT_SCHEMA_VERSION,
            "auditor_run": metadata,
            "auditor_prompt": {
                "path": str(auditor_prompt),
                "sha256": review_protocol.sha256_path(auditor_prompt),
            },
            "subject_role": subject_role,
            "subject_composed_input": {
                "path": str(subject), "sha256": review_protocol.sha256_path(subject),
            },
            "composed_input_sha256": composed_sha,
            **trace_output_fields("prompt_auditor", raw, metadata, composed_sha),
            "outcome": "PASS",
            "findings": [],
        })
        return path

    def review_package(
        *, stage: str, prompt: Path, queue: Path, audit: Path,
        decisions: list[dict], suffix: str,
    ) -> Path:
        path = tmp_path / f"stage-{stage}-review-{suffix}.json"
        role = f"stage_{stage}_reviewer"
        metadata = run(f"stage-{stage}-review-{suffix}", role)
        raw = json.dumps({"decisions": decisions}, sort_keys=True)
        composed_sha = review_protocol.composed_input_sha256(
            role, metadata["launcher_envelope"],
            trace_components(role, prompt, queue),
        )
        review_queue.write_json(path, {
            "schema_version": review_protocol.REVIEW_SCHEMA_VERSION,
            "role": role,
            "run": metadata,
            "prompt": {"path": str(prompt), "sha256": review_protocol.sha256_path(prompt)},
            "queue": {"path": str(queue), "sha256": review_protocol.sha256_path(queue)},
            "prompt_audit": {"path": str(audit), "sha256": review_protocol.sha256_path(audit)},
            "composed_input_sha256": composed_sha,
            **trace_output_fields(role, raw, metadata, composed_sha),
            "decisions": decisions,
        })
        return path

    def consensus_package(
        *, stage: str, reviewer_prompt: Path, reconciler_prompt: Path, queue: Path,
        reconciler_audit: Path, source_reviews: list[Path], reviewer_decisions: list[dict],
    ) -> Path:
        outcome_fields = (
            ("same_entity", "useful_granularity") if stage == "1"
            else ("canonical_identity",)
        )
        review_hashes = sorted(review_protocol.sha256_path(path) for path in source_reviews)
        consensus_decisions = []
        for source in reviewer_decisions:
            resolutions = {
                field: {
                    "method": "agreement",
                    "source_outcomes": [
                        {"review_sha256": digest, "outcome": source[field]}
                        for digest in review_hashes
                    ],
                    "rationale": "The independent reviewers agree.",
                    "citations": [],
                }
                for field in outcome_fields
            }
            consensus_decisions.append({**source, "field_resolutions": resolutions})
        path = tmp_path / f"stage-{stage}-consensus.json"
        role = f"stage_{stage}_reconciler"
        metadata = run(f"stage-{stage}-consensus", role)
        raw = json.dumps({"decisions": consensus_decisions}, sort_keys=True)
        ordered = sorted(source_reviews, key=review_protocol.sha256_path)
        composed_sha = review_protocol.composed_input_sha256(
            role, metadata["launcher_envelope"],
            trace_components(role, reconciler_prompt, queue, ordered),
        )
        review_queue.write_json(path, {
            "schema_version": review_protocol.CONSENSUS_SCHEMA_VERSION,
            "role": role,
            "run": metadata,
            "prompt": {
                "path": str(reconciler_prompt),
                "sha256": review_protocol.sha256_path(reconciler_prompt),
            },
            "queue": {"path": str(queue), "sha256": review_protocol.sha256_path(queue)},
            "prompt_audit": {
                "path": str(reconciler_audit),
                "sha256": review_protocol.sha256_path(reconciler_audit),
            },
            "source_reviews": [
                {"path": str(source_path), "sha256": review_protocol.sha256_path(source_path)}
                for source_path in ordered
            ],
            "composed_input_sha256": composed_sha,
            **trace_output_fields(role, raw, metadata, composed_sha),
            "decisions": consensus_decisions,
        })
        return path

    def stage_1_decision(unit: str) -> dict:
        same, useful = unit_outcomes[unit]
        return {
            "case_id": unit,
            "evidence_sha256": review_protocol.canonical_sha256(evidence_by_unit[unit]),
            "same_entity": same,
            "useful_granularity": useful,
            "reasoning": "Institutional evidence supports this test judgment.",
            "citations": ["https://www.metmuseum.org/"],
            "artifact_exceptions": [],
        }

    stage_1_decisions = [stage_1_decision(unit) for unit in unit_outcomes]
    stage_1_reviewer_subject = subject_input(
        "stage_1_reviewer", stage_1_reviewer_prompt, stage_1_queue_path,
        "stage-1-reviewer",
    )
    stage_1_reviewer_audit = prompt_audit(
        stage_1_reviewer_subject, "stage_1_reviewer", "stage-1-reviewer"
    )
    stage_1_reviews = [
        review_package(
            stage="1", prompt=stage_1_reviewer_prompt, queue=stage_1_queue_path,
            audit=stage_1_reviewer_audit, decisions=stage_1_decisions, suffix=suffix,
        )
        for suffix in ("alpha", "beta")
    ]
    stage_1_reconciler_subject = subject_input(
        "stage_1_reconciler", stage_1_reconciler_prompt, stage_1_queue_path,
        "stage-1-reconciler", stage_1_reviews,
    )
    stage_1_reconciler_audit = prompt_audit(
        stage_1_reconciler_subject, "stage_1_reconciler", "stage-1-reconciler"
    )
    stage_1_consensus = consensus_package(
        stage="1", reviewer_prompt=stage_1_reviewer_prompt,
        reconciler_prompt=stage_1_reconciler_prompt, queue=stage_1_queue_path,
        reconciler_audit=stage_1_reconciler_audit, source_reviews=stage_1_reviews,
        reviewer_decisions=stage_1_decisions,
    )

    stage_2_custodian_path = tmp_path / "stage-2-custodian.json"
    review_queue.write_json(stage_2_custodian_path, {
        "review_protocol": {
            "role": "stage_2_reviewer",
            "prompt_sha256": review_protocol.sha256_path(stage_2_reviewer_prompt),
            "raw_response_contract_sha256": review_protocol.sha256_path(
                review_protocol.raw_response_contract_path("stage_2_reviewer")
            ),
        },
        "cases": [
            {
                "case_id": case_id,
                "stage_1_review_unit_id": unit,
                "evidence_sha256": review_protocol.canonical_sha256(evidence_by_unit[unit]),
                "proposed_target": {"target_id": target},
                "question": "Is this the exact identity?",
                "allowed_outcomes": [
                    "exact_identity", "different_identity", "insufficient_evidence",
                ],
            }
            for case_id, unit, target in (
                ("case-a", "unit-a", "authority:a"),
                ("case-r", "unit-r-authority", "authority:r"),
            )
        ],
    })
    stage_2_queue_path = tmp_path / "stage-2-queue.json"
    review_queue.release_stage_2(
        ROOT, stage_1_queue_path, stage_2_custodian_path, stage_1_reviews,
        stage_1_reviewer_audit, stage_1_consensus, stage_1_reconciler_audit,
        stage_2_queue_path,
    )

    stage_2_reviewer_subject = subject_input(
        "stage_2_reviewer", stage_2_reviewer_prompt, stage_2_queue_path,
        "stage-2-reviewer",
    )
    stage_2_reviewer_audit = prompt_audit(
        stage_2_reviewer_subject, "stage_2_reviewer", "stage-2-reviewer"
    )
    stage_2_decisions = [
        {
            "case_id": case_id,
            "evidence_sha256": review_protocol.canonical_sha256(evidence_by_unit[unit]),
            "canonical_identity": "exact_identity",
            "reasoning": "Institutional evidence supports the exact target.",
            "citations": ["https://www.metmuseum.org/"],
            "artifact_exceptions": [],
        }
        for case_id, unit in (("case-a", "unit-a"), ("case-r", "unit-r-authority"))
    ]
    stage_2_reviews = [
        review_package(
            stage="2", prompt=stage_2_reviewer_prompt, queue=stage_2_queue_path,
            audit=stage_2_reviewer_audit, decisions=stage_2_decisions, suffix=suffix,
        )
        for suffix in ("alpha", "beta")
    ]
    stage_2_reconciler_subject = subject_input(
        "stage_2_reconciler", stage_2_reconciler_prompt, stage_2_queue_path,
        "stage-2-reconciler", stage_2_reviews,
    )
    stage_2_reconciler_audit = prompt_audit(
        stage_2_reconciler_subject, "stage_2_reconciler", "stage-2-reconciler"
    )
    stage_2_consensus = consensus_package(
        stage="2", reviewer_prompt=stage_2_reviewer_prompt,
        reconciler_prompt=stage_2_reconciler_prompt, queue=stage_2_queue_path,
        reconciler_audit=stage_2_reconciler_audit, source_reviews=stage_2_reviews,
        reviewer_decisions=stage_2_decisions,
    )

    def native_node(target: str, unit: str, left: list[str], right: list[str]) -> dict:
        return {
            "target_id": target,
            "mention_ids_by_side": {
                "met": [f"mention:{value}" for value in left],
                "brooklyn": [f"mention:{value}" for value in right],
            },
            "artifact_ids_by_side": {"met": left, "brooklyn": right},
            "stage_1_review_unit_id": unit,
            "stage_1_evidence_sha256": review_protocol.canonical_sha256(
                evidence_by_unit[unit]
            ),
        }

    answer_cases = []
    shapes = {
        "case-a": (
            "authority_only_transition", [],
            [native_node("authority:a", "unit-a", ["met:a"], ["brooklyn:a"])],
            "authority:a",
        ),
        "case-d": (
            "literal_only_transition",
            [native_node("literal:d", "unit-d", ["met:d"], ["brooklyn:d"])],
            [], None,
        ),
        "case-r": (
            "retained_control",
            [
                native_node("literal:r1", "unit-r-literal-1", ["met:r1"], ["brooklyn:r1"]),
                native_node("literal:r2", "unit-r-literal-2", ["met:r2"], ["brooklyn:r2"]),
            ],
            [native_node(
                "authority:r", "unit-r-authority", ["met:r1", "met:r2"],
                ["brooklyn:r1", "brooklyn:r2", "brooklyn:authority-extra"],
            )],
            "authority:r",
        ),
    }
    for case_id, (hidden_class, literal_nodes, authority_nodes, proposed) in shapes.items():
        binding = {
            "transition_class": hidden_class,
            "museum_pair": ["met", "brooklyn"],
            "entity_type": "site",
            "arm_native": {
                "literal": {"nodes": literal_nodes},
                "authority": {"nodes": authority_nodes},
            },
            "proposed_target_id": proposed,
        }
        answer_cases.append({
            "case_id": case_id,
            "case_binding_sha256": review_score.canonical_sha256(binding),
            **binding,
        })
    answer_key_path = tmp_path / "private-answer-key.json"
    review_queue.write_json(answer_key_path, {"cases": answer_cases})
    digest_path = tmp_path / "population-digest.json"
    bound_protocol_files = {
        "validator": CONTROL / "review_protocol.py",
        "scorer": CONTROL / "score_review.py",
        "response_wrapper": CONTROL / "wrap_review_response.py",
        "artifact_schema": CONTROL.parent / "review-artifact.schema.json",
    }
    prompt_files = {
        "prompt_auditor": auditor_prompt,
        "stage_1_reviewer": stage_1_reviewer_prompt,
        "stage_1_reconciler": stage_1_reconciler_prompt,
        "stage_2_reviewer": stage_2_reviewer_prompt,
        "stage_2_reconciler": stage_2_reconciler_prompt,
    }
    contract_files = {
        role: review_protocol.raw_response_contract_path(role)
        for role in review_protocol.RAW_RESPONSE_CONTRACT_PATHS
    }
    system_prompt_files = {
        "prompt_auditor": review_protocol.launcher_system_prompt_path("prompt_auditor"),
        "review": review_protocol.launcher_system_prompt_path("stage_1_reviewer"),
    }
    review_queue.write_json(digest_path, {
        "input_hashes": {"review_protocol": {
            **{
                name: {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": review_protocol.sha256_path(path),
                }
                for name, path in bound_protocol_files.items()
            },
            "prompts": {
                name: {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": review_protocol.sha256_path(path),
                }
                for name, path in prompt_files.items()
            },
            "raw_response_contracts": {
                name: {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": review_protocol.sha256_path(path),
                }
                for name, path in contract_files.items()
            },
            "launcher_system_prompts": {
                name: {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": review_protocol.sha256_path(path),
                }
                for name, path in system_prompt_files.items()
            },
        }},
        "output_hashes": {
            "stage_1_queue_sha256": review_protocol.sha256_path(stage_1_queue_path),
            "stage_2_custodian_sha256": review_protocol.sha256_path(
                stage_2_custodian_path
            ),
            "private_answer_key_sha256": review_protocol.sha256_path(answer_key_path),
        },
    })

    public = review_score.score(
        repo_root=ROOT,
        stage_1_queue_path=stage_1_queue_path,
        stage_1_review_paths=stage_1_reviews,
        stage_1_reviewer_prompt_audit_path=stage_1_reviewer_audit,
        stage_1_consensus_path=stage_1_consensus,
        stage_1_reconciler_prompt_audit_path=stage_1_reconciler_audit,
        stage_2_queue_path=stage_2_queue_path,
        stage_2_review_paths=stage_2_reviews,
        stage_2_reviewer_prompt_audit_path=stage_2_reviewer_audit,
        stage_2_consensus_path=stage_2_consensus,
        stage_2_reconciler_prompt_audit_path=stage_2_reconciler_audit,
        answer_key_path=answer_key_path,
        population_digest_path=digest_path,
        private_out=tmp_path / "private-score.json",
        public_out=tmp_path / "public-score.json",
    )
    assert public["adjudicated_arm_outcomes"]["useful_nodes_by_arm"] == {
        "literal_baseline": 3,
        "authority_treatment": 1,
        "net_treatment_minus_baseline": -2,
    }
    brooklyn = public["adjudicated_arm_outcomes"]["per_museum_any_other_museum_record_union"][
        "brooklyn"
    ]
    assert brooklyn == {
        "literal_baseline": 3,
        "authority_treatment": 1,
        "authority_only": 1,
        "literal_only": 3,
        "both": 0,
        "net_treatment_minus_baseline": -2,
        "by_entity_type": {
            "site": {
                "literal_baseline": 3,
                "authority_treatment": 1,
                "authority_only": 1,
                "literal_only": 3,
                "both": 0,
                "net_treatment_minus_baseline": -2,
            }
        },
    }

    tampered = json.loads(answer_key_path.read_text())
    tampered["cases"][2]["arm_native"]["literal"]["nodes"][0][
        "stage_1_evidence_sha256"
    ] = "0" * 64
    review_queue.write_json(answer_key_path, tampered)
    digest = json.loads(digest_path.read_text())
    digest["output_hashes"]["private_answer_key_sha256"] = review_protocol.sha256_path(
        answer_key_path
    )
    review_queue.write_json(digest_path, digest)
    with pytest.raises(ValueError, match="case binding mismatch"):
        review_score.score(
            repo_root=ROOT,
            stage_1_queue_path=stage_1_queue_path,
            stage_1_review_paths=stage_1_reviews,
            stage_1_reviewer_prompt_audit_path=stage_1_reviewer_audit,
            stage_1_consensus_path=stage_1_consensus,
            stage_1_reconciler_prompt_audit_path=stage_1_reconciler_audit,
            stage_2_queue_path=stage_2_queue_path,
            stage_2_review_paths=stage_2_reviews,
            stage_2_reviewer_prompt_audit_path=stage_2_reviewer_audit,
            stage_2_consensus_path=stage_2_consensus,
            stage_2_reconciler_prompt_audit_path=stage_2_reconciler_audit,
            answer_key_path=answer_key_path,
            population_digest_path=digest_path,
            private_out=tmp_path / "tampered-private.json",
            public_out=tmp_path / "tampered-public.json",
        )


def test_committed_report_and_review_digest_are_hash_and_count_bound() -> None:
    results = CONTROL.parent / "results"
    report_path = results / "real-run-report.json"
    manifest_path = results / "real-run-manifest.json"
    digest_path = results / "real-review-population-digest.json"
    proof_path = results / "real-rerun-proof.json"
    report_sha = review_queue.sha256_path(report_path)
    manifest_sha = review_queue.sha256_path(manifest_path)
    digest_sha = review_queue.sha256_path(digest_path)
    assert report_sha == "dd74f6b05d322efe2137c87b4ccd4c0f5b3ad91ccf8479fd45f67607ae2e39df"
    assert manifest_sha == "6c79cb360d2e9e315ef6de2ddab68c857dfe637ed06ed7b93e3e04059a174ed8"
    assert digest_sha == "43c597deca5f766717642f05c63edda23aebd55ae853596370f180f678611c75"
    assert review_queue.sha256_path(proof_path) == (
        "2a33f43c745a96d385b569a1072a3709ebcba4cd718cdbfd14e7dbd671315bc6"
    )

    report = json.loads(report_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    digest = json.loads(digest_path.read_text())
    proof = json.loads(proof_path.read_text())
    assert report["scope"]["evaluation_date"] == "2026-09-13"
    assert report["scope"]["corpus_snapshot_date"] == "2026-08-27"
    assert report["identical_mentions_proof"]["mention_ledger"]["rows"] == 148_871
    assert manifest["outputs_sha256"]["report.json"] == report_sha
    assert digest["input_hashes"]["report_sha256"] == report_sha
    assert digest["input_hashes"]["run_manifest_sha256"] == manifest_sha
    assert review_queue.recursive_forbidden_keys(digest) == []
    assert digest["review"] == {
        "protocol_manifest_sha256": (
                "cb8c18883af7f54c4f47caafc4fc30ff07ef9435f4393851da76ab0387270a38"
        ),
        "quality_conclusion_status": "NOT_AVAILABLE",
        "runtime_readiness": "BLOCKED",
        "status": "NOT_RUN",
        "valid_review_artifact_count": 0,
    }
    assert digest["arm_native_inventory"] == {
        "different_membership_case_binding_set_sha256": (
            "85f8cdec9bf2826440906a2f0c399c2339adddfe3d7c6bef47780de532274295"
        ),
        "distinct_accounting_case_binding_set_sha256": (
            "33b2dc681e3e2a980f9daa2cde5160a2863771314231e8dead3369a00655b738"
        ),
        "literal_nodes_represented_by_retained_controls": 47,
        "multiple_literal_case_binding_set_sha256": (
            "46f94afbfefa4a5024572ea4ed6c24bbf1d6f236f4e6c787c8c19ea96cbe4a4c"
        ),
        "retained_authority_control_cases": 46,
        "retained_controls_requiring_distinct_arm_native_accounting": 9,
        "retained_controls_with_different_arm_native_record_membership": 8,
        "retained_controls_with_multiple_literal_nodes": 1,
        "shared_node_cases_by_arm": {"authority": 59, "literal": 84},
        "shared_node_cases_by_pair_and_arm": {
            "brooklyn__harvard": {"authority": 4, "literal": 7},
            "met__brooklyn": {"authority": 52, "literal": 70},
            "met__harvard": {"authority": 3, "literal": 7},
        },
    }
    protocol = digest["input_hashes"]["review_protocol"]
    assert protocol["protocol_version"] == "hapi-authority-control-traceable-review/2"
    assert protocol["validator"]["sha256"] == review_queue.sha256_path(
        CONTROL / "review_protocol.py"
    )
    assert protocol["scorer"]["sha256"] == review_queue.sha256_path(
        CONTROL / "score_review.py"
    )
    assert protocol["response_wrapper"]["sha256"] == review_queue.sha256_path(
        CONTROL / "wrap_review_response.py"
    )
    assert protocol["artifact_schema"]["sha256"] == review_queue.sha256_path(
        CONTROL.parent / "review-artifact.schema.json"
    )
    for role, binding in protocol["prompts"].items():
        prompt_path = ROOT / binding["path"]
        assert binding["sha256"] == review_queue.sha256_path(prompt_path), role
    for group in ("raw_response_contracts", "launcher_system_prompts"):
        for role, binding in protocol[group].items():
            path = ROOT / binding["path"]
            assert binding["sha256"] == review_queue.sha256_path(path), (group, role)

    losses = report["comparison"]["literal_loss_attribution"]["per_pair"]
    assert {
        pair: value["nodes_by_entity_type_and_closed_cause"] for pair, value in losses.items()
    } == {
        "met__brooklyn": {
            "ruler": {
                "absent_or_unmatched_authority_target": 4,
                "ambiguous_multiple_unmerged_claim_graph_units_for_same_literal": 4,
            },
            "site": {"absent_or_unmatched_authority_target": 19, "ambiguous_authority_target": 1},
        },
        "met__harvard": {
            "ruler": {"ambiguous_multiple_unmerged_claim_graph_units_for_same_literal": 1},
            "site": {"absent_or_unmatched_authority_target": 3, "ambiguous_authority_target": 1},
        },
        "brooklyn__harvard": {
            "ruler": {"ambiguous_multiple_unmerged_claim_graph_units_for_same_literal": 1},
            "site": {"absent_or_unmatched_authority_target": 2, "ambiguous_authority_target": 1},
        },
    }

    expected = review_queue.expected_counts_from_report(report)
    assert digest["executable_check_counts"]["transition_expected"] == expected
    assert digest["executable_check_counts"]["transition_observed"] == expected
    assert digest["population_counts"] == {
        "total": 96,
        "stage_1_arm_native_review_units": 106,
        "by_class": {
            "authority_only_transition": 13,
            "literal_only_transition": 37,
            "retained_control": 46,
        },
        "by_pair_and_class": {
            "met__brooklyn": {
                "authority_only_transition": 11,
                "literal_only_transition": 28,
                "retained_control": 41,
            },
            "met__harvard": {
                "authority_only_transition": 1,
                "literal_only_transition": 5,
                "retained_control": 2,
            },
            "brooklyn__harvard": {
                "authority_only_transition": 1,
                "literal_only_transition": 4,
                "retained_control": 3,
            },
        },
        "by_entity_type": {"ruler": 15, "site": 81},
    }
    checks = digest["executable_check_counts"]
    assert checks["stage_1_forbidden_key_occurrences"] == 0
    assert checks["stage_1_private_identifier_occurrences"] == 0
    assert checks["stage_1_cross_side_group_token_matches"] == 0
    assert checks["stage_1_distinct_visible_structure_signatures"] == 1
    assert checks["stage_1_evidence_hash_mismatches"] == 0
    assert checks["stage_1_malformed_evidence_block_schemas"] == 0
    assert checks["stage_1_non_singleton_side_evidence_blocks"] == 0
    assert checks["stage_2_release_candidate_cases"] == 59
    assert checks["stage_2_stage_1_duplicate_case_ids"] == 0
    assert checks["stage_2_custodian_duplicate_case_ids"] == 0
    assert checks["stage_2_missing_stage_1_review_units"] == 0
    assert checks["stage_2_evidence_hash_mismatches"] == 0
    assert checks["stage_2_recomputed_evidence_hash_mismatches"] == 0
    assert checks["stage_2_insufficient_evidence_cases"] == 0
    assert checks["actual_controls_numerator"] >= checks["required_controls_numerator"]

    assert proof["identical_file_count"] == len(rerun.FILES) == 15
    assert proof["sha256_by_file"]["report.json"] == report_sha
    assert proof["sha256_by_file"]["run-manifest.json"] == manifest_sha
    assert proof["sha256_by_file"]["review/public-review-population-digest.json"] == digest_sha
    for digest_key, relative in {
        "stage_1_queue_sha256": "review/stage-1-queue.json",
        "stage_2_custodian_sha256": "review/stage-2-custodian.json",
        "private_answer_key_sha256": "review/private-answer-key.json",
        "private_population_manifest_sha256": "review/review-population-manifest.json",
        "review_protocol_manifest_sha256": "review/review-protocol-manifest.json",
    }.items():
        assert digest["output_hashes"][digest_key] == proof["sha256_by_file"][relative]

    protocol_manifest_path = results / "real-review-protocol-manifest.json"
    assert review_queue.sha256_path(protocol_manifest_path) == (
        digest["output_hashes"]["review_protocol_manifest_sha256"]
    )
    protocol_manifest = json.loads(protocol_manifest_path.read_text())
    assert protocol_manifest == {
        **protocol_manifest,
        "review_status": "NOT_RUN",
        "quality_conclusion_status": "NOT_AVAILABLE",
        "valid_review_artifact_count": 0,
        "runtime_readiness": {
            "status": "BLOCKED",
            "blocker": (
                "missing_genuine_immutable_provider_snapshot_and_authorized_api_path"
            ),
        },
    }
    assert not (results / "real-adjudicated-review.json").exists()
    assert not (results / "real-adjudicated-review.md").exists()
