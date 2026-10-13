#!/usr/bin/env python3
"""#337 re-registration: the per-case review protocol shared by every stage.

Each role (Stage 1 and Stage 2 reviewer and reconciler) answers one case per call through
headless Claude Code (`run_harness_review.py`). This module owns what is common to all of
them: the audited prompt, response schema and system prompt of each role, the exact model
input of a case, the validation of a stored call from its saved event stream alone (so a
decision is re-checked without calling the model again, Constitutional Rule 13), the
reconciliation queue of the cases two reviewers disagree on, and the frozen consensus.

Consensus (Rule 2): a question two reviewers answer identically is settled by that
agreement. A disputed question is settled only by the reconciler's explicit override, which
must cite at least one page it opened, unless it answers insufficient_evidence because no
page it opened loaded; nothing else (reviewer order, label, or a tie-break) can
settle it, and a missing override fails loud. A consensus file is accepted only if it is
exactly what this module rebuilds from the stored records.

    pipeline/.venv/bin/python .../scripts/review_protocol.py prepare-reconciliation \\
      --stage 1 --queue <stage-1-queue.json> --records <private stage-1 dir> --out <file>
    pipeline/.venv/bin/python .../scripts/review_protocol.py freeze-consensus \\
      --stage 1 --queue <stage-1-queue.json> --records <private stage-1 dir> --out <file>
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import jsonschema

EVALUATION_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PROMPT_PATH = EVALUATION_ROOT / "launcher-instructions" / "review-system-v3.txt"
SERVED_MODEL = "claude-sonnet-5-5"
# The agents read pages only through `open_page` (open_page_server.py, a headless Chromium):
# Claude Code's WebFetch cannot pass the JavaScript checkpoint in front of the Met and
# Brooklyn collection sites. Web search finds pages; it is never a source.
OPEN_PAGE_SERVER = "museum-browser"
OPEN_PAGE_SERVER_PATH = EVALUATION_ROOT / "scripts" / "open_page_server.py"
OPEN_PAGE_TOOL = f"mcp__{OPEN_PAGE_SERVER}__open_page"
TOOLS = ("WebSearch", OPEN_PAGE_TOOL)
# Titles of the bot-challenge interstitials (Vercel, Cloudflare): such a page never loaded.
CHECKPOINT_TITLES = ("Security Checkpoint", "Just a moment")
# Wikidata is never a source (role prompts), and this public repository lives on GitHub.
BLOCKED_DOMAINS = ("wikidata.org", "github.com", "raw.githubusercontent.com")
SESSION_LIMIT_TEXT = "hit your session limit"
REVIEWERS = ("A", "B")
# Fixed seed for the order in which a reconciler sees the two reviews: a hash of the seed,
# the case and the review's record hash, so neither reviewer label comes first by rule.
REVIEW_ORDER_SEED = "hapi-337-reregistration-2026-10-11-reconciliation-order-v1"
CONSENSUS_SCHEMA_VERSION = "hapi-337-reregistration-consensus/1"
RECONCILIATION_SCHEMA_VERSION = "hapi-337-reregistration-reconciliation-queue/1"
ATTEMPT_RE = re.compile(r"^(?P<case>.+)\.attempt-(?P<n>[1-9][0-9]*)\.json$")


@dataclass(frozen=True)
class Role:
    name: str
    prompt: Path
    schema: Path
    fields: tuple[str, ...]
    reconciler: bool


STAGE_FIELDS = {"1": ("same_entity", "useful_granularity"), "2": ("canonical_identity",)}
ROLES = {
    role.name: role
    for role in (
        Role("stage_1_reviewer", EVALUATION_ROOT / "prompts/stage-1-reviewer-v4.txt",
             EVALUATION_ROOT / "raw-response-contracts/stage-1-reviewer-case-v2.schema.json",
             STAGE_FIELDS["1"], False),
        Role("stage_1_reconciler", EVALUATION_ROOT / "prompts/stage-1-reconciler-v4.txt",
             EVALUATION_ROOT / "raw-response-contracts/stage-1-reconciler-case-v2.schema.json",
             STAGE_FIELDS["1"], True),
        Role("stage_2_reviewer", EVALUATION_ROOT / "prompts/stage-2-reviewer-v4.txt",
             EVALUATION_ROOT / "raw-response-contracts/stage-2-reviewer-case-v2.schema.json",
             STAGE_FIELDS["2"], False),
        Role("stage_2_reconciler", EVALUATION_ROOT / "prompts/stage-2-reconciler-v4.txt",
             EVALUATION_ROOT / "raw-response-contracts/stage-2-reconciler-case-v2.schema.json",
             STAGE_FIELDS["2"], True),
    )
}
# Private-only keys that must never reach a model input (arms, classes, hidden bindings).
MODEL_INPUT_FORBIDDEN_KEYS = {
    "arm_native", "artifact_id", "artifact_ids", "artifact_ids_by_side", "case_binding_sha256",
    "mention_id", "mention_ids", "mention_ids_by_side", "proposed_target_id",
    "stage_1_review_unit_id", "transition_class",
}


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


def role_inputs(role: Role) -> dict:
    return {
        "prompt": role.prompt.read_text("utf-8"),
        "schema": read_json(role.schema),
        "system_prompt": SYSTEM_PROMPT_PATH.read_text("utf-8"),
    }


def role_bindings(role: Role) -> dict:
    return {
        "prompt": {"path": role.prompt.name, "sha256": sha256_path(role.prompt)},
        "schema": {"path": role.schema.name, "sha256": sha256_path(role.schema)},
        "system_prompt": {"path": SYSTEM_PROMPT_PATH.name, "sha256": sha256_path(SYSTEM_PROMPT_PATH)},
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


def compose_user_content(case: dict, role_prompt: str, schema: dict) -> str:
    leaks = forbidden_keys(case)
    if leaks:
        raise ProtocolFailure(f"model input carries private keys: {leaks}")
    return "\n\n".join([
        role_prompt.strip(),
        "Response schema:\n" + json.dumps(schema, indent=1, sort_keys=True),
        "Case:\n" + json.dumps(case, indent=1, sort_keys=True, ensure_ascii=False),
    ])


def _blocked(url: str | None) -> bool:
    host = (urlparse(url or "").hostname or "").lower()
    return any(host == domain or host.endswith("." + domain) for domain in BLOCKED_DOMAINS)


def _page(url: str | None) -> tuple[str, str]:
    """A URL's page identity: host without `www.` and path without trailing slash. The query
    is dropped, since a fetch of `.../object/292258?position=0` reads the cited object page."""
    parsed = urlparse((url or "").strip())
    return (parsed.hostname or "").lower().removeprefix("www."), parsed.path.rstrip("/")


def opened_pages(record: dict) -> set[tuple[str, str]]:
    """The pages a validated record shows the call read: every `open_page` result that loaded,
    under both its requested and its final (post-redirect) URL."""
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

    Reads only `record["events"]`, so a stored attempt is re-checked without calling the
    model again (Rule 13)."""

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
            record["page_opens"].append({
                "url": calls[b["tool_use_id"]]["input"].get("url"),
                **({"loaded": False, "error": opened["error"]} if "error" in opened else {
                    key: opened[key] for key in ("requested_url", "final_url", "status", "title", "loaded")
                }),
            })
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
    if not record["stated_text"]:
        record["failure"] = "no final text"
        return record
    final_text = record["stated_text"][-1].strip()
    record["final_text"] = final_text
    if SESSION_LIMIT_TEXT in final_text:
        record["failure"] = f"Claude Code session limit: {final_text}"
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
    if decision["case_id"] != case["case_id"] or decision["evidence_sha256"] != case["evidence_sha256"]:
        record["failure"] = "decision does not echo the case ID and evidence hash exactly"
        return record
    if role.reconciler and sorted(decision["resolutions"]) != sorted(case["disputed_questions"]):
        record["failure"] = (
            f"invalid decision: resolves {sorted(decision['resolutions'])}, "
            f"not the disputed questions {sorted(case['disputed_questions'])}"
        )
        return record
    cited = decision.get("citations", []) + [
        url for resolution in decision.get("resolutions", {}).values() for url in resolution["citations"]
    ]
    touched = [r["url"] for r in record["web_search_results"]] + [o["url"] for o in record["page_opens"]] + cited
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


