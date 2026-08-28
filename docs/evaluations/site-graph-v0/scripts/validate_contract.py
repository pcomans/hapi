#!/usr/bin/env python3
"""Read-only release authentication and real-private-corpus semantic validation."""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from build_baseline import (
    build_metrics,
    build_opportunity_queue,
    canonical_json_sha256,
    classify_current_nodes,
    read_gzip_jsonl,
    read_jsonl,
)
from compare_candidate import (
    AMBIGUITY_MAXIMUM_INCREASE,
    CONCENTRATION_MAXIMUM_INCREASE,
    MINIMUM_AFFECTED_FRACTION,
    MINIMUM_GAINED_IDENTITIES,
    REVIEWS_PER_CREDITED_DECISION,
)
from contract_constants import OPPORTUNITY_MUSEUM_PROTECTION, OPPORTUNITY_TOTAL_SIGNATURES
from integrity import IntegrityError, sha256, verify_release
from private_ledgers import verify_private_ledgers, verify_public_boundary
from schema_validation import validate_schema


PUBLIC_BASELINE_OUTPUTS = (
    "baseline-metrics.json",
    "baseline-node-scope.json",
    "planned-opportunity-summary.json",
    "private-ledger-digests.json",
    "top-unmatched-components.json",
)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_file(path: Path, expected: dict) -> dict:
    actual = {
        "exists": path.is_file(),
        "bytes": path.stat().st_size if path.is_file() else None,
        "sha256": sha256(path) if path.is_file() else None,
    }
    actual["passed"] = (
        actual["exists"]
        and actual["bytes"] == expected["bytes"]
        and actual["sha256"] == expected["sha256"]
    )
    return actual


