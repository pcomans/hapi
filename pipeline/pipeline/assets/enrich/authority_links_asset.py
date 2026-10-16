"""Authority links asset — resolves every museum mention and writes the run's files (#338)."""

import json
import os
from pathlib import Path

import sqlalchemy as sa
from dagster import AssetExecutionContext, asset

from pipeline.enrich.link_files import run_lock, write_run_locked
from pipeline.resources import DatabaseResource
from pipeline.types.models import artifacts_table, raw_brooklyn_table, raw_harvard_table, raw_met_table

RAW_TABLES = {"met": raw_met_table, "brooklyn": raw_brooklyn_table, "harvard": raw_harvard_table}
# Where the runs are written: files first, a database table later (owner, 2026-10-16).
DEFAULT_ROOT = Path(__file__).resolve().parents[4] / "data" / "authority-links"


@asset(
    group_name="enrich",
    kinds={"python"},
    deps=["normalize_met", "normalize_harvard", "normalize_brooklyn"],
)
def authority_links(context: AssetExecutionContext, database: DatabaseResource) -> None:
    """Resolve every mention of every canonical record in both modes and write the run under
    HAPI_AUTHORITY_LINKS_DIR (default `data/authority-links/`)."""
    engine = database.get_engine()
    root = Path(os.environ.get("HAPI_AUTHORITY_LINKS_DIR", DEFAULT_ROOT))
    # The lock is taken before the tables are read, so a run cannot read older inputs than one
    # that becomes current before it; one REPEATABLE READ transaction reads every table from one
    # snapshot, so canonical rows and raw payloads are of the same moment.
    with run_lock(root):
        with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn, conn.begin():
            canonical = [dict(row) for row in conn.execute(sa.select(artifacts_table)).mappings()]
            raw = {museum: {row["object_id"]: json.loads(row["data"])
                            for row in conn.execute(sa.select(table)).mappings()}
                   for museum, table in RAW_TABLES.items()}
        manifest = write_run_locked(canonical, raw, root)
    context.log.info(f"authority links run {manifest['run_id']}: {manifest['files']['links-authority.ndjson.gz']['rows']} links")
    context.add_output_metadata({
        "run_id": manifest["run_id"],
        "records": manifest["records"],
        "links_authority": manifest["files"]["links-authority.ndjson.gz"]["rows"],
        "links_literal": manifest["files"]["links-literal.ndjson.gz"]["rows"],
    })