def decided_record(directory: Path, case: dict, role: Role, inputs: dict) -> tuple[str, dict]:
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
    user_content = compose_user_content(case, inputs["prompt"], inputs["schema"])
    latest, valid_calls = {}, set()
    for path in paths:
        if ATTEMPT_RE.match(path.name)["case"] != case["case_id"]:
            raise ProtocolFailure(f"unexpected record name: {path}")
        stored = read_json(path)
        if stored["user_content"] != user_content or stored["system_prompt"] != inputs["system_prompt"]:
            raise ProtocolFailure(f"{path}: not composed from the current prompt, schema and case")
        if "events" not in stored:
            if "decision" in stored:
                raise ProtocolFailure(f"{path}: a decision without its event stream")
            continue
        call = stored.get("revalidated_from", path.name)
        if call != path.name:
            source = directory / call
            if not source.exists() or read_json(source).get("events") != stored["events"]:
                raise ProtocolFailure(f"{path}: a re-check whose events are not those of {call}")
        recheck = validate({"events": stored["events"]}, case, role, inputs["schema"])
        if "decision" in recheck:
            valid_calls.add(call)
        latest[call] = (path, stored, recheck)
    for call, (path, stored, recheck) in latest.items():
        if stored.get("decision") != recheck.get("decision"):
            raise ProtocolFailure(f"{path}: stored outcome differs from its re-check under the current rules")
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


def reviewer_decisions(stage: str, queue: dict, records: Path) -> dict[str, dict[str, tuple[str, dict]]]:
    """Each case's two independent reviews. Every deciding call must be its own session: the
    same stored call under both labels (or under two cases) would turn one judgment into an
    agreement, so a repeated session fails loud."""
    role = ROLES[f"stage_{stage}_reviewer"]
    inputs = role_inputs(role)
    decisions = {
        case["case_id"]: {
            label: decided_record(records / f"reviewer-{label}", case, role, inputs)
            for label in REVIEWERS
        }
        for case in queue["cases"]
    }
    sessions = collections.Counter(
        session_id(record) for by_label in decisions.values() for _, record in by_label.values()
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
                        *fields, "reasoning", "citations")},
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
    reconciler = ROLES[f"stage_{stage}_reconciler"]
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
            for name in (f"stage_{stage}_reviewer", f"stage_{stage}_reconciler")
        },
        "decisions": decisions,
    }


def verify_consensus(stage: str, consensus_path: Path, queue_path: Path, records: Path) -> dict:
    consensus = read_json(consensus_path)
    if consensus != build_consensus(stage, queue_path, records):
        raise ProtocolFailure(f"{consensus_path} is not the consensus of the stored Stage {stage} records")
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
