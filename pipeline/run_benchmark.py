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
from pipeline.authority.graph.ir import Edge
from pipeline.authority.graph.loader import load_poc_graph
from pipeline.authority.graph.poc import build_3way_graph

_GRAPH_DIR = Path(__file__).resolve().parent / "pipeline" / "authority" / "graph"
_LB_MATCHES = _GRAPH_DIR / "match_rate_result.json"
_OUT = _GRAPH_DIR / "benchmark_results.json"


def _llm_lb_graph():
    """Rebuild the LB LLM matcher's predictions from the persisted match_list."""
    g = load_poc_graph()
    matches = json.loads(_LB_MATCHES.read_text())["match_list"]
    for m in matches:
        g.node(m["lid"]); g.node(m["rid"])
        g.add_edge(Edge(m["lid"], "hapi:same_entity_as", m["rid"]))
    return g


def main() -> None:
    results = {
        "exact_3way": evaluate(build_3way_graph()),
        "llm_leprohon_beckerath": evaluate(_llm_lb_graph()),
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
