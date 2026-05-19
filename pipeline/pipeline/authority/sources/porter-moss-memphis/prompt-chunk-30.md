# Extraction prompt — Porter & Moss Vol III.2, Chunk 30

> **Thirtieth chunk drawn from PM Vol III** — Ṣaqqâra § II.J TOMBS OF POSITION UNKNOWN (a) OLD KINGDOM. PM III.2 physical pp.329–339 / printed pp.689–699. Closes the OK private-tomb coverage of PM III.2. The chunk opens with a small "NEAR PYRAMID OF USERKAREʿ KHENZER" + "EXACT POSITION UNKNOWN" tail (last few rows of § II.I Pepy II / Userkareʿ Khenzer area where position couldn't be pinpointed) before the § II.J banner. After § II.J `(a) OLD KINGDOM` ends (likely phys p.338), `(b)` Middle Kingdom / `(c)` 2nd Int Period / `(d)` New Kingdom / `(e)` Late Period sub-banners follow — those are OUT OF SCOPE. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-30-p329-p339-position-unknown.txt`.

**Source:** PM III.2 2nd ed. 1978/1981, ed. Málek. **Page offset:** printed = physical + 360.

**Output:** one JSONL line per row sorted by `tomb_id`, `json.dumps(..., sort_keys=True, ensure_ascii=False)`. Write to ONE of `raw/agent-{a,b,c}-chunk30.jsonl`.

## tomb_id convention (multi-banner)

1. **Mariette letter-coded tombs** (`B 8`, `B 14`, `C 12`, `C 25`, `C 27`, `D 67`, `D 68`, `D 69`, `E 16`, etc.) — `MAR-<letter><num>` form per chunk-28 precedent (e.g. `MAR-B8`, `MAR-D67`, `MAR-E16`). Distinct from chunks 27a/b `MAR<N>` for the Nos. 1-88 sequential series.
2. **Bare-named OK tombs** (`GEGI`, `INPUKHAʿ`, `IRUKAPTAḤ`, `IRI`, etc.) — `SAQ-<TitleCaseAsciiName>` descriptor form.
3. **Homonym disambiguators**: if a name collides with prior-chunk SAQ-/MAR- entries (e.g. `SAQ-Irukaptah` chunk 26 vs `IRUKAPTAH` chunk 30; `MAR-C27` may collide with chunk-28 `SAQ-Kaiḥap`), use a topographic-anchor / title-anchor suffix in the tomb_id (e.g. `SAQ-IrukaptahGranary`, `SAQ-Iri`) to avoid duplicates.

## Cemetery field

All chunk-30 rows: `cemetery: "Tombs of position unknown"` per the § II.J banner.

The IRI row at phys p.329 (under "NEAR PYRAMID OF USERKAREʿ KHENZER") is on a TOPOGRAPHIC anchor before § II.J — use cemetery `"Around Pyramid-enclosure of Userkareʿ Khenzer"` for IRI specifically. The D 67 / D 68 / D 69 / E 16 cluster under "EXACT POSITION UNKNOWN" sub-banner BEFORE § II.J also belongs to § II.J effectively — use `"Tombs of position unknown"`.

## Schema (23 keys, same as chunks 20–29)

```json
{
  "tomb_id": "...",
  "memphite_area": "Saqqara",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "Vizier" | "High Priest" | "Official" | "Royal Family" | "Princess" | "Prince" | "Queen" | "King" | "Unknown",
  "dynasty": "5" | "6" | null,
  "sub_period": null | "1st Int. Period",
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "Tombs of position unknown" | "Around Pyramid-enclosure of Userkareʿ Khenzer",
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "is_uninscribed": false,
  "is_usurped": false,
  "attribution_certainty": "attested" | "probable" | "uncertain",
  "shared_with_tombs": [],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM III.2 2nd ed. 1978/1981", "section": "II"}
}
```

## How to identify a row

**Shape 1 — Letter-coded MARIETTE.** `<letter> <num>. <NAME IN CAPS>, <Title cluster>. <Dating>.` → tomb_id `MAR-<letter><num>`. Chunk-28 precedent.

**Shape 1b — Bare-named OK.** `<NAME IN CAPS>, <Title cluster>. <Dating>.` → tomb_id `SAQ-<TitleCaseName>`.

**Shape 4 — Joint twin/family-tomb headword.** Per chunks 21-22/28 convention.

**OUT-OF-SCOPE — do NOT emit rows for:**
- Sub-rooms (Chapel., Burial chamber., Room I., (N)-numbered scenes).
- Body-prose object findspots / museum-citation lines / cartographic refs.
- `FOUND NEAR THE PYRAMID` sub-banner (line ~13) — loose-object catalog under IRI's tomb.
- `(b)` Middle Kingdom / `(c)` 2nd Int Period / `(d)` New Kingdom / `(e)` Late Period sub-banners after § II.J `(a) OLD KINGDOM` — all post-OK out of MVP.
- Body-prose tomb mentions ("see No. <N>", "Another tomb at Nagʿ el-Deir N.90").

## Expected row count

Rule-driven; ~12–22 rows expected (band 10–28). The chunk spans 11 pages with a final § II.J banner closing the OK coverage. Re-read the chunk file if your count falls outside the band 10–28.

## PM III.2 text-layer noise — same rules as chunks 19–29

- Raised-ayin → U+02BF `ʿ`; ASCII descriptor drops the glyph.
- Underdot-Ḥ on ḥ-roots per source-wide convention (Ḥathor single-underdot per the 44-vs-6 majority).
- Macron-Ē on Re-deity compounds: Rēʿ, Saḥurēʿ, Neuserrēʿ, Neferirkarēʿ, Menkauḥor (no macron), Merenrēʿ. OCR vowel rule: capital R+E = macron; capital R+A = no macron.
- OCR `<` and `>` and `(` artifacts around ayin glyphs — normalise to `ʿ`.
- OCR Roman numerals interspersed in tomb numbers (e.g. `B IS` for `B 15`, `E r6` for `E 16`, `B I4` for `B 14`). Normalise to Arabic in tomb_id.

## Dating mappings

- `Temp. <king>` → dynasty number per chunks 27a/27b precedent.
- `Probably Dyn. V` / `Probably Dyn. VI` → dynasty + probable.
- `Middle Dyn. V or later` / `Late Dyn. V or Dyn. VI` → `"6"` (range-tail).
- `End of Dyn. VI or 1st Int. Period` → `"6"` (range-tail) + `sub_period: null`.
- `Dyn. V-VI` → `"6"` (range-tail).
- `1st Int. Period` alone → `null` + `sub_period: "1st Int. Period"`.

## Field-by-field rules

Same as chunks 24–29. Wife/parents body-prose clauses → MUST be captured in BOTH `co_occupants` / `co_occupant_roles` AND preserved in `notes_from_pm`. `co_occupant_roles` MUST be `<Relation>, <title>`, NOT `"Official"`.

**`occupant_role`** — `"Vizier"` for Chief Justice and Vizier. `"Official"` for everything else (most rows in this chunk).

**`notes_from_pm`** — Headword block prose; drop body-prose object catalog / museum citations / cartographic refs. Preserve title cluster + dating + family clauses + topographic-anchor when present.

**`source_citation`** — printed = physical + 360.

## Report format

```
agent-<X>-chunk30: <count> rows; <MAR-letter-coded>/<SAQ->/<other> split; <anomalies or "none">
```

Under 100 words.
