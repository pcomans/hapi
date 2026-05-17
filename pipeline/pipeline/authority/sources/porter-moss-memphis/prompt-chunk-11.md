# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 11

> **Eleventh chunk drawn from PM Vol III** — sixth Gîza West Field chunk. Covers PM's `STEINDORFF CEMETERY` (Georg Steindorff Excavation, University of Leipzig + Pelizaeus Expedition 1903-7). Physical pp.105–114 / printed pp.108–117. **D-numbered tombs are PRIMARY** in this chunk: PM prints `D. <NUM>. <NAME IN CAPS> <Title cluster>. <Dating>.` as the standard headword form, with `D. <NUM>` being Steindorff's own field numbering (NOT Mariette's Saqqâra D-prefix). Junker Cemetery (East) is OUT OF SCOPE — moves to chunk 12. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-11-p105-p114-steindorff.txt` and produce a JSONL file with one structured row per **PM-headworded mastaba** in the Steindorff Cemetery cluster. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–10 have already shipped (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — A. WEST FIELD** continuation, `STEINDORFF CEMETERY` (Steindorff Excavation, University of Leipzig + Pelizaeus Expedition 1903-7).
- PM III.1 offset for this chunk: **printed = physical + 3** (verify in-chunk via the right-page running header `West Field <N>`).
- The chunk file covers physical pp.105–114 / printed pp.108–117. Per-page markers `=== PHYS PAGE N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens with `STEINDORFF CEMETERY` banner on physical p.105 (file pre-trimmed before).
- **Bottom boundary:** the chunk file ends just before the `JUNKER CEMETERY (EAST)` banner (chunk-12 territory).
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk11.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk11.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk11.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — 23 keys, full schema)

```json
{
  "tomb_id": "D<NUM>" | "D<NUM><letter>" | "STN-<TitleCaseName>",
  "memphite_area": "Giza",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "King" | "Queen" | "Prince" | "Princess" | "Vizier" | "High Priest" | "Official" | "Royal Family" | "Unknown",
  "dynasty": "4" | "5" | "6" | null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "Steindorff",
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "is_uninscribed": false,
  "is_usurped": false,
  "attribution_certainty": "attested" | "probable" | "uncertain",
  "shared_with_tombs": [],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}
}
```

## tomb_id convention — NEW for chunk 11

This chunk introduces **D-numbered** tombs as the PRIMARY identifier scheme. PM prints `D. <NUM>` as the standalone headword form (Steindorff's own field numbering — NOT Mariette's Saqqâra D-prefix; this is a chunk-11 discovery via the revise-priors check that corrected the chunk-10 prompt's wrong attribution).

**D-number primary form (most chunk-11 rows):**
- PM headword `D. <NUM>. <NAME IN CAPS> <Title cluster>. <Dating>.` → `tomb_id: D<NUM>` (drop the period + space). Examples (abstract shape):
  - PM `D. <NUM>. <NAME>` → `tomb_id: D<NUM>`, `occupant_name: <Name>`
  - PM `D. <NUM><letter>. <NAME>` (suffix-letter form) → `tomb_id: D<NUM><letter>` (e.g., `D<NUM>B` for a `D. <NUM> B` form)
  - PM `D. <NUM1>/<NUM2>.` (twin-number form, parallel to chunk-10 S<NUM1>/<NUM2>) → `tomb_id: D<NUM1>` + `tomb_aliases: ["D <NUM2>"]` (PM-verbatim with the space)
  - PM `D. I.` (Roman numeral one — rare opening form for the first cemetery tomb) → `tomb_id: D1` (Arabic-normalised)
- For bare D-numbered headwords (no occupant name, only a dating marker) → Shape 2 below.

**STN- descriptor form (interstitial named tombs without a D-number):**
- A small subset of named Steindorff tombs are NOT given a D-number in PM (they appear between D-numbered headwords). For these, synthesise `tomb_id: STN-<TitleCaseAsciiName>` (drop ayin/underdot from the descriptor; they live in `occupant_name`). Examples are rare in this chunk — only handful of cases between D-numbered blocks.

**Bracketed Roman regnal Shape-3** (rare in this chunk): drop brackets, append Roman without space in tomb_id (`D<NUM>I`, `D<NUM>II`); with space in occupant_name (`<Name> I`, `<Name> II`).

**Joint-named twin headwords** (Shape 4 — common in this chunk): PM occasionally prints `D. <NUM>. <NAME1> ... and <NAME2> ... <Title cluster>. <Dating>.` — two occupants of one mastaba. Emit ONE row with `tomb_id: D<NUM>`, `is_joint_burial: true`, second occupant in `co_occupants` with role-string in `co_occupant_roles`.

## How to identify a row

Four shapes:

**Shape 1 — D-numbered named primary headword.** Line `D. <NUM>. <NAME IN CAPS> <Title cluster>. <Dating>.`. Title-case the name for `occupant_name`; tomb_id `D<NUM>`.

**Shape 2 — Bare D-numbered headword.** Line `D. <NUM>.` followed by only a dating marker (or even nothing more). NO occupant name. `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`. Dynasty from dating marker if present. Examples (shape illustration only): `D. <NUM>. Dyn. V-VI.` or just `D. <NUM>.`.

**Shape 3 — Bracketed Roman regnal D-numbered** (rare). `D. <NUM>. <NAME [I]> <Title cluster>.` — drop brackets, append Roman.

**Shape 4 — Joint-named twin headword.** `D. <NUM>. <NAME1> ... and <NAME2> ... <Title cluster>. <Dating>.` — emit ONE row, joint_burial = true.

**Shape 5 — STN- descriptor named** (interstitial, no D-number). Line `<NAME IN CAPS> <Title cluster>. <Dating>.` appears between D-numbered headwords, with no D-number on its own line. Title-case the name; tomb_id `STN-<TitleCaseAsciiName>`.

**ROW-EMITTING vs OUT-OF-SCOPE in this chunk.** Emit one row per:
- Each D-numbered headword (Shape 1, 2, 3, or 4).
- Each interstitial Shape-5 named tomb without a D-number.

Do NOT emit rows for:
- The `STEINDORFF CEMETERY` banner — section divider.
- The `JUNKER CEMETERY (EAST)` banner — chunk-12 territory; should not appear (pre-trimmed).
- Body-prose object mentions (statues, lintels, slabs, false-doors, drum-of-deceased, etc.).
- Chapel sub-features (`West wall.`, `North wall.`, `False-door.`, `Burial chamber.`, etc.).
- Excavator-photo / publication-reference lines (`BREASTED (Jr.)`, `HERMANN and SCHWAN`, `KAYSER`, `LANGE`, `IPPEL and ROEDER`, `MULLER`, `HORNEMANN`, `SENK`, `RANKE`, etc.).
- Person names in publication footers (`L. D.`, `Aeg. Inschr.`, `Ausf. Verz.`, etc.).

**Headword block ends** at the first sub-feature heading or museum-citation: `Mortuary Chapel.`, `Burial Chamber.`, `Chapel.`, `West wall.`, `North wall.`, `South wall.`, `East wall.`, `False-door.`, `Drum`, `Lintel`, `Plan <Roman>`, `Stone-built mastaba.`, `Brick-built mastaba.`, `Mud-brick mastaba.`, `Stone-cased mastaba.`, `Statue-group`, `Relief-fragments`, `Name from`, `Mostly brick-built mastabas.`, or any prose line beginning with a museum-citation/publication token (`Cairo Mus.`, `Hildesheim Mus.`, `Leipzig Mus.`, `Berlin Mus.`, `Vienna Mus.`, `London Mus.`, `Boston Mus.`, `Bryn Athyn`, `M.M.A.`, `JUNKER`, `REISNER`, `STEINDORFF`, `BREASTED`, `KAYSER`, `LANGE`, `IPPEL and ROEDER`, `HORNEMANN`, `BORCHARDT`).

## Expected row count

Pre-extraction structural scan: PM prints ~32 named D-numbered tombs + ~8 bare D-numbered headwords + ~3 interstitial named tombs without a D-number under the STEINDORFF CEMETERY banner. **Total expected: ~45 rows (acceptable band 40–55).** If your final count is below 35 or above 60, re-read the chunk file — you've either missed tombs or emitted out-of-scope body items / chapel sub-features.

## PM III.1 text-layer noise (chunk-11-relevant)

**Raised-ayin in occupant names.** Replace mid-name or leading raised-`a`/`c`/`'` glyphs with `ʿ` (U+02BF) and title-case. ASCII-only in `tomb_id` descriptor (STN-`<Name>` drops ayin; D-numbers are pure ASCII already).

