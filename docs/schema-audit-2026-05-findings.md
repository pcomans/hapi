# Schema audit — findings (2026-05)

Aggregated cross-cut of 11 per-source audits run per the rubric in `schema-audit-2026-05.md`. Each per-source report lives in `/tmp/claude/schema-audit-<source>.md` (working notes; not committed).

## TL;DR

**Bad. Worse than expected.** PR #169's PM Theban audit (Shape A + Shape B) was not an isolated incident — it was a representative case. Of 10 other sources audited, **only Porter-Moss is now clean**. Every other source has at least one P1 finding. Three sources (HKW 2006, Ryholt 1997, Baud 1999) have 4+ P1s each. The same root causes repeat: scalar fields packing list-shaped data, compound strings instead of structured records, load-bearing facts hidden in prose `notes` fields, missing typed flags for known structural variants.

**Numbers (severity counts per source):**

| Source                | P0 | P1 | P2 | P3 | CLEAN shapes |
|-----------------------|----|----|----|----|--------------|
| porter-moss-theban    |  0 |  0 |  4 |  1 |  4 (A, B, J-`is_joint_burial`, H) |
| leprohon-2013         |  0 |  1 |  3 |  1 |  2 (I, J reference pattern) |
| shaw-ohae-2000        |  0 |  0–1 |  6 |  1 |  4 (A, G, H, I) |
| kitchen-tipe          |  0 |  3 |  4 |  1 |  1 (G partial) |
| pharaoh-se            |  0 |  3 |  4 |  2 |  2 (G primary, H) |
| beckerath-1997        |  0 |  2 |  3 |  2 |  0 |
| dodson-hilton-queens  |  0 |  4 |  4 |  2 |  0 |
| baud-1999             |  0 |  4 |  5 |  0 |  1 (A) |
| ryholt-1997-sip       |  0 |  6 |  3 |  0 |  1 (C) |
| hkw-chronology-2006   |  0 |  6 |  2 |  0 |  1 (H) |
| idai-gazetteer        |  1 |  1 |  5 |  0 |  4 (A, B, C, H) |
| **TOTAL**             |  **1** | **30** | **43** | **10** | |

The single P0 (iDAI gazetteer Shape G — 10 duplicate `display` values + 566/1000 rows have dangling `parent_id` references) is the only hard blocker right now. The 30 P1s are merge-blockers when their respective Phase-A consumer code lands; today they're latent.

## By failure mode (cross-cut across sources)

### Shape A — conflated semantics (one field carries multiple distinct concepts)

The most pervasive failure mode. **8 of 11 sources hit.**

- **PR #169 reference case:** PM `occupant_alt_names` carried both same-person variants AND tomb-nicknames. Fixed by splitting into `occupant_alt_names` (narrowed) + new `tomb_aliases`.
- **Beckerath (P1):** `egyptian_titulary` packs slash-separated alternative throne-names (`"A-qen-en-rê/A-user-rê"`) into a scalar; `name` carries embedded paren birth-names inconsistently across 12 rows. 21.01 Smendes literally duplicates `Nes-bi-neb-dedet` in BOTH `name` parens AND `egyptian_titulary`.
- **Dodson-Hilton (P1):** `alt_names` mixes true variants (`Mut-Tuy`) with regnal-name-on-accession (`["Ramesses I"]` on `Paramessu` × 10 rows) AND a speculative cross-row identity (`Sitre A.alt_names = ["Tia Q"]` — fix_rows already enforces this rule for `Thutmose B` but not here).
- **HKW 2006 (P1):** `alternative_reading` field-choice driven by PDF layout, not semantics — Khufu/Menkaure get `greek_form`, Khephren gets the same Greek form in `alternative_reading`.
- **Pharaoh.se (P1):** `alt_labels` merges 4 distinct sources (index alts, a.k.a. line, synthesised compact-prenomen, Greek/Manetho transcriptions) into one untyped list.
- **Ryholt 1997 (P1):** `dynasty: null` conflates Abydos Dynasty rows (8 rows, real dynasty) with truly unattributed kings (23 rows, prefix `N.*`/`P.*`/`H.*`/`D.*`/`G.*`).
- **Leprohon (P2):** README self-flags — `Cartouche:` / `Throne and birth:` source labels project onto canonical fields with the original Leprohon label recoverable only via prose-regex.
- **Kitchen TIPE (P2):** `notes_from_kitchen` carries one editorial-gloss annotation mixed with verbatim Kitchen prose; field name lies about provenance.

