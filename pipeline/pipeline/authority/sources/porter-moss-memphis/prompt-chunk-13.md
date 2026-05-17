# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 13

> **Thirteenth chunk drawn from PM Vol III** — seventh Gîza West Field chunk. Covers PM's `JUNKER CEMETERY (EAST)` (Junker Excavation, Akademie der Wissenschaften in Wien + Pelizaeus-Museum Hildesheim + University of Leipzig). Physical pp.115–118 / printed pp.118–121. Parallel structure to chunk 10 (Junker Cemetery WEST): named-tomb cluster without Reisner G-numbers. Uses **JKE- descriptor convention** (parallel to chunk-10's JKR-). This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-13-p115-p118-junker-east.txt` and produce a JSONL file with one structured row per **PM-headworded named mastaba** in the Junker Cemetery (East) cluster. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–12 have already shipped (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — A. WEST FIELD** continuation, `JUNKER CEMETERY (EAST)` (Junker Excavation, Akademie der Wissenschaften in Wien + Pelizaeus-Museum Hildesheim + University of Leipzig).
- PM III.1 offset for this chunk: **printed = physical + 3** (verify in-chunk via the right-page running header `West Field <N>` or `<N> GÎZA—NECROPOLIS`).
- The chunk file covers physical pp.115–118 / printed pp.118–121. Per-page markers `=== PHYS PAGE N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens with end-of-prior-tomb body-prose on physical p.115, followed by the `JUNKER CEMETERY (EAST)` banner mid-page.
- **Bottom boundary:** the chunk file ends mid-content on physical p.118 (next chunk 14 will pick up with CEMETERY G 4000 banner).
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk13.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk13.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk13.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — 23 keys, full schema)

