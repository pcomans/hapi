"""Ruler-mention resolution before vs after working off the escalation queue.

Runs the #337 ruler resolver over the frozen #337 mention ledger against the graph before
this change (`--before-graph`, from main) and the rebuilt graph, and writes aggregate counts
plus the complete list of merges the rebuild added (for review). Reuses the #342
measurement's resolver wiring unchanged. No model call.

    pipeline/.venv/bin/python docs/evaluations/ruler-escalation-queue/scripts/measure_rebuild.py \\
      --ledger <#337 run>/mentions.ndjson.gz --extraction-manifest <#337 run>/extraction-manifest.json \\
      --before-graph <graph before> --after-graph web-claimgraph/data/claim-graph.json \\
      --out docs/evaluations/ruler-escalation-queue/results/rebuild.json
"""

from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MEASURE_342 = ROOT / "docs/evaluations/ruler-cluster-reconciliation-342/scripts/measure_ruler_ambiguity.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--extraction-manifest", type=Path, required=True)
    ap.add_argument("--before-graph", type=Path, required=True)
    ap.add_argument("--after-graph", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    m342 = _load("_rebuild_measure_342", MEASURE_342)
    os.environ["HAPI_ROOT"] = str(ROOT)
    compare = m342._load("_rebuild_compare_arms", m342.CONTROL)
    linkability = m342._load("_rebuild_run_linkability", m342.LINKABILITY)
    manifest = json.loads(args.extraction_manifest.read_text("utf-8"))
    ledger, ledger_proof = compare.read_ledger(args.ledger, manifest)
    rulers = [m for m in ledger if m["entity_type"] == "ruler"]
    before_graph = json.loads(args.before_graph.read_text("utf-8"))
    after_graph = json.loads(args.after_graph.read_text("utf-8"))
    before = m342._resolve(compare, linkability, before_graph, rulers)
    after = m342._resolve(compare, linkability, after_graph, rulers)

    label_of = {r["id"]: r["display_name"] for r in after_graph["rulers"]}
    transitions = collections.Counter()
    moved = 0
    newly = collections.Counter()
    still_ambiguous = collections.Counter()
    for b, a in zip(before, after, strict=True):
        if b["mention_id"] != a["mention_id"]:
            raise ValueError("before/after resolutions are not aligned")
        transitions[f"{b['status']}->{a['status']}"] += 1
        if b["status"] == "resolved" and a["status"] == "resolved" and not (
            m342._record_ids_of(before_graph, b["target_ids"][0])
            & m342._record_ids_of(after_graph, a["target_ids"][0])
        ):
            moved += 1
        if b["status"] != "resolved" and a["status"] == "resolved":
            records = m342._record_ids_of(after_graph, a["target_ids"][0])
            newly[" / ".join(sorted({label_of[r] for r in records}))] += 1
        if a["status"] == "ambiguous":
            still_ambiguous[" | ".join(
                " / ".join(sorted({label_of[r] for r in m342._record_ids_of(after_graph, t)}))
                for t in sorted(a["target_ids"])
            )] += 1

    # Every rebuilt cluster joining more than one before-unit: the complete list of merges
    # this rebuild made. A false merge can only appear here.
    unit_of = {r["id"]: r["id"] for r in before_graph["rulers"]}
    for cluster in before_graph["clusters"]:
        for member in cluster["member_ids"]:
            unit_of[member] = cluster["id"]
    merges = []
    for cluster in after_graph["clusters"]:
        units = sorted({unit_of[m] for m in cluster["member_ids"]})
        if len(units) > 1:
            new_edges = [
                e for e in after_graph["approvedEdges"]
                if e["a_id"] in cluster["member_ids"] and unit_of[e["a_id"]] != unit_of[e["b_id"]]
            ]
            merges.append({
                "label": cluster["label"],
                "members": [f"{m} ({label_of[m]})" for m in cluster["member_ids"]],
                "before_units": units,
                "joining_edges": [
                    {"a": e["a_id"], "b": e["b_id"], "basis": e["basis"], "reason": e["reason"]}
                    for e in new_edges
                ],
            })

    # Approved links of the before graph the rebuild no longer approves (each with what
    # became of the pair), and the count of newly approved links by basis.
    pair = lambda e: frozenset((e["a_id"], e["b_id"]))  # noqa: E731
    after_approved = {pair(e) for e in after_graph["approvedEdges"]}
    before_approved = {pair(e) for e in before_graph["approvedEdges"]}
    after_escalated = {pair(e): e for e in after_graph["escalations"]}
    lost = [
        {
            "a": f"{e['a_id']} ({e['a_name']})",
            "b": f"{e['b_id']} ({e['b_name']})",
            "now": (
                {"escalated": after_escalated[pair(e)]["reason"]}
                if pair(e) in after_escalated else "not materialised (rejected or not a candidate)"
            ),
        }
        for e in before_graph["approvedEdges"] if pair(e) not in after_approved
    ]
    gained = collections.Counter(
        e["basis"] for e in after_graph["approvedEdges"] if pair(e) not in before_approved
    )

    result = {
        "schema_version": "hapi-ruler-escalation-queue-rebuild/1",
        "inputs": {
            "mention_ledger": ledger_proof,
            "before_graph_sha256": m342._sha256(args.before_graph),
            "after_graph_sha256": m342._sha256(args.after_graph),
            "measure_342_sha256": m342._sha256(MEASURE_342),
            "resolver_sha256": m342._sha256(m342.LINKABILITY),
            "control_sha256": m342._sha256(m342.CONTROL),
            "script_sha256": m342._sha256(Path(__file__)),
        },
        "graph_stats": {"before": before_graph["meta"]["stats"], "after": after_graph["meta"]["stats"]},
        "ruler_mentions": len(rulers),
        "before": m342._summary(before),
        "after": m342._summary(after),
        "status_transitions": dict(sorted(transitions.items())),
        "resolved_mentions_moved_to_a_different_king": moved,
        "newly_resolved_by_target": dict(sorted(newly.items(), key=lambda kv: (-kv[1], kv[0]))),
        "still_ambiguous_by_targets": dict(sorted(still_ambiguous.items(), key=lambda kv: (-kv[1], kv[0]))),
        "merged_clusters": sorted(merges, key=lambda c: c["label"]),
        "approved_links_lost": sorted(lost, key=lambda r: (r["a"], r["b"])),
        "approved_links_gained_by_basis": dict(sorted(gained.items())),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True) + "\n", "utf-8")
    print(json.dumps({k: result[k] for k in ("graph_stats", "before", "after", "status_transitions",
                                             "resolved_mentions_moved_to_a_different_king",
                                             "approved_links_gained_by_basis")}, indent=1))
    print(len(lost), "approved links lost")
    print(len(merges), "merged clusters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
