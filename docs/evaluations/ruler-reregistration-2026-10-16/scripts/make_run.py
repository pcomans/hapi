#!/usr/bin/env python3
"""The registration's run: the production authority-links step on the frozen inputs, twice.

The inputs are two archives:
- #337's frozen corpus (`hapi-museum-corpus-2026-08-27`): the Met's, Brooklyn's and Harvard's
  canonical and raw records, read by #338's `check_promotion.load_corpus`;
- the added museums' raw tables as ingested into Neon on 2026-10-16
  (`hapi-added-museums-2026-10-16`): Cleveland's and the Walters', each row's stored text verbatim.
  Their canonical rows are what the normalize step makes of them (`pipeline.enrich.inputs`).
  Each table reproduces its committed profile's `raw_sha256`
  (`docs/museum-sources/<museum>-profile/profile.json`), so the archive is the table those
  profiles measured.

The step (`pipeline.enrich.link_files.write_run`) runs in two interpreters with different
`PYTHONHASHSEED`s, each into a fresh directory; the two runs must have the same manifest and the
same file contents. The run's files carry museum text, so they are written to a private directory
(`--out-run`); what is committed (`--manifest`) holds hashes, counts and target ids only.

The ruler transitions it counts (`transition_counts`) are the population definition of #361's
`build_review_queue.derive_candidates`, computed here independently, so the queue builder can
check that it found every one.

    uv run python docs/evaluations/ruler-reregistration-2026-10-16/scripts/make_run.py \\
        --corpus <corpus archive> --added <added-museums archive> --out-run <private dir> \\
        --manifest docs/evaluations/ruler-reregistration-2026-10-16/results/run-manifest.json
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
from pipeline.enrich import authority_links, link_files  # noqa: E402
from pipeline.enrich.inputs import normalized  # noqa: E402

ADDED_ARCHIVE_SHA256 = "61ada79d99d6b91192bc4f2d768627e71aad9911fc77e52d2e5bca14f8c89913"
ADDED_PREFIX = "hapi-added-museums-2026-10-16/"
ADDED_MUSEUMS = ("cleveland", "walters")
PROFILES = {museum: REPO / f"docs/museum-sources/{museum}-profile/profile.json" for museum in ADDED_MUSEUMS}
ENTITY = "ruler"
SCHEMA_VERSION = "hapi-ruler-reregistration-2026-10-16-run/1"


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


def transition_counts(run: Path) -> dict:
    """Ruler transitions per museum pair, by #361's population definition: an authority target
    both museums link to is a retained control when the two sides' mentions share a literal
    target, else an authority-only transition; a literal target both museums link to whose sides'
    mentions share no authority target is a literal-only transition."""
    rows = {mode: {r["mention_id"]: r for r in link_files.read_rows(run / f"resolutions-{mode}.ndjson.gz")
                   if r["entity_type"] == ENTITY} for mode in authority_links.MODES}
    by_target: dict[str, dict[str, dict[str, set[str]]]] = {}
    for mode in authority_links.MODES:
        grouped: dict[str, dict[str, set[str]]] = {}
        for link in link_files.read_rows(run / f"links-{mode}.ndjson.gz"):
            if link["entity_type"] == ENTITY:
                grouped.setdefault(link["target_id"], {}).setdefault(link["museum"], set()).update(link["mention_ids"])
        by_target[mode] = grouped

    def targets(mode: str, mention_ids: set[str]) -> set[str]:
        return {t for m in mention_ids if rows[mode][m]["status"] == "resolved" for t in rows[mode][m]["target_ids"]}

    out = {}
    for pair in authority_links.MUSEUM_PAIRS:
        counts = {"authority_only_transition": 0, "literal_only_transition": 0, "retained_control": 0}
        for sides in by_target["authority"].values():
            if all(m in sides for m in pair):
                shared = targets("literal", sides[pair[0]]) & targets("literal", sides[pair[1]])
                counts["retained_control" if shared else "authority_only_transition"] += 1
        for sides in by_target["literal"].values():
            if all(m in sides for m in pair):
                if not targets("authority", sides[pair[0]]) & targets("authority", sides[pair[1]]):
                    counts["literal_only_transition"] += 1
        out["__".join(pair)] = counts
    return out


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
        "transition_counts": transition_counts(run),
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
