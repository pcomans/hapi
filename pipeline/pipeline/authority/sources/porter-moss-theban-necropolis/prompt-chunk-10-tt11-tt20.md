# Extraction prompt — Porter & Moss Vol I.1 (Theban Necropolis), Chunk 10

> **Second chunk drawn from PM I.1 (Private Tombs).** Chunk 9 (TT1–TT10) introduced the PM-I.1 conventions; chunk 10 inherits them. PM I.1's printed-page offset is **+18** (printed = physical − 18), distinct from PM I.2's +458. Read chunk 9's `prompt-chunk-9-tt1-tt10.md` for the established conventions; this prompt only documents what is NEW or DIFFERENT for the TT11–TT20 range.

> **Schema reference.** Same locked schema as chunk 9 (`tomb_id`, `theban_area`, `occupant_name`, `occupant_alt_names`, `tomb_aliases`, `co_occupants`, `is_joint_burial`, `occupant_role`, `dynasty`, `sub_period`, `date_bce_approx_start`, `date_bce_approx_end`, `location_sub_area`, `discovery_year`, `discoverer`, `is_unfinished`, `shared_with_tombs`, `notes_from_pm`, `source_citation`, plus the Tier-3 typed flags `is_uninscribed`, `is_usurped`, `attribution_certainty` — emit `false`/`false`/`"attested"` defaults; `fix_rows.py` derives them post-merge from `notes_from_pm`).

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p39-p55.txt` and produce a JSONL file with one structured row per numbered tomb in PM I.1 § I "Numbered Tombs" within the **TT11–TT20** range. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-tomb answers. Every field value must trace to something in the chunk file. The only things the prompt may validly hint: structural facts about the section (page range, tomb-id range), text-layer noise signatures, vocabulary constraints, and explicit examples drawn from chunks 1–9 (for analogy, never as values to copy).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume I, Part 1: Private Tombs.* 2nd edition, Oxford 1960 (re-issued 1970).
- Section: **I. Numbered Tombs**, TT11–TT20 range.
- Offset: **printed = physical − 18** (PM I.1 convention, same as chunk 9).
- The chunk file starts at physical p.39 (printed p.21, capturing the **TT11 headword**) and extends through physical p.55 (printed p.37) so you can see the **TT22 headword** at the tail as a second boundary marker — **do NOT extract any TT21+ rows**. The TT21 headword at physical p.53 (printed p.35) is the primary stop signal; TT22 at p.55 confirms TT21 is closed.
- Per-page markers `===== PHYSICAL PAGE N (PRINTED PAGE M) =====` precede each page's text-layer dump. Use `M` (the printed number) for `source_citation.page` per the chunk-9 convention.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF, then post-processed by `postprocess.py`.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-a-chunk10.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-b-chunk10.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-c-chunk10.jsonl`

One JSON object per line. Sort rows by numeric `tomb_id` ascending (TT11 first, TT20 last). Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## How to identify a tomb headword

Each TT tomb's section begins with a heading line of the form:

```
N. NAME (cartouches), <Role-or-Title>. <Regnal-or-Dynasty>.
<Sub-site>. (Optional bibliographic cross-ref.)
```

The number is followed by **either a period (`.`) or a middle-dot (`·`) or a bullet (`•`)** — the latter two are text-layer noise for a regular period. The publisher OCR has also been observed to render an Arabic `2` as the letter `z` and a `0` as the letter `o` inside tomb-number tokens (i.e. a tomb-number can render as `zo.` instead of `20.`); recognise such headword-position tokens as their numeric reading by looking at the all-caps NAME that follows. The same lithographic-OCR class can also render `1` as `I` or `l` mid-token — but a tomb-number is always at column-zero, immediately preceded by whitespace (or page boundary) and followed by an all-caps name token; this positional shape disambiguates from non-headword `Igxx`-style year tokens.

