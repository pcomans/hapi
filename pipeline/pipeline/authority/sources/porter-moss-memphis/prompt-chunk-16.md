# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 16

> **Sixteenth chunk drawn from PM Vol III** — Gîza West Field continuation. Covers PM's **CEMETERY G 6000** (Reisner Excavation, Harvard-Boston Expedition). Physical pp.166–179 / printed pp.169–182. Small cluster: 4 Shape-1 named-primary (G 6010 NEFERBAUPTAH, G 6020 IYMERY, G 6030 IT [I], G 6040 SHEPSESKAFʿANKH) + 4 Shape-2 bare-numeric (G 6012, G 6014, G 6037, G 6042). Single chunk file (no a+b split). The named cohort form a three-generation family clan: G 6040 SHEPSESKAFʿANKH (grandfather) → G 6020 IYMERY (father) → G 6010 NEFERBAUPTAH (son), per PM's father/parents body-prose. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-16-p166-p179-cemetery-g6000.txt` and produce a JSONL file with one structured row per **PM-headworded Reisner-numbered mastaba** in Cemetery G 6000. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–15 have already shipped (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — A. WEST FIELD** continuation, `CEMETERY G 6000` cluster (Reisner Excavation, Harvard-Boston Expedition).
- PM III.1 offset for this chunk: **printed = physical + 3** (verify in-chunk via the right-page running header `West Field <N>` or `<N> GÎZA—NECROPOLIS`).
- The chunk file covers physical pp.166–179 / printed pp.169–182. Per-page markers `=== PHYS PAGE N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens at physical p.166 with `West Field 169 / G 6010. NEFERBAUPTAH`. There is no PM `CEMETERY G 6000` banner printed at the top of this cluster — PM goes directly from the prior section (Cemetery en Echelon South, ended at G 5560 on chunk 15) into G 6010 without a banner line. Treat G 6010 as the first in-scope row.
- **Bottom boundary:** the chunk file ends mid-content on physical p.179, after the last G 6042 row. Chunk 17 will pick up with G 7000X / CEMETERY G 7000 banner.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk16.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk16.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk16.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — 23 keys, full schema)

```json
{
  "tomb_id": "G<NUM>",
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
  "cemetery": "G 6000",
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

Three shapes expected in this chunk:

**Shape 1 — Named-primary headword** (`G 6010 NEFERBAUPTAH`, `G 6020 IYMERY`, `G 6040 SHEPSESKAFʿANKH`). Line `G <NUM>. <NAME IN CAPS> <Title cluster>. <Dating>.` Title-case the name with diacritics; `tomb_id: G<NUM>` (drop space).

**Shape 2 — Bare-numeric headword** (`G 6012`, `G 6014`, `G 6037`, `G 6042`). Line `G <NUM>.` followed by optional `(Exped. No. ...)` reference, museum citation, or dating tag. No occupant name. `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`.

**Shape 3 — Bracketed Roman regnal** (`G 6030. IT [I]`). Drop brackets, append Roman with space to occupant_name: `It I`. The Reisner G-number alone is the `tomb_id` (e.g., `G6030`). Do NOT append the Roman to tomb_id for G-numbered tombs.

**ROW-EMITTING vs OUT-OF-SCOPE in this chunk.** Emit one row per:
- Each Shape-1 named-primary headword (4 expected).
- Each Shape-2 bare-numeric headword (4 expected).
- Each Shape-3 bracketed-Roman headword (1 expected — G 6030 IT [I]).

Do NOT emit rows for:
- The `CEMETERY G 7000` banner at the bottom (chunk 17 territory).
- The `G 7000X. TOMB OF HETEPHERES [I]` headword (already in reconciled from chunk 2).
- Body-prose object mentions (statues, lintels, drum-of-deceased, slab-stelae, etc.).
- Chapel sub-features (`Room I.`, `Room II.`, `Burial chamber.`, `Chapel.`, `False-door.`, `Plan XXIX`, etc.).
- Excavator/publication-reference lines (`L. D.`, `REISNER`, `MARIETTE`, `JUNKER`, `NESTOR L'HÔTE`, `BRUGSCH`, `LIEDER squeezes`, `DEVÉRIA squeezes`, `BURTON MSS`, `WILKINSON MSS`, `ROSELLINI`, `CHAMPOLLION`, `CAILLIAUD`, `LANE MSS`, `BISSING`, `SHARPE`, `ANTHES`, `GARDINER`, `BORCHARDT`, `DUNHAM`, `CURTO`, `LIESEGANG`, etc.).
- The "Various. Dyn. V-VI." anonymous block on physical p.175 (printed p.178) — that is a body-prose object-aggregation section listing false-doors and ka-servant blocks without tomb attribution; not a headworded tomb.
- "Dersenez Scribe of the granary, Steward, Dyn. V." body-prose statue-attribution line on physical p.173 (printed p.176) — this is a statue findspot mention, NOT a Cemetery G 6000 headword. Dersenez has no G-number in this chunk; out of scope.

