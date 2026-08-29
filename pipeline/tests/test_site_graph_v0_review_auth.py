"""Adversarial mechanics tests for authenticated site-graph review evidence.

All keys and records in this module are generated control-flow inputs.  They are not
review evidence, are explicitly marked TEST_ONLY_MECHANICS, and cannot satisfy the
release-pinned production reviewer policy.
"""

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


REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = REPO_ROOT / "docs/evaluations/site-graph-v0"
SCHEMA_ROOT = EVAL_ROOT / "schemas"
SCRIPTS = EVAL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import review_auth  # noqa: E402


SUBJECT = {
    "artifact_id": "artifact-under-review",
    "target_id": "target-under-review",
    "opportunity_id": "opportunity-under-review",
    "opportunity_binding_sha256": "a" * 64,
}
DECISION_KEY = f"link_support:{review_auth.canonical_sha256(SUBJECT)}"
PREFERRED_LABELS = ["Memphis", "Thebes"]
ALIASES = ["Luxor", "Waset"]
ANSWER_NAMES = [
    "distinct",
    "equivalent",
    "strict_refinement",
    "supported",
    "uncertain",
    "unsupported",
]
IDENTIFIERS = ["candidate-real-42", "source-real-99"]
LOCATORS = ["authority:memphis", "authority:thebes"]


class ArtifactStore:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def add(self, path: str, raw: bytes) -> dict:
        self.files[path] = raw
        blob = hashlib.sha1(
            f"blob {len(raw)}\0".encode("ascii") + raw,
            usedforsecurity=False,
        ).hexdigest()
        return {
            "path": path,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob_oid": blob,
        }

    def read(self, reference: dict) -> bytes:
        return self.files[reference["path"]]


def _public_key(private_key: Ed25519PrivateKey) -> str:
    raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return base64.b64encode(raw).decode("ascii")


def _identity(
    principal_id: str,
    group: str,
    private_key: Ed25519PrivateKey,
    *,
    roles: list[str],
    methods: list[str],
) -> dict:
    public_key = _public_key(private_key)
    return {
        "principal_id": principal_id,
        "independence_group": group,
        "identity_kind": "HUMAN",
        "roles": sorted(roles),
        "methods": sorted(methods),
        "key_id": review_auth.reviewer_key_id(public_key),
        "public_key_base64": public_key,
        "valid_from_utc": "2026-01-01T00:00:00Z",
        "valid_until_utc": None,
        "credential_provenance": {
            "issuer": "test-only mechanics harness",
            "credential_id": f"test-only-credential:{principal_id}",
            "verification_method": "ephemeral in-process key generation",
            "verified_at_utc": "2026-01-01T00:00:00Z",
            "evidence_sha256": hashlib.sha256(
                f"test-only:{principal_id}".encode("utf-8")
            ).hexdigest(),
        },
        "trust_basis": "Test-only signature mechanics; never production trust.",
    }


@pytest.fixture
def auth_case() -> dict:
    keys = {
        principal: Ed25519PrivateKey.generate()
        for principal in ("auditor-a", "auditor-b", "reviewer-a", "reviewer-b")
    }
    identities = [
        _identity(
            "auditor-a",
            "audit-group-a",
            keys["auditor-a"],
            roles=["prompt_auditor"],
            methods=[review_auth.AUDIT_METHOD],
        ),
        _identity(
            "auditor-b",
            "audit-group-b",
            keys["auditor-b"],
            roles=["prompt_auditor"],
            methods=[review_auth.AUDIT_METHOD],
        ),
        _identity(
            "reviewer-a",
            "review-group-a",
            keys["reviewer-a"],
            roles=["reviewer"],
            methods=["human", "llm"],
        ),
        _identity(
            "reviewer-b",
            "review-group-b",
            keys["reviewer-b"],
            roles=["reviewer"],
            methods=["human", "llm"],
        ),
    ]
    registry = {
        "schema_version": review_auth.REGISTRY_SCHEMA_VERSION,
        "registry_id": "test-only:site-graph-reviewers",
        "status": "CONFIGURED",
        "trust_tier": "TEST_ONLY_MECHANICS",
        "signature_scheme": "ed25519",
        "signature_context": review_auth.SIGNATURE_CONTEXT,
        "configuration_rule": "Generated keys are mechanics-only.",
        "current_effect": "Never accepted by production policy.",
        "identities": identities,
    }
    review_auth.validate_reviewer_registry(
        registry,
        schema_path=SCHEMA_ROOT / "trusted-reviewers.schema.json",
        allow_test_registry=True,
    )
    return {"keys": keys, "registry": registry, "store": ArtifactStore()}


def _placeholder_reference(path: str) -> dict:
    return {"path": path, "sha256": "0" * 64, "git_blob_oid": "0" * 40}


