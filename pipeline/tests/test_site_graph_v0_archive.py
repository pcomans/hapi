"""Adversarial logic and opt-in real-archive tests for issue #327.

Fixture-backed tests below prove only verifier behavior.  Tests carrying a corpus
claim require the authorized archive environment variables and otherwise skip;
the release evidence command sets both variables explicitly.
"""

from __future__ import annotations

import copy
import importlib.util
import io
import json
import os
import sys
import tarfile
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "docs/evaluations/site-graph-v0/scripts/corpus_archive.py"
SPEC = importlib.util.spec_from_file_location("_hapi_site_graph_v0_corpus_archive", SCRIPT)
assert SPEC and SPEC.loader
corpus_archive = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = corpus_archive
SPEC.loader.exec_module(corpus_archive)


def _authorized_paths() -> tuple[Path, Path]:
    archive = os.environ.get(corpus_archive.ARCHIVE_ENV)
    sidecar = os.environ.get(corpus_archive.SIDECAR_ENV)
    if not archive or not sidecar:
        pytest.skip("authorized external private archive variables are not configured")
    return Path(archive), Path(sidecar)


@pytest.mark.parametrize(
    "name",
    ["/absolute", "hapi-museum-corpus-2026-08-27/../escape", "other/file"],
)
def test_safe_extraction_rejects_escape_paths(name: str) -> None:
    with pytest.raises(corpus_archive.CorpusArchiveInvalid):
        corpus_archive._safe_relative_member(name, "hapi-museum-corpus-2026-08-27")


def test_missing_archive_is_blocked_not_passed(tmp_path: Path) -> None:
    with pytest.raises(corpus_archive.CorpusArchiveBlocked):
        with corpus_archive.authenticated_corpus(
            REPO, tmp_path / "missing.tar.gz", tmp_path / "missing.sha256"
        ):
            pass


def test_outer_archive_corruption_is_invalid_before_extraction(tmp_path: Path) -> None:
    archive = tmp_path / "wrong.tar.gz"
    sidecar = tmp_path / "wrong.sha256"
    archive.write_bytes(b"not the authorized archive")
    sidecar.write_text("0" * 64 + "  wrong.tar.gz\n", encoding="utf-8")
    with pytest.raises(corpus_archive.CorpusArchiveInvalid, match="archive mismatch"):
        with corpus_archive.authenticated_corpus(REPO, archive, sidecar):
            pass


def test_count_reader_checks_exact_museum_population(tmp_path: Path) -> None:
    import gzip

    path = tmp_path / "records.ndjson.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write('{"source_museum":"met"}\n')
        handle.write('{"source_museum":"brooklyn"}\n')
        handle.write('{"source_museum":"met"}\n')
    assert corpus_archive._canonical_counts(path) == (
        3,
        {"brooklyn": 1, "met": 2},
    )


def test_real_archive_authenticates_and_attestation_is_bound() -> None:
    archive, sidecar = _authorized_paths()
    snapshot = json.loads(
        (REPO / "docs/evaluations/site-graph-v0/input-snapshot.json").read_text()
    )["corpus"]
    with corpus_archive.authenticated_corpus(REPO, archive, sidecar) as (root, attestation):
        assert root.name == snapshot["archive_acquisition"]["expected_archive_root"]
        assert (
            attestation["extraction"]["canonical_record_count"]
            == snapshot["canonical_record_count"]
        )
        corpus_archive.validate_archive_attestation(snapshot, attestation)
        mutated = copy.deepcopy(attestation)
        mutated["extraction"]["canonical_record_count"] -= 1
        with pytest.raises(corpus_archive.CorpusArchiveInvalid, match="binding mismatch"):
            corpus_archive.validate_archive_attestation(snapshot, mutated)


def test_real_archive_internal_member_corruption_fails_checksum(tmp_path: Path) -> None:
    archive, _ = _authorized_paths()
    corrupted = tmp_path / "internal-corruption.tar.gz"
    with tarfile.open(archive, "r:gz") as source, tarfile.open(corrupted, "w:gz") as target:
        for member in source.getmembers():
            if member.isdir():
                target.addfile(member)
                continue
            extracted = source.extractfile(member)
            assert extracted is not None
            payload = extracted.read()
            if member.name.endswith("/NOTICE") and not member.name.endswith("/._NOTICE"):
                payload += b"corrupt"
                member.size = len(payload)
            target.addfile(member, io.BytesIO(payload))
    snapshot = json.loads(
        (REPO / "docs/evaluations/site-graph-v0/input-snapshot.json").read_text()
    )["corpus"]
    with pytest.raises(corpus_archive.CorpusArchiveInvalid, match="checksum mismatch"):
        corpus_archive._extract_and_verify(corrupted, tmp_path / "extract", snapshot)
