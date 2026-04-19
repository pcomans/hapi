# Extraction prompt — Porter & Moss Vol I (Theban Necropolis), Chunk 1: KV1–KV10

You are one of three independent extraction subagents. Your job: read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p37-p60.txt` and produce a JSONL file with one structured row per Theban tomb in this chunk. The other two agents see the same prompt and the same chunk; their outputs will be majority-voted by `merge.py` to produce `reconciled.jsonl`. Disagreements are resolved by majority vote per field.

This is a fact-extraction task on the Griffith Institute's published topographical bibliography. We extract: tomb number, occupant, dynasty, and headword-only metadata. We do NOT extract Moss's per-room descriptive prose.

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
  "occupant_role": "King",
  "dynasty": "20",
  "sub_period": null,
  "date_bce_approx_start": -1145,
  "date_bce_approx_end": -1137,
  "location_sub_area": null,
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "shared_with_tombs": [],
  "notes_from_pm": null,
  "source_citation": {"page": 511, "edition": "PM I.2 2nd ed. 1964", "section": "I.A"}
}
```

### Field-by-field rules

- **`tomb_id`** — `KV<N>` where `<N>` is the Arabic-numeral tomb number. PM's text-layer renders the leading `1.` of Tomb 1 as `I.` (Roman one); the headword name and surrounding context still establish it as Tomb 1. Disambiguate by sequence: tombs in this chunk are 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 in order. If you find more than 10 tomb numbers, you have over-matched (probably grabbed numbered scene refs `1, King...` as if they were tomb headers).

- **`valley`** — Always exactly the string `"Valley of the Kings"` for this chunk. Do not abbreviate.

- **`occupant_name`** — Conventional English form, titlecase, exactly as PM prints in the headword. Treat the text-layer noise:
  - `RAMESSES Ill` (capital I + lowercase L + lowercase L) → `Ramesses III` (Roman three).
  - `RAMESSES I I` → `Ramesses II`.
  - `MERNEPTAI;I` → `Merneptah`. PM consistently uses the spelling `Merneptah`; the `;I` is the text layer's rendering of an `H` glyph that printed weirdly.
  - `RAMESSES XI (formerly XII)` → `Ramesses XI` (the `(formerly XII)` is a parenthetical for `notes_from_pm`).
  - `AMENMESSE` → `Amenmesse`. PM's spelling — do NOT regularise to `Amenmesses`.
  - `RAMESSES VII` → `Ramesses VII`.
  Use the Roman numeral for the regnal-number suffix exactly as PM prints (after correcting the OCR drift): `I, II, III, IV, V, VI, VII, VIII, IX, X, XI`.

- **`occupant_alt_names`** — Alternative names PM gives parenthetically as part of the headword (NOT classical-traveller cross-refs like `Descr. Ant. 1st tomb west` — those go in `notes_from_pm`). Defaults to `[]`. For this chunk, KV9 (Ramesses VI) has been called "Memnon" in some 18th–19th c. sources, but PM does not state this in the headword — leave the array empty unless PM literally prints the alt-name in the headword block.

- **`occupant_role`** — Always exactly `"King"` for this chunk. KV1–KV10 are all kings.

- **`dynasty`** — String form of the Arabic dynasty number. PM does not always state it bare in the headword; you must supply it from the standard Egyptological consensus for each named king. For the chunk-1 kings:
  - `Ramesses VII` (KV1): Dyn `"20"`.
  - `Ramesses IV` (KV2): Dyn `"20"`.
  - `Ramesses III` (KV3): Dyn `"20"`.
  - `Ramesses XI` (KV4): Dyn `"20"`.
  - `Ramesses II` (KV5 and KV7): Dyn `"19"`.
  - `Ramesses IX` (KV6): Dyn `"20"`.
  - `Merneptah` (KV8): Dyn `"19"`.
  - `Ramesses VI` (KV9): Dyn `"20"`.
  - `Amenmesse` (KV10): Dyn `"19"`.

- **`sub_period`** — `null` for everything in this chunk (all are New Kingdom Dyn 19/20, no sub-period qualifier needed).

- **`date_bce_approx_start` / `date_bce_approx_end`** — Negative integers; the BCE convention. For this chunk, use the standard high-chronology consensus:
  - `Ramesses VII` (KV1): start `-1136`, end `-1129`.
  - `Ramesses IV` (KV2): start `-1153`, end `-1147`.
  - `Ramesses III` (KV3): start `-1184`, end `-1153`.
  - `Ramesses XI` (KV4): start `-1107`, end `-1077`.
  - `Ramesses II` (KV5 and KV7): start `-1279`, end `-1213`.
  - `Ramesses IX` (KV6): start `-1126`, end `-1108`.
  - `Merneptah` (KV8): start `-1213`, end `-1203`.
  - `Ramesses VI` (KV9): start `-1145`, end `-1137`.
  - `Amenmesse` (KV10): start `-1203`, end `-1200`.

- **`location_sub_area`** — `null` for KV in this chunk. PM does not identify East Valley vs West Valley vs Branch in the chunk-1 headwords for these tombs.

