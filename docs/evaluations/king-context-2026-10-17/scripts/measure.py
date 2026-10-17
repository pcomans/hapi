#!/usr/bin/env python3
"""What resolving kings in their record's context (`pipeline.authority.king_context`) changes, on the
frozen inputs of the per-museum ruler test (`../ruler-per-museum-2026-10-17/`).

Compares, mention by mention, the authority-mode ruler resolutions of that test's frozen run (name
only) with what this tree's code gives on the same mentions and records. Writes counts, and the
mention texts with the record's dynasty field and the new target; no other museum text.

    pipeline/.venv/bin/python docs/evaluations/king-context-2026-10-17/scripts/measure.py \\
        --corpus <corpus archive> --added <added-museums archive> --run <frozen run dir> --out <json>
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "docs/evaluations/ruler-per-museum-2026-10-17/scripts"))
sys.path.insert(0, str(REPO / "docs/evaluations/authority-bridge-338/scripts"))
import make_run  # noqa: E402
from pipeline.enrich import authority_links as al, link_files as lf  # noqa: E402


def measure(corpus: Path, added: Path, run: Path) -> dict:
    canonical, _ = make_run.load_inputs(corpus, added)
    records = {r["id"]: r for r in canonical}
    found = lf.read_rows(run / "mentions.ndjson.gz")
    old = {r["mention_id"]: r for r in lf.read_rows(run / "resolutions-authority.ndjson.gz") if r["entity_type"] == "ruler"}
    authority = al.load_authority()
    new = {r["mention_id"]: r for r in al.resolve_mentions(found, "authority", authority, al.record_contexts(canonical))
           if r["entity_type"] == "ruler"}
    changes: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for mention_id, before in old.items():
        after = new[mention_id]
        if (before["status"], before["target_ids"]) == (after["status"], after["target_ids"]):
            continue
        if before["status"] == "resolved" and after["status"] == "resolved":
            kind = "retargeted"
        elif before["status"] == "resolved":
            kind = f"link_removed:{after['reason']}"
        elif after["status"] == "resolved":
            kind = f"link_added_from_{before['status']}:{after['resolution']['context_rule']}"
        else:
            kind = f"{before['status']}_to_{after['status']}"
        key = f"{before['museum']}|{kind}|{before['mention_text']}|{records[before['artifact_id']].get('dynasty')}|" \
              f"{(after['target_ids'] or [None])[0]}"
        changes[before["museum"]][key] += 1
    kings = authority.kings
    ambiguous = collections.Counter()
    for row in new.values():
        if row["status"] == "ambiguous" and row["authority"] == "kings":
            labels = [kings.label(t).casefold() for t in row["resolution"]["target_ids"]]
            ambiguous["same_label_entries" if len(set(labels)) < len(labels) else "different_kings"] += 1
    return {
        "schema_version": "hapi-king-context-measure/1",
        "run_id": run.name,
        "resolver_version_now": authority.snapshot["resolver_version"],
        "changed_mentions": {m: sum(c.values()) for m, c in sorted(changes.items())},
        "changes": {m: dict(sorted(c.items())) for m, c in sorted(changes.items())},
        "ambiguous_king_mentions_now": dict(sorted(ambiguous.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--added", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = measure(args.corpus, args.added, args.run)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
