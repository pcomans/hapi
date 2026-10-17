#!/usr/bin/env python3
"""Per-museum ruler test: build the review queues from the frozen run.

Every unit comes from the run's authority-mode resolutions of ruler mentions
(`resolutions-authority.ndjson.gz`), museum by museum:
- a **link** unit is one distinct link: a mention text and the one target it resolved to, with
  every record that carries it. The question: is the target the ruler those records name?
- a **miss** unit is one distinct mention text the authority left unmatched or ambiguous. The
  question: do those records name one specific ruler with it?
- a **decoy** is a link unit shown with a wrong target: another ruler of the same name and a
  different regnal number in the authority's catalog ("Senusret I" shown as Senusret II). The
  reviewers are not told decoys exist; the scorer uses them to check that the review rejects a
  wrong ruler (`decision-rule.md`).

An abstained mention (a list, a range, a doubt, a field the parser does not read) names no single
ruler by the extractor's own grammar and is not reviewed (`make_run.ruler_counts`).

What a reviewer sees of a unit: the museum, the mention text, the field paths and every distinct
text of the fields that hold the mention, each with its record count and up to five record URLs
(`record_texts`), and for a link or decoy the target's label and authority metadata. What only
the private answer key holds: whether a link case is a decoy and its true target, and the
records. Case IDs and order are opaque (`OPAQUE_ORDER_SEED`), so neither reveals the museum, the
kind or a decoy.

    pipeline/.venv/bin/python docs/evaluations/ruler-per-museum-2026-10-17/scripts/build_queue.py \\
        --repo-root . --run <private run dir>/<run id> --corpus <corpus archive> \\
        --added <added-museums archive> --out <private review dir> \\
        --public-digest docs/evaluations/ruler-per-museum-2026-10-17/results/review-population-digest.json
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

EVALUATION_ROOT = Path("docs/evaluations/ruler-per-museum-2026-10-17")
RUN_MANIFEST = EVALUATION_ROOT / "results/run-manifest.json"
OPAQUE_ORDER_SEED = "hapi-ruler-per-museum-2026-10-17-v1"
ENTITY = "ruler"
EXAMPLE_URLS_PER_TEXT = 5
DECOY_COUNT = 20
LINK_QUESTION = "Is this proposed canonical target the exact ruler that the museum's records name?"
MISS_QUESTION = "Does this mention, as these records use it, name one specific ruler?"
LINK_OUTCOMES = ("exact_identity", "different_identity", "insufficient_evidence")
MISS_OUTCOMES = ("one_ruler", "not_one_ruler", "insufficient_evidence")
# A catalog label that ends in a regnal number ("Senusret III", "Sethôs II."): its name and number.
NUMBERED_LABEL = re.compile(r"^(?P<name>.*\S)\s+(?P<number>[IVXL]+)\.?$")
# Builder internals of a claim-graph target that are no evidence a reviewer can check (as in the
# 2026-10-16 registration, leak audit round 10).
UNRELEASED_TARGET_METADATA = ("label_count_including_duplicates", "name_claim_ids")
SCHEMA_VERSION = "hapi-ruler-per-museum-queue/1"


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha256(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    if path.exists():
        raise ValueError(f"{path} exists; frozen files are never overwritten")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def opaque(kind: str, value: str) -> str:
    return hashlib.sha256(f"{OPAQUE_ORDER_SEED}|{kind}|{value}".encode("utf-8")).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_make_run(repo_root: Path):
    return load_module(repo_root / EVALUATION_ROOT / "scripts/make_run.py", "_ruler_per_museum_make_run")


def load_review_protocol(repo_root: Path):
    return load_module(repo_root / EVALUATION_ROOT / "scripts/review_protocol.py", "_ruler_per_museum_review_protocol")


def pipeline_modules(repo_root: Path):
    """This tree's production modules: the link step's files and its authority."""
    pipeline_root = str(repo_root / "pipeline")
    if pipeline_root not in sys.path:
        sys.path.insert(0, pipeline_root)
    from pipeline.authority import royal_women
    from pipeline.enrich import authority_links, link_files
    for module in (royal_women, authority_links, link_files):
        if not Path(module.__file__).resolve().is_relative_to(Path(pipeline_root).resolve()):
            raise ValueError(f"{module.__name__} was imported from {module.__file__}, not from {pipeline_root}")
    return authority_links, link_files, royal_women


def validate_run(repo_root: Path, run: Path) -> dict:
    """Accept the private run only if it is the committed run manifest's, made by `make_run.py`
    from the frozen archives, and the resolver versions this tree's code gives now are the run's."""
    authority_links, link_files, _ = pipeline_modules(repo_root)
    make_run = load_make_run(repo_root)
    committed = read_json(repo_root / RUN_MANIFEST)
    if committed["make_run_sha256"] != sha256_path(repo_root / EVALUATION_ROOT / "scripts/make_run.py"):
        raise ValueError("the run manifest was made by another make_run.py")
    if committed["inputs"]["corpus_archive_sha256"] != make_run.CORPUS_SHA256 or (
            committed["inputs"]["added_museums_archive_sha256"] != make_run.ADDED_ARCHIVE_SHA256):
        raise ValueError("the run was made from other archives")
    link_files.verify_run(run)
    manifest = read_json(run / "manifest.json")
    if manifest != committed["manifest"] or run.name != committed["run_id"]:
        raise ValueError("the run is not the committed run manifest's")
    for mode in authority_links.MODES:
        if authority_links.snapshot(mode)["resolver_version"] != manifest["snapshots"][mode]["resolver_version"]:
            raise ValueError(f"this tree's {mode} resolver is not the run's")
    if make_run.ruler_counts(run) != committed["ruler_counts"]:
        raise ValueError("the run's ruler counts are not the committed ones")
    return committed


def load_source_urls(repo_root: Path, corpus: Path, added: Path, run: Path) -> dict[str, str]:
    """Every canonical artifact ID's public record URL, from the frozen inputs. The run must have
    been made from exactly these inputs: its recorded input digest is re-derived here."""
    pipeline_modules(repo_root)
    from pipeline.enrich import inputs, link_files
    canonical, raw = load_make_run(repo_root).load_inputs(corpus, added)
    kept, _ = inputs.check_inputs(canonical, raw)
    if link_files.input_digest(kept, raw) != read_json(run / "manifest.json")["inputs_sha256"]:
        raise ValueError("the run was not made from these archives' inputs")
    urls: dict[str, str] = {}
    for row in canonical:
        url = row.get("source_url")
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            raise ValueError(f"canonical record has no public source_url: {row.get('id')}")
        if row["id"] in urls:
            raise ValueError(f"duplicate canonical record: {row['id']}")
        urls[row["id"]] = url
    return urls


def record_texts(rows: list[dict], source_urls: dict[str, str]) -> list[dict]:
    """Every distinct set of field texts that holds the unit's mentions, one entry per set, with
    the number of records that carry it and up to `EXAMPLE_URLS_PER_TEXT` of their URLs in an
    opaque seeded order. Ordered by the same seed, so neither record IDs nor counts order them."""
    fields_by_artifact: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    for row in rows:
        fields_by_artifact[row["artifact_id"]].add((row["field_path"], row["field_value"]))
    by_text: dict[tuple, list[str]] = collections.defaultdict(list)
    for artifact_id, fields in fields_by_artifact.items():
        by_text[tuple(sorted(fields))].append(artifact_id)
    entries = []
    for fields, artifact_ids in by_text.items():
        chosen = sorted(artifact_ids, key=lambda a: opaque("example-record", a))[:EXAMPLE_URLS_PER_TEXT]
        entries.append({
            "fields": [{"field_path": path, "field_text": value} for path, value in fields],
            "record_count": len(artifact_ids),
            "example_record_urls": [source_urls[a] for a in chosen],
        })
    return sorted(entries, key=lambda e: opaque("record-text", canonical_sha256(e["fields"])))


def ruler_catalog(repo_root: Path) -> dict[str, dict]:
    """What a reviewer sees of a target: the claim graph's king clusters as the production
    authority builds them (`load_authority().kings.catalog`), and Dodson & Hilton's royal women as
    the 2026-10-16 registration released them (no spellings, no page numbers)."""
    authority_links, _, royal_women = pipeline_modules(repo_root)
    catalog = dict(authority_links.load_authority().kings.catalog)
    for woman in royal_women.load_royal_women():
        if woman.target_id in catalog:
            raise ValueError(f"royal-woman target collides with a king target: {woman.target_id}")
        catalog[woman.target_id] = {
            "label": woman.label, "entity_type": "ruler", "representation": "dodson_hilton_royal_woman",
            "source": "Dodson & Hilton, The Complete Royal Families of Ancient Egypt (2004)",
            "dynasties": list(woman.dynasties), "family_names": list(woman.family_names),
        }
    return catalog


def released_target(target_id: str, catalog: dict[str, dict]) -> dict:
    metadata = catalog[target_id]
    return {
        "target_id": target_id,
        "target_label": metadata["label"],
        "target_metadata": {k: v for k, v in metadata.items() if k not in UNRELEASED_TARGET_METADATA},
    }


def units(run: Path, mentions: dict[str, dict], link_files) -> tuple[list[dict], list[dict]]:
    """The link and miss units, by `make_run`'s grouping: a link per (museum, mention text, target
    ids), a miss per (museum, mention text)."""
    linked: dict[tuple, list[dict]] = collections.defaultdict(list)
    missed: dict[tuple, list[dict]] = collections.defaultdict(list)
    for row in link_files.read_rows(run / "resolutions-authority.ndjson.gz"):
        if row["entity_type"] != ENTITY:
            continue
        mention = mentions[row["mention_id"]]
        if row["status"] == "resolved":
            if len(row["target_ids"]) != 1:
                raise ValueError(f"a resolved ruler mention with {len(row['target_ids'])} targets: {row['mention_id']}")
            linked[(row["museum"], row["mention_text"], tuple(row["target_ids"]))].append(mention)
        elif row["status"] in ("unmatched", "ambiguous"):
            missed[(row["museum"], row["mention_text"])].append(mention)
    link_units = [{"museum": m, "mention_text": text, "resolved_target_ids": list(targets), "rows": rows}
                  for (m, text, targets), rows in linked.items()]
    miss_units = [{"museum": m, "mention_text": text, "rows": rows} for (m, text), rows in missed.items()]
    for unit in link_units + miss_units:
        unit["unit_id"] = "unit-" + opaque("unit", canonical_sha256(
            [unit["museum"], unit["mention_text"], unit.get("resolved_target_ids", [])]))[:16]
    return link_units, miss_units


def decoy_target(target_id: str, catalog: dict[str, dict]) -> str | None:
    """Another ruler of the same name with a different regnal number, the first in the seeded
    order; None when the target's label has no number or no other ruler shares its name."""
    match = NUMBERED_LABEL.match(catalog[target_id]["label"])
    if match is None:
        return None
    others = []
    for other_id, metadata in catalog.items():
        other = NUMBERED_LABEL.match(metadata["label"])
        if other and other["name"] == match["name"] and other["number"] != match["number"]:
            others.append(other_id)
    return min(others, key=lambda t: opaque("decoy-target", f"{target_id}|{t}")) if others else None


