"""Brooklyn normalize asset — reads raw Brooklyn data and writes canonical artifacts."""

import json

import sqlalchemy as sa
from dagster import AssetExecutionContext, asset

from pipeline.assets.normalize.brooklyn import BrooklynMapper, is_egyptian
from pipeline.resources import DatabaseResource
from pipeline.types.models import artifacts_table, raw_brooklyn_table

BATCH_SIZE = 500


@asset(
    group_name="normalize",
    kinds={"python", "postgres"},
    deps=["raw_brooklyn"],
)
def normalize_brooklyn(context: AssetExecutionContext, database: DatabaseResource) -> None:
    """Map all raw Brooklyn records to canonical schema and write to artifacts table."""
    mapper = BrooklynMapper()
    engine = database.get_engine()

    with engine.connect() as conn:
        result = conn.execute(sa.select(raw_brooklyn_table))
        raw_rows = result.mappings().all()

    context.log.info(f"Found {len(raw_rows)} raw Brooklyn records to normalize")

    total = len(raw_rows)
    mapped = 0
    skipped = 0

    with engine.begin() as conn:
        for i in range(0, total, BATCH_SIZE):
            batch = raw_rows[i : i + BATCH_SIZE]
            rows = []
            for raw_row in batch:
                raw_data = json.loads(raw_row["data"])
                if not is_egyptian(raw_data):
                    skipped += 1
                    continue
                artifact = mapper.map_to_canonical(raw_data)
                rows.append(artifact.model_dump())

            if rows:
                stmt = sa.dialects.postgresql.insert(artifacts_table).values(rows)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={col: stmt.excluded[col] for col in rows[0] if col != "id"},
                )
                conn.execute(stmt)
                mapped += len(rows)

    context.log.info(f"Normalized {mapped} artifacts, skipped {skipped} non-Egyptian out of {total}")
    context.add_output_metadata({"total_raw": total, "mapped": mapped, "skipped_non_egyptian": skipped})
