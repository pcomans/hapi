#!/usr/bin/env python3
"""#337 review protocol v4: the review agents' one way to read a web page.

An MCP server (stdio) with a single tool, `open_page`, that loads a URL in headless Chromium
and returns what the page says. The Met and Brooklyn collection sites sit behind Vercel's
JavaScript "Security Checkpoint", which answers every request that cannot run JavaScript with
HTTP 429; Claude Code's WebFetch is such a request, so in the v3 run 69% of Met and 96% of
Brooklyn fetches were refused and most judgments about those records rested on search
summaries. A real browser passes the checkpoint.

The tool's result is the whole record of what the agent read: the requested and final URL,
the HTTP status of the final document, its title, whether it loaded, and its visible text.
`review_protocol.validate` reads it back from the stored event stream; only a page that
loaded counts as a source. Opens are paced per host. A navigation error is not caught: the
tool call fails and the agent sees the error.

Launched once per review call by `run_harness_review.py` (`--mcp-config`).
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from mcp.server.mcpserver import MCPServer
from playwright.async_api import Browser, Page, Response, async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_protocol import BLOCKED_DOMAINS, CHECKPOINT_TITLES, OPEN_PAGE_SERVER  # noqa: E402

CHECKPOINT_WAIT_SECONDS = 20
NAVIGATION_TIMEOUT_MS = 45_000
MIN_SECONDS_BETWEEN_OPENS_PER_HOST = 2.0
MAX_TEXT_CHARS = 40_000

server = MCPServer(OPEN_PAGE_SERVER)
_browser: Browser | None = None
_last_open: dict[str, float] = {}


async def _page() -> Page:
    global _browser
    if _browser is None:
        _browser = await (await async_playwright().start()).chromium.launch()
    return await _browser.new_page()


def _blocked(host: str) -> bool:
    return any(host == domain or host.endswith("." + domain) for domain in BLOCKED_DOMAINS)


@server.tool(structured_output=False, description=(
    "Open a web page in a real browser and return its visible text. Returns JSON: "
    "requested_url, final_url, status (HTTP status of the final document), title, loaded "
    "(true only if status is 200 and the page is not a bot checkpoint), text (visible text, at most "
    f"{MAX_TEXT_CHARS} characters) and text_truncated. Only a page with loaded: true may be "
    "cited."
))
async def open_page(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if not url.startswith(("https://", "http://")) or not host:
        raise ValueError(f"not a web URL: {url!r}")
    if _blocked(host):
        raise ValueError(f"{host} may not be opened in this review")
    wait = _last_open.get(host, 0.0) + MIN_SECONDS_BETWEEN_OPENS_PER_HOST - time.monotonic()
    if wait > 0:
        await asyncio.sleep(wait)
    _last_open[host] = time.monotonic()

    page = await _page()
    documents: list[Response] = []
    page.on("response", lambda r: documents.append(r) if (
        r.request.is_navigation_request() and r.frame == page.main_frame) else None)
    await page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
    title = await page.title()
    deadline = time.monotonic() + CHECKPOINT_WAIT_SECONDS
    while any(marker in title for marker in CHECKPOINT_TITLES) and time.monotonic() < deadline:
        await page.wait_for_timeout(1000)
        title = await page.title()
    await page.wait_for_load_state("domcontentloaded")
    status = documents[-1].status
    text = await page.inner_text("body")
    result = {
        "requested_url": url,
        "final_url": page.url,
        "status": status,
        "title": title,
        "loaded": status == 200 and not any(marker in title for marker in CHECKPOINT_TITLES),
        "text": text[:MAX_TEXT_CHARS],
        "text_truncated": len(text) > MAX_TEXT_CHARS,
    }
    await page.close()
    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    server.run("stdio")
