# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 7

> **Seventh chunk drawn from PM Vol III** — second West Field chunk (chunk 6 covered cemeteries G 1000–G 1900). This chunk covers Cemetery G 2000 + Cemetery G 2100 (with the eponymous Mastaba G 2220 attached). Dense royal-family material including Khufu-period princes, princesses, and senior officials. This prompt is **self-contained** — the agent does NOT need to read prior chunks' prompts.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-7-p63-p80.txt` and produce a JSONL file with one structured row per **PM-headworded Reisner-numbered mastaba** in Cemetery G 2000 + Cemetery G 2100 + Mastaba G 2220 within the **A. WEST FIELD** section of `§ III. NECROPOLIS`. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-row answers. Every field value must trace to something in the chunk file.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–6 have already shipped (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — A. WEST FIELD** continuation, Cemetery G 2000 and Cemetery G 2100 (including the eponymous Mastaba G 2220).
- PM III.1 offset for this chunk: **printed = physical + 3** (verify in-chunk via the right-page running header `West Field <N>`).
- The chunk file covers physical pp.63–80 / printed pp.66–83. Per-page markers `=== physical page N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens at physical p.63 with `G 2000. Temp. Khufu or Khephren.` headword, immediately followed by the `CEMETERY G 2000¹` banner. The G 2000 row IS the first row-emitting headword in the chunk.
- **Bottom boundary:** the chunk file ends at physical p.80. The `CEMETERY EN ECHELON. NORTH PART WITH MASTABAS G 2300` banner appears near the bottom of physical p.80 — **everything from `CEMETERY EN ECHELON` onwards is OUT OF SCOPE (chunk 8 territory)**. The last in-scope row is the closing G 2200 series tomb on physical p.80 (typically the eponymous Mastaba G 2220 itself).
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk7.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk7.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk7.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — full schema, no cross-references)

Every row MUST have these 22 keys; use `null` (not omitted, not empty string) for unknown values.

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
  "cemetery": "G 2000" | "G 2100",
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

This chunk's rows are PM-headworded Reisner-numbered mastabas in three shapes:

**Shape 1 — Named primary headword.** A line starting with `G <NNNN>. <OCCUPANT NAME IN CAPS> <Title>, <Title>, etc. <Date>.` followed by Reisner/Junker publication body refs. The all-caps name token (which may contain mid-name raised-`a`-style OCR clusters for the Egyptological ayin) IS the conventional English form of the occupant. Title-case it for `occupant_name`.

**Shape 2 — Bare-suffix headword.** A line starting with `G <NNNN>.` followed by either nothing more (purely numeric stub), or only a dating marker, or only `Not marked on plan.`, or only a single short body clause. The headword carries NO occupant-name token. Emit one row with `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`. Dating marker → `dynasty`.

**Shape 3 — Compound twin-mastaba headword.** A line starting with `G <NNNN1>+<NNNN2>. <OCCUPANT NAME IN CAPS>` — PM's convention for two Reisner-numbered mastabas grouped under one headword. Emit ONE row per Reisner number (compound emits TWO rows). Both rows inherit the same occupant-name token UNLESS PM separately gives one or both sub-numbers their own standalone headword line later in the section. Each row gets `shared_with_tombs: ["G<other>"]` cross-referencing the twin half.

**ROW-EMITTING vs OUT-OF-SCOPE in this chunk.** Emit one row per:
- Each Reisner-numbered mastaba `G <NNNN>.` or `G <NNNN1>+<NNNN2>.` headword within the chunk's cemetery range (G 2000 + G 2100 + G 2220).
- Both Shape-1 named, Shape-2 bare-suffix, and Shape-3 compound forms.
- A standalone headword like `G 2100-I-annexe.` (compound suffix form for an annexe to G 2100) — emit a row with `tomb_id` matching PM's full identifier.

Do NOT emit rows for:
- Sub-shaft references within a parent mastaba (`G 2185 A`, `G 2185 B` — these are letter-suffix shafts inside the parent, not standalone tombs UNLESS PM gives them their own standalone headword block with a Reisner number on its own line followed by an occupant cluster).
- The CEMETERY banner lines (`CEMETERY G 2000`, `CEMETERY G 2100 AND MASTABA G 2220`) — section dividers, not rows.
- The `CEMETERY EN ECHELON. NORTH PART WITH MASTABAS G 2300` banner at the bottom of physical p.80 and everything below — chunk 8 territory.
- Cross-references to G 4000s, G 6000s, G 7000s (future chunks / chunk 2).
- Body-prose mentions of objects (statues, false-doors, lintels, slabs with secondary names) — these are body items inside a parent headword block.
- Mortuary chapels, serdabs, boat-pits, satellite chapels — sub-features of a parent mastaba.

**Headword block ends** at the first sub-feature heading after the Reisner-number line: `Mortuary Chapel.`, `Burial Chamber.`, `Chapel.`, `Hall.`, `Serdab.`, `Sloping shaft`, `Plan <Roman>`, `Plans and sections`, `Pillared portico.`, `False-door.`, `Finds`, `Statues.`, or any prose line beginning with a museum-citation token (`Cairo Mus.`, `REISNER`, `JUNKER`, `STEINDORFF`, `SMITH`). The headword block carries the structured fields; the body is dropped.

## Expected row count

Pre-extraction structural scan of the chunk: each Reisner-numbered tomb under the CEMETERY G 2000 or CEMETERY G 2100 AND MASTABA G 2220 banners (plus the eponymous G 2220 mastaba itself) emits one row, in mixed Shape-1/2/3 forms. **Total expected: 40–55 rows.** If your final count is below 30 or above 65, re-read the chunk file — you've either missed cemetery sub-sections or emitted out-of-scope shafts.

## PM III.1 text-layer noise (chunk-7-relevant)

**Raised-ayin in occupant names.** PM prints Egyptological ayin as a small raised glyph; pypdf renders it as a lowercase `a` or `c` mid-word inside otherwise-uppercase names. Normalisation rule: replace the mid-word lowercase `a` or `c` (when it sits between two uppercase letters in an ALL-CAPS name token, or appears as the first character before an otherwise-uppercase continuation) with `ʿ` (U+02BF) and title-case the result. Abstract form examples:
- `<ROOT>a<SUFFIX>` (mid-name ayin between two uppercase blocks) → `<Root>ʿ<suffix>`
- `<PREFIX>aA<ROOT>` → `<Prefix>ʿA<root>` after title-casing (U+02BF replaces the lowercase `a` and the following uppercase block continues)
- `a<ROOT>` (leading raised-ayin) → `ʿ<Root>` (leading U+02BF before title-cased root)
- `<ROOT1>-<ROOT2>` (hyphen-joined compound) — apply the rule independently to each side of the hyphen; the hyphen survives.
- An all-caps name token with no lowercase `a`/`c` inside has NO ayin to normalise — title-case as-is.

**Underdot-Ḥ glyph.** When PM prints the Egyptological underdot-Ḥ glyph (cobra-goddess Meḥyt, frog-goddess Heqet contexts), pypdf may render it as a mid-word uppercase `H` (`MeHyt` for `Meḥyt`). Normalisation rule: when an all-caps name or title cluster contains a mid-word uppercase `H` flanked by lowercase characters, restore to underdot-Ḥ (`ḥ`). NB: PM's typesetting is asymmetric — some divine-names get the underdot (Meḥyt), others don't (Heqet). Match PM's printed form exactly; don't blanket-apply the underdot to every god/goddess name.

**Regnal numbers in brackets.** Some royal-family rows carry bracketed Roman regnal numerals like `<NAME> [I]` or `<NAME> [II]` to disambiguate same-name individuals. PM prints these brackets explicitly when needed. Normalise: title-case the name + space + Roman regnal (`<Name> I`, `<Name> II`). The bracket itself is PM editorial disambiguation; drop the brackets from `occupant_name` after title-casing. pypdf may render bracketed Roman `[II]` as `[11]` or `[Il]` (digit-1 / lowercase-l confusion); normalise to Roman `II` (or `I` for `[I]`).

**Bare-suffix headword variants** (Shape 2):
- `G <NNNN>.` (purely numeric, nothing more)
- `G <NNNN>. Dyn. V.` (only a dating marker)
- `G <NNNN>. Middle Dyn. V or later.`
- `G <NNNN>. Late Dyn. IV or Dyn. V.`
- `G <NNNN>. Not marked on plan.`
All produce a Shape-2 row: `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`. Dynasty extracted from the dating marker if present.

**Reisner-number formatting drift.** pypdf occasionally inserts spaces inside the Reisner number (`G  2110`, `G 21 10`). Normalise to single-space form in the chunk file mental model; the `tomb_id` strips the space entirely (`G2110`).

**Annexe / sub-tomb form.** PM occasionally prints suffix notation for an annexe attached to a parent mastaba (e.g. headword form `G <NNNN>-<Roman>-annexe. <OCCUPANT>` with the annexe identified by a Roman-numeral suffix). Treat as a standalone row with `tomb_id` synthesised as `G<NNNN>a` (lowercase letter suffix `a`, matching the existing chunk-1 subsidiary-pyramid suffix convention G1a/G1b/G1c). The "I-annexe" PM-faithful detail moves to `notes_from_pm` (the verbatim form of PM's printed identifier is appended to notes as e.g. `[PM headword: G <NNNN>-I-annexe]`). Cross-link via `shared_with_tombs` only if PM also prints a separate parent headword for the bare `G<NNNN>` in the chunk; otherwise leave `shared_with_tombs` empty. If PM's headword for the annexe also lists an alt-name clause like `(also <ALT-NAME>, see p. <N>)`, capture the alt form in `occupant_alt_names` (title-cased).

**Letter-suffix shafts.** Lowercase letter suffixes (`G 2185 A` / `G 2185 B`) are typically secondary shafts inside the parent and do NOT emit their own row UNLESS PM gives them a standalone headword block. Uppercase X (chunk-2 precedent `G7000X`) is reserved for extension-shafts.

## Field-by-field rules

- **`tomb_id`** — Reisner G-number form `G<NNNN>` (no spaces, no period). For Shape-3 compound twin halves, two separate rows each with their own `G<NNNN>` form.
- **`memphite_area`** — Always `"Giza"` for chunk 7.
- **`occupant_name`** — Title-cased conventional English form, with raised-ayin normalised to U+02BF and underdot glyphs restored to ḥ where PM prints them. `null` for Shape-2 bare-suffix.
- **`occupant_alt_names`** — When PM prints `<NAME> good name <ALT>` or `(also <ALT>, see p. <N>)` after the primary name, capture the alt form here (title-cased).
- **`tomb_aliases`** — Empty `[]` unless PM appends an Arabic popular-name clause or Lepsius LG cross-reference. For Shape-1 rows in chunk 7 typically `[]`.
- **`co_occupants`** — Empty `[]` unless PM's headword explicitly lists two or more named buried persons in the same tomb. For twin-mastaba Shape-3 compounds, use `shared_with_tombs` not `co_occupants`.
- **`co_occupant_roles`** — Empty `[]` whenever `co_occupants` is empty (length-coupled).
- **`is_joint_burial`** — `false` for typical rows. `true` only when PM explicitly says coordinate two-or-more burials in the same tomb.
- **`occupant_role`** — Controlled vocabulary derived from the title cluster in the headword:
  - `Vizier`, `Chief Justice and Vizier` → `"Vizier"`
  - `King's son`, `King's son of his body`, `Eldest son of the King` → `"Prince"` (named-male royal)
  - `King's daughter` → `"Princess"` (named-female royal)
  - `Hereditary prince` AND `Overlord of <place>` → `"Royal Family"` (administrator-prince hybrid; chunk-2 G 7060 NEFERMAaET precedent)
  - `Prophet`, `Inspector`, `Overseer`, `Judge`, `Tenant`, `Director`, `Strong-of-voice`, `Royal acquaintance` (incl. `(woman)` — non-royal honorific), `Supervisor`, `Book-keeper`, `Secretary`, `Craftsman`, `wad-priest`, `waab-priest`, `sem-priest`, `Greatest of the Ten`, `Hairdresser of the Great House` → `"Official"`
  - `High Priest` of any divinity → `"High Priest"`
  - **Named occupant with NO title cluster** (e.g. `G NNNN. <NAME>. <dating only>`) → `"Official"` (most common OK Memphite non-royal role).
  - Bare-suffix Shape-2 (no name, no title) → `"Unknown"`
