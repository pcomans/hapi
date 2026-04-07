"""Brooklyn Museum ingest — fetches all Egyptian department objects and stores raw JSON.

Two-phase approach:
1. Search API pagination (search.brooklynmuseum.org) — no auth, no bot protection.
   Gets: sourceId, title, dates, startYear, endYear, classification, geographicalLocations,
   imageUrl, accessionNumber, constituents, description, onView, collection.
2. RSC detail fetch via Playwright — www.brooklynmuseum.org blocks curl/requests with
   Vercel bot protection, so we use a headless browser to fetch RSC payloads from within
   the domain context. Gets: medium, dimensions, dynasty, period, creditLine, provenance,
   rightsType, inscribed, objectDate, objectDateBegin, objectDateEnd, section.

Both sources are merged into a single JSON blob per object in raw_brooklyn.
"""

import json
import logging

import requests
import sqlalchemy as sa
from dagster import AssetExecutionContext, asset

from pipeline.resources import DatabaseResource
from pipeline.types.models import raw_brooklyn_table

logger = logging.getLogger(__name__)

SEARCH_API_BASE = "https://search.brooklynmuseum.org/api/search"
BROOKLYN_BASE_URL = "https://www.brooklynmuseum.org"
COLLECTION_NAME = "Egyptian, Classical, Ancient Near Eastern Art"
SEARCH_PAGE_SIZE = 50
RSC_BATCH_SIZE = 20
DB_BATCH_SIZE = 250


@asset(
    group_name="ingest",
    kinds={"python", "api"},
)
def raw_brooklyn(context: AssetExecutionContext, database: DatabaseResource) -> None:
    """Fetch all Brooklyn Egyptian department objects and store raw JSON verbatim.

    Two-phase process:
    1. Paginate search API to get all sourceIds and basic metadata
    2. Fetch RSC detail pages via Playwright for medium, dynasty, period, etc.

    Idempotent: re-running overwrites existing records.
    """
    # Phase 1: Search API pagination
    context.log.info("Phase 1: Fetching search API pages...")
    search_records = _fetch_all_search_pages(context)
    context.log.info(f"Phase 1 complete: {len(search_records)} objects from search API")

    # Phase 2: RSC detail fetch via Playwright
    context.log.info("Phase 2: Fetching RSC detail pages via Playwright...")
    source_ids = [r["sourceId"] for r in search_records]
    detail_map = _fetch_rsc_details_playwright(context, source_ids)
    context.log.info(f"Phase 2 complete: {len(detail_map)} detail records fetched")

    # Merge and store
    context.log.info("Merging search + detail data and storing...")
    engine = database.get_engine()
    stored = 0

    for i in range(0, len(search_records), DB_BATCH_SIZE):
        batch = search_records[i : i + DB_BATCH_SIZE]
        rows = []
        for record in batch:
            source_id = record["sourceId"]
            merged = {**record}
            detail = detail_map.get(source_id)
            if detail:
                # Overlay RSC detail fields onto search data
                for field in (
                    "medium", "dimensions", "dynasty", "period", "creditLine",
                    "provenance", "rightsType", "inscribed", "objectDate",
                    "objectDateBegin", "objectDateEnd", "section",
                ):
                    if field in detail:
                        merged[field] = detail[field]
            rows.append({"object_id": source_id, "data": json.dumps(merged)})

        with engine.begin() as conn:
            stmt = sa.dialects.postgresql.insert(raw_brooklyn_table).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["object_id"],
                set_={"data": stmt.excluded.data},
            )
            conn.execute(stmt)
        stored += len(rows)
        context.log.info(f"Stored {stored}/{len(search_records)}")

    context.log.info(f"Ingest complete: {stored} objects stored ({len(detail_map)} with detail data)")
    context.add_output_metadata({
        "total_search": len(search_records),
        "total_detail": len(detail_map),
        "stored": stored,
    })


