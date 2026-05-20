# Extraction prompt — Porter & Moss Vol III.2, Chunk 32

> **Thirty-second chunk drawn from PM Vol III** — Ṣaqqâra § II.J `TOMBS OF POSITION UNKNOWN` (b) MIDDLE KINGDOM + (c) NEW KINGDOM + (d) LATE AND PTOLEMAIC PERIODS. PM III.2 physical pp.340–359 / printed pp.700–719. Closes § II.J's post-OK coverage (chunk 30 already landed § II.J(a) Old Kingdom). Per the 2026-05-19 all-dynastic scope expansion (mvp-tasks.md item 3; PR #254), all sub-banners (b/c/d) are in scope. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-32-p340-p359-position-unknown-mk-nk-lp.txt`.

**Source:** PM III.2 2nd ed. 1978/1981, ed. Málek. **Page offset:** printed = physical + 360.

**Output:** one JSONL line per row sorted by `tomb_id`, `json.dumps(..., sort_keys=True, ensure_ascii=False)`. Write to ONE of `raw/agent-{a,b,c}-chunk32.jsonl`.

## Scope: what TO extract

§ II.J sub-banners in this chunk:

| Sub-banner | Treatment |
|---|---|
| `(b) MIDDLE KINGDOM` | IN SCOPE — extract every all-caps headword that opens a tomb section |
| `(c) NEW KINGDOM` | IN SCOPE — extract every all-caps headword that opens a tomb section |
| `(d) LATE AND PTOLEMAIC PERIODS` | IN SCOPE — extract every all-caps headword that opens a tomb section |

Stop at the `K. OBJECTS FROM TOMBS` banner — that's PM's loose-objects-without-known-tomb section (FINDS-style, OUT OF SCOPE).

FINDS sub-banners within (b)/(c)/(d) sub-sections, if any (look for headers like `<period> FINDS` or unmarked lists of partaged blocks with named individuals in italic / lowercase typography), are OUT OF SCOPE.

## How to identify a row

A row is opened by an **all-caps headword line** of one of these shapes:

- **Shape 1a — bare named NK/LP/MK tomb.** `<NAME IN CAPS> <hieroglyphs>, <role cluster>. <dating>.` — no prefix.
- **Shape 1c — `good name` (rn-nfr) compound headword.** `<NAME1 IN CAPS> <hieroglyphs> <NAME2 IN CAPS>, <role cluster>. <dating>.` — TWO all-caps names in the headword, both naming the same individual. The first is the formal name, the second is the "good name" (idiom: PM may prefix the second with `good name` text but often does not; the second hieroglyphic gloss confirms the same individual). The primary form is the FIRST all-caps name. The second goes in `occupant_alt_names`. Precedent: chunks 8/19/20/24/26 SAQ-Pepyzedi `(or Meryrēʿ-zedi or Zadi)`, chunks 27a/b Mariette good-name idiom.
- **Shape 1d — name variant `(or <ALT>)` or `(also <ALT>)` headword.** `<NAME IN CAPS> (or <ALT NAME IN CAPS>) <hieroglyphs> <hieroglyphs>, <role cluster>. <dating>.` or with `(also ...)` — PM marks alternative attestations of the SAME person OR a name variant. The primary form is the one before `(or ...)` or `(also ...)`. The alt goes in `occupant_alt_names`. PM may attach MULTIPLE alts (Shape-1d-multi): `<NAME> (also <ALT1> and <ALT2>)`.
- **Shape 1e — name-change `(altered to <ALT>)` headword.** Atenist alteration pattern (chunk-31 SAQH9 Merytyneit precedent). Primary = pre-alteration; alt = post-alteration.
- **Shape 4 — joint multi-burial tomb headword.** `<NAME1> AND <NAME2>` / `<NAME1>, <NAME2>, AND <NAME3>` / `TOMB OF THE <names>` followed by per-occupant details. Same convention as chunk-31 SAQ-TombPsammetheks: emit ONE row with `is_joint_burial: true`, the first-listed occupant as `occupant_name`, the rest in `co_occupants` / `co_occupant_roles`.
- **Shape 4b — family tomb headword.** `FAMILY TOMB.` followed by per-occupant details (parents, children listed with their own titles and dating). Single row with `is_joint_burial: true`, primary occupant = the first-listed named individual, all others in co_occupants.

## tomb_id convention

All chunk-32 rows use the descriptor form (no LS/Mariette numbers expected in § II.J position-unknown sub-banners): `SAQ-<TitleCaseAsciiName>`.

