#!/usr/bin/env python3
"""#338 step 3: the pipeline's authority links, end to end on the frozen corpus.

Runs the production step (`pipeline.enrich.link_files.write_run`) twice on the frozen corpus
archive, in two interpreters with different `PYTHONHASHSEED`s and each into a fresh directory,
requires the two runs to have the same manifest and file contents, and measures
cross-museum matching with the authority on and off on the run (`pipeline.enrich.cross_museum
.report`), by museum, museum pair and entity type. Writes counts only; no museum text.

What it measures is the pipeline code's lift on a frozen export of the museum tables, not a
deployed run: the asset reads the database, which this environment does not have (owner,
2026-10-16: files first, database later).

    uv run python docs/evaluations/authority-bridge-338/scripts/run_end_to_end.py \\
        --archive <corpus archive> --out <json>
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_promotion import ARCHIVE_SHA256, load_corpus  # noqa: E402
from pipeline.enrich import cross_museum, link_files  # noqa: E402


def write_once(archive: Path, root: Path) -> dict:
    canonical, raw = load_corpus(archive)
    return link_files.write_run(root, lambda: (canonical, raw))


def end_to_end(archive: Path) -> dict:
    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        manifests = []
        for seed, root in (("1", first), ("2", second)):
            out = subprocess.run([sys.executable, __file__, "--archive", str(archive), "--write-once", root],
                                 check=True, capture_output=True, text=True,
                                 env={**os.environ, "PYTHONHASHSEED": seed})
            manifests.append(json.loads(out.stdout))
        contents = [{name: link_files.content_sha256(name, (Path(root) / m["run_id"] / name).read_bytes())
                     for name in m["files"]} for root, m in ((first, manifests[0]), (second, manifests[1]))]
        if manifests[0] != manifests[1] or contents[0] != contents[1]:
            raise ValueError("two runs on the same inputs and code differ")
        manifest = manifests[0]
        measured = cross_museum.report(Path(first) / manifest["run_id"])
    return {
        "schema_version": "hapi-338-end-to-end/1",
        "corpus_archive_sha256": ARCHIVE_SHA256,
        "run_id": manifest["run_id"],
        "inputs_sha256": manifest["inputs_sha256"],
        "writer_sha256": manifest["writer_sha256"],
        "resolver_versions": {mode: s["resolver_version"] for mode, s in manifest["snapshots"].items()},
        "two_runs": {"python_hash_seeds": ["1", "2"], "same_manifest_and_contents": True},
        "files": manifest["files"],
        "outcomes": manifest["outcomes"],
        "inventory": manifest["inventory"],
        "matching": measured,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--write-once", type=Path)
    args = parser.parse_args()
    if args.write_once:
        print(json.dumps(write_once(args.archive, args.write_once)))
        return
    result = end_to_end(args.archive)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
