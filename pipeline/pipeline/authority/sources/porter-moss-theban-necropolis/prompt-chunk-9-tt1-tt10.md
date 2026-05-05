# Extraction prompt — Porter & Moss Vol I.1 (Theban Necropolis), Chunk 9

> **First chunk drawn from PM I.1 (Private Tombs).** All prior chunks (1–8) came from PM I.2 (Royal Tombs and Smaller Cemeteries). PM I.1 has a different printed-page offset (+18, not +458) and noisier text-layer OCR. Read the "PM I.1 text-layer noise" section before you start so you recognise the new noise classes.

> **Schema reference (PR A 2026-05-02, PR #182 2026-05-03).** This prompt assumes the schema currently locked in on `main`:
>
> - `tomb_id`, `theban_area`, `occupant_name`, `occupant_alt_names`, `occupant_role`, `tomb_aliases`, `co_occupants`, `is_joint_burial`, `dynasty`, `sub_period`, `date_bce_approx_start`, `date_bce_approx_end`, `location_sub_area`, `discovery_year`, `discoverer`, `is_unfinished`, `shared_with_tombs`, `notes_from_pm`, `source_citation`, **plus the Tier-3 typed flags `is_uninscribed`, `is_usurped`, `attribution_certainty`** (derived post-merge from `notes_from_pm` by `fix_rows.py` — emit `false`/`false`/`"attested"` defaults; the deriver overwrites them deterministically).
> - `occupant_alt_names` is ONLY for alternate name forms of the SAME PERSON. Tomb-nicknames go in `tomb_aliases`.
> - `co_occupants: list[{name, role, alt_names}]` — additional people buried in the same tomb. The headword (PM's first-listed person) goes in `occupant_name` / `occupant_role` / `occupant_alt_names`; secondary occupants go in `co_occupants` with per-person role.
> - `is_joint_burial: bool` — flag coordinate burials where PM does NOT mark a principal occupant. Default `false`. Set `true` when PM lists multiple occupants coordinately (e.g. SWV-ThreePrincesses pattern: PM prints `MENHET, MERTI, AND MENWI`). Leave `false` when one occupant is the syntactic subject and the other is structurally subordinate (e.g. KV46 `YUIA …, AND THUIU …` — Yuia leads; or `X and son Y` — X is the parent, syntactic head). The bare conjunction `X and Y, <plural-role>` IS coordinate.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p18-p40.txt` and produce a JSONL file with one structured row per numbered tomb in PM I.1 § I "Numbered Tombs" within the TT1–TT10 range. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-tomb answers. Every field value must trace to something in the chunk file. The only things the prompt may validly hint: structural facts about the section (page range, tomb-id range), text-layer noise signatures, vocabulary constraints, and explicit examples drawn from chunks 1–8 (for analogy, never as values to copy).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume I, Part 1: Private Tombs.* 2nd edition, Oxford 1960 (re-issued 1970).
- Section: **I. Numbered Tombs**, opening of the volume — TT1 starts at printed p.1 (physical p.19) immediately after the Note-to-Readers preface.
- Offset: **printed = physical − 18** (NOT the +458 PM-I.2 offset of chunks 1–8). Verified against TT1 = printed p.1 = physical p.19. Each `===== PHYSICAL PAGE N (PRINTED PAGE M) =====` marker in the chunk file gives both numbers directly — use `M` (printed) for `source_citation.page`.
- The chunk file starts at physical p.18 (the `NOTE TO READERS` page that precedes § I) and extends through physical p.40 so you can see the **TT11 headword** at the tail as a boundary marker — **do NOT extract any TT11+ rows**.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF (see `transcribe.md` § "Method deviation"), then post-processed by `postprocess.py` for the documented Unicode-fixup table.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-a-chunk9.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-b-chunk9.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-c-chunk9.jsonl`

One JSON object per line. Sort rows by numeric `tomb_id` ascending (TT1 first, TT10 last). Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## How to identify a tomb headword

Each TT tomb's section begins with a heading line of the form:

```
N. NAME (cartouches), <Role-or-Title>. <Regnal-or-Dynasty>. 
<Sub-site>. (Optional bibliographic cross-ref.)
```

The number is followed by **either a period (`.`) or a middle-dot (`·`)** — the middle-dot is text-layer noise for a regular period (same convention as chunk-8's QV middle-dot). Examples in this chunk: `1.`, `2.`, `3·`, `4·`, `5·`, `6.`, `7·`, `8.`, `9·`, `10.` — the inconsistency is publisher rendering, not a tomb-id semantic distinction.

Cartouche garbage: PM prints royal/personal-name cartouches inline; the text layer renders these as `~~~`, `}}`, `c:7`, `0,`, `Q`, etc. Drop the cartouche garbage from `occupant_name`. The titlecase English NAME token before the cartouche garbage is the canonical handle.

The headword block ends at the first body sub-header — any of `Court.`, `Court with Chapel.`, `Chapel.`, `Passage.`, `Hall.`, `Burial Chamber.`, `Burial Chambers.`, `Innermost Chamber.`, `Side-room.`, `Pillar.`, `Shrine.`, `Outer Hall.`, `Inner Room.`, `Sarcophagus.`, `Finds`, or any line introducing scene-by-scene `(1) … (2) …` prose. Lines like `Father, …`, `Mother, …`, `Wife, …`, `Wives, …`, `Parents, …`, `Plan, p. N`, `Map VII, …`, and the bibliographic-references paragraph (`BRUYERE, Rapport …`, `CERNY, Rep. onom. …`, `L. D. Text, iii, p. N`) are part of the headword block but supply structured-field content selectively (see field rules below).

## Expected TT numbering in PM I.1 § I (TT1–TT10 range)

A pre-extraction headword scan of the chunk file confirms PM I.1 catalogues all ten numbers TT1 through TT10 in this section: **TT1, TT2, TT3, TT4, TT5, TT6, TT7, TT8, TT9, TT10**. **10 rows expected**.

If your headword scan returns a number outside this range, RE-CHECK the chunk file — it may be (a) a scene-number marker like `(7)` or `(8)` (not a tomb row), (b) a plate-caption tomb-number reference like `Tombs 9-16, 18` (printed p.20 of the chunk), (c) a cross-reference from one tomb's headword to another (`also owner of tomb 326`), or (d) the TT11 headword at the chunk tail (boundary marker, OUT of scope). None of those are tomb headwords for THIS chunk.

## PM I.1 text-layer noise (reproducible patterns)

PM I.1's Griffith Institute scan has noisier OCR than PM I.2. The `postprocess.py` table normalises the patterns shared across the volume; PM-I.1-specific patterns that don't yet have postprocess rules are listed here so all three agents read them the same way.

- **`J.I` (J + period + I) inside an all-caps name token** renders for capital underdot-Ḥ (`Ḥ`). The bigram `J.I` does not appear in normal English prose in this source — verified by `grep -E 'J\.I' raw/chunk-*.txt` before this prompt was written. After the postprocess.py update added in this PR, this pattern is normalised to `Ḥ` automatically — but be alert in case a chunk-text token slipped through with PM-I.1-shaped noise the postprocessor didn't catch. The README's strip-Ḥ rule then applies to `occupant_name` (matchable field).
- **Open-paren `(` adjacent to a letter then a cartouche-glyph context** (i.e. `<LETTER>(<space-then-cartouche-char>`) renders for the ayin glyph `ʿ` at the END of a name. The agent applies: ayin preserved in `occupant_name` per the README's matchable-name policy (chunk-7's `Khaʿemweset` and `ʿAḳ-hor` are the convention). Do NOT fire this rule on prose-parenthetical phrases like `(Also owner of tomb <N>.)` or `(L. D. Text, No. <N>.)` — they have a closing `)` and surrounding sentence prose, no cartouche-glyph context.
- **`I>.` (I + `>` + period) at the START of an all-caps name token** renders for capital underdot-Ḳ (`Ḳ`). Underdot-K is **preserved** in `occupant_name` per the README (chunk-7's `ʿAḳ-hor` is the convention).
- **Trailing-`c`-as-ayin** inside an all-caps name token like `RAcMOSI` (where `c` substitutes for the ayin `ʿ`). The publisher OCR renders the ayin inconsistently — both `<` (handled by Phase-2 of `postprocess.py`) and `c` (handled by Phase-3's whitelist) appear in the same chunk. PM-I.1-specific tokens that aren't in the Phase-3 whitelist appear in this chunk's raw form; restore the ayin per the README convention. English `c`-trailing tokens (`Cairo`, `Asiatic`, `Photographic`) are NOT subject to this rule and survive untouched.

The `postprocess.py` table already runs against this chunk file; you'll see `Ḥ`, `ʿ`, `Ḳ`, `Ḍ`, `ḳ`, `ʿ` in body prose where the publisher noise has been reduced to canonical Unicode. The four noise classes above are residual cases not yet whitelisted in the postprocessor.

## Schema (per row)

Every row MUST have these keys; use `null` (not omitted, not empty string) for unknown values.

```json
{
  "tomb_id": "TT<N>",
  "theban_area": "Deir el-Medina",
  "occupant_name": "...",
  "occupant_alt_names": [...],
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
  "shared_with_tombs": [...],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM I.1 2nd ed. 1960", "section": "I"},
  "is_uninscribed": false,
  "is_usurped": false,
  "attribution_certainty": "attested"
}
```

## Field-by-field extraction rules

### `tomb_id`

`TT<N>` where `<N>` is the Arabic tomb number from the heading line (10 expected values: TT1–TT10).

### `theban_area`

The PM I.1 § I "Numbered Tombs" headwords each declare a Theban sub-site on the line immediately below the title clause — extract that string verbatim per row. The TT1–TT10 range falls within a single sub-site cluster per PM's Appendix-D classification (re-read Appendix D + the chunk to confirm the canonical string and pin the literal value across all 10 rows). Use ASCII hyphen for rendering (em-dashes / hyphens normalise post-postprocess). If a row's headword declares a DIFFERENT sub-site than the rest, that is a re-check signal — the TT11+ chunks shift sub-site, and a row that doesn't fit the expected sub-site is either out-of-range or worth a closer read of the headword.

### `occupant_name`

**PM-verbatim, conventional-English form, titlecase.** Extract the NAME token from the heading line after applying the README's diacritic policy and the noise rules above.

Per README (`occupant_name` is the matchable name field for Phase-A authority joining):
- Strip underdot-Ḥ (`Ḥ` / `ḥ`) → plain `H` / `h`. Underdot-Ḥ is the ONLY scholarly diacritic stripped from `occupant_name` — same convention as chunk-8 (e.g. `IMḤOTEP` → `Imhotep`).
- Preserve ayin (`ʿ`) where PM prints it as a distinguishing radical — same convention as chunk-7 / chunk-8 (e.g. `KHAʿEMWESET` → `Khaʿemweset`).
- Preserve underdot-Ḳ (`Ḳ` / `ḳ`) — same convention as chunk-7 (`ʿAḲ-ḤOR` → `ʿAḳ-hor` retains the ḳ).
- Drop cartouche garbage (the text-layer noise after the name token).

Honorific prefixes that PM uses to introduce role (e.g. an all-caps `KING`, `PRINCE`, `QUEEN`, `VIZIER` before the name) — strip from `occupant_name`, capture in `occupant_role`. Most TT1–TT10 headwords do not lead with such a prefix; the role is given by the title clause AFTER the name (see `occupant_role` rules).

Compound-name renderings: where PM prints a hyphenated or multi-token name, preserve PM's word choice (`Pesedu` vs `Peshedu` — keep PM's spelling). When in doubt, copy what PM prints; the authority-list cross-resolution downstream handles synonyms.

### `occupant_alt_names`

Alternate name forms PM gives for the SAME PERSON in the headword block (prenomens, transliteration variants, parenthesised alternative). Empty list `[]` when absent — most TT1–TT10 headwords don't carry per-person alt-names.

`CHAMPOLLION, No. N` / `L. D. Text, No. N` / `WILKINSON MSS. v. N` cross-refs are NOT alt-names — those go in `notes_from_pm`. Tomb-nicknames (rare in TT1–TT10) go in `tomb_aliases`, not here.

### `tomb_aliases`

Popular names of the tomb itself (19th-c. surveyor designations, classical aliases, local Arabic names). Empty list `[]` when absent — TT1–TT10 are all numbered Deir el-Medina workmen's tombs; few carry popular names. If PM prints a clear alias for the TOMB (not the person), capture it here.

### `co_occupants` and `is_joint_burial`

Both fields apply ONLY when PM's headword names more than one person buried in the tomb. Apply the structural rule mechanically per headword; do not pre-count which rows in this range will hit which branch — read the chunk and let the rule fire.

- `<NAME-A> … and son <NAME-B>` (or `…and daughter <NAME-B>`, etc.) — **hierarchical** (NAME-A is the parent, syntactic head). NAME-B goes in `co_occupants` with per-person role; `is_joint_burial = false`. Same shape as KV46 `YUIA …, AND THUIU` (Yuia leads). Wife / son / daughter clauses lower in the headword (`Father, …`, `Wife, …`) describe family but those people are NOT buried in the tomb — they go in `notes_from_pm`, not `co_occupants`.
- `<NAME-A> … and <NAME-B>, <PLURAL-ROLE>` — **coordinate** (no syntactic primacy; PM lists them as a coordinate pair, the plural role applies to both). `is_joint_burial = true`. NAME-B goes in `co_occupants` with the same role as NAME-A. Same shape as SWV-ThreePrincesses (`MENHET, MERTI, AND MENWI`).
- Single-occupant headword (no `and <NAME-B>`): `co_occupants: []`, `is_joint_burial: false`.

The role assigned to each `co_occupants[]` entry follows the same controlled-vocabulary mapping as `occupant_role` (see below). Per-person `alt_names: []` is the common case; populate only if PM gives a parenthesised alternative form for that specific person.

### `occupant_role`

Controlled vocabulary: `"King"`, `"Queen"`, `"Royal Family"`, `"Vizier"`, `"Official"`, `"High Priest"`, `"Princess"`, `"Prince"`, `"Unknown"`.

Assignment rules:
1. If `occupant_name` is null (cartouche-blank / uninscribed): role `"Unknown"`.
2. If the headword title clause names a controlled-vocab role explicitly (e.g. `Vizier`, `Princess`, `King`): use it.
3. Otherwise the controlled-vocab assignment for non-royal occupational titles (workman / scribe / chiseller / foreman / priest / official) flattens to **`"Official"`** — same convention as chunk-7's DAN-Neferhotep ("Scribe of the Great Harim" → role `"Official"`). The verbatim role title PM prints in the headword title-clause (e.g. `<Title> in the Place of Truth`, `Chiseller of <Deity> in the <Workshop>`, `Chief in the <Workshop>`, `Scribe in the <Workshop>`) goes in `notes_from_pm` — extract it from the chunk, do NOT use any examples this prompt may once have enumerated as a substitute for reading the source.

### `dynasty`, `sub_period`, `date_bce_approx_start`, `date_bce_approx_end`

**All `null`** for every row at this extraction stage. Phase A enrichment fills these from the king authority. Do NOT supply from outside knowledge or from PM's `Temp. <King>` / `Dyn. <Numeral>` clauses — those go in `notes_from_pm` verbatim.

### `location_sub_area`

`null` for every TT1–TT10 row. None of the chunk-9 headwords carry a sub-site flag like `Eastern Cemetery.` (PM I.1 Appendix D's sub-site convention applies to other Deir el-Medina tombs but not to this range).

### `discovery_year`, `discoverer`

`null` for every row. `Excavated by <X>` / `Discovered by <X>` / `BRUYERE, Rapport (1924-1925)` clauses go in `notes_from_pm` only when they're part of the headword's structured prose — same convention as chunks 1–8.

### `is_unfinished`

`true` iff the literal word `Unfinished` (capital-U) appears in the headword block of a TT tomb. Otherwise `false`. Apply this rule mechanically to each headword.

### `shared_with_tombs`

List of `TT<N>` strings parsed from cross-tomb references in the headword block. PM I.1 phrasings to capture:
- `See also Tomb N` / `See also Tombs N and M`
- `Also owner of tomb N` / `(Also owner of tomb N.)` / `(Perhaps also owner of tomb N.)` / `(also owner of tombs N and M)` — same semantic relation (one occupant, multiple tombs).

Empty list `[]` when absent. Hedged variants (`Perhaps also owner of …`) DO populate `shared_with_tombs` regardless of the hedge — the cross-reference is the same structural fact whether PM hedges it or not. Do NOT emit the hedge phrase in `notes_from_pm` (see the `notes_from_pm` exclusion list — the hedge applies to the secondary-attribution cross-reference, not to the primary occupant attribution, so propagating it through `notes_from_pm` would spuriously trigger the Tier-3 `attribution_certainty="uncertain"` deriver).

Numbered TT-cross-refs only — do not list `(belonging to (4))`, `(tomb 7)` mid-prose scene cross-refs (those are scene-list internal references, not headword cross-refs).

### `notes_from_pm`

A short verbatim prose fragment from the headword block that doesn't fit a structured field. **Verbatim-preserve against PM's printed text** — preserve PM's diacritics including `ḥ`, `ʿ`, `ḳ`, `ḍ`, and PM's vowel macrons (`ē`, `ō`, `ū`) where the printed page carries them (do NOT apply the strip-ḥ rule here; that rule is for `occupant_name` only). Capture each of the following clause types from the headword as PM prints them, joined by `". "`:

- **Verbatim role-title clause** (the title description that follows the name) — this is the more specific occupational role that the controlled-vocab `"Official"` flattens; preserve PM's exact wording.
- **Regnal / dynasty clauses** (`Dyn. <Numeral>.`, `<Period>.`, `Temp. <King>.`, `Temp. <King-A> to <King-B>.`). Preserve PM's wording verbatim including any underdot-Ḥ or macron that publisher OCR has degraded; restore what PM actually prints. Same convention as chunks 1–8 (e.g. KV13 `Temp. Merneptaḥ-Siptaḥ.` preserves the underdot).
- **Family clauses on the lines below the title** (`Father, <Name>`, `Mother, <Name>`, `Wife, <Name>`, `Wives (of <X>), <Name>; (of <Y>), <Name>`, `Parents, <Name> and <Name>`). These name family members who are NOT buried in the tomb (so do NOT use `co_occupants` for them). Use the convention `Wife, <Name>.` (singular) or `Wives, <Name> and <Name>.` (plural) to mirror PM. Strip the cartouche garbage but keep the name and role-relation.
- **Object-cite parentheticals** (`(name from offering-table of <Person>, in <Museum> <Cat-No.>)`). Preserve where PM prints them — these are exactly the catalog cross-references the schema retains. Same shape as chunk-7 SWV-HatshepsutSouth's `Cairo Mus. Ent. 47032` clause.
- **Cross-numbering parentheticals** (`(L. D. Text, No. <N>.)`, `(CHAMPOLLION, No. <N>.)`). Preserve where PM prints them as headword cross-numbering.
- **Hedge tokens for PRIMARY attribution** (`(probably)`, `(?)`) when printed against the occupant's NAME or identification — preserve verbatim. These feed the Tier-3 `attribution_certainty` derivation. Primary-attribution hedges are e.g. PM printing `Probably <Name>` against the headword name itself, or `(?)` immediately after the occupant's identity clause (chunk-3 KV42 / chunk-8 QV60 are the canonical patterns).

Drop entirely from `notes_from_pm`:
- `Plan, p. N`, `Map VII, …` plan-marker references.
- The bibliographic-references paragraph itself (the long list of `BRUYERE, Rapport …`, `CERNY, Rep. onom. …` citations between the headword block and the first body sub-header).
- **The cross-tomb-ownership parentheticals** `(Also owner of tomb N.)`, `(Perhaps also owner of tomb N.)`, `(also owner of tombs N and M)` — these are structurally captured by `shared_with_tombs` (numbered cross-refs there). Do NOT also place them in `notes_from_pm`; the `Perhaps` hedge in the secondary-attribution clause would otherwise spuriously trigger the Tier-3 `attribution_certainty="uncertain"` deriver on a row whose PRIMARY attribution is fully attested. The hedge is a property of the OWNERSHIP CROSS-REFERENCE, not the primary occupant identification.

`null` when the headword has nothing beyond the bare name + cartouche garbage + `Deir el-Medina.` (rare for this range — most TT1–TT10 rows have substantial structured content).

### `source_citation`

Object with three fixed keys:

- `"edition"`: exactly `"PM I.1 2nd ed. 1960"`.
- `"section"`: exactly `"I"` (PM I.1's "I. NUMBERED TOMBS" master section — no sub-section letter for this range).
- `"page"`: the **printed** page number on which the tomb's headword line sits. Extract from the chunk file's `===== PHYSICAL PAGE N (PRINTED PAGE M) =====` markers. Use `M` (the printed number), NOT `N` (the physical number). Do NOT supply from memory.

### Tier-3 typed flags (`is_uninscribed`, `is_usurped`, `attribution_certainty`)

These three fields are **emit defaults at extraction time** — `false`, `false`, `"attested"`. The `fix_rows.py` `_apply_issue_182_migrations` deriver runs post-merge and overwrites them deterministically from regex matches against `notes_from_pm`. Do NOT pre-derive them in your output; emit the defaults so the deriver's run produces a clean idempotent log entry.

(Background, FYI only: the deriver flips `is_uninscribed=true` on `\buninscribed\b`, `is_usurped=true` on `\busurp(?:ed|ation)\b`, and sets `attribution_certainty` to `"uncertain"` on `\b(uncertain|perhaps|possibly|tentatively)\b|\(\?\)`, `"probable"` on `\bprobably\b|\(probably\)|\battributed to\b`. **Because the `notes_from_pm` exclusion rule above strips `(Perhaps also owner of tomb N.)` cross-tomb-ownership parentheticals from the field, the secondary-attribution hedge on those rows never reaches the deriver — the `attribution_certainty` for such rows stays at the default `"attested"`, which is the correct downstream consequence.** Primary-attribution hedges that ARE captured in `notes_from_pm` per the rules above (e.g. a `(probably)` qualifying the occupant's identity clause) DO fire the regex and are the cases where `"probable"` / `"uncertain"` is the correct downstream value.)

## Structural gotchas to watch

- **Scene numbers vs tomb headwords.** Long body-prose blocks `(1) … (2) … (3) … (10) …` with parenthesised numbers are scene-item markers, NOT tomb headwords. Distinguish by line-start position: tomb headwords start at column zero with `<digit><period-or-middledot> <NAME-IN-CAPS>`; scene markers are inset and start `(N)`.
- **Plate-caption headers.** `TOMBS 9-16, 18` at printed p.20 (physical p.38) is a plate-caption listing of plan numbers shown on a shared floor-plan; not a tomb headword.
- **`Tombs 6 and 7` running header** at printed p.15 (physical p.33) is a publisher's running-header label spanning the joint TT6/TT7 plan; not a tomb headword.
- **Boundary marker — TT11.** The chunk file extends through physical p.40 to include the start of TT11's body so you can see the boundary clearly. **Do not extract a TT11 row.** Stop at the end of TT10's headword block.
- **`(also owner of tombs N and M)`-style cross-refs** populate `shared_with_tombs` but do NOT generate additional rows for those numbers — TT212 and TT250 are out of scope for this chunk regardless of the cross-reference.

## Pitfall summary (read LAST before running)

1. **10 rows expected** (every TT number in TT1..TT10 has a headword in PM I.1 § I — no gaps in this decade). The expected-tomb-id-set is a STRUCTURAL invariant the prompt declares; per-row content is what you extract from the chunk file.
2. **PM I.1 offset is +18**, not +458. `printed = physical − 18`. Use the `===== PRINTED PAGE M =====` marker for `source_citation.page`.
3. **`section: "I"`**, NOT `"I.A"` (PM I.1 § I has no sub-section letter for the TT1–TT10 range).
4. **`edition: "PM I.1 2nd ed. 1960"`**, not the chunk-1–8 `"PM I.2 2nd ed. 1964"`.
5. **`theban_area`** is the headword's structural sub-site classification — every row in this range's section sits under PM I.1 § I's Appendix-D sub-site assignment. Read the chunk and use what PM declares per row.
6. **`is_joint_burial` / `co_occupants`** apply only when the headword names more than one person. Apply the `<X> and son <Y>` (hierarchical, `is_joint_burial=false`) vs `<X> and <Y>, <plural-role>` (coordinate, `is_joint_burial=true`) rule from the schema preamble. Single-occupant rows: empty `co_occupants` and `is_joint_burial=false`.
7. **`occupant_role`** assignment per the rules above (controlled-vocab `"Official"` is the typical flattening for non-royal occupational titles). The verbatim role-title clause that PM prints goes in `notes_from_pm`.
8. **`dynasty` / `sub_period` / `date_bce_*` / `location_sub_area` / `discovery_year` / `discoverer`** all `null` for every row.
9. **PM I.1 noise residuals**: `J.I` → `Ḥ`, `( <space-cartouche>` → `ʿ`, `I>.` → `Ḳ`, `c` (token-final in known transliterations) → `ʿ`. Apply per the README's `occupant_name` diacritic policy.
10. **Tier-3 typed flags** emit defaults (`false`/`false`/`"attested"`); the `fix_rows.py` deriver overwrites post-merge.
11. **`shared_with_tombs`** captures numbered TT cross-references including `Also owner of tomb <N>` / `Perhaps also owner of tomb <N>` phrasings.

## Report back

After writing the JSONL, output a one-paragraph report with:
- Row count (should be 10) and the complete list of TT tomb_ids you emitted in sort order.
- Any row where you're unsure about a field, with the field name and your best-guess value.
- Any unexpected text-layer noise that this prompt doesn't already flag.
- For any multi-occupant headwords you found in the chunk, which classification (hierarchical vs coordinate) you applied and the structural reason (which conjunction shape PM printed).

Stay under 200 words.
