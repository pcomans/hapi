#!/usr/bin/env python3
"""Create, authenticate, and compare two fresh real-corpus baseline runs."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from compare_baseline_runs import atomic_write_json, compare
from run_baseline import run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    if output_root.exists():
        raise RuntimeError(f"two-run output root must be fresh: {output_root}")
    if not output_root.parent.is_dir():
        raise RuntimeError(f"two-run output parent must exist: {output_root.parent}")
    output_root.mkdir()
    try:
        run_a, run_b = output_root / "run-a", output_root / "run-b"
        run(args.repo_root, args.corpus, run_a)
        run(args.repo_root, args.corpus, run_b)
        evidence = compare(run_a, run_b)
        if evidence["status"] != "pass":
            raise RuntimeError(f"deterministic baseline reproduction failed: {evidence}")
        evidence["orchestration"] = {
            "script": "docs/evaluations/site-graph-v0/scripts/run_two_baselines.py",
            "created_fresh_output_root": "<fresh-output-root>",
            "created_run_directories": ["<fresh-output-root>/run-a", "<fresh-output-root>/run-b"],
        }
        atomic_write_json(args.evidence, evidence)
        print(json.dumps({"status": "pass", "output_root": str(output_root)}, sort_keys=True))
    except BaseException:
        shutil.rmtree(output_root, ignore_errors=True)
        raise


if __name__ == "__main__":
    main()
