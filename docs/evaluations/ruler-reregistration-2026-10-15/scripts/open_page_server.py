#!/usr/bin/env python3
"""#361 review protocol (#337 v10 with #358's fixes): the review agents' one way to read a web page.

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
(`BROWSERBASE_API_KEY`). Any other page that does not load in the local browser (an error, a
wall, an empty page; not a 404 or 410) is read again in Browserbase, and the result keeps the
local failure (`local_failure`). A navigation error in Browserbase is not caught: the tool
call fails and the agent sees the error.

Navigation waits for the HTML to be parsed (`domcontentloaded`), then up to
LOAD_EVENT_WAIT_SECONDS for the `load` event, and records whether it fired (`load_event`). The
v7 run waited for `load` itself, which some pages never reach: on the iDAI gazetteer's place
pages an analytics script (piwik.dainst.org) never finishes loading, although the record has
rendered within seconds, so every open of the record the Stage 2 reviewers were judging timed
out. A page whose `load` fires is read exactly as before.

Launched once per review call by `run_harness_review.py` (`--mcp-config`, under `xvfb-run`).
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import socket
import sys
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from mcp.server.mcpserver import MCPServer
from playwright.async_api import Browser, Error as PlaywrightError, Page, Response, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_protocol import BLOCKED_DOMAINS, CHECKPOINT_TITLES, OPEN_PAGE_SERVER, browser_for, page_loaded  # noqa: E402

CHECKPOINT_WAIT_SECONDS = 30
LOAD_EVENT_WAIT_SECONDS = 15
NAVIGATION_TIMEOUT_MS = 45_000
MIN_SECONDS_BETWEEN_OPENS_PER_HOST = 2.0
MAX_TEXT_CHARS = 40_000
# Chromium answers a navigation to a file it downloads (a PDF) with this error; the file is
# then fetched through the same browser context (its cookies, so a passed wall stays passed).
DOWNLOAD_STARTING = "Download is starting"
# Playwright's error for a page read while it navigates on.
CONTEXT_DESTROYED = "Execution context was destroyed"

BROWSERBASE_API = "https://api.browserbase.com/v1/sessions"

server = MCPServer(OPEN_PAGE_SERVER)
_browser: Browser | None = None
_playwright = None
_next_open: dict[str, float] = {}
_pacing = asyncio.Lock()
_starting, _launching = asyncio.Lock(), asyncio.Lock()
# One Browserbase session at a time per review call: the account allows 3 at once, and the two
# reviewers run side by side.
_browserbase_slot = asyncio.Lock()


async def _playwright_driver():
    global _playwright
    async with _starting:
        if _playwright is None:
            _playwright = await async_playwright().start()
    return _playwright


async def _page() -> Page:
    global _browser
    async with _launching:  # parallel first calls would each launch a browser
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
    async with _browserbase_slot:
        return await _browserbase_read(url)


async def _browserbase_read(url: str) -> dict:
    session = await asyncio.to_thread(_browserbase, "POST", "", {})
    # The session is released, and the remote closed, whatever fails after it is created
    # (#358: a raise in `connect_over_cdp` or `new_page` left both open).
    try:
        remote = await (await _playwright_driver()).chromium.connect_over_cdp(session["connectUrl"])
        try:
            opened = await _read(await remote.contexts[0].new_page(), url)
        finally:
            await remote.close()
    finally:
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
    host = (urlparse(url).hostname or "").lower().rstrip(".")  # "www.wikidata.org." too (#358)
    return any(host == domain or host.endswith("." + domain) for domain in BLOCKED_DOMAINS)


def _local(url: str) -> bool:
    """Whether the URL's host is the review host or its network: loopback, link-local or
    private, by name or by what the name resolves to (#358: a page or search result could
    point the tool at a service on the review host)."""
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return not ipaddress.ip_address(host).is_global
    except ValueError:
        pass
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror:
        return False  # an unknown name: the browser's own error says so
    return any(not ipaddress.ip_address(address.split("%")[0]).is_global for address in addresses)


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
    # A file has no load event: none was measured (#358: it was recorded as true).
    return {"final_url": response.url, "status": response.status, "title": title, "text": text, "load_event": None}


async def _html(page: Page, url: str) -> dict:
    documents: list[Response] = []
    page.on("response", lambda r: documents.append(r) if (
        r.request.is_navigation_request() and r.frame == page.main_frame) else None)
    await page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
    # The load event is awaited once, after any checkpoint has passed (#358: a first, unused
    # wait made a page whose load never fires wait twice).
    title = await _title(page)
    deadline = time.monotonic() + CHECKPOINT_WAIT_SECONDS
    while any(marker in title for marker in CHECKPOINT_TITLES) and time.monotonic() < deadline:
        await page.wait_for_timeout(1000)
        title = await _title(page)
    load_event = await _load_event(page)
    if documents[-1].headers.get("content-type", "").startswith("application/pdf"):
        # A headful browser shows a PDF in its viewer, which has no page text: read the file,
        # fetched in full through the same browser context.
        return await _pdf_download(page, documents[-1].url)
    return {"final_url": page.url, "status": documents[-1].status, "title": await _title(page),
            "text": await _guarded(page, lambda: page.inner_text("body")), "load_event": load_event}


async def _load_event(page: Page) -> bool:
    """Whether the page's `load` event fires within LOAD_EVENT_WAIT_SECONDS. Not a failure to
    read if it does not: the page is read as it stands and the result says so."""
    try:
        await page.wait_for_load_state("load", timeout=LOAD_EVENT_WAIT_SECONDS * 1000)
    except PlaywrightTimeoutError:
        return False
    return True


MAX_NAVIGATIONS_FOLLOWED = 3


async def _guarded(page: Page, read):
    """`read()` of the page; if the page navigates on while it is read (a wall's challenge
    passing, a redirect by script), the same read of the page it arrives at, up to
    MAX_NAVIGATIONS_FOLLOWED navigations (#358: the text had no guard, the title one)."""
    for _ in range(MAX_NAVIGATIONS_FOLLOWED):
        try:
            return await read()
        except PlaywrightError as err:
            if CONTEXT_DESTROYED not in str(err):
                raise
            await page.wait_for_load_state("domcontentloaded")
    return await read()


async def _title(page: Page) -> str:
    return await _guarded(page, page.title)


async def _open_locally(url: str) -> dict:
    """Read the page in the local browser. If it does not load there (an error, a wall, an
    empty page), the result says why in `local_failure`, and the caller reads it in Browserbase
    instead; a 404 or 410 is the site's answer, not a failure of the browser, and is returned."""
    page = await _page()
    try:
        opened = {**await _read(page, url), "browser": "local"}
    except PlaywrightError as err:
        return {"local_failure": str(err).splitlines()[0]}
    finally:
        await page.close()
    if opened["status"] in (404, 410) or page_loaded(opened["status"], opened["title"], opened["text"]):
        return opened
    return {"local_failure": f"status {opened['status']}, title {opened['title']!r}"}


async def _reread_in_browserbase(url: str, host: str, local_failure: str) -> dict:
    """A page that did not load locally, read again in Browserbase: paced per host like any
    open, and if the re-read itself raises, the error names the local failure too (#358)."""
    await _paced(host)
    try:
        opened = await _open_in_browserbase(url)
    except Exception as err:
        raise RuntimeError(f"{url}: Browserbase re-read failed ({err}); local failure: {local_failure}") from err
    return {**opened, "local_failure": local_failure}


@server.tool(structured_output=False, description=(
    "Open a web page or PDF in a real browser and return its visible text. Returns JSON: "
    "requested_url, final_url, status (HTTP status of the final document), title (for a PDF, "
    "\"PDF: \" and its title), loaded (true only if status is 200, the page is not a bot "
    "checkpoint or wall, and it has text), load_event (whether the page finished loading within "
    f"{LOAD_EVENT_WAIT_SECONDS} seconds; if not, the text is what had rendered by then), text (visible text, "
    f"at most {MAX_TEXT_CHARS} characters) and text_truncated. Only a page with loaded: true whose final_url belongs to a citable source may be cited."
))
async def open_page(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if not url.startswith(("https://", "http://")) or not host:
        raise ValueError(f"not a web URL: {url!r}")
    if _blocked(url):
        raise ValueError(f"{host} may not be opened in this review")
    if _local(url):
        raise ValueError(f"{host} is a local or private-network host and may not be opened")
    await _paced(host)
    if browser_for(url) == "browserbase":
        opened = await _open_in_browserbase(url)
    else:
        opened = await _open_locally(url)
        if "local_failure" in opened:
            opened = await _reread_in_browserbase(url, host, opened["local_failure"])
    if _blocked(opened["final_url"]) or _local(opened["final_url"]):
        raise ValueError(f"{url} redirected to {opened['final_url']}, which may not be opened in this review")
    return json.dumps({
        "requested_url": url,
        "final_url": opened["final_url"],
        "status": opened["status"],
        "title": opened["title"],
        "loaded": page_loaded(opened["status"], opened["title"], opened["text"]),
        "text": opened["text"][:MAX_TEXT_CHARS],
        "text_truncated": len(opened["text"]) > MAX_TEXT_CHARS,
        "load_event": opened["load_event"],
        "browser": opened["browser"],
        **({"browserbase_session_id": opened["browserbase_session_id"]} if "browserbase_session_id" in opened else {}),
        **({"local_failure": opened["local_failure"]} if "local_failure" in opened else {}),
    }, ensure_ascii=False)


if __name__ == "__main__":
    server.run("stdio")
