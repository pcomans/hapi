#!/usr/bin/env python3
"""#337 Rule 14 gate (prompt audit round 12): could the reviewers read citable pages equally
well in every case class, and what did their citations rest on?

Without the v3 exception route, a page that will not load can force `insufficient_evidence`,
which is class-neutral only if the loaded rate is. For the deciding reviewer calls of both
stages (re-validated from their stored events, so `loaded` is the validator's re-derived
flag), counts `open_page` results that loaded: by museum host, by transition class (all
opens, and opens of citable sources), and the hosts whose pages did not load; and counts the
deciding calls' citations by role (`citable-sources.json`: the case's own museums, the
target's own record, or an independent source) and by source, per class; and opens by the
browser that served them (local, or Browserbase for the sources routed to it); opens by
citation role (protocol v8: the v7 run's Stage 2 reviewers could almost never open the target
record they were judging, which the class comparison cannot show); by host, the loaded
pages read before their `load` event fired (`open_page_server.py`); and (protocol v10) the
pages read again in Browserbase after the local browser failed, by class and by host. A Stage 1
review unit counts toward the class of every scored case it belongs to, a Stage 2 case
toward its own (from the private answer key). Writes aggregate counts only.

Classes are compared within each entity type (site, ruler), because the citable sources
cover sites and rulers unequally (no ruler authority has an openable page). The gate passes
when, in each stage and entity type, every class's loaded rate for opens of citable sources
is within MAX_CLASS_DEVIATION_PERCENTAGE_POINTS of that entity type's overall rate for them,
and (from 2026-10-14, on Codex review) every class the stage's cases belong to has opened at
least one citable page; an unmeasured class fails the gate. The
rule and threshold were committed before the protocol v5 run (README); all opens are
reported but not gated, since a page outside the citable sources can never be a citation.
It fails loud.

    pipeline/.venv/bin/python .../scripts/page_load_gate.py \\
      --stage-1-queue <queue> --stage-1-records <private stage-1 dir> \\
      --stage-2-queue <queue> --stage-2-records <private stage-2 dir> \\
      --private-answer-key <key> --out <json>
"""

from __future__ import annotations

import argparse
import collections
import ipaddress
import json
import socket
from pathlib import Path
from urllib.parse import urlparse

from review_protocol import (
    cited_urls,
    OPEN_PAGE_TOOL, _open_page_result, REVIEWERS, requestable, ROLES, ProtocolFailure, citable_source_of, decided_record, read_json, role_inputs, sha256_path,
    validate, write_atomic,
)

MAX_CLASS_DEVIATION_PERCENTAGE_POINTS = 5
MUSEUM_HOSTS = {
    "met": ("metmuseum.org",),
    "brooklyn": ("brooklynmuseum.org",),
    "harvard": ("harvardartmuseums.org", "hvrd.art"),
}


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def museum_of(url: str) -> str:
    host = _host(url)
    for museum, domains in MUSEUM_HOSTS.items():
        if any(host == d or host.endswith("." + d) for d in domains):
            return museum
    return "other"


def _rate(counts: dict) -> float:
    return counts["loaded"] / counts["opened"]


def is_local_host(host: str) -> bool:
    """A loopback, link-local, private, shared (CGNAT) or otherwise non-global address, in any
    form Chromium accepts (`127.1`, `0x7f.1`), or a name only a local network resolves
    (`localhost`, `*.local`, `*.internal`, a single label)."""
    host = host.lower().strip("[]").rstrip(".")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        try:
            address = ipaddress.ip_address(socket.inet_aton(host))
        except OSError:  # not an IPv4 literal in any form: a name
            return host == "localhost" or host.endswith((".localhost", ".local", ".internal")) or "." not in host
    return not address.is_global


def open_page_urls(events: list) -> list[str]:
    """Every URL an `open_page` call in this event stream asked for, and every final URL one
    returned, matched to the call by its tool-use id (an error result names no final URL)."""
    calls, urls = {}, []
    for event in events:
        for block in (event.get("message") or {}).get("content") or []:
            if block.get("type") == "tool_use" and block.get("name") == OPEN_PAGE_TOOL:
                calls[block["id"]] = block
                urls.append(block["input"]["url"])
            elif block.get("type") == "tool_result" and block.get("tool_use_id") in calls:
                opened = _open_page_result(block)
                if "error" not in opened:
                    urls.append(opened["final_url"])
    return urls


def local_host_opens(records: Path) -> dict:
    """The URLs `open_page` was asked for or ended on, in every stored call of the stage
    (reviewers and reconciler, deciding or not), and those whose host is local (#358, item 7).
    A stored attempt without an event stream made no call and is skipped by name; a URL
    `open_page` refuses outright is never requested and not counted."""
    scanned, found = 0, set()
    for path in sorted(records.glob("*/*.attempt-*.json")):
        stored = read_json(path)
        if "events" not in stored:
            continue
        for url in open_page_urls(stored["events"]):
            if requestable(url):
                scanned += 1
                if is_local_host(urlparse(url).hostname or ""):
                    found.add(url)
    return {"urls_scanned": scanned, "local": sorted(found)}


