#!/usr/bin/env python3
"""Apply exact private mention corrections without rewriting the frozen ITT."""

from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from candidate_git import (
    blob_oid,
    is_ancestor,
    normalize_relative_path,
    read_authenticated_bytes,
    read_bytes,
    resolve_commit,
)
from build_baseline import (
    build_metrics,
    build_opportunity_queue,
    canonical_json_sha256,
    gzip_ledger_digest,
    read_gzip_jsonl,
    read_json,
    resolution_state,
    sha256,
    validate_site_mention,
    write_gzip_jsonl,
    write_json,
)
from contract_constants import MINIMUM_AFFECTED_FRACTION, MUSEUMS, PAIRS
from integrity import verify_release
from metrics_core import partition_scopes, ratio
from private_ledgers import verify_private_ledgers
from review_auth import (
    ArtifactUsageTracker,
    authenticate_review_artifact,
    canonical_json_bytes,
    canonical_sha256,
    require_distinct_registered_reviewers,
    strict_json_object,
    validate_reviewer_registry,
)
from schema_validation import validate_schema


DERIVED_RECORD_FIELDS = (
    "extracted_site_text_evidence",
    "site_mention_count",
    "site_mention_status_counts",
    "baseline_resolution_state",
    "baseline_site_target_ids",
    "baseline_site_target_scope_counts",
    "baseline_record_scope",
    "has_any_ambiguity",
    "has_blocking_ambiguity",
    "has_any_unmatched_expression",
)

CORRECTION_SCHEMA_VERSION = "site-graph-v0-correction-ledger/4"
CORRECTION_POLICY_VERSION = "site-graph-v0-correction-policy/4"
CORRECTION_EVIDENCE_VERSION = "site-graph-v0-correction-evidence-source/1"
CORRECTION_REGISTRATION_VERSION = "site-graph-v0-correction-chain-registration/1"
CORRECTION_DECISION_KIND = "correction_support"
CORRECTION_POLICY_RELATIVE = "docs/evaluations/site-graph-v0/correction-policy.json"
RELEASE_MANIFEST_RELATIVE = (
    "docs/evaluations/site-graph-v0/release-manifest.json"
)
TRUSTED_REVIEWERS_RELATIVE = (
    "docs/evaluations/site-graph-v0/trusted-reviewers.json"
)


def record_hash(correction: dict) -> str:
    value = {key: child for key, child in correction.items() if key != "record_sha256"}
    return canonical_json_sha256(value)


def correction_decision_hash(correction: dict) -> str:
    """Hash the complete reviewable decision without its later Git-commit binding.

    Review artifacts and their signatures live in ``decision_commit``.  Including
    that commit in the signed statement would be circular because the commit ID also
    depends on those review bytes.  The immutable ledger record subsequently binds
    the signed decision to that exact commit and to the previous chain hash.
    """
    return canonical_json_sha256(
        {
            key: value
            for key, value in correction.items()
            if key not in {"decision_commit", "record_sha256"}
        }
    )


def correction_review_subject(ledger: dict, correction: dict) -> dict:
    """Bind a signed correction to one chain and exact private baseline inputs."""
    return {
        "chain_id": ledger["chain_id"],
        "private_record_evidence_canonical_sha256": ledger[
            "private_record_evidence_canonical_sha256"
        ],
        "private_opportunity_source_canonical_sha256": ledger[
            "private_opportunity_source_canonical_sha256"
        ],
        "correction_id": correction["correction_id"],
        "correction_decision_sha256": correction_decision_hash(correction),
    }


def correction_review_path(
    directory: str, chain_id: str, correction_id: str, reviewer_id: str
) -> str:
    digest = hashlib.sha256(
        f"{chain_id}\0{correction_id}\0{reviewer_id}".encode("utf-8")
    ).hexdigest()
    return f"{directory}/{digest}.json"