The headword block ends at the first body sub-header — any of `Court.`, `Court with Chapel.`, `Chapel.`, `Passage.`, `Hall.`, `Burial Chamber.`, `Burial Chambers.`, `Burial Chamber of <X>.`, `Inner Room.`, `Vestibule.`, `Outer Hall.`, `Side-room.`, `Pillar.`, `Shrine.`, `Sarcophagus.`, `Entrance.`, `Finds`, or any line introducing scene-by-scene `(1) … (2) …` prose. Lines like `Father, …`, `Mother, …`, `Wife, …`, `Wives, …`, `Parents, …`, `Plan, p. N`, `Map I, …`, `Map II, …`, `Map V, …`, and the bibliographic-references paragraph (any long run of `<AUTHOR>, <Title>, …` citations between the headword block and the first body sub-header — chunk-9's `BRUYERE, Rapport …` / `CERNY, Rep. onom. …` is the canonical pattern) are part of the headword block but supply structured-field content selectively (see field rules below).

Cartouche garbage: PM prints royal/personal-name cartouches inline; the text layer renders these as `~~~`, `}}`, `c:7`, `0,`, `Q`, `Q Q`, `~`, etc. Drop the cartouche garbage from `occupant_name`. The titlecase English NAME token before the cartouche garbage is the canonical handle.

## Expected TT numbering in PM I.1 § I (TT11–TT20 range)

A pre-extraction headword scan of the chunk file confirms PM I.1 catalogues all ten numbers TT11 through TT20 in this section: **TT11, TT12, TT13, TT14, TT15, TT16, TT17, TT18, TT19, TT20**. **10 rows expected** — every number in the decade is present, no gaps (same as chunk 9; unlike KV/QV).

If your headword scan returns a number outside this range, RE-CHECK the chunk file — it may be (a) a scene-number marker like `(7)` or `(8)` (not a tomb row), (b) a plate-caption tomb-number reference like `TOMBS 9-16, 18` or `TOMBS 17, 19-25, 165` (printed pages within this chunk carry such plate captions), (c) a cross-reference from one tomb's headword to another, (d) the TT21 / TT22 headwords near the chunk tail (boundary markers, OUT of scope), or (e) a publisher running-header `Tombs N and N+1` or `Tomb N` page-header (e.g. `Tombs 16 and 17`, `Tomb 19`, `Tombs 20 and 21`). None of those are tomb headwords for THIS chunk.

## PM I.1 text-layer noise (chunk-10-specific residuals)

`postprocess.py` already runs against this chunk file. It normalises the patterns shared with chunks 1–9 (Ḥ-substitutes including the chunk-9-introduced `J.I` rule, `<` adjacent to letter for `ʿ`, the trailing-`c`-as-ayin whitelist, `Ist ed.` → `1st ed.`, king-name-anchored Roman-numeral fixes). The following noise classes are NEW or RESIDUAL in chunk 10 and are NOT yet whitelisted in the postprocessor — handle them via the rules in this section.

- **Tomb-number-position digit/letter substitution.** A headword tomb-number can appear in the postprocessed chunk text as a non-canonical glyph: an Arabic `2` rendered as `z`, an Arabic `0` rendered as `o`, or the ASCII period rendered as a middle-dot `·` or bullet `•`. Disambiguation: a tomb-number is at column-zero, immediately followed by an all-caps NAME token. A token like `zo. <CAPS-NAME>` at column zero is the tomb-number `20`; `12• <CAPS-NAME>` is the tomb-number `12`. Apply this only at headword position.
- **Capital underdot-Ḥ residuals beyond `J.I`.** PM-I.1 prints capital underdot-Ḥ (`Ḥ`) inside all-caps name tokens; chunk 9 added `J.I` to the postprocess table. Where the OCR has rendered the Ḥ-glyph as a `<DIGIT>;I`-shaped multi-glyph cluster preceding a space and the rest of the name, read this as `Ḥ<NAME-TAIL>` per PM's printed page. Apply the README's strip-Ḥ rule then to `occupant_name` (matchable field — the underdot-Ḥ becomes plain `H` there).
- **Capital underdot-Ḍ.** Where PM-I.1 prints capital underdot-Ḍ (`Ḍ`) at the start of an all-caps name token, the text-layer renders this as a noisy multi-glyph cluster `:[>` immediately preceding the rest of the all-caps name. Read this as `Ḍ` per PM's printed page. PM-I.1's underdot-Ḍ glyph in `occupant_name` is **preserved** (the README's strip rule covers underdot-Ḥ ONLY). The lowercase `ḍ` may also appear in `notes_from_pm` transliteration clauses where PM prints it; preserve as PM prints.
- **Token-final ayin `<NAME>(`.** PM's name-ending ayin (`ʿ`) renders in chunk 9 as `<LETTER>(` adjacent to a cartouche-glyph context. Chunk-10 headwords for the Draʿ Abû el-Nagaʿ sub-site contain the very common phrase `Dra' Abû el-Naga'.` as the sub-site declaration; the publisher OCR renders the trailing apostrophe as a middle-dot or bullet (`Dra· Abu el-Naga·.` / `Dra· Abu el-Naga•.`). The intended canonical English is `Draʿ Abû el-Nagaʿ`. Per chunk-7 convention `theban_area = "Draʿ Abû el-Nagaʿ"` (U+02BF ʿayin in BOTH positions, circumflex `û` per PM).

After postprocessing you'll see canonical Unicode `Ḥ`, `Ḳ`, `Ḍ`, `ʿ`, `ē`, `ō`, `ū` in body prose where the publisher noise has already been reduced. Restore the residuals listed above per the README's `occupant_name` diacritic policy.

## Schema (per row)

Every row MUST have these keys; use `null` (not omitted, not empty string) for unknown values.

```json
{
  "tomb_id": "TT<N>",
  "theban_area": "Draʿ Abû el-Nagaʿ",
  "occupant_name": "...",
  "occupant_alt_names": [],
  "tomb_aliases": [],
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
  "is_unfinished": false,
  "shared_with_tombs": [],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM I.1 2nd ed. 1960", "section": "I"},
  "is_uninscribed": false,
  "is_usurped": false,
  "attribution_certainty": "attested"
}
```

## Field-by-field extraction rules

Identical to chunk 9 unless explicitly overridden below. Re-read chunk 9's prompt for the full rules; the deltas:

### `tomb_id`
`TT<N>` where `<N>` is the Arabic tomb number from the heading line (10 expected values: TT11–TT20).

### `theban_area`
The TT11–TT20 range falls under PM I.1's Draʿ Abû el-Nagaʿ sub-site (PM declares `Dra' Abû el-Naga'.` on the line below each headword title). Use the canonical form **`"Draʿ Abû el-Nagaʿ"`** (U+02BF ʿayin in BOTH `Draʿ` and terminal `Nagaʿ` positions, circumflex `û` per PM's printed form — issue #288 migration; same convention as chunk-7's `DAN-` rows). Re-read each headword's sub-site line; if PM declares a DIFFERENT sub-site for any row in this range that is a re-check signal — the range was scoped to a single sub-site cluster.

### `occupant_name`
**PM-verbatim, conventional-English form, titlecase**, per chunk 9's diacritic policy:
- Strip underdot-Ḥ (`Ḥ` / `ḥ`) → plain `H` / `h`. Only diacritic stripped from `occupant_name`.
- Preserve ayin (`ʿ`) where PM prints it as a distinguishing radical.
- Preserve underdot-Ḳ (`Ḳ` / `ḳ`).
- **Preserve underdot-Ḍ (`Ḍ` / `ḍ`).** First chunk to surface underdot-Ḍ in a headword name token; the chunk-7/8 strip-Ḥ rule does NOT extend to underdot-Ḍ — preserve it as PM prints.
- Preserve vowel macrons (`ū`, `ō`, `ē`, `ā`) where PM prints them in name tokens — these are PM's anglicised vowel-length marks and are part of the matchable name form.
- Drop cartouche garbage.

### `occupant_role`
Controlled vocabulary unchanged. Two TT11–TT20 row shapes worth flagging:
- A headword that opens with a non-royal occupational title clause (e.g. an `Overseer of <X>`, `Scribe of <X>`, `<X>-priest of <Y>`, `Chief servant who <does X>`, `Royal butler`) maps to **`"Official"`** (chunk-7 convention); the verbatim PM clause goes in `notes_from_pm`.
- A headword that opens with `<NAME>, King's son, <secondary-title>` is a royal-blood individual whose primary functional role per PM is the secondary title (mayor / general / etc.). Apply controlled-vocab rule 2 (explicit named role) only when the role is in the controlled vocab; otherwise fall through to rule 3 (`"Official"` flatten) and preserve `King's son` verbatim in `notes_from_pm`. Same posture as a chunk-3 `Prince` mid-functional-titleholder — the controlled-vocab role names structural placement, not noble blood.

### `notes_from_pm`
Per chunk 9. Additional clause types observed in chunk-10 headwords beyond chunk 9's list:
- **Plan-page cross-references** like `Plan, p. 20` / `Plan, p. 30` — these are plan-marker references and per chunk 9 are dropped.
- **Bibliographic citations at headword level** (any `<AUTHOR>, <Title>, …` form) — drop entirely from `notes_from_pm` per chunk 9's bibliographic-paragraph rule.
- **`Partly usurped by <NAME>`** clauses — preserve verbatim if PM prints them in a TT11–TT20 headword block. (The Tier-3 deriver fires `is_usurped=true` post-merge from the `usurp` regex match.)
- **Eponym / parenthesised classical-name aliases** in role-title clauses (`Mayor of <Toponym>`, `Mayor in <Region>`, `<Functional-title> of <Estate-or-Deity>`) — preserve verbatim in `notes_from_pm` as part of the verbatim role-title clause.

### `shared_with_tombs`
Per chunk 9's rule. Body-prose mentions of other TT numbers like `(tomb 183)`, scene-internal references, and footnote misnumberings (e.g. `For WRESZ., Atlas, … called by him tomb 24, … see tomb 100 (19)`) are NOT headword cross-refs and do NOT populate `shared_with_tombs`. Apply the populate rule mechanically per headword: it fires when PM prints `Also owner of tomb N` / `Perhaps also owner of tomb N` / `See also Tomb N` / `(also owner of tombs N and M)` in the headword block, and only then.

### `co_occupants` and `is_joint_burial`
Per chunk 9's rule (apply mechanically per headword). Recall from chunk 9 the two structural branches: `<NAME-A> … and son <NAME-B>` (hierarchical, `is_joint_burial=false`, NAME-B in `co_occupants`) and `<NAME-A> … and <NAME-B>, <PLURAL-ROLE>` (coordinate, `is_joint_burial=true`, NAME-B in `co_occupants`). Single-occupant headword (no `and <NAME-B>`): `co_occupants=[]`, `is_joint_burial=false`.

## Structural gotchas to watch

- **Plate-caption headers.** `TOMBS 9-16, 18` (printed p.20 / physical p.38) and `TOMBS 17, 19-25, 165` (printed p.30 / physical p.48) are plan-page captions — NOT tomb headwords for the listed numbers. The chunk text at the corresponding physical page may render the caption with the chunk-10 lithographic-OCR digit/letter substitutions; don't be tricked.
- **Page-running-headers.** Lines like `Tombs II and I2`, `Tomb I7`, `Tombs zo and zI` (publisher running-header at the top of each printed page) are running-headers, NOT tomb headwords. Distinguish by line-position (running-headers appear at page top, after the page marker, and use Roman-numeral-style noise; tomb headwords appear at column-zero with a numeric token followed by an all-caps name).
- **Wreszinski footnote at physical p.47 (printed p.29)** carries a `[For WRESZ., Atlas, i. 126 (called by him tomb 24, …), see tomb 100 (19).]`-style footnote in body prose — this is a Wreszinski misnumbering correction, NOT a `shared_with_tombs` cross-reference for whichever tomb's body it sits in. Drop entirely from `notes_from_pm`; do NOT propagate `tomb 24` or `tomb 100` into `shared_with_tombs`.
- **Boundary marker — TT21 / TT22.** The chunk file extends through physical p.55 to include the start of TT21 and TT22 bodies so you can see both boundaries clearly. **Do not extract a TT21 or TT22 row.** Stop at the end of TT20's headword block.
- **Page boundary internal to a tomb.** TT11 spans physical p.39 (headword) into p.40+ (body); TT17 spans physical p.47 (headword) into p.48+ (body); TT19 / TT20 span similarly. The headword's PRINTED page is the page where its first headword line sits — extract from the page marker that immediately precedes the headword line, not from a body-prose page.

## Pitfall summary (read LAST before running)

1. **10 rows expected** (every TT number in TT11..TT20 has a headword in PM I.1 § I — no gaps in this decade).
2. **PM I.1 offset is +18** (printed = physical − 18). Use the `===== PRINTED PAGE M =====` marker for `source_citation.page`.
3. **`section: "I"`**, **`edition: "PM I.1 2nd ed. 1960"`** (same as chunk 9).
4. **`theban_area: "Draʿ Abû el-Nagaʿ"`** for every row in this range (U+02BF ʿayin in BOTH positions, circumflex `û` per PM).
5. **`is_joint_burial`** / **`co_occupants`**: apply the hierarchical (`X and son Y`, `false`) vs coordinate (`X and Y, plural-role`, `true`) rule mechanically per headword. Single-occupant: `is_joint_burial=false`, `co_occupants=[]`.
6. **`shared_with_tombs`**: populate when a TT11–TT20 headword carries `Also owner of tomb N` / `Perhaps also owner of tomb N` / `See also Tomb N` / `(also owner of tombs N and M)` phrasing per the field rule. Empty list `[]` otherwise.
7. **`occupant_role`** per the controlled-vocab rules; non-royal occupational titles flatten to `"Official"`. The verbatim role-title clause goes in `notes_from_pm`.
8. **`dynasty` / `sub_period` / `date_bce_*` / `location_sub_area` / `discovery_year` / `discoverer`** all `null` for every row — Phase A enrichment fills these. PM's `Temp. <King>` / `Dyn. <Numeral>` / `Ramesside.` / `Early Dyn. XVIII.` clauses go verbatim into `notes_from_pm`, not into typed fields.
9. **PM I.1 chunk-10 noise residuals**: `12•` / `zo.` for tomb-number positions; `1;I` for `Ḥ`; `:[>` for `Ḍ`; mid-dot/bullet for trailing apostrophe in `Draʿ Abû el-Nagaʿ`. Apply per the README's `occupant_name` diacritic policy and the noise section above.
10. **Tier-3 typed flags** emit defaults (`false`/`false`/`"attested"`); the `fix_rows.py` deriver overwrites post-merge.
11. **Preserve underdot-Ḍ (`Ḍ` / `ḍ`)** in `occupant_name` — first chunk to surface this glyph in a headword name token; the README's strip rule covers underdot-Ḥ ONLY.

## Report back

After writing the JSONL, output a one-paragraph report with:
- Row count (should be 10) and the complete list of TT tomb_ids you emitted in sort order.
- Any row where you're unsure about a field, with the field name and your best-guess value.
- Any unexpected text-layer noise that this prompt doesn't already flag.
- For any multi-occupant headwords or any `shared_with_tombs` headword cross-references you found in the chunk, which classification (hierarchical vs coordinate, or which cross-ref phrasing) you applied and the structural reason.

Stay under 200 words.
