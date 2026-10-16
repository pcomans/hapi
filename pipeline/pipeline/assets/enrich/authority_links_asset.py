"""Authority links asset — resolves every museum mention and writes the run's files (#338)."""

import json
import os
from pathlib import Path

import sqlalchemy as sa
from dagster import AssetExecutionContext, asset

from pipeline.enrich.link_files import write_run
from pipeline.resources import DatabaseResource
from pipeline.types.models import (
    artifacts_table, raw_brooklyn_table, raw_cleveland_table, raw_harvard_table, raw_met_table,
)

RAW_TABLES = {"met": raw_met_table, "brooklyn": raw_brooklyn_table, "harvard": raw_harvard_table,
              "cleveland": raw_cleveland_table}
# Where the runs are written: files first, a database table later (owner, 2026-10-16).
DEFAULT_ROOT = Path(__file__).resolve().parents[4] / "data" / "authority-links"


@asset(
    group_name="enrich",
    kinds={"python"},
    deps=["normalize_met", "normalize_harvard", "normalize_brooklyn", "normalize_cleveland"],
)
def authority_links(context: AssetExecutionContext, database: DatabaseResource) -> None:
    """Resolve every mention of every canonical record in both modes and write the run under
    HAPI_AUTHORITY_LINKS_DIR (default `data/authority-links/`)."""
    engine = database.get_engine()

    def read_inputs():
        # Called with the run lock held. One REPEATABLE READ transaction reads every table from
        # one snapshot, so canonical rows and raw payloads are of the same moment.
        with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn, conn.begin():
            canonical = [dict(row) for row in conn.execute(sa.select(artifacts_table)).mappings()]
            raw = {museum: {row["object_id"]: json.loads(row["data"])
                            for row in conn.execute(sa.select(table)).mappings()}
                   for museum, table in RAW_TABLES.items()}
        return canonical, raw

    manifest = write_run(Path(os.environ.get("HAPI_AUTHORITY_LINKS_DIR", DEFAULT_ROOT)), read_inputs)
    context.log.info(f"authority links run {manifest['run_id']}: {manifest['files']['links-authority.ndjson.gz']['rows']} links")
    set_aside = manifest["canonical_rows_set_aside"]
    if set_aside:
        context.log.warning(f"{len(set_aside)} canonical rows set aside: the normalize step no longer keeps their "
                            f"raw payload, and the normalize assets do not delete them (#374): {set_aside}")
    context.add_output_metadata({
        "run_id": manifest["run_id"],
        "records": manifest["records"],
        "canonical_rows_set_aside": set_aside,
        "links_authority": manifest["files"]["links-authority.ndjson.gz"]["rows"],
        "links_literal": manifest["files"]["links-literal.ndjson.gz"]["rows"],
    })
