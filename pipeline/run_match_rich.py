"""Retry the LLM match with RICH context (ADR-020 §6) and compare to name-only.

Re-runs the Leprohon×Beckerath constraint-narrowed pick passing the full
structured record (dynasty, reign dates, throne name/prenomen, variants, source)
instead of the display name alone, persists the edges (rule 13: disk-evaluable),
and scores precision/recall vs Wikidata silver against the name-only baseline.

~395 Opus calls. Persists match_rich_edges.json + match_rich_result.json.
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
    transient_sdk_errors,
)
from pipeline.authority.graph.poc import guarded_same_entity_clusters
from pipeline.authority.graph.verdicts import emit_shortcuts

_GRAPH_DIR = Path(__file__).resolve().parent / "pipeline" / "authority" / "graph"
errors: list[dict] = []
_TRANSIENT = transient_sdk_errors()


def resilient(left, rights):
    for a in range(4):
        try:
            return _default_pick(left, rights)
        except _TRANSIENT as exc:  # only flaky network/rate-limit/5xx; bugs propagate (Rule 2)
            if a == 3:
                errors.append({"left": left["ruler_id"], "error": f"{type(exc).__name__}: {exc}"})
                return {"choice": None, "escalate": False, "reasoning": "ERROR"}
            time.sleep(2 ** a)


def main() -> None:
    g = load_poc_graph()
    narrowed = narrowed_sets(g, left="leprohon", right="beckerath")
    cand = generate_candidates(g, narrowed)
    matches, escalations = review_narrowed(g, cand, pick_fn=resilient, rich_context=True)
    emit_shortcuts(g)

    write_same_entity_edges(g, _GRAPH_DIR / "match_rich_edges.json")
    clusters, conflicts = guarded_same_entity_clusters(g)
    result = {
        "calls": len(narrowed),
        "errors": len(errors),
        "matches": len(matches),
        "escalations": len(escalations),
        "unguarded": evaluate(g),
        "guarded": {**evaluate(g, clusters=clusters), "conflicts_held_apart": len(conflicts)},
    }
    (_GRAPH_DIR / "match_rich_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"DONE. calls={len(narrowed)} matches={len(matches)} escalations={len(escalations)} errors={len(errors)}")
    print("  RICH unguarded pairwise:", result["unguarded"]["pairwise"])
    print("  RICH guarded   pairwise:", result["guarded"]["pairwise"])
    print("  (name-only baseline was: unguarded P0.92/R0.89, guarded P0.98/R0.89)")


if __name__ == "__main__":
    main()
