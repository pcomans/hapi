# Extraction prompt — Porter & Moss Vol I (Theban Necropolis), Chunk 2

> **Schema update — PR A (2026-05-02).** Two new fields were added to the canonical row, and `occupant_alt_names` semantics were narrowed:
>
> - **`occupant_alt_names`** is now ONLY for alternate name forms of the SAME PERSON (prenomens; throne-name vs birth-name; transliteration variants). Tomb-nicknames (`Belzoni's tomb`, `Tomb of Memnon`, `Bruce's tomb`, etc.) DO NOT belong here — they go in `tomb_aliases`.
> - **`tomb_aliases: list[str]`** is the new field for popular names of the *tomb itself* (19th-c. surveyor designations, classical mis-attributions, local Arabic names).
> - **`co_occupants: list[{name, role, alt_names}]`** is the new field for joint burials — a tomb shared by multiple people. The headword (PM's first-listed person) goes in `occupant_name` / `occupant_role` / `occupant_alt_names`; the additional people go in `co_occupants` with per-person role.
>
> The body of this prompt is preserved as historical record from the original extraction; the schema example below has been updated to show the new fields. If you re-run an agent against this prompt, follow the updated schema, not the body's older `occupant_alt_names` directives that conflated tomb-names with person-names.


You are one of three independent extraction subagents. Your job: read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p60-p90.txt` and produce a JSONL file with one structured row per Theban tomb in this chunk. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`. Disagreements are resolved by per-field majority vote.

This is a fact-extraction task on the Griffith Institute's published topographical bibliography. Extract: tomb number, occupant name, and headword-only metadata. Do NOT extract Moss's per-room descriptive prose. Do NOT supply dynasty or BCE dates from outside knowledge — those stay null and are filled in Phase A.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-tomb answers. If you find yourself tempted to emit a value because the prompt named it, stop and re-read the chunk text. Every field value must trace to something in the chunk file. The only thing the prompt may validly hint is:

- structural facts about the section (what page range the chunk covers; which tomb-id range is in scope; whether any expected tomb-id is absent from the section);
- text-layer noise signatures (how the publisher's PDF text layer renders certain glyphs);
- vocabulary constraints (controlled-vocab enumerations).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume I, Part 2: Royal Tombs and Smaller Cemeteries.* 2nd edition, Oxford 1964.
- Section: I. Valley of the Kings, A. Tombs.
- Chunk tomb range: **KV11 through KV20** (inclusive) — 10 rows expected. **KV21 is absent from PM I.2 § I.A** (the list jumps from KV20 to KV22). This is a structural fact about PM's organisation, not a hint about contents.
- Printed page range: p.518–548. Physical PDF page range: p.60–90. Offset: physical = printed − 458.
- The chunk file begins at physical p.60 (printed 518) deliberately — KV11's headword sits at the tail of p.60 (the rest of p.60 is KV10 body, which is out of scope for chunk 2).
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF (text was OCRed at the source by the publisher; we are not re-OCRing). See `transcribe.md` § "Method deviation".

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-a-chunk2.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-b-chunk2.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-c-chunk2.jsonl`

(Whichever path the launching prompt tells you.)

One JSON object per line. Sort rows by tomb number ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Finding tomb headwords in the chunk text

Each tomb's section begins with a heading line of the form `N. NAME (cartouches) (parenthetical)` where `N` is the tomb number, `NAME` is the conventional-English occupant name in the publisher's all-caps typesetting, `cartouches` is the garbage-rendered hieroglyphic cartouche pair, and the `parenthetical` after the cartouches carries classical-tradition nicknames, cross-refs, and bibliographic shorthand.

The headword block ends at the first body sub-header — any of:
`Approach.`, `Entrance.`, `First Corridor.`, `Corridor A.`, `Corridor B.`, ...
`Hall D.`, `Hall E.`, `Hall J.`, `Hall N.`, ...
`Side-room C.`, `Side-room K.`, `Side-room L.`, ...
`Pillars.`, `Pillars A-F.`, `Ceiling.`, `Sarcophagus Chamber H.`, `Sarcophagus Chamber K.`, `Finds`, `Room F.`, ...
`Plan, p. N.`

— OR at the next tomb-number heading (whichever comes first). The bibliographic-references paragraph immediately after the headword (the `LEFEBURE, ...; CHAMP., ...; L. D. Text, ...` ribbon) is NOT body prose — it's part of the bibliographic ribbon and contains classical aliases / cross-refs you may need for `occupant_alt_names` and `shared_with_tombs`.

The text layer renders digits unreliably. A tomb number may appear as:
- Arabic (`15.`, `16.`, `17.`, `19.`, `20.`);
- Roman-via-capital-I (`II.` for 11; `I2.` for 12; `I 3·` or `I 3.` for 13 — middle-dot period is normal; `I4.` for 14; `I8.` for 18);
- Or separated-with-whitespace (`I 3.`).

When the first non-space glyph on a line is a digit-or-Roman-numeral sequence followed by `.` and an all-caps word, that's a tomb heading. When the first non-space glyph is `(N)` or `N,` it's a scene ID INSIDE a tomb, not a new tomb heading — skip.

## Schema (per row)

Every row MUST have these keys; use `null` (not omitted, not empty string) for unknown values.

```json
{
  "tomb_id": "KV<N>",
  "valley": "Valley of the Kings",
  "occupant_name": "...",
  "occupant_alt_names": [...],
  "tomb_aliases": [...],
  "co_occupants": [],
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
  "source_citation": {"page": <int>, "edition": "PM I.2 2nd ed. 1964", "section": "I.A"}
}
```

## Field-by-field extraction rules

### `tomb_id`

`KV<N>` where `<N>` is the Arabic-numeral tomb number recovered from the heading line. Normalise any Roman-via-`I` rendering back to Arabic (`II` → `11`, `I2` → `12`, `I 3` → `13`, `I4` → `14`, `I8` → `18`). Expected range: KV11–KV20 (10 rows). If you find a KV21 headword, re-check — the chunk description says KV21 is absent.

### `valley`

Always exactly `"Valley of the Kings"` for this chunk (PM I.2 § I.A is "Valley of the Kings — A. Tombs").

### `occupant_name`

**PM-verbatim, conventional-English form, titlecase, with regnal Roman numeral**. Extract the NAME token from the heading line after normalising text-layer noise. Preserve PM's scholarly spelling even when a more common modern form exists — the project's policy is PM-verbatim at this extraction layer, with Phase A ruler-authority reconciliation bridging to modern forms. Examples of the policy (not an answer key — the principle, that you apply per row you encounter):

- If PM prints `SETHOS`, emit `Sethos` (not `Seti`). Same principle for any other scholarly-variant spelling.
- If PM prints `RAʿMESES` or a compound like `MENTUHIRKHOPSHEF`, preserve PM's `e`/`i`/`u` choices and PM's apostrophe-for-ayin. Do NOT substitute the modern `Ramesses` or `herkhepshef` spelling — PM's form is a deliberate scholarly convention, not OCR noise.
- If PM prints `UNINSCRIBED` instead of a name, the tomb has no attested occupant — emit `occupant_name: null`.

Text-layer noise you SHOULD normalise (these are glyph-rendering artifacts, not PM's scholarly choice):

- `I:I` or `I;I` → `H` (underdot-H glyph in the text layer): `I:IATSHEPSUT` → `Hatshepsut`, `MERNEPTAI;I` → `Merneptah`.
- `Il` (capital-I + lowercase-l) in a regnal-numeral position → Roman `II`: `Sethos Il` → `Sethos II`.
- `Ill` in a regnal-numeral position → Roman `III`.
- `RAC ` with a trailing space mid-word → `Raʿ` (ayin rendered as separated `c` plus space): `RAC MESES` → `Raʿmeses`.
- Titlecase the all-caps heading: `RAMESSES` → `Ramesses`, `TAUSERT` → `Tausert`, `BAY` → `Bay`.
- Cartouches after the name render as garbage (`(0E:'l~] (0 ffi ~t l]`, `(0~U] o=~~J`, etc.). Drop entirely.

### `occupant_alt_names`

A list of alternative names PM gives in the headword block. Two things count:

1. **Single-quoted classical-tradition nicknames** inside a parenthetical that follows the cartouches. Example patterns: `('Belzoni's tomb', CHAMPOLLION, No. 3, ...)`, `(Bruce's tomb, or the Harper's tomb. Descr. Ant. 5th tomb east, ...)`. When PM gives two nicknames joined by `or`, both go into the list, each as its own string, preserving the leading article where PM uses one (`the Harper's tomb`, not `Harper's tomb`).
2. **Classical-traveller occupant-ascriptions** inside a `('Tomb of <Name>', ...)` quoted parenthetical — the `<Name>` inside the quotes, not the literal `Tomb of <Name>`. (E.g. chunk 1's KV9 `'Tomb of Memnon'` → alias `Memnon`.)

Things that do NOT count (do not collect as alt names):
- Bibliographic cross-references: `CHAMPOLLION, No. ii`, `L. D. Text and WILKINSON, No. 18`, `BuRTON, E`, `HAY, No. 13` — these name the classical-traveller publication and its internal numbering, not an alias for the occupant.
- `Descr. Ant. <Nth tomb east/west>` — positional reference inside Description de l'Égypte, not an alias.
- Cross-refs to other tombs (`See also Tomb N`) — those go in `shared_with_tombs`.
- Usurper names or relational biographical phrases (`wife of X`, `son of X`) — those go in `notes_from_pm`.

Empty list `[]` when no quoted alias appears in the headword.

### `occupant_role`

Controlled vocabulary (exact strings): `"King"`, `"Queen"`, `"Royal Family"`, `"Vizier"`, `"Official"`, `"High Priest"`, `"Princess"`, `"Prince"`, `"Unknown"`.

Assignment rules, in order:

1. If `occupant_name` is null (PM says `UNINSCRIBED` or equivalent), role is `"Unknown"`.
2. If the headword carries an explicit relational phrase naming a role (`Chancellor`, `Vizier`, `son of X`, `daughter of X`, `wife of X`), use it:
   - `Chancellor` → `"Official"` (no dedicated Chancellor slot in the vocab).
   - `son of <King>` → `"Prince"`.
   - `daughter of <King>` → `"Princess"`.
   - `wife of <King>` → `"Queen"` unless the cartouches and regnal notes indicate ruling-as-King (see rule 3).
3. If the tomb's occupant has cartouches drawn in the PM headword AND the surrounding text (section header, bibliographic ribbon, or body headers referring to the occupant) refers to them as `King` or uses `King's names` / `King receives life` in the scene-ref ribbon, role is `"King"` regardless of biological sex. This is how Hatshepsut and Tausert — both of whom ruled as king — are typed.
4. Otherwise role is `"King"` by default for KV tombs (KV § I.A is the royal tombs section; any non-royal exception is caught by rules 1–3 above).

### `dynasty`

**`null`** for every row. PM's headwords do not print dynasty numbers. Phase A ruler-authority enrichment against pharaoh.se fills this. Do NOT supply from your own knowledge of who the king is.

### `sub_period`

**`null`** for every row at this extraction stage.

### `date_bce_approx_start` / `date_bce_approx_end`

**`null`** for every row. Phase A fills these from the ruler authority.

### `location_sub_area`

PM I.2 § I.A does not sub-divide into East / West Valley at the headword level for most of these tombs — it reserves `West Valley` as an explicit flag on tombs that sit there (KV23 Ay is flagged in PM; that tomb is outside this chunk, but the same rule applies). Emit the exact PM flag if present; `null` otherwise.

### `discovery_year` / `discoverer`

**`null`** for every row. PM names Belzoni / Carter / Davis / Loret / Champollion / Wilkinson in bibliographic ribbons as *publication* references, not as statements of who *discovered* the tomb. `Excavated by X` phrases in body prose ARE discoverer info, but sit past the first body sub-header and are out of scope for the headword-only rule.

### `is_unfinished`

`true` if the literal word `Unfinished` (capital-U, lowercase tail) appears in the headword block — typically either as a standalone sentence after the bibliographic ribbon (`... BuRTON, U.) Unfinished.`) or inside a parenthetical. Case-sensitive: lower-case uses of "unfinished" in body prose don't count (and sit past the headword anyway).

### `shared_with_tombs`

A list of `KV<N>` strings parsed from `See also Tomb N` / `See also Tombs N and M` / `See also Tomb N.` phrases in the headword block.

Only **numbered** references count. If PM writes `See also South Tomb, infra, p. N` (a positional informal reference, not a numbered KV tomb), emit `[]` — `South Tomb` is not a tomb_id. Likewise, `See also p. N` (unqualified page reference without a tomb number) does not populate this list.

Empty list `[]` when no numbered cross-ref appears.

### `notes_from_pm`

A short verbatim prose fragment from the headword block that doesn't fit any structured field. Capture things like:
- Biographical/relational phrases: `wife of <King>`, `son of <King>`, `daughter of <King>`, `Temp. <King A>-<King B>` (regnal-dating phrase Egyptologists use to mean "in the reign of").
- Parenthetical disambiguations around a regnal number: `(formerly <other-number>)`.
- Usurpation phrases: `Usurped by <King Y>`.
- Short interpretive clauses present in the headword (not in the body) such as the "doorways in outer part usurped from Ramesses V" clause chunk 1 captured for KV9.

Preserve PM's wording. Apply the same text-layer noise normalisation as on `occupant_name` (e.g. `Il` → `II`, `I;I` → `h`, titlecase small-caps king names). If two distinct headword phrases should both be captured, join them with `". "` — e.g. `wife of Sethos II. Usurped by Setnakht`.

`null` when the headword has nothing besides the name + cartouches + bibliographic ribbon.

### `source_citation`

Object with three fixed keys:

- `"edition"`: exactly `"PM I.2 2nd ed. 1964"`.
- `"section"`: exactly `"I.A"`.
- `"page"`: the printed page number on which the tomb's headword line sits. **Extract from the chunk text — do NOT supply from a hardcoded table.** Method:
  1. The chunk file uses form-feed (`\f`, ASCII 12) as a page separator.
  2. Each physical page begins with a running header. On recto pages the header typically shows the tomb number and the printed page number, e.g. `Tomb I4 531`, `Tombs I6 and I7 535`, `Tombs 20 and 22 547`. On verso pages it's usually `<page> VALLEY OF THE KINGS` or just `VALLEY OF THE KINGS` (without a visible digit when the digit drifted into the margin).
  3. When the running header has a visible printed-page digit, use it.
  4. When the running header lacks a visible digit (verso pages where the digit drifted), derive via the offset: printed = physical + 458. The chunk starts at physical page 1 of the file = overall physical p.60 = printed p.518; count form-feeds to find which physical page a headword sits on, then add the offset.
  5. When a headword appears at the tail of one page and its bibliographic ribbon flows onto the next, use the page where the **heading line itself** appears.

## Pitfall summary (read LAST before running)

1. **Output exactly one JSONL file** at the path the launcher gave you; one JSON object per line; sort by numeric tomb id; deterministic serialisation (`sort_keys=True, ensure_ascii=False`).
2. **Do NOT supply dynasty or BCE dates** from your knowledge. They stay null.
3. **Do NOT over-modernise occupant names** past PM's own spelling. PM-verbatim at this layer; Phase A bridges to modern conventions.
4. **Cartouche garbage drops entirely** — don't try to recover cartouche text from the text layer.
5. **Only numbered `See also Tomb N` refs** populate `shared_with_tombs`. Informal or unnumbered references go nowhere (or to `notes_from_pm` if they're substantive prose).
6. **Body prose starts at the first `Approach` / `Entrance` / `Corridor` / `Hall` / `Side-room` / `Pillars` / `Ceiling` / `Sarcophagus Chamber` / `Finds` / `Plan, p.` sub-header** after the bibliographic ribbon. Everything from there until the next tomb heading is out of scope.
7. **`(N)` and `N,` at line start are scene-refs inside a tomb**, not tomb headings. Don't be fooled.
8. **`source_citation.page` comes from the chunk text**, not from your recollection of PM's pagination.

## Report back

After writing the JSONL, output a one-paragraph report with:
- Row count.
- Any row where you're unsure about a field, with the field name and your best-guess value.
- Any unexpected text-layer noise that this prompt doesn't already flag.

Stay under 150 words.