def _request_parts(
    *,
    review_invocation_id: str,
    decision_key: str = DECISION_KEY,
    decision_kind: str = "link_support",
    subject: dict = SUBJECT,
    task_instructions: str = (
        "Assess the evidence attached to the opaque items and provide a reasoned assessment."
    ),
    payloads: list[dict] | None = None,
) -> dict:
    if payloads is None:
        payloads = [
            {"description": "Neutral evidence alpha."},
            {"description": "Neutral evidence beta."},
            {"description": "Neutral evidence gamma."},
        ]
    input_value, provenance = review_auth.build_structured_input_envelope(
        payloads,
        review_invocation_id=review_invocation_id,
        decision_key=decision_key,
        decision_kind=decision_kind,
        subject=subject,
    )
    input_raw = review_auth.canonical_json_bytes(input_value) + b"\n"
    prompt_value = review_auth.build_structured_prompt_envelope(
        review_invocation_id=review_invocation_id,
        input_envelope_bytes=input_raw,
        task_instructions=task_instructions,
    )
    return {
        "prompt_value": prompt_value,
        "prompt_raw": review_auth.canonical_json_bytes(prompt_value) + b"\n",
        "input_value": input_value,
        "input_raw": input_raw,
        "shuffle_provenance": provenance,
    }


def _guard_for_request(
    request: dict,
    *,
    review_invocation_id: str,
    decision_key: str = DECISION_KEY,
    decision_kind: str = "link_support",
    subject: dict = SUBJECT,
) -> dict:
    return review_auth.deterministic_guard_record(
        request["prompt_raw"],
        request["input_raw"],
        shuffle_provenance=request["shuffle_provenance"],
        review_invocation_id=review_invocation_id,
        decision_key=decision_key,
        decision_kind=decision_kind,
        subject=subject,
        preferred_labels=PREFERRED_LABELS,
        aliases=ALIASES,
        answer_names=ANSWER_NAMES,
        identifiers=IDENTIFIERS,
        locators=LOCATORS,
    )


def _sign(
    value: dict,
    *,
    kind: str,
    principal_id: str,
    signed_at_utc: str,
    signature_path: str,
    case: dict,
) -> tuple[bytes, bytes, dict]:
    identity = next(
        row
        for row in case["registry"]["identities"]
        if row["principal_id"] == principal_id
    )
    value["authentication"] = {
        "registry_id": case["registry"]["registry_id"],
        "signature_context": review_auth.SIGNATURE_CONTEXT,
        "principal_id": principal_id,
        "key_id": identity["key_id"],
        "signed_at_utc": signed_at_utc,
        "statement_sha256": "0" * 64,
        "signature": _placeholder_reference(signature_path),
    }
    statement = review_auth.signature_statement_bytes(value, artifact_kind=kind)
    value["authentication"]["statement_sha256"] = hashlib.sha256(
        statement
    ).hexdigest()
    signature = case["keys"][principal_id].sign(statement)
    signature_reference = case["store"].add(signature_path, signature)
    value["authentication"]["signature"] = signature_reference
    assert review_auth.signature_statement_bytes(value, artifact_kind=kind) == statement
    raw = review_auth.canonical_json_bytes(value) + b"\n"
    return raw, signature, signature_reference


