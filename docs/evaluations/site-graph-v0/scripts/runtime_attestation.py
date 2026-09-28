"""Exact, deterministic runtime provenance for site-graph-v0 baselines."""

from __future__ import annotations

import hashlib
import platform
import sys
from pathlib import Path

from schema_validation import validate_schema


RUNTIME_SCHEMA_VERSION = "site-graph-v0-baseline-runtime-attestation/1"
RUNTIME_SCHEMA_NAME = "baseline-runtime-attestation.schema.json"
UV_LOCK_RELATIVE = "pipeline/uv.lock"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _runtime_expectation(snapshot: dict) -> dict:
    try:
        expectation = snapshot["extractor_and_matcher"]["python_baseline_runtime"]
    except (KeyError, TypeError) as error:
        raise RuntimeError(
            "input snapshot lacks the exact baseline runtime expectation"
        ) from error
    required = {"implementation", "implementation_name", "version", "dependency_lock"}
    if not isinstance(expectation, dict) or set(expectation) != required:
        raise RuntimeError("input snapshot baseline runtime fields are not exact")
    lock = expectation["dependency_lock"]
    if (
        not isinstance(lock, dict)
        or set(lock) != {"path", "bytes", "sha256"}
        or lock["path"] != UV_LOCK_RELATIVE
        or not isinstance(lock["bytes"], int)
        or lock["bytes"] <= 0
        or not isinstance(lock["sha256"], str)
        or len(lock["sha256"]) != 64
    ):
        raise RuntimeError("input snapshot dependency-lock binding is invalid")
    return expectation


def build_runtime_attestation(repo_root: Path, snapshot: dict) -> dict:
    """Build an attestation only when the executing runtime matches the snapshot.

    This function intentionally reads the active interpreter rather than accepting
    caller-supplied runtime strings.  It also rehashes the release-pinned uv lock.
    """
    repo_root = repo_root.resolve()
    expectation = _runtime_expectation(snapshot)
    actual_python = {
        "implementation": platform.python_implementation(),
        "implementation_name": sys.implementation.name,
        "version": platform.python_version(),
    }
    expected_python = {
        key: expectation[key]
        for key in ("implementation", "implementation_name", "version")
    }
    if actual_python != expected_python:
        raise RuntimeError(
            f"baseline Python runtime mismatch: expected {expected_python}, got {actual_python}"
        )

    lock_path = repo_root / UV_LOCK_RELATIVE
    if not lock_path.is_file():
        raise RuntimeError(f"baseline dependency lock is missing: {lock_path}")
    actual_lock = {
        "path": UV_LOCK_RELATIVE,
        "bytes": lock_path.stat().st_size,
        "sha256": _sha256(lock_path),
    }
    if actual_lock != expectation["dependency_lock"]:
        raise RuntimeError(
            "baseline dependency-lock mismatch: "
            f"expected {expectation['dependency_lock']}, got {actual_lock}"
        )

    attestation = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "python": actual_python,
        "dependency_lock": actual_lock,
        "verification": {
            "input_snapshot_runtime_binding": "PASS",
            "executing_interpreter_match": "PASS",
            "dependency_lock_match": "PASS",
        },
    }
    schema_path = (
        repo_root
        / "docs/evaluations/site-graph-v0/schemas"
        / RUNTIME_SCHEMA_NAME
    )
    validate_schema(attestation, schema_path, "baseline runtime attestation")
    return attestation


def validate_runtime_attestation(
    repo_root: Path,
    snapshot: dict,
    attestation: dict,
) -> dict:
    """Recompute and require the one truthful attestation for this checkout."""
    expected = build_runtime_attestation(repo_root, snapshot)
    if attestation != expected:
        raise RuntimeError("recorded baseline runtime attestation mismatch")
    return expected
