#!/usr/bin/env python3
"""#338: the production enrichment step reproduces what the evaluations measured.

On the frozen corpus archive (`hapi-museum-corpus-2026-08-27`):

1. `pipeline.enrich.mentions.extract_mentions` gives exactly #361's mention ledger, row for
   row.
2. In the authority mode, every ruler mention resolves as #361's current-authority arm did,
   except on the records #369 changed, which resolve as #369 measured
   (`resolver-gaps-369/results/resolver-change.json`).
3. Every site and tomb mention resolves as the evaluations' linkability adapter resolves it
   (#337 v10's resolvers, `run_linkability.build_site_resolver` and `build_pm_resolver`).
4. In the literal mode, every ruler mention gets #361's typed-literal target, and every site
   and tomb mention the target #337's typed-literal arm gives (its `resolve_mentions`).
5. The frozen tables pass `pipeline.enrich.inputs.check_inputs`: every canonical row is what its
   museum's normalize step makes of its raw payload, and every kept raw row is normalized.

Writes counts, and the mention ids of any difference; no museum text.

    uv run python docs/evaluations/authority-bridge-338/scripts/check_promotion.py \\
        --archive <corpus archive> --run <#361 run-A directory> --out <json>
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "pipeline"))
from pipeline.authority import graph_kings, royal_women  # noqa: E402
from pipeline.enrich import authority_links, mentions as production_mentions  # noqa: E402
from pipeline.enrich.inputs import check_inputs  # noqa: E402


def check_inputs_code() -> dict:
    """The code `check_inputs` runs: every `pipeline` module a fresh interpreter loads to import
    it (the mappers, the canonical model and source types it dumps through, the package
    `__init__`s), with its SHA-256; and the library versions its rows depend on."""
    code = ("import sys, json, pydantic, pipeline.enrich.inputs; "
            "print(json.dumps({'files': sorted(m.__file__ for n, m in sys.modules.items() "
            "if (n == 'pipeline' or n.startswith('pipeline.')) and getattr(m, '__file__', None)), "
            "'pydantic': pydantic.VERSION}))")
    out = json.loads(subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True,
                                    cwd=REPO / "pipeline").stdout)
    return {"code_sha256": {str(Path(f).relative_to(REPO)): sha256_path(Path(f)) for f in out["files"]},
            "pydantic": out["pydantic"], "uv_lock_sha256": sha256_path(REPO / "pipeline" / "uv.lock")}
ARCHIVE_SHA256 = "f4aabc2fc03b3ee0b5965bb9b27129e0ac482dae086c6124dd0d73d70276cc5b"
PREFIX = "hapi-museum-corpus-2026-08-27/data/"
EVALUATIONS = REPO / "docs/evaluations"
RUN_MANIFEST = EVALUATIONS / "ruler-reregistration-2026-10-15/results/real-run-manifest.json"
RESOLVER_CHANGE = EVALUATIONS / "resolver-gaps-369/results/resolver-change.json"
COMPARE_ARMS_337 = EVALUATIONS / "authority-independent-control-2026-10-11/scripts/compare_arms.py"


def run_files() -> dict[str, str]:
    """#361's run-A files this check reads, with the SHA-256 its run manifest pins."""
    proof = json.loads(RUN_MANIFEST.read_text(encoding="utf-8"))["identical_mentions_proof"]
    return {"mentions.ndjson.gz": proof["mention_ledger"]["gzip_sha256"],
            "current-authority-arm.ndjson.gz": proof["current_authority_arm"]["gzip_sha256"],
            "typed-literal-arm.ndjson.gz": proof["typed_literal_arm"]["gzip_sha256"]}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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
    # The 2026-08-27 corpus predates Cleveland (docs/museum-sources/cleveland.md): its raw table
    # is empty, as a run reads it from a database that holds this corpus alone.
    raw["cleveland"] = {}
    return canonical, raw


