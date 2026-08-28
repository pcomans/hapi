#!/usr/bin/env python3
"""Read-only integrity checks for the committed site-graph-v0 release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from release_contract import CONTRACT_VERSION, PYCACHE_EXCLUSION, REQUIRED_RELEASE_FILES


EVALUATION_RELATIVE = Path("docs/evaluations/site-graph-v0")
MANIFEST_NAME = "release-manifest.json"
IGNORED_PARTS = {"__pycache__", ".pytest_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


class IntegrityError(RuntimeError):
    """The checkout does not match the frozen release inventory."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tracked_file(path: Path) -> bool:
    return (
        path.is_file()
        and not any(part in IGNORED_PARTS for part in path.parts)
        and path.suffix not in IGNORED_SUFFIXES
    )


def discovered_release_files(repo_root: Path) -> set[str]:
    """Return the exact release surface; the self-describing manifest is excluded."""
    evaluation_root = repo_root / EVALUATION_RELATIVE
    files = {
        path.relative_to(repo_root).as_posix()
        for path in evaluation_root.rglob("*")
        if _tracked_file(path) and path.name != MANIFEST_NAME
    }
    for relative in (
        "pipeline/pyproject.toml",
        "pipeline/tests/test_site_graph_v0_contract.py",
        "pipeline/uv.lock",
    ):
        path = repo_root / relative
        if _tracked_file(path):
            files.add(relative)
    return files


def load_release_manifest(repo_root: Path) -> dict:
    path = repo_root / EVALUATION_RELATIVE / MANIFEST_NAME
    if not path.is_file():
        raise IntegrityError(f"missing immutable release manifest: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IntegrityError(f"cannot read release manifest: {error}") from error
    if value.get("schema_version") != "site-graph-v0-release-manifest/2":
        raise IntegrityError("unsupported release manifest schema_version")
    if value.get("contract_version") != CONTRACT_VERSION:
        raise IntegrityError("release manifest contract_version mismatch")
    if value.get("pycache_exclusion") != PYCACHE_EXCLUSION:
        raise IntegrityError("release manifest cache exclusion mismatch")
    if value.get("hash_algorithm") != "sha256":
        raise IntegrityError("release manifest must use sha256")
    files = value.get("files")
    if not isinstance(files, dict) or not files:
        raise IntegrityError("release manifest files must be a non-empty object")
    for relative, expected in files.items():
        if (
            not isinstance(relative, str)
            or relative.startswith("/")
            or ".." in Path(relative).parts
            or not isinstance(expected, dict)
            or set(expected) != {"bytes", "sha256"}
            or not isinstance(expected["bytes"], int)
            or expected["bytes"] < 0
            or not isinstance(expected["sha256"], str)
            or len(expected["sha256"]) != 64
        ):
            raise IntegrityError(f"invalid release manifest entry: {relative!r}")
    if set(files) != REQUIRED_RELEASE_FILES:
        raise IntegrityError(
            "release manifest inventory differs from static contract: "
            + json.dumps(
                {
                    "missing": sorted(REQUIRED_RELEASE_FILES - set(files)),
                    "extra": sorted(set(files) - REQUIRED_RELEASE_FILES),
                },
                sort_keys=True,
            )
        )
    return value


def verify_release(repo_root: Path) -> dict:
    """Verify exact inventory and every byte hash without changing any file."""
    repo_root = repo_root.resolve()
    manifest = load_release_manifest(repo_root)
    expected_names = set(REQUIRED_RELEASE_FILES)
    actual_names = discovered_release_files(repo_root)
    missing = sorted(expected_names - actual_names)
    extra = sorted(actual_names - expected_names)
    mismatches = {}
    for relative in sorted(expected_names & actual_names):
        path = repo_root / relative
        expected = manifest["files"][relative]
        actual = {"bytes": path.stat().st_size, "sha256": sha256(path)}
        if actual != expected:
            mismatches[relative] = {"expected": expected, "actual": actual}
    if missing or extra or mismatches:
        raise IntegrityError(
            json.dumps(
                {"missing": missing, "extra": extra, "mismatches": mismatches},
                sort_keys=True,
            )
        )
    return {
        "manifest_sha256": sha256(
            repo_root / EVALUATION_RELATIVE / MANIFEST_NAME
        ),
        "verified_file_count": len(expected_names),
    }
