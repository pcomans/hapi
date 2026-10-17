#!/usr/bin/env python3
"""Per-museum ruler test: before the review, open the record pages the queues show reviewers,
with the review's own `open_page` tool and no model, to find any that will not load.

Pages: every record URL either queue shows, except the Met's, of which a seeded sample of
MET_SAMPLE (the Met has most of the pages, and its site has loaded reliably in every run since
#337). Hosts are opened in parallel (at most PARALLEL_HOSTS), each host's pages in turn. Writes
one row per page: what `open_page` returned (no page text), or its error. The review starts only
once every page here has loaded (README; tested).

    xvfb-run -a runtime/.venv/bin/python scripts/preflight_page_check.py \\
      --queue <link-queue.json> --queue <miss-queue.json> --out results/preflight-page-check.json
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
from review_protocol import CITABLE_SOURCES_PATH, OPEN_PAGE_SERVER_PATH, sha256_path

SEED = 20261017
MET_HOST = "metmuseum.org"
MET_SAMPLE = 60
PARALLEL_HOSTS = 6


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").removeprefix("www.")


def queue_pages(queues: list[Path]) -> list[str]:
    shown = sorted({url for queue in queues for case in json.loads(queue.read_text())["cases"]
                    for entry in case["evidence"]["record_texts"] for url in entry["example_record_urls"]})
    met = [url for url in shown if _host(url) == MET_HOST]
    return [url for url in shown if _host(url) != MET_HOST] + sorted(random.Random(SEED).sample(met, min(MET_SAMPLE, len(met))))


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
    ap.add_argument("--queue", type=Path, action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rows = asyncio.run(check(queue_pages(args.queue)))
    args.out.write_text(json.dumps({
        "schema_version": "hapi-ruler-per-museum-preflight-page-check/1",
        "queue_sha256": {path.name: sha256_path(path) for path in args.queue},
        "made_with": {path.name: sha256_path(path) for path in (Path(__file__), OPEN_PAGE_SERVER_PATH, CITABLE_SOURCES_PATH)},
        "pages": rows,
    }, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
