# Extraction prompt — Porter & Moss Vol III.2, Chunk 27b

> **Twenty-seventh chunk (back half) drawn from PM Vol III** — Ṣaqqâra § II.A NORTH OF THE STEP PYRAMID, sub-section `OLD KINGDOM TOMBS NOS. I-88 OF MARIETTE` (back half). PM III.2 physical pp.108–129 / printed pp.468–489. Continuation of chunk 27a — covers Ti's mega-block (No. 60 [D 22]) and Mariette Nos. 61-88. Includes famous **TY** (Mariette's Mastaba of Ti, the touchstone OK private tomb at Saqqâra North), **MERUKA** (No. 77 [D 9], distinct from chunk-21 Mereruka), **NIʿANKH-SEKHMET** (No. 74 [D 12], Greatest of the physicians of the South and North), and royal-family tombs **NUBNEBTI** (No. 64, King's wife), **KHUIT** (No. 70, King's daughter / King's wife), **MERESʿANKH** (No. 82, King's wife perhaps of Isesi), **REʿEMKA** (No. 80, King's eldest son), plus several King's-son/Royal-acquaintance entries. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-27b-p108-p129-mariette-ok-back.txt`.

**Source:** PM III.2 2nd ed. 1978/1981, ed. Málek. **Page offset:** printed = physical + 360.

**Output:** one JSONL line per row sorted by `tomb_id`, `json.dumps(..., sort_keys=True, ensure_ascii=False)`. Write to ONE of `raw/agent-{a,b,c}-chunk27b.jsonl`.

## tomb_id convention (continuing chunk 27a)

- `MAR<N>` where `<N>` is the Mariette sequential number (e.g. `MAR60` for Ti, `MAR77` for Meruka).
- PM's bracketed letter-classification (`[D 22]`, `[D 9]`, etc.) goes into `tomb_aliases` as the literal PM string (`"D 22"`, `"D 9"`, etc.).
- Compound bracketed forms like `[D 2; S 905]` go in `tomb_aliases` as TWO entries: `["D 2", "S 905"]`.

**Start boundary:** No. 60 TY (the mega-block at phys p.108). The chunk-27b text file begins with the END of No. 59 SNEFRUNUFER [II] continuing from chunk-27a — **DO NOT** emit a row for No. 59 (already extracted in chunk-27a). Start emission at No. 60.

**End boundary:** No. 88 ḤUTI (last numbered Mariette tomb).

## Cemetery field

All chunk-27b rows: `cemetery: "North of the Step Pyramid"` (per PM § II.A banner; continuation of chunk-27a's banner).

## Schema (23 keys, same as chunks 20–27a)

```json
{
  "tomb_id": "MAR<N>",
  "memphite_area": "Saqqara",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": ["<letter-code>", "S <S-num>"],
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

**Shape 1 — Standard Mariette numbered.** Same as chunk-27a: `No. <N> [<letter-code>]. <NAME IN CAPS>, <Title cluster>. <Dating>.`

**Shape 1d — Mega-block (Ti).** No. 60 TY occupies phys pp.108–117 with 30+ sub-rooms and 100+ scene numbers. Roll Ti into a SINGLE row per chunk-21 Mereruka mega-block convention. Headword block is the first paragraph: `No. 60 [D 22]. TY <hieroglyphs>. Overseer of the Pyramids of Neferirkareʿ and Ne<userrēʿ>, Overseer of the Sun-temples of Saḥurēʿ, Neferirkarēʿ, Neuserrēʿ, etc. Dyn. V (probably temp. Neuserrēʿ).` + wife/parent clauses. Drop sub-room scene-by-scene catalog from notes_from_pm.

**Shape 1c — "or" / "good name" idiom.** Per chunks 20-25 convention.

**Shape 4 — Joint twin/family-tomb headword.** Per chunks 21-22 convention.

**Shape 3 — Bracketed-Roman regnal ordinal.** `<NAME> [I]` / `<NAME> [II]` (e.g. `TEPEMʿANKH [I]` at No. 75, `TEPEMʿANKH [II]` at No. 76) — preserve in occupant_name as `"TepemʿAnkh [I]"` per chunks 11/15/17.

**Shape 5 — Anonymous king's-son/wife.** `NUBNEBTI` (No. 64), `KHUIT` (No. 70), `MERESʿANKH` (No. 82) carry royal-family roles. Use `"Queen"` for `"King's wife"`, `"Princess"` for `"King's daughter"`, `"Prince"` for `"King's son"`.

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per Shape-1 / 1c / 1d / 4 headword whose dating is OK (Dyn III/IV/V/VI) or 1st Int. Period. Do NOT emit rows for:
- Sub-rooms of Ti's mastaba (Chapel., Room I., Burial chamber., (N)-numbered scenes).
- Body-prose object mentions / sub-feature decoration / museum-citation lines.
- Cross-reference body-prose "No. <N>" mentions.
- No. 59 SNEFRUNUFER [II] (already extracted in chunk-27a).

## Expected row count

Rule-driven; ~22–28 rows expected (band 18–32). The chunk spans 22 dense pages; expects Ti + Nos. 61-88 (with some gaps like missing Nos. 78, 86, 87 in PM's numbering — emit only what PM prints as a headword). Re-read the chunk file if your count falls outside the band 18–32.

## PM III.2 text-layer noise — same rules as chunks 19–27a

- Raised-ayin → U+02BF `ʿ`; ASCII descriptor drops the glyph.
- Underdot-Ḥ on ḥ-roots per source-wide convention (Ḥathor single-underdot per the 44-vs-6 majority).
- Macron-Ē on Re-deity compounds: Rēʿ, Saḥurēʿ, Neuserrēʿ, Neferirkarēʿ, Menkauḥor (no macron, kʿw-ḥr), Merenrēʿ. OCR vowel rule: capital R+E = macron; capital R+A = no macron.
- OCR `<` and `>` and `(` artifacts around ayin glyphs — normalise to `ʿ`.

## Dating mappings

Same as chunk-27a. `Temp. <Dyn V king>` → `"5"`. `Probably Dyn. V` → `"5"` + probable. `Dyn. V or later` → `"6"` range-tail. `Middle Dyn. V` → `"5"`. `Late Dyn. V` → `"5"`.

## Field-by-field rules

Same as chunks 24–27a. Wife/parents body-prose clauses → MUST be captured in BOTH `co_occupants` / `co_occupant_roles` AND preserved in `notes_from_pm`. `co_occupant_roles` MUST be `<Relation>, <title>` (e.g. `"Wife, Prophetess of Ḥathor"`), NOT `"Official"`.

**`occupant_role`** — `"Vizier"` for Chief Justice and Vizier. `"Princess"` for King's daughter; `"Prince"` for King's son. `"Queen"` for King's wife. `"High Priest"` for `Greatest of the directors of craftsmen` (wr-ḫrp-ḥmwt) / `Greatest of the seers` (wr-mꜣw) / `Greatest of the physicians`. `"Official"` for everything else.

**`source_citation`** — printed = physical + 360.

## Report format

```
agent-<X>-chunk27b: <count> rows; <MAR-numeric-range>; <anomalies or "none">
```

Under 100 words.
