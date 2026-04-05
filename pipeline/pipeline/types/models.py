"""SQLAlchemy table definitions — the source of truth for the Postgres schema.

The pipeline owns the database schema via Alembic migrations.
The web app (Drizzle) introspects from the live DB to generate its types.
See ADR-011.

These table definitions must stay in sync with the Pydantic CanonicalArtifact
model. A structural test (test_structure.py) verifies column names match.
"""

from sqlalchemy import (
    ARRAY,
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

metadata = MetaData()

artifacts_table = Table(
    "artifacts",
    metadata,
    # Required fields
    Column("id", String, primary_key=True),
    Column("source_museum", String, nullable=False, index=True),
    Column("source_url", Text, nullable=False),

    # Identification
    Column("source_id", String),
    Column("title", Text),
    Column("description", Text),
    Column("object_type", String, index=True),
    Column("materials", ARRAY(String)),
    Column("dimensions", Text),

    # Chronology
    Column("period", String, index=True),
    Column("dynasty", String, index=True),
    Column("ruler_id", String, index=True),
    Column("ruler_display_name", String),
    Column("date_start", Integer),
    Column("date_end", Integer),
    Column("date_display", String),

    # Provenance / origin
    Column("origin_site_id", String, index=True),
    Column("origin_site_display_name", String),
    Column("origin_site_raw", Text),
    Column("origin_certainty", String),
    Column("excavation_id", String, index=True),
    Column("tomb_temple_id", String, index=True),

    # Current location
    Column("current_location", String),
    Column("accession_number", String),
    Column("credit_line", Text),

    # Images + license
    Column("image_url", Text),
    Column("thumbnail_url", Text),
    Column("license", String, nullable=False, default="unknown"),

    # External identifiers
    Column("wikidata_id", String),
)

# Raw museum data tables — one per source, stores API responses verbatim
raw_met_table = Table(
    "raw_met",
    metadata,
    Column("object_id", String, primary_key=True),
    Column("data", Text, nullable=False),
)

raw_brooklyn_table = Table(
    "raw_brooklyn",
    metadata,
    Column("object_id", String, primary_key=True),
    Column("data", Text, nullable=False),
)

raw_harvard_table = Table(
    "raw_harvard",
    metadata,
    Column("object_id", String, primary_key=True),
    Column("data", Text, nullable=False),
)

# Fuzzy match review queue (ADR-009)
fuzzy_match_reviews_table = Table(
    "fuzzy_match_reviews",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("artifact_id", String, nullable=False),
    Column("field", String, nullable=False),
    Column("raw_value", Text, nullable=False),
    Column("matched_id", String),
    Column("confidence", Float, nullable=False),
    Column("status", String, nullable=False, default="pending"),
    Column("reviewed_by", String),
    Column("review_notes", Text),
)
