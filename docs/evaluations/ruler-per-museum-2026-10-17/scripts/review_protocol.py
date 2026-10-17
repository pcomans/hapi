#!/usr/bin/env python3
"""Per-museum ruler test: the per-case review protocol shared by every role.

Each role (the link and miss reviewers and their reconcilers) answers one case per call through
headless Claude Code (`run_harness_review.py`). This module owns what is common to all of
them: the audited prompt, response schema and system prompt of each role, the exact model
input of a case, the validation of a stored call from its saved event stream alone (so a
decision is re-checked without calling the model again, Constitutional Rule 13), the
reconciliation queue of the cases two reviewers disagree on, and the frozen consensus.

Two questions, each a "stage" of this module:
- `link`: is the authority ruler a museum text was linked to the ruler its records name?
- `miss`: does a museum text the authority left unmatched or ambiguous name one specific ruler?

Consensus (Rule 2): a question two reviewers answer identically is settled by that
agreement. A disputed question is settled only by the reconciler's explicit override, which
must cite at least one page it opened, unless it answers insufficient_evidence because no
page it opened loaded; nothing else (reviewer order, label, or a tie-break) can
settle it, and a missing override fails loud. A consensus file is accepted only if it is
exactly what this module rebuilds from the stored records.

    runtime/.venv/bin/python .../scripts/review_protocol.py prepare-reconciliation \\
      --stage link --queue <link-queue.json> --records <private link dir> --out <file>
    runtime/.venv/bin/python .../scripts/review_protocol.py freeze-consensus \\
      --stage link --queue <link-queue.json> --records <private link dir> --out <file>
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse

import jsonschema

EVALUATION_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PROMPT_PATH = EVALUATION_ROOT / "launcher-instructions" / "review-system-v4.txt"
SERVED_MODEL = "claude-sonnet-5-5"
# The Claude Code release every scored call ran on, from its init event.
CLAUDE_CODE_VERSION = "2.1.302"
# The Chromium build the runtime's Playwright (runtime/uv.lock) launches; every page a call reads
# in the local browser reports it (`browser_version`), and a call whose local pages report another
# build is refused (#358 item 8).
CHROMIUM_VERSION = "145.0.7632.6"
RUNTIME_LOCK_PATH = EVALUATION_ROOT / "runtime" / "uv.lock"
# The agents read pages only through `open_page` (open_page_server.py, a headless Chromium):
# Claude Code's WebFetch cannot pass the JavaScript checkpoint in front of the Met and
# Brooklyn collection sites. Web search finds pages; it is never a source.
OPEN_PAGE_SERVER = "museum-browser"
OPEN_PAGE_SERVER_PATH = EVALUATION_ROOT / "scripts" / "open_page_server.py"
OPEN_PAGE_TOOL = f"mcp__{OPEN_PAGE_SERVER}__open_page"
TOOLS = ("WebSearch", OPEN_PAGE_TOOL)
# The sources a citation may come from (`citable-sources.json`, committed before the run that
# uses it): museum collections, scholarly gazetteers, research institutions and heritage
# authorities. Any other page may help a reviewer find sources but is never a citation.
CITABLE_SOURCES_PATH = EVALUATION_ROOT / "citable-sources.json"
# Titles of the bot-challenge interstitials `open_page` waits out (Vercel, Cloudflare, Anubis).
CHECKPOINT_TITLES = ("Security Checkpoint", "Just a moment", "Making sure you're not a bot")
# Titles of pages that are not the page's own content: those interstitials, and the walls
# seen in the v4 run that `open_page` does not wait out (an Anubis "Oh noes!" page, a captcha
# page). The validator re-derives `loaded` from the stored status and title with this list.
NOT_LOADED_TITLES = (*CHECKPOINT_TITLES, "Oh noes!", "Captcha Verification Needed")
# An error page a site serves with status 200 (#358 item 10: `arachne.dainst.org/place/2042876`
# returned "Arachne | 404"): a title that says the page was not found.
ERROR_PAGE_TITLE = re.compile(
    r"\bpage not found\b|\b404\b.*\bnot found\b|^\s*not found\s*$|\|\s*404\s*$|^\s*404\s*(\||$)", re.I)
# Wikidata is never a source (role prompts), and this public repository lives on GitHub.
BLOCKED_DOMAINS = ("wikidata.org", "github.com", "raw.githubusercontent.com")
SESSION_LIMIT_TEXT = "hit your session limit"
REVIEWERS = ("A", "B")
# Fixed seed for the order in which a reconciler sees the two reviews: a hash of the seed,
# the case and the review's record hash, so neither reviewer label comes first by rule.
REVIEW_ORDER_SEED = "hapi-ruler-per-museum-2026-10-17-reconciliation-order-v1"
CONSENSUS_SCHEMA_VERSION = "hapi-ruler-per-museum-consensus/1"
RECONCILIATION_SCHEMA_VERSION = "hapi-ruler-per-museum-reconciliation-queue/1"
ATTEMPT_RE = re.compile(r"^(?P<case>.+)\.attempt-(?P<n>[1-9][0-9]*)\.json$")


@dataclass(frozen=True)
class Role:
    name: str
    prompt: Path
    schema: Path
    fields: tuple[str, ...]
    reconciler: bool


STAGE_FIELDS = {"link": ("canonical_identity",), "miss": ("names_one_ruler",)}
CITATION_KEYS = {stage: ("citations",) for stage in STAGE_FIELDS}
# What a reconciler sees of each review besides its outcomes, reasoning and citations: a miss
# review's named ruler.
REVIEW_EXTRA_KEYS = {"link": (), "miss": ("ruler",)}
ROLES = {
    role.name: role
    for role in (
        Role("link_reviewer", EVALUATION_ROOT / "prompts/link-reviewer-v1.txt",
             EVALUATION_ROOT / "raw-response-contracts/link-reviewer-case-v1.schema.json",
             STAGE_FIELDS["link"], False),
        Role("link_reconciler", EVALUATION_ROOT / "prompts/link-reconciler-v1.txt",
             EVALUATION_ROOT / "raw-response-contracts/link-reconciler-case-v1.schema.json",
             STAGE_FIELDS["link"], True),
        Role("miss_reviewer", EVALUATION_ROOT / "prompts/miss-reviewer-v1.txt",
             EVALUATION_ROOT / "raw-response-contracts/miss-reviewer-case-v1.schema.json",
             STAGE_FIELDS["miss"], False),
        Role("miss_reconciler", EVALUATION_ROOT / "prompts/miss-reconciler-v1.txt",
             EVALUATION_ROOT / "raw-response-contracts/miss-reconciler-case-v1.schema.json",
             STAGE_FIELDS["miss"], True),
    )
}
# Private-only keys that must never reach a model input (which links are decoys, the true target
# of a decoy, the unit's hidden binding and record IDs).
MODEL_INPUT_FORBIDDEN_KEYS = {
    "artifact_id", "artifact_ids", "case_binding_sha256", "decoy", "mention_id", "mention_ids",
    "proposed_target_id", "resolved_target_ids", "unit_id", "unit_kind",
}
# The validator's failure for a call in which every `open_page` call returned an error and none a
# page: the call could read nothing, so its answer is no finding (#384; the line the 2026-10-16
# run drew by hand). A call that read at least one page decides as usual.
BROWSER_TOOL_FAILURE = "browser tool failed:"
# Failures the runner retries, up to MAX_ATTEMPTS calls per case: a malformed answer (not JSON,
# schema-invalid, a miscopied case ID, or a reconciler answer that resolves other than the
# disputed questions), an answer citing a page the call did not open or a non-citable source, a
# call whose search results, opened pages or citations touched a blocked domain, and a call whose
# browser read nothing.
RETRYABLE_FAILURES = (
    "invalid decision:", "decision does not echo", "blocked domain used:", "cites a page it did not open:",
    "cites a non-citable source:", BROWSER_TOOL_FAILURE,
)
MAX_ATTEMPTS = 3
SESSION_LIMIT_FAILURE = "Claude Code session limit"
# The committed ledger of stored calls set aside (`decision-rule.md`, "Calls that give no
# answer"). It is not a protocol binding: it may grow during the run, and every entry is
# disclosed with its reason.
SET_ASIDES_PATH = EVALUATION_ROOT / "set-asides.json"


class ProtocolFailure(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def write_atomic(path: Path, value: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True) + "\n", "utf-8")
    tmp.replace(path)


def write_new(path: Path, value: dict) -> None:
    if path.exists():
        raise ProtocolFailure(f"{path} already exists; frozen files are never overwritten")
    write_atomic(path, value)


def citable_sources() -> list[dict]:
    return read_json(CITABLE_SOURCES_PATH)["sources"]


def citable_source_of(url: str) -> dict | None:
    """The citable source a URL belongs to: its host is the source's host or a subdomain of
    it and, where the source names a path prefix, its path starts with it."""
    parsed = urlparse(url)
    host, path = (parsed.hostname or "").lower(), parsed.path
    matches = [
        source for source in citable_sources()
        if (host == source["domain"] or host.endswith("." + source["domain"]))
        and path.startswith(source.get("path_prefix", ""))
    ]
    if len(matches) > 1:
        raise ProtocolFailure(f"{url} matches more than one citable source: {matches}")
    return matches[0] if matches else None


def browser_for(url: str) -> str:
    """Which browser `open_page` reads a URL in: `browserbase` for a citable source marked so in
    `citable-sources.json` (its pages need a cloud browser), `local` for everything else."""
    source = citable_source_of(url)
    return source.get("browser", "local") if source else "local"


def citable_sources_text() -> str:
    """The citable sources as the model reads them: one line per host (and path) and institution."""
    return "\n".join(
        f"- {source['domain']}{source.get('path_prefix', '')}: {source['institution']}"
        for source in citable_sources()
    )


def role_inputs(role: Role) -> dict:
    return {
        "prompt": role.prompt.read_text("utf-8"),
        "schema": read_json(role.schema),
        "system_prompt": SYSTEM_PROMPT_PATH.read_text("utf-8"),
        "citable_sources": citable_sources_text(),
    }


def run_bindings() -> dict:
    """The files that make a call besides its composed input: the runner (command, tools,
    model) and the browser server (what `open_page` does, and its description, which the
    model reads), and the runtime's lock file, which pins the browser and every other dependency
    (#358 item 8; the Claude Code release is checked from each call's init event, the Chromium
    build from each page it read locally). Each stored call records them; a call made by other
    files is not accepted."""
    return {
        "runner_sha256": sha256_path(EVALUATION_ROOT / "scripts" / "run_harness_review.py"),
        "browser_tool_sha256": sha256_path(OPEN_PAGE_SERVER_PATH),
        "runtime_lock_sha256": sha256_path(RUNTIME_LOCK_PATH),
    }


def role_bindings(role: Role) -> dict:
    return {
        "prompt": {"path": role.prompt.name, "sha256": sha256_path(role.prompt)},
        "schema": {"path": role.schema.name, "sha256": sha256_path(role.schema)},
        "system_prompt": {"path": SYSTEM_PROMPT_PATH.name, "sha256": sha256_path(SYSTEM_PROMPT_PATH)},
        "citable_sources": {"path": CITABLE_SOURCES_PATH.name, "sha256": sha256_path(CITABLE_SOURCES_PATH)},
    }


def forbidden_keys(value, path: str = "$") -> list[str]:
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in MODEL_INPUT_FORBIDDEN_KEYS:
                found.append(f"{path}.{key}")
            found.extend(forbidden_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(forbidden_keys(child, f"{path}[{index}]"))
    return found


def without_hashes(value):
    """The model input without `evidence_sha256`: the hash binds a case to the frozen
    population in our records; the model has no use for it (and copying a 64-character hex
    string back is a needless way for an answer to fail)."""
    if isinstance(value, dict):
        return {key: without_hashes(child) for key, child in value.items() if key != "evidence_sha256"}
    if isinstance(value, list):
        return [without_hashes(child) for child in value]
    return value


def compose_user_content(case: dict, role_prompt: str, schema: dict, citable_sources: str) -> str:
    leaks = forbidden_keys(case)
    if leaks:
        raise ProtocolFailure(f"model input carries private keys: {leaks}")
    case = without_hashes(case)
    return "\n\n".join([
        role_prompt.strip(),
        "Citable sources (a page on one of these hosts or its subdomains, under the path where one is given):\n"
        + citable_sources,
        "Response schema:\n" + json.dumps(schema, indent=1, sort_keys=True),
        "Case:\n" + json.dumps(case, indent=1, sort_keys=True, ensure_ascii=False),
    ])


def page_loaded(status: int | None, title: str | None, text: str | None) -> bool:
    """A page loaded when its final document has status 200, it is not a wall or an error page,
    and it has text to read (a challenge page or an empty viewer has none)."""
    return (
        status == 200 and bool((text or "").strip())
        and not any(marker.casefold() in (title or "").casefold() for marker in NOT_LOADED_TITLES)
        and not ERROR_PAGE_TITLE.search(title or "")
    )


def citation_lists(decision: dict) -> list[list[str]]:
    """Each judgment's own citations: a reconciler's per resolution, a reviewer's one list for
    its one question."""
    if "resolutions" in decision:
        return [resolution["citations"] for resolution in decision["resolutions"].values()]
    return [decision["citations"]]


def cited_urls(decision: dict) -> list[str]:
    return [url for citations in citation_lists(decision) for url in citations]


def _citable(url: str) -> bool:
    return citable_source_of(url) is not None


def _blocked(url: str | None) -> bool:
    # A trailing dot (an absolute DNS name) names the same host.
    host = (urlparse(url or "").hostname or "").lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain) for domain in BLOCKED_DOMAINS)


def _page(url: str | None) -> tuple[str, str, str, str]:
    """A URL's page identity: host without `www.`, path without trailing slash, the query (its
    parameters sorted), since a query can name the page (`?q=<id>`, `?p=<post>`), and a
    fragment that routes a single-page app (`#!/show/<id>` on the iDAI gazetteer, `#/...`),
    since it names the page too. The scheme and any other fragment (an anchor) are not part
    of it."""
    parsed = urlparse((url or "").strip())
    return (
        (parsed.hostname or "").lower().removeprefix("www."),
        parsed.path.rstrip("/"),
        urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True))),
        parsed.fragment if parsed.fragment.startswith(("!", "/")) else "",
    )


def requestable(url: object) -> bool:
    """Whether the URL has a scheme `open_page` requests (it refuses any other; it also refuses
    an http(s) URL with no host, which no citable source matches either)."""
    return isinstance(url, str) and url.startswith(("https://", "http://"))


def opened_pages(record: dict) -> set[tuple[str, str, str, str]]:
    """The pages a validated record shows the call read: every `open_page` result that loaded,
    under the URL it requested and the URL it ended on. A citation of the requested URL of a
    redirect is checkable: following it reaches the page the call read (in the v4 run,
    pharaoh.se's old king paths and Brooklyn's `/opencollection/objects/<id>` redirect to the
    same record under a new path)."""
    return {
        _page(url) for opened in record["page_opens"] if opened["loaded"]
        for url in (opened["requested_url"], opened["final_url"])
    }


def _open_page_result(block: dict) -> dict:
    """The record `open_page` returned (open_page_server.py), or its error."""
    content = block.get("content")
    if isinstance(content, list):
        texts = [part["text"] for part in content if part.get("type") == "text"]
        if len(texts) != 1:
            raise ProtocolFailure(f"open_page result without exactly one text part: {content!r:.300}")
        content = texts[0]
    if block.get("is_error"):
        return {"error": content}
    return json.loads(content)


def validate(record: dict, case: dict, role: Role, schema: dict) -> dict:
    """Derive the record's fields from its stored event stream and validate the answer.

    Reads only `record["events"]` and `record["exit_code"]`, so a stored attempt is re-checked
    without calling the model again (Rule 13)."""

    events = record["events"]
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), None)
    if init is None:
        record["failure"] = "no init event"
        return record
    record["served_model"] = init.get("model")
    record["auth"] = init.get("apiKeySource")
    if init.get("apiKeySource") != "none":
        record["failure"] = f"API-key auth would bill this call: {init.get('apiKeySource')!r}"
        return record
    servers = [(server.get("name"), server.get("status")) for server in init.get("mcp_servers") or []]
    if sorted(init.get("tools") or []) != sorted(TOOLS) or servers != [(OPEN_PAGE_SERVER, "connected")]:
        record["failure"] = f"unexpected tools {init.get('tools')} or MCP servers {init.get('mcp_servers')}"
        return record
    if init.get("model") != SERVED_MODEL:
        record["failure"] = f"served model {init.get('model')!r}, not {SERVED_MODEL!r}"
        return record
    if init.get("claude_code_version") != CLAUDE_CODE_VERSION:
        record["failure"] = f"Claude Code {init.get('claude_code_version')!r}, not {CLAUDE_CODE_VERSION!r}"
        return record
    # User-level hooks still run in a `claude -p` session; any output would reach the model.
    hook_output = [
        e.get("hook_name") for e in events
        if e.get("type") == "system" and e.get("subtype") == "hook_response"
        and (e.get("output") or e.get("stdout") or e.get("stderr"))
    ]
    if hook_output:
        record["failure"] = f"hook output reached the session: {hook_output}"
        return record

    blocks = [
        (e["type"], b, e.get("tool_use_result"))
        for e in events if e.get("type") in ("assistant", "user")
        and isinstance(e["message"].get("content"), list)
        for b in e["message"]["content"]
    ]
    calls = {b["id"]: b for kind, b, _ in blocks if b.get("type") == "tool_use"}
    record["stated_text"] = [b["text"] for kind, b, _ in blocks if kind == "assistant" and b.get("type") == "text"]
    record["thinking"] = [b.get("thinking", "") for kind, b, _ in blocks if b.get("type") == "thinking"]
    record["web_searches"] = [b["input"].get("query") for b in calls.values() if b["name"] == "WebSearch"]
    record["web_search_results"] = []
    record["page_opens"] = []
    for kind, b, result in blocks:
        if b.get("type") != "tool_result":
            continue
        name = calls[b["tool_use_id"]]["name"]
        if name == "WebSearch" and isinstance(result, dict):
            record["web_search_results"].extend(
                {"title": item.get("title"), "url": item.get("url")}
                for group in result.get("results") or [] if isinstance(group, dict)
                for item in group.get("content") or []
            )
        elif name == OPEN_PAGE_TOOL:
            opened = _open_page_result(b)
            url = calls[b["tool_use_id"]]["input"].get("url")
            if "error" in opened:
                record["page_opens"].append({"url": url, "loaded": False, "error": opened["error"]})
            else:
                # `loaded` is re-derived here from the stored status and title, not taken
                # from the server's own flag (`reported_loaded`), so a rule change reaches
                # every stored call when it is re-checked.
                record["page_opens"].append({
                    "url": url, **{key: opened[key] for key in (
                        "requested_url", "final_url", "status", "title", "browser", "browser_version", "load_event")},
                    **({"local_failure": opened["local_failure"]} if "local_failure" in opened else {}),
                    "reported_loaded": opened["loaded"], "loaded": page_loaded(opened["status"], opened["title"], opened["text"]),
                })
    other_builds = sorted({o["browser_version"] for o in record["page_opens"]
                           if o.get("browser") == "local" and o["browser_version"] != CHROMIUM_VERSION})
    if other_builds:
        record["failure"] = f"pages read by Chromium {other_builds}, not {CHROMIUM_VERSION}"
        return record
    final = next((e for e in reversed(events) if e.get("type") == "result"), None)
    record["usage"] = final.get("usage") if final else None
    record["notional_cost_usd"] = final.get("total_cost_usd") if final else None

    # A tool call the session limit refused leaves the research cut short for a reason
    # unrelated to the case, so the call is a session-limit stop, not a decision.
    refused = [
        b for kind, b, _ in blocks
        if b.get("type") == "tool_result" and b.get("is_error")
        and SESSION_LIMIT_TEXT in json.dumps(b.get("content"))
    ]
    if refused:
        record["failure"] = f"Claude Code session limit during research: {len(refused)} tool call(s) refused"
        return record
    # A call that did not finish (a crash, a session cut off) has no successful result event,
    # whatever answer its last message may hold.
    if final is None or final.get("subtype") != "success" or final.get("is_error"):
        record["failure"] = "the call did not end in a successful result"
        return record
    if not record["stated_text"]:
        record["failure"] = "no final text"
        return record
    final_text = record["stated_text"][-1].strip()
    record["final_text"] = final_text
    if SESSION_LIMIT_TEXT in final_text:
        record["failure"] = f"Claude Code session limit: {final_text}"
        return record
    if record["page_opens"] and all("error" in o for o in record["page_opens"]):
        record["failure"] = (f"{BROWSER_TOOL_FAILURE} all {len(record['page_opens'])} open_page call(s) "
                             f"returned an error: {[o['url'] for o in record['page_opens']][:5]}")
        return record
    # A process that exited unsuccessfully decides nothing, whatever it answered: here, the one
    # check every path reads (a new call, a re-check, a decided record, the gate) (#358 item 9);
    # after the session-limit check, so a session limit stays resumable.
    if record["exit_code"] != 0:
        record["failure"] = f"the call's process exited {record['exit_code']}"
        return record
    # The answer is the JSON object that ends the final message. A note the model writes on
    # its own line(s) before it ("I'm wrapping up ...") is kept, not parsed.
    text = final_text
    if not text.startswith("{") and "\n{" in text:
        record["note_before_answer"], text = text[: text.index("\n{")].strip(), text[text.index("\n{") + 1:]
    try:
        decision = json.loads(text)
        jsonschema.validate(decision, schema)
    except (json.JSONDecodeError, jsonschema.ValidationError) as err:
        record["failure"] = f"invalid decision: {type(err).__name__}: {str(err)[:500]}"
        return record
    if decision["case_id"] != case["case_id"]:
        record["failure"] = "decision does not echo the case ID exactly"
        return record
    if role.reconciler and sorted(decision["resolutions"]) != sorted(case["disputed_questions"]):
        record["failure"] = (
            f"invalid decision: resolves {sorted(decision['resolutions'])}, "
            f"not the disputed questions {sorted(case['disputed_questions'])}"
        )
        return record
    cited = cited_urls(decision)
    touched = (
        [r["url"] for r in record["web_search_results"]] + [o["url"] for o in record["page_opens"]]
        + [o["final_url"] for o in record["page_opens"] if "final_url" in o] + cited
    )
    if any(_blocked(url) for url in touched):
        record["failure"] = f"blocked domain used: {[u for u in touched if _blocked(u)]}"
        return record
    # A citation is a page this call opened and that loaded; nothing else is a source (not a
    # search result, not a URL the case shows, not a page another call opened). Every
    # citation must be one, and a reconciler must open what it cites itself.
    opened = opened_pages(record)
    unopened = sorted({url for url in cited if _page(url) not in opened})
    if unopened:
        record["failure"] = f"cites a page it did not open: {unopened}"
        return record
    # Both the cited URL and the page the browser ended on must belong to a citable source,
    # so a redirect cannot carry a citation onto, or off, the list.
    final_urls = collections.defaultdict(set)
    for o in record["page_opens"]:
        if o["loaded"]:
            for url in (o["requested_url"], o["final_url"]):
                final_urls[_page(url)].add(o["final_url"])
    uncitable = sorted({
        url for url in cited
        if not _citable(url) or not any(_citable(final) for final in final_urls[_page(url)])
    })
    if uncitable:
        record["failure"] = f"cites a non-citable source: {uncitable}"
        return record
    # insufficient_evidence may cite nothing only when no citable page the call opened loaded
    # (a page outside the list may lead to sources but can never be cited).
    judgments = citation_lists(decision)
    citable_loaded = any(
        o["loaded"] and _citable(o["requested_url"]) and _citable(o["final_url"]) for o in record["page_opens"]
    )
    if any(not citations for citations in judgments) and citable_loaded:
        record["failure"] = "invalid decision: cites nothing although a citable page it opened loaded"
        return record
    # ... and only after trying: an answer that cites nothing without having tried to open a
    # citable page is unresearched, not a finding that the evidence is insufficient.
    # (A URL `open_page` refuses outright, not http(s), is no attempt.)
    if any(not citations for citations in judgments) and not any(
        requestable(o["url"]) and _citable(o["url"]) for o in record["page_opens"]
    ):
        record["failure"] = "invalid decision: cites nothing without having tried a citable page"
        return record
    record["decision"] = decision
    return record


def attempt_number(path: Path) -> int:
    match = ATTEMPT_RE.match(path.name)
    if match is None:
        raise ProtocolFailure(f"unexpected record name: {path}")
    return int(match["n"])


def calls_by_latest_attempt(directory: Path, case_id: str) -> dict[str, Path]:
    """Each model call of a case (a re-check is its source call) and its latest attempt file."""
    latest = {}
    for path in sorted(directory.glob(f"{case_id}.attempt-*.json"), key=attempt_number):
        latest[read_json(path).get("revalidated_from", path.name)] = path
    return latest


def set_asides(directory: Path) -> dict[str, str]:
    """The calls of one record directory (`<stage>/<reviewer-A|reviewer-B|reconciler>`) the
    committed ledger sets aside: file name to SHA-256. Each listed file must be there with its
    hash."""
    ledger = read_json(SET_ASIDES_PATH)
    listed = {entry["file"]: entry["sha256"] for entry in ledger["set_asides"]
              if (entry["stage"], entry["directory"]) == (directory.parent.name, directory.name)}
    for name, sha in listed.items():
        if not (directory / name).is_file() or sha256_path(directory / name) != sha:
            raise ProtocolFailure(f"{directory / name}: set aside in the ledger, but missing or changed")
        stored = read_json(directory / name)
        if "decision" in stored:
            raise ProtocolFailure(f"{directory / name}: a call with a decision is never set aside")
        if retryable(stored.get("failure", "")):
            raise ProtocolFailure(f"{directory / name}: a retryable failure is never set aside; it counts toward giving up")
    return listed


def retryable(failure: str) -> bool:
    return failure.startswith(RETRYABLE_FAILURES)


def gave_no_answer(failures: list[str]) -> bool:
    """Whether a case's calls (none of them valid) mean it gives no answer: at least MAX_ATTEMPTS
    retryable failures, and every other failure a session limit, which a resumed run retries
    without counting. The runner stops trying a case, and `decided_record` settles it, on this
    one rule (`decision-rule.md`, "Calls that give no answer")."""
    return (sum(retryable(f) for f in failures) >= MAX_ATTEMPTS
            and all(retryable(f) or f.startswith(SESSION_LIMIT_FAILURE) for f in failures))


def decided_record(directory: Path, case: dict, role: Role, inputs: dict) -> tuple[str, dict] | None:
    """The one stored call that decided `case`, re-validated from its events under the current rules.

    Every attempt is re-checked. A re-check attempt (`revalidated_from`) is the same model
    call as its source. Exactly one call must be valid, and the latest stored attempt of
    every call must record what its re-check gives (a call whose verdict changed under a
    later rule carries a re-check attempt saying so). Each attempt must have been composed
    from the current prompt, schema, system prompt and case. Returns the SHA-256 of the
    valid call's latest attempt file and its stored record."""
    paths = sorted(directory.glob(f"{case['case_id']}.attempt-*.json"), key=attempt_number)
    if not paths:
        raise ProtocolFailure(f"no record for {case['case_id']} in {directory}")
    # Attempts are numbered 1..n with no gap: a removed or moved attempt fails loud.
    if [attempt_number(p) for p in paths] != list(range(1, len(paths) + 1)):
        raise ProtocolFailure(f"{case['case_id']} in {directory}: attempts {[p.name for p in paths]} are not 1..n")
    aside = set_asides(directory)
    paths = [p for p in paths if p.name not in aside]
    user_content = compose_user_content(case, inputs["prompt"], inputs["schema"], inputs["citable_sources"])
    latest, valid_calls = {}, set()
    for path in paths:
        if ATTEMPT_RE.match(path.name)["case"] != case["case_id"]:
            raise ProtocolFailure(f"unexpected record name: {path}")
        stored = read_json(path)
        if stored["user_content"] != user_content or stored["system_prompt"] != inputs["system_prompt"]:
            raise ProtocolFailure(f"{path}: not composed from the current prompt, schema and case")
        if stored.get("run_bindings") != run_bindings():
            raise ProtocolFailure(f"{path}: not made by the current runner and browser tool")
        if "events" not in stored:
            if "decision" in stored:
                raise ProtocolFailure(f"{path}: a decision without its event stream")
            continue
        call = stored.get("revalidated_from", path.name)
        if call != path.name:
            source = directory / call
            if not source.exists() or read_json(source).get("events") != stored["events"]:
                raise ProtocolFailure(f"{path}: a re-check whose events are not those of {call}")
        recheck = validate({"events": stored["events"], "exit_code": stored["exit_code"]}, case, role, inputs["schema"])
        # A process that exited unsuccessfully decides nothing, whatever it answered.
        if stored["exit_code"] != 0:
            if "decision" in stored:
                raise ProtocolFailure(f"{path}: a decision from a call that exited {stored['exit_code']}")
            recheck = {key: value for key, value in recheck.items() if key != "decision"}
        if "decision" in recheck:
            valid_calls.add(call)
        latest[call] = (path, stored, recheck)
    for call, (path, stored, recheck) in latest.items():
        if stored.get("decision") != recheck.get("decision"):
            raise ProtocolFailure(f"{path}: stored outcome differs from its re-check under the current rules")
    if not valid_calls and gave_no_answer([recheck.get("failure", "") for _, _, recheck in latest.values()]):
        # No valid answer in MAX_ATTEMPTS retryable calls: the review gives none
        # (`decision-rule.md`, "Calls that give no answer").
        return None
    if len(valid_calls) != 1:
        raise ProtocolFailure(f"{case['case_id']} in {directory}: valid calls {sorted(valid_calls)}")
    path, stored, _ = latest[valid_calls.pop()]
    return sha256_path(path), stored


