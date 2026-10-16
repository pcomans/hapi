#!/usr/bin/env python3
"""#337 protocol v10: before a review run, open the citable pages earlier runs' reviewers
tried, with the current `open_page` tool and no model, to find what will not load. This
registration also opens the record pages its own Stage 1 queue shows reviewers: every one of the
museums added since (Cleveland, the Walters, behind Cloudflare), and up to LOADED_PER_HOST of each
other museum's (seeded).

Pages: every citable page that failed to load in any given run's records, and up to
LOADED_PER_HOST that loaded, per host (seeded). The iDAI gazetteer's place pages are sampled
(GAZETTEER_SAMPLE): 183 of them failed in the v7 run for one reason, the `load` event. Hosts are
opened in parallel (at most PARALLEL_HOSTS), each host's pages in turn. Writes one row per page:
what `open_page` returned (no page text), or its error.

    xvfb-run -a runtime/.venv/bin/python scripts/preflight_page_check.py \\
      --records <private run dir> [<private run dir> ...] --queue <stage-1 queue> --out <json>
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import json
import random
from pathlib import Path
from urllib.parse import urlparse

import open_page_server
from review_protocol import CITABLE_SOURCES_PATH, OPEN_PAGE_SERVER_PATH, citable_source_of, sha256_path

SEED = 20261016
LOADED_PER_HOST = 3
GAZETTEER_SAMPLE = 20
PARALLEL_HOSTS = 6


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").removeprefix("www.")


def pages(run_dirs: list[Path]) -> list[str]:
    always_loaded: dict[str, bool] = {}
    for run in run_dirs:
        for path in sorted(run.glob("stage-*/*/*.attempt-*.json")):
            for opened in json.loads(path.read_text()).get("page_opens", []):
                url = opened.get("url")
                if url and citable_source_of(url):
                    always_loaded[url] = always_loaded.get(url, True) and bool(opened.get("loaded"))
    rng = random.Random(SEED)
    failed = sorted(u for u, ok in always_loaded.items() if not ok)
    gazetteer = [u for u in failed if _host(u) == "gazetteer.dainst.org"]
    chosen = [u for u in failed if u not in gazetteer] + rng.sample(gazetteer, min(GAZETTEER_SAMPLE, len(gazetteer)))
    loaded_by_host = collections.defaultdict(list)
    for url, ok in sorted(always_loaded.items()):
        if ok:
            loaded_by_host[_host(url)].append(url)
    for urls in loaded_by_host.values():
        chosen += rng.sample(urls, min(LOADED_PER_HOST, len(urls)))
    return chosen


# The hosts of the museums added since #361's run, whose record pages no earlier run opened.
ADDED_MUSEUM_HOSTS = ("clevelandart.org", "purl.thewalters.org")


def queue_pages(queue: Path) -> list[str]:
    """The record URLs the Stage 1 queue shows: all of the added museums', a seeded sample of
    the others' per host."""
    shown = sorted({url for case in json.loads(queue.read_text())["cases"] for groups in case["sides"].values()
                    for group in groups for entry in group["record_texts"] for url in entry["example_record_urls"]})
    by_host = collections.defaultdict(list)
    for url in shown:
        by_host[_host(url)].append(url)
    rng = random.Random(SEED)
    chosen = []
    for host, urls in sorted(by_host.items()):
        chosen += urls if host in ADDED_MUSEUM_HOSTS else rng.sample(urls, min(LOADED_PER_HOST, len(urls)))
    return chosen


async def check(urls: list[str]) -> list[dict]:
    by_host = collections.defaultdict(list)
    for url in urls:
        by_host[_host(url)].append(url)
    slots = asyncio.Semaphore(PARALLEL_HOSTS)
    rows: list[dict] = []

    async def host_pages(host: str, host_urls: list[str]) -> None:
        async with slots:
            for url in host_urls:
                try:
                    opened = json.loads(await open_page_server.open_page(url))
                except Exception as err:  # recorded per page: this check reports failures
                    rows.append({"url": url, "host": host, "error": f"{type(err).__name__}: {(str(err).splitlines() or [''])[0]}"})
                    continue
                rows.append({"url": url, "host": host, **{k: opened.get(k) for k in (
                    "final_url", "status", "title", "loaded", "load_event", "browser", "local_failure")}})

    await asyncio.gather(*(host_pages(h, u) for h, u in by_host.items()))
    return sorted(rows, key=lambda r: r["url"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--records", type=Path, nargs="+", required=True)
    ap.add_argument("--queue", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    earlier = pages(args.records)
    rows = asyncio.run(check(earlier + [url for url in queue_pages(args.queue) if url not in earlier]))
    args.out.write_text(json.dumps({"schema_version": "hapi-337-preflight-page-check/3",
                                    "runs": [p.name for p in args.records],
                                    "stage_1_queue_sha256": sha256_path(args.queue),
                                    "made_with": {path.name: sha256_path(path) for path in (
                                        Path(__file__), OPEN_PAGE_SERVER_PATH, CITABLE_SOURCES_PATH)},
                                    "pages": rows},
                                   indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
