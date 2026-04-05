"""Typesense sync — pushes all canonical artifacts to the search index."""

import json
import os

import sqlalchemy as sa
import typesense
from dagster import AssetExecutionContext, asset

from pipeline.resources import DatabaseResource
from pipeline.types.models import artifacts_table

COLLECTION_NAME = "artifacts"
BATCH_SIZE = 250

TYPESENSE_SCHEMA = {
    "name": COLLECTION_NAME,
    "fields": [
        {"name": "id", "type": "string"},
        {"name": "source_museum", "type": "string", "facet": True},
        {"name": "source_url", "type": "string", "index": False},
        {"name": "title", "type": "string", "optional": True},
        {"name": "description", "type": "string", "optional": True},
        {"name": "object_type", "type": "string", "optional": True, "facet": True},
        {"name": "materials", "type": "string[]", "optional": True, "facet": True},
        {"name": "dimensions", "type": "string", "optional": True, "index": False},
        {"name": "period", "type": "string", "optional": True, "facet": True},
        {"name": "dynasty", "type": "string", "optional": True, "facet": True},
        {"name": "ruler_display_name", "type": "string", "optional": True, "facet": True},
        {"name": "date_start", "type": "int32", "optional": True},
        {"name": "date_end", "type": "int32", "optional": True},
        {"name": "date_display", "type": "string", "optional": True, "index": False},
        {"name": "origin_site_raw", "type": "string", "optional": True, "facet": True},
        {"name": "origin_site_display_name", "type": "string", "optional": True, "facet": True},
        {"name": "origin_certainty", "type": "string", "optional": True, "facet": True},
        {"name": "excavation_id", "type": "string", "optional": True},
        {"name": "current_location", "type": "string", "optional": True},
        {"name": "accession_number", "type": "string", "optional": True},
        {"name": "image_url", "type": "string", "optional": True, "index": False},
        {"name": "thumbnail_url", "type": "string", "optional": True, "index": False},
        {"name": "license", "type": "string", "facet": True},
    ],
}


def _get_typesense_client() -> typesense.Client:
    return typesense.Client({
        "api_key": os.environ.get("TYPESENSE_API_KEY", "hapi-dev-key"),
        "nodes": [{
            "host": os.environ.get("TYPESENSE_HOST", "localhost"),
            "port": os.environ.get("TYPESENSE_PORT", "8108"),
            "protocol": "http",
        }],
        "connection_timeout_seconds": 10,
    })


@asset(
    group_name="index",
    kinds={"python", "typesense"},
    deps=["normalize_met"],
)
def sync_search(context: AssetExecutionContext, database: DatabaseResource) -> None:
    """Sync all canonical artifacts from Postgres to Typesense.

    Drops and recreates the collection each time for idempotency.
    """
    client = _get_typesense_client()

    # Drop existing collection if present
    try:
        client.collections[COLLECTION_NAME].delete()
        context.log.info("Dropped existing Typesense collection")
    except typesense.exceptions.ObjectNotFound:
        pass

    client.collections.create(TYPESENSE_SCHEMA)
    context.log.info("Created Typesense collection")

    # Read all artifacts from Postgres
    engine = database.get_engine()
    with engine.connect() as conn:
        result = conn.execute(sa.select(artifacts_table))
        rows = result.mappings().all()

    context.log.info(f"Found {len(rows)} artifacts to index")

    # Index in batches
    indexed = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        documents = [_row_to_document(row) for row in batch]
        jsonl = "\n".join(json.dumps(doc) for doc in documents)
        client.collections[COLLECTION_NAME].documents.import_(jsonl, {"action": "upsert"})
        indexed += len(batch)

    context.log.info(f"Indexed {indexed} artifacts")
    context.add_output_metadata({"indexed": indexed})


def _row_to_document(row: sa.RowMapping) -> dict:
    """Convert a DB row to a Typesense document, omitting None values."""
    doc = {}
    for key in row.keys():
        value = row[key]
        if value is not None:
            doc[key] = value
    return doc
