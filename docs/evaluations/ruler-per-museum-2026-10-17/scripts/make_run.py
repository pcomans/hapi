#!/usr/bin/env python3
"""The per-museum ruler test's run: the production authority-links step on the frozen inputs, twice.

The inputs are two archives:
- #337's frozen corpus (`hapi-museum-corpus-2026-08-27`): the Met's, Brooklyn's and Harvard's
  canonical and raw records, read by #338's `check_promotion.load_corpus`;
- the added museums' raw tables as ingested into Neon on 2026-10-16
  (`hapi-added-museums-2026-10-16`): Cleveland's and the Walters', each row's stored text verbatim.
  Their canonical rows are what the normalize step makes of them (`pipeline.enrich.inputs`).
  Each table reproduces its committed profile's `raw_sha256`
  (`docs/museum-sources/<museum>-profile/profile.json`), so the archive is the table those
  profiles measured.

They are the 2026-10-16 ruler re-registration's inputs; the code is today's main.

The step (`pipeline.enrich.link_files.write_run`) runs in two interpreters with different
`PYTHONHASHSEED`s, each into a fresh directory; the two runs must have the same manifest and the
same file contents. The run's files carry museum text, so they are written to a private directory
(`--out-run`); what is committed (`--manifest`) holds hashes and counts only.

`ruler_counts` counts, per museum, what the test reviews: the distinct links (a mention text and
the targets it resolved to) and the distinct texts left unmatched or ambiguous. The queue builder
derives its units a second way and requires the same counts.

    uv run python docs/evaluations/ruler-per-museum-2026-10-17/scripts/make_run.py \\
        --corpus <corpus archive> --added <added-museums archive> --out-run <private dir> \\
        --manifest docs/evaluations/ruler-per-museum-2026-10-17/results/run-manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "docs/evaluations/authority-bridge-338/scripts"))
from check_promotion import ARCHIVE_SHA256 as CORPUS_SHA256, load_corpus  # noqa: E402
from pipeline.enrich import link_files  # noqa: E402
from pipeline.enrich.inputs import normalized  # noqa: E402

ADDED_ARCHIVE_SHA256 = "f9c353f6e5a7757533739210d94550d00091fde026ca3ca9ea2ede5d7c30186e"
ADDED_PREFIX = "hapi-added-museums-2026-10-16/"
ADDED_MUSEUMS = ("cleveland", "walters")
PROFILES = {museum: REPO / f"docs/museum-sources/{museum}-profile/profile.json" for museum in ADDED_MUSEUMS}
ENTITY = "ruler"
SCHEMA_VERSION = "hapi-ruler-per-museum-2026-10-17-run/1"


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_added(archive: Path) -> dict[str, dict[str, dict]]:
    """The added museums' raw payloads by source id. Raises unless the archive is the pinned one
    and each table digests to its committed profile's `raw_sha256`."""
    if sha256_path(archive) != ADDED_ARCHIVE_SHA256:
        raise ValueError(f"{archive} is not the frozen added-museums archive")
    raw = {}
    with tarfile.open(archive, "r:gz") as bundle:
        for museum in ADDED_MUSEUMS:
            handle = bundle.extractfile(f"{ADDED_PREFIX}raw_{museum}.ndjson")
            if handle is None:
                raise ValueError(f"raw_{museum}.ndjson is not a regular file")
            rows = [json.loads(line) for line in handle.read().decode("utf-8").splitlines()]
            stored = sorted((r["object_id"], r["data"]) for r in rows)
            digest = hashlib.sha256("".join(f"{i}\x1f{d}\x1e" for i, d in stored).encode("utf-8")).hexdigest()
            if digest != json.loads(PROFILES[museum].read_text(encoding="utf-8"))["raw_sha256"]:
                raise ValueError(f"the archive's {museum} table is not the one its profile measured")
            raw[museum] = {object_id: json.loads(data) for object_id, data in stored}
    return raw


def load_inputs(corpus: Path, added: Path) -> tuple[list[dict], dict[str, dict[str, dict]]]:
    canonical, raw = load_corpus(corpus)
    extra = load_added(added)
    for museum in ADDED_MUSEUMS:
        if raw[museum]:
            raise ValueError(f"the frozen corpus already holds {museum} records")
    canonical = canonical + normalized(extra)
    return canonical, {**raw, **extra}


