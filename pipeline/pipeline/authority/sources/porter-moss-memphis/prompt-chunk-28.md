# Extraction prompt — Porter & Moss Vol III.2, Chunk 28

> **Twenty-eighth chunk drawn from PM Vol III** — Ṣaqqâra § II.A NORTH OF THE STEP PYRAMID, three trailing sub-sections: `OTHER NUMBERED OLD KINGDOM TOMBS` (sub-sub-banners (a) MARIETTE, (b) LEPSIUS, (c) QUIBELL) + `UNNUMBERED EARLY DYNASTIC AND OLD KINGDOM TOMBS` (sub-sub-banners (a) POSITION KNOWN, (b) POSITION UNKNOWN). PM III.2 physical pp.130–147 / printed pp.490–507. Closes § II.A's Old-Kingdom coverage. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-28-p130-p147-mariette-tail.txt`.

**Source:** PM III.2 2nd ed. 1978/1981, ed. Málek. **Page offset:** printed = physical + 360.

**Output:** one JSONL line per row sorted by `tomb_id`, `json.dumps(..., sort_keys=True, ensure_ascii=False)`. Write to ONE of `raw/agent-{a,b,c}-chunk28.jsonl`.

## tomb_id convention (multi-banner)

This chunk mixes three tomb-id forms depending on the sub-sub-banner:

