"""Dagster definitions — the entry point for `dagster dev`.

Registers all assets, resources, and schedules.
"""

from dagster import Definitions

from pipeline.assets.enrich.authority_links_asset import authority_links
from pipeline.assets.index.sync_search import sync_search
from pipeline.assets.ingest.brooklyn import raw_brooklyn
from pipeline.assets.ingest.cleveland import raw_cleveland
from pipeline.assets.ingest.harvard import raw_harvard
from pipeline.assets.ingest.met import raw_met
from pipeline.assets.ingest.walters import raw_walters
from pipeline.assets.normalize.brooklyn_asset import normalize_brooklyn
from pipeline.assets.normalize.cleveland_asset import normalize_cleveland
from pipeline.assets.normalize.harvard_asset import normalize_harvard
from pipeline.assets.normalize.met_asset import normalize_met
from pipeline.assets.normalize.walters_asset import normalize_walters
from pipeline.resources import DatabaseResource

defs = Definitions(
    assets=[
        raw_met, normalize_met,
        raw_harvard, normalize_harvard,
        raw_brooklyn, normalize_brooklyn,
        raw_cleveland, normalize_cleveland,
        raw_walters, normalize_walters,
        authority_links,
        sync_search,
    ],
    resources={
        "database": DatabaseResource(),
    },
)
