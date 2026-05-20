# Extraction prompt — Porter & Moss Vol III.2, Chunk 33

> **Thirty-third chunk drawn from PM Vol III.2** — **Dahshûr § I. PYRAMIDS** (full section). PM III.2 physical pp.516–529 / printed pp.876–889. First Dahshûr chunk — covers the entire royal-pyramid section in one chunk (8 lettered sub-sections A–H + I). Per the 2026-05-19 all-dynastic scope expansion (mvp-tasks.md item 3), Dahshûr royal pyramid material is in scope. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-33-p516-p529-dahshur-pyramids.txt`.

**Source:** PM III.2 2nd ed. 1978/1981, ed. Málek. **Page offset:** printed = physical + 360.

**Output:** one JSONL line per row sorted by `tomb_id`, `json.dumps(..., sort_keys=True, ensure_ascii=False)`. Write to ONE of `raw/agent-{a,b,c}-chunk33.jsonl`.

## Scope

§ I. PYRAMIDS at Dahshûr — categorial sub-section index (PM lettered A through I):
- **A.** Named Dyn IV royal pyramid-complex (northern)
- **B.** Named Dyn IV royal pyramid-complex (southern)
- **C.** Named Dyn XII royal pyramid-complex
- **D.** Named Dyn XII royal pyramid-complex
- **E.** Anonymous pyramid-enclosure ("PROBABLY OF DYNASTY XIII")
- **F.** Named Dyn XII royal pyramid-complex
- **G + H.** Anonymous pyramid(s) "PROBABLY OF DYNASTY XIII" (PM may treat as joint or separate)
- **I.** Named Dyn XIII royal pyramid

You will discover the named rulers, popular tomb-names, and the exact number of named queen-enclosures by reading the chunk text. The categorial index above is so you can confirm scope coverage, not a per-section answer key.

Stop at the first heading of `§ II. — A. EAST OF THE NORTHERN PYRAMID OF SNEFRU` (next chunk).

## How to identify a row

Same convention as chunk-4 (Saqqâra royal pyramids):

**Shape 1 — Royal pyramid-complex MAIN pyramid.** Each `PYRAMID-COMPLEX OF <KING>` / `NORTHERN COMPLEX` / `SOUTHERN COMPLEX` lettered section opens with the section heading. Inside the section, the main pyramid carries a `PYRAMID.` sub-heading. The main pyramid attributes to the named KING of the complex (role = `"King"`).

**Shape 2 — Queen's pyramid-enclosure (named or anonymous).** A `PYRAMID-ENCLOSURE OF <QUEEN-NAME>` sub-heading (named queen) or `PYRAMID-ENCLOSURE PROBABLY OF WIFE OF <KING>` (anonymous) within a king's complex. Named enclosure: role = `"Queen"`, `attribution_certainty: "attested"`. Anonymous: `occupant_name: null`, role = `"Queen"`, `attribution_certainty: "uncertain"` (override on the three-tier rule below: the occupant's identity is **unknown**, not merely hedged — `"uncertain"` reflects identity-unknown rather than identity-known-but-PM-hedges).

**Shape 3 — Anonymous Dyn-XIII pyramid (E / G / H).** Sections E, G, H are pyramids `PROBABLY OF DYNASTY XIII` with no named ruler. Emit ONE row per pyramid with `occupant_name: null`, role = `"King"` (per shape — they ARE royal pyramids, just anonymous), `attribution_certainty: "probable"` (PM's "probably" hedge), `dynasty: "13"`.

**Shape 4 — Subsidiary cult pyramid.** Each main pyramid typically has a `SUBSIDIARY PYRAMID.` sub-heading (cult pyramid, not a queen). **Do NOT emit a row for subsidiary pyramids** (sub-architecture, not a separate tomb-occupant entry). This matches the chunk-4 convention.

**Out of scope (no rows for these features):**
- `MORTUARY TEMPLE.`, `VALLEY TEMPLE.`, `CAUSEWAY.`, `BURIAL CHAMBER.`, `PYRAMID-TEXTS.` sub-features — sub-architecture
- `NORTH GALLERIES AND MASTABAS OF PRINCESSES.`, `SOUTH MASTABAS.`, `TOMBS IN NORTH PART OF ENCLOSURE`, `BUILDING NORTH OF CAUSEWAY.`, `REMAINS OF BUILDING SOUTH OF CAUSEWAY.` — mastaba clusters around the pyramid, not the pyramid itself (these are private-tomb clusters belonging to § II)
- Individual mastaba entries (e.g. Mastaba I, II, III in Sesostris III's complex; named queens buried in galleries vs in their own pyramid-enclosures) — § II scope
- Pyramid-text catalogues, sarcophagus-find lists, scene catalogues — body items under each pyramid

**Boundary edge case:** Within a king's pyramid-complex, named queens may be (a) buried in a **pyramid-enclosure** of their own (emit a row per Shape 2) or (b) buried in **shaft tombs / galleries** within the king's enclosure (do NOT emit — these are § II-style sub-entries). The distinguishing PM marker is the `PYRAMID-ENCLOSURE OF <NAME>` sub-heading. A `Shaft tomb of <NAME>` or `Mastaba <N>` or `Sarcophagus of <NAME>` body-clause is NOT a pyramid-enclosure and does NOT emit a row.

## tomb_id convention

**New prefix for Dahshûr**: `DAH-<DescriptorName>` (mirrors `SAQ-` for Saqqâra). Descriptor is TitleCase ASCII (strip Egyptological diacritics from the descriptor key — same convention as chunks 22/25/26/28/29/30/31/32).

Examples (RULE-based, not per-row answers):
- For `NORTHERN COMPLEX` (Snefru's Red Pyramid): anchor on the king + complex direction. The descriptor combines king-name + geographic anchor.
- For `SOUTHERN COMPLEX` (Snefru's Bent Pyramid): same pattern with opposite direction anchor.
- For `PYRAMID-COMPLEX OF <KING>`: anchor on the king's conventional English name (TitleCase ASCII, no diacritics, no Roman ordinal if PM uses Arabic; preserve Roman ordinal if PM does — e.g. `Sesostris III` → `Sesostris3`).
- For a `PYRAMID-ENCLOSURE OF <QUEEN-NAME>`: anchor on the queen's name. If a queen-name collides with a prior-chunk entry, append the husband-king as disambiguator (`DAH-<QueenName>Wife<KingName>`).
- For an anonymous `PYRAMID-ENCLOSURE PROBABLY OF WIFE OF <KING>`: anchor on the king + "AnonWife" (e.g. `DAH-AnonWife<KingName>`).
- For an anonymous Dyn-XIII pyramid (E / G / H): use the PM letter anchor (`DAH-PyramidE` / `DAH-PyramidG` / `DAH-PyramidH`) since no ruler is named.
- For a `PYRAMID OF <KING>` form (no "complex"): anchor on the king's name in TitleCase ASCII (drop hyphen if PM uses one).

**Homonym discipline**: existing tomb_ids in `reconciled.jsonl` (809 rows from chunks 1–32) are all SAQ-/MAR-/LS/G prefixed except cemetery-specific. The new DAH- prefix collides with none. Within the chunk, queen-name collisions across pyramid-complexes (e.g. if two named queens share a Khent-name) require disambiguator suffixes.

## Schema (23 keys, identical to chunks 20–32)

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
  "dynasty": "4" | "12" | "13" | null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "Pyramid-field of Dahshur",
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "is_uninscribed": false,
  "is_usurped": false,
  "attribution_certainty": "attested" | "probable" | "uncertain",
  "shared_with_tombs": [],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM III.2 2nd ed. 1978/1981", "section": "I"}
}
```

