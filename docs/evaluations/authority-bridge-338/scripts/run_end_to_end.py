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
import hashlib
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
QUALIFIED_BY = {"site": "#337 v10", "ruler": "#361"}
# The code the report itself runs.
REPORT_CODE = (REPO / "pipeline/pipeline/enrich/cross_museum.py", Path(__file__).resolve())


def evaluation_headline(name: str) -> dict:
    """An evaluation's committed headline, as its `real-run-report.json` gives it: each arm's
    records on targets shared by any two museums, by museum."""
    report = json.loads((EVALUATIONS / name / "results/real-run-report.json").read_text(encoding="utf-8"))
    return {arm: {museum: values["records_on_any_two_museum_shared_useful_nodes"]
                  for museum, values in report["arms"][arm]["per_museum"].items()}
            for arm in ("typed_literal", "current_authority")}


def ahmes_b_records(run: Path) -> dict:
    """The records #369's one new shared Met-Brooklyn ruler target joins, by museum, each with the
    other shared Met-Brooklyn ruler targets it is on with the authority (none means Ahmes B is
    what connects it) and whether plain text connects it (so it was one of #361's losses)."""
    by_mode = {mode: cross_museum.target_records(cross_museum.load_links(run, mode)) for mode in ("authority", "literal")}

    def shared(by_target: dict) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for (entity, target), sides in by_target.items():
            if entity == "ruler" and "met" in sides and "brooklyn" in sides:
                for museum in ("met", "brooklyn"):
                    for record in sides[museum]:
                        out.setdefault(record, set()).add(target)
        return out
    on, off = shared(by_mode["authority"]), shared(by_mode["literal"])
    return {museum: {record: {"other_shared_authority_targets": sorted(on[record] - {"dodson_hilton:Ahmes B"}),
                              "connected_by_plain_text": record in off}
                     for record in sorted(records)}
            for museum, records in sorted(by_mode["authority"][("ruler", "dodson_hilton:Ahmes B")].items())}


def review_coverage(run: Path, report: dict) -> dict:
    """For this frozen run only: per qualified scope, the review that qualified it, the evidence,
    and the connected records that review did not see.
    * Sites: their links are #337's record for record (`test_the_site_links_are_337s_record_for_record`),
      so nothing is unreviewed; nothing is computed here.
    * Rulers: the links made from the mentions whose resolution differs from #361's (the step-1
      proof's `differ_as_369_measured`) are removed; a record connected now but not without them
      depends on a change #361's review did not see."""
    changed = set(json.loads((EVALUATIONS / "authority-bridge-338/results/promotion-check.json").read_text(
        encoding="utf-8"))["rulers_vs_361_authority_arm"]["differ_as_369_measured"])
    links = cross_museum.load_links(run, "authority")
    before = cross_museum.connected(cross_museum.target_records(
        [l for l in links if not (l["entity_type"] == "ruler" and set(l["mention_ids"]) & changed)]))
    now = cross_museum.connected(cross_museum.target_records(links))
    empty = {"records": set()}
    out = {}
    for key, row in sorted(report["by_museum_pair"].items()):
        if not row["qualified"]:
            continue
        entity, a, b = key.split("|")
        if entity == "site":
            out[key] = {"qualified_by": QUALIFIED_BY[entity], "unreviewed_connected_records": [],
                        "review_covers_population": True, "by": "site links identical to #337's (identity test)"}
        else:
            unreviewed = sorted(r for x, y in ((a, b), (b, a))
                                for r in now.get((entity, x, y), empty)["records"] - before.get((entity, x, y), empty)["records"])
            out[key] = {"qualified_by": QUALIFIED_BY[entity], "unreviewed_connected_records": unreviewed,
                        "review_covers_population": not unreviewed,
                        "by": "links of the mentions resolving differently from #361 removed (step-1 proof)"}
    return out


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
        ahmes_b = ahmes_b_records(runs[0])
        coverage = review_coverage(runs[0], reports[0])
    return {
        "schema_version": "hapi-338-end-to-end/3",
        "corpus_archive_sha256": ARCHIVE_SHA256,
        "run_ids": [m["run_id"] for m in manifests],
        "inputs_sha256": manifest["inputs_sha256"],
        "writer_sha256": manifest["writer_sha256"],
        "resolver_versions": {mode: s["resolver_version"] for mode, s in manifest["snapshots"].items()},
        "report_sha256": {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in REPORT_CODE},
        "two_runs": {"python_hash_seeds": ["1", "2"], "same_manifest_contents_and_report": True},
        "files": manifest["files"],
        "outcomes": manifest["outcomes"],
        "inventory": manifest["inventory"],
        "matching": reports[0],
        "tuned_on_369": sorted(TUNED_ON_369),
        # The records #369's one new shared ruler target joins, by museum (authority mode).
        "ahmes_b_records": ahmes_b,
        # For this frozen run only: whether the review that qualified each scope saw its population.
        "review_coverage": coverage,
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
