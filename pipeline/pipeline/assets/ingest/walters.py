"""Walters Art Museum ingest — reads the museum's published collection files and stores raw rows.

The Walters' collections API (v1) closed in 2023. The museum publishes its collection data instead
as CSV files in the GitHub repository WaltersArtMuseum/api-thewalters-org (CC0). The ingest
resolves the branch to a commit, reads `art.csv` (one row per object) and `media.csv` (one row
per image) at that commit, and stores each candidate object's `art.csv` row with its `media.csv`
rows, as the CSV reader gives them. See docs/museum-sources/walters.md.
"""

import csv
import hashlib
import io
import json

import requests
import sqlalchemy as sa
from dagster import AssetExecutionContext, asset

from pipeline.resources import DatabaseResource
from pipeline.types.models import raw_walters_table

DATA_REPOSITORY = "WaltersArtMuseum/api-thewalters-org"
BRANCH = "main"
# The museum's code for its "Ancient Egypt and Nubia" collection (collections.csv).
EGYPT_COLLECTION_CODE = "EGY"
# The ingest stores every object that may be in scope: its collection codes name the Egyptian
# collection, or its culture names Egypt. Which of them are Egyptian is decided at
# normalization (`is_egyptian` in the mapper).
EGYPT_CULTURE_TEXT = "Egypt"


def resolve_commit() -> str:
    """The commit the branch points at now, so both files are read from one version."""
    resp = requests.get(f"https://api.github.com/repos/{DATA_REPOSITORY}/commits/{BRANCH}", timeout=60)
    resp.raise_for_status()
    return resp.json()["sha"]


def read_csv(commit: str, name: str) -> tuple[list[dict], str]:
    """One published file's rows, and the file's SHA-256. A row with more or fewer fields than
    the header raises."""
    resp = requests.get(f"https://raw.githubusercontent.com/{DATA_REPOSITORY}/{commit}/{name}", timeout=300)
    resp.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(resp.content.decode("utf-8"), newline="")))
    for index, row in enumerate(rows):
        if None in row or None in row.values():
            raise ValueError(f"{name} row {index + 2} does not have the header's fields")
    return rows, hashlib.sha256(resp.content).hexdigest()


def is_candidate(row: dict) -> bool:
    return EGYPT_COLLECTION_CODE in row["CollectionID"] or EGYPT_CULTURE_TEXT in row["Culture"]


def candidate_records(art: list[dict], media: list[dict]) -> list[dict]:
    """Each candidate object's `art.csv` row and its `media.csv` rows, in file order. Raises on a
    repeated object id."""
    ids = [row["ObjectID"] for row in art]
    if len(set(ids)) != len(ids):
        raise ValueError("art.csv repeats an ObjectID")
    by_object: dict[str, list[dict]] = {}
    for row in media:
        by_object.setdefault(row["ObjectID"], []).append(row)
    return [{"object": row, "media": by_object.get(row["ObjectID"], [])} for row in art if is_candidate(row)]


@asset(
    group_name="ingest",
    kinds={"python", "api"},
)
def raw_walters(context: AssetExecutionContext, database: DatabaseResource) -> None:
    """Read the Walters' published `art.csv` and `media.csv` at the branch's current commit and
    store every candidate Egyptian object verbatim. Idempotent: re-running overwrites existing
    records.
    """
    commit = resolve_commit()
    art, art_sha256 = read_csv(commit, "art.csv")
    media, media_sha256 = read_csv(commit, "media.csv")
    records = candidate_records(art, media)
    context.log.info(f"Walters data at {commit}: {len(art)} objects, {len(records)} candidates")
    rows = [{"object_id": r["object"]["ObjectID"], "data": json.dumps(r)} for r in records]
    engine = database.get_engine()
    with engine.begin() as conn:
        for i in range(0, len(rows), 250):
            stmt = sa.dialects.postgresql.insert(raw_walters_table).values(rows[i : i + 250])
            stmt = stmt.on_conflict_do_update(
                index_elements=["object_id"],
                set_={"data": stmt.excluded.data},
            )
            conn.execute(stmt)
    context.log.info(f"Ingest complete: {len(rows)} objects stored")
    context.add_output_metadata({
        "commit": commit, "art_csv_sha256": art_sha256, "media_csv_sha256": media_sha256,
        "objects_in_file": len(art), "stored": len(rows),
    })
