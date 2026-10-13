"""The committed escalation-queue audit and rebuild measurement are bound to the graph,
matcher, scripts and runs they describe."""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs/evaluations/ruler-escalation-queue"
GRAPH = ROOT / "web-claimgraph/data/claim-graph.json"
# main before the queue was worked off (the audit at a4ab486 describes this graph).
BEFORE_COMMIT = "9402974"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _before_graph_sha() -> str:
    graph = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{BEFORE_COMMIT}:web-claimgraph/data/claim-graph.json"],
        check=True, capture_output=True,
    ).stdout
    return hashlib.sha256(graph).hexdigest()


def test_audit_is_bound_to_the_committed_graph_matcher_and_script() -> None:
    result = json.loads((AUDIT / "results/escalation-queue.json").read_text())
    assert result["inputs"]["graph_sha256"] == _sha(GRAPH)
    assert result["inputs"]["matcher_sha256"] == _sha(
        ROOT / "pipeline/pipeline/authority/claimgraph/matcher.py"
    )
    assert result["inputs"]["script_sha256"] == _sha(AUDIT / "scripts/audit_escalations.py")
    graph = json.loads(GRAPH.read_text())
    assert result["escalations"] == len(graph["escalations"]) == 890
    assert result["by_park_reason"] == {
        "homonym_list": 79, "king_name_route": 7, "name_only": 544, "reviewer_escalated": 139,
        "uncertain_reading": 1, "uniqueness_clash": 120,
    }
    assert result["ruler_mentions"] == 11_555
    assert result["ambiguous_mentions"] == 62
    assert sum(s["mentions"] for s in result["ambiguous_target_sets"]) == 62
    top = result["ambiguous_target_sets"][0]
    assert (top["labels"], top["mentions"]) == (["Djoser", "Netjerikhet/Djoser"], 48)
    assert top["parked_pairs_between_targets"] == [
        {"candidate": "cand-beckerath-03.02|leprohon-leprohon-3.01", "park_reason": "reviewer_escalated"},
        {"candidate": "cand-beckerath-03.02|pharaoh_se-Djoser", "park_reason": "reviewer_escalated"},
    ]


def test_rebuild_measurement_is_bound_to_the_committed_graph_and_script() -> None:
    result = json.loads((AUDIT / "results/rebuild.json").read_text())
    assert result["inputs"]["after_graph_sha256"] == _sha(GRAPH)
    assert result["inputs"]["before_graph_sha256"] == _before_graph_sha()
    assert result["inputs"]["script_sha256"] == _sha(AUDIT / "scripts/measure_rebuild.py")
    assert result["before"]["mentions_by_status"] == {
        "abstained": 2241, "ambiguous": 689, "resolved": 8279, "unmatched": 346,
    }
    assert result["after"]["mentions_by_status"] == {
        "abstained": 2241, "ambiguous": 62, "resolved": 8906, "unmatched": 346,
    }
    assert result["status_transitions"] == {
        "abstained->abstained": 2241, "ambiguous->ambiguous": 62, "ambiguous->resolved": 627,
        "resolved->resolved": 8279, "unmatched->unmatched": 346,
    }
    assert result["resolved_mentions_moved_to_a_different_king"] == 0
    assert len(result["merged_clusters"]) == 51
    assert result["approved_links_gained_by_basis"] == {"horus": 14, "name_dynasty": 55, "prenomen": 10}
    assert [(r["a"], r["b"]) for r in result["approved_links_lost"]] == [
        ("leprohon-leprohon-17.26 (Senakhtenre Ahmose (I))", "ryholt-17.7 (Siamun (?))"),
        ("leprohon-leprohon-17.27 (Seqenenre Tao)", "ryholt-17.8 (Tao)"),
        ("pharaoh_se-Senakhtenra (Senakhtenra)", "ryholt-17.7 (Siamun (?))"),
        ("pharaoh_se-Seqenenra (Seqenenra)", "ryholt-17.8 (Tao)"),
    ]
    assert all(isinstance(r["now"], dict) and set(r["now"]) == {"escalated"} for r in result["approved_links_lost"])


def test_the_distinct_shoshenq_iv_kings_stay_apart() -> None:
    """Beckerath's Schoschenq IV (Usermaatre) and pharaoh.se's Shoshenq IV (Hedjkheperre)
    share a name, numeral and dynasty but are different kings (code review P1-3)."""
    graph = json.loads(GRAPH.read_text())
    cluster_of = {m: c["id"] for c in graph["clusters"] for m in c["member_ids"]}
    a, b = "beckerath-22.14", "pharaoh_se-Shoshenq-IV"
    assert cluster_of.get(a, a) != cluster_of.get(b, b)


