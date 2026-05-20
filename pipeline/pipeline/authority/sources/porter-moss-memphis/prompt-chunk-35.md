# Extraction prompt — Porter & Moss Vol III.2, Chunk 35

> **Thirty-fifth chunk drawn from PM Vol III.2** — **Dahshûr § II.B + § II.C + § II.D** (closes the Dahshûr private-mastaba § II coverage). PM III.2 physical pp.534–538 / printed pp.894–898. Three lettered sub-sections all on the eastern flank of the southern pyramids and queens' enclosures. Per the 2026-05-19 all-dynastic scope expansion (mvp-tasks.md item 3). This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-35-p534-p538-dahshur-iib-c-d.txt`.

**Source:** PM III.2 2nd ed. 1978/1981, ed. Málek. **Page offset:** printed = physical + 360.

**Output:** one JSONL line per row sorted by `tomb_id`, `json.dumps(..., sort_keys=True, ensure_ascii=False)`. Write to ONE of `raw/agent-{a,b,c}-chunk35.jsonl`.

## Scope: three sub-banners (all under § II)

- **B. EAST OF THE SOUTHERN PYRAMID OF SNEFRU** — private OK mastabas east of Snefru's Bent Pyramid.
- **C. NORTH OF THE ENCLOSURE OF SESOSTRIS III** — private MK mastabas north of Sesostris III's enclosure.
- **D. SOUTH OF THE ENCLOSURE OF AMENEMḤET II** — private MK mastabas south of Amenemḥet II's enclosure.

cemetery values (NEW for § II.B/C/D):
- `"East of Southern Pyramid of Snefru"` (§ II.B)
- `"North of Enclosure of Sesostris III"` (§ II.C)
- `"South of Enclosure of Amenemḥet II"` (§ II.D)

memphite_area = `"Dahshur"` (continuing chunk 33+34). section = `"II"`.

**OUT OF SCOPE:**
- `FINDS` sub-sections within any of the three sub-banners (chunk-31/32/34 precedent — loose objects without tomb-owner attribution).
- `III. Miscellaneous` heading at chunk file's end (p.538 bottom; FINDS-style "loose statues/heads/false-doors found in the area" without explicit tomb attribution).
- Sub-features under each headword: `Plan,`, `View,`, `Stela,`, `Statue`, `False-door,`, `Pyramid-texts.`, etc.

## How to identify a row

Same shape grammar as chunk 34:

