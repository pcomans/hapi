# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 9

> **Ninth chunk drawn from PM Vol III** — fourth Gîza West Field chunk. Covers PM's `CEMETERY G 3000` ("The Minor Cemetery"), excavated by Clarence S. Fisher for the University of Pennsylvania's Eckley B. Coxe Jr. Expedition (1915), opening on physical p.92 and running to the `JUNKER CEMETERY (WEST)` banner on physical p.97. Small, coherent chunk: 14 PM-headworded Reisner-numbered tombs in the G 3000–G 3099 range. This prompt is **self-contained** — the agent does NOT need to read prior chunks' prompts.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-9-p92-p97.txt` and produce a JSONL file with one structured row per **PM-headworded Reisner-numbered mastaba** in Cemetery G 3000 within the **A. WEST FIELD** section of `§ III. NECROPOLIS`. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-row answers. Every field value must trace to something in the chunk file.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–8 have already shipped (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — A. WEST FIELD** continuation, Cemetery G 3000 (Fisher's "Minor Cemetery", Penn Coxe Expedition 1915).
- PM III.1 offset for this chunk: **printed = physical + 3** (verify in-chunk via the right-page running header `West Field <N>`).
- The chunk file covers physical pp.92–96 / printed pp.95–99. Per-page markers `=== PHYS PAGE N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens with `CEMETERY G 3000` banner on physical p.92 (the file was pre-trimmed before this banner; nothing above it).
- **Bottom boundary:** the chunk file ends just before the `JUNKER CEMETERY (WEST)` banner on physical p.97 (chunk-10 territory; Junker's named-tomb cluster uses a different identifier convention with no Reisner G-numbers).
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk9.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk9.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk9.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — full schema)

Every row MUST have these 23 keys; use `null` (not omitted, not empty string) for unknown values.

```json
{
  "tomb_id": "G<NNNN>" | "G<NNNN><letter>",
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
  "cemetery": "G 3000",
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

This chunk's rows are PM-headworded Reisner-numbered mastabas in the following shapes:

**Shape 1 — Named primary headword.** A line starting with `G <NNNN>. <OCCUPANT NAME IN CAPS> <Title>, <Title>, etc. <Date>.` followed by publication body refs. The all-caps name token IS the conventional English form; title-case it for `occupant_name`. Raised-`a`/`c` glyphs inside the all-caps name normalise to U+02BF ayin (see noise section). Multi-line headword carryover is common — the title cluster spills to a second printed line.

**Shape 2 — Bare-suffix headword.** A line starting with `G <NNNN>.` followed by only a dating marker (`Dyn. VI.`) or nothing at all. Emit one row with `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`. Dynasty extracted from the dating marker if present.

**Shape-1-annexe variant — `G <NNNN> with annexe.`** PM occasionally prints a tomb headword annotated `with annexe.` indicating the mastaba has an attached annexe sub-structure. Treat as ONE row with `tomb_id: G<NNNN>` (no separate annexe row unless PM gives the annexe its own separate headword). The `with annexe.` phrase moves to `notes_from_pm` to preserve the structural detail.

**ROW-EMITTING vs OUT-OF-SCOPE in this chunk.** Emit one row per:
- Each Reisner-numbered mastaba `G <NNNN>.` headword in the G 3000–G 3099 range.
- Both Shape-1 named and Shape-2 bare-suffix forms.

Do NOT emit rows for:
- The `CEMETERY G 3000` banner line — section divider, not a row.
- The `JUNKER CEMETERY (WEST)` banner — chunk-10 territory; should not appear in this file (pre-trimmed).
- Body-prose mentions of objects (statues, false-doors, lintels, slabs with secondary names) — these are body items inside a parent headword block.
- Burial-chamber, serdab, shaft sub-features — sub-features of a parent mastaba.

**Headword block ends** at the first sub-feature heading after the Reisner-number line: `Mortuary Chapel.`, `Burial Chamber.`, `Chapel.`, `Hall.`, `Serdab.`, `Sloping shaft`, `Plan <Roman>`, `Plans and sections`, `Pillared portico.`, `False-door.`, `Finds`, `Statues.`, `Mastaba with stone filling lined with bricks.`, or any prose line beginning with a museum-citation token (`Cairo Mus.`, `REISNER`, `FISHER`, `JUNKER`, `STEINDORFF`, `SMITH`, `HASSAN`, `BOSTON MUS.`). The headword block carries the structured fields; the body is dropped.

## Expected row count

Pre-extraction structural scan of the chunk: 14 Reisner-numbered tombs visible under the CEMETERY G 3000 banner. **Total expected: 12–16 rows.** If your final count is below 10 or above 20, re-read the chunk file — you've either missed cemetery sub-sections or emitted out-of-scope sub-features.

## PM III.1 text-layer noise (chunk-9-relevant)

**Raised-ayin in occupant names.** PM prints Egyptological ayin as a small raised glyph; pypdf renders it as a lowercase `a` or `c` mid-word inside otherwise-uppercase names. Normalisation rule: replace the mid-word lowercase `a` or `c` (when it sits between two uppercase letters in an ALL-CAPS name token, or appears as the first character before an otherwise-uppercase continuation) with `ʿ` (U+02BF) and title-case the result. Abstract form examples:
- `<ROOT>a<SUFFIX>` (mid-name ayin between two uppercase blocks) → `<Root>ʿ<suffix>`
- `<PREFIX>aA<ROOT>` → `<Prefix>ʿA<root>` after title-casing
- `a<ROOT>` (leading raised-ayin) → `ʿ<Root>` (leading U+02BF before title-cased root)
- `<ROOT1>-<ROOT2>` (hyphen-joined compound) — apply the rule independently to each side of the hyphen; the hyphen survives.

**Underdot-Ḥ glyph on Egyptian theophoric / personal-name roots.** PM uses underdot-Ḥ (ḥ) on the Egyptological transliteration of names whose underlying root contains the *ḥ* phoneme. Common roots: *ḥtp* (peace/satisfaction), *mḥ* (north / fill), *ptḥ* (god Ptaḥ), *nḫ-ḥ* (eternity), *ḥgy*, *ḥnk* (donate). When the all-caps occupant name's pypdf rendering shows `H` flanked by lowercase letters that maps to one of these roots, restore the underdot-ḥ. NB: also apply to goddess names (e.g. Ḥathor, Meḥyt) where PM prints with underdot. When in doubt about a specific name, preserve the OCR-literal `h` and let the egyptologist-reviewer pass restore the underdot.

**Macron-Ē on Re/Reʿ-compound names.** PM uses macron-Ē when the Re sun-god component appears in a compound name (the Ē reflects the long vowel of the deity's name in Egyptological reconstruction). Examples (abstract): `MERYRĒC` → `Meryrēʿ`, `MERENRĒC` → `Merenrēʿ`. The pypdf text layer may render this as plain `E` or as `£`/`Ē`. Apply the macron when the name's root contains Re-as-deity. Chunk-4 / chunk-8 precedent.

**Royal-name "good name" alt-name idiom** (Egyptian *rn nfr*). PM prints `<PRIMARY-NAME> good name <ALT-NAME>` to denote a "beautiful name" — the secondary personal name an Old Kingdom official commonly used. Capture the PRIMARY as `occupant_name` and the ALT as a single entry in `occupant_alt_names`. Title-case both. Apply the pattern wherever PM uses the `good name` idiom in the chunk.

**"Wife, <NAME>" body-prose preservation when adjacent to headword.** PM occasionally prints a `Wife, <NAME> <Title cluster>.` clause immediately after the dating marker line, before the structural body (`Stone-built mastaba.`, `Brick-built mastaba.`, etc.). Capture the wife in `co_occupants` (and her title cluster in `co_occupant_roles`); also preserve the verbatim wife clause in `notes_from_pm`. Chunk-8 precedent (G 2370 Thefi, G 2378 Khentkaus, G 2423 Khenit, G 2430 Khaʿmerernebti).

**Bare-suffix headword variants** (Shape 2):
- `G <NNNN>. Dyn. VI.` (dating-only)
- `G <NNNN>.` (purely numeric)
All produce a Shape-2 row: `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`. Dynasty extracted from the dating marker if present.

**Annexe form** `G <NNNN> with annexe.` — single row, `tomb_id: G<NNNN>`. The `with annexe.` phrase preserved in `notes_from_pm`. NOT a separate sub-row (distinct from chunk-7's `G 2100-I-annexe` which was a separately-headworded Roman-numeral-suffixed annexe).

**Royal cartouches in body refs.** PM may print royal names with raised-ayin in body content (e.g. titles like `Prophet of <King1> and <King2>` where one or both kings carry a raised-`a`/`c` terminal glyph). Normalise raised-`a`/`c` → U+02BF when in `notes_from_pm` cells too, per the chunks 1-8 source-wide convention.

**Body-attested name recovery.** Chunk-6 G 1314 + chunk-8 G 2336 precedent: when PM's headword is bare-suffix `G <NNNN>.` but the body block contains an inscribed object naming an Old-Kingdom official (architrave, double-statue, false-door FOUND IN this tomb, relief-fragment with name), DO NOT promote at extraction time. The egyptologist-reviewer applies these body-recoveries via `fix_rows.py` corrections, not at the extraction stage. Agents should emit the Shape-2 null-occupant row.

## Field-by-field rules

- **`tomb_id`** — Reisner G-number form `G<NNNN>` (no spaces, no period). Letter-suffix `G<NNNN><letter>` if PM uses one.
- **`memphite_area`** — Always `"Giza"` for chunk 9.
- **`occupant_name`** — Title-cased conventional English form, with raised-ayin normalised to U+02BF, underdot-Ḥ on known *ḥ*-root names, macron-Ē on Re-deity-compound names. `null` for Shape-2 bare-suffix.
- **`occupant_alt_names`** — When PM prints `<NAME> good name <ALT>` or `(also <ALT>, see p. <N>)` after the primary name, capture the alt form here (title-cased).
- **`tomb_aliases`** — Empty `[]` unless PM appends a Lepsius LG cross-reference (`LG <N>`) in the headword/body block.
- **`co_occupants`** — Empty `[]` unless PM's headword block (or immediately-adjacent body line like `Wife, <NAME>...`) explicitly lists buried persons beyond the primary occupant.
- **`co_occupant_roles`** — Empty `[]` whenever `co_occupants` is empty (length-coupled). When populated, each entry holds the title-cluster prose for the corresponding co-occupant (e.g. `"Wife, Royal acquaintance"`).
- **`is_joint_burial`** — `false` for typical rows. `true` only when PM's headword itself names two equal occupants joined by `and` (e.g. `G <NNNN>. <NAME1> and wife <NAME2>.`).
- **`occupant_role`** — Controlled vocabulary derived from the title cluster in the headword:
  - `Vizier`, `Chief Justice and Vizier` → `"Vizier"`
  - `King's son`, `King's son of his body` → `"Prince"`
  - `King's daughter` → `"Princess"`
  - `Prophet`, `Inspector`, `Overseer` (of <X>), `Judge`, `Tenant`, `Director`, `Royal acquaintance`, `Supervisor`, `Book-keeper`, `Secretary`, `Craftsman`, `Greatest of the Ten`, `wad-priest`, `waab-priest`, `sem-priest` → `"Official"`
  - `High Priest` of any divinity → `"High Priest"`
  - **Any other non-royal, non-vizier, non-high-priest title cluster** → `"Official"` (catch-all; Old Kingdom non-royal court / cultic / administrative titles default to Official).
  - **Named occupant with NO title cluster** → `"Official"` (chunk-6 default per egyptologist precedent).
  - Bare-suffix Shape-2 (no name, no title) → `"Unknown"`
- **`dynasty`** — Roman→Arabic from PM's `Dyn. <Roman>` token. `"4"` for `Dyn. IV`, `"5"` for `Dyn. V`, `"6"` for `Dyn. VI`. Range tokens use the more specific tail (`Dyn. V-VI` → `"6"`; `End of Dyn. V or later` → `"6"`). For `Temp. <King>` clauses, derive dynasty from the named king's regnal period — Dyn IV kings (Snefru, Khufu, Raʿdjedef, Khephren, Menkaureʿ, Shepseskaf) → `"4"`; Dyn V (Userkaf through Unis) → `"5"`; Dyn VI (Teti through Pepy II) → `"6"`. `null` ONLY when PM's headword carries no dating clue at all.
- **`sub_period`** — `null` for all chunk-9 rows.
- **`date_bce_approx_start`** / **`date_bce_approx_end`** — `null` for all rows.
- **`cemetery`** — `"G 3000"` for every row in chunk 9 (the lone cemetery banner).
- **`discovery_year`** / **`discoverer`** — `null` for all rows.
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM's HEADWORD block literally contains the respective token. Body prose does NOT fire the flag (chunk-6 G 1607 precedent).
- **`attribution_certainty`** — `"attested"` for Shape-1 named-primary with no hedge. `"probable"` for `Probably`, `(probably)`, `Perhaps`. `"uncertain"` for `(?)`, `possibly`, `tentatively`, AND for all Shape-2 bare-suffix rows.
- **`shared_with_tombs`** — Empty `[]` unless PM explicitly cross-references via `Also owner of tomb N` or `(tomb G NNNN)`.
- **`notes_from_pm`** — Verbatim short prose from PM's headword block: title cluster + date marker + cross-reference clauses + wife clause if adjacent + `with annexe.` clause if present. Publication-citation ribbon dropped. PM-faithful preservation. For Shape-2 rows, only the dating marker (if any) — pure-numeric stubs get `notes_from_pm: null`. Per chunks 6–8 convention, the OCCUPANT NAME is dropped from notes (already in `occupant_name`); notes capture title + dating + cross-refs + wife clause.
- **`source_citation`** — `{"page": <printed page where the row's headword first appears>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}`. Use the printed page (physical + 3); verify per-row against right-page running headers.

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk9: <count> rows; <shape1>/<shape2> split; <anomalies or "none">
```

Where `<shape1>` is the count of named-primary rows and `<shape2>` is the count of bare-suffix rows. Under 80 words.
