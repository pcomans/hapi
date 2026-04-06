"""Typesense sync — pushes all canonical artifacts to the search index."""

import json
import os
import time

import sqlalchemy as sa
import typesense
from dagster import AssetExecutionContext, asset

from pipeline.resources import DatabaseResource
from pipeline.types.models import artifacts_table

ALIAS_NAME = "artifacts"
BATCH_SIZE = 250

TYPESENSE_FIELDS = [
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
]


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
    deps=["normalize_met", "normalize_harvard"],
)
def sync_search(context: AssetExecutionContext, database: DatabaseResource) -> None:
    """Sync all canonical artifacts from Postgres to Typesense.

    Uses a shadow collection + alias swap for atomicity: indexes into a
    new timestamped collection, then atomically points the alias to it.
    The old collection is deleted after the swap.
    """
    client = _get_typesense_client()
    new_collection_name = f"{ALIAS_NAME}_{int(time.time())}"

    # Create shadow collection
    client.collections.create({
        "name": new_collection_name,
        "fields": TYPESENSE_FIELDS,
    })
    context.log.info(f"Created shadow collection: {new_collection_name}")

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
        results = client.collections[new_collection_name].documents.import_(jsonl, {"action": "upsert"})
        _check_import_results(results)
        indexed += len(batch)

    context.log.info(f"Indexed {indexed} artifacts into {new_collection_name}")

    # Find old collection name before alias swap
    old_collection_name = None
    try:
        alias = client.aliases[ALIAS_NAME].retrieve()
        old_collection_name = alias["collection_name"]
    except typesense.exceptions.ObjectNotFound:
        pass

    # Atomically swap alias to new collection
    client.aliases.upsert(ALIAS_NAME, {"collection_name": new_collection_name})
    context.log.info(f"Swapped alias '{ALIAS_NAME}' to {new_collection_name}")

    # Clean up old collection
    if old_collection_name:
        client.collections[old_collection_name].delete()
        context.log.info(f"Deleted old collection: {old_collection_name}")

    context.add_output_metadata({"indexed": indexed, "collection": new_collection_name})


def _check_import_results(results: str) -> None:
    """Check Typesense import results and raise on any failures."""
    for line in results.strip().split("\n"):
        result = json.loads(line)
        if not result.get("success"):
            raise RuntimeError(
                f"Typesense import failed for document: {result.get('error', 'unknown error')}"
            )


def _row_to_document(row: sa.RowMapping) -> dict:
    """Convert a DB row to a Typesense document, omitting None values."""
    doc = {}
    for key in row.keys():
        value = row[key]
        if value is not None:
            doc[key] = value
    return doc