```json
{
  "tomb_id": "JKE-<TitleCaseName>" | "S<NUM>",
  "memphite_area": "Giza",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "King" | "Queen" | "Prince" | "Princess" | "Vizier" | "High Priest" | "Official" | "Royal Family" | "Unknown",
  "dynasty": "5" | "6" | null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "Junker East",
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

## tomb_id convention — NEW for chunk 13

This chunk uses **JKE- descriptor** (parallel to chunk-10's JKR-). The Junker Cemetery (East) named tombs have NO Reisner G-number — PM prints the all-caps occupant name as the headword, with title cluster trailing.

**JKE- descriptor form (most chunk-13 rows):**
- PM headword `<NAME IN CAPS> <Title cluster>. <Dating>.` → `tomb_id: JKE-<TitleCaseAsciiName>`, `occupant_name: <Name>` with diacritics applied (ayin, underdot-Ḥ, macron-Ē).
- Descriptor is ASCII-only: drop ayin / underdot / macron from the descriptor; they live in `occupant_name`. Examples:
  - PM `NIaANKH-HATHOR` → `tomb_id: JKE-NiankhHathor`, `occupant_name: Niʿankh-Ḥathor`
  - PM `MERUKA` → `tomb_id: JKE-Meruka`, `occupant_name: Meruka`

**S-number form (rare in this chunk):**
- PM `S <NUM>. Dyn. <Roman>.` → `tomb_id: S<NUM>` (drop space), `occupant_name: null` (Shape-2 bare-numeric).
- These are Steindorff-style S-numbered tombs that appear within the Junker East banner (PM groups them topographically with the Junker East cluster). Per chunk-10 convention, S-numbers go in their own family (rank 4 in AREA_ORDER), not under JKE-.

**Anonymous-named form:**
- PM `NAME UNKNOWN, <descriptor>` → `tomb_id: JKE-<DescriptorTitleCase>` (e.g., `JKE-AnonCompanion` for the smr-N.N. anonymous "Companion" tomb). `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`.

**Joint-named twin headword (Shape 4):**
- PM `<NAME1> and <NAME2> <Title cluster>. <Dating>.` → ONE row, `tomb_id: JKE-<TitleCase first occupant>`, `is_joint_burial: true`, second occupant in `co_occupants`.

## How to identify a row

Five shapes:

**Shape 1 — Named-primary descriptor headword.** Line `<NAME IN CAPS> <Title cluster>. <Dating>.`. Title-case the name for `occupant_name`; tomb_id `JKE-<TitleCaseAsciiName>`.

**Shape 2 — S-numbered Steindorff-style bare-numeric.** Line `S <NUM>. <Dating>.` followed by `Stone-built mastaba.` body trailer. NO occupant name. `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`.

**Shape 3 — Bracketed Roman regnal** (rare in this chunk). `<NAME [I]> <Title cluster>.` — drop brackets, append Roman.

**Shape 4 — Joint-named twin headword.** `<NAME1> and <NAME2> <Title cluster>. <Dating>.` — emit ONE row, joint_burial = true.

**Shape 5 — Anonymous "NAME UNKNOWN, <descriptor>" headword.** PM gives no occupant name, only a descriptor. `tomb_id: JKE-<AnonDescriptor>`, `occupant_name: null`.

**ROW-EMITTING vs OUT-OF-SCOPE in this chunk.** Emit one row per:
- Each Shape-1 named-primary headword.
- Each Shape-2 S-numbered bare-numeric headword.
- Each Shape-4 joint twin (one row, joint_burial = true).
- Each Shape-5 anonymous "NAME UNKNOWN" headword.

Do NOT emit rows for:
- The `JUNKER CEMETERY (EAST)` banner — section divider.
- The `CEMETERY G 4000` banner — chunk-14 territory (should not appear).
- Body-prose object mentions (statues, lintels, slabs, false-doors, drum-of-deceased, etc.).
- Chapel sub-features (`West wall.`, `North wall.`, `False-door.`, `Burial chamber.`, `Chapel.`, `Entrance doorway.`, etc.).
- Excavator-photo / publication-reference lines (`HORNEMANN`, `JUNKER`, `FISCHER`, `KAYSER`, `LANGE`, `IPPEL and ROEDER`, `MULLER`, `SENK`, `RANKE`, `BREASTED`, `STEINDORFF`, `HERMANN and SCHWAN`, etc.).
- Stray-find "Finds from area south of tombs G 2015 and 2015b" body block — list of object findspots, not a headworded tomb.
- "Lintel and drum of false-door of Nensezerkai" or similar object-attribution lines for sub-features lacking their own tomb headword.

**Headword block ends** at the first sub-feature heading or museum-citation: `Mortuary Chapel.`, `Burial Chamber.`, `Chapel.`, `West wall.`, `North wall.`, `South wall.`, `East wall.`, `False-door.`, `Drum`, `Lintel`, `Plan <Roman>`, `Stone-built mastaba.`, `Brick-built mastaba.`, `Statue-group`, `Relief-fragments`, `Name from`, `Pillared Hall.`, `Entrance doorway.`, `Niche.`, `Serdab.`, `Statues.`, or any prose line beginning with a museum-citation/publication token (`Cairo Mus.`, `Hildesheim Mus.`, `Leipzig Mus.`, `Berlin Mus.`, `Vienna Mus.`, `JUNKER`, `REISNER`, `STEINDORFF`, `KAYSER`, `LANGE`, `IPPEL and ROEDER`, `HORNEMANN`, `BORCHARDT`).

## Expected row count

Pre-extraction structural scan: PM prints ~13 Shape-1 named-primary tombs + 1 Shape-2 S-numbered (S 2411) + 1 Shape-4 joint (Nikaukhnum + Neferesris) + 1 Shape-5 anonymous (NAME UNKNOWN Companion). **Total expected: ~13–16 rows (acceptable band 11–18).** If your final count is below 10 or above 20, re-read the chunk file — you've either missed tombs or emitted out-of-scope body items / chapel sub-features.

## PM III.1 text-layer noise (chunk-13-relevant)

**Raised-ayin in occupant names.** Replace mid-name or leading raised-`a`/`c`/`'` glyphs with `ʿ` (U+02BF) and title-case. ASCII-only in `tomb_id` descriptor (JKE-`<Name>` drops ayin).

