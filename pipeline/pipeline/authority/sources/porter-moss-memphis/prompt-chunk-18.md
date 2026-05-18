# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 18

> **Eighteenth chunk drawn from PM Vol III** — Gîza § III.B EAST FIELD terminal LG-numbered cluster. Covers PM's `LG 63 → LG 80` named tombs that immediately follow G 7948 (the last G-numbered tomb in chunk 17b). PM III.1 physical pp.205–210 / printed pp.208–213. These tombs have LG (Lepsius) numbers but NO Reisner G-numbers — they are the trailing G 7000 East Field cluster grouped under the same PM section. **This chunk uses `LG<N>` tomb_id format** (precedent: chunk 3 `LG81`, `LG83`, `LG84`, `LG97`, `LG100`). The `cemetery` field stays `"G 7000"` since these tombs are within the CEMETERY G 7000 East Field banner. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-18-p205-p210-lg-cluster.txt` and produce a JSONL file with one structured row per **PM-headworded LG-numbered tomb** in the LG 63 → LG 80 range. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–17 have already shipped (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — B. EAST FIELD** terminal portion, `CEMETERY G 7000` cluster (Lepsius-numbered terminal sub-cluster).
- PM III.1 offset for this chunk: **printed = physical + 3**.
- The chunk file covers physical pp.205–210 / printed pp.208–213.
- **Top boundary:** chunk file opens at physical p.205 with body-prose from preceding G 7948 (chunk-17b territory, already shipped). The first IN-SCOPE row begins at `LG 63. KAEMNEFERT` on physical p.205. Skip anything above the `LG 63.` headword.
- **Bottom boundary:** chunk file ends at physical p.210 (just before the rock-cut tombs by Service des Antiquités sub-section). The last IN-SCOPE row is `LG 80. I P I`. The rock-cut tombs sub-section + Cemetery G I S + Quarry Cemetery + Central Field OK portion are chunk 19+ territory.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk18.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk18.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk18.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — 23 keys)

```json
{
  "tomb_id": "LG<N>",
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

## tomb_id convention — LG-prefix (precedent: chunk 3)

This chunk uses **LG-prefix tomb_id** (`LG<N>`, no space — drop the space PM prints between `LG` and the number). Parallel to chunk 3's `LG81`, `LG83`, `LG84`, `LG97`, `LG100` for the Central Field Saite intrusions + Khentkaus I tomb.

## How to identify a row

**Shape 1 — Named-primary headword.** Line `LG <N>. <NAME IN CAPS> <Title cluster>. <Dating>.` Title-case the name with diacritics. `tomb_id: LG<N>`. Examples in this chunk: `LG 63. KAEMNEFERT`, `LG 64. NESEMNAU`, `LG 68. ITETI`, etc.

**Shape 2 — Bare-numeric headword.** Line `LG <N>. <Dating>.` with no occupant name. `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`. Examples expected: `LG 66.` `LG 71.`

**Shape 5 — Anonymous "NAME UNCERTAIN" / "NAME LOST" headword.** PM `LG <N>. NAME UNCERTAIN <Title> <Dating>` or `LG <N>. NAME LOST, <descriptor>. <Dating>`. `occupant_name: null`, `attribution_certainty: "uncertain"`. Examples expected: `LG 65. NAME UNCERTAIN Elder of the house`.

**ROW-EMITTING vs OUT-OF-SCOPE.**

Emit one row per:
- Each `LG <N>. <NAME ...>` headword in the page range LG 63 → LG 80.

Do NOT emit rows for:
- Anything before `LG 63.` (chunk-17b territory: body-prose from G 7948 area).
- Anything after `LG 80.` (chunk-19+ territory: rock-cut tombs by Service des Antiquités, etc.).
- Body-prose object mentions, museum-citation lines, publication references.
- Chapel sub-features (`Room I.`, `North wall.`, `False-door.`, `Plan ...`).

**Headword block ends** at the first sub-feature heading: `Chapel.`, `Room I.`, `Room II.`, `North wall.`, `South wall.`, `False-door.`, `Stone-built mastaba.`, `Rock-cut tomb.`, `Plan ...`, or any prose line beginning with a museum-citation/publication token (`L. D.`, `REISNER`, `MARIETTE`, `JUNKER`, etc.).

## Expected row count

Pre-extraction structural scan: 17 LG-numbered tombs in the LG 63 → LG 80 range. Mostly Shape-1 named-primary, with 1-2 Shape-2 bare-numeric (LG 66, LG 71) and possibly 1 Shape-5 anonymous (LG 65 NAME UNCERTAIN). LG 75 corresponds to G 7948 (chunk 17b shipped it with tomb_aliases=["LG 75"]) — do NOT emit LG 75 as a separate row (it's already in reconciled). **Total expected: ~16 rows (acceptable band 13–19).**

## PM III.1 text-layer noise (chunk-18-relevant)

**Raised-ayin in occupant names.** Replace mid-name or leading raised-`a`/`c`/`'` glyphs with `ʿ` (U+02BF) and title-case. tomb_id is ASCII-only (drop ayin from descriptor — only LG-number digits).