def write_once(corpus: Path, added: Path, root: Path) -> dict:
    canonical, raw = load_inputs(corpus, added)
    return link_files.write_run(root, lambda: (canonical, raw))


# What the test reviews of a museum's ruler mentions: the resolved ones (links) and those the
# authority could not settle. An abstained mention (a list, a range, a doubt, a field the parser
# does not read) is not a single ruler by the extractor's own grammar and is not reviewed.
LINKED, MISSED, NOT_REVIEWED = ("resolved",), ("unmatched", "ambiguous"), ("abstained",)


def ruler_counts(run: Path) -> dict:
    """Per museum: distinct links (mention text, sorted target ids) with their records and
    mentions, and distinct unmatched or ambiguous mention texts with theirs."""
    out = {}
    for row in link_files.read_rows(run / "resolutions-authority.ndjson.gz"):
        if row["entity_type"] != ENTITY:
            continue
        if row["status"] not in LINKED + MISSED + NOT_REVIEWED:
            raise ValueError(f"a ruler resolution with an unknown status: {row['status']!r} ({row['mention_id']})")
        if row["status"] in NOT_REVIEWED:
            continue
        side = out.setdefault(row["museum"], {"linked": {}, "missed": {}})
        if row["status"] in LINKED:
            key = (row["mention_text"], tuple(sorted(row["target_ids"])))
            group = side["linked"].setdefault(key, [set(), 0])
        else:
            group = side["missed"].setdefault(row["mention_text"], [set(), 0])
        group[0].add(row["artifact_id"])
        group[1] += 1
    return {museum: {kind: {"units": len(groups), "records": len(set().union(*(g[0] for g in groups.values()))),
                             "mentions": sum(g[1] for g in groups.values())}
                     for kind, groups in sorted(side.items())}
            for museum, side in sorted(out.items())}


def make(corpus: Path, added: Path, out_run: Path) -> dict:
    if out_run.exists():
        raise ValueError(f"{out_run} exists; a run is written once")
    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        manifests = []
        for seed, root in (("1", first), ("2", second)):
            done = subprocess.run([sys.executable, __file__, "--corpus", str(corpus), "--added", str(added),
                                   "--write-once", root], check=True, capture_output=True, text=True,
                                  env={**os.environ, "PYTHONHASHSEED": seed})
            manifests.append(json.loads(done.stdout))
        runs = [Path(root) / m["run_id"] for root, m in ((first, manifests[0]), (second, manifests[1]))]
        contents = [{name: link_files.content_sha256(name, (run / name).read_bytes()) for name in m["files"]}
                    for run, m in zip(runs, manifests)]
        if manifests[0] != manifests[1] or contents[0] != contents[1]:
            raise ValueError("two runs on the same inputs and code differ")
        out_run.mkdir(parents=True)
        shutil.copytree(runs[0], out_run / manifests[0]["run_id"])
    run = out_run / manifests[0]["run_id"]
    link_files.verify_run(run)
    return {
        "schema_version": SCHEMA_VERSION,
        "inputs": {
            "corpus_archive_sha256": CORPUS_SHA256,
            "added_museums_archive_sha256": ADDED_ARCHIVE_SHA256,
            "added_museum_profiles_raw_sha256": {
                m: json.loads(p.read_text(encoding="utf-8"))["raw_sha256"] for m, p in PROFILES.items()},
        },
        "make_run_sha256": sha256_path(Path(__file__)),
        "run_id": manifests[0]["run_id"],
        "two_runs": {"python_hash_seeds": ["1", "2"], "same_manifest_and_contents": True,
                     "run_ids": [m["run_id"] for m in manifests]},
        "manifest": manifests[0],
        "ruler_counts": ruler_counts(run),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--added", type=Path, required=True)
    parser.add_argument("--write-once", type=Path)
    parser.add_argument("--out-run", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    if args.write_once:
        print(json.dumps(write_once(args.corpus, args.added, args.write_once)))
        return
    if args.out_run is None or args.manifest is None:
        parser.error("--out-run and --manifest are required")
    result = make(args.corpus, args.added, args.out_run)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
