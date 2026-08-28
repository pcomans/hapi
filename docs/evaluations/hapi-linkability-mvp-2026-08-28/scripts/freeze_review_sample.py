#!/usr/bin/env python3
"""Freeze the pre-adjudication SILVER review sample deterministically.

Sampling is over mention signatures, weighted explicitly through a high-frequency slot,
and includes deterministic long-tail slots.  No web evidence is read by this script.
"""

from __future__ import annotations

import collections
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path


OUT = Path(os.environ.get("HAPI_EVAL_OUT", "/tmp/hapi-linkability-mvp"))
SEED = "hapi-linkability-mvp-review-v1-2026-08-28"
CORE_LONG_TAIL = {"resolved", "ambiguous", "unmatched"}


def stable_score(*parts: str) -> str:
    return hashlib.sha256("\x1f".join((SEED, *parts)).encode("utf-8")).hexdigest()


def norm(text: str) -> str:
    return " ".join(text.casefold().split())


def main() -> None:
    with gzip.open(OUT / "mentions.ndjson.gz", "rt", encoding="utf-8") as handle:
        mentions = [json.loads(line) for line in handle]

    signatures: dict[tuple, list[dict]] = collections.defaultdict(list)
    for mention in mentions:
        key = (
            mention["museum"], mention["entity_type"], mention["status"],
            mention["expression_type"], norm(mention["mention_text"]),
            tuple(mention["target_ids"]),
        )
        signatures[key].append(mention)

    signature_rows = []
    for key, rows in signatures.items():
        artifacts = sorted({row["artifact_id"] for row in rows})
        representative = min(rows, key=lambda row: (row["artifact_id"], row["mention_id"]))
        signature_rows.append({
            "key": key,
            "museum": key[0], "entity_type": key[1], "status": key[2],
            "expression_type": key[3], "normalized_mention": key[4],
            "target_ids": list(key[5]), "artifact_frequency": len(artifacts),
            "mention_frequency": len(rows), "representative": representative,
        })

    cells: dict[tuple, list[dict]] = collections.defaultdict(list)
    for row in signature_rows:
        cells[(row["museum"], row["entity_type"], row["status"])].append(row)

    selected: list[tuple[str, dict]] = []
    selected_mentions = set()
    cell_manifest = []
    for cell in sorted(cells):
        rows = cells[cell]
        high = min(
            rows,
            key=lambda row: (
                -row["artifact_frequency"], row["normalized_mention"],
                row["expression_type"], row["representative"]["mention_id"],
            ),
        )
        selected.append(("high_frequency_cell", high))
        selected_mentions.add(high["representative"]["mention_id"])
        slots = ["high_frequency_cell"]

        want_long_tail = (
            cell[2] in CORE_LONG_TAIL and cell[1] in {"ruler", "site", "tomb_monument"}
        ) or cell[2] == "authority_unavailable"
        if want_long_tail:
            candidates = [row for row in rows if row["representative"]["mention_id"] not in selected_mentions]
            if candidates:
                minimum_frequency = min(row["artifact_frequency"] for row in candidates)
                tails = [row for row in candidates if row["artifact_frequency"] == minimum_frequency]
                tail = min(
                    tails,
                    key=lambda row: stable_score(
                        *cell, row["normalized_mention"], row["representative"]["mention_id"]
                    ),
                )
                selected.append(("deterministic_long_tail", tail))
                selected_mentions.add(tail["representative"]["mention_id"])
                slots.append("deterministic_long_tail")
        cell_manifest.append({
            "museum": cell[0], "entity_type": cell[1], "status": cell[2],
            "available_signatures": len(rows), "selected_slots": slots,
        })

    output = []
    for index, (slot, signature) in enumerate(selected, 1):
        mention = dict(signature["representative"])
        output.append({
            "sample_id": f"review-{index:03d}",
            "sampling_slot": slot,
            "signature_artifact_frequency": signature["artifact_frequency"],
            "signature_mention_frequency": signature["mention_frequency"],
            **mention,
        })

    manifest = {
        "label": "FROZEN BEFORE WEB ADJUDICATION — provisional SILVER review sample, never gold truth or human validation",
        "seed": SEED,
        "input": str(OUT / "mentions.ndjson.gz"),
        "input_sha256": hashlib.sha256((OUT / "mentions.ndjson.gz").read_bytes()).hexdigest(),
        "signature_definition": ["museum", "entity_type", "status", "expression_type", "casefolded whitespace-collapsed mention", "target_ids"],
        "selection_policy": "One highest-artifact-frequency signature per observed museum/entity/status cell; plus one deterministic minimum-frequency signature for every resolved/ambiguous/unmatched ruler/site/tomb cell and authority-unavailable cell when another signature exists.",
        "sample_size": len(output),
        "counts_by_museum": dict(sorted(collections.Counter(row["museum"] for row in output).items())),
        "counts_by_entity_type": dict(sorted(collections.Counter(row["entity_type"] for row in output).items())),
        "counts_by_status": dict(sorted(collections.Counter(row["status"] for row in output).items())),
        "counts_by_sampling_slot": dict(sorted(collections.Counter(row["sampling_slot"] for row in output).items())),
        "cells": cell_manifest,
    }
    (OUT / "review_sample.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "review_sample_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    fields = [
        "sample_id", "sampling_slot", "museum", "entity_type", "status", "expression_type",
        "signature_artifact_frequency", "artifact_id", "artifact_title", "field_path",
        "mention_text", "span_start", "span_end", "resolution_method", "target_ids", "source_url",
    ]
    with (OUT / "review_sample.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in output:
            printable = {key: row.get(key) for key in fields}
            printable["target_ids"] = "|".join(row["target_ids"])
            writer.writerow(printable)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
