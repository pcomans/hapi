"""Issue #342: every candidate the era gate rejects that the claim graph #337 registered had
approved or escalated — the complete set of queue entries the gate removes, for review.

Deterministic, no model calls: candidates come from the committed sources through the
current matcher; the previous queue is the claim graph at the #337 registered commit.

    pipeline/.venv/bin/python docs/evaluations/ruler-cluster-reconciliation-342/scripts/list_era_rejected.py \
      --out docs/evaluations/ruler-cluster-reconciliation-342/results/era-rejected-previously-queued.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "pipeline"))

from pipeline.authority.claimgraph.build_graph import AUTHORITY_ROOT  # noqa: E402
from pipeline.authority.claimgraph.matcher import generate_candidates  # noqa: E402
from pipeline.authority.claimgraph.sources import load_all_sources  # noqa: E402

# The commit #337's frozen current-authority arm was registered against
# (docs/evaluations/authority-independent-control-2026-09-13/scripts/compare_arms.py).
REGISTERED_BASE_COMMIT = "97f2e610974f0e89b9c03d409b230dff89edbb1f"


def previous_queue(root: Path = ROOT) -> dict[str, str]:
    graph = json.loads(
        subprocess.run(
            ["git", "-C", str(root), "show",
             f"{REGISTERED_BASE_COMMIT}:web-claimgraph/data/claim-graph.json"],
            check=True, capture_output=True,
        ).stdout
    )
    queue = {e["candidate_id"]: "escalated" for e in graph["escalations"]}
    queue.update({e["candidate_id"]: "approved" for e in graph["approvedEdges"]})
    return queue


def era_rejected_previously_queued(root: Path = ROOT) -> list[dict]:
    records = load_all_sources(AUTHORITY_ROOT).records
    name = {r.local_id: r.display_name for r in records}
    queue = previous_queue(root)
    return [
        {
            "candidate_id": c.id,
            "previously": queue[c.id],
            "a": f"{c.a_id} ({name[c.a_id]})",
            "b": f"{c.b_id} ({name[c.b_id]})",
            "basis": c.basis,
            "era_conflict": c.era_conflict,
        }
        for c in generate_candidates(records)
        if c.era_conflict and c.id in queue
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rows = era_rejected_previously_queued()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"registered_base_commit": REGISTERED_BASE_COMMIT, "pairs": rows},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    by = {}
    for r in rows:
        by[(r["previously"], r["basis"])] = by.get((r["previously"], r["basis"]), 0) + 1
    print(len(rows), by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
