"""Authenticate and safely materialize the authorized private corpus archive."""

from __future__ import annotations

import argparse
import contextlib
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Iterator


ARCHIVE_ENV = "HAPI_CORPUS_ARCHIVE"
SIDECAR_ENV = "HAPI_CORPUS_ARCHIVE_SHA256"


class CorpusArchiveError(RuntimeError):
    """Base class for authenticated private-input failures."""


class CorpusArchiveBlocked(CorpusArchiveError):
    """The authorized external prerequisite is not available."""


class CorpusArchiveInvalid(CorpusArchiveError):
    """Provided bytes fail the frozen acquisition contract."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative_member(name: str, expected_root: str) -> Path:
    value = PurePosixPath(name)
    if value.is_absolute() or ".." in value.parts or not value.parts:
        raise CorpusArchiveInvalid(f"unsafe corpus archive member path: {name!r}")
    if value.parts[0] not in {expected_root, f"._{expected_root}"}:
        raise CorpusArchiveInvalid(
            f"corpus archive member is outside expected root {expected_root!r}: {name!r}"
        )
    return Path(*value.parts)


def _is_appledouble(path: Path) -> bool:
    return any(part.startswith("._") for part in path.parts)


def _parse_checksums(path: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, separator, relative = line.partition("  ")
        normalized = relative.removeprefix("./")
        if (
            not separator
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or not normalized
            or normalized in output
        ):
            raise CorpusArchiveInvalid(f"invalid internal corpus checksum line: {line!r}")
        candidate = PurePosixPath(normalized)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise CorpusArchiveInvalid(f"unsafe internal corpus checksum path: {normalized!r}")
        output[normalized] = digest
    return output


def _canonical_counts(path: Path) -> tuple[int, dict[str, int]]:
    total = 0
    counts: dict[str, int] = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            museum = json.loads(line)["source_museum"]
            counts[museum] = counts.get(museum, 0) + 1
            total += 1
    return total, dict(sorted(counts.items()))


def validate_archive_attestation(corpus_snapshot: dict, attestation: dict) -> None:
    """Fail closed if a runtime attestation is not bound to the frozen snapshot."""
    acquisition = corpus_snapshot["archive_acquisition"]
    expected_archive = {
        "logical_locator": acquisition["archive_logical_locator"],
        "filename": acquisition["archive_filename"],
        "bytes": acquisition["archive_bytes"],
        "sha256": acquisition["archive_sha256"],
        "sidecar_logical_locator": acquisition["sidecar_logical_locator"],
        "sidecar_filename": acquisition["sidecar_filename"],
        "sidecar_sha256": acquisition["sidecar_sha256"],
        "sidecar_expected_line": acquisition["sidecar_expected_line"],
        "expected_archive_root": acquisition["expected_archive_root"],
    }
    if attestation.get("schema_version") != "site-graph-v0-corpus-archive-attestation/1":
        raise CorpusArchiveInvalid("unsupported corpus archive attestation schema")
    if attestation.get("archive") != expected_archive:
        raise CorpusArchiveInvalid("corpus archive attestation acquisition binding mismatch")
    extraction = attestation.get("extraction", {})
    required_extraction = {
        "internal_sha256sums_sha256": acquisition["internal_sha256sums_sha256"],
        "substantive_member_count": acquisition["substantive_member_count"],
        "archive_member_count": acquisition["archive_member_count"],
        "archive_member_inventory_sha256": acquisition[
            "archive_member_inventory_sha256"
        ],
        "canonical_record_count": corpus_snapshot["canonical_record_count"],
        "records_by_museum": corpus_snapshot["records_by_museum"],
        "bundled_verifier_stdout_sha256": acquisition[
            "bundled_verifier_stdout_sha256"
        ],
    }
    if any(extraction.get(key) != value for key, value in required_extraction.items()):
        raise CorpusArchiveInvalid("corpus archive attestation extraction binding mismatch")
    if attestation.get("production_lineage") != corpus_snapshot["production_lineage"]:
        raise CorpusArchiveInvalid("corpus archive attestation lineage binding mismatch")
    if attestation.get("status") != {
        "snapshot_acquisition_integrity": "PASS",
        "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
    }:
        raise CorpusArchiveInvalid("corpus archive attestation status mismatch")


def _extract_and_verify(
    archive: Path,
    destination: Path,
    corpus_snapshot: dict,
) -> tuple[Path, dict]:
    acquisition = corpus_snapshot["archive_acquisition"]
    expected_root = acquisition["expected_archive_root"]
    with tarfile.open(archive, mode="r:gz") as bundle:
        members = bundle.getmembers()
        inventory = [
            {
                "name": member.name,
                "type": (
                    "dir"
                    if member.isdir()
                    else "file"
                    if member.isfile()
                    else "symlink"
                    if member.issym()
                    else "hardlink"
                    if member.islnk()
                    else "other"
                ),
            }
            for member in members
        ]
        inventory_bytes = (
            json.dumps(inventory, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        if len(inventory) != acquisition["archive_member_count"]:
            raise CorpusArchiveInvalid("corpus archive member count mismatch")
        if hashlib.sha256(inventory_bytes).hexdigest() != acquisition[
            "archive_member_inventory_sha256"
        ]:
            raise CorpusArchiveInvalid("corpus archive member inventory mismatch")

        written: set[Path] = set()
        substantive_regular: set[str] = set()
        for member in members:
            relative = _safe_relative_member(member.name, expected_root)
            if member.isdir():
                continue
            if not member.isfile():
                raise CorpusArchiveInvalid(
                    f"corpus archive contains unsupported member type: {member.name!r}"
                )
            if _is_appledouble(relative):
                continue
            source = bundle.extractfile(member)
            if source is None:
                raise CorpusArchiveInvalid(f"cannot read corpus archive member: {member.name!r}")
            output = destination / relative
            if output in written or output.exists():
                raise CorpusArchiveInvalid(
                    f"corpus archive would overwrite an extracted member: {member.name!r}"
                )
            written.add(output)
            substantive_regular.add(relative.relative_to(expected_root).as_posix())
            output.parent.mkdir(parents=True, exist_ok=True)
            with source, output.open("wb") as handle:
                shutil.copyfileobj(source, handle)

    root = destination / expected_root
    checksum_path = root / "SHA256SUMS"
    if not checksum_path.is_file():
        raise CorpusArchiveInvalid("corpus archive lacks internal SHA256SUMS")
    if sha256(checksum_path) != acquisition["internal_sha256sums_sha256"]:
        raise CorpusArchiveInvalid("corpus archive internal SHA256SUMS hash mismatch")
    expected_members = _parse_checksums(checksum_path)
    if len(expected_members) != acquisition["substantive_member_count"]:
        raise CorpusArchiveInvalid("corpus archive substantive member count mismatch")
    expected_regular = set(expected_members) | {"SHA256SUMS"}
    if substantive_regular != expected_regular:
        raise CorpusArchiveInvalid(
            "corpus archive substantive inventory mismatch: "
            f"missing={sorted(expected_regular - substantive_regular)}, "
            f"extra={sorted(substantive_regular - expected_regular)}"
        )
    actual_member_hashes = {}
    for relative, expected_digest in sorted(expected_members.items()):
        member_path = root / relative
        if not member_path.is_file():
            raise CorpusArchiveInvalid(f"corpus archive substantive member missing: {relative}")
        actual_digest = sha256(member_path)
        if actual_digest != expected_digest:
            raise CorpusArchiveInvalid(f"corpus archive internal checksum mismatch: {relative}")
        actual_member_hashes[relative] = actual_digest

    for relative, expected_digest in acquisition["pinned_internal_files"].items():
        if actual_member_hashes.get(relative) != expected_digest:
            raise CorpusArchiveInvalid(f"corpus archive pinned internal file mismatch: {relative}")

    total, museums = _canonical_counts(root / "data/artifacts.ndjson.gz")
    if total != corpus_snapshot["canonical_record_count"]:
        raise CorpusArchiveInvalid("corpus archive canonical record count mismatch")
    if museums != corpus_snapshot["records_by_museum"]:
        raise CorpusArchiveInvalid("corpus archive canonical museum counts mismatch")

    verifier = subprocess.run(
        ["bash", "validation/verify_bundle.sh"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "LC_ALL": "C"},
    )
    if verifier.returncode:
        raise CorpusArchiveInvalid(
            "bundled corpus verifier failed\n"
            f"stdout:\n{verifier.stdout}\nstderr:\n{verifier.stderr}"
        )
    stdout_sha256 = hashlib.sha256(verifier.stdout.encode("utf-8")).hexdigest()
    if stdout_sha256 != acquisition["bundled_verifier_stdout_sha256"]:
        raise CorpusArchiveInvalid("bundled corpus verifier output mismatch")
    if verifier.stdout.rstrip("\n").splitlines()[-1] != acquisition[
        "bundled_verifier_required_final_line"
    ]:
        raise CorpusArchiveInvalid("bundled corpus verifier did not emit its required PASS line")

    return root, {
        "internal_sha256sums_sha256": sha256(checksum_path),
        "substantive_member_count": len(actual_member_hashes),
        "substantive_member_hashes": actual_member_hashes,
        "archive_member_count": len(inventory),
        "archive_member_inventory_sha256": hashlib.sha256(inventory_bytes).hexdigest(),
        "canonical_record_count": total,
        "records_by_museum": museums,
        "bundled_verifier_stdout_sha256": stdout_sha256,
    }


@contextlib.contextmanager
def authenticated_corpus(
    repo_root: Path,
    archive: Path,
    sidecar: Path,
) -> Iterator[tuple[Path, dict]]:
    """Yield a verified temporary extraction and deterministic attestation."""
    snapshot_path = repo_root / "docs/evaluations/site-graph-v0/input-snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    corpus_snapshot = snapshot["corpus"]
    acquisition = corpus_snapshot["archive_acquisition"]
    archive = archive.resolve()
    sidecar = sidecar.resolve()
    if not archive.is_file() or not sidecar.is_file():
        raise CorpusArchiveBlocked(
            "authorized corpus archive and checksum sidecar are both required"
        )
    actual_archive = {"bytes": archive.stat().st_size, "sha256": sha256(archive)}
    expected_archive = {
        "bytes": acquisition["archive_bytes"],
        "sha256": acquisition["archive_sha256"],
    }
    if actual_archive != expected_archive:
        raise CorpusArchiveInvalid(
            f"authorized corpus archive mismatch: expected {expected_archive}, got {actual_archive}"
        )
    sidecar_bytes = sidecar.read_bytes()
    if hashlib.sha256(sidecar_bytes).hexdigest() != acquisition["sidecar_sha256"]:
        raise CorpusArchiveInvalid("authorized corpus archive sidecar hash mismatch")
    if sidecar_bytes.decode("utf-8") != acquisition["sidecar_expected_line"]:
        raise CorpusArchiveInvalid("authorized corpus archive sidecar content mismatch")

    with tempfile.TemporaryDirectory(prefix="hapi-site-graph-v0-corpus-") as temporary:
        root, internal = _extract_and_verify(
            archive, Path(temporary), corpus_snapshot
        )
        attestation = {
            "schema_version": "site-graph-v0-corpus-archive-attestation/1",
            "evaluation_scope": "immutable_snapshot_only_not_historical_export_reproducibility",
            "archive": {
                "logical_locator": acquisition["archive_logical_locator"],
                "filename": acquisition["archive_filename"],
                **actual_archive,
                "sidecar_logical_locator": acquisition["sidecar_logical_locator"],
                "sidecar_filename": acquisition["sidecar_filename"],
                "sidecar_sha256": acquisition["sidecar_sha256"],
                "sidecar_expected_line": acquisition["sidecar_expected_line"],
                "expected_archive_root": acquisition["expected_archive_root"],
            },
            "extraction": {
                "policy": "validated normalized paths; regular substantive files only; AppleDouble metadata ignored; temporary directory removed after use",
                **internal,
            },
            "status": {
                "snapshot_acquisition_integrity": "PASS",
                "upstream_production_lineage": corpus_snapshot[
                    "production_lineage"
                ]["status"],
            },
            "production_lineage": corpus_snapshot["production_lineage"],
        }
        validate_archive_attestation(corpus_snapshot, attestation)
        yield root, attestation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--corpus-archive", type=Path, required=True)
    parser.add_argument("--corpus-archive-sidecar", type=Path, required=True)
    parser.add_argument("--attestation-output", type=Path, required=True)
    args = parser.parse_args()
    output = args.attestation_output.resolve()
    if output.exists():
        raise CorpusArchiveInvalid(f"attestation output must not already exist: {output}")
    if not output.parent.is_dir():
        raise CorpusArchiveBlocked(
            f"attestation output parent must already exist: {output.parent}"
        )
    with authenticated_corpus(
        args.repo_root.resolve(),
        args.corpus_archive,
        args.corpus_archive_sidecar,
    ) as (_, attestation):
        encoded = (
            json.dumps(attestation, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    print(
        json.dumps(
            {
                "snapshot_acquisition_integrity": "PASS",
                "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
                "archive_sha256": attestation["archive"]["sha256"],
                "attestation_sha256": hashlib.sha256(encoded).hexdigest(),
                "attestation_output": str(output),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
