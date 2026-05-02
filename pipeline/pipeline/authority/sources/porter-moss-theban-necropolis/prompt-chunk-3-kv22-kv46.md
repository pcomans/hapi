# Extraction prompt — Porter & Moss Vol I (Theban Necropolis), Chunk 3

> **Schema update — PR A (2026-05-02).** Two new fields were added to the canonical row, and `occupant_alt_names` semantics were narrowed:
>
> - **`occupant_alt_names`** is now ONLY for alternate name forms of the SAME PERSON (prenomens; throne-name vs birth-name; transliteration variants). Tomb-nicknames (`Belzoni's tomb`, `Tomb of Memnon`, `Bruce's tomb`, etc.) DO NOT belong here — they go in `tomb_aliases`.
> - **`tomb_aliases: list[str]`** is the new field for popular names of the *tomb itself* (19th-c. surveyor designations, classical mis-attributions, local Arabic names).
> - **`co_occupants: list[{name, role, alt_names}]`** is the new field for joint burials — a tomb shared by multiple people. The headword (PM's first-listed person) goes in `occupant_name` / `occupant_role` / `occupant_alt_names`; the additional people go in `co_occupants` with per-person role.
> - **`is_joint_burial: bool`** (PR #169 round-2) flags coordinate burials where PM does NOT mark a principal occupant — the headword is a serialisation artifact, not a primacy claim. Default `false`. Set `true` when PM lists multiple occupants coordinately (e.g. SWV-ThreePrincesses: PM I.2 p.591 prints `MENHET, MERTI, AND MENWI` as a coordinate triple). Leave `false` when PM marks one occupant as syntactic subject (e.g. KV46: PM I.2 p.562 prints `YUIA ..., Divine father, AND THUIU ...` — Yuia leads). Phase-A consumers MUST treat `occupant_name` and `co_occupants[*].name` as a coordinate union for join purposes when this flag is `true`.
>
> The body of this prompt is preserved as historical record from the original extraction; the schema example below has been updated to show the new fields. If you re-run an agent against this prompt, follow the updated schema, not the body's older `occupant_alt_names` directives that conflated tomb-names with person-names.


You are one of three independent extraction subagents. Your job: read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p89-p106.txt` and produce a JSONL file with one structured row per Theban tomb in this chunk. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`. Disagreements are resolved by per-field majority vote.

This is a fact-extraction task on the Griffith Institute's published topographical bibliography. Extract: tomb number, occupant name, and headword-only metadata. Do NOT extract Moss's per-room descriptive prose. Do NOT supply dynasty or BCE dates from outside knowledge — those stay null and are filled in Phase A.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-tomb answers. If you find yourself tempted to emit a value because the prompt named it, stop and re-read the chunk text. Every field value must trace to something in the chunk file. The only things the prompt may validly hint:
- structural facts about the section (what page range the chunk covers; which tomb-id range is in scope; which expected tomb-ids are absent from the section);
- text-layer noise signatures (how the publisher's PDF text layer renders certain glyphs);
- vocabulary constraints (controlled-vocab enumerations).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume I, Part 2: Royal Tombs and Smaller Cemeteries.* 2nd edition, Oxford 1964.
- Section: I. Valley of the Kings, A. Tombs.
- Chunk tomb range: **KV22, KV23, KV34, KV35, KV36, KV38, KV39, KV42, KV43, KV45, KV46** — 11 rows expected. The following KV numbers ARE NOT in PM I.2 § I.A (not gaps in this chunk file — genuinely absent from that PM section, because PM did not catalogue them as inscribed royal tombs at the time of the 1964 edition): KV24–KV33 (jump from KV23 to KV34), KV37, KV40, KV41, KV44. This is a structural fact about PM's organisation, not a hint about contents.
- Printed page range: p.547–564. Physical PDF page range: p.89–106. Offset: physical = printed − 458.
- The chunk file begins at physical p.89 (printed 547) deliberately — KV22's headword sits at the tail of p.89 (after KV20's "See also South Tomb, infra, p. 556." line). The file extends through p.106 so agents see the KV47 heading as a boundary marker closing KV46.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF. See `transcribe.md` § "Method deviation".

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-a-chunk3.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-b-chunk3.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-c-chunk3.jsonl`

(Whichever path the launching prompt tells you.)

One JSON object per line. Sort rows by numeric tomb_id ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Finding tomb headwords in the chunk text

Each tomb's section begins with a heading line of the form `N. NAME (cartouches) (parenthetical)` — a number, a period (or middle-dot rendered in the text layer as `·`), a name in the publisher's all-caps typesetting, optional hieroglyphic-cartouche garbage, and an optional parenthetical carrying classical-tradition nicknames, cross-refs, or bibliographic shorthand.

The headword block ends at the first body sub-header. Sub-headers seen in chunk-3 territory include `Approach.`, `Entrance.`, `First Corridor.`, `Corridor A.`, `Corridor B.`, `Hall D.`, `Hall E.`, `Hall J.`, `Sarcophagus Chamber.`, `Sarcophagus Chamber A.`, `Sarcophagus Chamber F.`, `Sarcophagus Chamber H.`, `Room F.`, `Pillars.`, `Pillars A-F.`, `Ceiling.`, `Finds`, `Plan, p. N.`, `Stairs.`, `Well.`, `Antechamber.`. Any of these — OR the next tomb-number heading — ends the headword block.

The bibliographic-references paragraph immediately after the headword (`LEFEBURE, ...; CHAMP., ...; L. D. Text, ...`) is NOT body prose — it's the bibliographic ribbon, part of the headword block, and contains classical aliases / cross-refs you may need for `occupant_alt_names` and `shared_with_tombs`.

Text-layer digit rendering is unreliable. A tomb number may appear as:
- Arabic: `22.`, `23.`, `35·`, `36.`, `38.`, `39·`, `42.`, `43·`, `46.`.
- Roman-via-capital-I for number sequences starting with 1 (not expected in this chunk since all tomb-ids are ≥22).
- Middle-dot `·` instead of period `.` — same meaning.
- The leading "34" appears as `34·` followed by `[Ist ed. 24]` — the bracketed `[Ist ed. N]` is PM's cross-reference to the first edition's numbering, not a tomb number itself.

When the first non-space glyph on a line is a digit sequence followed by `.` or `·` and a capital letter, that's a tomb heading. When the first non-space glyph is `(N)` or `N,` that's a scene ID INSIDE a tomb, not a new tomb heading — skip.

## Schema (per row)

Every row MUST have these keys; use `null` (not omitted, not empty string) for unknown values.

```json
{
  "tomb_id": "KV<N>",
  "valley": "Valley of the Kings",
  "occupant_name": "...",
  "occupant_alt_names": [...],
  "tomb_aliases": [...],
  "co_occupants": [],
  "is_joint_burial": false,
  "occupant_role": "...",
  "dynasty": null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "location_sub_area": null,
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": true|false,
  "shared_with_tombs": [...],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM I.2 2nd ed. 1964", "section": "I.A"}
}
```

## Field-by-field extraction rules

### `tomb_id`

`KV<N>` where `<N>` is the Arabic-numeral tomb number recovered from the heading line. Strip any Roman/mixed rendering back to Arabic. Expected set: {22, 23, 34, 35, 36, 38, 39, 42, 43, 45, 46}. If you find a heading for KV24–KV33, KV37, KV40, KV41, or KV44, re-check — those numbers are documented absent from this PM section.

### `valley`

Always exactly `"Valley of the Kings"` for this chunk.

### `occupant_name`

**PM-verbatim, conventional-English form, titlecase, with regnal Roman numeral**. Extract the NAME token from the heading line after normalising text-layer noise. Preserve PM's scholarly spelling even when a more common modern form exists — Phase A ruler-authority reconciliation bridges to modern forms. Examples of the policy (not per-tomb hints — these are normalisation cases you might encounter for ANY row):

- If PM prints `SETHOS`, emit `Sethos` (not `Seti`). Same principle for any other scholarly-variant spelling.
- If PM prints `AMENOPHIS`, emit `Amenophis` (PM's preferred English form at the time; Phase A reconciles to modern `Amenhotep` if needed). Do NOT substitute `Amenhotep`.
- If PM prints `TUTHMOSIS`, emit `Tuthmosis` (PM's form). Do NOT substitute `Thutmose`.
- If PM prints a compound name with an **underdot-H** glyph like `MAI:IIRPER` (the `:I` / `;I` sequence is the text-layer rendering of the underdot `ḥ`, NOT an ayin `ꜥ`), render the underdot as plain `h` (chunk-1/2 precedent: Hatshepsut / Merneptah without underdot). The `I:I` glyph drops to `h`, not `ḥ`.
- If PM prints `UNINSCRIBED` or a descriptive phrase (e.g. `Uninscribed tomb, attributed to ...`) instead of a name, emit `occupant_name: null`. Put the descriptive content in `notes_from_pm`.

Text-layer noise to normalise (glyph-rendering artifacts, not PM's scholarly choice):

- `I:I` or `I;I` → `h`: `MAI:IIRPER` → `Mahirper` (the I;I consumes its surrounding slot — no `i` is left before the `h`; the pattern is `MA` + `h` + `IRPER`, NOT `MAI` + `h` + `IRPER`). Same for `MERNEPTAI;I` → `Merneptah`.
- Regnal-numeral Roman numerals are GLYPH-COUNTED from the text layer. Count the capital-I glyphs — including any that appear as lowercase-l (`Il`) or separated by spaces — and emit the total Roman numeral. Examples: `SETHOS Il` → `Sethos II` (two I-glyphs: `I` + `l`). `AMENOPHIS I Il` → `Amenophis III` (three I-glyphs: `I` + `I` + `l`). `Ill` at the end of a name → `III`. Do NOT memorise a per-king table — count the glyphs in each row and sum them.
- `n` as a regnal numeral (lower-case `n`) in some headwords → Roman `II`: if you see `AMENOPHIS n` at a headword that's clearly Amenophis II, that's a text-layer rendering of `II`, not the letter `n`.
- Middle-dot `·` in the heading's number separator → period.
- Cartouches after the name render as garbage — drop entirely.
- Titlecase the all-caps heading: `AMENOPHIS` → `Amenophis`, `TUTHMOSIS` → `Tuthmosis`, `YUIA` → `Yuia`, `THUIU` → `Thuiu`.

### `occupant_alt_names`

A list of alternative names PM gives in the headword block. Two things count:

1. **Single-quoted classical-tradition nicknames** inside a parenthetical that follows the cartouches. Example pattern: `('Schai' of PRISSE and NESTOR L'HÔTE.)` — the quoted `Schai` is a classical alias.
2. **Classical-traveller occupant-ascriptions** inside a `('Tomb of <Name>', ...)` or `(<Name>'s tomb, ...)` quoted parenthetical — the `<Name>` inside the quotes, not the literal `Tomb of <Name>`. (E.g. chunk 1's KV9 `'Tomb of Memnon'` → alias `Memnon`.)

Things that do NOT count (do not collect as alt names):
- Bibliographic cross-references: `CHAMPOLLION, No. x`, `L. D. Text and WILKINSON, No. 22`, `BURTON, B`, `HAY, No. 13` — these are classical-traveller publication numbering, not an alias for the occupant.
- `Descr. Ant. 'Tombeau isolé de l'ouest'` — a French positional descriptor, still bibliographic.
- Cross-refs to other tombs (`See also Tomb N`) — those go in `shared_with_tombs`.
- Usurper names or relational phrases (`wife of X`, `son of X`, `re-used by X`) — those go in `notes_from_pm`.

Empty list `[]` when no quoted alias appears in the headword.

### `occupant_role`

Controlled vocabulary (exact strings): `"King"`, `"Queen"`, `"Royal Family"`, `"Vizier"`, `"Official"`, `"High Priest"`, `"Princess"`, `"Prince"`, `"Unknown"`.

Assignment rules, in order (same as chunk 2; applied per row):

1. If `occupant_name` is null (PM says `UNINSCRIBED` or a descriptive `Uninscribed tomb, ...` phrase), role is `"Unknown"`.
2. If the headword explicitly names a role (titles or relational phrases), use it:
   - `Vizier` → `"Vizier"`.
   - `Chancellor` → `"Official"` (no dedicated Chancellor slot in the vocab).
   - `Governor of the town` (common Egyptian vizier title) → `"Vizier"` when paired with `Vizier` in the same line; otherwise `"Official"`.
   - `Standard-bearer`, `Child of the nursery`, `Overseer of the Fields of Amun`, `Doorkeeper of the House of Amun`, `Divine father`, `Chief of the harim` → `"Official"` (no finer-grained vocab).
   - `son of <King>` → `"Prince"`. `daughter of <King>` → `"Princess"`. `wife of <King>` → `"Queen"` (unless rule 3 overrides).
   - `Royal Family` catch-all: if multiple relational phrases combine (e.g. `parents of Queen <X>`) and no single rank applies to all occupants, use `"Royal Family"`.
3. If the tomb's occupant has cartouches in the PM headword AND the surrounding text refers to them as `King` or uses `King's names` in the scene-ref ribbon, role is `"King"` regardless of biological sex.
4. Otherwise role is `"King"` by default for KV tombs (KV § I.A is the royal tombs section).

### `dynasty`

**`null`** for every row. PM's headwords do not print dynasty numbers. Phase A ruler-authority enrichment against pharaoh.se fills this. **Note:** some rows in this chunk DO include regnal-era phrases in PM's headword (e.g. `Temp. Hatshepsut`, `Temp. Amenophis II`). Those phrases go in `notes_from_pm`, NOT in `dynasty` — `dynasty` is the Arabic-numeral dynasty ID which PM does not state verbatim.

### `sub_period`

**`null`** for every row at this extraction stage.

### `date_bce_approx_start` / `date_bce_approx_end`

**`null`** for every row. Phase A fills these.

### `location_sub_area`

PM flags certain KV tombs with an explicit sub-area. `West Valley` is the main flag seen in this chunk — KV23 Ay and possibly KV25 (absent here) and KV63 (absent) are in the West Valley, and PM writes `West Valley.` at the end of the headword parenthetical to mark it. If the headword carries such a flag, emit it verbatim (`"West Valley"`). Otherwise `null`.

### `discovery_year` / `discoverer`

**`null`** for every row. PM names `Davis`, `Carter`, `Carnarvon`, `Loret`, `Ayrton`, `Daressy`, etc. in bibliographic ribbons as *publication* references, not as statements of who *discovered* the tomb. `Excavated by X` phrases in body prose are discoverer info but sit past the first body sub-header and are out of scope for the headword-only rule. **But** if a phrase like `Excavated by <X>` appears inside the headword block (before the first body sub-header), capture it in `notes_from_pm`, not in `discoverer` — the `discoverer` field is reserved for structured values added by a future Phase-A enrichment step.

### `is_unfinished`

`true` if the literal word `Unfinished` (capital-U) appears in the headword block. KV39 has `Uninscribed tomb, attributed to ...` — the word here is `Uninscribed`, NOT `Unfinished`. `Uninscribed` means "no inscriptions / no occupant identified from inscriptions", which feeds into `occupant_name=null` + `occupant_role="Unknown"`, but does NOT set `is_unfinished=true`. The two concepts are distinct in PM: "Unfinished" = construction incomplete, "Uninscribed" = decoration never applied / no name given.

### `shared_with_tombs`

A list of `KV<N>` strings parsed from `See also Tomb N` / `See also Tombs N and M` phrases in the headword block. Only **numbered** references count. Informal references like `See also South Tomb, infra, p. N` do NOT populate this list (that went to `[]` in chunk 2 for KV20).

Empty list `[]` when no numbered cross-ref appears.

### `notes_from_pm`

A short verbatim prose fragment from the headword block that doesn't fit any structured field. Capture things like:
- Biographical/relational phrases: `wife of <King>`, `son of <King>`, `parents of Queen <X>`.
- Regnal-dating phrases: `Temp. <King>`, `Temp. <King A>-<King B>` (PM shorthand for "in the reign of").
- Job-title clauses that don't fit `occupant_role` precisely: `Standard-bearer, Child of the nursery`, `Overseer of the Fields of Amun, Dyn. XVIII`, `Dyn. XXII (name from scarab)` — these are biographical context.
- Re-use / usurpation phrases: `re-used by <King>`, `Usurped by <King>`, `Shared with <King>`.
- Descriptive attributions on uninscribed tombs: `Uninscribed tomb, attributed to <King> by <scholar> in <citation>`.
- `Excavated by <X>` when it appears inside the headword block.
- Any short clause that PM prints in the headword but isn't the name/cartouche/ribbon/sub-header.

Preserve PM's wording. Apply text-layer noise normalisation (`Il` → `II`, `I:I` → `h`, titlecase small-caps king names). If two distinct headword phrases should both be captured, join them with `". "` (period-space). If an attribution phrase is long, truncate after the scholar's citation verb (e.g. keep `attributed to Amenophis I by Weigall in Ann. Serv. xi (1911)`, drop subsequent plate/page refs).

`null` when the headword has nothing beyond the name + cartouches + bibliographic ribbon.

### `source_citation`

Object with three fixed keys:

- `"edition"`: exactly `"PM I.2 2nd ed. 1964"`.
- `"section"`: exactly `"I.A"`.
- `"page"`: the printed page number on which the tomb's headword line sits. **Extract from the chunk text — do NOT supply from a hardcoded table.** Method:
  1. The chunk file uses form-feed (`\f`, ASCII 12) as a page separator.
  2. Each physical page begins with a running header. Recto pages typically show the tomb number and the printed page number (e.g. `Tomb 22 549`, `Tombs 23 and 34 551`, `Tomb 34 553`, `Tombs 47, 48, and 55 565`). Verso pages typically show `<page> VALLEY OF THE KINGS` (sometimes with OCR-mangled page digits like `sso` for `550`, `ss6` for `556`).
  3. When the running header shows a legible printed-page digit, use it.
  4. When it's mangled or absent, derive via the offset: printed = physical + 458. The chunk file's first physical page = overall physical p.89 = printed p.547; count form-feeds to find which physical page a headword sits on, then add the offset.
  5. When a headword appears at the tail of one page (e.g. KV22's `22. AMENOPHIS II` at the tail of p.547), use the page where the heading line itself appears, not where its bibliographic ribbon flows to.

## Shared-row patterns

Two headword patterns in this chunk don't fit the single-name / single-role default. Both are structural — describe the SHAPE of the rule, find the matching tomb(s) in the chunk text yourself:

### Pattern A — multi-occupant headword

When PM's headword prints TWO names connected by `and` (typically two non-royal figures buried together, e.g. a husband-and-wife pair), with a shared biographical context (e.g. `parents of Queen <X>`):

- `occupant_name`: extract both names from PM's headword in PM's order, join with `" and "` (titlecased: e.g. `"<Name1> and <Name2>"`).
- `occupant_role`: use `"Royal Family"` when the relational phrase names them as royal in-laws (parents/siblings of a king or queen), regardless of their own non-royal titles. Use the specific title (`"Official"`, `"Queen"`, etc.) when both figures share the same title and no royal-in-law phrase is present.
- `notes_from_pm`: capture both figures' titles plus the relational phrase PM gives, in PM's wording. Separate the two figures' clauses with `"; "` (semicolon-space) to preserve the pairing.

### Pattern B — re-used tomb headword

When PM's headword prints an original occupant with their Dynasty, then `re-used by <Name>` with a later-Dynasty title:

- `occupant_name`: the ORIGINAL occupant (pre-`re-used`). Do NOT compound with the re-user's name — the tomb is, for PM's purposes, the original owner's tomb.
- `occupant_role`: based on the ORIGINAL owner's title and rule 2 above.
- `notes_from_pm`: capture PM's full re-use clause verbatim, including both figures' titles and both dynasties. `re-used by`, `Re-used by`, and `reused by` are all variants — preserve PM's casing and hyphenation.

## Pitfall summary (read LAST before running)

1. **Output exactly one JSONL file** at the launcher-specified path; one JSON object per line; sort by numeric tomb id; deterministic serialisation.
2. **11 rows expected**: tomb_ids {22, 23, 34, 35, 36, 38, 39, 42, 43, 45, 46}. If you count more, you've picked up a scene-ref `(N)` or a noisy body line. If you count fewer, re-check for headword patterns under the noise.
3. **Do NOT supply dynasty or BCE dates** from your knowledge.
4. **Do NOT over-modernise occupant names**. PM-verbatim.
5. **KV39 `is_unfinished` is `false`**. `Uninscribed` is not `Unfinished`.
6. **Watch for the two shared-row patterns** (see "Shared-row patterns" section above): multi-occupant (two names joined by `and` → both in `occupant_name`, role may be `Royal Family`) and re-used (`re-used by` → original occupant in `occupant_name`, re-user goes in `notes_from_pm`). These patterns appear in this chunk — identify matches by reading the chunk text, not by memorising which tomb_id they attach to.
7. **`West Valley` in a headword** → populate `location_sub_area: "West Valley"`. This is the only location_sub_area value seen in PM I.2 § I.A.
8. **Cartouche garbage drops entirely**.
9. **`source_citation.page` comes from the chunk text**, not from your knowledge.
10. **Skip body prose** starting at the first sub-header after the headword + bibliographic ribbon.

## Report back

After writing the JSONL, output a one-paragraph report with:
- Row count.
- Any row where you're unsure about a field, with the field name and your best-guess value.
- Any unexpected text-layer noise that this prompt doesn't already flag.

Stay under 150 words.