### Shape B — compound strings where structured data is the truth

**8 of 11 sources hit.** PM's `"Yuia and Thuiu"` joint-burial pattern repeats almost verbatim elsewhere.

- **Baud 1999 (P1):** `baud-209` is a Yuia-and-Thuiu-style joint entry: `name_egyptian: "Snj* et Zzj*"`, notes literally say `"Joint entry for Snj and his wife Zzj"`. 10 more rows pack collective/lost-name/disambiguation semantics into `name_egyptian`. 14 rows have compound `pm_ref` with `;` or `et` separators.
- **HKW 2006 (P1):** 5 multi-ruler `display` strings (e.g. `"Sobekhotep VIII, Nebiriau, Rahotep, Sobekemzaf I & II, Bebiankh"`); 7 slash-name-variant displays where `"Amenhotep IV/Akhenaten"` is one person but `"Smenkhkare'/Nefernefruaten"` is two distinct figures with NO way to disambiguate.
- **Beckerath (P1):** 18 `mixed`-kind rows pack `<nomen>, <prenomen>` pairs into one string. The `mixed` enum collapses 3+ distinct compound shapes (03.02 Djoser is `"Tosorthros, Hor Netri-chet"` = nomen + horus_name, not nomen + prenomen).
- **Pharaoh.se (P2):** `chronologies` value shapes mix ranges, durations (`"57 years"`), single years, period-durations like `"2y 1m 1d"` with no discriminator.
- **Ryholt 1997 (P2):** `nomen` packs Roman-numeral disambiguators `(III)`, uncertainty markers `(?)`, lacuna `[...]`.
- **Kitchen TIPE (P2):** `name` cells pack disambiguators / hedges / Greek-only markers (`Pimay (the later king??)`, `(Har-)Psusennes II`).
- **Dodson-Hilton (P2):** Compound `dh_id` slash/paren conventions.
- **Shaw OHAE (P3):** `chapter_title` packs period+qualifier+dates into one verbatim banner string (but components are also typed; recommend parser-consistency test only).

### Shape C — load-bearing facts hidden in prose fields

**8 of 11 sources hit.** A `notes_from_<author>` / `source_note` carrying structured facts that should be in their own typed fields.

