"""De-leaked A/B: name-only vs rich context, full Leprohon×Beckerath.

Both arms use the de-leaked prompt (no ids, no named answer pairs, shuffled
opaque labels). Isolates the effect of rich structured context (dynasty, reign,
throne name/prenomen) under zero leakage. Persists edges per arm (rule 13:
disk-evaluable) and scores precision/recall vs Wikidata silver, unguarded and
guarded. ~790 Opus calls.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from pipeline.authority.graph.benchmark.evaluate import evaluate
from pipeline.authority.graph.benchmark.persist import write_same_entity_edges
from pipeline.authority.graph.loader import load_poc_graph
from pipeline.authority.graph.matcher.constraint_narrowed import (
    _default_pick,
    generate_candidates,
    narrowed_sets,
    review_narrowed,
)
from pipeline.authority.graph.poc import guarded_same_entity_clusters
from pipeline.authority.graph.verdicts import emit_shortcuts

_GRAPH_DIR = Path(__file__).resolve().parent / "pipeline" / "authority" / "graph"


def _resilient(errors):
    def pick(left, rights):
        for a in range(4):
            try:
                return _default_pick(left, rights)
            except Exception as exc:  # noqa: BLE001 - measurement resilience, recorded
                if a == 3:
                    errors.append(str(exc)[:80])
                    return {"choice": None, "escalate": False, "reasoning": "ERROR"}
                time.sleep(2 ** a)
    return pick


def _run(rich: bool, tag: str) -> dict:
    errors: list[str] = []
    g = load_poc_graph()
    narrowed = narrowed_sets(g, left="leprohon", right="beckerath")
    cand = generate_candidates(g, narrowed)
    matches, escalations = review_narrowed(
        g, cand, pick_fn=_resilient(errors), rich_context=rich, run_id=f"cn_{tag}"
    )
    emit_shortcuts(g)
    write_same_entity_edges(g, _GRAPH_DIR / f"match_{tag}_edges.json")
    clusters, conflicts = guarded_same_entity_clusters(g)
    return {
        "calls": len(narrowed), "matches": len(matches),
        "escalations": len(escalations), "errors": len(errors),
        "unguarded": evaluate(g),
        "guarded": {**evaluate(g, clusters=clusters), "conflicts_held_apart": len(conflicts)},
    }


def main() -> None:
    results = {"name_only_clean": _run(False, "nameonly_clean"),
               "rich_clean": _run(True, "rich_clean")}
    (_GRAPH_DIR / "ab_clean_result.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    for tag, r in results.items():
        print(f"=== {tag}: matches={r['matches']} escalations={r['escalations']} errors={r['errors']} ===")
        print("  unguarded:", r["unguarded"]["pairwise"])
        print("  guarded  :", r["guarded"]["pairwise"])
    print("(leaky-prompt numbers were P0.92/R0.89 unguarded, P0.98/R0.89 guarded — not comparable)")


if __name__ == "__main__":
    main()
