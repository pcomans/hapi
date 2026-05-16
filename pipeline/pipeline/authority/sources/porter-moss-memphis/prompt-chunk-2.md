# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 2

> **Second chunk drawn from PM Vol III** — covers the Reisner G 7000 East Field cluster (Khufu royal family). This prompt is **self-contained** — the agent does NOT need to read prior chunks' prompts. Every field rule, schema invariant, and noise pattern is documented here in full.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-2-p176-p187.txt` and produce a JSONL file with one structured row per **PM-headworded Reisner-numbered mastaba** in the **B. EAST FIELD** section of `§ III. NECROPOLIS` within the Pyramid-Field of Gîza. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-row answers. Every field value must trace to something in the chunk file. The only things the prompt may validly hint: structural facts about the section (page range, expected row count, headword shape), text-layer noise signatures, vocabulary constraints, and explicit examples drawn from sibling sources / chunk 1 for analogy. Per-row values for individual mastaba occupants are NOT supplied here — derive them from the chunk file's headwords.

## Refusal framing

This is fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose (scene-by-scene descriptions, bibliographic ribbons, plate-reference catalogs) is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside the scope of US copyright protection. Chunk 1 of this same source has already shipped (see `reconciled.jsonl`), and equivalent work exists for PM Vol I (`porter-moss-theban-necropolis/`) and Dodson-Hilton, Baud, Leprohon, Beckerath, Kitchen, Ryholt, HKW, Shaw.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — B. EAST FIELD** (the cluster of Cemetery G 7000 mastabas immediately east of Khufu's pyramid, containing Khufu's mother + sons + daughters + viziers).
- PM III.1 offset for this chunk: **printed = physical + 3** (verified at physical p.176 with running header `West Field 179` and at physical p.178 with running header `East Field 181`). Per-page markers `=== physical page N ===` precede each page's text-layer dump. Right-hand pages print their running header as `East Field <N>` (where `<N>` is the printed odd page); left-hand pages print `<N> GÎZA—NECROPOLIS` (printed even page). Use the **printed** page (`physical + 3` for this chunk's range) for `source_citation.page`.
- The chunk file covers physical pp.176–187 / printed pp.179–190. Boundary at the top: the `B. EAST FIELD` section heading appears mid-page on physical p.176 (printed p.179); rows from before the heading are out of scope (those belong to A. WEST FIELD, a future chunk). Boundary at the bottom: the chunk ends with G 7150 KHUFUKHAEF [II] starting on physical p.187 (printed p.190). G 7152 and beyond are out of scope for this chunk.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk2.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk2.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk2.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — full schema, no cross-references)

Every row MUST have these 21 keys; use `null` (not omitted, not empty string) for unknown values.