def _review_order_key(case_id: str, review_sha256: str) -> str:
    return sha256_bytes(f"{REVIEW_ORDER_SEED}|{case_id}|{review_sha256}".encode("utf-8"))


def session_id(record: dict) -> str:
    """The Claude Code session that made a stored call (its init event's `session_id`)."""
    init = next(e for e in record["events"] if e.get("type") == "system" and e.get("subtype") == "init")
    if not init.get("session_id"):
        raise ProtocolFailure(f"{record['case_id']}: a call without a session ID")
    return init["session_id"]


def reviewer_decisions(stage: str, queue: dict, records: Path) -> dict[str, dict[str, tuple[str, dict] | None]]:
    """Each case's two independent reviews (None for a reviewer that gave no answer in
    MAX_ATTEMPTS retryable calls). Every deciding call must be its own session: the same stored
    call under both labels (or under two cases) would turn one judgment into an agreement, so a
    repeated session fails loud."""
    role = ROLES[f"{stage}_reviewer"]
    inputs = role_inputs(role)
    decisions = {
        case["case_id"]: {
            label: decided_record(records / f"reviewer-{label}", case, role, inputs)
            for label in REVIEWERS
        }
        for case in queue["cases"]
    }
    sessions = collections.Counter(
        session_id(review[1]) for by_label in decisions.values() for review in by_label.values() if review
    )
    repeated = sorted(session for session, count in sessions.items() if count > 1)
    if repeated:
        raise ProtocolFailure(f"stage {stage}: one call decides more than one review: {repeated}")
    return decisions