- **`dynasty`** — Roman→Arabic from PM's `Dyn. <Roman>` token. `"4"` for `Dyn. IV`, `"5"` for `Dyn. V`, `"6"` for `Dyn. VI`. For range tokens (`Dyn. V-VI`, `Dyn. IV-V`, `Late Dyn. V or Dyn. VI`), use the more specific tail (`V-VI` → `"6"`). For temporal markers without a dynasty number (`Temp. <King>` clauses), derive the dynasty from the named king's known regnal period — Dyn IV kings (Snefru, Khufu, Djedefre/Raʿdjedef, Khephren, Menkaure, Shepseskaf) → `"4"`; Dyn V kings (Userkaf through Unas) → `"5"`; Dyn VI kings (Teti through Pepy II) → `"6"`. `null` ONLY when PM's headword carries no dating clue at all.
- **`sub_period`** — `null` for all chunk-7 rows.
- **`date_bce_approx_start`** / **`date_bce_approx_end`** — `null` for all rows.
- **`cemetery`** — `"G 2000"` for rows under the CEMETERY G 2000 banner; `"G 2100"` for rows under the CEMETERY G 2100 AND MASTABA G 2220 banner (including the G 2220 mastaba itself).
- **`discovery_year`** / **`discoverer`** — `null` for all rows.
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM's HEADWORD block literally contains the respective token. Body prose like `Rock-cut tomb, unfinished.` does NOT fire the flag (chunk-6 G 1607 precedent — only headword-line `unfinished` counts).
- **`attribution_certainty`** — `"attested"` for Shape-1 named-primary with no hedge. `"probable"` for `Probably`, `(probably)`, `Perhaps`. `"uncertain"` for `(?)`, `possibly`, `tentatively`, attributed-to phrasing, AND for all Shape-2 bare-suffix rows.
- **`shared_with_tombs`** — Reisner-form `tomb_id` of the twin half for Shape-3 compound rows; otherwise empty `[]` unless PM explicitly cross-references via `Also owner of tomb N`.
- **`notes_from_pm`** — Verbatim short prose from PM's headword block: title cluster + date marker + cross-reference clauses, publication-citation ribbon dropped. PM-faithful preservation of words and punctuation. For Shape-2 rows, only the dating marker (if any) — pure-numeric stubs get `notes_from_pm: null`.
- **`source_citation`** — `{"page": <printed page where the row's headword first appears>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}`. Use the printed page (physical + 3); verify per-row against right-page running headers.

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk7: <count> rows; <shape1>/<shape2>/<shape3> split; cemeteries G 2000 = <count1>, G 2100 = <count2>; <anomalies or "none">
```

Where `<shape1>` is the count of named-primary rows, `<shape2>` is the count of bare-suffix rows, and `<shape3>` is the count of compound-twin rows. Under 100 words.
