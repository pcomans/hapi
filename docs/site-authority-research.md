# Site Authority Sources: Research Findings

**Date:** 2026-04-13
**Context:** ADR-012 designated TM Places as the sole site authority. Egyptologist review revealed TM Places has papyrological bias — pharaonic archaeological sites are subsumed under coarse toponyms (e.g., Deir el-Bahari, Valley of the Kings, and Medinet Habu all lumped into TM Geo 1341 "Memnoneia"), making them unusable for resolving museum provenance strings. This document reports live research into five candidate replacement sources.

## Executive Summary

**Recommended sole site authority: iDAI.gazetteer**

| Rank | Source | Verdict |
|---|---|---|
| 1 | **iDAI.gazetteer** | **Sole site authority.** 2,061 Egyptian places (filter to ~1,000 site-relevant types). 29/30 sites found across Upper Egypt, Delta, Middle Egypt, Fayum, and Nubia. Rich multilingual names, hierarchy, coordinates. CC BY 4.0. No auth. |
| 2 | **Wikidata** | Dropped. CC0 and SPARQL are attractive, but adds complexity as a second source. Could revisit for tomb-level granularity if individual tomb provenance becomes a mapper requirement. |
| 3 | **PAThs** | Dropped. CC BY-NC-SA license creates a permanent ceiling on commercial use. |
| 4 | **TopBib** | Not needed. Bibliographic index, not a site gazetteer. Undocumented JSON API exists if bibliography enrichment becomes a future requirement. |
| 5 | **Theban Mapping Project** | Dead end. Site returning 403/503, no API, restrictive copyright. |

TM Places is dropped as a site authority source. Its papyrological bias (built from documentary attestations, not archaeological provenance) means pharaonic sites are present but subsumed under coarse toponyms — Deir el-Bahari, Valley of the Kings, Medinet Habu, and Deir el-Medina are all lumped into a single entry (TM Geo 1341, "Memnoneia - Djeme / Thebes west"). You cannot resolve a Met provenance string like "Thebes, Deir el-Bahri" to a specific TM place because TM Places does not distinguish these sites from each other. iDAI.gazetteer models them as separate entries with distinct coordinates and hierarchy.

---

## 1. iDAI.gazetteer (German Archaeological Institute)

**Verdict: SOLE SITE AUTHORITY.**

### Access

- **API root:** `https://gazetteer.dainst.org`
- **No authentication required**
- **License:** CC BY 4.0
- **Format:** JSON REST API (undocumented but fully functional)

### Key endpoints

| Endpoint | Description |
|---|---|
| `GET /search.json?q=TERM` | Full-text search |
| `GET /place/{gazId}` (Accept: application/json) | Full record |
| `GET /search.json?q=*&fq=ancestors:2042786&limit=100&offset=0` | All Egyptian places (paginated) |

### Egypt coverage

- **Egypt's gazId:** 2042786
- **Total descendants:** 2,061 places
- **Archaeological sites:** 854
- **Other types:** 575 building/institution, 356 populated-place, 94 archaeological-area, 65 landform, etc.

### Canary site results: 10/10 found

| Site | gazId | Coordinates | Cross-refs |
|---|---|---|---|
| Deir el-Bahari | 2110510 | 32.608, 25.738 | GeoNames 361834, Toponyms-ID 71 |
| Valley of the Kings | 2096884 | 32.602, 25.740 | GeoNames 353494, GND 4078137-9 |
| Karnak | 2178702 | 32.654, 25.718 | GeoNames 360964, Pleiades 786050 |
| Saqqara | 2042907 | 31.217, 29.850 | GeoNames 349608, Pleiades 796289136 (sub-feature; canonical is 737148) |
| Thebes | 2042921 | 32.638, 25.692 | GeoNames 347342, Pleiades 786017 |
| Giza | 2089516 | 31.130, 29.980 | GeoNames 360995 |
| Abydos | 2412478 | 31.922, 26.184 | GeoNames 445007 |
| Amarna | 2296218 | 30.900, 27.700 | GeoNames 347585, Pleiades 149576487 (sub-feature; canonical is 589957) |
| Medinet Habu | 2042876 | 32.600, 25.700 | GeoNames 8224862 |
| Elephantine | 2751511 | 32.885, 24.085 | GeoNames 359790 |

### Standout feature: multilingual alternate names