def choose_decoys(link_units: list[dict], catalog: dict[str, dict]) -> list[tuple[dict, str]]:
    """`DECOY_COUNT` link units that have a decoy target, the first in the seeded order."""
    eligible = [(unit, decoy_target(unit["resolved_target_ids"][0], catalog)) for unit in link_units]
    eligible = sorted(((u, t) for u, t in eligible if t is not None), key=lambda ut: opaque("decoy", ut[0]["unit_id"]))
    if len(eligible) < DECOY_COUNT:
        raise ValueError(f"only {len(eligible)} link units have a decoy target")
    return eligible[:DECOY_COUNT]


def evidence(unit: dict, source_urls: dict[str, str]) -> dict:
    rows = unit["rows"]
    return {
        "museum": unit["museum"],
        "mention_text": unit["mention_text"],
        "mention_count": len(rows),
        "distinct_record_count": len({row["artifact_id"] for row in rows}),
        "field_paths": sorted({row["field_path"] for row in rows}),
        "record_texts": record_texts(rows, source_urls),
    }


def build(repo_root: Path, run: Path, corpus: Path, added: Path, out: Path, public_digest: Path | None) -> dict:
    committed = validate_run(repo_root, run)
    _, link_files, _ = pipeline_modules(repo_root)
    source_urls = load_source_urls(repo_root, corpus, added, run)
    mentions = {row["mention_id"]: row for row in link_files.read_rows(run / "mentions.ndjson.gz")}
    catalog = ruler_catalog(repo_root)
    link_units, miss_units = units(run, mentions, link_files)
    decoys = choose_decoys(link_units, catalog)

    link_items = [(unit, unit["resolved_target_ids"][0], False) for unit in link_units]
    link_items += [(unit, target, True) for unit, target in decoys]
    link_cases, miss_cases, key = [], [], []
    for index, (unit, target, decoy) in enumerate(sorted(
            link_items, key=lambda item: opaque("link-case", f"{item[0]['unit_id']}|{item[1]}")), 1):
        body = {"entity_type": ENTITY, "evidence": evidence(unit, source_urls),
                "proposed_target": released_target(target, catalog)}
        case_id = f"link-{index:03d}"
        link_cases.append({"case_id": case_id, "evidence_sha256": canonical_sha256(body), **body,
                           "question": LINK_QUESTION, "allowed_outcomes": list(LINK_OUTCOMES)})
        key.append({"case_id": case_id, "unit_id": unit["unit_id"], "unit_kind": "decoy" if decoy else "link",
                    "decoy": decoy, "museum": unit["museum"], "mention_text": unit["mention_text"],
                    "proposed_target_id": target, "resolved_target_ids": unit["resolved_target_ids"],
                    "artifact_ids": sorted({row["artifact_id"] for row in unit["rows"]}),
                    "mention_ids": sorted(row["mention_id"] for row in unit["rows"])})
    for index, unit in enumerate(sorted(miss_units, key=lambda u: opaque("miss-case", u["unit_id"])), 1):
        body = {"entity_type": ENTITY, "evidence": evidence(unit, source_urls)}
        case_id = f"miss-{index:03d}"
        miss_cases.append({"case_id": case_id, "evidence_sha256": canonical_sha256(body), **body,
                           "question": MISS_QUESTION, "allowed_outcomes": list(MISS_OUTCOMES)})
        key.append({"case_id": case_id, "unit_id": unit["unit_id"], "unit_kind": "miss", "decoy": False,
                    "museum": unit["museum"], "mention_text": unit["mention_text"],
                    "artifact_ids": sorted({row["artifact_id"] for row in unit["rows"]}),
                    "mention_ids": sorted(row["mention_id"] for row in unit["rows"])})

    protocol = load_review_protocol(repo_root)
    for case in link_cases + miss_cases:
        leaks = protocol.forbidden_keys(case)
        if leaks:
            raise ValueError(f"a case carries private keys: {leaks}")
    counts = population_counts(key)
    expected = {m: {kind: c["units"] for kind, c in sides.items()} for m, sides in committed["ruler_counts"].items()}
    if {m: {"linked": c["link"], "missed": c["miss"]} for m, c in counts.items()} != expected:
        raise ValueError(f"the units are not the run's ruler counts: {counts} != {expected}")

    out.mkdir(parents=True, exist_ok=False)
    queues = {"link-queue.json": {"schema_version": SCHEMA_VERSION, "stage": "link", "cases": link_cases},
              "miss-queue.json": {"schema_version": SCHEMA_VERSION, "stage": "miss", "cases": miss_cases},
              "private-answer-key.json": {"schema_version": SCHEMA_VERSION, "cases": key,
                                          "warning": "private: never a model input"}}
    for name, value in queues.items():
        write_json(out / name, value)
    digest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": committed["run_id"],
        "seed": OPAQUE_ORDER_SEED,
        "decoy_count": DECOY_COUNT,
        "builder_sha256": sha256_path(Path(__file__).resolve()),
        "review_protocol": review_protocol_bindings(repo_root),
        "population": counts,
        "output_sha256": {name: sha256_path(out / name) for name in queues},
    }
    if public_digest is not None:
        write_json(public_digest, digest)
    return digest


