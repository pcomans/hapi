#!/usr/bin/env python3
"""#369: what the three resolver fixes change, on the frozen corpus and #361's mention ledger.

Resolves the same inputs with the resolver of `BASE_COMMIT` (main before #369, the tree #361
froze) and with the working tree's, and compares:

* every dynasty value of the corpus's canonical records, read by `royal_women.single_dynasty`;
* every distinct single-identity ruler mention text of the ledger, and every Dodson & Hilton
  family name, resolved by `graph_kings.GraphKings`;
* every royal-woman-cued single-identity ruler mention, resolved as #361 resolved it (the
  record's kings from its uncued mentions, its single dynasty, the TLA-linked spellings), by
  `resolve_royal_woman` on the base tree and `resolve_ruler_mention` on the working tree, so
  all three fixes act together.

Writes counts and the artifact ids of the changed cued mentions; no museum text.

    uv run python docs/evaluations/resolver-gaps-369/scripts/measure_resolver_change.py \\
        --archive <corpus archive> --ledger <#361 mentions.ndjson.gz> --out <json>
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import inspect
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
BASE_COMMIT = "d82b7ef9f689bbf2e01b9fdc81eb76b070fa83b4"
ARCHIVE_SHA256 = "f4aabc2fc03b3ee0b5965bb9b27129e0ac482dae086c6124dd0d73d70276cc5b"
ARTIFACTS_MEMBER = "hapi-museum-corpus-2026-08-27/data/artifacts.ndjson.gz"
# #361's mention ledger (`ruler-reregistration-2026-10-15/results/ledger-diff.json`).
LEDGER_SHA256 = "98ec263a0aa2f295758d98e60676d830ea9dd698b66739134e3af275641ead26"
# The working-tree files the "after" side is measured from.
MEASURED = ("pipeline/pipeline/authority/royal_women.py", "pipeline/pipeline/authority/graph_kings.py")
TREE_PATHS = ("pipeline/pipeline", "docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts",
              "web-claimgraph/data")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require_sha(path: Path, expected: str) -> None:
    actual = sha256_path(path)
    if actual != expected:
        raise ValueError(f"{path}: SHA-256 {actual}, expected {expected}")


def dynasty_values(archive: Path) -> dict[str, int]:
    with tarfile.open(archive, "r:gz") as bundle:
        member = bundle.extractfile(ARTIFACTS_MEMBER)
        if member is None:
            raise ValueError(f"{ARTIFACTS_MEMBER} is not a regular file")
        rows = [json.loads(line) for line in gzip.GzipFile(fileobj=io.BytesIO(member.read()))]
    return dict(collections.Counter(r["dynasty"] for r in rows if r.get("dynasty")))


def resolve_side(root: Path, ledger: Path, values: list[str]) -> dict:
    """One tree's answers (run in a fresh interpreter, so each tree's `pipeline` is its own)."""
    sys.path.insert(0, str(root / "pipeline"))
    from pipeline.authority import graph_kings, royal_women as rw, tla_links

    module = graph_kings.load_linkability(
        root / "docs/evaluations/hapi-linkability-mvp-2026-08-28/scripts/run_linkability.py")
    kings = graph_kings.GraphKings(module, json.loads(module.GRAPH.read_text(encoding="utf-8")))
    women = rw.load_royal_women()
    index = rw.build_index(women, kings, linked_spellings=tla_links.linked_spellings())
    mentions = [json.loads(line) for line in gzip.open(ledger, "rt", encoding="utf-8")]
    ruler = [m for m in mentions if m["entity_type"] == "ruler" and m["expression_type"] == "single_identity"]
    record_kings: dict[str, set[str]] = collections.defaultdict(set)
    for m in ruler:
        if not rw.royal_woman_cued(m["field_value"], m["span_start"]):
            found = kings.resolve(m["mention_text"])
            if found["status"] == "resolved":
                record_kings[m["artifact_id"]].update(found["target_ids"])
    field_api = "field_value" in inspect.signature(rw.resolve_ruler_mention).parameters
    cued = {}
    for m in ruler:
        if not rw.royal_woman_cued(m["field_value"], m["span_start"]):
            continue
        dynasty = rw.single_dynasty(m["record_dynasty"])
        if field_api:
            found = rw.resolve_ruler_mention(index, kings, m["field_value"], m["span_start"], m["span_end"],
                                             record_king_ids=record_kings[m["artifact_id"]], record_dynasty=dynasty)
        else:
            found = rw.resolve_royal_woman(index, m["mention_text"], record_king_ids=record_kings[m["artifact_id"]],
                                           record_dynasty=dynasty)
        cued[m["mention_id"]] = {"artifact_id": m["artifact_id"], "status": found["status"],
                                 "target_ids": found["target_ids"], "context_rule": found["context_rule"]}
    return {
        "dynasty": {v: rw.single_dynasty(v) for v in values},
        "mention_texts": {t: kings.resolve(t)["target_ids"] for t in sorted({m["mention_text"] for m in ruler})},
        "family_names": {n: kings.resolve(n)["target_ids"] for n in sorted({n for w in women for n in w.family_names})},
        "cued": cued,
    }


def run_side(root: Path, ledger: Path, values: list[str]) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as handle:
        json.dump(values, handle)
        handle.flush()
        out = subprocess.run([sys.executable, "-I", __file__, "--side", str(root), "--ledger", str(ledger),
                              "--values", handle.name], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def base_tree(directory: Path) -> Path:
    archive = subprocess.run(["git", "-C", str(REPO), "archive", BASE_COMMIT, *TREE_PATHS],
                             check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        bundle.extractall(directory, filter="data")
    return directory


def measure(archive: Path, ledger: Path) -> dict:
    require_sha(archive, ARCHIVE_SHA256)
    require_sha(ledger, LEDGER_SHA256)
    counts = dynasty_values(archive)
    values = sorted(counts)
    with tempfile.TemporaryDirectory() as tmp:
        before = run_side(base_tree(Path(tmp)), ledger, values)
    after = run_side(REPO, ledger, values)
    read = [v for v in values if before["dynasty"][v] != after["dynasty"][v]]
    if any(before["dynasty"][v] is not None for v in read):
        raise ValueError("a dynasty value the base tree read is read differently")

    def changed(section: str) -> int:
        return sum(before[section][k] != after[section][k] for k in before[section])

    cued_changes = [{"artifact_id": before["cued"][k]["artifact_id"],
                     "before": {f: before["cued"][k][f] for f in ("status", "target_ids", "context_rule")},
                     "after": {f: after["cued"][k][f] for f in ("status", "target_ids", "context_rule")}}
                    for k in sorted(before["cued"])
                    if (before["cued"][k]["status"], before["cued"][k]["target_ids"])
                    != (after["cued"][k]["status"], after["cued"][k]["target_ids"])]
    return {
        "schema_version": "hapi-369-resolver-change/1",
        "base_commit": BASE_COMMIT,
        "measured_sha256": {path: sha256_path(REPO / path) for path in MEASURED},
        "corpus_archive_sha256": ARCHIVE_SHA256,
        "ledger_gzip_sha256": LEDGER_SHA256,
        "dynasty_values": {"distinct": len(values), "newly_read_as_one_dynasty": len(read),
                           "records_newly_read": sum(counts[v] for v in read), "read_differently": 0},
        "king_mention_texts": {"distinct": len(before["mention_texts"]), "changed": changed("mention_texts")},
        "dh_family_names": {"distinct": len(before["family_names"]), "changed": changed("family_names")},
        "royal_woman_cued_mentions": {"count": len(before["cued"]), "changed": len(cued_changes),
                                      "changes": cued_changes},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--side", type=Path)
    parser.add_argument("--values", type=Path)
    args = parser.parse_args()
    if args.side:
        values = json.loads(args.values.read_text(encoding="utf-8"))
        print(json.dumps(resolve_side(args.side, args.ledger, values), ensure_ascii=False))
        return
    result = measure(args.archive, args.ledger)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