Records include rich multilingual name variants. Examples across the canary sites:
- Modern Arabic (script + transliterated): e.g., "الدير البحري" for Deir el-Bahari
- Ancient Egyptian (transliterated, marked `ancient: true`)
- Ancient Greek: e.g., "Diospolis" for Thebes
- Coptic: e.g., "Djeme" for Medinet Habu
- Meaning translations: e.g., "'northern monastery'" for Deir el-Bahari

This directly solves our mapper alias-matching problem — museums use wildly different spellings.

### Extended audit: Delta, Middle Egypt, and Fayum (20 additional sites)

A follow-up audit tested 20 sites beyond the initial Upper Egyptian canary set. **19 out of 20 are correctly typed as `archaeological-site` and would pass the filter.** The sole exception is Qubbet el-Hawa (typed `landform`), which is why the type filter was broadened.

Sites confirmed present with coordinates and cross-refs: Asasif, Sheikh Abd el-Qurna, Dra Abu el-Naga, Beni Hasan, Tell el-Amarna, Hawara, Lahun, Gurob, Naucratis, Tell Basta (Bubastis), Tanis, Lisht, Abusir, Dahshur, Dendera, Edfu, Kom Ombo, Philae, Abu Simbel.

### Hierarchy

Clear parent-child structure from country down to individual monuments:

```
World > Afrika > Agypten > Qina (Governorate) > Theben >
  ├── Karnak
  └── Theben West >
       ├── Medinet Habu
       ├── Valley of the Kings
       └── Deir el-Bahari >
            └── Heiligtum der Hatschepsut (sub-monument)
```

### Cross-reference systems

| System | Coverage |
|---|---|
| GeoNames | Very common |
| Pleiades | Present on major sites (Karnak, Saqqara, Thebes, Amarna) |
| GND (German National Library) | Common |
| DAI Arachne | Very common |
| DAI Cairo Toponyms | Common for Egyptian sites |
| **Trismegistos** | **ABSENT** — no TM IDs |
| **Wikidata** | **ABSENT** — no Q-IDs |

The missing TM and Wikidata cross-refs mean we'd need to bridge through Pleiades or GeoNames.

### Record schema

```
gazId, @id (canonical URI)
parent, ancestors (hierarchy)
types: ["archaeological-site", "populated-place", ...]
prefName: {title, language, transliterated?, ancient?}
names: [{title, language, ...}, ...] (alternate names)
prefLocation: {coordinates: [lon, lat], confidence: 0-3}
  — may include GeoJSON "shape" polygons
identifiers: [{value, context}, ...] (cross-refs)
tags: ["necropolis", "temple", "tell", ...]
```

---

## 2. Wikidata

**Verdict: DROPPED. Adds complexity as a second source; no current need for its unique strengths.**

### Access

- **Endpoint:** `https://query.wikidata.org/sparql`
- **License:** CC0 (public domain)
- **Format:** SPARQL + JSON

### What it offers

- **CC0 license** — no restrictions whatsoever
- **Tomb-level granularity** — individual KV, QV, TT entries with occupant data
- **Alt-labels** (`skos:altLabel`) — variant spellings in English for alias matching
- **Cross-reference hub** — bridges to TM (P1598), Pleiades (P1584), GeoNames (P1566)
- **Existing integration pattern** — `wikidata-pharaohs/fetch.py` already queries Wikidata

### Why dropped

Wikidata's strengths (tomb-level granularity, TM cross-refs) don't address a current requirement. No museum in our corpus provides tomb-number provenance, and we don't need TM interoperability now. Adding a second source doubles the reconciliation complexity. If either requirement materializes, Wikidata is the obvious first source to revisit.

SPARQL queries from the research brief could not be executed (sandbox blocks `*.wikidata.org`). The Q-IDs in the brief were all wrong (lookup errors by the brief author, not a Wikidata quality issue), but this is moot since we're not using it.

---

## 3. PAThs (Archaeological Atlas of Coptic Literature)

**Verdict: VALUABLE SUPPLEMENT, but NC license is a concern.**

### Access

- **Frontend:** `https://atlas.paths-erc.eu` (React SPA, live)
- **API:** `https://bdus.cloud/db/api/paths/` (v4.5.1, no auth required)
- **License:** CC BY-NC-SA (non-commercial — needs legal review)

### Coverage

- **481 total places** in the database
- **399 have coordinates** (83%)
- **358 have TM GeoIDs** (74%) — unique among all candidates
- **325 have Pleiades IDs** (68%)
- **12 geographic regions** covering all Egypt + Nubia + oases

