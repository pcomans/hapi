"""Fetch and reconcile place records from iDAI.gazetteer into authority source JSONL.

Paginates all Egyptian place descendants via the iDAI REST API, fetches full
place records, and reconciles to authority JSONL filtered to archaeological
sites, areas, and landforms.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/idai-gazetteer/fetch.py

Output:
    raw.json           — verbatim API responses (all place records, JSON array)
    reconciled.jsonl   — filtered to archaeological-site/area/landform types
"""

import json
import re
import sys
import time
from pathlib import Path

import requests

SOURCE_DIR = Path(__file__).parent

SEARCH_URL = "https://gazetteer.dainst.org/search.json"
PLACE_URL = "https://gazetteer.dainst.org/place/{gaz_id}"

# Egypt's gazId in iDAI.gazetteer
EGYPT_GAZ_ID = 2042786

# Page size for search pagination
PAGE_LIMIT = 100

# Type values that indicate an archaeological site/area/landform we want to keep.
# The broader filter is needed because iDAI misclassifies some sites — e.g.,
# Qubbet el-Hawa (a major Old Kingdom necropolis) is typed as `landform`.
# Genuine geographic features included by the broader filter won't match any
# provenance string, so they are harmless.
SITE_TYPES = {"archaeological-site", "archaeological-area", "landform"}

# Supplementary gazIds that the (ancestors:2042786 + type filter) search misses
# but which are regularly referenced in Egyptian museum catalog data.
# Each entry: (gazId, display, reason)
# These bypass the type filter in reconcile() because iDAI types them as
# populated-place / administrative-unit / empty (Fayum region) or places them
# under the Sudan ancestor 2042707 (Nubian sites), so the paginated Egypt-tree
# search excludes them. They are fetched individually via /place/{gazId} and
# merged into raw.json alongside the Egypt-tree results.
ADDITIONAL_GAZ_IDS: list[tuple[str, str, str]] = [
    # Fayum region (under Egypt ancestor but excluded by type filter)
    ("2042846", "al-Fayyūm", "populated-place; 'Fayum' is a major museum provenance term (Fayum portraits)"),
    ("2751193", "Fayyum Oasis", "empty types; regional reference"),
    # Nubian sites (under Sudan ancestor 2042707, outside Egypt search)
    ("2751172", "Buhen", "Middle Kingdom fortress; heavily represented in Harvard/Brooklyn collections"),
    ("2751351", "Kerma", "Kushite capital; Harvard excavated extensively"),
    ("2293921", "Meroë", "Meroitic kingdom capital"),
    ("2379057", "Napata", "Kushite royal city; Gebel Barkal complex"),
    ("2361100", "Jebel Barkal", "Napatan sacred mountain / archaeological landmark"),
    ("2042733", "Semna West", "Middle Kingdom fortress"),
    ("2767800", "Tempel von Soleb", "18th Dynasty temple of Amenhotep III"),
    ("2751349", "Kawa", "Kushite temple site"),
    ("2751492", "Sesibi", "Akhenaten-era fortress"),
    ("2042808", "Aniba", "Lower Nubia, Harvard/Penn excavations"),
    ("2767808", "Uronarti", "Middle Kingdom fortress"),
    ("2751391", "Mirgissa", "Middle Kingdom fortress"),
    ("2751155", "Askut", "Middle Kingdom fortress"),
    ("2751146", "Amara West", "New Kingdom Egyptian town in Nubia"),
]

ADDITIONAL_GAZ_ID_SET: set[str] = {gid for gid, _, _ in ADDITIONAL_GAZ_IDS}

# User-Agent for all requests
USER_AGENT = "hapi-pipeline/1.0 (research)"


# ---------------------------------------------------------------------------
# Phase 1 — Collect all Egyptian place IDs via paginated search
# ---------------------------------------------------------------------------

