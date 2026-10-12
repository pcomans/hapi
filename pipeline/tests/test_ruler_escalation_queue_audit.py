"""The committed escalation-queue audit is bound to the graph, matcher and script it describes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs/evaluations/ruler-escalation-queue"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_audit_is_bound_to_the_committed_graph_matcher_and_script() -> None:
    result = json.loads((AUDIT / "results/escalation-queue.json").read_text())
    assert result["inputs"]["graph_sha256"] == _sha(ROOT / "web-claimgraph/data/claim-graph.json")
    assert result["inputs"]["matcher_sha256"] == _sha(
        ROOT / "pipeline/pipeline/authority/claimgraph/matcher.py"
    )
    assert result["inputs"]["script_sha256"] == _sha(AUDIT / "scripts/audit_escalations.py")
    graph = json.loads((ROOT / "web-claimgraph/data/claim-graph.json").read_text())
    assert result["escalations"] == len(graph["escalations"]) == 974
    assert result["by_park_reason"] == {
        "homonym_list": 77, "name_only": 735, "reviewer_escalated": 46, "uniqueness_clash": 116,
    }
    assert result["ruler_mentions"] == 11_555
    assert result["ambiguous_mentions"] == 689
    assert sum(s["mentions"] for s in result["ambiguous_target_sets"]) == 689
    top = result["ambiguous_target_sets"][0]
    assert (top["labels"], top["mentions"]) == (["Psusennes I", "Psusennes I"], 309)
    assert top["parked_pairs_between_targets"] == [
        {"candidate": "cand-kitchen-21.03|pharaoh_se-Psusennes-I", "park_reason": "name_only"}
    ]
