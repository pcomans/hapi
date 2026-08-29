"""Adversarial mechanics for trusted completion and exact runtime provenance.

All signing keys and Git histories in this module are ephemeral logic-only inputs.
They make no claim about the unavailable production candidate or trust roots.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


REPO = Path(__file__).resolve().parents[2]
EVALUATION = REPO / "docs/evaluations/site-graph-v0"
SCRIPTS = EVALUATION / "scripts"
SCHEMAS = EVALUATION / "schemas"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import candidate_git  # noqa: E402
import compare_candidate  # noqa: E402
import run_baseline  # noqa: E402
import runtime_attestation  # noqa: E402
import schema_validation  # noqa: E402
import source_exports  # noqa: E402
import trusted_completion  # noqa: E402
import validate_contract  # noqa: E402


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_bytes(root: Path, relative: str, raw: bytes) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def _write_json(root: Path, relative: str, value: object) -> bytes:
    raw = _json_bytes(value)
    _write_bytes(root, relative, raw)
    return raw


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _working_artifact(repo: Path, relative: str) -> dict:
    raw = (repo / relative).read_bytes()
    return {
        "path": relative,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_oid": _git(repo, "hash-object", relative),
    }


def _committed_artifact(repo: Path, commit: str, relative: str) -> dict:
    raw = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout
    return {
        "path": relative,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_oid": _git(repo, "rev-parse", f"{commit}:{relative}"),
    }


def _key() -> tuple[Ed25519PrivateKey, str, str]:
    private = Ed25519PrivateKey.generate()
    public_raw = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return (
        private,
        base64.b64encode(public_raw).decode("ascii"),
        hashlib.sha256(public_raw).hexdigest(),
    )


def test_runtime_attestation_records_the_executing_uv_environment() -> None:
    snapshot = json.loads((EVALUATION / "input-snapshot.json").read_text())
    attestation = runtime_attestation.build_runtime_attestation(REPO, snapshot)
    assert attestation == {
        "schema_version": "site-graph-v0-baseline-runtime-attestation/1",
        "python": {
            "implementation": "CPython",
            "implementation_name": "cpython",
            "version": "3.12.13",
        },
        "dependency_lock": {
            "path": "pipeline/uv.lock",
            "bytes": 500187,
            "sha256": "647f76bca14be56e358fa66c156cc8b9a6dc57f6cd4dbaccd47a3224bcae6f3f",
        },
        "verification": {
            "input_snapshot_runtime_binding": "PASS",
            "executing_interpreter_match": "PASS",
            "dependency_lock_match": "PASS",
        },
    }


def test_runtime_attestation_rejects_runtime_or_lock_drift(tmp_path: Path) -> None:
    snapshot = json.loads((EVALUATION / "input-snapshot.json").read_text())
    recorded = runtime_attestation.build_runtime_attestation(REPO, snapshot)
    altered_record = copy.deepcopy(recorded)
    altered_record["dependency_lock"]["sha256"] = "f" * 64
    with pytest.raises(RuntimeError, match="recorded baseline runtime"):
        runtime_attestation.validate_runtime_attestation(
            REPO, snapshot, altered_record
        )

    wrong_runtime = copy.deepcopy(snapshot)
    wrong_runtime["extractor_and_matcher"]["python_baseline_runtime"][
        "version"
    ] = "3.12.12"
    with pytest.raises(RuntimeError, match="Python runtime mismatch"):
        runtime_attestation.build_runtime_attestation(REPO, wrong_runtime)

    temporary_repo = tmp_path / "runtime-repo"
    (temporary_repo / "pipeline").mkdir(parents=True)
    schema_target = temporary_repo / "docs/evaluations/site-graph-v0/schemas"
    schema_target.mkdir(parents=True)
    shutil.copy2(
        SCHEMAS / "baseline-runtime-attestation.schema.json", schema_target
    )
    shutil.copy2(REPO / "pipeline/uv.lock", temporary_repo / "pipeline/uv.lock")
    runtime_attestation.build_runtime_attestation(temporary_repo, snapshot)
    (temporary_repo / "pipeline/uv.lock").write_bytes(b"changed lock\n")
    with pytest.raises(RuntimeError, match="dependency-lock mismatch"):
        runtime_attestation.build_runtime_attestation(temporary_repo, snapshot)


def _private_run_runtime_case(tmp_path: Path) -> tuple[Path, dict, dict]:
    private_run = tmp_path / "logic-runtime-run"
    private_run.mkdir()
    snapshot = json.loads((EVALUATION / "input-snapshot.json").read_text())
    for name in sorted(run_baseline.DETERMINISTIC_OUTPUTS):
        _write_bytes(private_run, name, f"logic-only {name}\n".encode())

    archive_sha256 = "c" * 64
    archive_attestation = {
        "schema_version": "site-graph-v0-corpus-archive-attestation/1",
        "archive": {
            "logical_locator": "HAPI_CORPUS_ARCHIVE",
            "sha256": archive_sha256,
        },
        "status": {
            "snapshot_acquisition_integrity": "PASS",
            "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
        },
        "extraction": {
            "canonical_record_count": 1,
            "records_by_museum": {"logic-only": 1},
        },
    }
    _write_json(
        private_run, "corpus-archive-attestation.json", archive_attestation
    )
    runtime = runtime_attestation.build_runtime_attestation(REPO, snapshot)
    runtime_raw = _write_json(
        private_run, "runtime-attestation.json", runtime
    )
    runtime_reference = {
        "path": "runtime-attestation.json",
        "sha256": hashlib.sha256(runtime_raw).hexdigest(),
        "python": runtime["python"],
        "dependency_lock": runtime["dependency_lock"],
    }
    output_hashes = {
        name: hashlib.sha256((private_run / name).read_bytes()).hexdigest()
        for name in sorted(run_baseline.DETERMINISTIC_OUTPUTS)
    }
    status = {
        "snapshot_acquisition_integrity": "PASS",
        "derived_baseline_reproducibility": "PASS",
        "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
        "overall_contract_status": "READY_SNAPSHOT_CONDITIONAL",
        "downstream_product_verdict": "NOT_RUN",
    }
    manifest = {
        "schema_version": "site-graph-v0-baseline-run-manifest/3",
        "commands": [],
        "deterministic_output_hashes": output_hashes,
        "input_snapshot_sha256": hashlib.sha256(
            (EVALUATION / "input-snapshot.json").read_bytes()
        ).hexdigest(),
        "runner_sha256": hashlib.sha256(
            (SCRIPTS / "run_baseline.py").read_bytes()
        ).hexdigest(),
        "builder_sha256": hashlib.sha256(
            (SCRIPTS / "build_baseline.py").read_bytes()
        ).hexdigest(),
        "inventory_path_canonicalization": "logic-only fixture",
        "corpus_archive_attestation_sha256": output_hashes[
            "corpus-archive-attestation.json"
        ],
        "corpus_archive_sha256": archive_sha256,
        "runtime_attestation": runtime_reference,
        "scope": "logic-only exact-output validation fixture; no corpus claim",
        "status": status,
    }
    _write_json(private_run, "run-output-manifest.json", manifest)
    provenance = {
        "schema_version": "site-graph-v0-baseline-run-provenance/3",
        "run_id": "00000000-0000-4000-8000-000000000001",
        "started_at_utc": "2026-08-29T00:00:00+00:00",
        "finished_at_utc": "2026-08-29T00:00:01+00:00",
        "requested_output": str(private_run.resolve()),
        "publication": "logic-only fixture",
        "repo_root": str(REPO),
        "corpus_archive_logical_locator": "HAPI_CORPUS_ARCHIVE",
        "corpus_archive_sha256": archive_sha256,
        "corpus_archive_attestation_sha256": output_hashes[
            "corpus-archive-attestation.json"
        ],
        "temporary_extraction_policy": "logic-only fixture",
        "canonical_records": 1,
        "records_by_museum": {"logic-only": 1},
        "input_snapshot_sha256": manifest["input_snapshot_sha256"],
        "runner_sha256": manifest["runner_sha256"],
        "builder_sha256": manifest["builder_sha256"],
        "runtime_attestation": runtime_reference,
        "status": status,
    }
    _write_json(private_run, "run-provenance.json", provenance)
    evidence = {
        "run_a": {
            "resolved_directory": str(private_run.resolve()),
            "run_id": provenance["run_id"],
            "manifest_sha256": hashlib.sha256(
                (private_run / "run-output-manifest.json").read_bytes()
            ).hexdigest(),
            "provenance_sha256": hashlib.sha256(
                (private_run / "run-provenance.json").read_bytes()
            ).hexdigest(),
        },
        "run_b": {
            "resolved_directory": str((tmp_path / "different-run").resolve()),
            "run_id": "00000000-0000-4000-8000-000000000002",
            "manifest_sha256": "1" * 64,
            "provenance_sha256": "2" * 64,
        },
        "runtime_attestation": runtime_reference,
        "deterministic_output_hashes": output_hashes,
    }
    return private_run, snapshot, evidence


@pytest.mark.parametrize(
    ("attack", "failed_check"),
    [
        ("runtime_file", "runtime_attestation_matches_release_environment"),
        ("manifest", "manifest_runtime_binding"),
        ("evidence", "rerun_evidence_runtime_binding"),
        ("identity", "rerun_identity_binding"),
        ("resolved_directory", "rerun_identity_binding"),
        ("requested_output", "provenance_requested_output_binding"),
        ("partial_run", "exact_full_run_output_validation"),
    ],
)
def test_private_run_runtime_requires_exact_manifest_and_rerun_evidence(
    tmp_path: Path, attack: str, failed_check: str
) -> None:
    private_run, snapshot, evidence = _private_run_runtime_case(tmp_path)
    verified = validate_contract._validate_private_run_runtime(
        REPO, private_run, snapshot, evidence
    )
    assert verified["passed"] is True
    assert verified["matching_rerun"] == "run_a"

    if attack == "runtime_file":
        altered = json.loads(
            (private_run / "runtime-attestation.json").read_text()
        )
        altered["python"]["version"] = "3.12.12"
        _write_json(private_run, "runtime-attestation.json", altered)
    elif attack == "manifest":
        altered = json.loads(
            (private_run / "run-output-manifest.json").read_text()
        )
        altered["runtime_attestation"]["sha256"] = "3" * 64
        _write_json(private_run, "run-output-manifest.json", altered)
    elif attack == "evidence":
        evidence["runtime_attestation"]["sha256"] = "4" * 64
    elif attack == "identity":
        evidence["run_a"]["run_id"] = "substituted-runtime-run"
    elif attack == "resolved_directory":
        evidence["run_a"]["resolved_directory"] = str(
            (tmp_path / "substituted-run").resolve()
        )
    elif attack == "requested_output":
        altered = json.loads((private_run / "run-provenance.json").read_text())
        altered["requested_output"] = str((tmp_path / "substituted-run").resolve())
        _write_json(private_run, "run-provenance.json", altered)
    else:
        (private_run / "adapter_catalog_summary.json").unlink()

    rejected = validate_contract._validate_private_run_runtime(
        REPO, private_run, snapshot, evidence
    )
    assert rejected["passed"] is False
    assert rejected["checks"][failed_check] is False


def test_release_run_completion_policy_remains_fail_closed() -> None:
    policy = json.loads((EVALUATION / "trusted-run-attestors.json").read_text())
    assert policy["registry_scope"] == "production_release"
    assert policy["status"] == "NOT_CONFIGURED"
    assert policy["attestors"] == []
    with pytest.raises(candidate_git.CandidateGitError, match="NOT_CONFIGURED"):
        trusted_completion._load_run_attestor_policy(REPO, SCHEMAS)


def _schema_const(schema_name: str, field: str) -> str:
    schema = json.loads((SCHEMAS / schema_name).read_text())
    value = schema["properties"][field]["const"]
    assert isinstance(value, str)
    return value


def _completion_case(tmp_path: Path) -> dict:
    """Create a three-commit, logic-only start/result/completion history."""
    repo = tmp_path / "completion-repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "logic-only@example.invalid")
    _git(repo, "config", "user.name", "Logic Only")

    run_private, run_public, run_key_id = _key()
    other_run_private, other_run_public, other_run_key_id = _key()
    export_private, export_public, export_key_id = _key()
    run_policy = {
        "schema_version": "site-graph-v0-trusted-run-attestors/1",
        "registry_scope": "test_only",
        "status": "CONFIGURED",
        "signature_scheme": "ed25519",
        "signature_context": "hapi-site-graph-v0-run-start/1",
        "configuration_rule": "ephemeral logic-only completion-chain test",
        "current_effect": "not production authority",
        "attestors": [
            {
                "attestor_id": "logic-run-attestor",
                "key_id": run_key_id,
                "public_key_base64": run_public,
                "trust_basis": "ephemeral test key",
            },
            {
                "attestor_id": "other-logic-run-attestor",
                "key_id": other_run_key_id,
                "public_key_base64": other_run_public,
                "trust_basis": "ephemeral test key for negative chain test",
            },
        ],
    }
    source_policy = {
        "schema_version": "site-graph-v0-trusted-source-exporters/1",
        "registry_scope": "test_only",
        "status": "CONFIGURED",
        "signature_scheme": "ed25519",
        "signature_context": "hapi-site-graph-v0-authority-source-export/1",
        "configuration_rule": "ephemeral logic-only source-export test",
        "current_effect": "not production authority",
        "exporters": [
            {
                "exporter_id": "logic-source-exporter",
                "key_id": export_key_id,
                "public_key_base64": export_public,
                "trust_basis": "ephemeral test key",
            }
        ],
    }
    run_policy_path = "docs/evaluations/site-graph-v0/trusted-run-attestors.json"
    source_policy_path = (
        "docs/evaluations/site-graph-v0/trusted-source-exporters.json"
    )
    _write_json(repo, run_policy_path, run_policy)
    _write_json(repo, source_policy_path, source_policy)
    release_snapshot = json.loads((EVALUATION / "input-snapshot.json").read_text())
    release_runtime = runtime_attestation.build_runtime_attestation(
        REPO, release_snapshot
    )
    runtime_binding = {
        "python": release_runtime["python"],
        "dependency_lock": release_runtime["dependency_lock"],
    }

    source_records = [
        {
            "source_record_id": "logic-record-1",
            "target_id": "logic-target-1",
            "authority_identity_locator": "logic:target-1",
            "raw_source_types": ["archaeological-site"],
            "parent_ids": [],
            "child_ids": [],
            "authority_citations": ["logic:citation-1"],
        }
    ]
    source_export = {
        "schema_version": _schema_const(
            "authority-source-export.schema.json", "schema_version"
        ),
        "source_export_id": "logic-export-1",
        "authority_name": "logic-only authority",
        "source_kind": "logic-only",
        "originating_museum": False,
        "acquired_at_utc": "2026-08-29T00:00:00+00:00",
        "provenance": {
            "source_locator": "logic://source/export",
            "acquisition_method": "purpose-built unit input",
            "producer_identity": "logic-source-exporter",
        },
        "completeness": {
            "coverage_statement": "all records in this logic-only export",
            "known_incompleteness": ["not evidence about the Hapi corpus"],
            "record_selection_policy": "all_records_in_authenticated_source_export",
            "record_count": 1,
            "records_canonical_sha256": trusted_completion.canonical_sha256(
                source_records
            ),
            "complete_for_candidate_target_derivation": True,
        },
        "records": source_records,
    }
    export_path = "candidate/source-export.json"
    export_attestation_path = "candidate/source-export.attestation.json"
    export_signature_path = "candidate/source-export.attestation.sig"
    _write_json(repo, export_path, source_export)
    export_reference = _working_artifact(repo, export_path)
    export_attestation = {
        "schema_version": _schema_const(
            "authority-source-export-attestation.schema.json", "schema_version"
        ),
        "signature_context": source_policy["signature_context"],
        "export_invocation_id": "1" * 64,
        "exporter_id": "logic-source-exporter",
        "exporter_key_id": export_key_id,
        "trusted_source_exporters_canonical_sha256": (
            trusted_completion.canonical_sha256(source_policy)
        ),
        "source_export_id": "logic-export-1",
        "source_export": export_reference,
        "detached_signature_path": export_signature_path,
        "record_count": 1,
        "records_canonical_sha256": source_export["completeness"][
            "records_canonical_sha256"
        ],
    }
    export_attestation_raw = _write_json(
        repo, export_attestation_path, export_attestation
    )
    _write_bytes(
        repo, export_signature_path, export_private.sign(export_attestation_raw)
    )
    hierarchy_path = "candidate/hierarchy.json"
    relation_path = "candidate/relations.json"
    _write_json(
        repo,
        hierarchy_path,
        {
            "schema_version": _schema_const(
                "candidate-hierarchy.schema.json", "schema_version"
            ),
            "coverage": (
                "every_target_and_every_record_from_all_authenticated_complete_"
                "authority_source_exports"
            ),
            "known_incompleteness": {
                "closed_world_claim": False,
                "limitations": ["logic-only test input"],
                "derivation_statement": "one test target from one signed export",
            },
            "nodes": [
                {
                    "target_id": "logic-target-1",
                    "candidate_e55_type": "archaeological-site",
                    "child_ids": [],
                    "ancestor_target_ids": [],
                    "source_export_ids": ["logic-export-1"],
                    "source_record_ids": ["logic-record-1"],
                }
            ],
        },
    )
    _write_json(
        repo,
        relation_path,
        {
            "schema_version": _schema_const(
                "relation-ledger.schema.json", "schema_version"
            ),
            "strict_refinement_direction": (
                "left_target_id_is_narrower_than_right_target_id"
            ),
            "identity_census_policy": (
                "every_counted_candidate_class_is_censused_against_every_relevant_"
                "frozen_baseline_identity_including_one_sided_and_every_other_"
                "counted_candidate_class"
            ),
            "relations": [],
        },
    )
    review_prompt_path = "candidate/review-prompt.txt"
    review_input_path = "candidate/review-input.json"
    prompt_audit_path = "candidate/prompt-audit.json"
    prompt_audit_signature_path = "candidate/prompt-audit.sig"
    _write_bytes(repo, review_prompt_path, b"logic-only review prompt\n")
    _write_bytes(repo, review_input_path, b'{"logic_only":true}\n')
    _write_bytes(repo, prompt_audit_signature_path, b"P" * 64)
    prompt_reference = _working_artifact(repo, review_prompt_path)
    input_reference = _working_artifact(repo, review_input_path)
    prompt_audit_signature_reference = _working_artifact(
        repo, prompt_audit_signature_path
    )
    prompt_audit = {
        "schema_version": _schema_const(
            "prompt-leakage-audit.schema.json", "schema_version"
        ),
        "audit_id": "logic-prompt-audit",
        "review_id": "logic-review",
        "review_invocation_id": "logic-review-invocation",
        "decision_key": "logic-decision-key",
        "decision_kind": "link_support",
        "subject": {"artifact_id": "logic-artifact", "target_id": "logic-target-1"},
        "prompt": prompt_reference,
        "input": input_reference,
        "audit_method": "deterministic_prompt_leakage_guard/1",
        "auditor": {
            "auditor_id": "logic-auditor",
            "independence_group": "logic-auditor-group",
        },
        "executed_at_utc": "2026-08-29T00:00:00+00:00",
        "deterministic_guard": {
            "guard_version": "site-graph-v0-deterministic-prompt-leakage-guard/1",
            "request_binding_sha256": "5" * 64,
            "candidate_ids": {"count": 1, "canonical_sha256": "6" * 64},
            "source_ids": {"count": 1, "canonical_sha256": "7" * 64},
            "answer_strings": {"count": 1, "canonical_sha256": "8" * 64},
            "result": "PASS",
            "findings": [],
        },
        "authentication": {
            "registry_id": "logic-review-registry",
            "signature_context": "hapi-site-graph-v0-review-evidence/1",
            "principal_id": "logic-auditor",
            "key_id": "9" * 64,
            "signed_at_utc": "2026-08-29T00:00:00+00:00",
            "statement_sha256": "a" * 64,
            "signature": prompt_audit_signature_reference,
        },
    }
    _write_json(repo, prompt_audit_path, prompt_audit)

    role_specs = (
        (
            "hierarchy",
            None,
            hierarchy_path,
            "application/json",
            _schema_const("candidate-hierarchy.schema.json", "schema_version"),
        ),
        (
            "relation_ledger",
            None,
            relation_path,
            "application/json",
            _schema_const("relation-ledger.schema.json", "schema_version"),
        ),
        (
            "authority_source_export",
            "logic-export-1",
            export_path,
            "application/json",
            source_export["schema_version"],
        ),
        (
            "authority_source_export_attestation",
            "logic-export-1",
            export_attestation_path,
            "application/json",
            export_attestation["schema_version"],
        ),
        (
            "authority_source_export_signature",
            "logic-export-1",
            export_signature_path,
            "application/octet-stream",
            None,
        ),
        (
            "review_prompt",
            None,
            review_prompt_path,
            "text/plain",
            None,
        ),
        (
            "review_input",
            None,
            review_input_path,
            "application/json",
            None,
        ),
        (
            "prompt_leakage_audit",
            None,
            prompt_audit_path,
            "application/json",
            prompt_audit["schema_version"],
        ),
        (
            "prompt_leakage_audit_signature",
            None,
            prompt_audit_signature_path,
            "application/octet-stream",
            None,
        ),
    )
    freeze_files = [
        {
            "role": role,
            "source_export_group_id": group_id,
            **_working_artifact(repo, path),
            "media_type": media_type,
            "schema_version": schema_version,
        }
        for role, group_id, path, media_type, schema_version in role_specs
    ]
    release_sha = "a" * 64
    private_ledger_sha = "b" * 64
    run_policy_reference = _working_artifact(repo, run_policy_path)
    source_policy_reference = _working_artifact(repo, source_policy_path)
    freeze = {
        "schema_version": _schema_const(
            "candidate-freeze-manifest.schema.json", "schema_version"
        ),
        "contract_version": _schema_const(
            "candidate-freeze-manifest.schema.json", "contract_version"
        ),
        "candidate_id": "logic-candidate",
        "run_nonce": "c" * 64,
        "release_manifest_sha256": release_sha,
        "private_opportunity_ledger_canonical_sha256": private_ledger_sha,
        "trusted_run_attestors": {
            "path": run_policy_path,
            "raw_sha256": run_policy_reference["sha256"],
            "git_blob_oid": run_policy_reference["git_blob_oid"],
            "canonical_sha256": trusted_completion.canonical_sha256(run_policy),
            "status": "CONFIGURED",
            "attestor_key_ids": sorted(
                row["key_id"] for row in run_policy["attestors"]
            ),
        },
        "trusted_source_exporters": {
            "path": source_policy_path,
            "raw_sha256": source_policy_reference["sha256"],
            "git_blob_oid": source_policy_reference["git_blob_oid"],
            "canonical_sha256": trusted_completion.canonical_sha256(source_policy),
            "status": "CONFIGURED",
            "exporter_key_ids": [export_key_id],
        },
        "created_at_utc": "2026-08-29T00:00:01+00:00",
        "created_by": "logic-only test",
        "provenance": {"method": "purpose-built mechanics test"},
        "files": sorted(freeze_files, key=lambda row: (row["role"], row["path"])),
    }
    freeze_path = "candidate/freeze.json"
    _write_json(repo, freeze_path, freeze)
    freeze_commit = _commit(repo, "logic freeze")
    freeze_reference = _committed_artifact(repo, freeze_commit, freeze_path)

    start_receipt = {
        "schema_version": _schema_const(
            "run-start-receipt.schema.json", "schema_version"
        ),
        "contract_version": _schema_const(
            "run-start-receipt.schema.json", "contract_version"
        ),
        "signature_context": run_policy["signature_context"],
        "release_manifest_sha256": release_sha,
        "trusted_run_attestors_canonical_sha256": (
            trusted_completion.canonical_sha256(run_policy)
        ),
        "attestor_id": "logic-run-attestor",
        "attestor_key_id": run_key_id,
        "candidate_id": "logic-candidate",
        "invocation_id": "logic-invocation-1",
        "runtime": runtime_binding,
        "freeze_commit": freeze_commit,
        "freeze_manifest": freeze_reference,
        "freeze_nonce": freeze["run_nonce"],
        "started_at_utc": "2026-08-29T00:01:00+00:00",
    }
    receipt_path = "candidate/run-start-receipt.json"
    receipt_signature_path = "candidate/run-start-receipt.sig"
    receipt_raw = _write_json(repo, receipt_path, start_receipt)
    _write_bytes(repo, receipt_signature_path, run_private.sign(receipt_raw))
    review_path = "candidate/reviews.json"
    reviews = {
        "schema_version": "site-graph-v0-review-ledger/3",
        "review_scope": "census_of_every_credited_link_refinement_equivalence_and_positive_distinctness_decision",
        "decisions": [],
    }
    _write_json(repo, review_path, reviews)
    review_reference = _working_artifact(repo, review_path)
    receipt_reference = _working_artifact(repo, receipt_path)
    receipt_signature_reference = _working_artifact(repo, receipt_signature_path)
    candidate = {
        "schema_version": _schema_const("candidate.schema.json", "schema_version"),
        "candidate_id": "logic-candidate",
        "release_manifest_sha256": release_sha,
        "private_opportunity_ledger_canonical_sha256": private_ledger_sha,
        "freeze_commit": freeze_commit,
        "freeze_manifest": freeze_reference,
        "review_ledger": review_reference,
        "run_start_receipt": receipt_reference,
        "run_start_signature": receipt_signature_reference,
        "records": [],
    }
    candidate_path = "candidate/result.json"
    _write_json(repo, candidate_path, candidate)
    result_commit = _commit(repo, "logic result")
    candidate_reference = _committed_artifact(repo, result_commit, candidate_path)
    review_reference = _committed_artifact(repo, result_commit, review_path)
    receipt_reference = _committed_artifact(repo, result_commit, receipt_path)
    receipt_signature_reference = _committed_artifact(
        repo, result_commit, receipt_signature_path
    )

    run_manifest = {
        "schema_version": _schema_const(
            "run-result-manifest.schema.json", "schema_version"
        ),
        "contract_version": _schema_const(
            "run-result-manifest.schema.json", "contract_version"
        ),
        "release_manifest_sha256": release_sha,
        "trusted_run_attestors_canonical_sha256": (
            trusted_completion.canonical_sha256(run_policy)
        ),
        "runtime": runtime_binding,
        "result_commit": result_commit,
        "freeze_commit": freeze_commit,
        "freeze_manifest": freeze_reference,
        "candidate_result": candidate_reference,
        "review_ledger": review_reference,
        "run_start_receipt": receipt_reference,
        "run_start_signature": receipt_signature_reference,
        "attestor_key_id": run_key_id,
    }
    run_manifest_path = "candidate/run-result-manifest.json"
    _write_json(repo, run_manifest_path, run_manifest)
    run_manifest_reference = _working_artifact(repo, run_manifest_path)
    source_group = {
        "source_export_group_id": "logic-export-1",
        "export": _committed_artifact(repo, freeze_commit, export_path),
        "trusted_export_attestation": _committed_artifact(
            repo, freeze_commit, export_attestation_path
        ),
        "trusted_export_signature": _committed_artifact(
            repo, freeze_commit, export_signature_path
        ),
    }
    completion = {
        "schema_version": _schema_const(
            "run-completion-attestation.schema.json", "schema_version"
        ),
        "contract_version": _schema_const(
            "run-completion-attestation.schema.json", "contract_version"
        ),
        "signature_context": trusted_completion.COMPLETION_SIGNATURE_CONTEXT,
        "release_manifest_sha256": release_sha,
        "trusted_run_attestors_canonical_sha256": (
            trusted_completion.canonical_sha256(run_policy)
        ),
        "trusted_source_exporters_canonical_sha256": (
            trusted_completion.canonical_sha256(source_policy)
        ),
        "attestor_id": "logic-run-attestor",
        "attestor_key_id": run_key_id,
        "candidate_id": "logic-candidate",
        "invocation_id": "logic-invocation-1",
        "runtime": runtime_binding,
        "run_start_receipt": receipt_reference,
        "run_start_signature": receipt_signature_reference,
        "freeze_commit": freeze_commit,
        "freeze_manifest": freeze_reference,
        "freeze_nonce": freeze["run_nonce"],
        "result_commit": result_commit,
        "result_manifest": run_manifest_reference,
        "candidate_output": candidate_reference,
        "review_ledger": review_reference,
        "authority_source_exports": [source_group],
        "completed_at_utc": "2026-08-29T00:02:00+00:00",
    }
    completion_path = "candidate/run-completion-attestation.json"
    completion_signature_path = "candidate/run-completion-attestation.sig"
    completion_raw = _write_json(repo, completion_path, completion)
    _write_bytes(repo, completion_signature_path, run_private.sign(completion_raw))
    audit_commit = _commit(repo, "logic completion")
    return {
        "repo": repo,
        "release_sha": release_sha,
        "private_ledger_sha": private_ledger_sha,
        "run_private": run_private,
        "other_run_private": other_run_private,
        "other_run_key_id": other_run_key_id,
        "run_manifest_path": run_manifest_path,
        "completion": completion,
        "completion_path": completion_path,
        "completion_signature_path": completion_signature_path,
        "run_start_signature": receipt_signature_reference,
        "prompt_audit_signature": prompt_audit_signature_reference,
        "audit_commit": audit_commit,
    }


def _verify_completion(case: dict) -> dict:
    return trusted_completion.verify_trusted_completion(
        case["repo"],
        case["audit_commit"],
        case["run_manifest_path"],
        case["completion_path"],
        case["completion_signature_path"],
        case["release_sha"],
        schema_root=SCHEMAS,
        production=False,
    )


def _replace_signed_completion(
    case: dict, completion: dict, private_key: Ed25519PrivateKey, message: str
) -> None:
    raw = _write_json(case["repo"], case["completion_path"], completion)
    _write_bytes(
        case["repo"],
        case["completion_signature_path"],
        private_key.sign(raw),
    )
    case["audit_commit"] = _commit(case["repo"], message)


def test_signed_completion_authenticates_the_exact_three_commit_chain(
    tmp_path: Path,
) -> None:
    case = _completion_case(tmp_path)
    verified = _verify_completion(case)
    assert verified["status"] == "VERIFIED"
    assert verified["candidate_id"] == "logic-candidate"
    assert verified["invocation_id"] == "logic-invocation-1"
    assert verified["trusted_attestor_id"] == "logic-run-attestor"
    assert [
        row["source_export_group_id"]
        for row in verified["authority_source_exports"]
    ] == ["logic-export-1"]


def test_run_binding_keeps_start_signature_distinct_from_prompt_audit_signature(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _completion_case(tmp_path)

    monkeypatch.setattr(
        compare_candidate,
        "_load_trusted_attestor_policy",
        lambda repo, schema_root: trusted_completion._load_run_attestor_policy(
            repo, schema_root, production=False
        ),
    )
    monkeypatch.setattr(
        compare_candidate,
        "load_source_exporter_policy",
        lambda repo, schema_root, production=True: (
            source_exports.load_source_exporter_policy(
                repo, schema_root, production=False
            )
        ),
    )

    def verify_completion_for_test(*args, **kwargs):
        kwargs["production"] = False
        return trusted_completion.verify_trusted_completion(*args, **kwargs)

    def authenticate_export_for_test(**kwargs):
        kwargs["production"] = False
        return source_exports.authenticate_source_export(**kwargs)

    monkeypatch.setattr(
        compare_candidate, "verify_trusted_completion", verify_completion_for_test
    )
    monkeypatch.setattr(
        compare_candidate, "authenticate_source_export", authenticate_export_for_test
    )
    loaded = compare_candidate._load_candidate_run(
        case["repo"],
        case["audit_commit"],
        case["run_manifest_path"],
        case["completion_path"],
        case["completion_signature_path"],
        case["release_sha"],
        case["private_ledger_sha"],
        SCHEMAS,
    )
    run_binding = loaded[5]
    assert case["run_start_signature"] != case["prompt_audit_signature"]
    assert run_binding["run_start_signature"] == case["run_start_signature"]


def test_signed_completion_rejects_a_different_invocation_chain(
    tmp_path: Path,
) -> None:
    case = _completion_case(tmp_path)
    changed = copy.deepcopy(case["completion"])
    changed["invocation_id"] = "different-logic-invocation"
    _replace_signed_completion(case, changed, case["run_private"], "wrong invocation")
    with pytest.raises(candidate_git.CandidateGitError, match="invocation_id"):
        _verify_completion(case)


def test_signed_completion_rejects_runtime_binding_drift(tmp_path: Path) -> None:
    case = _completion_case(tmp_path)
    changed = copy.deepcopy(case["completion"])
    changed["runtime"]["python"]["version"] = "3.12.12"
    _replace_signed_completion(case, changed, case["run_private"], "wrong runtime")
    with pytest.raises(
        (candidate_git.CandidateGitError, schema_validation.SchemaValidationError),
        match="runtime|3.12.13",
    ):
        _verify_completion(case)


def test_signed_completion_rejects_a_different_trusted_attestor(
    tmp_path: Path,
) -> None:
    case = _completion_case(tmp_path)
    changed = copy.deepcopy(case["completion"])
    changed["attestor_id"] = "other-logic-run-attestor"
    changed["attestor_key_id"] = case["other_run_key_id"]
    _replace_signed_completion(
        case, changed, case["other_run_private"], "wrong completion attestor"
    )
    with pytest.raises(candidate_git.CandidateGitError, match="attestor key mismatch"):
        _verify_completion(case)


def test_signed_completion_rejects_changed_source_export_binding(
    tmp_path: Path,
) -> None:
    case = _completion_case(tmp_path)
    changed = copy.deepcopy(case["completion"])
    changed["authority_source_exports"][0]["export"]["sha256"] = "d" * 64
    _replace_signed_completion(case, changed, case["run_private"], "wrong source export")
    with pytest.raises(candidate_git.CandidateGitError, match="differs from freeze"):
        _verify_completion(case)


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("result_manifest", "result-manifest path/hash/blob"),
        ("candidate_output", "exact candidate_output"),
        ("review_ledger", "exact review_ledger"),
        ("freeze_manifest", "exact freeze_manifest"),
    ],
)
def test_signed_completion_rejects_changed_core_artifact_bindings(
    tmp_path: Path, field: str, message: str
) -> None:
    case = _completion_case(tmp_path)
    changed = copy.deepcopy(case["completion"])
    changed[field]["sha256"] = "e" * 64
    _replace_signed_completion(case, changed, case["run_private"], f"wrong {field}")
    with pytest.raises(candidate_git.CandidateGitError, match=message):
        _verify_completion(case)


def test_completion_signature_cannot_be_reused_after_attestation_mutation(
    tmp_path: Path,
) -> None:
    case = _completion_case(tmp_path)
    changed = copy.deepcopy(case["completion"])
    changed["completed_at_utc"] = "2026-08-29T00:03:00+00:00"
    _write_json(case["repo"], case["completion_path"], changed)
    case["audit_commit"] = _commit(case["repo"], "unsigned completion mutation")
    with pytest.raises(candidate_git.CandidateGitError, match="completion Ed25519"):
        _verify_completion(case)


def test_ephemeral_run_attestor_registry_is_rejected_in_production(
    tmp_path: Path,
) -> None:
    case = _completion_case(tmp_path)
    with pytest.raises(candidate_git.CandidateGitError, match="test-only"):
        trusted_completion.verify_trusted_completion(
            case["repo"],
            case["audit_commit"],
            case["run_manifest_path"],
            case["completion_path"],
            case["completion_signature_path"],
            case["release_sha"],
            schema_root=SCHEMAS,
        )
