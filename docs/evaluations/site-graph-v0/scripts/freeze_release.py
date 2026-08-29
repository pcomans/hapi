#!/usr/bin/env python3
"""Explicitly freeze the release inventory; never called by validation or tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from integrity import EVALUATION_RELATIVE, MANIFEST_NAME, discovered_release_files, sha256
from release_contract import (
    CONTRACT_VERSION,
    PYCACHE_EXCLUSION,
    REQUIRED_RELEASE_FILES,
    validation_input_bindings,
)
from schema_validation import execute_schema_contract_tests, validate_schema


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="replace an existing manifest after an intentional release update",
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    output = repo_root / EVALUATION_RELATIVE / MANIFEST_NAME
    if output.exists() and not args.replace:
        raise RuntimeError(f"refusing to replace {output} without --replace")
    actual = discovered_release_files(repo_root)
    missing = sorted(REQUIRED_RELEASE_FILES - actual)
    extra = sorted(actual - REQUIRED_RELEASE_FILES)
    if missing or extra:
        raise RuntimeError(
            "refusing to freeze a release outside the static contract: "
            + json.dumps({"missing": missing, "extra": extra}, sort_keys=True)
        )
    evaluation_root = repo_root / EVALUATION_RELATIVE
    report = json.loads(
        (evaluation_root / "validation-report.json").read_text(encoding="utf-8")
    )
    expected_ready = {
        "snapshot_acquisition_integrity": "PASS",
        "derived_baseline_reproducibility": "PASS",
        "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
        "overall_contract_status": "READY_SNAPSHOT_CONDITIONAL",
        "downstream_product_verdict": "NOT_RUN",
        "external_exact_head_review_gate": "PENDING_OUTSIDE_COMMIT",
        "pre_pr_ci_status": "PENDING_OUTSIDE_COMMIT",
    }
    if report.get("status") != expected_ready:
        raise RuntimeError(
            "refusing to freeze a failing or stale validation report: "
            + json.dumps(report.get("status"), sort_keys=True)
        )
    expected_binding = {
        "hash_algorithm": "sha256",
        "rule": (
            "Every static required release file except validation-report.json is "
            "hashed after semantic recomputation and before release-manifest generation."
        ),
        "files": validation_input_bindings(repo_root),
    }
    if report.get("release_candidate_binding") != expected_binding:
        raise RuntimeError(
            "refusing to freeze a stale validation report: release candidate bytes "
            "changed after semantic recomputation"
        )
    execute_schema_contract_tests(
        evaluation_root / "schemas", evaluation_root / "schema-test-cases.json"
    )
    validate_schema(
        json.loads(
            (evaluation_root / "trusted-run-attestors.json").read_text(encoding="utf-8")
        ),
        evaluation_root / "schemas/trusted-run-attestors.schema.json",
        "trusted run-attestor release policy",
    )
    names = sorted(REQUIRED_RELEASE_FILES)
    value = {
        "schema_version": "site-graph-v0-release-manifest/2",
        "contract_version": CONTRACT_VERSION,
        "hash_algorithm": "sha256",
        "pycache_exclusion": PYCACHE_EXCLUSION,
        "inventory_rule": (
            "Exactly REQUIRED_RELEASE_FILES in scripts/release_contract.py. Any addition, "
            "removal, or cache-exclusion change requires a separately reviewed contract-version migration."
        ),
        "files": {
            name: {
                "bytes": (repo_root / name).stat().st_size,
                "sha256": sha256(repo_root / name),
            }
            for name in names
        },
    }
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    print(json.dumps({"files": len(names), "manifest": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
