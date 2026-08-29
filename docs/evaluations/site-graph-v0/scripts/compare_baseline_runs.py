#!/usr/bin/env python3
"""Authenticate and compare two deterministic baseline reproductions."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import tempfile
import uuid
from pathlib import Path

from run_baseline import DETERMINISTIC_OUTPUTS, FINAL_OUTPUTS, sha256


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"invalid JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def validate_run(directory: Path) -> dict:
    if not directory.is_dir():
        raise RuntimeError(f"baseline run is not a directory: {directory}")
    actual_names = {path.name for path in directory.iterdir() if path.is_file()}
    nonfiles = sorted(path.name for path in directory.iterdir() if not path.is_file())
    if actual_names != FINAL_OUTPUTS or nonfiles:
        raise RuntimeError(
            f"run output set mismatch at {directory}: "
            f"missing={sorted(FINAL_OUTPUTS - actual_names)}, "
            f"extra={sorted(actual_names - FINAL_OUTPUTS)}, nonfiles={nonfiles}"
        )
    manifest_path = directory / "run-output-manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != "site-graph-v0-baseline-run-manifest/2":
        raise RuntimeError(f"unsupported run manifest schema: {manifest_path}")
    hashes = manifest.get("deterministic_output_hashes")
    if not isinstance(hashes, dict) or set(hashes) != DETERMINISTIC_OUTPUTS:
        raise RuntimeError(f"manifest output inventory mismatch: {manifest_path}")
    corrupt = {
        name: {"manifest": hashes[name], "actual": sha256(directory / name)}
        for name in sorted(DETERMINISTIC_OUTPUTS)
        if hashes[name] != sha256(directory / name)
    }
    if corrupt:
        raise RuntimeError(f"run output hash mismatch at {directory}: {json.dumps(corrupt)}")

    provenance_path = directory / "run-provenance.json"
    provenance = read_json(provenance_path)
    required = {
        "schema_version", "run_id", "started_at_utc", "finished_at_utc", "requested_output",
        "publication", "repo_root", "corpus_archive_logical_locator",
        "corpus_archive_sha256", "corpus_archive_attestation_sha256",
        "temporary_extraction_policy", "canonical_records", "records_by_museum",
        "input_snapshot_sha256", "runner_sha256", "builder_sha256",
        "status",
    }
    if set(provenance) != required:
        raise RuntimeError(f"provenance fields mismatch: {provenance_path}")
    if provenance["schema_version"] != "site-graph-v0-baseline-run-provenance/2":
        raise RuntimeError(f"unsupported run provenance schema: {provenance_path}")
    try:
        uuid.UUID(provenance["run_id"])
    except (ValueError, TypeError) as error:
        raise RuntimeError(f"invalid run_id in {provenance_path}") from error
    try:
        started = dt.datetime.fromisoformat(provenance["started_at_utc"])
        finished = dt.datetime.fromisoformat(provenance["finished_at_utc"])
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"invalid provenance timestamps in {provenance_path}") from error
    if (
        started.tzinfo is None
        or finished.tzinfo is None
        or finished < started
        or not isinstance(provenance["canonical_records"], int)
        or provenance["canonical_records"] <= 0
        or not isinstance(provenance["records_by_museum"], dict)
        or sum(provenance["records_by_museum"].values()) != provenance["canonical_records"]
        or not Path(provenance["repo_root"]).is_absolute()
        or provenance["corpus_archive_logical_locator"] != "HAPI_CORPUS_ARCHIVE"
        or len(provenance["corpus_archive_sha256"]) != 64
        or provenance["status"]
        != {
            "snapshot_acquisition_integrity": "PASS",
            "derived_baseline_reproducibility": "PASS",
            "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
            "overall_contract_status": "READY_SNAPSHOT_CONDITIONAL",
            "downstream_product_verdict": "NOT_RUN",
        }
    ):
        raise RuntimeError(f"invalid run provenance values in {provenance_path}")
    for key in (
        "input_snapshot_sha256", "runner_sha256", "builder_sha256",
        "corpus_archive_attestation_sha256", "corpus_archive_sha256",
    ):
        if provenance[key] != manifest[key]:
            raise RuntimeError(f"provenance/manifest {key} mismatch at {directory}")
    if Path(provenance["requested_output"]).resolve() != directory.resolve():
        raise RuntimeError(f"provenance output path mismatch at {directory}")
    attestation_path = directory / "corpus-archive-attestation.json"
    attestation = read_json(attestation_path)
    if (
        attestation.get("schema_version")
        != "site-graph-v0-corpus-archive-attestation/1"
        or attestation.get("archive", {}).get("sha256")
        != provenance["corpus_archive_sha256"]
        or attestation.get("status")
        != {
            "snapshot_acquisition_integrity": "PASS",
            "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
        }
        or attestation.get("extraction", {}).get("canonical_record_count")
        != provenance["canonical_records"]
        or attestation.get("extraction", {}).get("records_by_museum")
        != provenance["records_by_museum"]
    ):
        raise RuntimeError(f"invalid archive attestation values at {directory}")
    return {
        "manifest": manifest,
        "manifest_sha256": sha256(manifest_path),
        "provenance": provenance,
        "provenance_sha256": sha256(provenance_path),
    }


def compare(run_a: Path, run_b: Path) -> dict:
    left_path, right_path = run_a.resolve(), run_b.resolve()
    if left_path == right_path:
        raise RuntimeError("deterministic reproductions must resolve to different directories")
    left, right = validate_run(left_path), validate_run(right_path)
    if left["provenance"]["run_id"] == right["provenance"]["run_id"]:
        raise RuntimeError("deterministic reproductions must have distinct run_id values")
    stable_fields = (
        "commands", "input_snapshot_sha256", "runner_sha256", "builder_sha256",
        "inventory_path_canonicalization", "corpus_archive_attestation_sha256", "scope",
        "corpus_archive_sha256", "status",
    )
    metadata_mismatches = {
        key: {"run_a": left["manifest"].get(key), "run_b": right["manifest"].get(key)}
        for key in stable_fields
        if left["manifest"].get(key) != right["manifest"].get(key)
    }
    hashes_a = left["manifest"]["deterministic_output_hashes"]
    hashes_b = right["manifest"]["deterministic_output_hashes"]
    output_mismatches = {
        name: {"run_a": hashes_a[name], "run_b": hashes_b[name]}
        for name in sorted(DETERMINISTIC_OUTPUTS)
        if hashes_a[name] != hashes_b[name]
    }
    passed = not metadata_mismatches and not output_mismatches
    return {
        "schema_version": "site-graph-v0-baseline-rerun-evidence/3",
        "status": {
            "snapshot_acquisition_integrity": "PASS",
            "derived_baseline_reproducibility": "PASS" if passed else "INVALID",
            "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
            "overall_contract_status": (
                "READY_SNAPSHOT_CONDITIONAL" if passed else "INVALID"
            ),
            "downstream_product_verdict": "NOT_RUN",
        },
        "terminology": "deterministic_reproduction_not_statistical_independence",
        "authentication": (
            "Authenticated distinct run directories, distinct UUID run IDs, exact output sets, "
            "and actual output bytes rehashed against each manifest."
        ),
        "run_a": {
            "resolved_directory": str(left_path),
            "run_id": left["provenance"]["run_id"],
            "manifest_sha256": left["manifest_sha256"],
            "provenance_sha256": left["provenance_sha256"],
        },
        "run_b": {
            "resolved_directory": str(right_path),
            "run_id": right["provenance"]["run_id"],
            "manifest_sha256": right["manifest_sha256"],
            "provenance_sha256": right["provenance_sha256"],
        },
        "deterministic_output_count": len(DETERMINISTIC_OUTPUTS),
        "deterministic_output_hashes": hashes_a,
        "metadata_mismatches": metadata_mismatches,
        "output_mismatches": output_mismatches,
        "input_snapshot_sha256": left["manifest"]["input_snapshot_sha256"],
        "runner_sha256": left["manifest"]["runner_sha256"],
        "builder_sha256": left["manifest"]["builder_sha256"],
        "scope": left["manifest"]["scope"],
        "corpus_archive_sha256": left["provenance"]["corpus_archive_sha256"],
        "production_lineage": {
            "status": "UNAVAILABLE_DISCLOSED",
            "missing": ["export_command", "producer_git_revision", "dagster_run_ids"],
        },
    }


def atomic_write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-a", type=Path, required=True)
    parser.add_argument("--run-b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = compare(args.run_a, args.run_b)
    atomic_write_json(args.output, evidence)
    print(json.dumps({"status": evidence["status"], "mismatches": evidence["output_mismatches"]}, sort_keys=True))
    if evidence["status"]["overall_contract_status"] != "READY_SNAPSHOT_CONDITIONAL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