**Headword block ends** at the first sub-feature heading: `Room I.`, `Room II.`, `Room III.`, `Room IV.`, `Burial Chamber.`, `Chapel.`, `False-door.`, `Plan <Roman>`, `Stone-built mastaba.`, `Brick-built mastaba.`, `Statue-group`, `Relief-fragments`, `Statues.`, `Various.`, or any prose line beginning with a museum-citation/publication token (`Cairo Mus.`, `Berlin Mus.`, `Hildesheim Mus.`, `Leipzig Mus.`, `L. D.`, `REISNER`, `JUNKER`, `MARIETTE`).

## Expected row count

Pre-extraction structural scan: 3 Shape-1 named-primary (G 6010, G 6020, G 6040) + 1 Shape-3 bracketed-Roman (G 6030 IT [I]) + 4 Shape-2 bare-numeric (G 6012, G 6014, G 6037, G 6042). **Total expected: 8 rows (acceptable band 6–10).** If your final count is below 6 or above 12, re-read the chunk file — you've either missed Shape-2 bare-numeric subsidiaries (commonly missed) or emitted out-of-scope body-prose statues / sub-features.

## PM III.1 text-layer noise (chunk-16-relevant)

**Raised-ayin in occupant names.** Replace mid-name or leading raised-`a`/`c`/`'` glyphs with `ʿ` (U+02BF) and title-case. tomb_id is ASCII-only (drop ayin).

**Theophoric-ankh hyphenation.** Any `<BASE>aANKH` token in PM → `<Base>-ʿankh` with hyphen before the `ʿankh` element. Per source-wide convention (chunks 8/14/15 precedents: `Khufu-ʿAnkh`, `Meryrēʿ-Meryptaḥ-ʿankh`, `Khufudinef-ʿankh`). Note: when the `ankh` element is interior to the name (e.g., `Niʿankh-Ḥathor`), preserve PM's printed hyphenation as-is.

