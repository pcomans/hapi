# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 10

> **Tenth chunk drawn from PM Vol III** — fifth Gîza West Field chunk and the FIRST chunk to use **named-headword Junker tombs** (no Reisner G-numbers). Covers PM's `JUNKER CEMETERY (WEST)` cluster, excavated by Hermann Junker for the Akademie der Wissenschaften in Wien / Pelizaeus-Museum Hildesheim / University of Leipzig (1926-7). Physical pp.97–104 / printed pp.100–107. ~20 named tombs + 5 Steindorff S-numbered tombs. This prompt is **self-contained** — the agent does NOT need to read prior chunks' prompts.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-10-p97-p104.txt` and produce a JSONL file with one structured row per **PM-headworded mastaba** in the Junker West cluster. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-row answers. Every field value must trace to something in the chunk file.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–9 have already shipped (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — A. WEST FIELD** continuation, `JUNKER CEMETERY (WEST)` (Akademie der Wissenschaften in Wien + Pelizaeus-Museum Hildesheim + University of Leipzig Expedition, 1926-7).
- PM III.1 offset for this chunk: **printed = physical + 3** (verify in-chunk via the right-page running header `West Field <N>`).
- The chunk file covers physical pp.97–105 / printed pp.100–108. Per-page markers `=== PHYS PAGE N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens with `JUNKER CEMETERY (WEST)` banner on physical p.97 (the file was pre-trimmed before this banner; nothing above it).
- **Bottom boundary:** the chunk file ends just before the `STEINDORFF CEMETERY` banner (chunk-11 territory).
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk10.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk10.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk10.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — 23 keys, full schema)

