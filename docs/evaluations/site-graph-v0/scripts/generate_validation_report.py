#!/usr/bin/env python3
"""Explicit release-time writer for semantic validation-report.json."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from validate_contract import semantic_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--private-run", type=Path, required=True)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    report = semantic_report(
        repo_root, args.corpus.resolve(), args.private_run.resolve()
    )
    print(json.dumps(report["summary"] | {"status": report["status"]}, sort_keys=True))
    if report["status"] != "pass":
        raise SystemExit(1)
    output = repo_root / "docs/evaluations/site-graph-v0/validation-report.json"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".validation-report.", suffix=".tmp", dir=output.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
