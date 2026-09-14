#!/usr/bin/env python3
"""Prove that two complete private control runs produced identical bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


FILES = (
    "mentions.ndjson.gz",
    "extraction-manifest.json",
    "typed-literal-arm.ndjson.gz",
    "current-authority-arm.ndjson.gz",
    "typed-literal-links.ndjson.gz",
    "current-authority-links.ndjson.gz",
    "report.json",
    "run-manifest.json",
    "SHA256SUMS",
    "review/stage-1-queue.json",
    "review/stage-2-custodian.json",
    "review/private-answer-key.json",
    "review/review-population-manifest.json",
    "review/public-review-population-digest.json",
    "review/review-protocol-manifest.json",
)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(first: Path, second: Path) -> dict:
    first_hashes = {name: sha256_path(first / name) for name in FILES}
    second_hashes = {name: sha256_path(second / name) for name in FILES}
    mismatches = [name for name in FILES if first_hashes[name] != second_hashes[name]]
    if mismatches:
        raise ValueError(f"rerun byte mismatch: {mismatches}")
    first_manifest = json.loads((first / "run-manifest.json").read_text(encoding="utf-8"))
    second_manifest = json.loads((second / "run-manifest.json").read_text(encoding="utf-8"))
    if first_manifest != second_manifest:
        raise ValueError("run manifests differ despite matching registered files")
    return {
        "schema_version": "hapi-authority-independent-control-rerun-proof/1",
        "complete_runs_compared": 2,
        "identical_file_count": len(FILES),
        "all_registered_files_byte_identical": True,
        "sha256_by_file": first_hashes,
        "mention_ledger_sha256": first_manifest["inputs"]["mention_ledger"]["gzip_sha256"],
        "ordered_mention_ids_sha256": first_manifest["inputs"]["mention_ledger"]["ordered_mention_ids_sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    proof = verify(args.first, args.second)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
