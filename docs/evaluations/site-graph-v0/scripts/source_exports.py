"""Authenticate complete authority exports before candidate scope derivation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from candidate_git import CandidateGitError, ed25519_key_id, verify_ed25519_signature
from schema_validation import validate_schema


TRUSTED_SOURCE_EXPORTERS_RELATIVE = (
    "docs/evaluations/site-graph-v0/trusted-source-exporters.json"
)


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def validate_source_export_records(source_export: dict) -> None:
    if source_export.get("originating_museum") is not False:
        raise CandidateGitError(
            "authenticated authority source export must be non-originating-museum evidence"
        )
    records = source_export["records"]
    completeness = source_export["completeness"]
    if records != sorted(records, key=lambda row: row["source_record_id"]):
        raise CandidateGitError("authenticated source-export records are not sorted")
    record_ids = [row["source_record_id"] for row in records]
    if len(record_ids) != len(set(record_ids)):
        raise CandidateGitError("authenticated source-export record IDs are not unique")
    if completeness["record_count"] != len(records):
        raise CandidateGitError("authenticated source-export record count mismatch")
    if completeness["records_canonical_sha256"] != canonical_sha256(records):
        raise CandidateGitError("authenticated source-export canonical hash mismatch")
    for record in records:
        for field in (
            "aliases",
            "raw_source_types",
            "parent_ids",
            "child_ids",
            "authority_citations",
        ):
            if record[field] != sorted(set(record[field])):
                raise CandidateGitError(
                    f"authenticated source-export {field} is not sorted and unique"
                )
        if record["preferred_label"] in record["aliases"]:
            raise CandidateGitError(
                "authenticated source-export aliases repeat the preferred label"
            )


def validate_source_exporter_registry(
    policy: dict, *, production: bool
) -> dict[str, dict]:
    if production and policy["registry_scope"] != "production_release":
        raise CandidateGitError("test-only source-export registry rejected in production")
    if policy["status"] != "CONFIGURED":
        raise CandidateGitError(
            "production candidate comparison blocked: trusted source exporters are NOT_CONFIGURED"
        )
    exporters: dict[str, dict] = {}
    key_ids: set[str] = set()
    for exporter in policy["exporters"]:
        if exporter["exporter_id"] in exporters or exporter["key_id"] in key_ids:
            raise CandidateGitError("trusted source exporter IDs and keys must be unique")
        if ed25519_key_id(exporter["public_key_base64"]) != exporter["key_id"]:
            raise CandidateGitError(
                f"trusted source exporter key ID mismatch: {exporter['exporter_id']}"
            )
        exporters[exporter["exporter_id"]] = exporter
        key_ids.add(exporter["key_id"])
    return exporters


def load_source_exporter_policy(
    repo: Path, schema_root: Path, *, production: bool = True
) -> tuple[dict, dict]:
    path = repo / TRUSTED_SOURCE_EXPORTERS_RELATIVE
    raw = path.read_bytes()
    try:
        policy = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CandidateGitError("trusted source-export registry is not JSON") from error
    validate_schema(
        policy,
        schema_root / "trusted-source-exporters.schema.json",
        "release-pinned trusted source exporters",
    )
    validate_source_exporter_registry(policy, production=production)
    return policy, {
        "path": TRUSTED_SOURCE_EXPORTERS_RELATIVE,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_sha256": canonical_sha256(policy),
    }


def authenticate_source_export(
    *,
    source_export: dict,
    source_export_raw: bytes,
    source_export_metadata: dict,
    attestation: dict,
    attestation_raw: bytes,
    signature_raw: bytes,
    policy: dict,
    production: bool,
) -> dict:
    """Verify a detached trusted-exporter signature and every export binding."""
    try:
        parsed_export = json.loads(source_export_raw)
    except json.JSONDecodeError as error:
        raise CandidateGitError("authenticated source-export bytes are not JSON") from error
    if parsed_export != source_export:
        raise CandidateGitError("source-export object differs from authenticated exact bytes")
    try:
        parsed_attestation = json.loads(attestation_raw)
    except json.JSONDecodeError as error:
        raise CandidateGitError(
            "authenticated source-export attestation bytes are not JSON"
        ) from error
    if parsed_attestation != attestation:
        raise CandidateGitError(
            "source-export attestation object differs from authenticated exact bytes"
        )
    exporters = validate_source_exporter_registry(policy, production=production)
    exporter = exporters.get(attestation["exporter_id"])
    if exporter is None or exporter["key_id"] != attestation["exporter_key_id"]:
        raise CandidateGitError("source export was not signed by a registered exporter")
    if attestation["signature_context"] != policy["signature_context"]:
        raise CandidateGitError("source-export signature context mismatch")
    if attestation["trusted_source_exporters_canonical_sha256"] != canonical_sha256(
        policy
    ):
        raise CandidateGitError("source-export registry binding mismatch")
    verify_ed25519_signature(
        attestation_raw,
        signature_raw,
        public_key_base64=exporter["public_key_base64"],
    )
    reference = attestation["source_export"]
    for field in ("path", "sha256", "git_blob_oid"):
        if reference[field] != source_export_metadata[field]:
            raise CandidateGitError(f"source-export {field} binding mismatch")
    if reference["sha256"] != hashlib.sha256(source_export_raw).hexdigest():
        raise CandidateGitError("source-export raw-byte hash mismatch")
    if attestation["source_export_id"] != source_export["source_export_id"]:
        raise CandidateGitError("source-export ID binding mismatch")
    validate_source_export_records(source_export)
    completeness = source_export["completeness"]
    if (
        attestation["record_count"] != completeness["record_count"]
        or attestation["records_canonical_sha256"]
        != completeness["records_canonical_sha256"]
    ):
        raise CandidateGitError("source-export completeness attestation mismatch")
    return source_export
