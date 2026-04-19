# Extraction prompt — Porter & Moss Vol I (Theban Necropolis), Chunk 2: KV11–KV20

You are one of three independent extraction subagents. Your job: read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p60-p90.txt` and produce a JSONL file with one structured row per Theban tomb in this chunk. The other two agents see the same prompt and the same chunk; their outputs will be majority-voted by `merge.py` to produce `reconciled.jsonl`.

This is a fact-extraction task on the Griffith Institute's published topographical bibliography. Extract: tomb number, occupant name, and headword-only metadata (the `Unfinished` flag, `See also Tomb N` cross-refs, classical aliases, page citation). Do NOT extract Moss's per-room descriptive prose. Do NOT supply dynasty or BCE dates from outside knowledge — those fields stay null and are filled in Phase A.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume I, Part 2: Royal Tombs and Smaller Cemeteries.* 2nd edition, Oxford 1964.
- Section: I. Valley of the Kings, A. Tombs.
- Printed page range: p.518–548. Physical PDF page range: p.60–90. Offset: physical = printed − 458.
- The chunk begins at the tail of physical p.60 (printed 518), which carries the **KV11** headword block after the end of KV10's body. This is a deliberate boundary choice so you have KV11's headword in the chunk text — the rest of p.60 is KV10 body (out of scope for this chunk).
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF. See `transcribe.md` § "Method deviation".

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-a-chunk2.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-b-chunk2.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-c-chunk2.jsonl`

(Whichever path the launching prompt tells you.)

