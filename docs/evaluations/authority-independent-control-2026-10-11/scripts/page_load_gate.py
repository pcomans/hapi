#!/usr/bin/env python3
"""#337 Rule 14 gate (prompt audit round 12): could the reviewers read citable pages equally
well in every case class, and what did their citations rest on?

Without the v3 exception route, a page that will not load can force `insufficient_evidence`,
which is class-neutral only if the loaded rate is. For the deciding reviewer calls of both
stages (re-validated from their stored events, so `loaded` is the validator's re-derived
flag), counts `open_page` results that loaded: by museum host, by transition class (all
opens, and opens of citable sources), and the hosts whose pages did not load; and counts the
deciding calls' citations by role (`citable-sources.json`: the case's own museums, the
target's own record, or an independent source) and class. A Stage 1
review unit counts toward the class of every scored case it belongs to, a Stage 2 case
toward its own (from the private answer key). Writes aggregate counts only.

Classes are compared within each entity type (site, ruler), because the citable sources
cover sites and rulers unequally (no ruler authority has an openable page). The gate passes
when, in each stage and entity type, every class's loaded rate for opens of citable sources
is within MAX_CLASS_DEVIATION_PERCENTAGE_POINTS of that entity type's overall rate for them. The
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
import json
from pathlib import Path
from urllib.parse import urlparse

from review_protocol import (
    REVIEWERS, ROLES, ProtocolFailure, citable_source_of, decided_record, read_json, role_inputs, sha256_path,
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


def stage_gate(stage: str, queue_path: Path, records: Path, classes_of: dict[str, set[str]]) -> dict:
    role = ROLES[f"stage_{stage}_reviewer"]
    inputs = role_inputs(role)
    counter = lambda: collections.defaultdict(lambda: {"loaded": 0, "opened": 0})  # noqa: E731
    by_museum, all_by_class, citable_by_class = counter(), counter(), counter()
    citations_by_class = collections.defaultdict(collections.Counter)
    not_loaded_by_host = collections.Counter()
    calls = calls_without_a_loaded_page = 0
    for case in read_json(queue_path)["cases"]:
        classes = classes_of.get(case["case_id"])
        if not classes:
            raise ProtocolFailure(f"stage {stage}: {case['case_id']} belongs to no scored case")
        classes = {f"{case['entity_type']}/{transition_class}" for transition_class in classes}
        for label in REVIEWERS:
            _, stored = decided_record(records / f"reviewer-{label}", case, role, inputs)
            record = validate({"events": stored["events"]}, case, role, inputs["schema"])
            calls += 1
            calls_without_a_loaded_page += not any(o["loaded"] for o in record["page_opens"])
            decision = record["decision"]
            for url in decision.get("citations", []) + [
                u for resolution in decision.get("resolutions", {}).values() for u in resolution["citations"]
            ]:
                for transition_class in classes:
                    citations_by_class[transition_class][citable_source_of(url)["role"]] += 1
            for opened in record["page_opens"]:
                museum = museum_of(opened["url"])
                citable = citable_source_of(opened["url"]) is not None
                for bucket in [by_museum[museum]] + [all_by_class[c] for c in classes] + (
                    [citable_by_class[c] for c in classes] if citable else []
                ):
                    bucket["opened"] += 1
                    bucket["loaded"] += opened["loaded"]
                if not opened["loaded"]:
                    not_loaded_by_host[_host(opened["url"])] += 1
    overall_all = {k: sum(v[k] for v in by_museum.values()) for k in ("loaded", "opened")}
    def deviations(by_class: dict) -> dict:
        """Each entity-type/class rate minus the rate of all opens of that entity type."""
        overall = collections.defaultdict(lambda: {"loaded": 0, "opened": 0})
        for key, counts in by_class.items():
            for k in ("loaded", "opened"):
                overall[key.split("/")[0]][k] += counts[k]
        return {key: round(100 * (_rate(counts) - _rate(overall[key.split("/")[0]])), 2)
                for key, counts in sorted(by_class.items())}
    gated = deviations(citable_by_class)
    return {
        "deciding_reviewer_calls": calls,
        "calls_without_a_loaded_page": calls_without_a_loaded_page,
        "opens_by_museum_host": dict(sorted(by_museum.items())),
        "all_opens": overall_all,
        "all_opens_by_transition_class": dict(sorted(all_by_class.items())),
        "all_opens_class_deviation_percentage_points": deviations(all_by_class),
        "citable_opens_by_transition_class": dict(sorted(citable_by_class.items())),
        "citable_opens_class_deviation_percentage_points": gated,
        "not_loaded_opens_by_host": dict(sorted(not_loaded_by_host.items(), key=lambda kv: (-kv[1], kv[0]))),
        "citations_by_transition_class_and_role": {
            c: dict(sorted(roles.items())) for c, roles in sorted(citations_by_class.items())
        },
        "passed": all(abs(d) <= MAX_CLASS_DEVIATION_PERCENTAGE_POINTS for d in gated.values()),
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
        "schema_version": "hapi-337-page-load-gate/3",
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
        raise ProtocolFailure("page-load gate failed: a class's loaded rate for citable sources deviates by more than "
                              f"{MAX_CLASS_DEVIATION_PERCENTAGE_POINTS} percentage points")


if __name__ == "__main__":
    main()
