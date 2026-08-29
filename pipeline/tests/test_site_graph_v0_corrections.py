"""Logic-only attacks on correction and ITT binding invariants.

The temporary rows in this module exercise control flow only.  They are not corpus
evidence and make no evaluation, validation, or product claim.
"""

from __future__ import annotations

import gzip
import base64
import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = REPO_ROOT / "docs/evaluations/site-graph-v0"
SCRIPTS = EVAL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _load_script(name: str, aliases: dict[str, object] | None = None):
    """Load a release script under a test namespace with explicit dependencies."""
    qualified = f"_hapi_site_graph_v0_corrections_{name}"
    spec = importlib.util.spec_from_file_location(qualified, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = {key: sys.modules.get(key) for key in aliases or {}}
    try:
        for key, value in (aliases or {}).items():
            sys.modules[key] = value
        sys.modules[qualified] = module
        spec.loader.exec_module(module)
    finally:
        for key, value in previous.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value
    return module


baseline = _load_script("build_baseline")
private_ledgers = _load_script("private_ledgers", {"build_baseline": baseline})
corrections = _load_script(
    "apply_corrections",
    {"build_baseline": baseline, "private_ledgers": private_ledgers},
)
import review_auth  # noqa: E402


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(repo: Path, *args: str, stdin: bytes | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        input=stdin,
        check=False,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    return result.stdout.decode("utf-8").strip()


def _exact_reference(repo: Path, path: str, raw: bytes) -> dict:
    return {
        "path": path,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_oid": _git(repo, "hash-object", "--stdin", stdin=raw),
    }


def _reviewer_identity(
    principal_id: str,
    independence_group: str,
    key: Ed25519PrivateKey,
) -> dict:
    public_key = base64.b64encode(
        key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
    ).decode("ascii")
    return {
        "principal_id": principal_id,
        "independence_group": independence_group,
        "identity_kind": "HUMAN",
        "roles": ["reviewer"],
        "methods": ["human"],
        "key_id": review_auth.reviewer_key_id(public_key),
        "public_key_base64": public_key,
        "valid_from_utc": "2026-01-01T00:00:00Z",
        "valid_until_utc": None,
        "credential_provenance": {
            "issuer": "test-only correction mechanics harness",
            "credential_id": f"test-only-correction:{principal_id}",
            "verification_method": "ephemeral in-process Ed25519 key",
            "verified_at_utc": "2026-01-01T00:00:00Z",
            "evidence_sha256": hashlib.sha256(
                f"test-only-correction:{principal_id}".encode("utf-8")
            ).hexdigest(),
        },
        "trust_basis": "TEST_ONLY_MECHANICS; never a production identity.",
    }


def _signed_human_review(
    repo: Path,
    value: dict,
    key: Ed25519PrivateKey,
    signature_path: str,
) -> tuple[bytes, bytes]:
    value["authentication"] = {
        "registry_id": "test-only:correction-reviewers",
        "signature_context": review_auth.SIGNATURE_CONTEXT,
        "principal_id": value["reviewer"]["reviewer_id"],
        "key_id": review_auth.reviewer_key_id(
            base64.b64encode(
                key.public_key().public_bytes(
                    serialization.Encoding.Raw, serialization.PublicFormat.Raw
                )
            ).decode("ascii")
        ),
        "signed_at_utc": "2026-08-28T00:03:00Z",
        "statement_sha256": "0" * 64,
        "signature": {
            "path": signature_path,
            "sha256": "0" * 64,
            "git_blob_oid": "0" * 40,
        },
    }
    statement = review_auth.signature_statement_bytes(
        value, artifact_kind="review_artifact"
    )
    value["authentication"]["statement_sha256"] = hashlib.sha256(
        statement
    ).hexdigest()
    signature = key.sign(statement)
    value["authentication"]["signature"] = _exact_reference(
        repo, signature_path, signature
    )
    assert (
        review_auth.signature_statement_bytes(value, artifact_kind="review_artifact")
        == statement
    )
    return review_auth.canonical_json_bytes(value) + b"\n", signature


def _authenticated_chain_fixture(tmp_path: Path, *, attack: str | None = None) -> dict:
    """Create TEST_ONLY_MECHANICS Git history; it is never corpus evidence."""
    repo = tmp_path / "correction-auth-repo"
    evaluation = repo / "docs/evaluations/site-graph-v0"
    schemas = evaluation / "schemas"
    schemas.mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Correction mechanics test")
    for name in (
        "correction-ledger.schema.json",
        "review-artifact.schema.json",
        "trusted-reviewers.schema.json",
    ):
        shutil.copy2(EVAL_ROOT / "schemas" / name, schemas / name)

    keys = {
        principal: Ed25519PrivateKey.generate()
        for principal in ("reviewer-a", "reviewer-b", "reviewer-rogue")
    }
    identities = [
        _reviewer_identity("reviewer-a", "independence-a", keys["reviewer-a"]),
        _reviewer_identity(
            "reviewer-b",
            "independence-a" if attack == "same-independence-group" else "independence-b",
            keys["reviewer-b"],
        ),
    ]
    registry = {
        "schema_version": review_auth.REGISTRY_SCHEMA_VERSION,
        "registry_id": "test-only:correction-reviewers",
        "status": "CONFIGURED",
        "trust_tier": "TEST_ONLY_MECHANICS",
        "signature_scheme": "ed25519",
        "signature_context": review_auth.SIGNATURE_CONTEXT,
        "configuration_rule": "Generated keys exercise mechanics only.",
        "current_effect": "Never accepted without explicit test opt-in.",
        "identities": identities,
    }
    _write_json(evaluation / "trusted-reviewers.json", registry)
    policy = json.loads((EVAL_ROOT / "correction-policy.json").read_text())
    _write_json(evaluation / "correction-policy.json", policy)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "test-only correction genesis")
    genesis = _git(repo, "rev-parse", "HEAD")

    prior_head = {
        "sequence": 0,
        "record_sha256": None,
        "ledger_commit": None,
        "ledger_sha256": None,
        "ledger_git_blob_oid": None,
    }
    registration_path = "private/corrections/registration.json"
    registration = {
        "schema_version": corrections.CORRECTION_REGISTRATION_VERSION,
        "chain_id": "test-only-correction-chain",
        "genesis_commit": genesis,
        "prior_head": prior_head,
        "private_record_evidence_canonical_sha256": "a" * 64,
        "private_opportunity_source_canonical_sha256": "b" * 64,
        "registered_at_utc": "2026-08-28T00:00:30Z",
    }
    registration_raw = review_auth.canonical_json_bytes(registration) + b"\n"
    registration_file = repo / registration_path
    registration_file.parent.mkdir(parents=True)
    registration_file.write_bytes(registration_raw)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "test-only correction registration")
    registration_commit = _git(repo, "rev-parse", "HEAD")

    policy["chain_trust"] = {
        "status": "CONFIGURED",
        "chain_id": "test-only-correction-chain",
        "ledger_path": "private/corrections/ledger.json",
        "review_artifact_directory": "private/corrections/reviews",
        "genesis_commit": genesis,
        "registration": (
            None
            if attack == "no-registration"
            else {
                "commit": registration_commit,
                **_exact_reference(repo, registration_path, registration_raw),
            }
        ),
        "prior_head": prior_head,
        "configuration_rule": "Test-only exact Git root.",
        "current_effect": "Enabled only with explicit TEST_ONLY_MECHANICS opt-in.",
    }
    _write_json(evaluation / "correction-policy.json", policy)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "test-only activate correction registration")
    release_activation_commit = _git(repo, "rev-parse", "HEAD")

    evidence_path = "private/corrections/evidence/source.json"
    evidence = {
        "schema_version": corrections.CORRECTION_EVIDENCE_VERSION,
        "source_id": "source-real",
        "source_kind": "archival-record",
        "originating_museum": False,
        "acquired_at_utc": "2026-08-28T00:00:00Z",
        "provenance": {
            "source_locator": "archive:test-only",
            "acquisition_method": "test-only committed byte construction",
            "producer_identity": "test-only mechanics harness",
        },
        "records": [
            {
                "locator": "record-real",
                "evidence_summary": "Exact test-only record supports this transition.",
                "artifact_ids": ["artifact-under-correction"],
                "mention_ids": ["mention-under-correction"],
                "target_ids": ["target-specific"],
            }
        ],
    }
    evidence_raw = review_auth.canonical_json_bytes(evidence) + b"\n"
    evidence_file = repo / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_bytes(evidence_raw)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "test-only correction source bytes")
    source_commit = _git(repo, "rev-parse", "HEAD")
    citation = {
        "source_id": "source-real",
        "source_kind": "archival-record",
        "locator": "made-up-locator" if attack == "made-up-citation" else "record-real",
        "evidence_summary": "Exact test-only record supports this transition.",
        "originating_museum": False,
        "source_commit": source_commit,
        "source_artifact": _exact_reference(repo, evidence_path, evidence_raw),
    }
    reviewer_ids = (
        ["reviewer-a", "reviewer-rogue"]
        if attack == "made-up-reviewer"
        else ["reviewer-a", "reviewer-b"]
    )
    correction = {
        "sequence": 1,
        "correction_id": "correction-one",
        "previous_correction_sha256": None,
        "supersedes_correction_id": None,
        "artifact_id": "artifact-under-correction",
        "operation": {
            "kind": "set_site_mention_resolution",
            "mention_id": "mention-under-correction",
            "from_status": "unmatched",
            "from_target_ids": [],
            "to_status": "resolved",
            "to_target_ids": ["target-specific"],
        },
        "reason": "Exact source-supported primitive resolution transition.",
        "citations": [citation],
        "reviewer_ids": reviewer_ids,
        "decision_commit": "f" * 40,
        "recorded_at_utc": "2026-08-28T00:04:00Z",
        "record_sha256": "0" * 64,
    }
    subject = corrections.correction_review_subject(
        {
            "chain_id": policy["chain_trust"]["chain_id"],
            "private_record_evidence_canonical_sha256": "a" * 64,
            "private_opportunity_source_canonical_sha256": "b" * 64,
        },
        correction,
    )
    decision_key = (
        f"{corrections.CORRECTION_DECISION_KIND}:"
        f"{review_auth.canonical_sha256(subject)}"
    )
    for reviewer_id in reviewer_ids:
        group = {
            "reviewer-a": "independence-a",
            "reviewer-b": (
                "independence-a"
                if attack == "same-independence-group"
                else "independence-b"
            ),
            "reviewer-rogue": "independence-rogue",
        }[reviewer_id]
        review = {
            "schema_version": review_auth.REVIEW_SCHEMA_VERSION,
            "review_id": f"review-{reviewer_id}",
            "decision_key": decision_key,
            "decision_kind": corrections.CORRECTION_DECISION_KIND,
            "subject": subject,
            "reviewer": {
                "reviewer_id": reviewer_id,
                "independence_group": group,
            },
            "outcome": "supported",
            "method": "human",
            "citations": [citation],
            "reasoning": f"{reviewer_id} independently supports the exact transition.",
            "human_provenance": {
                "review_session_id": f"session-{reviewer_id}",
                "started_at_utc": "2026-08-28T00:01:00Z",
                "completed_at_utc": "2026-08-28T00:02:00Z",
                "reasoning_utf8_sha256": hashlib.sha256(
                    f"{reviewer_id} independently supports the exact transition.".encode(
                        "utf-8"
                    )
                ).hexdigest(),
            },
            "llm_interaction": None,
        }
        review_path = corrections.correction_review_path(
            policy["chain_trust"]["review_artifact_directory"],
            policy["chain_trust"]["chain_id"],
            correction["correction_id"],
            reviewer_id,
        )
        signature_path = f"private/corrections/signatures/{reviewer_id}.sig"
        review_raw, signature = _signed_human_review(
            repo, review, keys[reviewer_id], signature_path
        )
        review_file = repo / review_path
        review_file.parent.mkdir(parents=True, exist_ok=True)
        review_file.write_bytes(review_raw)
        signature_file = repo / signature_path
        signature_file.parent.mkdir(parents=True, exist_ok=True)
        signature_file.write_bytes(signature)

    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "test-only signed correction decision")
    decision_commit = _git(repo, "rev-parse", "HEAD")
    correction["decision_commit"] = (
        "0" * 40 if attack == "all-zero-decision" else decision_commit
    )
    correction["record_sha256"] = corrections.record_hash(correction)
    ledger = {
        "schema_version": corrections.CORRECTION_SCHEMA_VERSION,
        "chain_id": policy["chain_trust"]["chain_id"],
        "baseline_mutated": False,
        "private_record_evidence_canonical_sha256": "a" * 64,
        "private_opportunity_source_canonical_sha256": "b" * 64,
        "corrections": [correction],
    }
    ledger_file = repo / policy["chain_trust"]["ledger_path"]
    ledger_file.parent.mkdir(parents=True, exist_ok=True)
    _write_json(ledger_file, ledger)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "test-only correction ledger")
    ledger_commit = _git(repo, "rev-parse", "HEAD")
    ledger_raw = ledger_file.read_bytes()
    if attack == "post-hoc-registration":
        _git(repo, "checkout", "-q", "--detach", registration_commit)
        _write_json(evaluation / "correction-policy.json", policy)
        _git(repo, "add", ".")
        _git(repo, "commit", "-qm", "test-only post-hoc policy activation")
        release_activation_commit = _git(repo, "rev-parse", "HEAD")
    else:
        _git(repo, "checkout", "-q", "--detach", release_activation_commit)
    return {
        "repo": repo,
        "evaluation": evaluation,
        "policy": policy,
        "ledger": ledger,
        "ledger_file": ledger_file,
        "ledger_raw": ledger_raw,
        "ledger_commit": ledger_commit,
        "genesis": genesis,
        "registration": registration,
        "registration_commit": registration_commit,
        "registration_path": registration_path,
        "release_activation_commit": release_activation_commit,
        "source_commit": source_commit,
    }