**Shape 1a — bare named tomb headword.** PM section opens with `<NAME IN CAPS> <hieroglyphs>, <role cluster>. <dating>.` (e.g. headword pattern in § II.B for OK officials). NO leading PM-number for § II.B (it's a named-tomb section, not a DE MORGAN numbered series). § II.C + § II.D use the DE MORGAN numbering convention from chunk 34: `<N>. <NAME IN CAPS> <hieroglyphs>, <role cluster>. <dating>.`

**Shape 5 — anonymous numbered tomb (§ II.C + § II.D).** PM-numbered DE MORGAN tomb opens with `<N>. <hedge> <dating>.` — NO all-caps name in the headword. `occupant_name: null`; `attribution_certainty: "probable"` if PM uses a hedge.

**Shape 5b — "NAME UNKNOWN" numbered tomb.** PM-numbered DE MORGAN tomb with explicit `<N>. NAME UNKNOWN <role cluster>. <dating>.` PM names the tomb as having an unknown occupant explicitly. `occupant_name: null` AND `occupant_role` is whichever role-cluster PM provides (rank-class title → `Royal Family`; office-role → `Official`; no titles → `Unknown`). `attribution_certainty: "attested"` (PM positively identified the tomb as having an unknown-occupant attribution — not a probability hedge).

## tomb_id convention

**Existing prefix:** `DAH-` (chunks 33-34).

**For § II.B named tombs (Shape 1a):** `DAH-<TitleCaseAsciiName>` form. Strip Egyptological diacritics (chunk-34 convention).

**For § II.C + § II.D named DE MORGAN-numbered tombs (Shape 1a):** `DAH-<TitleCaseAsciiName>` form. Capture the DE MORGAN number in `tomb_aliases` as `"DE MORGAN <N>"` (chunk-34 convention).

**For § II.C + § II.D anonymous DE MORGAN-numbered tombs (Shape 5 / 5b):** `DAH-MorganN<num>` where the `N` series resumes from chunk-34's NORTHERN-PART numbering (chunk-34 used § II.A NORTHERN PART numbers, restarting at 1 for SOUTHERN PART). § II.C + § II.D continue the SOUTHERN PART numbering series. Use `DAH-MorganS<num>` (S = chunk-34's SOUTHERN PART convention; § II.C/D extend the same series since they are geographically adjacent and PM's numbering is continuous from § II.A SOUTHERN PART through § II.C through § II.D — verify by inspecting chunk text-layer page numbers).

**Cross-chunk homonym discipline:** if any § II.B/C/D occupant-name collides with a prior `DAH-*` tomb_id (incl. chunk 33/34), append a disambiguator suffix (per chunk-30/31/32 precedent). If an occupant-name collides WITHIN this chunk, append a disambiguator (DE MORGAN-number anchor for Shape-1a, or topographic anchor). Shape-5b `NAME UNKNOWN` rows use the DE MORGAN number directly via the same `DAH-MorganS<N>` form as Shape-5 — the explicit-NAME-UNKNOWN flag is captured by `attribution_certainty: "attested"` + `occupant_name: null`.

## Schema (23 keys, identical to chunks 20-34)

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
  "dynasty": "4" | "5" | "6" | "12" | null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "East of Southern Pyramid of Snefru" | "North of Enclosure of Sesostris III" | "South of Enclosure of Amenemḥet II",
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

**Field-rule notes:**
- `memphite_area`: `"Dahshur"` for all rows (continuing chunk 33-34).
- `cemetery`: ONE of three new values per sub-banner (see Scope above).
- `section`: `"II"` for all rows.
- `dynasty`: PM Roman numerals → Arabic-decimal STRING. Closed-range hedges (`Dyn. V-VI`, `Dyn. V or VI`, `Dyn. IV-V`) resolve to the LATER bound per source-wide convention (DAH-InSnefruIshtef precedent set in chunk 34: `Dyn. V-VI` → `"6"`). Open-ended hedges ("or later") stay null. PM's `Old Kingdom` (no specific dynasty) → `null`. `Middle Kingdom` with no Dyn-number → `null`. `Temp. <King>` where King is in a single dynasty → that dynasty.
- `attribution_certainty`:
  - `"attested"`: PM directly names the occupant + role-cluster without hedge. ALSO applies to Shape-5b `NAME UNKNOWN` rows when PM positively asserts the absence of name (the assertion itself is attested).
  - `"probable"`: PM uses `Probably` / `Probably temp. <King>`. Reflects hedge on the identification.
  - `"uncertain"`: stronger hedge or PM's `(?)` marker.
- `occupant_role`: standard controlled vocab. `King's son` → `Prince`. `Vizier` / `Chief Justice and Vizier` → `Vizier`. Functional-office titles (`Prophet of <king>`, `Overseer of <X>`, `Scribe of <X>`, `Royal acquaintance`, `Boundary official`, `Embalmer`, `Regulator of a phyle`, etc.) → `Official`. Ethnic or status descriptor without office title → `Unknown`. Hereditary-prince-class rank titles with no specific office → `Royal Family` (the rank is class-marker, not specifically "son of the king").
- `is_joint_burial`: false unless PM uses an explicit joint-burial headword.
- `co_occupants` / `co_occupant_roles`: capture PM-named wives, sons, daughters in the headword block. Mirror chunk 32/34 convention.
- `notes_from_pm`: capture the dating + PM citation block (DE MORGAN, BORCHARDT, BARSANTI, etc.). PM-faithful verbatim. Drop hieroglyph noise.

## Diacritic conventions

Same as chunks 9-34:
- Strip Egyptological diacritics from `tomb_id` descriptor (ASCII-only).
- Preserve PM-faithful diacritics in `occupant_name`, `occupant_alt_names`, `notes_from_pm`, `co_occupants`, `co_occupant_roles`: macron-ē/ū/ō, underdot-Ḥ/Ḫ/Ḳ/Ḏ, ayin U+02BF.
- ḳ → Q convention for tomb_id (chunk-34 established). Add K-form to tomb_aliases if any ḳ-bearing name appears.
- Ayin: where PM's all-caps form renders as OCR `c` (e.g. headword `Nic` = `Niʿ`), strip the c entirely in tomb_id and use ayin U+02BF in occupant_name (chunk-34 round-3 precedent for DAH-NiankhSnefru).

## Calibration self-check (not a hard rule)

Total calibration target: ≈ 18–22 rows across § II.B + § II.C + § II.D. If your final count diverges by more than ±5 from this calibration, re-read the chunk file and check whether you've accidentally included FINDS / III. Miscellaneous content or missed a numbered-tomb headword.

## Constitutional Rule 1 — scholar-grade source-traced

Every value traces verbatim to `raw/chunk-35-p534-p538-dahshur-iib-c-d.txt`. No synthesis from training data.

## Constitutional Rule 2 — no silent picks, no synthesis

Ambiguity → null. Never invent characters absent from the text-layer.

## Stop criterion

Emit one row per ROW-EMITTING headword in scope. Sort by `tomb_id`. Every row has all 23 schema keys present. `dynasty` is a STRING. `memphite_area` = `"Dahshur"`. `section` = `"II"`. Do NOT emit a top-level `section` field (fix_rows strips spurious ones — chunk-34 lesson).
