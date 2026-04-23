# Extraction prompt — Porter & Moss Vol I.2 (Theban Necropolis), Chunk 8

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p292-p314.txt` and produce a JSONL file with one structured row per numbered tomb in PM I.2 § X.A "Valley of the Queens — Numbered tombs". The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

This chunk uses the **existing numbered-tomb schema** (QV-prefixed ids like `KV1` for Valley of the Kings). No new schema innovation — it's the QV analogue of chunk 1's KV coverage.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-tomb answers. Every field value must trace to something in the chunk file. The only things the prompt may validly hint: structural facts about the section (page range, tomb-id range, absent numbers); text-layer noise signatures; vocabulary constraints.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume I, Part 2: Royal Tombs and Smaller Cemeteries.* 2nd edition, Oxford 1964.
- Section: **X. Valley of the Queens, A. Numbered tombs** (printed p.744–769; physical p.292–313).
- Offset: printed = physical + 458.
- The chunk file starts at physical p.292 (the QV plan-and-headword introductory page) and extends through p.313 (end of § X.A). It continues through p.314 so agents can see `XI. MEDYNET HABU` as a boundary marker — **do NOT extract rows from content at or after `XI. MEDYNET HABU` / `TOMBS INSIDE ENCLOSURE` (printed p.772)**.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF (see `transcribe.md` § "Method deviation").

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-a-chunk8.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-b-chunk8.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-c-chunk8.jsonl`

One JSON object per line. Sort rows by numeric `tomb_id` ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## How to identify a tomb headword

Each QV tomb's section begins with a heading line of the form `N. NAME (cartouches) parenthetical` — a number + period (or middle-dot rendered as `·`), a name in all-caps, optional cartouche garbage, optional parenthetical bibliographic/classical-traveller cross-references.

The headword block ends at the first body sub-header — any of `Corridor.`, `Hall.`, `Burial Chamber.`, `Side-room.`, `Sarcophagus Chamber.`, `Pillar.`, `East Side-room.`, `Shrine.`, `Outer Hall.`, `Inner Room.`, `Outer lintel`, `Approach.`, `Finds`, or any line introducing scene-by-scene `(1) ... (2) ... (3) ...` prose.

The bibliographic-references paragraph (`SCHIAPARELLI, Relazione, ...`, `CHAMPOLLION, Not. descr. ...`, `L. D. Text, iii, p. 234`) is part of the headword block but supplies no structured-field content — its `(CHAMPOLLION, No. X, L. D. Text, No. Y, WILKINSON, No. Z.)` parenthetical records earlier-edition cross-numbering that goes in `notes_from_pm`.

Text-layer digit rendering: QV tomb numbers may be rendered as `33·`, `38.`, `46.`, `66.`, etc. The middle-dot `·` is text-layer noise for a regular period. `51.` and `71.` appear as plain periods.

## Expected QV numbering in PM I.2 § X.A

The PM 1964 2nd edition catalogues these QV numbers (verified by a headword scan of the chunk text): **QV33, QV36, QV38, QV40, QV42, QV43, QV44, QV46, QV47, QV51, QV52, QV53, QV55, QV66, QV68, QV71, QV73, QV74, QV75**. That's **19 rows**.

Numbers absent from PM I.2 § X.A:
- QV1–QV32 (never catalogued in the 1964 edition)
- QV34, QV35, QV37, QV39, QV41, QV45, QV48–QV50, QV54, QV56–QV65, QV67, QV69, QV70, QV72, QV76–QV80 (numbered tombs PM does not catalogue as inscribed)

If your headword scan returns a number outside the expected-19 list, RE-CHECK the chunk file — it may be (a) a scene-number marker like `(38)` (not a tomb row), (b) a plate-caption tomb-number reference like "Tomb 71", or (c) a find-cross-reference in the § X.B unnumbered-tombs-and-pits sub-section. Those are NOT tomb headwords.

**False-positive watch:**
- `38. Nebnery` at printed p.757 is a SCENE-ITEM inside QV44's body (a figure labelled "Nebnery" in scene 38), NOT a tomb headword.
- `12. Mosi` at printed p.770 is inside § X.B "Unnumbered tombs and pits → Finds", NOT a numbered tomb.
- Any number < 33 that appears in your scan is likely a scene item or find reference. PM's § X.A numbering starts at QV33.

## Schema (per row)

Every row MUST have these keys; use `null` (not omitted, not empty string) for unknown values. This is the same schema used by chunks 1–5 for KV rows.

```json
{
  "tomb_id": "QV<N>",
  "valley": "Valley of the Queens",
  "occupant_name": "...",
  "occupant_alt_names": [...],
  "occupant_role": "...",
  "dynasty": null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "location_sub_area": null,
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": true|false,
  "shared_with_tombs": [...],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM I.2 2nd ed. 1964", "section": "X.A"}
}
```

## Field-by-field extraction rules

### `tomb_id`

`QV<N>` where `<N>` is the Arabic tomb number from the heading line (19 expected values — see list above).

### `valley`

Always `"Valley of the Queens"`.

### `occupant_name`