**Underdot-Ḥ glyph.** Apply on `ḥ`-root names per source-wide convention (precedent names from prior chunks: Ḥathor, Meḥu, Meḥyt, Snefruḥotp, Meryptaḥ, Neferḥetpes, Neferḥi, Akhetmeḥu, Ḥetepniptaḥ, ʿAnkhirptaḥ, ʿAnkh-Ḥathor, Weḥemka, Kheriḥet, Irkaptaḥ, Washptaḥ, Imḥotep, Neferḥerenptaḥ). For this chunk, `NIaANKH-HATHOR` carries underdot-Ḥ on the `Ḥathor` root → `Niʿankh-Ḥathor`. NB: `NepeHkau` appears in the chunk text only as a body-prose object mention (double-statue findspot south of tombs G 2015 and 2015b, NOT a tomb headword) — it would normalise to `Nepeḥkau` IF you ever emit it, but it is out of scope for this chunk; do not emit a row for it.

**Macron-Ē on Re-deity-compound names.** Per chunks 4/8/10/11 precedent (Merenrēʿ I, Meryrēʿ-Meryptaḥʿankh, Saḥurēʿ, Neuserrēʿ, Rēʿ, Rēʿḥerka, Rēʿḥotp, Rēʿshepses). Unlikely to occur in this chunk, but apply if present.

**"Wife, <NAME>" body-prose preservation.** When PM prints a wife clause adjacent to the headword (before the body cue line), capture wife in `co_occupants` + her title cluster in `co_occupant_roles` (`"Wife, <title>"` form per chunks 9-11 convention); preserve the verbatim wife clause in `notes_from_pm`.

**"and" joint-named twin headword (Shape 4).** PM occasionally prints `<NAME1> and <NAME2> <Title cluster>.` for two occupants of one mastaba. Distinct from `Wife, <NAME>` body-prose wife notation. Joint-named twin → `is_joint_burial: true` AND `co_occupants` populated with the second name.

**`waab-priest` / `wad-priest` / `waʿb-priest` drift.** Source-wide ayin-normalisation: raw OCR `waab` or `wad` (the latter is OCR drift on raised-a) → `waʿb`. Per chunks 1/9/10/11 convention.

**`mjtrt` typography.** Female OK title appears as `mjtrt` in PM print → `mitrt` per chunks 9/10/11 normalisation convention. Lowercase. Used in `co_occupant_roles` as `"Wife, mitrt"` form.

**"Late Old Kingdom" / "Late Dyn. V or early Dyn. VI" dating tokens.** Per chunk-10 convention: `Late Old Kingdom.` → `"6"`. `Late Dyn. V or early Dyn. VI.` → `"6"` (range tail). `Dyn. VI.` → `"6"`. `Late Dyn. V.` → `"5"`.

**Anonymous "NAME UNKNOWN, smr N.N." convention.** PM `NAME UNKNOWN, Companion (smr N.N. of Junker). Dyn. VI.` is an anonymous tomb where Junker classified the occupant as a "Companion of the King" (smr nswt) but the personal name is lost. tomb_id `JKE-AnonCompanion` (or analogous descriptor); occupant_name `null`; occupant_role `"Official"` (smr is an Old Kingdom court title — not Unknown); attribution_certainty `"uncertain"`.

## Field-by-field rules