def deviations(by_class: dict) -> dict:
    """Each entity-type/class rate minus the rate of all opens of that entity type."""
    overall = collections.defaultdict(lambda: {"loaded": 0, "opened": 0})
    for key, counts in by_class.items():
        for k in ("loaded", "opened"):
            overall[key.split("/")[0]][k] += counts[k]
    return {key: round(100 * (_rate(counts) - _rate(overall[key.split("/")[0]])), 2)
            for key, counts in sorted(by_class.items())}


def class_verdict(expected_classes: set[str], citable_by_class: dict) -> dict:
    """The gate for one stage: every entity-type/class the stage's cases belong to must have
    opened citable pages (a class with none is unmeasured, and fails), and each class's loaded
    rate must be within MAX_CLASS_DEVIATION_PERCENTAGE_POINTS of its entity type's."""
    measured = {key: counts for key, counts in citable_by_class.items() if counts["opened"]}
    missing = sorted(expected_classes - measured.keys())
    gated = deviations(measured)
    return {"deviations": gated, "classes_without_citable_opens": missing,
            "passed": not missing and all(abs(d) <= MAX_CLASS_DEVIATION_PERCENTAGE_POINTS for d in gated.values())}


def stage_gate(stage: str, queue_path: Path, records: Path, classes_of: dict[str, set[str]]) -> dict:
    role = ROLES[f"stage_{stage}_reviewer"]
    inputs = role_inputs(role)
    counter = lambda: collections.defaultdict(lambda: {"loaded": 0, "opened": 0})  # noqa: E731
    by_museum, all_by_class, citable_by_class = counter(), counter(), counter()
    citations_by_class = collections.defaultdict(collections.Counter)
    citation_domains_by_class = collections.defaultdict(collections.Counter)
    by_browser, by_role = counter(), counter()
    loaded_without_load_event_by_host = collections.Counter()
    retried_by_class, retried_by_host = counter(), collections.Counter()
    not_loaded_by_host = collections.Counter()
    calls = reconciler_calls = calls_without_a_loaded_page = 0
    expected_classes: set[str] = set()
    # The deciding calls: both reviewers of every case, and the reconciler of every disputed
    # one (its sources settle the dispute, so its pages count too).
    deciding, classes_of_case = [], {}
    for case in read_json(queue_path)["cases"]:
        classes = classes_of.get(case["case_id"])
        if not classes:
            raise ProtocolFailure(f"stage {stage}: {case['case_id']} belongs to no scored case")
        classes = {f"{case['entity_type']}/{transition_class}" for transition_class in classes}
        expected_classes |= classes
        classes_of_case[case["case_id"]] = classes
        deciding += [(records / f"reviewer-{label}", case, role, inputs, classes) for label in REVIEWERS]
    reconciler = ROLES[f"stage_{stage}_reconciler"]
    reconciler_inputs = role_inputs(reconciler)
    for item in read_json(records / "reconciliation-queue.json")["cases"]:
        deciding.append((records / "reconciler", item, reconciler, reconciler_inputs, classes_of_case[item["case_id"]]))
    for directory, case, call_role, call_inputs, classes in deciding:
        _, stored = decided_record(directory, case, call_role, call_inputs)
        record = validate({"events": stored["events"], "exit_code": stored["exit_code"]}, case, call_role,
                          call_inputs["schema"])
        calls += not call_role.reconciler
        reconciler_calls += call_role.reconciler
        calls_without_a_loaded_page += not any(o["loaded"] for o in record["page_opens"])
        decision = record["decision"]
        for url in cited_urls(decision):
            source = citable_source_of(url)
            for transition_class in classes:
                citations_by_class[transition_class][source["role"]] += 1
                citation_domains_by_class[transition_class][source["domain"] + source.get("path_prefix", "")] += 1
        for opened in record["page_opens"]:
            if "browser" in opened:
                by_browser[opened["browser"]]["opened"] += 1
                by_browser[opened["browser"]]["loaded"] += opened["loaded"]
            museum = museum_of(opened["url"])
            # A URL open_page refuses outright (not http(s)) was never a source request.
            source = citable_source_of(opened["url"]) if requestable(opened["url"]) else None
            citable = source is not None
            # A citable page counts as loaded only if the page it ended on is citable too,
            # as for a citation (a redirect off the list is not an available source).
            citable_loaded = opened["loaded"] and citable_source_of(opened["final_url"]) is not None
            role_counts = by_role[source["role"] if citable else "not_citable"]
            role_counts["opened"] += 1
            role_counts["loaded"] += citable_loaded if citable else opened["loaded"]
            if opened["loaded"] and opened["load_event"] is False:  # a PDF's is None: not measured
                loaded_without_load_event_by_host[_host(opened["url"])] += 1
            if "local_failure" in opened:
                retried_by_host[_host(opened["url"])] += 1
                for c in classes:
                    retried_by_class[c]["opened"] += 1
                    retried_by_class[c]["loaded"] += opened["loaded"]
            for bucket in [by_museum[museum]] + [all_by_class[c] for c in classes]:
                bucket["opened"] += 1
                bucket["loaded"] += opened["loaded"]
            if citable:
                for c in classes:
                    citable_by_class[c]["opened"] += 1
                    citable_by_class[c]["loaded"] += citable_loaded
            if not opened["loaded"]:
                not_loaded_by_host[_host(opened["url"])] += 1
    overall_all = {k: sum(v[k] for v in by_museum.values()) for k in ("loaded", "opened")}
    verdict = class_verdict(expected_classes, citable_by_class)
    return {
        "deciding_reviewer_calls": calls,
        "deciding_reconciler_calls": reconciler_calls,
        "calls_without_a_loaded_page": calls_without_a_loaded_page,
        "opens_by_museum_host": dict(sorted(by_museum.items())),
        "all_opens": overall_all,
        "all_opens_by_transition_class": dict(sorted(all_by_class.items())),
        "all_opens_class_deviation_percentage_points": deviations(all_by_class),
        "classes_without_citable_opens": verdict["classes_without_citable_opens"],
        "citable_opens_by_transition_class": dict(sorted(citable_by_class.items())),
        "citable_opens_class_deviation_percentage_points": verdict["deviations"],
        "not_loaded_opens_by_host": dict(sorted(not_loaded_by_host.items(), key=lambda kv: (-kv[1], kv[0]))),
        "opens_by_browser": dict(sorted(by_browser.items())),
        "opens_by_citation_role": dict(sorted(by_role.items())),
        "loaded_without_load_event_by_host": dict(sorted(
            loaded_without_load_event_by_host.items(), key=lambda kv: (-kv[1], kv[0]))),
        "retried_after_local_failure_by_transition_class": dict(sorted(retried_by_class.items())),
        "local_host_opens_in_any_stored_call": local_host_opens(records),
        "retried_after_local_failure_by_host": dict(sorted(retried_by_host.items(), key=lambda kv: (-kv[1], kv[0]))),
        "citations_by_transition_class_and_source": {
            c: dict(sorted(domains.items(), key=lambda kv: (-kv[1], kv[0])))
            for c, domains in sorted(citation_domains_by_class.items())
        },
        "citations_by_transition_class_and_role": {
            c: dict(sorted(roles.items())) for c, roles in sorted(citations_by_class.items())
        },
        "passed": verdict["passed"],
    }


