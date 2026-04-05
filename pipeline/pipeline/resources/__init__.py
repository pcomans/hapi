"""Dagster resources for the pipeline."""

import os

import sqlalchemy as sa
from dagster import ConfigurableResource


class DatabaseResource(ConfigurableResource):
    """Wraps a SQLAlchemy engine as a Dagster resource."""

    connection_string: str = os.environ.get(
        "DATABASE_URL", "postgresql://hapi:hapi@localhost:5432/hapi"
    )

    def get_engine(self) -> sa.engine.Engine:
        return sa.create_engine(self.connection_string)