def reconciliation_queue(stage: str, queue: dict, records: Path) -> dict:
    """The cases two reviewers disagree on, with both reviews under opaque labels."""
    fields = STAGE_FIELDS[stage]
    reviews = reviewer_decisions(stage, queue, records)
    items = []
    for case in queue["cases"]:
        by_label = reviews[case["case_id"]]
        if None in by_label.values():
            continue  # settled without a reconciler (build_consensus)
        disputed = [
            field for field in fields
            if by_label["A"][1]["decision"][field] != by_label["B"][1]["decision"][field]
        ]
        if not disputed:
            continue
        ordered = sorted(by_label.values(), key=lambda item: _review_order_key(case["case_id"], item[0]))
        items.append({
            "case_id": case["case_id"],
            "evidence_sha256": case["evidence_sha256"],
            "case": case,
            "disputed_questions": disputed,
            "reviews": [
                {
                    "label": f"review-{index}",
                    **{key: record["decision"][key] for key in (
                        *fields, *REVIEW_EXTRA_KEYS[stage], "reasoning", *CITATION_KEYS[stage])},
                }
                for index, (_, record) in enumerate(ordered, 1)
            ],
        })
    return {"schema_version": RECONCILIATION_SCHEMA_VERSION, "stage": stage, "cases": items}


