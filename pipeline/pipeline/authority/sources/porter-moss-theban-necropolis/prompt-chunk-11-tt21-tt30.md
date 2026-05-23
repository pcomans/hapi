# Extraction prompt — Porter & Moss Vol I.1 (Theban Necropolis), Chunk 11

> **Third chunk drawn from PM I.1 (Private Tombs).** Chunk 9 (TT1–TT10) and chunk 10 (TT11–TT20) established the PM-I.1 conventions. This prompt is **self-contained** — the agent does NOT need to read prior chunks' prompts; every field rule, schema invariant, and noise pattern is documented here in full. (Per chunk-10 code-reviewer P1 #3: cross-prompt references are fragility risk; each subagent reads exactly one prompt.)

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/chunk-p53-p68.txt` and produce a JSONL file with one structured row per numbered tomb in PM I.1 § I "Numbered Tombs" within the **TT21–TT30** range. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** this prompt gives field-extraction RULES and normalisation conventions — it does NOT hand you per-tomb answers. Every field value must trace to something in the chunk file. The only things the prompt may validly hint: structural facts about the section (page range, tomb-id range), text-layer noise signatures, vocabulary constraints, and explicit examples drawn from PRIOR landed chunks (chunks 1–10) for analogy. NEW row shapes that appear for the first time in chunk 11 (heterogeneous sub-sites, usurpation pattern, cross-valley cross-references, Vizier role) are documented here as RULES, not as per-row values to copy.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume I, Part 1: Private Tombs.* 2nd edition, Oxford 1960 (re-issued 1970).
- Section: **I. Numbered Tombs**, TT21–TT30 range.
- PM I.1 offset: **printed = physical − 18** (distinct from PM I.2's +458 used in chunks 1–8).
- The chunk file starts at physical p.53 (printed p.35, capturing the **TT21 headword**) and extends through physical p.68 (printed p.50) so you can see boundary markers TT31, TT32, and TT33 — **do NOT extract any TT21+ rows beyond TT30**. Stop at the end of TT30's headword block.
- Per-page markers `===== PHYSICAL PAGE N (PRINTED PAGE M) =====` precede each page's text-layer dump. Use `M` (the printed number) for `source_citation.page`.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF, then post-processed by `postprocess.py`.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-a-chunk11.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-b-chunk11.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/raw/agent-c-chunk11.jsonl`

One JSON object per line. Sort rows by numeric `tomb_id` ascending (TT21 first, TT30 last). Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — full schema, no cross-references)

Every row MUST have these 22 keys; use `null` (not omitted, not empty string) for unknown values.