**PM-verbatim, conventional-English form, titlecase.** Extract the NAME token from the heading line after normalising text-layer noise.

Occupant-type prefixes in PM's QV headwords vary:
- `QUEEN <Name>` → `occupant_name: "<Name>"` (strip `QUEEN` prefix; role captured separately).
- `PRINCESS <Name>` → `occupant_name: "<Name>"`.
- `PRINCE <Name>` → `occupant_name: "<Name>"`.
- Plain `<NAME>` (no preceding role word) → `occupant_name: "<Name>"`.
- `A PRINCESS, no name.` / `A QUEEN, cartouche blank.` / `A QUEEN, no name.` → `occupant_name: null`. Capture the prose in `notes_from_pm`.

Text-layer noise to normalise (same rules as chunks 1–7):
- Underdot-H (`ḥ`) renders as `I:I`, `I;I`, `I}`, `l;I`, `1;1`; normalise per-convention:
  - In `occupant_name`: PRESERVE the `ḥ` diacritic when PM prints it scholarly-style (e.g. `KHAʿEMWESET`'s `ḥ` in the prenomen stays as `Khaʿemweset`; `MERYTAMUN` has no underdot).
  - In `notes_from_pm`: preserve underdot-H verbatim per PM.
- Ayin `ʿ` / text-layer `<` / `c` → use Unicode `ʿ` in `occupant_name` where PM prints the ayin (e.g. `BENTʿANTA`, `PARAʿḤIRWENEMEF`, `AMEN(ḤIR)KHOPSHEF`, `KHAʿEMWESET`).
- Cartouches render as garbage: drop entirely.
- Regnal Roman numerals: count capital-I glyphs even if rendered `Il` / `I Il` / `Ill`. `ESI II` → `Esi II`.
- Long name-plus-title clauses after the name (`Charioteer of the stable of the <XYZ>`, `Royal scribe, Overseer of horses`, `King's son, Hereditary prince of the <ABC>`) are NOT part of the name — those go in `notes_from_pm`.

### `occupant_alt_names`

A list of alternative names PM gives in the headword block (classical aliases in parentheses, variant personal-name forms). Empty list `[]` when absent.

Most QV headwords don't carry alt-names (the Dyn-XIX-XX royal ladies are Egyptologically fixed names without classical-tradition aliases). An exception: if PM prints a parenthesised alternative form after the primary name (e.g. `MERYTAMUN (MERYTAMUN)`), capture the parenthetical. `CHAMPOLLION, No. N` cross-refs are NOT alt-names — those go in `notes_from_pm`.

### `occupant_role`

Controlled vocabulary: `"King"`, `"Queen"`, `"Royal Family"`, `"Vizier"`, `"Official"`, `"High Priest"`, `"Princess"`, `"Prince"`, `"Unknown"`.

Assignment rules:
1. If `occupant_name` is null (`A QUEEN, no name`, `UNINSCRIBED`, cartouche-blank): role `"Unknown"`.
2. If the headword explicitly names the role:
   - `QUEEN <Name>` → `"Queen"`.
   - `PRINCESS <Name>` → `"Princess"`.
   - `PRINCE <Name>` → `"Prince"`.
   - `VIZIER <Name>` → `"Vizier"`.
3. If the headword lists a non-royal role title (e.g. `IMHOTEP, Vizier` — QV46): role is that title (`"Vizier"`).
4. Default for QV (§ X.A is the royal-female-tomb section): `"Queen"` if the occupant is biologically female per PM's prose, `"Prince"` if male prince.

For `A QUEEN, cartouche blank` / `A QUEEN, no name`: `occupant_name: null`, `occupant_role: "Unknown"` per rule 1.

### `dynasty`, `sub_period`, `date_bce_approx_start`, `date_bce_approx_end`

**All `null`** for every row at this extraction stage. Phase A enrichment fills these. Do NOT supply from outside knowledge.

### `location_sub_area`

`null` for all QV rows. PM does not sub-divide Valley of the Queens the way it does Valley of the Kings (West Valley vs East Valley for KV). The QV is a single valley with numbered tombs.

### `discovery_year`, `discoverer`

**`null`** for every row. `Excavated by <X>` / `Found by <X>` clauses go in `notes_from_pm`, not in these structured fields (same convention as chunks 1–7).

### `is_unfinished`

`true` iff the literal word `Unfinished` (capital-U) appears in the headword block. Note: QV38 (Queen Sitreʿ, wife of Ramesses I) has `Unfinished` explicitly in PM's headword — that's a known case. Other QV tombs should default to `false`.

### `shared_with_tombs`

List of `QV<N>` strings parsed from `See also Tomb N` / `See also Tombs N and M` / `See also KV<N>` phrases in the headword block. Only numbered cross-refs. Empty list `[]` when absent.

Most QV headwords don't cross-reference; `shared_with_tombs: []` is expected on most rows.

### `notes_from_pm`

A short verbatim prose fragment from the headword block that doesn't fit a structured field. Preserve PM's diacritics (ayin `ʿ`, underdot-H `ḥ`, underdot-T `ṭ`). Capture:

- **Royal-family kinship clauses:** `wife of Ramesses II`, `mother of Ramesses VI, daughter of Ḫubalzanet`, `King's son, Hereditary prince of the <XYZ>`, `daughter of Seḳenenreʿ-Taʿa and Sit-gehut`, `son of Ramesses III`, `Sem-priest of Ptaḥ, son of Ramesses III`. These are PM's primary genealogical content.
- **Regnal dating clauses:** `Ramesside.`, `Dyn. XX.`, `Dyn. XXVI.`, `Temp. Tuthmosis I.`, `Dyn. XX(?)`. PM uses Roman numerals + Latin `Temp.` prefix. Preserve verbatim.
- **Attribution hedges:** `(probably)`, `cartouche blank`, `no name.`
- **Earlier-edition cross-numbering:** `(CHAMPOLLION, No. 7, L. D. Text, No. 13, WILKINSON, No. 19.)` — preserve the bibliographic-reference parenthetical where it serves as cross-numbering. Join distinct clauses with `". "` per chunks 1-7.
- **Non-royal-role clauses** when the occupant is an official/vizier/priest with relationship to a royal: `Vizier. Temp. Tuthmosis I.` / `Charioteer of the stable of the Great King's son, Ramesses.`

Preserve PM's wording. Apply text-layer-noise normalisation. `null` when the headword has nothing beyond the name + cartouches + bare-biblio.

### `source_citation`

Object with three fixed keys:

- `"edition"`: exactly `"PM I.2 2nd ed. 1964"`.
- `"section"`: exactly `"X.A"`.
- `"page"`: the printed page number on which the tomb's headword line sits. **Extract from the chunk text** — the page-separator markers `===== PHYSICAL PAGE N (PRINTED PAGE M) =====` in the chunk file give you the printed number directly. Do NOT supply from memory.

## Structural gotchas to watch

- **False positive: scene numbers.** QV44 and QV66 and QV68 and others have long body-prose sections with scene lists `(1) ... (2) ... (38) ... (75) ...`. A `38.` at start of a line INSIDE a body-prose block is a scene-item marker, NOT a tomb headword. Distinguish by (a) position — after `Hall.` / `Burial Chamber.` / `Outer Hall.` sub-headers, and (b) context — scene items name divinities / wall-features, tomb headwords name royals with title prefixes.
- **Plate-caption cross-refs.** PM inserts plate-caption headers like `QUEENS' TOMBS, 60, 66, 68, 71, 73-5, and HAY, 3rd tomb east` (printed p.760) as page headers above shared floor-plans. These are PLATE CAPTIONS, not tomb headwords, and contain only a list of QV numbers — they do not produce rows.
- **§ X.B Unnumbered tombs and pits** starts at printed p.769. Content there is an object-level inventory (`Mosi, son of Ḥarwoz, in Cairo Mus.`) and NOT tomb rows. STOP emitting rows when you hit `B. UNNUMBERED TOMBS AND PITS` section header.
- **§ X.C Finds** and **§ X.D Graffiti** (printed p.770-771) are also out of scope.
- **`TOMBS INSIDE ENCLOSURE. DYN. XXII-XXVI.`** at printed p.772 is the § XI Medinet Habu section-start boundary; STOP before it. The chunk file includes p.772–773 only so you can see the boundary clearly — do NOT extract MEDINET HABU Mortuary Chapels (those are a separate future chunk).

## Pitfall summary (read LAST before running)

1. **19 rows expected**: QV{33, 36, 38, 40, 42, 43, 44, 46, 47, 51, 52, 53, 55, 66, 68, 71, 73, 74, 75}.
2. **QV33 is the LOWEST expected tomb number.** Any headword matching `\d+\.` at line start with number < 33 is almost certainly a scene item (`(38) Nebnery`) or § X.B find-cross-reference.
3. **Do NOT extract § X.B / § X.C / § X.D / § XI rows.** STOP at `B. UNNUMBERED TOMBS AND PITS` (~printed p.769).
4. **Do NOT supply dynasty / BCE dates** from your knowledge.
5. **PM-verbatim occupant names.** `Sitreʿ` keeps its ayin. `Merytamun` keeps PM's spelling (not "Meritamon" or "Merytamen"). `Bentʿanta` keeps its ayin. `Paraʿḥirwenemef` keeps ayin + underdot-H.
6. **`A QUEEN, no name` / `A PRINCESS, no name` rows** emit `occupant_name: null`, `occupant_role: "Unknown"`, the full prose PM prints in `notes_from_pm`.
7. **Role vocab**: Queen / Princess / Prince / Vizier / Official / Unknown — don't invent new roles.
8. **`source_citation.page` comes from the chunk text** (use `===== PRINTED PAGE M =====` markers), not memory.
9. **Skip body prose** (scene lists, wall-texts, bibliographic per-scene refs) starting at the first sub-header.

## Report back

After writing the JSONL, output a one-paragraph report with:
- Row count (should be 19) and the complete list of QV tomb_ids you emitted.
- Any row where you're unsure about a field, with the field name and your best-guess value.
- Any unexpected text-layer noise that this prompt doesn't already flag.

Stay under 150 words.