```json
{
  "tomb_id": "JKR-<TitleCaseName>" | "S<NUM>",
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
  "cemetery": "Junker West",
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

## tomb_id convention — NEW for chunk 10

Chunk 10 introduces TWO new tomb_id schemes (Junker West has no Reisner G-numbers):

**Named tombs (JKR descriptor form):** PM prints `<NAME IN CAPS> <Title cluster>. <Dating>.` as a standalone line opening the tomb's headword block. Synthesise the tomb_id as `JKR-<TitleCaseName>`. ASCII-only descriptor body (drop ayin/underdot from the tomb_id itself — they live in `occupant_name`):
- Abstract shape examples (illustrative only — actual chunk-10 names you will encounter in the source):
  - PM `<NAME>` (plain ASCII caps) → tomb_id `JKR-<Name>` (title-cased ASCII)
  - PM `a<ROOT>` (leading raised-a ayin glyph) → tomb_id `JKR-<Root>` (ASCII; the ʿ U+02BF ayin appears only in `occupant_name` as `ʿ<Root>`)
  - PM `<NAME [I]>` (Roman regnal disambiguator) → tomb_id `JKR-<Name>I` (the bracket itself dropped, Roman regnal appended without space)
  - PM `<NAME [II]>` → tomb_id `JKR-<Name>II`
- The PM all-caps name token IS the conventional English form; title-case it for `occupant_name` AND derive the tomb_id descriptor from the title-cased ASCII form.

**S-numbered tombs (Steindorff form):** PM prints `S <NUM>. <Dating>.` OR `S <NUM1>/<NUM2>. <Dating>.` as a standalone headword line. Synthesise the tomb_id as `S<NUM>` (drop the space; first number only for twin-number form). The second number of a twin pair (`<NUM2>` in `<NUM1>/<NUM2>`) goes into `tomb_aliases` as `["S <NUM2>"]` (PM-verbatim with the space).

## How to identify a row

This chunk's rows are PM-headworded named-or-S-numbered mastabas in three shapes:

**Shape 1 — Named primary headword.** A line starting with `<NAME IN CAPS> <Title>, <Title>, etc. <Date>.` followed by publication body refs. The all-caps name token (which may contain mid-name raised-`a`/`c` glyphs for the Egyptological ayin) IS the conventional English form of the occupant. Title-case it for `occupant_name` (with ayin/underdot normalisation per the noise section); derive tomb_id `JKR-<AsciiTitleCaseName>` from the same name (ASCII-only).

**Shape 2 — Bare S-numbered headword.** A line starting with `S <NUM>.` or `S <NUM1>/<NUM2>.` followed by only a dating marker. The headword carries NO occupant-name token. Emit one row with `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`. Dynasty extracted from the dating marker if present.

**Shape 3 — Named tomb with bracketed Roman regnal.** A line starting with `<NAME IN CAPS> [<Roman>] <Title cluster>. <Dating>.` — PM editorial Roman regnal to disambiguate same-name individuals. Title-case the name + Roman regnal (without brackets): tomb_id `JKR-<Name><Roman>`, `occupant_name: "<Name> <Roman>"`.

**ROW-EMITTING vs OUT-OF-SCOPE in this chunk.** Emit one row per:
- Each named-headword mastaba within the Junker West cluster — Shape 1.
- Each `S <NUM>` or `S <NUM>/<NUM>` headword — Shape 2.
- Each bracketed-Roman-regnal named tomb — Shape 3.

Do NOT emit rows for:
- The `JUNKER CEMETERY (WEST)` banner — section divider, not a row.
- The `STEINDORFF CEMETERY` banner — chunk-11 territory; should not appear in this file (pre-trimmed).
- Body-prose mentions of objects (statues, false-doors, lintels, slabs with secondary names) — these are body items inside a parent headword block.
- Chapel sub-feature subsections like `I. Offering-room.`, `(I) Doorway.`, `(2) Offering-table`, `(a) Three registers`, etc. — these are nested chapel-decoration descriptors inside a parent tomb (notably the very large SONB I block which spans 3+ printed pages).
- Mortuary chapels, serdabs, boat-pits, satellite chapels — sub-features of a parent mastaba.

**Headword block ends** at the first sub-feature heading after the name/S-number line: `Mortuary Chapel.`, `Burial Chamber.`, `Chapel.`, `Hall.`, `Serdab.`, `Sloping shaft`, `Plan <Roman>`, `Plans and sections`, `Pillared portico.`, `False-door.`, `Finds`, `Statues.`, `Stone-built mastaba.`, `Brick-built mastaba.`, `Stone-cased mastaba.`, `Stone chest, originally...`, or any prose line beginning with a museum-citation token (`Cairo Mus.`, `Hildesheim Mus.`, `Leipzig Mus.`, `Berlin Mus.`, `REISNER`, `JUNKER`, `STEINDORFF`, `SMITH`, `HASSAN`). The headword block carries the structured fields; the body is dropped.

## Expected row count

Pre-extraction structural scan: ~25 named tombs (Shape 1/3) + 5 S-numbered tombs (Shape 2) under the JUNKER CEMETERY (WEST) banner. **Total expected: ~30 rows (acceptable band 26–34).** If your final count is below 25 or above 35, re-read the chunk file — you've either missed tombs or emitted out-of-scope sub-features (the largest named-headword block in this cluster spans 3+ printed pages of chapel-decoration sub-features and is ONE row — do not sub-split it).

## PM III.1 text-layer noise (chunk-10-relevant)

**Raised-ayin in occupant names.** PM prints Egyptological ayin as a small raised glyph; pypdf renders it as a lowercase `a` or `c` mid-word inside otherwise-uppercase names. Normalisation rule: replace the mid-word lowercase `a` or `c` (when it sits between two uppercase letters in an ALL-CAPS name token, or appears as the first character before an otherwise-uppercase continuation, or as the first character of an ALL-CAPS name token) with `ʿ` (U+02BF) and title-case the result. Abstract form examples:
- `<ROOT>a<SUFFIX>` (mid-name ayin between two uppercase blocks) → `<Root>ʿ<suffix>`
- `<PREFIX>aA<ROOT>` → `<Prefix>ʿA<root>` after title-casing
- `a<ROOT>` (leading raised-ayin) → `ʿ<Root>` (leading U+02BF before title-cased root)
- `'<ROOT>` with literal apostrophe (some pages render the raised-ayin as a straight quote) → `ʿ<Root>`
- `<ROOT1>-<ROOT2>` (hyphen-joined compound) — apply the rule independently to each side of the hyphen; the hyphen survives.
- An all-caps name token with no lowercase `a`/`c` inside has NO ayin to normalise — title-case as-is.

**ASCII-only tomb_id descriptor.** The `tomb_id` itself is ASCII (`JKR-Ankh`, not `JKR-ʿAnkh`) for stability across downstream consumers. Ayin and underdot-ḥ live in `occupant_name` only.

**Underdot-Ḥ glyph.** When PM prints the Egyptological underdot-Ḥ glyph on names whose Egyptian root contains the *ḥ* phoneme, pypdf may render it as a mid-word uppercase `H` flanked by lowercase letters. Apply the underdot-ḥ in `occupant_name` per the source-wide convention established in chunks 6/8/9 (precedent names: Ḥathor, Meḥu, Meḥyt, Snefruḥotp, Meryptaḥ, Neferḥetpes, Neferḥi).

