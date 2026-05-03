# iDAI.gazetteer — Site Authority Source

## Source

- **Name:** iDAI.gazetteer (Deutsches Archäologisches Institut / German Archaeological Institute)
- **URL:** https://gazetteer.dainst.org
- **License:** CC BY 4.0
- **Retrieved:** 2026-04-13
- **API:** REST JSON, no authentication required

## Counts

- **Total fetched:** 2,075 place records (2,061 Egyptian descendants of gazId 2042786, plus 14 supplementary IDs fetched individually — 2 others were already present from the Egypt-tree search and deduped; see "Supplementary additions" below)
- **Filtered (site-relevant):** 1,000 records after type filter, including 16 supplementary additions that bypass the filter
- **Supplementary additions:** 16 (Fayum region + Nubian sites — see below)

## Type filter rationale

Records are kept where `types` contains any of:

- `archaeological-site` — covers 854 places; the primary type for excavated sites
- `archaeological-area` — covers 94 places; used for zones that encompass multiple sites
- `landform` — covers 65 places; included because iDAI misclassifies some archaeological sites as landforms

The `landform` extension is necessary because of sites like **Qubbet el-Hawa** — a major Old Kingdom rock-cut necropolis near Aswan — which iDAI types as `landform` rather than `archaeological-site`. This is documented in `docs/site-authority-research.md`. Genuine geographic features (wadis, gebels) that pass the filter will not match any museum provenance string, making them harmless.

## Supplementary additions

The `(ancestors:2042786 + type filter)` search has two structural gaps that the
type filter alone cannot bridge:

1. **Fayum region** is typed `populated-place` / `administrative-unit` / empty,
   all of which the filter rejects — even though "Fayum" is a major museum
   provenance term (Fayum portraits, Lahun, Hawara).
2. **Nubian sites** (Buhen, Kerma, Meroë, Napata, etc.) live under the **Sudan**
   ancestor `2042707`, not Egypt — so the paginated Egyptian search never sees
   them. They appear regularly in Harvard, Penn, Brooklyn, and Met Egyptian
   collections.

Rather than punt this to curation in `sites.json`, the fetch module resolves it
at acquisition: the constant `ADDITIONAL_GAZ_IDS` in `fetch.py` lists 16 gazIds
that are fetched individually via `/place/{gazId}` and merged into `raw.json`
alongside the Egypt-tree results. These records **bypass** the type filter in
`reconcile()` (so a `populated-place` Fayum is retained).

