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
    read_authenticated_json,
    read_bytes,
    resolve_commit,
)
from integrity import EVALUATION_RELATIVE, verify_release
from schema_validation import validate_schema


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


def _validate_source_snapshot(snapshot: dict, path: str) -> None:
    records = snapshot["records"]
    completeness = snapshot["completeness"]
    if records != sorted(records, key=lambda row: row["source_record_id"]):
        raise RuntimeError(f"source snapshot records must be sorted by ID: {path}")
    record_ids = [row["source_record_id"] for row in records]
    if len(record_ids) != len(set(record_ids)):
        raise RuntimeError(f"source snapshot record IDs must be unique: {path}")
    if completeness["record_count"] != len(records):
        raise RuntimeError(f"source snapshot complete record count mismatch: {path}")
    if completeness["records_canonical_sha256"] != _canonical_sha256(records):
        raise RuntimeError(f"source snapshot complete-record hash mismatch: {path}")
    for row in records:
        for field in ("raw_source_types", "parent_ids", "child_ids", "authority_citations"):
            if row[field] != sorted(set(row[field])):
                raise RuntimeError(f"source snapshot {field} must be sorted and unique: {path}")


def generate(
    repo_root: Path,
    output: Path,
    hierarchy_path: str,
    relation_ledger_path: str,
    source_snapshot_paths: list[str],
    prompt_leakage_audit_paths: list[str],
    candidate_id: str,
    created_by: str,
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
    head = resolve_commit(repo_root, _git(repo_root, "rev-parse", "HEAD"))
    specs = [
        ("hierarchy", normalize_relative_path(hierarchy_path), "candidate-hierarchy.schema.json"),
        (
            "relation_ledger",
            normalize_relative_path(relation_ledger_path),
            "relation-ledger.schema.json",
        ),
        *[
            (
                "source_snapshot",
                normalize_relative_path(path),
                "candidate-source-snapshot.schema.json",
            )
            for path in source_snapshot_paths
        ],
    ]
    if not source_snapshot_paths:
        raise RuntimeError("at least one source snapshot is required")
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
        if role == "source_snapshot":
            _validate_source_snapshot(committed, relative)
        files.append(
            {
                "role": role,
                "path": relative,
                "sha256": metadata["sha256"],
                "git_blob_oid": blob_oid(repo_root, head, relative),
                "media_type": "application/json",
                "schema_version": committed["schema_version"],
            }
        )

    frozen_paths = set(paths)
    frozen_hashes = {entry["sha256"] for entry in files}
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
        prompt_reference = audit["prompt"]
        prompt_path = normalize_relative_path(prompt_reference["path"])
        if prompt_path in frozen_paths or audit_path == prompt_path:
            raise RuntimeError(f"candidate freeze prompt/audit path reused: {prompt_path}")
        prompt_raw = read_bytes(repo_root, head, prompt_path)
        if not prompt_raw.strip():
            raise RuntimeError(f"review prompt must be nonempty: {prompt_path}")
        prompt_sha = hashlib.sha256(prompt_raw).hexdigest()
        prompt_blob = blob_oid(repo_root, head, prompt_path)
        if (
            prompt_reference["sha256"] != prompt_sha
            or prompt_reference["git_blob_oid"] != prompt_blob
        ):
            raise RuntimeError(f"prompt leakage audit prompt binding mismatch: {audit_path}")
        working_prompt = repo_root / prompt_path
        if not working_prompt.is_file() or hashlib.sha256(working_prompt.read_bytes()).hexdigest() != prompt_sha:
            raise RuntimeError(f"review prompt has uncommitted changes: {prompt_path}")
        if audit_metadata["sha256"] in frozen_hashes or prompt_sha in frozen_hashes or audit_metadata["sha256"] == prompt_sha:
            raise RuntimeError("prompt and audit content hashes must be globally unique")
        frozen_paths.update({audit_path, prompt_path})
        frozen_hashes.update({audit_metadata["sha256"], prompt_sha})
        files.extend(
            [
                {
                    "role": "prompt_leakage_audit",
                    "path": audit_path,
                    "sha256": audit_metadata["sha256"],
                    "git_blob_oid": audit_metadata["git_blob_oid"],
                    "media_type": "application/json",
                    "schema_version": audit["schema_version"],
                },
                {
                    "role": "review_prompt",
                    "path": prompt_path,
                    "sha256": prompt_sha,
                    "git_blob_oid": prompt_blob,
                    "media_type": "text/plain",
                    "schema_version": None,
                },
            ]
        )
    value = {
        "schema_version": "site-graph-v0-candidate-freeze-manifest/2",
        "contract_version": "site-graph-v0/3",
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
    parser.add_argument("--source-snapshot-path", action="append", default=[])
    parser.add_argument("--prompt-leakage-audit-path", action="append", default=[])
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
                args.source_snapshot_path,
                args.prompt_leakage_audit_path,
                args.candidate_id,
                args.created_by,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
