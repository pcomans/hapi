"""One-off measurement: full cross-source match rate via constraint-narrowing + LLM pick.

Not part of the POC package — a measurement harness. Runs ~395 LLM pick calls
(one per Leprohon ruler in a shared dynasty), each choosing its match from the
same-dynasty Beckerath set, then reports the match rate and writes the full
result to /tmp/match_rate_result.json.

Per-call resilience (retry then record-as-error) is intentional for a long
measurement run; it is NOT a silent fallback in an authority-data path.
"""

from __future__ import annotations

import json
import time

from pipeline.authority.graph.loader import load_poc_graph
from pipeline.authority.graph.matcher.constraint_narrowed import (
    _default_pick,
    generate_candidates,
    narrowed_sets,
    review_narrowed,
)

RESULT_PATH = "/tmp/match_rate_result.json"
errors: list[dict] = []


def resilient_pick(left, rights):
    for attempt in range(3):
        try:
            return _default_pick(left, rights)
        except Exception as exc:  # noqa: BLE001 - measurement resilience, recorded not swallowed
            if attempt == 2:
                errors.append({"left": left["ruler_id"], "error": f"{type(exc).__name__}: {exc}"})
                return {"choice": None, "escalate": False, "reasoning": f"ERROR: {exc}"}
            time.sleep(2 ** attempt)


def main() -> None:
    g = load_poc_graph()
    narrowed = narrowed_sets(g)
    leprohon_total = len(narrowed)
    cand_map = generate_candidates(g, narrowed)
    matches, escalations = review_narrowed(g, cand_map, pick_fn=resilient_pick)

    def disp(rid):
        try:
            return g.node(f"appellation::{rid}::display_name").props["symbolic_content"]
        except KeyError:
            return "?"

    distinct_beckerath = {r for _, r in matches}
    beckerath_total = len([
        n for n in g.nodes_of_class("E21") if n.props.get("source") == "beckerath"
    ])
    result = {
        "leprohon_rulers_in_shared_dynasty": leprohon_total,
        "beckerath_rulers": beckerath_total,
        "matches": len(matches),
        "escalated": len(escalations),
        "distinct_beckerath_matched": len(distinct_beckerath),
        "leprohon_match_rate_pct": round(100 * len(matches) / leprohon_total, 1),
        "beckerath_coverage_pct": round(100 * len(distinct_beckerath) / beckerath_total, 1),
        "errors": errors,
        "escalations": escalations,
        "match_list": [{"leprohon": disp(l), "beckerath": disp(r), "lid": l, "rid": r} for l, r in matches],
    }
    with open(RESULT_PATH, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"DONE. matches={result['matches']}/{leprohon_total} "
          f"({result['leprohon_match_rate_pct']}% of Leprohon), "
          f"Beckerath coverage {result['distinct_beckerath_matched']}/{beckerath_total} "
          f"({result['beckerath_coverage_pct']}%), errors={len(errors)}")
    print(f"Full result: {RESULT_PATH}")


if __name__ == "__main__":
    main()
