"""Dagster resources for the pipeline."""

import os
from functools import cached_property

import sqlalchemy as sa
from dagster import ConfigurableResource


class DatabaseResource(ConfigurableResource):
    """Wraps a SQLAlchemy engine as a Dagster resource."""

    connection_string: str = ""

    def effective_connection_string(self) -> str:
        return self.connection_string or os.environ.get(
            "DATABASE_URL", "postgresql://hapi:hapi@localhost:5432/hapi"
        )

    def get_engine(self) -> sa.engine.Engine:
        if not hasattr(self, "_engine"):
            self._engine = sa.create_engine(self.effective_connection_string())
        return self._engine
