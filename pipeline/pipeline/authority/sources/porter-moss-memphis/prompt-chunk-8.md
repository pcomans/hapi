# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 8

> **Eighth chunk drawn from PM Vol III** — third West Field chunk. Chunk 6 covered G 1000–G 1900 (Junker), chunk 7 covered G 2000 + G 2100 + Mastaba G 2220. This chunk covers Cemetery G 2300 + Cemetery G 2400 + Cemetery G 2500 — Reisner's "Cemetery en Echelon" North Part and the smaller G 2500 cluster. Dense Dyn V–VI official material. This prompt is **self-contained** — the agent does NOT need to read prior chunks' prompts.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-8-p80-p92.txt` and produce a JSONL file with one structured row per **PM-headworded Reisner-numbered mastaba** in Cemetery G 2300 + Cemetery G 2400 + Cemetery G 2500 within the **A. WEST FIELD** section of `§ III. NECROPOLIS`. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-row answers. Every field value must trace to something in the chunk file.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–7 have already shipped (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — A. WEST FIELD** continuation, Cemetery G 2300 + Cemetery G 2400 (under the "Cemetery en Echelon North Part" banner) and Cemetery G 2500.
- PM III.1 offset for this chunk: **printed = physical + 3** (verify in-chunk via the right-page running header `West Field <N>`).
- The chunk file covers physical pp.80–92 / printed pp.83–95. Per-page markers `=== PHYS PAGE N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens at physical p.80 mid-way through the **G 2220** mastaba block (chunk-7 territory; already extracted). The first IN-SCOPE row begins at the `CEMETERY EN ECHELON. NORTH PART WITH MASTABAS G 2300 AND 2400` banner near the bottom of physical p.80. Skip the G 2220 overflow above that banner — it is chunk-7's row and is OUT OF SCOPE here.
- **Bottom boundary:** the chunk file has been truncated immediately before the `CEMETERY G 3000` banner on physical p.92. Every row in the file is in scope; the last row is `G 2501` on physical p.92. The chunk file does NOT contain G 3000 material.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk8.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk8.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk8.jsonl`

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
  "cemetery": "G 2300" | "G 2400" | "G 2500",
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
- Each Reisner-numbered mastaba `G <NNNN>.` or `G <NNNN1>+<NNNN2>.` headword within the chunk's cemetery range (G 2300 + G 2400 + G 2500).
- Both Shape-1 named, Shape-2 bare-suffix, and Shape-3 compound forms.
- An annexe sub-tomb headword like `G <NNNN>-<Roman>-annexe.` — emit a row with `tomb_id: G<NNNN>a` (lowercase letter suffix `a`, matching the chunk-7 G2100a precedent).

Do NOT emit rows for:
- Sub-shaft references within a parent mastaba's headword line (`G 2374 with shaft G 2385A.` — the parent is G2374; `G2385A` is a shaft INSIDE G 2374, NOT a standalone tomb). Same for `G 2381 with shaft G 2382A.` (parent G2381; G2382A is a shaft inside it).
- The CEMETERY banner lines (`CEMETERY EN ECHELON. NORTH PART WITH MASTABAS G 2300 AND 2400`, `CEMETERY G 2500`) — section dividers, not rows.
- The G 2220 mastaba overflow at the top of the file (chunk 7's row, already in `reconciled.jsonl`).
- The `CEMETERY G 3000` banner — absent from the chunk file by design (chunk truncated above it).
- Cross-references to G 1000s, G 4000s, G 7000s (other chunks).
- Body-prose mentions of objects (statues, false-doors, lintels, slabs with secondary names) — these are body items inside a parent headword block.
- Mortuary chapels, serdabs, boat-pits, satellite chapels — sub-features of a parent mastaba.
- Cross-reference lines like `G 2373, probably from here, in Boston Mus. ...` — this is a body-prose CROSS-REFERENCE to another tomb, not a standalone G 2373 headword. Only emit G 2373 if it has its own headword block elsewhere in the chunk.

**Headword block ends** at the first sub-feature heading after the Reisner-number line: `Mortuary Chapel.`, `Burial Chamber.`, `Chapel.`, `Hall.`, `Serdab.`, `Sloping shaft`, `Plan <Roman>`, `Plans and sections`, `Pillared portico.`, `False-door.`, `Finds`, `Statues.`, or any prose line beginning with a museum-citation token (`Cairo Mus.`, `REISNER`, `JUNKER`, `STEINDORFF`, `SMITH`, `HASSAN`). The headword block carries the structured fields; the body is dropped.

## Expected row count

Pre-extraction structural scan of the chunk: each Reisner-numbered tomb under the CEMETERY EN ECHELON G 2300/G 2400 or CEMETERY G 2500 banners emits one row, in mixed Shape-1/2/3 forms. **Total expected: 28–40 rows.** If your final count is below 22 or above 50, re-read the chunk file — you've either missed cemetery sub-sections or emitted out-of-scope shafts.

## PM III.1 text-layer noise (chunk-8-relevant)

**Raised-ayin in occupant names.** PM prints Egyptological ayin as a small raised glyph; pypdf renders it as a lowercase `a` or `c` mid-word inside otherwise-uppercase names. Normalisation rule: replace the mid-word lowercase `a` or `c` (when it sits between two uppercase letters in an ALL-CAPS name token, or appears as the first character before an otherwise-uppercase continuation) with `ʿ` (U+02BF) and title-case the result. Abstract form examples:
- `<ROOT>a<SUFFIX>` (mid-name ayin between two uppercase blocks) → `<Root>ʿ<suffix>`
- `<PREFIX>aA<ROOT>` → `<Prefix>ʿA<root>` after title-casing
- `a<ROOT>` (leading raised-ayin) → `ʿ<Root>` (leading U+02BF before title-cased root)
- `<ROOT1>-<ROOT2>` (hyphen-joined compound) — apply the rule independently to each side of the hyphen; the hyphen survives.
- An all-caps name token with no lowercase `a`/`c` inside has NO ayin to normalise — title-case as-is.

**Underdot-Ḥ glyph.** When PM prints the Egyptological underdot-Ḥ glyph, pypdf may render it as a mid-word uppercase `H` (`MeHyt` for `Meḥyt`). Normalisation rule: when an all-caps name or title cluster contains a mid-word uppercase `H` flanked by lowercase characters, restore to underdot-Ḥ (`ḥ`). NB: PM's typesetting is asymmetric — some divine-names get the underdot, others don't. Match PM's printed form exactly; don't blanket-apply the underdot.

**"good name" alias convention.** PM prints `<PRIMARY-NAME> good name <ALT-NAME>` to denote a "beautiful name" (Egyptian *rn nfr*) — the secondary personal name an Old Kingdom official commonly used. Capture the PRIMARY name as `occupant_name` and the ALT as a single entry in `occupant_alt_names`. Title-case both. PM's "beautiful name" idiom is the dominant alias source in chunk 8; apply the rule to every such headword you encounter.

**Bare-suffix headword variants** (Shape 2):
- `G <NNNN>.` (purely numeric, nothing more)
- `G <NNNN>. Dyn. VI.`
- `G <NNNN>. Late Dyn. V or later.`
- `G <NNNN>. Position not marked on plan.`
All produce a Shape-2 row: `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`. Dynasty extracted from the dating marker if present.

**Reisner-number formatting drift.** pypdf occasionally inserts spaces inside the Reisner number (`G  2330`, `G 23 30`). Normalise to single-space form in the chunk file mental model; the `tomb_id` strips the space entirely (`G2330`).

**Annexe / shaft / sub-tomb forms.**
- **Annexe headword** `G <NNNN>-<Roman>-annexe.` — standalone row, `tomb_id: G<NNNN>a` (chunk-7 G2100a precedent). Note the verbatim PM identifier in `notes_from_pm`.
- **Letter-suffix sub-headword** `G <NNNN><letter>.` (PM prints a lowercase-letter suffix on its own headword line, abstract form) — standalone row, `tomb_id: G<NNNN><letter>` (preserve the suffix verbatim).
- **Inline "with shaft" clause** `G <NNNN> with shaft G <MMMM>A.` (abstract form) — the parent is G<NNNN>; the shaft G<MMMM>A is INSIDE the parent and does NOT emit its own row. Only the parent G<NNNN> emits a row.

**Multi-line headword carryover.** Some Shape-1 named-primary headwords run two or three printed lines because the title cluster is long — abstract form `G <NNNN>. <NAME> good name <ALT> <Title cluster>, etc. Dyn. <Roman>.`. Concatenate continuation lines into the single headword block until the body / sub-feature heading starts. Don't split a multi-line headword into two rows.

**Cross-reference inside body prose.** A body-prose line that mentions a *different* Reisner number (e.g. `G 2373, probably from here, in Boston Mus. 13.3139.` inside the G 2370 body) is a CROSS-REFERENCE, not a new headword. Do NOT emit a row for the cross-referenced tomb unless it has its own standalone headword block elsewhere in the chunk.

## Field-by-field rules

- **`tomb_id`** — Reisner G-number form `G<NNNN>` (no spaces, no period). For Shape-3 compound twin halves, two separate rows each with their own `G<NNNN>` form. For lowercase-letter-suffix sub-tombs, `G<NNNN><letter>`.
- **`memphite_area`** — Always `"Giza"` for chunk 8.
- **`occupant_name`** — Title-cased conventional English form, with raised-ayin normalised to U+02BF and underdot glyphs restored to ḥ where PM prints them. `null` for Shape-2 bare-suffix.
- **`occupant_alt_names`** — When PM prints `<NAME> good name <ALT>` or `(also <ALT>, see p. <N>)` after the primary name, capture the alt form here (title-cased). PM's "beautiful name" idiom is the dominant alias source in chunk 8.
- **`tomb_aliases`** — Empty `[]` unless PM appends an Arabic popular-name clause or Lepsius LG cross-reference. For Shape-1 rows in chunk 8 typically `[]`. When PM appends an `LG <N>` Lepsius number after the headword/title cluster, capture it as `["LG <N>"]` in `tomb_aliases`.
- **`co_occupants`** — Empty `[]` unless PM's headword explicitly lists two or more named buried persons in the same tomb. Body-prose mentions like `Wife, <NAME> Prophetess of Hathor, etc.` after the headword line ARE explicit co-occupant declarations — capture the wife as a co-occupant with role `"Wife"` (or the printed title cluster).
- **`co_occupant_roles`** — Empty `[]` whenever `co_occupants` is empty (length-coupled).
- **`is_joint_burial`** — `false` for typical rows. `true` only when PM explicitly says coordinate two-or-more burials in the same tomb (the headword itself names two equal occupants joined by `and`, e.g. abstract form `G <NNNN>. <NAME1> and wife <NAME2>.`).
- **`occupant_role`** — Controlled vocabulary derived from the title cluster in the headword:
  - `Vizier`, `Chief Justice and Vizier` → `"Vizier"`
  - `King's son`, `King's son of his body`, `Eldest son of the King` → `"Prince"` (named-male royal)
  - `King's daughter` → `"Princess"` (named-female royal)
  - `Prophet`, `Inspector`, `Overseer`, `Judge`, `Tenant`, `Director`, `Strong-of-voice`, `Royal acquaintance` (incl. `(woman)` — non-royal honorific), `Supervisor`, `Book-keeper`, `Secretary`, `Craftsman`, `Keeper of Nekhen`, `Elder of the Hall`, `Greatest of the Ten`, `Flutist`, `Overseer of barbers`, `Overseer of commissions`, `wad-priest`, `waab-priest`, `sem-priest` → `"Official"`
  - `High Priest` of any divinity → `"High Priest"`
  - **Named occupant with NO title cluster** (e.g. `G 2336.` with body-prose only) → `"Official"` (most common OK Memphite non-royal role).
  - Bare-suffix Shape-2 (no name, no title) → `"Unknown"`
