"""Issue #342 measurement: ruler-mention resolution before vs after the claim-graph rebuild.

Runs the #337 current-authority ruler resolver (unchanged code from the linkability
benchmark) over the SAME frozen mention ledger twice — once against the claim graph
#337 registered, once against the rebuilt graph — and writes aggregate counts only.
Row-level museum data stays private (see the #337 README on redistribution terms).

The three #342 kings are identified by their claim-graph record ids, not by strings: a
mention is attributed to a king when every target its BEFORE resolution named is one of
that king's records.

Run from the repository root with the pipeline environment:

    pipeline/.venv/bin/python docs/evaluations/ruler-cluster-reconciliation-342/scripts/measure_ruler_ambiguity.py \
      --ledger <dir>/mentions.ndjson.gz --extraction-manifest <dir>/extraction-manifest.json \
      --before-graph <before claim-graph.json> --after-graph web-claimgraph/data/claim-graph.json \
      --out docs/evaluations/ruler-cluster-reconciliation-342/results/ruler-ambiguity.json
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CONTROL = ROOT / "docs/evaluations/authority-independent-control-2026-09-13/scripts/compare_arms.py"
LINKABILITY = ROOT / "docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts/run_linkability.py"

KINGS = {
    "Amenhotep III": ("beckerath-18.09", "leprohon-leprohon-18.09", "pharaoh_se-Amenhotep-III"),
    "Akhenaten": (
        "beckerath-18.10",
        "leprohon-leprohon-18.10a",
        "leprohon-leprohon-18.10b",
        "pharaoh_se-Amenhotep-IV",
    ),
    "Ramesses II": ("beckerath-19.03", "leprohon-leprohon-19.03", "pharaoh_se-Ramesses-II"),
}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record_ids_of(graph: dict, target_id: str) -> set[str]:
    """A resolver target is a cluster id or a singleton record id."""
    for cluster in graph["clusters"]:
        if cluster["id"] == target_id:
            return set(cluster["member_ids"])
    return {target_id}


def _resolve(compare, linkability, graph: dict, mentions: list[dict]) -> list[dict]:
    resolver, _catalog = linkability.build_ruler_resolver(graph)
    return compare.resolve_mentions(
        mentions, "current_authority", {"ruler": (resolver, linkability.ruler_norm)}
    )


def _summary(rows: list[dict]) -> dict:
    status = collections.Counter(r["status"] for r in rows)
    artifacts = collections.defaultdict(set)
    for r in rows:
        artifacts[r["status"]].add((r["museum"], r["artifact_id"]))
    return {
        "mentions_by_status": dict(sorted(status.items())),
        "artifacts_by_status": {k: len(v) for k, v in sorted(artifacts.items())},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--extraction-manifest", type=Path, required=True)
    ap.add_argument("--before-graph", type=Path, required=True)
    ap.add_argument("--after-graph", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    os.environ["HAPI_ROOT"] = str(ROOT)
    compare = _load("_342_compare_arms", CONTROL)
    linkability = _load("_342_run_linkability", LINKABILITY)

    manifest = json.loads(args.extraction_manifest.read_text(encoding="utf-8"))
    ledger, ledger_proof = compare.read_ledger(args.ledger, manifest)
    rulers = [m for m in ledger if m["entity_type"] == "ruler"]

    before_graph = json.loads(args.before_graph.read_text(encoding="utf-8"))
    after_graph = json.loads(args.after_graph.read_text(encoding="utf-8"))
    before = _resolve(compare, linkability, before_graph, rulers)
    after = _resolve(compare, linkability, after_graph, rulers)

    king_of: dict[str, str] = {}
    for king, ids in KINGS.items():
        for record_id in ids:
            king_of[record_id] = king

    per_king = {
        king: {"before": collections.Counter(), "after": collections.Counter(),
               "before_artifacts": collections.defaultdict(set),
               "after_artifacts": collections.defaultdict(set)}
        for king in KINGS
    }
    transitions = collections.Counter()
    for b, a in zip(before, after, strict=True):
        if b["mention_id"] != a["mention_id"]:
            raise ValueError("before/after resolutions are not aligned")
        transitions[f"{b['status']}->{a['status']}"] += 1
        records = set().union(*(_record_ids_of(before_graph, t) for t in b["target_ids"])) \
            if b["target_ids"] else set()
        kings = {king_of.get(r) for r in records}
        if len(kings) == 1 and None not in kings:
            (king,) = kings
            artifact = (b["museum"], b["artifact_id"])
            per_king[king]["before"][b["status"]] += 1
            per_king[king]["after"][a["status"]] += 1
            per_king[king]["before_artifacts"][b["status"]].add(artifact)
            per_king[king]["after_artifacts"][a["status"]].add(artifact)

    # A mention resolved before must not resolve somewhere ELSE after: the rebuild may
    # only merge a king's records, never move an existing link to a different king.
    moved = 0
    for b, a in zip(before, after, strict=True):
        if b["status"] == "resolved" and a["status"] == "resolved":
            if not (_record_ids_of(before_graph, b["target_ids"][0])
                    & _record_ids_of(after_graph, a["target_ids"][0])):
                moved += 1

    result = {
        "schema_version": "hapi-342-ruler-ambiguity/1",
        "inputs": {
            "mention_ledger": ledger_proof,
            "before_graph_sha256": _sha256(args.before_graph),
            "after_graph_sha256": _sha256(args.after_graph),
            "resolver_sha256": _sha256(LINKABILITY),
            "script_sha256": _sha256(Path(__file__)),
        },
        "ruler_mentions": len(rulers),
        "before": _summary(before),
        "after": _summary(after),
        "status_transitions": dict(sorted(transitions.items())),
        "resolved_mentions_moved_to_a_different_king": moved,
        "kings": {
            king: {
                "mentions_before": dict(sorted(v["before"].items())),
                "mentions_after": dict(sorted(v["after"].items())),
                "artifacts_before": {k: len(s) for k, s in sorted(v["before_artifacts"].items())},
                "artifacts_after": {k: len(s) for k, s in sorted(v["after_artifacts"].items())},
            }
            for king, v in per_king.items()
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps(result["kings"], indent=2))
    print("moved:", moved, "| transitions:", result["status_transitions"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
