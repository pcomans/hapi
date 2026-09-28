"""Authenticated reviewer provenance and deterministic prompt-leakage guards.

The release-pinned reviewer registry is the only production trust root.  Detached
Ed25519 signatures prove who authored an audit or review; candidate-supplied keys and
unregistered identity strings never establish trust.  Generated keys are accepted
only when a caller explicitly opts into the test-only mechanics tier.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Callable, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from schema_validation import validate_schema


TRUSTED_REVIEWERS_RELATIVE = (
    "docs/evaluations/site-graph-v0/trusted-reviewers.json"
)
REGISTRY_SCHEMA_VERSION = "site-graph-v0-trusted-reviewers/1"
REVIEW_SCHEMA_VERSION = "site-graph-v0-review-artifact/4"
AUDIT_SCHEMA_VERSION = "site-graph-v0-prompt-leakage-audit/5"
SIGNATURE_CONTEXT = "hapi-site-graph-v0-review-evidence/1"
GUARD_VERSION = "site-graph-v0-deterministic-prompt-leakage-guard/3"
AUDIT_METHOD = "deterministic_prompt_leakage_guard/3"
SEMANTIC_AUDIT_METHOD = "independent_semantic_prompt_audit/1"
PROMPT_ENVELOPE_SCHEMA_VERSION = "site-graph-v0-review-prompt-envelope/2"
INPUT_ENVELOPE_SCHEMA_VERSION = "site-graph-v0-review-input-envelope/2"
PROMPT_TEMPLATE_SCHEMA_VERSION = "site-graph-v0-review-prompt-template/1"
SHUFFLE_PROVENANCE_SCHEMA_VERSION = "site-graph-v0-review-shuffle-provenance/1"
SHUFFLE_ALGORITHM = "sha256-ranked-nonidentity/1"
SHUFFLE_SEED_CONTEXT = "hapi-site-graph-v0-review-shuffle-seed/1"
SHUFFLE_RANK_CONTEXT = "hapi-site-graph-v0-review-shuffle-rank/1"
OPAQUE_LABEL_CONTEXT = "hapi-site-graph-v0-review-opaque-label/1"
OPAQUE_LABEL_PATTERN = re.compile(r"^item-[0-9a-f]{24}$")
OPAQUE_LABEL_SEARCH_PATTERN = re.compile(
    r"(?<![0-9A-Za-z_-])item-[0-9a-f]{24}(?![0-9A-Za-z_-])"
)
LLM_ASSESSMENTS = ("supported", "uncertain", "unsupported")
RESPONSE_CONTRACT = {
    "format": "canonical_json_object",
    "exact_fields": ["assessment", "reasoning"],
    "assessment_values": list(LLM_ASSESSMENTS),
    "reasoning_contract": "nonempty_string_without_outer_whitespace",
}
DECISION_TASKS = {
    "link_support": {
        "claim": "The presented evidence establishes the proposed direct artifact-to-authority link bound to this request.",
        "question": "Does the presented evidence support that direct-link claim?",
    },
    "strict_refinement_support": {
        "claim": "The proposed authority target is a strict refinement of the baseline authority target bound to this request.",
        "question": "Does the presented evidence support that directional strict-refinement claim?",
    },
    "equivalence_support": {
        "claim": "The two authority targets bound to this request denote the same authority identity.",
        "question": "Does the presented evidence support that identity-equivalence claim?",
    },
    "distinctness_support": {
        "claim": "The two authority targets bound to this request denote distinct authority identities.",
        "question": "Does the presented evidence support that identity-distinctness claim?",
    },
    "mention_status_resolution": {
        "claim": "The proposed mention-resolution status bound to this request is supported relative to the frozen baseline statuses.",
        "question": "Does the presented evidence support that mention-status claim?",
    },
}
REVIEW_PROMPT_TEMPLATE = {
    "schema_version": PROMPT_TEMPLATE_SCHEMA_VERSION,
    "instructions": [
        "Evaluate only the content presented in each option payload.",
        "Treat each opaque label only as an option handle and do not infer meaning from its bytes or presentation order.",
        "Apply only the release-defined task selected by decision_kind. Treat subject_binding_sha256 only as an integrity binding, never as evidence.",
        "Return exactly one response object satisfying the response contract.",
    ],
    "decision_tasks": DECISION_TASKS,
    "option_slots": {
        "input_schema_version": INPUT_ENVELOPE_SCHEMA_VERSION,
        "items_path": "$.items[*]",
        "opaque_label_path": "$.items[*].opaque_label",
        "payload_path": "$.items[*].payload",
    },
    "response_contract": RESPONSE_CONTRACT,
}
PROMPT_TEMPLATE_SHA256 = hashlib.sha256(
    json.dumps(
        REVIEW_PROMPT_TEMPLATE,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
).hexdigest()
SEMANTIC_AUDIT_LIMITATION = (
    "A signed semantic prompt audit records one independent pre-invocation review; "
    "it reduces known leakage risk but does not prove semantic perfection."
)

# These cues are never needed to describe evidence. They either state a result or
# tell the model how position/order should map to a result. Keeping this list in the
# verifier prevents a signed audit from silently narrowing the guard.
DECISION_PROXY_STRINGS = frozenset(
    {
        "accept",
        "accepted",
        "answer is",
        "answer key",
        "approve",
        "approved",
        "bottom",
        "choose first",
        "choose last",
        "choose second",
        "correct",
        "correct answer",
        "correct verdict",
        "different",
        "false",
        "favor",
        "favorable",
        "favored",
        "first",
        "first item",
        "first option",
        "former",
        "gold label",
        "ground truth",
        "incorrect",
        "index",
        "last",
        "last item",
        "last option",
        "latter",
        "left",
        "match",
        "merge",
        "negative",
        "no",
        "oppose",
        "option",
        "order",
        "ordinal",
        "position",
        "positive",
        "preferred",
        "priority",
        "probability",
        "rank",
        "reject",
        "rejected",
        "right",
        "same",
        "score",
        "second",
        "second item",
        "second option",
        "selected",
        "selection",
        "sequence",
        "split",
        "support",
        "third",
        "top",
        "true",
        "unfavorable",
        "verdict is",
        "warrant",
        "warrants",
        "winner",
        "yes",
    }
)

ArtifactReader = Callable[[dict], bytes]


class ReviewAuthenticationError(ValueError):
    """A review identity, signature, provenance, or leakage binding is invalid."""


def _reject_constant(value: str) -> None:
    raise ReviewAuthenticationError(f"non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ReviewAuthenticationError(f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def strict_json_object(raw: bytes, *, label: str) -> dict:
    """Parse UTF-8 JSON without duplicate keys or non-finite numbers."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ReviewAuthenticationError(f"{label} is not UTF-8") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as error:
        raise ReviewAuthenticationError(f"{label} is not JSON: {error}") from error
    if not isinstance(value, dict):
        raise ReviewAuthenticationError(f"{label} must be a JSON object")
    return value


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _require_canonical_artifact_bytes(raw: bytes, value: dict, *, label: str) -> None:
    expected = canonical_json_bytes(value) + b"\n"
    if raw != expected:
        raise ReviewAuthenticationError(
            f"{label} bytes must be exact canonical JSON followed by one newline"
        )


def parse_llm_raw_response(raw: bytes) -> dict:
    """Parse the only authenticated LLM response representation.

    Provider prose, markdown fences, duplicate fields, extra metadata, and wrapper-
    only decisions are deliberately not accepted as review evidence.
    """
    response = strict_json_object(raw, label="LLM raw response")
    _require_canonical_artifact_bytes(raw, response, label="LLM raw response")
    _exact_keys(
        response,
        {"assessment", "reasoning"},
        label="LLM raw response",
    )
    if response["assessment"] not in LLM_ASSESSMENTS:
        raise ReviewAuthenticationError(
            "LLM raw response assessment is not an allowed review outcome"
        )
    _string(response["reasoning"], label="LLM raw response reasoning")
    return response


