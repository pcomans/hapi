"""Verify a signed, release-trusted completion chain for one candidate run."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from candidate_git import (
    CandidateGitError,
    blob_oid,
    ed25519_key_id,
    is_ancestor,
    normalize_relative_path,
    read_authenticated_bytes,
    read_authenticated_json,
    read_bytes,
    resolve_commit,
    verify_ed25519_signature,
)
from schema_validation import validate_schema
from runtime_attestation import build_runtime_attestation
from source_exports import (
    authenticate_source_export,
    load_source_exporter_policy,
)


TRUSTED_RUN_ATTESTORS_RELATIVE = (
    "docs/evaluations/site-graph-v0/trusted-run-attestors.json"
)
COMPLETION_SIGNATURE_CONTEXT = "hapi-site-graph-v0-run-completion/1"
SOURCE_ROLE_TO_FIELD = {
    "authority_source_export": "export",
    "authority_source_export_attestation": "trusted_export_attestation",
    "authority_source_export_signature": "trusted_export_signature",
}
ARTIFACT_FIELDS = ("path", "sha256", "git_blob_oid")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _artifact(entry: dict) -> dict:
    return {field: entry[field] for field in ARTIFACT_FIELDS}


def _read_unbound_artifact(
    repo: Path, commit: str, relative: str
) -> tuple[bytes, dict]:
    relative = normalize_relative_path(relative)
    raw = read_bytes(repo, commit, relative)
    return raw, {
        "path": relative,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_oid": blob_oid(repo, commit, relative),
    }


def _load_json_bytes(raw: bytes, label: str) -> dict:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CandidateGitError(f"{label} is not JSON") from error
    if not isinstance(value, dict):
        raise CandidateGitError(f"{label} must be a JSON object")
    return value


def _load_run_attestor_policy(
    repo: Path, schema_root: Path, *, production: bool = True
) -> tuple[dict, dict]:
    path = repo / TRUSTED_RUN_ATTESTORS_RELATIVE
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise CandidateGitError("release-pinned run-attestor policy is unavailable") from error
    policy = _load_json_bytes(raw, "release-pinned run-attestor policy")
    validate_schema(
        policy,
        schema_root / "trusted-run-attestors.schema.json",
        "release-pinned trusted run attestors",
    )
    if production and policy["registry_scope"] != "production_release":
        raise CandidateGitError("test-only run-attestor registry rejected in production")
    if policy["status"] != "CONFIGURED":
        raise CandidateGitError(
            "trusted completion blocked: trusted run attestors are NOT_CONFIGURED"
        )
    attestor_ids = [row["attestor_id"] for row in policy["attestors"]]
    key_ids = [row["key_id"] for row in policy["attestors"]]
    if len(attestor_ids) != len(set(attestor_ids)) or len(key_ids) != len(
        set(key_ids)
    ):
        raise CandidateGitError("trusted run-attestor IDs and keys must be unique")
    for attestor in policy["attestors"]:
        if ed25519_key_id(attestor["public_key_base64"]) != attestor["key_id"]:
            raise CandidateGitError(
                f"trusted run-attestor key ID mismatch: {attestor['attestor_id']}"
            )
    return policy, {
        "path": TRUSTED_RUN_ATTESTORS_RELATIVE,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_sha256": canonical_sha256(policy),
    }


def _aware_datetime(value: str, label: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError as error:
        raise CandidateGitError(f"{label} is not an RFC 3339 timestamp") from error
    if parsed.tzinfo is None:
        raise CandidateGitError(f"{label} must include a UTC offset")
    return parsed


def _verified_runtime_binding(repo: Path) -> dict:
    """Read the release-pinned expectation and verify the executing environment."""
    snapshot_path = repo / "docs/evaluations/site-graph-v0/input-snapshot.json"
    try:
        snapshot = json.loads(snapshot_path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise CandidateGitError(
            "release input snapshot is unavailable for candidate runtime verification"
        ) from error
    try:
        attestation = build_runtime_attestation(repo, snapshot)
    except RuntimeError as error:
        raise CandidateGitError(str(error)) from error
    return {
        "python": attestation["python"],
        "dependency_lock": attestation["dependency_lock"],
    }


def _require_distinct_paths(references: list[dict], label: str) -> None:
    paths = [reference["path"] for reference in references]
    if len(paths) != len(set(paths)):
        raise CandidateGitError(f"{label} artifact paths must be unique")


def _verify_freeze_policy_bindings(
    *,
    repo: Path,
    freeze_commit: str,
    freeze: dict,
    run_policy: dict,
    run_policy_metadata: dict,
    source_policy: dict,
    source_policy_metadata: dict,
) -> None:
    run_binding = freeze["trusted_run_attestors"]
    frozen_run_policy, frozen_run_metadata = read_authenticated_json(
        repo,
        freeze_commit,
        run_binding["path"],
        expected_sha256=run_binding["raw_sha256"],
        expected_blob_oid=run_binding["git_blob_oid"],
    )
    if frozen_run_policy != run_policy:
        raise CandidateGitError("freeze used a different trusted run-attestor policy")
    if (
        run_binding["path"] != run_policy_metadata["path"]
        or run_binding["raw_sha256"] != run_policy_metadata["raw_sha256"]
        or run_binding["canonical_sha256"]
        != run_policy_metadata["canonical_sha256"]
        or run_binding["status"] != "CONFIGURED"
        or run_binding["attestor_key_ids"]
        != sorted(row["key_id"] for row in run_policy["attestors"])
        or frozen_run_metadata["git_blob_oid"] != run_binding["git_blob_oid"]
    ):
        raise CandidateGitError("freeze trusted run-attestor binding mismatch")

    source_binding = freeze["trusted_source_exporters"]
    frozen_source_policy, frozen_source_metadata = read_authenticated_json(
        repo,
        freeze_commit,
        source_binding["path"],
        expected_sha256=source_binding["raw_sha256"],
        expected_blob_oid=source_binding["git_blob_oid"],
    )
    if frozen_source_policy != source_policy:
        raise CandidateGitError("freeze used a different trusted source-exporter policy")
    if (
        source_binding["path"] != source_policy_metadata["path"]
        or source_binding["raw_sha256"] != source_policy_metadata["raw_sha256"]
        or source_binding["canonical_sha256"]
        != source_policy_metadata["canonical_sha256"]
        or source_binding["status"] != "CONFIGURED"
        or source_binding["exporter_key_ids"]
        != sorted(row["key_id"] for row in source_policy["exporters"])
        or frozen_source_metadata["git_blob_oid"] != source_binding["git_blob_oid"]
    ):
        raise CandidateGitError("freeze trusted source-exporter binding mismatch")


def _verify_authority_source_exports(
    *,
    repo: Path,
    freeze_commit: str,
    freeze: dict,
    completion: dict,
    schema_root: Path,
    source_policy: dict,
    production: bool,
) -> list[dict]:
    frozen_groups: dict[str, dict[str, dict]] = defaultdict(dict)
    for entry in freeze["files"]:
        role = entry["role"]
        if role not in SOURCE_ROLE_TO_FIELD:
            continue
        group_id = entry.get("source_export_group_id")
        if not isinstance(group_id, str) or not group_id:
            raise CandidateGitError("source-export freeze entry lacks its group ID")
        if role in frozen_groups[group_id]:
            raise CandidateGitError(
                f"duplicate {role} in source-export freeze group {group_id}"
            )
        frozen_groups[group_id][role] = entry
    if not frozen_groups:
        raise CandidateGitError("freeze has no authenticated authority source exports")
    required_roles = set(SOURCE_ROLE_TO_FIELD)
    incomplete = {
        group_id: sorted(required_roles - set(entries))
        for group_id, entries in frozen_groups.items()
        if set(entries) != required_roles
    }
    if incomplete:
        raise CandidateGitError(
            f"incomplete source-export freeze groups: {json.dumps(incomplete, sort_keys=True)}"
        )

    completion_groups = completion["authority_source_exports"]
    completion_ids = [row["source_export_group_id"] for row in completion_groups]
    if completion_ids != sorted(completion_ids) or len(completion_ids) != len(
        set(completion_ids)
    ):
        raise CandidateGitError(
            "completion source-export group IDs must be sorted and unique"
        )
    if set(completion_ids) != set(frozen_groups):
        raise CandidateGitError("completion source-export census differs from freeze")

    all_references = [
        row[field]
        for row in completion_groups
        for field in SOURCE_ROLE_TO_FIELD.values()
    ]
    _require_distinct_paths(all_references, "completion source-export")
    verified = []
    export_invocation_ids: set[str] = set()
    for group in completion_groups:
        group_id = group["source_export_group_id"]
        frozen = frozen_groups[group_id]
        for role, field in SOURCE_ROLE_TO_FIELD.items():
            if group[field] != _artifact(frozen[role]):
                raise CandidateGitError(
                    f"completion {field} differs from freeze group {group_id}"
                )

        export_reference = group["export"]
        export_raw, export_metadata = read_authenticated_bytes(
            repo,
            freeze_commit,
            export_reference["path"],
            expected_sha256=export_reference["sha256"],
            expected_blob_oid=export_reference["git_blob_oid"],
        )
        export = _load_json_bytes(export_raw, f"authority source export {group_id}")
        validate_schema(
            export,
            schema_root / "authority-source-export.schema.json",
            f"authority source export {group_id}",
        )

        attestation_reference = group["trusted_export_attestation"]
        attestation_raw, _ = read_authenticated_bytes(
            repo,
            freeze_commit,
            attestation_reference["path"],
            expected_sha256=attestation_reference["sha256"],
            expected_blob_oid=attestation_reference["git_blob_oid"],
        )
        export_attestation = _load_json_bytes(
            attestation_raw, f"authority source-export attestation {group_id}"
        )
        validate_schema(
            export_attestation,
            schema_root / "authority-source-export-attestation.schema.json",
            f"authority source-export attestation {group_id}",
        )
        if export_attestation["source_export_id"] != group_id:
            raise CandidateGitError(
                f"source-export attestation group-ID mismatch: {group_id}"
            )
        invocation_id = export_attestation["export_invocation_id"]
        if invocation_id in export_invocation_ids:
            raise CandidateGitError("source-export invocation IDs must be unique")
        export_invocation_ids.add(invocation_id)

        signature_reference = group["trusted_export_signature"]
        if (
            export_attestation["detached_signature_path"]
            != signature_reference["path"]
        ):
            raise CandidateGitError(
                f"source-export detached-signature path mismatch: {group_id}"
            )
        signature_raw, _ = read_authenticated_bytes(
            repo,
            freeze_commit,
            signature_reference["path"],
            expected_sha256=signature_reference["sha256"],
            expected_blob_oid=signature_reference["git_blob_oid"],
        )
        authenticate_source_export(
            source_export=export,
            source_export_raw=export_raw,
            source_export_metadata=export_metadata,
            attestation=export_attestation,
            attestation_raw=attestation_raw,
            signature_raw=signature_raw,
            policy=source_policy,
            production=production,
        )
        verified.append(
            {
                "source_export_group_id": group_id,
                "source_export_id": export["source_export_id"],
                "export_invocation_id": invocation_id,
                "artifacts": group,
            }
        )
    return verified


def verify_trusted_completion(
    repo: Path,
    audit_commit: str,
    run_result_manifest_path: str,
    completion_attestation_path: str,
    completion_signature_path: str,
    expected_release_manifest_sha256: str,
    *,
    schema_root: Path | None = None,
    production: bool = True,
) -> dict:
    """Authenticate one exact start-to-completion chain.

    Production callers must leave ``production`` true.  The false mode exists only
    so adversarial unit tests can exercise ephemeral keys in a test-only source
    exporter registry; it does not weaken run-attestor signature verification.
    """
    repo = repo.resolve()
    schema_root = (
        schema_root.resolve()
        if schema_root is not None
        else repo / "docs/evaluations/site-graph-v0/schemas"
    )
    audit_commit = resolve_commit(repo, audit_commit)
    run_result_manifest_path = normalize_relative_path(run_result_manifest_path)
    completion_attestation_path = normalize_relative_path(completion_attestation_path)
    completion_signature_path = normalize_relative_path(completion_signature_path)
    if len(
        {
            run_result_manifest_path,
            completion_attestation_path,
            completion_signature_path,
        }
    ) != 3:
        raise CandidateGitError(
            "result manifest, completion attestation, and signature paths must differ"
        )

    run_policy, run_policy_metadata = _load_run_attestor_policy(
        repo, schema_root, production=production
    )
    source_policy, source_policy_metadata = load_source_exporter_policy(
        repo, schema_root, production=production
    )
    run_manifest, run_manifest_metadata = read_authenticated_json(
        repo, audit_commit, run_result_manifest_path
    )
    validate_schema(
        run_manifest,
        schema_root / "run-result-manifest.schema.json",
        "candidate run-result manifest",
    )
    completion_raw, completion_metadata = _read_unbound_artifact(
        repo, audit_commit, completion_attestation_path
    )
    completion = _load_json_bytes(completion_raw, "run-completion attestation")
    validate_schema(
        completion,
        schema_root / "run-completion-attestation.schema.json",
        "run-completion attestation",
    )
    completion_signature_raw, completion_signature_metadata = _read_unbound_artifact(
        repo, audit_commit, completion_signature_path
    )

    expected_result_manifest_reference = {
        "path": run_result_manifest_path,
        **run_manifest_metadata,
    }
    if completion["result_manifest"] != expected_result_manifest_reference:
        raise CandidateGitError("completion result-manifest path/hash/blob mismatch")
    if completion["signature_context"] != COMPLETION_SIGNATURE_CONTEXT:
        raise CandidateGitError("run-completion signature context mismatch")
    attestor = next(
        (
            row
            for row in run_policy["attestors"]
            if row["attestor_id"] == completion["attestor_id"]
            and row["key_id"] == completion["attestor_key_id"]
        ),
        None,
    )
    if attestor is None:
        raise CandidateGitError(
            "run completion was not signed by a release-trusted attestor"
        )
    try:
        verify_ed25519_signature(
            completion_raw,
            completion_signature_raw,
            public_key_base64=attestor["public_key_base64"],
        )
    except CandidateGitError as error:
        raise CandidateGitError(
            "trusted run-completion Ed25519 signature verification failed"
        ) from error

    if run_manifest["release_manifest_sha256"] != expected_release_manifest_sha256:
        raise CandidateGitError("run-result manifest release binding mismatch")
    if run_manifest["contract_version"] != completion["contract_version"]:
        raise CandidateGitError("completion/result-manifest contract-version mismatch")
    common_bindings = {
        "release_manifest_sha256": expected_release_manifest_sha256,
        "trusted_run_attestors_canonical_sha256": run_policy_metadata[
            "canonical_sha256"
        ],
    }
    for field, expected in common_bindings.items():
        if run_manifest[field] != expected or completion[field] != expected:
            raise CandidateGitError(f"completion chain {field} binding mismatch")
    if (
        completion["trusted_source_exporters_canonical_sha256"]
        != source_policy_metadata["canonical_sha256"]
    ):
        raise CandidateGitError("completion source-exporter policy binding mismatch")
    if run_manifest["attestor_key_id"] != completion["attestor_key_id"]:
        raise CandidateGitError("completion/result-manifest attestor key mismatch")

    result_commit = resolve_commit(repo, run_manifest["result_commit"])
    freeze_commit = resolve_commit(repo, run_manifest["freeze_commit"])
    if completion["result_commit"] != result_commit:
        raise CandidateGitError("completion result-commit binding mismatch")
    if completion["freeze_commit"] != freeze_commit:
        raise CandidateGitError("completion freeze-commit binding mismatch")
    if freeze_commit == result_commit or not is_ancestor(
        repo, freeze_commit, result_commit
    ):
        raise CandidateGitError(
            "candidate freeze commit must be a distinct ancestor of result commit"
        )
    if result_commit == audit_commit or not is_ancestor(
        repo, result_commit, audit_commit
    ):
        raise CandidateGitError(
            "candidate result commit must be a distinct ancestor of completion commit"
        )

    candidate_reference = run_manifest["candidate_result"]
    review_reference = run_manifest["review_ledger"]
    receipt_reference = run_manifest["run_start_receipt"]
    start_signature_reference = run_manifest["run_start_signature"]
    freeze_reference = run_manifest["freeze_manifest"]
    _require_distinct_paths(
        [
            candidate_reference,
            review_reference,
            receipt_reference,
            start_signature_reference,
            freeze_reference,
        ],
        "completion chain",
    )
    for field, expected in (
        ("candidate_output", candidate_reference),
        ("review_ledger", review_reference),
        ("run_start_receipt", receipt_reference),
        ("run_start_signature", start_signature_reference),
        ("freeze_manifest", freeze_reference),
    ):
        if completion[field] != expected:
            raise CandidateGitError(f"completion exact {field} binding mismatch")

    candidate, _ = read_authenticated_json(
        repo,
        result_commit,
        candidate_reference["path"],
        expected_sha256=candidate_reference["sha256"],
        expected_blob_oid=candidate_reference["git_blob_oid"],
    )
    reviews, _ = read_authenticated_json(
        repo,
        result_commit,
        review_reference["path"],
        expected_sha256=review_reference["sha256"],
        expected_blob_oid=review_reference["git_blob_oid"],
    )
    receipt_raw, _ = read_authenticated_bytes(
        repo,
        result_commit,
        receipt_reference["path"],
        expected_sha256=receipt_reference["sha256"],
        expected_blob_oid=receipt_reference["git_blob_oid"],
    )
    start_signature_raw, _ = read_authenticated_bytes(
        repo,
        result_commit,
        start_signature_reference["path"],
        expected_sha256=start_signature_reference["sha256"],
        expected_blob_oid=start_signature_reference["git_blob_oid"],
    )
    receipt = _load_json_bytes(receipt_raw, "run-start receipt")
    validate_schema(candidate, schema_root / "candidate.schema.json", "candidate result")
    validate_schema(reviews, schema_root / "review-ledger.schema.json", "review ledger")
    validate_schema(
        receipt, schema_root / "run-start-receipt.schema.json", "run-start receipt"
    )
    if candidate["candidate_id"] != completion["candidate_id"]:
        raise CandidateGitError("completion candidate-ID binding mismatch")
    if candidate["review_ledger"] != review_reference:
        raise CandidateGitError("candidate exact review-ledger binding mismatch")
    if candidate["run_start_receipt"] != receipt_reference:
        raise CandidateGitError("candidate exact run-start receipt binding mismatch")
    if candidate["run_start_signature"] != start_signature_reference:
        raise CandidateGitError("candidate exact run-start signature binding mismatch")
    if (
        candidate["freeze_commit"] != freeze_commit
        or candidate["freeze_manifest"] != freeze_reference
    ):
        raise CandidateGitError("candidate exact freeze binding mismatch")

    freeze, _ = read_authenticated_json(
        repo,
        freeze_commit,
        freeze_reference["path"],
        expected_sha256=freeze_reference["sha256"],
        expected_blob_oid=freeze_reference["git_blob_oid"],
    )
    validate_schema(
        freeze,
        schema_root / "candidate-freeze-manifest.schema.json",
        "candidate freeze",
    )
    if freeze["contract_version"] != completion["contract_version"]:
        raise CandidateGitError("completion/freeze contract-version mismatch")
    _verify_freeze_policy_bindings(
        repo=repo,
        freeze_commit=freeze_commit,
        freeze=freeze,
        run_policy=run_policy,
        run_policy_metadata=run_policy_metadata,
        source_policy=source_policy,
        source_policy_metadata=source_policy_metadata,
    )
    for document, label in ((freeze, "freeze"), (candidate, "candidate")):
        if document["release_manifest_sha256"] != expected_release_manifest_sha256:
            raise CandidateGitError(f"{label} release binding mismatch")
        if document["candidate_id"] != completion["candidate_id"]:
            raise CandidateGitError(f"{label} candidate-ID binding mismatch")
    if completion["freeze_nonce"] != freeze["run_nonce"]:
        raise CandidateGitError("completion freeze-nonce binding mismatch")

    expected_receipt_bindings = {
        **common_bindings,
        "attestor_id": completion["attestor_id"],
        "attestor_key_id": completion["attestor_key_id"],
        "candidate_id": completion["candidate_id"],
        "invocation_id": completion["invocation_id"],
        "freeze_commit": freeze_commit,
        "freeze_manifest": freeze_reference,
        "freeze_nonce": freeze["run_nonce"],
        "signature_context": run_policy["signature_context"],
    }
    if receipt["contract_version"] != completion["contract_version"]:
        raise CandidateGitError("run-start/completion contract-version mismatch")
    for field, expected in expected_receipt_bindings.items():
        if receipt[field] != expected:
            raise CandidateGitError(f"run-start/completion {field} chain mismatch")
    if not (
        receipt["runtime"] == run_manifest["runtime"] == completion["runtime"]
    ):
        raise CandidateGitError(
            "run-start/result/completion runtime binding mismatch"
        )
    if production and completion["runtime"] != _verified_runtime_binding(repo):
        raise CandidateGitError(
            "candidate run runtime differs from the executing release environment"
        )
    verify_ed25519_signature(
        receipt_raw,
        start_signature_raw,
        public_key_base64=attestor["public_key_base64"],
    )
    started = _aware_datetime(receipt["started_at_utc"], "run-start time")
    completed = _aware_datetime(completion["completed_at_utc"], "completion time")
    if completed < started:
        raise CandidateGitError("run completion predates its signed start receipt")

    verified_exports = _verify_authority_source_exports(
        repo=repo,
        freeze_commit=freeze_commit,
        freeze=freeze,
        completion=completion,
        schema_root=schema_root,
        source_policy=source_policy,
        production=production,
    )
    return {
        "schema_version": "site-graph-v0-trusted-completion-verification/1",
        "status": "VERIFIED",
        "audit_commit": audit_commit,
        "freeze_commit": freeze_commit,
        "result_commit": result_commit,
        "candidate_id": completion["candidate_id"],
        "invocation_id": completion["invocation_id"],
        "trusted_attestor_id": attestor["attestor_id"],
        "trusted_attestor_key_id": attestor["key_id"],
        "runtime": completion["runtime"],
        "result_manifest": expected_result_manifest_reference,
        "completion_attestation": completion_metadata,
        "completion_signature": completion_signature_metadata,
        "authority_source_exports": verified_exports,
    }
