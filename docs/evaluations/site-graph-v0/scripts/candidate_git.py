"""Read and authenticate candidate inputs from immutable Git commits."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath


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
