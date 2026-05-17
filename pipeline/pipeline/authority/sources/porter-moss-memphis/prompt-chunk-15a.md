# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 15a

> **Chunk 15a (first half of CEMETERY EN ECHELON. SOUTH PART)** — Reisner-numbered G-series mastabas G 4911 through G 5230. PM III.1 physical pp.138–153 / printed pp.141–156. Chunk 15b picks up at G 5232 onwards (G-series through G 5560). Reisner+Junker Excavations. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-15a-p138-p153-en-echelon-south.txt` and produce a JSONL file with one structured row per **PM-headworded Reisner-numbered mastaba** in Cemetery en Echelon South Part (G 4911 → G 5230). The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–14 have already shipped (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — A. WEST FIELD** continuation, `CEMETERY EN ECHELON. SOUTH PART` banner (Reisner + Junker Excavations, Harvard-Boston + Akademie/Pelizaeus + Univ. Leipzig Expeditions; some tombs earlier by Schiaparelli for Turin and by Steindorff for the Sieglin Expedition).
- PM III.1 offset for this chunk: **printed = physical + 3** (verify in-chunk via the right-page running header `West Field <N>`).
- The chunk file covers physical pp.138–153 / printed pp.141–156. Per-page markers `=== PHYS PAGE N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens at physical p.138 with chunk-14 G 4860 overflow followed by the `CEMETERY EN ECHELON. SOUTH PART` banner. The first IN-SCOPE row begins at the banner, followed by `G 4911.`. Skip everything above the banner — it is chunk-14 overflow (G 4860 is already extracted).
- **Bottom boundary:** the chunk file ends at physical p.153. The last IN-SCOPE row is `G 5230` on physical p.152 (BABAF "sometimes called Khnembaf"). Chunk 15b will pick up with G 5232 on physical p.154.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk15a.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk15a.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk15a.jsonl`

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
  "cemetery": "Cemetery en Echelon South",
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

Same Reisner G-numbered convention as chunks 7/8/14. tomb_id `G<NUM>` (drop space).

## How to identify a row

Five shapes (same as chunks 7/8/14):

**Shape 1 — Named-primary headword.** `G <NUM>. <NAME IN CAPS> <Title cluster>. <Dating>.`

**Shape 2 — Bare-numeric headword.** `G <NUM>. <Dating>.` (no occupant name).

**Shape 3 — Bracketed Roman regnal.** `G <NUM>. <NAME [I]> <Title cluster>.` → drop brackets, append Roman. Examples in chunk 15a: `G 4940. SESHEMNUFER [I]`, `G 5170. SESHEMNUFER [III]` (pypdf may render `[III]` as `[111]`).

**Shape 4 — Joint-named twin headword.** `G <NUM>. <NAME1> and <NAME2> ...` — emit ONE row, `is_joint_burial: true` (only if PM names TWO occupants). NB: structural `G <NUM1> + <NUM2>` twin with ONE named occupant → `is_joint_burial: false`, second number in `tomb_aliases` (chunk-11 D80/80A + chunk-14 G4811 precedent). No such structural twins expected in chunk 15a.

**Shape 5 — Anonymous "NAME UNKNOWN, <descriptor>" headword.** Rare; same convention as chunk-13/14.

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per `G <NUM>` headword. Do NOT emit rows for:
- The `CEMETERY EN ECHELON. SOUTH PART` banner — section divider.
- The G 4860 row at the top of physical p.138 — chunk-14 overflow.
- Body-prose object mentions (statues, lintels, slabs, false-doors, drum-of-deceased, etc.).
- Chapel sub-features (`West wall.`, `Chapel.`, `Burial chamber.`, `Mortuary Chapel.`, `Pillared Hall.`, `Niche.`, `Serdab.`, `Entrance doorway.`, `False-door.`, `Drum`, `Lintel`, `Plan`, etc.).
- Excavator-photo / publication-reference lines (`REISNER`, `JUNKER`, `SMITH`, `JACQUET-GORDON`, `HORNEMANN`, `L. D.`, `STEINDORFF`, `Schiaparelli`, etc.).
- Cross-references to G-numbers in OTHER chunks (e.g., body-prose `G 5280`, `G 5270`, `G 5160`, `G 6020` mentions BEFORE you reach those headwords).

**Headword block ends** at the first sub-feature heading or museum-citation: `Mortuary Chapel.`, `Burial Chamber.`, `Chapel.`, `West wall.`, `North wall.`, `South wall.`, `East wall.`, `False-door.`, `Drum`, `Lintel`, `Plan <Roman>`, `Stone-built mastaba.`, `Brick-built mastaba.`, `Stone-cased mastaba.`, `Statue-group`, `Reserve-head`, `Pillared Hall.`, `Entrance doorway.`, `Niche.`, `Serdab.`, `Reserve-head`, or any prose line beginning with a museum-citation/publication token.

## Expected row count

Pre-extraction structural scan: PM prints ~14–17 Reisner-numbered headwords in physical pp.138–153 from G 4911 through G 5230. Mix of Shape-1 named-primary (majority) + a few Shape-2 bare-numeric (e.g., G 5190, G 5221) + 2 Shape-3 bracketed Roman (G 4940 SESHEMNUFER [I], G 5170 SESHEMNUFER [III]). **Total expected: ~14–17 rows (acceptable band 12–20).** If your final count is below 10 or above 22, re-read the chunk file.

## PM III.1 text-layer noise (chunk-15-relevant)

**Raised-ayin in occupant names.** Replace mid-name or leading raised-`a`/`c`/`'` glyphs with `ʿ` (U+02BF) and title-case. tomb_id is ASCII (drop ayin).