**Macron-Ē on Re/Reʿ-compound names.** PM uses macron-Ē when the Re sun-god component appears in a compound name. Apply where the name's root contains Re-as-deity (chunks 4 + 8 precedent for Merenrēʿ I and Meryrēʿ-Meryptaḥʿankh).

**Royal-name "good name" alt-name idiom** (Egyptian *rn nfr*). PM prints `<PRIMARY-NAME> good name <ALT-NAME>` to denote a "beautiful name" — the secondary personal name an Old Kingdom official commonly used. Capture the PRIMARY as `occupant_name` and the ALT as a single entry in `occupant_alt_names`. Title-case both. Apply the pattern wherever PM uses the `good name` idiom in the chunk.

**"Wife, <NAME>" body-prose preservation when adjacent to headword.** PM occasionally prints a `Wife, <NAME> <Title cluster>.` clause immediately after the dating marker line, before the structural body (`Stone-built mastaba.`, `Brick-built mastaba.`, etc.). Capture the wife in `co_occupants` (and her title cluster in `co_occupant_roles`); also preserve the verbatim wife clause in `notes_from_pm`. Chunks 8/9 precedent.

**Bracketed Roman regnal pypdf drift.** PM prints `[I]`, `[II]`, `[III]` for same-name individuals; pypdf may render `[II]` as `[Il]` (digit-1 + lowercase-l confusion) or `[I I]` or `[11]`. Normalise to Roman `I`/`II`/`III` and drop the brackets from `occupant_name` and `tomb_id`. Abstract form: `<NAME [I]>` becomes `<Name> I` in `occupant_name` (with space) and `JKR-<Name>I` in `tomb_id` (no space). `<NAME [II]>` becomes `<Name> II` / `JKR-<Name>II`.

**Junker "Late Old Kingdom" dating marker.** Many Junker West tombs are dated `Late Old Kingdom.` rather than a specific dynasty number. Per the chunk-10 prompt rule: when PM prints `Late Old Kingdom.` without a specific dynasty, set `dynasty: "6"` (Late Old Kingdom = Dyn VI in the standard Egyptological chronology; matches the PM convention seen elsewhere where "Late Old Kingdom" is shorthand for terminal-Dyn-VI). Document this in `notes_from_pm` verbatim.

**Junker S-numbered Shape-2 dating.** S-numbered tombs typically carry only `Late Old Kingdom.` or `Dyn. VI.`. Use the same Dyn VI = "6" mapping.

**"atw-official" pypdf drift.** PM prints the OK title `ʾtw` (transliterated *ʾtw* in Egyptian) but pypdf may render it as `ATw-official` (with raised-`A` ayin glyph) or `atw-official`. Per the source-wide ayin convention, this should appear in titles as `ʾtw-official` or simply `atw-official` PM-verbatim. The role classification is `"Official"` regardless.

**"warb-priest" / "waab-priest" drift.** PM `waʿb-priest` (the *w3b*-priest) renders as either `warb-priest` (with raised-`r` for ayin) or `waab-priest` (with raised-`a`) in the text layer. Normalise both to `waʿb-priest` per the chunk-1 + chunk-9 source-wide ayin convention.

## Field-by-field rules