Despite Coptic focus, strong pharaonic representation:
- New Kingdom: 126 phase records
- Late Period: 60
- Middle Kingdom: 39
- Old Kingdom: 28

### Canary site results: mixed

| Site | Found? | PAThs ID | TM GeoID | Pleiades |
|---|---|---|---|---|
| Karnak | Yes | 182 | 576, 13524, 13525 | 786017, 786050 |
| Luxor | Yes | 19 | 576 | 786017 |
| Giza | Yes | 274 | 716 | 442962448 |
| Abydos | Yes | 23 | 34 | 756512 |
| Memphis | Yes | 1 | 1344 | 736963 |
| Western Thebes sub-sites | Yes | 111 entries | Various | Various |
| **Saqqara** | **NO** | — | — | — |
| **Deir el-Bahari** | **NO** (covered indirectly) | — | — | — |

### Standout feature: TM GeoID cross-references

PAThs is the ONLY candidate that provides direct Trismegistos GeoID links. This bridges the gap between iDAI.gazetteer (which lacks TM IDs) and our existing TM Places data. 358 places with TM cross-refs.

### Multilingual toponyms

Rich name data per place. Example for Karnak:
- Egyptian: `Ip.t-sw.t`, `Ns.wt-ta.wy`
- Greek: `Thebai`
- Coptic: `ne`
- Arabic: `كرنك`
- English: `Karnak`, `Eastern Thebes`

### Record schema

```
id, name, copticname, greekname, arabicname, egyptianname
tmgeo (TM GeoID), pleiades (Pleiades ID)
region, area, nomos (ancient nome), province (Byzantine)
typology (36 values: settlement, monastery, temple, tomb, ...)
toporeferredto (parent site)
datefrom, dateto
+ plugin tables: toponyms, placephase, biblio, geodata
```

### Acquisition plan

1. Single call: `verb=search&shortsql=@paths__places` with `records_per_page=500` gets all 481 IDs
2. Individual `verb=read&tb=paths__places&id={id}` for full records (481 calls)
3. Extract TM GeoIDs as the primary cross-reference bridge
4. **Legal review required** on CC BY-NC-SA before integration

---

## 4. TopBib / Griffith Institute

**Verdict: ENRICHMENT SOURCE ONLY. Not a site gazetteer.**

### Access

- **URL:** `https://topbib.griffith.ox.ac.uk` (live, launched January 2026)
- **Backend:** Express.js + MongoDB
- **License:** No visible terms of use (legal ambiguity)
- **API:** Undocumented JSON endpoints discovered via reverse engineering

### What it is

The **Digital Topographical Bibliography** (Porter & Moss) — the canonical Egyptological reference for locating every published mention of an Egyptian monument or artifact, organized topographically. It's a *bibliographic* index, not a *site* gazetteer.

### Coverage

6,279 nodes (5,073 leaf records) across 8 sections:

| Section | Nodes |
|---|---|
| Thebes: Tombs | 1,214 |
| Thebes: Temples | 385 |
| Memphis | 383 |
| Lower and Middle Egypt | 1,490 |
| Upper Egypt: Sites | 423 |
| Upper Egypt: Temples | 103 |
| Nubia, deserts, etc. | 790 |
| Provenance Not Known | 1,490 |

**Limitation:** Only 55 TT entries digitized (mostly Deir el-Medina). TT100 (Rekhmire) is NOT in the database yet. ~1 million handwritten reference slips remain to be digitized.

### Undocumented JSON API

| Endpoint | Auth | Returns |
|---|---|---|
| `GET /tree/published?date=none` | Public | Full 6,279-node hierarchy (496 KB JSON) |
| `GET /record/fields?id={mongoId}` | Public | Full record with bibliography, geolocation, ancestors |
| `GET /record/search?title=X&name=X` | Public | Matching record IDs |
| `GET /record/allfields?id={mongoId}` | **Auth required** | Extended fields |
| `GET /geo/list?date=none` | **Auth required** | Geolocation data |

No rate limiting detected. No CORS headers (server-side access only).

### Record schema

```
_id, title, type ("area"|"site"|"structure"|"finds")
identifier (permalink slug), parent, children, ancestors
geolocation: {latitude, longitude, radius} or null
modern_names, ancient_names, related_places
printed_source (PM volume/page)
bibliographies: [{name, cites: [{author, title, date, pages, ...}]}]
user_notes (HTML, may contain hieroglyphic Unicode)
```

