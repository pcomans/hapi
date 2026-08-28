#!/usr/bin/env python3
"""Run one pinned real-corpus baseline with failure-safe publication."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path


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
        "corpus_inventory.json",
        "private-record-evidence.ndjson.gz",
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


def canonical_counts(path: Path) -> tuple[int, dict[str, int]]:
    counts: dict[str, int] = {}
    total = 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            museum = json.loads(line)["source_museum"]
            counts[museum] = counts.get(museum, 0) + 1
            total += 1
    return total, dict(sorted(counts.items()))


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


def preflight(repo_root: Path, corpus: Path, output: Path) -> tuple[dict, int, dict[str, int]]:
    """Perform every possible check before creating a temporary output directory."""
    if output.exists():
        raise RuntimeError(f"baseline output must not already exist: {output}")
    if not output.parent.is_dir():
        raise RuntimeError(f"baseline output parent must already exist: {output.parent}")
    evaluation_root = repo_root / "docs/evaluations/site-graph-v0"
    snapshot_path = evaluation_root / "input-snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    for relative, expected in snapshot["corpus"]["files"].items():
        verify_file(corpus / relative, expected)
    for group in ("extractor_and_matcher", "current_authority"):
        for relative, expected in snapshot[group]["files"].items():
            verify_file(repo_root / relative, expected)
    for relative in (*ARCHIVED_SCRIPTS, "docs/evaluations/site-graph-v0/scripts/build_baseline.py"):
        if not (repo_root / relative).is_file():
            raise RuntimeError(f"required runner component is missing: {relative}")
    total, museums = canonical_counts(corpus / "data/artifacts.ndjson.gz")
    if total != snapshot["corpus"]["canonical_record_count"]:
        raise RuntimeError(
            f"canonical count mismatch: expected {snapshot['corpus']['canonical_record_count']}, got {total}"
        )
    if museums != snapshot["corpus"]["records_by_museum"]:
        raise RuntimeError(
            f"canonical museum counts mismatch: expected {snapshot['corpus']['records_by_museum']}, got {museums}"
        )
    return snapshot, total, museums


def run(repo_root: Path, corpus: Path, output: Path) -> dict:
    repo_root, corpus, output = repo_root.resolve(), corpus.resolve(), output.resolve()
    _, total, museums = preflight(repo_root, corpus, output)
    evaluation_root = repo_root / "docs/evaluations/site-graph-v0"
    snapshot_path = evaluation_root / "input-snapshot.json"
    started = dt.datetime.now(dt.UTC).isoformat()
    run_id = str(uuid.uuid4())
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    published = False
    try:
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
                    "argv": ["python3", relative],
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
                "argv": ["python3", build_relative, "--repo-root", "<repo-root>",
                         "--corpus", "<corpus>", "--run-dir", "<fresh-output>"],
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
            "schema_version": "site-graph-v0-baseline-run-manifest/1",
            "commands": commands,
            "deterministic_output_hashes": output_hashes,
            "input_snapshot_sha256": sha256(snapshot_path),
            "runner_sha256": sha256(Path(__file__)),
            "builder_sha256": sha256(evaluation_root / "scripts/build_baseline.py"),
            "inventory_path_canonicalization": "absolute repo paths replaced by <repo-root>",
            "scope": (
                f"verified real {total:,}-record private corpus; no fixtures or proxies; "
                "private ledgers remain in the runtime directory"
            ),
        }
        write_json(temporary / "run-output-manifest.json", manifest)
        provenance = {
            "schema_version": "site-graph-v0-baseline-run-provenance/1",
            "run_id": run_id,
            "started_at_utc": started,
            "finished_at_utc": dt.datetime.now(dt.UTC).isoformat(),
            "requested_output": str(output),
            "publication": "temporary sibling directory atomically renamed after exact-output validation",
            "repo_root": str(repo_root),
            "corpus_root": str(corpus),
            "canonical_records": total,
            "records_by_museum": museums,
            "input_snapshot_sha256": manifest["input_snapshot_sha256"],
            "runner_sha256": manifest["runner_sha256"],
            "builder_sha256": manifest["builder_sha256"],
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
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.repo_root, args.corpus, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