Examples (rule-based, NOT a per-row answer):
- For a bare-named MK/NK/LP tomb like `<NAME> ...`, the tomb_id is `SAQ-<TitleCaseAsciiName>`. Strip Egyptological diacritics from the descriptor (ASCII-only — chunks 22/25/26/28/29/30 source-wide convention).
- For a Shape-4 joint multi-burial, anchor on the first-listed principal occupant: `SAQ-<FirstPrincipalTitleCase>` or, when the first principal's name is too long or generic, `SAQ-TombOf<FirstName>` (chunk-31 SAQ-TombPsammetheks precedent).
- For a Shape-4b FAMILY TOMB: anchor on the primary occupant's name (e.g. `SAQ-FamilyTombOf<FirstName>` if multi-generational, or `SAQ-<FirstName>` if a clear single principal).

## Homonym disambiguators

Tomb-ids must be unique across the source. The reconciled source (current ≈779 rows after chunk 31) carries descriptor-form tomb_ids like `SAQ-Sankhenptah`, `SAQ-TombPsammetheks`, etc. If your descriptor collides with an existing tomb_id, append a topographic-anchor / title-anchor / period-anchor suffix (e.g. `SAQ-<Name>Dyn<N>` for a dynasty anchor or `SAQ-<Name><TitleSlug>` for a title anchor). Chunk-30 used `SAQ-NikaureJudge` / `SAQ-NikaureOverseerOfWorks` for two homonymous Nikaurēʿ rows on adjacent pages — that's the title-anchor pattern.

## Schema (23 keys, identical to chunks 20–31)

```json
{
  "tomb_id": "...",
  "memphite_area": "Saqqara",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "King" | "Queen" | "Royal Family" | "Vizier" | "High Priest" | "Princess" | "Prince" | "Official" | "Unknown",
  "dynasty": "11" | "12" | "13" | "18" | "19" | "20" | "26" | "27" | "28" | "29" | "30" | "32" | "33" | null,
  "sub_period": null | "Amarna" | "1st Int. Period",
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "Tombs of position unknown",
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "is_uninscribed": false,
  "is_usurped": false,
  "attribution_certainty": "attested" | "probable" | "uncertain",
  "shared_with_tombs": [],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM III.2 2nd ed. 1978/1981", "section": "II"}
}
```

### Cemetery field

**Every row** in chunk 32 uses `cemetery: "Tombs of position unknown"` — same banner as chunk-30 (§ II.J).

### Dynasty mapping (rule-based, by pharaoh-dynasty class)

| PM dating phrase | dynasty value | sub_period |
|---|---|---|
| `Early Middle Kingdom` / `Middle Kingdom` (no king) | `"12"` (best-guess Dyn 12; if PM specifies Dyn 11 or 13, use that) | null |
| `Temp. <King>` where `<King>` is a Dyn. XI/XII/XIII king | match the king's dynasty | null |
| `Temp. <King>` where `<King>` is a Dyn. XVIII pharaoh (NOT Amenophis IV/Akhenaten/Smenkhkareʿ) | `"18"` | null |
| `Temp. Amenophis IV` / `Temp. Akhenaten` | `"18"` | `"Amarna"` |
| `Temp. <King>` where `<King>` is a Dyn. XIX pharaoh (Ramesses I/II, Sethos I/II, Merenptah, Amenmesse, Siptah, Tawosret) | `"19"` | null |
| `Temp. <King>` where `<King>` is a Dyn. XX pharaoh (Ramesses III–XI, Setnakht) | `"20"` | null |
| `Ramesside` (no specific king named) | `"19"` (Dyn 19/20 ambiguous; default to 19 per source-wide range-tail convention; per chunk-31 dynasty table) | null |
| `Temp. <King>` where `<King>` is a Dyn. XXVI pharaoh (Psammetikhos / Psammetichus I/II/III, Necho I/II, Apries, Amasis) | `"26"` | null |
| `Temp. <King>` where `<King>` is a Dyn. XXVII pharaoh (Persian) | `"27"` | null |
| `Temp. <King>` where `<King>` is a Dyn. XXVIII pharaoh (Amyrtaeus) | `"28"` | null |
| `Temp. <King>` where `<King>` is a Dyn. XXIX pharaoh (Nepherites, Hakor/Achoris, Psammuthis) | `"29"` | null |
| `Temp. <King>` where `<King>` is a Dyn. XXX pharaoh (Nectanebo I/II, Teos) | `"30"` | null |
| `Ptolemaic` / `Temp. Ptolemy <N>` | use `"32"` for Macedonian-era / `"33"` for Ptolemaic (per Leprohon-local convention used by chunks 18-19); if uncertain, use `"33"` | null |
| `Dyn. <Roman>` explicit | Arabic numeral string | null |
| `Probably temp. <King>` | apply the matching class rule above; ADDITIONALLY set `attribution_certainty: "probable"` | — |
| Range `Dyn. X or Dyn. Y` (or `early/late Dyn. X or Dyn. Y`) | take the **later** dynasty (per chunk-23/30 range-tail convention) | — |
| Range `Dyn. XXVIII-XXX` or `Dyn. XXVIII-XXX or early Ptolemaic` | take the latest period the range covers: `"30"` (or `"33"` if Ptolemaic is included) | — |
| No dating stated | `null` | — |