**Underdot-Ḥ glyph.** Apply on `ḥ`-root names per source-wide convention (chunks 8/9 precedent: Ḥathor, Snefruḥotp, Meryptaḥ, Neferḥerenptaḥ, Imḥotep, ʿAnkh-Ḥathor, Weḥemka, Washptaḥ, Kheriḥet, Irkaptaḥ, Meḥi).

**Macron-Ē on Re-deity-compound names.** Per chunks 4/8/10/11/13/14 precedent (Merenrēʿ I, Saḥurēʿ, Neuserrēʿ, Rēʿḥerka, Rēʿḥotp, Rēʿshepses, Rēʿʿankh). For this chunk: `DUAENREa` (G 5110) → `Duaenrēʿ`; `RAaWER` (G 5270) → `Rēʿwer` (Re-compound + ḥ-root applicable if `wer` has ḥ? *wr* doesn't have ḥ. So `Rēʿwer` only).

**Bracketed Roman regnal pypdf drift.** pypdf renders `[I]` correctly, but `[II]` may render as `[11]` and `[III]` may render as `[111]`. Normalise back to Roman: `[11]` → `[II]`, `[111]` → `[III]`. After normalisation, drop brackets and append the Roman in occupant_name: `Sheshemnufer III` (no brackets, Roman with space). The Reisner G-number alone is the tomb_id (e.g., `G5170`). Do NOT append the Roman to tomb_id for G-numbered tombs. The bracketed regnal Roman applies to occupant_name disambiguation only.

**`HetH` / `aankH` / similar cap-H rendering.** pypdf renders PM's underdot-Ḥ glyph as cap-H mid-word. Normalise per ḥ-root convention. Examples expected: `HetepHeres` → `Ḥetep-ḥeres` if applicable; `HetepHi` → `Ḥetep-ḥi`.

**`waab-priest` / `wad-priest` / `ma-priest` / `sma-priest` drift.** Source-wide ayin-normalisation: raw OCR `waab` or `wad` → `waʿb`. Also normalise `ma-priest` / `sma-priest` → `sm-priest` (PM-printed Egyptian *sm*-priest).

**`warbt` / `waabt` drift.** Normalise to `waʿbt`.

**`wrt Hts` drift.** Normalise to `wrt-ḥts` (royal-women title).

**`KAEMqED` (G 5040).** pypdf renders the Egyptian `KAEMQED` (qed is the *q* phoneme). Title-case `Kaemqed`. (Not a *ḥ*-root.)

**`sometimes called <ALT>` alt-name idiom.** PM `BABAF (sometimes called Khnembaf)` → `occupant_name: Babaf`, `occupant_alt_names: ["Khnembaf"]`. Parallel to `called <ALT>` and `good name <ALT>` patterns.

**`good name <ALT>`.** Chunk-3 LG 84 PAKAP good name WEHEBREc-EMAKHET precedent. Example in chunk 15: G 5550 NUFER good name IDU [I] (G 5550 is chunk-15b, listed here for cross-reference). The "good name" introduces an Egyptological alt-name.

**"Wife, <NAME>" body-prose preservation.** Per chunks 9-11/13/14 convention — capture wife in `co_occupants` + `co_occupant_roles` (`"Wife, <title>"` form). Same for `Father, <title>` / `Mother, <title>` / `Son, <title>` / parental clusters.

**"Probably parents" / "Probably son" hedged co-occupant.** Per chunk-14 G 4761 precedent, prefix `Parent (probably), <title>` etc.

## Field-by-field rules

- **`tomb_id`** — `G<NUM>` (drop space from PM).
- **`memphite_area`** — Always `"Giza"`.
- **`occupant_name`** — Title-cased with diacritics applied. `null` for Shape-2/5. For Shape-3 bracketed Roman, drop brackets and append Roman with space (e.g., `Sheshemnufer III`).
- **`occupant_alt_names`** — From `<NAME> good name <ALT>` / `<NAME> called <ALT>` / `<NAME> (sometimes called <ALT>)` idioms.
- **`tomb_aliases`** — Empty unless PM explicitly cross-references.
- **`co_occupants`** — Wife, parents, joint-named twins.
- **`co_occupant_roles`** — Length-coupled. `"Wife, <title>"`, `"Father, <title>"`, etc.
- **`is_joint_burial`** — `false` for all chunk-15a rows (no Shape-4 `and`-joined two-occupant headwords expected). Structural twins (none expected here) would also be `false` per chunk-14 G4811 precedent.
- **`occupant_role`** — Controlled vocab. `"Vizier"` for `Chief Justice and Vizier` (G 5170 SESHEMNUFER [III] is `Chief Justice and Vizier`). `"Prince"` for `King's son`. `"Princess"` for `King's daughter`. `"High Priest"` of any divinity. `"Royal Family"` only when PM gives explicit royal-blood genealogy (e.g., G 5230 BABAF — `Father (probably), Duaenrēʿ (tomb G 5110)` where Duaenrēʿ is `son of Khephren` per G 5110; the grandson-of-king genealogy qualifies). `Hereditary prince` is a rank token — without explicit royal genealogy it does NOT promote to Royal Family. Most named non-royal (including bare `Hereditary prince`) → `"Official"`. Bare-numeric Shape-2 → `"Unknown"`.
- **`dynasty`** — Roman→Arabic. `Dyn. IV` → `"4"`, `Dyn. V` → `"5"`, `Dyn. VI` → `"6"`. `Late Dyn. V or Dyn. VI` → `"6"` (range tail). `Temp. Khufu` → `"4"`. `Temp. Khephren to <ruler>` → `"4"` (start of range). `Temp. Menkaureʿ` → `"4"`. `Temp. Userkaf or later` → `"5"`. `Middle Dyn. V or later` → `"5"`. `null` only when PM gives no dating clue.
- **`sub_period`** / **`date_bce_*`** — `null`.
- **`cemetery`** — `"Cemetery en Echelon South"` for every row in chunk 15 (single banner; parallel to chunk-3 `"Central Field"` descriptor and chunk-8 `"G 2300"`/`"G 2400"`/`"G 2500"` cemetery-banner convention).
- **`discovery_year`** / **`discoverer`** — `null`.
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM HEADWORD literally contains the token.
- **`attribution_certainty`** — `"attested"` / `"probable"` / `"uncertain"` per usual rule.
- **`shared_with_tombs`** — Empty unless PM cross-references explicitly.
- **`notes_from_pm`** — Headword block prose (title + dating + cross-refs + wife clause + father/mother/son clause). **Drop** mastaba body trailer (`Stone-built mastaba.`, etc.) + excavator/section codes (`LG <N>`, `<Roman> of Junker`) + occupant name (already in occupant_name). Joint twin keeps `and <co-occupant>` clause per chunks 11/13/14 convention.
- **`source_citation`** — `{"page": <printed page>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}`. Page boundaries: physical p.138 = printed p.141, ..., physical p.153 = printed p.156.

## Report format

```
agent-<X>-chunk15a: <count> rows; <shape1>/<shape2>/<shape3>/<shape4>/<shape5> split; <anomalies or "none">
```

Under 100 words.
