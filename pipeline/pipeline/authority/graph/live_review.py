"""Runnable live stage-2 reviewer demo.

    uv run python -m pipeline.authority.graph.live_review

Requires ANTHROPIC_API_KEY. Builds the Leprohon+Beckerath graph, runs the LIVE
Anthropic reviewer over the 11 deterministic candidates, prints each verdict and
any human-escalations, then reports the gated same_entity_as shortcut count.
"""

from __future__ import annotations

import os
import sys

from .poc import build_poc_graph_live, summarize
from .verdicts import SAME_ENTITY_AS, tip_verdict, verdict_outcome


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "ANTHROPIC_API_KEY is not set — the live stage-2 reviewer cannot run.\n"
            "Add it to the environment (the Claude Code OAuth proxy is not exposed\n"
            "to the SDK), then re-run. No silent fallback (Constitutional rule 2).",
            file=sys.stderr,
        )
        return 2

    graph, verdicts, escalations = build_poc_graph_live()
    print("=== live stage-2 reviewer verdicts ===")
    for vid in verdicts:
        # vid == f"verdict::{candidate}"; recover the candidate id.
        candidate = vid[len("verdict::"):]
        tip = tip_verdict(graph, candidate)
        print(f"  {candidate}  →  {verdict_outcome(graph, tip)}")
    if escalations:
        print(f"\n=== escalated to human curator ({len(escalations)}) ===")
        for cid in escalations:
            print(f"  {cid}")
    print("\n=== summary ===")
    for k, v in summarize(graph).items():
        print(f"  {k}: {v}")
    print(f"  approved same_entity_as shortcuts: {len(graph.edges_with_predicate(SAME_ENTITY_AS))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
