#!/usr/bin/env python3
"""#338: the production enrichment step reproduces what the evaluations measured.

On the frozen corpus archive (`hapi-museum-corpus-2026-08-27`):

1. `pipeline.enrich.mentions.extract_mentions` gives exactly #361's mention ledger, row for
   row.
2. In the authority mode, every ruler mention resolves as #361's current-authority arm did,
   except on the records #369 changed (`resolver-gaps-369/results/resolver-change.json`).
3. Every site mention resolves as the evaluations' linkability adapter resolves it (#337
   v10's site resolver, `run_linkability.build_site_resolver`).
4. In the literal mode, every ruler mention gets #361's typed-literal target.

Writes counts, and the mention ids of any difference; no museum text.

    uv run python docs/evaluations/authority-bridge-338/scripts/check_promotion.py \\
        --archive <corpus archive> --run <#361 run-A directory> --out <json>
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "pipeline"))
from pipeline.authority import graph_kings  # noqa: E402
from pipeline.enrich import authority_links, mentions as production_mentions  # noqa: E402
ARCHIVE_SHA256 = "f4aabc2fc03b3ee0b5965bb9b27129e0ac482dae086c6124dd0d73d70276cc5b"
PREFIX = "hapi-museum-corpus-2026-08-27/data/"
# #361's run-A outputs (`ruler-reregistration-2026-10-15/results/real-run-manifest.json`).
RUN_FILES = {
    "mentions.ndjson.gz": "98ec263a0aa2f295758d98e60676d830ea9dd698b66739134e3af275641ead26",
}
RESOLVER_CHANGE = REPO / "docs/evaluations/resolver-gaps-369/results/resolver-change.json"


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gz_rows(data: bytes) -> list[dict]:
    return [json.loads(line) for line in gzip.GzipFile(fileobj=io.BytesIO(data)).read().splitlines()]


def load_corpus(archive: Path) -> tuple[list[dict], dict[str, dict[str, dict]]]:
    if sha256_path(archive) != ARCHIVE_SHA256:
        raise ValueError(f"{archive} is not the frozen corpus archive")
    with tarfile.open(archive, "r:gz") as bundle:
        def member(name: str) -> bytes:
            handle = bundle.extractfile(PREFIX + name)
            if handle is None:
                raise ValueError(f"{name} is not a regular file")
            return handle.read()
        canonical = gz_rows(member("artifacts.ndjson.gz"))
        raw = {museum: {str(r["object_id"]): r["data"] for r in gz_rows(member(f"raw_{museum}.ndjson.gz"))}
               for museum in ("met", "brooklyn", "harvard")}
    return canonical, raw


def canonical_line(row: dict) -> str:
    return json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def in_play(row: dict) -> list[str]:
    """The targets a production row leaves in play, as the evaluations' arms record them: the
    resolved one, or an ambiguous row's alternatives. (An unmatched row's `candidate_ids`, the
    names it met but could not take, the arms did not record.)"""
    return row["target_ids"] if row["status"] == "resolved" else row["candidate_ids"] if row["status"] == "ambiguous" else []


def check(archive: Path, run: Path) -> dict:
    for name, expected in RUN_FILES.items():
        if sha256_path(run / name) != expected:
            raise ValueError(f"{run / name} is not #361's")
    canonical, raw = load_corpus(archive)
    ledger = gz_rows((run / "mentions.ndjson.gz").read_bytes())
    found, _ = production_mentions.extract_mentions(canonical, raw)
    mention_rows_equal = [canonical_line(r) for r in found] == [canonical_line(r) for r in ledger]

    authority = authority_links.load_authority()
    by_id = {r["mention_id"]: r for r in authority_links.resolve_mentions(found, "authority", authority)}
    literal = {r["mention_id"]: r for r in authority_links.resolve_mentions(found, "literal", None)}

    # 2. Rulers against #361's current-authority arm.
    changed_369 = {c["artifact_id"] for c in json.loads(RESOLVER_CHANGE.read_text(encoding="utf-8"))
                   ["royal_woman_cued_mentions"]["changes"]}
    arm = [r for r in gz_rows((run / "current-authority-arm.ndjson.gz").read_bytes()) if r["entity_type"] == "ruler"]
    differ, differ_outside_369 = [], []
    for old in arm:
        new = by_id[old["mention_id"]]
        if (old["status"], old["target_ids"]) != (new["status"], in_play(new)):
            differ.append(old["mention_id"])
            if old["artifact_id"] not in changed_369:
                differ_outside_369.append(old["mention_id"])

    # 3. Sites against the linkability adapter's site resolver.
    linkability = graph_kings.load_linkability()
    sites, _ = linkability.build_site_resolver(linkability.load_jsonl(linkability.IDAI))
    site_rows = [m for m in found if m["entity_type"] == "site" and m["expression_type"] == "single_identity"]
    site_differ = []
    for m in site_rows:
        old = sites.resolve(m["mention_text"], linkability.place_norm_set)
        if (old["status"], old["target_ids"]) != (by_id[m["mention_id"]]["status"], in_play(by_id[m["mention_id"]])):
            site_differ.append(m["mention_id"])

    # 4. Literal targets against #361's typed-literal arm.
    literal_arm = [r for r in gz_rows((run / "typed-literal-arm.ndjson.gz").read_bytes()) if r["entity_type"] == "ruler"]
    literal_differ = [r["mention_id"] for r in literal_arm
                      if (r["status"], r["target_ids"]) != (literal[r["mention_id"]]["status"],
                                                            literal[r["mention_id"]]["target_ids"])]

    statuses = collections.Counter((r["entity_type"], r["status"]) for r in by_id.values())
    return {
        "schema_version": "hapi-338-promotion-check/1",
        "corpus_archive_sha256": ARCHIVE_SHA256,
        "run_361_files": RUN_FILES,
        "resolver_version": authority.snapshot["resolver_version"],
        "mentions": {"production": len(found), "ledger_361": len(ledger), "rows_equal": mention_rows_equal},
        "rulers_vs_361_authority_arm": {
            "compared": len(arm), "differ": len(differ),
            "differ_outside_369_changed_records": differ_outside_369,
        },
        "sites_vs_linkability_adapter": {"compared": len(site_rows), "differ": site_differ},
        "rulers_vs_361_literal_arm": {"compared": len(literal_arm), "differ": literal_differ},
        "authority_mode_statuses": {f"{t}:{s}": n for (t, s), n in sorted(statuses.items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = check(args.archive, args.run)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