def gate(stage_1: tuple[Path, Path], stage_2: tuple[Path, Path], answer_key_path: Path) -> dict:
    stage_1_classes, stage_2_classes = collections.defaultdict(set), {}
    for case in read_json(answer_key_path)["cases"]:
        stage_2_classes[case["case_id"]] = {case["transition_class"]}
        for arm in ("literal", "authority"):
            for node in case["arm_native"][arm]["nodes"]:
                stage_1_classes[node["stage_1_review_unit_id"]].add(case["transition_class"])
    stages = {
        "1": stage_gate("1", *stage_1, stage_1_classes),
        "2": stage_gate("2", *stage_2, stage_2_classes),
    }
    value = {
        "schema_version": "hapi-337-page-load-gate/11",
        "inputs": {
            "stage_1_queue_sha256": sha256_path(stage_1[0]),
            "stage_2_queue_sha256": sha256_path(stage_2[0]),
            "private_answer_key_sha256": sha256_path(answer_key_path),
        },
        "max_class_deviation_percentage_points": MAX_CLASS_DEVIATION_PERCENTAGE_POINTS,
        "stages": stages,
        "passed": all(s["passed"] for s in stages.values()),
    }
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-1-queue", type=Path, required=True)
    parser.add_argument("--stage-1-records", type=Path, required=True)
    parser.add_argument("--stage-2-queue", type=Path, required=True)
    parser.add_argument("--stage-2-records", type=Path, required=True)
    parser.add_argument("--private-answer-key", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    value = gate((args.stage_1_queue, args.stage_1_records), (args.stage_2_queue, args.stage_2_records),
                 args.private_answer_key)
    write_atomic(args.out, value)
    print(json.dumps(value, indent=1))
    if not value["passed"]:
        raise ProtocolFailure("page-load gate failed: a class opened no citable page, or its loaded rate for "
                              f"citable sources deviates by more than {MAX_CLASS_DEVIATION_PERCENTAGE_POINTS} "
                              "percentage points")


if __name__ == "__main__":
    main()