def _build_audit(
    case: dict,
    *,
    suffix: str = "a",
    auditor_id: str = "auditor-a",
    review_id: str | None = None,
    review_invocation_id: str | None = None,
    decision_key: str = DECISION_KEY,
    subject: dict = SUBJECT,
    prompt_reference: dict | None = None,
    input_reference: dict | None = None,
    prompt_bytes: bytes | None = None,
    input_bytes: bytes | None = None,
    shuffle_provenance: dict | None = None,
    task_instructions: str = (
        "Assess the evidence attached to the opaque items and provide a reasoned assessment."
    ),
    payloads: list[dict] | None = None,
    guard: dict | None = None,
    signed_at_utc: str = "2026-08-28T00:02:00Z",
) -> dict:
    store = case["store"]
    actual_review_id = review_id or f"review-{suffix}"
    actual_invocation_id = review_invocation_id or f"invocation-{suffix}"
    if prompt_bytes is None or input_bytes is None or shuffle_provenance is None:
        if prompt_bytes is not None or input_bytes is not None or shuffle_provenance is not None:
            raise AssertionError("custom request parts must be supplied together")
        request = _request_parts(
            review_invocation_id=actual_invocation_id,
            decision_key=decision_key,
            subject=subject,
            task_instructions=task_instructions,
            payloads=payloads,
        )
        prompt_bytes = request["prompt_raw"]
        input_bytes = request["input_raw"]
        shuffle_provenance = request["shuffle_provenance"]
    if prompt_reference is None:
        prompt_reference = store.add(f"frozen/prompt-{suffix}.json", prompt_bytes)
    if input_reference is None:
        input_reference = store.add(f"frozen/input-{suffix}.json", input_bytes)
    if guard is None:
        guard = review_auth.deterministic_guard_record(
            store.read(prompt_reference),
            store.read(input_reference),
            shuffle_provenance=shuffle_provenance,
            review_invocation_id=actual_invocation_id,
            decision_key=decision_key,
            decision_kind="link_support",
            subject=subject,
            preferred_labels=PREFERRED_LABELS,
            aliases=ALIASES,
            answer_names=ANSWER_NAMES,
            identifiers=IDENTIFIERS,
            locators=LOCATORS,
        )
    value = {
        "schema_version": review_auth.AUDIT_SCHEMA_VERSION,
        "audit_id": f"audit-{suffix}",
        "review_id": actual_review_id,
        "review_invocation_id": actual_invocation_id,
        "decision_key": decision_key,
        "decision_kind": "link_support",
        "subject": subject,
        "prompt": prompt_reference,
        "input": input_reference,
        "shuffle_provenance": shuffle_provenance,
        "audit_method": review_auth.AUDIT_METHOD,
        "auditor": {
            "auditor_id": auditor_id,
            "independence_group": next(
                row["independence_group"]
                for row in case["registry"]["identities"]
                if row["principal_id"] == auditor_id
            ),
        },
        "executed_at_utc": "2026-08-28T00:01:00Z",
        "deterministic_guard": guard,
    }
    raw, signature, signature_reference = _sign(
        value,
        kind="prompt_leakage_audit",
        principal_id=auditor_id,
        signed_at_utc=signed_at_utc,
        signature_path=f"signatures/audit-{suffix}.sig",
        case=case,
    )
    artifact_reference = store.add(f"frozen/audit-{suffix}.json", raw)
    return {
        "value": value,
        "raw": raw,
        "signature": signature,
        "signature_reference": signature_reference,
        "artifact_reference": artifact_reference,
        "prompt_reference": prompt_reference,
        "input_reference": input_reference,
        "shuffle_provenance": shuffle_provenance,
    }


def _authenticate_audit(
    case: dict,
    audit: dict,
    usage: review_auth.ArtifactUsageTracker,
    *,
    invocation_started_at_utc: str = "2026-08-28T00:03:00Z",
) -> dict:
    return review_auth.authenticate_prompt_audit(
        audit["raw"],
        registry=case["registry"],
        schema_root=SCHEMA_ROOT,
        signature_bytes=audit["signature"],
        signature_reference=audit["signature_reference"],
        read_artifact=case["store"].read,
        preferred_labels=PREFERRED_LABELS,
        aliases=ALIASES,
        answer_names=ANSWER_NAMES,
        identifiers=IDENTIFIERS,
        locators=LOCATORS,
        invocation_started_at_utc=invocation_started_at_utc,
        usage=usage,
        allow_test_registry=True,
    )


def _build_llm_review(
    case: dict,
    audit: dict,
    *,
    suffix: str = "a",
    reviewer_id: str = "reviewer-a",
) -> dict:
    store = case["store"]
    source_reference = store.add(
        f"sources/source-{suffix}.txt", b"Independent authority evidence bytes.\n"
    )
    response_reference = store.add(
        f"result/raw-response-{suffix}.txt",
        b"Full raw model response, including stated reasoning.\n",
    )
    value = {
        "schema_version": review_auth.REVIEW_SCHEMA_VERSION,
        "review_id": f"review-{suffix}",
        "decision_key": DECISION_KEY,
        "decision_kind": "link_support",
        "subject": SUBJECT,
        "reviewer": {
            "reviewer_id": reviewer_id,
            "independence_group": next(
                row["independence_group"]
                for row in case["registry"]["identities"]
                if row["principal_id"] == reviewer_id
            ),
        },
        "outcome": "supported",
        "method": "llm",
        "citations": [
            {
                "source_id": f"independent-authority-{suffix}",
                "source_kind": "independent_authority",
                "locator": f"page-{suffix}",
                "evidence_summary": "Independent source supports this mechanics record.",
                "originating_museum": False,
                "source_artifact": source_reference,
            }
        ],
        "reasoning": "Test-only reasoning linked to the full raw response.",
        "human_provenance": None,
        "llm_interaction": {
            "review_invocation_id": f"invocation-{suffix}",
            "invoked_at_utc": "2026-08-28T00:03:00Z",
            "completed_at_utc": "2026-08-28T00:04:00Z",
            "model": {
                "provider": "test-only",
                "model_selector": "mechanics-model",
                "backend_model_id": "mechanics-model-2026-08-28",
                "snapshot_exposure": "EXPOSED",
                "snapshot_id": "mechanics-model-2026-08-28",
                "snapshot_date": "2026-08-28",
            },
            "parameters": {
                "reported_parameters": {"temperature": 0},
                "unexposed_parameters": [],
                "completeness_statement": "All mechanics-harness parameters reported.",
            },
            "prompt": audit["prompt_reference"],
            "input": audit["input_reference"],
            "raw_response": response_reference,
            "prompt_leakage_audit": audit["artifact_reference"],
            "interaction_binding_sha256": "0" * 64,
        },
    }
    value["llm_interaction"]["interaction_binding_sha256"] = (
        review_auth.llm_interaction_binding_sha256(value)
    )
    raw, signature, signature_reference = _sign(
        value,
        kind="review_artifact",
        principal_id=reviewer_id,
        signed_at_utc="2026-08-28T00:05:00Z",
        signature_path=f"signatures/review-{suffix}.sig",
        case=case,
    )
    return {
        "value": value,
        "raw": raw,
        "signature": signature,
        "signature_reference": signature_reference,
    }


