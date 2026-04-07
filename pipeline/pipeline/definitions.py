"""Dagster definitions — the entry point for `dagster dev`.

Registers all assets, resources, and schedules.
"""

from dagster import Definitions

from pipeline.assets.index.sync_search import sync_search
from pipeline.assets.ingest.brooklyn import raw_brooklyn
from pipeline.assets.ingest.harvard import raw_harvard
from pipeline.assets.ingest.met import raw_met
from pipeline.assets.normalize.brooklyn_asset import normalize_brooklyn
from pipeline.assets.normalize.harvard_asset import normalize_harvard
from pipeline.assets.normalize.met_asset import normalize_met
from pipeline.resources import DatabaseResource

defs = Definitions(
    assets=[
        raw_met, normalize_met,
        raw_harvard, normalize_harvard,
        raw_brooklyn, normalize_brooklyn,
        sync_search,
    ],
    resources={
        "database": DatabaseResource(),
    },
)
