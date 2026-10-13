#!/usr/bin/env python3
"""#337 v4 Rule 14 gate (prompt audit round 12): were the shown museum records equally
openable in every case class?

Without the v3 exception route, a record that will not load forces `insufficient_evidence`,
which is class-neutral only if the loaded rate is. From the deciding Stage 1 reviewer calls
(re-validated from their stored events), counts `open_page` results that loaded, by museum
and, for museum record pages, by the transition class of every scored case the review unit
belongs to (from the private answer key). Writes aggregate counts only: no case, outcome or
class of any single unit.

    pipeline/.venv/bin/python .../scripts/page_load_gate.py --stage-1-queue <queue> \\
      --stage-1-records <private stage-1 dir> --private-answer-key <key> --out <json>
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from urllib.parse import urlparse

from review_protocol import REVIEWERS, ROLES, decided_record, read_json, role_inputs, sha256_path, validate, write_atomic

MUSEUM_HOSTS = {
    "met": ("metmuseum.org",),
    "brooklyn": ("brooklynmuseum.org",),
    "harvard": ("harvardartmuseums.org", "hvrd.art"),
}


def museum_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    for museum, domains in MUSEUM_HOSTS.items():
        if any(host == d or host.endswith("." + d) for d in domains):
            return museum
    return "other"


def gate(queue_path: Path, records: Path, answer_key_path: Path) -> dict:
    classes = collections.defaultdict(set)
    for case in read_json(answer_key_path)["cases"]:
        for arm in ("literal", "authority"):
            for node in case["arm_native"][arm]["nodes"]:
                classes[node["stage_1_review_unit_id"]].add(case["transition_class"])
    role = ROLES["stage_1_reviewer"]
    inputs = role_inputs(role)
    by_museum = collections.defaultdict(lambda: {"loaded": 0, "opened": 0})
    by_class = collections.defaultdict(lambda: {"loaded": 0, "opened": 0})
    calls = calls_without_a_loaded_page = 0
    for case in read_json(queue_path)["cases"]:
        for label in REVIEWERS:
            _, stored = decided_record(records / f"reviewer-{label}", case, role, inputs)
            record = validate({"events": stored["events"]}, case, role, inputs["schema"])
            calls += 1
            calls_without_a_loaded_page += not any(o["loaded"] for o in record["page_opens"])
            for opened in record["page_opens"]:
                museum = museum_of(opened["url"])
                by_museum[museum]["opened"] += 1
                by_museum[museum]["loaded"] += opened["loaded"]
                if museum != "other":
                    for transition_class in classes[case["case_id"]]:
                        by_class[transition_class]["opened"] += 1
                        by_class[transition_class]["loaded"] += opened["loaded"]
    return {
        "schema_version": "hapi-337-v4-page-load-gate/1",
        "inputs": {"stage_1_queue_sha256": sha256_path(queue_path),
                   "private_answer_key_sha256": sha256_path(answer_key_path)},
        "deciding_calls": calls,
        "calls_without_a_loaded_page": calls_without_a_loaded_page,
        "open_page_by_museum": dict(sorted(by_museum.items())),
        "museum_record_opens_by_transition_class": dict(sorted(by_class.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-1-queue", type=Path, required=True)
    parser.add_argument("--stage-1-records", type=Path, required=True)
    parser.add_argument("--private-answer-key", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    value = gate(args.stage_1_queue, args.stage_1_records, args.private_answer_key)
    write_atomic(args.out, value)
    print(json.dumps(value, indent=1))


if __name__ == "__main__":
    main()
