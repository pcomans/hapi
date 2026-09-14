#!/usr/bin/env python3
"""Build and gate the private two-stage transition review population."""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


PAIRS = (("met", "brooklyn"), ("met", "harvard"), ("brooklyn", "harvard"))
OPAQUE_ORDER_SEED = "hapi-authority-independent-control-2026-09-13-stage-1-v1"
CONTROL_RATIO_NUMERATOR = 9
CONTROL_RATIO_DENOMINATOR = 10
STAGE_1_FORBIDDEN_KEYS = {
    "artifact_id",
    "artifact_ids",
    "artifact_ids_by_side",
    "authority_target",
    "case_binding_sha256",
    "mention_id",
    "mention_ids",
    "mention_ids_by_side",
    "proposed_target",
    "proposed_target_id",
    "source_target_id",
    "surface_group",
    "target_id",
    "target_ids",
    "target_label",
    "target_metadata",
    "transition_class",
}
STAGE_2_FORBIDDEN_KEYS = {
    "arm",
    "artifact_id",
    "artifact_ids",
    "artifact_ids_by_side",
    "case_binding_sha256",
    "gain_loss_label",
    "mention_id",
    "mention_ids",
    "mention_ids_by_side",
    "source_arm",
    "source_target_id",
    "transition_class",
}
SAME_ENTITY_OUTCOMES = ("same_entity", "different_entity", "insufficient_evidence")
USEFUL_GRANULARITY_OUTCOMES = ("useful", "too_broad", "too_narrow", "insufficient_evidence")
CANONICAL_IDENTITY_OUTCOMES = ("exact_identity", "different_identity", "insufficient_evidence")
EVALUATION_ROOT = Path("docs/evaluations/authority-independent-control-2026-09-13")
PROMPT_PATHS = {
    "prompt_auditor": EVALUATION_ROOT / "prompts/prompt-auditor-v2.txt",
    "stage_1_reviewer": EVALUATION_ROOT / "prompts/stage-1-reviewer-v2.txt",
    "stage_1_reconciler": EVALUATION_ROOT / "prompts/stage-1-reconciler-v2.txt",
    "stage_2_reviewer": EVALUATION_ROOT / "prompts/stage-2-reviewer-v2.txt",
    "stage_2_reconciler": EVALUATION_ROOT / "prompts/stage-2-reconciler-v2.txt",
}
RAW_RESPONSE_CONTRACT_PATHS = {
    "prompt_auditor": EVALUATION_ROOT / "raw-response-contracts/prompt-auditor-v1.schema.json",
    "stage_1_reviewer": EVALUATION_ROOT / "raw-response-contracts/stage-1-reviewer-v1.schema.json",
    "stage_1_reconciler": EVALUATION_ROOT / "raw-response-contracts/stage-1-reconciler-v1.schema.json",
    "stage_2_reviewer": EVALUATION_ROOT / "raw-response-contracts/stage-2-reviewer-v1.schema.json",
    "stage_2_reconciler": EVALUATION_ROOT / "raw-response-contracts/stage-2-reconciler-v1.schema.json",
}
LAUNCHER_SYSTEM_PROMPT_PATHS = {
    "prompt_auditor": EVALUATION_ROOT / "launcher-instructions/prompt-auditor-system-v1.txt",
    "review": EVALUATION_ROOT / "launcher-instructions/review-system-v1.txt",
}
REVIEW_SCHEMA_PATH = EVALUATION_ROOT / "review-artifact.schema.json"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha256(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_gzip_rows(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def review_protocol_inputs(repo_root: Path) -> dict:
    prompts = {
        role: {
            "path": path.as_posix(),
            "sha256": sha256_path(repo_root / path),
        }
        for role, path in sorted(PROMPT_PATHS.items())
    }
    contracts = {
        role: {
            "path": path.as_posix(),
            "sha256": sha256_path(repo_root / path),
        }
        for role, path in sorted(RAW_RESPONSE_CONTRACT_PATHS.items())
    }
    launcher_system_prompts = {
        role: {
            "path": path.as_posix(),
            "sha256": sha256_path(repo_root / path),
        }
        for role, path in sorted(LAUNCHER_SYSTEM_PROMPT_PATHS.items())
    }
    return {
        "protocol_version": "hapi-authority-control-traceable-review/2",
        "validator": {
            "path": (EVALUATION_ROOT / "scripts/review_protocol.py").as_posix(),
            "sha256": sha256_path(repo_root / EVALUATION_ROOT / "scripts/review_protocol.py"),
        },
        "scorer": {
            "path": (EVALUATION_ROOT / "scripts/score_review.py").as_posix(),
            "sha256": sha256_path(repo_root / EVALUATION_ROOT / "scripts/score_review.py"),
        },
        "response_wrapper": {
            "path": (EVALUATION_ROOT / "scripts/wrap_review_response.py").as_posix(),
            "sha256": sha256_path(
                repo_root / EVALUATION_ROOT / "scripts/wrap_review_response.py"
            ),
        },
        "artifact_schema": {
            "path": REVIEW_SCHEMA_PATH.as_posix(),
            "sha256": sha256_path(repo_root / REVIEW_SCHEMA_PATH),
        },
        "prompts": prompts,
        "raw_response_contracts": contracts,
        "launcher_system_prompts": launcher_system_prompts,
    }


def load_comparison_module(repo_root: Path):
    path = repo_root / "docs/evaluations/authority-independent-control-2026-09-13/scripts/compare_arms.py"
    spec = importlib.util.spec_from_file_location("_authority_control_for_queue", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load control comparison module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_review_protocol_module(repo_root: Path):
    path = repo_root / EVALUATION_ROOT / "scripts/review_protocol.py"
    spec = importlib.util.spec_from_file_location("_authority_control_review_protocol", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load traceable review protocol module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_run(run: Path) -> tuple[dict, dict]:
    manifest = read_json(run / "run-manifest.json")
    report = read_json(run / "report.json")
    ledger = run / "mentions.ndjson.gz"
    if sha256_path(ledger) != manifest["inputs"]["mention_ledger"]["gzip_sha256"]:
        raise ValueError("review population mention ledger does not match run manifest")
    for name, expected in manifest["outputs_sha256"].items():
        if sha256_path(run / name) != expected:
            raise ValueError(f"review population input changed after run: {name}")
    if sha256_path(run / "report.json") != manifest["outputs_sha256"]["report.json"]:
        raise ValueError("report is not bound by the run manifest")
    return manifest, report


def surface_groups(
    mention_ids: list[str],
    mentions: dict[str, dict],
    literal_rows: dict[str, dict],
    side_index: int,
) -> list[dict]:
    rows = []
    for mention_id in mention_ids:
        literal = literal_rows[mention_id]
        if literal["status"] != "resolved" or len(literal["target_ids"]) != 1:
            raise ValueError(f"transition evidence has no literal control target: {mention_id}")
        rows.append(mentions[mention_id])
    texts = collections.Counter(row["mention_text"] for row in rows)
    representative = sorted(texts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    # One aggregate evidence block per museum side preserves every exact surface,
    # role, path, and count without exposing a hidden typed-literal partition or
    # target-derived order/cardinality proxy.
    return [{
        "evidence_group": f"side-{side_index}-evidence",
        "representative_exact_mention": representative,
        "exact_mention_variants": dict(sorted(texts.items())),
        "mention_count": len(rows),
        "distinct_record_count": len({row["artifact_id"] for row in rows}),
        "field_paths": sorted({row["field_path"] for row in rows}),
        "evidence_roles": sorted({row["evidence_role"] for row in rows}),
    }]


def links_by_target(links: list[dict]) -> dict[str, dict[str, list[dict]]]:
    grouped: dict[str, dict[str, list[dict]]] = collections.defaultdict(
        lambda: collections.defaultdict(list)
    )
    for link in links:
        grouped[link["target_id"]][link["museum"]].append(link)
    return grouped


def mention_ids_for_sides(sides: dict[str, list[dict]], pair: tuple[str, str]) -> dict[str, list[str]]:
    return {
        museum: sorted({
            mention_id
            for link in sides[museum]
            for mention_id in link["mention_ids"]
        })
        for museum in pair
    }


def target_sets_by_side(
    mention_ids_by_side: dict[str, list[str]], resolution_rows: dict[str, dict]
) -> dict[str, set[str]]:
    return {
        museum: {
            target
            for mention_id in mention_ids
            if resolution_rows[mention_id]["status"] == "resolved"
            for target in resolution_rows[mention_id]["target_ids"]
        }
        for museum, mention_ids in mention_ids_by_side.items()
    }


def common_target(targets_by_side: dict[str, set[str]], pair: tuple[str, str]) -> set[str]:
    return targets_by_side[pair[0]] & targets_by_side[pair[1]]


def make_candidate(
    *,
    transition_class: str,
    pair: tuple[str, str],
    entity_type: str,
    order_source_target_id: str,
    order_mention_ids_by_side: dict[str, list[str]],
    literal_nodes: list[dict],
    authority_nodes: list[dict],
    proposed_target: dict | None,
) -> dict:
    order_binding = {
        "transition_class": transition_class,
        "museum_pair": list(pair),
        "entity_type": entity_type,
        "source_target_id": order_source_target_id,
        "mention_ids_by_side": order_mention_ids_by_side,
        "proposed_target_id": proposed_target["target_id"] if proposed_target else None,
    }
    hidden_binding = {
        "transition_class": transition_class,
        "museum_pair": list(pair),
        "entity_type": entity_type,
        "arm_native": {
            "literal": {"nodes": literal_nodes},
            "authority": {"nodes": authority_nodes},
        },
        "proposed_target_id": proposed_target["target_id"] if proposed_target else None,
    }
    return {
        "hidden_binding": hidden_binding,
        "proposed_target": proposed_target,
        "opaque_order_binding_sha256": canonical_sha256(order_binding),
    }


def review_unit_binding(pair: list[str], entity_type: str, node: dict) -> dict:
    return {
        "museum_pair": pair,
        "entity_type": entity_type,
        "mention_ids_by_side": node["mention_ids_by_side"],
    }


def review_unit_evidence(
    binding: dict, mentions: dict[str, dict], literal_rows: dict[str, dict]
) -> dict:
    return {
        "museum_pair": binding["museum_pair"],
        "entity_type": binding["entity_type"],
        "sides": {
            museum: surface_groups(
                binding["mention_ids_by_side"][museum],
                mentions,
                literal_rows,
                side_index,
            )
            for side_index, museum in enumerate(binding["museum_pair"], 1)
        },
    }


def arm_node(
    target_id: str, mention_ids_by_side: dict[str, list[str]], mentions: dict[str, dict]
) -> dict:
    return {
        "target_id": target_id,
        "mention_ids_by_side": {
            museum: sorted(ids) for museum, ids in sorted(mention_ids_by_side.items())
        },
        "artifact_ids_by_side": {
            museum: sorted({mentions[mention_id]["artifact_id"] for mention_id in ids})
            for museum, ids in sorted(mention_ids_by_side.items())
        },
    }


def expected_counts_from_report(report: dict) -> dict[str, dict[str, int]]:
    output = {
        "authority_only_transition": {},
        "literal_only_transition": {},
        "retained_control": {},
    }
    for pair in PAIRS:
        pair_key = "__".join(pair)
        transitions = report["comparison"]["shared_node_transitions"]["per_pair"][pair_key]
        output["authority_only_transition"][pair_key] = transitions[
            "authority_shared_nodes_created_only_by_cross_literal_authority_consolidation"
        ]
        output["literal_only_transition"][pair_key] = transitions[
            "literal_shared_nodes_lost_by_authority"
        ]
        output["retained_control"][pair_key] = transitions[
            "authority_shared_nodes_with_one_common_surface_literal"
        ]
    return output


def derive_candidates(
    repo_root: Path, run: Path
) -> tuple[list[dict], dict, dict, dict[str, dict], dict[str, dict]]:
    run_manifest, report = validate_run(run)
    mentions_list = read_gzip_rows(run / "mentions.ndjson.gz")
    literal_list = read_gzip_rows(run / "typed-literal-arm.ndjson.gz")
    authority_list = read_gzip_rows(run / "current-authority-arm.ndjson.gz")
    literal_links = read_gzip_rows(run / "typed-literal-links.ndjson.gz")
    authority_links = read_gzip_rows(run / "current-authority-links.ndjson.gz")
    mentions = {row["mention_id"]: row for row in mentions_list}
    literal_rows = {row["mention_id"]: row for row in literal_list}
    authority_rows = {row["mention_id"]: row for row in authority_list}
    if not (set(mentions) == set(literal_rows) == set(authority_rows)):
        raise ValueError("review population arms do not share the mention ledger")

    module = load_comparison_module(repo_root)
    _resolver_module, _resolvers, catalogs = module.load_current_resolvers(repo_root)
    literal_targets = links_by_target(literal_links)
    authority_targets = links_by_target(authority_links)
    candidates = []

    for pair in PAIRS:
        for target_id, sides in authority_targets.items():
            if not all(museum in sides for museum in pair):
                continue
            mention_ids_by_side = mention_ids_for_sides(sides, pair)
            literal_by_side = target_sets_by_side(mention_ids_by_side, literal_rows)
            common_literal_targets = sorted(common_target(literal_by_side, pair))
            transition_class = (
                "retained_control"
                if common_literal_targets
                else "authority_only_transition"
            )
            entity_types = {link["entity_type"] for museum in pair for link in sides[museum]}
            if len(entity_types) != 1:
                raise ValueError(f"one authority target crosses entity types: {target_id}")
            entity_type = entity_types.pop()
            catalog = catalogs[entity_type][target_id]
            literal_nodes = [
                arm_node(
                    literal_target,
                    mention_ids_for_sides(literal_targets[literal_target], pair),
                    mentions,
                )
                for literal_target in common_literal_targets
            ]
            authority_nodes = [arm_node(target_id, mention_ids_by_side, mentions)]
            order_mention_ids_by_side = {
                museum: sorted({
                    *mention_ids_by_side[museum],
                    *(
                        mention_id
                        for node in literal_nodes
                        for mention_id in node["mention_ids_by_side"][museum]
                    ),
                })
                for museum in pair
            }
            candidates.append(make_candidate(
                transition_class=transition_class,
                pair=pair,
                entity_type=entity_type,
                order_source_target_id=target_id,
                order_mention_ids_by_side=order_mention_ids_by_side,
                literal_nodes=literal_nodes,
                authority_nodes=authority_nodes,
                proposed_target={"target_id": target_id, "target_label": catalog["label"], "target_metadata": catalog},
            ))

        for target_id, sides in literal_targets.items():
            if not all(museum in sides for museum in pair):
                continue
            mention_ids_by_side = mention_ids_for_sides(sides, pair)
            authority_by_side = target_sets_by_side(mention_ids_by_side, authority_rows)
            if common_target(authority_by_side, pair):
                continue
            entity_types = {link["entity_type"] for museum in pair for link in sides[museum]}
            if len(entity_types) != 1:
                raise ValueError(f"one literal target crosses entity types: {target_id}")
            literal_nodes = [arm_node(target_id, mention_ids_by_side, mentions)]
            candidates.append(make_candidate(
                transition_class="literal_only_transition",
                pair=pair,
                entity_type=entity_types.pop(),
                order_source_target_id=target_id,
                order_mention_ids_by_side=mention_ids_by_side,
                literal_nodes=literal_nodes,
                authority_nodes=[],
                proposed_target=None,
            ))

    candidates.sort(key=lambda candidate: hashlib.sha256(
        (OPAQUE_ORDER_SEED + candidate["opaque_order_binding_sha256"]).encode("utf-8")
    ).hexdigest())
    expected = expected_counts_from_report(report)
    observed: dict[str, dict[str, int]] = {
        transition_class: {"__".join(pair): 0 for pair in PAIRS}
        for transition_class in expected
    }
    for candidate in candidates:
        observed[candidate["hidden_binding"]["transition_class"]][
            "__".join(candidate["hidden_binding"]["museum_pair"])
        ] += 1
    if observed != expected:
        raise ValueError(f"review population is not exhaustive against report: {observed} != {expected}")
    inputs = {
        "review_population_builder_sha256": sha256_path(Path(__file__)),
        "run_manifest_sha256": sha256_path(run / "run-manifest.json"),
        "mention_ledger_sha256": run_manifest["inputs"]["mention_ledger"]["gzip_sha256"],
        "literal_arm_sha256": sha256_path(run / "typed-literal-arm.ndjson.gz"),
        "authority_arm_sha256": sha256_path(run / "current-authority-arm.ndjson.gz"),
        "literal_links_sha256": sha256_path(run / "typed-literal-links.ndjson.gz"),
        "authority_links_sha256": sha256_path(run / "current-authority-links.ndjson.gz"),
        "report_sha256": sha256_path(run / "report.json"),
    }
    return candidates, {"expected": expected, "observed": observed}, inputs, mentions, literal_rows


def recursive_forbidden_keys(
    value, path: str = "$", forbidden_keys: set[str] = STAGE_1_FORBIDDEN_KEYS
) -> list[str]:
    findings = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in forbidden_keys:
                findings.append(child_path)
            findings.extend(recursive_forbidden_keys(child, child_path, forbidden_keys))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(recursive_forbidden_keys(child, f"{path}[{index}]", forbidden_keys))
    return findings


def stage_1_evidence(case: dict) -> dict:
    return {
        "museum_pair": case["museum_pair"],
        "entity_type": case["entity_type"],
        "sides": case["sides"],
    }


def evidence_sufficiency_failures(evidence: dict) -> list[str]:
    failures = []
    pair = evidence.get("museum_pair")
    sides = evidence.get("sides")
    if not isinstance(pair, list) or len(pair) != 2 or len(set(pair)) != 2:
        return ["museum_pair"]
    if not isinstance(sides, dict) or set(sides) != set(pair):
        return ["sides"]
    for museum in pair:
        groups = sides[museum]
        if not isinstance(groups, list) or not groups:
            failures.append(f"sides.{museum}")
            continue
        for index, group in enumerate(groups):
            prefix = f"sides.{museum}[{index}]"
            variants = group.get("exact_mention_variants")
            if not isinstance(variants, dict) or not variants:
                failures.append(f"{prefix}.exact_mention_variants")
            if not isinstance(group.get("representative_exact_mention"), str) or not group[
                "representative_exact_mention"
            ].strip():
                failures.append(f"{prefix}.representative_exact_mention")
            if not isinstance(group.get("mention_count"), int) or group["mention_count"] <= 0:
                failures.append(f"{prefix}.mention_count")
            elif isinstance(variants, dict) and sum(variants.values()) != group["mention_count"]:
                failures.append(f"{prefix}.mention_count_vs_variants")
            if not isinstance(group.get("distinct_record_count"), int) or not (
                0 < group["distinct_record_count"] <= group.get("mention_count", 0)
            ):
                failures.append(f"{prefix}.distinct_record_count")
            for key in ("field_paths", "evidence_roles"):
                values = group.get(key)
                if not isinstance(values, list) or not values or not all(
                    isinstance(value, str) and value for value in values
                ):
                    failures.append(f"{prefix}.{key}")
    return failures


def stage_2_release_readiness(stage_1: dict, custodian: dict) -> dict:
    stage_1_cases = stage_1.get("cases", [])
    custodian_cases = custodian.get("cases", [])
    stage_1_ids = [case.get("case_id") for case in stage_1_cases]
    custodian_ids = [case.get("case_id") for case in custodian_cases]
    duplicate_stage_1_ids = len(stage_1_ids) - len(set(stage_1_ids))
    duplicate_custodian_ids = len(custodian_ids) - len(set(custodian_ids))
    stage_1_by_id = {case["case_id"]: case for case in stage_1_cases}
    custodian_by_id = {case["case_id"]: case for case in custodian_cases}
    missing_review_unit_count = 0
    evidence_hash_mismatches = 0
    recomputed_evidence_hash_mismatches = 0
    insufficient_evidence_case_count = 0
    release_candidate_count = 0
    for custodian_case in custodian_cases:
        review_unit_id = custodian_case.get("stage_1_review_unit_id")
        stage_1_case = stage_1_by_id.get(review_unit_id)
        if stage_1_case is None:
            missing_review_unit_count += 1
            continue
        release_candidate_count += 1
        evidence = stage_1_evidence(stage_1_case)
        if custodian_case.get("evidence_sha256") != stage_1_case.get("evidence_sha256"):
            evidence_hash_mismatches += 1
        if canonical_sha256(evidence) != stage_1_case.get("evidence_sha256"):
            recomputed_evidence_hash_mismatches += 1
        if evidence_sufficiency_failures(evidence):
            insufficient_evidence_case_count += 1
    result = {
        "stage_1_duplicate_case_ids": duplicate_stage_1_ids,
        "custodian_duplicate_case_ids": duplicate_custodian_ids,
        "missing_review_unit_count": missing_review_unit_count,
        "release_candidate_count": release_candidate_count,
        "evidence_hash_mismatches": evidence_hash_mismatches,
        "recomputed_evidence_hash_mismatches": recomputed_evidence_hash_mismatches,
        "insufficient_evidence_case_count": insufficient_evidence_case_count,
    }
    result["passed"] = all(value == 0 for key, value in result.items() if key != "release_candidate_count")
    return result


def stage_1_blinding_check(stage_1: dict, answer_key: dict) -> dict:
    forbidden_keys = recursive_forbidden_keys(stage_1)
    encoded = canonical_bytes(stage_1)
    private_identifiers = set()
    for case in answer_key["cases"]:
        if case["proposed_target_id"]:
            private_identifiers.add(case["proposed_target_id"])
        for arm in case["arm_native"].values():
            for node in arm["nodes"]:
                private_identifiers.add(node["target_id"])
                for ids in node["mention_ids_by_side"].values():
                    private_identifiers.update(ids)
                for ids in node["artifact_ids_by_side"].values():
                    private_identifiers.update(ids)
    leaked_identifiers = sorted(identifier for identifier in private_identifiers if identifier.encode("utf-8") in encoded)
    evidence_mismatches = sum(
        canonical_sha256({
            "museum_pair": case["museum_pair"],
            "entity_type": case["entity_type"],
            "sides": case["sides"],
        }) != case["evidence_sha256"]
        for case in stage_1["cases"]
    )
    cross_side_group_token_matches = 0
    non_singleton_side_evidence_blocks = 0
    structure_signatures = set()
    malformed_evidence_block_schemas = 0
    expected_block_keys = {
        "evidence_group", "representative_exact_mention", "exact_mention_variants",
        "mention_count", "distinct_record_count", "field_paths", "evidence_roles",
    }
    for case in stage_1["cases"]:
        pair = case["museum_pair"]
        groups = {
            museum: {group["evidence_group"] for group in case["sides"][museum]}
            for museum in pair
        }
        cross_side_group_token_matches += len(groups[pair[0]] & groups[pair[1]])
        non_singleton_side_evidence_blocks += sum(
            len(case["sides"][museum]) != 1 for museum in pair
        )
        block_key_shapes = tuple(
            tuple(sorted(group))
            for museum in pair
            for group in case["sides"][museum]
        )
        malformed_evidence_block_schemas += sum(
            set(group) != expected_block_keys
            for museum in pair
            for group in case["sides"][museum]
        )
        structure_signatures.add((
            len(pair), tuple(len(case["sides"][museum]) for museum in pair),
            block_key_shapes,
        ))
    return {
        "forbidden_key_occurrences": len(forbidden_keys),
        "private_identifier_occurrences": len(leaked_identifiers),
        "evidence_hash_mismatches": evidence_mismatches,
        "cross_side_group_token_matches": cross_side_group_token_matches,
        "non_singleton_side_evidence_blocks": non_singleton_side_evidence_blocks,
        "distinct_visible_structure_signatures": len(structure_signatures),
        "malformed_evidence_block_schemas": malformed_evidence_block_schemas,
        "passed": (
            not forbidden_keys
            and not leaked_identifiers
            and evidence_mismatches == 0
            and cross_side_group_token_matches == 0
            and non_singleton_side_evidence_blocks == 0
            and len(structure_signatures) == 1
            and malformed_evidence_block_schemas == 0
        ),
    }


def arm_native_inventory(answer_cases: list[dict]) -> dict:
    per_pair = {}
    for pair in PAIRS:
        pair_key = "__".join(pair)
        cases = [case for case in answer_cases if tuple(case["museum_pair"]) == pair]
        per_pair[pair_key] = {
            arm: sum(len(case["arm_native"][arm]["nodes"]) for case in cases)
            for arm in ("literal", "authority")
        }
    controls = [
        case for case in answer_cases if case["transition_class"] == "retained_control"
    ]
    mismatched_controls = 0
    multi_literal_controls = 0
    distinct_accounting_controls = 0
    mismatched_bindings = []
    multi_literal_bindings = []
    distinct_accounting_bindings = []
    for case in controls:
        multi_literal = len(case["arm_native"]["literal"]["nodes"]) != 1
        multi_literal_controls += multi_literal
        mismatch = False
        for museum in case["museum_pair"]:
            literal_records = {
                artifact_id
                for node in case["arm_native"]["literal"]["nodes"]
                for artifact_id in node["artifact_ids_by_side"][museum]
            }
            authority_records = {
                artifact_id
                for node in case["arm_native"]["authority"]["nodes"]
                for artifact_id in node["artifact_ids_by_side"][museum]
            }
            mismatch = mismatch or literal_records != authority_records
        mismatched_controls += mismatch
        distinct_accounting_controls += mismatch or multi_literal
        if mismatch:
            mismatched_bindings.append(case["case_binding_sha256"])
        if multi_literal:
            multi_literal_bindings.append(case["case_binding_sha256"])
        if mismatch or multi_literal:
            distinct_accounting_bindings.append(case["case_binding_sha256"])
    return {
        "shared_node_cases_by_arm": {
            arm: sum(values[arm] for values in per_pair.values())
            for arm in ("literal", "authority")
        },
        "shared_node_cases_by_pair_and_arm": per_pair,
        "retained_authority_control_cases": len(controls),
        "literal_nodes_represented_by_retained_controls": sum(
            len(case["arm_native"]["literal"]["nodes"]) for case in controls
        ),
        "retained_controls_with_different_arm_native_record_membership": mismatched_controls,
        "retained_controls_with_multiple_literal_nodes": multi_literal_controls,
        "retained_controls_requiring_distinct_arm_native_accounting": (
            distinct_accounting_controls
        ),
        "different_membership_case_binding_set_sha256": canonical_sha256(
            sorted(mismatched_bindings)
        ),
        "multiple_literal_case_binding_set_sha256": canonical_sha256(
            sorted(multi_literal_bindings)
        ),
        "distinct_accounting_case_binding_set_sha256": canonical_sha256(
            sorted(distinct_accounting_bindings)
        ),
    }


def build(repo_root: Path, run: Path, out: Path, public_digest: Path | None = None) -> dict:
    candidates, exhaustive, inputs, mentions, literal_rows = derive_candidates(repo_root, run)
    protocol_inputs = review_protocol_inputs(repo_root)
    review_units_by_binding: dict[str, dict] = {}
    for candidate in candidates:
        hidden = candidate["hidden_binding"]
        for arm in ("literal", "authority"):
            for node in hidden["arm_native"][arm]["nodes"]:
                binding = review_unit_binding(
                    hidden["museum_pair"], hidden["entity_type"], node
                )
                binding_sha = canonical_sha256(binding)
                evidence = review_unit_evidence(binding, mentions, literal_rows)
                value = {
                    "binding_sha256": binding_sha,
                    "evidence": evidence,
                    "evidence_sha256": canonical_sha256(evidence),
                }
                existing = review_units_by_binding.setdefault(binding_sha, value)
                if existing != value:
                    raise ValueError("Stage 1 review-unit hash collision")

    review_units = sorted(
        review_units_by_binding.values(),
        key=lambda unit: hashlib.sha256(
            f"{OPAQUE_ORDER_SEED}|review-unit|{unit['binding_sha256']}".encode("utf-8")
        ).hexdigest(),
    )
    review_unit_id_by_binding = {
        unit["binding_sha256"]: f"review-unit-{index:03d}"
        for index, unit in enumerate(review_units, 1)
    }
    stage_1_cases = [
        {
            "case_id": review_unit_id_by_binding[unit["binding_sha256"]],
            "evidence_sha256": unit["evidence_sha256"],
            **unit["evidence"],
            "questions": {
                "same_entity": {
                    "prompt": "Do the two museum-side evidence groups refer to the same entity?",
                    "allowed_outcomes": list(SAME_ENTITY_OUTCOMES),
                },
                "useful_granularity": {
                    "prompt": "Is the shared identity, if any, useful at this entity type and granularity?",
                    "allowed_outcomes": list(USEFUL_GRANULARITY_OUTCOMES),
                },
            },
        }
        for unit in review_units
    ]
    stage_2_cases = []
    answer_cases = []
    manifest_cases = []
    for index, candidate in enumerate(candidates, 1):
        case_id = f"case-{index:03d}"
        binding = json.loads(json.dumps(candidate["hidden_binding"]))
        for arm in ("literal", "authority"):
            for node in binding["arm_native"][arm]["nodes"]:
                unit_binding = review_unit_binding(
                    binding["museum_pair"], binding["entity_type"], node
                )
                unit = review_units_by_binding[canonical_sha256(unit_binding)]
                node["stage_1_review_unit_id"] = review_unit_id_by_binding[
                    unit["binding_sha256"]
                ]
                node["stage_1_evidence_sha256"] = unit["evidence_sha256"]
        case_binding_sha256 = canonical_sha256(binding)
        proposed = candidate["proposed_target"]
        if proposed:
            authority_node = binding["arm_native"]["authority"]["nodes"][0]
            stage_2_cases.append({
                "case_id": case_id,
                "stage_1_review_unit_id": authority_node["stage_1_review_unit_id"],
                "evidence_sha256": authority_node["stage_1_evidence_sha256"],
                "proposed_target": proposed,
                "question": (
                    "Does this proposed canonical target denote the exact identity represented "
                    "by the museum-side evidence?"
                ),
                "allowed_outcomes": list(CANONICAL_IDENTITY_OUTCOMES),
            })
        answer_cases.append({
            "case_id": case_id,
            "case_binding_sha256": case_binding_sha256,
            **binding,
        })
        manifest_cases.append({
            "case_id": case_id,
            "transition_class": binding["transition_class"],
            "museum_pair": binding["museum_pair"],
            "entity_type": binding["entity_type"],
            "case_binding_sha256": case_binding_sha256,
            "stage_2_has_proposed_target": proposed is not None,
            "arm_native_node_counts": {
                arm: len(binding["arm_native"][arm]["nodes"])
                for arm in ("literal", "authority")
            },
            "stage_1_review_unit_ids_by_arm": {
                arm: [
                    node["stage_1_review_unit_id"]
                    for node in binding["arm_native"][arm]["nodes"]
                ]
                for arm in ("literal", "authority")
            },
        })

    stage_1 = {
        "schema_version": "hapi-authority-independent-control-stage-1-review/5",
        "review_protocol": {
            "role": "stage_1_reviewer",
            "prompt_sha256": protocol_inputs["prompts"]["stage_1_reviewer"]["sha256"],
            "artifact_schema_sha256": protocol_inputs["artifact_schema"]["sha256"],
            "raw_response_contract_sha256": protocol_inputs["raw_response_contracts"][
                "stage_1_reviewer"
            ]["sha256"],
        },
        "task": (
            "Judge each independently shuffled museum-side census unit without "
            "consulting a proposed canonical target."
        ),
        "instructions": {
            "same_entity": "Judge whether the two sides denote the same entity.",
            "useful_granularity": "Separately judge whether that identity is useful at the stated type and granularity.",
            "freeze_requirement": "Submit and freeze every Stage 1 judgment before receiving Stage 2.",
        },
        "cases": stage_1_cases,
    }
    stage_2 = {
        "schema_version": "hapi-authority-independent-control-stage-2-custodian/5",
        "review_protocol": {
            "role": "stage_2_reviewer",
            "prompt_sha256": protocol_inputs["prompts"]["stage_2_reviewer"]["sha256"],
            "artifact_schema_sha256": protocol_inputs["artifact_schema"]["sha256"],
            "raw_response_contract_sha256": protocol_inputs["raw_response_contracts"][
                "stage_2_reviewer"
            ]["sha256"],
        },
        "warning": "Custodian-only until a complete Stage 1 decision file has been frozen and hash-bound.",
        "cases": stage_2_cases,
    }
    answer_key = {
        "schema_version": "hapi-authority-independent-control-private-answer-key/5",
        "warning": "Keep separate from reviewers through both stages.",
        "cases": answer_cases,
    }

    blinding = stage_1_blinding_check(stage_1, answer_key)
    stage_2_readiness = stage_2_release_readiness(stage_1, stage_2)
    transition_count = sum(
        1 for case in manifest_cases if case["transition_class"].endswith("_transition")
    )
    control_count = sum(1 for case in manifest_cases if case["transition_class"] == "retained_control")
    controls = {
        "transition_case_count": transition_count,
        "retained_control_count": control_count,
        "required_control_ratio_numerator": CONTROL_RATIO_NUMERATOR,
        "required_control_ratio_denominator": CONTROL_RATIO_DENOMINATOR,
        "coverage_ratio_passed": (
            control_count * CONTROL_RATIO_DENOMINATOR
            >= transition_count * CONTROL_RATIO_NUMERATOR
        ),
    }
    exhaustive_check = {
        "expected_counts": exhaustive["expected"],
        "observed_counts": exhaustive["observed"],
        "passed": exhaustive["expected"] == exhaustive["observed"],
    }
    if not blinding["passed"]:
        raise ValueError(f"Stage 1 blinding check failed: {blinding}")
    if not stage_2_readiness["passed"]:
        raise ValueError(f"Stage 2 release evidence is not ready: {stage_2_readiness}")
    if not controls["coverage_ratio_passed"]:
        raise ValueError(f"retained control frame is unexpectedly small: {controls}")
    if not exhaustive_check["passed"]:
        raise ValueError("transition population is not exhaustive against the report")

    counts_by_class = dict(sorted(collections.Counter(
        case["transition_class"] for case in manifest_cases
    ).items()))
    counts_by_pair = {
        pair_key: dict(sorted(collections.Counter(
            case["transition_class"]
            for case in manifest_cases
            if "__".join(case["museum_pair"]) == pair_key
        ).items()))
        for pair_key in ("__".join(pair) for pair in PAIRS)
    }
    counts_by_entity_type = dict(sorted(collections.Counter(
        case["entity_type"] for case in manifest_cases
    ).items()))
    native_inventory = arm_native_inventory(answer_cases)

    out.mkdir(parents=True, exist_ok=True)
    stage_1_path = out / "stage-1-queue.json"
    stage_2_path = out / "stage-2-custodian.json"
    answer_path = out / "private-answer-key.json"
    manifest_path = out / "review-population-manifest.json"
    digest_path = out / "public-review-population-digest.json"
    protocol_path = out / "review-protocol-manifest.json"
    write_json(stage_1_path, stage_1)
    write_json(stage_2_path, stage_2)
    write_json(answer_path, answer_key)
    review_protocol_manifest = {
        "schema_version": "hapi-authority-control-review-protocol-manifest/3",
        "evaluation_date": "2026-09-13",
        "review_status": "NOT_RUN",
        "quality_conclusion_status": "NOT_AVAILABLE",
        "reason": (
            "Review is blocked: no genuine immutable provider snapshot is exposed for "
            "gpt-5.6-sol and no authorized direct Responses API credential is available."
        ),
        "runtime_readiness": {
            "status": "BLOCKED",
            "blocker": "missing_genuine_immutable_provider_snapshot_and_authorized_api_path",
        },
        "valid_review_artifact_count": 0,
        "protocol_inputs": protocol_inputs,
        "queue_inputs": {
            "stage_1_queue_sha256": sha256_path(stage_1_path),
            "stage_2_custodian_sha256": sha256_path(stage_2_path),
        },
        "required_sequence": [
            "satisfy_provider_snapshot_and_explicit_launcher_gate",
            "audit_stage_1_reviewer_composed_input",
            "run_two_stage_1_reviewers",
            "audit_stage_1_reconciler_composed_input",
            "run_stage_1_reconciler_with_explicit_cited_overrides",
            "release_stage_2_through_official_gate",
            "audit_stage_2_reviewer_composed_input",
            "run_two_stage_2_reviewers",
            "audit_stage_2_reconciler_composed_input",
            "run_stage_2_reconciler_with_explicit_cited_overrides",
            "score",
        ],
    }
    write_json(protocol_path, review_protocol_manifest)
    private_manifest = {
        "schema_version": "hapi-authority-independent-control-private-review-population/5",
        "opaque_order_seed_sha256": hashlib.sha256(OPAQUE_ORDER_SEED.encode("utf-8")).hexdigest(),
        "input_hashes": inputs,
        "population_counts": {
            "total": len(manifest_cases),
            "stage_1_arm_native_review_units": len(stage_1_cases),
            "by_class": counts_by_class,
            "by_pair_and_class": counts_by_pair,
            "by_entity_type": counts_by_entity_type,
        },
        "executable_checks": {
            "transition_exhaustiveness": exhaustive_check,
            "stage_1_blinding": blinding,
            "stage_2_release_readiness": stage_2_readiness,
            "retained_control_frame": controls,
        },
        "cases": manifest_cases,
        "output_hashes": {
            "stage_1_queue_sha256": sha256_path(stage_1_path),
            "stage_2_custodian_sha256": sha256_path(stage_2_path),
            "private_answer_key_sha256": sha256_path(answer_path),
            "review_protocol_manifest_sha256": sha256_path(protocol_path),
        },
    }
    write_json(manifest_path, private_manifest)
    public = {
        "schema_version": "hapi-authority-independent-control-public-review-population-digest/5",
        "input_hashes": {**inputs, "review_protocol": protocol_inputs},
        "review": {
            "status": "NOT_RUN",
            "quality_conclusion_status": "NOT_AVAILABLE",
            "valid_review_artifact_count": 0,
            "protocol_manifest_sha256": sha256_path(protocol_path),
            "runtime_readiness": "BLOCKED",
        },
        "population_counts": private_manifest["population_counts"],
        "arm_native_inventory": native_inventory,
        "executable_check_counts": {
            "transition_expected": exhaustive_check["expected_counts"],
            "transition_observed": exhaustive_check["observed_counts"],
            "stage_1_forbidden_key_occurrences": blinding["forbidden_key_occurrences"],
            "stage_1_private_identifier_occurrences": blinding["private_identifier_occurrences"],
            "stage_1_evidence_hash_mismatches": blinding["evidence_hash_mismatches"],
            "stage_1_cross_side_group_token_matches": blinding[
                "cross_side_group_token_matches"
            ],
            "stage_1_non_singleton_side_evidence_blocks": blinding[
                "non_singleton_side_evidence_blocks"
            ],
            "stage_1_distinct_visible_structure_signatures": blinding[
                "distinct_visible_structure_signatures"
            ],
            "stage_1_malformed_evidence_block_schemas": blinding[
                "malformed_evidence_block_schemas"
            ],
            "stage_2_release_candidate_cases": stage_2_readiness["release_candidate_count"],
            "stage_2_stage_1_duplicate_case_ids": stage_2_readiness[
                "stage_1_duplicate_case_ids"
            ],
            "stage_2_custodian_duplicate_case_ids": stage_2_readiness[
                "custodian_duplicate_case_ids"
            ],
            "stage_2_missing_stage_1_review_units": stage_2_readiness[
                "missing_review_unit_count"
            ],
            "stage_2_evidence_hash_mismatches": stage_2_readiness["evidence_hash_mismatches"],
            "stage_2_recomputed_evidence_hash_mismatches": stage_2_readiness[
                "recomputed_evidence_hash_mismatches"
            ],
            "stage_2_insufficient_evidence_cases": stage_2_readiness[
                "insufficient_evidence_case_count"
            ],
            "transition_cases": transition_count,
            "retained_controls": control_count,
            "required_controls_numerator": transition_count * CONTROL_RATIO_NUMERATOR,
            "actual_controls_numerator": control_count * CONTROL_RATIO_DENOMINATOR,
        },
        "output_hashes": {
            **private_manifest["output_hashes"],
            "private_population_manifest_sha256": sha256_path(manifest_path),
        },
    }
    write_json(digest_path, public)
    if public_digest is not None:
        write_json(public_digest, public)
    return public


def release_stage_2(
    repo_root: Path,
    stage_1_path: Path,
    custodian_path: Path,
    reviewer_paths: list[Path],
    reviewer_prompt_audit_path: Path,
    consensus_path: Path,
    reconciler_prompt_audit_path: Path,
    out_path: Path,
) -> dict:
    stage_1 = read_json(stage_1_path)
    custodian = read_json(custodian_path)
    protocol = load_review_protocol_module(repo_root)
    consensus = protocol.validate_consensus_package(
        consensus_path,
        stage_1_path,
        repo_root / PROMPT_PATHS["stage_1_reviewer"],
        reviewer_prompt_audit_path,
        reviewer_paths,
        repo_root / PROMPT_PATHS["stage_1_reconciler"],
        reconciler_prompt_audit_path,
        repo_root / PROMPT_PATHS["prompt_auditor"],
        "1",
    )
    readiness = stage_2_release_readiness(stage_1, custodian)
    if not readiness["passed"]:
        raise ValueError(f"Stage 2 release evidence contract failed: {readiness}")
    expected = {case["case_id"]: case for case in stage_1["cases"]}
    supplied = consensus["decisions"]
    supplied_ids = [decision.get("case_id") for decision in supplied]
    if len(supplied_ids) != len(set(supplied_ids)):
        raise ValueError("Stage 1 decisions contain duplicate case IDs")
    if set(supplied_ids) != set(expected):
        raise ValueError("Stage 1 decisions must cover every Stage 1 case exactly once")
    for decision in supplied:
        case = expected[decision["case_id"]]
        if decision.get("evidence_sha256") != case["evidence_sha256"]:
            raise ValueError(f"Stage 1 evidence hash mismatch: {decision['case_id']}")
        if decision.get("same_entity") not in SAME_ENTITY_OUTCOMES:
            raise ValueError(f"invalid same-entity outcome: {decision['case_id']}")
        if decision.get("useful_granularity") not in USEFUL_GRANULARITY_OUTCOMES:
            raise ValueError(f"invalid useful-granularity outcome: {decision['case_id']}")

    released_cases = []
    for custodian_case in custodian["cases"]:
        case_id = custodian_case["case_id"]
        review_unit_id = custodian_case["stage_1_review_unit_id"]
        stage_1_case = expected[review_unit_id]
        evidence = stage_1_evidence(stage_1_case)
        released_cases.append({
            "case_id": case_id,
            "evidence_sha256": stage_1_case["evidence_sha256"],
            **evidence,
            "proposed_target": custodian_case["proposed_target"],
            "question": custodian_case["question"],
            "allowed_outcomes": custodian_case["allowed_outcomes"],
        })
    released = {
        "schema_version": "hapi-authority-independent-control-stage-2-review/6",
        "stage_1_queue_sha256": sha256_path(stage_1_path),
        "frozen_stage_1_consensus_sha256": sha256_path(consensus_path),
        "stage_1_source_review_sha256": sorted(sha256_path(path) for path in reviewer_paths),
        "stage_1_reviewer_prompt_audit_sha256": sha256_path(reviewer_prompt_audit_path),
        "stage_1_reconciler_prompt_audit_sha256": sha256_path(reconciler_prompt_audit_path),
        "stage_2_custodian_sha256": sha256_path(custodian_path),
        "review_protocol": custodian["review_protocol"],
        "task": "Judge whether each proposed canonical target is the exact identity represented by the included museum-side evidence, not merely a containing, adjacent, diachronically associated, or broader place.",
        "cases": released_cases,
    }
    forbidden = recursive_forbidden_keys(released, forbidden_keys=STAGE_2_FORBIDDEN_KEYS)
    if forbidden:
        raise ValueError(f"Stage 2 release contains forbidden private/class fields: {forbidden}")
    if len(released_cases) != readiness["release_candidate_count"]:
        raise ValueError("Stage 2 released case count changed after readiness validation")
    write_json(out_path, released)
    return released


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--repo-root", type=Path, required=True)
    build_parser.add_argument("--run", type=Path, required=True)
    build_parser.add_argument("--out", type=Path, required=True)
    build_parser.add_argument("--public-digest", type=Path)
    release_parser = subparsers.add_parser("release-stage-2")
    release_parser.add_argument("--repo-root", type=Path, required=True)
    release_parser.add_argument("--stage-1-queue", type=Path, required=True)
    release_parser.add_argument("--stage-2-custodian", type=Path, required=True)
    release_parser.add_argument("--stage-1-review", type=Path, action="append", required=True)
    release_parser.add_argument("--stage-1-reviewer-prompt-audit", type=Path, required=True)
    release_parser.add_argument("--stage-1-consensus", type=Path, required=True)
    release_parser.add_argument("--stage-1-reconciler-prompt-audit", type=Path, required=True)
    release_parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build":
        result = build(args.repo_root.resolve(), args.run, args.out, args.public_digest)
    else:
        result = release_stage_2(
            args.repo_root.resolve(), args.stage_1_queue, args.stage_2_custodian,
            args.stage_1_review, args.stage_1_reviewer_prompt_audit,
            args.stage_1_consensus, args.stage_1_reconciler_prompt_audit, args.out,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
