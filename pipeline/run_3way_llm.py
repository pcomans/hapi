"""One-off: LLM 3-way clustering over the TIP dynasties (Leprohon+Beckerath+Kitchen).

Builds the exact 3-way base, then runs the constraint-narrowed LLM pick for the
Kitchen pairs (kitchen×leprohon, kitchen×beckerath) over the Third-Intermediate-
Period dynasties (21-25), where cross-spelling (Takeloth/Takelot, Shoshenq/
Schoschenq) defeats the exact matcher. Re-clusters and reports how many 3-source
clusters emerge vs the exact-only baseline (2). Writes /tmp/threeway_llm.json.
"""

from __future__ import annotations

import json
import time

from pipeline.authority.graph.loader import load_poc_graph_3way
from pipeline.authority.graph.matcher.constraint_narrowed import (
    _default_pick,
    generate_candidates,
    narrowed_sets,
    review_narrowed,
    transient_sdk_errors,
)
from pipeline.authority.graph.matcher.stage1_deterministic import run_stage1_matcher
from pipeline.authority.graph.poc import approve_candidates_via_curator, same_entity_clusters
from pipeline.authority.graph.verdicts import emit_shortcuts

TIP_DYNASTIES = [21, 22, 23, 24, 25]
errors: list[dict] = []
_TRANSIENT = transient_sdk_errors()


def resilient_pick(left, rights):
    for attempt in range(4):
        try:
            return _default_pick(left, rights)
        except _TRANSIENT as exc:  # only flaky network/rate-limit/5xx; bugs propagate (Rule 2)
            if attempt == 3:
                errors.append({"left": left["ruler_id"], "error": f"{type(exc).__name__}: {exc}"})
                return {"choice": None, "escalate": False, "reasoning": f"ERROR: {exc}"}
            time.sleep(2 ** attempt)


def main() -> None:
    g = load_poc_graph_3way()

    # Exact base across all three pairs (catches Osorkon I/II 3-way).
    exact = []
    for left, right, rid in [
        ("leprohon", "beckerath", "ex_lb"),
        ("leprohon", "kitchen", "ex_lk"),
        ("beckerath", "kitchen", "ex_bk"),
    ]:
        exact += run_stage1_matcher(g, left_source=left, right_source=right, run_id=rid)
    approve_candidates_via_curator(g, exact)

    # LLM constraint-narrowed pick for the Kitchen pairs over the TIP dynasties.
    llm_calls = 0
    for left, right, rid in [("kitchen", "leprohon", "cn_kl"), ("kitchen", "beckerath", "cn_kb")]:
        merged: dict[str, list[str]] = {}
        for d in TIP_DYNASTIES:
            merged.update(narrowed_sets(g, left=left, right=right, dynasty=d))
        llm_calls += len(merged)
        cand_map = generate_candidates(g, merged, run_id=f"{rid}_gen")
        review_narrowed(g, cand_map, pick_fn=resilient_pick, run_id=rid)

    emit_shortcuts(g)
    clusters = same_entity_clusters(g)
    threeway = [c for c in clusters if len({m.split("::")[0] for m in c}) == 3]

    def disp(rid):
        try:
            return g.node(f"appellation::{rid}::display_name").props["symbolic_content"]
        except KeyError:
            return "?"

    result = {
        "llm_pick_calls": llm_calls,
        "errors": len(errors),
        "total_clusters": len(clusters),
        "three_source_clusters": len(threeway),
        "three_source_list": [
            sorted(f"{m.split('::')[0]}:{disp(m)}" for m in c) for c in threeway
        ],
    }
    with open("/tmp/threeway_llm.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    # Persist the same_entity_as edges (subject/object/outcome/reasoning) so this
    # run is disk-evaluable — never re-run the LLM just to score it (ADR-020).
    from pathlib import Path
    from pipeline.authority.graph.benchmark.persist import write_same_entity_edges
    edges_path = Path(__file__).resolve().parent / "pipeline" / "authority" / "graph" / "threeway_edges.json"
    n_edges = write_same_entity_edges(g, edges_path)
    print(f"DONE. llm_calls={llm_calls} errors={len(errors)} "
          f"3-source clusters={len(threeway)} (exact-only baseline was 2); "
          f"persisted {n_edges} same_entity_as edge records -> {edges_path.name}")
    for c in result["three_source_list"]:
        print("  " + "  |  ".join(c))


if __name__ == "__main__":
    main()