```json
{
  "tomb_id": "G<NNNN>" | "G<NNNN><lowercase-letter>",
  "memphite_area": "Giza",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "is_joint_burial": false,
  "occupant_role": "King" | "Queen" | "Prince" | "Princess" | "Vizier" | "High Priest" | "Official" | "Royal Family" | "Unknown",
  "dynasty": "4" | "5" | null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "G 7000",
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

This chunk's rows are PM-headworded Reisner-numbered mastabas in the form:

```
G <NNNN>. <OCCUPANT NAME IN CAPS> <Title>, <Title>, etc. <Date>.
```

or a JOINT-MASTABA compound headword:

```
G <NNNN1>+<NNNN2>. <PRIMARY OCCUPANT NAME IN CAPS> ... and wife <SECONDARY NAME>.
G <NNNN1>. <secondary occupant>
G <NNNN2>. <primary occupant>
```

For each PM headword that defines a Reisner mastaba, emit ONE row. Compound headwords like `G 7110+7120. KAWAaB ... and wife HETEPHERES [11]` followed by sub-rows `G 7110. Hetepheres [11]` and `G 7120. Kawaab` produce TWO rows (one per Reisner number), each with `shared_with_tombs: ["G<other>"]` cross-referencing the twin half. The compound `G NNNN1+NNNN2` is NOT itself a row — it's a section header that bundles two physical mastabas.

**ROW-EMITTING headwords** in this chunk (each line starting with a Reisner G-number followed by a period or compound `+`):
- Single primary headwords: `G 7000X.` (the `X` suffix is PM's notation for an unattached shaft with no mastaba superstructure), `G 7050.`, `G 7060.`, `G 7070.`, `G 7101.`, `G 7102.`, `G 7150.`
- Compound twin-mastaba headwords (each emits TWO rows): `G 7110+7120.`, `G 7130+7140.`
- Bare-suffix headwords (PM lists the Reisner number with no occupant in the headword line — emit one row with `occupant_name: null`): `G 7112.`, `G 7142.`

**OUT OF SCOPE for rows in this chunk** — do NOT emit rows for any of:
- Sub-shafts within a numbered mastaba (e.g. `G 7120A`, `G 7130A`, `G 7130B`, `G 7130X`) — these are shaft-IDs within the parent mastaba, not their own row.
- Body-prose mentions of mastabas outside the chunk's range (e.g. mentions of `G 7350`, `G 7530`, `G 7510` in cross-references — those are future-chunk rows; in this chunk they're just cross-reference text).
- Find-listings (statues, false-doors, lintels with names of secondary persons) — these are body-prose items, not headword rows.
- Mortuary chapels, boat-pits, satellite chapels — sub-features of a parent mastaba.
- Anything in the A. WEST FIELD section at the top of the chunk file (physical p.176 lines 1–20 before the `B. EAST FIELD` heading at line 21).
- The `CEMETERY G 7000` line on physical p.179 (line 179 in chunk text) — this is a cemetery banner, not a row.
- G 7152 and beyond — those are in chunk 3.

**Headword block ends** at the first sub-feature heading after the Reisner-number line: `Plan <Roman>`, `Plans and sections`, `Mortuary Chapel.`, `Burial Chamber.`, `Chapel.`, `Hall.`, `Sloping shaft`, or any prose line beginning with a museum-citation token (`Cairo Mus.`, `REISNER`, `SMITH`, `JUNKER`). The headword block carries the structured fields; the body is dropped.

## Expected row count

Pre-extraction scan of the chunk file:
- 7 single primary headwords (G7000x, G7050, G7060, G7070, G7101, G7102, G7150)
- 2 compound twin-mastaba headwords producing 2 rows each (G7110+G7120, G7130+G7140) = 4 rows
- 2 bare-suffix headwords (G7112, G7142) = 2 rows

**Total: 13 rows.** If your final count is below 11 or above 15, re-read the chunk file — you've either missed a headword or emitted an out-of-scope feature row.

## PM III.1 text-layer noise (chunk-2-relevant)

PM prints Egyptological raised-ayin (ʿ) as a superscript lowercase-`a` glyph; pypdf renders this as a regular inline lowercase `a`. In ALL-CAPS PM headword names, a lowercase `a` surrounded by uppercase letters is the raised-ayin's pypdf rendering — not a "real" letter `a`.

**Normalisation rule for `occupant_name`:** when extracting an occupant name from an ALL-CAPS PM headword, drop any **interior** lowercase `a` that sits immediately adjacent to uppercase letters on both sides. Then title-case the result (first letter upper, rest lower). Preserve PM-printed form verbatim in `notes_from_pm` for traceability.

Rule application examples (showing the rule's behaviour, not a target answer table — verify each against the chunk file):
- An ALL-CAPS name of the form `XAaY` (where `X` and `Y` are uppercase) drops the interior `a` → `XAY` → title `Xay`.
- An ALL-CAPS name of the form `XEaY` drops the interior `a` → `XEY` → title `Xey`.

For trailing raised-ayin in an ALL-CAPS name (lowercase `a` at the end of an otherwise-uppercase token, e.g. `MENKAUREa` from chunk 1 → `Menkaureʿ`), replace with `ʿ` (U+02BF). Apply this rule if encountered; do not assume it is absent.

**Bracket regnal numbers:** PM headwords print regnal numbers as `[I]`, `[II]`, etc. pypdf may render `[II]` as `[11]` (Roman II mis-OCRed as Arabic 11). Normalise to space + Roman: a headword like `<NAME> [I]` → `Name I`; `<NAME> [11]` → `Name II`. Drop the brackets in `occupant_name`; preserve PM-printed bracket form verbatim in `notes_from_pm`.

**Sub-shaft IDs in body cross-references:** body prose like `Shaft G 7130B, see p. 190` or `Sloping shaft G 7120A` are cross-references, NOT row identifiers. They contribute nothing to structured fields; they may be summarised in `notes_from_pm` only if they appear in the headword block (before any `Plan`/`Plans` sub-heading).

**Footnote markers** like `¹`, `²`, `³` and `'` (apostrophe-as-footnote-call) appear after some headword names. Drop from structured `occupant_name`; the footnote bodies are body-prose and out of scope.

## Field-by-field rules