1. **(a) MARIETTE — letter-coded tombs WITHOUT a Mariette sequential number.** PM headword `<letter> <num>. <NAME>` (e.g. `B 2. ḤETEPḤERES`, `B 3. SHERY`, `B 7. SETHU [II]`, `B 15. WERKAPTAḤ`, `D 70 [LS 15]. PEḤNUIKA`, `H 12. KHUIT`). tomb_id = `MAR-<letter><num>` (e.g. `MAR-B2`, `MAR-B3`, `MAR-B7`, `MAR-D70`, `MAR-H12`). Compound bracketed cross-references (e.g. `[LS 15]` on `D 70`) go into `tomb_aliases` as `["LS 15"]`. Distinct from chunks 27a/27b's `MAR<N>` for the Nos. 1-88 numbered series.
2. **(b) LEPSIUS — LS-numbered tombs.** tomb_id = `LS<N>` (already-established prefix from chunks 20/23).
3. **(c) QUIBELL — bare-named tombs.** Famous **PERNEB** (Cairo Mus. tomb chapel moved to Metropolitan Museum, New York). tomb_id = `SAQ-<TitleCaseName>` (descriptor form per chunks 22/25/26).
4. **UNNUMBERED (a) POSITION KNOWN + (b) POSITION UNKNOWN.** Bare-named OK tombs. tomb_id = `SAQ-<TitleCaseName>` (descriptor form). For homonym disambiguation (KAʿAPER vs MAR36 KAʿAPER, KHUIT vs MAR70 KHUIT, PTAḤSHEPSES [I] vs MAR48-50 PTAḤSHEPSES siblings, NUFER vs SAQ-Nufer chunk-26): use the topographic anchor or bracketed Roman ordinal in the tomb_id (e.g. `SAQ-KaaperJudge` for the Judge-and-Boundary-official Kaʿaper, vs the Sheikh-el-Beled MAR36; `SAQ-PtahshepsesIDirectorOfCraftsmen` if the bracketed [I] distinguishes from chunk-27a's). For anonymous `NAME UNKNOWN` tombs, use `SAQ-AnonPostNoX` or similar topographic anchor (Shape-5 convention from chunks 13/14/22).

## Cemetery field

All chunk-28 rows: `cemetery: "North of the Step Pyramid"` (continuation of chunks 27a/27b banner).

## Schema (23 keys, same as chunks 20–27b)

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
  "dynasty": "3" | "4" | "5" | "6" | null,
  "sub_period": null | "1st Int. Period",
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "North of the Step Pyramid",
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

**Shape 1 — Letter-coded MARIETTE.** `<letter> <num>. <NAME IN CAPS>, <Title cluster>. <Dating>.` → tomb_id `MAR-<letter><num>`.

**Shape 1b — Bare-named OK.** `<NAME IN CAPS>, <Title cluster>. <Dating>.` → tomb_id `SAQ-<TitleCaseName>`.

**Shape 1c — `<NAME> good name <ALT>` idiom.** Per chunks 8-25 convention.

**Shape 4 — Joint twin/family-tomb headword.** Per chunks 21-22 convention. Example: `TETI and NEFERḤERES, Scribes of the archives. Late Dyn. III or early Dyn. IV.` → tomb_id `SAQ-TetiNeferheres`, co_occupants=["Neferḥeres"], is_joint_burial=true.

**Shape 5 — Anonymous `NAME UNKNOWN`.** tomb_id with topographic anchor (e.g. `SAQ-AnonMastabaXEarlyDynV` for the "NAME UNKNOWN. Early Dyn. V." at line ~442 with its position context). Per chunks 13/14/22 anonymous Shape-5 convention.

**OUT-OF-SCOPE — do NOT emit rows for:**
- Sub-rooms (Chapel., Burial chamber., Room I., (N)-numbered scenes).
- Body-prose object mentions / sub-feature decoration / museum-citation lines.
- The `LATE PERIOD, PTOLEMAIC AND ROMAN TOMBS` sub-banner (line ~602 onwards) — Dyn XXVI/XXVII/XXX, Ptolemaic, Roman are post-OK / out of MVP scope.
- The `FINDS FROM NORTH OF THE STEP PYRAMID` sub-banner (line ~699 onwards) — loose-object findspots, not tomb headwords.
- Cross-reference body-prose tomb mentions ("see No. <N>", "between Nos. X and Y" — these are topographic anchors, not headwords).
- Mastaba X (Probably Late Dyn. I) — Early Dynastic, out of MVP scope (chunks 4-26 source-wide Early Dynastic exclusion).

## Expected row count

Rule-driven; ~15–25 rows expected (band 12–30). The chunk spans 18 pages with mixed sub-sub-banners. Re-read the chunk file if your count falls outside the band 12–30.

## PM III.2 text-layer noise — same rules as chunks 19–27b

- Raised-ayin → U+02BF `ʿ`; ASCII descriptor drops the glyph.
- Underdot-Ḥ on ḥ-roots per source-wide convention (Ḥathor single-underdot per the 44-vs-6 majority).
- Macron-Ē on Re-deity compounds: Rēʿ, Saḥurēʿ, Neuserrēʿ, Neferirkarēʿ, Menkauḥor (no macron), Merenrēʿ. OCR vowel rule: capital R+E = macron; capital R+A = no macron.
- OCR `<` and `>` and `(` artifacts around ayin glyphs — normalise to `ʿ`.
- OCR `\1` `~` `}` etc. = hieroglyphic-cartouche garbage from PM's inline typography. Strip; preserve only the romanized name and titles.
- OCR Roman numerals interspersed in tomb numbers (e.g. `B IS` for `B 15`, `B 49` rendered as `B 49C`, `H 12` correct). Normalise to Arabic in tomb_id.

## Dating mappings

- `Temp. <Dyn V king>` → `"5"`. `Temp. <Dyn VI king>` → `"6"`.
- `Probably Dyn. V` / `Probably Dyn. VI` → `"5"` / `"6"` + `attribution_certainty: "probable"`.
- `Dyn. V or later` → `"6"` (range-tail).
- `Late Dyn. III or early Dyn. IV` → `"4"` (range-tail; settle on later term).
- `Middle Dyn. III to early Dyn. IV` → `"4"` (range-tail; chunk-27a MAR5 precedent).
- `Dyn. IV-V` / `Late Dyn. IV or early Dyn. V` → `"5"` (range-tail).
- `Dyn. V-VI` / `End of Dyn. V or Dyn. VI` → `"6"` (range-tail).
- `Dyn. IV(?)` → `"4"` + `attribution_certainty: "uncertain"`.
- `1st Int. Period` (no Dyn-VI co-marker) → `null` + `sub_period: "1st Int. Period"`.

## Field-by-field rules

Same as chunks 24–27b. Wife/parents body-prose clauses → MUST be captured in BOTH `co_occupants` / `co_occupant_roles` AND preserved in `notes_from_pm`. `co_occupant_roles` MUST be `<Relation>, <title>` (e.g. `"Wife, Prophetess of Ḥathor"`), NOT `"Official"`.

**`occupant_role`** — `"Vizier"` for Chief Justice and Vizier. `"Princess"` for King's daughter; `"Prince"` for King's son. `"Queen"` for King's wife. `"High Priest"` for `Greatest of the directors of craftsmen` (wr-ḫrp-ḥmwt) / `Greatest of the seers` / `Greatest of the physicians`. `"Official"` for everything else (including bare-named female "King's sole adorner", since this is a court-title not a royal-spouse title).

**`tomb_aliases`** — For MARIETTE letter-coded tombs (Shape 1), the `<letter> <num>` PM-literal string is the PRIMARY identifier captured in tomb_id (`MAR-<letter><num>`). Cross-reference codes (e.g. `[LS 15]` on `D 70 PEḤNUIKA`) go in `tomb_aliases` as `["LS 15"]`. For bare-named tombs (Shape 1b), `tomb_aliases` stays empty unless PM prints an explicit `[<code>]` cross-reference.

**`notes_from_pm`** — Headword block prose; drop body-prose object catalog / museum citations / cartographic refs / sub-feature room headings. Preserve title cluster + dating + wife/parent clauses + topographic anchor (e.g. `North-west of No. 42 [C 7].`, `South of Nos. 37-8 [E 1, 2 and H 3].`).

**`source_citation`** — printed = physical + 360.

## Report format

```
agent-<X>-chunk28: <count> rows; <MAR-letter-coded>/<LS>/<SAQ->/<other> split; <anomalies or "none">
```

Under 100 words.
