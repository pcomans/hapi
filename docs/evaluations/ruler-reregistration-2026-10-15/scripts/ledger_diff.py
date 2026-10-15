#!/usr/bin/env python3
"""#361: what this registration's extractor changes against #337 v10's, on the frozen corpus.

Runs both extractors on the archive and compares their ledgers by mention ID: every v10
mention must be present and unchanged (all fields but the new `record_dynasty`), and every new
mention must follow one of the royal-woman cues. Also counts the new ledger's mentions after a
royal-woman cue that the resolver would not read as cued (`royal_women.royal_woman_cued`):
such a mention would reach the kings, so the count must be 0. Writes counts only, no museum
text.

    python3 -I scripts/ledger_diff.py --archive <corpus archive> --repo-root <repo> --out <json>
"""

from __future__ import annotations

import argparse
import collections
import gzip
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
V10 = HERE.parents[1] / "authority-independent-control-2026-10-11" / "scripts" / "extract_mentions.py"
ROYAL_WOMAN_CUES = ("queen mother", "great royal wife", "god's wife of amun", "divine adoratrice of amun", "king's great wife", "king's wife", "king's mother",
                    "king's daughter", "god's wife", "divine adoratrice", "princess")


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ledger(extractor, archive: Path, work: Path) -> dict[str, dict]:
    ledger, manifest = work / "ledger.ndjson.gz", work / "manifest.json"
    extractor.build_from_archive(archive, ledger, manifest)
    return {row["mention_id"]: row for row in map(json.loads, gzip.open(ledger, "rt")) if "mention_id" in row}


def diff(archive: Path, repo_root: Path) -> dict:
    sys.path.insert(0, str(repo_root / "pipeline"))
    from pipeline.authority import royal_women
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "a").mkdir()
        (Path(tmp) / "b").mkdir()
        old = _ledger(_module("_v10_extractor", V10), archive, Path(tmp) / "a")
        new = _ledger(_module("_361_extractor", HERE / "extract_mentions.py"), archive, Path(tmp) / "b")
    lost = sorted(set(old) - set(new))
    changed = sorted(i for i in set(old) & set(new)
                     if {k: v for k, v in new[i].items() if k != "record_dynasty"} != old[i])
    added = [new[i] for i in sorted(set(new) - set(old))]
    by_cue: collections.Counter = collections.Counter()
    for row in added:
        before = row["field_value"][:row["span_start"]].rstrip(" :-,\t").lower().replace("’", "'")
        cue = next((c for c in ROYAL_WOMAN_CUES if before.endswith(c)), None)
        by_cue[cue or "none"] += 1
    cued_by_extractor = [row for row in new.values() if row["entity_type"] == "ruler" and row["extraction_method"]
                         == "explicit_royal_cue_grammar" and any(
                             row["field_value"][:row["span_start"]].rstrip(" :-,\t").lower().replace("’", "'")
                             .endswith(c) for c in (*ROYAL_WOMAN_CUES, "queen"))]
    not_read_as_cued = sum(not royal_women.royal_woman_cued(r["field_value"], r["span_start"]) for r in cued_by_extractor)
    return {
        "schema_version": "hapi-361-ledger-diff/1",
        "v10_mentions": len(old), "new_mentions": len(new),
        "lost": len(lost), "changed_ignoring_record_dynasty": len(changed), "added": len(added),
        "added_by_royal_woman_cue": dict(sorted(by_cue.items())),
        "royal_woman_cued_mentions": len(cued_by_extractor),
        "royal_woman_cued_mentions_the_resolver_does_not_read_as_cued": not_read_as_cued,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = diff(args.archive, args.repo_root.resolve())
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