- **`dynasty`** — Roman→Arabic from PM's `Dyn. <Roman>` token. `"4"` for `Dyn. IV`, `"5"` for `Dyn. V`, `"6"` for `Dyn. VI`. For range tokens (`Dyn. V-VI`, `Late Dyn. V or later`, `End of Dyn. V or later`), use the more specific tail (`V-VI` → `"6"`; `Late Dyn. V or later` → `"6"`; `End of Dyn. V` → `"5"`). pypdf occasionally renders `Dyn. VI` as `Dyn. vr` (lowercase OCR drift); treat as `Dyn. VI` → `"6"`. `null` ONLY when PM's headword carries no dating clue at all.
- **`sub_period`** — `null` for all chunk-8 rows.
- **`date_bce_approx_start`** / **`date_bce_approx_end`** — `null` for all rows.
- **`cemetery`** — `"G 2300"` for rows under the CEMETERY EN ECHELON banner whose Reisner number falls in the 2300–2399 range; `"G 2400"` for the 2400–2499 range; `"G 2500"` for rows under the CEMETERY G 2500 banner (2500–2599). Use the Reisner-number range, not the banner-text wording.
- **`discovery_year`** / **`discoverer`** — `null` for all rows.
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM's HEADWORD block literally contains the respective token. Body prose like `Rock-cut tomb, unfinished.` does NOT fire the flag (chunk-6 G 1607 precedent — only headword-line `unfinished` counts).
- **`attribution_certainty`** — `"attested"` for Shape-1 named-primary with no hedge. `"probable"` for `Probably`, `(probably)`, `Perhaps`. `"uncertain"` for `(?)`, `possibly`, `tentatively`, attributed-to phrasing, AND for all Shape-2 bare-suffix rows.
- **`shared_with_tombs`** — Reisner-form `tomb_id` of the twin half for Shape-3 compound rows; otherwise empty `[]` unless PM explicitly cross-references via `Also owner of tomb N`.
- **`notes_from_pm`** — Verbatim short prose from PM's headword block: title cluster + date marker + cross-reference clauses, publication-citation ribbon dropped. PM-faithful preservation of words and punctuation. For Shape-2 rows, only the dating marker (if any) — pure-numeric stubs get `notes_from_pm: null`. Per chunk-6/7 convention, the OCCUPANT NAME itself is dropped from notes (already lives in `occupant_name`); notes capture title + dating + cross-refs only.
- **`source_citation`** — `{"page": <printed page where the row's headword first appears>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}`. Use the printed page (physical + 3); verify per-row against right-page running headers.

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk8: <count> rows; <shape1>/<shape2>/<shape3> split; cemeteries G 2300 = <count1>, G 2400 = <count2>, G 2500 = <count3>; <anomalies or "none">
```

Where `<shape1>` is the count of named-primary rows, `<shape2>` is the count of bare-suffix rows, and `<shape3>` is the count of compound-twin rows. Under 100 words.
