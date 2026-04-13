# Wikidata Pharaohs SPARQL Dump

Comprehensive list of pharaohs from Wikidata, covering Predynastic through Dynasty 31 plus Ptolemaic and foreign rulers (Achaemenid, Argead).

## Source

- **Query**: Wikidata SPARQL endpoint (`query.wikidata.org`)
- **Criteria**: Entities that are `instance of` pharaoh (Q12097) or `position held` pharaoh of Egypt (Q37110)
- **License**: CC0 (Wikidata)
- **Retrieved**: 2026-04-12

## What this provides

| Field | Coverage | Notes |
|---|---|---|
| `qid` | 100% | Wikidata entity ID (e.g. Q157899 for Thutmose III). Use for linking to Wikipedia/Wikidata in the web app |
| `display` | 100% | English label from Wikidata |
| `alt_labels` | 35% | English alternate names/spellings |
| `dynasty` | 69% | Parsed from `family` (P53) property; numbered 0-31 |
| `start_bce`/`end_bce` | 78% | Reign dates from `position held` qualifiers; falls back to birth/death dates (flagged `approximate: true`) |
| `prenomen` | 0% | Not available as transliterated text from Wikidata (stored as hieroglyphic markup in P7383) |

## Schema

Each line in `reconciled.jsonl` is a JSON object with:

```json
{
  "kind": "ruler",
  "qid": "Q157899",
  "display": "Thutmose III",
  "alt_labels": ["Tuthmosis III", "Thutmosis III", "Menkheperre"],
  "prenomen": null,
  "start_bce": -1478,
  "end_bce": -1424,
  "approximate": false,
  "uncertainty_plus_years": null,
  "dynasty": 18,
  "dynasty_label": "Eighteenth Dynasty of Egypt",
  "page": null,
  "note": "Replaces: Hatshepsut; Replaced by: Amenhotep II"
}
```

Fields not present in HKW/Wikipedia Ptolemaic sources:
- `qid` — Wikidata entity identifier. Resolves to Wikipedia via `https://www.wikidata.org/wiki/{qid}`
- `alt_labels` — list of English alternate names from Wikidata (useful for seeding the authority `aliases` array)
- `dynasty_label` — raw Wikidata family label before parsing to dynasty number

## Re-fetching

```bash
cd pipeline && uv run python pipeline/authority/sources/wikidata-pharaohs/fetch.py
```

This overwrites both `raw.json` and `reconciled.jsonl`. The row count may change as Wikidata editors add or merge entities.

## Design decisions

- **Dates**: Reign dates (from `position held` → `start time`/`end time` qualifiers) are preferred. When unavailable, birth/death dates are used as approximations and flagged with `approximate: true`. Most early dynastic rulers only have birth/death dates on Wikidata.
- **Dynasty 0**: Maps both "Protodynastic Period of Egypt" and "Dynasty 00" to dynasty number 0.
- **No dynasty (160 rulers)**: Rulers without a `family` (P53) property linking to a numbered dynasty. Includes Ptolemaic rulers (covered by the separate Wikipedia Ptolemaic source), Achaemenid/Argead rulers, and some poorly-documented rulers.
- **No prenomen**: Wikidata stores Egyptian royal names in hieroglyphic Manuel de Codage markup (P7383), not as transliterated Latin text. Prenomen will come from the Beckerath cross-check pass during authority curation (Phase A).
- **Foreign rulers included**: Achaemenid and Argead pharaohs are kept — they held the title and appear on Egyptian monuments. Their dynasty_label preserves the foreign dynasty name.
