#!/usr/bin/env python3
"""Score only prompt-audited, fully traceable two-stage review artifacts."""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


PRIMARY_CATEGORIES = (
    "a_authority_only_same_useful_exact_target",
    "b_authority_only_useful_but_wrong_or_nonidentity",
    "c_authority_only_false_or_not_useful_gain",
    "d_literal_only_same_useful_connection_lost",
    "e_literal_only_false_or_not_useful_removal",
    "f_transition_uncertainty",
)
PUBLIC_FORBIDDEN_KEYS = {
    "arm_native", "artifact_id", "artifact_ids", "artifact_ids_by_side", "case_id",
    "case_binding_sha256", "mention_id", "mention_ids", "mention_ids_by_side",
    "proposed_target", "proposed_target_id", "target_id",
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_protocol(repo_root: Path):
    path = repo_root / "docs/evaluations/authority-independent-control-2026-09-13/scripts/review_protocol.py"
    spec = importlib.util.spec_from_file_location("_authority_control_review_protocol_for_score", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load traceable review protocol")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def keyed(rows: list[dict], label: str) -> dict[str, dict]:
    ids = [row.get("case_id") for row in rows]
    if None in ids or len(ids) != len(set(ids)):
        raise ValueError(f"{label} case IDs are missing or duplicated")
    return {row["case_id"]: row for row in rows}


def stage_1_evidence(case: dict) -> dict:
    return {
        "museum_pair": case["museum_pair"],
        "entity_type": case["entity_type"],
        "sides": case["sides"],
    }


def validate_native_arms(case: dict) -> None:
    pair = case["museum_pair"]
    arms = case.get("arm_native")
    if not isinstance(arms, dict) or set(arms) != {"literal", "authority"}:
        raise ValueError(f"arm-native binding missing: {case['case_id']}")
    for arm_name, arm in arms.items():
        if not isinstance(arm, dict) or set(arm) != {"nodes"} or not isinstance(arm["nodes"], list):
            raise ValueError(f"invalid {arm_name} arm binding: {case['case_id']}")
        targets = [node.get("target_id") for node in arm["nodes"]]
        if None in targets or len(targets) != len(set(targets)):
            raise ValueError(f"invalid {arm_name} node IDs: {case['case_id']}")
        for node in arm["nodes"]:
            base_fields = {
                "target_id", "mention_ids_by_side", "artifact_ids_by_side",
                "stage_1_review_unit_id", "stage_1_evidence_sha256",
            }
            if set(node) not in (base_fields, base_fields | {"stage_1"}):
                raise ValueError(f"invalid {arm_name} node fields: {case['case_id']}")
            if not isinstance(node["stage_1_review_unit_id"], str) or not node[
                "stage_1_review_unit_id"
            ]:
                raise ValueError(f"invalid {arm_name} review-unit ID: {case['case_id']}")
            for key in ("mention_ids_by_side", "artifact_ids_by_side"):
                values = node[key]
                if set(values) != set(pair) or any(not values[museum] for museum in pair):
                    raise ValueError(f"invalid {arm_name} {key}: {case['case_id']}")
    node_counts_for_case = {arm: len(arms[arm]["nodes"]) for arm in arms}
    expected = {
        "authority_only_transition": {"literal": 0, "authority": 1},
        "literal_only_transition": {"literal": 1, "authority": 0},
    }
    transition_class = case["transition_class"]
    if transition_class in expected and node_counts_for_case != expected[transition_class]:
        raise ValueError(f"arm-native transition shape mismatch: {case['case_id']}")
    if transition_class == "retained_control" and not (
        node_counts_for_case["literal"] >= 1 and node_counts_for_case["authority"] == 1
    ):
        raise ValueError(f"arm-native retained-control shape mismatch: {case['case_id']}")
    authority_targets = [node["target_id"] for node in arms["authority"]["nodes"]]
    if case["proposed_target_id"] != (authority_targets[0] if authority_targets else None):
        raise ValueError(f"proposed target/authority node mismatch: {case['case_id']}")


def classify_case(case: dict) -> str:
    native_arm = (
        "literal" if case["transition_class"] == "literal_only_transition" else "authority"
    )
    native_nodes = case["arm_native"][native_arm]["nodes"]
    stage_1 = native_nodes[0]["stage_1"]
    stage_2 = case["stage_2"]
    uncertain = (
        stage_1["same_entity"] == "insufficient_evidence"
        or stage_1["useful_granularity"] == "insufficient_evidence"
        or (stage_2 is not None and stage_2["canonical_identity"] == "insufficient_evidence")
    )
    same = stage_1["same_entity"] == "same_entity"
    useful = stage_1["useful_granularity"] == "useful"
    exact = stage_2 is not None and stage_2["canonical_identity"] == "exact_identity"
    different = stage_2 is not None and stage_2["canonical_identity"] == "different_identity"
    if case["transition_class"] == "authority_only_transition":
        if uncertain:
            return "f_transition_uncertainty"
        if same and useful and exact:
            return "a_authority_only_same_useful_exact_target"
        if useful and (not same or different):
            return "b_authority_only_useful_but_wrong_or_nonidentity"
        return "c_authority_only_false_or_not_useful_gain"
    if case["transition_class"] == "literal_only_transition":
        if uncertain:
            return "f_transition_uncertainty"
        if same and useful:
            return "d_literal_only_same_useful_connection_lost"
        return "e_literal_only_false_or_not_useful_removal"
    if uncertain:
        return "calibration_control_uncertainty"
    if same and useful and exact:
        return "calibration_control_same_useful_exact_target"
    if useful and (not same or different):
        return "calibration_control_useful_but_wrong_or_nonidentity"
    return "calibration_control_false_or_not_useful"


def validate_and_join(
    stage_1_queue: dict,
    stage_1_consensus: dict,
    stage_2_queue: dict,
    stage_2_consensus: dict,
    answer_key: dict,
) -> list[dict]:
    stage_1_cases = keyed(stage_1_queue["cases"], "Stage 1 queue")
    stage_1_decisions = keyed(stage_1_consensus["decisions"], "Stage 1 consensus")
    stage_2_cases = keyed(stage_2_queue["cases"], "Stage 2 queue")
    stage_2_decisions = keyed(stage_2_consensus["decisions"], "Stage 2 consensus")
    answers = keyed(answer_key["cases"], "answer key")
    if set(stage_1_cases) != set(stage_1_decisions):
        raise ValueError("Stage 1 queue and consensus review-unit sets differ")
    proposed = {case_id for case_id, case in answers.items() if case["proposed_target_id"]}
    if set(stage_2_cases) != proposed or set(stage_2_decisions) != proposed:
        raise ValueError("Stage 2 case set differs from proposed-target cases")
    joined = []
    for case_id, answer in answers.items():
        validate_native_arms(answer)
        binding = {
            key: answer[key]
            for key in (
                "transition_class", "museum_pair", "entity_type", "arm_native",
                "proposed_target_id",
            )
        }
        if canonical_sha256(binding) != answer["case_binding_sha256"]:
            raise ValueError(f"answer-key case binding mismatch: {case_id}")
        joined_arms = json.loads(json.dumps(answer["arm_native"]))
        for arm in ("literal", "authority"):
            for node in joined_arms[arm]["nodes"]:
                review_unit_id = node["stage_1_review_unit_id"]
                if review_unit_id not in stage_1_cases:
                    raise ValueError(f"missing Stage 1 review unit: {case_id}/{review_unit_id}")
                stage_1_case = stage_1_cases[review_unit_id]
                expected_evidence_sha = node["stage_1_evidence_sha256"]
                if canonical_sha256(stage_1_evidence(stage_1_case)) != expected_evidence_sha:
                    raise ValueError(
                        f"Stage 1 evidence content mismatch: {case_id}/{review_unit_id}"
                    )
                decision_1 = stage_1_decisions[review_unit_id]
                if decision_1["evidence_sha256"] != expected_evidence_sha:
                    raise ValueError(
                        f"Stage 1 consensus evidence mismatch: {case_id}/{review_unit_id}"
                    )
                node["stage_1"] = {
                    "same_entity": decision_1["same_entity"],
                    "useful_granularity": decision_1["useful_granularity"],
                }
        decision_2 = None
        if case_id in stage_2_cases:
            stage_2_case = stage_2_cases[case_id]
            authority_node = joined_arms["authority"]["nodes"][0]
            if canonical_sha256(stage_1_evidence(stage_2_case)) != authority_node[
                "stage_1_evidence_sha256"
            ]:
                raise ValueError(f"Stage 2 evidence content mismatch: {case_id}")
            if stage_2_case["proposed_target"]["target_id"] != answer["proposed_target_id"]:
                raise ValueError(f"Stage 2 proposed target mismatch: {case_id}")
            decision_2 = {
                "canonical_identity": stage_2_decisions[case_id]["canonical_identity"]
            }
        row = {
            **answer,
            "arm_native": joined_arms,
            "stage_2": decision_2,
        }
        row["decision_category"] = classify_case(row)
        joined.append(row)
    return sorted(joined, key=lambda row: row["case_id"])


def eligible_nodes(case: dict, arm: str) -> list[dict]:
    if arm == "authority" and (
        case["stage_2"] is None
        or case["stage_2"]["canonical_identity"] != "exact_identity"
    ):
        return []
    return [
        node for node in case["arm_native"][arm]["nodes"]
        if node["stage_1"]["same_entity"] == "same_entity"
        and node["stage_1"]["useful_granularity"] == "useful"
    ]


def node_counts(cases: list[dict]) -> dict[str, int]:
    literal = sum(len(eligible_nodes(case, "literal")) for case in cases)
    authority = sum(len(eligible_nodes(case, "authority")) for case in cases)
    return {
        "literal_baseline": literal,
        "authority_treatment": authority,
        "net_treatment_minus_baseline": authority - literal,
    }


def record_sets(cases: list[dict], museum: str) -> tuple[set[str], set[str]]:
    output = []
    for arm in ("literal", "authority"):
        output.append({
            artifact_id
            for case in cases
            if museum in case["museum_pair"]
            for node in eligible_nodes(case, arm)
            for artifact_id in node["artifact_ids_by_side"][museum]
        })
    return output[0], output[1]


def record_counts(literal: set[str], authority: set[str]) -> dict:
    baseline = len(literal)
    treatment = len(authority)
    result = {
        "literal_baseline": baseline,
        "authority_treatment": treatment,
        "authority_only": len(authority - literal),
        "literal_only": len(literal - authority),
        "both": len(literal & authority),
        "net_treatment_minus_baseline": treatment - baseline,
    }
    if result["authority_only"] + result["both"] != treatment:
        raise ValueError("authority record partition invariant failed")
    if result["literal_only"] + result["both"] != baseline:
        raise ValueError("literal record partition invariant failed")
    if result["authority_only"] - result["literal_only"] != result["net_treatment_minus_baseline"]:
        raise ValueError("record net invariant failed")
    return result


def arm_outcomes(cases: list[dict]) -> dict:
    entity_types = sorted({case["entity_type"] for case in cases})
    museums = sorted({museum for case in cases for museum in case["museum_pair"]})
    pairs = sorted({tuple(case["museum_pair"]) for case in cases})
    by_pair = {}
    for pair in pairs:
        pair_cases = [case for case in cases if tuple(case["museum_pair"]) == pair]
        pair_key = "__".join(pair)
        by_pair[pair_key] = {
            "useful_nodes_by_arm": node_counts(pair_cases),
            "museum_side_record_sets": {
                museum: record_counts(*record_sets(pair_cases, museum)) for museum in pair
            },
            "by_entity_type": {
                entity_type: {
                    "useful_nodes_by_arm": node_counts(entity_cases),
                    "museum_side_record_sets": {
                        museum: record_counts(*record_sets(entity_cases, museum)) for museum in pair
                    },
                }
                for entity_type in entity_types
                for entity_cases in [[
                    case for case in pair_cases if case["entity_type"] == entity_type
                ]]
            },
        }
    return {
        "useful_nodes_by_arm": node_counts(cases),
        "by_entity_type": {
            entity_type: node_counts(entity_cases)
            for entity_type in entity_types
            for entity_cases in [[case for case in cases if case["entity_type"] == entity_type]]
        },
        "by_museum_pair": by_pair,
        "per_museum_any_other_museum_record_union": {
            museum: {
                **record_counts(*record_sets(cases, museum)),
                "by_entity_type": {
                    entity_type: record_counts(*record_sets(
                        [case for case in cases if case["entity_type"] == entity_type], museum
                    ))
                    for entity_type in entity_types
                },
            }
            for museum in museums
        },
    }


def recursive_forbidden_keys(value, path: str = "$") -> list[str]:
    findings = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in PUBLIC_FORBIDDEN_KEYS:
                findings.append(child_path)
            findings.extend(recursive_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(recursive_forbidden_keys(child, f"{path}[{index}]"))
    return findings


def score(
    *, repo_root: Path, stage_1_queue_path: Path, stage_1_review_paths: list[Path],
    stage_1_reviewer_prompt_audit_path: Path, stage_1_consensus_path: Path,
    stage_1_reconciler_prompt_audit_path: Path, stage_2_queue_path: Path,
    stage_2_review_paths: list[Path], stage_2_reviewer_prompt_audit_path: Path,
    stage_2_consensus_path: Path, stage_2_reconciler_prompt_audit_path: Path,
    answer_key_path: Path, population_digest_path: Path, private_out: Path,
    public_out: Path,
) -> dict:
    protocol = load_protocol(repo_root)
    prompt_root = repo_root / "docs/evaluations/authority-independent-control-2026-09-13/prompts"
    consensus_1 = protocol.validate_consensus_package(
        stage_1_consensus_path, stage_1_queue_path,
        prompt_root / "stage-1-reviewer-v2.txt", stage_1_reviewer_prompt_audit_path,
        stage_1_review_paths, prompt_root / "stage-1-reconciler-v2.txt",
        stage_1_reconciler_prompt_audit_path, prompt_root / "prompt-auditor-v2.txt", "1",
    )
    consensus_2 = protocol.validate_consensus_package(
        stage_2_consensus_path, stage_2_queue_path,
        prompt_root / "stage-2-reviewer-v2.txt", stage_2_reviewer_prompt_audit_path,
        stage_2_review_paths, prompt_root / "stage-2-reconciler-v2.txt",
        stage_2_reconciler_prompt_audit_path, prompt_root / "prompt-auditor-v2.txt", "2",
    )
    digest = read_json(population_digest_path)
    answer = read_json(answer_key_path)
    protocol_bindings = digest.get("input_hashes", {}).get("review_protocol", {})
    expected_protocol_paths = [
        protocol_bindings.get("validator"),
        protocol_bindings.get("scorer"),
        protocol_bindings.get("response_wrapper"),
        protocol_bindings.get("artifact_schema"),
        *protocol_bindings.get("prompts", {}).values(),
        *protocol_bindings.get("raw_response_contracts", {}).values(),
        *protocol_bindings.get("launcher_system_prompts", {}).values(),
    ]
    if not expected_protocol_paths or any(not isinstance(item, dict) for item in expected_protocol_paths):
        raise ValueError("population digest lacks complete review-protocol bindings")
    for binding in expected_protocol_paths:
        bound_path = repo_root / binding.get("path", "")
        if binding.get("sha256") != sha256_path(bound_path):
            raise ValueError(f"population digest review-protocol binding changed: {bound_path}")
    if digest["output_hashes"]["stage_1_queue_sha256"] != sha256_path(stage_1_queue_path):
        raise ValueError("population digest does not bind Stage 1 queue")
    if digest["output_hashes"]["private_answer_key_sha256"] != sha256_path(answer_key_path):
        raise ValueError("population digest does not bind answer key")
    stage_2_queue = read_json(stage_2_queue_path)
    if stage_2_queue["stage_1_queue_sha256"] != sha256_path(stage_1_queue_path):
        raise ValueError("Stage 2 queue does not bind Stage 1 queue")
    if stage_2_queue["stage_2_custodian_sha256"] != digest["output_hashes"][
        "stage_2_custodian_sha256"
    ]:
        raise ValueError("Stage 2 queue does not bind the population custodian")
    if stage_2_queue["frozen_stage_1_consensus_sha256"] != sha256_path(stage_1_consensus_path):
        raise ValueError("Stage 2 queue does not bind Stage 1 consensus")
    joined = validate_and_join(
        read_json(stage_1_queue_path), consensus_1, stage_2_queue, consensus_2, answer
    )
    input_paths = {
        "stage_1_queue": stage_1_queue_path,
        "stage_1_consensus": stage_1_consensus_path,
        "stage_2_queue": stage_2_queue_path,
        "stage_2_consensus": stage_2_consensus_path,
        "private_answer_key": answer_key_path,
        "review_population_digest": population_digest_path,
    }
    private = {
        "schema_version": "hapi-authority-control-private-adjudicated-join/2",
        "scorer_sha256": sha256_path(Path(__file__)),
        "input_hashes": {name: sha256_path(path) for name, path in input_paths.items()},
        "source_review_hashes": sorted(
            sha256_path(path) for path in [*stage_1_review_paths, *stage_2_review_paths]
        ),
        "cases": joined,
    }
    write_json(private_out, private)
    transitions = [case for case in joined if case["transition_class"] != "retained_control"]
    public = {
        "schema_version": "hapi-authority-control-adjudicated-score/2",
        "evaluation_date": "2026-09-13",
        "scorer_sha256": sha256_path(Path(__file__)),
        "input_hashes": private["input_hashes"],
        "source_review_hashes": private["source_review_hashes"],
        "private_join_sha256": sha256_path(private_out),
        "primary_decision_counts": {
            category: sum(case["decision_category"] == category for case in transitions)
            for category in PRIMARY_CATEGORIES
        },
        "adjudicated_arm_outcomes": arm_outcomes(joined),
        "review_status": "COMPLETE_TRACEABLE",
    }
    leaks = recursive_forbidden_keys(public)
    if leaks:
        raise ValueError(f"public score leaks private fields: {leaks}")
    write_json(public_out, public)
    return public


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--stage-1-queue", type=Path, required=True)
    parser.add_argument("--stage-1-review", type=Path, action="append", required=True)
    parser.add_argument("--stage-1-reviewer-prompt-audit", type=Path, required=True)
    parser.add_argument("--stage-1-consensus", type=Path, required=True)
    parser.add_argument("--stage-1-reconciler-prompt-audit", type=Path, required=True)
    parser.add_argument("--stage-2-queue", type=Path, required=True)
    parser.add_argument("--stage-2-review", type=Path, action="append", required=True)
    parser.add_argument("--stage-2-reviewer-prompt-audit", type=Path, required=True)
    parser.add_argument("--stage-2-consensus", type=Path, required=True)
    parser.add_argument("--stage-2-reconciler-prompt-audit", type=Path, required=True)
    parser.add_argument("--private-answer-key", type=Path, required=True)
    parser.add_argument("--review-population-digest", type=Path, required=True)
    parser.add_argument("--private-out", type=Path, required=True)
    parser.add_argument("--public-out", type=Path, required=True)
    args = parser.parse_args()
    public = score(
        repo_root=args.repo_root.resolve(), stage_1_queue_path=args.stage_1_queue,
        stage_1_review_paths=args.stage_1_review,
        stage_1_reviewer_prompt_audit_path=args.stage_1_reviewer_prompt_audit,
        stage_1_consensus_path=args.stage_1_consensus,
        stage_1_reconciler_prompt_audit_path=args.stage_1_reconciler_prompt_audit,
        stage_2_queue_path=args.stage_2_queue, stage_2_review_paths=args.stage_2_review,
        stage_2_reviewer_prompt_audit_path=args.stage_2_reviewer_prompt_audit,
        stage_2_consensus_path=args.stage_2_consensus,
        stage_2_reconciler_prompt_audit_path=args.stage_2_reconciler_prompt_audit,
        answer_key_path=args.private_answer_key,
        population_digest_path=args.review_population_digest,
        private_out=args.private_out, public_out=args.public_out,
    )
    print(json.dumps(public, indent=2))


if __name__ == "__main__":
    main()