- **Beckerath (P2):** `notes_from_beckerath` carries 3 distinct fact-classes — geographic seat (`in Theben`/`in Sais`/`in Persien`) on 16 rows; precise NK accession dates (`Antritt 31.5.1279`) on 23 rows (the *defining feature* of Beckerath vs HKW); regnal-count placeholders.
- **Porter-Moss (P2 — post-PR-#169 finding):** `notes_from_pm` carries 6+ distinct structured fact-types: filiation/kinship across ~14 rows, occupational title across ~6 rows, regnal-period `Temp. <king>` across 6 rows, re-use, usurpation, hedged-attribution markers. Existing typed `discoverer` / `discovery_year` fields exist (0/75 populated) — agents put "Excavated by" prose into notes instead.
- **HKW 2006 (P1):** `note` carries 5 categories: coregencies, rival-claimant flags, alt-reading-type qualifiers, per-bound `ca.` qualifiers, transcription-correction provenance.
- **Kitchen TIPE (P2):** Co-regency years, alternative reign-lengths, Chief-of-Mā role, HPA `hp`/`'kg'` shorthand, Tantamani's "in S. Egypt" geographic scope all hidden in `notes_from_kitchen`.
- **Leprohon (P1):** `notes` field is broken in two ways simultaneously — key present on only 6/395 rows AND value is always null on those 6 because agent-b emitted real prose that majority-voted to None. The prose still exists in `raw/agent-b-late-period.jsonl` but is gone from `reconciled.jsonl`. `fix_rows.py:830` explicitly defers a top-level `notes` field.
- **Shaw OHAE (P2):** `source_note` on chapters 4/9/10 carries Phase-A canonical-mapping facts in English prose.
- **Dodson-Hilton (P2):** Tomb numbers in `notes`.
- **Pharaoh.se (P2):** `sources` lists pack bibliographic citations and primary-source attestations together.

### Shape D — silent defaults for "unknown" vs "verified empty"

**7 of 11 sources hit.** Empty `[]` / null collapses two distinct semantic states.

- **Kitchen TIPE (P1):** `prenomen: null` overloads "Kitchen-printed-unknown" (`[Prenomen unknown]` on 2 rows) with "not-in-Kitchen's-table-layout" (30 other null rows). Bracketed sentinel used inconsistently — only 2/32 times.
- **Ryholt 1997 (P1):** 18 rows have one of `date_bce_start`/`date_bce_end` populated and the other null per Ryholt's own single-cell entries — but `null` also means "no date at all" (89 rows).
- **Baud 1999 (P1):** `[]`/`{}`/`null` cannot distinguish "Baud explicitly attests nothing" from "extraction lossy" on 5 fields (228+211+73+47+19 empty rows).
- **Leprohon (P1):** Tied to Shape C — `notes` key present on only 6/395 rows.
- **HKW 2006 (P2):** `null` in `start_year`/`end_year`/`dynasty`/`prenomen` collapses 3-4 distinct semantic states each.
- **Beckerath (P3):** 6 rows with all-null BCE endpoints have no typed reason flag.
- **iDAI (P2):** Nulls collapse "absent in iDAI" with "we didn't look".
- **Shaw OHAE (P2):** `sub_periods: []` conflates "Shaw said none" with "transcriber skipped" (README §"Known gaps" admits the latter for ch 2 Palaeolithic and Naqada III).

### Shape E — implicit conventions ("when X looks like Y, treat as Z")

**8 of 11 sources hit.** Rules that exist only in README prose / Python code, not as typed flags.

- **HKW 2006 (P1):** 7 unwritten conventions a consumer must memorize.
- **Ryholt 1997 (P1):** `polity` and `concurrent_with` are deterministic functions of `dynasty` per README, yet stored redundantly on every row → Rule-4 single-source-of-truth violation. Plus `if ryholt_id.startswith("Abyd.")` convention used in tests.
- **Beckerath (P2):** Conventions instead of types: `Kgin.<name>` queen-honorific, `Gegenkönig`-in-notes, `Mitregentin von <king>`-in-notes.
- **Pharaoh.se (P1):** `_is_roman_dynasty()` checks `"Roman" in dynasty_label` to decide if bare years are CE; no `era` field. Augustus crosses the BCE/CE boundary with no flag.
- **Kitchen TIPE (P1):** Multiple structural conventions (Dyn-21-only concurrency, `start_bce > end_bce` permitted only on 21H.06, single-point dates, Harsiese-A polity exception) live only in README prose / hardcoded Python.
- **Shaw OHAE (P2):** Sign convention, `period_name` derivation rule, `date_qualifier` policy live in README only.
- **iDAI (P2):** `[lon, lat]` ordering (existing test only bounds-checks, can't catch a swap), and `parent_id` may dangle.
- **Dodson-Hilton (P2):** `Q`-suffix-not-implying-unplaced, lacuna prefixes encoding attestation.
- **Porter-Moss (P2 — new finding):** `occupant_alt_names` doubles as the prenomen-disambiguator for ambiguous join keys (5 `DAN-Antef*` rows); `shared_with_tombs` conflates 3+ distinct relations.

### Shape F — controlled vocabulary not enforced

**8 of 11 sources hit.** Documented allowlists with no test asserting every value is in the allowlist.

- **iDAI (P1):** `types` documented as filtered to 3 values; corpus actually has 9 distinct values (multi-typed rows + supplementary bypasses leak `populated-place`, `building-institution`, `island`, `administrative-unit`, `hydrography`, `landcover`).
- **Dodson-Hilton (P1):** `roles` controlled vocab not enforced. 74 distinct tokens, no allowlist, no test. **Currently shipping a typo: `OPULE` (1×) where `MULE` was intended (8×).** Test `test_role_code_set_spans_the_known_codes` runs the *opposite* direction.
- **Pharaoh.se (P2):** `chronologies` keys not allowlisted — 17 free-text scholar keys, including ambiguous bare `"Manetho"` (25 rows) alongside qualified `"Manetho (Africanus/Eusebius/Jerome/Josephus)"`.
- **Beckerath (P3):** `period` and `egyptian_titulary_kind` enums tested; `sub_line` enum NOT.
- **Kitchen TIPE (P2):** `polity` allowlist documented but not asserted.
- **Baud 1999 (P2):** `sub_period` and `baud_refs` keys have no controlled-vocab test.
- **HKW 2006 (P2):** Only `kind` has enforced controlled vocab; `parent_period`, `dynasty.label`, `uncertainty_plus_years` have no shape tests.
- **Shaw OHAE (P2):** `date_qualifier ∈ {"c.", None}` controlled vocab not enforced.

### Shape G — ambiguous join keys

**6 of 11 sources hit.** Two distinct authority records share the same value the consumer would join on.

- **iDAI (P0):** 10 duplicate `display` values (e.g. `Qasr el-Banât` × 3 in geographically distinct locations); 566/1000 rows have `parent_id` pointing OUTSIDE the file (parents are typically `administrative-unit` ancestors filtered out). 56% broken FK if anyone treats it as internal.
- **HKW 2006 (P1):** `display: "Ini"` appears 2× (L44 dyn-5 + L91 dyn-13); `display: "Ta'o"` appears 2× **in the same dynasty 17** (L102/L103); `number: 23` appears 2× (UE + LE) with no per-ruler typed branch field.
- **Ryholt 1997 (P1):** `nomen` is non-unique cross-source (homonyms + 23 N/P/H/D/G attestation rows that will collide with Old Kingdom homonyms on pharaoh.se join).
- **Porter-Moss (P2 — new finding):** `occupant_name` ambiguity: KV5+KV7 both `Ramesses II`; KV3+KV11 both `Ramesses III`; 5 `Antef` rows; SWV-HatshepsutSouth+KV20 both `Hatshepsut`.
- **Baud 1999 (P2):** `name_egyptian` + `pm_ref` cross-row collisions.
- **Leprohon (P3):** 3 stub `display_name` duplicates `"Name Lost"` etc., disambiguated by unique `leprohon_id`.

### Shape H — compound IDs / opaque keys

**3 of 11 sources hit.**

- **Ryholt 1997 (P1):** `ryholt_id` packs four facts (dynasty / attestation-class / sequence / suffix); the prefix `Abyd|N|P|H|D|G` is NOT redundantly stored as a typed field.
- **Leprohon (P2):** `dynasty_label` carries facts not in `dynasty_number` — `Dynasty 8a` → 8 (sub-dynasty letter `a` lost), `Dynasties 9–10a` → 9 (10 endpoint lost entirely).
- **Kitchen TIPE (P3):** `kitchen_id` substream letter (`H`/`E`/`P`) is load-bearing structured data, not a separate field.
- **CLEAN:** Beckerath, iDAI, pharaoh.se primary, Porter-Moss.

### Shape I — fields that should be a list but are a scalar (or vice versa)

**6 of 11 sources hit.** Cardinality dishonesty.

- **HKW 2006 (P1):** Zero `list` fields anywhere despite multi-ruler/multi-name data.
- **Pharaoh.se (P1):** Scalar `prenomen`/`nomen` over list cards — 118 rows have multiple birth-name cards; `prenomen = throne_names[0].name` arbitrarily picks the first card without preferring `is_variant=False`. This is the field Phase-A will use as a primary join key.
- **Beckerath (P1/P2):** `egyptian_titulary` is a scalar that should be a list (consequence of Shapes A+B); `prenomen` similarly for 19.07 (`"anfangs … später …"` packs two temporal throne-names).
- **Baud 1999 (P1):** `father_name`/`mother_name` are scalars but Baud routinely reports competing parental hypotheses; the `(probable)`/`(per Baud)`/`(?)` hedge ladder is a pseudo-cardinality marker existing *because* the field is a scalar.
- **Ryholt 1997 (P2):** `nomen_transliterated: str` should be `list[str]` (3 rows pack canonical + variant via comma-concat).
- **iDAI (P2):** `alt_labels: None` for empty, but `cross_refs.other: []` for empty. Pick one sentinel.
- **Dodson-Hilton (P3):** `father_name` scalar-only cardinality.

### Shape J — missing typed flags for known structural variants

**10 of 11 sources hit.** The most universally-applicable failure mode.

- **PR #169 reference case:** PM `is_joint_burial: bool` was added to disambiguate KV46 (asymmetric) from SWV-ThreePrincesses (coordinate). Pattern works.
- **Leprohon (CLEAN, reference pattern):** `printed_under: str | None` correctly resolves the same-king-stage vs queen-consort sub-entry overload (added 2026-04-24). **Cite this as the canonical fix pattern alongside PR #169.**
- **Beckerath (P2):** Missing `is_dynasty_marker`, `is_queen_coregent`, `is_anti_king`, `existence_uncertain`, `accession_date_*`, `coregent_of`.
- **Dodson-Hilton (P1):** Cross-section-duplicate vs letter-reuse phenomena (both producing non-unique `dh_id`s) documented in README prose only; no typed per-row flag. Group entries (`[...]18A–H` covers up to 8 daughters) have no `is_group_entry: bool`.
- **Kitchen TIPE (P1):** Piankhy's two-prenomen sequence packed into one comma-string; co-regent-only / existence-doubtful / same-person-as / source-typo / single-point-date are all known structural variants with no typed flags.
- **Ryholt 1997 (P1):** Missing `is_unattributed`, `is_abydos_dynasty`, `is_uncertain_attribution`, `is_lacunose`, `is_syllabic`, `homonym_index`, `date_attestation`.
- **HKW 2006 (P1):** 7 missing typed flags.
- **Pharaoh.se (P2):** Missing typed flags for Roman / Predynastic / Unplaced / Argead+Ptolemaic structural variants.
- **Baud 1999 (P1):** Missing `is_joint_entry`, `entry_kind` enum, `name_status` enum (direct PR #169 analogue).
- **Shaw OHAE (P2 / P1-conditional):** Missing `is_composite`, BCE/CE-crossing, `date_precision`. The geological `-700000` BCE date for Palaeolithic silently corrupts arithmetic if Phase-A treats it like ruler-era dates.
- **iDAI (P2):** No `is_supplementary` flag.
- **Porter-Moss (P2 — new finding):** Missing `is_reused`/`reused_by_*` (KV45), `is_usurped`/`usurper` (KV9, KV14), `attribution_certainty` enum, `is_uninscribed` flag.

## Cross-source disagreements (Phase-A integration risks)

- **Pharaoh.se vs Leprohon (king-titulary asymmetry).** Pharaoh.se's `alt_labels` is a mixed signal bag (Shape A); Leprohon's `alt_display_names` is true alternates only (clean). Pharaoh.se has scalar `prenomen`/`nomen` (Shape I); Leprohon has pure-list shape (clean). No shared join key between them. Phase-A will need an explicit normalisation reader.
- **Ryholt 1997 vs pharaoh.se (homonym collisions).** Ryholt's 23 N/P/H/D/G attestation rows have non-unique `nomen` values that will collide with Old Kingdom homonyms on a pharaoh.se join (Shape G).
- **Beckerath, HKW, Shaw, Kitchen, Pharaoh.se all carry BCE dates** with subtly different conventions (sign, qualifier vocab, single-point semantics, Roman-era era handling). No cross-source date-shape audit exists.

## Recommended priority order

This is a sanity-check audit, not a fix-it directive. Recommendation for sequencing the fix PRs:

### Tier 1 — fix BEFORE Phase-A enrichment lands

These will silently produce wrong joins / dropped data when Phase-A consumers read them.

1. **iDAI gazetteer Shape G + F (P0/P1).** Duplicate `display` values + 56% dangling `parent_id` references + `types` vocab leak. Block before any sites-join code is written.
2. **Pharaoh.se Shape I (P1).** Scalar `prenomen`/`nomen` over list cards on 118 rows. This IS the primary join key for Phase-A king enrichment. Fix first or every join silently picks the wrong card.
3. **Leprohon Shape C+D (P1).** `notes` field broken — agent-b prose silently dropped by majority-vote. Re-extract or hand-restore from `raw/agent-b-late-period.jsonl`.
4. **Dodson-Hilton Shape F (P1).** `OPULE` typo currently shipping; controlled-vocab test would have caught it.

### Tier 2 — schema-revision PRs per source (PR #169 pattern)

Apply the `SCHEMA_FIELD_DEFAULTS` + `AUDIT_FIX_CORRECTIONS` + new structural tests pattern to each source. Recommended order by P1 count:

5. **HKW 2006** (6 P1) — biggest cleanup; `display` field overhaul + 7 typed flags.
6. **Ryholt 1997** (6 P1) — flat-schema → typed-flags conversion; redundant `polity`/`concurrent_with` removal.
7. **Baud 1999** (4 P1) — `is_joint_entry` + `entry_kind` + `name_status` enums (direct PM port).
8. **Beckerath 1997** (2 P1) — replace scalar `egyptian_titulary` + `egyptian_titulary_kind` with `egyptian_titularies: list[{name, kind, when}]`.
9. **Kitchen TIPE** (3 P1) — `[Prenomen unknown]` sentinel rationalization + typed flags + parallel `editorial_notes` field.
10. **Pharaoh.se** (remaining 2 P1 after Tier 1) — `era` field + Roman-CE typed handling.
11. **Shaw OHAE** (1 P1-conditional + 6 P2) — `date_precision` for the geological row + missing typed flags.

### Tier 3 — Porter-Moss round 2 (P2 cleanup)

12. **Porter-Moss** — extract `notes_from_pm` structured facts (filiation, occupational title, `Temp. <king>`, re-use, usurpation) into typed fields; add `is_reused`, `is_usurped`, `is_uninscribed`, `attribution_certainty`. Bundles cleanly with chunk 9 since chunk 9 will introduce more rows that need the same fields.

### Tier 4 — Cross-source

13. BCE-date convention audit across Beckerath / HKW / Shaw / Kitchen / Pharaoh.se. Out of scope for the per-source pattern; needs its own design pass.

## What this means for chunk 9 (PR C)

Chunk 9 (PM I.1 TT1–TT10) extends the Porter-Moss schema. The audit confirms PM is currently the cleanest schema in the corpus (post-PR-#169). PR C can proceed without waiting for the other-source fixes — **but** the Tier 3 Porter-Moss cleanup (typed flags for `is_reused` / `is_usurped` / `is_uninscribed` / structured `notes_from_pm` extraction) would best land BEFORE chunk 9 if the Tier 3 work is in scope, because chunk 9's TT private tombs will hit some of those patterns (uninscribed tombs, joint occupants TT6/TT10).

Recommendation: ship chunk 9 first (the pattern is established and the typed flags can land in a follow-up PR), unless you'd rather bundle.
