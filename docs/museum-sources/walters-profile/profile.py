#!/usr/bin/env python3
"""The figures docs/museum-sources/walters.md quotes, measured on the ingested raw table and on
the published files it was ingested from.

Reads `catalog.raw_walters` (what the `raw_walters` asset stored) and the museum's `art.csv` and
`media.csv` at the commit the ingest read (`COMMIT`; their SHA-256 are checked). It requires the
table to be exactly what the ingest's own `candidate_records` makes of those files, so the
figures trace to a public, reproducible source. It writes `profile.json` beside this script. The
figures:
- the whole file: objects, `Period`, and the objects using the unlisted code "PRE";
- the stored candidates by collection codes and culture;
- the in-scope records (`is_egyptian`) and those left out, by id;
- their `Reign`, `DateText`, `Dynasty`, credit-line and image fields, and how each record's image
  was chosen;
- the ruler mentions of the in-scope records by field and expression, and the hyphenated pairs
  classified as one name;
- whether each test fixture is its record as the ingest stored it.

`raw_sha256` digests the rows read, so the figures name their input.

    DATABASE_URL=<postgres url> uv run python ../docs/museum-sources/walters-profile/profile.py
"""

from __future__ import annotations

import collections
import csv
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path

import requests
import sqlalchemy as sa

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "pipeline"))
from pipeline.assets.ingest.walters import DATA_REPOSITORY, candidate_records  # noqa: E402
from pipeline.assets.normalize.walters import WaltersMapper, collection_codes, is_egyptian  # noqa: E402
from pipeline.enrich.mentions import walters_mentions  # noqa: E402
from pipeline.types.models import raw_walters_table  # noqa: E402

FIXTURES = REPO / "pipeline" / "tests" / "fixtures" / "walters"
# The data commit the ingest of 2026-10-16 read (its materialization metadata), and its files.
COMMIT = "f7531ed751ac2c138eeb6f923a3b4fd325d78adf"
FILE_SHA256 = {
    "art.csv": "bd3d85ba8c871948d269aea2a51947eda4dcde0a0f1da7e87c1a34e8fafa704b",
    "media.csv": "a93cf8b2e7181416f301fa91f858d43742ecc4d98c0b7510d9a42b488bfa64d6",
}
# Two names joined by a hyphen ("Psametik I-Necho II", "Apries (589-570 BC)-Amasis"); a hyphen
# inside one name is followed by a lower-case letter ("Ni-user-re").
HYPHENATED_PAIR = re.compile(r"[\w)]\s*-\s*[A-Z]")
LOAN = re.compile(r"\b(?:loan|lent|on deposit|courtesy)\b", re.I)


def published(name: str) -> tuple[list[dict], str]:
    resp = requests.get(f"https://raw.githubusercontent.com/{DATA_REPOSITORY}/{COMMIT}/{name}", timeout=300)
    resp.raise_for_status()
    digest = hashlib.sha256(resp.content).hexdigest()
    if digest != FILE_SHA256[name]:
        raise ValueError(f"{name} at {COMMIT} is not the file the ingest read")
    return list(csv.DictReader(io.StringIO(resp.content.decode("utf-8"), newline=""))), digest


def image_rule(raw: dict) -> str:
    images = [m for m in raw["media"] if m["MediaType"] == "Image"]
    if not images:
        return "no image row"
    return "marked primary" if any(m["IsPrimary"] == "1" for m in images) else "lowest rank"


