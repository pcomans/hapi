#!/usr/bin/env python3
"""The figures docs/museum-sources/cleveland.md quotes, measured on the ingested raw table.

Reads `catalog.raw_cleveland` (what the `raw_cleveland` asset stored) and writes `profile.json`
beside this script. The figures: the department's records by `collection`, `share_license_status`,
images and `find_spot`; the reign components (`cleveland_reign_components`) and how their final
parenthesis reads; the mapper's in-scope records and their ruler mentions by expression; the
raise paths the mapper guards (none hit); and whether each test fixture is its record as the list
endpoint gave it to the ingest. `raw_sha256` digests the rows read, so the figures name their input.

    DATABASE_URL=<postgres url> uv run python ../docs/museum-sources/cleveland-profile/profile.py
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import sqlalchemy as sa

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "pipeline"))
from pipeline.assets.normalize.cleveland import ClevelandMapper, is_egyptian  # noqa: E402
from pipeline.enrich.mentions import cleveland_mentions, cleveland_reign_components  # noqa: E402
from pipeline.types.models import raw_cleveland_table  # noqa: E402

FIXTURES = REPO / "pipeline" / "tests" / "fixtures" / "cleveland"


def profile(url: str) -> dict:
    with sa.create_engine(url).connect() as conn:
        rows = sorted((r["object_id"], r["data"]) for r in conn.execute(sa.select(raw_cleveland_table)).mappings())
    raw = {object_id: json.loads(data) for object_id, data in rows}
    digest = hashlib.sha256("".join(f"{i}\x1f{d}\x1e" for i, d in rows).encode("utf-8")).hexdigest()
    in_scope = [r for r in raw.values() if is_egyptian(r)]
    components = [(r, c) for r in raw.values() for entry in r["culture"] or [] for c, _ in cleveland_reign_components(entry)]

    def ending(component: str) -> str:
        if not component.endswith(")"):
            return "no final parenthesis"
        return "final parenthesis with a digit" if re.search(r"\d", component[component.rfind("("):]) else (
            "final parenthesis without a digit")

    mentions = [m for r in in_scope for m in cleveland_mentions(ClevelandMapper().map_to_canonical(r).model_dump(), r)]
    fixtures = {}
    for path in sorted(FIXTURES.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        fixtures[path.name] = {"object_id": str(payload["id"]), "equals_ingested_record": raw.get(str(payload["id"])) == payload}
    code = {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        REPO / "pipeline/pipeline/assets/normalize/cleveland.py", REPO / "pipeline/pipeline/enrich/mentions.py", HERE / "profile.py")}
    return {
        "code_sha256": code,
        "raw_sha256": digest,
        "raw_records": len(raw),
        "by_collection": dict(sorted(collections.Counter(r["collection"] for r in raw.values()).items())),
        "in_scope_records": len(in_scope),
        "by_share_license_status": dict(sorted(collections.Counter(r["share_license_status"] for r in raw.values()).items())),
        "records_with_images": sum(1 for r in raw.values() if r["images"]),
        "records_with_find_spot": sum(1 for r in raw.values() if r["find_spot"]),
        "in_scope_records_whose_culture_does_not_start_with_egypt": sorted(
            r["id"] for r in in_scope if not (r["culture"] or [""])[0].startswith("Egypt")),
        "in_scope_records_with_find_spot": sum(1 for r in in_scope if r["find_spot"]),
        "culture_entries_per_record": dict(sorted(collections.Counter(len(r["culture"] or []) for r in raw.values()).items())),
        "reign_components": {
            "department": len(components),
            "in_scope": sum(1 for r, _ in components if is_egyptian(r)),
            "by_ending": dict(sorted(collections.Counter(ending(c) for _, c in components).items())),
        },
        "in_scope_ruler_mentions": {
            "total": len(mentions),
            "by_expression_type": dict(sorted(collections.Counter(m["expression_type"] for m in mentions).items())),
        },
        "in_scope_records_with_ruler_display_name": sum(
            1 for r in in_scope if ClevelandMapper().map_to_canonical(r).ruler_display_name is not None),
        "guards": {
            "provenance_entries_without_description": sum(
                1 for r in raw.values() for p in r["provenance"] or [] if not p.get("description")),
            "records_with_several_wikidata_items": sum(
                1 for r in raw.values() if len((r.get("external_resources") or {}).get("wikidata") or []) > 1),
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