def _parse_time(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be an RFC3339 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed


def _operation_slot(correction: dict) -> str:
    operation = correction["operation"]
    return (
        correction["artifact_id"]
        + "\0site-mention-resolution:"
        + operation["mention_id"]
    )


def _validate_resolution_shape(status: str, target_ids: list[str], label: str) -> None:
    if target_ids != sorted(set(target_ids)):
        raise ValueError(f"{label} target IDs must be sorted and unique")
    if status == "resolved" and len(target_ids) != 1:
        raise ValueError(f"{label} resolved mention must have exactly one target")
    if status == "unmatched" and target_ids:
        raise ValueError(f"{label} unmatched mention must have no targets")
    if status == "ambiguous" and len(target_ids) < 2:
        raise ValueError(f"{label} ambiguous mention must have at least two targets")


def _artifact_reference(reference: object, label: str) -> dict:
    if not isinstance(reference, dict) or set(reference) != {
        "path",
        "sha256",
        "git_blob_oid",
    }:
        raise ValueError(f"{label} must be one exact path/SHA/blob reference")
    path = normalize_relative_path(reference["path"])
    sha256_value = reference["sha256"]
    blob = reference["git_blob_oid"]
    if (
        not isinstance(sha256_value, str)
        or len(sha256_value) != 64
        or any(character not in "0123456789abcdef" for character in sha256_value)
        or not isinstance(blob, str)
        or len(blob) not in {40, 64}
        or any(character not in "0123456789abcdef" for character in blob)
    ):
        raise ValueError(f"{label} SHA/blob values are invalid")
    return {"path": path, "sha256": sha256_value, "git_blob_oid": blob}


def _working_head(repo: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD^{commit}"],
        cwd=repo,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        raise ValueError(
            "cannot resolve release-policy activation commit: "
            + result.stderr.decode("utf-8", errors="replace").strip()
        )
    return resolve_commit(repo, result.stdout.decode("ascii").strip())


def _require_release_bytes_committed(repo: Path, release_head: str) -> None:
    """Bind the release-authenticated worktree to one exact Git commit."""
    manifest_raw = (repo / RELEASE_MANIFEST_RELATIVE).read_bytes()
    if read_bytes(repo, release_head, RELEASE_MANIFEST_RELATIVE) != manifest_raw:
        raise ValueError("release manifest is not committed at the activation HEAD")
    manifest = strict_json_object(manifest_raw, label="release manifest")
    for relative in sorted(manifest["files"]):
        working = (repo / relative).read_bytes()
        if read_bytes(repo, release_head, relative) != working:
            raise ValueError(
                f"release-authenticated file is not committed at activation HEAD: {relative}"
            )


def _validate_policy_shape(policy: dict) -> dict:
    if policy.get("schema_version") != CORRECTION_POLICY_VERSION:
        raise ValueError("unsupported correction policy version")
    trust = copy.deepcopy(policy.get("chain_trust"))
    if not isinstance(trust, dict):
        raise ValueError("correction policy lacks chain trust")
    required = {
        "status",
        "chain_id",
        "ledger_path",
        "review_artifact_directory",
        "genesis_commit",
        "prior_head",
        "registration",
        "configuration_rule",
        "current_effect",
    }
    if set(trust) != required:
        raise ValueError("correction chain trust fields differ from the fixed contract")
    if trust["status"] not in {"CONFIGURED", "NOT_CONFIGURED"}:
        raise ValueError("correction chain trust status is invalid")
    for field in ("chain_id", "configuration_rule", "current_effect"):
        if not isinstance(trust[field], str) or not trust[field].strip():
            raise ValueError(f"correction chain trust {field} must be nonempty")
    trust["ledger_path"] = normalize_relative_path(trust["ledger_path"])
    trust["review_artifact_directory"] = normalize_relative_path(
        trust["review_artifact_directory"]
    ).rstrip("/")
    if not trust["review_artifact_directory"]:
        raise ValueError("correction review artifact directory must be nonempty")
    prior = trust["prior_head"]
    if not isinstance(prior, dict) or set(prior) != {
        "sequence",
        "record_sha256",
        "ledger_commit",
        "ledger_sha256",
        "ledger_git_blob_oid",
    }:
        raise ValueError("correction chain prior head is malformed")
    if type(prior["sequence"]) is not int or prior["sequence"] < 0:
        raise ValueError("correction chain prior sequence is invalid")
    if trust["status"] == "NOT_CONFIGURED":
        if trust["genesis_commit"] is not None or trust["registration"] is not None or any(
            prior[field] is not None
            for field in (
                "record_sha256",
                "ledger_commit",
                "ledger_sha256",
                "ledger_git_blob_oid",
            )
        ) or prior["sequence"] != 0:
            raise ValueError("NOT_CONFIGURED correction chain cannot declare trusted roots")
        raise ValueError(
            "production correction sensitivity blocked: correction chain trust is NOT_CONFIGURED"
        )
    if not isinstance(trust["genesis_commit"], str):
        raise ValueError("configured correction chain lacks a genesis commit")
    registration = trust["registration"]
    if not isinstance(registration, dict) or set(registration) != {
        "commit",
        "path",
        "sha256",
        "git_blob_oid",
    }:
        raise ValueError("configured correction chain lacks an exact registration artifact")
    if not isinstance(registration["commit"], str):
        raise ValueError("correction registration commit is invalid")
    normalized_registration = _artifact_reference(
        {key: registration[key] for key in ("path", "sha256", "git_blob_oid")},
        "correction chain registration artifact",
    )
    trust["registration"] = {"commit": registration["commit"], **normalized_registration}
    if prior["sequence"] == 0:
        if any(
            prior[field] is not None
            for field in (
                "record_sha256",
                "ledger_commit",
                "ledger_sha256",
                "ledger_git_blob_oid",
            )
        ):
            raise ValueError("zero correction head cannot bind a prior ledger")
    elif any(
        not isinstance(prior[field], str)
        for field in (
            "record_sha256",
            "ledger_commit",
            "ledger_sha256",
            "ledger_git_blob_oid",
        )
    ):
        raise ValueError("nonzero correction head must bind its exact prior ledger")
    if prior["sequence"] > 0:
        _artifact_reference(
            {
                "path": trust["ledger_path"],
                "sha256": prior["ledger_sha256"],
                "git_blob_oid": prior["ledger_git_blob_oid"],
            },
            "registered prior correction ledger",
        )
        if (
            len(prior["record_sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in prior["record_sha256"])
        ):
            raise ValueError("registered prior correction record hash is invalid")
    return trust


def _load_registration(
    repo: Path,
    trust: dict,
    ledger: dict,
    prior_commit: str,
) -> tuple[dict, str]:
    reference = trust["registration"]
    commit = resolve_commit(repo, reference["commit"])
    raw, _ = read_authenticated_bytes(
        repo,
        commit,
        reference["path"],
        expected_sha256=reference["sha256"],
        expected_blob_oid=reference["git_blob_oid"],
    )
    registration = strict_json_object(raw, label="correction chain registration")
    if raw != canonical_json_bytes(registration) + b"\n":
        raise ValueError("correction chain registration must be canonical JSON")
    if set(registration) != {
        "schema_version",
        "chain_id",
        "genesis_commit",
        "prior_head",
        "private_record_evidence_canonical_sha256",
        "private_opportunity_source_canonical_sha256",
        "registered_at_utc",
    } or registration.get("schema_version") != CORRECTION_REGISTRATION_VERSION:
        raise ValueError("correction chain registration shape/version is invalid")
    _parse_time(registration["registered_at_utc"], "correction registered_at_utc")
    if (
        registration["chain_id"] != trust["chain_id"]
        or registration["genesis_commit"] != trust["genesis_commit"]
        or registration["prior_head"] != trust["prior_head"]
        or registration["private_record_evidence_canonical_sha256"]
        != ledger["private_record_evidence_canonical_sha256"]
        or registration["private_opportunity_source_canonical_sha256"]
        != ledger["private_opportunity_source_canonical_sha256"]
    ):
        raise ValueError("correction registration differs from chain/baseline bindings")
    genesis = resolve_commit(repo, trust["genesis_commit"])
    if not is_ancestor(repo, genesis, commit):
        raise ValueError("correction registration is not descended from genesis")
    if trust["prior_head"]["sequence"] > 0 and (
        commit == prior_commit or not is_ancestor(repo, prior_commit, commit)
    ):
        raise ValueError("correction registration must postdate the registered prior head")
    return registration, commit


def _load_reviewer_trust(
    repo: Path, schema_root: Path, *, allow_test_trust: bool
) -> dict:
    raw = (repo / TRUSTED_REVIEWERS_RELATIVE).read_bytes()
    registry = strict_json_object(raw, label="trusted correction reviewer registry")
    validate_reviewer_registry(
        registry,
        schema_path=schema_root / "trusted-reviewers.schema.json",
        allow_test_registry=allow_test_trust,
        require_configured=True,
    )
    return registry


def _validate_evidence_source(raw: bytes, label: str) -> dict:
    source = strict_json_object(raw, label=label)
    if raw != canonical_json_bytes(source) + b"\n":
        raise ValueError(f"{label} must be canonical JSON followed by one newline")
    if set(source) != {
        "schema_version",
        "source_id",
        "source_kind",
        "originating_museum",
        "acquired_at_utc",
        "provenance",
        "records",
    } or source.get("schema_version") != CORRECTION_EVIDENCE_VERSION:
        raise ValueError(f"{label} has an unsupported correction-evidence shape")
    if not isinstance(source["source_id"], str) or not source["source_id"]:
        raise ValueError(f"{label} source_id must be nonempty")
    if not isinstance(source["source_kind"], str) or not source["source_kind"]:
        raise ValueError(f"{label} source_kind must be nonempty")
    if not isinstance(source["originating_museum"], bool):
        raise ValueError(f"{label} originating_museum must be boolean")
    _parse_time(source["acquired_at_utc"], f"{label} acquired_at_utc")
    provenance = source["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != {
        "source_locator",
        "acquisition_method",
        "producer_identity",
    } or any(
        not isinstance(provenance[field], str) or not provenance[field].strip()
        for field in provenance
    ):
        raise ValueError(f"{label} provenance is incomplete")
    records = source["records"]
    if not isinstance(records, list) or not records:
        raise ValueError(f"{label} records must be nonempty")
    locators: list[str] = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {
            "locator",
            "evidence_summary",
            "artifact_ids",
            "mention_ids",
            "target_ids",
        }:
            raise ValueError(f"{label} contains a malformed evidence record")
        for field in ("locator", "evidence_summary"):
            if not isinstance(record[field], str) or not record[field].strip():
                raise ValueError(f"{label} evidence {field} must be nonempty")
        for field in ("artifact_ids", "mention_ids", "target_ids"):
            values = record[field]
            if (
                not isinstance(values, list)
                or values != sorted(set(values))
                or any(not isinstance(value, str) or not value for value in values)
            ):
                raise ValueError(f"{label} evidence {field} must be sorted and unique")
        locators.append(record["locator"])
    if locators != sorted(set(locators)):
        raise ValueError(f"{label} evidence records must have sorted unique locators")
    return source


def _citation_coverage(
    repo: Path,
    release_head: str,
    decision_commit: str,
    citations: list[dict],
    correction: dict,
) -> datetime:
    covered_artifacts: set[str] = set()
    covered_mentions: set[str] = set()
    covered_targets: set[str] = set()
    seen: set[tuple[str, str, str]] = set()
    latest_acquisition: datetime | None = None
    for citation in citations:
        source_commit = resolve_commit(repo, citation["source_commit"])
        if source_commit == decision_commit or not is_ancestor(
            repo, source_commit, decision_commit
        ):
            raise ValueError(
                "correction source commit must be a strict ancestor of its decision"
            )
        if not (
            is_ancestor(repo, source_commit, release_head)
            or is_ancestor(repo, release_head, source_commit)
        ):
            raise ValueError(
                "correction source commit is not ancestry comparable with registration"
            )
        reference = _artifact_reference(
            citation.get("source_artifact"), "correction citation source artifact"
        )
        key = (citation.get("source_id"), citation.get("locator"), reference["path"])
        if key in seen:
            raise ValueError("correction review contains a duplicate citation")
        seen.add(key)
        raw, _ = read_authenticated_bytes(
            repo,
            source_commit,
            reference["path"],
            expected_sha256=reference["sha256"],
            expected_blob_oid=reference["git_blob_oid"],
        )
        source = _validate_evidence_source(raw, f"correction evidence {reference['path']}")
        acquired_at = _parse_time(
            source["acquired_at_utc"], f"correction evidence {reference['path']} acquired_at_utc"
        )
        latest_acquisition = (
            acquired_at
            if latest_acquisition is None
            else max(latest_acquisition, acquired_at)
        )
        if (
            citation.get("source_id") != source["source_id"]
            or citation.get("source_kind") != source["source_kind"]
            or citation.get("originating_museum") is not source["originating_museum"]
        ):
            raise ValueError("correction citation identity differs from exact evidence bytes")
        record = next(
            (
                row
                for row in source["records"]
                if row["locator"] == citation.get("locator")
                and row["evidence_summary"] == citation.get("evidence_summary")
            ),
            None,
        )
        if record is None:
            raise ValueError(
                "correction citation locator/summary is absent from exact evidence bytes"
            )
        covered_artifacts.update(record["artifact_ids"])
        covered_mentions.update(record["mention_ids"])
        covered_targets.update(record["target_ids"])
    operation = correction["operation"]
    required_targets = set(operation["from_target_ids"]) | set(
        operation["to_target_ids"]
    )
    if correction["artifact_id"] not in covered_artifacts:
        raise ValueError("correction citations do not cover the exact artifact")
    if operation["mention_id"] not in covered_mentions:
        raise ValueError("correction citations do not cover the exact mention")
    if not required_targets <= covered_targets:
        raise ValueError("correction citations do not cover every changed target")
    assert latest_acquisition is not None
    return latest_acquisition


def _prior_ledger(
    repo: Path,
    schema_root: Path,
    trust: dict,
) -> tuple[list[dict], str]:
    genesis = resolve_commit(repo, trust["genesis_commit"])
    prior = trust["prior_head"]
    if prior["sequence"] == 0:
        return [], genesis
    prior_commit = resolve_commit(repo, prior["ledger_commit"])
    if prior_commit == genesis or not is_ancestor(repo, genesis, prior_commit):
        raise ValueError("registered correction head is not a descendant of genesis")
    raw, _ = read_authenticated_bytes(
        repo,
        prior_commit,
        trust["ledger_path"],
        expected_sha256=prior["ledger_sha256"],
        expected_blob_oid=prior["ledger_git_blob_oid"],
    )
    ledger = strict_json_object(raw, label="registered prior correction ledger")
    validate_schema(
        ledger,
        schema_root / "correction-ledger.schema.json",
        "registered prior correction ledger",
    )
    corrections = ledger["corrections"]
    if (
        ledger["chain_id"] != trust["chain_id"]
        or len(corrections) != prior["sequence"]
        or corrections[-1]["record_sha256"] != prior["record_sha256"]
    ):
        raise ValueError("registered prior correction ledger head binding mismatch")
    return corrections, prior_commit


def authenticate_correction_ledger(
    repo: Path,
    evaluation_root: Path,
    ledger_commit: str | None,
    ledger_path: str | Path,
    *,
    allow_test_trust: bool = False,
) -> dict:
    """Authenticate one append-only correction extension and all review evidence."""
    if ledger_commit is None:
        raise ValueError("production correction sensitivity requires --correction-commit")
    schema_root = evaluation_root / "schemas"
    policy_raw = (evaluation_root / "correction-policy.json").read_bytes()
    policy = strict_json_object(policy_raw, label="correction policy")
    trust = _validate_policy_shape(policy)
    release_integrity = None
    if not allow_test_trust:
        release_integrity = verify_release(repo)
    release_head = _working_head(repo)
    if not allow_test_trust:
        _require_release_bytes_committed(repo, release_head)
    if read_bytes(repo, release_head, CORRECTION_POLICY_RELATIVE) != policy_raw:
        raise ValueError(
            "working correction policy is not committed at the release activation HEAD"
        )
    normalized_ledger_path = normalize_relative_path(str(ledger_path))
    if normalized_ledger_path != trust["ledger_path"]:
        raise ValueError("correction ledger path differs from the registered chain path")
    commit = resolve_commit(repo, ledger_commit)
    raw = read_bytes(repo, commit, normalized_ledger_path)
    ledger = strict_json_object(raw, label="correction ledger")
    validate_schema(
        ledger,
        schema_root / "correction-ledger.schema.json",
        "private correction ledger",
    )
    if ledger["schema_version"] != CORRECTION_SCHEMA_VERSION:
        raise ValueError("unsupported correction ledger version")
    if ledger["chain_id"] != trust["chain_id"]:
        raise ValueError("correction ledger chain ID differs from registered trust root")

    prior_rows, prior_commit = _prior_ledger(repo, schema_root, trust)
    registration, registration_commit = _load_registration(
        repo, trust, ledger, prior_commit
    )
    if registration_commit == release_head or not is_ancestor(
        repo, registration_commit, release_head
    ):
        raise ValueError(
            "release policy activation must strictly postdate chain registration"
        )
    if commit == release_head or not is_ancestor(repo, release_head, commit):
        raise ValueError(
            "correction ledger commit must descend from the registered release policy"
        )
    if ledger["corrections"][: len(prior_rows)] != prior_rows:
        raise ValueError("correction ledger does not byte-for-byte extend its registered prefix")
    new_rows = ledger["corrections"][len(prior_rows) :]
    if not new_rows:
        raise ValueError("correction ledger must append at least one new correction")

    registry = _load_reviewer_trust(
        repo, schema_root, allow_test_trust=allow_test_trust
    )
    review_usage = ArtifactUsageTracker()
    prior_decision_commit = release_head
    authenticated_corrections = []
    for correction in new_rows:
        decision_commit = resolve_commit(repo, correction["decision_commit"])
        if not is_ancestor(repo, prior_decision_commit, decision_commit):
            raise ValueError("correction decision commits are not ancestry ordered")
        if decision_commit == release_head:
            raise ValueError("new correction decision must postdate policy activation")
        if decision_commit == commit or not is_ancestor(repo, decision_commit, commit):
            raise ValueError("correction ledger must be committed after its signed decision")
        prior_decision_commit = decision_commit

        reviewer_ids = correction["reviewer_ids"]
        if reviewer_ids != sorted(set(reviewer_ids)) or len(reviewer_ids) != 2:
            raise ValueError("correction must name exactly two sorted reviewer IDs")
        citations = correction["citations"]
        if citations != sorted(
            citations,
            key=lambda row: (
                row["source_id"],
                row["locator"],
                row["source_artifact"]["path"],
            ),
        ):
            raise ValueError("correction citations must be canonically sorted")
        subject = correction_review_subject(ledger, correction)
        decision_key = f"{CORRECTION_DECISION_KIND}:{canonical_sha256(subject)}"
        latest_evidence_acquisition = _citation_coverage(
            repo, release_head, decision_commit, citations, correction
        )
        citation_commits = {
            (
                row["source_artifact"]["path"],
                row["source_artifact"]["sha256"],
                row["source_artifact"]["git_blob_oid"],
            ): resolve_commit(repo, row["source_commit"])
            for row in citations
        }
        authenticated_reviews = []
        latest_signature_time: datetime | None = None
        for reviewer_id in reviewer_ids:
            path = correction_review_path(
                trust["review_artifact_directory"],
                trust["chain_id"],
                correction["correction_id"],
                reviewer_id,
            )
            review_raw = read_bytes(repo, decision_commit, path)
            review = strict_json_object(
                review_raw, label=f"correction review {path}"
            )
            if (
                review.get("decision_kind") != CORRECTION_DECISION_KIND
                or review.get("decision_key") != decision_key
                or review.get("subject") != subject
                or review.get("outcome") != "supported"
                or review.get("method") != "human"
                or review.get("citations") != citations
                or review.get("reviewer", {}).get("reviewer_id") != reviewer_id
            ):
                raise ValueError("correction review is not bound to the exact supported decision")

            def read_bound(reference: dict) -> bytes:
                normalized = _artifact_reference(
                    reference, "correction review dependency"
                )
                dependency_commit = citation_commits.get(
                    (
                        normalized["path"],
                        normalized["sha256"],
                        normalized["git_blob_oid"],
                    ),
                    decision_commit,
                )
                dependency, _ = read_authenticated_bytes(
                    repo,
                    dependency_commit,
                    normalized["path"],
                    expected_sha256=normalized["sha256"],
                    expected_blob_oid=normalized["git_blob_oid"],
                )
                return dependency

            signature_reference = review["authentication"]["signature"]
            authenticated = authenticate_review_artifact(
                review_raw,
                registry=registry,
                schema_root=schema_root,
                signature_bytes=read_bound(signature_reference),
                signature_reference=signature_reference,
                read_artifact=read_bound,
                usage=review_usage,
                allow_test_registry=allow_test_trust,
            )
            review_started_at = _parse_time(
                review["human_provenance"]["started_at_utc"],
                "correction human review started_at_utc",
            )
            if review_started_at < _parse_time(
                registration["registered_at_utc"],
                "correction chain registered_at_utc",
            ):
                raise ValueError("correction review predates chain registration")
            if review_started_at < latest_evidence_acquisition:
                raise ValueError("correction review predates its cited evidence acquisition")
            signed_at = _parse_time(
                authenticated["signed_at_utc"], "correction review signed_at_utc"
            )
            latest_signature_time = (
                signed_at
                if latest_signature_time is None
                else max(latest_signature_time, signed_at)
            )
            authenticated_reviews.append(authenticated)
        require_distinct_registered_reviewers(authenticated_reviews)
        if latest_signature_time is not None and _parse_time(
            correction["recorded_at_utc"], "correction recorded_at_utc"
        ) < latest_signature_time:
            raise ValueError("correction record predates its authenticated reviews")
        authenticated_corrections.append(
            {
                "correction_id": correction["correction_id"],
                "decision_commit": decision_commit,
                "reviewer_ids": reviewer_ids,
            }
        )
    return {
        "ledger": ledger,
        "metadata": {
            "commit": commit,
            "path": normalized_ledger_path,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob_oid": blob_oid(repo, commit, normalized_ledger_path),
        },
        "chain_id": trust["chain_id"],
        "registration_commit": registration_commit,
        "release_activation_commit": release_head,
        "release_integrity": release_integrity,
        "prior_head_sequence": len(prior_rows),
        "authenticated_corrections": authenticated_corrections,
    }


def _validate_chain(
    ledger: dict,
    records_by_id: dict[str, dict],
    source_by_mention: dict[str, dict],
    target_ids: set[str],
) -> None:
    seen_ids: set[str] = set()
    last_by_slot: dict[str, str] = {}
    previous_hash = None
    previous_recorded_at: datetime | None = None
    for index, correction in enumerate(ledger["corrections"], 1):
        if correction["sequence"] != index:
            raise ValueError("correction sequences must be contiguous from one")
        correction_id = correction["correction_id"]
        if correction_id in seen_ids:
            raise ValueError("correction IDs must be unique")
        if correction["previous_correction_sha256"] != previous_hash:
            raise ValueError(f"correction {correction_id} hash chain mismatch")
        if correction["record_sha256"] != record_hash(correction):
            raise ValueError(f"correction {correction_id} record hash mismatch")
        recorded_at = _parse_time(
            correction["recorded_at_utc"], f"correction {correction_id} recorded_at_utc"
        )
        if previous_recorded_at is not None and recorded_at <= previous_recorded_at:
            raise ValueError("correction timestamps must increase strictly with sequence")
        artifact_id = correction["artifact_id"]
        if artifact_id not in records_by_id:
            raise ValueError(f"correction {correction_id} references unknown artifact")
        operation = correction["operation"]
        mention_id = operation["mention_id"]
        if mention_id not in source_by_mention:
            raise ValueError(f"correction {correction_id} references unknown site mention")
        if source_by_mention[mention_id]["artifact_id"] != artifact_id:
            raise ValueError(f"correction {correction_id} mention/artifact binding mismatch")
        for endpoint in ("from", "to"):
            _validate_resolution_shape(
                operation[f"{endpoint}_status"],
                operation[f"{endpoint}_target_ids"],
                f"correction {correction_id} {endpoint}",
            )
        referenced_targets = set(operation["from_target_ids"]) | set(
            operation["to_target_ids"]
        )
        if referenced_targets - target_ids:
            raise ValueError(
                f"correction {correction_id} references unknown targets: "
                f"{sorted(referenced_targets - target_ids)}"
            )
        if (
            operation["from_status"],
            operation["from_target_ids"],
        ) == (
            operation["to_status"],
            operation["to_target_ids"],
        ):
            raise ValueError(f"correction {correction_id} is a no-op")
        slot = _operation_slot(correction)
        supersedes = correction["supersedes_correction_id"]
        if slot in last_by_slot:
            if supersedes != last_by_slot[slot]:
                raise ValueError(
                    f"correction {correction_id} repeats primitive evidence without exact supersession"
                )
        elif supersedes is not None:
            raise ValueError(f"correction {correction_id} names a supersession without a repeat")
        last_by_slot[slot] = correction_id
        seen_ids.add(correction_id)
        previous_hash = correction["record_sha256"]
        previous_recorded_at = recorded_at


def _index_source(
    source: list[dict],
    records_by_id: dict[str, dict],
    target_ids: set[str],
) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    if source != sorted(source, key=lambda row: row["mention_id"]):
        raise ValueError("private opportunity source must be sorted by mention ID")
    source_by_mention: dict[str, dict] = {}
    mentions_by_artifact: dict[str, list[dict]] = collections.defaultdict(list)
    for mention in source:
        if mention.get("entity_type") != "site":
            raise ValueError("private opportunity source may contain only site mentions")
        try:
            validate_site_mention(mention)
        except RuntimeError as error:
            raise ValueError(str(error)) from error
        mention_id = mention["mention_id"]
        if mention_id in source_by_mention:
            raise ValueError(f"duplicate private source mention ID {mention_id}")
        artifact_id = mention["artifact_id"]
        if artifact_id not in records_by_id:
            raise ValueError(f"private source mention {mention_id} references unknown artifact")
        if records_by_id[artifact_id]["museum"] != mention["museum"]:
            raise ValueError(f"private source mention {mention_id} museum mismatch")
        unknown = set(mention["target_ids"]) - target_ids
        if unknown:
            raise ValueError(
                f"private source mention {mention_id} references unknown targets: {sorted(unknown)}"
            )
        source_by_mention[mention_id] = mention
        mentions_by_artifact[artifact_id].append(mention)
    return source_by_mention, mentions_by_artifact


def _recompute_record(
    row: dict,
    mentions: list[dict],
    scope_by_target: dict[str, str],
) -> None:
    for mention in mentions:
        try:
            validate_site_mention(mention)
        except RuntimeError as error:
            raise ValueError(str(error)) from error
    counts = collections.Counter(mention["status"] for mention in mentions)
    statuses = set(counts)
    targets = sorted(
        {
            mention["target_ids"][0]
            for mention in mentions
            if mention["status"] == "resolved"
        }
    )
    if len(targets) > counts["resolved"]:
        raise ValueError(
            f"corrected record {row['artifact_id']} has more unique direct targets "
            "than resolved mentions"
        )
    row["site_mention_status_counts"] = dict(sorted(counts.items()))
    row["site_mention_count"] = len(mentions)
    row["extracted_site_text_evidence"] = bool(mentions)
    row["baseline_resolution_state"] = resolution_state(statuses)
    row["baseline_site_target_ids"] = targets
    scope_counts = collections.Counter(scope_by_target[target] for target in targets)
    row["baseline_site_target_scope_counts"] = dict(sorted(scope_counts.items()))
    row["baseline_record_scope"] = partition_scopes(set(scope_counts))
    row["has_any_ambiguity"] = counts["ambiguous"] > 0
    row["has_blocking_ambiguity"] = bool(mentions) and not targets and counts["ambiguous"] > 0
    row["has_any_unmatched_expression"] = counts["unmatched"] > 0


def _assert_source_reproduces_records(
    baseline_rows: list[dict],
    mentions_by_artifact: dict[str, list[dict]],
    scope_by_target: dict[str, str],
) -> None:
    for baseline in baseline_rows:
        derived = json.loads(json.dumps(baseline))
        _recompute_record(
            derived,
            mentions_by_artifact.get(baseline["artifact_id"], []),
            scope_by_target,
        )
        mismatches = [
            field
            for field in DERIVED_RECORD_FIELDS
            if derived[field] != baseline[field]
        ]
        if mismatches:
            raise ValueError(
                f"private opportunity source does not reproduce record "
                f"{baseline['artifact_id']}: {mismatches}"
            )


def _apply_operation(mention: dict, correction: dict) -> None:
    operation = correction["operation"]
    if (
        mention["status"] != operation["from_status"]
        or mention["target_ids"] != operation["from_target_ids"]
    ):
        raise ValueError(f"{correction['correction_id']} mention resolution precondition failed")
    mention["status"] = operation["to_status"]
    mention["target_ids"] = operation["to_target_ids"]
    try:
        validate_site_mention(mention)
    except RuntimeError as error:
        raise ValueError(str(error)) from error


def _links_from_records(rows: list[dict]) -> list[dict]:
    return [
        {"artifact_id": row["artifact_id"], "museum": row["museum"], "target_id": target}
        for row in rows
        for target in row["baseline_site_target_ids"]
    ]


def _queue(
    source: list[dict],
    rows: list[dict],
    links: list[dict],
    scope_by_target: dict[str, str],
) -> tuple[dict, dict, dict]:
    record_counts = collections.Counter(row["museum"] for row in rows)
    evidence_counts = collections.Counter(
        row["museum"] for row in rows if row["extracted_site_text_evidence"]
    )
    return build_opportunity_queue(
        source,
        rows,
        links,
        scope_by_target,
        dict(record_counts),
        dict(evidence_counts),
    )


def _minimum_required(denominator: int) -> int:
    if not denominator:
        return 0
    return max(
        1,
        (
            denominator * MINIMUM_AFFECTED_FRACTION.numerator
            + MINIMUM_AFFECTED_FRACTION.denominator
            - 1
        )
        // MINIMUM_AFFECTED_FRACTION.denominator,
    )


def fixed_frozen_itt_analysis(
    frozen_ledger: dict,
    corrected_rows: list[dict],
    corrected_links: list[dict],
    scope_by_target: dict[str, str],
) -> tuple[dict, dict]:
    """Re-evaluate corrected outcomes over unchanged frozen memberships."""
    record_by_id = {row["artifact_id"]: row for row in corrected_rows}
    record_counts = collections.Counter(row["museum"] for row in corrected_rows)
    evidence_counts = collections.Counter(
        row["museum"] for row in corrected_rows if row["extracted_site_text_evidence"]
    )
    links_by_artifact: dict[str, set[str]] = collections.defaultdict(set)
    targets_by_museum: dict[str, set[str]] = {museum: set() for museum in MUSEUMS}
    for link in corrected_links:
        links_by_artifact[link["artifact_id"]].add(link["target_id"])
        targets_by_museum[link["museum"]].add(link["target_id"])

    per_museum = {}
    private_record_states = {}
    for museum in MUSEUMS:
        frozen_rows = frozen_ledger["intent_to_treat_records_by_museum"][museum]
        states = []
        for frozen in frozen_rows:
            current = record_by_id[frozen["artifact_id"]]
            states.append(
                {
                    "artifact_id": frozen["artifact_id"],
                    "opportunity_bindings": frozen["opportunity_bindings"],
                    "frozen_baseline_record_scope": frozen["baseline_record_scope"],
                    "corrected_record_scope": current["baseline_record_scope"],
                }
            )
        categories = collections.Counter(row["corrected_record_scope"] for row in states)
        maximum = categories["no_link"] + categories["broad_only"]
        per_museum[museum] = {
            "selected_signature_count": sum(
                opportunity["museum"] == museum
                for opportunity in frozen_ledger["opportunities"]
            ),
            "intent_to_treat_record_count": len(states),
            "frozen_intent_to_treat_membership_sha256": canonical_json_sha256(frozen_rows),
            "membership_and_denominator_unchanged": True,
            "corrected_record_scope_counts": dict(sorted(categories.items())),
            "new_record_link_ceiling_records": categories["no_link"],
            "strict_refinement_reassignment_ceiling_records": categories["broad_only"],
            "maximum_credited_affected_records": maximum,
            "maximum_overall_effect": ratio(maximum, record_counts[museum]),
            "maximum_extracted_site_text_conditional_effect": ratio(
                maximum, evidence_counts[museum]
            ),
        }
        private_record_states[museum] = states

    pair_sides = {}
    private_pair_states = {}
    for left, right in PAIRS:
        pair_key = f"{left}__{right}"
        shared = targets_by_museum[left] & targets_by_museum[right]
        public_sides = {}
        private_sides = {}
        for museum in (left, right):
            frozen_members = frozen_ledger["credited_pair_opportunity_memberships"][
                pair_key
            ]["sides"][museum]
            states = []
            counts = collections.Counter()
            for member in frozen_members:
                pair_targets = links_by_artifact[member["artifact_id"]] & shared
                scopes = {scope_by_target[target] for target in pair_targets}
                if not pair_targets:
                    state = "no_corrected_pair_connection"
                elif "specific_candidate" in scopes:
                    state = "corrected_specific_present"
                elif "broad" in scopes:
                    state = "corrected_broad_only"
                else:
                    state = "corrected_unclassified_only"
                counts[state] += 1
                states.append(
                    {
                        **member,
                        "corrected_pair_state": state,
                        "corrected_pair_target_ids": sorted(pair_targets),
                    }
                )
            denominator = len(frozen_members)
            public_sides[museum] = {
                "frozen_credited_effect_opportunity_denominator": denominator,
                "frozen_credited_pair_opportunity_membership_sha256": canonical_json_sha256(
                    frozen_members
                ),
                "membership_and_denominator_unchanged": True,
                "corrected_state_counts": dict(sorted(counts.items())),
                "new_pair_connection_ceiling_records": counts[
                    "no_corrected_pair_connection"
                ],
                "strict_refinement_pair_reassignment_ceiling_records": counts[
                    "corrected_broad_only"
                ],
                "minimum_credited_affected_records_for_continue": _minimum_required(
                    denominator
                ),
            }
            private_sides[museum] = states
        pair_sides[pair_key] = {"sides": public_sides}
        private_pair_states[pair_key] = {"sides": private_sides}

    private = {
        "schema_version": "site-graph-v0-fixed-frozen-itt-sensitivity/1",
        "privacy": "private runtime derivative; contains exact artifact memberships",
        "frozen_private_opportunity_ledger_canonical_sha256": canonical_json_sha256(
            frozen_ledger
        ),
        "frozen_membership_rewritten": False,
        "intent_to_treat_record_states_by_museum": private_record_states,
        "credited_pair_opportunity_member_states": private_pair_states,
    }
    public = {
        "schema_version": "site-graph-v0-fixed-frozen-itt-sensitivity-summary/1",
        "estimand": "corrected outcomes over the unchanged frozen intent-to-treat membership",
        "frozen_membership_rewritten": False,
        "selected_signature_count": frozen_ledger["selected_signature_count"],
        "per_museum": per_museum,
        "pair_side_ceilings": pair_sides,
        "private_exact_analysis_canonical_sha256": canonical_json_sha256(private),
    }
    return public, private


def counterfactual_selection_changes(baseline: dict, corrected: dict) -> tuple[dict, dict]:
    """Describe a reselection without treating it as the frozen ITT."""

    def opportunity_key(row: dict) -> tuple[str, str]:
        return row["museum"], row["normalized_expression_key"]

    baseline_opportunities = {opportunity_key(row): row for row in baseline["opportunities"]}
    corrected_opportunities = {opportunity_key(row): row for row in corrected["opportunities"]}
    baseline_keys = set(baseline_opportunities)
    corrected_keys = set(corrected_opportunities)
    removed_keys = sorted(baseline_keys - corrected_keys)
    added_keys = sorted(corrected_keys - baseline_keys)
    changed_keys = sorted(
        key
        for key in baseline_keys & corrected_keys
        if baseline_opportunities[key] != corrected_opportunities[key]
    )
    signature_changes = {
        "removed": [baseline_opportunities[key] for key in removed_keys],
        "added": [corrected_opportunities[key] for key in added_keys],
        "retained_but_changed": [
            {
                "museum": key[0],
                "normalized_expression_key": key[1],
                "before": baseline_opportunities[key],
                "after": corrected_opportunities[key],
            }
            for key in changed_keys
        ],
    }

    record_changes = {}
    per_museum = {}
    for museum in MUSEUMS:
        before_rows = baseline["intent_to_treat_records_by_museum"][museum]
        after_rows = corrected["intent_to_treat_records_by_museum"][museum]
        before = {row["artifact_id"] for row in before_rows}
        after = {row["artifact_id"] for row in after_rows}
        removed = sorted(before - after)
        added = sorted(after - before)
        record_changes[museum] = {"removed_artifact_ids": removed, "added_artifact_ids": added}
        per_museum[museum] = {
            "frozen_intent_to_treat_record_count": len(before),
            "counterfactual_intent_to_treat_record_count": len(after),
            "denominator_change": len(after) - len(before),
            "removed_record_count": len(removed),
            "added_record_count": len(added),
        }

    exact_pair_changes = {}
    public_pair_changes = {}
    for left, right in PAIRS:
        pair_key = f"{left}__{right}"
        exact_sides = {}
        public_sides = {}
        for museum in (left, right):
            before_rows = baseline["credited_pair_opportunity_memberships"][pair_key][
                "sides"
            ][museum]
            after_rows = corrected["credited_pair_opportunity_memberships"][pair_key][
                "sides"
            ][museum]
            before = {row["artifact_id"] for row in before_rows}
            after = {row["artifact_id"] for row in after_rows}
            removed = sorted(before - after)
            added = sorted(after - before)
            exact_sides[museum] = {
                "removed_artifact_ids": removed,
                "added_artifact_ids": added,
            }
            public_sides[museum] = {
                "frozen_credited_effect_opportunity_denominator": len(before),
                "counterfactual_credited_effect_opportunity_denominator": len(after),
                "denominator_change": len(after) - len(before),
                "removed_record_count": len(removed),
                "added_record_count": len(added),
            }
        exact_pair_changes[pair_key] = {"sides": exact_sides}
        public_pair_changes[pair_key] = {"sides": public_sides}

    private = {
        "schema_version": "site-graph-v0-corrected-source-counterfactual-changes/1",
        "privacy": "private runtime derivative; contains exact expressions and artifact IDs",
        "estimand": "counterfactual reselection from corrected source; not the frozen ITT",
        "signature_changes": signature_changes,
        "intent_to_treat_record_changes_by_museum": record_changes,
        "credited_pair_opportunity_membership_changes": exact_pair_changes,
    }
    public = {
        "schema_version": "site-graph-v0-corrected-source-counterfactual-summary/1",
        "estimand": "counterfactual reselection from corrected source; not the frozen ITT",
        "frozen_membership_rewritten": False,
        "frozen_selected_signature_count": baseline["selected_signature_count"],
        "counterfactual_selected_signature_count": corrected["selected_signature_count"],
        "removed_signature_count": len(removed_keys),
        "added_signature_count": len(added_keys),
        "retained_but_changed_signature_count": len(changed_keys),
        "per_museum": per_museum,
        "pair_side_denominator_changes": public_pair_changes,
        "private_exact_changes_canonical_sha256": canonical_json_sha256(private),
    }
    return public, private


def apply(
    repo_root: Path,
    private_run: Path,
    ledger_path: str | Path,
    output: Path,
    *,
    ledger_commit: str | None = None,
) -> dict:
    repo_root = repo_root.resolve()
    private_run = private_run.resolve()
    output = output.resolve()
    evaluation_root = repo_root / "docs/evaluations/site-graph-v0"
    if output.exists():
        raise ValueError(f"sensitivity output must not already exist: {output}")
    if not output.parent.is_dir():
        raise ValueError(f"sensitivity output parent must exist: {output.parent}")
    verify_private_ledgers(private_run, evaluation_root)
    authentication = authenticate_correction_ledger(
        repo_root,
        evaluation_root,
        ledger_commit,
        ledger_path,
    )
    ledger = authentication["ledger"]
    digest_registry = read_json(evaluation_root / "private-ledger-digests.json")
    expected_ledgers = digest_registry["ledgers"]
    if ledger["private_record_evidence_canonical_sha256"] != expected_ledgers[
        "private_record_evidence"
    ]["canonical_uncompressed_ndjson_sha256"]:
        raise ValueError("correction ledger private record baseline binding mismatch")
    if ledger["private_opportunity_source_canonical_sha256"] != expected_ledgers[
        "private_opportunity_source"
    ]["canonical_uncompressed_ndjson_sha256"]:
        raise ValueError("correction ledger private mention source binding mismatch")

    baseline_path = private_run / "private-record-evidence.ndjson.gz"
    source_path = private_run / "private-opportunity-source.ndjson.gz"
    frozen_ledger_path = private_run / "private-opportunity-ledger.json"
    baseline_rows = read_gzip_jsonl(baseline_path)
    source = read_gzip_jsonl(source_path)
    frozen_ledger = read_json(frozen_ledger_path)
    validate_schema(
        frozen_ledger,
        evaluation_root / "schemas/private-opportunity-ledger.schema.json",
        "private frozen opportunity ledger",
    )
    node_scope = read_json(evaluation_root / "baseline-node-scope.json")
    scope_by_target = {
        row["target_id"]: row["scope_class"] for row in node_scope["nodes"]
    }
    records_by_id: dict[str, dict] = {}
    for row in baseline_rows:
        if row["artifact_id"] in records_by_id:
            raise ValueError(f"duplicate private record {row['artifact_id']}")
        records_by_id[row["artifact_id"]] = row
    source_by_mention, mentions_by_artifact = _index_source(
        source, records_by_id, set(scope_by_target)
    )
    _assert_source_reproduces_records(baseline_rows, mentions_by_artifact, scope_by_target)

    baseline_links = _links_from_records(baseline_rows)
    _, reproduced_frozen_ledger, _ = _queue(
        source, baseline_rows, baseline_links, scope_by_target
    )
    if reproduced_frozen_ledger != frozen_ledger:
        raise ValueError(
            "private mention source and record evidence do not reproduce exact frozen ITT ledger"
        )

    _validate_chain(ledger, records_by_id, source_by_mention, set(scope_by_target))
    corrected_source = json.loads(json.dumps(source))
    corrected_source_by_mention = {
        mention["mention_id"]: mention for mention in corrected_source
    }
    for correction in ledger["corrections"]:
        _apply_operation(
            corrected_source_by_mention[correction["operation"]["mention_id"]],
            correction,
        )
    _, corrected_mentions_by_artifact = _index_source(
        corrected_source, records_by_id, set(scope_by_target)
    )
    corrected_rows = [json.loads(json.dumps(row)) for row in baseline_rows]
    for row in corrected_rows:
        _recompute_record(
            row,
            corrected_mentions_by_artifact.get(row["artifact_id"], []),
            scope_by_target,
        )
    corrected_links = _links_from_records(corrected_rows)
    metrics = build_metrics(corrected_rows, corrected_links, scope_by_target)
    fixed_summary, fixed_private = fixed_frozen_itt_analysis(
        frozen_ledger, corrected_rows, corrected_links, scope_by_target
    )
    metrics["planned_slice_maximum_measurable_effect"] = {
        "source": "fixed-frozen-itt-sensitivity-summary.json",
        "estimand": fixed_summary["estimand"],
        "per_museum": fixed_summary["per_museum"],
        "pair_side_ceilings": fixed_summary["pair_side_ceilings"],
        "interpretation": (
            "Sensitivity-only recomputation from corrected mention primitives over the "
            "unchanged frozen ITT; primary baseline and denominators remain unchanged."
        ),
    }

    counterfactual_summary, counterfactual_ledger, counterfactual_components = _queue(
        corrected_source, corrected_rows, corrected_links, scope_by_target
    )
    corrected_source_timing = (
        "Counterfactual replay uses only corrected source primitives for selection. It is "
        "reported after correction review and makes no claim to predate the frozen ITT."
    )
    counterfactual_summary["selection_algorithm"]["result_blind"] = corrected_source_timing
    counterfactual_ledger["selection_algorithm"]["result_blind"] = corrected_source_timing
    validate_schema(
        counterfactual_ledger,
        evaluation_root / "schemas/private-opportunity-ledger.schema.json",
        "private corrected-source counterfactual opportunity ledger",
    )
    reselection_summary, reselection_private = counterfactual_selection_changes(
        frozen_ledger, counterfactual_ledger
    )

    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    published = False
    try:
        corrected_source_output = temporary / "private-sensitivity-opportunity-source.ndjson.gz"
        record_output = temporary / "private-sensitivity-record-evidence.ndjson.gz"
        link_output = temporary / "private-sensitivity-site-links.ndjson.gz"
        fixed_private_output = temporary / "private-fixed-frozen-itt-analysis.json"
        counterfactual_output = (
            temporary / "private-corrected-source-counterfactual-opportunity-ledger.json"
        )
        reselection_output = (
            temporary / "private-corrected-source-counterfactual-changes.json"
        )
        write_gzip_jsonl(corrected_source_output, corrected_source)
        write_gzip_jsonl(record_output, corrected_rows)
        write_gzip_jsonl(link_output, corrected_links)
        write_json(fixed_private_output, fixed_private)
        write_json(counterfactual_output, counterfactual_ledger)
        write_json(reselection_output, reselection_private)
        write_json(temporary / "sensitivity-metrics.json", metrics)
        write_json(temporary / "fixed-frozen-itt-sensitivity-summary.json", fixed_summary)
        write_json(
            temporary / "corrected-source-counterfactual-opportunity-summary.json",
            counterfactual_summary,
        )
        write_json(
            temporary / "corrected-source-counterfactual-top-components.json",
            counterfactual_components,
        )
        write_json(
            temporary / "corrected-source-counterfactual-reselection-summary.json",
            reselection_summary,
        )
        summary = {
            "schema_version": "site-graph-v0-correction-sensitivity-summary/4",
            "primary_baseline_immutable": True,
            "frozen_intent_to_treat_membership_rewritten": False,
            "correction_count": len(ledger["corrections"]),
            "correction_chain_id": authentication["chain_id"],
            "registered_prior_head_sequence": authentication[
                "prior_head_sequence"
            ],
            "authenticated_correction_count": len(
                authentication["authenticated_corrections"]
            ),
            "release_manifest_sha256": authentication["release_integrity"][
                "manifest_sha256"
            ],
            "private_correction_ledger_commit": authentication["metadata"]["commit"],
            "private_correction_ledger_path": authentication["metadata"]["path"],
            "private_correction_ledger_sha256": authentication["metadata"]["sha256"],
            "private_correction_ledger_git_blob_oid": authentication["metadata"][
                "git_blob_oid"
            ],
            "private_correction_ledger_canonical_sha256": canonical_json_sha256(ledger),
            "primary_private_record_evidence": gzip_ledger_digest(baseline_path),
            "primary_private_opportunity_source": gzip_ledger_digest(source_path),
            "sensitivity_private_record_evidence": gzip_ledger_digest(record_output),
            "sensitivity_private_opportunity_source": gzip_ledger_digest(
                corrected_source_output
            ),
            "sensitivity_private_site_links": gzip_ledger_digest(link_output),
            "fixed_frozen_intent_to_treat": fixed_summary,
            "corrected_source_counterfactual_reselection": reselection_summary,
            "private_counterfactual_opportunity_ledger_canonical_sha256": (
                canonical_json_sha256(counterfactual_ledger)
            ),
            "sensitivity_metrics_sha256": sha256(temporary / "sensitivity-metrics.json"),
            "public_data_boundary": (
                "Only this aggregate/hash summary and aggregate metrics are eligible for "
                "release; corrected mention/record rows, exact fixed memberships, and exact "
                "counterfactual additions/removals remain private."
            ),
        }
        write_json(temporary / "sensitivity-summary.json", summary)
        os.replace(temporary, output)
        published = True
        return summary
    finally:
        if not published and temporary.exists():
            shutil.rmtree(temporary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--private-run", type=Path, required=True)
    parser.add_argument("--correction-commit", required=True)
    parser.add_argument("--correction-ledger", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            apply(
                args.repo_root,
                args.private_run,
                args.correction_ledger,
                args.output,
                ledger_commit=args.correction_commit,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
