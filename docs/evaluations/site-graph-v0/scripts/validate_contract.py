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
from corpus_archive import (
    CorpusArchiveBlocked,
    CorpusArchiveInvalid,
    authenticated_corpus,
)
from integrity import IntegrityError, sha256, verify_release
from private_ledgers import verify_private_ledgers, verify_public_boundary
from release_contract import validation_input_bindings
from runtime_attestation import validate_runtime_attestation
from schema_validation import execute_schema_contract_tests, validate_schema


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


def _validate_private_run_runtime(
    repo_root: Path,
    private_run: Path,
    snapshot: dict,
    reruns: dict,
) -> dict:
    """Verify one exact rerun identity and its truthful runtime provenance."""
    # Import only after the caller's release-integrity preflight.  Keeping a required
    # release module out of top-level imports ensures deletion/corruption is reported
    # as an inventory failure before Python attempts to load semantic tooling.
    from compare_baseline_runs import validate_run as validate_baseline_run

    runtime_path = private_run / "runtime-attestation.json"
    manifest_path = private_run / "run-output-manifest.json"
    provenance_path = private_run / "run-provenance.json"
    paths = {
        "runtime_attestation": runtime_path,
        "run_output_manifest": manifest_path,
        "run_provenance": provenance_path,
    }
    missing = sorted(label for label, path in paths.items() if not path.is_file())
    if missing:
        return {
            "passed": False,
            "missing": missing,
            "checks": {},
            "matching_rerun": None,
        }

    try:
        runtime = read_json(runtime_path)
        manifest = read_json(manifest_path)
        provenance = read_json(provenance_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return {
            "passed": False,
            "missing": [],
            "checks": {},
            "matching_rerun": None,
            "error": f"private-run runtime provenance is unreadable: {error}",
        }

    errors: list[str] = []
    exact_full_run_validation = False
    try:
        validate_baseline_run(private_run)
        exact_full_run_validation = True
    except (KeyError, OSError, TypeError, ValueError, RuntimeError) as error:
        errors.append(str(error))

    runtime_matches_release = False
    try:
        validated_runtime = validate_runtime_attestation(
            repo_root, snapshot, runtime
        )
        runtime_matches_release = True
    except (KeyError, TypeError, ValueError, RuntimeError) as error:
        validated_runtime = None
        errors.append(str(error))

    runtime_reference = None
    if validated_runtime is not None:
        runtime_reference = {
            "path": "runtime-attestation.json",
            "sha256": sha256(runtime_path),
            "python": validated_runtime["python"],
            "dependency_lock": validated_runtime["dependency_lock"],
        }

    manifest_sha256 = sha256(manifest_path)
    provenance_sha256 = sha256(provenance_path)
    identity = {
        "resolved_directory": str(private_run.resolve()),
        "run_id": provenance.get("run_id") if isinstance(provenance, dict) else None,
        "manifest_sha256": manifest_sha256,
        "provenance_sha256": provenance_sha256,
    }
    matching_reruns = [
        label
        for label in ("run_a", "run_b")
        if isinstance(reruns.get(label), dict)
        and all(reruns[label].get(field) == value for field, value in identity.items())
    ]
    manifest_hashes = (
        manifest.get("deterministic_output_hashes", {})
        if isinstance(manifest, dict)
        else {}
    )
    rerun_hashes = (
        reruns.get("deterministic_output_hashes", {})
        if isinstance(reruns, dict)
        else {}
    )
    requested_output = (
        provenance.get("requested_output") if isinstance(provenance, dict) else None
    )
    requested_output_matches = (
        isinstance(requested_output, str)
        and Path(requested_output).resolve() == private_run.resolve()
    )
    checks = {
        "exact_full_run_output_validation": exact_full_run_validation,
        "runtime_attestation_matches_release_environment": runtime_matches_release,
        "manifest_schema_version": (
            isinstance(manifest, dict)
            and manifest.get("schema_version")
            == "site-graph-v0-baseline-run-manifest/3"
        ),
        "manifest_runtime_binding": (
            runtime_reference is not None
            and isinstance(manifest, dict)
            and manifest.get("runtime_attestation") == runtime_reference
        ),
        "manifest_runtime_output_hash": (
            runtime_reference is not None
            and isinstance(manifest_hashes, dict)
            and manifest_hashes.get("runtime-attestation.json")
            == runtime_reference["sha256"]
        ),
        "provenance_schema_version": (
            isinstance(provenance, dict)
            and provenance.get("schema_version")
            == "site-graph-v0-baseline-run-provenance/3"
        ),
        "provenance_runtime_binding": (
            runtime_reference is not None
            and isinstance(provenance, dict)
            and provenance.get("runtime_attestation") == runtime_reference
        ),
        "provenance_requested_output_binding": requested_output_matches,
        "rerun_evidence_runtime_binding": (
            runtime_reference is not None
            and reruns.get("runtime_attestation") == runtime_reference
        ),
        "rerun_evidence_runtime_output_hash": (
            runtime_reference is not None
            and isinstance(rerun_hashes, dict)
            and rerun_hashes.get("runtime-attestation.json")
            == runtime_reference["sha256"]
        ),
        "rerun_identity_binding": len(matching_reruns) == 1,
    }
    return {
        "passed": all(checks.values()),
        "missing": [],
        "checks": checks,
        "matching_rerun": matching_reruns[0] if len(matching_reruns) == 1 else None,
        "runtime_attestation": runtime_reference,
        "private_run_identity": identity,
        "errors": errors,
    }


def _semantic_report(
    repo_root: Path,
    corpus: Path,
    private_run: Path,
    archive_attestation: dict,
) -> dict:
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

    private_runtime_validation = _validate_private_run_runtime(
        repo_root, private_run, snapshot, reruns
    )
    check(
        "private_run_runtime_attestation_and_rerun_binding",
        private_runtime_validation["passed"],
        private_runtime_validation,
    )

    runtime_attestation_path = private_run / "corpus-archive-attestation.json"
    runtime_attestation = (
        read_json(runtime_attestation_path) if runtime_attestation_path.is_file() else None
    )
    check(
        "authenticated_archive_attestation_bound_to_private_run",
        runtime_attestation == archive_attestation,
        {
            "archive_sha256": archive_attestation["archive"]["sha256"],
            "runtime_attestation_sha256": (
                sha256(runtime_attestation_path)
                if runtime_attestation_path.is_file()
                else None
            ),
            "exact_attestation_match": runtime_attestation == archive_attestation,
        },
    )

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
    external_private_input = private_digests["external_private_input"]
    check(
        "authenticated_private_snapshot_input",
        external_private_input["snapshot_acquisition_integrity"] == "PASS"
        and external_private_input["upstream_production_lineage"]
        == "UNAVAILABLE_DISCLOSED"
        and external_private_input["archive_sha256"]
        == archive_attestation["archive"]["sha256"]
        and private_authentication["private_record_count"]
        == snapshot["corpus"]["canonical_record_count"],
        {
            **private_authentication,
            "canonical_transport_sha256": external_private_input[
                "canonical_artifact_transport_gzip_sha256"
            ],
            "archive_sha256": archive_attestation["archive"]["sha256"],
            "snapshot_acquisition_integrity": external_private_input[
                "snapshot_acquisition_integrity"
            ],
            "upstream_production_lineage": external_private_input[
                "upstream_production_lineage"
            ],
            "historical_export_reproducibility": external_private_input[
                "historical_export_reproducibility"
            ],
            "unavailable_lineage_effect": external_private_input[
                "unavailable_lineage_effect"
            ],
        },
    )
    frozen = prereg["frozen_artifacts"]
    record_digest = private_digests["ledgers"]["private_record_evidence"]
    source_digest = private_digests["ledgers"]["private_opportunity_source"]
    opportunity_digest = private_digests["ledgers"][
        "private_opportunity_membership"
    ]
    preregistered_digest_bindings = {
        "private_record_evidence": {
            "runtime_path": "private-record-evidence.ndjson.gz",
            "record_count": record_digest["row_count"],
            "gzip_transport_sha256": record_digest["transport_gzip_sha256"],
            "canonical_uncompressed_ndjson_sha256": record_digest[
                "canonical_uncompressed_ndjson_sha256"
            ],
            "canonical_row_merkle_sha256": record_digest[
                "canonical_row_merkle_sha256"
            ],
            "publicly_redistributed": False,
        },
        "private_opportunity_source": {
            "runtime_path": "private-opportunity-source.ndjson.gz",
            "record_count": source_digest["row_count"],
            "gzip_transport_sha256": source_digest["transport_gzip_sha256"],
            "canonical_uncompressed_ndjson_sha256": source_digest[
                "canonical_uncompressed_ndjson_sha256"
            ],
            "canonical_row_merkle_sha256": source_digest[
                "canonical_row_merkle_sha256"
            ],
            "publicly_redistributed": False,
        },
        "private_opportunity_ledger": {
            "runtime_path": "private-opportunity-ledger.json",
            "canonical_json_sha256": opportunity_digest["canonical_json_sha256"],
            "transport_json_sha256": opportunity_digest["transport_json_sha256"],
            "publicly_redistributed": False,
        },
    }
    check(
        "preregistered_private_and_public_digest_bindings",
        all(
            frozen[name] == value
            for name, value in preregistered_digest_bindings.items()
        )
        and frozen["public_opportunity_summary"]["sha256"]
        == sha256(root / frozen["public_opportunity_summary"]["path"])
        and frozen["private_ledger_digests"]["sha256"]
        == sha256(root / frozen["private_ledger_digests"]["path"])
        and frozen["type_crosswalk"]["sha256"]
        == sha256(root / frozen["type_crosswalk"]["path"]),
        {
            "private": preregistered_digest_bindings,
            "public_opportunity_summary_sha256": sha256(
                root / frozen["public_opportunity_summary"]["path"]
            ),
            "private_ledger_digests_sha256": sha256(
                root / frozen["private_ledger_digests"]["path"]
            ),
            "type_crosswalk_sha256": sha256(
                root / frozen["type_crosswalk"]["path"]
            ),
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
    unclassified_with_mapped_types = [
        row["target_id"]
        for row in recomputed_nodes
        if row["scope_class"] == "unclassified" and row["source_types"]
    ]
    check(
        "single_source_type_crosswalk",
        actual_idai_types == crosswalk_types
        and unclassified_with_mapped_types == []
        and crosswalk["credit_policy"][
            "broad_or_administrative_new_link_improvement_credit"
        ]
        == 0,
        {
            "actual_idai_types": actual_idai_types,
            "crosswalk_types": crosswalk_types,
            "unclassified_targets_with_mapped_source_types": unclassified_with_mapped_types,
        },
    )

    schema_execution = execute_schema_contract_tests(
        root / "schemas", root / "schema-test-cases.json"
    )
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
        "all_json_schemas_meta_valid_and_instance_executed",
        True,
        schema_execution,
    )

    trusted_attestors = read_json(root / "trusted-run-attestors.json")
    trusted_source_exporters = read_json(root / "trusted-source-exporters.json")
    trusted_reviewers = read_json(root / "trusted-reviewers.json")
    validate_schema(
        trusted_attestors,
        root / "schemas/trusted-run-attestors.schema.json",
        "release-pinned trusted run attestors",
    )
    validate_schema(
        trusted_source_exporters,
        root / "schemas/trusted-source-exporters.schema.json",
        "release-pinned trusted source exporters",
    )
    validate_schema(
        trusted_reviewers,
        root / "schemas/trusted-reviewers.schema.json",
        "release-pinned trusted reviewers and auditors",
    )
    check(
        "production_candidate_trust_gates_fail_closed",
        trusted_attestors["status"] == "NOT_CONFIGURED"
        and trusted_attestors["attestors"] == []
        and trusted_source_exporters["status"] == "NOT_CONFIGURED"
        and trusted_source_exporters["registry_scope"] == "production_release"
        and trusted_source_exporters["exporters"] == []
        and trusted_reviewers["status"] == "NOT_CONFIGURED"
        and trusted_reviewers["trust_tier"] == "PRODUCTION"
        and trusted_reviewers["identities"] == [],
        {
            "trusted_run_attestor_status": trusted_attestors["status"],
            "trusted_source_exporter_status": trusted_source_exporters["status"],
            "trusted_reviewer_status": trusted_reviewers["status"],
            "downstream_product_verdict": "NOT_RUN",
            "effects": {
                "run_completion": trusted_attestors["current_effect"],
                "source_export": trusted_source_exporters["current_effect"],
                "review_evidence": trusted_reviewers["current_effect"],
            },
        },
    )

    correction_policy = read_json(root / "correction-policy.json")
    check(
        "immutable_primary_and_private_correction_policy",
        correction_policy["current_primary_corrections_applied"] == 0
        and correction_policy["allowed_operations"] == ["set_site_mention_resolution"]
        and correction_policy["sensitivity_estimands"][
            "fixed_frozen_intent_to_treat"
        ]
        and correction_policy["sensitivity_estimands"][
            "corrected_source_counterfactual_reselection"
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
        and reruns.get("status")
        == {
            "snapshot_acquisition_integrity": "PASS",
            "derived_baseline_reproducibility": "PASS",
            "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
            "overall_contract_status": "READY_SNAPSHOT_CONDITIONAL",
            "downstream_product_verdict": "NOT_RUN",
        }
        and reruns.get("terminology") == "deterministic_reproduction_not_statistical_independence"
        and reruns.get("run_a", {}).get("run_id") != reruns.get("run_b", {}).get("run_id")
        and reruns.get("output_mismatches") == {}
        and reruns.get("metadata_mismatches") == {}
        and reruns.get("input_snapshot_sha256") == sha256(root / "input-snapshot.json")
        and reruns.get("runner_sha256") == sha256(root / "scripts/run_baseline.py")
        and reruns.get("builder_sha256") == sha256(root / "scripts/build_baseline.py")
        and reruns.get("corpus_archive_sha256")
        == snapshot["corpus"]["archive_acquisition"]["archive_sha256"]
        and private_runtime_validation["passed"]
        and public_match,
        {
            "run_a": reruns.get("run_a"),
            "run_b": reruns.get("run_b"),
            "deterministic_output_count": reruns.get("deterministic_output_count"),
            "private_run_runtime_binding": private_runtime_validation,
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
        "snapshot_handoff_metadata_bytes_authenticated",
        provenance_bytes_authenticated
        and "cannot be regenerated bit-for-bit" in provenance["known_reproduction_limit"],
        {
            "snapshot_acquisition_integrity": "PASS",
            "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
            "historical_export_reproducible": False,
            "known_reproduction_limit": provenance["known_reproduction_limit"],
        },
    )

    round_1 = read_json(root / "reviews/round-1/metadata.json")
    round_2 = read_json(root / "reviews/round-2/metadata.json")
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
    )
    check(
        "historical_review_provenance_authenticated_not_approval",
        review_ok,
        {
            "round_1_reviewed_commit": round_1["reviewed_commit_sha"],
            "round_2_reviewed_commit": round_2["reviewed_commit"],
            "historical_review_outcome": "REQUEST_CHANGES",
            "exact_current_head_external_review_gate": "PENDING_OUTSIDE_COMMIT",
            "implementer_dispositions_are_reviewer_approval": False,
        },
    )

    derived_status = "PASS" if all(item["passed"] for item in checks) else "INVALID"
    overall_status = (
        "READY_SNAPSHOT_CONDITIONAL" if derived_status == "PASS" else "INVALID"
    )
    return {
        "schema_version": "site-graph-v0-validation-report/4",
        "status": {
            "snapshot_acquisition_integrity": "PASS",
            "derived_baseline_reproducibility": derived_status,
            "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
            "overall_contract_status": overall_status,
            "downstream_product_verdict": "NOT_RUN",
            "external_exact_head_review_gate": "PENDING_OUTSIDE_COMMIT",
            "pre_pr_ci_status": "PENDING_OUTSIDE_COMMIT",
        },
        "scope": (
            f"snapshot-conditional evaluation over the authenticated real "
            f"{snapshot['corpus']['canonical_record_count']:,}-record private archive; "
            "fixtures/proxies support no corpus claim and historical export reproducibility "
            "is not asserted"
        ),
        "archive_sha256": archive_attestation["archive"]["sha256"],
        "production_lineage": snapshot["corpus"]["production_lineage"],
        "prohibited_claims": snapshot["corpus"]["production_lineage"][
            "prohibited_inferences"
        ],
        "release_candidate_binding": {
            "hash_algorithm": "sha256",
            "rule": (
                "Every static required release file except validation-report.json is "
                "hashed after semantic recomputation and before release-manifest generation."
            ),
            "files": validation_input_bindings(repo_root),
        },
        "checks": checks,
        "limitations": [
            {
                "id": "upstream_production_lineage_unavailable_disclosed",
                "status": "UNAVAILABLE_DISCLOSED",
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
            "archive_sha256": archive_attestation["archive"]["sha256"],
            "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
            "overall_contract_status": overall_status,
            "downstream_product_verdict": "NOT_RUN",
        },
    }


def semantic_report(
    repo_root: Path,
    corpus_archive: Path,
    corpus_archive_sidecar: Path,
    private_run: Path,
) -> dict:
    """Authenticate the external archive, then recompute the snapshot contract."""
    with authenticated_corpus(
        repo_root, corpus_archive, corpus_archive_sidecar
    ) as (corpus, archive_attestation):
        return _semantic_report(
            repo_root, corpus, private_run, archive_attestation
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--corpus-archive", type=Path, required=True)
    parser.add_argument("--corpus-archive-sidecar", type=Path, required=True)
    parser.add_argument("--private-run", type=Path, required=True)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    try:
        integrity = verify_release(repo_root)
    except IntegrityError as error:
        print(
            json.dumps(
                {
                    "snapshot_acquisition_integrity": "BLOCKED",
                    "derived_baseline_reproducibility": "INVALID",
                    "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
                    "overall_contract_status": "INVALID",
                    "downstream_product_verdict": "NOT_RUN",
                    "phase": "release_integrity",
                    "error": str(error),
                },
                sort_keys=True,
            )
        )
        raise SystemExit(1) from error
    try:
        report = semantic_report(
            repo_root,
            args.corpus_archive.resolve(),
            args.corpus_archive_sidecar.resolve(),
            args.private_run.resolve(),
        )
    except CorpusArchiveBlocked as error:
        print(
            json.dumps(
                {
                    "snapshot_acquisition_integrity": "BLOCKED",
                    "derived_baseline_reproducibility": "BLOCKED",
                    "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
                    "overall_contract_status": "BLOCKED",
                    "downstream_product_verdict": "NOT_RUN",
                    "error": str(error),
                },
                sort_keys=True,
            )
        )
        raise SystemExit(1) from error
    except CorpusArchiveInvalid as error:
        print(
            json.dumps(
                {
                    "snapshot_acquisition_integrity": "INVALID",
                    "derived_baseline_reproducibility": "BLOCKED",
                    "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
                    "overall_contract_status": "INVALID",
                    "downstream_product_verdict": "NOT_RUN",
                    "error": str(error),
                },
                sort_keys=True,
            )
        )
        raise SystemExit(1) from error
    committed = read_json(
        repo_root / "docs/evaluations/site-graph-v0/validation-report.json"
    )
    report_matches = report == committed
    output = {
        "status": (
            report["status"]
            if report_matches
            else {
                **report["status"],
                "overall_contract_status": "INVALID",
                "derived_baseline_reproducibility": "INVALID",
            }
        ),
        "release_integrity": integrity,
        "committed_validation_report_matches_recomputation": report_matches,
        **report["summary"],
    }
    print(json.dumps(output, sort_keys=True))
    if (
        report["status"]["overall_contract_status"]
        != "READY_SNAPSHOT_CONDITIONAL"
        or not report_matches
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
