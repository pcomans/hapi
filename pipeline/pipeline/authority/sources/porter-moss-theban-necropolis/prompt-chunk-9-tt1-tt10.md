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

- **`J.I` (J + period + I)** in an all-caps name context renders for capital underdot-Ḥ (`Ḥ`). Example expected in this chunk: `NEFERJ.IOTEP` → `NEFERḤOTEP` → after the README's strip-Ḥ rule for `occupant_name` → `Neferhotep`. The bigram `J.I` does not appear in normal English prose in this source — verify by grep before extending the rule.
- **Open-paren `(` adjacent to a letter then a space-cartouche** (i.e. `<LETTER>( <cartouche-char>`) renders for the ayin glyph `ʿ` at the END of a name. Example: `KHA( ~. Chief in the Great Place.` → headword name is `KHAʿ` → `Khaʿ` (ayin preserved per README's matchable-name policy — same convention as chunk-7's `Khaʿemweset` / `ʿAḳ-hor`). Do NOT fire this rule on parenthetical phrases like `(Also owner of tomb 326.)` — they have a closing `)` and surrounding prose, no cartouche-glyph context.
- **`I>.` (I + > + period)** at name start in an all-caps context renders for capital underdot-Ḳ (`Ḳ`). Example: `I>.EN` → `ḲEN` → `Ḳen` (underdot-K **preserved** in `occupant_name` per README). Same policy as chunk-7's `ʿAḳ-hor`.
- **Trailing-`c`-as-ayin** in token-exact occupant-name forms: `RAcMosi` → `Raʿmose`. The trailing `c` substitutes for `ʿ` (ayin) in roughly 5% of ayin occurrences (per `postprocess.py`'s § 3). The token `RAcMosi`/`Racmosi` is not in the postprocessor's whitelist so you see it in raw form here.

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

`"Deir el-Medina"` for every row in this chunk's TT1–TT10 range — every headword in scope explicitly declares `Deir el-Medina.` on the line immediately below the title clause. The literal string MUST be `"Deir el-Medina"` (em-dashes / hyphens render consistently as ASCII hyphen post-postprocess). If a row's headword does NOT print `Deir el-Medina`, RE-CHECK the section assignment — the TT11+ rows shift sub-site (TT11 is Dra' Abu el-Naga) and would land in a future chunk, not this one.

### `occupant_name`

**PM-verbatim, conventional-English form, titlecase.** Extract the NAME token from the heading line after applying the README's diacritic policy and the noise rules above.

Per README (`occupant_name` is the matchable name field for Phase-A authority joining):
- Strip underdot-Ḥ (`Ḥ` / `ḥ`) → plain `H` / `h` (`NEFERḤOTEP` → `Neferhotep`, `RAḤMOSE` → `Rahmose`). Underdot-Ḥ is the ONLY scholarly diacritic stripped from `occupant_name`.
- Preserve ayin (`ʿ`) where PM prints it as a distinguishing radical (`KHAʿBEKHNET` → `Khaʿbekhnet`; `RAʿMOSE` → `Raʿmose`; `KHAʿ` → `Khaʿ`; `NEFERʿABET` → `Neferʿabet`).
- Preserve underdot-Ḳ (`Ḳ` / `ḳ`) (`ḲEN` → `Ḳen`).
- Drop cartouche garbage (the text-layer noise after the name token).

Honorific prefixes that PM uses to introduce role (e.g. an all-caps `KING`, `PRINCE`, `QUEEN`, `VIZIER` before the name) — strip from `occupant_name`, capture in `occupant_role`. Most TT1–TT10 headwords do not lead with such a prefix; the role is given by the title clause AFTER the name (see `occupant_role` rules).

Compound-name renderings: where PM prints a hyphenated or multi-token name, preserve PM's word choice (`Pesedu` vs `Peshedu` — keep PM's spelling). When in doubt, copy what PM prints; the authority-list cross-resolution downstream handles synonyms.

### `occupant_alt_names`

Alternate name forms PM gives for the SAME PERSON in the headword block (prenomens, transliteration variants, parenthesised alternative). Empty list `[]` when absent — most TT1–TT10 headwords don't carry per-person alt-names.

`CHAMPOLLION, No. N` / `L. D. Text, No. N` / `WILKINSON MSS. v. N` cross-refs are NOT alt-names — those go in `notes_from_pm`. Tomb-nicknames (rare in TT1–TT10) go in `tomb_aliases`, not here.

### `tomb_aliases`

Popular names of the tomb itself (19th-c. surveyor designations, classical aliases, local Arabic names). Empty list `[]` when absent — TT1–TT10 are all numbered Deir el-Medina workmen's tombs; few carry popular names. If PM prints a clear alias for the TOMB (not the person), capture it here.

### `co_occupants` and `is_joint_burial`

Both fields apply ONLY when PM's headword names more than one person buried in the tomb.

The TT1–TT10 range contains two such headwords. The pattern distinction is structural:

- `<NAME-A> … and son <NAME-B>` — **hierarchical** (NAME-A is the parent, syntactic head). NAME-B goes in `co_occupants` with per-person role; `is_joint_burial = false`. Same shape as KV46 `YUIA …, AND THUIU` (Yuia leads). Wife / son / daughter clauses lower in the headword (`Father, …`, `Wife, …`) describe family but those people are NOT buried in the tomb — they go in `notes_from_pm`, not `co_occupants`.
- `<NAME-A> … and <NAME-B>, <PLURAL-ROLE>` — **coordinate** (no syntactic primacy; PM lists them as a coordinate pair, the plural role applies to both). `is_joint_burial = true`. NAME-B goes in `co_occupants` with the same role as NAME-A. Same shape as SWV-ThreePrincesses (`MENHET, MERTI, AND MENWI`).

The role assigned to each `co_occupants[]` entry follows the same controlled-vocabulary mapping as `occupant_role` (see below) — `"Official"` for a workman / scribe / chiseller / foreman, etc. Per-person `alt_names: []` is the common case; populate only if PM gives a parenthesised alternative form for that specific person.

Default for the eight non-joint TT rows: `co_occupants: []`, `is_joint_burial: false`.

### `occupant_role`

Controlled vocabulary: `"King"`, `"Queen"`, `"Royal Family"`, `"Vizier"`, `"Official"`, `"High Priest"`, `"Princess"`, `"Prince"`, `"Unknown"`.

Assignment rules:
1. If `occupant_name` is null (cartouche-blank / uninscribed): role `"Unknown"`. None of the TT1–TT10 headwords are uninscribed.
2. If the headword title clause names a controlled-vocab role explicitly (e.g. `Vizier`): use it.
3. Default for TT1–TT10: most occupants are Deir el-Medina workmen / scribes / foremen / chisellers — controlled-vocab assignment is **`"Official"`** (same convention as chunk-7's DAN-Neferhotep "Scribe of the Great Harim" → role `"Official"`). The verbatim title (`Servant in the Place of Truth`, `Chiseller of Amun in the Place of Truth`, `Foremen in the Place of Truth`, `Chief in the Great Place`, `Scribe in the Place of Truth`) goes in `notes_from_pm`.

### `dynasty`, `sub_period`, `date_bce_approx_start`, `date_bce_approx_end`

**All `null`** for every row at this extraction stage. Phase A enrichment fills these from the king authority. Do NOT supply from outside knowledge or from PM's `Temp. Ramesses II.` / `Dyn. XIX.` clauses — those go in `notes_from_pm` verbatim.

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

A short verbatim prose fragment from the headword block that doesn't fit a structured field. **Verbatim-preserve against PM's printed text** — preserve PM's diacritics including `ḥ`, `ʿ`, `ḳ`, `ḍ` (do NOT apply the strip-ḥ rule here; that rule is for `occupant_name` only). Capture, joined by `". "`:

- **Verbatim title clause** (the role description that follows the name): `Servant in the Place of Truth on the west of Thebes`, `Chiseller of Amun in the Place of Truth`, `Chief in the Great Place`, `Foremen in the Place of Truth`, `Scribe in the Place of Truth`, `Charmer of scorpions`, `Overseer of works`. Capture verbatim — these encode the more specific occupational role that the controlled-vocab `"Official"` flattens.
- **Regnal / dynasty clauses:** `Dyn. XIX.`, `Ramesside.`, `Temp. Ramesses II.`, `Temp. Amenophis II, Tuthmosis IV, and Amenophis III.`, `Temp. Ḥarem(ḥ)ab to Ramesses II.`. Preserve PM's wording verbatim including any underdot-Ḥ that publisher OCR has degraded; restore what PM actually prints.
- **Family clauses on the lines below the title:** `Father, <Name>`, `Mother, <Name>`, `Wife, <Name>`, `Wives (of <X>), <Name>; (of <Y>), <Name>`, `Parents, <Name> and <Name>`. These name family members who are NOT buried in the tomb (so do NOT use `co_occupants` for them). The names go in `notes_from_pm` only if PM prints them in the headword block — which it does for most TT1–TT10 rows. Use the convention `Wife, <Name>.` (singular) or `Wives, <Name> and <Name>.` (plural) to mirror PM. Strip the cartouche garbage but keep the name and role-relation.
- **Cross-numbering parentheticals:** `(L. D. Text, No. 96.)`, `(L. D. Text, No. 107.)`, `(CHAMPOLLION, No. N)`. Preserve where PM prints them as headword cross-numbering.
- **Hedge tokens for PRIMARY attribution:** `(probably)`, `(?)` printed against the occupant's NAME or against the occupant's identification — preserve verbatim. These feed the Tier-3 `attribution_certainty` derivation. Examples of primary-attribution hedges: PM printing `… (probably) …` or `Probably <Name>` against the headword name itself, or `(?)` immediately after the occupant's role/identity clause.

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

(Background, FYI only: the deriver flips `is_uninscribed=true` on `\buninscribed\b`, `is_usurped=true` on `\busurp(?:ed|ation)\b`, and sets `attribution_certainty` to `"uncertain"` on `\b(uncertain|perhaps|possibly|tentatively)\b|\(\?\)`, `"probable"` on `\bprobably\b|\(probably\)|\battributed to\b`. The `Perhaps also owner of tomb N` phrasing in TT4's headword DOES fire the `\bperhaps\b` rule — that's expected, the hedge applies to the cross-tomb attribution, and `attribution_certainty="uncertain"` is the correct downstream consequence.)

## Structural gotchas to watch

- **Scene numbers vs tomb headwords.** Long body-prose blocks `(1) … (2) … (3) … (10) …` with parenthesised numbers are scene-item markers, NOT tomb headwords. Distinguish by line-start position: tomb headwords start at column zero with `<digit><period-or-middledot> <NAME-IN-CAPS>`; scene markers are inset and start `(N)`.
- **Plate-caption headers.** `TOMBS 9-16, 18` at printed p.20 (physical p.38) is a plate-caption listing of plan numbers shown on a shared floor-plan; not a tomb headword.
- **`Tombs 6 and 7` running header** at printed p.15 (physical p.33) is a publisher's running-header label spanning the joint TT6/TT7 plan; not a tomb headword.
- **Boundary marker — TT11.** The chunk file extends through physical p.40 to include the start of TT11's body so you can see the boundary clearly. **Do not extract a TT11 row.** Stop at the end of TT10's headword block.
- **`(also owner of tombs N and M)`-style cross-refs** populate `shared_with_tombs` but do NOT generate additional rows for those numbers — TT212 and TT250 are out of scope for this chunk regardless of the cross-reference.

## Pitfall summary (read LAST before running)

1. **10 rows expected**: TT1, TT2, TT3, TT4, TT5, TT6, TT7, TT8, TT9, TT10. Every number in TT1..TT10 is present in PM I.1 § I.
2. **PM I.1 offset is +18**, not +458. `printed = physical − 18`. Use the `===== PRINTED PAGE M =====` marker for `source_citation.page`.
3. **`section: "I"`**, NOT `"I.A"` (PM I.1 § I has no sub-section letter for the TT1–TT10 range).
4. **`edition: "PM I.1 2nd ed. 1960"`**, not the chunk-1–8 `"PM I.2 2nd ed. 1964"`.
5. **`theban_area: "Deir el-Medina"`** for all 10 rows (Deir el-Medina workmen).
6. **Two joint burials in this range** (rows where the headword names two people). One is hierarchical (`X and son Y`), one is coordinate (`X and Y, plural-role`). Apply the `is_joint_burial` rule from the schema preamble.
7. **`occupant_role: "Official"`** for the entire range — Deir el-Medina workmen, foremen, scribes, chisellers all map to the controlled-vocab `"Official"`. The verbatim title clause (`Servant in the Place of Truth`, etc.) goes in `notes_from_pm`.
8. **`dynasty` / `sub_period` / `date_bce_*` / `location_sub_area` / `discovery_year` / `discoverer`** all `null` for every row.
9. **PM I.1 noise residuals**: `J.I` → `Ḥ`, `( <space-cartouche>` → `ʿ`, `I>.` → `Ḳ`, `c` (token-final in known transliterations) → `ʿ`. Apply per the README's `occupant_name` diacritic policy.
10. **Tier-3 typed flags** emit defaults (`false`/`false`/`"attested"`); the `fix_rows.py` deriver overwrites post-merge.
11. **`shared_with_tombs`** captures numbered TT cross-references including `Also owner of tomb N` / `Perhaps also owner of tomb N` phrasings.

## Report back

After writing the JSONL, output a one-paragraph report with:
- Row count (should be 10) and the complete list of TT tomb_ids you emitted in sort order.
- Any row where you're unsure about a field, with the field name and your best-guess value.
- Any unexpected text-layer noise that this prompt doesn't already flag.
- Whether you treated TT6 and TT10 as joint or hierarchical (and which `is_joint_burial` value you set on each).

Stay under 200 words.