- **`tomb_id`** — Derived from the row's Reisner G-number. Normalisation: strip the literal space between `G` and the number, retain any letter suffix in lowercase. So `G 7000X` → `G7000x`, `G 7050` → `G7050`, `G 7110` → `G7110`. For twin-mastaba compound headwords, the compound `G 7110+7120` is NOT a `tomb_id` — it produces TWO rows with `tomb_id: "G7110"` and `tomb_id: "G7120"` respectively.
- **`memphite_area`** — Always `"Giza"` for this chunk.
- **`occupant_name`** — Conventional English form from PM's headword, derived by applying the raised-ayin normalisation rule above + bracket regnal-number rule + title-casing. For bare-suffix headwords (`G NNNN.` with no occupant in the headword line), set `occupant_name: null`. For twin-mastaba sub-rows, the sub-row line `G NNNN. <Name>` (PM-printed in mixed case, NOT ALL-CAPS) names the specific occupant of that half: take that name (after applying the rules) as `occupant_name` for that row. The compound headword's ALL-CAPS primary name names the occupant of the LARGER Reisner-number half within the twin — verify by matching the compound's primary name against the sub-row labels in the chunk.
- **`occupant_alt_names`** — Alternate name forms of the SAME PERSON that appear verbatim in the headword block. Empty `[]` if PM gives only one form. Greek/Latin/colloquial alt-names are NOT in this chunk's PM-printed headwords; do NOT import alt-names from outside the chunk file.
- **`occupant_role`** — Controlled vocabulary, derived from the FIRST role-token PM prints in the headword block:
  - `"King"` — PM headword names a reigning king as primary occupant. Not expected in this chunk (all chunk-2 occupants are queens / princes / princesses / officials).
  - `"Queen"` — PM headword identifies the occupant as `King's wife`, `King's mother`, names her as a queen consort, or includes a `Husband, <king>. Son, <king>.` block establishing her as a king's wife and/or mother. A `later, wife of King <N>` parenthetical also qualifies (queen via remarriage), provided no `King's son/daughter` token outranks it.
  - `"Prince"` — PM headword identifies occupant as `King's son` (or `King's eldest son`) as the FIRST/PRIMARY role token. If PM ALSO lists official titles after the King's-son token (e.g. `King's son of his body, Chief Justice and Vizier`), `Prince` still wins because the King's-son tie to royal blood is the primary attribution.
  - `"Princess"` — PM headword identifies occupant as `King's daughter`.
  - `"Vizier"` — PM headword's FIRST role token is `Vizier` or `Chief Justice and Vizier` AND the occupant is NOT a King's son/daughter. (When `Vizier` is a secondary title following `King's son`, the role is `Prince`, not `Vizier`.) Exception: if PM gives a parenthetical `(Vizier of <king>)` AFTER the primary role line, and no King's son/daughter token is present, treat as `Vizier`.
  - `"High Priest"` — PM headword's first role token is `High Priest of <god>`. Not expected in chunk 2.
  - `"Official"` — PM headword names occupant with administrative title(s) (`Treasurer`, `Overseer`, `Inspector`, `Tenant`, `Royal acquaintance`, `Greatest of the Ten of Upper Egypt`, `Steward`, `Scribe`, etc.) and NO `King's son/daughter` token. This is the catch-all for non-royal officials.
  - `"Royal Family"` — reserve for cases where PM marks the occupant as related to a king or king's child by blood or marriage but without naming them with a direct `King's son/daughter` token and without naming them with their own administrative title. Examples: `Father of king`, `Cousin of king`, the untitled wife of a King's-son occupant (PM-faithful pattern: a compound twin-mastaba headword like `G XXXX+YYYY. KING'S-SON-NAME ... and wife UNTITLED-WIFE-NAME` produces a sub-row for the wife where PM names her by name but gives her no title of her own).
  - `"Unknown"` — when the headword consists of a bare Reisner-number line with no occupant name and no role token (and no `Probably` / `attributed to` hedge that names an attribution candidate). Bare-Reisner-number rows are valid: PM lists the Reisner number with a period and the headword block then steps directly into a `Superstructure...` or `Stone-built mastaba...` description without naming an occupant.