def _mention(
    museum: str,
    artifact_id: str,
    mention_id: str,
    key: str,
    *,
    status: str = "unmatched",
    target_ids: list[str] | None = None,
) -> dict:
    return {
        "artifact_id": artifact_id,
        "field_path": "logic.place",
        "mention_id": mention_id,
        "mention_text": key.replace("-", " "),
        "museum": museum,
        "normalized_keys": [key],
        "status": status,
        "target_ids": target_ids or [],
        "entity_type": "site",
    }


def _logic_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Build a complete tiny contract shape solely for correction control-flow tests."""
    monkeypatch.setattr(baseline, "OPPORTUNITY_MUSEUM_PROTECTION", 1)
    monkeypatch.setattr(baseline, "OPPORTUNITY_TOTAL_SIGNATURES", 3)
    monkeypatch.setattr(corrections, "verify_private_ledgers", lambda *_: {})

    repo = tmp_path / "repo"
    evaluation = repo / "docs/evaluations/site-graph-v0"
    schemas = evaluation / "schemas"
    schemas.mkdir(parents=True)
    for name in ("correction-ledger.schema.json", "private-opportunity-ledger.schema.json"):
        shutil.copy2(EVAL_ROOT / "schemas" / name, schemas / name)

    def logic_only_authentication(
        _repo: Path,
        _evaluation: Path,
        _commit: str | None,
        ledger_path: str | Path,
        *,
        allow_test_trust: bool = False,
    ) -> dict:
        del allow_test_trust
        ledger_value = baseline.read_json(Path(ledger_path))
        corrections.validate_schema(
            ledger_value,
            schemas / "correction-ledger.schema.json",
            "logic-only correction ledger",
        )
        raw = Path(ledger_path).read_bytes()
        return {
            "ledger": ledger_value,
            "metadata": {
                "commit": "logic-only-untrusted",
                "path": str(ledger_path),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "git_blob_oid": "0" * 40,
            },
            "chain_id": ledger_value["chain_id"],
            "release_integrity": {"manifest_sha256": "0" * 64},
            "prior_head_sequence": 0,
            "authenticated_corrections": [
                {"correction_id": row["correction_id"]}
                for row in ledger_value["corrections"]
            ],
        }

    monkeypatch.setattr(
        corrections, "authenticate_correction_ledger", logic_only_authentication
    )

    scope_by_target = {
        "target-broad": "broad",
        "target-specific": "specific_candidate",
    }
    _write_json(
        evaluation / "baseline-node-scope.json",
        {
            "schema_version": "logic-only",
            "nodes": [
                {"target_id": target, "scope_class": scope}
                for target, scope in scope_by_target.items()
            ],
        },
    )

    source = [
        _mention("met", "met-a", "mention-met-a", "met-top"),
        _mention("met", "met-b", "mention-met-b", "met-top"),
        _mention("met", "met-c", "mention-met-c", "met-top"),
        _mention("met", "met-d", "mention-met-d", "met-next"),
        _mention("met", "met-e", "mention-met-e", "met-next"),
        _mention("brooklyn", "brooklyn-a", "mention-brooklyn-a", "brooklyn-top"),
        _mention("harvard", "harvard-a", "mention-harvard-a", "harvard-top"),
    ]
    source.sort(key=lambda row: row["mention_id"])
    canonical = [
        {"id": mention["artifact_id"], "source_museum": mention["museum"]}
        for mention in source
    ]
    records = baseline.build_record_rows(canonical, source, [], scope_by_target)
    record_counts = {
        museum: sum(row["museum"] == museum for row in records)
        for museum in ("met", "brooklyn", "harvard")
    }
    evidence_counts = dict(record_counts)
    _, frozen_ledger, _ = baseline.build_opportunity_queue(
        source,
        records,
        [],
        scope_by_target,
        record_counts,
        evidence_counts,
    )

    private_run = tmp_path / "private-run"
    private_run.mkdir()
    record_path = private_run / "private-record-evidence.ndjson.gz"
    source_path = private_run / "private-opportunity-source.ndjson.gz"
    baseline.write_gzip_jsonl(record_path, records)
    baseline.write_gzip_jsonl(source_path, source)
    _write_json(private_run / "private-opportunity-ledger.json", frozen_ledger)
    record_digest = baseline.gzip_ledger_digest(record_path)
    source_digest = baseline.gzip_ledger_digest(source_path)
    _write_json(
        evaluation / "private-ledger-digests.json",
        {
            "ledgers": {
                "private_record_evidence": record_digest,
                "private_opportunity_source": source_digest,
            }
        },
    )

    operations = [
        {
            "kind": "set_site_mention_resolution",
            "mention_id": f"mention-met-{suffix}",
            "from_status": "unmatched",
            "from_target_ids": [],
            "to_status": "resolved",
            "to_target_ids": ["target-broad"],
        }
        for suffix in ("a", "b", "c")
    ]
    correction_rows = []
    previous = None
    for sequence, operation in enumerate(operations, 1):
        correction = {
            "sequence": sequence,
            "correction_id": f"logic-correction-{sequence}",
            "previous_correction_sha256": previous,
            "supersedes_correction_id": None,
            "artifact_id": f"met-{chr(96 + sequence)}",
            "operation": operation,
            "reason": "logic-only exact mention resolution transition",
            "citations": [
                {
                    "source_id": "logic-only-source",
                    "source_kind": "logic-only-mechanics",
                    "locator": f"logic-row-{sequence}",
                    "evidence_summary": "purpose-built control-flow evidence",
                    "originating_museum": False,
                    "source_commit": "c" * 40,
                    "source_artifact": {
                        "path": "logic-only/evidence.json",
                        "sha256": "0" * 64,
                        "git_blob_oid": "0" * 40,
                    },
                }
            ],
            "reviewer_ids": ["logic-reviewer-a", "logic-reviewer-b"],
            "decision_commit": "a" * 40,
            "recorded_at_utc": f"2026-08-28T00:00:0{sequence}Z",
            "record_sha256": "",
        }
        correction["record_sha256"] = corrections.record_hash(correction)
        previous = correction["record_sha256"]
        correction_rows.append(correction)
    ledger = {
        "schema_version": "site-graph-v0-correction-ledger/4",
        "chain_id": "logic-only-correction-chain",
        "baseline_mutated": False,
        "private_record_evidence_canonical_sha256": record_digest[
            "canonical_uncompressed_ndjson_sha256"
        ],
        "private_opportunity_source_canonical_sha256": source_digest[
            "canonical_uncompressed_ndjson_sha256"
        ],
        "corrections": correction_rows,
    }
    ledger_path = tmp_path / "corrections.json"
    _write_json(ledger_path, ledger)
    return {
        "repo": repo,
        "evaluation": evaluation,
        "private_run": private_run,
        "frozen_ledger": frozen_ledger,
        "ledger": ledger,
        "ledger_path": ledger_path,
    }


def test_private_source_and_itt_rows_bind_exact_selecting_mentions() -> None:
    mentions = [
        _mention(
            "met",
            "met-resolved",
            "mention-resolved",
            "resolved-key",
            status="resolved",
            target_ids=["target-broad"],
        ),
        _mention("met", "met-unmatched", "mention-unmatched", "unmatched-key"),
        _mention("brooklyn", "brooklyn-u", "mention-brooklyn", "brooklyn-key"),
        _mention("harvard", "harvard-u", "mention-harvard", "harvard-key"),
    ]
    source = baseline.private_opportunity_source(mentions)
    assert [row["mention_id"] for row in source] == [
        "mention-brooklyn",
        "mention-harvard",
        "mention-resolved",
        "mention-unmatched",
    ]
    assert source[2]["status"] == "resolved"
    assert source[2]["target_ids"] == ["target-broad"]

    scope = {"target-broad": "broad"}
    canonical = [
        {"id": mention["artifact_id"], "source_museum": mention["museum"]}
        for mention in mentions
    ]
    links = [
        {
            "entity_type": "site",
            "artifact_id": "met-resolved",
            "museum": "met",
            "target_id": "target-broad",
        }
    ]
    records = baseline.build_record_rows(canonical, mentions, links, scope)
    counts = {"met": 2, "brooklyn": 1, "harvard": 1}
    summary, ledger, _ = baseline.build_opportunity_queue(
        source, records, links, scope, counts, counts
    )
    assert summary["selected_signature_count"] == 3
    unmatched = next(
        row for row in ledger["opportunities"] if row["museum"] == "met"
    )
    membership = unmatched["artifact_memberships"][0]
    assert membership["mentions"][0]["mention_id"] == "mention-unmatched"
    assert len(membership["opportunity_binding_sha256"]) == 64
    itt = next(
        row
        for row in ledger["intent_to_treat_records_by_museum"]["met"]
        if row["artifact_id"] == "met-unmatched"
    )
    assert itt["opportunity_bindings"] == [
        {
            "opportunity_id": unmatched["opportunity_id"],
            "opportunity_binding_sha256": membership["opportunity_binding_sha256"],
        }
    ]
    pair_member = next(
        row
        for row in ledger["credited_pair_opportunity_memberships"]["met__brooklyn"][
            "sides"
        ]["met"]
        if row["artifact_id"] == "met-unmatched"
    )
    assert pair_member["opportunity_bindings"] == itt["opportunity_bindings"]


def test_resolved_mention_with_two_targets_is_rejected() -> None:
    bad = _mention(
        "met",
        "met-a",
        "mention-a",
        "bad",
        status="resolved",
        target_ids=["target-a", "target-b"],
    )
    with pytest.raises(RuntimeError, match="exactly one target"):
        baseline.build_record_rows(
            [{"id": "met-a", "source_museum": "met"}],
            [bad],
            [],
            {"target-a": "broad", "target-b": "broad"},
        )


def test_fixed_itt_stays_frozen_while_counterfactual_reports_exact_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _logic_fixture(tmp_path, monkeypatch)
    private_before = {
        path.relative_to(fixture["private_run"]).as_posix(): baseline.sha256(path)
        for path in fixture["private_run"].rglob("*")
        if path.is_file()
    }
    public_before = {
        path.relative_to(fixture["evaluation"]).as_posix(): baseline.sha256(path)
        for path in fixture["evaluation"].rglob("*")
        if path.is_file()
    }
    output = tmp_path / "sensitivity"
    summary = corrections.apply(
        fixture["repo"], fixture["private_run"], fixture["ledger_path"], output
    )
    assert summary["primary_baseline_immutable"] is True
    assert summary["frozen_intent_to_treat_membership_rewritten"] is False
    assert private_before == {
        path.relative_to(fixture["private_run"]).as_posix(): baseline.sha256(path)
        for path in fixture["private_run"].rglob("*")
        if path.is_file()
    }
    assert public_before == {
        path.relative_to(fixture["evaluation"]).as_posix(): baseline.sha256(path)
        for path in fixture["evaluation"].rglob("*")
        if path.is_file()
    }

    fixed = json.loads((output / "private-fixed-frozen-itt-analysis.json").read_text())
    frozen_met = fixture["frozen_ledger"]["intent_to_treat_records_by_museum"]["met"]
    assert [row["artifact_id"] for row in fixed["intent_to_treat_record_states_by_museum"]["met"]] == [
        row["artifact_id"] for row in frozen_met
    ]
    assert all(
        row["opportunity_bindings"] == frozen["opportunity_bindings"]
        for row, frozen in zip(
            fixed["intent_to_treat_record_states_by_museum"]["met"], frozen_met, strict=True
        )
    )
    fixed_pair = summary["fixed_frozen_intent_to_treat"]["pair_side_ceilings"][
        "met__brooklyn"
    ]["sides"]["met"]
    assert fixed_pair["frozen_credited_effect_opportunity_denominator"] == 3
    assert fixed_pair["membership_and_denominator_unchanged"] is True

    exact = json.loads(
        (output / "private-corrected-source-counterfactual-changes.json").read_text()
    )
    assert [row["normalized_expression_key"] for row in exact["signature_changes"]["removed"]] == [
        "met-top"
    ]
    assert [row["normalized_expression_key"] for row in exact["signature_changes"]["added"]] == [
        "met-next"
    ]
    assert exact["intent_to_treat_record_changes_by_museum"]["met"] == {
        "removed_artifact_ids": ["met-a", "met-b", "met-c"],
        "added_artifact_ids": ["met-d", "met-e"],
    }
    reselection = summary["corrected_source_counterfactual_reselection"]
    assert reselection["removed_signature_count"] == 1
    assert reselection["added_signature_count"] == 1
    assert reselection["per_museum"]["met"]["denominator_change"] == -1
    assert reselection["pair_side_denominator_changes"]["met__brooklyn"]["sides"][
        "met"
    ]["denominator_change"] == -1

    with gzip.open(
        output / "private-sensitivity-opportunity-source.ndjson.gz",
        "rt",
        encoding="utf-8",
    ) as handle:
        corrected_source = [json.loads(line) for line in handle]
    corrected_top = [
        row
        for row in corrected_source
        if row["normalized_keys"] == ["met-top"]
    ]
    assert len(corrected_top) == 3
    assert all(
        row["status"] == "resolved" and row["target_ids"] == ["target-broad"]
        for row in corrected_top
    )


def test_correction_rejects_one_resolved_mention_with_two_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _logic_fixture(tmp_path, monkeypatch)
    ledger = fixture["ledger"]
    ledger["corrections"] = [ledger["corrections"][0]]
    operation = ledger["corrections"][0]["operation"]
    operation["to_target_ids"] = ["target-broad", "target-specific"]
    ledger["corrections"][0]["record_sha256"] = corrections.record_hash(
        ledger["corrections"][0]
    )
    path = tmp_path / "invalid-two-targets.json"
    _write_json(path, ledger)
    with pytest.raises(ValueError, match="resolved mention must have exactly one target"):
        corrections.apply(
            fixture["repo"], fixture["private_run"], path, tmp_path / "never"
        )


def test_correction_rejects_unknown_target_wrong_type_and_unsuperseded_repeat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _logic_fixture(tmp_path, monkeypatch)

    unknown = json.loads(json.dumps(fixture["ledger"]))
    unknown["corrections"][0]["operation"]["to_target_ids"] = ["invented-target"]
    unknown["corrections"][0]["record_sha256"] = corrections.record_hash(
        unknown["corrections"][0]
    )
    unknown_path = tmp_path / "unknown-target.json"
    _write_json(unknown_path, unknown)
    with pytest.raises(ValueError, match="unknown targets"):
        corrections.apply(
            fixture["repo"], fixture["private_run"], unknown_path, tmp_path / "never-unknown"
        )

    wrong_type = json.loads(json.dumps(fixture["ledger"]))
    wrong_type["baseline_mutated"] = "false"
    wrong_type_path = tmp_path / "wrong-type.json"
    _write_json(wrong_type_path, wrong_type)
    with pytest.raises(ValueError, match="schema validation"):
        corrections.apply(
            fixture["repo"], fixture["private_run"], wrong_type_path, tmp_path / "never-type"
        )

    repeated = json.loads(json.dumps(fixture["ledger"]))
    extra = json.loads(json.dumps(repeated["corrections"][0]))
    extra.update(
        {
            "sequence": 4,
            "correction_id": "logic-correction-4",
            "previous_correction_sha256": repeated["corrections"][-1][
                "record_sha256"
            ],
            "supersedes_correction_id": None,
            "recorded_at_utc": "2026-08-28T00:00:04Z",
        }
    )
    extra["operation"] = {
        "kind": "set_site_mention_resolution",
        "mention_id": "mention-met-a",
        "from_status": "resolved",
        "from_target_ids": ["target-broad"],
        "to_status": "unmatched",
        "to_target_ids": [],
    }
    extra["record_sha256"] = corrections.record_hash(extra)
    repeated["corrections"].append(extra)
    repeated_path = tmp_path / "unsuperseded-repeat.json"
    _write_json(repeated_path, repeated)
    with pytest.raises(ValueError, match="without exact supersession"):
        corrections.apply(
            fixture["repo"], fixture["private_run"], repeated_path, tmp_path / "never-repeat"
        )


def test_production_correction_chain_fails_closed_without_genuine_roots() -> None:
    head = _git(REPO_ROOT, "rev-parse", "HEAD")
    with pytest.raises(ValueError, match="chain trust is NOT_CONFIGURED"):
        corrections.authenticate_correction_ledger(
            REPO_ROOT,
            EVAL_ROOT,
            head,
            "private/corrections/ledger.json",
        )


def test_correction_chain_sequence_rejects_json_boolean() -> None:
    policy = baseline.read_json(EVAL_ROOT / "correction-policy.json")
    policy["chain_trust"]["prior_head"]["sequence"] = True
    with pytest.raises(ValueError, match="prior sequence is invalid"):
        corrections._validate_policy_shape(policy)


def test_authenticated_correction_chain_accepts_exact_signed_git_evidence(
    tmp_path: Path,
) -> None:
    case = _authenticated_chain_fixture(tmp_path)
    authenticated = corrections.authenticate_correction_ledger(
        case["repo"],
        case["evaluation"],
        case["ledger_commit"],
        "private/corrections/ledger.json",
        allow_test_trust=True,
    )
    assert authenticated["chain_id"] == "test-only-correction-chain"
    assert authenticated["prior_head_sequence"] == 0
    assert authenticated["metadata"]["commit"] == case["ledger_commit"]
    assert authenticated["metadata"]["sha256"] == hashlib.sha256(
        case["ledger_raw"]
    ).hexdigest()
    assert authenticated["registration_commit"] == case["registration_commit"]
    assert authenticated["release_activation_commit"] == case[
        "release_activation_commit"
    ]
    assert authenticated["authenticated_corrections"] == [
        {
            "correction_id": "correction-one",
            "decision_commit": case["ledger"]["corrections"][0]["decision_commit"],
            "reviewer_ids": ["reviewer-a", "reviewer-b"],
        }
    ]


def test_configured_worktree_policy_cannot_bypass_release_integrity(
    tmp_path: Path,
) -> None:
    case = _authenticated_chain_fixture(tmp_path)
    with pytest.raises(RuntimeError, match="missing immutable release manifest"):
        corrections.authenticate_correction_ledger(
            case["repo"],
            case["evaluation"],
            case["ledger_commit"],
            "private/corrections/ledger.json",
        )


def test_correction_release_activation_requires_every_release_byte_in_head(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "release-head-binding"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Release byte binding test")
    payload = repo / "release-payload.txt"
    payload.write_bytes(b"exact release byte\n")
    manifest = repo / corrections.RELEASE_MANIFEST_RELATIVE
    manifest.parent.mkdir(parents=True)
    _write_json(
        manifest,
        {
            "files": {
                "release-payload.txt": {
                    "bytes": payload.stat().st_size,
                    "sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
                }
            }
        },
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "test-only release activation")
    head = _git(repo, "rev-parse", "HEAD")
    corrections._require_release_bytes_committed(repo, head)
    payload.write_bytes(b"caller substituted byte\n")
    with pytest.raises(ValueError, match="not committed at activation HEAD"):
        corrections._require_release_bytes_committed(repo, head)


@pytest.mark.parametrize(
    ("attack", "message"),
    [
        ("made-up-citation", "locator/summary is absent"),
        ("made-up-reviewer", "unregistered review principal"),
        ("all-zero-decision", "schema validation"),
        ("same-independence-group", "distinct independence_group"),
        ("no-registration", "lacks an exact registration artifact"),
        (
            "post-hoc-registration",
            "ledger commit must descend from the registered release policy",
        ),
    ],
)
def test_authenticated_correction_chain_rejects_fabricated_trust_inputs(
    tmp_path: Path,
    attack: str,
    message: str,
) -> None:
    case = _authenticated_chain_fixture(tmp_path, attack=attack)
    with pytest.raises(ValueError, match=message):
        corrections.authenticate_correction_ledger(
            case["repo"],
            case["evaluation"],
            case["ledger_commit"],
            "private/corrections/ledger.json",
            allow_test_trust=True,
        )


def test_correction_source_must_be_committed_before_signed_decision(
    tmp_path: Path,
) -> None:
    case = _authenticated_chain_fixture(tmp_path)
    correction = copy.deepcopy(case["ledger"]["corrections"][0])
    decision_commit = correction["decision_commit"]
    correction["citations"][0]["source_commit"] = decision_commit
    with pytest.raises(ValueError, match="strict ancestor of its decision"):
        corrections._citation_coverage(
            case["repo"],
            case["release_activation_commit"],
            decision_commit,
            correction["citations"],
            correction,
        )


def test_correction_review_subject_prevents_chain_and_baseline_replay() -> None:
    correction = {
        "correction_id": "correction-one",
        "artifact_id": "artifact-one",
        "operation": {
            "kind": "set_site_mention_resolution",
            "mention_id": "mention-one",
            "from_status": "unmatched",
            "from_target_ids": [],
            "to_status": "resolved",
            "to_target_ids": ["target-one"],
        },
    }
    ledger = {
        "chain_id": "chain-a",
        "private_record_evidence_canonical_sha256": "a" * 64,
        "private_opportunity_source_canonical_sha256": "b" * 64,
    }
    subject = corrections.correction_review_subject(ledger, correction)
    changed_chain = corrections.correction_review_subject(
        {**ledger, "chain_id": "chain-b"}, correction
    )
    changed_baseline = corrections.correction_review_subject(
        {
            **ledger,
            "private_record_evidence_canonical_sha256": "c" * 64,
        },
        correction,
    )
    assert subject != changed_chain
    assert subject != changed_baseline
    assert review_auth.canonical_sha256(subject) not in {
        review_auth.canonical_sha256(changed_chain),
        review_auth.canonical_sha256(changed_baseline),
    }


def test_registered_correction_prefix_cannot_be_rewritten(tmp_path: Path) -> None:
    case = _authenticated_chain_fixture(tmp_path)
    repo = case["repo"]
    _git(repo, "checkout", "-q", "--detach", case["ledger_commit"])
    policy = copy.deepcopy(case["policy"])
    ledger_raw = case["ledger_raw"]
    policy["chain_trust"]["prior_head"] = {
        "sequence": 1,
        "record_sha256": case["ledger"]["corrections"][0]["record_sha256"],
        "ledger_commit": case["ledger_commit"],
        "ledger_sha256": hashlib.sha256(ledger_raw).hexdigest(),
        "ledger_git_blob_oid": _git(
            repo,
            "rev-parse",
            f"{case['ledger_commit']}:private/corrections/ledger.json",
        ),
    }
    registration = copy.deepcopy(case["registration"])
    registration["prior_head"] = policy["chain_trust"]["prior_head"]
    registration["registered_at_utc"] = "2026-08-28T00:04:30Z"
    registration_raw = review_auth.canonical_json_bytes(registration) + b"\n"
    registration_file = repo / case["registration_path"]
    registration_file.write_bytes(registration_raw)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "test-only register prior correction head")
    registration_commit = _git(repo, "rev-parse", "HEAD")
    policy["chain_trust"]["registration"] = {
        "commit": registration_commit,
        **_exact_reference(repo, case["registration_path"], registration_raw),
    }
    _write_json(case["evaluation"] / "correction-policy.json", policy)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "test-only activate registered prior head")
    activation_commit = _git(repo, "rev-parse", "HEAD")
    rewritten = copy.deepcopy(case["ledger"])
    rewritten["corrections"][0]["reason"] = "Rewritten registered history."
    rewritten["corrections"][0]["record_sha256"] = corrections.record_hash(
        rewritten["corrections"][0]
    )
    appended = copy.deepcopy(rewritten["corrections"][0])
    appended.update(
        {
            "sequence": 2,
            "correction_id": "correction-two",
            "previous_correction_sha256": rewritten["corrections"][0][
                "record_sha256"
            ],
            "artifact_id": "artifact-two",
            "recorded_at_utc": "2026-08-28T00:05:00Z",
            "decision_commit": activation_commit,
            "record_sha256": "0" * 64,
        }
    )
    appended["operation"]["mention_id"] = "mention-two"
    appended["record_sha256"] = corrections.record_hash(appended)
    rewritten["corrections"].append(appended)
    _write_json(case["ledger_file"], rewritten)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "test-only attempted history rewrite")
    rewritten_commit = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "--detach", activation_commit)
    with pytest.raises(ValueError, match="registered prefix"):
        corrections.authenticate_correction_ledger(
            repo,
            case["evaluation"],
            rewritten_commit,
            "private/corrections/ledger.json",
            allow_test_trust=True,
        )
