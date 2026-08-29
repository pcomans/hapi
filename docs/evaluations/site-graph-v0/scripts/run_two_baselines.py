#!/usr/bin/env python3
"""Create, authenticate, and compare two fresh real-corpus baseline runs."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from compare_baseline_runs import atomic_write_json, compare
from run_baseline import run


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def run_two(
    repo_root: Path,
    corpus_archive: Path,
    corpus_archive_sidecar: Path,
    output_root: Path,
    evidence_path: Path,
    *,
    release_maintainer_mode: bool = False,
) -> dict:
    repo_root = repo_root.resolve()
    release_root = (repo_root / "docs/evaluations/site-graph-v0").resolve()
    output_root = output_root.resolve()
    evidence_path = evidence_path.resolve()
    protected_destinations = [
        path for path in (output_root, evidence_path) if _inside(path, release_root)
    ]
    if protected_destinations and not release_maintainer_mode:
        raise RuntimeError(
            "refusing tracked release output/evidence destination without explicit "
            f"--release-maintainer-mode: {protected_destinations}"
        )
    if evidence_path.exists() and not release_maintainer_mode:
        raise RuntimeError(f"two-run evidence path must be fresh: {evidence_path}")
    if _inside(evidence_path, output_root):
        raise RuntimeError("two-run evidence must be outside the fresh output root")
    if output_root.exists():
        raise RuntimeError(f"two-run output root must be fresh: {output_root}")
    if not output_root.parent.is_dir():
        raise RuntimeError(f"two-run output parent must exist: {output_root.parent}")
    if not evidence_path.parent.is_dir():
        raise RuntimeError(f"two-run evidence parent must exist: {evidence_path.parent}")
    output_root.mkdir()
    try:
        run_a, run_b = output_root / "run-a", output_root / "run-b"
        run(repo_root, corpus_archive, corpus_archive_sidecar, run_a)
        run(repo_root, corpus_archive, corpus_archive_sidecar, run_b)
        evidence = compare(run_a, run_b)
        if (
            evidence["status"]["overall_contract_status"]
            != "READY_SNAPSHOT_CONDITIONAL"
        ):
            raise RuntimeError(f"deterministic baseline reproduction failed: {evidence}")
        evidence["orchestration"] = {
            "script": "docs/evaluations/site-graph-v0/scripts/run_two_baselines.py",
            "created_fresh_output_root": "<fresh-output-root>",
            "created_run_directories": [
                "<fresh-output-root>/run-a",
                "<fresh-output-root>/run-b",
            ],
        }
        atomic_write_json(evidence_path, evidence)
        return evidence
    except BaseException:
        shutil.rmtree(output_root, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--corpus-archive", type=Path, required=True)
    parser.add_argument("--corpus-archive-sidecar", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument(
        "--release-maintainer-mode",
        action="store_true",
        help=(
            "allow an intentional tracked release destination; ordinary reproduction "
            "must keep all outputs outside docs/evaluations/site-graph-v0"
        ),
    )
    args = parser.parse_args()
    evidence = run_two(
        args.repo_root,
        args.corpus_archive,
        args.corpus_archive_sidecar,
        args.output_root,
        args.evidence,
        release_maintainer_mode=args.release_maintainer_mode,
    )
    print(
        json.dumps(
            {"status": evidence["status"], "output_root": str(args.output_root.resolve())},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
