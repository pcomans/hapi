# Extraction prompt — Porter & Moss Vol III.2 (Saqqâra-Dahshûr), Chunk 4

> **Fourth chunk drawn from PM Vol III** — and the FIRST chunk from PM Vol III.2 (Saqqâra-Dahshûr fascicles, ed. Málek, 1978/1981). Covers the back half of § I. PYRAMIDS at Saqqâra: the Dyn V/VI royal pyramid-complexes from section F through section K, plus their queens' pyramid-enclosures. This prompt is **self-contained** — the agent does NOT need to read prior chunks' prompts.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-4-p61-p72.txt` and produce a JSONL file with one structured row per **PM-headworded Saqqâra pyramid-complex** in the chunk's range. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-row answers. Every field value must trace to something in the chunk file.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1-3 of PM III.1 have shipped (see `reconciled.jsonl`); chunk 4 is the first PM III.2 chunk.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part 2. Saqqâra to Dahshûr.* 2nd edition, fascicles ed. Jaromír Málek, 1978/1981. (Different volume from chunks 1-3, which used PM III.1.)
- Section: **PYRAMID-FIELD OF SAQQÂRA — I. PYRAMIDS — F → K (back half)**, covering the Dyn V/VI royal pyramid-complexes and their queens' pyramid-enclosures.
- PM III.2 offset for this chunk: **printed = physical + 360** (verified at physical p.61 with right-page running header `Pyramid-complex of … 421` and at physical p.67 with `Pyramid-complex of … 427`).
- The chunk file covers physical pp.61–72 / printed pp.421–432. Per-page markers `=== physical page N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens mid-page on physical p.61 with the running header `Pyramid-complex of … 421`. The F. PYRAMID-COMPLEX OF … section heading was on the page BEFORE the chunk (out of file). Body content (mortuary temple, valley temple) precedes the F-section `PYRAMID.` sub-heading on line 21 of the chunk file — that `PYRAMID.` sub-heading is the FIRST emit-row in the chunk.
- **Bottom boundary:** the chunk ends inside K's queen-enclosure block. The third queen's `PYRAMID-ENCLOSURE OF …` headword appears on physical p.72 but her `PYRAMID.` sub-heading and continuing content extend onto physical p.73, OUT of this chunk. The L. BURIAL-COMPLEX OF SHEPSESKAF heading on physical p.73 is out of scope.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk4.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk4.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk4.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — full schema, no cross-references)

Every row MUST have these 22 keys (chunks 1-3 schema + `co_occupant_roles` added in chunk-3 PR); use `null` (not omitted, not empty string) for unknown values.

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
  "dynasty": "5" | "6",
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

This chunk's row-emitting patterns are TWO shapes:

**Shape 1 — Royal pyramid-complex MAIN pyramid.** Each `PYRAMID-COMPLEX OF <KING>` section (PM lettered A through N) opens with a section heading. Inside the section, the main pyramid carries a `PYRAMID.` sub-heading followed by an identification line of the form `Lepsius, <Roman>; Perring and Vyse, <num>.` (sometimes with an additional `<popular name>` clause). The main pyramid attributes to the named KING of the complex (role = `"King"`, attribution = `"attested"`).

**Shape 2 — Queen's pyramid-enclosure.** A `PYRAMID-ENCLOSURE OF <QUEEN-NAME>` sub-heading (PM convention: queens' enclosures sit within or after the king's complex). Each enclosure has its own `PYRAMID.` sub-heading and identification line. The enclosure attributes to the named QUEEN (role = `"Queen"`, attribution = `"attested"`). Anonymous variants (`PYRAMID-ENCLOSURE PROBABLY OF WIFE OF <KING>`) carry `occupant_name: null` and `attribution_certainty: "uncertain"`.

**ROW-EMITTING headwords** in this chunk:
- F. The main pyramid of the section opening the chunk.
- G. The main pyramid of the next king's complex.
- H. Two sub-headwords: the main pyramid + an anonymous queen-enclosure of the form `PYRAMID-ENCLOSURE PROBABLY OF WIFE OF <KING>`.
- I. The main pyramid of the following king's complex.
- K. The main pyramid of the final king's complex in this chunk's range, PLUS three named queen-enclosure sub-rows (each headed `PYRAMID-ENCLOSURE OF <QUEEN-NAME>`).

