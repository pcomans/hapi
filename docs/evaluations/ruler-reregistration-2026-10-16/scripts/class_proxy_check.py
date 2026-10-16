#!/usr/bin/env python3
"""The prompt audit's population-wide proxy check (prompt-audit-2026-10-16.md, P2-b): what the
reviewers see of each museum side in Stage 1, tabulated by the case class it is hidden from.

For every Stage 1 review unit, each side's `record_texts`: the number of entries, the largest
`record_count`, the number of example URLs, the most field paths in one entry, and (already
shown in #361's protocol) `distinct_record_count` and the number of mention variants. A unit is
labelled by every class of the cases whose nodes it reviews. Writes min / median / max per class,
and the largest entry count and unit size, so the audit's table has a committed source.

    uv run python docs/evaluations/ruler-reregistration-2026-10-16/scripts/class_proxy_check.py \\
        --population <private review dir> --out <json>
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import statistics
from pathlib import Path

FEATURES = ("entries", "largest_record_count", "example_urls", "most_field_paths_per_entry",
            "distinct_record_count", "mention_variants")


def side_features(group: dict) -> dict[str, int]:
    texts = group["record_texts"]
    return {
        "entries": len(texts),
        "largest_record_count": max(e["record_count"] for e in texts),
        "example_urls": sum(len(e["example_record_urls"]) for e in texts),
        "most_field_paths_per_entry": max(len(e["fields"]) for e in texts),
        "distinct_record_count": group["distinct_record_count"],
        "mention_variants": len(group["exact_mention_variants"]),
    }


def check(population: Path) -> dict:
    queue_path, key_path = population / "stage-1-queue.json", population / "private-answer-key.json"
    units = json.loads(queue_path.read_text(encoding="utf-8"))["cases"]
    classes = collections.defaultdict(set)
    for case in json.loads(key_path.read_text(encoding="utf-8"))["cases"]:
        for arm in ("literal", "authority"):
            for node in case["arm_native"][arm]["nodes"]:
                classes[node["stage_1_review_unit_id"]].add(case["transition_class"])
    by_class = collections.defaultdict(list)
    for unit in units:
        label = "+".join(sorted(classes[unit["case_id"]]))
        for (group,) in unit["sides"].values():
            by_class[label].append(side_features(group))
    return {
        "schema_version": "hapi-ruler-reregistration-2026-10-16-class-proxy-check/1",
        "stage_1_queue_sha256": hashlib.sha256(queue_path.read_bytes()).hexdigest(),
        "units": len(units),
        "by_class": {
            label: {"sides": len(rows), **{f: {"min": min(r[f] for r in rows),
                                              "median": statistics.median(r[f] for r in rows),
                                              "max": max(r[f] for r in rows)} for f in FEATURES}}
            for label, rows in sorted(by_class.items())
        },
        "most_entries_on_one_side": max(r["entries"] for rows in by_class.values() for r in rows),
        "largest_unit_characters": max(len(json.dumps(unit, ensure_ascii=False)) for unit in units),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--population", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(check(args.population), indent=1, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
