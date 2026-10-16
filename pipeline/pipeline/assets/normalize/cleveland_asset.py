"""Cleveland normalize asset — reads raw Cleveland data and writes canonical artifacts."""

import json

import sqlalchemy as sa
from dagster import AssetExecutionContext, asset

from pipeline.assets.normalize.cleveland import ClevelandMapper, is_egyptian
from pipeline.resources import DatabaseResource
from pipeline.types.models import artifacts_table, raw_cleveland_table

BATCH_SIZE = 500


@asset(
    group_name="normalize",
    kinds={"python", "postgres"},
    deps=["raw_cleveland"],
)
def normalize_cleveland(context: AssetExecutionContext, database: DatabaseResource) -> None:
    """Map all raw Cleveland records (Egyptian collections only) to canonical schema and write to artifacts table."""
    mapper = ClevelandMapper()
    engine = database.get_engine()

    with engine.connect() as conn:
        result = conn.execute(sa.select(raw_cleveland_table))
        raw_rows = result.mappings().all()

    context.log.info(f"Found {len(raw_rows)} raw Cleveland records to normalize")

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

    context.log.info(f"Normalized {mapped} artifacts, skipped {skipped} out of scope (Near Eastern or modern forgery) out of {total}")
    context.add_output_metadata({"total_raw": total, "mapped": mapped, "skipped_out_of_scope": skipped})
