# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 6

> **Sixth chunk drawn from PM Vol III** — and the SECOND chunk from PM Vol III.1's § III. NECROPOLIS, opening the WEST FIELD sub-section A. Chunk 2 already covered the East Field (G 7000 cluster); chunk 6 covers the densely-Junker-excavated West Field cemeteries G 1000 → G 1900. This prompt is **self-contained** — the agent does NOT need to read prior chunks' prompts. Every field rule, schema invariant, and noise pattern is documented here in full.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-6-p46-p62.txt` and produce a JSONL file with one structured row per **PM-headworded Reisner-numbered mastaba** in the **A. WEST FIELD** section of `§ III. NECROPOLIS` within the Pyramid-Field of Gîza, restricted to the cemetery range opened in this chunk file. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-row answers. Every field value must trace to something in the chunk file. Per-row values for individual mastaba occupants are NOT supplied here — derive them from the chunk file's headwords.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–5 of PM III have already shipped (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — A. WEST FIELD** (Reisner-numbered mastabas immediately west of Khufu's pyramid, Junker / Steindorff cemeteries).
- PM III.1 offset for this chunk: **printed = physical + 3** (verify in-chunk via the right-page running header `West Field <N>` where `<N>` IS the printed page).
- The chunk file covers physical pp.46–62 / printed pp.49–65. Per-page markers `=== physical page N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens at physical p.46 with the `A. WEST FIELD` section heading and Junker's introductory references (chronology of his Vienna-Cairo expedition campaigns 1912–1929, plan references, etc.). The first CEMETERY banner `CEMETERY G 1000` appears mid-chunk — that banner is NOT itself a row; rows begin at the first `G <NNNN>.` headword within G 1000.
- **Bottom boundary:** the chunk ends inside Cemetery G 1900 (the smallest of the West Field family of low-thousands cemeteries) on physical p.62. The next CEMETERY banner — opening the G 2000 series — falls just past the chunk boundary on physical p.63, OUT of this chunk.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk6.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk6.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk6.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — full schema, no cross-references)

Every row MUST have these 22 keys; use `null` (not omitted, not empty string) for unknown values.