def _build_human_review(
    case: dict,
    *,
    suffix: str,
    reviewer_id: str,
) -> dict:
    store = case["store"]
    source_reference = store.add(
        f"sources/human-source-{suffix}.txt", b"Exact human source bytes.\n"
    )
    reasoning = "Authenticated human reasoning with exact source provenance."
    value = {
        "schema_version": review_auth.REVIEW_SCHEMA_VERSION,
        "review_id": f"review-{suffix}",
        "decision_key": DECISION_KEY,
        "decision_kind": "link_support",
        "subject": SUBJECT,
        "reviewer": {
            "reviewer_id": reviewer_id,
            "independence_group": next(
                row["independence_group"]
                for row in case["registry"]["identities"]
                if row["principal_id"] == reviewer_id
            ),
        },
        "outcome": "supported",
        "method": "human",
        "citations": [
            {
                "source_id": f"human-authority-{suffix}",
                "source_kind": "independent_authority",
                "locator": f"folio-{suffix}",
                "evidence_summary": "Human reviewer consulted the exact cited bytes.",
                "originating_museum": False,
                "source_artifact": source_reference,
            }
        ],
        "reasoning": reasoning,
        "human_provenance": {
            "review_session_id": f"human-session-{suffix}",
            "started_at_utc": "2026-08-28T00:01:00Z",
            "completed_at_utc": "2026-08-28T00:04:00Z",
            "reasoning_utf8_sha256": hashlib.sha256(
                reasoning.encode("utf-8")
            ).hexdigest(),
        },
        "llm_interaction": None,
    }
    raw, signature, signature_reference = _sign(
        value,
        kind="review_artifact",
        principal_id=reviewer_id,
        signed_at_utc="2026-08-28T00:05:00Z",
        signature_path=f"signatures/human-review-{suffix}.sig",
        case=case,
    )
    return {
        "value": value,
        "raw": raw,
        "signature": signature,
        "signature_reference": signature_reference,
    }


def _authenticate_review(
    case: dict,
    review: dict,
    usage: review_auth.ArtifactUsageTracker,
    *,
    authenticated_audit: dict | None = None,
) -> dict:
    return review_auth.authenticate_review_artifact(
        review["raw"],
        registry=case["registry"],
        schema_root=SCHEMA_ROOT,
        signature_bytes=review["signature"],
        signature_reference=review["signature_reference"],
        read_artifact=case["store"].read,
        usage=usage,
        authenticated_prompt_audit=authenticated_audit,
        allow_test_registry=True,
    )


def test_production_registry_fails_closed_and_rejects_test_keys(auth_case: dict) -> None:
    with pytest.raises(review_auth.ReviewAuthenticationError, match="NOT_CONFIGURED"):
        review_auth.load_reviewer_registry(REPO_ROOT, SCHEMA_ROOT)
    with pytest.raises(
        review_auth.ReviewAuthenticationError,
        match="cannot satisfy production policy",
    ):
        review_auth.validate_reviewer_registry(auth_case["registry"])