def _fetch_all_search_pages(context: AssetExecutionContext) -> list[dict]:
    """Paginate the Brooklyn search API to get all objects in the Egyptian department."""
    records: list[dict] = []
    page = 1

    while True:
        resp = requests.get(
            SEARCH_API_BASE,
            params={
                "type": "collectionObject",
                "collection.name": COLLECTION_NAME,
                "size": SEARCH_PAGE_SIZE,
                "page": page,
                "sortField": "accessionNumber",
                "sortOrder": "asc",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        page_records = data.get("data", [])
        if not page_records:
            break

        records.extend(page_records)

        total = data.get("metadata", {}).get("total", 0)
        context.log.info(f"Search page {page}: {len(records)}/{total} fetched")

        # Stop when we've got all records
        if len(records) >= total:
            break
        page += 1

    return records


def _fetch_rsc_details_playwright(
    context: AssetExecutionContext, source_ids: list[str]
) -> dict[str, dict]:
    """Fetch RSC detail data for all objects using Playwright.

    Launches a headless browser, navigates to a Brooklyn Museum page to pass
    Vercel's bot protection, then uses page.evaluate(fetch(...)) to get RSC
    payloads from within the browser context.
    """
    from playwright.sync_api import sync_playwright

    detail_map: dict[str, dict] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the Brooklyn Museum site to establish context/cookies
        context.log.info("Navigating to Brooklyn Museum to pass Vercel checkpoint...")
        page.goto(f"{BROOKLYN_BASE_URL}/opencollection", wait_until="networkidle", timeout=60000)
        context.log.info("Browser context established")

        # Fetch RSC details in batches
        total = len(source_ids)
        for i in range(0, total, RSC_BATCH_SIZE):
            batch_ids = source_ids[i : i + RSC_BATCH_SIZE]
            results = page.evaluate(_JS_FETCH_BATCH, batch_ids)

            for source_id, detail in results.items():
                if detail:
                    detail_map[source_id] = detail

            context.log.info(
                f"RSC detail: {min(i + RSC_BATCH_SIZE, total)}/{total} "
                f"({len(detail_map)} successful)"
            )

        browser.close()

    return detail_map


# JavaScript function executed in the browser context to fetch and parse RSC payloads.
# Takes an array of sourceIds, fetches them concurrently, parses the RSC payload
# using the ref-map approach documented in brooklyn.md, and returns the detail fields.
_JS_FETCH_BATCH = """
async (sourceIds) => {
    const results = {};

    const fetches = sourceIds.map(async (sourceId) => {
        try {
            const resp = await fetch(`/objects/${sourceId}`, {
                headers: {
                    'RSC': '1',
                    'Next-Url': `/DEFAULT/objects/${sourceId}`
                }
            });
            const text = await resp.text();

            // Build ref map from RSC lines
            const lines = text.split('\\n');
            const refMap = {};
            for (const line of lines) {
                const colonIdx = line.indexOf(':');
                if (colonIdx > 0 && colonIdx < 10) {
                    const id = line.substring(0, colonIdx);
                    const data = line.substring(colonIdx + 1);
                    if (data.startsWith('{') || data.startsWith('[') || data.startsWith('"')) {
                        try { refMap[id] = JSON.parse(data); } catch(e) {}
                    }
                }
            }

            // Find the collectionObject
            let obj = null;
            for (const val of Object.values(refMap)) {
                if (val && typeof val === 'object' && val._type === 'collectionObject' && val.accessionNumber) {
                    obj = val;
                    break;
                }
            }

            if (obj) {
                results[sourceId] = {
                    medium: obj.medium || null,
                    dimensions: obj.dimensions || null,
                    dynasty: obj.dynasty || null,
                    period: obj.period || null,
                    creditLine: obj.creditLine || null,
                    provenance: obj.provenance || null,
                    rightsType: obj.rightsType || null,
                    inscribed: obj.inscribed || null,
                    objectDate: obj.objectDate || null,
                    objectDateBegin: obj.objectDateBegin ?? null,
                    objectDateEnd: obj.objectDateEnd ?? null,
                    section: obj.section || null
                };
            }
        } catch(e) {
            // Skip failed fetches — search data is still available
        }
    });

    await Promise.all(fetches);
    return results;
}
"""
