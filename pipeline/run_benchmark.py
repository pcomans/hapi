"""Reproducible matcher benchmark vs the Wikidata silver standard (ADR-020).

NO API calls: evaluates matcher outputs already persisted on disk.
- Exact matcher: rebuilt deterministically (build_3way_graph, no API).
- LLM matcher: reconstructed from the committed match_rate_result.json match_list
  (node ids) — the 395-call leprohon×beckerath run we already paid for.

Writes benchmark_results.json. Re-running the LLM matcher itself is unnecessary
for evaluation; persist the matcher's edges and evaluate them from disk.
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.authority.graph.benchmark.evaluate import evaluate
from pipeline.authority.graph.loader import load_poc_graph
from pipeline.authority.graph.poc import build_3way_graph

_GRAPH_DIR = Path(__file__).resolve().parent / "pipeline" / "authority" / "graph"
# Canonical clean (de-leaked) LB matcher output, persisted by run_ab_clean.py.
_LB_EDGES = _GRAPH_DIR / "match_nameonly_clean_edges.json"
_OUT = _GRAPH_DIR / "benchmark_results.json"


def _llm_lb_graph():
    """Rebuild the LB LLM matcher's predictions from the persisted clean edges.

    Reads the de-leaked run's edge records (rule 13: never re-run to score).
    """
    from pipeline.authority.graph.benchmark.persist import load_same_entity_edges

    g = load_poc_graph()
    records = json.loads(_LB_EDGES.read_text())
    load_same_entity_edges(g, records)
    return g


def main() -> None:
    from pipeline.authority.graph.poc import guarded_same_entity_clusters

    lb = _llm_lb_graph()
    clusters, conflicts = guarded_same_entity_clusters(lb)
    guarded = evaluate(lb, clusters=clusters)
    guarded["conflicts_held_apart"] = len(conflicts)

    results = {
        "exact_3way": evaluate(build_3way_graph()),
        "llm_leprohon_beckerath": evaluate(_llm_lb_graph()),
        "llm_leprohon_beckerath_guarded": guarded,
    }
    _OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    for name, ev in results.items():
        print(f"=== {name} (aligned {ev['aligned']}) ===")
        print("  pairwise:", ev["pairwise"])
        print("  b-cubed :", ev["bcubed"])
        print(f"  false merges: {len(ev['false_merges'])}  missed: {len(ev['missed_pairs'])}")
    print(f"\nwrote {_OUT.name}")


if __name__ == "__main__":
    main()
