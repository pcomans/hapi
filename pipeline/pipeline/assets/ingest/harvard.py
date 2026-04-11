"""Harvard Art Museums ingest — fetches all Egyptian objects and stores raw JSON."""

import json
import os

import requests
import sqlalchemy as sa
from dagster import AssetExecutionContext, asset

from pipeline.resources import DatabaseResource
from pipeline.types.models import raw_harvard_table

HARVARD_API_BASE = "https://api.harvardartmuseums.org"
PAGE_SIZE = 100


@asset(
    group_name="ingest",
    kinds={"python", "api"},
)
def raw_harvard(context: AssetExecutionContext, database: DatabaseResource) -> None:
    """Fetch all Harvard Egyptian objects and store raw JSON verbatim.

    Paginates through the Harvard API (100 objects per page, ~8 pages for 722 objects).
    Idempotent: re-running overwrites existing records.
    """
    api_key = os.environ["HARVARD_ART_MUSEUMS_API_KEY"]
    engine = database.get_engine()

    page = 1
    stored = 0
    total_records = None

    while True:
        url = f"{HARVARD_API_BASE}/object"
        params = {
            "apikey": api_key,
            "culture": "Egyptian",
            "size": PAGE_SIZE,
            "page": page,
            "fields": "*",  # Default response omits `places`; `*` returns the full field set.
        }
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if total_records is None:
            total_records = data["info"]["totalrecords"]
            context.log.info(f"Harvard API reports {total_records} Egyptian objects")

        records = data["records"]
        if not records:
            break

        rows = [
            {"object_id": str(record["id"]), "data": json.dumps(record)}
            for record in records
        ]

        with engine.begin() as conn:
            stmt = sa.dialects.postgresql.insert(raw_harvard_table).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["object_id"],
                set_={"data": stmt.excluded.data},
            )
            conn.execute(stmt)

        stored += len(rows)
        context.log.info(f"Page {page}: {stored}/{total_records} stored")

        if not data["info"].get("next"):
            break
        page += 1

    context.log.info(f"Ingest complete: {stored} objects stored")
    context.add_output_metadata({"total_api": total_records, "stored": stored})
