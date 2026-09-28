"""Read and authenticate candidate inputs from immutable Git commits."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class CandidateGitError(ValueError):
    pass


def _run(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=False, capture_output=True
    )
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise CandidateGitError(f"git {' '.join(args)} failed: {message}")
    return result.stdout


def normalize_relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or value != path.as_posix():
        raise CandidateGitError(f"candidate path must be normalized repository-relative: {value!r}")
    return value


def resolve_commit(repo: Path, value: str) -> str:
    resolved = _run(repo, "rev-parse", "--verify", f"{value}^{{commit}}").decode().strip()
    if value != resolved:
        raise CandidateGitError(f"commit must be the full resolved object ID: {value!r} != {resolved!r}")
    return resolved


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo,
        check=False,
        capture_output=True,
    )
    if result.returncode not in {0, 1}:
        raise CandidateGitError(result.stderr.decode("utf-8", errors="replace"))
    return result.returncode == 0


def read_bytes(repo: Path, commit: str, relative: str) -> bytes:
    relative = normalize_relative_path(relative)
    return _run(repo, "show", f"{commit}:{relative}")


def read_authenticated_bytes(
    repo: Path,
    commit: str,
    relative: str,
    *,
    expected_sha256: str,
    expected_blob_oid: str,
) -> tuple[bytes, dict]:
    """Read exact committed bytes and enforce both content-address bindings."""
    raw = read_bytes(repo, commit, relative)
    actual_sha = hashlib.sha256(raw).hexdigest()
    actual_blob = blob_oid(repo, commit, relative)
    if actual_sha != expected_sha256:
        raise CandidateGitError(
            f"candidate file SHA-256 mismatch for {relative}: "
            f"{actual_sha} != {expected_sha256}"
        )
    if actual_blob != expected_blob_oid:
        raise CandidateGitError(
            f"candidate file Git blob mismatch for {relative}: "
            f"{actual_blob} != {expected_blob_oid}"
        )
    return raw, {"path": relative, "sha256": actual_sha, "git_blob_oid": actual_blob}


def blob_oid(repo: Path, commit: str, relative: str) -> str:
    relative = normalize_relative_path(relative)
    return _run(repo, "rev-parse", f"{commit}:{relative}").decode().strip()


def read_authenticated_json(
    repo: Path,
    commit: str,
    relative: str,
    *,
    expected_sha256: str | None = None,
    expected_blob_oid: str | None = None,
) -> tuple[dict, dict]:
    raw = read_bytes(repo, commit, relative)
    actual_sha = hashlib.sha256(raw).hexdigest()
    actual_blob = blob_oid(repo, commit, relative)
    if expected_sha256 is not None and actual_sha != expected_sha256:
        raise CandidateGitError(
            f"candidate file SHA-256 mismatch for {relative}: {actual_sha} != {expected_sha256}"
        )
    if expected_blob_oid is not None and actual_blob != expected_blob_oid:
        raise CandidateGitError(
            f"candidate file Git blob mismatch for {relative}: {actual_blob} != {expected_blob_oid}"
        )
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CandidateGitError(f"candidate file is not JSON: {relative}: {error}") from error
    if not isinstance(value, dict):
        raise CandidateGitError(f"candidate JSON must be an object: {relative}")
    return value, {"path": relative, "sha256": actual_sha, "git_blob_oid": actual_blob}


def _decode_ed25519_public_key(public_key_base64: str) -> bytes:
    try:
        raw = base64.b64decode(public_key_base64, validate=True)
    except (ValueError, UnicodeEncodeError) as error:
        raise CandidateGitError("trusted run attestor public key is not base64") from error
    if len(raw) != 32:
        raise CandidateGitError("trusted run attestor Ed25519 public key must be 32 bytes")
    return raw


def ed25519_key_id(public_key_base64: str) -> str:
    """Return the contract key id for one raw-base64 Ed25519 public key."""
    return hashlib.sha256(_decode_ed25519_public_key(public_key_base64)).hexdigest()


def verify_ed25519_signature(
    message: bytes,
    signature: bytes,
    *,
    public_key_base64: str,
) -> None:
    """Verify a raw detached Ed25519 signature.

    This is a pure cryptographic primitive. Trust is established separately by the
    release-pinned attestor policy; callers must never accept a candidate-supplied key.
    """
    if not message:
        raise CandidateGitError("run-start receipt bytes must be nonempty")
    if len(signature) != 64:
        raise CandidateGitError("run-start Ed25519 signature must be exactly 64 bytes")
    key = Ed25519PublicKey.from_public_bytes(
        _decode_ed25519_public_key(public_key_base64)
    )
    try:
        key.verify(signature, message)
    except InvalidSignature as error:
        raise CandidateGitError(
            "trusted run-start Ed25519 signature verification failed"
        ) from error