def profile(url: str) -> dict:
    with sa.create_engine(url).connect() as conn:
        rows = sorted((r["object_id"], r["data"]) for r in conn.execute(sa.select(raw_walters_table)).mappings())
    raw = {object_id: json.loads(data) for object_id, data in rows}
    art, art_sha256 = published("art.csv")
    media, media_sha256 = published("media.csv")
    if {r["object"]["ObjectID"]: r for r in candidate_records(art, media)} != raw:
        raise ValueError(f"catalog.raw_walters is not the ingest's candidates of the files at {COMMIT}")
    digest = hashlib.sha256("".join(f"{i}\x1f{d}\x1e" for i, d in rows).encode("utf-8")).hexdigest()
    in_scope = [r for r in raw.values() if is_egyptian(r)]
    out = [r for r in raw.values() if not is_egyptian(r)]
    mapper = WaltersMapper()
    found, missed = [], collections.Counter()
    for r in in_scope:
        rows_, misses = walters_mentions(mapper.map_to_canonical(r).model_dump(), r)
        found += rows_
        missed.update(misses)
    fixtures = {}
    for path in sorted(FIXTURES.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        object_id = payload["object"]["ObjectID"]
        fixtures[path.name] = {"object_id": object_id, "equals_ingested_record": raw.get(object_id) == payload}
    code = {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        REPO / "pipeline/pipeline/assets/ingest/walters.py", REPO / "pipeline/pipeline/assets/normalize/walters.py",
        REPO / "pipeline/pipeline/enrich/mentions.py", HERE / "profile.py")}

    def count(values) -> dict:
        return dict(sorted(collections.Counter(values).items()))

    singles = [m for m in found if m["field_path"] == "object.Reign" and m["expression_type"] == "single_identity"]
    reign_in_date = [r for r in in_scope if re.search(r"\breigns?\s+of\b", r["object"]["DateText"], re.I)]
    return {
        "code_sha256": code,
        "source": {"repository": DATA_REPOSITORY, "commit": COMMIT, "art_csv_sha256": art_sha256,
                   "media_csv_sha256": media_sha256, "raw_table_equals_ingest_candidates": True},
        "file_objects": len(art),
        "file_objects_with_period": sum(1 for r in art if r["Period"].strip()),
        "file_objects_using_code_pre": {r["ObjectID"]: f'{r["CollectionID"]} | {r["DateText"]}'
                                        for r in art if "PRE" in r["CollectionID"].split("|")},
        "raw_sha256": digest,
        "raw_records": len(raw),
        "by_collection_id": count(r["object"]["CollectionID"] for r in raw.values()),
        "in_scope_records": len(in_scope),
        "in_scope_by_reason": count(
            "collection includes EGY" if "EGY" in collection_codes(r) else "no collection, culture Egyptian"
            for r in in_scope),
        "out_of_scope": count(f'{r["object"]["CollectionID"]} | {r["object"]["Culture"]}' for r in out),
        "out_of_scope_ids": sorted(r["object"]["ObjectID"] for r in out),
        "in_scope_by_culture": count(r["object"]["Culture"] for r in in_scope),
        "in_scope_with_reign": sum(1 for r in in_scope if r["object"]["Reign"].strip()),
        "in_scope_with_dynasty": sum(1 for r in in_scope if r["object"]["Dynasty"].strip()),
        "in_scope_with_period": sum(1 for r in in_scope if r["object"]["Period"].strip()),
        "in_scope_with_geography_id": sum(1 for r in in_scope if r["object"]["GeographyID"].strip()),
        "in_scope_dated_after_1800": sorted(
            r["object"]["ObjectID"] for r in in_scope
            if r["object"]["DateBeginYear"].strip() and int(r["object"]["DateBeginYear"]) > 1800),
        "in_scope_image": count(image_rule(r) for r in in_scope),
        "in_scope_credit_lines_naming_a_loan": sorted(
            r["object"]["ObjectID"] for r in in_scope if LOAN.search(r["object"]["CreditLine"])),
        "in_scope_date_text_naming_a_reign": {
            "records": len(reign_in_date),
            "of_which_without_reign": sum(1 for r in reign_in_date if not r["object"]["Reign"].strip())},
        "in_scope_ruler_mentions": {
            "total": len(found),
            "by_field_and_expression": count(f'{m["field_path"]} | {m["expression_type"]}' for m in found),
            "cues_without_a_name": dict(sorted(missed.items())),
            "reign_single_identity_hyphenated_pairs": sorted(
                m["mention_text"] for m in singles if HYPHENATED_PAIR.search(m["mention_text"])),
        },
        "fixtures": fixtures,
    }


def main() -> None:
    result = profile(os.environ["DATABASE_URL"])
    (HERE / "profile.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                                       encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