def _parse_time(value: str, *, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ReviewAuthenticationError(f"{label} is not an RFC3339 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReviewAuthenticationError(f"{label} must include a UTC offset")
    return parsed


def _normalize_reference(reference: dict, *, label: str) -> dict:
    if not isinstance(reference, dict) or set(reference) != {
        "path",
        "sha256",
        "git_blob_oid",
    }:
        raise ReviewAuthenticationError(f"{label} must be an exact artifact reference")
    path_value = reference["path"]
    if not isinstance(path_value, str):
        raise ReviewAuthenticationError(f"{label} path must be a string")
    path = PurePosixPath(path_value)
    if (
        not path_value
        or path.is_absolute()
        or ".." in path.parts
        or path.as_posix() != path_value
    ):
        raise ReviewAuthenticationError(
            f"{label} path must be normalized repository-relative: {path_value!r}"
        )
    sha256_value = reference["sha256"]
    blob_value = reference["git_blob_oid"]
    if not isinstance(sha256_value, str) or re.fullmatch(r"[0-9a-f]{64}", sha256_value) is None:
        raise ReviewAuthenticationError(f"{label} has an invalid SHA-256")
    if not isinstance(blob_value, str) or re.fullmatch(r"[0-9a-f]{40,64}", blob_value) is None:
        raise ReviewAuthenticationError(f"{label} has an invalid Git blob object ID")
    return dict(reference)


def _read_bound_artifact(
    reference: dict,
    *,
    read_artifact: ArtifactReader,
    label: str,
    require_nonempty: bool = True,
) -> bytes:
    normalized = _normalize_reference(reference, label=label)
    raw = read_artifact(normalized)
    if not isinstance(raw, bytes):
        raise ReviewAuthenticationError(f"{label} reader must return bytes")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != normalized["sha256"]:
        raise ReviewAuthenticationError(
            f"{label} SHA-256 mismatch: {actual} != {normalized['sha256']}"
        )
    if require_nonempty and not raw.strip():
        raise ReviewAuthenticationError(f"{label} bytes must be nonempty")
    return raw


def _decode_public_key(value: str) -> bytes:
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, UnicodeEncodeError) as error:
        raise ReviewAuthenticationError("reviewer public key is not strict base64") from error
    if len(raw) != 32:
        raise ReviewAuthenticationError("reviewer Ed25519 public key must be 32 bytes")
    return raw


def reviewer_key_id(public_key_base64: str) -> str:
    return hashlib.sha256(_decode_public_key(public_key_base64)).hexdigest()


def _validate_registry_semantics(
    registry: dict,
    *,
    allow_test_registry: bool,
    require_configured: bool,
) -> dict[str, dict]:
    if registry.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        raise ReviewAuthenticationError("unsupported trusted reviewer registry version")
    if registry.get("signature_scheme") != "ed25519":
        raise ReviewAuthenticationError("trusted reviewer registry signature scheme must be ed25519")
    if registry.get("signature_context") != SIGNATURE_CONTEXT:
        raise ReviewAuthenticationError("trusted reviewer registry signature context mismatch")
    status = registry.get("status")
    if status not in {"CONFIGURED", "NOT_CONFIGURED"}:
        raise ReviewAuthenticationError("trusted reviewer registry status is invalid")
    tier = registry.get("trust_tier")
    if tier not in {"PRODUCTION", "TEST_ONLY_MECHANICS"}:
        raise ReviewAuthenticationError("trusted reviewer registry trust tier is invalid")
    if tier == "TEST_ONLY_MECHANICS" and not allow_test_registry:
        raise ReviewAuthenticationError(
            "TEST_ONLY_MECHANICS reviewer keys cannot satisfy production policy"
        )
    identities = registry.get("identities")
    if not isinstance(identities, list):
        raise ReviewAuthenticationError("trusted reviewer identities must be an array")
    if status == "NOT_CONFIGURED":
        if identities:
            raise ReviewAuthenticationError(
                "NOT_CONFIGURED trusted reviewer registry must contain no identities"
            )
        if require_configured:
            raise ReviewAuthenticationError(
                "trusted reviewer registry is NOT_CONFIGURED"
            )
        return {}
    if not identities:
        raise ReviewAuthenticationError(
            "CONFIGURED trusted reviewer registry must contain identities"
        )
    principal_ids: set[str] = set()
    key_ids: set[str] = set()
    credential_ids: set[str] = set()
    index: dict[str, dict] = {}
    ordered_principals: list[str] = []
    for identity in identities:
        if not isinstance(identity, dict):
            raise ReviewAuthenticationError("trusted reviewer identity must be an object")
        principal_id = identity.get("principal_id")
        group = identity.get("independence_group")
        key_id = identity.get("key_id")
        if not all(isinstance(value, str) and value and not any(c.isspace() for c in value) for value in (principal_id, group)):
            raise ReviewAuthenticationError("reviewer principal and group IDs must be non-whitespace tokens")
        if principal_id in principal_ids:
            raise ReviewAuthenticationError(f"duplicate reviewer principal ID: {principal_id}")
        if key_id in key_ids:
            raise ReviewAuthenticationError(f"duplicate reviewer key ID: {key_id}")
        if reviewer_key_id(identity.get("public_key_base64", "")) != key_id:
            raise ReviewAuthenticationError(f"reviewer key ID mismatch: {principal_id}")
        roles = identity.get("roles")
        methods = identity.get("methods")
        if (
            not isinstance(roles, list)
            or not roles
            or len(roles) != len(set(roles))
            or roles != sorted(roles)
            or set(roles) - {"reviewer", "prompt_auditor"}
        ):
            raise ReviewAuthenticationError(
                f"reviewer roles must be unique and sorted: {principal_id}"
            )
        audit_methods = {AUDIT_METHOD, SEMANTIC_AUDIT_METHOD}
        allowed_methods = {"human", "llm", *audit_methods}
        if (
            not isinstance(methods, list)
            or not methods
            or len(methods) != len(set(methods))
            or methods != sorted(methods)
            or set(methods) - allowed_methods
        ):
            raise ReviewAuthenticationError(
                f"reviewer methods must be unique and sorted: {principal_id}"
            )
        if "reviewer" not in roles and set(methods) & {"human", "llm"}:
            raise ReviewAuthenticationError(
                f"non-reviewer principal has review methods: {principal_id}"
            )
        if "prompt_auditor" not in roles and set(methods) & audit_methods:
            raise ReviewAuthenticationError(
                f"non-auditor principal has an audit method: {principal_id}"
            )
        if "reviewer" in roles and not set(methods) & {"human", "llm"}:
            raise ReviewAuthenticationError(
                f"reviewer principal lacks a review method: {principal_id}"
            )
        if "prompt_auditor" in roles and not set(methods) & audit_methods:
            raise ReviewAuthenticationError(
                f"prompt auditor lacks an audit method: {principal_id}"
            )
        valid_from = _parse_time(
            identity.get("valid_from_utc", ""),
            label=f"reviewer {principal_id} valid_from_utc",
        )
        valid_until_value = identity.get("valid_until_utc")
        if valid_until_value is not None:
            if not isinstance(valid_until_value, str):
                raise ReviewAuthenticationError(
                    f"reviewer {principal_id} valid_until_utc must be a timestamp or null"
                )
            valid_until = _parse_time(
                valid_until_value,
                label=f"reviewer {principal_id} valid_until_utc",
            )
            if valid_until <= valid_from:
                raise ReviewAuthenticationError(
                    f"reviewer validity interval is empty: {principal_id}"
                )
        credential = identity.get("credential_provenance")
        if not isinstance(credential, dict):
            raise ReviewAuthenticationError(
                f"reviewer credential provenance is missing: {principal_id}"
            )
        credential_id = credential.get("credential_id")
        if not isinstance(credential_id, str) or not credential_id:
            raise ReviewAuthenticationError(
                f"reviewer credential ID is missing: {principal_id}"
            )
        if credential_id in credential_ids:
            raise ReviewAuthenticationError(
                f"reviewer credential ID is reused: {credential_id}"
            )
        evidence_hash = credential.get("evidence_sha256")
        if not isinstance(evidence_hash, str) or re.fullmatch(r"[0-9a-f]{64}", evidence_hash) is None:
            raise ReviewAuthenticationError(
                f"reviewer credential evidence hash is invalid: {principal_id}"
            )
        verified_at = credential.get("verified_at_utc")
        if not isinstance(verified_at, str):
            raise ReviewAuthenticationError(
                f"reviewer credential verification time is missing: {principal_id}"
            )
        _parse_time(verified_at, label=f"reviewer {principal_id} credential verified_at_utc")
        principal_ids.add(principal_id)
        key_ids.add(key_id)
        credential_ids.add(credential_id)
        ordered_principals.append(principal_id)
        index[principal_id] = identity
    if ordered_principals != sorted(ordered_principals):
        raise ReviewAuthenticationError(
            "trusted reviewer identities must be sorted by principal_id"
        )
    return index


def validate_reviewer_registry(
    registry: dict,
    *,
    schema_path: Path | None = None,
    allow_test_registry: bool = False,
    require_configured: bool = True,
) -> dict[str, dict]:
    """Validate a registry and return its exact principal lookup table.

    Production callers must retain the default ``allow_test_registry=False``.  The
    explicit opt-in exists solely so adversarial unit tests can exercise cryptography
    without pretending generated keys are production identities.
    """
    if schema_path is not None:
        validate_schema(registry, schema_path, "trusted reviewer registry")
    return _validate_registry_semantics(
        registry,
        allow_test_registry=allow_test_registry,
        require_configured=require_configured,
    )


def load_reviewer_registry(repo: Path, schema_root: Path) -> tuple[dict, dict]:
    """Load the fixed production registry and fail closed unless it is configured."""
    path = repo / TRUSTED_REVIEWERS_RELATIVE
    raw = path.read_bytes()
    registry = strict_json_object(raw, label="trusted reviewer registry")
    validate_reviewer_registry(
        registry,
        schema_path=schema_root / "trusted-reviewers.schema.json",
        allow_test_registry=False,
        require_configured=True,
    )
    return registry, {
        "path": TRUSTED_REVIEWERS_RELATIVE,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _forbidden_set_binding(
    values: Sequence[str], *, label: str, allow_empty: bool = False
) -> dict:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ReviewAuthenticationError(f"{label} must be a sequence of strings")
    exact = list(values)
    if not exact and not allow_empty:
        raise ReviewAuthenticationError(f"{label} must be nonempty")
    if any(not isinstance(value, str) or not value or value.strip() != value for value in exact):
        raise ReviewAuthenticationError(
            f"{label} values must be nonempty strings without outer whitespace"
        )
    if len(exact) != len(set(exact)):
        raise ReviewAuthenticationError(f"{label} contains duplicate exact values")
    normalized = [_normalized_text(value) for value in exact]
    if len(normalized) != len(set(normalized)):
        raise ReviewAuthenticationError(
            f"{label} contains Unicode/case-equivalent duplicate values"
        )
    ordered = sorted(exact)
    return {"count": len(ordered), "canonical_sha256": canonical_sha256(ordered)}


def _normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _compact_text(value: str) -> str:
    return "".join(character for character in _normalized_text(value) if character.isalnum())


def canonical_forbidden_values(values: Sequence[str]) -> list[str]:
    """Collapse Unicode/case-equivalent values without weakening text matching."""
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ReviewAuthenticationError("forbidden values must be a sequence of strings")
    by_normalized: dict[str, str] = {}
    for value in sorted(values):
        _string(value, label="forbidden value")
        by_normalized.setdefault(_normalized_text(value), value)
    return sorted(by_normalized.values())


def _exact_keys(value: object, expected: set[str], *, label: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise ReviewAuthenticationError(
            f"{label} must contain exactly {sorted(expected)}"
        )
    return value


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ReviewAuthenticationError(
            f"{label} must be a nonempty string without outer whitespace"
        )
    return value


def _sha256_string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ReviewAuthenticationError(f"{label} must be a lowercase SHA-256")
    return value


def _shuffle_seed_sha256(
    *,
    decision_key: str,
    decision_kind: str,
    subject: dict,
) -> str:
    return canonical_sha256(
        {
            "context": SHUFFLE_SEED_CONTEXT,
            "decision_key": decision_key,
            "decision_kind": decision_kind,
            "subject": subject,
        }
    )


def _shuffle_rank(seed_sha256: str, payload_sha256: str) -> str:
    return canonical_sha256(
        {
            "context": SHUFFLE_RANK_CONTEXT,
            "seed_sha256": seed_sha256,
            "payload_sha256": payload_sha256,
        }
    )


def _opaque_label(seed_sha256: str, payload_sha256: str) -> str:
    digest = canonical_sha256(
        {
            "context": OPAQUE_LABEL_CONTEXT,
            "seed_sha256": seed_sha256,
            "payload_sha256": payload_sha256,
        }
    )
    return f"item-{digest[:24]}"


def _iter_json_strings(value: object, path: tuple[object, ...] = ()):
    """Yield JSON string keys and values with deterministic structural paths."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                yield (*path, "@key"), key
            yield from _iter_json_strings(item, (*path, key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_json_strings(item, (*path, index))


def _reject_opaque_label_channels(
    value: object,
    *,
    allowed_value_paths: set[tuple[object, ...]],
    label: str,
) -> None:
    """Allow concrete opaque labels only in declared option-label value slots."""
    for path, text in _iter_json_strings(value):
        matches = list(OPAQUE_LABEL_SEARCH_PATTERN.finditer(text))
        if not matches:
            continue
        if path not in allowed_value_paths or len(matches) != 1 or matches[0].group() != text:
            raise ReviewAuthenticationError(
                f"{label} contains an opaque label outside a schema-defined option slot"
            )


def _reject_reserved_payload_slots(payload: dict, *, label: str) -> None:
    for path, text in _iter_json_strings(payload):
        if path and path[-1] == "@key" and text == "opaque_label":
            raise ReviewAuthenticationError(
                f"{label} cannot define the reserved opaque_label option slot"
            )
    _reject_opaque_label_channels(
        payload,
        allowed_value_paths=set(),
        label=label,
    )


def build_structured_input_envelope(
    payloads: Sequence[dict],
    *,
    review_invocation_id: str,
    decision_key: str,
    decision_kind: str,
    subject: dict,
) -> tuple[dict, dict]:
    """Build an opaque request input and hidden, signed order provenance.

    The provenance belongs in the pre-invocation audit, not in the bytes sent to
    the model. The model sees only derived opaque labels and the shuffled order;
    the verifier can reproduce both exactly.
    """
    _string(review_invocation_id, label="review invocation ID")
    _string(decision_key, label="decision key")
    _string(decision_kind, label="decision kind")
    if not isinstance(subject, dict) or len(subject) < 2:
        raise ReviewAuthenticationError("review subject must be an object with two fields")
    if isinstance(payloads, (str, bytes)) or not isinstance(payloads, Sequence):
        raise ReviewAuthenticationError("review payloads must be a sequence")
    payload_values = list(payloads)
    if len(payload_values) < 2:
        raise ReviewAuthenticationError("structured review input requires at least two items")
    if any(not isinstance(payload, dict) or not payload for payload in payload_values):
        raise ReviewAuthenticationError("every structured review item payload must be an object")
    for index, payload in enumerate(payload_values):
        _reject_reserved_payload_slots(payload, label=f"review item payload {index}")
    # Canonical hash order is independent of caller order, so a producer cannot put
    # the intended answer first and rely on knowledge of the shuffle algorithm.
    payload_hashes = sorted(canonical_sha256(payload) for payload in payload_values)
    if len(payload_hashes) != len(set(payload_hashes)):
        raise ReviewAuthenticationError("structured review item payloads must be unique")
    seed_sha256 = _shuffle_seed_sha256(
        decision_key=decision_key,
        decision_kind=decision_kind,
        subject=subject,
    )
    presented_hashes = sorted(
        payload_hashes, key=lambda digest: (_shuffle_rank(seed_sha256, digest), digest)
    )
    # A ranked permutation can be the identity. That does not satisfy the explicit
    # presentation requirement, so this named algorithm applies one rotation.
    if presented_hashes == payload_hashes:
        presented_hashes = presented_hashes[1:] + presented_hashes[:1]
    payload_by_hash = {
        canonical_sha256(payload): payload for payload in payload_values
    }
    provenance = {
        "schema_version": SHUFFLE_PROVENANCE_SCHEMA_VERSION,
        "algorithm": SHUFFLE_ALGORITHM,
        "seed_sha256": seed_sha256,
        "source_order_payload_sha256": payload_hashes,
        "presented_order_payload_sha256": presented_hashes,
    }
    claim_semantics = _decision_claim_semantics(decision_kind, subject)
    input_envelope = {
        "schema_version": INPUT_ENVELOPE_SCHEMA_VERSION,
        "review_invocation_id": review_invocation_id,
        "decision_kind": decision_kind,
        "subject_binding_sha256": canonical_sha256(subject),
        "claim_semantics": claim_semantics,
        "shuffle_provenance_sha256": canonical_sha256(provenance),
        "items": [
            {
                "opaque_label": _opaque_label(seed_sha256, digest),
                "payload": payload_by_hash[digest],
            }
            for digest in presented_hashes
        ],
    }
    return input_envelope, provenance


def _decision_claim_semantics(decision_kind: str, subject: dict) -> dict:
    """Return release-defined, identity-free semantics for one exact subject."""
    task = DECISION_TASKS.get(decision_kind)
    if task is None:
        raise ReviewAuthenticationError("unsupported review decision kind")
    claim = {
        "decision_kind": decision_kind,
        "subject_binding_sha256": canonical_sha256(subject),
        "task": copy.deepcopy(task),
    }
    if decision_kind == "mention_status_resolution":
        proposed_status = subject.get("proposed_status")
        baseline_statuses = subject.get("baseline_statuses")
        allowed_statuses = {"resolved", "ambiguous", "unmatched"}
        if proposed_status not in allowed_statuses:
            raise ReviewAuthenticationError(
                "mention-status subject lacks an allowed proposed_status"
            )
        if (
            not isinstance(baseline_statuses, list)
            or not baseline_statuses
            or any(
                not isinstance(row, dict)
                or set(row) != {"mention_id", "status"}
                or not isinstance(row["mention_id"], str)
                or not row["mention_id"]
                or row["status"] not in allowed_statuses
                for row in baseline_statuses
            )
        ):
            raise ReviewAuthenticationError(
                "mention-status subject lacks allowed baseline_statuses"
            )
        claim["proposed_status"] = proposed_status
        claim["baseline_statuses"] = [row["status"] for row in baseline_statuses]
    return claim


def build_structured_prompt_envelope(
    *,
    review_invocation_id: str,
    input_envelope_bytes: bytes,
    task_instructions: str | None = None,
) -> dict:
    """Build the release-owned prompt bound to one structured input envelope.

    ``task_instructions`` is accepted only as a compatibility placeholder for older
    producers.  It is deliberately ignored: callers cannot add, remove, or alter
    model instructions.  The exact template and its digest are release constants.
    """
    _string(review_invocation_id, label="review invocation ID")
    if task_instructions is not None:
        _string(task_instructions, label="ignored legacy task instructions")
    if not isinstance(input_envelope_bytes, bytes) or not input_envelope_bytes:
        raise ReviewAuthenticationError("input envelope bytes must be nonempty bytes")
    input_envelope = strict_json_object(
        input_envelope_bytes, label="review input envelope"
    )
    _require_canonical_artifact_bytes(
        input_envelope_bytes, input_envelope, label="review input envelope"
    )
    decision_kind = input_envelope.get("decision_kind")
    if decision_kind not in DECISION_TASKS:
        raise ReviewAuthenticationError(
            "input envelope lacks a release-defined decision task"
        )
    subject_binding_sha256 = input_envelope.get("subject_binding_sha256")
    _sha256_string(
        subject_binding_sha256, label="input envelope subject binding"
    )
    claim_semantics = input_envelope.get("claim_semantics")
    if not isinstance(claim_semantics, dict):
        raise ReviewAuthenticationError(
            "input envelope lacks release-defined claim semantics"
        )
    return {
        "schema_version": PROMPT_ENVELOPE_SCHEMA_VERSION,
        "review_invocation_id": review_invocation_id,
        "decision_kind": decision_kind,
        "subject_binding_sha256": subject_binding_sha256,
        "claim_semantics": copy.deepcopy(claim_semantics),
        "decision_task": copy.deepcopy(DECISION_TASKS[decision_kind]),
        "input_envelope_sha256": hashlib.sha256(input_envelope_bytes).hexdigest(),
        "template_sha256": PROMPT_TEMPLATE_SHA256,
        "template": copy.deepcopy(REVIEW_PROMPT_TEMPLATE),
    }


def _validate_structured_request(
    prompt_bytes: bytes,
    input_bytes: bytes,
    *,
    shuffle_provenance: dict,
    review_invocation_id: str,
    decision_key: str,
    decision_kind: str,
    subject: dict,
) -> dict:
    prompt = strict_json_object(prompt_bytes, label="review prompt envelope")
    input_envelope = strict_json_object(input_bytes, label="review input envelope")
    _require_canonical_artifact_bytes(
        prompt_bytes, prompt, label="review prompt envelope"
    )
    _require_canonical_artifact_bytes(
        input_bytes, input_envelope, label="review input envelope"
    )
    _exact_keys(
        prompt,
        {
            "schema_version",
            "review_invocation_id",
            "decision_kind",
            "subject_binding_sha256",
            "claim_semantics",
            "decision_task",
            "input_envelope_sha256",
            "template_sha256",
            "template",
        },
        label="review prompt envelope",
    )
    if prompt["schema_version"] != PROMPT_ENVELOPE_SCHEMA_VERSION:
        raise ReviewAuthenticationError("unsupported review prompt envelope version")
    if prompt["review_invocation_id"] != review_invocation_id:
        raise ReviewAuthenticationError("prompt envelope review_invocation_id mismatch")
    expected_claim_semantics = _decision_claim_semantics(decision_kind, subject)
    expected_subject_binding = canonical_sha256(subject)
    if prompt["decision_kind"] != decision_kind:
        raise ReviewAuthenticationError("prompt envelope decision-kind binding mismatch")
    if prompt["subject_binding_sha256"] != expected_subject_binding:
        raise ReviewAuthenticationError("prompt envelope subject binding mismatch")
    if prompt["claim_semantics"] != expected_claim_semantics:
        raise ReviewAuthenticationError("prompt envelope claim semantics mismatch")
    if prompt["decision_task"] != DECISION_TASKS.get(decision_kind):
        raise ReviewAuthenticationError("prompt envelope decision task is not release-owned")
    if prompt["input_envelope_sha256"] != hashlib.sha256(input_bytes).hexdigest():
        raise ReviewAuthenticationError("prompt envelope input-byte binding mismatch")
    if prompt["template_sha256"] != PROMPT_TEMPLATE_SHA256:
        raise ReviewAuthenticationError("prompt envelope template hash is not release-owned")
    if prompt["template"] != REVIEW_PROMPT_TEMPLATE:
        raise ReviewAuthenticationError("prompt envelope template is not release-owned")
    if canonical_sha256(prompt["template"]) != prompt["template_sha256"]:
        raise ReviewAuthenticationError("prompt envelope template hash mismatch")
    _reject_opaque_label_channels(
        prompt,
        allowed_value_paths=set(),
        label="review prompt envelope",
    )

    _exact_keys(
        input_envelope,
        {
            "schema_version",
            "review_invocation_id",
            "decision_kind",
            "subject_binding_sha256",
            "claim_semantics",
            "shuffle_provenance_sha256",
            "items",
        },
        label="review input envelope",
    )
    if input_envelope["schema_version"] != INPUT_ENVELOPE_SCHEMA_VERSION:
        raise ReviewAuthenticationError("unsupported review input envelope version")
    if input_envelope["review_invocation_id"] != review_invocation_id:
        raise ReviewAuthenticationError("input envelope review_invocation_id mismatch")
    if input_envelope["decision_kind"] != decision_kind:
        raise ReviewAuthenticationError("input envelope decision-kind binding mismatch")
    if input_envelope["subject_binding_sha256"] != expected_subject_binding:
        raise ReviewAuthenticationError("input envelope subject binding mismatch")
    if input_envelope["claim_semantics"] != expected_claim_semantics:
        raise ReviewAuthenticationError("input envelope claim semantics mismatch")
    if input_envelope["shuffle_provenance_sha256"] != canonical_sha256(
        shuffle_provenance
    ):
        raise ReviewAuthenticationError("input envelope shuffle provenance binding mismatch")

    _exact_keys(
        shuffle_provenance,
        {
            "schema_version",
            "algorithm",
            "seed_sha256",
            "source_order_payload_sha256",
            "presented_order_payload_sha256",
        },
        label="review shuffle provenance",
    )
    if shuffle_provenance["schema_version"] != SHUFFLE_PROVENANCE_SCHEMA_VERSION:
        raise ReviewAuthenticationError("unsupported review shuffle provenance version")
    if shuffle_provenance["algorithm"] != SHUFFLE_ALGORITHM:
        raise ReviewAuthenticationError("unsupported review shuffle algorithm")
    expected_seed = _shuffle_seed_sha256(
        decision_key=decision_key,
        decision_kind=decision_kind,
        subject=subject,
    )
    if shuffle_provenance["seed_sha256"] != expected_seed:
        raise ReviewAuthenticationError("review shuffle seed/decision binding mismatch")
    for field in (
        "source_order_payload_sha256",
        "presented_order_payload_sha256",
    ):
        hashes = shuffle_provenance[field]
        if (
            not isinstance(hashes, list)
            or len(hashes) < 2
            or len(hashes) != len(set(hashes))
        ):
            raise ReviewAuthenticationError(
                f"review shuffle {field} must contain at least two unique hashes"
            )
        for index, digest in enumerate(hashes):
            _sha256_string(digest, label=f"review shuffle {field}[{index}]")
    source_hashes = shuffle_provenance["source_order_payload_sha256"]
    presented_hashes = shuffle_provenance["presented_order_payload_sha256"]
    if source_hashes != sorted(source_hashes):
        raise ReviewAuthenticationError("review shuffle source order is not canonical")
    if set(source_hashes) != set(presented_hashes):
        raise ReviewAuthenticationError("review shuffle source/presentation census mismatch")
    expected_presented = sorted(
        source_hashes,
        key=lambda digest: (_shuffle_rank(expected_seed, digest), digest),
    )
    if expected_presented == source_hashes:
        expected_presented = expected_presented[1:] + expected_presented[:1]
    if presented_hashes != expected_presented or presented_hashes == source_hashes:
        raise ReviewAuthenticationError("review presentation order is not the proven shuffle")

    items = input_envelope["items"]
    if not isinstance(items, list) or len(items) != len(presented_hashes):
        raise ReviewAuthenticationError("review input item census differs from shuffle")
    actual_presented: list[str] = []
    labels: list[str] = []
    for index, item in enumerate(items):
        _exact_keys(item, {"opaque_label", "payload"}, label=f"review item {index}")
        label = item["opaque_label"]
        if not isinstance(label, str) or OPAQUE_LABEL_PATTERN.fullmatch(label) is None:
            raise ReviewAuthenticationError(f"review item {index} label is not opaque")
        if not isinstance(item["payload"], dict) or not item["payload"]:
            raise ReviewAuthenticationError(f"review item {index} payload must be an object")
        digest = canonical_sha256(item["payload"])
        if label != _opaque_label(expected_seed, digest):
            raise ReviewAuthenticationError(
                f"review item {index} opaque label does not derive from provenance"
            )
        labels.append(label)
        actual_presented.append(digest)
    _reject_opaque_label_channels(
        input_envelope,
        allowed_value_paths={
            ("items", index, "opaque_label") for index in range(len(items))
        },
        label="review input envelope",
    )
    if len(labels) != len(set(labels)):
        raise ReviewAuthenticationError("review opaque labels must be unique")
    if actual_presented != presented_hashes:
        raise ReviewAuthenticationError("review input items are not in proven presentation order")
    return {
        "prompt_schema_version": PROMPT_ENVELOPE_SCHEMA_VERSION,
        "input_schema_version": INPUT_ENVELOPE_SCHEMA_VERSION,
        "shuffle_provenance_schema_version": SHUFFLE_PROVENANCE_SCHEMA_VERSION,
        "shuffle_algorithm": SHUFFLE_ALGORITHM,
        "prompt_template_sha256": PROMPT_TEMPLATE_SHA256,
        "review_invocation_id": review_invocation_id,
        "item_count": len(items),
        "opaque_labels_canonical_sha256": canonical_sha256(labels),
        "shuffle_provenance_sha256": canonical_sha256(shuffle_provenance),
    }


def _contains_normalized(haystack: str, needle: str) -> bool:
    start = r"(?<!\w)" if needle[0].isalnum() else ""
    end = r"(?!\w)" if needle[-1].isalnum() else ""
    return re.search(f"{start}{re.escape(needle)}{end}", haystack) is not None


def _separator_insensitive_contains(haystack: str, needle: str) -> bool:
    """Match punctuation variants without finding short IDs inside opaque hashes."""
    haystack_parts = re.findall(r"[^\W_]+", haystack, flags=re.UNICODE)
    compact_needle = _compact_text(needle)
    if len(compact_needle) < 2:
        return False
    for start in range(len(haystack_parts)):
        candidate = ""
        for part in haystack_parts[start:]:
            candidate += part
            if candidate == compact_needle:
                return True
            if len(candidate) >= len(compact_needle):
                break
    return False


def deterministic_leakage_findings(
    prompt_bytes: bytes,
    input_bytes: bytes,
    *,
    preferred_labels: Sequence[str],
    aliases: Sequence[str],
    answer_names: Sequence[str],
    identifiers: Sequence[str],
    locators: Sequence[str],
) -> list[dict]:
    """Find semantic-name, identifier, locator, and decision-cue leakage.

    NFKC + case-folded matching catches superficial casing/Unicode changes. A
    token-aware compacted match catches separator substitutions without treating
    substrings of opaque hashes as evidence. The whole exact request is scanned, so
    putting an answer in an example, payload key, or instruction does not exempt it.
    """
    decoded: list[tuple[str, str]] = []
    for label, raw in (("prompt", prompt_bytes), ("input", input_bytes)):
        if not isinstance(raw, bytes):
            raise ReviewAuthenticationError(f"{label} bytes must be bytes")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ReviewAuthenticationError(f"{label} bytes are not UTF-8") from error
        if not text.strip():
            raise ReviewAuthenticationError(f"{label} bytes must be nonempty")
        if "\x00" in text:
            raise ReviewAuthenticationError(f"{label} contains a NUL byte")
        decoded.append((label, text))
    categories = (
        ("preferred_label", preferred_labels, True),
        ("alias", aliases, True),
        ("answer_name", answer_names, True),
        ("identifier", identifiers, True),
        ("locator", locators, True),
        ("decision_proxy", sorted(DECISION_PROXY_STRINGS), False),
    )
    for category, values, allow_empty in categories:
        _forbidden_set_binding(
            values, label=f"{category} values", allow_empty=allow_empty
        )
    findings: list[dict] = []
    for location, text in decoded:
        normalized_haystack = _normalized_text(text)
        for category, values, _ in categories:
            for value in sorted(values):
                normalized_needle = _normalized_text(value)
                match_kind = None
                if _contains_normalized(normalized_haystack, normalized_needle):
                    match_kind = "normalized_literal"
                elif _separator_insensitive_contains(
                    normalized_haystack, normalized_needle
                ):
                    match_kind = "separator_insensitive"
                if match_kind is not None:
                    findings.append(
                        {
                            "location": location,
                            "category": category,
                            "value_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                            "match_kind": match_kind,
                        }
                    )
    return sorted(
        findings,
        key=lambda row: (
            row["location"],
            row["category"],
            row["value_sha256"],
            row["match_kind"],
        ),
    )


def deterministic_guard_record(
    prompt_bytes: bytes,
    input_bytes: bytes,
    *,
    shuffle_provenance: dict,
    review_invocation_id: str,
    decision_key: str,
    decision_kind: str,
    subject: dict,
    preferred_labels: Sequence[str],
    aliases: Sequence[str],
    answer_names: Sequence[str],
    identifiers: Sequence[str],
    locators: Sequence[str],
) -> dict:
    """Return the only acceptable deterministic guard record, or reject leakage."""
    request_envelope = _validate_structured_request(
        prompt_bytes,
        input_bytes,
        shuffle_provenance=shuffle_provenance,
        review_invocation_id=review_invocation_id,
        decision_key=decision_key,
        decision_kind=decision_kind,
        subject=subject,
    )
    # The prompt template is immutable release content validated above. Scan only
    # caller-controlled request surfaces; otherwise a short locator such as "1"
    # could collide with a fixed schema version it did not introduce.
    prompt_envelope = strict_json_object(prompt_bytes, label="review prompt envelope")
    input_envelope = strict_json_object(input_bytes, label="review input envelope")
    prompt_surface = canonical_json_bytes(
        [prompt_envelope["review_invocation_id"]]
    )
    input_surface = canonical_json_bytes(
        [
            input_envelope["review_invocation_id"],
            [item["payload"] for item in input_envelope["items"]],
        ]
    )
    findings = deterministic_leakage_findings(
        prompt_surface,
        input_surface,
        preferred_labels=preferred_labels,
        aliases=aliases,
        answer_names=answer_names,
        identifiers=identifiers,
        locators=locators,
    )
    if findings:
        rendered = ", ".join(
            f"{row['location']}:{row['category']}:{row['value_sha256']}"
            for row in findings
        )
        raise ReviewAuthenticationError(f"prompt leakage detected: {rendered}")
    prompt_sha = hashlib.sha256(prompt_bytes).hexdigest()
    input_sha = hashlib.sha256(input_bytes).hexdigest()
    return {
        "guard_version": GUARD_VERSION,
        "request_binding_sha256": canonical_sha256(
            {"prompt_sha256": prompt_sha, "input_sha256": input_sha}
        ),
        "request_envelope": request_envelope,
        "preferred_labels": _forbidden_set_binding(
            preferred_labels, label="preferred_labels", allow_empty=True
        ),
        "aliases": _forbidden_set_binding(
            aliases, label="aliases", allow_empty=True
        ),
        "answer_names": _forbidden_set_binding(
            answer_names, label="answer_names", allow_empty=True
        ),
        "identifiers": _forbidden_set_binding(
            identifiers, label="identifiers", allow_empty=True
        ),
        "locators": _forbidden_set_binding(
            locators, label="locators", allow_empty=True
        ),
        "decision_proxies": _forbidden_set_binding(
            sorted(DECISION_PROXY_STRINGS), label="decision_proxies"
        ),
        "result": "PASS",
        "findings": [],
    }


def semantic_prompt_assessment_record(
    prompt_bytes: bytes,
    input_bytes: bytes,
    *,
    reasoning: str,
) -> dict:
    """Build the signed semantic-auditor statement bound to exact request bytes.

    This helper only builds the statement shape.  The registered human auditor's
    detached signature supplies provenance for the judgment; neither this helper nor
    the deterministic guard claims that semantic neutrality can be proven perfectly.
    """
    if not isinstance(prompt_bytes, bytes) or not prompt_bytes:
        raise ReviewAuthenticationError("semantic audit prompt bytes must be nonempty")
    if not isinstance(input_bytes, bytes) or not input_bytes:
        raise ReviewAuthenticationError("semantic audit input bytes must be nonempty")
    _string(reasoning, label="semantic prompt audit reasoning")
    prompt_sha = hashlib.sha256(prompt_bytes).hexdigest()
    input_sha = hashlib.sha256(input_bytes).hexdigest()
    return {
        "request_binding_sha256": canonical_sha256(
            {"prompt_sha256": prompt_sha, "input_sha256": input_sha}
        ),
        "prompt_sha256": prompt_sha,
        "input_sha256": input_sha,
        "result": "PASS",
        "checks": {
            "label_specific_directives": "NONE_OBSERVED",
            "favorable_assessment_directives": "NONE_OBSERVED",
            "evidence_warrant_directives": "NONE_OBSERVED",
            "other_semantic_leakage": "NONE_OBSERVED",
        },
        "reasoning": reasoning,
        "limitation_acknowledgement": SEMANTIC_AUDIT_LIMITATION,
    }


def signature_statement_bytes(
    artifact: bytes | dict,
    *,
    artifact_kind: str,
) -> bytes:
    """Build the non-circular canonical statement covered by a detached signature.

    The signature file path is signed, while its SHA/blob fields and the statement
    digest are excluded because those values are known only after signing.  The
    verifier separately authenticates the exact detached signature bytes against the
    full reference.  Every other artifact field is covered.
    """
    if artifact_kind not in {"prompt_leakage_audit", "review_artifact"}:
        raise ReviewAuthenticationError(f"unsupported signed artifact kind: {artifact_kind}")
    if isinstance(artifact, bytes):
        value = strict_json_object(artifact, label=artifact_kind)
    elif isinstance(artifact, dict):
        value = copy.deepcopy(artifact)
    else:
        raise ReviewAuthenticationError("signed artifact must be bytes or an object")
    authentication = value.get("authentication")
    if not isinstance(authentication, dict):
        raise ReviewAuthenticationError("signed artifact lacks authentication metadata")
    signature = authentication.get("signature")
    if not isinstance(signature, dict) or not isinstance(signature.get("path"), str):
        raise ReviewAuthenticationError("signed artifact lacks a detached signature path")
    signature_path = _normalize_reference(signature, label="detached signature")["path"]
    authentication.pop("statement_sha256", None)
    authentication["signature"] = {"path": signature_path}
    return canonical_json_bytes(
        {
            "signature_context": SIGNATURE_CONTEXT,
            "artifact_kind": artifact_kind,
            "registry_id": authentication.get("registry_id"),
            "principal_id": authentication.get("principal_id"),
            "key_id": authentication.get("key_id"),
            "artifact": value,
        }
    )


@dataclass
class ArtifactUsageTracker:
    """Global one-run uniqueness state for review and audit artifacts."""

    _paths: dict[str, tuple[str, str]] = field(default_factory=dict)
    _digests: dict[str, tuple[str, str]] = field(default_factory=dict)
    _identifiers: dict[tuple[str, str], str] = field(default_factory=dict)
    _owner_reviews: dict[str, tuple[str, str]] = field(default_factory=dict)
    _review_owners: dict[str, tuple[str, str]] = field(default_factory=dict)

    def bind_owner(
        self, owner: str, review_id: str, decision_fingerprint: str
    ) -> None:
        """Bind one invocation/session and review ID to exactly one decision.

        Audit authentication and its matching review intentionally call this twice
        with the same tuple.  Reusing either identifier for another decision is not
        idempotent and must fail before shared prompt/input references can be claimed.
        """
        binding = (review_id, decision_fingerprint)
        prior = self._owner_reviews.get(owner)
        if prior is not None and prior != binding:
            raise ReviewAuthenticationError(
                f"review invocation/session reused across decisions: {owner}"
            )
        reverse_binding = (owner, decision_fingerprint)
        prior_owner = self._review_owners.get(review_id)
        if prior_owner is not None and prior_owner != reverse_binding:
            raise ReviewAuthenticationError(
                f"review ID reused across decisions or owners: {review_id}"
            )
        self._owner_reviews[owner] = binding
        self._review_owners[review_id] = reverse_binding

    def claim_identifier(self, kind: str, value: str, owner: str) -> None:
        key = (kind, value)
        prior = self._identifiers.get(key)
        if prior is not None and prior != owner:
            raise ReviewAuthenticationError(f"{kind} reused across reviews: {value}")
        self._identifiers[key] = owner

    def claim_reference(
        self, reference: dict, *, owner: str, role: str, label: str
    ) -> None:
        normalized = _normalize_reference(reference, label=label)
        path = normalized["path"]
        digest = normalized["sha256"]
        prior_path = self._paths.get(path)
        if prior_path is not None and prior_path != (owner, role):
            raise ReviewAuthenticationError(f"{label} path reused across reviews: {path}")
        prior_digest = self._digests.get(digest)
        if prior_digest is not None and prior_digest != (owner, role):
            raise ReviewAuthenticationError(
                f"{label} bytes reused across reviews: {digest}"
            )
        self._paths[path] = (owner, role)
        self._digests[digest] = (owner, role)

    def claim_bytes(self, raw: bytes, *, owner: str, role: str, label: str) -> None:
        digest = hashlib.sha256(raw).hexdigest()
        prior = self._digests.get(digest)
        if prior is not None and prior != (owner, role):
            raise ReviewAuthenticationError(
                f"{label} bytes reused across reviews: {digest}"
            )
        self._digests[digest] = (owner, role)


def _registered_identity(
    registry: dict,
    authentication: dict,
    *,
    schema_root: Path,
    role: str,
    method: str,
    allow_test_registry: bool,
) -> dict:
    identities = validate_reviewer_registry(
        registry,
        schema_path=schema_root / "trusted-reviewers.schema.json",
        allow_test_registry=allow_test_registry,
        require_configured=True,
    )
    if authentication.get("registry_id") != registry["registry_id"]:
        raise ReviewAuthenticationError("signed artifact reviewer registry ID mismatch")
    if authentication.get("signature_context") != registry["signature_context"]:
        raise ReviewAuthenticationError("signed artifact signature context mismatch")
    principal_id = authentication.get("principal_id")
    identity = identities.get(principal_id)
    if identity is None:
        raise ReviewAuthenticationError(f"unregistered review principal: {principal_id}")
    if authentication.get("key_id") != identity["key_id"]:
        raise ReviewAuthenticationError(f"registered reviewer key mismatch: {principal_id}")
    if role not in identity["roles"]:
        raise ReviewAuthenticationError(
            f"registered principal lacks {role} role: {principal_id}"
        )
    if method not in identity["methods"]:
        raise ReviewAuthenticationError(
            f"registered principal cannot use {method}: {principal_id}"
        )
    signed_at = _parse_time(
        authentication.get("signed_at_utc", ""),
        label=f"{principal_id} signed_at_utc",
    )
    valid_from = _parse_time(
        identity["valid_from_utc"], label=f"{principal_id} valid_from_utc"
    )
    if signed_at < valid_from:
        raise ReviewAuthenticationError(f"review signature predates key validity: {principal_id}")
    if identity["valid_until_utc"] is not None:
        valid_until = _parse_time(
            identity["valid_until_utc"], label=f"{principal_id} valid_until_utc"
        )
        if signed_at >= valid_until:
            raise ReviewAuthenticationError(f"review signature is outside key validity: {principal_id}")
    return identity


def _verify_signature(
    raw_artifact: bytes,
    *,
    artifact_kind: str,
    authentication: dict,
    identity: dict,
    signature_bytes: bytes,
    signature_reference: dict,
) -> tuple[str, str]:
    normalized_reference = _normalize_reference(
        signature_reference, label=f"{artifact_kind} detached signature"
    )
    if authentication.get("signature") != normalized_reference:
        raise ReviewAuthenticationError(
            f"{artifact_kind} detached signature reference mismatch"
        )
    actual_signature_sha = hashlib.sha256(signature_bytes).hexdigest()
    if actual_signature_sha != normalized_reference["sha256"]:
        raise ReviewAuthenticationError(
            f"{artifact_kind} detached signature SHA-256 mismatch"
        )
    if len(signature_bytes) != 64:
        raise ReviewAuthenticationError(
            f"{artifact_kind} Ed25519 signature must be exactly 64 bytes"
        )
    statement = signature_statement_bytes(raw_artifact, artifact_kind=artifact_kind)
    statement_sha = hashlib.sha256(statement).hexdigest()
    if authentication.get("statement_sha256") != statement_sha:
        raise ReviewAuthenticationError(f"{artifact_kind} signed statement hash mismatch")
    public_key = Ed25519PublicKey.from_public_bytes(
        _decode_public_key(identity["public_key_base64"])
    )
    try:
        public_key.verify(signature_bytes, statement)
    except InvalidSignature as error:
        raise ReviewAuthenticationError(
            f"{artifact_kind} Ed25519 signature verification failed"
        ) from error
    return statement_sha, actual_signature_sha


def authenticate_prompt_audit(
    raw_audit: bytes,
    *,
    registry: dict,
    schema_root: Path,
    signature_bytes: bytes,
    signature_reference: dict,
    read_artifact: ArtifactReader,
    preferred_labels: Sequence[str],
    aliases: Sequence[str],
    answer_names: Sequence[str],
    identifiers: Sequence[str],
    locators: Sequence[str],
    invocation_started_at_utc: str,
    usage: ArtifactUsageTracker,
    allow_test_registry: bool = False,
    _expected_method: str = AUDIT_METHOD,
) -> dict:
    """Authenticate and recompute a signed pre-invocation request audit.

    Normal callers authenticate the deterministic artifact.  The private
    ``_expected_method`` hook is used only by ``authenticate_semantic_prompt_audit``
    so the two required artifacts cannot be confused.
    """
    if not isinstance(usage, ArtifactUsageTracker):
        raise ReviewAuthenticationError("a global artifact usage tracker is required")
    audit = strict_json_object(raw_audit, label="prompt leakage audit")
    _require_canonical_artifact_bytes(
        raw_audit, audit, label="prompt leakage audit"
    )
    validate_schema(
        audit,
        schema_root / "prompt-leakage-audit.schema.json",
        "prompt leakage audit",
    )
    if audit["schema_version"] != AUDIT_SCHEMA_VERSION:
        raise ReviewAuthenticationError("unsupported prompt leakage audit version")
    if _expected_method not in {AUDIT_METHOD, SEMANTIC_AUDIT_METHOD}:
        raise ReviewAuthenticationError("unsupported expected prompt audit method")
    if audit["audit_method"] != _expected_method:
        raise ReviewAuthenticationError(
            f"prompt audit method is not the required {_expected_method}"
        )
    authentication = audit["authentication"]
    identity = _registered_identity(
        registry,
        authentication,
        schema_root=schema_root,
        role="prompt_auditor",
        method=_expected_method,
        allow_test_registry=allow_test_registry,
    )
    if _expected_method == SEMANTIC_AUDIT_METHOD and identity.get("identity_kind") != "HUMAN":
        raise ReviewAuthenticationError(
            "semantic prompt auditor must be a registered human identity"
        )
    if audit["auditor"] != {
        "auditor_id": identity["principal_id"],
        "independence_group": identity["independence_group"],
    }:
        raise ReviewAuthenticationError(
            "prompt audit auditor identity/group is not the registered principal"
        )
    statement_sha, signature_sha = _verify_signature(
        raw_audit,
        artifact_kind="prompt_leakage_audit",
        authentication=authentication,
        identity=identity,
        signature_bytes=signature_bytes,
        signature_reference=signature_reference,
    )
    executed_at = _parse_time(audit["executed_at_utc"], label="audit executed_at_utc")
    signed_at = _parse_time(authentication["signed_at_utc"], label="audit signed_at_utc")
    invoked_at = _parse_time(
        invocation_started_at_utc, label="review invocation started_at_utc"
    )
    if signed_at < executed_at:
        raise ReviewAuthenticationError("prompt audit was signed before it was executed")
    if signed_at >= invoked_at:
        raise ReviewAuthenticationError(
            "prompt audit signature is not pre-invocation"
        )
    prompt_raw = _read_bound_artifact(
        audit["prompt"], read_artifact=read_artifact, label="audited prompt"
    )
    input_raw = _read_bound_artifact(
        audit["input"], read_artifact=read_artifact, label="audited input"
    )
    recomputed_guard = deterministic_guard_record(
        prompt_raw,
        input_raw,
        shuffle_provenance=audit["shuffle_provenance"],
        review_invocation_id=audit["review_invocation_id"],
        decision_key=audit["decision_key"],
        decision_kind=audit["decision_kind"],
        subject=audit["subject"],
        preferred_labels=preferred_labels,
        aliases=aliases,
        answer_names=answer_names,
        identifiers=identifiers,
        locators=locators,
    )
    if audit["deterministic_guard"] != recomputed_guard:
        raise ReviewAuthenticationError(
            "signed prompt audit deterministic guard/input bindings do not recompute"
        )
    semantic_assessment = audit["semantic_assessment"]
    if _expected_method == AUDIT_METHOD:
        if semantic_assessment is not None:
            raise ReviewAuthenticationError(
                "deterministic prompt audit cannot carry a semantic assessment"
            )
    else:
        if not isinstance(semantic_assessment, dict):
            raise ReviewAuthenticationError(
                "semantic prompt audit lacks its signed semantic assessment"
            )
        prompt_sha = hashlib.sha256(prompt_raw).hexdigest()
        input_sha = hashlib.sha256(input_raw).hexdigest()
        expected_request_binding = canonical_sha256(
            {"prompt_sha256": prompt_sha, "input_sha256": input_sha}
        )
        if semantic_assessment["prompt_sha256"] != prompt_sha:
            raise ReviewAuthenticationError(
                "semantic prompt audit prompt-byte binding mismatch"
            )
        if semantic_assessment["input_sha256"] != input_sha:
            raise ReviewAuthenticationError(
                "semantic prompt audit input-byte binding mismatch"
            )
        if semantic_assessment["request_binding_sha256"] != expected_request_binding:
            raise ReviewAuthenticationError(
                "semantic prompt audit request binding mismatch"
            )
        _string(
            semantic_assessment["reasoning"],
            label="semantic prompt audit reasoning",
        )
    owner = audit["review_invocation_id"]
    decision_fingerprint = canonical_sha256(
        {
            "decision_key": audit["decision_key"],
            "decision_kind": audit["decision_kind"],
            "subject": audit["subject"],
        }
    )
    usage.bind_owner(owner, audit["review_id"], decision_fingerprint)
    usage.claim_identifier("audit_id", audit["audit_id"], owner)
    usage.claim_identifier("review_id", audit["review_id"], owner)
    usage.claim_identifier("review_invocation_id", owner, owner)
    usage.claim_bytes(
        raw_audit,
        owner=owner,
        role=(
            "prompt_leakage_audit"
            if _expected_method == AUDIT_METHOD
            else "semantic_prompt_audit"
        ),
        label=f"{_expected_method} prompt audit",
    )
    usage.claim_reference(
        signature_reference,
        owner=owner,
        role=f"prompt_audit_signature:{_expected_method}",
        label="prompt audit signature",
    )
    usage.claim_reference(
        audit["prompt"], owner=owner, role="prompt", label="review prompt"
    )
    usage.claim_reference(
        audit["input"], owner=owner, role="input", label="review input"
    )
    return {
        "registry_id": registry["registry_id"],
        "auditor_id": identity["principal_id"],
        "independence_group": identity["independence_group"],
        "method": _expected_method,
        "key_id": identity["key_id"],
        "audit_id": audit["audit_id"],
        "review_id": audit["review_id"],
        "review_invocation_id": owner,
        "decision_key": audit["decision_key"],
        "decision_kind": audit["decision_kind"],
        "subject": audit["subject"],
        "prompt": audit["prompt"],
        "input": audit["input"],
        "request_envelope": recomputed_guard["request_envelope"],
        "artifact_sha256": hashlib.sha256(raw_audit).hexdigest(),
        "statement_sha256": statement_sha,
        "signature_sha256": signature_sha,
        "signed_at_utc": authentication["signed_at_utc"],
        "invocation_started_at_utc": invocation_started_at_utc,
    }


def authenticate_semantic_prompt_audit(
    raw_audit: bytes,
    *,
    registry: dict,
    schema_root: Path,
    signature_bytes: bytes,
    signature_reference: dict,
    read_artifact: ArtifactReader,
    preferred_labels: Sequence[str],
    aliases: Sequence[str],
    answer_names: Sequence[str],
    identifiers: Sequence[str],
    locators: Sequence[str],
    invocation_started_at_utc: str,
    usage: ArtifactUsageTracker,
    allow_test_registry: bool = False,
) -> dict:
    """Authenticate the separate signed human semantic request audit."""
    return authenticate_prompt_audit(
        raw_audit,
        registry=registry,
        schema_root=schema_root,
        signature_bytes=signature_bytes,
        signature_reference=signature_reference,
        read_artifact=read_artifact,
        preferred_labels=preferred_labels,
        aliases=aliases,
        answer_names=answer_names,
        identifiers=identifiers,
        locators=locators,
        invocation_started_at_utc=invocation_started_at_utc,
        usage=usage,
        allow_test_registry=allow_test_registry,
        _expected_method=SEMANTIC_AUDIT_METHOD,
    )


def llm_interaction_binding_sha256(review: dict) -> str:
    """Bind one review to the exact LLM request, response, model, and parameters."""
    interaction = review["llm_interaction"]
    return canonical_sha256(
        {
            "review_id": review["review_id"],
            "review_invocation_id": interaction["review_invocation_id"],
            "invoked_at_utc": interaction["invoked_at_utc"],
            "completed_at_utc": interaction["completed_at_utc"],
            "decision_key": review["decision_key"],
            "decision_kind": review["decision_kind"],
            "subject": review["subject"],
            "model": interaction["model"],
            "parameters": interaction["parameters"],
            "prompt": interaction["prompt"],
            "input": interaction["input"],
            "raw_response": interaction["raw_response"],
            "parsed_response_sha256": interaction["parsed_response_sha256"],
            "prompt_leakage_audit": interaction["prompt_leakage_audit"],
            "semantic_prompt_audit": interaction["semantic_prompt_audit"],
        }
    )


def authenticate_review_artifact(
    raw_review: bytes,
    *,
    registry: dict,
    schema_root: Path,
    signature_bytes: bytes,
    signature_reference: dict,
    read_artifact: ArtifactReader,
    usage: ArtifactUsageTracker,
    authenticated_prompt_audit: dict | None = None,
    authenticated_semantic_prompt_audit: dict | None = None,
    allow_test_registry: bool = False,
) -> dict:
    """Authenticate one human or LLM review and all exact byte dependencies."""
    if not isinstance(usage, ArtifactUsageTracker):
        raise ReviewAuthenticationError("a global artifact usage tracker is required")
    review = strict_json_object(raw_review, label="review artifact")
    _require_canonical_artifact_bytes(raw_review, review, label="review artifact")
    validate_schema(
        review, schema_root / "review-artifact.schema.json", "review artifact"
    )
    if review["schema_version"] != REVIEW_SCHEMA_VERSION:
        raise ReviewAuthenticationError("unsupported review artifact version")
    authentication = review["authentication"]
    identity = _registered_identity(
        registry,
        authentication,
        schema_root=schema_root,
        role="reviewer",
        method=review["method"],
        allow_test_registry=allow_test_registry,
    )
    if review["reviewer"] != {
        "reviewer_id": identity["principal_id"],
        "independence_group": identity["independence_group"],
    }:
        raise ReviewAuthenticationError(
            "reviewer identity/group is not the registered principal"
        )
    statement_sha, signature_sha = _verify_signature(
        raw_review,
        artifact_kind="review_artifact",
        authentication=authentication,
        identity=identity,
        signature_bytes=signature_bytes,
        signature_reference=signature_reference,
    )
    source_ids: set[str] = set()
    for index, citation in enumerate(review["citations"]):
        source_id = citation["source_id"]
        if source_id in source_ids:
            raise ReviewAuthenticationError(
                f"duplicate citation source_id in review: {source_id}"
            )
        source_ids.add(source_id)
        _read_bound_artifact(
            citation["source_artifact"],
            read_artifact=read_artifact,
            label=f"citation source {index}",
        )
    signed_at = _parse_time(authentication["signed_at_utc"], label="review signed_at_utc")
    parsed_response_sha: str | None = None
    if review["method"] == "human":
        if (
            authenticated_prompt_audit is not None
            or authenticated_semantic_prompt_audit is not None
        ):
            raise ReviewAuthenticationError("human review cannot carry a prompt audit")
        provenance = review["human_provenance"]
        started_at = _parse_time(
            provenance["started_at_utc"], label="human review started_at_utc"
        )
        completed_at = _parse_time(
            provenance["completed_at_utc"], label="human review completed_at_utc"
        )
        if completed_at < started_at:
            raise ReviewAuthenticationError("human review completed before it started")
        if signed_at < completed_at:
            raise ReviewAuthenticationError("human review was signed before completion")
        reasoning_sha = hashlib.sha256(review["reasoning"].encode("utf-8")).hexdigest()
        if provenance["reasoning_utf8_sha256"] != reasoning_sha:
            raise ReviewAuthenticationError("human review reasoning byte hash mismatch")
        owner = f"human:{provenance['review_session_id']}"
        invocation_id = None
    else:
        interaction = review["llm_interaction"]
        if not isinstance(authenticated_prompt_audit, dict):
            raise ReviewAuthenticationError(
                "LLM review requires an authenticated deterministic pre-invocation prompt audit"
            )
        if not isinstance(authenticated_semantic_prompt_audit, dict):
            raise ReviewAuthenticationError(
                "LLM review requires a separate authenticated semantic pre-invocation prompt audit"
            )
        invoked_at = _parse_time(
            interaction["invoked_at_utc"], label="LLM invoked_at_utc"
        )
        completed_at = _parse_time(
            interaction["completed_at_utc"], label="LLM completed_at_utc"
        )
        if completed_at < invoked_at:
            raise ReviewAuthenticationError("LLM review completed before invocation")
        if signed_at < completed_at:
            raise ReviewAuthenticationError("LLM review was signed before completion")
        if (
            interaction["interaction_binding_sha256"]
            != llm_interaction_binding_sha256(review)
        ):
            raise ReviewAuthenticationError("LLM interaction binding hash mismatch")
        prompt_raw = _read_bound_artifact(
            interaction["prompt"], read_artifact=read_artifact, label="LLM prompt"
        )
        input_raw = _read_bound_artifact(
            interaction["input"], read_artifact=read_artifact, label="LLM input"
        )
        raw_response = _read_bound_artifact(
            interaction["raw_response"],
            read_artifact=read_artifact,
            label="LLM full raw response",
        )
        parsed_response = parse_llm_raw_response(raw_response)
        parsed_response_sha = canonical_sha256(parsed_response)
        if interaction["parsed_response_sha256"] != parsed_response_sha:
            raise ReviewAuthenticationError("LLM parsed response binding hash mismatch")
        if review["outcome"] != parsed_response["assessment"]:
            raise ReviewAuthenticationError(
                "LLM review wrapper outcome differs from the parsed raw response"
            )
        if review["reasoning"] != parsed_response["reasoning"]:
            raise ReviewAuthenticationError(
                "LLM review wrapper reasoning differs from the parsed raw response"
            )
        audit_raw = _read_bound_artifact(
            interaction["prompt_leakage_audit"],
            read_artifact=read_artifact,
            label="deterministic prompt leakage audit",
        )
        semantic_audit_raw = _read_bound_artifact(
            interaction["semantic_prompt_audit"],
            read_artifact=read_artifact,
            label="semantic prompt audit",
        )
        expected_audit = {
            "registry_id": registry["registry_id"],
            "review_id": review["review_id"],
            "review_invocation_id": interaction["review_invocation_id"],
            "invocation_started_at_utc": interaction["invoked_at_utc"],
            "decision_key": review["decision_key"],
            "decision_kind": review["decision_kind"],
            "subject": review["subject"],
            "prompt": interaction["prompt"],
            "input": interaction["input"],
            "artifact_sha256": hashlib.sha256(audit_raw).hexdigest(),
        }
        for key, expected in expected_audit.items():
            if authenticated_prompt_audit.get(key) != expected:
                raise ReviewAuthenticationError(
                    f"authenticated deterministic prompt audit {key} does not bind the exact review"
                )
        expected_semantic_audit = {
            **expected_audit,
            "artifact_sha256": hashlib.sha256(semantic_audit_raw).hexdigest(),
        }
        for key, expected in expected_semantic_audit.items():
            if authenticated_semantic_prompt_audit.get(key) != expected:
                raise ReviewAuthenticationError(
                    f"authenticated semantic prompt audit {key} does not bind the exact review"
                )
        if authenticated_prompt_audit.get("method") != AUDIT_METHOD:
            raise ReviewAuthenticationError(
                "deterministic prompt audit method does not bind the exact review"
            )
        if authenticated_semantic_prompt_audit.get("method") != SEMANTIC_AUDIT_METHOD:
            raise ReviewAuthenticationError(
                "semantic prompt audit method does not bind the exact review"
            )
        if (
            authenticated_prompt_audit["auditor_id"] == identity["principal_id"]
            or authenticated_prompt_audit["independence_group"]
            == identity["independence_group"]
        ):
            raise ReviewAuthenticationError(
                "prompt auditor must be independent of the LLM reviewer identity/group"
            )
        if (
            authenticated_semantic_prompt_audit["auditor_id"]
            == identity["principal_id"]
            or authenticated_semantic_prompt_audit["independence_group"]
            == identity["independence_group"]
        ):
            raise ReviewAuthenticationError(
                "semantic prompt auditor must be independent of the LLM reviewer identity/group"
            )
        if (
            authenticated_semantic_prompt_audit["auditor_id"]
            == authenticated_prompt_audit["auditor_id"]
            or authenticated_semantic_prompt_audit["independence_group"]
            == authenticated_prompt_audit["independence_group"]
        ):
            raise ReviewAuthenticationError(
                "semantic and deterministic prompt auditors must be distinct identities/groups"
            )
        if hashlib.sha256(prompt_raw).hexdigest() != interaction["prompt"]["sha256"]:
            raise ReviewAuthenticationError("LLM prompt exact-byte binding mismatch")
        if hashlib.sha256(input_raw).hexdigest() != interaction["input"]["sha256"]:
            raise ReviewAuthenticationError("LLM input exact-byte binding mismatch")
        owner = interaction["review_invocation_id"]
        invocation_id = owner
    decision_fingerprint = canonical_sha256(
        {
            "decision_key": review["decision_key"],
            "decision_kind": review["decision_kind"],
            "subject": review["subject"],
        }
    )
    usage.bind_owner(owner, review["review_id"], decision_fingerprint)
    usage.claim_identifier("review_id", review["review_id"], owner)
    if invocation_id is not None:
        usage.claim_identifier("review_invocation_id", invocation_id, owner)
    else:
        usage.claim_identifier(
            "human_review_session_id", review["human_provenance"]["review_session_id"], owner
        )
    usage.claim_bytes(
        raw_review, owner=owner, role="review_artifact", label="review artifact"
    )
    usage.claim_reference(
        signature_reference,
        owner=owner,
        role="review_signature",
        label="review signature",
    )
    if review["method"] == "llm":
        interaction = review["llm_interaction"]
        usage.claim_reference(
            interaction["prompt"], owner=owner, role="prompt", label="LLM prompt"
        )
        usage.claim_reference(
            interaction["input"], owner=owner, role="input", label="LLM input"
        )
        usage.claim_reference(
            interaction["raw_response"],
            owner=owner,
            role="raw_response",
            label="LLM raw response",
        )
        usage.claim_reference(
            interaction["prompt_leakage_audit"],
            owner=owner,
            role="prompt_leakage_audit",
            label="prompt leakage audit",
        )
        usage.claim_reference(
            interaction["semantic_prompt_audit"],
            owner=owner,
            role="semantic_prompt_audit",
            label="semantic prompt audit",
        )
    return {
        "registry_id": registry["registry_id"],
        "reviewer_id": identity["principal_id"],
        "independence_group": identity["independence_group"],
        "method": review["method"],
        "key_id": identity["key_id"],
        "review_id": review["review_id"],
        "review_invocation_id": invocation_id,
        "decision_key": review["decision_key"],
        "decision_kind": review["decision_kind"],
        "subject": review["subject"],
        "outcome": review["outcome"],
        "parsed_response_sha256": parsed_response_sha,
        "artifact_sha256": hashlib.sha256(raw_review).hexdigest(),
        "statement_sha256": statement_sha,
        "signature_sha256": signature_sha,
        "signed_at_utc": authentication["signed_at_utc"],
    }


def require_distinct_registered_reviewers(
    reviews: Sequence[dict], *, required_count: int = 2
) -> None:
    """Require an exact census of distinct authenticated identities and groups."""
    if len(reviews) != required_count:
        raise ReviewAuthenticationError(
            f"credited decision requires exactly {required_count} authenticated reviews"
        )
    fields = (
        "reviewer_id",
        "independence_group",
        "key_id",
        "review_id",
        "artifact_sha256",
        "statement_sha256",
        "signature_sha256",
    )
    for field_name in fields:
        values = [review.get(field_name) for review in reviews]
        if any(not isinstance(value, str) or not value for value in values):
            raise ReviewAuthenticationError(
                f"authenticated review lacks {field_name}"
            )
        if len(set(values)) != required_count:
            raise ReviewAuthenticationError(
                f"credited reviews lack distinct {field_name} values"
            )
    registry_ids = {review.get("registry_id") for review in reviews}
    decisions = {
        canonical_sha256(
            {
                "decision_key": review.get("decision_key"),
                "decision_kind": review.get("decision_kind"),
                "subject": review.get("subject"),
            }
        )
        for review in reviews
    }
    if len(registry_ids) != 1:
        raise ReviewAuthenticationError("credited reviews do not share one trusted registry")
    if len(decisions) != 1:
        raise ReviewAuthenticationError("credited reviews do not bind one exact decision")
