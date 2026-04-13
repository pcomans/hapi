# iDAI.gazetteer — Site Authority Source

## Source

- **Name:** iDAI.gazetteer (Deutsches Archäologisches Institut / German Archaeological Institute)
- **URL:** https://gazetteer.dainst.org
- **License:** CC BY 4.0
- **Retrieved:** 2026-04-13
- **API:** REST JSON, no authentication required

## Counts

- **Total fetched:** 2,061 Egyptian place records (descendants of gazId 2042786)
- **Filtered (site-relevant):** 984 records after `archaeological-site` / `archaeological-area` / `landform` type filter
- **With coordinates:** 920/984 (93%)
- **With alt_labels:** 685/984 (69%)
- **With GeoNames ref:** 300/984 (30%)
- **With parent:** 984/984 (100%)

## Type filter rationale

Records are kept where `types` contains any of:

- `archaeological-site` — covers 854 places; the primary type for excavated sites
- `archaeological-area` — covers 94 places; used for zones that encompass multiple sites
- `landform` — covers 65 places; included because iDAI misclassifies some archaeological sites as landforms

The `landform` extension is necessary because of sites like **Qubbet el-Hawa** — a major Old Kingdom rock-cut necropolis near Aswan — which iDAI types as `landform` rather than `archaeological-site`. This is documented in `docs/site-authority-research.md`. Genuine geographic features (wadis, gebels) that pass the filter will not match any museum provenance string, making them harmless.

## Coordinate order

Coordinates are stored in GeoJSON order: `[longitude, latitude]`.

Example: Deir el-Bahari `[32.60771, 25.73783]` — longitude first, latitude second.

## Schema example

```json
{
  "kind": "site",
  "id": "idai:2110510",
  "display": "Deir el-Bahari",
  "alt_labels": [
    "Deir el-Bahri",
    "Dayr al-Bahri",
    "الدير البحري",
    "Dêr el-Bahari",
    "'northern monastery'"
  ],
  "coordinates": [32.60771, 25.73783],
  "types": ["archaeological-site"],
  "parent_id": "idai:2105638",
  "cross_refs": {
    "geonames": "361834",
    "pleiades": null,
    "gnd": null,
    "dai-arachne": null,
    "other": []
  }
}
```

## Field notes

| Field | Source |
|---|---|
| `id` | `"idai:" + gazId` |
| `display` | `prefName.title` |
| `alt_labels` | All `names[].title` values, deduped, excluding `display`. Includes all languages (Arabic, German, French, ancient Egyptian transliterations, Coptic, etc.). `null` if none. |
| `coordinates` | `prefLocation.coordinates` — GeoJSON `[lon, lat]`. `null` if absent. |
| `types` | `types` array verbatim from API |
| `parent_id` | `"idai:" + parent.gazId` if present, else `null` |
| `cross_refs.geonames` | From `identifiers[context="geonames"].value` |
| `cross_refs.pleiades` | From `identifiers[context="pleiades"].value` |
| `cross_refs.gnd` | From `identifiers[context="GND"].value` (normalized to lowercase) |
| `cross_refs.dai-arachne` | From `identifiers[context="dai-arachne"].value` |
| `cross_refs.other` | All other identifiers as `{context, value}` objects |

## Re-fetch instructions

```bash
cd pipeline && uv run python pipeline/authority/sources/idai-gazetteer/fetch.py
```

This will:
1. Paginate `GET /search.json?q=*&fq=ancestors:2042786` (~21 pages, 100/page)
2. Fetch each full place record via `GET /place/{gazId}`
3. Write `raw.json` (verbatim API responses)
4. Write `reconciled.jsonl` (filtered and shaped authority data)

Runtime: approximately 5–10 minutes (2,061 HTTP requests with 50ms sleep between place fetches).

## Parse-only mode (re-reconcile without re-fetching)

```bash
cd pipeline && uv run python pipeline/authority/sources/idai-gazetteer/fetch.py --parse-only
```

Requires `raw.json` to already exist. Re-runs only phase 4 (reconciliation) from the saved raw data. Use this when adjusting the type filter or schema without re-hitting the API.

## Canary sites

29/30 canary sites from `docs/site-authority-research.md` confirmed present with correct gazIds. The following 10 were spot-checked in `TestIdaiGazetteerIntegrity`:

| Site | gazId | GeoNames |
|---|---|---|
| Deir el-Bahari | 2110510 | 361834 |
| Valley of the Kings | 2096884 | 353494 |
| Karnak | 2178702 | 360964 |
| Saqqara | 2042907 | 349608 |
| Thebes | 2042921 | 347342 |
| Giza | 2089516 | 360995 |
| Abydos | 2412478 | 445007 |
| Amarna | 2296218 | 347585 |
| Medinet Habu | 2042876 | 8224862 |
| Elephantine | 2751511 | 359790 |