def build_consensus(stage: str, queue_path: Path, records: Path) -> dict:
    """Every case's outcome per question: reviewer agreement, or the reconciler's cited override
    (or its uncited insufficient_evidence when no page it opened loaded)."""
    queue = read_json(queue_path)
    fields = STAGE_FIELDS[stage]
    reviews = reviewer_decisions(stage, queue, records)
    reconcile = {item["case_id"]: item for item in reconciliation_queue(stage, queue, records)["cases"]}
    reconciler = ROLES[f"{stage}_reconciler"]
    reconciler_inputs = role_inputs(reconciler)
    decisions = []
    for case in sorted(queue["cases"], key=lambda c: c["case_id"]):
        by_label = reviews[case["case_id"]]
        override = None
        if case["case_id"] in reconcile:
            override = decided_record(
                records / "reconciler", reconcile[case["case_id"]], reconciler, reconciler_inputs
            )
        decision = {"case_id": case["case_id"], "evidence_sha256": case["evidence_sha256"]}
        resolutions = {}
        if None in by_label.values():
            # A reviewer gave no answer: the case is unsettled (`decision-rule.md`).
            for field in fields:
                decision[field] = "insufficient_evidence"
                resolutions[field] = {"method": "no_valid_review", "reviewers_without_an_answer": sorted(
                    label for label, review in by_label.items() if review is None)}
            decision["field_resolutions"] = resolutions
            decisions.append(decision)
            continue
        for field in fields:
            sources = sorted(
                ({"review_sha256": sha, "outcome": record["decision"][field]}
                 for sha, record in by_label.values()),
                key=lambda item: item["review_sha256"],
            )
            if sources[0]["outcome"] == sources[1]["outcome"]:
                decision[field] = sources[0]["outcome"]
                resolutions[field] = {"method": "agreement", "source_outcomes": sources}
                continue
            if override is None:
                # The reconciler gave no answer: the disputed question is unsettled.
                decision[field] = "insufficient_evidence"
                resolutions[field] = {"method": "no_valid_reconciliation", "source_outcomes": sources}
                continue
            resolution = override[1]["decision"]["resolutions"][field]
            decision[field] = resolution["outcome"]
            # A reconciler may answer insufficient_evidence with no citation when no page it
            # opened loaded (the schema allows that only for insufficient_evidence); that is
            # recorded as what it is, not as a cited override.
            resolutions[field] = {
                "method": "explicit_cited_override" if resolution["citations"]
                else "reconciler_insufficient_evidence_without_source",
                "source_outcomes": sources,
                "reconciler_record_sha256": override[0],
                "rationale": resolution["rationale"],
                "citations": resolution["citations"],
            }
        decision["field_resolutions"] = resolutions
        decisions.append(decision)
    return {
        "schema_version": CONSENSUS_SCHEMA_VERSION,
        "stage": stage,
        "queue_sha256": sha256_path(queue_path),
        "roles": {
            name: role_bindings(ROLES[name])
            for name in (f"{stage}_reviewer", f"{stage}_reconciler")
        },
        "decisions": decisions,
    }


