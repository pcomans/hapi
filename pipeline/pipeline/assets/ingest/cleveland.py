"""Cleveland Museum of Art ingest — fetches the Egyptian department and stores raw JSON.

The Open Access API's list endpoint returns full object records (the same fields as
`/api/artworks/{id}`), so the department is read page by page and each record is stored as
the ingest assets store raw data: `json.dumps` of the record. See docs/museum-sources/cleveland.md.
"""

import json

import requests
import sqlalchemy as sa
from dagster import AssetExecutionContext, asset

from pipeline.resources import DatabaseResource
from pipeline.types.models import raw_cleveland_table

CLEVELAND_API_BASE = "https://openaccess-api.clevelandart.org/api"
DEPARTMENT = "Egyptian and Ancient Near Eastern Art"
# The API's largest page. Pages of 500 were seen to repeat one record and drop another, so the
# ingest also checks that it stored exactly the reported total of distinct records.
PAGE_SIZE = 1000


def fetch_department() -> list[dict]:
    """Every record of the department, in API order. Raises unless the distinct ids read equal
    the total the API reports."""
    records: list[dict] = []
    total = None
    skip = 0
    while True:
        resp = requests.get(
            f"{CLEVELAND_API_BASE}/artworks/",
            params={"department": DEPARTMENT, "limit": PAGE_SIZE, "skip": skip},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        page_total = data["info"]["total"]
        if total is None:
            total = page_total
        elif page_total != total:
            raise ValueError(f"department total changed during ingest: {total} -> {page_total}")
        if not data["data"]:
            break
        records.extend(data["data"])
        skip += PAGE_SIZE
        if skip >= total:
            break
    ids = [r["id"] for r in records]
    if len(set(ids)) != len(ids) or len(ids) != total:
        raise ValueError(f"read {len(ids)} records ({len(set(ids))} distinct); the API reports {total}")
    return records


@asset(
    group_name="ingest",
    kinds={"python", "api"},
)
def raw_cleveland(context: AssetExecutionContext, database: DatabaseResource) -> None:
    """Fetch the whole Cleveland Egyptian and Ancient Near Eastern department and store raw JSON
    verbatim. Which records are Egyptian is decided at normalization, from the museum's own
    `collection` field. Idempotent: re-running overwrites existing records.
    """
    records = fetch_department()
    context.log.info(f"Cleveland API: {len(records)} records in {DEPARTMENT}")
    rows = [{"object_id": str(r["id"]), "data": json.dumps(r)} for r in records]
    engine = database.get_engine()
    with engine.begin() as conn:
        for i in range(0, len(rows), 250):
            stmt = sa.dialects.postgresql.insert(raw_cleveland_table).values(rows[i : i + 250])
            stmt = stmt.on_conflict_do_update(
                index_elements=["object_id"],
                set_={"data": stmt.excluded.data},
            )
            conn.execute(stmt)
    context.log.info(f"Ingest complete: {len(rows)} objects stored")
    context.add_output_metadata({"total_api": len(records), "stored": len(rows)})
