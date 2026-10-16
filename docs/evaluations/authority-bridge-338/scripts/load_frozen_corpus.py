#!/usr/bin/env python3
"""Load the frozen museum corpus (2026-08-27) into a database's catalog tables (#338).

The archive is an export of the `catalog` tables: the canonical `artifacts` rows and each
museum's raw payloads. This writes them back as the pipeline's assets would have: a raw row's
`data` as the JSON text the ingest assets write (`json.dumps` of the payload), a canonical row as
the normalize assets write it. Then the `authority_links` asset can run against the database on
the very inputs the evaluations measured, and its run id says whether it made the same links.

Refuses a database whose catalog tables already hold rows: it loads into empty tables only, so
it never mixes generations.

    DATABASE_URL=<postgres url> uv run python docs/evaluations/authority-bridge-338/scripts/load_frozen_corpus.py \\
        --archive <corpus archive>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import sqlalchemy as sa

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_promotion import load_corpus  # noqa: E402  (verifies the archive's SHA-256)
from pipeline.types.models import artifacts_table, raw_brooklyn_table, raw_harvard_table, raw_met_table  # noqa: E402

RAW_TABLES = {"met": raw_met_table, "brooklyn": raw_brooklyn_table, "harvard": raw_harvard_table}
BATCH = 1000


def load(archive: Path, url: str) -> dict[str, int]:
    canonical, raw = load_corpus(archive)
    engine = sa.create_engine(url)
    tables = [artifacts_table, *RAW_TABLES.values()]
    with engine.begin() as conn:
        for table in tables:
            rows = conn.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()
            if rows:
                raise ValueError(f"{table.fullname} already holds {rows} rows; load into empty tables only")
        for museum, table in RAW_TABLES.items():
            rows = [{"object_id": source_id, "data": json.dumps(payload)} for source_id, payload in sorted(raw[museum].items())]
            for i in range(0, len(rows), BATCH):
                conn.execute(sa.insert(table), rows[i:i + BATCH])
        columns = {c.name for c in artifacts_table.columns}
        for i in range(0, len(canonical), BATCH):
            batch = canonical[i:i + BATCH]
            extra = {k for row in batch for k in row} - columns
            if extra:
                raise ValueError(f"canonical rows carry columns the table does not: {sorted(extra)}")
            conn.execute(sa.insert(artifacts_table), batch)
        return {table.fullname: conn.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()
                for table in tables}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(load(args.archive, os.environ["DATABASE_URL"]), sort_keys=True))


if __name__ == "__main__":
    main()