def test_signed_audit_and_llm_review_bind_every_exact_artifact(auth_case: dict) -> None:
    usage = review_auth.ArtifactUsageTracker()
    audit = _build_audit(auth_case)
    authenticated_audit = _authenticate_audit(auth_case, audit, usage)
    review = _build_llm_review(auth_case, audit)
    authenticated_review = _authenticate_review(
        auth_case, review, usage, authenticated_audit=authenticated_audit
    )
    assert authenticated_audit["auditor_id"] == "auditor-a"
    assert authenticated_audit["independence_group"] == "audit-group-a"
    assert authenticated_audit["method"] == review_auth.AUDIT_METHOD
    assert authenticated_review["reviewer_id"] == "reviewer-a"
    assert authenticated_review["independence_group"] == "review-group-a"
    assert authenticated_review["method"] == "llm"
    assert authenticated_review["outcome"] == "supported"
    assert authenticated_review["decision_key"] == DECISION_KEY


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda value: value["subject"].__setitem__("target_id", "tampered-target"),
            "signed statement hash mismatch",
        ),
        (
            lambda value: value.__setitem__("outcome", "unsupported"),
            "signed statement hash mismatch",
        ),
        (
            lambda value: value["llm_interaction"]["parameters"][
                "reported_parameters"
            ].__setitem__("temperature", 1),
            "signed statement hash mismatch",
        ),
        (
            lambda value: value["citations"][0].__setitem__(
                "locator", "tampered-locator"
            ),
            "signed statement hash mismatch",
        ),
    ],
)
def test_signed_review_rejects_decision_and_llm_provenance_tampering(
    auth_case: dict, mutation, message: str
) -> None:
    usage = review_auth.ArtifactUsageTracker()
    audit = _build_audit(auth_case)
    authenticated_audit = _authenticate_audit(auth_case, audit, usage)
    review = _build_llm_review(auth_case, audit)
    value = copy.deepcopy(review["value"])
    mutation(value)
    review["raw"] = review_auth.canonical_json_bytes(value) + b"\n"
    with pytest.raises(review_auth.ReviewAuthenticationError, match=message):
        _authenticate_review(
            auth_case, review, usage, authenticated_audit=authenticated_audit
        )


def test_arbitrary_reviewer_string_is_not_identity(auth_case: dict) -> None:
    review = _build_human_review(
        auth_case, suffix="human-a", reviewer_id="reviewer-a"
    )
    value = copy.deepcopy(review["value"])
    value["reviewer"]["reviewer_id"] = "arbitrary-unregistered-string"
    raw, signature, signature_reference = _sign(
        value,
        kind="review_artifact",
        principal_id="reviewer-a",
        signed_at_utc="2026-08-28T00:05:00Z",
        signature_path="signatures/arbitrary-reviewer.sig",
        case=auth_case,
    )
    forged = {
        "raw": raw,
        "signature": signature,
        "signature_reference": signature_reference,
    }
    with pytest.raises(
        review_auth.ReviewAuthenticationError,
        match="not the registered principal",
    ):
        _authenticate_review(
            auth_case, forged, review_auth.ArtifactUsageTracker()
        )


def test_exact_source_and_raw_response_byte_hashes_are_enforced(auth_case: dict) -> None:
    usage = review_auth.ArtifactUsageTracker()
    audit = _build_audit(auth_case)
    authenticated_audit = _authenticate_audit(auth_case, audit, usage)
    review = _build_llm_review(auth_case, audit)
    response_path = review["value"]["llm_interaction"]["raw_response"]["path"]
    auth_case["store"].files[response_path] += b"tampered"
    with pytest.raises(review_auth.ReviewAuthenticationError, match="SHA-256 mismatch"):
        _authenticate_review(
            auth_case, review, usage, authenticated_audit=authenticated_audit
        )

    human = _build_human_review(
        auth_case, suffix="human-source", reviewer_id="reviewer-b"
    )
    source_path = human["value"]["citations"][0]["source_artifact"]["path"]
    auth_case["store"].files[source_path] += b"tampered"
    with pytest.raises(review_auth.ReviewAuthenticationError, match="SHA-256 mismatch"):
        _authenticate_review(
            auth_case, human, review_auth.ArtifactUsageTracker()
        )


def test_signed_pass_claim_cannot_hide_leak_in_example(auth_case: dict) -> None:
    invocation_id = "invocation-leaked"
    safe = _request_parts(review_invocation_id=invocation_id)
    forged_guard = _guard_for_request(
        safe, review_invocation_id=invocation_id
    )
    leaked = _request_parts(
        review_invocation_id=invocation_id,
        task_instructions=(
            "Use this example mapping: candidate-real-42 denotes Memphis."
        ),
    )
    audit = _build_audit(
        auth_case,
        suffix="leaked",
        prompt_bytes=leaked["prompt_raw"],
        input_bytes=leaked["input_raw"],
        shuffle_provenance=leaked["shuffle_provenance"],
        guard=forged_guard,
    )
    with pytest.raises(review_auth.ReviewAuthenticationError, match="prompt leakage detected"):
        _authenticate_audit(auth_case, audit, review_auth.ArtifactUsageTracker())


def test_signed_pass_claim_cannot_hide_outcome_token_leak(auth_case: dict) -> None:
    invocation_id = "invocation-leaked-outcome"
    safe = _request_parts(review_invocation_id=invocation_id)
    forged_guard = _guard_for_request(
        safe, review_invocation_id=invocation_id
    )
    leaked = _request_parts(
        review_invocation_id=invocation_id,
        task_instructions="The outcome name for this request is supported.",
    )
    audit = _build_audit(
        auth_case,
        suffix="leaked-outcome",
        prompt_bytes=leaked["prompt_raw"],
        input_bytes=leaked["input_raw"],
        shuffle_provenance=leaked["shuffle_provenance"],
        guard=forged_guard,
    )
    with pytest.raises(
        review_auth.ReviewAuthenticationError, match="prompt leakage detected"
    ):
        _authenticate_audit(auth_case, audit, review_auth.ArtifactUsageTracker())


