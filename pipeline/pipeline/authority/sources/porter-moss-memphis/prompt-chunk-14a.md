# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 14a

> **Chunk 14a (first half of CEMETERY G 4000, Hemiunu cluster)** — Reisner-numbered G 4000-series mastabas G 4000 through G 4540. PM III.1 physical pp.119–127 / printed pp.122–130. Chunk 14b picks up at G 4560 onwards. Split into halves preemptively (50+ tombs total in Cemetery G 4000) parallel to the chunk-11 halving pattern. Headlined by **G 4000 HEMYUNU**, Khufu's Chief Justice and Vizier and chief architect of the Great Pyramid. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-14a-p119-p127-g4000.txt` and produce a JSONL file with one structured row per **PM-headworded Reisner-numbered mastaba** in Cemetery G 4000, G 4000 through G 4540, within the **A. WEST FIELD** section of `§ III. NECROPOLIS`. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–13 have already shipped (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — A. WEST FIELD** continuation, `CEMETERY G 4000` banner (Reisner Excavation, Harvard-Boston Expedition).
- PM III.1 offset for this chunk: **printed = physical + 3** (verify in-chunk via the right-page running header `West Field <N>`).
- The chunk file covers physical pp.119–127 / printed pp.122–130. Per-page markers `=== PHYS PAGE N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens at physical p.119 with end-of-prior-tomb body-prose from the Junker East chunk-13 territory. The first IN-SCOPE row begins at the `CEMETERY G 4000` banner mid-way down physical p.119, followed by `G 4000. HEMYUNU ...`. Skip everything above the banner — it is chunk-13 overflow and OUT OF SCOPE.
- **Bottom boundary:** the chunk file ends at physical p.127. The last row in the file is `G 4540` on physical p.127. Chunk 14b will pick up with G 4560 on physical p.128.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk14a.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk14a.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk14a.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — 23 keys, full schema)

```json
{
  "tomb_id": "G<NUM>" | "G<NUM><letter>",
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
  "cemetery": "G 4000",
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

## tomb_id convention

Reisner G-numbered cemetery. PM prints `G <NUM>` headwords. tomb_id format `G<NUM>` (drop the space). Examples:
- PM `G 4000.` → `G4000`
- PM `G 4351.` → `G4351` (pypdf may render as `G 435 I` — normalise trailing Roman `I` back to Arabic `1`)
- PM `G 4811 + 4812.` (joint mastaba) → `tomb_id: G4811`, `tomb_aliases: ["G 4812"]`, `is_joint_burial: true` (chunk-14b case; listed here for shape reference)

## How to identify a row

Five shapes:

**Shape 1 — Named-primary headword.** `G <NUM>. <NAME IN CAPS> <Title cluster>. <Dating>.`. Title-case occupant_name; tomb_id `G<NUM>`.

**Shape 2 — Bare-numeric headword.** `G <NUM>. <Dating>.` (no occupant name). `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`. Dynasty from dating marker.

**Shape 3 — Bracketed Roman regnal.** `G <NUM>. <NAME [I]> <Title cluster>.` — drop brackets, append Roman.

**Shape 4 — Joint-named twin headword.** `G <NUM1> + <NUM2>. <NAME1> ...` or `G <NUM>. <NAME1> and <NAME2> ...` — emit ONE row, `is_joint_burial: true`.

**Shape 5 — Anonymous "NAME UNKNOWN, <descriptor>" headword.** PM gives no occupant name. `occupant_name: null`, `attribution_certainty: "uncertain"`.

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per `G <NUM>` headword. Do NOT emit rows for:
- The `CEMETERY G 4000` banner — section divider.
- Body-prose object mentions (statues, lintels, slabs, false-doors, drum-of-deceased, reserve-heads, etc.).
- Chapel sub-features (`West wall.`, `Chapel.`, `Burial chamber.`, `Mortuary Chapel.`, `Pillared Hall.`, `Niche.`, `Serdab.`, etc.).
- Excavator-photo / publication-reference lines (`REISNER`, `JUNKER`, `SMITH`, `JACQUET-GORDON`, `HORNEMANN`, `L. D.`, etc.).
- Cross-references to G-numbers in OTHER cemeteries (e.g., body-prose `G 5280` mentions).

**Headword block ends** at the first sub-feature heading or museum-citation: `Mortuary Chapel.`, `Burial Chamber.`, `Chapel.`, `West wall.`, etc., `Stone-built mastaba.`, `Mud-brick mastaba.`, `Stone-cased mastaba.`, `Statue-group`, `Reserve-head`, or any prose line beginning with a museum-citation/publication token.

## Expected row count

Pre-extraction structural scan: PM prints ~22–26 Reisner-numbered headwords in physical pp.119–127. Mix of Shape-1 named-primary (majority) + ~8 Shape-2 bare-numeric (the dating-only headwords like G 4160, G 4260, G 4340, G 4350, G 4410, G 4430, G 4440, G 4522, G 4530, G 4540). **Total expected: ~22–26 rows (acceptable band 20–30).** If your final count is below 18 or above 32, re-read the chunk file.

## PM III.1 text-layer noise (chunk-14-relevant)

**Raised-ayin in occupant names.** Replace mid-name or leading raised-`a`/`c`/`'` glyphs with `ʿ` (U+02BF) and title-case. tomb_id is ASCII (drop ayin).

**Underdot-Ḥ glyph.** Apply on `ḥ`-root names per source-wide convention (precedent names: Ḥathor, Snefruḥotp, Meryptaḥ, Neferḥerenptaḥ, Imḥotep, ʿAnkh-Ḥathor, Weḥemka, Washptaḥ, Kheriḥet, Irkaptaḥ).

**Macron-Ē on Re-deity-compound names.** Per chunks 4/8/10/11/13 precedent (Merenrēʿ I, Saḥurēʿ, Neuserrēʿ, Rēʿḥerka, Rēʿḥotp, Rēʿshepses). For this chunk: `RAaHOTP` (G 4241) → `Rēʿḥotp` (combines all three diacritics).

**`HEMYUNU` (G 4000).** Egyptian *ḥmw-nw* (or *ḥm-iwnw* "servant of Iunu/Heliopolis"). Title-case `Hemyunu`. Apply underdot-Ḥ on initial ḥ → `Ḥemyunu` per source-wide ḥ-root convention.

**`aANKH-` raised-ayin.** PM prints leading `aANKH-` → `ʿAnkh-` after normalisation. Example: `aANKHEMREa` (G 4121) → `ʿAnkhemrēʿ` (raised-a ayin at start AND end; the trailing -REa is Re-deity → macron-Ē + ayin).

**`waab-priest` / `wad-priest` drift.** Source-wide ayin-normalisation: raw OCR `waab` or `wad` → `waʿb`.

**`G 4351` + `IMISETKAI` OCR drift.** pypdf may render `G 4351` as `G 435 I` and the occupant name `IMISETKAI` as `I M I SET KA I` (broken with spaces). Normalise the Roman `I` back to Arabic `1` in tomb_id; restore unspaced occupant name.

**`King's son of his body` / `King's daughter of his body` Royal-Family titles.** Per source-wide convention, OK royal-children titles map to `occupant_role: "Prince"` / `"Princess"`. (G 4000 HEMYUNU is `King's son` of an earlier king + Vizier; default to `"Vizier"` since Vizier outranks Prince in the controlled vocab.) `Queen` reserved for explicit OK royal consorts; `Royal Family` for those without a specific Prince/Princess title.

**"Wife, <NAME>" body-prose preservation.** Per chunks 9-11/13 convention — capture wife in `co_occupants` + `co_occupant_roles` (`"Wife, <title>"` form).

## Field-by-field rules

- **`tomb_id`** — `G<NUM>` (drop space from PM).
- **`memphite_area`** — Always `"Giza"`.
- **`occupant_name`** — Title-cased with diacritics applied. `null` for Shape-2/5.
- **`occupant_alt_names`** — From `<NAME> good name <ALT>` or `<NAME> called <ALT>` idioms.
- **`tomb_aliases`** — Empty for chunk-14a rows (joint twin G 4811 + 4812 is chunk 14b).
- **`co_occupants`** — Wife, parents, joint-named twins.
- **`co_occupant_roles`** — Length-coupled. `"Wife, <title>"`, `"Father, <title>"` form.
- **`is_joint_burial`** — `true` only for Shape-4 joint twins (none expected in chunk 14a; chunk 14b has G 4811 + 4812).
- **`occupant_role`** — Controlled vocab. `"Vizier"` for `Chief Justice and Vizier` (G 4000 HEMYUNU). `"Prince"` for `King's son`. `"Princess"` for `King's daughter`. `"High Priest"` of any divinity. Most named-non-royal → `"Official"`. Bare-numeric Shape-2 → `"Unknown"`.
- **`dynasty`** — Roman→Arabic. `Dyn. IV` → `"4"`, `Dyn. V` → `"5"`, `Dyn. VI` → `"6"`. `Middle or late Dyn. IV` → `"4"`. `Late Dyn. IV or Dyn. V` → `"5"` (range tail). `Temp. Khufu` → `"4"`. `Temp. Khephren or later` → `"4"`. `Temp. Userkaf or later` → `"5"`. `null` only when PM gives no dating clue.
- **`sub_period`** / **`date_bce_*`** — `null`.
- **`cemetery`** — `"G 4000"` for every row.
- **`discovery_year`** / **`discoverer`** — `null`.
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM HEADWORD literally contains the token.
- **`attribution_certainty`** — `"attested"` for clean named-primary; `"probable"` for hedge tokens; `"uncertain"` for `(?)` / Shape-2 bare-numeric / Shape-5 anonymous.
- **`shared_with_tombs`** — Empty unless PM cross-references explicitly.
- **`notes_from_pm`** — Headword block prose (title + dating + cross-refs + wife clause + father/mother clause). Mastaba-type body trailer dropped. Occupant name dropped (already in occupant_name).
- **`source_citation`** — `{"page": <printed page>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}`. Page boundaries: physical p.119 = printed p.122, ..., physical p.127 = printed p.130.

## Report format

```
agent-<X>-chunk14a: <count> rows; <shape1>/<shape2>/<shape3>/<shape4>/<shape5> split; <anomalies or "none">
```

Under 100 words.