def collect_place_ids(session: requests.Session) -> list[str]:
    """Paginate the iDAI search endpoint and collect all Egyptian place IDs.

    gazIds come back from the API as strings (and are stored as strings in
    raw.json), so they are returned as ``list[str]``.
    """
    gaz_ids: list[str] = []
    offset = 0

    print("Phase 1: collecting place IDs...")

    while True:
        params = {
            "q": "*",
            "fq": f"ancestors:{EGYPT_GAZ_ID}",
            "limit": PAGE_LIMIT,
            "offset": offset,
        }
        resp = session.get(SEARCH_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("result", [])
        if not results:
            break

        for item in results:
            gaz_ids.append(item["gazId"])

        print(f"  offset={offset}: {len(results)} results (total so far: {len(gaz_ids)})", flush=True)

        if len(results) < PAGE_LIMIT:
            break

        offset += PAGE_LIMIT

    print(f"  Collected {len(gaz_ids)} place IDs")
    return gaz_ids


# ---------------------------------------------------------------------------
# Phase 2 — Fetch full place records
# ---------------------------------------------------------------------------

def fetch_place_records(session: requests.Session, gaz_ids: list[str]) -> list[dict]:
    """Fetch full place records for each gazId (gazIds are API-typed strings)."""
    records: list[dict] = []
    total = len(gaz_ids)

    print(f"Phase 2: fetching {total} place records...")

    for i, gaz_id in enumerate(gaz_ids, 1):
        url = PLACE_URL.format(gaz_id=gaz_id)
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        records.append(resp.json())

        if i % 100 == 0 or i == total:
            print(f"  {i}/{total}", flush=True)

        time.sleep(0.05)

    print(f"  Fetched {len(records)} records")
    return records


# ---------------------------------------------------------------------------
# Phase 3 — Save raw.json
# ---------------------------------------------------------------------------

def save_raw(records: list[dict]) -> None:
    """Save verbatim API responses as a JSON array."""
    raw_path = SOURCE_DIR / "raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"  Saved raw.json ({len(records)} records) → {raw_path}")


def load_raw() -> list[dict]:
    """Load previously saved raw.json."""
    raw_path = SOURCE_DIR / "raw.json"
    with open(raw_path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Phase 4 — Reconcile to reconciled.jsonl
# ---------------------------------------------------------------------------

def _extract_cross_refs(identifiers: list[dict]) -> dict:
    """Extract cross-references from the identifiers array.

    iDAI identifier contexts observed in the wild:
      "geonames"      → cross_refs["geonames"]
      "pleiades"      → cross_refs["pleiades"]
      "GND-ID"        → cross_refs["gnd"]  (normalized to lowercase: "gnd-id")
      "arachne-entity"/ "arachne-place" → cross_refs["dai-arachne"]
      everything else → cross_refs["other"]
    """
    cross_refs: dict = {
        "geonames": None,
        "pleiades": None,
        "gnd": None,
        "dai-arachne": None,
        "other": [],
    }
    for entry in identifiers:
        raw_context = entry.get("context", "")
        context = raw_context.lower()
        value = entry.get("value")
        if context == "geonames":
            cross_refs["geonames"] = value
        elif context == "pleiades":
            cross_refs["pleiades"] = value
        elif context in ("gnd", "gnd-id"):
            cross_refs["gnd"] = value
        elif context in ("dai-arachne", "arachne-entity", "arachne-place"):
            # Take first occurrence only
            if cross_refs["dai-arachne"] is None:
                cross_refs["dai-arachne"] = value
        else:
            cross_refs["other"].append({"context": raw_context, "value": value})
    return cross_refs


_PLACE_URL_RE = re.compile(r"/place/(\d+)$")


def _extract_parent_id(parent_field) -> str | None:
    """Extract idai:NNNN from the parent field.

    The API returns parent as a URL string like:
      "https://gazetteer.dainst.org/place/2042858"
    """
    if not parent_field:
        return None
    m = _PLACE_URL_RE.search(parent_field)
    if m:
        return "idai:" + m.group(1)
    return None


def _extract_coordinates(pref_location) -> list | None:
    """Extract [lon, lat] from prefLocation.

    The API returns prefLocation in two forms:
      - A dict: {"coordinates": [lon, lat], "confidence": N, ...}
      - A list directly: [lon, lat]  (observed on some records)
    """
    if pref_location is None:
        return None
    if isinstance(pref_location, list) and len(pref_location) == 2:
        return pref_location
    if isinstance(pref_location, dict):
        coords = pref_location.get("coordinates")
        if coords and isinstance(coords, list) and len(coords) == 2:
            return coords
    return None


def reconcile(records: list[dict]) -> tuple[list[dict], int]:
    """Filter and shape raw place records into authority records.

    Returns a tuple of (reconciled_rows, raw_total) where reconciled_rows has
    the _source block as the first element followed by one record per filtered
    place, and raw_total is the pre-filter count of input records.
    """
    source_block = {
        "_source": {
            "citation": "iDAI.gazetteer, German Archaeological Institute (DAI). https://gazetteer.dainst.org",
            "retrieved": time.strftime("%Y-%m-%d"),
            "license": "CC BY 4.0",
            "raw_file": "sources/idai-gazetteer/raw.json",
        }
    }

    reconciled = [source_block]
    raw_total = len(records)

    for record in records:
        types = record.get("types", [])
        gaz_id = record["gazId"]

        # Supplementary IDs bypass the type filter (they are explicitly curated
        # for museum-provenance reasons — see ADDITIONAL_GAZ_IDS).
        is_supplementary = gaz_id in ADDITIONAL_GAZ_ID_SET

        # Keep only records with at least one matching type, unless supplementary
        if not is_supplementary and not set(types) & SITE_TYPES:
            continue

        # display name
        display = record["prefName"]["title"]

        # alt_labels: all names[].title, deduped, excluding display
        seen_labels: set[str] = {display}
        alt_labels_list = []
        for name_entry in record.get("names", []):
            title = name_entry.get("title")
            if title and title not in seen_labels:
                alt_labels_list.append(title)
                seen_labels.add(title)
        alt_labels = alt_labels_list if alt_labels_list else None

        # coordinates: GeoJSON [lon, lat] order
        coordinates = _extract_coordinates(record.get("prefLocation"))

        # parent_id
        parent_id = _extract_parent_id(record.get("parent"))

        # cross_refs
        cross_refs = _extract_cross_refs(record.get("identifiers", []))

        reconciled.append({
            "kind": "site",
            "id": "idai:" + str(gaz_id),
            "display": display,
            "alt_labels": alt_labels,
            "coordinates": coordinates,
            "types": types,
            "parent_id": parent_id,
            "cross_refs": cross_refs,
        })

    return reconciled, raw_total


def save_reconciled(reconciled: list[dict]) -> None:
    """Save reconciled records as JSONL."""
    jsonl_path = SOURCE_DIR / "reconciled.jsonl"
    with open(jsonl_path, "w", encoding="utf-8", newline="\n") as f:
        for row in reconciled:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"  Saved reconciled.jsonl ({len(reconciled)} lines) → {jsonl_path}")


def print_stats(reconciled: list[dict], raw_total: int) -> None:
    """Print coverage statistics."""
    site_rows = [r for r in reconciled if "_source" not in r]
    filtered = len(site_rows)

    if filtered == 0:
        print("Stats: no site records found")
        return

    with_coords = sum(1 for r in site_rows if r["coordinates"] is not None)
    with_alts = sum(1 for r in site_rows if r["alt_labels"] is not None)
    with_geonames = sum(1 for r in site_rows if r["cross_refs"]["geonames"] is not None)
    with_parent = sum(1 for r in site_rows if r["parent_id"] is not None)
    supplementary_count = sum(
        1 for r in site_rows
        if r["id"].split(":", 1)[1] in ADDITIONAL_GAZ_ID_SET
    )

    print(f"\nStats ({filtered} filtered / {raw_total} total):")
    print(f"  With coordinates:   {with_coords} ({100 * with_coords // filtered}%)")
    print(f"  With alt_labels:    {with_alts} ({100 * with_alts // filtered}%)")
    print(f"  With geonames ref:  {with_geonames} ({100 * with_geonames // filtered}%)")
    print(f"  With parent:        {with_parent} ({100 * with_parent // filtered}%)")
    print(f"  Supplementary additions:  {supplementary_count} (outside Egypt tree or non-standard types)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parse_only = "--parse-only" in sys.argv

    if parse_only:
        raw_path = SOURCE_DIR / "raw.json"
        if not raw_path.exists():
            print("ERROR: raw.json not found. Run without --parse-only first.", file=sys.stderr)
            sys.exit(1)
        print("Running in parse-only mode (using saved raw.json)...")
        records = load_raw()
        print(f"  Loaded {len(records)} records from raw.json")

        # A complete fetch always produces the supplementary IDs. If any are
        # missing, raw.json is stale — fail loudly rather than silently produce
        # a reconciled.jsonl with gaps.
        present_ids = {r["gazId"] for r in records}
        missing = ADDITIONAL_GAZ_ID_SET - present_ids
        if missing:
            raise RuntimeError(
                f"raw.json is missing supplementary gazIds: {sorted(missing)}. "
                "Re-run fetch.py without --parse-only to regenerate."
            )
    else:
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})

        # Phase 1: collect IDs
        gaz_ids = collect_place_ids(session)

        # Phase 2: fetch full records
        records = fetch_place_records(session, gaz_ids)

        # Phase 2b: fetch supplementary IDs (outside Egypt tree or wrong type).
        # Skip any that are already present from the Egypt-tree search (some
        # Fayum IDs are descendants of Egypt — they are re-included here to
        # bypass the type filter, but fetching them again would duplicate).
        present_ids = {r["gazId"] for r in records}
        supplementary_ids = [
            gid for gid, _, _ in ADDITIONAL_GAZ_IDS if gid not in present_ids
        ]
        print(
            f"Phase 2b: fetching {len(supplementary_ids)} supplementary place records "
            f"({len(ADDITIONAL_GAZ_IDS) - len(supplementary_ids)} already present from Egypt search)..."
        )
        supplementary_records = fetch_place_records(session, supplementary_ids)
        records.extend(supplementary_records)

        # Phase 3: save raw
        print("Phase 3: saving raw.json...")
        save_raw(records)

    # Phase 4: reconcile
    print("Phase 4: reconciling...")
    reconciled, raw_total = reconcile(records)
    save_reconciled(reconciled)

    print_stats(reconciled, raw_total)


if __name__ == "__main__":
    main()
