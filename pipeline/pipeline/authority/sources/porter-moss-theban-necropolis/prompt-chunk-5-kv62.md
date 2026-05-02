# Extraction prompt — Porter & Moss Vol I (Theban Necropolis), Chunk 5

> **Schema update — PR A (2026-05-02).** Two new fields were added to the canonical row, and `occupant_alt_names` semantics were narrowed:
>
> - **`occupant_alt_names`** is now ONLY for alternate name forms of the SAME PERSON (prenomens; throne-name vs birth-name; transliteration variants). Tomb-nicknames (`Belzoni's tomb`, `Tomb of Memnon`, `Bruce's tomb`, etc.) DO NOT belong here — they go in `tomb_aliases`.
> - **`tomb_aliases: list[str]`** is the new field for popular names of the *tomb itself* (19th-c. surveyor designations, classical mis-attributions, local Arabic names).
> - **`co_occupants: list[{name, role, alt_names}]`** is the new field for joint burials — a tomb shared by multiple people. The headword (PM's first-listed person) goes in `occupant_name` / `occupant_role` / `occupant_alt_names`; the additional people go in `co_occupants` with per-person role.
> - **`is_joint_burial: bool`** (PR #169 round-2) flags coordinate burials where PM does NOT mark a principal occupant — the headword is a serialisation artifact, not a primacy claim. Default `false`. Set `true` when PM lists multiple occupants coordinately (e.g. SWV-ThreePrincesses: PM I.2 p.591 prints `MENHET, MERTI, AND MENWI` as a coordinate triple). Leave `false` when PM marks one occupant as syntactic subject (e.g. KV46: PM I.2 p.562 prints `YUIA ..., Divine father, AND THUIU ...` — Yuia leads). Phase-A consumers MUST treat `occupant_name` and `co_occupants[*].name` as a coordinate union for join purposes when this flag is `true`.
>
> The body of this prompt is preserved as historical record from the original extraction; the schema example below has been updated to show the new fields. If you re-run an agent against this prompt, follow the updated schema, not the body's older `occupant_alt_names` directives that conflated tomb-names with person-names.


You are one of three independent extraction subagents. Your job: read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p111-p112.txt` and produce a JSONL file with one structured row — KV62 (Tutʿankhamun) — from PM I.2 § I.A "Tombs".

This is a fact-extraction task on the Griffith Institute's published topographical bibliography. Extract: tomb number, occupant name, and headword-only metadata. Do NOT extract Moss's per-room descriptive prose. Do NOT supply dynasty or BCE dates from outside knowledge.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you answers. The expected row count and structural facts about the section are hints about PM's layout, not about the row's values. Every field value must trace to something in the chunk file.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume I, Part 2: Royal Tombs and Smaller Cemeteries.* 2nd edition, Oxford 1964.
- Section: I. Valley of the Kings, A. Tombs.
- Chunk tomb range: **KV62 only** — 1 row expected. **Why its own chunk:** PM's KV62 entry's body prose (per-room scene catalogues for Corridor, Antechamber, Annex, Sarcophagus Chamber, Treasury; object-by-object find lists including the sarcophagus, shrines, canopic box, `Anc. Near East, fig. 414`, etc.) spans physical p.112–128 (~17 printed pages) and is emphatically out of scope. The headword-only chunk file is trimmed to physical p.111–p.112 so you can't accidentally wander into the body.
- Printed page range: p.569–570. Physical PDF page range: p.111–112. Offset: physical = printed − 458.
- The chunk file begins at physical p.111 (printed 569) deliberately — KV62's headword sits at the tail of p.111 (earlier pages are KV56/KV57 body prose and shared finds; out of scope). The file extends through p.112 so you see the full bibliographic ribbon ending with `Excavated by Carnarvon and Carter.` before the first body sub-header `Corridor.`.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF. See `transcribe.md` § "Method deviation".

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-a-chunk5.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-b-chunk5.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-c-chunk5.jsonl`

One JSON object per line (just one line here). Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Finding the tomb headword

The KV62 headword sits in the chunk file. Scan for a line starting with a tomb-number-like glyph sequence followed by all-caps name and cartouches. Text-layer noise to expect for the NUMBER: `62` often renders as `6z` (lowercase z for 2) — this is a common OCR artefact in PM's lithographic text layer. Digit `2` → letter `z` and digit `5` → letter `s` are frequent in PM's running headers (chunk 4 saw `s66` for 566, `s6z` for 562, etc.).

The headword block ends at the first body sub-header. For KV62 this is `Corridor.` on physical p.112. Everything from `Corridor.` onwards is body prose and out of scope. The bibliographic ribbon between the headword and `Corridor.` IS part of the headword block.

## Schema (per row)

Every row MUST have these keys; use `null` for unknown values.

```json
{
  "tomb_id": "KV<N>",
  "valley": "Valley of the Kings",
  "occupant_name": "...",
  "occupant_alt_names": [...],
  "tomb_aliases": [...],
  "co_occupants": [],
  "is_joint_burial": false,
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

`KV<N>`. Normalise `6z.` → `62.`, or whatever the text layer emitted back to the Arabic tomb number.

### `valley`

Always `"Valley of the Kings"`.

### `occupant_name`

**PM-verbatim, conventional-English form, titlecase**. Extract the NAME token from the heading line after normalising text-layer noise.

Text-layer noise to normalise (these are glyph-rendering artefacts):
- All-caps name: titlecase it.
- Ayin (`ʿ`) in PM's headwords renders as `C` in the all-caps form and as `r` in the running headers (`Tomb 62, Tutrankhamun 571` is the running header version). When you encounter an ayin glyph in a royal name, preserve it in `occupant_name` (the ayin is a distinguishing radical — the chunk-1/2/3/4 precedent is to keep it in royal names: chunk-2 kept `Raʿmeses-Mentuhirkhopshef` with the ayin). Use the Unicode half-ring `ʿ` (U+02BF) for consistency with prior chunks.
- Cartouches after the name render as garbage — drop entirely.
- Any trailing `I` (capital-I) immediately after the name is likely a footnote-marker (superscript 1) that the text layer flattened inline. PM prints a footnote 1 at the bottom of p.111. Do NOT incorporate the superscript into the name — it's a typographic artefact.

Preserve PM's scholarly spelling (e.g. PM has historically preferred the ayin form over a plain apostrophe — use the Unicode ayin to match chunk-2 conventions).

### `occupant_alt_names`

Single-quoted classical-tradition nicknames in the headword block. Empty list `[]` if PM's headword doesn't carry a quoted alias.

### `occupant_role`

Controlled vocabulary. KV62's occupant is a king. Role is `"King"`.

### `dynasty`, `sub_period`, `date_bce_approx_start`, `date_bce_approx_end`

**All `null`**. Do NOT supply from outside knowledge.

### `location_sub_area`

KV62 sits in the East Valley (the main wadi). PM does NOT flag this tomb with an explicit sub-area marker like `West Valley.` in the headword — emit `null`.

### `discovery_year`, `discoverer`

**`null`**. Even if PM's headword contains a discovery phrase, the structured `discovery_year` / `discoverer` fields are reserved for future Phase-A enrichment. Discovery-related prose goes in `notes_from_pm` instead.

### `is_unfinished`

`true` iff the literal word `Unfinished` (capital-U) appears in the headword block. Otherwise `false`.

### `shared_with_tombs`

List of `KV<N>` strings parsed from `See also Tomb N` phrases in the headword block. Page running headers like `Tombs 57 and 62` are layout headers, NOT `See also` cross-references.

### `notes_from_pm`

Verbatim short prose fragments from the headword block that don't fit any structured field. For KV62 specifically, watch for:
- **1st-edition cross-ref.** PM prints a `[1st ed. N]` bracketed reference right after the tomb number and before the name, giving the 1st-edition tomb numbering. Text-layer OCR for this pattern is inconsistent (chunk 1 KV4 saw `formerly XII`, chunk 2 KV18 saw `(formerly XI)` which we stripped to `formerly XI`, chunk 3 KV34 saw `[rst ed. 24]` which we normalised to `1st ed. 24` based on corpus evidence). Capture the 1st-edition reference as `"1st ed. N"` (no brackets, Arabic numerals, matching the chunk-3 KV34 normalisation).
- **Discoverer / excavator clause.** PM prints `Excavated by <names>.` inside the bibliographic ribbon for many KV tombs. For KV62, this clause names the actual excavators (not just publication references). Capture it verbatim.
- If both a 1st-edition cross-ref AND an `Excavated by` clause appear, join them with `". "` (period-space) — chunk-2 KV14 precedent.

Per the diacritic policy (`README.md`): `notes_from_pm` is verbatim-preserve against PM's printed text. Preserve any diacritics (macrons, ayin, underdot-H) as PM prints them.

### `source_citation`

- `"edition"`: exactly `"PM I.2 2nd ed. 1964"`.
- `"section"`: exactly `"I.A"`.
- `"page"`: the printed page on which the KV62 HEADING LINE (the `62.` / `6z.` glyph sequence) sits. Extract from the chunk text — not from memory. The chunk text's form-feed separator identifies physical pages; the running header on the page where the heading line appears gives the printed-page number (look for `Tombs 57 and 62` or `Tomb 62, Tutankhamun N` style headers). Cross-check via the offset printed = physical + 458.

## Pitfall summary (read LAST)

1. **1 row expected**. If you emit more, you've picked up a scene-ref `(N)` or a shared-header line.
2. **PM's KV62 body prose is out of scope.** The file is trimmed to physical p.111–112 so you can't wander — but if you see `Corridor.`, `Antechamber.`, `Sarcophagus Chamber.`, `Annex.`, or any object-finds list, stop — that's body prose.
3. **Do NOT supply dynasty / BCE dates / discoverer** from your knowledge.
4. **Preserve PM's ayin in royal names** using `ʿ` (U+02BF), matching chunk-2 KV19 precedent.
5. **Trailing superscript-1 footnote marker** inline with the name is OCR noise — drop it.
6. **1st-edition cross-ref** in brackets → capture as `"1st ed. N"` in notes (chunk-3 KV34 convention).
7. **`Excavated by <names>.`** inside the ribbon → capture verbatim in notes.
8. **`source_citation.page`** from chunk text running header, not memory.
9. **`shared_with_tombs`** only from explicit `See also Tomb N` phrases, not page layout headers.

## Report back

After writing the JSONL, output a one-paragraph report (under 150 words) with:
- Row count (should be 1).
- Any field where you're uncertain + best-guess value.
- Any unexpected text-layer noise not already flagged by this prompt.