- **`tomb_id`** — `JKE-<TitleCaseAsciiName>` for Shape-1 named-primary tombs. `S<NUM>` for Shape-2 S-numbered (no JKE- prefix; S-numbers form their own family). `JKE-<AnonDescriptor>` for Shape-5 anonymous tombs (e.g., `JKE-AnonCompanion`).
- **`memphite_area`** — Always `"Giza"`.
- **`occupant_name`** — Title-cased with U+02BF ayin / underdot-ḥ / macron-Ē applied. `null` for Shape-2 + Shape-5. For Shape-4 joint twin, the FIRST name listed by PM goes in occupant_name; the second goes in co_occupants.
- **`occupant_alt_names`** — From `<NAME> good name <ALT>` idiom if it appears.
- **`tomb_aliases`** — Empty for most rows (these are descriptor tombs without cross-references).
- **`co_occupants`** — Wife, parents, joint-named twins. PM-faithful order. Apply diacritics.
- **`co_occupant_roles`** — Length-coupled with `co_occupants`. `"Wife, <title>"`, `"Father, <title>"`, `"Mother, <title>"` form per chunks 9-11 convention. For wife without explicit title cluster: just `"Wife"` (chunk-8/10 precedent). For `mitrt` title: `"Wife, mitrt"`.
- **`is_joint_burial`** — `true` only for Shape-4 joint-named twin headwords.
- **`occupant_role`** — Controlled vocab. `"Vizier"` for Chief Justice and Vizier. `"High Priest"` of any divinity. Most named tombs in this chunk default to `"Official"` (Inspector, Overseer, Tutor, Director, ka-servant, waʿb-priest, Steward, Singer, Scribe, Carpenter, Secretary, Tenant, Companion, etc.). For named-but-female titled "Prophetess of Hathor" (NIaANKH-HATHOR) → `"Official"` (priestess role classified as Official; reserve `"High Priest"` for male `Prophet of <divinity>` cluster). Shape-2 + Shape-5 → `"Unknown"` or `"Official"` per anonymous convention above.
- **`dynasty`** — Roman→Arabic. `Dyn. V` → `"5"`, `Dyn. VI` → `"6"`. `Late Dyn. V or early Dyn. VI` → `"6"`. `Late Dyn. V` → `"5"`. `Late Old Kingdom` → `"6"` (chunk-10 convention). `null` only when PM gives no dating clue.
- **`sub_period`** / **`date_bce_*`** — `null`.
- **`cemetery`** — `"Junker East"` for every row in chunk 13 (single banner). Parallel to chunk-10's `"Junker West"` descriptor convention.
- **`discovery_year`** / **`discoverer`** — `null` (excavator history is body-prose context, reserved for Phase-A enrichment).
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM HEADWORD literally contains the token.
- **`attribution_certainty`** — `"attested"` for clean named-primary; `"probable"` for hedge tokens (`Probably`, `Perhaps`); `"uncertain"` for `(?)` / Shape-2 bare-numeric / Shape-5 anonymous.
- **`shared_with_tombs`** — Empty unless PM cross-references explicitly.
- **`notes_from_pm`** — Headword block prose (title + dating + cross-refs + wife clause + father/mother clause). Mastaba-type body trailer (`Stone-built mastaba.`) dropped. Occupant name dropped (already in occupant_name). For Shape-2 bare-numeric, only the dating marker.
- **`source_citation`** — `{"page": <printed page>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}`. Use the right-page running header to verify per-row. Page boundaries in this chunk (offset `printed = physical + 3`): physical p.115 = printed p.118 (banner + first tombs NIaANKH-HATHOR + SENSEN + MERUKA start), physical p.116 = printed p.119 (MERUKA cont. + IUF + NIKAUKHNUM/NEFERESRIS + KHENU), physical p.117 = printed p.120 (IBINEZEM + NAME UNKNOWN + KHUY + S 2411 + NEFEREN), physical p.118 = printed p.121 (NEFEREN cont. + WERI + KHNEMU + USER + SHEPSI).

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk13: <count> rows; <shape1>/<shape2>/<shape3>/<shape4>/<shape5> split; <anomalies or "none">
```

Where `<shape1>` = JKE-named primary, `<shape2>` = S-numbered, `<shape3>` = bracketed-Roman-regnal, `<shape4>` = joint-named twin, `<shape5>` = anonymous NAME UNKNOWN. Under 100 words.
