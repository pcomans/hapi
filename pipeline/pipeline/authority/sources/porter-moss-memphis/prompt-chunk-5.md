# Extraction prompt — Porter & Moss Vol III.2 (Saqqâra-Dahshûr), Chunk 5

> **Fifth chunk overall; SECOND chunk from PM Vol III.2 (Saqqâra-Dahshûr fascicles, ed. Málek, 1978/1981).** Covers the FRONT half of § I. PYRAMIDS at Saqqâra: the Dyn III / V / VI royal pyramid-complexes from section A through section E, plus the two queens' pyramid-enclosures under Teti's complex. Chunk 4 covered sections F-K (Unis, Pepy I, Isesi, Merenreʿ I, Pepy II + queens). This prompt is **self-contained** — the agent does NOT need to read prior chunks' prompts.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-5-p33-p57.txt` and produce a JSONL file with one structured row per **PM-headworded Saqqâra pyramid-complex or pyramid-enclosure** in the chunk's range. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-row answers. Every field value must trace to something in the chunk file.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1-4 of PM III have shipped (see `reconciled.jsonl`); chunk 5 closes the front half of PM III.2's § I. PYRAMIDS that chunk 4 left open.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part 2. Saqqâra to Dahshûr.* 2nd edition, fascicles ed. Jaromír Málek, 1978/1981.
- Section: **PYRAMID-FIELD OF SAQQÂRA — I. PYRAMIDS — A → E (front half)**, covering the Dyn III / V / VI royal pyramid-complexes and the two named queens' pyramid-enclosures attached to Teti's complex.
- PM III.2 offset for this chunk: **printed = physical + 360** (verify in-chunk by reading the right-page running header on any right-hand physical page — its trailing number IS the printed page).
- The chunk file covers physical pp.33–57 / printed pp.393–417. Per-page markers `=== physical page N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens at physical p.33 with `PYRAMID-FIELD OF $AQQARA / Maps XLI, XLII` followed by the `I. Pyramids` sub-heading and the `A. PYRAMID-COMPLEX OF TETI.` section heading mid-page. The Teti section heading IS the first row-emitting headword in the chunk.
- **Bottom boundary:** the chunk ends inside physical p.57 with `F. PYRAMID-COMPLEX OF UNIS` appearing as a section heading at the bottom. **F. UNIS and onwards is OUT OF SCOPE — chunk 4 already covered it.** Stop emitting rows at the `F. PYRAMID-COMPLEX OF UNIS` section heading.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk5.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk5.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk5.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — full schema, no cross-references)

Every row MUST have these 22 keys (chunks 1-4 schema, including `co_occupant_roles` added in chunk 3); use `null` (not omitted, not empty string) for unknown values.

```json
{
  "tomb_id": "SAQ-<DescriptorName>",
  "memphite_area": "Saqqara",
  "occupant_name": "..." | null,
  "occupant_alt_names": [...],
  "tomb_aliases": [...],
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "King" | "Queen" | "Prince" | "Princess" | "Vizier" | "High Priest" | "Official" | "Royal Family" | "Unknown",
  "dynasty": "3" | "5" | "6",
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": null,
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "is_uninscribed": false,
  "is_usurped": false,
  "attribution_certainty": "attested" | "uncertain",
  "shared_with_tombs": [],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM III.2 2nd ed. 1978/1981", "section": "I"}
}
```

## How to identify a row

This chunk's row-emitting patterns are THREE shapes:

**Shape 1 — Royal pyramid-complex MAIN pyramid.** Each `<LETTER>. PYRAMID-COMPLEX OF <KING>` section opens with a section heading. Inside the section, the main pyramid carries a `PYRAMID.` sub-heading followed by an identification line of the form `Lepsius, <Roman>; Perring and Vyse, <num>.` (sometimes with an additional `el-Haram el-<arabic-popular-name>` clause). The main pyramid attributes to the named KING of the complex (role = `"King"`, attribution = `"attested"`).

**Shape 1b — Step pyramid enclosure (Dyn III variant).** Sections C and D open `<LETTER>. STEP PYRAMID ENCLOSURE OF <KING>` rather than `PYRAMID-COMPLEX OF`. Inside, the main pyramid carries a `STEP PYRAMID.` sub-heading (not `PYRAMID.`) with the same `Lepsius, <Roman>; Perring and Vyse, <num>` identification convention. Same role (`"King"`) and attribution (`"attested"`) as Shape 1.

**Shape 2 — Queen's pyramid-enclosure.** A `PYRAMID-ENCLOSURE OF <QUEEN-NAME>` sub-heading inside Teti's section (PM convention: queens' enclosures sit within the king's complex). Some enclosures carry an internal `PYRAMID.` sub-heading; others go directly from the enclosure heading into `MORTUARY TEMPLE.` body — either way the queen-enclosure headword block IS a row. The enclosure attributes to the named QUEEN (role = `"Queen"`, attribution = `"attested"`).

**Shape 3 — Anonymous structure with no named occupant.** Section `E. 'GREAT ENCLOSURE'` (note the quotes around 'GREAT ENCLOSURE' in PM's heading) is an anonymous Dyn III royal structure with no attested occupant. Emit with `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"`, and `dynasty: "3"` (PM states `Probably Dyn. III` after the heading).