**Underdot-Ḥ glyph.** Apply on `ḥ`-root names per source-wide convention (precedent: Ḥathor, Ḥeket, Ḥarzedef, Meḥu, Meḥyt, Snefruḥotp, Meryptaḥ, Neferḥerenptaḥ, Imḥotep, Ḥetepheres, ʿAnkh-Ḥathor, Weḥemka, Washptaḥ, Kheriḥet, Irkaptaḥ, Meḥi, Ptaḥiufni, Seshetḥotp). For names ending in `-ptah` / `-PTAH`: apply underdot on the `ptḥ` root. For names containing `hathor` / `HATHOR` / `cap-H + othor` (pypdf renders PM's underdot-Ḥ as cap-H mid-word): normalise to `Ḥathor` / `-ḥathor` per ḥ-root convention.

**Macron-Ē on Re-deity-compound names.** Per chunks 4/8/10/11/13/14/15 precedent (Merenrēʿ I, Saḥurēʿ, Neferirkarēʿ, Neuserrēʿ, Rēʿḥerka, Rēʿḥotp, Rēʿshepses, Duaenrēʿ, Menkaurēʿ). For this chunk:
- PM `SaHurea` → `Saḥurēʿ` (Re-compound + ḥ-root).
- PM `Neferirkarea` → `Neferirkarēʿ` (Re-compound).
- PM `Neuserrea` → `Neuserrēʿ` (Re-compound; PM's `Neuser` is one of several spellings — preserve PM's printed `Neuser-` prefix rather than substituting `Niuser-`).

**`HetH` / `aankH` / similar cap-H rendering.** pypdf renders PM's underdot-Ḥ glyph as cap-H mid-word. Normalise per ḥ-root convention. Examples: `Nikauhathor` → `Nikauḥathor`; if any chunk-16 row contained `HetepHeres` → `Ḥetepḥeres`.

**`waab-priest` / `wad-priest` drift.** Source-wide ayin-normalisation: raw OCR `waab` or `wad` → `waʿb`. Per chunks 1/9/10/11/14/15 convention.

**Wife-clause idiom.** PM body-prose `Wife, <NAME> <Title>.` → wife in `co_occupants` (`["<NAME>"]`), title in `co_occupant_roles` (`["Wife, <Title>"]`). Capture verbatim from PM; apply diacritics. Per chunks 9–15 convention.

**"Parents, <NAME1> and <NAME2> (tomb G<NUM>)" body-prose preservation.** PM cross-references parental tombs via `(tomb G <NUM>)`. Capture both parents in `co_occupants` with role `"Father"` / `"Mother"` (length-coupled). The `(tomb G <NUM>)` cross-ref goes in `notes_from_pm` but is NOT added to `tomb_aliases` (that field is reserved for explicit cross-references to ALIASES of the headword tomb, not relatives' tombs).

**"Father, <NAME> (tomb G<NUM>)" body-prose preservation.** Parallel to the parents-cluster idiom: single parent → one `co_occupant` + `"Father"` or `"Mother"` role + `(tomb G <NUM>)` preserved in notes.

## Field-by-field rules

- **`tomb_id`** — `G<NUM>` (drop space from PM). For G 6030 IT [I], `tomb_id` is `G6030` (NO Roman appended; G-numbered tomb_id convention).
- **`memphite_area`** — Always `"Giza"`.
- **`occupant_name`** — Title-cased with U+02BF ayin / underdot-Ḥ / macron-Ē applied. Theophoric-ankh names hyphenated (`Shepseskaf-ʿankh`). `null` for Shape-2 bare-numeric. For Shape-3 bracketed Roman, drop brackets and append Roman with space (e.g., `It I`).
- **`occupant_alt_names`** — Empty for this chunk (no `good name <ALT>` / `called <ALT>` idioms expected).
- **`tomb_aliases`** — PM prints `LG <N>` body trailers adjacent to some headwords; record as `["LG <N>"]` when present, per chunks 14/15 convention. Empty otherwise. (These are aliases of the same tomb, not cross-references to other tombs.)
- **`co_occupants`** — Wife, parents per body-prose clauses. PM-faithful order: PM's `Parents, X and Y. Wife, Z.` → co_occupants order `[X, Y, Z]`. Apply diacritics.
- **`co_occupant_roles`** — Length-coupled with `co_occupants`. `"Father"` / `"Mother"` (no title needed when PM gives no parental title cluster) per chunk-15 G 5170 convention. `"Wife, <title>"` form for wife. Example: `["Father", "Mother", "Wife, Royal acquaintance"]`.
- **`is_joint_burial`** — `false` for all chunk-16 rows. No Shape-4 joint-named twins expected in Cemetery G 6000. Multiple co-occupants (parents + wife) is NOT joint burial (joint = multiple OCCUPANTS sharing the tomb, not relatives mentioned in body-prose).
- **`occupant_role`** — Controlled vocab.
  - `"Vizier"` for `Chief Justice and Vizier` (none expected in this chunk).
  - `"Prince"` for `King's son` (none expected).
  - `"Princess"` for `King's daughter` (none expected).
  - `"High Priest"` of any divinity.
  - `"Royal Family"` ONLY when PM gives explicit royal-blood genealogy (e.g., `Father, <King>` or `Mother, <Queen>`). The Cemetery G 6000 named cohort are all officials/stewards/prophets — NO royal genealogy expected.
  - Most named: `"Official"` (Steward, Prophet of Khufu, Scribe of the archives, Overseer of singing in the Great House, etc.).
  - Shape-2 bare-numeric: `"Unknown"`.
- **`dynasty`** — Roman→Arabic. `Dyn. V` → `"5"`, `Dyn. VI` → `"6"`. `Middle to end of Dyn. V` → `"5"` (start of range, body-attested). `Temp. <Ruler>` → derive from ruler's dynasty (`Temp. Neferirkarēʿ` → `"5"`; `Temp. Neuserrēʿ or later` → `"5"`). `Dyn. V-VI` → `"6"` (range tail). `null` only when PM gives NO dating clue. For Shape-2 bare-numeric: `null` unless body-prose dating is printed adjacent to the headword (apply chunks 6/8 body-attestation rule).
- **`sub_period`** / **`date_bce_*`** — `null`.
- **`cemetery`** — `"G 6000"` for every row in chunk 16 (single banner, parallel to chunks 9/14's `"G 3000"` / `"G 4000"` convention).
- **`discovery_year`** / **`discoverer`** — `null` (excavator history is reserved for Phase-A enrichment).
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM HEADWORD literally contains the token (none expected).
- **`attribution_certainty`** — `"attested"` for clean Shape-1 named-primary. `"uncertain"` for Shape-2 bare-numeric. `"probable"` only if PM uses `Probably` / `Perhaps` hedges at the headword (none expected in this chunk).
- **`shared_with_tombs`** — Empty for all chunk-16 rows. (PM cross-references parental tombs in body-prose via `(tomb G <NUM>)`, but those are RELATIVES' tombs, not shared occupancy of the headword's own tomb — keep `shared_with_tombs` empty.)
- **`notes_from_pm`** — Headword block prose: title cluster + dating + parents/wife/father clauses (verbatim, with diacritics applied). DROP: mastaba body trailer (`Stone-built mastaba.`, `‘Tomb of Trades.’`), LG codes (already in `tomb_aliases`), `Plan <Roman>` references, room/chapel sub-feature headings, museum-citation lines, publication references, photo/squeeze references. Keep the `(tomb G <NUM>)` parental cross-ref token in the parents/wife/father clause so the genealogy is traceable.
- **`source_citation`** — `{"page": <printed page>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}`. Use the right-page running header (`West Field <N>` or `<N> GÎZA—NECROPOLIS`) to verify per-row. Page boundaries in this chunk (offset `printed = physical + 3`): physical p.166 = printed p.169 (G 6010 headword), physical p.167 = printed p.170 (G 6010 cont. + G 6012 + G 6014 + G 6020 headword), physical p.171 = printed p.174 (G 6030 headword), physical p.172 = printed p.175 (G 6037 + G 6040 headword), physical p.173 = printed p.176 (G 6040 cont.), physical p.175 = printed p.178 (G 6042 expected).

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk16: <count> rows; <shape1>/<shape2>/<shape3> split; <anomalies or "none">
```

Where `<shape1>` = G-named primary, `<shape2>` = G-bare-numeric, `<shape3>` = bracketed-Roman-regnal. Under 100 words.