**Underdot-Ḥ glyph.** Apply on `ḥ`-root names per source-wide convention (precedent: Ḥathor, Ḥeket, Meḥu, Meryptaḥ, Ḥetepheres, Imḥotep, Neferbauptaḥ, Akhtiḥotp). Apply if any chunk-18 headword carries an ḥ-root name (e.g., `NEFERSEFEKH-PTAH` → `Nefersefekh-ptaḥ` if PM prints the ḥ-root).

**Macron-Ē on Re-deity-compound names.** Per source-wide convention (Duaenrēʿ, Saḥurēʿ, Neferirkarēʿ, Menkaurēʿ). The OCR vowel rule applies: `REa` → `Rēʿ` (macron-Ē), but `RAa` → `Raʿ` (NO macron). Verify per OCR signature.

**`waab-priest` / `wad-priest` drift.** Source-wide ayin-normalisation: raw OCR `waab` or `wad` → `waʿb`.

**"Wife, <NAME>" body-prose preservation.** When PM prints a wife clause adjacent to the headword (before the body cue line), capture wife in `co_occupants` + her title cluster in `co_occupant_roles` (`"Wife, <title>"` form per chunks 9-17 convention). Preserve `, etc.` markers when PM prints them.

**LG 75 = G 7948 cross-reference.** LG 75 corresponds to the Reisner-numbered G 7948 (Raʿkhaʿef-ʿankh) that chunk 17b already shipped with `tomb_aliases: ["LG 75"]`. DO NOT emit a separate `LG75` row — that would create a duplicate. If PM's text in this page range mentions LG 75, skip it.

## Field-by-field rules

- **`tomb_id`** — `LG<N>` (drop space from `LG <N>`). E.g., PM `LG 63.` → `tomb_id: LG63`. NO Roman suffix; NO letter suffix expected in this range.
- **`memphite_area`** — Always `"Giza"`.
- **`occupant_name`** — Title-cased with U+02BF ayin / underdot-Ḥ / macron-Ē applied. `null` for Shape-2 bare-numeric and Shape-5 anonymous. For Shape-3 bracketed-Roman regnal (if any), drop brackets and append Roman with space.
- **`occupant_alt_names`** — Empty unless PM uses `<NAME> called <ALT>` / `<NAME> good name <ALT>` idiom.
- **`tomb_aliases`** — Empty for these LG-numbered tombs (no parallel G-number; the LG IS the primary identifier here).
- **`co_occupants`** — Wife, parents per body-prose clauses. Apply diacritics. PM-faithful order.
- **`co_occupant_roles`** — Length-coupled. `"Wife, <title>"`, `"Father"`, `"Mother"` per chunks 9-17 convention. Preserve `, etc.` markers.
- **`is_joint_burial`** — `false` unless PM HEADWORD prints `<NAME1> and <NAME2>` for two co-occupants of the same tomb (Shape 4). No Shape-4 expected in this chunk.
- **`occupant_role`** — Controlled vocab. `"Vizier"` for `Chief Justice and Vizier`. `"Prince"` for `King's son`. `"Princess"` for `King's daughter`. `"High Priest"` for `Greatest of the ḥm-nṯr` / `Greatest of the craftsmen` (wr-ḫrp-ḥmwt, the High Priest of Ptah at Memphis) / `chief of the ...`. `"Prophet of <X>"` alone is NOT `High Priest` — generic priestly title → `"Official"` (per source-wide 32-of-34 convention). Most named tombs in this chunk default to `"Official"` (King's waʿb-priest, Eye physician, Inspector of waʿb-priests, etc.). Shape-2 + Shape-5 → `"Unknown"`.
- **`dynasty`** — Roman→Arabic. `Dyn. V` → `"5"`, `Dyn. VI` → `"6"`. `Dyn. V-VI` → `"6"` (range tail). `Middle Dyn. V or Dyn. VI` → `"6"`. `null` only when PM gives no dating clue.
- **`sub_period`** / **`date_bce_*`** — `null`.
- **`cemetery`** — `"G 7000"` for every row in chunk 18 (the LG-numbered terminal cluster is grouped under the same CEMETERY G 7000 East Field banner — continuation of chunks 2 + 17).
- **`discovery_year`** / **`discoverer`** — `null`.
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM HEADWORD literally contains the token.
- **`attribution_certainty`** — `"attested"` for clean Shape-1 named-primary. `"uncertain"` for Shape-2 bare-numeric + Shape-5 anonymous. `"probable"` for `Probably <name>` hedges.
- **`shared_with_tombs`** — Empty unless PM cross-references explicitly.
- **`notes_from_pm`** — Headword block prose (title cluster + dating + parents/wife/father clauses). Drop occupant name, `Stone-built mastaba.` / `Rock-cut tomb.` body trailer, `Plan ...` references, sub-feature headings, museum-citation lines, publication references. For Shape-2 bare-numeric: only the dating marker if printed adjacent to the headword.
- **`source_citation`** — `{"page": <printed page>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}`. Boundary rule: **printed = physical + 3**. Page boundaries: phys p.205 = printed p.208, ..., phys p.210 = printed p.213.

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk18: <count> rows; <shape1>/<shape2>/<shape5> split; <anomalies or "none">
```

Where shape1 = LG-named primary, shape2 = LG-bare-numeric, shape5 = anonymous NAME UNCERTAIN/LOST. Under 100 words.