def test_signed_exact_yes_approve_prompt_is_rejected(auth_case: dict) -> None:
    invocation_id = "invocation-exact-proxy"
    safe = _request_parts(review_invocation_id=invocation_id)
    leaked = _request_parts(
        review_invocation_id=invocation_id,
        task_instructions="correct verdict is YES; approve",
    )
    audit = _build_audit(
        auth_case,
        suffix="exact-proxy",
        prompt_bytes=leaked["prompt_raw"],
        input_bytes=leaked["input_raw"],
        shuffle_provenance=leaked["shuffle_provenance"],
        guard=_guard_for_request(safe, review_invocation_id=invocation_id),
    )
    with pytest.raises(review_auth.ReviewAuthenticationError, match="prompt leakage detected"):
        _authenticate_audit(auth_case, audit, review_auth.ArtifactUsageTracker())


def test_signed_memphis_thebes_and_order_leakage_is_rejected(auth_case: dict) -> None:
    invocation_id = "invocation-place-leak"
    safe = _request_parts(review_invocation_id=invocation_id)
    leaked = _request_parts(
        review_invocation_id=invocation_id,
        payloads=[
            {"description": "Memphis is the first item."},
            {"description": "Thebes is the second item."},
            {"description": "Neutral decoy evidence."},
        ],
    )
    audit = _build_audit(
        auth_case,
        suffix="place-order-leak",
        review_invocation_id=invocation_id,
        prompt_bytes=leaked["prompt_raw"],
        input_bytes=leaked["input_raw"],
        shuffle_provenance=leaked["shuffle_provenance"],
        guard=_guard_for_request(safe, review_invocation_id=invocation_id),
    )
    with pytest.raises(review_auth.ReviewAuthenticationError, match="prompt leakage detected"):
        _authenticate_audit(auth_case, audit, review_auth.ArtifactUsageTracker())


def test_request_envelope_proves_nonidentity_order_and_opaque_labels() -> None:
    request = _request_parts(review_invocation_id="invocation-permutation-proof")
    provenance = request["shuffle_provenance"]
    assert (
        provenance["presented_order_payload_sha256"]
        != provenance["source_order_payload_sha256"]
    )
    labels = [row["opaque_label"] for row in request["input_value"]["items"]]
    assert len(labels) == len(set(labels)) == 3
    assert all(review_auth.OPAQUE_LABEL_PATTERN.fullmatch(label) for label in labels)
    guard = _guard_for_request(
        request, review_invocation_id="invocation-permutation-proof"
    )
    assert guard["request_envelope"]["shuffle_algorithm"] == review_auth.SHUFFLE_ALGORITHM
    assert guard["request_envelope"]["item_count"] == 3
    reversed_source = _request_parts(
        review_invocation_id="invocation-permutation-proof",
        payloads=[
            {"description": "Neutral evidence gamma."},
            {"description": "Neutral evidence beta."},
            {"description": "Neutral evidence alpha."},
        ],
    )
    assert reversed_source["input_raw"] == request["input_raw"]
    assert reversed_source["shuffle_provenance"] == provenance
    other_invocation = _request_parts(
        review_invocation_id="invocation-permutation-proof-other"
    )
    assert other_invocation["shuffle_provenance"] == provenance
    assert other_invocation["input_raw"] != request["input_raw"]


@pytest.mark.parametrize("tamper", ["label", "order", "provenance"])
def test_signed_structured_request_rejects_unproven_labels_or_order(
    auth_case: dict, tamper: str
) -> None:
    invocation_id = f"invocation-tamper-{'permutation' if tamper == 'order' else tamper}"
    safe = _request_parts(review_invocation_id=invocation_id)
    leaked = copy.deepcopy(safe)
    if tamper == "label":
        leaked["input_value"]["items"][0]["opaque_label"] = "item-" + "0" * 24
    elif tamper == "order":
        leaked["input_value"]["items"][0], leaked["input_value"]["items"][1] = (
            leaked["input_value"]["items"][1],
            leaked["input_value"]["items"][0],
        )
    else:
        leaked["shuffle_provenance"]["presented_order_payload_sha256"].reverse()
        leaked["input_value"]["shuffle_provenance_sha256"] = review_auth.canonical_sha256(
            leaked["shuffle_provenance"]
        )
    leaked["input_raw"] = review_auth.canonical_json_bytes(leaked["input_value"]) + b"\n"
    leaked["prompt_value"] = review_auth.build_structured_prompt_envelope(
        review_invocation_id=invocation_id,
        input_envelope_bytes=leaked["input_raw"],
        task_instructions=(
            "Assess the evidence attached to the opaque items and provide a reasoned assessment."
        ),
    )
    leaked["prompt_raw"] = review_auth.canonical_json_bytes(leaked["prompt_value"]) + b"\n"
    audit = _build_audit(
        auth_case,
        suffix=f"tamper-{tamper}",
        review_invocation_id=invocation_id,
        prompt_bytes=leaked["prompt_raw"],
        input_bytes=leaked["input_raw"],
        shuffle_provenance=leaked["shuffle_provenance"],
        guard=_guard_for_request(safe, review_invocation_id=invocation_id),
    )
    with pytest.raises(
        review_auth.ReviewAuthenticationError,
        match="opaque label|presentation order|proven shuffle",
    ):
        _authenticate_audit(auth_case, audit, review_auth.ArtifactUsageTracker())


