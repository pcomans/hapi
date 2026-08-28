#!/usr/bin/env python3
"""Explicitly freeze the release inventory; never called by validation or tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from integrity import EVALUATION_RELATIVE, MANIFEST_NAME, discovered_release_files, sha256
from release_contract import CONTRACT_VERSION, PYCACHE_EXCLUSION, REQUIRED_RELEASE_FILES


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="replace an existing manifest after an intentional release update",
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    output = repo_root / EVALUATION_RELATIVE / MANIFEST_NAME
    if output.exists() and not args.replace:
        raise RuntimeError(f"refusing to replace {output} without --replace")
    actual = discovered_release_files(repo_root)
    missing = sorted(REQUIRED_RELEASE_FILES - actual)
    extra = sorted(actual - REQUIRED_RELEASE_FILES)
    if missing or extra:
        raise RuntimeError(
            "refusing to freeze a release outside the static contract: "
            + json.dumps({"missing": missing, "extra": extra}, sort_keys=True)
        )
    names = sorted(REQUIRED_RELEASE_FILES)
    value = {
        "schema_version": "site-graph-v0-release-manifest/2",
        "contract_version": CONTRACT_VERSION,
        "hash_algorithm": "sha256",
        "pycache_exclusion": PYCACHE_EXCLUSION,
        "inventory_rule": (
            "Exactly REQUIRED_RELEASE_FILES in scripts/release_contract.py. Any addition, "
            "removal, or cache-exclusion change requires a separately reviewed contract-version migration."
        ),
        "files": {
            name: {
                "bytes": (repo_root / name).stat().st_size,
                "sha256": sha256(repo_root / name),
            }
            for name in names
        },
    }
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    print(json.dumps({"files": len(names), "manifest": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