```json
{
  "tomb_id": "G<NNNN>" | "G<NNNN><lowercase-letter>",
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
  "cemetery": "G 1000" | "G 1100" | "G 1200" | "G 1300" | "G 1400" | "G 1500" | "G 1600" | "G 1900",
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

This chunk's rows are PM-headworded Reisner-numbered mastabas in two shapes:

**Shape 1 — Named primary headword.** A line starting with `G <NNNN>. <OCCUPANT NAME IN CAPS> <Title>, <Title>, etc. <Date>.` followed by Junker / publication body refs. The all-caps name token (which may itself contain mid-name raised-`a`-style OCR clusters for the Egyptological ayin, see Noise rules below) IS the conventional English form of the occupant. Title-case it for `occupant_name`. Titles and date are body content of the headword block — they go to `notes_from_pm`, not into separate role/sub_period fields (occupant_role is derived from the title cluster as below).

**Shape 2 — Bare-suffix headword.** A line starting with `G <NNNN>.` followed by either nothing more (purely numeric stub), or only a dating marker like `Dyn. V.`, or only `Not marked on plan.`, or only a single short body clause like `Late Dyn. IV.`. The headword carries NO occupant-name token. Emit one row with `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`. The dating marker, if present, goes to `dynasty` after Roman→Arabic normalisation; otherwise `dynasty: null`.

**Shape 3 — Compound twin-mastaba headword.** A line starting with `G <NNNN1>+<NNNN2>. <OCCUPANT NAME IN CAPS> <Title>, <Title>, etc.` — PM's convention for two Reisner-numbered mastabas grouped under one headword (typically because excavator/publication treats them jointly or they share a structural feature). Emit ONE row per Reisner number (so the compound emits TWO rows). Both rows inherit the same occupant-name token from the compound headword UNLESS PM separately gives one or both sub-numbers their own standalone headword line later in the section (in which case the standalone line's occupant_name wins for that half). Each row gets `shared_with_tombs: ["G<other>"]` cross-referencing the twin half. Chunk-2 precedent: G 7110+7120 KAWAaB ... and wife HETEPHERES [11], with both halves printed as standalone sub-rows below the compound. Chunk-6 may have compound headwords in the West Field G 1400 / G 1500 range and elsewhere — handle each rigorously when encountered.

**ROW-EMITTING vs OUT-OF-SCOPE in this chunk.** Emit one row per:
- Each Reisner-numbered mastaba `G <NNNN>.` headword within the chunk's range (G 1000–G 1900 cemeteries).
- Both shape-1 named primary headwords AND shape-2 bare-suffix headwords.

Do NOT emit rows for:
- Sub-shaft references within a parent mastaba (e.g., `G 1213a`, `G 1226A` — these are shafts inside the parent, not standalone tombs unless PM gives them their own primary headword block). Shaft IDs without an own headword block stay as body content.
- The CEMETERY banner lines (`CEMETERY G 1000`, `CEMETERY G 1100`, etc.) — these are section dividers, not rows.
- Body-prose mentions of mastabas outside the chunk's cemetery range (cross-references to G 4000s, G 7000s — those are chunk-7+ rows; in this chunk they're cross-reference text only).
- Find-listings (statues, false-doors, lintels, slabs with names of secondary persons) — these are body items inside a parent headword block.
- Mortuary chapels, serdabs, boat-pits, satellite chapels — sub-features of a parent mastaba.
- Cemetery G 2000 or higher (out of chunk).

**Headword block ends** at the first sub-feature heading after the Reisner-number line: `Mortuary Chapel.`, `Burial Chamber.`, `Chapel.`, `Hall.`, `Serdab.`, `Sloping shaft`, `Plan <Roman>`, `Plans and sections`, `Pillared portico.`, `False-door.`, `Finds`, or any prose line beginning with a museum-citation token (`Cairo Mus.`, `REISNER`, `JUNKER`, `STEINDORFF`, `SMITH`). The headword block carries the structured fields; the body is dropped.

## Expected row count

Pre-extraction structural scan of the chunk file: 8 CEMETERY banner lines (not rows) + dozens of `G <NNNN>.` headword lines split between Shape 1 (named) and Shape 2 (bare-suffix). The exact split between shapes per cemetery is for the extractor to compute — count every `G <NNNN>.` line within the cemetery-banner range whose continuation is not a sub-feature heading.

**Total expected: 40–60 rows.** If your final count is below 30 or above 75, re-read the chunk file — you've either missed cemetery sub-sections or emitted out-of-scope shafts.

## PM III.1 text-layer noise (chunk-6-relevant)

The Griffith-Institute scan of PM III.1 has structured text-layer noise that pypdf reproduces literally:

**Raised-ayin in occupant names.** PM prints Egyptological ayin as a small raised glyph; pypdf renders it as a lowercase `a` or `c` mid-word inside otherwise-uppercase names. Normalisation rule: replace the mid-word lowercase `a` or `c` (when it sits between two uppercase letters in an ALL-CAPS name token, or appears as the first character before an otherwise-uppercase continuation) with `ʿ` (U+02BF) and title-case the result. Abstract form examples:
- `<ROOT>a<SUFFIX>` (mid-name ayin between two uppercase blocks) → `<Root>ʿ<suffix>`
- `<PREFIX>aA<ROOT>` (raised-ayin between an uppercase letter and a following uppercase `A`) → `<Prefix>ʿA<root>` after title-casing, i.e. the U+02BF replaces the mid-name lowercase `a` and the following uppercase block continues
- `a<ROOT>` (leading raised-ayin at the start of an all-caps name token) → `ʿ<Root>` (leading U+02BF before title-cased root)
- `<ROOT1>-<ROOT2>` or `<ROOT1>a-<ROOT2>` (hyphen-joined compound) — apply the rule independently to each side of the hyphen; the hyphen survives.
- An all-caps name token with no lowercase `a`/`c` inside it has NO ayin to normalise — title-case as-is.

**Numbered references inside an occupant name token.** PM often appends a footnote-anchor digit immediately after an all-caps name (e.g. `<NAME>1`); pypdf renders it inline. Strip trailing digits from `occupant_name` after title-casing; the digit's footnote prose is body content.

**Bare-suffix headword variants.** Within the chunk, the bare-suffix Shape 2 takes several forms:
- `G <NNNN>.` (purely numeric, nothing follows on the line)
- `G <NNNN>. Dyn. V.` (only a dating marker)
- `G <NNNN>. Late Dyn. IV.` / `G <NNNN>. Late Dyn. V or Dyn. VI.` (dating with qualifier)
- `G <NNNN>. Not marked on plan.` (PM's plan-cross-ref marker, no occupant)
- `G <NNNN>. Second half of Dyn. V.` (dating only)
All produce a Shape 2 row: `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`. Dynasty extracted from the dating marker if present; null otherwise. PM's plan-cross-ref text goes to `notes_from_pm`.

**Reisner-number formatting drift.** pypdf occasionally inserts spaces inside the Reisner number (`G  1207`, `G 1 207`). Normalise to single-space form `G <NNNN>` in the chunk file mental model; the `tomb_id` strips the space entirely (`G1207`).

**Letter-suffix shafts.** Some shafts have letter-suffix IDs like `G 1213a` (lowercase suffix for sub-shafts) or `G 1226A` (uppercase). Per the chunk-2 + chunk-1 precedent, lowercase-letter suffixes are typically secondary shafts of the same parent and do NOT emit their own row; uppercase X (as in chunk-2's G7000X) is reserved for extension-shafts. For chunk 6's range, treat any `G <NNNN><letter>` form as a sub-shaft of `G <NNNN>` and do NOT emit a separate row UNLESS PM gives it a standalone headword block (Reisner number on its own line followed by an occupant-name + title cluster).

**Sub-period spelling.** PM uses Roman-numeral dynasty forms (`Dyn. IV`, `Dyn. V`, `Dyn. VI`) with optional qualifiers (`Early`, `Late`, `Middle`, `Second half of`, hyphenated ranges `Dyn. V-VI`). Normalise dynasty to Arabic string `"4"` / `"5"` / `"6"` for the primary value; range tokens (`V-VI`) prefer the more specific tail (`"6"`). Sub-period qualifiers (`Early`, `Late`, `Middle`) stay in `notes_from_pm`; the chunk-6 schema does not have a dedicated qualifier field (sub_period is null for all chunk-6 rows).

## Field-by-field rules

- **`tomb_id`** — Reisner G-number form `G<NNNN>` (no spaces, no period). Letter-suffix shafts (`G<NNNN><letter>`) ONLY when PM emits a separate standalone headword block for the shaft.
- **`memphite_area`** — Always `"Giza"` for chunk 6.
- **`occupant_name`** — Title-cased conventional English form of the all-caps name token in the headword, with raised-ayin glyphs normalised to U+02BF. `null` for Shape-2 bare-suffix headwords.
- **`occupant_alt_names`** — Empty `[]` unless PM explicitly prints an alt-name phrase like `good name <ALT>` after the primary name (Egyptological "good name" convention for an attested alternate). Drop museum-conventional aliases unless PM lists them.
- **`tomb_aliases`** — Empty `[]` unless PM appends an Arabic popular-name clause or a Lepsius LG cross-reference. For named West Field mastabas without alias clauses, `[]`.
- **`co_occupants`** — Empty `[]` for the typical single-occupant chunk-6 row. For a compound twin-mastaba headword (Shape 3 above) PM groups two Reisner numbers under one occupant; emit one row per Reisner number with the compound's occupant as the SHARED primary on both rows, and use `shared_with_tombs` (NOT `co_occupants`) to cross-reference the twin half. Reserve `co_occupants` for a single tomb whose headword PM explicitly lists two-or-more distinct buried persons.
- **`co_occupant_roles`** — Empty `[]` whenever `co_occupants` is empty (parallel array, length-coupled).
- **`is_joint_burial`** — `false` for the typical chunk-6 row. Set `true` only when PM's headword block explicitly says the tomb holds two-or-more coordinate burials (rare in the West Field).
- **`occupant_role`** — Controlled vocabulary derived from the title cluster in the headword. Mapping:
  - Title cluster includes `Vizier`, `Chief Justice and Vizier` → `"Vizier"`
  - Title cluster includes `King's son`, `Eldest son of the King`, `King's son of his body` → `"Prince"` (for named-male royals)
  - Title cluster includes `King's daughter` → `"Princess"` (female royal directly descended from a king)
  - Title cluster includes `Hereditary prince` AND `Overlord of <place>` → `"Royal Family"` (administrator-prince hybrid, see chunk-2 precedent G 7060 NEFERMAaET)
  - Title cluster includes `Prophet`, `Inspector`, `Overseer`, `Judge`, `Tenant`, `Director`, `Strong-of-voice`, `Royal acquaintance` (male), `Royal acquaintance (woman)`, `Supervisor`, `Book-keeper`, `Secretary`, `Craftsman`, `wad-priest`, `waab-priest` → `"Official"`. **NB: `Royal acquaintance (woman)` (the Egyptological *rḫt-nswt*) is a non-royal honorific court title held by elite women — NOT a royal-family descent indicator. Map to `Official`, NOT `Royal Family` or `Princess`.**
  - Title cluster includes `High Priest` of any divinity → `"High Priest"`
  - **Named occupant with NO title cluster** (e.g. `G NNNN. <NAME>. <dating only>`) → `"Official"` (the most common Old-Kingdom Memphite non-royal role). `Unknown` is reserved for Shape-2 bare-suffix headwords (no name AT ALL).
  - Bare-suffix Shape-2 headwords (no name, no title cluster) → `"Unknown"`
