# Extraction prompt — Porter & Moss Vol I (Theban Necropolis), Chunk 4

You are one of three independent extraction subagents. Your job: read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p106-p111.txt` and produce a JSONL file with one structured row per Theban tomb in this chunk. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

This is a fact-extraction task on the Griffith Institute's published topographical bibliography. Extract: tomb number, occupant name, and headword-only metadata. Do NOT extract Moss's per-room descriptive prose. Do NOT supply dynasty or BCE dates from outside knowledge — those stay null and are filled in Phase A.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-tomb answers. If you find yourself tempted to emit a value because the prompt named it, stop and re-read the chunk text. Every field value must trace to something in the chunk file. The only things the prompt may validly hint: structural facts about the section (page range, tomb-id range, absent numbers); text-layer noise signatures; vocabulary constraints.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume I, Part 2: Royal Tombs and Smaller Cemeteries.* 2nd edition, Oxford 1964.
- Section: I. Valley of the Kings, A. Tombs.
- Chunk tomb range: **KV47, KV48, KV55, KV56, KV57** — 5 rows expected. The following KV numbers ARE NOT in this chunk's range (either genuinely absent from PM I.2, or deferred to a later chunk): KV49–KV54 and KV58–KV61 are absent from PM I.2 § I.A (PM jumps 48 → 55, 57 → 62). KV62 (Tutankhamun) is deferred to a later chunk because PM's KV62 entry spans 11 pages and warrants its own extraction PR.
- Printed page range: p.564–569. Physical PDF page range: p.106–111. Offset: physical = printed − 458.
- The chunk file begins at physical p.106 (printed 564) deliberately — KV47's headword sits at the tail of p.106 (KV46 body is out of scope, belonging to chunk 3). The file extends through p.111 so you can see the KV62 boundary marker closing KV57.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF. See `transcribe.md` § "Method deviation".

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-a-chunk4.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-b-chunk4.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-c-chunk4.jsonl`

One JSON object per line. Sort rows by numeric tomb_id ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Finding tomb headwords in the chunk text

Each tomb's section begins with a heading line of the form `N. NAME (cartouches) (parenthetical)` — a number, a period (or middle-dot rendered as `·`), a name, optional cartouche garbage, optional parenthetical.

The headword block ends at the first body sub-header — any of the following or similar:
`Approach.`, `Entrance.`, `Corridor A.`, `Hall D.`, `Sarcophagus Chamber.`, `Sarcophagus Chamber H.`, `Room E (Well Room).`, `Pillars.`, `Ceiling.`, `Finds`, `Objects in Cairo Museum.`, `Plan, p. N.`, `Gilded shrines.`, or any line introducing room-by-room or object-by-object prose.

The bibliographic-references paragraph (`DAVIS, &c., ...`, `LEFEBURE, ...`, `AYRTON in P.S.B.A. ...`) is part of the headword block and contains classical aliases / cross-refs. `Excavated by <X>` clauses inside the headword block go in `notes_from_pm`.

Text-layer digit rendering: expect `47·` (middle-dot period), `48.` (plain period), `55·`, `57·`. Some headwords may have irregular spacing.

## Schema (per row)

Every row MUST have these keys; use `null` (not omitted, not empty string) for unknown values.

```json
{
  "tomb_id": "KV<N>",
  "valley": "Valley of the Kings",
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
  "source_citation": {"page": <int>, "edition": "PM I.2 2nd ed. 1964", "section": "I.A"}
}
```

## Field-by-field extraction rules

### `tomb_id`

`KV<N>` where `<N>` is the Arabic tomb number from the heading line. Expected set: {47, 48, 55, 56, 57}.

### `valley`

Always `"Valley of the Kings"`.

### `occupant_name`

**PM-verbatim, conventional-English form, titlecase, with regnal Roman numeral.** Extract the NAME token from the heading line after normalising text-layer noise. Preserve PM's scholarly spelling (PM uses `Amenophis`/`Tuthmosis`/`Sethos`; do NOT modernise to `Amenhotep`/`Thutmose`/`Seti`).

