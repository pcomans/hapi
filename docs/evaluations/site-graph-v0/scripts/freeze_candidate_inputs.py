#!/usr/bin/env python3
"""Generate a pre-run candidate-input manifest from already committed bytes."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import secrets
import subprocess
from pathlib import Path

from candidate_git import (
    blob_oid,
    ed25519_key_id,
    normalize_relative_path,
    read_authenticated_bytes,
    read_authenticated_json,
    read_bytes,
    resolve_commit,
)
from integrity import EVALUATION_RELATIVE, verify_release
from schema_validation import validate_schema
from source_exports import (
    TRUSTED_SOURCE_EXPORTERS_RELATIVE,
    authenticate_source_export,
    validate_source_exporter_registry,
)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, check=False, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _prompt_audit_request_key(audit: dict) -> tuple[str, str, str, str, str, str]:
    return (
        audit["review_id"],
        audit["review_invocation_id"],
        audit["decision_key"],
        audit["decision_kind"],
        audit["prompt"]["path"],
        audit["input"]["path"],
    )


def _validate_semantic_prompt_audit_pair(
    semantic_audit: dict, deterministic_audit: dict
) -> None:
    """Require two audit methods to cover one identical frozen request."""
    if semantic_audit["audit_method"] != "independent_semantic_prompt_audit/1":
        raise RuntimeError("semantic prompt-audit path has the wrong method")
    if deterministic_audit["audit_method"] != "deterministic_prompt_leakage_guard/3":
        raise RuntimeError("deterministic prompt-audit path has the wrong method")
    if _prompt_audit_request_key(semantic_audit) != _prompt_audit_request_key(
        deterministic_audit
    ):
        raise RuntimeError("semantic prompt audit has no matching deterministic request")
    if semantic_audit["audit_id"] == deterministic_audit["audit_id"]:
        raise RuntimeError("semantic and deterministic prompt audits reuse an audit ID")
    for field in ("subject", "shuffle_provenance", "deterministic_guard"):
        if semantic_audit[field] != deterministic_audit[field]:
            raise RuntimeError(
                f"semantic/deterministic prompt audit {field} mismatch"
            )


def generate(
    repo_root: Path,
    output: Path,
    hierarchy_path: str,
    relation_ledger_path: str,
    source_export_attestation_paths: list[str],
    prompt_leakage_audit_paths: list[str],
    candidate_id: str,
    created_by: str,
    semantic_prompt_audit_paths: list[str] | None = None,
) -> dict:
    repo_root = repo_root.resolve()
    output = output.resolve()
    if output.exists():
        raise RuntimeError(f"refusing to overwrite candidate freeze manifest: {output}")
    if not output.parent.is_dir():
        raise RuntimeError(f"candidate freeze output parent does not exist: {output.parent}")
    release = verify_release(repo_root)
    evaluation_root = repo_root / EVALUATION_RELATIVE
    private_digest = json.loads(
        (evaluation_root / "private-ledger-digests.json").read_text(encoding="utf-8")
    )
    trusted_policy_path = evaluation_root / "trusted-run-attestors.json"
    trusted_policy_raw = trusted_policy_path.read_bytes()
    trusted_policy = json.loads(trusted_policy_raw)
    validate_schema(
        trusted_policy,
        evaluation_root / "schemas/trusted-run-attestors.schema.json",
        "release-pinned trusted run attestors",
    )
    if trusted_policy["status"] != "CONFIGURED":
        raise RuntimeError(
            "candidate freeze is blocked: release-pinned trusted run attestors are NOT_CONFIGURED"
        )
    attestor_ids = [row["attestor_id"] for row in trusted_policy["attestors"]]
    key_ids = [row["key_id"] for row in trusted_policy["attestors"]]
    if len(attestor_ids) != len(set(attestor_ids)) or len(key_ids) != len(set(key_ids)):
        raise RuntimeError("trusted run attestor IDs and key IDs must be unique")
    for attestor in trusted_policy["attestors"]:
        if ed25519_key_id(attestor["public_key_base64"]) != attestor["key_id"]:
            raise RuntimeError(
                f"trusted run attestor key ID mismatch: {attestor['attestor_id']}"
            )
    trusted_source_policy_path = repo_root / TRUSTED_SOURCE_EXPORTERS_RELATIVE
    trusted_source_policy_raw = trusted_source_policy_path.read_bytes()
    trusted_source_policy = json.loads(trusted_source_policy_raw)
    validate_schema(
        trusted_source_policy,
        evaluation_root / "schemas/trusted-source-exporters.schema.json",
        "release-pinned trusted source exporters",
    )
    source_exporters = validate_source_exporter_registry(
        trusted_source_policy, production=True
    )
    head = resolve_commit(repo_root, _git(repo_root, "rev-parse", "HEAD"))
    specs = [
        ("hierarchy", normalize_relative_path(hierarchy_path), "candidate-hierarchy.schema.json"),
        (
            "relation_ledger",
            normalize_relative_path(relation_ledger_path),
            "relation-ledger.schema.json",
        ),
    ]
    if not source_export_attestation_paths:
        raise RuntimeError("at least one authenticated authority source export is required")
    paths = [path for _, path, _ in specs]
    if len(paths) != len(set(paths)):
        raise RuntimeError("candidate freeze input paths must be unique")

    files = []
    for role, relative, schema_name in specs:
        working_path = repo_root / relative
        if not working_path.is_file():
            raise RuntimeError(f"candidate freeze input missing: {relative}")
        committed, metadata = read_authenticated_json(repo_root, head, relative)
        if hashlib.sha256(working_path.read_bytes()).hexdigest() != metadata["sha256"]:
            raise RuntimeError(f"candidate freeze input has uncommitted changes: {relative}")
        validate_schema(
            committed,
            evaluation_root / "schemas" / schema_name,
            f"candidate freeze input {relative}",
        )
        files.append(
            {
                "role": role,
                "source_export_group_id": None,
                "path": relative,
                "sha256": metadata["sha256"],
                "git_blob_oid": blob_oid(repo_root, head, relative),
                "media_type": "application/json",
                "schema_version": committed["schema_version"],
            }
        )

    frozen_paths = set(paths)
    frozen_hashes = {entry["sha256"] for entry in files}
    source_export_ids: set[str] = set()
    for attestation_path_value in source_export_attestation_paths:
        attestation_path = normalize_relative_path(attestation_path_value)
        if attestation_path in frozen_paths:
            raise RuntimeError(
                f"candidate freeze input path reused: {attestation_path}"
            )
        attestation, attestation_metadata = read_authenticated_json(
            repo_root, head, attestation_path
        )
        validate_schema(
            attestation,
            evaluation_root
            / "schemas/authority-source-export-attestation.schema.json",
            f"authority source-export attestation {attestation_path}",
        )
        source_export_id = attestation["source_export_id"]
        if source_export_id in source_export_ids:
            raise RuntimeError(f"duplicate source export ID: {source_export_id}")
        source_export_ids.add(source_export_id)
        export_reference = attestation["source_export"]
        export_path = normalize_relative_path(export_reference["path"])
        signature_path = normalize_relative_path(
            attestation["detached_signature_path"]
        )
        group_paths = {attestation_path, export_path, signature_path}
        if len(group_paths) != 3 or group_paths & frozen_paths:
            raise RuntimeError(
                f"authority source-export group paths must be unique: {source_export_id}"
            )
        source_export, export_metadata = read_authenticated_json(
            repo_root,
            head,
            export_path,
            expected_sha256=export_reference["sha256"],
            expected_blob_oid=export_reference["git_blob_oid"],
        )
        validate_schema(
            source_export,
            evaluation_root / "schemas/authority-source-export.schema.json",
            f"authority source export {export_path}",
        )
        signature_raw = read_bytes(repo_root, head, signature_path)
        signature_metadata = {
            "path": signature_path,
            "sha256": hashlib.sha256(signature_raw).hexdigest(),
            "git_blob_oid": blob_oid(repo_root, head, signature_path),
        }
        attestation_raw = read_bytes(repo_root, head, attestation_path)
        export_raw = read_bytes(repo_root, head, export_path)
        authenticate_source_export(
            source_export=source_export,
            source_export_raw=export_raw,
            source_export_metadata=export_metadata,
            attestation=attestation,
            attestation_raw=attestation_raw,
            signature_raw=signature_raw,
            policy=trusted_source_policy,
            production=True,
        )
        for group_path, group_sha in (
            (attestation_path, attestation_metadata["sha256"]),
            (export_path, export_metadata["sha256"]),
            (signature_path, signature_metadata["sha256"]),
        ):
            working = repo_root / group_path
            if not working.is_file() or hashlib.sha256(
                working.read_bytes()
            ).hexdigest() != group_sha:
                raise RuntimeError(
                    f"authority source-export input has uncommitted changes: {group_path}"
                )
            if group_sha in frozen_hashes:
                raise RuntimeError(
                    f"candidate freeze content hash reused: {group_path}"
                )
        files.extend(
            [
                {
                    "role": "authority_source_export",
                    "source_export_group_id": source_export_id,
                    **export_metadata,
                    "media_type": "application/json",
                    "schema_version": source_export["schema_version"],
                },
                {
                    "role": "authority_source_export_attestation",
                    "source_export_group_id": source_export_id,
                    **attestation_metadata,
                    "media_type": "application/json",
                    "schema_version": attestation["schema_version"],
                },
                {
                    "role": "authority_source_export_signature",
                    "source_export_group_id": source_export_id,
                    **signature_metadata,
                    "media_type": "application/octet-stream",
                    "schema_version": None,
                },
            ]
        )
        frozen_paths.update(group_paths)
        frozen_hashes.update(
            {
                attestation_metadata["sha256"],
                export_metadata["sha256"],
                signature_metadata["sha256"],
            }
        )
    semantic_prompt_audit_paths = semantic_prompt_audit_paths or []
    deterministic_audits_by_request: dict[
        tuple[str, str, str, str, str, str], dict
    ] = {}
    for audit_path_value in prompt_leakage_audit_paths:
        audit_path = normalize_relative_path(audit_path_value)
        if audit_path in frozen_paths:
            raise RuntimeError(f"candidate freeze input path reused: {audit_path}")
        audit, audit_metadata = read_authenticated_json(repo_root, head, audit_path)
        working_audit = repo_root / audit_path
        if not working_audit.is_file() or hashlib.sha256(working_audit.read_bytes()).hexdigest() != audit_metadata["sha256"]:
            raise RuntimeError(f"prompt audit has uncommitted changes: {audit_path}")
        validate_schema(
            audit,
            evaluation_root / "schemas/prompt-leakage-audit.schema.json",
            f"prompt leakage audit {audit_path}",
        )
        if audit["audit_method"] != "deterministic_prompt_leakage_guard/3":
            raise RuntimeError(
                f"deterministic prompt-audit path has the wrong method: {audit_path}"
            )
        audit_references = (
            ("review_prompt", audit["prompt"], "text/plain"),
            ("review_input", audit["input"], "application/octet-stream"),
            (
                "prompt_leakage_audit_signature",
                audit["authentication"]["signature"],
                "application/octet-stream",
            ),
        )
        referenced_paths = [
            normalize_relative_path(reference["path"])
            for _, reference, _ in audit_references
        ]
        if (
            len(referenced_paths) != len(set(referenced_paths))
            or audit_path in referenced_paths
            or set(referenced_paths) & frozen_paths
        ):
            raise RuntimeError(
                f"candidate freeze prompt/audit inputs are not path-unique: {audit_path}"
            )
        reference_entries = []
        for (role, reference, media_type), relative in zip(
            audit_references, referenced_paths, strict=True
        ):
            raw = read_bytes(repo_root, head, relative)
            if not raw.strip():
                raise RuntimeError(f"frozen review input must be nonempty: {relative}")
            if role == "prompt_leakage_audit_signature" and len(raw) != 64:
                raise RuntimeError(
                    f"prompt audit signature must be exactly 64 bytes: {relative}"
                )
            digest = hashlib.sha256(raw).hexdigest()
            git_blob = blob_oid(repo_root, head, relative)
            if reference["sha256"] != digest or reference["git_blob_oid"] != git_blob:
                raise RuntimeError(
                    f"prompt leakage audit {role} binding mismatch: {audit_path}"
                )
            working = repo_root / relative
            if not working.is_file() or hashlib.sha256(
                working.read_bytes()
            ).hexdigest() != digest:
                raise RuntimeError(f"frozen review input has uncommitted changes: {relative}")
            reference_entries.append(
                {
                    "role": role,
                    "source_export_group_id": None,
                    "path": relative,
                    "sha256": digest,
                    "git_blob_oid": git_blob,
                    "media_type": media_type,
                    "schema_version": None,
                }
            )
        group_hashes = {
            audit_metadata["sha256"],
            *(entry["sha256"] for entry in reference_entries),
        }
        if (
            len(group_hashes) != 1 + len(reference_entries)
            or bool(group_hashes & frozen_hashes)
        ):
            raise RuntimeError("prompt, input, audit, and signature hashes must be unique")
        frozen_paths.update({audit_path, *referenced_paths})
        frozen_hashes.update(group_hashes)
        files.extend(
            [
                {
                    "role": "prompt_leakage_audit",
                    "source_export_group_id": None,
                    "path": audit_path,
                    "sha256": audit_metadata["sha256"],
                    "git_blob_oid": audit_metadata["git_blob_oid"],
                    "media_type": "application/json",
                    "schema_version": audit["schema_version"],
                },
                *reference_entries,
            ]
        )
        request_key = _prompt_audit_request_key(audit)
        if request_key in deterministic_audits_by_request:
            raise RuntimeError("deterministic prompt audit request binding is duplicated")
        deterministic_audits_by_request[request_key] = audit

    semantic_request_keys: set[tuple[str, str, str, str, str, str]] = set()
    for audit_path_value in semantic_prompt_audit_paths:
        audit_path = normalize_relative_path(audit_path_value)
        if audit_path in frozen_paths:
            raise RuntimeError(f"candidate freeze input path reused: {audit_path}")
        audit, audit_metadata = read_authenticated_json(repo_root, head, audit_path)
        working_audit = repo_root / audit_path
        if (
            not working_audit.is_file()
            or hashlib.sha256(working_audit.read_bytes()).hexdigest()
            != audit_metadata["sha256"]
        ):
            raise RuntimeError(f"semantic prompt audit has uncommitted changes: {audit_path}")
        validate_schema(
            audit,
            evaluation_root / "schemas/prompt-leakage-audit.schema.json",
            f"semantic prompt audit {audit_path}",
        )
        if audit["audit_method"] != "independent_semantic_prompt_audit/1":
            raise RuntimeError(
                f"semantic prompt-audit path has the wrong method: {audit_path}"
            )
        request_key = _prompt_audit_request_key(audit)
        deterministic_audit = deterministic_audits_by_request.get(request_key)
        if deterministic_audit is None:
            raise RuntimeError(
                f"semantic prompt audit has no matching deterministic request: {audit_path}"
            )
        if request_key in semantic_request_keys:
            raise RuntimeError(
                f"semantic prompt audit request binding is duplicated: {audit_path}"
            )
        try:
            _validate_semantic_prompt_audit_pair(audit, deterministic_audit)
        except RuntimeError as error:
            raise RuntimeError(f"{error}: {audit_path}") from error
        for role, reference in (
            ("review_prompt", audit["prompt"]),
            ("review_input", audit["input"]),
        ):
            relative = normalize_relative_path(reference["path"])
            frozen_entry = next(
                (entry for entry in files if entry["path"] == relative), None
            )
            if (
                frozen_entry is None
                or frozen_entry["role"] != role
                or any(
                    reference[field] != frozen_entry[field]
                    for field in ("path", "sha256", "git_blob_oid")
                )
            ):
                raise RuntimeError(
                    f"semantic prompt audit does not reuse the exact frozen {role}: {audit_path}"
                )
        signature_reference = audit["authentication"]["signature"]
        signature_path = normalize_relative_path(signature_reference["path"])
        if signature_path == audit_path or signature_path in frozen_paths:
            raise RuntimeError(
                f"semantic prompt audit/signature path is reused: {audit_path}"
            )
        signature_raw = read_bytes(repo_root, head, signature_path)
        if len(signature_raw) != 64:
            raise RuntimeError(
                f"semantic prompt audit signature must be exactly 64 bytes: {signature_path}"
            )
        signature_sha256 = hashlib.sha256(signature_raw).hexdigest()
        signature_blob = blob_oid(repo_root, head, signature_path)
        if (
            signature_reference["sha256"] != signature_sha256
            or signature_reference["git_blob_oid"] != signature_blob
        ):
            raise RuntimeError(
                f"semantic prompt audit signature binding mismatch: {audit_path}"
            )
        working_signature = repo_root / signature_path
        if (
            not working_signature.is_file()
            or hashlib.sha256(working_signature.read_bytes()).hexdigest()
            != signature_sha256
        ):
            raise RuntimeError(
                f"semantic prompt audit signature has uncommitted changes: {signature_path}"
            )
        if (
            audit_metadata["sha256"] == signature_sha256
            or audit_metadata["sha256"] in frozen_hashes
            or signature_sha256 in frozen_hashes
        ):
            raise RuntimeError("semantic prompt audit and signature hashes must be unique")
        files.extend(
            [
                {
                    "role": "semantic_prompt_audit",
                    "source_export_group_id": None,
                    "path": audit_path,
                    "sha256": audit_metadata["sha256"],
                    "git_blob_oid": audit_metadata["git_blob_oid"],
                    "media_type": "application/json",
                    "schema_version": audit["schema_version"],
                },
                {
                    "role": "semantic_prompt_audit_signature",
                    "source_export_group_id": None,
                    "path": signature_path,
                    "sha256": signature_sha256,
                    "git_blob_oid": signature_blob,
                    "media_type": "application/octet-stream",
                    "schema_version": None,
                },
            ]
        )
        frozen_paths.update({audit_path, signature_path})
        frozen_hashes.update({audit_metadata["sha256"], signature_sha256})
        semantic_request_keys.add(request_key)
    if semantic_request_keys != set(deterministic_audits_by_request):
        raise RuntimeError(
            "every deterministic prompt audit requires exactly one semantic prompt audit"
        )
    value = {
        "schema_version": "site-graph-v0-candidate-freeze-manifest/3",
        "contract_version": "site-graph-v0/4",
        "candidate_id": candidate_id,
        "run_nonce": secrets.token_hex(32),
        "release_manifest_sha256": release["manifest_sha256"],
        "private_opportunity_ledger_canonical_sha256": private_digest["ledgers"][
            "private_opportunity_membership"
        ]["canonical_json_sha256"],
        "trusted_run_attestors": {
            "path": "docs/evaluations/site-graph-v0/trusted-run-attestors.json",
            "raw_sha256": hashlib.sha256(trusted_policy_raw).hexdigest(),
            "git_blob_oid": blob_oid(
                repo_root, head, "docs/evaluations/site-graph-v0/trusted-run-attestors.json"
            ),
            "canonical_sha256": _canonical_sha256(trusted_policy),
            "status": trusted_policy["status"],
            "attestor_key_ids": sorted(key_ids),
        },
        "trusted_source_exporters": {
            "path": TRUSTED_SOURCE_EXPORTERS_RELATIVE,
            "raw_sha256": hashlib.sha256(trusted_source_policy_raw).hexdigest(),
            "git_blob_oid": blob_oid(
                repo_root, head, TRUSTED_SOURCE_EXPORTERS_RELATIVE
            ),
            "canonical_sha256": _canonical_sha256(trusted_source_policy),
            "status": trusted_source_policy["status"],
            "exporter_key_ids": sorted(
                exporter["key_id"]
                for exporter in trusted_source_policy["exporters"]
            ),
        },
        "created_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "created_by": created_by,
        "provenance": {
            "input_commit": head,
            "method": "validated committed Git blobs before manifest generation",
            "timing_policy": (
                "the manifest must be committed as the distinct freeze commit before any "
                "candidate result commit; comparator gates Git ancestry, not timestamps"
            ),
        },
        "files": sorted(files, key=lambda item: (item["role"], item["path"])),
    }
    validate_schema(
        value,
        evaluation_root / "schemas/candidate-freeze-manifest.schema.json",
        "candidate freeze manifest",
    )
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    return {
        "output": str(output),
        "input_commit": head,
        "file_count": len(files),
        "candidate_id": candidate_id,
        "run_nonce": value["run_nonce"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hierarchy-path", required=True)
    parser.add_argument("--relation-ledger-path", required=True)
    parser.add_argument(
        "--source-export-attestation-path", action="append", default=[]
    )
    parser.add_argument("--prompt-leakage-audit-path", action="append", default=[])
    parser.add_argument("--semantic-prompt-audit-path", action="append", default=[])
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--created-by", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            generate(
                args.repo_root,
                args.output,
                args.hierarchy_path,
                args.relation_ledger_path,
                args.source_export_attestation_path,
                args.prompt_leakage_audit_path,
                args.candidate_id,
                args.created_by,
                semantic_prompt_audit_paths=args.semantic_prompt_audit_path,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
