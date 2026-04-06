"""Met Museum ingest — fetches all Egyptian Art objects and stores raw JSON."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import sqlalchemy as sa
from dagster import AssetExecutionContext, asset

from pipeline.resources import DatabaseResource
from pipeline.types.models import raw_met_table

logger = logging.getLogger(__name__)

MET_API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
EGYPTIAN_ART_DEPARTMENT_ID = 10
BATCH_SIZE = 250
MAX_WORKERS = 20  # ~20 concurrent requests, well under 80 req/sec limit


@asset(
    group_name="ingest",
    kinds={"python", "api"},
)
def raw_met(context: AssetExecutionContext, database: DatabaseResource) -> None:
    """Fetch all Met Egyptian Art objects and store raw JSON verbatim.

    Two-step process:
    1. Fetch all object IDs for Egyptian Art department
    2. Fetch each object concurrently, storing the raw JSON response

    Idempotent: re-running overwrites existing records.
    """
    object_ids = _fetch_object_ids(context)
    context.log.info(f"Found {len(object_ids)} Egyptian Art object IDs")

    engine = database.get_engine()
    total = len(object_ids)
    stored = 0
    skipped = 0

    for i in range(0, total, BATCH_SIZE):
        batch_ids = object_ids[i : i + BATCH_SIZE]
        rows = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(_fetch_object, oid): oid for oid in batch_ids}
            for future in as_completed(futures):
                object_id = futures[future]
                raw_data = future.result()
                if raw_data is None:
                    skipped += 1
                    continue
                rows.append({"object_id": str(object_id), "data": json.dumps(raw_data)})

        if rows:
            with engine.begin() as conn:
                stmt = sa.dialects.postgresql.insert(raw_met_table).values(rows)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["object_id"],
                    set_={"data": stmt.excluded.data},
                )
                conn.execute(stmt)
            stored += len(rows)

        context.log.info(f"Progress: {min(i + BATCH_SIZE, total)}/{total} fetched, {stored} stored, {skipped} skipped (404)")

    context.log.info(f"Ingest complete: {stored} stored, {skipped} skipped (404) out of {total}")
    context.add_output_metadata({"total_ids": total, "stored": stored, "skipped_404": skipped})


def _fetch_object_ids(context: AssetExecutionContext) -> list[int]:
    """Fetch all object IDs for the Egyptian Art department."""
    url = f"{MET_API_BASE}/objects?departmentIds={EGYPTIAN_ART_DEPARTMENT_ID}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    ids = data.get("objectIDs", [])
    if not ids:
        raise ValueError("Met API returned no object IDs for Egyptian Art department")
    return ids


def _fetch_object(object_id: int) -> dict | None:
    """Fetch a single object record. Returns None on 404 (deleted objects)."""
    url = f"{MET_API_BASE}/objects/{object_id}"
    resp = requests.get(url, timeout=15)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()