- **`tomb_id`** — `JKR-<TitleCaseAsciiName>` for named tombs; `S<NUM>` for Steindorff numbers. Drop ASCII-incompatible glyphs (ayin, underdot) from `tomb_id`; they live in `occupant_name`. For bracketed Roman regnal, append the Roman without brackets and without spaces (abstract form `JKR-<Name>I`, `JKR-<Name>II`).
- **`memphite_area`** — Always `"Giza"` for chunk 10.
- **`occupant_name`** — Title-cased conventional English form, with raised-ayin normalised to U+02BF, underdot-Ḥ on known *ḥ*-root names, macron-Ē on Re-deity-compound names, Roman regnal appended with space (abstract form `<Name> I`, `<Name> II`). `null` for Shape-2 S-numbered bare-headword.
- **`occupant_alt_names`** — When PM prints `<NAME> good name <ALT>` after the primary name, capture the alt form here.
- **`tomb_aliases`** — For Shape-2 twin-numbered S-tombs (`S <NUM1>/<NUM2>`), the second number goes here as `["S <NUM2>"]` (PM-verbatim with the space). For named tombs, empty `[]` unless PM appends an explicit Lepsius LG cross-reference.
- **`co_occupants`** — Empty `[]` unless PM's headword block (or immediately-adjacent body line `Wife, <NAME> ...` / `Parents, <NAME> ...`) explicitly lists buried persons beyond the primary occupant.
- **`co_occupant_roles`** — Empty `[]` whenever `co_occupants` is empty (length-coupled). When populated, each entry holds the title-cluster prose for the corresponding co-occupant.
- **`is_joint_burial`** — `false` for typical rows.
- **`occupant_role`** — Controlled vocabulary derived from the title cluster in the headword:
  - `Vizier`, `Chief Justice and Vizier` → `"Vizier"`
  - `King's son`, `King's son of his body` → `"Prince"`
  - `King's daughter` → `"Princess"`
  - `Prophet`, `Inspector`, `Overseer` (of <X>), `Judge`, `Tenant`, `Director`, `Recruit`, `Royal acquaintance`, `Supervisor`, `Book-keeper`, `Secretary`, `Tutor`, `Steward`, `Elder of the house`, `Overlord of <X>`, `Singer`, `Master`, `Master of secrets`, `Strong-of-voice`, `Hereditary prince` (without `Overlord of <place>`), `Counsel`, `atw-official`, `Greatest of the Ten`, `Eldest of the corps`, `wad-priest`, `waʿb-priest`, `sem-priest`, `ka-servant` → `"Official"`
  - `Prophet of <Goddess>` for a Prophetess (woman, e.g. `Prophetess of Hathor`) → `"Official"` (non-royal female cult title).
  - `High Priest` of any divinity → `"High Priest"`
  - **Named occupant with NO title cluster** (e.g. `<NAME>. <Dating>.`) → `"Official"` (chunks 6/9 default).
  - Bare-suffix S-number Shape-2 (no name, no title) → `"Unknown"`
- **`dynasty`** — Roman→Arabic from PM's `Dyn. <Roman>` token. `"4"` for `Dyn. IV`, `"5"` for `Dyn. V`, `"6"` for `Dyn. VI`. Range tokens use the more specific tail. **Junker's `Late Old Kingdom.` marker → `"6"`** (terminal-Dyn-VI convention; chunk-10 specific). For `Temp. <King>` clauses, derive dynasty from the named king's regnal period.
- **`sub_period`** — `null` for all chunk-10 rows.
- **`date_bce_approx_start`** / **`date_bce_approx_end`** — `null` for all rows.
- **`cemetery`** — `"Junker West"` for every row in chunk 10 (the lone cemetery banner). Note: uses a descriptor cemetery name, NOT a Reisner G-number, parallel to chunk-3's `"Central Field"` precedent.
- **`discovery_year`** / **`discoverer`** — `null` for all rows. (Excavation history is PM body-prose context; the discoverer field is reserved for explicit Phase-A enrichment from archaeological-fieldwork records.)
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM's HEADWORD block literally contains the respective token. Body prose does NOT fire the flag.
- **`attribution_certainty`** — `"attested"` for Shape-1 / Shape-3 named-primary with no hedge. `"probable"` for `Probably`, `(probably)`, `Perhaps`. `"uncertain"` for `(?)`, `possibly`, `tentatively`, AND for all Shape-2 S-numbered bare-headword rows.
- **`shared_with_tombs`** — Empty `[]` unless PM explicitly cross-references via `Also owner of tomb N` or `(tomb <ID>)` in the headword block.
- **`notes_from_pm`** — Verbatim short prose from PM's headword block: title cluster + date marker + cross-reference clauses + wife clause if adjacent. Publication-citation ribbon dropped. PM-faithful preservation. For Shape-2 bare-S-numbered rows, only the dating marker (if any). Per chunks 6–9 convention, the OCCUPANT NAME is dropped from notes (already in `occupant_name`); notes capture title + dating + cross-refs + wife clause.
- **`source_citation`** — `{"page": <printed page where the row's headword first appears>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}`. Use the printed page (physical + 3); verify per-row against right-page running headers.

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk10: <count> rows; <shape1>/<shape2>/<shape3> split; <anomalies or "none">
```

Where `<shape1>` is named-primary, `<shape2>` is S-numbered bare-headword, `<shape3>` is bracketed-Roman-regnal named. Under 100 words.