**Underdot-Ḥ glyph.** Apply on `ḥ`-root names per source-wide convention (precedent names from prior chunks: Ḥathor, Meḥu, Meḥyt, Snefruḥotp, Meryptaḥ, Neferḥetpes, Neferḥi, Akhetmeḥu, Ḥetepniptaḥ, ʿAnkhirptaḥ, ʿAnkh-ḥathor).

**Macron-Ē on Re-deity-compound names.** Per chunks 4/8/10 precedent (Merenrēʿ I, Meryrēʿ-Meryptaḥʿankh, Saḥurēʿ, Neuserrēʿ, Rēʿ).

**"Wife, <NAME>" body-prose preservation.** When PM prints a wife clause adjacent to the D-numbered headword (before the body cue line), capture wife in `co_occupants` + her title cluster in `co_occupant_roles` (`"Wife, <title>"` form per chunks 9-10 convention); preserve the verbatim wife clause in `notes_from_pm`.

**"good name" alt-name idiom.** PM `<PRIMARY> good name <ALT>` → primary in `occupant_name`, alt in `occupant_alt_names`.

**"and" joint-named twin headword (Shape 4).** PM occasionally prints `D. <NUM>. <NAME1> and <NAME2> <Title cluster>.` for two occupants of one mastaba. Distinct from `Wife, <NAME>` body-prose wife notation. Joint-named twin → `is_joint_burial: true` AND `co_occupants` populated with the second name.

