# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 17a

> **Chunk 17a (first half of CEMETERY G 7000 East Field remainder, Reisner G-numbered)** — picks up where chunk 2 left off at G 7150. PM III.1 physical pp.188–196 / printed pp.191–199. Chunk 17b picks up at G 7550 onwards. Headlined by the Khufu royal-family core: Ḥarzedef (Dyn IV King's son), the multiple Meresʿankhs (Meresʿankh II at G 7410+7420, Meresʿankh III at G 7530+7540), ʿAnkh-haf the Vizier of Khephren at G 7510. Split into halves preemptively (50+ tombs total in the chunk-17 page range) parallel to chunk 14/15 halving pattern. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-17a-p188-p196-g7000-east-remainder-a.txt` and produce a JSONL file with one structured row per **PM-headworded Reisner-numbered mastaba** in the G 7152→G 7540 range. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–16 have already shipped (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — B. EAST FIELD** continuation, `CEMETERY G 7000` (Reisner Excavation, Harvard-Boston Expedition).
- PM III.1 offset for this chunk: **printed = physical + 3** (verify in-chunk via the right-page running header `East Field <N>` or `<N> GÎZA—NECROPOLIS`).
- The chunk file covers physical pp.188–196 / printed pp.191–199. Per-page markers `=== PHYS PAGE N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens at physical p.188 with `G 7152. SEKHEMaANKHPTAH`. Chunk 2 (already shipped) covered through G 7150 on physical p.187.
- **Bottom boundary:** the chunk file ends at physical p.196. Chunk 17b will pick up with G 7550 on physical p.197.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk17a.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk17a.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk17a.jsonl`

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
  "cemetery": "G 7000",
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

## How to identify a row

**Shape 1 — Named-primary headword.** Line `G <NUM>. <NAME IN CAPS> <Title cluster>. <Dating>.` Title-case the name with diacritics; `tomb_id: G<NUM>` (drop space).

**Shape 2 — Bare-numeric headword.** Line `G <NUM>.` (sometimes followed by body-prose dating clue, museum reference, or `(Exped. No. ...)` line). No occupant name. `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`. Apply chunks 6/8 body-attestation rule to derive `dynasty` from adjacent body-prose if PM prints a dating clue (e.g., `Dyn. V-VI.` → `"6"` per range-tail rule).

**Shape 3 — Bracketed-Roman regnal headword.** Line `G <NUM>. <NAME> [I]/[II]/[III] <title cluster>` (pypdf renders `[II]` as `[11]`, `[III]` as `[111]` — normalise back). Drop brackets and append the Roman with space in `occupant_name` (e.g., `Hetepheres II`). The Reisner G-number alone is the `tomb_id`. Hedge `(?)` after the regnal becomes `attribution_certainty: "probable"`.

**Shape 4 — Joint-named twin headword.** PM literal `G xxxx+yyyy. <NAME> <title cluster>.` — two G-numbers joined by `+` introducing ONE named occupant (the occupant is buried in the combined mastaba complex). Per chunk-14 G 4811+G 4812 ʿAnkhirptaḥ convention: emit **ONE row** with `tomb_id: G<xxxx>`, `tomb_aliases: ["G <yyyy>"]`, `occupant_name: <Name>`, `is_joint_burial: false` (multiple tomb numbers ≠ multiple occupants — `is_joint_burial` denotes multiple occupants of the same tomb, not multiple tomb numbers; see chunk-14 G 4811 round-1 Gemini fix).
- If PM ALSO prints a separate body-prose Shape-2 entry for `G yyyy.` (the second number repeated as its own headword to list body-prose object findspots), emit that as a SEPARATE Shape-2 row with `tomb_id: G<yyyy>`. PM's structure is: the `+`-joined line is the joint-named twin headword; subsequent standalone `G yyyy. <body prose>` lines are object-findspot subsidiaries.

**Shape 5 — Anonymous/range headword.** Line `G <NUM>-<NUM>.` (hyphenated range, e.g., `G 7244-6`) or `G <NUM>. <object body prose>`. Treat range-headwords (`G 7244-6.`) as a SINGLE Shape-2 row with `tomb_id: G<first-NUM>` and the range note in `tomb_aliases: ["G <NUM2>", "G <NUM3>"]` only if PM cross-references explicitly. Otherwise emit one row per the lowest number in the range.

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per:
- Each Shape-1, 2, 3, 4, 5 headword line in the page range G 7152→G 7540.

Do NOT emit rows for:
- Out-of-range headwords (G 7150 and below = chunk 2 territory; G 7550 and above = chunk 17b territory).
- Body-prose object mentions (statues, reliefs, slabs, false-doors, drum-of-deceased, ointment-slabs, lintel attributions) that lack a `G <NUM>.` headword line.
- Chapel sub-features (`Room I.`, `Burial Chamber.`, `Chapel.`, `False-door.`, `Plan <Roman>`, `Statue-group`, `Relief-fragments`, etc.).
- Excavator/publication-reference lines (`L. D.`, `REISNER`, `MARIETTE`, `JUNKER`, `DUNHAM`, `SIMPSON`, `SMITH`, `BOSTON`, `Cairo Mus.`, etc.).

**Headword block ends** at the first sub-feature heading: `Room I.`, `Burial Chamber.`, `Chapel.`, `False-door.`, `Plan <Roman>`, `Stone-built mastaba.`, `Statues.`, `Statue-group`, `Relief-fragments`, or any prose line beginning with a museum-citation/publication token.

## Expected row count

Pre-extraction structural scan: ~10 Shape-1 named-primary (G 7152 SEKHEMaANKHPTAH, G 7211 KAEMaANKH, G 7249 MENIB, G 7391 ITETI, G 7411 KAEMTHENENT, G 7510 aANKH-HAF, G 7550-onwards is chunk-17b) + ~5 Shape-4 joint-twin headwords (G 7210+7220, G 7330+7340, G 7410+7420, G 7430+7440, G 7530+7540) + 1 Shape-3 bracketed-Roman (G 7350 HETEPHERES [II] (?)) + ~10 Shape-2 bare-numeric (G 7220 body-prose, G 7244-6 range, G 7244, G 7248, G 7410 body, G 7420 body, G 7430 body, G 7450, G 7491, G 7524, G 7530 body, G 7540 body). **Total expected: ~22–28 rows (acceptable band 18–32).** If your final count falls outside that band, re-read the chunk file — you've either missed Shape-2 bare-numeric subsidiaries or emitted out-of-scope body-prose statues.

## PM III.1 text-layer noise (chunk-17a-relevant)

**Raised-ayin in occupant names.** Replace mid-name or leading raised-`a`/`c`/`'` glyphs with `ʿ` (U+02BF) and title-case. tomb_id is ASCII-only (drop ayin). PM uppercase `aANKH-HAF` → `ʿAnkh-ḥaf`.

**Underdot-Ḥ glyph.** Apply on `ḥ`-root names per source-wide convention (precedent: Ḥathor, Ḥeket, Ḥarzedef, Meḥu, Meḥyt, Snefruḥotp, Meryptaḥ, Neferḥerenptaḥ, Imḥotep, Ḥetepheres, ʿAnkh-Ḥathor, Weḥemka, Washptaḥ, Kheriḥet, Irkaptaḥ, Meḥi, Ptaḥiufni, Seshetḥotp, Neferbauptaḥ, Nikauḥathor). For this chunk: `HARZEDEF` → `Ḥarzedef` (ḥ-root *ḥr-ḏd.f*); `aANKH-HAF` → `ʿAnkh-ḥaf` (ḥ-root *ḥʿf*); `KAKHERPTAH` → `Kakherptaḥ` (out of range for 17a but a precedent); `HETEPHERES` → `Ḥetepḥeres` (double ḥ-root); `MERESaANKH` → `Meresʿankh` (no ḥ here, just ayin).

**Macron-Ē on Re-deity-compound names.** Per source-wide convention (Merenrēʿ I, Saḥurēʿ, Neferirkarēʿ, Neuserrēʿ, Rēʿḥerka, Rēʿḥotp, Rēʿshepses, Duaenrēʿ, Menkaurēʿ). Apply to any `<X>REa` token in the chunk.

**Bracketed Roman regnal pypdf drift.** `[I]` renders correctly. `[II]` may render as `[11]` or `[If]` (chunk-17a OCR has both). `[III]` may render as `[111]`. Normalise back to Roman, then drop brackets when appending to `occupant_name`.

**`+` joint-twin headword convention.** PM literal `G xxxx+yyyy. <NAME IN CAPS> <title cluster>.` See Shape 4 above. The `+` between Reisner numbers is PM's joint-mastaba notation.

**"Wife, <NAME>" body-prose preservation.** Per chunks 9-16 convention — capture wife in `co_occupants` + her title cluster in `co_occupant_roles` (`"Wife, <title>"` form). Same for `Father, <title>` / `Mother, <title>` / `Son, <title>` clusters. PM-faithful word-for-word title cluster.

**Royal-family occupant_role mapping.** `King's son [of his body]` → `Prince`. `King's daughter [of his body]` → `Princess`. `Hereditary prince` ALONE → `Official` (per chunk-15 G 5230 prompt update; Royal Family requires explicit royal-blood genealogy). `Hereditary prince` + `King's son` together → `Prince` (the King's son token wins). Chief Justice and Vizier → `Vizier`. `Prophet of <X>` (without `Greatest of` / `chief of` modifier) → `Official` per source-wide pattern (32 of 34 such rows in chunks 6-15 map to Official).

## Field-by-field rules

- **`tomb_id`** — `G<NUM>` (drop space from PM). For Shape-4 joint twin `G xxxx+yyyy`, tomb_id is `G<xxxx>` (the lower number) and `tomb_aliases: ["G <yyyy>"]`. For Shape-3 bracketed-Roman: G-number alone is tomb_id (no Roman appended).
- **`memphite_area`** — Always `"Giza"`.
- **`occupant_name`** — Title-cased with U+02BF ayin / underdot-Ḥ / macron-Ē applied. `null` for Shape-2 bare-numeric. For Shape-3 bracketed Roman, drop brackets and append Roman with space.
- **`occupant_alt_names`** — From `<NAME> called <ALT>` / `<NAME> good name <ALT>` idioms if present.
- **`tomb_aliases`** — For Shape-4 joint twin: `["G <yyyy>"]` (the second number). For LG-numbered tombs: `["LG <N>"]` per chunks 14-16 convention. Empty otherwise.
- **`co_occupants`** — Wife, parents, children per PM body-prose clauses. PM-faithful order. Apply diacritics.
- **`co_occupant_roles`** — Length-coupled with `co_occupants`. `"Wife, <title>"`, `"Father"`, `"Mother"` per chunks 9-16 convention. Preserve `, etc.` marker when PM prints it.
- **`is_joint_burial`** — `false` for all chunk-17a rows. Shape-4 joint-named TWINS are multiple tomb numbers (not multiple occupants) per chunk-14 G 4811 lesson.
- **`occupant_role`** — Controlled vocab per Royal-family mapping section above.
- **`dynasty`** — Roman→Arabic. `Dyn. IV` → `"4"`, `Dyn. V` → `"5"`, `Dyn. VI` → `"6"`. `Middle or late Dyn. IV` → `"4"`. `End of Dyn. IV` → `"4"`. `Temp. Khephren` → `"4"`. `Dyn. IV-V` → `"5"` (range tail). `null` only when PM gives no dating clue. For Shape-2 bare-numeric: `null` unless body-prose dating is printed adjacent to the headword.
- **`sub_period`** / **`date_bce_*`** — `null`.
- **`cemetery`** — `"G 7000"` for every row in chunk 17a (single CEMETERY G 7000 banner, continuation of chunk 2's coverage).
- **`discovery_year`** / **`discoverer`** — `null`.
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM HEADWORD literally contains the token.
- **`attribution_certainty`** — `"attested"` for clean Shape-1 named. `"probable"` for Shape-1 with `Probably <name>` hedge or Shape-3 with `(?)` hedge. `"uncertain"` for Shape-2 bare-numeric.
- **`shared_with_tombs`** — Empty for all chunk-17a rows.
- **`notes_from_pm`** — Headword block prose (title cluster + dating + parents/wife/father clauses). Drop mastaba body trailer (`Stone-built mastaba.`), LG codes (in `tomb_aliases`), `Plan <Roman>` references, sub-feature headings, museum-citation lines, publication references. For Shape-2 bare-numeric body-prose-only rows: the dating clue + adjacent body-prose object reference verbatim.
- **`source_citation`** — `{"page": <printed page>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}`. Use the right-page running header to verify per-row. Boundary rule: **printed = physical + 3**. Page boundaries in this chunk: physical p.188 = printed p.191, ..., physical p.196 = printed p.199.

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk17a: <count> rows; <shape1>/<shape2>/<shape3>/<shape4>/<shape5> split; <anomalies or "none">
```

Where shape1 = G-named primary, shape2 = G-bare-numeric, shape3 = bracketed-Roman, shape4 = joint-twin `+`, shape5 = range/anonymous. Under 100 words.
