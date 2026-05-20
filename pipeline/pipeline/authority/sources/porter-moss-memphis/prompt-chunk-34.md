# Extraction prompt — Porter & Moss Vol III.2, Chunk 34

> **Thirty-fourth chunk drawn from PM Vol III.2** — **Dahshûr § I.G/H/I trailing Dyn-XIII pyramids + § II.A "East of the Northern Pyramid of Snefru"** (private OK mastabas around Snefru's Red Pyramid). PM III.2 physical pp.530–533 / printed pp.890–893. Closes § I and opens § II at Dahshûr. Per the 2026-05-19 all-dynastic scope expansion (mvp-tasks.md item 3). This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-34-p530-p533-dahshur-i-ghi-iia-east-of-north-pyramid.txt`.

**Source:** PM III.2 2nd ed. 1978/1981, ed. Málek. **Page offset:** printed = physical + 360.

**Output:** one JSONL line per row sorted by `tomb_id`, `json.dumps(..., sort_keys=True, ensure_ascii=False)`. Write to ONE of `raw/agent-{a,b,c}-chunk34.jsonl`.

## Scope: two sub-corpora

**Part 1 — § I trailing pyramids (royal headwords).** PM lettered sections G/H/I that fell outside chunk-33's page range:
- **G AND H. PYRAMIDS PROBABLY OF DYNASTY XIII** (joint section in PM text)
- **I. PYRAMID OF <named ruler>** (named Dyn XIII pyramid)

Same shapes/conventions as chunk 33: Shape-1 named royal pyramid, Shape-3 anonymous Dyn-XIII pyramid. cemetery = `"Pyramid-field of Dahshur"`, section = `"I"`.

**Part 2 — § II.A "East of the Northern Pyramid of Snefru"** (private mastaba cluster around Snefru's Red Pyramid). Two sub-banners:
- **NORTHERN PART (SOUTH-EAST OF THE ENCLOSURE OF SESOSTRIS III)** — numbered DE MORGAN tombs
- **SOUTHERN PART (NORTH OF THE ENCLOSURE OF AMENEMḤET II)** — numbered DE MORGAN tombs

cemetery = `"East of Northern Pyramid of Snefru"`, section = `"II"`. memphite_area remains `"Dahshur"`.

## How to identify a row

**Shape 1a — bare named OK tomb headword.** PM-numbered DE MORGAN tomb opens with `<N>. <NAME IN CAPS> <hieroglyphs>, <role cluster>. <dating>.` PM's DE MORGAN tomb numbering is preserved verbatim in the headword.

**Shape 5 — anonymous numbered tomb.** PM-numbered DE MORGAN tomb opens with `<N>. <hedge> Dyn. <Roman>.` (e.g. headword form `<N>. Probably Dyn. <Roman>.` or `<N>. Mastaba-group. Probably Dyn. <Roman>.`) — NO all-caps name in the headword. `occupant_name: null`, `attribution_certainty: "probable"` if PM uses "Probably" hedge.

**Shape 3 — anonymous Dyn-XIII pyramid** (chunk-33 carryover): § I.G/H section header `PYRAMIDS PROBABLY OF DYNASTY XIII` opens an anonymous royal pyramid row.

**Shape 1 — named royal pyramid** (chunk-33 carryover): § I.I section header `PYRAMID OF <named ruler>` opens a Shape-1 royal pyramid row.

**Subsidiary cult pyramids** in § I: do NOT emit rows (sub-architecture; chunk-33 convention).

**Headword block ends** at the first sub-feature: `MORTUARY TEMPLE.`, `Plan,`, `View,`, `False-door,`, `Inscribed`, `Statue`, `Statuette`, `Wife,` (which IS a row-level field, not a sub-feature — capture for `co_occupants`), `Wall-paintings,`, `Offering-table`, citation names (`DE MORGAN`, `BORCHARDT`, etc.).

## tomb_id convention

**Existing prefix:** `DAH-` (introduced in chunk 33).

**For § I.G + H (joint anonymous Dyn-XIII pyramid section):** PM treats G and H as ONE joint section with ONE `PYRAMIDS PROBABLY OF DYNASTY XIII` header. If PM emits only ONE structural row (no individual G or H entries follow), use `DAH-PyramidsGH` (joint descriptor — the section header itself names both). If PM emits a separate paragraph for each, use `DAH-PyramidG` / `DAH-PyramidH`.

**For § I.I (named Dyn-XIII pyramid):** anchor on the king's TitleCase ASCII name (chunk-33 convention).

**For § II.A NORTHERN PART numbered anonymous tombs (Shape 5 — no name):** `DAH-MorganN<num>` (e.g. `DAH-MorganN5`, `DAH-MorganN7`) — the `N` distinguishes the NORTHERN PART numbering series from the SOUTHERN PART series, since PM restarts the numbering at 1 in the SOUTHERN PART. The `Morgan` reflects PM's citation of Jacques de Morgan's 1894/95 Dahchour excavation. Anchor exclusively on the DE MORGAN tomb number per PM's own annotation.

**For § II.A SOUTHERN PART numbered named tombs (Shape 1a):** `DAH-<TitleCaseAsciiName>` form (chunk-33 named-pyramid descriptor convention). The DE MORGAN number is captured in `tomb_aliases` as `"DE MORGAN <N>"`. Strip Egyptological diacritics from descriptor key.

**For § II.A SOUTHERN PART numbered anonymous tombs (Shape 5):** `DAH-MorganS<num>` form.

**Homonym discipline**: check existing tomb_ids in `reconciled.jsonl` (815 rows from chunks 1–33). The N/S prefix on `DAH-Morgan<num>` distinguishes DE MORGAN tomb numbers that restart at 1 in the SOUTHERN PART.

## Schema (23 keys, identical to chunks 20–33)

```json
{
  "tomb_id": "DAH-<DescriptorName>",
  "memphite_area": "Dahshur",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "King" | "Queen" | "Prince" | "Princess" | "Vizier" | "High Priest" | "Official" | "Royal Family" | "Unknown",
  "dynasty": "4" | "5" | "6" | "12" | "13" | null,
  "sub_period": null | "1st Int. Period",
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "Pyramid-field of Dahshur" | "East of Northern Pyramid of Snefru",
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "is_uninscribed": false,
  "is_usurped": false,
  "attribution_certainty": "attested" | "probable" | "uncertain",
  "shared_with_tombs": [],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM III.2 2nd ed. 1978/1981", "section": "I" | "II"}
}
```

**Field-rule notes:**
- `memphite_area`: `"Dahshur"` for ALL rows in this chunk (continuing chunk 33).
- `cemetery`:
  - `"Pyramid-field of Dahshur"` for § I rows (G/H/I)
  - `"East of Northern Pyramid of Snefru"` for § II.A rows (NEW VALUE — first chunk to land § II material)
- `section`:
  - `"I"` for § I rows (G/H/I)
  - `"II"` for § II.A rows
- `dynasty`: PM uses Roman numerals; convert to Arabic-decimal STRING. NEW DYNASTIES IN THIS CHUNK: "4" (Dyn IV for Snefru-associated officials), "5" (Dyn V), "6" (Dyn VI). The "12" / "13" carry over from chunk 33 for § I rows.
- `attribution_certainty`:
  - `"attested"`: PM names the ruler/occupant directly with no hedge
  - `"probable"`: PM uses "Probably" / `(?)` / `"Probably Dyn. <N>"` headword hedge
  - `"uncertain"`: stronger hedge or PM annotation of doubt
- `occupant_role`:
  - § I.I: `"King"`
  - § I.G/H joint anonymous: `"King"` (anonymous royal pyramid per chunk-33 Shape-3 convention)
  - § II.A: depends on PM's role-cluster. Common values for OK private mastabas: `"Official"`, `"Royal Family"` (King's son / King's eldest son), `"Princess"` (King's daughter), `"Vizier"` (if Chief Justice and Vizier title), `"Prince"` (King's son in adjective sense). When PM says `"King's son of his body"`, role = `"Prince"`. When PM says `"Inspector of <X>"` / `"Scribe of <X>"` / `"Overseer of <X>"` / `"Royal acquaintance"`, role = `"Official"`.
- `is_joint_burial`: false unless PM uses explicit joint-burial headword (Shape-4). A named-principal row with a co-occupant spouse (per PM's `Wife, <Name>` clause inside the headword block) is Shape-1 with co_occupants, NOT joint-burial.
- `co_occupants` / `co_occupant_roles`: capture PM-named wives, sons, daughters in the headword block. Mirror the chunk-31/32 convention (PM-faithful name strings; "Wife"/"Mother"/"Father"/"Son"/"Daughter" role tokens).
- `notes_from_pm`: capture the dating + cited authority (e.g. DE MORGAN, BORCHARDT, ScHMITZ). PM-faithful verbatim; drop hieroglyph noise.

## Diacritic conventions

Same as chunks 9-33:
- Strip Egyptological diacritics from `tomb_id` descriptor (ASCII-only).
- Preserve PM-faithful diacritics in `occupant_name`, `occupant_alt_names`, `notes_from_pm`, `co_occupants`, `co_occupant_roles`: macron-ē/ū/ō, underdot-Ḥ/Ḫ/Ḳ/Ḏ, ayin U+02BF.

## Calibration self-check (not a hard rule)

Total calibration target: ≈ 12–15 rows across § I.G/H/I + § II.A NORTHERN + SOUTHERN PART. If your final count diverges by more than ±4 from this calibration, re-read the chunk file and check whether you've missed a numbered tomb headword or emitted out-of-scope sub-features (find lists, statue catalogues, etc.).

## Constitutional Rule 1 — scholar-grade source-traced

Every field value must trace verbatim to text appearing in `raw/chunk-34-p530-p533-dahshur-i-ghi-iia-east-of-north-pyramid.txt`. Do not synthesize values from training data.

## Constitutional Rule 2 — no silent picks, no synthesis

Ambiguity → null. Never invent characters absent from the text-layer. If a tomb-numbered Shape-5 anonymous entry has no PM-attested dating, leave `dynasty: null` rather than guessing.

## Stop criterion

Emit one row per ROW-EMITTING headword in scope. Sort by `tomb_id`. Every row has all 23 schema keys present. `dynasty` is a STRING. `memphite_area` = `"Dahshur"`. `section` is `"I"` for G/H/I and `"II"` for § II.A.
