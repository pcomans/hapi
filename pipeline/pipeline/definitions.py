"""Dagster definitions — the entry point for `dagster dev`.

Registers all assets, resources, and schedules.
New museum assets are auto-discovered from the assets/ subdirectory.
"""

from dagster import Definitions

# Assets will be imported here as they are implemented.
# Example (uncomment when assets exist):
#
# from dagster import load_assets_from_modules
# from pipeline.assets import ingest, normalize, enrich, index
#
# all_assets = [
#     *load_assets_from_modules([ingest]),
#     *load_assets_from_modules([normalize]),
#     *load_assets_from_modules([enrich]),
#     *load_assets_from_modules([index]),
# ]

defs = Definitions(
    assets=[],
    resources={},
)