### TM cross-references (corrected finding)

Initial research incorrectly reported TopBib had no cross-references. Re-examination found **464 unique TM GeoIDs** as structured JSON in `modern_names[].sources[]`, `ancient_names[].sources[]`, and `related_places[].sources[]`. Also 106 TLA (Thesaurus Linguae Aegyptiae) cross-refs. These are first-class structured fields, not embedded HTML links.

### Why not primary

- It's a bibliography, not a gazetteer — tells you where things were *published*, not where they *are*
- Bulk geolocation data gated behind auth (`/geo/list` requires login), though 861 nodes carry lat/lng in the public tree
- No Pleiades IDs, no GeoNames IDs (TM cross-refs are the only external identifiers)
- Incomplete digitization (TT100 missing, many sections sparse)
- No visible license — legal risk
- Undocumented API with no CORS — may not be intended for external consumption

### Potential future use

Best available TM bridge if interoperability with Trismegistos becomes a requirement — pending license clarification with the Griffith Institute. Could also enrich artifact records with "published in PM vol.X p.Y" references.

---

## 5. Theban Mapping Project

**Verdict: DEAD END.**

### Status

- `thebanmappingproject.com` — **403 Forbidden**
- `tmp.arce.org` — **503 Service Unavailable**
- Wayback Machine also inaccessible from sandbox

The site has a history of multi-year outages. Original site (kv5.com) crashed ~2010, ARCE relaunched in 2021, now down again.

### What it would have

~65 KV tomb records with architectural data, condition assessments, axonometric drawings, occupant data. Rich but narrow (KV only, not QV or TT).

### Why it's a dead end

| Factor | Assessment |
|---|---|
| Availability | Currently down (403/503) |
| Structured data | None — pure Drupal HTML |
| API | None |
| Crawlability | robots.txt blocks search parameters |
| License | ARCE copyright, republication requires written approval |
| Volume | ~65 records |
| Overlap with Wikidata | KV tombs exist on Wikidata with coordinates and occupant data, openly licensed |

Wikidata provides the same KV tomb identifiers and basic metadata under CC0. TMP adds architectural detail we don't need for site authority.

---

## Comparative Matrix

| Criterion | iDAI.gazetteer | Wikidata | PAThs | TopBib | TMP |
|---|---|---|---|---|---|
| **Canary resolution** | 10/10 tested | Not runnable (sandbox) but sites confirmed to exist | 5/7 major sites + 111 Theban sub-sites | Not tested (bibliographic) | N/A (offline) |
| **Coordinates** | Yes, confidence-scored, some with GeoJSON polygons | Yes | 83% coverage | Gated behind auth | N/A |
| **Alternate names** | Exceptional (21+ per site, multilingual, ancient) | Good (skos:altLabel in English) | Good (Egyptian, Greek, Coptic, Arabic, English) | Modern + ancient names | N/A |
| **TM cross-refs** | **NO** | Yes (P1598) | **YES — 74% coverage** (unique) | **YES — 464 unique TM GeoIDs** (structured JSON) | N/A |
| **Pleiades cross-refs** | Some major sites | Yes (P1584) | 68% coverage | No | N/A |
| **Wikidata cross-refs** | No | N/A (is Wikidata) | No | No | N/A |
| **Hierarchy** | Excellent (country > governorate > site > monument) | Part-of (P361) relationships | Parent site references | Excellent (PM topographic structure) | N/A |
| **Tomb granularity** | Sub-monument level (individual chapels) | Yes (individual KV, TT entries) | TT/KV numbers in Theban sub-sites | Some TT entries | Would have KV |
| **Total Egypt sites** | 2,061 (~1,013 with broadened filter) | Unknown (query blocked) | 481 | 6,279 nodes (861 geolocated, 499 with TM) | ~65 |
| **License** | **CC BY 4.0** | **CC0** | CC BY-NC-SA | No visible terms | ARCE copyright |
| **API** | REST JSON, no auth | SPARQL, no auth | REST JSON, no auth | Undocumented JSON, partial auth | None |
| **Acquisition effort** | 2,082 HTTP requests, 1hr scripting | Adapt existing fetch.py, 2hr | ~482 HTTP requests, 1hr | ~6,280 requests, legal risk | Dead end |

---