def semantic_report(repo_root: Path, corpus: Path, private_run: Path) -> dict:
    root = repo_root / "docs/evaluations/site-graph-v0"
    snapshot = read_json(root / "input-snapshot.json")
    prereg = read_json(root / "preregistration.json")
    metrics = read_json(root / "baseline-metrics.json")
    node_scope = read_json(root / "baseline-node-scope.json")
    opportunity_summary = read_json(root / "planned-opportunity-summary.json")
    top_components = read_json(root / "top-unmatched-components.json")
    private_digests = read_json(root / "private-ledger-digests.json")
    reruns = read_json(root / "baseline-rerun-evidence.json")
    crosswalk = read_json(root / "type-crosswalk.json")
    checks: list[dict] = []

    def check(check_id: str, passed: bool, evidence: object) -> None:
        checks.append({"check_id": check_id, "passed": bool(passed), "evidence": evidence})

    frozen_inputs = {}
    for relative, expected in snapshot["corpus"]["files"].items():
        frozen_inputs[f"external-private/{relative}"] = verify_file(corpus / relative, expected)
    for group in ("extractor_and_matcher", "current_authority"):
        for relative, expected in snapshot[group]["files"].items():
            frozen_inputs[relative] = verify_file(repo_root / relative, expected)
    check(
        "frozen_input_bytes",
        all(item["passed"] for item in frozen_inputs.values()),
        frozen_inputs,
    )

    private_authentication = verify_private_ledgers(private_run, root)
    check(
        "external_private_input_verified",
        private_digests["external_private_input"]["status"]
        == "external_private_input_verified"
        and private_authentication["private_record_count"]
        == snapshot["corpus"]["canonical_record_count"],
        {
            **private_authentication,
            "canonical_transport_sha256": private_digests["external_private_input"][
                "canonical_artifact_transport_gzip_sha256"
            ],
            "generator_history": "not_available_in_handoff",
        },
    )
    check("public_data_boundary", True, verify_public_boundary(root))

    canonical = read_gzip_jsonl(corpus / "data/artifacts.ndjson.gz")
    canonical_by_id = {row["id"]: row for row in canonical}
    records = read_gzip_jsonl(private_run / "private-record-evidence.ndjson.gz")
    record_by_id = {row["artifact_id"]: row for row in records}
    canonical_counts = dict(
        sorted(collections.Counter(row["source_museum"] for row in canonical).items())
    )
    record_counts = dict(sorted(collections.Counter(row["museum"] for row in records).items()))
    aligned = (
        len(canonical_by_id) == len(canonical)
        and len(record_by_id) == len(records)
        and set(canonical_by_id) == set(record_by_id)
        and all(
            canonical_by_id[artifact_id]["source_museum"] == record_by_id[artifact_id]["museum"]
            for artifact_id in record_by_id
        )
    )
    check(
        "canonical_population_and_private_record_alignment",
        len(records) == snapshot["corpus"]["canonical_record_count"]
        and canonical_counts == snapshot["corpus"]["records_by_museum"]
        and record_counts == snapshot["corpus"]["records_by_museum"]
        and aligned,
        {
            "canonical_records": len(canonical),
            "private_records": len(records),
            "records_by_museum": record_counts,
            "artifact_and_museum_alignment": aligned,
        },
    )

    idai_rows = read_jsonl(
        repo_root / "pipeline/pipeline/authority/sources/idai-gazetteer/reconciled.jsonl"
    )
    raw_hierarchy = read_json(
        repo_root / "pipeline/pipeline/authority/sources/idai-gazetteer/raw.json"
    )
    expected_targets = snapshot["current_authority"]["site_snapshot"]["site_target_count"]
    recomputed_nodes, scope_by_target, hierarchy_summary = classify_current_nodes(
        idai_rows, raw_hierarchy, crosswalk, expected_targets
    )
    expected_node_scope = {
        "schema_version": "site-graph-v0-baseline-node-scope/2",
        "hierarchy_context": hierarchy_summary,
        "nodes": recomputed_nodes,
    }
    filtered_parent_missing = sum(
        row.get("kind") == "site" and row.get("parent_id") and not row.get("parent_in_file")
        for row in idai_rows
    )
    check(
        "node_scope_recomputed_from_crosswalk_and_complete_available_hierarchy",
        node_scope == expected_node_scope,
        {
            "scope_counts": dict(
                sorted(collections.Counter(row["scope_class"] for row in recomputed_nodes).items())
            ),
            "filtered_1000_parent_outside_filtered_set": filtered_parent_missing,
            "raw_2075_parent_reference_outside_raw_set": hierarchy_summary[
                "raw_records_with_parent_outside_available_hierarchy"
            ],
            "measure_explanation": (
                "566 counts filtered targets whose parent is absent from the filtered 1,000; "
                "699 counts raw records whose parent reference is absent from all 2,075 available raw records."
            ),
        },
    )

    site_links = [
        {"artifact_id": row["artifact_id"], "museum": row["museum"], "target_id": target}
        for row in records
        for target in row["baseline_site_target_ids"]
    ]
    source_rows = read_gzip_jsonl(private_run / "private-opportunity-source.ndjson.gz")
    actual_private_opportunity = read_json(private_run / "private-opportunity-ledger.json")
    evidence_counts = collections.Counter(
        row["museum"] for row in records if row["extracted_site_text_evidence"]
    )
    regenerated_summary, regenerated_private, regenerated_top = build_opportunity_queue(
        source_rows,
        records,
        site_links,
        scope_by_target,
        dict(collections.Counter(row["museum"] for row in records)),
        dict(evidence_counts),
    )
    regenerated_summary["private_ledger_authentication"] = opportunity_summary[
        "private_ledger_authentication"
    ]
    recomputed_metrics = build_metrics(records, site_links, scope_by_target)
    recomputed_metrics["planned_slice_maximum_measurable_effect"] = {
        "source": "planned-opportunity-summary.json",
        "per_museum": regenerated_summary["per_museum"],
        "pair_side_ceilings": regenerated_summary["pair_side_ceilings"],
        "interpretation": (
            "Numeric intent-to-treat upper bounds, not expected effects or accuracy claims. "
            "Unsupported, broad/administrative, abstained, failed, and disputed research "
            "remains in denominators and earns zero credit."
        ),
    }
    headline_evidence = {
        "per_museum": recomputed_metrics["per_museum"],
        "pair_shared_node_counts": {
            key: value["shared_node_count"]
            for key, value in recomputed_metrics["connectivity"]["pairs"].items()
        },
        "all_three_shared_node_count": recomputed_metrics["connectivity"]["all_three"][
            "shared_node_count"
        ],
        "any_two_or_more_shared_node_count": recomputed_metrics["connectivity"][
            "any_two_or_more"
        ]["shared_node_count"],
    }
    check("headline_metrics_recomputed", metrics == recomputed_metrics, headline_evidence)
    check(
        "intent_to_treat_aggregates_and_private_membership_recomputed",
        opportunity_summary == regenerated_summary
        and top_components == regenerated_top
        and actual_private_opportunity == regenerated_private,
        {
            "selected_signatures": regenerated_summary["selected_signature_count"],
            "per_museum": regenerated_summary["per_museum"],
            "pair_side_ceilings": regenerated_summary["pair_side_ceilings"],
            "private_opportunity_ledger_canonical_sha256": canonical_json_sha256(
                regenerated_private
            ),
        },
    )

    formula_expected = {
        "extracted_site_text_availability": "|X_m| / |A_m|",
        "overall_linkability": "|L_m| / |A_m|",
        "extracted_site_text_conditional_linkability": "|L_m| / |X_m|",
        "blocking_ambiguity": "|{r in X_m: direct targets empty and any site mention ambiguous}| / |X_m|",
        "planned_maximum_overall_effect": "(|new-link-eligible records in O_m| + |broad-only strict-refinement-eligible records in O_m|) / |A_m|",
        "planned_maximum_extracted_site_text_conditional_effect": "(|new-link-eligible records in O_m| + |broad-only strict-refinement-eligible records in O_m|) / |X_m|",
        "pair_side_coverage_overall": "D_(m->n) / |A_m|",
        "pair_side_coverage_extracted_site_text_conditional": "D_(m->n) / |X_m|",
        "top_k_concentration": "|union of museum-side records incident on its top-k shared identity classes| / |union of museum-side records incident on all its shared identity classes|",
        "hhi": "sum_j(I_j^2) / (sum_j I_j)^2",
    }
    actual_formulas = {
        key: prereg["metric_formulas"][key]["expression"] for key in formula_expected
    }
    check("machine_readable_formulas", actual_formulas == formula_expected, actual_formulas)

    machine_expected = {
        "ambiguity_maximum_increase": {
            "numerator": AMBIGUITY_MAXIMUM_INCREASE.numerator,
            "denominator": AMBIGUITY_MAXIMUM_INCREASE.denominator,
        },
        "concentration_maximum_increase": {
            "numerator": CONCENTRATION_MAXIMUM_INCREASE.numerator,
            "denominator": CONCENTRATION_MAXIMUM_INCREASE.denominator,
        },
        "minimum_gained_distinct_specific_identity_classes": MINIMUM_GAINED_IDENTITIES,
        "minimum_affected_opportunity_fraction": {
            "numerator": MINIMUM_AFFECTED_FRACTION.numerator,
            "denominator": MINIMUM_AFFECTED_FRACTION.denominator,
        },
        "minimum_reviews_per_credited_decision": REVIEWS_PER_CREDITED_DECISION,
        "opportunity_museum_protection_signatures": OPPORTUNITY_MUSEUM_PROTECTION,
        "opportunity_total_signatures": OPPORTUNITY_TOTAL_SIGNATURES,
    }
    check(
        "machine_readable_decision_thresholds",
        prereg["machine_thresholds"] == machine_expected
        and opportunity_summary["minimum_affected_opportunity_fraction"]
        == machine_expected["minimum_affected_opportunity_fraction"],
        {"preregistered": prereg["machine_thresholds"], "executable": machine_expected},
    )

    concentration_shape_ok = True
    side_values = {}
    for pair_key, pair in recomputed_metrics["connectivity"]["pairs"].items():
        expected_sides = set(pair_key.split("__"))
        concentration_shape_ok &= set(pair["concentration_by_museum_side"]) == expected_sides
        for museum in expected_sides:
            value = pair["concentration_by_museum_side"][museum]
            concentration_shape_ok &= set(value["top_k_unique_record_concentration"]) == {
                "1",
                "5",
                "10",
            }
        side_values[pair_key] = pair["concentration_by_museum_side"]
    check("per_side_top_k_and_hhi_concentration", concentration_shape_ok, side_values)

    actual_idai_types = sorted(
        {type_name for row in raw_hierarchy for type_name in row.get("types", [])}
    )
    crosswalk_types = sorted(crosswalk["idai_gazetteer_actual_hyphenated_types"])
    check(
        "single_source_type_crosswalk",
        actual_idai_types == crosswalk_types
        and crosswalk["credit_policy"][
            "broad_or_administrative_new_link_improvement_credit"
        ]
        == 0,
        {"actual_idai_types": actual_idai_types, "crosswalk_types": crosswalk_types},
    )

    schema_paths = sorted((root / "schemas").glob("*.schema.json"))
    for schema_path in schema_paths:
        # validate_schema checks the meta-schema before validating the harmless empty object.
        # Instance-bearing schemas are separately exercised below or by comparator tests.
        from jsonschema import Draft202012Validator

        Draft202012Validator.check_schema(read_json(schema_path))
    validate_schema(
        opportunity_summary,
        root / "schemas/opportunity-summary.schema.json",
        "committed opportunity summary",
    )
    validate_schema(
        actual_private_opportunity,
        root / "schemas/private-opportunity-ledger.schema.json",
        "regenerated private opportunity ledger",
    )
    check(
        "all_json_schemas_executed",
        True,
        {"schema_count": len(schema_paths), "schemas": [path.name for path in schema_paths]},
    )

    correction_policy = read_json(root / "correction-policy.json")
    check(
        "immutable_primary_and_private_correction_policy",
        correction_policy["current_primary_corrections_applied"] == 0
        and correction_policy["allowed_operations"]
        == [
            "add_direct_target",
            "remove_direct_target",
            "replace_direct_target",
            "set_site_mention_status_count",
        ],
        correction_policy,
    )

    rerun_hashes = reruns.get("deterministic_output_hashes", {})
    public_match = all(
        rerun_hashes.get(name) == sha256(root / name) for name in PUBLIC_BASELINE_OUTPUTS
    )
    check(
        "authenticated_deterministic_baseline_reproduction",
        reruns.get("schema_version") == "site-graph-v0-baseline-rerun-evidence/3"
        and reruns.get("status") == "pass"
        and reruns.get("terminology") == "deterministic_reproduction_not_statistical_independence"
        and reruns.get("run_a", {}).get("run_id") != reruns.get("run_b", {}).get("run_id")
        and reruns.get("output_mismatches") == {}
        and reruns.get("metadata_mismatches") == {}
        and reruns.get("input_snapshot_sha256") == sha256(root / "input-snapshot.json")
        and reruns.get("runner_sha256") == sha256(root / "scripts/run_baseline.py")
        and reruns.get("builder_sha256") == sha256(root / "scripts/build_baseline.py")
        and public_match,
        {
            "run_a": reruns.get("run_a"),
            "run_b": reruns.get("run_b"),
            "deterministic_output_count": reruns.get("deterministic_output_count"),
            "committed_public_outputs_match": public_match,
        },
    )

    rule = prereg["ordered_decision_rule"]
    review_rules = prereg["review_census"]
    check(
        "ordered_decision_and_review_census",
        rule["precedence"] == ["INVALID", "REDESIGN", "CONTINUE", "STOP"]
        and rule["raw_link_rate_growth_can_satisfy_continue"] is False
        and rule["museum_equality_required"] is False
        and review_rules["reviews_per_decision"] == 2
        and review_rules["held_out_sample_is_pass_gate"] is False
        and review_rules["population_precision_claim_permitted"] is False,
        {"decision_rule": rule, "review_census": review_rules},
    )

    provenance = snapshot["corpus"]["provenance"]
    provenance_bytes_authenticated = (
        sha256(root / "corpus-provenance/bundle-README.md")
        == provenance["verified_bundle_readme_sha256"]
        and sha256(root / "corpus-provenance/manifest.json")
        == provenance["verified_bundle_manifest_sha256"]
        and sha256(root / "corpus-provenance/validation/verify_bundle.sh")
        == provenance["verified_bundle_verifier_sha256"]
        and sha256(root / "corpus-provenance/validation/results.json")
        == provenance["verified_bundle_results_sha256"]
    )
    check(
        "external_handoff_metadata_authenticated",
        provenance_bytes_authenticated
        and "cannot be regenerated bit-for-bit" in provenance["known_reproduction_limit"],
        {
            "external_private_prerequisite": "verified",
            "historical_export_reproducible": False,
            "known_reproduction_limit": provenance["known_reproduction_limit"],
        },
    )

    round_1 = read_json(root / "reviews/round-1/metadata.json")
    round_2 = read_json(root / "reviews/round-2/metadata.json")
    round_2_disposition = read_json(root / "reviews/round-2/disposition.json")
    review_ok = (
        sha256(root / "reviews/round-1/prompt.md")
        == round_1["raw_artifacts"]["prompt"]["sha256"]
        and sha256(root / "reviews/round-1/raw-output.txt")
        == round_1["raw_artifacts"]["output"]["sha256"]
        and sha256(root / "reviews/round-2/prompt.md")
        == round_2["artifacts"]["prompt.md"]["sha256"]
        and sha256(root / "reviews/round-2/raw-output.txt")
        == round_2["artifacts"]["raw-output.txt"]["sha256"]
        and round_2["reviewed_commit"] == "0ea47dad1e9e415d0fe76ac1fc0157ce218fbdad"
        and round_2["reviewer_cli"]["version"] == "2.1.247"
        and round_2["reviewer_cli"]["model_selector"] == "opus"
        and round_2["reviewer_cli"]["backend_model_id"] == "not_exposed_by_claude_cli"
        and all(
            item["disposition"] == "accepted_repaired"
            for item in round_2_disposition["findings"].values()
        )
    )
    check(
        "review_provenance_and_dispositions",
        review_ok,
        {
            "round_1_reviewed_commit": round_1["reviewed_commit_sha"],
            "round_2_reviewed_commit": round_2["reviewed_commit"],
            "round_2_finding_count": len(round_2_disposition["findings"]),
        },
    )

    status = "pass" if all(item["passed"] for item in checks) else "fail"
    record_digest = private_digests["ledgers"]["private_record_evidence"]
    return {
        "schema_version": "site-graph-v0-validation-report/3",
        "status": status,
        "scope": (
            f"verified real {snapshot['corpus']['canonical_record_count']:,}-record private "
            "corpus; fixtures/proxies support no corpus claim"
        ),
        "checks": checks,
        "limitations": [
            {
                "id": "external_private_export_generator_history_missing",
                "effect": (
                    "The authorized handoff bytes are verified, but the historical export "
                    "cannot be regenerated from repository history because its export command, "
                    "code revision, and pipeline run identifiers were not supplied."
                ),
            }
        ],
        "summary": {
            "checks": len(checks),
            "passed": sum(item["passed"] for item in checks),
            "failed": sum(not item["passed"] for item in checks),
            "canonical_records": len(records),
            "private_record_evidence_gzip_sha256": record_digest["transport_gzip_sha256"],
            "private_record_evidence_uncompressed_sha256": record_digest[
                "canonical_uncompressed_ndjson_sha256"
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--private-run", type=Path, required=True)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    try:
        integrity = verify_release(repo_root)
    except IntegrityError as error:
        print(
            json.dumps(
                {"status": "fail", "phase": "release_integrity", "error": str(error)},
                sort_keys=True,
            )
        )
        raise SystemExit(1) from error
    report = semantic_report(repo_root, args.corpus.resolve(), args.private_run.resolve())
    committed = read_json(
        repo_root / "docs/evaluations/site-graph-v0/validation-report.json"
    )
    report_matches = report == committed
    output = {
        "status": report["status"] if report_matches else "fail",
        "release_integrity": integrity,
        "committed_validation_report_matches_recomputation": report_matches,
        **report["summary"],
    }
    print(json.dumps(output, sort_keys=True))
    if report["status"] != "pass" or not report_matches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