- **`discovery_year` / `discoverer`** — `null` unless PM literally prints the year and the discoverer's name in the headword block. (The body prose will name Belzoni, Loret, Carter, etc. but those refs sit in dropped material.)

- **`is_unfinished`** — `true` when the headword line literally contains the word `Unfinished`. For this chunk: KV3 (Ramesses III) and KV5 (Ramesses II) are flagged; KV4 (Ramesses XI) was also unfinished but PM's headword phrasing differs — only set `true` when the literal word appears.

- **`shared_with_tombs`** — When the headword has `See also Tomb N`, list the cross-referenced tombs as `KV<N>` strings. For this chunk:
  - KV3 (Ramesses III) headword: `See also Tomb 11.` → `["KV11"]`.
  - KV5 (Ramesses II) headword: `See also Tomb 7.` → `["KV7"]`.
  - KV7 (Ramesses II) headword: `See also Tomb 5.` → `["KV5"]`.
  - All others: `[]`.

- **`notes_from_pm`** — Short verbatim prose fragment from the headword that doesn't fit a structured field. Examples:
  - KV4 (Ramesses XI): `"formerly XII"` — PM's parenthetical regnal-number disambiguation.
  - KV9 (Ramesses VI): `"doorways in outer part usurped from"` — verbatim from the headword line; PM continues the sentence onto the next line (the doorways were usurped from another tomb's owner, named in the running prose).
  Otherwise: `null`.

- **`source_citation`** — Object with three fixed keys:
  - `"page"`: integer printed page number where the tomb's headword line appears. Per-tomb page mapping for chunk 1:
    - KV1: `495`. KV2: `497`. KV3: `500`. KV4: `501`. KV5: `501`. KV6: `501`. KV7: `505`. KV8: `509`. KV9: `511`. KV10: `517`.
  - `"edition"`: exactly the string `"PM I.2 2nd ed. 1964"`.
  - `"section"`: exactly the string `"I.A"` (Section I "Valley of the Kings", subsection A "Tombs").

## Edge-case handling

- **Cartouches** — PM prints the king's hieroglyphic cartouches inline immediately after the conventional English name (`RAMESSES IV (cartouche-1) (cartouche-2)`). The text layer renders these as garbage like `(0j~~-:=:) (0ffi J`. Drop them entirely. Do NOT try to recover the cartouche contents — they will be re-acquired from the king authority (pharaoh.se) in Phase A.

- **Egyptological ayin `ʿ` rendered as `c`** — PM's text layer outputs `Rec` for `Reʿ` and similar in king-titulary. This noise sits in dropped body prose, not in the conventional-English `occupant_name`. Don't normalise on your own — the centralised `fix_rows.py` will handle any that do reach structured fields.

- **Body prose detection** — every tomb's headword is followed by sub-headers like `Corridor A.`, `Corridor B.`, `Hall D.`, `Side-room L.`, `Sarcophagus Chamber K.`, `Approach.`, `Pillars.`, `Ceiling.`, `Finds`, `Plan, p. N.`. These mark the descriptive body prose — IGNORE everything from such a sub-header until the next tomb-number heading. Do NOT extract scene catalogs, plate references, or ceiling descriptions.

- **Numbered scene refs** — body prose contains lines like `(2) [1st ed. 4] Litany of Re c.` and `1, King receiving life from Rec-Harakhti`. These are scene IDs INSIDE a tomb, NOT new tombs. Never confuse `(N)` parentheticals or `N, ` comma-suffixed descriptions with tomb-number headers.

- **Tomb 5 has very little material** — PM gives essentially just the headword + a one-sentence `Remains of left jamb of entrance` note. Still emit a full row with all fields populated per the rules above.

- **Tombs 5 and 7 are both Ramesses II** — they are two distinct tombs both attributed to Ramesses II, cross-referenced by `See also Tomb 5` / `See also Tomb 7` headwords. Emit two rows, both with `occupant_name: "Ramesses II"`, both with `dynasty: "19"`, identical date fields, but different `tomb_id` and `source_citation.page` and `shared_with_tombs`.

## Pitfall summary (read this LAST before running)

1. **10 rows expected**, one per KV1–KV10. Not 9. Not 11. If your count is off, recheck — over-matching scene refs is the most common failure.
2. **`occupant_name` is titlecase, conventional English**, with the regnal-number suffix as a Roman numeral. NOT all-caps (PM headwords print all-caps for typesetting).
3. **`dynasty` is a STRING**, not an integer. `"19"` not `19`.
4. **Dates are negative integers**.
5. **Drop everything from `Corridor`/`Hall`/`Side-room`/`Approach`/`Pillars`/`Ceiling`/`Finds` headers onward** — those are descriptive prose, out of scope.
6. **Cartouches render as garbage** — drop them.
7. **`source_citation.page` is the PRINTED page** (495–518 range), not the physical PDF page (37–60 range).
8. **`shared_with_tombs` are the cross-referenced KV IDs**, not the body's `See also Tomb N` raw string.

## Report back

After writing the JSONL, output a one-paragraph report with:
- Row count (should be 10).
- Any row where you're unsure of a field assignment, with the field name and your best-guess value.
- Any unexpected text-layer noise that the chunk-1 prompt doesn't already call out.

Stay under 150 words.