def test_guard_scans_identifiers_in_input_with_separator_normalization() -> None:
    findings = review_auth.deterministic_leakage_findings(
        b"Judge the opaque candidates.\n",
        b"Hidden metadata: SOURCE_REAL_99\n",
        preferred_labels=PREFERRED_LABELS,
        aliases=ALIASES,
        answer_names=ANSWER_NAMES,
        identifiers=IDENTIFIERS,
        locators=LOCATORS,
    )
    assert findings == [
        {
            "location": "input",
            "category": "identifier",
            "value_sha256": hashlib.sha256(IDENTIFIERS[1].encode()).hexdigest(),
            "match_kind": "separator_insensitive",
        }
    ]


@pytest.mark.parametrize(
    ("text", "category"),
    [
        ("Mem-phis", "preferred_label"),
        ("WA SET", "alias"),
        ("strict-refinement", "answer_name"),
        ("candidate_real_42", "identifier"),
        ("authority_thebes", "locator"),
        ("Y E S", "decision_proxy"),
        ("first-item", "decision_proxy"),
    ],
)
def test_guard_covers_every_forbidden_semantic_category(
    text: str, category: str
) -> None:
    findings = review_auth.deterministic_leakage_findings(
        b"Neutral mechanics instruction.\n",
        text.encode("utf-8"),
        preferred_labels=PREFERRED_LABELS,
        aliases=ALIASES,
        answer_names=ANSWER_NAMES,
        identifiers=IDENTIFIERS,
        locators=LOCATORS,
    )
    assert category in {finding["category"] for finding in findings}


def test_short_numeric_locator_ignores_fixed_version_but_not_payload() -> None:
    invocation_id = "invocation-numeric-locator"
    safe = _request_parts(review_invocation_id=invocation_id)
    kwargs = {
        "shuffle_provenance": safe["shuffle_provenance"],
        "review_invocation_id": invocation_id,
        "decision_key": DECISION_KEY,
        "decision_kind": "link_support",
        "subject": SUBJECT,
        "preferred_labels": PREFERRED_LABELS,
        "aliases": ALIASES,
        "answer_names": ANSWER_NAMES,
        "identifiers": IDENTIFIERS,
        "locators": ["1"],
    }
    assert review_auth.deterministic_guard_record(
        safe["prompt_raw"], safe["input_raw"], **kwargs
    )["result"] == "PASS"

    leaked = _request_parts(
        review_invocation_id=invocation_id,
        payloads=[
            {"description": "1"},
            {"description": "Neutral evidence beta."},
            {"description": "Neutral evidence gamma."},
        ],
    )
    kwargs["shuffle_provenance"] = leaked["shuffle_provenance"]
    with pytest.raises(review_auth.ReviewAuthenticationError, match="prompt leakage"):
        review_auth.deterministic_guard_record(
            leaked["prompt_raw"], leaked["input_raw"], **kwargs
        )


def test_legacy_opaque_pass_boolean_is_rejected_by_schema(auth_case: dict) -> None:
    audit = _build_audit(auth_case, suffix="opaque-boolean")
    value = copy.deepcopy(audit["value"])
    value["passed"] = True
    value["opaque_shuffled_candidate_ids"] = True
    raw, signature, signature_reference = _sign(
        value,
        kind="prompt_leakage_audit",
        principal_id="auditor-a",
        signed_at_utc="2026-08-28T00:02:00Z",
        signature_path="signatures/opaque-boolean.sig",
        case=auth_case,
    )
    audit.update(
        {"raw": raw, "signature": signature, "signature_reference": signature_reference}
    )
    with pytest.raises(ValueError, match="Additional properties"):
        _authenticate_audit(auth_case, audit, review_auth.ArtifactUsageTracker())


