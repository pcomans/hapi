# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 1

> **First chunk drawn from PM Vol III** — establishes the Memphite `tomb_id` scheme, the `memphite_area` controlled vocabulary, and the PM-III.1 text-layer noise classes. This prompt is **self-contained** — the agent does NOT need to read prior chunks' prompts. Every field rule, schema invariant, and noise pattern is documented here in full.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-1-p8-p32.txt` and produce a JSONL file with one structured row per **named pyramid or named subsidiary pyramid** in PM III.1 § I "PYRAMIDS" within the **PYRAMID-COMPLEX OF KHUFU**, **PYRAMID-COMPLEX OF KHEPHREN**, and **PYRAMID-COMPLEX OF MENKAUREʿ** sections. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-pyramid answers. Every field value must trace to something in the chunk file. The only things the prompt may validly hint: structural facts about the section (page range, expected row count, headword shape), text-layer noise signatures, vocabulary constraints, and explicit examples drawn from sibling sources (`porter-moss-theban-necropolis/`) for analogy. Per-row values for Khufu / Khephren / Menkaureʿ / their subsidiary pyramids are NOT supplied here — derive them from the chunk file's headwords.

## Refusal framing

This is fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose (scene-by-scene descriptions, bibliographic ribbons, plate-reference catalogs) is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside the scope of US copyright protection. Other extractors have completed equivalent work on PM Vol I (`porter-moss-theban-necropolis/`) and on Dodson-Hilton, Baud, Leprohon, Beckerath, Kitchen, Ryholt, HKW, Shaw.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — I. PYRAMIDS — A / B / C** (Khufu / Khephren / Menkaureʿ complexes).
- PM III.1 offset for this chunk: **printed = physical + 3**. Verified at phys 8 = printed 11 (`Pyramid-field of Gîza 11`), phys 10 = printed 13, phys 18 = printed 21, phys 24 = printed 27. Per-page markers `===== PHYSICAL PAGE N (PRINTED PAGE M) =====` precede each page's text-layer dump. Use `M` (the printed number) for `source_citation.page`. Phys 9 has `?` because the text-layer header rendered as `I2 GÎZA-PYRAMIDS` (printed `12` mis-read as Roman `I2`); treat phys 9 as printed p.12.
- The chunk file starts at physical p.8 (printed p.11, the **PYRAMID-COMPLEX OF KHUFU** section heading) and extends through physical p.32 (printed p.35, just past the end of MENKAUREʿ). Boundary markers `II. GREAT SPHINX AND SURROUNDING AREA` and `A. GREAT SPHINX` appear at the chunk tail — **do NOT extract any Sphinx-area rows**. Stop at the end of the MENKAUREʿ section.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk1.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk1.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk1.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending (Python's default tuple sort over the chars; this orders a main pyramid `G<N>` before its subsidiary `G<N><letter>` rows because the shorter string sorts first). Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — full schema, no cross-references)

Every row MUST have these 21 keys; use `null` (not omitted, not empty string) for unknown values.

```json
{
  "tomb_id": "G<N>" | "G<N><letter>" | "GIIa" | etc.,
  "memphite_area": "Giza",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "is_joint_burial": false,
  "occupant_role": "King" | "Queen" | "Royal Family" | "Vizier" | "Official" | "High Priest" | "Princess" | "Prince" | "Unknown",
  "dynasty": null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": null,
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "is_uninscribed": false,
  "is_usurped": false,
  "attribution_certainty": "attested" | "probable" | "uncertain",
  "shared_with_tombs": [],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM III.1 2nd ed. 1974", "section": "I"}
}
```

## How to identify a row

This chunk contains **THREE pyramid-complex sections** (Khufu, Khephren, Menkaureʿ), each marked by a section heading of the form:

```
A. PYRAMID-COMPLEX OF KHUFU
Dyn. IV
```

(Variants: `B. PYRAMID-COMPLEX OF KHEPHREN` and `C. PYRAMID-COMPLEX OF MENKAUREa` — the trailing `a` is text-layer mis-rendering of PM's terminal ayin in `Menkaureʿ`.)

Within each pyramid-complex section, two kinds of named structures yield ROWS:

**A. The main pyramid.** Marked by a sub-heading `PYRAMID.` (or `THE PYRAMID.`) followed by an italic identification line of the form:

```
Lepsius, <Roman>; Perring and Vyse, <num> of Giza; Reisner, <G N>; called <Popular Name>.
```

Examples of identification-line shape (across chunk's three pyramid-complex sections):
- Khufu: `Lepsius, IV; Perring and Vyse, 1 of Giza; Reisner, G I; called Great or First Pyramid.`
- Khephren: similar pattern with different Roman/Arabic numerals.
- Menkaureʿ: similar pattern, sometimes `called Third Pyramid.`

The `Reisner, G <N>` token gives the `tomb_id`: render as Reisner's letter+number form **without** the space and **normalising Roman→Arabic** for the pyramid number — so `Reisner, G I` → `tomb_id: "G1"`, `Reisner, G II` → `tomb_id: "G2"`, `Reisner, G III` → `tomb_id: "G3"`. The popular tomb-name(s) after `called` go into `tomb_aliases` (e.g. `["Great Pyramid", "First Pyramid"]`).

**B. Subsidiary pyramids.** Each pyramid-complex includes subsidiary (queen's / cult) pyramids. The headword forms vary by complex:

- A **`THREE SUBSIDIARY PYRAMIDS.`** group heading followed by three sub-headed rows: `North Subsidiary Pyramid.`, `Middle Subsidiary Pyramid.`, `South Subsidiary Pyramid.` (Khufu) OR `East Subsidiary Pyramid.`, `Middle Subsidiary Pyramid.`, `West Subsidiary Pyramid.` (Menkaureʿ, in some chunks `East`/`Middle`/`Westernmost` per PM's exact text). Each sub-row carries an identification line `Lepsius, <Roman>; Perring and Vyse, <num> of Giza; Reisner, G <N>-<letter>.`
- A **single subsidiary pyramid** with its own heading (e.g. Khephren's `SUBSIDIARY PYRAMID WITH 'SERDAB'. Reisner, G II-a.`).

Render Reisner's form: `Reisner, G I-a` → `tomb_id: "G1a"` (strip space, strip hyphen, lowercase letter, Roman→Arabic). `Reisner, G III-b` → `tomb_id: "G3b"`. `Reisner, G II-a` → `tomb_id: "G2a"`.

If PM's subsidiary-pyramid headword does NOT name an occupant explicitly (the queens' identities are not stated in PM 1974's headwords for the Giza subsidiary pyramids — PM does not assert Hetepheres I / Meritites I / Henutsen for G1a/b/c, and does not name queens for G3a/b/c either), set `occupant_name: null` and `occupant_role: "Queen"` (subsidiary pyramids in pyramid-complex sections are conventionally queens' pyramids; PM treats these as queens' tombs even when the queen is unnamed) and `attribution_certainty: "uncertain"` for the anonymity. If PM DOES name an occupant in the headword (verify against the chunk file — do not import attributions from outside PM), set `occupant_name` to that name and `attribution_certainty: "attested"`.

**OUT OF SCOPE for rows in this chunk** — do NOT emit rows for any of:
- Mortuary Temple, Valley Temple, Causeway (these are sub-features of a pyramid-complex, not separate tombs).
- Boat-pits, queens' satellite chapels, princes' mastabas listed in the pyramid-complex body prose (those belong in future cemetery chunks, not in the pyramid-complex chunk).
- Temple of Isis Mistress-of-the-Pyramid (Saite temple addition to G1c; not a tomb).
- Anything inside § II. GREAT SPHINX AND SURROUNDING AREA (boundary marker — chunk 2 will handle).
- The bibliographic and museum-object reference catalogs (statues, blocks, stelae in Cairo Mus., Boston Mus., London BM, etc.) under each section's body — these are find-listings, not tomb-rows.

**Headword block ends** at the first sub-feature heading (`Mortuary Temple.`, `Valley Temple.`, `Causeway.`, `Boat-pit`, `Interior`, `Burial Chamber.`, `Finds.`, `Description, …`, etc.). The headword block carries the structured fields; the body is dropped.

## Expected row count

Pre-extraction scan of the chunk file (`grep`-able):
- **PYRAMID-COMPLEX OF KHUFU** main pyramid (1 row) + `THREE SUBSIDIARY PYRAMIDS` north/middle/south (3 rows) = 4 rows.
- **PYRAMID-COMPLEX OF KHEPHREN** main pyramid (1 row) + `SUBSIDIARY PYRAMID WITH 'SERDAB'` (1 row) = 2 rows.
- **PYRAMID-COMPLEX OF MENKAUREʿ** main pyramid (1 row) + `THREE SUBSIDIARY PYRAMIDS` east/middle/west (3 rows) = 4 rows.

**Total: 10 rows.** If your final count is below 9 or above 11, re-read the chunk file — you've either missed a subsidiary pyramid heading or emitted an out-of-scope feature row.

## PM III.1 text-layer noise (chunk-1-relevant)

- `Menkaurea` → `Menkaureʿ` (PM prints with terminal raised-`a` ayin, OCR drops the raising and outputs trailing plain `a`). Normalise `occupant_name` to `Menkaureʿ` (Unicode ayin U+02BF). Preserve `Menkaurea` verbatim in `notes_from_pm` if the headword line contains it.
- `Khufu` and `Khephren` clean — no normalisation needed.
- `I2 GÎZA-PYRAMIDS` page header at phys 9 = printed 12 (Roman `I` mis-read for Arabic `1`). Treat as printed page 12 — the chunk file's PRINTED PAGE marker is `?` for this page only.
- `G I-a`, `G I-b`, `G I-c`, `G II-a`, `G III-a`, `G III-b`, `G III-c` — Reisner's published form for subsidiary pyramids. Whitespace within `G I` etc. is PM-faithful; the `-` separator before the letter is also PM-faithful. **Normalisation rule:** `Reisner, G <ROMAN>-<letter>` → `tomb_id: "G<arabic><letter>"` (strip space, strip hyphen, lowercase letter, Roman→Arabic).
- Inline cartouche garbage: PM prints royal-name cartouches inline; text layer renders these as `~~~`, `(~~~ ::)`, `(•~~)`, etc. **Drop the cartouche garbage** from `occupant_name`; keep only the conventional English name.
- Footnote markers like `¹`, `²`, `³` and `'` (apostrophe-as-footnote-call) appear after some headwords. Drop from structured fields; the footnote bodies are body-prose and out of scope.

## Field-by-field rules

- **`tomb_id`** — Derived from the `Reisner, G <Roman>(-<letter>)` token in the row's identification line. Normalisation: strip the literal `Reisner, ` prefix, strip whitespace between `G` and the Roman numeral, strip the hyphen before the subsidiary-pyramid letter, lowercase the letter, Roman→Arabic for the number. So `Reisner, G I` → `G1`, `Reisner, G I-a` → `G1a`, `Reisner, G II-a` → `G2a`, `Reisner, G III` → `G3`. PM-faithful exception: if PM cites without a hyphen (e.g. `G IIa`), still produce the no-hyphen lowercase form (`G2a`).
- **`memphite_area`** — Always `"Giza"` for this chunk. Future chunks will introduce `"Abu Rawash"`, `"Saqqara"`, `"Abusir"`, `"Dahshur"`, `"Lisht"`, `"Meidum"` from different volumes.
- **`occupant_name`** — Conventional English form from PM's headword. For pyramid-complex MAIN pyramids: derive by stripping the `PYRAMID-COMPLEX OF ` prefix from the section heading in the chunk file, then applying the ayin-normalisation rule (trailing raised-`a` or `ea` rendered by the OCR as plain trailing `a` → Egyptological ayin `ʿ` U+02BF). Apply title-case to the result. For subsidiary pyramids: `null` unless PM's sub-headword names an occupant.
- **`occupant_alt_names`** — Alternate name forms of the SAME PERSON. For Khufu, if the text layer in the chunk contains `Cheops` (Greek form, often appears in older bibliographic refs PM cites), append to alt-names. For Khephren ↔ Khafre, Menkaureʿ ↔ Mycerinus, same rule. Only include the alt name if it actually appears verbatim in the chunk file's headword block, NOT if you "know" the Greek form from general Egyptological context. Phase A will add cross-source alt-names.
- **`occupant_role`** — Derived from the row's headword shape:
  - `"King"` when the row's identification line follows a `PYRAMID-COMPLEX OF <Name>` section heading and the row IS the main pyramid of that complex (i.e. the row whose `PYRAMID.` / `THE PYRAMID.` sub-heading appears at the top of the complex section). PM's convention: a "pyramid-complex of <Name>" entry attributes the main pyramid to that named king.
  - `"Queen"` when the row's identification line is a `Subsidiary Pyramid` sub-heading under a `PYRAMID-COMPLEX OF <Name>` section. PM's convention treats subsidiary pyramids within a pyramid-complex as queens' pyramids regardless of whether PM names the specific queen.
  - `"Unknown"` when PM's headword explicitly disclaims or queries the role (e.g. `(?)` on the occupant role itself, NOT on the date). No such cases are expected in this chunk based on a structural read of PM III.1 § I.
- **`tomb_aliases`** — Popular names of the *pyramid itself*, extracted verbatim from `called <Name>.` clauses in the Reisner identification line. Split a multi-alias `called <X> or <Y>.` clause on the literal ` or ` token, producing two list entries (`<X> Pyramid` / `<Y> Pyramid` where the trailing word `Pyramid` is implied by PM's elided phrasing — apply by reading the chunk's `called …` clause and reconstructing the full noun phrase for each alternative). When PM gives no `called …` clause for a row, return `[]`. Subsidiary-pyramid Lepsius/Vyse cross-numbering goes in `notes_from_pm`, not in `tomb_aliases` (the Lepsius-number IS a pyramid identifier but not a *popular* alias; alias is for evocative names PM marks with `called`).
- **`co_occupants`** — Empty list `[]` (no joint burials in this chunk).
- **`is_joint_burial`** — `false` (no coordinate burials in this chunk).
- **`dynasty`** — Derived from PM's `Dyn. <Roman>` line that follows the section heading (look for the literal substring `Dyn.` in the chunk text within the headword block for each row). Apply Roman→Arabic normalisation and store as a string (`Dyn. IV` → `"4"`, `Dyn. V` → `"5"`, `Dyn. VI` → `"6"`). If PM's headword block for a row carries no `Dyn. <Roman>` line, store `null`.
- **`sub_period`** — `null` for all rows.
- **`date_bce_approx_start`** / **`date_bce_approx_end`** — `null` for all rows (BCE dates are Phase-A king-authority lookup, not Phase-0 extraction).
- **`cemetery`** — `null` for the pyramid-complex rows (the pyramid IS its own complex; cemetery designation belongs to surrounding mastabas, handled in later chunks).
- **`discovery_year`** / **`discoverer`** — `null` for all rows (the Giza pyramids are not "discovered" in a modern excavation sense; PM's headword does not carry a discovery-year tag).
- **`is_unfinished`** — `false` unless PM headword literally says `Unfinished`.
- **`is_uninscribed`** — `false` unless PM headword literally says `uninscribed`.
- **`is_usurped`** — `false` unless PM headword literally says `usurp(ed|ation)`.
- **`attribution_certainty`** — Hedge-token derivation from PM's headword block:
  - `"attested"` when PM names an occupant in the headword without hedge tokens.
  - `"probable"` when PM uses `Probably`, `(probably)`, `attributed to`, `tentatively`, or `perhaps` to qualify the occupant attribution.
  - `"uncertain"` when PM uses `possibly`, `uncertain`, or the standard `(?)` attribution-uncertainty glyph; ALSO when PM does NOT name an occupant in the headword at all (`occupant_name: null` rows carry `"uncertain"` because the attribution is silent rather than positive).
  Stronger uncertainty wins on compound markers. Verify each row by reading the headword block — do NOT assume a row's certainty from class membership ("all main pyramids are attested") without confirming PM's headword for that specific row.
- **`shared_with_tombs`** — Empty list `[]` for all rows in this chunk (no `See also Tomb N` cross-references in the pyramid-complex sections).
- **`notes_from_pm`** — Verbatim short prose from PM's headword identification line. For each row: the Lepsius/Perring-Vyse/Reisner cross-numbering line in the form `Lepsius, <Roman>; Perring and Vyse, <N> of Giza; Reisner, G <Roman>(-<letter>).` plus any PM-printed `called …` clause or construction/attribution note that appears in the headword block before the first body sub-heading. PM-faithful preservation (keep PM's punctuation, capitalisation, and any text-layer rendering of typesetting glyphs). DO NOT include body-prose references, museum inventory listings, plate citations, or bibliographic refs from the body paragraphs — those are body, not headword. Trim trailing whitespace.
- **`source_citation`** — `{"page": <printed page where the row's headword first appears>, "edition": "PM III.1 2nd ed. 1974", "section": "I"}`. The `page` field is the printed page from the `===== PHYSICAL PAGE N (PRINTED PAGE M) =====` marker that precedes the headword; use `M`. Section is `"I"` for `I. PYRAMIDS` (subsection letter A/B/C distinguishes the three pyramid-complexes within `I` but lives implicitly in the row's `occupant_name`).

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk1: <count> rows; <main_pyramids>/<subsidiary_pyramids> split; <anomalies or "none">
```

Example: `agent-a-chunk1: 10 rows; 3/7 split; none`. Under 80 words including any anomaly note.
