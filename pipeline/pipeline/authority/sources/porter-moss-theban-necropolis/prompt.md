# Extraction prompt — Porter & Moss Vol I (Theban Necropolis), Chunk 1: KV1–KV10

> **Schema update — PR A (2026-05-02).** Two new fields were added to the canonical row, and `occupant_alt_names` semantics were narrowed:
>
> - **`occupant_alt_names`** is now ONLY for alternate name forms of the SAME PERSON (prenomens; throne-name vs birth-name; transliteration variants). Tomb-nicknames (`Belzoni's tomb`, `Tomb of Memnon`, `Bruce's tomb`, etc.) DO NOT belong here — they go in `tomb_aliases`.
> - **`tomb_aliases: list[str]`** is the new field for popular names of the *tomb itself* (19th-c. surveyor designations, classical mis-attributions, local Arabic names).
> - **`co_occupants: list[{name, role, alt_names}]`** is the new field for joint burials — a tomb shared by multiple people. The headword (PM's first-listed person) goes in `occupant_name` / `occupant_role` / `occupant_alt_names`; the additional people go in `co_occupants` with per-person role.
>
> The body of this prompt is preserved as historical record from the original extraction; the schema example below has been updated to show the new fields. If you re-run an agent against this prompt, follow the updated schema, not the body's older `occupant_alt_names` directives that conflated tomb-names with person-names.


You are one of three independent extraction subagents. Your job: read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p37-p60.txt` and produce a JSONL file with one structured row per Theban tomb in this chunk. The other two agents see the same prompt and the same chunk; their outputs will be majority-voted by `merge.py` to produce `reconciled.jsonl`. Disagreements are resolved by majority vote per field.

This is a fact-extraction task on the Griffith Institute's published topographical bibliography. We extract: tomb number, occupant name, and headword-only metadata (the `Unfinished` flag, `See also Tomb N` cross-refs, classical aliases, page citation). We do NOT extract Moss's per-room descriptive prose. We do NOT supply dynasty or BCE dates from outside knowledge — those fields stay null and are filled in Phase A by reconciling against the king authority (pharaoh.se).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume I, Part 2: Royal Tombs and Smaller Cemeteries.* 2nd edition, Oxford 1964.
- Section: I. Valley of the Kings, A. Tombs.
- Printed page range: p.495–518. Physical PDF page range: p.37–60. Offset: physical = printed − 458.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF (text was OCRed at the source by the publisher; we are NOT re-OCRing). See `transcribe.md` § "Method deviation".

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-a.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-b.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-c.jsonl`

(Whichever path the launching prompt tells you. If the launch prompt did not specify, use `agent-a.jsonl` — the launcher will rename if needed.)

One JSON object per line. Sort rows by tomb number (1, 2, 3, ..., 10). Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` so the output is deterministic and merge-friendly.

## Schema (per row)

Every row MUST have these keys; use `null` (not omitted, not empty string) for unknown values.

```json
{
  "tomb_id": "KV9",
  "valley": "Valley of the Kings",
  "occupant_name": "Ramesses VI",
  "occupant_alt_names": [],
  "tomb_aliases": ["Tomb of Metempsychosis", "Tomb of Memnon"],
  "co_occupants": [],
  "occupant_role": "King",
  "dynasty": null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "location_sub_area": null,
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "shared_with_tombs": [],
  "notes_from_pm": "doorways in outer part usurped from Ramesses V",
  "source_citation": {"page": 511, "edition": "PM I.2 2nd ed. 1964", "section": "I.A"}
}
```

## Field-by-field extraction rules

Every field is extracted from PM's HEADWORD BLOCK, never from the body prose. The headword block for tomb N starts at the line `N. NAME (cartouches) (parenthetical)` and ends at the first body sub-header (`Approach.`, `Corridor A.`, `Hall D.`, `Side-room K.`, `Pillars.`, `Ceiling.`, `Sarcophagus Chamber X.`, `Finds`, etc.) OR at the next tomb-number heading. The bibliographic-references paragraph immediately after the headword (the one that lists `LEFEBURE, ...; CHAMP., ...; L. D. Text, ...`) is NOT body prose — it's part of the bibliographic ribbon and contains classical aliases / cross-refs you may need.

### `tomb_id`

`KV<N>` where `<N>` is the Arabic-numeral tomb number. PM's text-layer renders the leading `1.` of Tomb 1 as `I.` (Roman one) due to font OCR; treat it as Arabic 1. The chunk contains tomb numbers 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 in order. If you find more than 10 distinct tomb numbers, you have over-matched (probably grabbed numbered scene refs `1, King...` as if they were tomb headers).

### `valley`

Always exactly the string `"Valley of the Kings"` for this chunk. (PM I.2 § I.A is "Valley of the Kings — A. Tombs".)

### `occupant_name`

Conventional English form, titlecase, exactly as PM prints in the headword (after correcting the OCR drift). Treat the predictable text-layer noise:
- `RAMESSES Ill` (capital I + lowercase L + lowercase L) → `Ramesses III` (Roman three).
- `RAMESSES I I` (with stray space) → `Ramesses II`.
- `MERNEPTAI;I` → `Merneptah`. PM consistently uses the spelling `Merneptah`; the `;I` is the text layer's rendering of an `H` glyph that printed weirdly.
- `RAMESSES XI (formerly XII)` → `Ramesses XI` (the `(formerly XII)` is a parenthetical for `notes_from_pm`).
- `AMENMESSE` → `Amenmesse`. PM's spelling — do NOT regularise to `Amenmesses`.
Use the Roman numeral for the regnal-number suffix exactly as PM prints (after OCR correction): `I, II, III, IV, V, VI, VII, VIII, IX, X, XI`.

### `occupant_alt_names`

A list of alternative names PM gives in the headword block — typically as a parenthetical right after the cartouches. Most KV in this chunk have none, in which case use `[]`.

**KV9 (Ramesses VI) is the example for this chunk** — its headword block contains the parenthetical `('Tomb of Metempsychosis', or 'Tomb of Memnon'. ...)`. The classical alias `Memnon` is a 19th-c. ascription that travel literature (and museum catalog provenance text) uses for KV9. Capture it as `["Memnon"]`. Do NOT include `Tomb of Metempsychosis` — that's a tomb-name not an occupant-name.

`Tomb of <Name>` parentheticals like the one in KV9's headword are PM's signal for classical aliases; treat the alias inside the quotes as an alt name when the named figure is plausibly the occupant or an ascribed classical alias for the occupant.

### `occupant_role`

Always exactly `"King"` for this chunk. KV1–KV10 are all kings. (Future chunks for QV will use `Queen`; TT uses `Vizier`/`Official`/`High Priest`.)

### `dynasty`

**`null`** for every row in this chunk. PM's headwords do NOT print dynasty. The `dynasty` field is filled in Phase A by reconciling `occupant_name` against the king authority (pharaoh.se). Do NOT supply dynasty from your own knowledge of who Ramesses III was — per CLAUDE.md rule 7, domain values come from authority lookup, not from string literals.

### `sub_period`

`null` for everything in this chunk.

### `date_bce_approx_start` / `date_bce_approx_end`

**`null`** for every row in this chunk, same reasoning as `dynasty`. Phase A king-authority reconciliation supplies BCE dates.

### `location_sub_area`

`null` for KV in this chunk. PM's KV section does not subdivide into East / West Valley at the headword level for these tombs.

### `discovery_year` / `discoverer`

`null` for every row in this chunk. PM does mention Belzoni / Loret / Carter / Carnarvon / Champollion / Wilkinson in the bibliographic-references paragraph, but those are RECORD-OF-WORK references (who published a description), not statements of who DISCOVERED the tomb. Do not infer discoverer from the bibliographic ribbon.

### `is_unfinished`

`true` if the literal word `Unfinished` appears in the headword block (the parenthetical right after the cartouches typically). Else `false`. Spot-check: search the headword block for the literal string `Unfinished`; the search is case-sensitive but PM consistently capitalises this word.

### `shared_with_tombs`

A list of `KV<N>` strings parsed from any `See also Tomb N` (or `See also Tombs N and M`, `See also Tomb N.`) phrase in the headword block. PM uses this convention to cross-reference tombs that are physically related (e.g. an unfinished + completed pair). Empty list `[]` if no such cross-ref appears.

### `notes_from_pm`

A short verbatim prose fragment from the headword block that doesn't fit a structured field. Preserve the EXACT PM wording (post OCR correction). If the prose continues onto a second physical line within the same headword block (before the bibliographic-references paragraph), include the continuation. Example: KV9's headword has `doorways in outer part usurped from RAMESSES V` spread across two lines — capture the full clause `doorways in outer part usurped from Ramesses V` (titlecase the king-name, since that's the canonical-English form and matches `occupant_name` casing). Other example: KV4's `RAMESSES XI (formerly XII)` — the parenthetical `formerly XII` goes here.

If no such fragment exists, use `null`.

### `source_citation`

Object with three fixed keys. **The `page` value is extracted from the chunk text — DO NOT supply it from a hardcoded table.** Instead:

1. The chunk file is divided into physical pages by the form-feed character (`\f`, ASCII 12, `chr(12)`). Each page starts with a running header that contains the printed page number (e.g. `Tombs 7 and 8 507` or `Tomb 9 511` at the top of the page).
2. To find the printed page for a tomb's headword: locate the headword line (e.g. `8. MERNEPTAH ...`) in the chunk text, identify which form-feed-delimited physical page it sits on, and read the printed page number from the running header on that page.
3. Cross-check: physical page = printed page − 458 (offset documented in `transcribe.md`). Physical page 1 in the chunk corresponds to PM I.2 printed page 495.
4. Use the printed page number from the running header. Do NOT guess; do NOT supply from outside knowledge.

The other two keys are fixed:
- `"edition"`: exactly the string `"PM I.2 2nd ed. 1964"`.
- `"section"`: exactly the string `"I.A"` (Section I "Valley of the Kings", subsection A "Tombs").

## Edge-case handling

- **Cartouches** — PM prints the king's hieroglyphic cartouches inline immediately after the conventional English name (`RAMESSES IV (cartouche-1) (cartouche-2)`). The text layer renders these as garbage like `(0j~~-:=:) (0ffi J`. Drop them entirely. Do NOT try to recover the cartouche contents — they will be re-acquired from the king authority (pharaoh.se) in Phase A.

- **Egyptological ayin `ʿ` rendered as `c`** — PM's text layer outputs `Rec` for `Reʿ` and similar in king-titulary. This noise sits in dropped body prose, not in the conventional-English `occupant_name`. Don't normalise on your own — the centralised `fix_rows.py` will handle any that do reach structured fields.

- **Body prose detection** — every tomb's headword is followed by sub-headers like `Corridor A.`, `Corridor B.`, `Hall D.`, `Side-room L.`, `Sarcophagus Chamber K.`, `Approach.`, `Pillars.`, `Ceiling.`, `Finds`, `Plan, p. N.`. These mark the descriptive body prose — IGNORE everything from such a sub-header until the next tomb-number heading. Do NOT extract scene catalogs, plate references, or ceiling descriptions.

- **Numbered scene refs** — body prose contains lines like `(2) [1st ed. 4] Litany of Re c.` and `1, King receiving life from Rec-Harakhti`. These are scene IDs INSIDE a tomb, NOT new tombs. Never confuse `(N)` parentheticals or `N, ` comma-suffixed descriptions with tomb-number headers.

- **Tomb 5 has very little material** — PM gives essentially just the headword + a one-sentence `Remains of left jamb of entrance` note. Still emit a full row with all fields populated per the rules above.

- **Tombs 5 and 7 are both Ramesses II** — they are two distinct tombs both attributed to Ramesses II, cross-referenced by `See also Tomb 5` / `See also Tomb 7` headwords. Emit two rows, both with `occupant_name: "Ramesses II"`, identical `occupant_role`, but different `tomb_id` and `source_citation.page`, and `shared_with_tombs` = the OTHER tomb's id.

## Pitfall summary (read this LAST before running)

1. **10 rows expected**, one per KV1–KV10. Not 9. Not 11. If your count is off, recheck — over-matching scene refs is the most common failure.
2. **`occupant_name` is titlecase, conventional English**, with the regnal-number suffix as a Roman numeral. NOT all-caps (PM headwords print all-caps for typesetting).
3. **`dynasty`, `date_bce_approx_*` are null** — Phase A king-authority enrichment fills them. Do NOT supply from your own knowledge.
4. **`source_citation.page` comes from the chunk text running header**, not from a hardcoded table. Identify the form-feed-delimited physical page where the headword sits, read the printed page number from the page's running header.
5. **Drop everything from `Corridor`/`Hall`/`Side-room`/`Approach`/`Pillars`/`Ceiling`/`Finds` headers onward** — those are descriptive prose, out of scope.
6. **Cartouches render as garbage** — drop them.
7. **`shared_with_tombs` are the cross-referenced KV IDs**, parsed from `See also Tomb N` literal text in the headword.
8. **`is_unfinished` is true ONLY if the literal word `Unfinished` appears in the headword block.**

## Report back

After writing the JSONL, output a one-paragraph report with:
- Row count (should be 10).
- Any row where you're unsure of a field assignment, with the field name and your best-guess value.
- Any unexpected text-layer noise that the chunk-1 prompt doesn't already call out.

Stay under 150 words.