def verify_consensus(stage: str, consensus_path: Path, queue_path: Path, records: Path) -> dict:
    consensus = read_json(consensus_path)
    if consensus != build_consensus(stage, queue_path, records):
        raise ProtocolFailure(f"{consensus_path} is not the consensus of the stored {stage} records")
    return consensus


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare-reconciliation", "freeze-consensus"):
        sub = commands.add_parser(name)
        sub.add_argument("--stage", choices=sorted(STAGE_FIELDS), required=True)
        sub.add_argument("--queue", type=Path, required=True)
        sub.add_argument("--records", type=Path, required=True,
                         help="private dir holding reviewer-A/, reviewer-B/ and reconciler/")
        sub.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare-reconciliation":
        value = reconciliation_queue(args.stage, read_json(args.queue), args.records)
        write_new(args.out, value)
        print(f"Stage {args.stage}: {len(value['cases'])} cases to reconcile")
    else:
        value = build_consensus(args.stage, args.queue, args.records)
        write_new(args.out, value)
        overrides = sum(
            r["method"] == "explicit_cited_override"
            for d in value["decisions"] for r in d["field_resolutions"].values()
        )
        print(f"Stage {args.stage}: {len(value['decisions'])} cases frozen, {overrides} cited overrides")


if __name__ == "__main__":
    main()