**`atw-official` rendering.** PM prints OK title `ʾtw` as `ATw-official` or `atw-official`. Role classification is `"Official"` regardless.

**`waab-priest` / `wad-priest` / `waʿb-priest` drift.** Source-wide ayin-normalisation: raw OCR `waab` or `wad` (the latter is OCR drift on raised-a) → `waʿb`. Per chunks 1/9/10 convention.

**D-number normalisation forms (chunk-11 specific):**
- `D. <NUM>` → `D<NUM>` (drop period and space).
- `D. <NUM><letter>` → `D<NUM><letter>` (e.g., `D. 15 B.` → `D15B`).
- `D. <NUM1>/<NUM2>` (twin-number) → `tomb_id: D<NUM1>` + `tomb_aliases: ["D <NUM2>"]`.
- `D. I.` (Roman one — rare opening form) → `D1` (Arabic-normalised).
- pypdf may render `D.` as `D ` (space instead of period) — normalise either form to `D<NUM>`.

## Field-by-field rules

- **`tomb_id`** — `D<NUM>` / `D<NUM><letter>` for D-numbered tombs (primary form, most rows). `STN-<TitleCaseAsciiName>` for interstitial named tombs without a D-number. ASCII descriptor; bracketed Roman appended without space.
- **`memphite_area`** — Always `"Giza"`.
- **`occupant_name`** — Title-cased with U+02BF ayin / underdot-ḥ / macron-Ē applied. `null` for Shape-2 bare-numeric. For Shape-1 with `name . . .` ellipsis-truncated PM form (e.g., `D. <NUM>. KHUFU . . ., King's waab-priest.`), capture the part before the ellipsis as `occupant_name` (`Khufu`) and note the truncation in `notes_from_pm`.
- **`occupant_alt_names`** — From `<NAME> good name <ALT>` idiom.
- **`tomb_aliases`** — Second number of twin-D-form; `LG <N>` cross-references; etc.
- **`co_occupants`** — Wife, parents, joint-named twins.
- **`co_occupant_roles`** — Length-coupled with `co_occupants`. `"Wife, <title>"` form per chunk-9/10 convention.
- **`is_joint_burial`** — `true` only for Shape-4 joint-named twin headwords.
- **`occupant_role`** — Controlled vocab. `"Vizier"` for Chief Justice and Vizier. `"High Priest"` of any divinity. Most named tombs in this chunk default to `"Official"` (Inspector, Overseer, Tutor, Director, Royal acquaintance, ka-servant, atw-official, waʿb-priest, wad-priest, Steward, Singer, Female steward, Prophet of <divinity>, Scribe, Carpenter of the Royal House, Secretary, etc.). Bare-numeric Shape-2 → `"Unknown"`.
- **`dynasty`** — Roman→Arabic. `Dyn. V` → `"5"`, `Dyn. VI` → `"6"`. `Dyn. V-VI` → `"6"` (range tail). `Late Old Kingdom.` → `"6"` (chunk-10 convention). `null` only when PM gives no dating clue.
- **`sub_period`** / **`date_bce_*`** — `null`.
- **`cemetery`** — `"Steindorff"` for every row in chunk 11 (single banner). Parallel to chunk-3's `"Central Field"` and chunk-10's `"Junker West"` descriptor convention.
- **`discovery_year`** / **`discoverer`** — `null` (excavator history is body-prose context, reserved for Phase-A enrichment).
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM HEADWORD literally contains the token.
- **`attribution_certainty`** — `"attested"` for clean named-primary; `"probable"` for hedge tokens (`Probably`, `Perhaps`); `"uncertain"` for `(?)` / Shape-2 bare-numeric.
- **`shared_with_tombs`** — Empty unless PM cross-references explicitly (e.g., `(tomb D <N>)`).
- **`notes_from_pm`** — Headword block prose (title + dating + cross-refs + wife clause). Mastaba-type body trailer dropped. Occupant name dropped (already in `occupant_name`). For Shape-2 bare-numeric, only the dating marker; pure-numeric (`D. <NUM>.`) → `notes_from_pm: null`.
- **`source_citation`** — `{"page": <printed page>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}`. Use the right-page running header to verify per-row.

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk11: <count> rows; <shape1>/<shape2>/<shape3>/<shape4>/<shape5> split; <anomalies or "none">
```

Where `<shape1>` = D-numbered named primary, `<shape2>` = bare D-numbered, `<shape3>` = bracketed-Roman-regnal D-numbered, `<shape4>` = joint-named twin D-numbered, `<shape5>` = STN- descriptor interstitial. Under 100 words.
