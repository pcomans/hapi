# Cross-Source Date Convention Spec

**Issue:** [#183](https://github.com/pcomans/hapi/issues/183) — Tier 4 of the 2026-05 schema audit.

**Status:** Design document. Captures the current per-source date conventions across all 11 authority sources after the Tier 1–3 schema-audit fixes (#172, #174–#182), proposes a canonical date-shape that Phase A consumers can normalise toward, and identifies the remaining cross-source mismatches that downstream code must handle until per-source migrations close them.

**Audience:** Phase A authors who cross-reference dates across sources. Per-source schema authors when adding new typed fields.

---

## Why this matters

Five sources carry numeric BCE/CE dates with subtly different conventions; another four carry only structured-prose dates (dynasty labels, sub-period names, regnal-attestation tokens). If Phase A enrichment cross-references dates across these sources without a canonical normalisation step, downstream code will silently:

- Mis-compare BCE years (e.g. arithmetic on Shaw OHAE Ch 2's `-700000` Palaeolithic figure as if it were a regnal-precise year).
- Mis-render qualifiers (`c.` vs `ca.` vs `ungefähr` vs no marker).
- Fail to detect BCE/CE boundary crossings (Shaw OHAE ch 15 Roman Period: `start=-30, end=395`).
- Conflate the four different existence-uncertainty conventions (`existence_uncertain` / `existence_doubtful` / `is_uncertain_attribution` / `attribution_certainty`).

The Tier 4 audit produced this spec; per-source migrations toward it will be tracked under follow-up issues.

---

## Per-source current shapes (post-audit)

### Numeric-date sources

#### Beckerath 1997 (`beckerath-1997-chronologie/`, 174 rows)

```jsonc
{
  "start_bce_high": -3032,        // older / more negative end of the slash range
  "start_bce_low":  -2982,        // younger / less negative end
  "end_bce_high":   -3000,
  "end_bce_low":    -2950,
  "start_approximate": true,      // per-bound `ca.` / `etwa` / `vor` / `nach` / `um`
  "end_approximate":   true
}
```

- **Sign convention:** BCE = negative.
- **Pair convention:** Beckerath's slash form (`X/Y`) splits into `_high` (older) and `_low` (younger). When Beckerath gives a single endpoint, both are equal.
- **Qualifier:** per-bound boolean (`start_approximate`, `end_approximate`). True when the cell carries `ca.`, `etwa`, `vor`, `nach`, `um`, `?`, `??`, OR when the section heading propagates `etwa N Jahre`.
- **Era:** BCE-only; all four bounds are negative integers or null.
- **Existence-uncertainty:** `existence_uncertain: bool` (post-#179, derived from `(?)` / leading `?` / German quotes `„...“` in the `name` field). 3 rows: 02.08, 22.07, 23.04.

#### HKW 2006 (`hkw-chronology-2006/`, 207 rows)

```jsonc
{
  "start_year": -2900,
  "end_year":   -2545,
  "start_year_approximate": null,         // per-bound, three-state (true/false/null)
  "end_year_approximate":   true,
  "approximate": true,                    // row-level rollup
  "uncertainty_plus_years": 25,           // HKW's `+25` convention
  "null_dates_reason": "HKW prints '2900–?+25' — end year unknown per HKW source."
}
```

- **Sign convention:** BCE = negative.
- **Pair convention:** Single bounds (no slash form).
- **Qualifier:** per-bound `_approximate` (three-state to distinguish "HKW marked approximate" from "HKW unmarked" from "HKW omitted entirely") + a row-level `approximate` rollup.
- **Era:** BCE-only.
- **Plus-years sentinel:** `uncertainty_plus_years` captures HKW's `+N` convention (e.g. `2900–?+25` means the end is unknown but at least +25 years past the start).
- **Null-dates rationale:** typed `null_dates_reason` field (post-#176) documents WHY the date is null on a row-by-row basis.
- **Existence-uncertainty:** `name_uncertain: bool` (post-#176).

#### Kitchen TIPE (`kitchen-tipe/`, 60 rows)

```jsonc
{
  "start_bce": -1098,
  "end_bce":   -1069,
  "approximate": true,
  "length_of_reign_years": 29,
  "corrected_end_bce": -1045   // Kitchen typo correction (only on 21H.06)
}
```

- **Sign convention:** BCE = negative.
- **Pair convention:** Single bounds (no slash form).
- **Qualifier:** row-level `approximate: bool` (no per-bound distinction).
- **Era:** BCE-only.
- **Typo correction:** `corrected_end_bce: int | None` (post-#180) — typed replacement for the previous `DKF_INTERVAL` Python constant. Single source of truth for `_compute_concurrency` interval math; `end_bce` itself stays Kitchen-verbatim.
- **Existence-uncertainty:** `existence_doubtful: bool` (post-#180). 4 rows: 23.08, 24E.01, 24E.02, 24P.01.

#### Ryholt 1997 SIP (`ryholt-1997-sip/`, 157 rows)

```jsonc
{
  "date_bce_start": -1803,
  "date_bce_end":   -1800,
  "date_attestation": "both",   // enum: both | start_only | end_only | none
  "is_uncertain_attribution": true
}
```

- **Sign convention:** BCE = negative.
- **Pair convention:** Single bounds (no slash form).
- **Qualifier:** typed `date_attestation` enum (post-#177) — distinguishes "no date" from "Ryholt couldn't reconcile single-cell entry to a range."
- **Era:** BCE-only.
- **Existence-uncertainty:** `is_uncertain_attribution: bool` (post-#177). 7 rows.

#### Shaw OHAE 2000 (`shaw-ohae-2000/`, 13 rows)

```jsonc
{
  "date_range_start_bce": -700000,           // negative even for geological scale
  "date_range_end_bce":   -4000,
  "date_qualifier": "c.",                    // enum: "c." | None
  "date_precision": "geological",            // enum: geological | regnal_approximate | regnal_precise
  "crosses_bce_ce": false                    // True for ch 15 Roman Period
}
```

- **Sign convention:** BCE = negative; **CE = positive**. Shaw is the only source whose `_end_bce` field can hold a positive value (Ch 15 Roman Period: `30 bc-ad 395` → `(start=-30, end=+395)`).
- **Pair convention:** Single bounds (no slash form).
- **Qualifier:** row-level `date_qualifier` enum (`c.` or null).
- **Era:** BCE+CE; `crosses_bce_ce: bool` (post-#181) explicitly flags the boundary-crossing row.
- **Date precision:** `date_precision` enum (post-#181) — `geological` for the Palaeolithic Ch 2 row (`-700000` is order-of-magnitude, NOT regnal-precise), `regnal_approximate` for `c.`-qualified rows, `regnal_precise` for the four chapters where Shaw drops the `c.` hedge (Ch 12–15).

#### pharaoh.se (`pharaoh-se/`, 381 rows) — **deprecated per #122**

```jsonc
{
  "start_year": -2900,
  "end_year":   -2870,
  "dynasty_label": "Predynastic kings"
}
```

- **Sign convention:** BCE = negative; **CE = positive** (Roman dynasties).
- **Era detection:** consumers must call `_is_roman_dynasty()` (substring check on `dynasty_label` for `"Roman"`) to know that bare `start_year=14` means CE not BCE. There is no typed `era` flag.
- **BCE/CE boundary:** Augustus row crosses (`-27` → `14`) with no flag.
- **Status:** being deprecated per #122; this convention block exists for historical reference and to inform the canonical spec.

#### Porter-Moss Theban Necropolis (`porter-moss-theban-necropolis/`, 75 rows)

```jsonc
{
  "date_bce_approx_start": null,             // currently always null
  "date_bce_approx_end":   null,             // currently always null
  "discovery_year":        null,             // CE year — modern excavation date
  "attribution_certainty": "attested"        // enum: attested | probable | uncertain
}
```

- **Sign convention:** BCE = negative; **CE = positive** (`discovery_year` only).
- **Pair convention:** Single bounds (no slash form).
- **Qualifier:** all rows currently null on the BCE fields — PM's tomb-attribution dates resolve via Phase-A king-authority lookup, not via PM verbatim.
- **Era:** mixed — BCE for tomb date, CE for `discovery_year`.
- **Attribution-certainty:** `attribution_certainty` enum (post-#182). 3-state: attested / probable / uncertain. Distinct from "the king's existence is doubtful" (which uses other sources' flags).

### Structured-prose-only sources

These sources don't carry numeric BCE fields; their date semantics live in `dynasty` / `sub_period` / `dynasty_label` text:

- **Baud 1999** — `dynasty: str`, `sub_period: str` (e.g. `"end Dyn 4 – early Dyn 5"`). No numeric BCE. Dates resolve via Phase-A dynasty-to-BCE crosswalk.
- **Dodson-Hilton queens** — `dynasty: int`, `sub_period: str` (e.g. `"The Decline of the Ramessides"`). No numeric BCE.
- **Leprohon 2013** — `dynasty_label: str`, `dynasty_number: int`. No numeric BCE. (Leprohon catalogues titularies, not chronology; consumers cross-reference Beckerath/Ryholt/Kitchen for BCE.)
- **iDAI gazetteer** — geographic source, no chronology.

---

## Canonical date-shape spec (proposed)

Phase A consumers MUST normalise per-source dates into a canonical envelope before cross-source comparison. The spec below is the target shape. Per-source migration toward it is tracked separately (see "Migration plan" below).

**Suffix convention:** `_older` and `_younger` are deliberately chosen over `_high`/`_low` because BCE numerics invert the usual ordering — the "older" date is numerically the SMALLER value (`-3032` is older than `-2982`). Calling the older value `_high` is the opposite of the standard programming convention where `_high` means max. The temporal-semantic suffix `_older` matches the meaning regardless of sign. Per Gemini PR #195 round-1.

**Sources without a slash range** (HKW, Kitchen, Ryholt, Shaw, PM) set `_older == _younger` to the single value. **Null endpoints** set both to null and populate `null_endpoints_reason`.

**Year 0 — astronomical-vs-historical convention.** This spec uses ASTRONOMICAL year numbering (ISO 8601-ish): `1 BCE = 0`, `2 BCE = -1`, `N BCE = -(N - 1)`, `1 CE = 1`, `N CE = N`. Rationale: integer arithmetic across the BCE/CE boundary (`end - start`) returns the correct year-count without an off-by-one correction. Sources that use the historical convention (1 BCE = -1, no year 0) MUST be normalised by the canonicalisation helper before storage in the canonical envelope. **Current state:** every numeric source in HAPI uses the historical convention (`-3032` means 3032 BCE; no year 0). The canonicalisation helper for v0 will ADD 1 to negative values to map historical → astronomical (`-3032` historical = `-3031` astronomical = 3032 BCE with year 0 = 1 BCE). Verify per-source on first integration.

```jsonc
{
  // === Era handling ===
  "era": "BCE",                    // enum: BCE | CE | crosses (BCE→CE within row)
  // For sources where end_year crosses 0, era="crosses" and the
  // numeric `start`/`end` fields use the BCE=negative / CE=positive
  // convention (matches Shaw OHAE post-#181).

  // === Numeric bounds (canonical names) ===
  // Values are in ASTRONOMICAL year numbering (see Year 0 section
  // below). Beckerath's verbatim `start_bce_high=-3032` (historical)
  // canonicalises to `-3031` here. Phase A consumers reading off the
  // canonicalisation helper see the astronomical values directly.
  "start_year_older":   -3031,     // older endpoint of the start range
  "start_year_younger": -2981,     // younger endpoint of the start range
  "end_year_older":     -2999,     // older endpoint of the end range
  "end_year_younger":   -2949,     // younger endpoint of the end range

  // === Qualifier handling ===
  "start_approximate": true,       // per-bound bool — true when source marks
  "end_approximate":   true,       //   the bound with c. / ca. / ?? / ungefähr
  // The row-level rollup (`approximate`) is computable as
  // `start_approximate or end_approximate` and is not stored.

  // === Precision / null-reason ===
  "date_precision": "regnal_approximate",
  // enum: geological | regnal_approximate | regnal_precise | null-only
  // - geological: BCE figures are order-of-magnitude (Palaeolithic)
  // - regnal_approximate: ±decade-precise (the default for Egyptological
  //   chronology pre-Saite)
  // - regnal_precise: source explicitly drops the qualifier (Saite +
  //   later, where ancient sources fix accession dates to the day)
  // - null-only: row carries no numeric date; consumer must use
  //   `dynasty` / `sub_period` for ordering

  "null_endpoints_reason": null,   // populated when both _older and _younger are null
  "corrected_end_year":   null,    // typed source-correction (Kitchen 21H.06)
  "minimum_duration_years": null,  // numeric "at least N years" constraint
                                   // when the source records a +N convention
                                   // with a null endpoint (HKW's `2900–?+25`
                                   // → start_year_*=−2900, end_year_*=null,
                                   // minimum_duration_years=25). Phase A
                                   // interval arithmetic uses this to compute
                                   // a lower bound for the duration even
                                   // when the end is unknown.

  // === Crosswalk-to-source ===
  // Per-bound qualifier tokens — Beckerath supports asymmetric per-bound
  // forms like `vor 1000 – nach 950`. Singular `source_qualifier_token`
  // would lose half the information for these rows. Per Gemini PR #195
  // round-6.
  "start_qualifier_token": "ca.",  // verbatim glyph from source on start
                                   // (`"c."` Shaw, `"ca."` Beckerath/Kitchen,
                                   // `"vor"` / `"ungefähr"` Beckerath, etc.)
  "end_qualifier_token":   "ca."   // verbatim glyph from source on end
}
```

### Uncertainty (TWO separate field families — do not conflate)

Per Gemini round-1 finding: an earlier draft of this spec proposed a single `existence_certainty` enum that conflated three distinct semantic axes. **They are NOT the same** and must be tracked in separate fields by Phase A consumers.

#### 1. Ruler / person existence-uncertainty

The source itself flags whether the named ruler / person is historically attested or doubted. Lives on the same row that carries the named ruler.

```jsonc
{
  "existence_certainty": "attested"
  // enum: attested | doubtful
  //
  // Sources mapping into this field:
  // - existence_uncertain (Beckerath, post-#179)        → doubtful when True
  // - existence_doubtful (Kitchen, post-#180)           → doubtful when True
  // - name_uncertain (HKW, post-#176)                   → see #2 below — semantically
  //   maps to attribution_certainty=uncertain, NOT existence (HKW's flag means
  //   "uncertain WHICH name belongs in this slot", not "the king didn't exist")
}
```

#### 2. Attribution-certainty (entity → ruler)

The source flags how confident it is that a particular entity (tomb, monument, attestation) belongs to a particular ruler. The ruler's existence is independent of the attribution. Lives on the entity row.

```jsonc
{
  "attribution_certainty": "attested"
  // enum: attested | probable | uncertain
  //
  // Sources mapping into this field:
  // - attribution_certainty (Porter-Moss, post-#182) — already in
  //   this exact 3-state enum; canonical reference shape.
  // - is_uncertain_attribution (Ryholt, post-#177) — per-row
  //   attribution-uncertainty (which dynasty does the king belong to).
  //   Maps to attribution_certainty=uncertain when True. NOTE:
  //   distinct from Ryholt's `is_unattributed` (no dynasty at all —
  //   see #3 below).
  // - name_uncertain (HKW, post-#176) — uncertainty between candidate
  //   names for a chronological slot whose existence is NOT doubted.
  //   Per Gemini PR #195 round-4: this is a name-attribution flag,
  //   not an existence flag. Maps to attribution_certainty=uncertain
  //   when True.
}
```

#### 3. Unattributed (no ruler claim at all)

The source records data (a name, a tomb, a fragment) without claiming who/where it belongs to. This is a third axis — an unattributed row may have neither an existence-certainty nor an attribution-certainty value because there's no candidate ruler to evaluate.

```jsonc
{
  "is_unattributed": false
  // bool. True when the source records the entity but assigns no ruler.
  //
  // Sources mapping into this field:
  // - is_unattributed (Ryholt, post-#177) — N/P/H/D/G prefix rows
  //   that record nomen/prenomen/etc. without dynasty assignment.
}
```

These three field families are orthogonal. A Phase-A AGGREGATE record (built from multiple source types — e.g. Beckerath for the king-list + Porter-Moss for the tomb catalogue) can carry `existence_certainty=doubtful` (sourced from Beckerath: the king's existence is debated) AND `attribution_certainty=probable` (sourced from PM: the tomb is probably his) AND `is_unattributed=false` (the row has a candidate ruler). The single-enum draft conflated them and would have lost semantic detail on every cross-source map. **Within a single source extract**, you typically see only one of the three; the orthogonality matters at the Phase-A aggregation step.

---

## Mismatches against the canonical spec

| Source | BCE field name | Slash range? | Qualifier shape | Era handling | Uncertainty field(s) | Largest gap |
|---|---|---|---|---|---|---|
| Beckerath | `start_bce_high/_low + end_bce_high/_low` | yes | per-bound bool | BCE-only | `existence_uncertain` | naming + slash |
| HKW | `start_year + end_year` | no | per-bound 3-state + row-level rollup | BCE-only | `name_uncertain` | naming + plus-years |
| Kitchen | `start_bce + end_bce` | no | row-level bool | BCE-only | `existence_doubtful` | naming + no per-bound qualifier |
| Ryholt | `date_bce_start + date_bce_end` | no | enum (`date_attestation`) | BCE-only | `is_uncertain_attribution` | naming + qualifier-as-enum |
| Shaw OHAE | `date_range_start_bce + date_range_end_bce` | no | row-level enum (`date_qualifier`) | BCE+CE explicit | (no flag — uses date_precision) | naming |
| pharaoh.se | `start_year + end_year` | no | none | BCE+CE substring-detected | (no flag) | era detection |
| PM Theban | `date_bce_approx_start + date_bce_approx_end` | no | implicit in field name | mixed (CE for `discovery_year`) | `attribution_certainty` | naming + always-null |

**Common mismatches**:
- **6 BCE field naming conventions across 7 numeric sources.** No two agree.
- **3 qualifier shapes**: per-bound bool (Beckerath, HKW), row-level bool (Kitchen), row-level enum (Shaw, Ryholt).
- **5 uncertainty-related field names** with overlapping semantics across two distinct axes (existence vs attribution); only PM's `attribution_certainty` is already a 3-state enum.

---

## Migration plan

The per-source schema-audit PRs (#175–#182) typed each source's existing date conventions; they did NOT migrate the field NAMES toward a canonical shape. That migration is deferred to one of two paths:

### Option A: Phase-A canonical-date helper (recommended for v0)

Build a `pipeline.authority.dates.canonicalize_date(row, source)` helper that maps each source's verbatim date fields into the canonical envelope at consumer-read time. No schema changes required; Phase A code works against the canonical envelope. Downside: every consumer call pays a small canonicalisation cost; field-name drift across sources persists in the on-disk JSONL.

**Advantages**:
- Zero risk to existing per-source tests / closure assertions
- Phase-A consumers see one shape; per-source extracts stay verbatim per Rule 6
- Reversible — if a source's convention changes, only the helper updates

**Disadvantages**:
- Two sources of truth for the same fact (verbatim + canonical); downstream consumers must always use the helper
- The helper is a bottleneck for new sources (every addition needs a mapper rule)

### Option B: Per-source field renames toward the canonical spec

Land 7 separate PRs, one per numeric source, that renames each source's BCE fields to the canonical names. Each PR runs the rename in `fix_rows.py` and updates the corresponding closure tests. Phase A then reads the canonical envelope directly off the JSONL.

**Advantages**:
- Single source of truth on disk
- Phase A consumers never need a canonicalisation helper
- The rename is grep-detectable in CI; drift can't accumulate silently

**Disadvantages**:
- 7 separate PRs (Beckerath, HKW, Kitchen, Ryholt, Shaw, PM, pharaoh.se if not deprecated first)
- Each PR breaks the source's existing closure tests; substantial test-update work
- Rule 10 ("no backwards compat") + the per-source legacy-scalar precedent set in #179 / #180 (where legacy scalars were KEPT as derivative ingest artifacts to preserve fix_rows idempotence) suggests this would generate a lot of "legacy field kept alongside canonical" pairs — at which point we're back to Option A's two-sources-of-truth concern

### Recommendation

**v0: Option A.** Build `canonicalize_date()` as a Phase-A read-side helper. Keep all per-source fields verbatim. Document the helper's mapping table inline as the authoritative cross-source reference.

**Post-v0 (post-real-consumer feedback)**: revisit. If multiple consumers replicate the canonicalisation logic OR if the per-source field names cause confusion in the JSONL itself, evaluate Option B as targeted renames on the highest-friction sources first.

---

## Per-source migration tickets (track here)

The following remaining cross-source gaps are candidates for follow-up issues:

- [ ] Build `pipeline.authority.dates.canonicalize_date(row, source)` helper (Option A v0).
- [ ] Beckerath: 23 NK accession dates (`Antritt 31.5.1279`-style) hidden in `notes_from_beckerath` (Shape C P2 deferred from #179) — extract into typed `accession_date_text` or `accession_date_iso` field.
- [ ] HKW: revisit `start_year_approximate=null` three-state convention — does Phase A actually need to distinguish "marked approximate" from "marked precise" from "unmarked"? If not, collapse to two-state.
- [ ] Kitchen: backfill `corrected_end_bce` audit if any other rows surface Kitchen-typo corrections beyond 21H.06.
- [ ] Cross-source: pharaoh.se deprecation per #122 — fold any pharaoh-se-only conventions into the canonicalisation helper as transitional, then drop when the source is deleted.
- [ ] Ryholt + Beckerath: dynasty-based BCE crosswalk — both sources annotate Dyn-13–17 with absolute BCE, but their conventions for `concurrent_with` differ (Ryholt's polity-list vs Beckerath's prose). Phase-A consumer needs a unified concurrency model.

Each of these warrants its own issue; this document is the canonical reference for what the date conventions ARE today.