```json
{
  "tomb_id": "TT<N>",
  "theban_area": "<sub-site string per row>",
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

## How to identify a tomb headword

Each TT tomb's section begins with a heading line of the form:

```
N. NAME (cartouches), <Role-or-Title>. <Regnal-or-Dynasty>.
<Sub-site>. (Optional bibliographic cross-ref.)
```

The number is followed by **a period (`.`), middle-dot (`·`), bullet (`•`), OR colon (`:`)** — all four are text-layer-noise variants of the same headword separator. The tomb-number digits themselves can be substituted by visually-similar letters when the publisher OCR confuses Arabic numerals with characters: `z` for `2`, `o` for `0`, `I` for `1`, `J5` for `27`-style-ligatures, etc. Disambiguation: a tomb-number is at column-zero, immediately followed by an all-caps NAME token. A spaced rendering like `3 I. K H oN s` at column zero (with mid-token spaces inside both number and name) is still a tomb-number headword; collapse spaces and read as `31. KHONS`. The `===== PHYSICAL PAGE N =====` markers also start at column zero — distinguish by the second token (page-marker → `PHYSICAL`; tomb-row → all-caps NAME).

The headword block ends at the first body sub-header — any of `Court.`, `Court with Chapel.`, `Chapel.`, `Passage.`, `Hall.`, `Burial Chamber.`, `Burial Chambers.`, `Burial Chamber of <X>.`, `Inner Room.`, `Vestibule.`, `Outer Hall.`, `Side-room.`, `Pillar.`, `Shrine.`, `Sarcophagus.`, `Entrance.`, `Stairway to entrance.`, `Façade.`, `Forecourt.`, `Portico.`, `Finds`, or any line introducing scene-by-scene `(1) … (2) …` prose. Lines like `Father, …`, `Mother, …`, `Wife, …`, `Wives, …`, `Wives (of <X>), …`, `Parents, …`, `Plan, p. N`, `Map I, …`, `Map II, …`, `Map IV, …`, `Map V, …`, `Map VI, …`, and the bibliographic-references paragraph (any long run of `<AUTHOR>, <Title>, …` citations between the headword block and the first body sub-header) are part of the headword block but supply structured-field content selectively (see field rules below).

Cartouche garbage: PM prints royal/personal-name cartouches inline; the text layer renders these as `~~~`, `}}`, `c:7`, `0,`, `Q`, `Q Q`, `~`, `[~]`, etc. Drop the cartouche garbage from `occupant_name`. The titlecase English NAME token before the cartouche garbage is the canonical handle.

## Expected TT numbering in PM I.1 § I (TT21–TT30 range)

A pre-extraction headword scan of the chunk file confirms PM I.1 catalogues all ten numbers TT21 through TT30 in this section: **TT21, TT22, TT23, TT24, TT25, TT26, TT27, TT28, TT29, TT30**. **10 rows expected** — every number in the decade is present, no gaps in this range.

If your headword scan returns a number outside this range, RE-CHECK the chunk file — it may be (a) a scene-number marker like `(7)` or `(8)` (not a tomb row), (b) a plate-caption tomb-number reference like `TOMBS 17, 19-25, 165` or `TOMBS 26, 28-32, 35, 38` (printed-page captions for shared floor plans within this chunk's range), (c) a cross-reference from one tomb's headword to another (`also owner of tomb N`), (d) the TT31 / TT32 / TT33 headwords near the chunk tail (boundary markers, OUT of scope), or (e) a publisher running-header `Tombs N and N+1` or `Tomb N` page-header. None of those are tomb headwords for THIS chunk.

## PM-I.1 text-layer noise (chunk-11-relevant)

`postprocess.py` runs against this chunk file and normalises the patterns shared with chunks 1–10 (Ḥ-substitutes including `J.I` → `Ḥ`; `<` adjacent to letter → `ʿ`; whitelisted Egyptian-name `c` → `ʿ`; `Ist ed.` → `1st ed.`; king-name-anchored Roman-numeral fixes). The following residual patterns are NOT yet whitelisted in the postprocessor and are handled at prompt + `CHUNK11_CORRECTIONS` level. None of them have unique-bigram signatures stable enough across chunks to safely promote to postprocess (collision risk with non-tomb-headword content is too high — see chunk-10 transcribe.md noise inventory for the precedent).

- **Tomb-number-position digit/letter substitution.** Headword tomb-numbers can render as non-canonical glyph clusters; chunk-9/10 examples cover the substitution classes: `12•` (bullet for period), `zo.` (z for 2 / o for 0), `33·` (middle-dot), and `3 I.`-shaped clusters (intra-number space + `I` for `1`, visible in this chunk's boundary-marker tail). A new chunk-11 variant adds colon-for-period (`<NUMBER>:`). Disambiguate by column-zero position followed by an all-caps NAME token; collapse the noise to the canonical `<NUMBER>.` form for `tomb_id`.
- **Capital underdot-Ḥ residuals.** PM-I.1 prints capital underdot-Ḥ (`Ḥ`) inside all-caps name tokens; chunk 9 added `J.I` to the postprocess table. Other Ḥ-residuals appear with one-off contextual signatures: `<DIGIT>;I` clusters preceding name-tail (chunk-10 precedent), and `<LETTER>FJ.`-shaped clusters following a vowel inside a CAPS NAME token. Read as `Ḥ` per PM's printed page, then apply the `occupant_name` strip-Ḥ rule below.
- **Capital underdot-Ḍ.** `:[>` cluster for capital underdot-Ḍ (chunk-10 precedent). Underdot-Ḍ is **preserved** in `occupant_name` (the strip rule covers underdot-Ḥ ONLY).
- **Capital underdot-Ḳ.** `I>.` cluster for capital underdot-Ḳ (chunk-9 precedent). Underdot-Ḳ is preserved in `occupant_name`.
- **Token-final ayin `<NAME>(`.** The publisher renders trailing-ayin as `<LETTER>(` adjacent to a cartouche-glyph context (chunk-9 precedent). Preserve ayin in `occupant_name`.
- **Vowel-cluster substitution `ii → ū`.** Double-`i` (`ii`) inside a name token where PM prints a macron-ū. Restore PM's printed macron-vowels in `notes_from_pm` (verbatim-preserve field) and in `occupant_name` (matchable form preserves macrons per the chunk-10 TT17 `Nebamūn` precedent).
- **Mid-dot/bullet for trailing apostrophe** in sub-site declarations like `Dra' Abû el-Naga'.` rendered as `Dra· Abu el-Naga·.` / `Dra· Abu el-Naga•.`. The canonical sub-site form for `theban_area` is documented per-row below.

## Field-by-field extraction rules

### `tomb_id`

`TT<N>` where `<N>` is the Arabic tomb number from the heading line (10 expected values: TT21–TT30). Apply the tomb-number-position-noise rule above when the OCR has substituted digits/letters.

### `theban_area`

**Per-row extraction.** Unlike chunks 9 and 10 (single sub-site cluster), chunk 11 spans MULTIPLE Theban sub-sites. Each TT21–TT30 headword's sub-site line — the line immediately below the title clause — declares which sub-site that row belongs to. Read the chunk and assign per row.

Canonical sub-site forms (use these literal strings; preserve PM's diacritics and apostrophes per the canonicalisation already established in chunks 7–10):
- **`"Sh. ʿAbd el-Qurna"`** — Sheikh ʿAbd el-Qurna (with U+02BF MODIFIER LETTER LEFT HALF RING for the ayin in `ʿAbd`; `Sh.` abbreviated as PM prints, period preserved).
- **`"Draʿ Abû el-Nagaʿ"`** — Draʿ Abû el-Nagaʿ (U+02BF MODIFIER LETTER LEFT HALF RING for the ʿayin in BOTH `Draʿ` and terminal `Nagaʿ` positions; circumflex `û` preserved per PM's printed form — migrated 2026-05-23 per issue #288 from project-stripped `Dra' Abu el-Naga` shared with chunk-7 `DAN-` rows).
- **`"ʿAsâsîf"`** — ʿAsâsîf (leading ayin U+02BF; circumflex `â` and `î` preserved per PM's printed typography).
- **`"Khôkha"`** — Khôkha (circumflex ô preserved per PM's printed form — migrated 2026-05-23 per issue #291 from project-stripped `Khokha`).

If a row's headword sub-site line declares a sub-site NOT in this list, restore it to its canonical form per PM's printed text and report it in your final report as a new sub-site that may need adding to the canonical list.

### `occupant_name`

**PM-verbatim, conventional-English form, titlecase.** Extract the NAME token from the heading line after applying the README's diacritic policy and the noise rules above.

Per the project's `occupant_name` matchable-name policy:
- Strip underdot-Ḥ (`Ḥ` / `ḥ`) → plain `H` / `h`. Underdot-Ḥ is the ONLY scholarly diacritic stripped from `occupant_name`.
- Preserve ayin (`ʿ`) where PM prints it as a distinguishing radical (chunk-7 / chunk-8 / chunk-9 precedent).
- Preserve underdot-Ḳ (`Ḳ` / `ḳ`) (chunk-7 / chunk-9 precedent).
- Preserve underdot-Ḍ (`Ḍ` / `ḍ`) (chunk-10 precedent: TT11 `Ḍhout`).
- Preserve vowel macrons (`ū`, `ō`, `ē`, `ā`) where PM prints them in name tokens (chunk-7 `Wahʿankh` / chunk-10 TT17 `Nebamūn` precedent).
- Drop cartouche garbage (the text-layer noise after the name token).

Honorific prefixes that PM uses to introduce role (an all-caps `KING`, `PRINCE`, `QUEEN`, `VIZIER` before the name) — strip from `occupant_name`, capture in `occupant_role`. Most TT21–TT30 headwords do not lead with such a prefix; the role is given by the title clause AFTER the name (see `occupant_role` rules).

### `occupant_alt_names`

Alternate name forms PM gives for the SAME PERSON in the headword block. PM's `<NAME-A>, also called <NAME-B>` phrasing is the canonical pattern (e.g. chunk-7 DAN- prefixed alt-name surfaces). When PM prints this in a chunk-11 headword, capture the secondary name token in `occupant_alt_names`. Apply the same diacritic/noise rules as `occupant_name`. Empty list `[]` when absent.

`L. D. Text, No. N` / `CHAMPOLLION, No. N` / `WILKINSON MSS. v. N` cross-refs are NOT alt-names — those go in `notes_from_pm` per the cross-numbering parenthetical rule.

### `tomb_aliases`

Popular names of the tomb itself (19th-c. surveyor designations, classical aliases, local Arabic names). Empty list `[]` when absent.

### `co_occupants` and `is_joint_burial`

Both fields apply ONLY when PM's headword names more than one person buried in the tomb. Apply the structural rule mechanically per headword.

- `<NAME-A> … and son <NAME-B>` (or `…and daughter <NAME-B>`, etc.) — **hierarchical** (NAME-A is the parent, syntactic head). NAME-B goes in `co_occupants` with per-person role; `is_joint_burial = false`.
- `<NAME-A> … and <NAME-B>, <PLURAL-ROLE>` — **coordinate** (no syntactic primacy; PM lists them as a coordinate pair, the plural role applies to both). `is_joint_burial = true`. NAME-B goes in `co_occupants` with the same role as NAME-A.
- Single-occupant headword (no `and <NAME-B>`): `co_occupants: []`, `is_joint_burial: false`.

The role assigned to each `co_occupants[]` entry follows the same controlled-vocabulary mapping as `occupant_role` (see below). Per-person `alt_names: []` is the common case; populate only if PM gives a parenthesised alternative form for that specific person.

**Family clauses on the lines below the title** (`Father, …`, `Mother, …`, `Wife, …`, `Wives (of <X>), …`, `Parents, …`) name family members who are NOT buried in the tomb — they go in `notes_from_pm`, NOT in `co_occupants`.

**Usurpation pattern** (NEW for chunk 11). PM's `Partly usurped by <USURPER-NAME>, <USURPER-ROLE>` clause in a headword (e.g. `<NAME-A>, <ROLE>. Partly usurped by <NAME-B>, <USURPER-ROLE>. <Regnal>.`) describes a tomb where a later occupant re-used the original burial. The original occupant (NAME-A) is the headword name and stays in `occupant_name`. The usurper does NOT go in `co_occupants` — usurpation is structurally distinct from co-burial; PM's prose marker is the differentiator. The usurper's name + role is preserved verbatim in `notes_from_pm`. The Tier-3 deriver fires `is_usurped=true` automatically from the regex match on `usurp(?:ed|ation)` in `notes_from_pm` — emit the field default `false` at extraction time and let the deriver overwrite post-merge.

### `occupant_role`

Controlled vocabulary: `"King"`, `"Queen"`, `"Royal Family"`, `"Vizier"`, `"Official"`, `"High Priest"`, `"Princess"`, `"Prince"`, `"Unknown"`.

Assignment rules:
1. If `occupant_name` is null (cartouche-blank / uninscribed): role `"Unknown"`.
2. If the headword title clause names a controlled-vocab role explicitly (e.g. `Vizier`, `Princess`, `King`, `High Priest of <X>`, `First prophet of <X>` flattens to `"High Priest"` only when the deity is a major cult-deity like Amun/Amen-Re — for minor cults flatten to `"Official"`): use the controlled-vocab match.
3. Otherwise the controlled-vocab assignment for non-royal occupational titles (workman / scribe / chiseller / foreman / priest / official / steward / overseer / royal butler / royal scribe / fan-bearer / chief steward / brazier-bearer) flattens to **`"Official"`**.
4. **`Vizier` precedence.** When the title clause names BOTH a non-Vizier functional title AND `Vizier` (e.g. `<functional-title>, Vizier`), apply rule 2 with the Vizier match — `Vizier` is in the controlled vocab and PM's listing places it as the structurally-determining role. The verbatim full title clause (including the non-Vizier portion) goes in `notes_from_pm`.
5. **`King's son` + functional title.** PM's `<NAME>, King's son, <secondary-title>` describes a royal-blood individual whose primary functional role per PM is the secondary title. Apply rule 2 only when the secondary title is in the controlled vocab; otherwise fall through to rule 3 (`"Official"` flatten) and preserve `King's son` verbatim in `notes_from_pm`. The controlled-vocab role names structural placement, not noble blood.

The verbatim role-title clause that PM prints in the headword title-clause goes in `notes_from_pm` regardless of which controlled-vocab role applies — read it from the chunk and preserve as PM prints.

### `dynasty`, `sub_period`, `date_bce_approx_start`, `date_bce_approx_end`

**All `null`** for every row at this extraction stage. Phase A enrichment fills these from the king authority. Do NOT supply from outside knowledge or from PM's `Temp. <King>` / `Dyn. <Numeral>` / `Saite.` / `Ramesside.` clauses — those go in `notes_from_pm` verbatim.

### `location_sub_area`

`null` for every TT21–TT30 row. None of the chunk-11 headwords are expected to carry a sub-site flag like `Eastern Cemetery.` — `theban_area` already captures the sub-site. If a headword in this range declares a finer-grained sub-area inside its sub-site, populate `location_sub_area` and report it.

### `discovery_year`, `discoverer`

`null` for every row. `Excavated by <X>` / `Discovered by <X>` / `<Author>, <Title>, <Date>` clauses go in `notes_from_pm` only when they're part of the headword's structured prose.

### `is_unfinished`

`true` iff the literal word `Unfinished` (capital-U) appears in the headword block of a TT tomb. Otherwise `false`. Apply mechanically per headword.

### `shared_with_tombs`

List of tomb-id strings parsed from cross-tomb references in the headword block. PM I.1 phrasings to capture:
- `See also Tomb N` / `See also Tombs N and M` (chunk-9 precedent).
- `Also owner of tomb N` / `(Also owner of tomb N.)` / `(Perhaps also owner of tomb N.)` / `(also owner of tombs N and M)` (chunk-9 precedent).

**NEW for chunk 11 — cross-valley references.** PM may print a cross-tomb-ownership reference that names the OTHER VALLEY explicitly: `(Also owner of tomb N in the Valley of the Kings.)`. The `Valley of the Kings` qualifier indicates the cross-referenced number is a `KV<N>` not a `TT<N>`. Populate `shared_with_tombs` with the prefix-qualified string (`"KV<N>"`, NOT `"TT<N>"`). The field is `list[str]`; semantically, cross-valley ownership is the same structural relation as same-valley ownership and the prefix-tagged string is the matchable form. If PM does NOT name a valley qualifier, default to `TT<N>` (chunks 1–10 convention). Hedged variants (`Perhaps also owner of …`) DO populate `shared_with_tombs` regardless of the hedge.

Empty list `[]` when absent.

Numbered tomb cross-refs only — do not list `(belonging to (4))`, `(tomb 7)` mid-prose scene cross-refs, or footnote-misnumbering corrections like `[For WRESZ., Atlas, … called by him tomb N, … see tomb M]`. Those are scene-internal references / Wreszinski misnumberings, not headword cross-refs.

### `notes_from_pm`

A short verbatim prose fragment from the headword block that doesn't fit a structured field. **Verbatim-preserve against PM's printed text** — preserve PM's diacritics including `ḥ`, `ʿ`, `ḳ`, `ḍ`, `ē`, `ō`, `ū`, `â`, `î` where the printed page carries them (do NOT apply the strip-ḥ rule here; that rule is for `occupant_name` only). Capture each of the following clause types from the headword as PM prints them, joined by `". "`:

- **Verbatim role-title clause** (the title description that follows the name) — preserve PM's exact wording. For Vizier rows, include the full functional title clause as PM prints it (e.g. `"<functional-title>, Vizier."`).
- **Regnal / dynasty clauses** (`Dyn. <Numeral>.`, `<Period>.`, `Temp. <King>.`, `Temp. <King-A> to <King-B>.`, `Saite.`, `Ramesside.`). Preserve PM's wording verbatim.
- **Family clauses on the lines below the title** (`Father, <Name>`, `Mother, <Name>`, `Wife, <Name>`, `Wives, <Name> and <Name>`, `Wives (of <X>), <Name>; (of <Y>), <Name>`, `Parents, <Name>, <Title>, and <Name>`). These name family members who are NOT buried in the tomb. Use the convention `Wife, <Name>.` (singular) or `Wives, <Name> and <Name>.` (plural). When PM disambiguates whose-wife with a parenthetical (e.g. `Wife (of <X>), <Name>.`), preserve the parenthetical.
- **Object-cite parentheticals** (`(name from offering-table of <Person>, in <Museum> <Cat-No.>)`). Preserve where PM prints them — these are catalog cross-references the schema retains.
- **Cross-numbering parentheticals** (`(L. D. Text, No. <N>.)`, `(CHAMPOLLION, No. <N>.)`, `(HAY, No. <N>.)`). Preserve where PM prints them as headword cross-numbering.
- **Usurpation clauses** (NEW for chunk 11): `Partly usurped by <USURPER-NAME>, <USURPER-ROLE>` — preserve verbatim. The Tier-3 `is_usurped` deriver fires on the `usurp` regex match.
- **Tomb-state-marker parentheticals on the sub-site line** (NEW for chunk 11): a parenthesised state-marker following the sub-site declaration (shapes like `(Inaccessible.)`, `(Unexcavated.)`, `(Reburied.)`) — preserve verbatim. There is no `is_inaccessible` / `is_unexcavated` schema field; the prose stays in `notes_from_pm`.
- **Hedge tokens for PRIMARY attribution** (`(probably)`, `(?)`) when printed against the occupant's NAME or identification — preserve verbatim. These feed the Tier-3 `attribution_certainty` derivation (regex fires `"uncertain"` on `(?)`, `"probable"` on `(probably)` / `Probably`). **Note:** PM's `Temp. <King> (?)` qualifies the regnal date, NOT the occupant identification; per chunk-9 TT2 + chunk-10 TT12/TT17/TT19/TT20 precedent, those rows get `DERIVER_OVERRIDES` post-merge to pin `attribution_certainty="attested"`. Emit defaults at extraction time and let the post-merge override layer handle the regnal-vs-occupant distinction.

Drop entirely from `notes_from_pm`:
- `Plan, p. N`, `Map I, …`, `Map IV, …`, `Map V, …`, `Map VI, …` plan-marker references.
- The bibliographic-references paragraph (any long run of `<AUTHOR>, <Title>, …` citations between the headword block and the first body sub-header).
- **The cross-tomb-ownership parentheticals** `(Also owner of tomb N.)`, `(Perhaps also owner of tomb N.)`, `(Also owner of tomb N in the Valley of the Kings.)`, `(also owner of tombs N and M)` — these are structurally captured by `shared_with_tombs` (numbered cross-refs there). Do NOT also place them in `notes_from_pm`; the `Perhaps` hedge in the secondary-attribution clause would otherwise spuriously trigger the Tier-3 `attribution_certainty="uncertain"` deriver on a row whose PRIMARY attribution is fully attested.

`null` when the headword has nothing beyond the bare name + cartouche garbage + sub-site (rare for chunk-11 — PM I.1 headwords are dense and most rows carry substantial structured content).

### `source_citation`

Object with three fixed keys:

- `"edition"`: exactly `"PM I.1 2nd ed. 1960"`.
- `"section"`: exactly `"I"` (PM I.1's "I. NUMBERED TOMBS" master section — no sub-section letter for this range).
- `"page"`: the **printed** page number on which the tomb's headword line sits. Extract from the chunk file's `===== PHYSICAL PAGE N (PRINTED PAGE M) =====` markers. Use `M` (the printed number), NOT `N` (the physical number). Do NOT supply from memory.

### Tier-3 typed flags (`is_uninscribed`, `is_usurped`, `attribution_certainty`)

These three fields are **emit defaults at extraction time** — `false`, `false`, `"attested"`. The `fix_rows.py` `_apply_issue_182_migrations` deriver runs post-merge and overwrites them deterministically from regex matches against `notes_from_pm`. Do NOT pre-derive them in your output; emit the defaults so the deriver's run produces a clean idempotent log entry.

Background (FYI only): the deriver flips `is_uninscribed=true` on `\buninscribed\b`, `is_usurped=true` on `\busurp(?:ed|ation)\b`, and sets `attribution_certainty` to `"uncertain"` on `\b(uncertain|perhaps|possibly|tentatively)\b|\(\?\)`, `"probable"` on `\bprobably\b|\(probably\)|\battributed to\b`. Primary-attribution hedges that ARE captured in `notes_from_pm` per the rules above DO fire the regex; secondary-clause hedges (like the `Temp. <King> (?)` regnal-date hedge in chunk-10 TT12/TT17/TT19/TT20, or the chunk-9 TT2 secondary-wife `(probably)` hedge) need post-merge `DERIVER_OVERRIDES` entries to revert to `"attested"`.

## Structural gotchas to watch

- **Scene numbers vs tomb headwords.** Long body-prose blocks `(1) … (2) … (3) … (10) …` with parenthesised numbers are scene-item markers, NOT tomb headwords. Distinguish by line-start position: tomb headwords start at column zero with `<digit><separator> <NAME-IN-CAPS>`; scene markers are inset and start `(N)`.
- **Plate-caption headers.** `TOMBS 17, 19-25, 165` and `TOMBS 26, 28-32, 35, 38` (running plate captions for shared floor plans within this chunk's range) are NOT tomb headwords for the listed numbers.
- **Page-running-headers.** Lines like `Tombs 21 and 22`, `Tomb 23`, `Tombs 23 and 24`, `Tombs 27, 28, and 29`, `Tombs 30 and 31`, `Tombs 31 and 32` (publisher running-header at the top of each printed page) are running-headers, NOT tomb headwords.
- **Name collisions across decades.** Two distinct individuals can share a name across different TT-decades (chunk-10's TT17 already established this for one common-name slot — extending into chunk 11 may surface another). The schema row-key is `tomb_id`, not name; apply each row's own headword for role / regnal / sub-site fields without conflating.
- **Boundary marker — TT31 / TT32 / TT33.** The chunk file extends through physical p.68 to include the start of TT31's body, the TT32 headword, and TT33's headword so you can see all three boundaries clearly. **Do not extract any TT31 / TT32 / TT33 rows.** Stop at the end of TT30's headword block.
- **Page boundary internal to a tomb.** Some headwords span a printed-page break (the headword starts on page N and the body continues on page N+1). The headword's PRINTED page is the page where its first headword line sits — extract from the page marker that immediately precedes the headword line, not from a body-prose page.

## Pitfall summary (read LAST before running)

1. **10 rows expected** (every TT number in TT21..TT30 has a headword in PM I.1 § I — no gaps in this decade).
2. **PM I.1 offset is +18** (printed = physical − 18). Use the `===== PRINTED PAGE M =====` marker for `source_citation.page`.
3. **`section: "I"`**, **`edition: "PM I.1 2nd ed. 1960"`**.
4. **`theban_area` is per-row** (chunk 11 spans 3+ sub-sites). Use the canonical sub-site list above; U+02BF ʿayin in `Draʿ Abû el-Nagaʿ`, U+02BF ayin in `ʿAsâsîf` and `Sh. ʿAbd el-Qurna`, circumflex preserved in `ʿAsâsîf`. Read each headword's sub-site line and assign per row.
5. **`is_joint_burial`** / **`co_occupants`**: apply the hierarchical (`X and son Y`, `false`) vs coordinate (`X and Y, plural-role`, `true`) rule mechanically per headword. Single-occupant: `is_joint_burial=false`, `co_occupants=[]`. **Usurpers do NOT go in `co_occupants`** — usurpation prose stays in `notes_from_pm`; the deriver flips `is_usurped=true`.
6. **`shared_with_tombs`**: populate when a TT21–TT30 headword carries `Also owner of tomb N` / `Perhaps also owner of tomb N` / `See also Tomb N` / `(also owner of tombs N and M)` / `(Also owner of tomb N in the Valley of the Kings.)` phrasing. Use `KV<N>` for cross-valley references when PM names the valley qualifier; default to `TT<N>` otherwise.
7. **`occupant_role`** per the controlled-vocab rules; non-royal occupational titles flatten to `"Official"` UNLESS PM explicitly names a controlled-vocab role (`Vizier` is the in-range example). The verbatim role-title clause goes in `notes_from_pm` regardless.
8. **`dynasty` / `sub_period` / `date_bce_*` / `location_sub_area` / `discovery_year` / `discoverer`** all `null` for every row — Phase A enrichment fills these. PM's `Temp. <King>` / `Dyn.` / `Saite.` / `Ramesside.` clauses go verbatim into `notes_from_pm`, not into typed fields.
9. **PM-I.1 noise residuals**: chunk-9/10 classes (`12•` / `zo.` / `33·` for tomb-number variants; `J.I` / `<DIGIT>;I` for `Ḥ`-residuals; `:[>` for `Ḍ`; `I>.` for `Ḳ`; `<LETTER>(` for token-final ayin); plus chunk-11 additions (colon-for-period `<NUMBER>:` in tomb-number position; `<LETTER>FJ.`-shaped clusters following a vowel inside CAPS NAME for `Ḥ`-residual; double-`i` for macron-`ū` inside name tokens).
10. **Tier-3 typed flags** emit defaults (`false`/`false`/`"attested"`); the `fix_rows.py` deriver overwrites post-merge.
11. **Preserve underdot-Ḍ (`Ḍ` / `ḍ`) and underdot-Ḳ (`Ḳ` / `ḳ`)** in `occupant_name`; only underdot-Ḥ is stripped.
12. **Preserve vowel macrons** (`ū`, `ō`, `ē`, `ā`) and circumflexes (`â`, `î`) in `occupant_name` AND `notes_from_pm` per PM's printed page.

## Report back

After writing the JSONL, output a one-paragraph report with:
- Row count (should be 10) and the complete list of TT tomb_ids you emitted in sort order.
- Per-row `theban_area` assignments (since this is the first chunk with heterogeneous sub-sites).
- Any field you're uncertain about, with the field name and your best-guess value.
- Any unexpected text-layer noise that this prompt doesn't already flag.
- For any usurpation clauses, multi-occupant headwords, cross-valley `shared_with_tombs`, or non-Official controlled-vocab roles you found in the chunk, which classification you applied and the structural reason (which PM phrasing triggered it).

Stay under 250 words.