**OUT OF SCOPE for rows in this chunk** — do NOT emit rows for:
- The body content of F. UNIS's complex that precedes the `PYRAMID.` sub-heading (the chunk file opens mid-section; the section header itself is on the prior physical page).
- Mortuary Temple, Valley Temple, Causeway sub-features under each complex — these are sub-architecture, not separate tombs.
- The SUBSIDIARY PYRAMID under each main pyramid (a small cult pyramid; not a queen's enclosure).
- J. PYRAMID OF KAKARE IBI on physical p.65 — this is a Dyn VIII (post-Old-Kingdom transitional) entry that falls between I. Merenre and K. Pepy II in PM's lettering. Explicitly excluded for chunk-4 MVP scope (Dyn V/VI only).
- L. BURIAL-COMPLEX OF SHEPSESKAF and onwards (on physical p.73, out of file).
- Pyramid-text catalogues, sarcophagus-find lists, scene catalogues — these are body items under each pyramid, not headword rows.

**Headword block ends** at the first sub-feature heading after the section opening: `MORTUARY TEMPLE.`, `VALLEY TEMPLE.`, `CAUSEWAY.`, `BURIAL CHAMBER.`, `PYRAMID-TEXTS.`, `Pyramid-texts.`, `View`, `Plan`, `Plans`, `L. D.`, `}EQUIER`, `LEPSIUS`, `MARIETTE`, `VYSE`, `PERRING`, `BORCHARDT`. The headword block carries the structured fields; the body is dropped.

## Expected row count

Pre-extraction scan of the chunk file: 5 royal main-pyramid headwords (one each in sections F, G, H, I, K) + 1 anonymous queen-enclosure under section H + 3 named queen-enclosures under section K.

**Total: 9 rows.** If your final count is below 7 or above 11, re-read the chunk file — you've either missed a queen-enclosure or emitted an out-of-scope feature.

## PM III.2 text-layer noise (chunk-4-relevant)

The Griffith-Institute scan of PM III.2 has heavy text-layer noise that pypdf reproduces literally. Apply the following rules:

**Hieroglyph-inline garbage:** PM prints royal cartouches and queen-name cartouches inline next to ALL-CAPS headword names. The text layer renders these cartouches as `(0H Q]`, `(ill]::::2 ~ il`, `(0~U]`, `[J\.t~]`, `~_}`, etc. — strings of brackets, tildes, dots, and stray Unicode glyphs that are NOT part of the name. **Drop the cartouche garbage** from `occupant_name`; keep only the conventional English name. Examples (rule-form, NOT row-callouts):
- A headword `K. PYRAMID-COMPLEX OF <KING>. (<garbage>) Dyn. VI` — the `<garbage>` token after the period is the cartouche; drop.
- A queen-enclosure headword `PYRAMID-ENCLOSURE OF <QUEEN> <garbage>. Dyn. VI` — same drop rule.

**Roman/Arabic + diacritic mis-OCR in headword content:** pypdf renders some PM characters with drift. Known patterns:
- `}EQUIER` / `}EQUIER` is a pypdf rendering of `JÉQUIER` (the French Egyptologist who excavated Saqqâra's queen pyramids). Drop bibliographic references entirely from `notes_from_pm` (body-prose citations, not headword fields).
- `J>:.<NAME>c <NAME>` — pypdf rendering of a Dyn VIII king-name with raised-c ayin. Out of scope per chunk-4 boundaries (Dyn VIII excluded).
- A headword name containing `£c` (e.g. `XYZ£c I`) is mis-OCR of a macron-Ē-plus-raised-ayin glyph cluster (PM uses `MERENRĒʿ`-style names where the macron-Ē is the `E` vowel of the `Re` element). Normalisation: replace `£c` with `eʿ` (lowercase `e` + U+02BF ayin). The underlying `Ē` vowel is restored as lowercase `e` after title-casing; the raised-ayin becomes U+02BF. Do NOT use the bare `£c → ʿ` rule (which drops the vowel and produces non-standard forms like `Merenrʿ`). Then apply the raised-ayin rules below if any further raised-ayin glyphs remain.

**Raised-ayin normalisation (carry-over from chunks 1-3):**
- Interior raised-ayin (`XAaY` / `XEcY` in ALL-CAPS) drops the inner lowercase letter; title-case after.
- Leading raised-ayin (`aXY...` / `cXY...`) replaces with `ʿ` (U+02BF), then title-case.
- Trailing raised-ayin (`XYZa` / `XYZc`) replaces with `ʿ` (U+02BF).
- Hyphen-adjacent in compounds (`XYZc-ABCD`) replaces with `ʿ` + lowercase post-hyphen.

**Bracket regnal numbers:** PM headwords print regnal numbers as `I`, `II`, etc. Some PM forms use bracketed `[I]`. In `occupant_name`, render with space + Roman: a king-name token of the form `<NAME>I` → `<Name> I`; `<NAME>II` → `<Name> II`. A name already conventionally spaced needs no change.

## Field-by-field rules

- **`tomb_id`** — Descriptor form `SAQ-<DescriptorName>` where `<DescriptorName>` is the title-cased occupant-name (no spaces, hyphens, or punctuation; Roman regnal numbers concatenated). Examples (rule-form): a complex named `<KING>` produces `tomb_id: "SAQ-<King>"`; a complex named `<KING><Roman>` (e.g. a king with a regnal number) produces `tomb_id: "SAQ-<King><Roman>"` (e.g. a Dyn-VI king with regnal `II` becomes `SAQ-<King>II`). For anonymous queen-enclosures (`PROBABLY OF WIFE OF <KING>`), the descriptor is `WifeOf<King>` (e.g. for the Dyn V king's anonymous wife, `tomb_id: "SAQ-WifeOf<King>"`).
- **`memphite_area`** — Always `"Saqqara"` for this chunk. Note: chunk 1-3 used `"Giza"`; chunk 4 introduces the `Saqqara` value.
- **`occupant_name`** — Conventional English form of the royal/queen name. For royal kings: derive from the section heading `PYRAMID-COMPLEX OF <KING>` (strip the prefix). For queen-enclosures: derive from `PYRAMID-ENCLOSURE OF <QUEEN-NAME>` (strip the prefix). Apply raised-ayin + bracket-regnal rules + title-casing. For `PROBABLY OF WIFE OF <KING>` anonymous queens, set `occupant_name: null`.
- **`occupant_alt_names`** — Alt-name forms that appear verbatim in the headword block. Greek/Latin names (Onnos/Unas etc.) NOT in PM's headword should NOT be imported.
- **`tomb_aliases`** — Popular pyramid-aliases from the `Lepsius, <Roman>` identification line's tail clauses. PM occasionally appends an Arabic popular-name token (e.g. `Haram <N>`) after the `Perring and Vyse, <N>` part — that token IS a popular alias and should be extracted into `tomb_aliases`. Empty `[]` if no alias clause is present.
- **`co_occupants`** — Empty `[]` for all rows in this chunk. The queen-enclosures are SEPARATE rows from their kings (not co-burials in a shared tomb).
- **`co_occupant_roles`** — Empty `[]` for all rows in this chunk (parallel array with `co_occupants`, length-coupled).
- **`is_joint_burial`** — `false` for all rows.
- **`occupant_role`** — `"King"` for the main pyramid of any `PYRAMID-COMPLEX OF <KING>` section. `"Queen"` for any `PYRAMID-ENCLOSURE OF <QUEEN-NAME>` headword AND for any `PROBABLY OF WIFE OF <KING>` anonymous-queen headword. No other roles expected in chunk 4.
- **`dynasty`** — Derived from PM's `Dyn. <Roman>` token in the headword block. Roman→Arabic: `Dyn. V` → `"5"`, `Dyn. VI` → `"6"`. The royal section heading takes the form `<LETTER>. PYRAMID-COMPLEX OF <KING>. (<cartouche garbage>) Dyn. <Roman>` — the dynasty tag appears on the same line or immediately below the section heading. Queen-enclosures inherit the dynasty of their king's complex; PM also prints `Dyn. <Roman>` after each queen-enclosure headword. Apply the literal PM rule per row.
- **`sub_period`** — `null` for all rows (no chunk-4 sub-period refinement).
- **`date_bce_approx_start`** / **`date_bce_approx_end`** — `null` for all rows.
- **`cemetery`** — `null` for all chunk-4 rows (the pyramid IS its own complex; no surrounding-cemetery designation as PM lists these under § I. PYRAMIDS, not § II. NECROPOLIS).
- **`discovery_year`** / **`discoverer`** — `null` for all rows.
- **`is_unfinished`** — `false` unless PM headword block literally says `unfinished`.
- **`is_uninscribed`** — `false` unless PM headword block literally says `uninscribed`.
- **`is_usurped`** — `false` unless PM headword block literally says `usurp(ed|ation)`.
- **`attribution_certainty`** — `"attested"` for named royal kings + named queens. `"uncertain"` for `PROBABLY OF WIFE OF <KING>` anonymous queen-enclosure rows AND any row whose headword PM marks with `Probably`, `(?)`, or `possibly`.
- **`shared_with_tombs`** — Empty `[]` for all rows. No architectural twin-mastaba links in this chunk.
- **`notes_from_pm`** — Verbatim short prose from PM's headword block: the section-heading line (with cartouche garbage dropped) + the `PYRAMID.` sub-heading line with its `Lepsius, <Roman>; Perring and Vyse, <num>` identification line. PM-faithful preservation of words and punctuation; drop only the cartouche-glyph runs and bibliographic ribbon. Trim trailing whitespace.
- **`source_citation`** — `{"page": <printed page where the row's headword first appears>, "edition": "PM III.2 2nd ed. 1978/1981", "section": "I"}`. Use the printed page (physical + 360 for this chunk's range; verify per-row against the running headers `Pyramid-complex of <King> <N>` on right-hand pages).

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk4: <count> rows; <kings>/<queens> split; <anomalies or "none">
```

Where `<kings>` is the count of King rows (Shape 1) and `<queens>` is the count of Queen rows (Shape 2, both named and anonymous).

Example: `agent-a-chunk4: <N> rows; <K>/<Q> split; <anomalies or "none">`. Under 80 words including any anomaly note.
