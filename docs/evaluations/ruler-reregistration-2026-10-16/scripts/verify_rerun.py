#!/usr/bin/env python3
"""Prove that two complete private runs produced identical bytes.

A complete run directory holds `run-manifest.json` (`make_run.py --manifest`), the run it names
under `run/<run_id>/` (`make_run.py --out-run <dir>/run`) and the review population built from it
under `review/` (`build_review_queue.py build --out <dir>/review`)."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


RUN_FILES = (
    "manifest.json",
    "mentions.ndjson.gz",
    "resolutions-literal.ndjson.gz",
    "resolutions-authority.ndjson.gz",
    "links-literal.ndjson.gz",
    "links-authority.ndjson.gz",
)
REVIEW_FILES = (
    "review/stage-1-queue.json",
    "review/stage-2-custodian.json",
    "review/private-answer-key.json",
    "review/review-population-manifest.json",
    "review/public-review-population-digest.json",
    "review/review-protocol-manifest.json",
)


def registered_files(run_dir: Path) -> tuple[str, ...]:
    run_id = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))["run_id"]
    return ("run-manifest.json", *(f"run/{run_id}/{name}" for name in RUN_FILES), *REVIEW_FILES)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(first: Path, second: Path) -> dict:
    # Two runs means two directories: the same one twice (or an alias of it) proves nothing.
    if first.resolve() == second.resolve() or first.samefile(second):
        raise ValueError(f"the two runs are one directory: {first} and {second}")
    files = registered_files(first)
    if registered_files(second) != files:
        raise ValueError("the two runs name different runs")
    first_hashes = {name: sha256_path(first / name) for name in files}
    second_hashes = {name: sha256_path(second / name) for name in files}
    mismatches = [name for name in files if first_hashes[name] != second_hashes[name]]
    if mismatches:
        raise ValueError(f"rerun byte mismatch: {mismatches}")
    return {
        "schema_version": "hapi-ruler-reregistration-2026-10-16-rerun-proof/1",
        "complete_runs_compared": 2,
        "identical_file_count": len(files),
        "all_registered_files_byte_identical": True,
        "sha256_by_file": first_hashes,
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