| gazId | Display | Reason |
|---|---|---|
| 2042846 | al-Fayyūm | populated-place; Fayum portraits provenance |
| 2751193 | Fayyum Oasis | empty types; regional reference |
| 2751172 | Buhen | Middle Kingdom fortress (Harvard/Brooklyn) |
| 2751351 | Kerma | Kushite capital (Harvard excavations) |
| 2293921 | Meroë | Meroitic kingdom capital |
| 2379057 | Napata | Kushite royal city |
| 2361100 | Jebel Barkal | Napatan sacred mountain |
| 2042733 | Semna West | Middle Kingdom fortress |
| 2767800 | Tempel von Soleb | 18th Dynasty temple of Amenhotep III |
| 2751349 | Kawa | Kushite temple site |
| 2751492 | Sesibi | Akhenaten-era fortress |
| 2042808 | Aniba | Lower Nubia (Harvard/Penn) |
| 2767808 | Uronarti | Middle Kingdom fortress |
| 2751391 | Mirgissa | Middle Kingdom fortress |
| 2751155 | Askut | Middle Kingdom fortress |
| 2751146 | Amara West | New Kingdom Egyptian town in Nubia |

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
  "parent_in_file": true,
  "is_supplementary": false,
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
| `id` | `"idai:" + gazId`. **Unique join key** — use this, not `display`, for cross-source joins. |
| `display` | `prefName.title`. **NOT unique** — 10 distinct names appear on multiple rows (e.g. `Qasr el-Banât` × 3, `Geheset` × 2 — different real places that happen to share a name). Phase-A consumers must disambiguate via `id`. |
| `alt_labels` | All `names[].title` values, deduped, excluding `display`. Includes all languages (Arabic, German, French, ancient Egyptian transliterations, Coptic, etc.). `[]` if none (uses empty-list sentinel, not `null` — issue #172 Shape I fix). |
| `coordinates` | `prefLocation.coordinates` — GeoJSON `[lon, lat]`. `null` if absent. iDAI's `[0.0, 0.0]` placeholder (used on a handful of gebel records — Gebel Abu-Fôda, Gebel el-Rus, Gebel Scheich el-Haridi, Gebel el-Silsile, Gebel el-Teir) is treated as `null` per issue #172 Shape D fix; `[0, 0]` is a real point in the Atlantic Ocean off Africa, clearly not a valid Egyptian site. |
| `types` | `types` array verbatim from API. The closure of every type that may appear is `KNOWN_TYPES` in `fetch.py`: the three `SITE_TYPES` (`archaeological-site`, `archaeological-area`, `landform`) plus six values that enter via supplementary IDs and multi-typed records (`populated-place`, `building-institution`, `island`, `administrative-unit`, `hydrography`, `landcover`). Enforced by `test_all_types_are_in_known_vocab`. |
| `parent_id` | `"idai:" + <gazId>` extracted from the `parent` URL string (e.g. `"https://gazetteer.dainst.org/place/2042858"` → `"idai:2042858"`), else `null`. **NOT a guaranteed in-file foreign key** — see `parent_in_file`. |
| `parent_in_file` | `true` iff `parent_id` resolves to another row in this file. `false` iff `parent_id` is a valid iDAI reference (e.g. an `administrative-unit` ancestor) that the type filter excluded. `null` iff `parent_id` is `null`. **566/1000 rows currently have `parent_in_file=false`** (the type filter excludes most administrative-unit ancestors). Phase-A consumers must respect this flag — treating `parent_id` as an unconditional internal FK will silently fail on more than half the rows. Issue #172 Shape G fix. |
| `is_supplementary` | `true` iff the row's gazId is in `ADDITIONAL_GAZ_IDS` (Fayum region + Nubian sites — the 16 entries listed in "Supplementary additions" above). These rows bypass the type filter and may carry types outside `SITE_TYPES`. Issue #172 Shape J fix; replaces the prior `importlib`-reload pattern in tests. |
| `cross_refs.geonames` | From `identifiers[context="geonames"].value` |
| `cross_refs.pleiades` | From `identifiers[context="pleiades"].value` |
| `cross_refs.gnd` | From `identifiers[context="GND-ID"].value` (context comparison is lowercased, so `"gnd-id"` / `"gnd"` both match) |
| `cross_refs.dai-arachne` | From `identifiers[context="dai-arachne"].value` |
| `cross_refs.other` | All other identifiers as `{context, value}` objects. `[]` if none. |

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

## Phase A curation notes

These are known data quality issues in the iDAI source that must be addressed
during authority curation (`sites.json`), not here in source acquisition.

**Display name language:** ~186 records have German or Arabic display names
as iDAI `prefName` (e.g., "Theben" for Thebes, "Bibân el-Mulûk" for Valley
of the Kings, "Luxor-Tempel" for Luxor Temple). The English name is typically
present in `alt_labels`. Curation must promote the English alt_label to
`display` for every such record.

**Composite alias gaps:** "Thebes (Luxor)" — used by Brooklyn Museum to
disambiguate from Greek Thebes — has no iDAI entry. Must be added as a
manual alias in `sites.json`.

**Luxor Temple alt_labels:** iDAI provides zero alternate names for Luxor
Temple (idai:2368506, display "Luxor-Tempel"). Must add "Luxor Temple",
"Temple of Luxor" manually in `sites.json`.

Note: The Fayum region and Nubian sites (Buhen, Kerma, Meroë, Napata, etc.)
that previously required manual entry are now resolved at acquisition via
`ADDITIONAL_GAZ_IDS` — see "Supplementary additions" above.
