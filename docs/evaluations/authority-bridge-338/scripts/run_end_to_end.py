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


EVALUATIONS = REPO / "docs/evaluations"
# The records #369's fixes were found on and changed (`resolver-gaps-369/README.md`, "Tuned on
# #361's deciding case"): the two Queen Ahmose records and #361's Neferu d. A next registration
# must flag them; this result names them, and the README sets this run beside #361's report.
TUNED_ON_369 = frozenset({"brooklyn-3634", "met-566763", "brooklyn-3599"})
# The code the report itself runs.
REPORT_CODE = (REPO / "pipeline/pipeline/enrich/cross_museum.py", Path(__file__).resolve())


def evaluation_headline(name: str) -> dict:
    """An evaluation's committed headline, as its `real-run-report.json` gives it: each arm's
    records on targets shared by any two museums, by museum."""
    report = json.loads((EVALUATIONS / name / "results/real-run-report.json").read_text(encoding="utf-8"))
    return {arm: {museum: values["records_on_any_two_museum_shared_useful_nodes"]
                  for museum, values in report["arms"][arm]["per_museum"].items()}
            for arm in ("typed_literal", "current_authority")}


def end_to_end(archive: Path) -> dict:
    changes = json.loads((EVALUATIONS / "resolver-gaps-369/results/resolver-change.json").read_text(encoding="utf-8"))
    if not TUNED_ON_369 <= {c["artifact_id"] for c in changes["royal_woman_cued_mentions"]["changes"]}:
        raise ValueError("a tuned-on record is not among #369's changes")
    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        manifests = []
        for seed, root in (("1", first), ("2", second)):
            out = subprocess.run([sys.executable, __file__, "--archive", str(archive), "--write-once", root],
                                 check=True, capture_output=True, text=True,
                                 env={**os.environ, "PYTHONHASHSEED": seed})
            manifests.append(json.loads(out.stdout))
        runs = [Path(root) / m["run_id"] for root, m in ((first, manifests[0]), (second, manifests[1]))]
        contents = [{name: link_files.content_sha256(name, (run / name).read_bytes()) for name in m["files"]}
                    for run, m in zip(runs, manifests)]
        reports = [cross_museum.report(run) for run in runs]
        if manifests[0] != manifests[1] or contents[0] != contents[1] or reports[0] != reports[1]:
            raise ValueError("two runs on the same inputs and code differ")
        manifest = manifests[0]
    return {
        "schema_version": "hapi-338-end-to-end/3",
        "corpus_archive_sha256": ARCHIVE_SHA256,
        "run_ids": [m["run_id"] for m in manifests],
        "inputs_sha256": manifest["inputs_sha256"],
        "writer_sha256": manifest["writer_sha256"],
        "resolver_versions": {mode: s["resolver_version"] for mode, s in manifest["snapshots"].items()},
        "report_sha256": {str(p.relative_to(REPO)): link_files.hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in REPORT_CODE},
        "two_runs": {"python_hash_seeds": ["1", "2"], "same_manifest_contents_and_report": True},
        "files": manifest["files"],
        "outcomes": manifest["outcomes"],
        "inventory": manifest["inventory"],
        "matching": reports[0],
        "tuned_on_369": sorted(TUNED_ON_369),
        # What #337 (sites, rulers and tombs; its own mention ledger and code of 2026-10-11) and #361
        # (rulers only; this mention ledger) reported, to set beside this run.
        "evaluation_headlines": {"337": evaluation_headline("authority-independent-control-2026-10-11"),
                                 "361": evaluation_headline("ruler-reregistration-2026-10-15")},
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
    if args.out is None:
        parser.error("--out is required")
    result = end_to_end(args.archive)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