One JSON object per line. Sort rows by tomb number (11, 12, 13, ..., 20). Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` so the output is deterministic and merge-friendly.

## Schema (per row)

Every row MUST have these keys; use `null` (not omitted, not empty string) for unknown values. Same schema as chunk 1 — see README.md for field semantics.

```json
{
  "tomb_id": "KV11",
  "valley": "Valley of the Kings",
  "occupant_name": "Ramesses III",
  "occupant_alt_names": ["Bruce's tomb", "the Harper's tomb"],
  "occupant_role": "King",
  "dynasty": null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "location_sub_area": null,
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "shared_with_tombs": ["KV3"],
  "notes_from_pm": null,
  "source_citation": {"page": 518, "edition": "PM I.2 2nd ed. 1964", "section": "I.A"}
}
```

## Field-by-field extraction rules

Every field is extracted from PM's HEADWORD BLOCK, never from the body prose. The headword block for tomb N starts at the line `N. NAME (cartouches) (parenthetical)` and ends at the first body sub-header (`Approach.`, `Entrance.`, `Corridor A.`, `Hall D.`, `Side-room K.`, `Pillars.`, `Ceiling.`, `Sarcophagus Chamber X.`, `Finds`, `Plan, p. N.`) OR at the next tomb-number heading. The bibliographic-references paragraph immediately after the headword (the one that lists `LEFEBURE, ...; CHAMP., ...; L. D. Text, ...`) is NOT body prose — it's part of the bibliographic ribbon and contains classical aliases / cross-refs you may need.

### `tomb_id`

`KV<N>` where `<N>` is the Arabic-numeral tomb number. PM's text-layer renders digits unreliably — the same tomb-number glyph may show up as `II` (Roman) or `11` (Arabic) depending on the font run. The headwords you should find in this chunk:

| tomb_id | Text-layer rendering of the leading number | Occupant (as PM prints) |
|---|---|---|
| KV11 | `II.` (Roman II) | `RAMESSES III` |
| KV12 | `I2.` | `UNINSCRIBED` |
| KV13 | `I 3·` or `I 3.` (with space split, middle-dot period) | `BAY` |
| KV14 | `I4.` | `TAUSERT` (usurped by `SETNAKHT`) |
| KV15 | `15.` | `SETHOS II` |
| KV16 | `16.` | `RAMESSES I` |
| KV17 | `17.` | `SETHOS I` |
| KV18 | `I8.` | `RAMESSES X (formerly XI)` |
| KV19 | `19.` | `RAC MESES-MENTUI;IIRKHOPSHEF` (= Ramesses-Mentuherkhepshef) |
| KV20 | `20.` | `I:IATSHEPSUT` (= Hatshepsut) |

10 rows expected, tomb_id KV11 through KV20 in order. **KV21 is absent from this PM section** — the text jumps from KV20 to KV22 (KV21 appears elsewhere in the volume per PM's organisation and is not part of this chunk). Do NOT emit a KV21 row. Do NOT emit a KV22 row — KV22's content begins on physical p.91, past the chunk boundary.

### `valley`

Always exactly the string `"Valley of the Kings"` for this chunk.

### `occupant_name`

Conventional English form, titlecase, exactly as PM prints in the headword (after correcting the OCR drift). Key text-layer noise in this chunk:

- `RAMESSES Ill` → `Ramesses III`.
- `I2. UNINSCRIBED` → `occupant_name = null` (the tomb has no occupant attested by PM).
- `I 3· BAY` → `Bay`. (The middle dot `·` in `I 3·` is the text layer's rendering of a regular period — ignore it.)
- `I4. TAUSERT ... Usurped by SETNAKHT` → `occupant_name = "Tausert"`. The usurpation detail goes in `notes_from_pm`, NOT in `occupant_alt_names` (Setnakht is a later usurper, not an alternative name for Tausert).
- `RAC MESES-MENTUI;IIRKHOPSHEF` → `Ramesses-Mentuherkhepshef`. The leading `RAC ` with space is the text layer's rendering of `RA<` (Egyptological ayin + space). Hyphenate the compound name.
- `I:IATSHEPSUT` → `Hatshepsut` (the `I:I` is the text layer's rendering of the underdot-H glyph for Ḥ).
- `MERNEPTAI;I` → `Merneptah` (same `I;I` → `H` rendering — appears in KV14's headword as usurpation note).
- For `RAMESSES X (formerly XI)` → `occupant_name = "Ramesses X"`; the `(formerly XI)` goes in `notes_from_pm`.

Use the Roman numeral for the regnal-number suffix exactly as PM prints (after OCR correction).

### `occupant_alt_names`

A list of alternative names PM gives in the headword block — typically as a parenthetical right after the cartouches, in single quotes.

- **KV11 (Ramesses III)**: headword begins `II. RAMESSES III (cartouches) (See also Tomb 3.) (Bruce's tomb, or the Harper's tomb. Descr. Ant. 5th tomb east, ...)`. The two classical-tradition nicknames in single quotes are `Bruce's tomb` and `the Harper's tomb` — capture both as `["Bruce's tomb", "the Harper's tomb"]`.
- **KV17 (Sethos I)**: headword contains `('Belzoni's tomb', CHAMPOLLION, No. 3, ...)` — the classical alias is `Belzoni's tomb`. Capture as `["Belzoni's tomb"]`.
- All other tombs in this chunk have no quoted classical alias in their headword — emit `[]`.

Do NOT capture `CHAMPOLLION, No. X` / `BuRTON, L` / `HAY, No. Y` style bibliographic numbering as alt names — those are classical-traveller cross-references, not alternative names for the occupant.

### `occupant_role`

Controlled vocabulary. Per-tomb in this chunk:
- KV11, KV14 (Tausert → `Queen`, see below), KV15, KV16, KV17, KV18, KV20 (Hatshepsut): `"King"` (Tausert and Hatshepsut both ruled as king; PM's emphasis on `as King` for Hatshepsut's sarcophagus confirms).
- KV12 (uninscribed): `"Unknown"`.
- KV13 (Bay, Chancellor): `"Official"`.
- KV19 (Ramesses-Mentuherkhepshef, "son of Ramesses IX"): `"Prince"`.

Rationale on the edge cases:
- **KV14 Tausert**: although she was originally queen consort of Sethos II, the tomb is her tomb-as-ruling-king (Dyn 19 end, reigned 1188–1186 BCE). PM's headword explicitly includes her cartouches. Record `occupant_role: "King"` — the tomb is a royal king's tomb, not a queen's.
- **KV20 Hatshepsut**: likewise ruled as King. The headword's `(L. D. Text and WILKINSON, No. 20, BuRTON, R.)` is the only biblio — her role is King.
- **KV19 Ramesses-Mentuherkhepshef**: the headword literally reads `son of Ramesses IX`. A royal son who never reigned — role is `Prince`, not `King`. The "son of Ramesses IX" phrase itself does NOT go into `occupant_alt_names` or `occupant_name` — it's a relational note that belongs in `notes_from_pm`.

### `dynasty`

**`null`** for every row in this chunk. PM's headwords do NOT print dynasty. Phase A king-authority enrichment (pharaoh.se) fills this. Do NOT supply dynasty from your own knowledge.

### `sub_period`

`null` for everything in this chunk.

### `date_bce_approx_start` / `date_bce_approx_end`

**`null`** for every row in this chunk. Phase A fills these.

### `location_sub_area`

`null` for every row in this chunk. PM's KV section does not subdivide into East / West Valley at the headword level for KV11–KV20. (KV23 Ay is marked `West Valley` at the headword but that's outside this chunk.)

### `discovery_year` / `discoverer`

`null` for every row in this chunk. PM mentions `Belzoni`, `Carter`, `Davis`, `Loret`, `Champollion`, `Wilkinson` in bibliographic ribbons as publication references, not as statements of who discovered the tomb. Do not infer discoverer from the ribbon. (The phrase `Excavated by Belzoni` sometimes appears in the body prose — that IS discoverer info, but it sits past the first body sub-header and is out of scope for the headword-only rule.)

### `is_unfinished`

`true` if the literal word `Unfinished` appears in the headword block (typically in the parenthetical right after the cartouches, or after the bibliographic ribbon before `Plan, p. N.`).

In this chunk: **KV18 Ramesses X** has `Unfinished.` in the headword — set `true`. Others are false unless you find the literal word.

### `shared_with_tombs`

A list of `KV<N>` strings parsed from any `See also Tomb N` (or `See also Tombs N and M`) phrase in the headword block.

- **KV11**: headword has `(See also Tomb 3.)` → `["KV3"]`.
- **KV20**: headword has `See also South Tomb, infra, p. ...` — that `South Tomb` is an informal reference, NOT a numbered KV. Do NOT expand it to a `KV<N>` — emit `[]` for KV20.
- Others: `[]` unless an explicit `See also Tomb N` appears.

### `notes_from_pm`

A short verbatim prose fragment from the headword block that doesn't fit a structured field. Preserve the EXACT PM wording (post OCR correction). Apply titlecase to royal names to match `occupant_name` casing. Examples specific to this chunk:

- **KV14 Tausert**: `"Usurped by Setnakht. Originally queen of Sethos II."` — combine the usurpation note with the "wife of Sethos II" biographical note. Use the exact wording PM provides, normalised: PM says `wife of Sethos Il. Usurped by SETNAKHT`. Render as `wife of Sethos II. Usurped by Setnakht`. (Capitalise `Sethos II` to normalise the text-layer `Il` = Roman II, and titlecase `Setnakht` from PM's `SETNAKHT` small-caps.)
- **KV18 Ramesses X**: `"formerly XI"` (the parenthetical from the headword).
- **KV19 Ramesses-Mentuherkhepshef**: `"son of Ramesses IX"`.

Otherwise `null`. Do not invent notes. Do not expand abbreviations. Do not copy bibliographic references.

### `source_citation`

Object with three fixed keys. **The `page` value is extracted from the chunk text — DO NOT supply from a hardcoded table.**

1. The chunk file is divided into physical pages by the form-feed character (`\f`, ASCII 12, `chr(12)`). Each page starts with a running header that contains the printed page number (e.g. `Tomb II 519` or `Tombs I7 and I8 545` at the top, or `518 VALLEY OF THE KINGS` / `534 V ALLEY OF THE KINGS` for verso-pages).
2. To find the printed page for a tomb's headword: locate the headword line (e.g. `I2. UNINSCRIBED`) in the chunk text, identify which form-feed-delimited physical page it sits on, and read the printed page number from that page's running header.
3. Cross-check: physical page = printed page − 458. The chunk starts at physical page 60 (= printed page 518).
4. Use the printed page number from the running header. **Do NOT guess; do NOT supply from outside knowledge.** If a headword is at the tail of one page and its bibliographic ribbon continues onto the next, use the page where the **headword line itself** appears.

The other two keys are fixed:
- `"edition"`: exactly the string `"PM I.2 2nd ed. 1964"`.
- `"section"`: exactly the string `"I.A"` (Section I "Valley of the Kings", subsection A "Tombs").

## Edge-case handling

- **Cartouches** — drop entirely. Cartouche garbage is `(0E:'l~] ( 0 ffi ~t l]`, `(~~~::~U`, etc. The titlecase English name before the cartouches is the canonical occupant.
- **Egyptological ayin `ʿ` rendered as `c`** — PM's text layer outputs `Rec` for `Reʿ` and similar. This typically sits in body prose, not in the headword. `fix_rows.py` applies normalisations centrally.
- **`I:I` → `Ḥ`** — PM's underdot-H glyph renders as `I:I` in the text layer (see `I:IATSHEPSUT`, `MERNEPTAI;I`). In conventional English names, drop the underdot entirely: `Hatshepsut`, `Merneptah`, `Harakhti`, `Hathor`. Standard Egyptological transliteration would use the underdot; PM's conventional-English-name convention (and this extract's) does not.
- **Body prose detection** — every tomb's headword is followed by sub-headers like `Approach.`, `Entrance.`, `First Corridor.`, `Corridor A.`, `Hall D.`, `Side-room L.`, `Sarcophagus Chamber H.`, `Pillars.`, `Ceiling.`, `Finds`, `Plan, p. N.`. These mark the descriptive body prose — IGNORE everything from such a sub-header until the next tomb-number heading. The ONE exception is the `Finds` section after KV14 which covers `Tombs II, I2, I3, and I4` jointly — that's still body prose, skip it.
- **Numbered scene refs** — body prose contains lines like `(I) [Ist ed. I] Outer lintel` and `I, King receives life from J:Iatl;wr`. These are scene IDs INSIDE a tomb, NOT new tombs.
- **KV12 has very little material** — PM gives essentially just the headword + a very short bibliographic ribbon. Still emit a full row with `occupant_name: null` and `occupant_role: "Unknown"`.
- **KV20's bibliographic ribbon continues past p.88** — the sarcophagus description on p.89 (printed 547) is body prose under the `Sarcophagus Chamber.` sub-header. KV20's headword itself is on p.88, so `source_citation.page = 546`.

## Pitfall summary (read this LAST before running)

1. **10 rows expected**, one per KV11–KV20. No KV21. No KV22. If your count is off, recheck — under-matching is the failure mode this time (KV11's headword is on p.60 which is also full of KV10 body; KV13 is very short; KV21 is absent).
2. **`occupant_name` is titlecase, conventional English**, with the regnal-number suffix as a Roman numeral. Normalise `I:I` → `H`, `Il` → `II` (Roman), drop the underdot.
3. **KV12's `occupant_name` is `null`**, not a placeholder string. `UNINSCRIBED` is PM's headword word, but the tomb has no occupant.
4. **KV14's `occupant_name` is `"Tausert"`** (the original royal occupant, who ruled as King). The `"Usurped by Setnakht"` fact goes in `notes_from_pm`.
5. **KV19's `occupant_role` is `"Prince"`** (never reigned; was royal son of Ramesses IX).
6. **KV20's `shared_with_tombs` is `[]`** — the `See also South Tomb` in the headword is an informal reference, not a numbered cross-ref.
7. **`dynasty`, `date_bce_approx_*` are null** — Phase A king-authority enrichment fills them.
8. **`source_citation.page` comes from the chunk text running header**, not from a hardcoded table.
9. **Drop everything from `Approach`/`Entrance`/`First Corridor`/`Corridor`/`Hall`/`Side-room`/`Pillars`/`Ceiling`/`Sarcophagus Chamber`/`Finds`/`Plan, p.` headers onward** — those are descriptive prose, out of scope.
10. **`KV11`'s headword sits at the bottom of p.60** (printed 518). The page's running header is `518 VALLEY OF THE KINGS`. Set `source_citation.page = 518`.

## Report back

After writing the JSONL, output a one-paragraph report with:
- Row count (should be 10).
- Any row where you're unsure of a field assignment, with the field name and your best-guess value.
- Any unexpected text-layer noise that the chunk-2 prompt doesn't already call out.

Stay under 150 words.
