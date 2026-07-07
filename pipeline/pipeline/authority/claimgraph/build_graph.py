"""Build-time pipeline: authority reconciled.jsonl → source-attributed claim graph →
best-effort cross-source matcher (LIVE Anthropic reviewer) → gated identity links →
committed JSON artifact consumed by the web-claimgraph Next.js app.

Run (from pipeline/):
    uv run python -m pipeline.authority.claimgraph.build_graph              # live reviewer
    uv run python -m pipeline.authority.claimgraph.build_graph --limit 8    # thin-slice
    uv run python -m pipeline.authority.claimgraph.build_graph --deterministic  # explicit

The live reviewer is REQUIRED by default. If ANTHROPIC_API_KEY is missing the build STOPS
loudly rather than silently falling back (that would ship a compromised graph). The
emitted claim-graph.json is the only thing the deployed app reads — no runtime API key.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from dataclasses import asdict
from pathlib import Path

from .clusters import compute_clusters
from .graph_ir import build_documentary_graph
from .sources import SOURCE_LABEL, load_all_sources
from .verdicts import resolve_matches

REPO_ROOT = Path(__file__).resolve().parents[4]
AUTHORITY_ROOT = REPO_ROOT / "pipeline" / "pipeline" / "authority" / "sources"
WEB_DATA_DIR = REPO_ROOT / "web-claimgraph" / "data"


def load_env_local() -> None:
    """Load a gitignored .env.local (pipeline/ or web-claimgraph/) into os.environ so the
    key never has to pass through the command line or an agent transcript."""
    for env_path in (REPO_ROOT / "pipeline" / ".env.local", WEB_DATA_DIR.parent / ".env.local"):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip().strip('"').strip("'")
            os.environ.setdefault(key, val)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deterministic", action="store_true",
                    help="explicitly use the deterministic policy instead of the live reviewer")
    ap.add_argument("--provider", choices=("anthropic", "openrouter"), default="anthropic",
                    help="live-reviewer backend: anthropic (ANTHROPIC_API_KEY) or "
                         "openrouter (OPENROUTER_API_KEY, e.g. GLM 5.2)")
    ap.add_argument("--model", default=None,
                    help="reviewer model id; defaults per provider "
                         "(claude-sonnet-5 / z-ai/glm-5.2)")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--limit", type=int, default=None,
                    help="cap candidates reviewed (thin-slice validation)")
    ap.add_argument("--out", default=str(WEB_DATA_DIR / "claim-graph.json"))
    ap.add_argument("--fresh", action="store_true",
                    help="ignore/clear the resumable verdict cache and re-review from scratch")
    args = ap.parse_args()

    load_env_local()
    mode = "deterministic" if args.deterministic else "llm"
    provider = args.provider
    model = args.model or (
        "z-ai/glm-5.2" if provider == "openrouter" else "claude-sonnet-5"
    )
    key_env = "OPENROUTER_API_KEY" if provider == "openrouter" else "ANTHROPIC_API_KEY"

    if mode == "llm" and not os.environ.get(key_env):
        sys.stderr.write(
            "\n  ✋ STOP — cannot build the claim graph.\n\n"
            f"  The live reviewer ({provider}) is the matcher, and {key_env} is not set.\n"
            "  Refusing to silently fall back to the deterministic policy (that would ship a\n"
            "  compromised graph).\n\n"
            "  Fix: put the key in pipeline/.env.local (gitignored):\n"
            f"      echo '{key_env}=...' > pipeline/.env.local\n"
            "  then re-run:\n"
            "      uv run python -m pipeline.authority.claimgraph.build_graph\n\n"
            "  (Only if you deliberately want the deterministic-only artifact, add\n"
            "   --deterministic — it will be labelled reviewer=deterministic.)\n\n"
        )
        return 2

    client = None
    api_key = None
    if mode == "llm":
        if provider == "openrouter":
            api_key = os.environ[key_env]
        else:
            from anthropic import Anthropic  # lazy so deterministic mode needs no dep

            client = Anthropic()

    print(f"[build-graph] authority root: {AUTHORITY_ROOT}")
    print(
        f"[build-graph] reviewer: "
        f"{f'LIVE {provider} reviewer ({model})' if mode == 'llm' else 'DETERMINISTIC (--deterministic)'}"
    )

    load = load_all_sources(AUTHORITY_ROOT)
    print(f"[build-graph] loaded {len(load.records)} ruler records: {load.per_source}")

    doc = build_documentary_graph(load.records)
    print(
        f"[build-graph] documentary graph: {len(doc.rulers)} rulers, "
        f"{len(doc.claims)} claims, {len(doc.intra_source_identities)} intra-source identities"
    )

    last = {"pct": -1}
    plock = threading.Lock()

    def on_progress(done: int, total: int) -> None:
        pct = int(done / total * 100) if total else 100
        with plock:
            if pct != last["pct"] and (pct % 10 == 0 or done == total):
                print(f"[build-graph] reviewing candidates: {pct}% ({done}/{total})")
                last["pct"] = pct

    cache_path = args.out + ".verdict-cache.jsonl"
    if args.fresh and os.path.exists(cache_path):
        os.remove(cache_path)
        print(f"[build-graph] --fresh: cleared verdict cache {cache_path}")
    if mode == "llm" and os.path.exists(cache_path):
        n = sum(1 for _ in open(cache_path, encoding="utf-8"))
        print(f"[build-graph] resuming: {n} verdicts already cached at {cache_path} (will review the rest)")

    resolved = resolve_matches(
        load.records,
        mode=mode,
        client=client,
        provider=provider,
        api_key=api_key,
        model=model,
        max_workers=args.workers,
        limit=args.limit,
        cache_path=cache_path if mode == "llm" else None,
        on_progress=on_progress,
    )
    print(
        f"[build-graph] matcher: {len(resolved.candidates)} candidates → "
        f"{len(resolved.approved_edges)} approved links, {len(resolved.escalations)} escalated"
    )

    clusters = compute_clusters(doc.rulers, resolved.approved_edges)
    multi = [c for c in clusters if c.source_count > 1]
    print(f"[build-graph] identity clusters: {len(clusters)} total, {len(multi)} span >1 source")

    artifact = {
        "meta": {
            "generatedNote": "Baked at build time from committed authority sources. Do not hand-edit.",
            "reviewer": resolved.mode,
            "provider": provider if mode == "llm" else None,
            "model": model if mode == "llm" else None,
            "partial": args.limit is not None,
            "sources": {
                sid: {"label": SOURCE_LABEL.get(sid, sid), "rulers": n}
                for sid, n in load.per_source.items()
            },
            "stats": {
                "rulers": len(doc.rulers),
                "claims": len(doc.claims),
                "candidates": len(resolved.candidates),
                "approvedLinks": len(resolved.approved_edges),
                "escalations": len(resolved.escalations),
                "intraSourceIdentities": len(doc.intra_source_identities),
                "clusters": len(clusters),
                "multiSourceClusters": len(multi),
            },
        },
        "rulers": [asdict(r) for r in doc.rulers],
        "claims": [asdict(c) for c in doc.claims],
        "intraSourceIdentities": [asdict(i) for i in doc.intra_source_identities],
        "approvedEdges": [asdict(e) for e in resolved.approved_edges],
        "escalations": [asdict(e) for e in resolved.escalations],
        "clusters": [asdict(c) for c in clusters],
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[build-graph] wrote {out_path}")

    # Rule-13 reasoning capture: the full reviewer interaction (prompt + raw response +
    # model snapshot) for every verdict, written separately so the app-facing artifact
    # stays lean. This is the replayable provenance record.
    run_path = out_path.with_name(out_path.stem + ".reviewer-run.jsonl")
    with run_path.open("w", encoding="utf-8") as fh:
        for v in resolved.verdicts:
            fh.write(json.dumps(asdict(v), ensure_ascii=False) + "\n")
    print(f"[build-graph] wrote reasoning capture {run_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