def population_counts(key: list[dict]) -> dict:
    """Per museum: link units (without decoys), decoys, miss units, and their records."""
    out: dict[str, dict] = {}
    for case in key:
        side = out.setdefault(case["museum"], {"link": 0, "decoy": 0, "miss": 0, "link_records": set(),
                                               "miss_records": set()})
        side[case["unit_kind"]] += 1
        if case["unit_kind"] in ("link", "miss"):
            side[f"{case['unit_kind']}_records"].update(case["artifact_ids"])
    return {m: {**{k: v for k, v in s.items() if not k.endswith("_records")},
                "link_records": len(s["link_records"]), "miss_records": len(s["miss_records"])}
            for m, s in sorted(out.items())}


def review_protocol_bindings(repo_root: Path) -> dict:
    """The hash of every file the review runs on (`review_protocol.ROLES` and the shared files)."""
    protocol = load_review_protocol(repo_root)

    def binding(path: Path) -> dict:
        path = path.resolve()
        return {"path": path.relative_to(repo_root.resolve()).as_posix(), "sha256": sha256_path(path)}

    root = repo_root / EVALUATION_ROOT
    return {
        "validator": binding(root / "scripts/review_protocol.py"),
        "runner": binding(root / "scripts/run_harness_review.py"),
        "browser_tool": binding(protocol.OPEN_PAGE_SERVER_PATH),
        "citable_sources": binding(protocol.CITABLE_SOURCES_PATH),
        "system_prompt": binding(protocol.SYSTEM_PROMPT_PATH),
        "runtime_lock": binding(protocol.RUNTIME_LOCK_PATH),
        "prompts": {name: binding(role.prompt) for name, role in sorted(protocol.ROLES.items())},
        "schemas": {name: binding(role.schema) for name, role in sorted(protocol.ROLES.items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--added", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--public-digest", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.repo_root.resolve(), args.run, args.corpus, args.added, args.out, args.public_digest),
                     indent=1))


if __name__ == "__main__":
    main()
