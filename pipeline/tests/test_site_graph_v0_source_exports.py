"""Logic-only adversarial checks for authenticated candidate source exports."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "docs/evaluations/site-graph-v0/scripts"
SCHEMAS = REPO / "docs/evaluations/site-graph-v0/schemas"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import candidate_git  # noqa: E402
import schema_validation  # noqa: E402
import source_exports  # noqa: E402


def _raw(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _case() -> dict:
    private = Ed25519PrivateKey.generate()
    public_raw = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    public_base64 = base64.b64encode(public_raw).decode("ascii")
    policy = {
        "schema_version": "site-graph-v0-trusted-source-exporters/1",
        "registry_scope": "test_only",
        "status": "CONFIGURED",
        "signature_scheme": "ed25519",
        "signature_context": "hapi-site-graph-v0-authority-source-export/1",
        "configuration_rule": "logic-only signature test",
        "current_effect": "never production authority",
        "exporters": [
            {
                "exporter_id": "logic-exporter",
                "key_id": hashlib.sha256(public_raw).hexdigest(),
                "public_key_base64": public_base64,
                "trust_basis": "ephemeral test key",
            }
        ],
    }
    records = [
        {
            "source_record_id": "source-1",
            "target_id": "target-1",
            "preferred_label": "Neutral place one",
            "aliases": ["Neutral alias one"],
            "authority_identity_locator": "logic:target-1",
            "raw_source_types": ["archaeological-site"],
            "parent_ids": [],
            "child_ids": [],
            "authority_citations": ["logic:citation-1"],
        },
        {
            "source_record_id": "source-2",
            "target_id": "target-2",
            "preferred_label": "Neutral place two",
            "aliases": [],
            "authority_identity_locator": "logic:target-2",
            "raw_source_types": ["archaeological-site"],
            "parent_ids": [],
            "child_ids": [],
            "authority_citations": ["logic:citation-2"],
        },
    ]
    export = {
        "schema_version": "site-graph-v0-authority-source-export/2",
        "source_export_id": "logic-export-1",
        "authority_name": "logic authority",
        "source_kind": "logic-only",
        "originating_museum": False,
        "acquired_at_utc": "2026-08-29T00:00:00Z",
        "provenance": {
            "source_locator": "logic://authority/export",
            "acquisition_method": "purpose-built unit input",
            "producer_identity": "logic-exporter",
        },
        "completeness": {
            "coverage_statement": "all records in logic export",
            "known_incompleteness": ["not corpus evidence"],
            "record_selection_policy": "all_records_in_authenticated_source_export",
            "record_count": 2,
            "records_canonical_sha256": source_exports.canonical_sha256(records),
            "complete_for_candidate_target_derivation": True,
        },
        "records": records,
    }
    export_raw = _raw(export)
    metadata = {
        "path": "candidate/source-export.json",
        "sha256": hashlib.sha256(export_raw).hexdigest(),
        "git_blob_oid": "1" * 40,
    }
    attestation = {
        "schema_version": "site-graph-v0-authority-source-export-attestation/1",
        "signature_context": policy["signature_context"],
        "export_invocation_id": "2" * 64,
        "exporter_id": "logic-exporter",
        "exporter_key_id": policy["exporters"][0]["key_id"],
        "trusted_source_exporters_canonical_sha256": source_exports.canonical_sha256(
            policy
        ),
        "source_export_id": export["source_export_id"],
        "source_export": metadata,
        "detached_signature_path": "candidate/source-export.attestation.sig",
        "record_count": 2,
        "records_canonical_sha256": export["completeness"][
            "records_canonical_sha256"
        ],
    }
    attestation_raw = _raw(attestation)
    return {
        "private": private,
        "policy": policy,
        "export": export,
        "export_raw": export_raw,
        "metadata": metadata,
        "attestation": attestation,
        "attestation_raw": attestation_raw,
        "signature": private.sign(attestation_raw),
    }


def _authenticate(case: dict, *, production: bool = False) -> dict:
    schema_validation.validate_schema(
        case["policy"], SCHEMAS / "trusted-source-exporters.schema.json", "policy"
    )
    schema_validation.validate_schema(
        case["export"], SCHEMAS / "authority-source-export.schema.json", "export"
    )
    schema_validation.validate_schema(
        case["attestation"],
        SCHEMAS / "authority-source-export-attestation.schema.json",
        "attestation",
    )
    return source_exports.authenticate_source_export(
        source_export=case["export"],
        source_export_raw=case["export_raw"],
        source_export_metadata=case["metadata"],
        attestation=case["attestation"],
        attestation_raw=case["attestation_raw"],
        signature_raw=case["signature"],
        policy=case["policy"],
        production=production,
    )


def test_exact_signed_source_export_authenticates_only_in_logic_mode() -> None:
    case = _case()
    assert _authenticate(case)["source_export_id"] == "logic-export-1"
    with pytest.raises(candidate_git.CandidateGitError, match="test-only"):
        _authenticate(case, production=True)


def test_candidate_cannot_omit_a_signed_export_record() -> None:
    case = _case()
    case["export"]["records"].pop()
    with pytest.raises(candidate_git.CandidateGitError, match="differs from authenticated"):
        _authenticate(case)


def test_originating_museum_source_cannot_be_independent_authority_evidence() -> None:
    case = _case()
    case["export"]["originating_museum"] = True
    with pytest.raises(
        (candidate_git.CandidateGitError, schema_validation.SchemaValidationError),
        match="originating_museum|non-originating",
    ):
        _authenticate(case)


def test_candidate_cannot_replace_export_bytes_and_self_attest_new_hash() -> None:
    case = _case()
    changed = copy.deepcopy(case["export"])
    changed["records"][0]["target_id"] = "invented-target"
    case["export"] = changed
    case["export_raw"] = _raw(changed)
    case["metadata"]["sha256"] = hashlib.sha256(case["export_raw"]).hexdigest()
    case["attestation"]["source_export"] = case["metadata"]
    case["attestation_raw"] = _raw(case["attestation"])
    with pytest.raises(candidate_git.CandidateGitError, match="signature verification failed"):
        _authenticate(case)


def test_unsigned_attestation_object_cannot_override_signed_attestation_bytes() -> None:
    case = _case()
    case["attestation"] = copy.deepcopy(case["attestation"])
    case["attestation"]["record_count"] = 1
    with pytest.raises(
        candidate_git.CandidateGitError,
        match="attestation object differs from authenticated exact bytes",
    ):
        _authenticate(case)


def test_signed_export_requires_sorted_alias_census_distinct_from_preferred_label() -> None:
    case = _case()
    changed = copy.deepcopy(case["export"])
    changed["records"][0]["aliases"] = ["Zulu alias", "Alpha alias"]
    changed["completeness"]["records_canonical_sha256"] = (
        source_exports.canonical_sha256(changed["records"])
    )
    with pytest.raises(candidate_git.CandidateGitError, match="aliases is not sorted"):
        source_exports.validate_source_export_records(changed)

    changed["records"][0]["aliases"] = ["Neutral place one"]
    changed["completeness"]["records_canonical_sha256"] = (
        source_exports.canonical_sha256(changed["records"])
    )
    with pytest.raises(candidate_git.CandidateGitError, match="repeat the preferred"):
        source_exports.validate_source_export_records(changed)


def test_release_source_export_policy_fails_closed() -> None:
    with pytest.raises(candidate_git.CandidateGitError, match="NOT_CONFIGURED"):
        source_exports.load_source_exporter_policy(REPO, SCHEMAS)
