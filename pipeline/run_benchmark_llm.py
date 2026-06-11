"""LLM-matcher precision/recall vs the Wikidata silver standard (ADR-020).

Builds the exact 3-way base, then runs the constraint-narrowed LLM pick for the
Kitchen pairs over the TIP dynasties (21-25), and evaluates the resulting clusters
against Wikidata. End-to-end metrics (abstained/unresolved gold links count as
FN). Compares against the exact-only baseline and prints the false merges (e.g.
Pinudjem I / Menkheperre) and the recovered cross-spelling matches.
"""

from __future__ import annotations

import json
import time

from pipeline.authority.graph.benchmark.evaluate import evaluate
from pipeline.authority.graph.loader import load_poc_graph_3way
from pipeline.authority.graph.matcher.constraint_narrowed import (
    _default_pick,
    generate_candidates,
    narrowed_sets,
    review_narrowed,
    transient_sdk_errors,
)
from pipeline.authority.graph.matcher.stage1_deterministic import run_stage1_matcher
from pipeline.authority.graph.poc import approve_candidates_via_curator
from pipeline.authority.graph.verdicts import emit_shortcuts

TIP = [21, 22, 23, 24, 25]
_TRANSIENT = transient_sdk_errors()


def resilient(left, rights):
    for a in range(4):
        try:
            return _default_pick(left, rights)
        except _TRANSIENT:  # only flaky network/rate-limit/5xx; bugs propagate (Rule 2)
            if a == 3:
                return {"choice": None, "escalate": False, "reasoning": "ERROR"}
            time.sleep(2 ** a)


def build_llm_graph():
    g = load_poc_graph_3way()
    exact = []
    for left, right, rid in [("leprohon", "beckerath", "ex_lb"),
                             ("leprohon", "kitchen", "ex_lk"),
                             ("beckerath", "kitchen", "ex_bk")]:
        exact += run_stage1_matcher(g, left_source=left, right_source=right, run_id=rid)
    approve_candidates_via_curator(g, exact)
    calls = 0
    for left, right, rid in [("kitchen", "leprohon", "cn_kl"), ("kitchen", "beckerath", "cn_kb")]:
        merged = {}
        for d in TIP:
            merged.update(narrowed_sets(g, left=left, right=right, dynasty=d))
        calls += len(merged)
        cand = generate_candidates(g, merged, run_id=f"{rid}_gen")
        review_narrowed(g, cand, pick_fn=resilient, run_id=rid)
    emit_shortcuts(g)
    return g, calls


def main() -> None:
    g, calls = build_llm_graph()
    res = evaluate(g)
    res["llm_pick_calls"] = calls
    with open("/tmp/benchmark_llm.json", "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print(f"DONE. llm_calls={calls} aligned={res['aligned']}")
    print("  pairwise:", res["pairwise"])
    print("  b-cubed :", res["bcubed"])
    print(f"  false merges ({len(res['false_merges'])}):")
    for fm in res["false_merges"]:
        print("     FP:", fm)
    print(f"  missed pairs: {len(res['missed_pairs'])} (sample)")
    for mp in res["missed_pairs"][:6]:
        print("     FN:", mp)


if __name__ == "__main__":
    main()