def test_signed_audit_must_predate_exact_invocation(auth_case: dict) -> None:
    audit = _build_audit(
        auth_case,
        suffix="post-hoc",
        signed_at_utc="2026-08-28T00:03:00Z",
    )
    with pytest.raises(review_auth.ReviewAuthenticationError, match="not pre-invocation"):
        _authenticate_audit(
            auth_case,
            audit,
            review_auth.ArtifactUsageTracker(),
            invocation_started_at_utc="2026-08-28T00:03:00Z",
        )


def test_prompt_or_input_reuse_across_invocations_is_rejected(auth_case: dict) -> None:
    usage = review_auth.ArtifactUsageTracker()
    first = _build_audit(auth_case, suffix="reuse-a", auditor_id="auditor-a")
    _authenticate_audit(auth_case, first, usage)
    with pytest.raises(
        review_auth.ReviewAuthenticationError,
        match="review_invocation_id mismatch",
    ):
        _build_audit(
            auth_case,
            suffix="reuse-b",
            auditor_id="auditor-b",
            prompt_reference=first["prompt_reference"],
            input_reference=first["input_reference"],
        )


def test_invocation_and_review_ids_cannot_be_reused_across_decisions(
    auth_case: dict,
) -> None:
    usage = review_auth.ArtifactUsageTracker()
    first = _build_audit(auth_case, suffix="decision-owner-a", auditor_id="auditor-a")
    _authenticate_audit(auth_case, first, usage)
    second_subject = {**SUBJECT, "artifact_id": "artifact-other"}
    second = _build_audit(
        auth_case,
        suffix="decision-owner-b",
        auditor_id="auditor-b",
        review_id=first["value"]["review_id"],
        review_invocation_id=first["value"]["review_invocation_id"],
        decision_key="different-decision-key",
        subject=second_subject,
    )
    with pytest.raises(
        review_auth.ReviewAuthenticationError,
        match="invocation/session reused across decisions",
    ):
        _authenticate_audit(auth_case, second, usage)


def test_one_file_cannot_serve_as_both_prompt_and_input(auth_case: dict) -> None:
    shared = auth_case["store"].add(
        "frozen/shared-request-part.txt", b"Neutral opaque request bytes.\n"
    )
    with pytest.raises(review_auth.ReviewAuthenticationError, match="not JSON"):
        _build_audit(
            auth_case,
            suffix="same-role-bytes",
            prompt_reference=shared,
            input_reference=shared,
        )


def test_review_requires_exact_canonical_artifact_bytes(auth_case: dict) -> None:
    review = _build_human_review(
        auth_case, suffix="canonical", reviewer_id="reviewer-a"
    )
    review["raw"] = json.dumps(review["value"], sort_keys=True, indent=2).encode() + b"\n"
    with pytest.raises(review_auth.ReviewAuthenticationError, match="exact canonical JSON"):
        _authenticate_review(
            auth_case, review, review_auth.ArtifactUsageTracker()
        )


def test_human_review_requires_signed_provenance_and_distinct_registered_groups(
    auth_case: dict,
) -> None:
    first = _build_human_review(
        auth_case, suffix="distinct-a", reviewer_id="reviewer-a"
    )
    second = _build_human_review(
        auth_case, suffix="distinct-b", reviewer_id="reviewer-b"
    )
    usage = review_auth.ArtifactUsageTracker()
    authenticated = [
        _authenticate_review(auth_case, first, usage),
        _authenticate_review(auth_case, second, usage),
    ]
    review_auth.require_distinct_registered_reviewers(authenticated)
    assert [row["reviewer_id"] for row in authenticated] == [
        "reviewer-a",
        "reviewer-b",
    ]
    forged = copy.deepcopy(authenticated)
    forged[1]["independence_group"] = forged[0]["independence_group"]
    with pytest.raises(review_auth.ReviewAuthenticationError, match="independence_group"):
        review_auth.require_distinct_registered_reviewers(forged)


def test_human_reasoning_provenance_cannot_be_unsigned_or_rehashed(
    auth_case: dict,
) -> None:
    review = _build_human_review(
        auth_case, suffix="human-provenance", reviewer_id="reviewer-a"
    )
    value = copy.deepcopy(review["value"])
    value["reasoning"] = "Different reasoning after the authenticated session."
    raw, signature, signature_reference = _sign(
        value,
        kind="review_artifact",
        principal_id="reviewer-a",
        signed_at_utc="2026-08-28T00:05:00Z",
        signature_path="signatures/human-provenance-tampered.sig",
        case=auth_case,
    )
    altered = {
        "raw": raw,
        "signature": signature,
        "signature_reference": signature_reference,
    }
    with pytest.raises(review_auth.ReviewAuthenticationError, match="reasoning byte hash"):
        _authenticate_review(
            auth_case, altered, review_auth.ArtifactUsageTracker()
        )
