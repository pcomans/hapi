#!/usr/bin/env python3
"""#337 review protocol v6: the review agents' one way to read a web page.

An MCP server (stdio) with a single tool, `open_page`, that loads a URL in Chromium (headful,
on the virtual X display `xvfb-run` gives it) and returns what the page or PDF says. The Met and Brooklyn collection sites sit behind Vercel's
JavaScript "Security Checkpoint", which answers every request that cannot run JavaScript with
HTTP 429; Claude Code's WebFetch is such a request, so in the v3 run 69% of Met and 96% of
Brooklyn fetches were refused and most judgments about those records rested on search
summaries. A real browser passes the checkpoint; a headful one also passes the Anubis and
Cloudflare walls in front of Pleiades, UNESCO and others, which refuse HeadlessChrome.

The tool's result is the whole record of what the agent read: the requested and final URL,
the HTTP status of the final document, its title, whether it loaded, and its visible text.
`review_protocol.validate` reads it back from the stored event stream and re-derives whether
it loaded; only a loaded page of a citable source counts. Opens are paced per host, also
across parallel calls. A PDF is read with pypdf. Sources marked `"browser": "browserbase"` in
`citable-sources.json` are read in a Browserbase cloud browser instead, one session per page
(its ID is in the result, for the session replay); the API key comes from the environment
(`BROWSERBASE_API_KEY`). A navigation error is not caught: the tool
call fails and the agent sees the error.

Launched once per review call by `run_harness_review.py` (`--mcp-config`, under `xvfb-run`).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from mcp.server.mcpserver import MCPServer
from playwright.async_api import Browser, Error as PlaywrightError, Page, Response, async_playwright
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_protocol import BLOCKED_DOMAINS, CHECKPOINT_TITLES, OPEN_PAGE_SERVER, browser_for, page_loaded  # noqa: E402

CHECKPOINT_WAIT_SECONDS = 30
NAVIGATION_TIMEOUT_MS = 45_000
MIN_SECONDS_BETWEEN_OPENS_PER_HOST = 2.0
MAX_TEXT_CHARS = 40_000
# Chromium answers a navigation to a file it downloads (a PDF) with this error; the file is
# then fetched through the same browser context (its cookies, so a passed wall stays passed).
DOWNLOAD_STARTING = "Download is starting"

BROWSERBASE_API = "https://api.browserbase.com/v1/sessions"

server = MCPServer(OPEN_PAGE_SERVER)
_browser: Browser | None = None
_playwright = None
_next_open: dict[str, float] = {}
_pacing = asyncio.Lock()


async def _playwright_driver():
    global _playwright
    if _playwright is None:
        _playwright = await async_playwright().start()
    return _playwright


async def _page() -> Page:
    global _browser
    if _browser is None:
        # Headful (on the X display `xvfb-run` provides): bot walls (Anubis, Cloudflare's
        # interstitial) refuse a browser that announces itself as HeadlessChrome.
        _browser = await (await _playwright_driver()).chromium.launch(headless=False)
    return await _browser.new_page()


def _browserbase(method: str, path: str, body: dict) -> dict:
    """A Browserbase API call with the key from the environment (never from the command line,
    which the runner records)."""
    response = requests.request(
        method, BROWSERBASE_API + path, json=body, timeout=60,
        headers={"X-BB-API-Key": os.environ["BROWSERBASE_API_KEY"], "Content-Type": "application/json"},
    )
    response.raise_for_status()
    return response.json()


async def _open_in_browserbase(url: str) -> dict:
    """Read one page in its own Browserbase cloud session, released as soon as it is read."""
    session = await asyncio.to_thread(_browserbase, "POST", "", {})
    remote = await (await _playwright_driver()).chromium.connect_over_cdp(session["connectUrl"])
    page = await remote.contexts[0].new_page()
    try:
        opened = await _read(page, url)
    finally:
        await remote.close()
        await asyncio.to_thread(_browserbase, "POST", f"/{session['id']}", {"status": "REQUEST_RELEASE"})
    return {**opened, "browser": "browserbase", "browserbase_session_id": session["id"]}


async def _read(page: Page, url: str) -> dict:
    try:
        return await _html(page, url)
    except PlaywrightError as err:
        if DOWNLOAD_STARTING not in str(err):
            raise
        return await _pdf_download(page, url)


def _blocked(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == domain or host.endswith("." + domain) for domain in BLOCKED_DOMAINS)


async def _paced(host: str) -> None:
    """Wait for this host's next free slot; slots are reserved under a lock, so calls made in
    parallel are spaced too."""
    async with _pacing:
        slot = max(time.monotonic(), _next_open.get(host, 0.0))
        _next_open[host] = slot + MIN_SECONDS_BETWEEN_OPENS_PER_HOST
    await asyncio.sleep(max(0.0, slot - time.monotonic()))


def _pdf_text(body: bytes, url: str) -> tuple[str, str]:
    reader = PdfReader(BytesIO(body))
    text = "\n".join(pdf_page.extract_text() for pdf_page in reader.pages)
    title = (reader.metadata.title if reader.metadata and reader.metadata.title else "") or url
    return f"PDF: {title}", text


async def _pdf_download(page: Page, url: str) -> dict:
    response = await page.context.request.get(url, timeout=NAVIGATION_TIMEOUT_MS)
    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("application/pdf"):
        raise ValueError(f"{url} started a download that is not a PDF: {content_type!r}")
    title, text = _pdf_text(await response.body(), url)
    return {"final_url": response.url, "status": response.status, "title": title, "text": text}


async def _html(page: Page, url: str) -> dict:
    documents: list[Response] = []
    page.on("response", lambda r: documents.append(r) if (
        r.request.is_navigation_request() and r.frame == page.main_frame) else None)
    await page.goto(url, wait_until="load", timeout=NAVIGATION_TIMEOUT_MS)
    if documents[-1].headers.get("content-type", "").startswith("application/pdf"):
        # A headful browser shows a PDF in its viewer, which has no page text: read the file,
        # fetched in full through the same browser context.
        return await _pdf_download(page, page.url)
    title = await page.title()
    deadline = time.monotonic() + CHECKPOINT_WAIT_SECONDS
    while any(marker in title for marker in CHECKPOINT_TITLES) and time.monotonic() < deadline:
        await page.wait_for_timeout(1000)
        title = await page.title()
    await page.wait_for_load_state("load")
    return {"final_url": page.url, "status": documents[-1].status, "title": title,
            "text": await page.inner_text("body")}


@server.tool(structured_output=False, description=(
    "Open a web page or PDF in a real browser and return its visible text. Returns JSON: "
    "requested_url, final_url, status (HTTP status of the final document), title (for a PDF, "
    "\"PDF: \" and its title), loaded (true only if status is 200, the page is not a bot "
    f"checkpoint or wall, and it has text), text (visible text, at most {MAX_TEXT_CHARS} characters) and "
    "text_truncated. Only a page with loaded: true whose final_url belongs to a citable source may be cited."
))
async def open_page(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if not url.startswith(("https://", "http://")) or not host:
        raise ValueError(f"not a web URL: {url!r}")
    if _blocked(url):
        raise ValueError(f"{host} may not be opened in this review")
    await _paced(host)
    if browser_for(url) == "browserbase":
        opened = await _open_in_browserbase(url)
    else:
        page = await _page()
        opened = {**await _read(page, url), "browser": "local"}
        await page.close()
    if _blocked(opened["final_url"]):
        raise ValueError(f"{url} redirected to {opened['final_url']}, which may not be opened in this review")
    return json.dumps({
        "requested_url": url,
        "final_url": opened["final_url"],
        "status": opened["status"],
        "title": opened["title"],
        "loaded": page_loaded(opened["status"], opened["title"], opened["text"]),
        "text": opened["text"][:MAX_TEXT_CHARS],
        "text_truncated": len(opened["text"]) > MAX_TEXT_CHARS,
        "browser": opened["browser"],
        **({"browserbase_session_id": opened["browserbase_session_id"]} if "browserbase_session_id" in opened else {}),
    }, ensure_ascii=False)


if __name__ == "__main__":
    server.run("stdio")