Text-layer noise to normalise (glyph-rendering artifacts, not PM's scholarly choice):
- `I:I` or `I;I` → `h` (underdot-H glyph — NOT ayin): `MERNEPTAI;I-SIPTAI;I` → `Merneptah-Siptah`, `I:IAREMI}AB` → `Haremhab`. The `I:I` consumes its surrounding slot — no stray `i` is left.
- Regnal Roman numerals are glyph-counted. Count capital-I glyphs — including ones that appear as lowercase `l` (`Il`) or separated by spaces. Examples: `Il` → `II`, `I Il` → `III`, `Ill` → `III`.
- Cartouches after the name render as garbage — drop entirely.
- Titlecase the all-caps heading: `MERNEPTAH-SIPTAH` → `Merneptah-Siptah`, `AMENEMOPET` → `Amenemopet`.

PM's precise headword wording matters in this chunk: some tombs are attributed with explicit uncertainty (see `occupant_alt_names` and `notes_from_pm` rules below).

If PM's headword begins with a hedge like **"Probably <NAME>"** or **"Attributed to <NAME>"**: extract `<NAME>` as `occupant_name` (without the "Probably" / "Attributed to" prefix), keep the structured name clean, and record the full hedging clause in `notes_from_pm` — same pattern as chunk-3 KV42's `(?)` handling.

If PM's headword gives no personal name (e.g. `'Gold Tomb', uninscribed.` or `UNINSCRIBED`): emit `occupant_name: null`. Any descriptive clause PM provides (nicknames in quotes, attribution guesses) goes in `notes_from_pm` — the `'Gold Tomb'` style nickname does NOT go in `occupant_alt_names` because that field is for alternative names of a known occupant.

### `occupant_alt_names`

A list of alternative names PM gives **for a named occupant** in the headword block — single-quoted classical-tradition nicknames (`'Belzoni's tomb'`) or quoted alternative personal-name forms. Only populated when `occupant_name` is non-null.

Empty list `[]` in the default case.

### `occupant_role`

Controlled vocabulary: `"King"`, `"Queen"`, `"Royal Family"`, `"Vizier"`, `"Official"`, `"High Priest"`, `"Princess"`, `"Prince"`, `"Unknown"`.

Assignment rules (apply per row):
1. If `occupant_name` is null (PM says `UNINSCRIBED`, a nickname-only headword, etc.): role is `"Unknown"`.
2. If the headword explicitly names a role (`Vizier`, `Chancellor`, `Governor of the town`, `Standard-bearer`, `son of <King>`, `wife of <King>`, `Overseer of the Fields of Amun`, etc.):
   - `Vizier` → `"Vizier"`.
   - `Governor of the town, Vizier` (a standard Egyptian vizier title pair) → `"Vizier"`.
   - `Chancellor` → `"Official"`.
   - Other officer titles → `"Official"`.
   - `son of <King>` → `"Prince"`; `daughter of <King>` → `"Princess"`; `wife of <King>` → `"Queen"` unless rule 3 overrides.
3. If the headword gives cartouches AND the surrounding text treats the figure as royal (PM's "King's names" / "Queen as King"): role is `"King"` regardless of biological sex.
4. Otherwise default `"King"` for KV tombs (§ I.A is the royal-tomb section).

For hedged attributions (`Probably <NAME>`): treat as if `<NAME>` is the occupant per rule 2 or 4.

### `dynasty`, `sub_period`, `date_bce_approx_start`, `date_bce_approx_end`

**All `null`** for every row at this extraction stage. Phase A ruler-authority enrichment fills these. Do NOT supply from outside knowledge.

### `location_sub_area`

`West Valley` is the explicit flag PM uses; any other sub-area phrase PM literally prints. If PM's headword doesn't flag a sub-area, emit `null`. (None of the chunk-4 tombs are expected to carry a sub-area flag, but apply the rule if PM prints one.)

### `discovery_year`, `discoverer`

**`null`** for every row. `Excavated by <X>` clauses go in `notes_from_pm`, not in these fields.

### `is_unfinished`

`true` iff the literal word `Unfinished` (capital-U) appears in the headword block. Note: `uninscribed` (lowercase i, different word) means "no inscriptions identifying the occupant" — it does NOT set `is_unfinished=true`. The two concepts are distinct in PM.

### `shared_with_tombs`

List of `KV<N>` strings parsed from `See also Tomb N` / `See also Tombs N and M` in the headword block. Only numbered references. Informal references (`See also South Tomb, infra, p. N`) do not populate this list.

Note: running-header text like `Tombs 47, 48, and 55` or `Tombs 56 and 57` is a PAGE HEADER, not a `See also` clause — those are page-layout groupings, not explicit cross-references the agents should transcribe as `shared_with_tombs`. Only use `See also Tomb N` phrases inside the headword body.

### `notes_from_pm`

A short verbatim prose fragment from the headword block that doesn't fit any structured field. Capture things like:
- Biographical / role clauses: `Governor of the town, Vizier. Temp. Amenophis II.` (some clauses like "Temp. X" go here even when the role is already captured in `occupant_role`; the regnal-dating phrase is distinct).
- Attribution hedges: `Probably <KING>, formerly attributed to <OTHER>` or `Attributed to X by Y in Z`.
- PM-given nicknames for uninscribed tombs: `'Gold Tomb', uninscribed` style phrases; preserve PM's single-quote wording.
- Cross-tomb ownership notes: `(Also owner of Theb. tb. 29.)` — this names a TT (Theban Tomb) number for Vizier Amenemopet's private tomb; preserve verbatim.
- `Excavated by <X>` when it appears inside the headword block (before the first body sub-header).
- Usurpation / re-use phrases: `re-used by <NAME>`, `Usurped by <NAME>`.

Preserve PM's wording. Apply text-layer noise normalisation. Join distinct clauses with `". "` (chunk-1/2/3 convention) or `"; "` for tightly-coupled titles.

`null` when the headword has nothing beyond the name + cartouches + bibliographic ribbon.

### `source_citation`

Object with three fixed keys:

- `"edition"`: exactly `"PM I.2 2nd ed. 1964"`.
- `"section"`: exactly `"I.A"`.
- `"page"`: the printed page number on which the tomb's headword line sits. **Extract from the chunk text** — do NOT supply from memory. Use form-feed (`\f`) to identify physical pages, read the printed-page digit from the running header (`Tombs 47, 48, and 55 565`, `Tombs 56 and 57`, `Tombs 57 and 62`, or the verso-style `N VALLEY OF THE KINGS` headers). When the digit is OCR-mangled (e.g. `s66` for 566), derive via the offset: printed = physical + 458.

## Structural gotchas to watch

- **Shared `Finds` / `Objects in Cairo Museum` sections.** PM groups some tomb finds under a shared header when artifacts were recovered together (e.g. a running header like `Tombs 47, 48, and 55` announces a shared finds section). Object lists under such a shared header sit past the first body sub-header and are out of scope for headword extraction. Do NOT copy finds lists into any of the three tombs' `notes_from_pm`.
- **Layout headers vs cross-refs.** Page running headers like `Tombs 47, 48, and 55` or `Tombs 56 and 57` are PAGE-LAYOUT groupings, not `See also Tomb N` cross-references. Only populate `shared_with_tombs` from explicit `See also Tomb N` phrases inside the headword block.

## Pitfall summary (read LAST before running)

1. **5 rows expected**: {KV47, KV48, KV55, KV56, KV57}.
2. **Do NOT supply dynasty / BCE dates** from your knowledge.
3. **Do NOT over-modernise** occupant names. PM-verbatim spelling (`Merneptah-Siptah`, `Haremhab`, `Amenophis IV`, `Amenemopet`).
4. **Hedged attributions** go in `notes_from_pm` while the structured `occupant_name` stays clean (strip the `Probably` / `Attributed to` prefix).
5. **Uninscribed tombs** (whether PM uses `UNINSCRIBED` or a nicknamed form like `'X Tomb', uninscribed.`): `occupant_name=null`, `occupant_role="Unknown"`, PM's nickname (if any) captured verbatim in `notes_from_pm`.
6. **Page running headers like `Tombs 47, 48, and 55`** are layout headers, NOT `shared_with_tombs` sources.
7. **Cartouche garbage drops entirely**.
8. **`source_citation.page` comes from the chunk text**, not memory.
9. **Skip body prose** (Finds, Objects in Cairo Museum, Corridor headers, etc.) starting at the first sub-header.

## Report back

After writing the JSONL, output a one-paragraph report with:
- Row count (should be 5).
- Any row where you're unsure about a field, with the field name and your best-guess value.
- Any unexpected text-layer noise that this prompt doesn't already flag.

Stay under 150 words.
