#!/usr/bin/env python3
"""The figures docs/museum-sources/walters.md quotes, measured on the ingested raw table.

Reads `catalog.raw_walters` (what the `raw_walters` asset stored) and writes `profile.json`
beside this script. The figures: the stored candidates by collection codes and culture; the
in-scope records (`is_egyptian`) and those left out; their `Reign`, `Dynasty` and image fields, and
how each record's image was chosen; the ruler mentions of the in-scope records by field and
expression; and whether each test fixture is its record as the ingest stored it. `raw_sha256`
digests the rows read, so the figures name their input.

    DATABASE_URL=<postgres url> uv run python ../docs/museum-sources/walters-profile/profile.py
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import sys
from pathlib import Path

import sqlalchemy as sa

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "pipeline"))
from pipeline.assets.normalize.walters import WaltersMapper, collection_codes, is_egyptian  # noqa: E402
from pipeline.enrich.mentions import walters_mentions  # noqa: E402
from pipeline.types.models import raw_walters_table  # noqa: E402

FIXTURES = REPO / "pipeline" / "tests" / "fixtures" / "walters"


def image_rule(raw: dict) -> str:
    images = [m for m in raw["media"] if m["MediaType"] == "Image"]
    if not images:
        return "no image row"
    return "marked primary" if any(m["IsPrimary"] == "1" for m in images) else "lowest rank"


def profile(url: str) -> dict:
    with sa.create_engine(url).connect() as conn:
        rows = sorted((r["object_id"], r["data"]) for r in conn.execute(sa.select(raw_walters_table)).mappings())
    raw = {object_id: json.loads(data) for object_id, data in rows}
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

    return {
        "code_sha256": code,
        "raw_sha256": digest,
        "raw_records": len(raw),
        "by_collection_id": count(r["object"]["CollectionID"] for r in raw.values()),
        "in_scope_records": len(in_scope),
        "in_scope_by_reason": count(
            "collection includes EGY" if "EGY" in collection_codes(r) else "no collection, culture Egyptian"
            for r in in_scope),
        "out_of_scope": count(f'{r["object"]["CollectionID"]} | {r["object"]["Culture"]}' for r in out),
        "in_scope_by_culture": count(r["object"]["Culture"] for r in in_scope),
        "in_scope_with_reign": sum(1 for r in in_scope if r["object"]["Reign"].strip()),
        "in_scope_with_dynasty": sum(1 for r in in_scope if r["object"]["Dynasty"].strip()),
        "in_scope_with_period": sum(1 for r in in_scope if r["object"]["Period"].strip()),
        "in_scope_with_geography_id": sum(1 for r in in_scope if r["object"]["GeographyID"].strip()),
        "in_scope_dated_after_1800": sorted(
            r["object"]["ObjectID"] for r in in_scope
            if r["object"]["DateBeginYear"].strip() and int(r["object"]["DateBeginYear"]) > 1800),
        "in_scope_image": count(image_rule(r) for r in in_scope),
        "in_scope_ruler_mentions": {
            "total": len(found),
            "by_field_and_expression": count(f'{m["field_path"]} | {m["expression_type"]}' for m in found),
            "cues_without_a_name": dict(sorted(missed.items())),
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