def canonical_line(row: dict) -> str:
    return json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def check(archive: Path, run: Path) -> dict:
    files = run_files()
    for name, expected in files.items():
        if sha256_path(run / name) != expected:
            raise ValueError(f"{run / name} is not #361's (its run manifest pins {expected})")
    canonical, raw = load_corpus(archive)
    # 5. The frozen tables are the normalize step's output for their raw rows (#338 step 2's
    #    `check_inputs`, which every run applies): raises if not.
    kept, set_aside = check_inputs(canonical, raw)
    if (len(kept), set_aside) != (len(canonical), []):
        raise ValueError(f"the frozen corpus has canonical rows check_inputs sets aside: {set_aside[:5]}")
    ledger = gz_rows((run / "mentions.ndjson.gz").read_bytes())
    found, _ = production_mentions.extract_mentions(canonical, raw)
    mention_rows_equal = [canonical_line(r) for r in found] == [canonical_line(r) for r in ledger]
    mention_by_id = {m["mention_id"]: m for m in found}

    authority = authority_links.load_authority()
    by_id = {r["mention_id"]: r for r in authority_links.resolve_mentions(found, "authority", authority)}
    literal = {r["mention_id"]: r for r in authority_links.resolve_mentions(found, "literal", None)}

    def answer(row: dict) -> tuple[str, list[str]]:
        """A production row as the evaluations' arms record a resolution: its status and the
        resolver's target ids (an ambiguous row's alternatives); an abstention has none."""
        return row["status"], row["resolution"]["target_ids"] if row["resolution"] else row["target_ids"]

    # 2. Rulers against #361's current-authority arm; #369's records against #369's measurement.
    # #369 records its changes by record (one cued mention each); each must be met exactly once,
    # from its recorded before to its recorded after.
    changes_369 = {c["artifact_id"]: c for c in json.loads(RESOLVER_CHANGE.read_text(encoding="utf-8"))
                   ["royal_woman_cued_mentions"]["changes"]}
    arm = [r for r in gz_rows((run / "current-authority-arm.ndjson.gz").read_bytes()) if r["entity_type"] == "ruler"]
    differ_369, differ_otherwise = [], []
    for old in arm:
        new = by_id[old["mention_id"]]
        if (old["status"], old["target_ids"]) == answer(new):
            continue
        change = changes_369.get(old["artifact_id"])
        cued = royal_women.royal_woman_cued(mention_by_id[old["mention_id"]]["field_value"],
                                            mention_by_id[old["mention_id"]]["span_start"])
        if (cued and change and (change["before"]["status"], change["before"]["target_ids"]) == (old["status"], old["target_ids"])
                and (change["after"]["status"], change["after"]["target_ids"], change["after"]["context_rule"])
                == (*answer(new), new["resolution"]["context_rule"])):
            differ_369.append((old["artifact_id"], old["mention_id"]))
        else:
            differ_otherwise.append(old["mention_id"])
    met = collections.Counter(artifact for artifact, _ in differ_369)
    if set(met) != set(changes_369) or set(met.values()) != {1}:
        raise ValueError(f"#369's changes are not each met exactly once: {dict(met)}")
    differ_369 = [mention_id for _, mention_id in differ_369]

    # 3. Sites and tombs against the linkability adapter's resolvers.
    linkability = graph_kings.load_linkability()
    adapter = {"site": (linkability.build_site_resolver(linkability.load_jsonl(linkability.IDAI))[0],
                        linkability.place_norm_set),
               "tomb_monument": (linkability.build_pm_resolver()[0], linkability.place_norm_set)}
    place_rows = [m for m in found if m["entity_type"] in adapter and m["expression_type"] == "single_identity"]
    place_differ = {t: [] for t in adapter}
    for m in place_rows:
        resolve, norm = adapter[m["entity_type"]]
        old = resolve.resolve(m["mention_text"], norm)
        if (old["status"], old["target_ids"]) != answer(by_id[m["mention_id"]]):
            place_differ[m["entity_type"]].append(m["mention_id"])

    # 4. Literal targets: rulers against #361's typed-literal arm; sites and tombs against
    #    #337's typed-literal arm, run by its own `resolve_mentions`.
    literal_arm = [r for r in gz_rows((run / "typed-literal-arm.ndjson.gz").read_bytes()) if r["entity_type"] == "ruler"]
    literal_differ = [r["mention_id"] for r in literal_arm
                      if (r["status"], r["target_ids"]) != (literal[r["mention_id"]]["status"],
                                                            literal[r["mention_id"]]["target_ids"])]
    arms_337 = load_module(COMPARE_ARMS_337, "_frozen_337_compare_arms")
    places_337 = arms_337.resolve_mentions([m for m in found if m["entity_type"] in adapter], "typed_literal")
    literal_place_differ = [r["mention_id"] for r in places_337
                            if (r["status"], r["target_ids"]) != (literal[r["mention_id"]]["status"],
                                                                  literal[r["mention_id"]]["target_ids"])]

    statuses = collections.Counter((r["entity_type"], r["status"]) for r in by_id.values())
    return {
        "schema_version": "hapi-338-promotion-check/3",
        "corpus_archive_sha256": ARCHIVE_SHA256,
        "run_361_files": files,
        "snapshot": {"authority": authority.snapshot, "literal": authority_links.snapshot("literal")},
        "mentions": {"production": len(found), "ledger_361": len(ledger), "rows_equal": mention_rows_equal},
        "rulers_vs_361_authority_arm": {
            "compared": len(arm), "differ_as_369_measured": sorted(differ_369), "differ_otherwise": differ_otherwise,
        },
        "places_vs_linkability_adapter": {
            "compared": dict(collections.Counter(m["entity_type"] for m in place_rows)), "differ": place_differ},
        "rulers_vs_361_literal_arm": {"compared": len(literal_arm), "differ": literal_differ},
        "places_vs_337_literal_arm": {"compared": len(places_337), "differ": literal_place_differ},
        "check_inputs": {"canonical_records": len(canonical), "passed": True, **check_inputs_code()},
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
