#!/usr/bin/env python3
"""
One-time acquisition script for TM Places bulk dump.

Downloads all geographic entries from Trismegistos Data Services
and writes them to reconciled.jsonl.

Run from the pipeline root:
    uv run python pipeline/authority/sources/tm-places/acquire.py

License of output data: CC BY-SA 4.0
Source: https://www.trismegistos.org/dataservices/tabledump/
"""

import csv
import io
import json
from pathlib import Path

import requests

DUMP_URL = "https://www.trismegistos.org/dataservices/tabledump/dump.php?serve=geo"

FIELDS = [
    "id",
    "country",
    "region",
    "nomos_code",
    "name_latin",
    "name_standard",
    "full_name",
    "status",
    "ethnicon",
    "location",
    "unicode_greek",
    "unicode_egyptian",
    "unicode_coptic",
    "begin_date",
    "begin_date_format",
    "end_date",
    "end_date_format",
    "provincia",
    "coordinates",
]

OUT = Path(__file__).parent / "reconciled.jsonl"


def fetch_dump() -> str:
    print("Fetching TM Places bulk dump (all fields, all countries)…")
    data: list[tuple[str, str]] = []
    for field in FIELDS:
        data.append(("checkbox[]", field))
    data.append(("mode", "csv"))
    resp = requests.post(DUMP_URL, data=data, timeout=120)
    resp.raise_for_status()
    # The dump appends a trailing semicolon to every row (including the header).
    # Strip it so csv.DictReader sees clean column names and values.
    lines = [line.rstrip(";") for line in resp.text.splitlines()]
    return "\n".join(lines)


def parse_coordinates(coord_str: str) -> tuple[float | None, float | None]:
    """Parse 'lat,lon' coordinate string into (latitude, longitude) floats.

    Note: the bulk CSV dump does not populate the coordinates field — it is
    always empty. Coordinates are available via the GeoResponder API
    (georesponder.php?id=<TM_GEO_ID>) but fetching them per-record is out of
    scope for source acquisition. Leave as null; enrich during sites.json
    curation (task 3.2) if needed for map view (Milestone 6).
    """
    if not coord_str or not coord_str.strip():
        return None, None
    parts = coord_str.split(",")
    if len(parts) != 2:
        return None, None
    try:
        return float(parts[0].strip()), float(parts[1].strip())
    except ValueError:
        return None, None


def coerce(value: str) -> str | None:
    """Convert empty string to None; strip whitespace."""
    stripped = value.strip() if value else ""
    return stripped if stripped else None


def transform_row(row: dict) -> dict:
    lat, lon = parse_coordinates(row.get("coordinates", ""))
    begin = row.get("begin_date", "").strip()
    end = row.get("end_date", "").strip()
    # TM uses 0 as a sentinel meaning "unknown/unspecified", not year 0 (which
    # is not a meaningful historical date in this context). Convert 0 → null.
    begin_int = int(begin) if begin else None
    end_int = int(end) if end else None
    return {
        "kind": "site",
        "tm_id": int(row["id"]) if row.get("id", "").strip() else None,
        "name_standard": coerce(row.get("name_standard", "")),
        "name_latin": coerce(row.get("name_latin", "")),
        "name_greek": coerce(row.get("unicode_greek", "")),
        "name_egyptian": coerce(row.get("unicode_egyptian", "")),
        "name_coptic": coerce(row.get("unicode_coptic", "")),
        "country": coerce(row.get("country", "")),
        "region": coerce(row.get("region", "")),
        "nomos_code": coerce(row.get("nomos_code", "")),
        "status": coerce(row.get("status", "")),
        "ethnicon": coerce(row.get("ethnicon", "")),
        "location": coerce(row.get("location", "")),
        "provincia": coerce(row.get("provincia", "")),
        "latitude": lat,
        "longitude": lon,
        "begin_date": begin_int if begin_int else None,
        "end_date": end_int if end_int else None,
        "note": None,
    }


def main() -> None:
    raw = fetch_dump()

    # Peek at the header to confirm column names
    first_line = raw.split("\n")[0]
    print(f"CSV header: {first_line}")

    reader = csv.DictReader(io.StringIO(raw))
    rows = list(reader)
    print(f"Total records: {len(rows)}")

    all_records = [transform_row(r) for r in rows]
    # Egypt covers the Nile Valley and Delta. Sudan covers ancient Nubia
    # (Meroe, Napata, Kerma, Soleb, Semna etc.) — all part of Egyptological
    # collections at Met, Brooklyn, and Harvard.
    records = [r for r in all_records if r.get("country") in ("Egypt", "Sudan")]

    # Sort by tm_id for stable diffs
    records.sort(key=lambda r: r["tm_id"] or 0)

    with OUT.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Total records in dump: {len(all_records)}")
    print(f"Written {len(records)} rows (Egypt + Sudan) to {OUT}")


if __name__ == "__main__":
    main()
