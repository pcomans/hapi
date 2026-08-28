#!/usr/bin/env python3
"""Generate a pre-run candidate-input manifest from already committed bytes."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

from candidate_git import blob_oid, normalize_relative_path, read_authenticated_json, resolve_commit
from integrity import EVALUATION_RELATIVE, verify_release
from schema_validation import validate_schema


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, check=False, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def generate(
    repo_root: Path,
    output: Path,
    hierarchy_path: str,
    relation_ledger_path: str,
    source_snapshot_paths: list[str],
    created_by: str,
) -> dict:
    repo_root = repo_root.resolve()
    output = output.resolve()
    if output.exists():
        raise RuntimeError(f"refusing to overwrite candidate freeze manifest: {output}")
    if not output.parent.is_dir():
        raise RuntimeError(f"candidate freeze output parent does not exist: {output.parent}")
    release = verify_release(repo_root)
    evaluation_root = repo_root / EVALUATION_RELATIVE
    private_digest = json.loads(
        (evaluation_root / "private-ledger-digests.json").read_text(encoding="utf-8")
    )
    head = resolve_commit(repo_root, _git(repo_root, "rev-parse", "HEAD"))
    specs = [
        ("hierarchy", normalize_relative_path(hierarchy_path), "candidate-hierarchy.schema.json"),
        (
            "relation_ledger",
            normalize_relative_path(relation_ledger_path),
            "relation-ledger.schema.json",
        ),
        *[
            (
                "source_snapshot",
                normalize_relative_path(path),
                "candidate-source-snapshot.schema.json",
            )
            for path in source_snapshot_paths
        ],
    ]
    if not source_snapshot_paths:
        raise RuntimeError("at least one source snapshot is required")
    paths = [path for _, path, _ in specs]
    if len(paths) != len(set(paths)):
        raise RuntimeError("candidate freeze input paths must be unique")

    files = []
    for role, relative, schema_name in specs:
        working_path = repo_root / relative
        if not working_path.is_file():
            raise RuntimeError(f"candidate freeze input missing: {relative}")
        committed, metadata = read_authenticated_json(repo_root, head, relative)
        if hashlib.sha256(working_path.read_bytes()).hexdigest() != metadata["sha256"]:
            raise RuntimeError(f"candidate freeze input has uncommitted changes: {relative}")
        validate_schema(
            committed,
            evaluation_root / "schemas" / schema_name,
            f"candidate freeze input {relative}",
        )
        files.append(
            {
                "role": role,
                "path": relative,
                "sha256": metadata["sha256"],
                "git_blob_oid": blob_oid(repo_root, head, relative),
                "schema_version": committed["schema_version"],
            }
        )
    value = {
        "schema_version": "site-graph-v0-candidate-freeze-manifest/1",
        "contract_version": "site-graph-v0/2",
        "release_manifest_sha256": release["manifest_sha256"],
        "private_opportunity_ledger_canonical_sha256": private_digest["ledgers"][
            "private_opportunity_membership"
        ]["canonical_json_sha256"],
        "created_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "created_by": created_by,
        "provenance": {
            "input_commit": head,
            "method": "validated committed Git blobs before manifest generation",
            "timing_policy": (
                "the manifest must be committed as the distinct freeze commit before any "
                "candidate result commit; comparator gates Git ancestry, not timestamps"
            ),
        },
        "files": sorted(files, key=lambda item: (item["role"], item["path"])),
    }
    validate_schema(
        value,
        evaluation_root / "schemas/candidate-freeze-manifest.schema.json",
        "candidate freeze manifest",
    )
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    return {"output": str(output), "input_commit": head, "file_count": len(files)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hierarchy-path", required=True)
    parser.add_argument("--relation-ledger-path", required=True)
    parser.add_argument("--source-snapshot-path", action="append", default=[])
    parser.add_argument("--created-by", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            generate(
                args.repo_root,
                args.output,
                args.hierarchy_path,
                args.relation_ledger_path,
                args.source_snapshot_path,
                args.created_by,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
