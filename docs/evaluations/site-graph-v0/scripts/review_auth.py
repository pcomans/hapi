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
REVIEW_SCHEMA_VERSION = "site-graph-v0-review-artifact/3"
AUDIT_SCHEMA_VERSION = "site-graph-v0-prompt-leakage-audit/3"
SIGNATURE_CONTEXT = "hapi-site-graph-v0-review-evidence/1"
GUARD_VERSION = "site-graph-v0-deterministic-prompt-leakage-guard/1"
AUDIT_METHOD = "deterministic_prompt_leakage_guard/1"

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
        allowed_methods = {"human", "llm", AUDIT_METHOD}
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
        if "prompt_auditor" not in roles and AUDIT_METHOD in methods:
            raise ReviewAuthenticationError(
                f"non-auditor principal has the audit method: {principal_id}"
            )
        if "reviewer" in roles and not set(methods) & {"human", "llm"}:
            raise ReviewAuthenticationError(
                f"reviewer principal lacks a review method: {principal_id}"
            )
        if "prompt_auditor" in roles and AUDIT_METHOD not in methods:
            raise ReviewAuthenticationError(
                f"prompt auditor lacks deterministic audit method: {principal_id}"
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


def _forbidden_set_binding(values: Sequence[str], *, label: str) -> dict:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ReviewAuthenticationError(f"{label} must be a sequence of strings")
    exact = list(values)
    if not exact:
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


def deterministic_leakage_findings(
    prompt_bytes: bytes,
    input_bytes: bytes,
    *,
    candidate_ids: Sequence[str],
    source_ids: Sequence[str],
    answer_strings: Sequence[str],
) -> list[dict]:
    """Find answer/identifier leakage anywhere in the exact LLM request bytes.

    NFKC + case-folded matching catches superficial casing/Unicode changes.  A second
    alphanumeric-compacted match catches separator substitutions in identifiers.  The
    whole request is scanned, so putting an answer in an example or instruction does
    not exempt it.
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
        ("answer_string", answer_strings),
        ("candidate_id", candidate_ids),
        ("source_id", source_ids),
    )
    for category, values in categories:
        _forbidden_set_binding(values, label=f"{category} values")
    findings: list[dict] = []
    for location, text in decoded:
        normalized_haystack = _normalized_text(text)
        compact_haystack = _compact_text(text)
        for category, values in categories:
            for value in sorted(values):
                normalized_needle = _normalized_text(value)
                compact_needle = _compact_text(value)
                match_kind = None
                if normalized_needle in normalized_haystack:
                    match_kind = "normalized_literal"
                elif len(compact_needle) >= 4 and compact_needle in compact_haystack:
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
    candidate_ids: Sequence[str],
    source_ids: Sequence[str],
    answer_strings: Sequence[str],
) -> dict:
    """Return the only acceptable deterministic guard record, or reject leakage."""
    findings = deterministic_leakage_findings(
        prompt_bytes,
        input_bytes,
        candidate_ids=candidate_ids,
        source_ids=source_ids,
        answer_strings=answer_strings,
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
        "candidate_ids": _forbidden_set_binding(
            candidate_ids, label="candidate_ids"
        ),
        "source_ids": _forbidden_set_binding(source_ids, label="source_ids"),
        "answer_strings": _forbidden_set_binding(
            answer_strings, label="answer_strings"
        ),
        "result": "PASS",
        "findings": [],
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
    candidate_ids: Sequence[str],
    source_ids: Sequence[str],
    answer_strings: Sequence[str],
    invocation_started_at_utc: str,
    usage: ArtifactUsageTracker,
    allow_test_registry: bool = False,
) -> dict:
    """Authenticate and independently recompute a signed pre-invocation audit."""
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
    authentication = audit["authentication"]
    identity = _registered_identity(
        registry,
        authentication,
        schema_root=schema_root,
        role="prompt_auditor",
        method=AUDIT_METHOD,
        allow_test_registry=allow_test_registry,
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
        candidate_ids=candidate_ids,
        source_ids=source_ids,
        answer_strings=answer_strings,
    )
    if audit["deterministic_guard"] != recomputed_guard:
        raise ReviewAuthenticationError(
            "signed prompt audit deterministic guard/input bindings do not recompute"
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
        role="prompt_leakage_audit",
        label="prompt leakage audit",
    )
    usage.claim_reference(
        signature_reference,
        owner=owner,
        role="prompt_audit_signature",
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
        "method": AUDIT_METHOD,
        "key_id": identity["key_id"],
        "audit_id": audit["audit_id"],
        "review_id": audit["review_id"],
        "review_invocation_id": owner,
        "decision_key": audit["decision_key"],
        "decision_kind": audit["decision_kind"],
        "subject": audit["subject"],
        "prompt": audit["prompt"],
        "input": audit["input"],
        "artifact_sha256": hashlib.sha256(raw_audit).hexdigest(),
        "statement_sha256": statement_sha,
        "signature_sha256": signature_sha,
        "signed_at_utc": authentication["signed_at_utc"],
        "invocation_started_at_utc": invocation_started_at_utc,
    }


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
            "prompt_leakage_audit": interaction["prompt_leakage_audit"],
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
    if review["method"] == "human":
        if authenticated_prompt_audit is not None:
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
                "LLM review requires an authenticated pre-invocation prompt audit"
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
        _read_bound_artifact(
            interaction["raw_response"],
            read_artifact=read_artifact,
            label="LLM full raw response",
        )
        audit_raw = _read_bound_artifact(
            interaction["prompt_leakage_audit"],
            read_artifact=read_artifact,
            label="prompt leakage audit",
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
                    f"authenticated prompt audit {key} does not bind the exact review"
                )
        if (
            authenticated_prompt_audit["auditor_id"] == identity["principal_id"]
            or authenticated_prompt_audit["independence_group"]
            == identity["independence_group"]
        ):
            raise ReviewAuthenticationError(
                "prompt auditor must be independent of the LLM reviewer identity/group"
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
