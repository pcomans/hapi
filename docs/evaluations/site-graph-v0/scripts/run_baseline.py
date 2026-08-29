#!/usr/bin/env python3
"""Run one pinned real-corpus baseline with failure-safe publication."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from corpus_archive import authenticated_corpus
from runtime_attestation import build_runtime_attestation


ARCHIVED_SCRIPTS = (
    "docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts/inventory_inputs.py",
    "docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts/run_linkability.py",
)
DETERMINISTIC_OUTPUTS = frozenset(
    {
        "adapter_catalog_summary.json",
        "artifact_authority_links.ndjson.gz",
        "authority_inventory.json",
        "authority_node_connectivity.json",
        "baseline-metrics.json",
        "baseline-node-scope.json",
        "connectivity_metrics.json",
        "corpus-archive-attestation.json",
        "corpus_inventory.json",
        "private-record-evidence.ndjson.gz",
        "runtime-attestation.json",
        "private-opportunity-source.ndjson.gz",
        "private-opportunity-ledger.json",
        "private-ledger-digests.json",
        "linkability_metrics.json",
        "mentions.ndjson.gz",
        "planned-opportunity-summary.json",
        "top_gaps.json",
        "top-unmatched-components.json",
    }
)
FINAL_OUTPUTS = DETERMINISTIC_OUTPUTS | {"run-output-manifest.json", "run-provenance.json"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def verify_file(path: Path, expected: dict) -> None:
    if not path.is_file():
        raise RuntimeError(f"required frozen input is missing: {path}")
    actual = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    wanted = {"bytes": expected["bytes"], "sha256": expected["sha256"]}
    if actual != wanted:
        raise RuntimeError(f"frozen input mismatch: {path}; expected {wanted}, got {actual}")


def canonicalize_repo_paths(value: object, repo_root: Path) -> object:
    """Preserve archived JSON shape while replacing only checkout prefixes."""
    if isinstance(value, dict):
        return {key: canonicalize_repo_paths(child, repo_root) for key, child in value.items()}
    if isinstance(value, list):
        return [canonicalize_repo_paths(child, repo_root) for child in value]
    if isinstance(value, str):
        prefix = str(repo_root) + "/"
        return "<repo-root>/" + value[len(prefix) :] if value.startswith(prefix) else value
    return value


def _regular_output_names(directory: Path) -> set[str]:
    names = set()
    for path in directory.iterdir():
        if not path.is_file():
            raise RuntimeError(f"unexpected non-file baseline output: {path.name}")
        names.add(path.name)
    return names


def preflight(repo_root: Path, output: Path) -> dict:
    """Perform every possible check before creating a temporary output directory."""
    if output.exists():
        raise RuntimeError(f"baseline output must not already exist: {output}")
    if not output.parent.is_dir():
        raise RuntimeError(f"baseline output parent must already exist: {output.parent}")
    evaluation_root = repo_root / "docs/evaluations/site-graph-v0"
    snapshot_path = evaluation_root / "input-snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    for group in ("extractor_and_matcher", "current_authority"):
        for relative, expected in snapshot[group]["files"].items():
            verify_file(repo_root / relative, expected)
    for relative in (*ARCHIVED_SCRIPTS, "docs/evaluations/site-graph-v0/scripts/build_baseline.py"):
        if not (repo_root / relative).is_file():
            raise RuntimeError(f"required runner component is missing: {relative}")
    return snapshot


def run(
    repo_root: Path,
    corpus_archive: Path,
    corpus_archive_sidecar: Path,
    output: Path,
) -> dict:
    repo_root, output = repo_root.resolve(), output.resolve()
    snapshot = preflight(repo_root, output)
    runtime_attestation = build_runtime_attestation(repo_root, snapshot)
    evaluation_root = repo_root / "docs/evaluations/site-graph-v0"
    snapshot_path = evaluation_root / "input-snapshot.json"
    started = dt.datetime.now(dt.UTC).isoformat()
    run_id = str(uuid.uuid4())
    with authenticated_corpus(
        repo_root, corpus_archive, corpus_archive_sidecar
    ) as (corpus, archive_attestation):
        total = archive_attestation["extraction"]["canonical_record_count"]
        museums = archive_attestation["extraction"]["records_by_museum"]
        temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
        published = False
        try:
            write_json(temporary / "corpus-archive-attestation.json", archive_attestation)
            write_json(temporary / "runtime-attestation.json", runtime_attestation)
            env = os.environ.copy()
            env.update(
                {
                    "HAPI_ROOT": str(repo_root),
                    "HAPI_CORPUS": str(corpus),
                    "HAPI_EVAL_OUT": str(temporary),
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
            )
            commands = []
            for relative in ARCHIVED_SCRIPTS:
                result = subprocess.run(
                    [sys.executable, str(repo_root / relative)], cwd=repo_root, env=env,
                    check=False, capture_output=True, text=True,
                )
                commands.append(
                    {
                        "argv": ["<pipeline-python>", relative],
                        "returncode": result.returncode,
                        "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
                        "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest(),
                    }
                )
                if result.returncode:
                    raise RuntimeError(
                        f"frozen baseline command failed: {relative}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
                    )

            for name in ("corpus_inventory.json", "authority_inventory.json"):
                path = temporary / name
                value = canonicalize_repo_paths(json.loads(path.read_text(encoding="utf-8")), repo_root)
                path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            build_relative = "docs/evaluations/site-graph-v0/scripts/build_baseline.py"
            result = subprocess.run(
                [sys.executable, str(repo_root / build_relative), "--repo-root", str(repo_root),
                 "--corpus", str(corpus), "--run-dir", str(temporary)],
                cwd=repo_root, env=env, check=False, capture_output=True, text=True,
            )
            commands.append(
                {
                    "argv": ["<pipeline-python>", build_relative, "--repo-root", "<repo-root>",
                             "--corpus", "<authenticated-temporary-extraction>",
                             "--run-dir", "<fresh-output>"],
                    "returncode": result.returncode,
                    "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
                    "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest(),
                }
            )
            if result.returncode:
                raise RuntimeError(
                    f"site baseline derivation failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
                )

            actual = _regular_output_names(temporary)
            if actual != DETERMINISTIC_OUTPUTS:
                raise RuntimeError(
                    f"baseline output set mismatch: missing={sorted(DETERMINISTIC_OUTPUTS - actual)}, "
                    f"extra={sorted(actual - DETERMINISTIC_OUTPUTS)}"
                )
            output_hashes = {name: sha256(temporary / name) for name in sorted(DETERMINISTIC_OUTPUTS)}
            manifest = {
                "schema_version": "site-graph-v0-baseline-run-manifest/3",
                "commands": commands,
                "deterministic_output_hashes": output_hashes,
                "input_snapshot_sha256": sha256(snapshot_path),
                "runner_sha256": sha256(Path(__file__)),
                "builder_sha256": sha256(evaluation_root / "scripts/build_baseline.py"),
                "inventory_path_canonicalization": "absolute repo paths replaced by <repo-root>",
                "corpus_archive_attestation_sha256": output_hashes[
                    "corpus-archive-attestation.json"
                ],
                "corpus_archive_sha256": archive_attestation["archive"]["sha256"],
                "runtime_attestation": {
                    "path": "runtime-attestation.json",
                    "sha256": output_hashes["runtime-attestation.json"],
                    "python": runtime_attestation["python"],
                    "dependency_lock": runtime_attestation["dependency_lock"],
                },
                "scope": (
                    f"authenticated immutable archive snapshot with {total:,} real private records; "
                    "no fixtures or proxies; private ledgers remain in the runtime directory; "
                    "historical producer lineage is unavailable"
                ),
                "status": {
                    "snapshot_acquisition_integrity": "PASS",
                    "derived_baseline_reproducibility": "PASS",
                    "upstream_production_lineage": "UNAVAILABLE_DISCLOSED",
                    "overall_contract_status": "READY_SNAPSHOT_CONDITIONAL",
                    "downstream_product_verdict": "NOT_RUN",
                },
            }
            write_json(temporary / "run-output-manifest.json", manifest)
            provenance = {
                "schema_version": "site-graph-v0-baseline-run-provenance/3",
                "run_id": run_id,
                "started_at_utc": started,
                "finished_at_utc": dt.datetime.now(dt.UTC).isoformat(),
                "requested_output": str(output),
                "publication": "temporary sibling directory atomically renamed after exact-output validation",
                "repo_root": str(repo_root),
                "corpus_archive_logical_locator": archive_attestation["archive"]["logical_locator"],
                "corpus_archive_sha256": archive_attestation["archive"]["sha256"],
                "corpus_archive_attestation_sha256": manifest[
                    "corpus_archive_attestation_sha256"
                ],
                "temporary_extraction_policy": archive_attestation["extraction"]["policy"],
                "canonical_records": total,
                "records_by_museum": museums,
                "input_snapshot_sha256": manifest["input_snapshot_sha256"],
                "runner_sha256": manifest["runner_sha256"],
                "builder_sha256": manifest["builder_sha256"],
                "runtime_attestation": manifest["runtime_attestation"],
                "status": manifest["status"],
            }
            write_json(temporary / "run-provenance.json", provenance)
            if _regular_output_names(temporary) != FINAL_OUTPUTS:
                raise RuntimeError("final baseline output set changed before publication")
            os.replace(temporary, output)
            published = True
            return {
                "output": str(output), "run_id": run_id, "canonical_records": total,
                "manifest_sha256": sha256(output / "run-output-manifest.json"),
                "deterministic_outputs": len(output_hashes),
            }
        finally:
            if not published and temporary.exists():
                shutil.rmtree(temporary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--corpus-archive", type=Path, required=True)
    parser.add_argument("--corpus-archive-sidecar", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.repo_root,
                args.corpus_archive,
                args.corpus_archive_sidecar,
                args.output,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