**ROW-EMITTING headwords** in this chunk:
- A. The main pyramid of the section opening the chunk, PLUS two named queen-enclosure sub-rows (each opened by a `PYRAMID-ENCLOSURE OF <QUEEN-NAME>` headword inside section A's body).
- B. The main pyramid of the next king's complex (Dyn V).
- C. The step pyramid of the next king's enclosure (Dyn III).
- D. The step pyramid of the following king's enclosure (Dyn III).
- E. The anonymous `'GREAT ENCLOSURE'` (Shape 3 — no occupant).

**OUT OF SCOPE for rows in this chunk** — do NOT emit rows for:
- Front-matter intro: `PYRAMID-FIELD OF $AQQARA / Maps XLI, XLII / Plan, POCOCKE…` block on physical p.33 (it lists references for the whole Saqqâra pyramid-field, not a single tomb).
- Mortuary Temple, Valley Temple, Causeway, North Enclosure Wall, South Tomb sub-features under each complex — these are sub-architecture, not separate tombs.
- F. PYRAMID-COMPLEX OF UNIS section heading at the bottom of physical p.57 and everything after — chunk 4 territory.
- Body content: pyramid-text catalogues, sarcophagus-find lists, scene catalogues, masons-graffiti lists, statue inventories — these are body items under each pyramid, not headword rows.
- Footnote markers like `1 King's wife (of Teti).` — these are body footnotes attached to the queen-enclosure heading; informative but not a row.

**Headword block ends** at the first sub-feature heading after the section opening: `MORTUARY TEMPLE.`, `VALLEY TEMPLE.`, `CAUSEWAY.`, `BURIAL CHAMBER.`, `PYRAMID-TEXTS.`, `Pyramid-texts.`, `NORTH ENCLOSURE WALL.`, `SOUTH TOMB.`, `Exterior.`, `Interior.`, `Finds, Dyn.`, `Statues.`, `View`, `Plan`, `Plans`, `L. D.`, `Aerial view`, `MARAGIOGLIO`, `LECLANT`, `LAUER`, `GONEIM`, `FIRTH`, `QUIBELL`, `EMERY`. The headword block carries the structured fields; the body is dropped.

## Expected row count

Pre-extraction structural scan of the chunk: 4 royal main-pyramid headwords (sections A, B, C, D — Shape 1 / Shape 1b) + 2 named queen-enclosures inside section A's body (Shape 2) + 1 anonymous structure (section E — Shape 3).

**Total: 7 rows.** If your final count is below 5 or above 9, re-read the chunk file — you've either missed a queen-enclosure or emitted an out-of-scope feature. The actual names go in the rows you extract, not in this prompt.

## PM III.2 text-layer noise (chunk-5-relevant)

The Griffith-Institute scan of PM III.2 has heavy text-layer noise that pypdf reproduces literally. Apply the following rules:

**Hieroglyph-inline garbage:** PM prints royal cartouches and queen-name cartouches inline next to ALL-CAPS headword names. The text layer renders these cartouches as `ED~ J j~~`, `(Hg)~_D.D _D ~`, `j;::`, `I ~ o }o`, `e} ~ o`, `i_l`, etc. — strings of brackets, tildes, dots, and stray Unicode glyphs that are NOT part of the name. **Drop the cartouche garbage** from `occupant_name`; keep only the conventional English name. Examples (rule-form, NOT row-callouts):
- A headword `A. PYRAMID-COMPLEX OF <KING>. <garbage>. Dyn. VI` — the `<garbage>` token after the period is the cartouche; drop.
- A queen-enclosure headword `PYRAMID-ENCLOSURE OF <QUEEN> <garbage>. Dyn. VI` — same drop rule.

**Word-spacing OCR artifacts:** pypdf occasionally inserts a space inside an ALL-CAPS word, or substitutes `~` for `-`. Known patterns in this chunk:
- `PYRAMID-CO MPLEX` → `PYRAMID-COMPLEX` (interior space dropped).
- `PYRAMID~COMPLEX` → `PYRAMID-COMPLEX` (tilde substituted for hyphen).
- `PYRAMID~ENCLOSURE` → `PYRAMID-ENCLOSURE`.
- `ENCLOS URE` → `ENCLOSURE`.
- A section heading may wrap across two text-layer lines when followed by a hieroglyph block — treat the two lines as one heading.

**Regnal numbers:** When PM prints a regnal `I` next to a queen's all-caps name, pypdf may render the cluster as `<NAME>1 I` (an Arabic `1` followed by a space and Roman `I` — OCR artifact). Treat the regnal as `I` (Roman one). The `<NAME>1 I` pattern collapses in `occupant_name` to `<Name> I` (title-cased name + single space + Roman regnal).

**Dynasty rendering:** PM prints dynasties in Roman; OCR variants seen in this chunk:
- `Dyn. VI` (clean) → `"6"`
- `Dyn. V` (clean) → `"5"`
- `Dyn. Ill` (lowercase L+L for Roman `III`) → `"3"` — this is the most common form in C/D/E.

**Footnote anchors:** Some queen-enclosure headings carry a superscript footnote digit that pypdf renders inline at the end of the queen's all-caps name: `PYRAMID-ENCLOSURE OF <QUEEN><digit> <garbage>. Dyn. <Roman>`. The footnote text `<digit> <prose>.` appears at the bottom of the same physical page (typically a "Selected references." or "King's wife..." annotation). Drop the trailing digit from `occupant_name`; the footnote text is body content, not part of the headword.

## Field-by-field rules

- **`tomb_id`** — Descriptor form `SAQ-<DescriptorName>` where `<DescriptorName>` is the title-cased occupant-name (no spaces, hyphens, or punctuation; Roman regnal numbers concatenated). Examples (rule-form): a complex named `<KING>` produces `tomb_id: "SAQ-<King>"`; a queen-enclosure named `<QUEEN><Roman>` produces `tomb_id: "SAQ-<Queen><Roman>"` (e.g. the Dyn-VI queen with regnal `I` becomes `SAQ-<Queen>I`). For the anonymous Great Enclosure (Shape 3), use the descriptor `SAQ-GreatEnclosure` (PascalCase, no quotes, no apostrophe).
- **`memphite_area`** — Always `"Saqqara"` for this chunk.
- **`occupant_name`** — Conventional English form of the royal/queen name. For royal kings: derive from the section heading `<LETTER>. PYRAMID-COMPLEX OF <KING>` or `<LETTER>. STEP PYRAMID ENCLOSURE OF <KING>` (strip the prefix and cartouche garbage). For queen-enclosures: derive from `PYRAMID-ENCLOSURE OF <QUEEN-NAME>` (strip the prefix). Apply title-casing to PM's ALL-CAPS form. **Parenthetical-alias rule:** when a section heading carries the form `<LETTER>. ... OF <PRIMARY-NAME> (<ALIAS>)`, emit `occupant_name: <Primary-Name title-cased>` (PM's primary form) and capture the parenthetical token in `occupant_alt_names`. For the Shape-3 anonymous structure, `occupant_name: null`.
- **`occupant_alt_names`** — Alt-name forms that appear verbatim in the headword block (typically a parenthetical alias on the heading line). Greek/Latin names that are NOT in PM's headword should NOT be imported (i.e., do not draw on prior knowledge to add aliases that the chunk file doesn't carry).
- **`tomb_aliases`** — Popular pyramid-aliases from the `Lepsius, <Roman>; Perring and Vyse, <num>` identification line's tail clauses. PM may append an Arabic popular-name token of the form `el-Haram el-<token>` (and similar transliterated Arabic descriptors) after the Lepsius/Perring-Vyse pair. Extract any such clause as a single string into `tomb_aliases`. Empty `[]` if the identification line carries no popular-name clause, OR if the `PYRAMID.` / `STEP PYRAMID.` sub-heading carries no identification line at all.
- **`co_occupants`** — Empty `[]` for all rows in this chunk. The queen-enclosures are SEPARATE rows from their kings (not co-burials in a shared tomb).
- **`co_occupant_roles`** — Empty `[]` for all rows in this chunk (parallel array with `co_occupants`, length-coupled).
- **`is_joint_burial`** — `false` for all rows.
- **`occupant_role`** — `"King"` for the main pyramid of any `PYRAMID-COMPLEX OF <KING>` or `STEP PYRAMID ENCLOSURE OF <KING>` section. `"Queen"` for any `PYRAMID-ENCLOSURE OF <QUEEN-NAME>` headword. `"Unknown"` for the Shape-3 anonymous Great Enclosure.
- **`dynasty`** — Derived from PM's `Dyn. <Roman>` token in the headword block. Roman→Arabic: `Dyn. III` (or OCR variant `Dyn. Ill`) → `"3"`, `Dyn. V` → `"5"`, `Dyn. VI` → `"6"`. The royal section heading takes the form `<LETTER>. PYRAMID-COMPLEX OF <KING>. <garbage>. Dyn. <Roman>` — the dynasty tag appears on the same line as the section heading. Queen-enclosures inherit the dynasty of their king's complex; PM also prints `Dyn. <Roman>` after each queen-enclosure headword. For the Great Enclosure, PM prints `Probably Dyn. III` after the section heading — extract dynasty `"3"` and set `attribution_certainty: "uncertain"`.
- **`sub_period`** — `null` for all rows.
- **`date_bce_approx_start`** / **`date_bce_approx_end`** — `null` for all rows.
- **`cemetery`** — `null` for all chunk-5 rows (the pyramid IS its own complex; no surrounding-cemetery designation as PM lists these under § I. PYRAMIDS).
- **`discovery_year`** / **`discoverer`** — `null` for all rows. Modern excavation history is body content, not headword.
- **`is_unfinished`** — `true` if and only if the row's `PYRAMID.` or `STEP PYRAMID.` sub-heading line literally contains the word `Unfinished`. `false` otherwise.
- **`is_uninscribed`** — `false` unless PM headword block literally says `uninscribed`.
- **`is_usurped`** — `false` unless PM headword block literally says `usurp(ed|ation)`.
- **`attribution_certainty`** — `"attested"` for any row whose headword names an occupant (Shape 1 / 1b king-rows and Shape 2 queen-rows whose name appears in PM's heading). `"uncertain"` for any Shape-3 anonymous row AND any row whose headword PM marks with `Probably`, `(?)`, or `possibly`.
- **`shared_with_tombs`** — Empty `[]` for all rows. No architectural twin-mastaba links in this chunk.
- **`notes_from_pm`** — Verbatim short prose from PM's headword block: the section-heading line (with cartouche garbage dropped) + the `PYRAMID.` / `STEP PYRAMID.` sub-heading line with its `Lepsius, <Roman>; Perring and Vyse, <num>` identification line + the popular-name clause when present. PM-faithful preservation of words and punctuation; drop only the cartouche-glyph runs and bibliographic citations after the identification line. If a row has no `PYRAMID.` sub-heading inside its section (some queen-enclosures go directly into `MORTUARY TEMPLE.`), the notes carry just the enclosure heading line cleaned up. If a row has only a section heading and no `PYRAMID.` line at all (Shape-3 anonymous structure), the notes carry the section-heading line cleaned up. Trim trailing whitespace.
- **`source_citation`** — `{"page": <printed page where the row's headword first appears>, "edition": "PM III.2 2nd ed. 1978/1981", "section": "I"}`. Derive the printed page from the offset rule `printed = physical + 360` for this chunk's range, and verify per-row against the right-page running header `Pyramid-complex of <King> <N>` or `Pyramid-enclosure of <Queen> <N>` (the trailing `<N>` IS the printed page number for that right-hand page). The page is the FIRST printed page on which the headword appears, not where it ends. When a row's headword sits on a left-hand physical page (no running header), use the offset rule + nearest verified anchor.

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk5: <count> rows; <kings>/<queens>/<unknowns> split; <anomalies or "none">
```

Where `<kings>` is the count of King rows, `<queens>` is the count of Queen rows, and `<unknowns>` is the count of Unknown rows (Shape 3 Great Enclosure).

Example: `agent-a-chunk5: <N> rows; <K>/<Q>/<U> split; <anomalies or "none">`. Under 80 words including any anomaly note.