- **`dynasty`** — Roman→Arabic from PM's `Dyn. <Roman>` token in the headword block. `"4"` for `Dyn. IV`, `"5"` for `Dyn. V`, `"6"` for `Dyn. VI`. For range tokens (`Dyn. V-VI`, `Dyn. IV-V`), use the more specific tail (e.g. `V-VI` → `"6"`). For temporal markers without a dynasty number (`Temp. Khufu`, `Temp. Khephren`, `Middle Dyn. V`), still derive the dynasty number from PM's context (`Temp. Khufu` implies `"4"`). `null` ONLY when PM's headword carries no dating clue.
- **`sub_period`** — `null` for all chunk 6 rows.
- **`date_bce_approx_start` / `date_bce_approx_end`** — `null` for all chunk 6 rows.
- **`cemetery`** — Match the most-recent CEMETERY banner line above the row in the chunk file: `"G 1000"`, `"G 1100"`, `"G 1200"`, `"G 1300"`, `"G 1400"`, `"G 1500"`, `"G 1600"`, or `"G 1900"`. Each row inherits the banner of the cemetery it falls under.
- **`discovery_year` / `discoverer`** — `null` for all chunk 6 rows (modern excavation history is body content, not headword).
- **`is_unfinished` / `is_uninscribed` / `is_usurped`** — `false` unless the PM headword block literally carries `unfinished` / `uninscribed` / `usurp(ed|ation)` respectively.
- **`attribution_certainty`** — `"attested"` for Shape-1 named primary headwords with no hedge token. `"probable"` for headwords with `Probably`, `(probably)`, `Perhaps`. `"uncertain"` for headwords with `(?)`, `possibly`, `tentatively`, attributed-to phrasing, AND for all Shape-2 bare-suffix headwords.
- **`shared_with_tombs`** — Empty `[]` for chunk 6 unless PM cross-references via `Also owner of tomb N` or `See tomb N for partner` phrasing. Drop ordinary `See p.<N>` cross-references; those are body text.
- **`notes_from_pm`** — Verbatim short prose from PM's headword block: the title cluster + date marker, with publication-citation ribbon dropped. PM-faithful preservation of words and punctuation. For Shape-2 rows, only the dating marker (if any) goes to notes; pure-numeric stubs get `notes_from_pm: null`.
- **`source_citation`** — `{"page": <printed page where the row's headword first appears>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}`. Use the printed page (physical + 3 for this chunk's range; verify per-row against right-page running headers).

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk6: <count> rows; <shape1>/<shape2> split; <cemeteries hit, comma-sep>; <anomalies or "none">
```

Where `<shape1>` is the count of named-primary rows and `<shape2>` is the count of bare-suffix rows. Under 100 words including any anomaly note.
