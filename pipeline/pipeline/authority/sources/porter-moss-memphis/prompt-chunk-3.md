# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 3

> **Third chunk drawn from PM Vol III** — covers the LG 100 Khentkaus I "Sarcophagus-shaped Tomb" (the famous Old Kingdom queen-mother burial at the transition between Dyn IV and Dyn V) and the surrounding Saite (Dyn XXVI) tombs in PM's `§ III. E. CENTRAL FIELD` section. This prompt is **self-contained** — the agent does NOT need to read prior chunks' prompts.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-3-p285-p289.txt` and produce a JSONL file with one structured row per **Lepsius-numbered (LG)** tomb in the chunk's range. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-row answers. Every field value must trace to something in the chunk file. Per-row values for individual LG-numbered tombs are NOT supplied here — derive them from the chunk file's headwords.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose (scene-by-scene descriptions, bibliographic ribbons, plate-reference catalogs) is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1 and 2 of this same source have shipped (see `reconciled.jsonl`); equivalent work exists for PM Vol I, Dodson-Hilton, Baud, Leprohon, Beckerath, Kitchen, Ryholt, HKW, Shaw.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — E. CENTRAL FIELD**, spanning the end of `Old Kingdom tombs` (printed p288 → LG 100 Khentkaus closes the OK section) into `Saite and later tombs` (printed p289 onwards). The `EXACT PROVENANCE UNKNOWN` section at the bottom of the chunk (printed p292) holds find-listings (statues, false-doors, libation-basins) NOT tomb-rows — drop entirely.
- PM III.1 offset for this chunk: **printed = physical + 3** (verified at physical p.285 with left-page header `288 GÎZA—NECROPOLIS` and at physical p.286 with right-page header `Central Field 289`). Per-page markers `=== physical page N ===` precede each page's text-layer dump.
- The chunk file covers physical pp.285–289 / printed pp.288–292. **Top boundary:** the chunk file opens mid-page on phys p.285 with the tail of the `WASHDUAU` Old Kingdom mastaba (Dyn V eye-physician); the LG 100 Khentkaus headword begins ~halfway down phys p.285. The WASHDUAU material is body-prose for a tomb whose headword is on a PRIOR (out-of-chunk) page — do NOT emit a row for WASHDUAU. **Bottom boundary:** the chunk ends inside the `EXACT PROVENANCE UNKNOWN` section on phys p.289 / printed p.292. The `F. MENKAUREʿ CEMETERY` heading and LG 93 SETHU row are out of scope for this chunk.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk3.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk3.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk3.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — full schema, no cross-references)

Every row MUST have these 21 keys; use `null` (not omitted, not empty string) for unknown values.

```json
{
  "tomb_id": "LG<N>",
  "memphite_area": "Giza",
  "occupant_name": "..." | null,
  "occupant_alt_names": [...],
  "tomb_aliases": [],
  "co_occupants": [...],
  "co_occupant_roles": [...],
  "is_joint_burial": false | true,
  "occupant_role": "King" | "Queen" | "Prince" | "Princess" | "Vizier" | "High Priest" | "Official" | "Royal Family" | "Unknown",
  "dynasty": "4" | "5" | "26" | null,
  "sub_period": "Saite" | null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "Central Field",
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

This chunk's rows are PM-headworded LG-numbered (Lepsius "Grab") tombs in the form:

```
LG <N>. <OCCUPANT NAME IN CAPS> <Title>, <Title>, etc. <Date>.
```

OR a JOINT-BURIAL headword for two co-occupants of the same tomb:

```
LG <N>. <NAME1> and <NAME2> both <shared title>. <Date>.
LG <N>. <NAME1> ..., and his mother Queen <NAME2> ... <Date>.
```

OR a SARCOPHAGUS-SHAPED-TOMB headword (LG 100 only):

```
LG 100. SARCOPHAGUS-SHAPED TOMB OF <OCCUPANT NAME IN CAPS> [<regnal number>]
<Date>
```

For each PM headword that defines an LG-numbered tomb in this chunk's range, emit ONE row. Joint-burial headwords (two named co-occupants of the SAME LG number) emit ONE row with the secondary occupant in `co_occupants` and `is_joint_burial: true` (the LG number identifies a single physical tomb, not twin mastabas — twin-mastaba compound headwords are NOT used in chunk 3).

**ROW-EMITTING headwords** in this chunk are exclusively LG-numbered. The Saite section's running-text introduces several no-number headwords (`THAIHARPATA Commander of the army`, `PEDUBASTE Commander of the army, Prophet of Bubastis`, `PTAHARDAIS Royal acquaintance` — each lacks an LG / Reisner / Mariette identifier). **DO NOT EMIT rows for these no-number headwords in chunk 3** — they require a tomb_id scheme that chunk 3 does not introduce. They will be picked up in a follow-up chunk with the descriptor-tomb-id form (`CF-Thaiharpata`-style).

**OUT OF SCOPE for rows in this chunk** — do NOT emit rows for any of:
- The tail of WASHDUAU (eye physician) at the very top of the chunk text — its headword is on a prior page outside this chunk.
- No-number headworded tombs (THAIHARPATA, PEDUBASTE, PTAHARDAIS) — see paragraph above.
- The `EXACT PROVENANCE UNKNOWN` section at the bottom of the chunk text (printed p.292) — find-listings (statues, false-doors, libation-basins, blocks) without tomb context. None of these are row-emitting.
- The `F. MENKAUREʿ CEMETERY` heading at the very bottom and LG 93 SETHU — those belong to chunk 4.
- Body-prose references to tombs in OTHER sections (e.g. `LG 94`, `LG 95`, `D. 80/80A` cross-references in plan-captions or coordinate tables).
- Sub-finds (sarcophagus fragments, ushabtis, false-doors) under each LG entry — these are body items, not headword rows.

**Headword block ends** at the first sub-feature heading after the LG-number line: `Plan <Roman>`, `Plans and sections`, `Position, on plan`, `Mortuary Chapel.`, `Burial Chamber.`, `Chapel.`, `Hall.`, `Entrance doorway`, `Columned Court`, `Sarcophagi.`, `Sarcophagus.`, `Finds.`, `Statues.`, or any prose line beginning with a museum-citation token (`Cairo Mus.`, `Brit. Mus.`, `Berlin (East) Mus.`, `Hermitage Mus.`, `Boston Mus.`, `REISNER`, `SMITH`, `JUNKER`, `HASSAN`, `L. D.`, `MARIETTE`, `WILKINSON`, `LIEBLEIN`). The headword block carries the structured fields; the body is dropped.

## Expected row count

Pre-extraction scan of the chunk file: 5 LG-numbered headwords are present (one Old Kingdom-era tomb, four Saite-era tombs).

**Total: 5 rows.** If your final count is below 4 or above 6, re-read the chunk file — you've either missed an LG headword or emitted an out-of-scope row.

## PM III.1 text-layer noise (chunk-3-relevant)

PM prints Egyptological raised-ayin (ʿ) as a superscript lowercase-`a` glyph; pypdf renders this as a regular inline lowercase `a`. In ALL-CAPS PM headword names, a lowercase `a` surrounded by uppercase letters is the raised-ayin's pypdf rendering — not a "real" letter `a`.

**Normalisation rule for `occupant_name`:** when extracting an occupant name from an ALL-CAPS PM headword, drop any **interior** lowercase `a` that sits immediately adjacent to uppercase letters on both sides. Then title-case the result (first letter upper, rest lower). Preserve PM-printed form verbatim in `notes_from_pm`.

Rule application (showing the rule's behaviour, NOT a target answer table — verify each against the chunk file):
- An ALL-CAPS name of the form `XAaY` (where `X` and `Y` are uppercase) drops the interior `a` → `XAY` → title `Xay`.

For trailing raised-ayin in an ALL-CAPS name, replace with `ʿ` (U+02BF). Apply this rule if encountered; do not assume it is absent.

**LG-number OCR drift:** when pypdf renders an LG-number with a separating space + Roman digit (e.g. `LG 8 I`, `LG 1 II`), this is the Griffith-Institute scan's drift where an Arabic numeral `1` mis-OCRs as Roman `I` with an inserted space. Normalisation rule: a headword token of the literal form `LG <digits> <I[I]*>` (digits followed by space-then-Roman-I-block) is the Lepsius number with the Roman-block re-read as Arabic. Apply this rule whenever such a form appears in the chunk's LG headwords. Preserve PM-printed verbatim form in `notes_from_pm`.

**Bracket regnal numbers:** PM headwords print regnal numbers as `[I]`, `[II]`, etc. pypdf may render `[II]` as `[11]`. Normalise to space + Roman in `occupant_name`; preserve bracket form in `notes_from_pm`.

**Footnote markers** (`¹`, `²`, `³`, `'`) appear after some headword names. Drop from structured `occupant_name`; the footnote bodies are body-prose and out of scope. (PM III footnote-1 under LG 100 reads `Mother of the two Kings of Upper and Lower Egypt, Daughter of the God, etc.` — this footnote DOES carry her PM-stated titulary; copy that single footnote line into `notes_from_pm` as a continuation of the headword block, because PM presents it as inseparable from the LG 100 attribution. Other footnotes carry only bibliographic content — drop those.)

## Field-by-field rules

- **`tomb_id`** — Derived from the row's `LG <N>` token in the PM headword. Normalisation: strip the whitespace between `LG` and the number. So `LG 100` → `tomb_id: "LG100"`, `LG 81` → `"LG81"`, `LG 83` → `"LG83"`. For the OCR-drift case (`LG 8 I`), the canonical `tomb_id` is `"LG81"` after un-drifting.
- **`memphite_area`** — Always `"Giza"` for this chunk.
- **`occupant_name`** — Conventional English form from PM's headword, derived by applying the raised-ayin + bracket regnal-number rules + title-casing. For an anonymous LG row (PM gives no occupant name in the headword), set `occupant_name: null`. For a JOINT-BURIAL row, the PRIMARY occupant is the FIRST named in the headword line (this is the row's `occupant_name`); the secondary co-occupant goes in `co_occupants`. For LG 100, PM's headword phrasing `SARCOPHAGUS-SHAPED TOMB OF KHENTKAUS [I]` puts the occupant name AFTER `TOMB OF`; extract `KHENTKAUS [I]` and normalise to `Khentkaus I`.
- **`occupant_alt_names`** — Alternate name forms of the SAME PERSON that appear verbatim in the headword block. PM uses the phrasing `<PRIMARY NAME> good name <SECONDARY NAME>` to mark a secondary "good name" — the secondary form goes in `occupant_alt_names`. Apply this rule when a `good name` token appears in the headword. Greek/Latin/colloquial alt-names NOT in PM's headword should NOT be imported.
- **`occupant_role`** — Controlled vocabulary, derived from the FIRST role-token PM prints in the headword block:
  - `"King"` — PM headword names a reigning king as primary occupant. Not expected in chunk 3.
  - `"Queen"` — PM headword identifies the occupant as `Queen <NAME>`, `King's wife`, `King's mother`, `Mother of the two Kings of Upper and Lower Egypt`, or includes a `wife of <king>` parenthetical naming a reigning king. When a `SARCOPHAGUS-SHAPED TOMB OF` row carries a footnote with the `Mother of the two Kings of Upper and Lower Egypt` titulary, that footnote qualifies the occupant as `Queen`. For a joint-burial headword where the secondary occupant carries a `Queen <NAME>` token, assign `Queen` to that secondary occupant even if the primary occupant of the same tomb holds an administrative title.
  - `"Prince"` / `"Princess"` — PM headword identifies occupant as `King's son` / `King's daughter`. Not expected in chunk 3.
  - `"Vizier"` — PM headword's FIRST role token is `Vizier` or `Chief Justice and Vizier`. Not expected in chunk 3.
  - `"High Priest"` — PM headword's first role token is `High Priest of <god>`. Not expected in chunk 3.
  - `"Official"` — PM headword names occupant with administrative title(s) (`Commander of the army`, `Overseer of scribes of the King's repast`, `Inspector of waab-priests`, `wnrw-priest`, `Royal acquaintance`, etc.) and NO `King's son/daughter` / Queen token. This is the catch-all for non-royal officials and priests.
  - `"Royal Family"` — reserve for cases where PM marks the occupant as related to a king or king's child by blood or marriage but without naming them with a direct `King's son/daughter` token and without naming them with their own administrative title.
  - `"Unknown"` — when the headword consists of a bare LG-number line with no occupant name token (PM gives the LG number, the dynasty, and the plan position, but no name).
- **`dynasty`** — Derived from PM's `Dyn. <Roman>` or `End of Dyn. <Roman>` line in the headword block. Apply this resolver:
  - `Dyn. IV` → `"4"`, `Dyn. V` → `"5"`, `Dyn. VI` → `"6"`, `Dyn. XXVI` → `"26"`.
  - Range like `Dyn. V-VI` → `"5"` (use the START dynasty; refinement in `notes_from_pm`).
  - Range like `Dyn. XXX or early Ptolemaic` → not expected in chunk 3 (those headwords lack LG numbers and are out of scope).
  - Transition phrasing like `End of Dyn. IV or early Dyn. V` → `"4"` (use the START / older dynasty; refinement in `notes_from_pm`).
  - If PM's headword block carries no dating line, store `null`.
- **`sub_period`** — Controlled-vocab refinement for sub-divisions of a dynasty. For chunk 3:
  - `"Saite"` when PM dates the tomb to `Dyn. XXVI` (Saite Dynasty). All Saite chunk-3 rows get `sub_period: "Saite"`.
  - `null` for `Dyn. IV` / `Dyn. V` / `Dyn. V-VI` rows (no chunk-3 sub-period refinement for the Old Kingdom rows).
- **`date_bce_approx_start`** / **`date_bce_approx_end`** — `null` for all rows.
- **`cemetery`** — `"Central Field"` for all rows in this chunk. PM's section header `E. CENTRAL FIELD` (printed p.130 onwards, with the Saite sub-section starting on printed p.289) sets the cemetery designation for this entire range.
- **`discovery_year`** / **`discoverer`** — `null` for all rows. PM mentions excavators (Hassan, Reisner, Lepsius, Mariette, Wilkinson) in body-prose bibliographic ribbons; do NOT extract per-row discovery years in this chunk.
- **`is_unfinished`** — `false` unless PM headword literally says `Unfinished`.
- **`is_uninscribed`** — `false` unless PM headword block literally says `uninscribed` or `No inscriptions found`.
- **`is_usurped`** — `false` unless PM headword literally says `usurp(ed|ation)`.
- **`attribution_certainty`** — Hedge-token derivation from PM's headword line:
  - `"attested"` when PM names an occupant in the headword without hedge tokens.
  - `"probable"` when PM uses `Probably`, `probably`, `attributed to`, `tentatively`, or `perhaps` in the headword.
  - `"uncertain"` when PM uses `possibly`, `uncertain`, or `(?)`. ALSO when PM does NOT name an occupant in the headword at all (bare-LG-number row).
- **`co_occupants`** — Non-empty for JOINT-BURIAL rows: list the secondary occupant(s) as strings, each in the same normalised-name form as `occupant_name`. Two joint-burial headword shapes apply in chunk 3:
  - `<NAME1> ..., and his mother Queen <NAME2> (wife of <king>)` — the secondary occupant (the queen-mother) goes in `co_occupants`.
  - `<NAME1> and <NAME2> both <shared title>` — the secondary occupant goes in `co_occupants`.
  Empty `[]` for single-occupant rows.
- **`co_occupant_roles`** — Parallel array order-coupled with `co_occupants`. Each entry types the role of the secondary occupant at the same index, using the same controlled vocabulary as `occupant_role`. For the `<NAME1> ..., and his mother Queen <NAME2>` shape, the secondary's role is `"Queen"` (PM's explicit `Queen <NAME>` token + `wife of <king>` parenthetical both type her as a queen). For the `<NAME1> and <NAME2> both <shared title>` shape, the secondary inherits the SAME role as the primary (symmetric typing). Empty `[]` for single-occupant rows; the length of `co_occupant_roles` MUST equal the length of `co_occupants`.
- **`is_joint_burial`** — `true` when `co_occupants` is non-empty (the LG number names a single tomb with two named occupants). `false` for single-occupant rows.
- **`shared_with_tombs`** — Empty `[]` for all chunk-3 rows. No twin-mastaba architectural links in this chunk's range.
- **`notes_from_pm`** — Verbatim short prose from PM's headword block: the LG-number title line + dating line + role-qualification parentheticals + any explicit relation lines (`Husband, X.`, `Wife, Y.`, `Mother, Z.`, `Parents, A and B`, `Father, W.`). PM-faithful preservation (keep PM's punctuation, capitalisation, including raised-ayin OCR artifacts and bracket regnal numbers — `KHENTKAUS [I]` stays `KHENTKAUS [I]` in notes). For LG 100, include the footnote-1 line `Mother of the two Kings of Upper and Lower Egypt, Daughter of the God, etc.` as a final sentence (PM presents this as titulary inseparable from the LG 100 attribution). Trim trailing whitespace. For bare-LG-number rows like LG 81 with no headword content beyond the number + dynasty, set `notes_from_pm` to just the bare LG-line + dynasty.
- **`source_citation`** — `{"page": <printed page where the row's LG-number headword first appears>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}`. The `page` field is the printed page (`physical + 3` for this chunk's range; verify per-row against the running headers in the chunk text — `Central Field <N>` on right-hand pages, `<N> GÎZA—NECROPOLIS` on left-hand pages). Section is `"III"` for `§ III. NECROPOLIS` (the E. CENTRAL FIELD sub-letter is implicit in `cemetery: "Central Field"`).

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk3: <count> rows; <single>/<joint>/<unknown> split; <anomalies or "none">
```

Where `<single>` is the count of single-occupant LG rows, `<joint>` is the count of joint-burial LG rows (those with non-empty `co_occupants`), and `<unknown>` is the count of bare-LG-number anonymous rows.

Example: `agent-a-chunk3: 5 rows; 2/2/1 split; none`. Under 80 words including any anomaly note.