## Acquisition Plan

### iDAI.gazetteer (sole source)

**Deliverable:** `pipeline/pipeline/authority/sources/idai-gazetteer/` with:
- `fetch.py` — paginate all Egyptian descendants, fetch full records
- `raw.json` — verbatim API responses
- `reconciled.jsonl` — normalized to site authority schema

**Steps:**
1. `GET /search.json?q=*&fq=ancestors:2042786&limit=100&offset=0` — paginate through 21 pages to get all 2,061 Egyptian place IDs
2. For each of the 2,061 results, `GET /place/{gazId}` with `Accept: application/json` for full record
3. Filter client-side by `types` containing `archaeological-site`, `archaeological-area`, or `landform`. The broader filter is needed because iDAI misclassifies some sites — e.g., Qubbet el-Hawa (a major Old Kingdom necropolis) is typed as `landform`. Genuine geographic features (wadis, gebels) included by the broader filter won't match any provenance string, so they're harmless. Records can have multiple types (e.g., Amarna is both `archaeological-site` and `populated-place`), so exact count after dedup needs to be determined at acquisition time.
4. Extract: display name, all alternate names (multilingual), coordinates, parent/ancestor hierarchy, GeoNames/Pleiades cross-refs
5. Total: 2,082 HTTP requests (21 pagination + 2,061 place fetches). No rate limiting detected. ~1 hour of scripting, ~5 minutes of runtime.

**Schema for `sites.json` entries:**
```json
{
  "id": "idai:2110510",
  "display": "Deir el-Bahari",
  "aliases": ["Deir el-Bahri", "Dayr al-Bahri", "الدير البحري", ...],
  "coordinates": [32.60771, 25.73783],
  "parent": "idai:2105638",
  "cross_refs": {
    "geonames": "361834",
    "pleiades": null,
    "idai": "2110510"
  }
}
```

### Tomb-level granularity

iDAI has only 5 tombs under Valley of the Kings (KV 2, KV 11, KV 17, plus two others). No KV62, no TT100. However, no museum in our current corpus provides tomb-number provenance — all mapper output is settlement/monument-level ("Thebes", "Saqqara", "Valley of the Kings"). Tomb-level resolution can be deferred until a museum mapper actually produces tomb-number strings.

### Sources not acquired (and why)

| Source | Why dropped |
|---|---|
| **TM Places** | Papyrological bias. Built from documentary attestations, not archaeological provenance. Pharaonic sites are present but subsumed under coarse toponyms (e.g., Deir el-Bahari, Valley of the Kings, and Medinet Habu all lumped into TM Geo 1341 "Memnoneia"). Granularity is too coarse to resolve museum provenance strings. |
| **Wikidata** | Adds complexity as a second source. Its unique strengths (tomb-level granularity, TM/Pleiades cross-refs) don't address current requirements. First source to revisit if tomb-number provenance or cross-gazetteer interoperability becomes needed. |
| **PAThs** | CC BY-NC-SA license creates a permanent ceiling on commercial use. EU sui generis database rights may apply to substantial extraction (needs legal review). If license were permissive, its 358 TM GeoIDs would be valuable for cross-referencing. |
| **TopBib** | Bibliographic index, not a site gazetteer. No visible license. However, re-examination found 464 unique TM GeoIDs as structured JSON cross-references across 499 geolocated records, plus 106 TLA cross-refs. If interoperability with Trismegistos or other digital Egyptology infrastructure becomes a requirement, TopBib is the best available TM bridge — pending license clarification with the Griffith Institute. |
| **Theban Mapping Project** | Offline (403/503), no API, ARCE copyright, blocks crawlers. |

---

## Impact on ADR-012

ADR-012 must be amended. The current decision states:

> Trismegistos Geo is the sole site authority. [...] + Theban Mapping Project (KV and TT codes)

This should change to:

> iDAI.gazetteer is the sole site authority. TM Places is dropped — its papyrological bias makes it structurally misaligned with museum artifact provenance. The Theban Mapping Project is dropped — its data is unavailable and its copyright is restrictive.

The `_source` block for `sites.json`:
```json
{
  "_source": {
    "citation": "iDAI.gazetteer, German Archaeological Institute (DAI). https://gazetteer.dainst.org",
    "retrieved": "2026-04-13",
    "license": "CC BY 4.0",
    "raw_file": "sources/idai-gazetteer/raw.json"
  }
}
```