- **`dynasty`** — Derived from PM's `Dyn. <Roman>` or `Temp. <king>` line in the headword block. Apply this resolver:
  - Literal `Dyn. IV` → `"4"`; `Dyn. V` → `"5"`; `Dyn. VI` → `"6"`.
  - `Temp. Khufu`, `Temp. Khephren`, `Temp. Menkaureʿ` → `"4"` (all three are Dyn. IV kings; this is PM's standard chronological vocabulary).
  - Date ranges like `Middle Dyn. IV to early Dyn. V` → `"4"` (use the START dynasty; the end-dynasty refinement goes in `notes_from_pm`).
  - Date ranges like `Temp. Khufu to Khephren` → `"4"`.
  - Date ranges like `Temp. Khufu to end of Dyn. IV` → `"4"`.
  - Mixed Roman dating like `Dyn. V-VI` → `"5"` (use the start dynasty).
  - If PM's headword block carries no dating line at all (e.g. bare `G 7112.` rows), store `null`.
- **`sub_period`** — `null` for all rows in this chunk.
- **`date_bce_approx_start`** / **`date_bce_approx_end`** — `null` for all rows.
- **`cemetery`** — `"G 7000"` for all rows in this chunk (the CEMETERY G 7000 banner on physical p.179 sets the cemetery designation for the entire B. EAST FIELD section; G 7000X belongs to this cemetery too even though its description precedes the banner).
- **`discovery_year`** / **`discoverer`** — `null` for all rows (PM's `Reisner Excavation. Harvard-Boston Expedition (1924-31)` covers the whole cemetery and is reproduced in `notes_from_pm` for individual rows where the headword block carries it; we do NOT extract per-row discovery years in this chunk).
- **`is_unfinished`** — `false` unless PM headword literally says `Unfinished` or `unfinished`.
- **`is_uninscribed`** — `false` unless PM headword block literally says `uninscribed` or `No inscriptions found`. The `No inscriptions found.` clause sometimes sits inside the headword block (between the Reisner-number title line and the first `Plan` / `Plans` / `Cairo Mus.` / `REISNER and SMITH,` boundary) on rows where PM had no inscribed material to catalog. When it falls within that block, `is_uninscribed: true`; when it appears later in body-prose listings, `false`. Read each row's headword block to decide.
- **`is_usurped`** — `false` unless PM headword literally says `usurp(ed|ation)`.
- **`attribution_certainty`** — Hedge-token derivation from PM's headword line:
  - `"attested"` when PM names an occupant in the headword without hedge tokens. (A headword of the form `G NNNN. ALLCAPSNAME <Title>...` with no qualifier is attested.)
  - `"probable"` when PM uses `Probably`, `probably`, `attributed to`, `tentatively`, or `perhaps` to qualify the occupant attribution in the headword.
  - `"uncertain"` when PM uses `possibly`, `uncertain`, or the standard `(?)` attribution-uncertainty glyph (typically following the occupant name in the headword). ALSO when PM does NOT name an occupant in the headword at all (bare `G NNNN.` rows with no name token carry `"uncertain"`).
- **`shared_with_tombs`** — For twin-mastaba sub-rows, list the OTHER Reisner number as a single-element list (e.g. `G 7110` → `shared_with_tombs: ["G7120"]`; `G 7140` → `shared_with_tombs: ["G7130"]`). For all other rows, empty `[]`. Note `shared_with_tombs` documents an ARCHITECTURAL link (twin mastaba); it does NOT mean the same person is buried in both. The two halves of a twin mastaba have different occupants; `is_joint_burial` stays `false`.
- **`co_occupants`** — Empty list `[]` for all rows in this chunk. The chunk's twin-mastabas have one occupant per Reisner number (not multiple in one tomb).
- **`is_joint_burial`** — `false` for all rows.
- **`notes_from_pm`** — Verbatim short prose from PM's headword block: the Reisner-line title text + dating line + parenthetical role qualifications + any explicit relation lines (`Husband, X.`, `Wife, Y.`, `Father, Z.`, `Son, W.`). PM-faithful preservation (keep PM's punctuation, capitalisation, including the raised-ayin OCR artifacts and bracket regnal numbers — `KAWAaB` stays `KAWAaB` in notes; `[11]` stays `[11]` in notes). DO NOT include body-prose references, museum inventory listings, plate citations, or bibliographic refs from after the first `Plan` / `Plans` / `Cairo Mus.` / `REISNER and SMITH,` line. Trim trailing whitespace. For bare-suffix rows like `G 7112.` with no headword content beyond the number line, set `notes_from_pm: null`.
- **`source_citation`** — `{"page": <printed page where the row's Reisner-number headword first appears>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}`. The `page` field is the printed page (the higher number on right-hand pages where the running header reads `East Field <N>`, equal to physical page + 3 for this chunk's range; verify per-row against the running headers in the chunk text). Section is `"III"` for `§ III. NECROPOLIS` (the B. EAST FIELD sub-letter distinguishes this from `A. WEST FIELD` but lives implicitly in the row's `cemetery: "G 7000"`).

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk2: <count> rows; <single>/<twin>/<bare> split; <anomalies or "none">
```

Where `<single>` is the number of single-primary headword rows, `<twin>` is the number of rows from twin-mastaba compound headwords, and `<bare>` is the number of bare-suffix rows.

Example: `agent-a-chunk2: 13 rows; 7/4/2 split; none`. Under 80 words including any anomaly note.