**Field-rule notes:**
- `memphite_area`: NEW VALUE `"Dahshur"` for this chunk (chunks 1-32 all used `"Saqqara"` or `"Giza"`; per the 2026-05-19 scope expansion, Dahshûr enters this source).
- `cemetery`: NEW VALUE `"Pyramid-field of Dahshur"` (per PM's `(876) PYRAMID-FIELD OF DAHSHUR` opening banner at chunk start).
- `dynasty`: PM uses Roman numerals in printed text (Dyn IV, Dyn XII, Dyn XIII). Convert to Arabic-decimal STRING for the field value: "4", "12", "13".
- `attribution_certainty`:
  - `"attested"`: PM names the ruler directly without hedge.
  - `"probable"`: PM hedges with "Probably" / "(?)" / "PROBABLY OF DYNASTY XIII" / "PROBABLY OF WIFE OF X" — preserved as `probable` for the certainty-axis.
  - `"uncertain"`: a stronger hedge (PM's "uncertain" / "possibly" / completely unattributed).
- `is_unfinished`: PM may note that a pyramid was unfinished. Preserve `true` only when PM explicitly says so.
- `notes_from_pm`: capture the dating + Lepsius / Perring-and-Vyse Roman ordinals + popular-name note (PM's "popularly known as the <name>" idiom when present — drop nothing PM verbalises) + any condition note. PM-faithful verbatim. Drop hieroglyph noise and cartouche bracket-blocks.

## Diacritic conventions

Same as chunks 9-32:
- Strip Egyptological diacritics from `tomb_id` descriptor (ASCII-only matching key for Phase A).
- Preserve PM-faithful diacritics in `occupant_name`, `occupant_alt_names`, `notes_from_pm`, `co_occupants`, `co_occupant_roles`: macron-ē/ū/ō, underdot-Ḥ/Ḫ/Ḳ/Ḏ, ayin U+02BF (modifier letter half ring; NOT U+2018 left single quote).
- The Snefru variant `Snofru` may appear; preserve PM's spelling verbatim.
- Sesostris III / Amenemḥet II / III are the conventional English forms; PM may use slightly different spellings — preserve PM's spelling in `occupant_name`, use the conventional ASCII form in `tomb_id`.

## Calibration self-check (not a hard rule)

Based on PM TOC structure for § I:
- A: ≈ 1 main pyramid + possible queen-enclosure(s)
- B: ≈ 1 main pyramid + possible queen-enclosure(s)
- C: ≈ 1 main pyramid + possible queen-enclosure(s)
- D: ≈ 1 main pyramid + possible queen-enclosure(s)
- E: ≈ 1 anonymous pyramid
- F: ≈ 1 main pyramid + possible queen-enclosure(s)
- G + H: ≈ 1–2 anonymous pyramids (depending on whether PM treats the combined section as one entry or two)
- I: ≈ 1 main pyramid

Total calibration target: ≈ 8–15 rows depending on how many queen-enclosures each king's complex carries and how G+H is structured. If your final count diverges by more than ±4 from this calibration, re-read the chunk file and check whether you've accidentally included § II mastabas / queens-in-galleries (not their own enclosures) or missed a queen-enclosure under one of the king's complexes.

## Constitutional Rule 1 — scholar-grade source-traced

Every field value must trace verbatim to text appearing in `raw/chunk-33-p516-p529-dahshur-pyramids.txt`. Do not synthesize values from your training knowledge of Dahshûr. If PM's printed text-layer is ambiguous, prefer the conservative null over a guessed value.

## Constitutional Rule 2 — no silent picks, no synthesis

If you encounter genuine ambiguity (multiple possible readings of an OCR glyph; PM body prose that could disambiguate but isn't part of the headword), leave the affected field null and the agent disagreement will surface in merge.

## Stop criterion

Emit one row per ROW-EMITTING headword in scope (Shape 1, 2, 3 above). Sort by `tomb_id` ascending. Sanity-check: each row has all 23 schema keys present (use `null` for unknown values, not omission), `dynasty` is a STRING ("4", "12", "13") not an integer, `memphite_area` is `"Dahshur"`, `cemetery` is `"Pyramid-field of Dahshur"`, `source_citation.section` is `"I"`.