def test_the_discarded_first_rebuild_is_bound_to_its_archived_graph() -> None:
    archive = AUDIT / "results/discarded-round-3"
    result = json.loads((archive / "rebuild.json").read_text())
    graph = gzip.decompress((archive / "claim-graph.json.gz").read_bytes())
    assert result["inputs"]["after_graph_sha256"] == hashlib.sha256(graph).hexdigest()
    assert result["inputs"]["before_graph_sha256"] == _before_graph_sha()
    assert result["inputs"]["script_sha256"] == _sha(AUDIT / "scripts/measure_rebuild.py")
    assert len(result["approved_links_lost"]) == 97
    assert result["after"]["mentions_by_status"]["ambiguous"] == 65
    run = [json.loads(line) for line in
           gzip.decompress((archive / "claim-graph.reviewer-run.jsonl.gz").read_bytes()).splitlines()]
    assert len(run) == 2208
    approved = {r["candidate_id"] for r in run if r["outcome"] == "hapi:verdict_approved"}
    edges = json.loads(graph)["approvedEdges"]
    assert len(edges) == len(approved) == 327
    assert {e["candidate_id"] for e in edges} == approved


def test_the_aborted_attempts_belong_to_the_committed_run() -> None:
    """The timed-out attempts of the aborted rebuild were sent with the prompts the committed
    run used for the same candidate, which was then reviewed on resume."""
    aborted = [json.loads(line) for line in
               (AUDIT / "results/aborted-attempts-2026-10-12.jsonl").read_text().splitlines()]
    run = {}
    for line in (ROOT / "web-claimgraph/data/claim-graph.reviewer-run.jsonl").read_text().splitlines():
        r = json.loads(line)
        run[r["candidate_id"]] = r
    assert [a["candidate_id"] for a in aborted] == ["cand-leprohon-leprohon-13.06|ryholt-13.10"]
    for a in aborted:
        assert a["aborted"] is True and len(a["interactions"]) == 3
        done = run[a["candidate_id"]]["interactions"][-1]
        for attempt in a["interactions"]:
            assert attempt["raw_response"] is None and "timed out" in attempt["call_error"]
            assert (attempt["system_prompt"], attempt["user_prompt"]) == (
                done["system_prompt"], done["user_prompt"]
            )


def test_the_measured_dyn_21_24_exclusion_is_bound_to_its_archived_graph() -> None:
    """ADR-020 amendment 2026-10-12 item 1: excluding Dyn 21–24 from `name_dynasty` was
    measured (same run, matcher with `NAME_DYNASTY_EXCLUDED_BANDS = ((13, 17), (21, 24))`)
    and not adopted: 312 more ambiguous mentions."""
    archive = AUDIT / "results/alternative-exclude-dyn-21-24"
    result = json.loads((archive / "rebuild.json").read_text())
    graph = gzip.decompress((archive / "claim-graph.json.gz").read_bytes())
    assert result["inputs"]["after_graph_sha256"] == hashlib.sha256(graph).hexdigest()
    assert result["inputs"]["before_graph_sha256"] == _before_graph_sha()
    assert result["inputs"]["script_sha256"] == _sha(AUDIT / "scripts/measure_rebuild.py")
    adopted = json.loads((AUDIT / "results/rebuild.json").read_text())
    assert (result["after"]["mentions_by_status"]["ambiguous"]
            - adopted["after"]["mentions_by_status"]["ambiguous"]) == 374 - 62 == 312
    assert result["still_ambiguous_by_targets"]["Psusennes I | Psusennes I"] == 309


def test_every_approved_link_was_in_the_reviewed_graph() -> None:
    """The egyptologist merge review (results/merge-review.md) covered the graph before the
    code-review guards; the guards only remove approvals, never add one."""
    review = json.loads((AUDIT / "results/merge-review.json").read_text())
    reviewed = set(review["reviewed_approved_candidates"])
    assert len(reviewed) == review["reviewed_graph_approved_links"] == 438
    approved = {e["candidate_id"] for e in json.loads(GRAPH.read_text())["approvedEdges"]}
    assert len(approved) == 429
    assert approved <= reviewed


def test_the_reviewed_run_is_archived_and_holds_the_reviewed_approvals() -> None:
    review = json.loads((AUDIT / "results/merge-review.json").read_text())
    run_bytes = gzip.decompress((AUDIT / "results" / review["reviewed_run"]).read_bytes())
    assert hashlib.sha256(run_bytes).hexdigest() == review["reviewed_run_sha256"]
    approved = {
        r["candidate_id"] for r in map(json.loads, run_bytes.splitlines())
        if r["outcome"] == "hapi:verdict_approved"
    }
    assert approved == set(review["reviewed_approved_candidates"])


def test_every_paid_verdict_is_committed() -> None:
    """Each reviewer verdict paid for is in the committed run, or (13) archived because the
    final matcher calls the pair name-only and settles it without the reviewer."""
    run = {json.loads(line)["candidate_id"]: json.loads(line)
           for line in (ROOT / "web-claimgraph/data/claim-graph.reviewer-run.jsonl").read_text().splitlines()}
    superseded = [json.loads(line) for line in
                  (AUDIT / "results/superseded-by-name-only.jsonl").read_text().splitlines()]
    assert len(superseded) == 13
    for v in superseded:
        assert v["reviewer"] == "llm" and v["interactions"]
        assert run[v["candidate_id"]]["reviewer"] == "deterministic"
        assert run[v["candidate_id"]]["reason"].startswith("Name-only match")
    llm = {cid for cid, r in run.items() if r["reviewer"] == "llm"}
    assert len(llm) + len(superseded) == 1229