Use a dynasty list / king-authority knowledge to classify any `Temp. <King>` you don't immediately recognize. If PM gives a king you cannot confidently place in a dynasty, emit `dynasty: null` rather than guessing.

### Occupant_role mapping (rule-based)

| PM headword title cluster contains | occupant_role |
|---|---|
| `Vizier`, `Governor of the town, Vizier` | `"Vizier"` |
| `King's son` + senior title (Greatest of the directors of craftsmen, etc.) | `"Prince"` |
| `King's daughter` + `King's wife` + no senior title | `"Royal Family"` |
| `Hereditary prince, Count` (MK/early-MK signature) | `"Official"` (despite "prince" — `Hereditary prince` is a hereditary nobility title, NOT a king's son) |
| `High Priest of Memphis` / `High priest` | `"High Priest"` |
| Else, when an official title is present (`Overseer of ...`, `Steward of ...`, `General`, `Royal scribe`, `Treasury`, `Fan-bearer`, `Judge`, `First chief`, `Custodian`, `Greatest of the directors of craftsmen`, `Head of`, `Prophet of`, etc.) | `"Official"` |

`Vizier` takes precedence when an individual carries both Vizier and other titles.

### `occupant_name` policy (PM-faithful, diacritic-stripped for Phase-A matching)

Per source-wide README:
- `occupant_name` strips Egyptological diacritics (underdot, macron, breve below).
- `occupant_name` KEEPS the ayin `ʿ` (U+02BF MODIFIER LETTER HALF RING).
- `notes_from_pm` and `co_occupants` and `co_occupant_roles` and `occupant_alt_names` ALL preserve PM-faithful diacritics verbatim (chunks 14/15/22/26/30 precedent).

Per-character mapping in occupant_name (apply uniformly):
- Underdot-Ḥ → plain `h` (preserved in notes/co_occupants/alt_names).
- Macron-Ē (Re-compounds) → plain `e` (preserved elsewhere).
- Macron-Ū (Amūn-compounds) → plain `u` (preserved elsewhere).
- Macron-Ō → plain `o` (preserved elsewhere).
- Underdot-Ḫ → plain `h` (preserved elsewhere).
- Underdot-Ḳ → plain `k` (preserved elsewhere).
- Underdot-Ḏ / d-bar Ḏ → plain `d` (preserved elsewhere).
- Ayin `ʿ` → keep in occupant_name AND elsewhere.

PM text-layer artifacts (apply silently):
- `I:I` or `I;I` → `Ḥ`; renders in notes/co_occupants as `Ḥ`; strips to `H` in occupant_name.
- `<` (alone) → `ʿ` (ayin). Renders in all fields as `ʿ`.
- `iin` → `ūn` (macron-Ū). E.g. `Amiin` → `Amūn`. Preserved in notes/co_occupants/co_occupant_roles; stripped in occupant_name.
- `Tutcankhamiin` → `Tutʿankhamūn` (ayin + macron-Ū). Same convention.
- `(` directly after a capital letter with no closing paren in the same word → cartouche-stub, strip.
- `~` (tilde alone) and `0` and `~~` and `}` etc. → hieroglyphic glyph artifacts, strip.

### `notes_from_pm` policy

Include ONLY the headword block:
- The role cluster following the all-caps name.
- The dating phrase (`Temp. <King>.`, `Dyn. <N>.`, etc.).
- Family clauses immediately following the headword (`Wife, X, ...`, `Father, Y, ...`, `Parents, A and B.`, `Mother, M.`).
- `Map <N>` / `Plan <N>` references when in the headword block.
- Standalone `Position, see <REF>.` lines (PM's geo-anchor refs).
- One-line excavation-summary lines if present in the headword block.

Do NOT include downstream museum-catalog rows ("Stela in Cairo Mus...", "Block in Leyden Mus...", "Sarcophagus in Brit. Mus..."). Those are body prose, not headword.

Do NOT prefix the occupant_name into notes_from_pm. notes starts with the role cluster.

KEEP PM-faithful diacritics verbatim (macron-Ē, underdot-Ḥ, ayin ʿ, macron-Ū) per chunks 14/15/22/26/27b/29/30 source-wide convention.

Use `null` if the headword block genuinely has no parenthetical refs / family clauses / Map line / Position line beyond the role + dating.

### Family-clause → `co_occupants` rule

Per chunks 8/14/15/22/27b/29/30/31 convention:
- `Wife, <Name>, <role>.` → add to `co_occupants` as `<Name>`, role string `"Wife, <role>"`. Always also keep verbatim in `notes_from_pm`.
- `Father, <Name>, <role>.` → add to `co_occupants` as `<Name>`, role string `"Father, <role>"`. Also in notes.
- `Mother, <Name>.` → add to `co_occupants` as `<Name>`, role string `"Mother"`. Also in notes.
- `Parents, A and B.` (with or without per-parent roles) → add BOTH to `co_occupants`. Use `"Father"` and `"Mother"` if PM does not specify per-parent roles; use `"Father, <role>"` if PM gives one for the father; same for mother.
- `Son, <Name>, <role>.` → add to `co_occupants` as `<Name>`, role string `"Son, <role>"`.
- `Daughter, <Name>, <role>.` → add to `co_occupants` as `<Name>`, role string `"Daughter, <role>"`.

For Shape-4 joint multi-burial tombs: the co-equal principals go in `co_occupants` (first principal in occupant_name, rest in co_occupants). For Shape-4b FAMILY TOMB headwords: the named family members listed under per-name sub-blocks all go as co_occupants — they're all residents of the family tomb. Roles use the form `"Joint occupant, <their role cluster>"` for the co-equal pattern, OR the parent/child/wife kinship form when PM specifies a relation to the primary.

### `co_occupants` / `co_occupant_roles` diacritic preservation

Per source-wide convention (chunks 14/15/22/26/30 + chunk-31 round-2 Gemini fix): macron-Ū on Amūn, underdot-Ḥ on Ḥathor/Ḥeneni/Ḥetepḥeres/Amenemḥab, macron-Ē on Re-compounds — ALL preserved in `co_occupants` and `co_occupant_roles`. Don't drop diacritics in these fields.

### `attribution_certainty` policy

- `Probably`, `(probably)`, `probably temp.` on the occupant identity / role → `"probable"`.
- `(?)` on the occupant's role OR name → `"uncertain"`.
- `(?)` on a PARENT name (e.g. `Degenneit(?)`) does NOT downgrade the row's attribution_certainty. Keep row at `"attested"`.
- `or` between two name forms does NOT downgrade — both forms are attested.
- `(altered to ...)` does NOT downgrade — that's a name-change record (Aten alteration), not an attribution hedge.
- `(also <ALT>)` does NOT downgrade — that's an alt-name record.
- Otherwise `"attested"`.

### `source_citation.page`

Use the **printed page number** of the headword line. The chunk file marker `=== phys p.<N> (printed p.<N+360>) ===` gives the printed page for each physical page. If the headword spans a page break, use the page where the all-caps name first appears.

## Constitutional Rule 1 — scholar-grade source-traced

Every emitted value must trace to the chunk file text. If the chunk text genuinely does not state a field, emit `null` / `[]`. Do NOT synthesize values from prior knowledge of famous tombs.

## Constitutional Rule 2 — no silent picks, no synthesis

If you genuinely can't decide a field value (ambiguous PM phrasing, OCR-noisy character that could resolve two ways), emit the value PM gives most literally in the headword. Do not silently pick "first one I thought of." If two readings are equally supported, prefer the shorter / more-conservative reading.

For tie-break compatibility downstream: every value you emit should be a STRICT verbatim from the chunk file — no character-level synthesis (e.g. don't add hyphens, line-break markers, or punctuation that aren't in the source).

## Stop criterion

Stop at the `K. OBJECTS FROM TOMBS` banner.

A calibration self-check (not a hard rule, revised 2026-05-19 after extraction; agents converged on 30 rows): the chunk covers approximately:
- (b) MIDDLE KINGDOM: ≈ 1 named-tomb headword
- (c) NEW KINGDOM: ≈ 23 named-tomb headwords (10 Dyn 18 + 12 Dyn 19 + 1 Dyn 20)
- (d) LATE AND PTOLEMAIC PERIODS: ≈ 6 named-tomb headwords (2 Dyn 26 + 2 Dyn 27 + 2 Ptolemaic Dyn 33)

Total calibration target: ≈ 30 rows. If your final count diverges by more than ±5 from this calibration, re-read the chunk file and check whether you've accidentally included FINDS-section partaged individuals or missed a sub-banner all-caps headword.
