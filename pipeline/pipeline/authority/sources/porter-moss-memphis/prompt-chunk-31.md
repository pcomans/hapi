# Extraction prompt — Porter & Moss Vol III.2, Chunk 31

> **Thirty-first chunk drawn from PM Vol III** — Ṣaqqâra § II.G `BETWEEN THE MONASTERY OF APA JEREMIAS AND THE ENCLOSURE OF SEKHEMKHET`. PM III.2 physical pp.293–310 / printed pp.653–670. **First NK / Late-Period chunk in this source** — all prior chunks (1–30) covered Old Kingdom + scattered Saite intrusions. Per the 2026-05-19 scope expansion (mvp-tasks.md item 3), § II.G's NK + Late-Period named-tomb material is now in MVP scope. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-31-p293-p311.txt`.

**Source:** PM III.2 2nd ed. 1978/1981, ed. Málek. **Page offset:** printed = physical + 360.

**Output:** one JSONL line per row sorted by `tomb_id`, `json.dumps(..., sort_keys=True, ensure_ascii=False)`. Write to ONE of `raw/agent-{a,b,c}-chunk31.jsonl`.

## Scope: what TO extract

§ II.G has multiple sub-banners in the chunk text. Apply these scope rules:

| Sub-banner | Treatment |
|---|---|
| `OLD KINGDOM FINDS` | OUT OF SCOPE (loose blocks, no tomb-owner rows) |
| `(b) NEW KINGDOM` | IN SCOPE — extract every all-caps headword that opens a tomb section |
| `NEW KINGDOM FINDS` | OUT OF SCOPE (loose blocks; the lowercase-italic individual names under this banner — e.g. `Ḥuya`, `Ḥatiay`, `Ptaḥemḥab and Amenemḥab`, `[Raʿmosi]` — are partaged objects, not structurally-identified tombs) |
| `(c) LATE PERIOD` | IN SCOPE — extract every all-caps headword that opens a tomb section |
| `LATE PERIOD FINDS` | OUT OF SCOPE (architraves, blocks, etc.) |

Stop at the `H. AROUND PYRAMIDS OF PEPY I, MERENRĒʿ I, AND ISESI` banner — the chunk file truncates immediately after it. Do NOT extract any § II.H content (chunk 29 already covered it).

## How to identify a row

A row is opened by an **all-caps headword line** of one of these shapes within (b) NEW KINGDOM or (c) LATE PERIOD:

- **Shape 1a — bare named NK/LP tomb.** `<NAME IN CAPS> <hieroglyphs>, <role cluster>. <dating>.` — no Lepsius/Mariette/H-number prefix.
- **Shape 1b — Lepsius-numbered.** `LS <N>. <NAME IN CAPS> <hieroglyphs>, <role cluster>. <dating>.` Text layer may render `LS 25` as `LS 2 5` with space-separated digits.
- **Shape 1c — H-numbered.** `H <N>. <NAME IN CAPS> <hieroglyphs>, <role cluster>. <dating>.` (Quibell H-series; chunk-25 SAQH1 Nisusert was the first occurrence in this source.)
- **Shape 1d — name variant `(or <ALT>)` headword.** `<NAME IN CAPS> (or <ALT NAME IN CAPS>) <hieroglyphs>, <role cluster>. <dating>.` PM marks alternative attestations of the SAME person. The primary form is the one before `(or ...)`. The alt goes in `occupant_alt_names`.
- **Shape 1e — name-change `(altered to <ALT>)` headword.** `<NAME IN CAPS> (altered to <ALT NAME IN CAPS>) ...` PM marks an Aten-period Atenist alteration of an originally-non-Aten name. The pre-alteration form is primary; the post-alteration alt goes in `occupant_alt_names`.
- **Shape 4 — joint multi-burial tomb.** `TOMB OF THE <NAME1>S AND <NAME2> [<roman bracket>]` followed by `East part. <occupant A details>. <occupant B details>.` and `West part. <occupant C details>.` PM treats this as ONE tomb structure with multiple co-equal occupants spread across multiple parts. Per chunk-22 (TPC-Shema) / chunk-30 (SAQ-SankhenptahPtahshepses) precedent, emit a single row with `is_joint_burial: true`, the first-listed occupant as `occupant_name`, and the remaining occupants in `co_occupants` / `co_occupant_roles`.

## tomb_id convention

Apply in this order:

1. **Lepsius-numbered (`LS <N>`)** → tomb_id `LS<N>` (no space). Precedent: chunks 3, 8, 18, 19, 20, 23, 28.
2. **H-numbered (`H <N>`)** → tomb_id `SAQH<N>` (no space). Precedent: chunk-25 SAQH1 Nisusert.
3. **Mariette-letter-coded (`<letter> <num>`)** — not expected in this chunk's NK material but if present (Mariette's K-series for NK or similar), use `MAR-<letter><num>`. Precedent: chunks 28, 30.
4. **Bare-named (no numbering)** → `SAQ-<TitleCaseAsciiName>` descriptor. Strip diacritics and turn the occupant_name into ASCII title-case (e.g. `Haremhab` → `SAQ-Haremhab`, `Parahotp` → `SAQ-Parahotp`).
5. **Joint multi-burial tomb (Shape 4)** → use a short descriptor anchored to the first one or two occupants (e.g. `SAQ-Tomb<First>And<Second>` or `SAQ-Tomb<First>` if the second name is too long).

## Homonym disambiguators

Tomb-ids must be unique across the source. Check whether your `SAQ-<Name>` collides with any tomb_id in `reconciled.jsonl` (chunks 1-30, 767 rows). If a collision is unavoidable for a clean name, append a topographic-anchor or title-anchor suffix (e.g. `SAQ-PaserVizier` would distinguish a Vizier-titled Paser from a Steward-titled Paser; chunk-30 used `SAQ-NikaureJudge` vs `SAQ-NikaureOverseerOfWorks`).

## Schema (23 keys, identical to chunks 20–30)

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
  "dynasty": "18" | "19" | "26" | null,
  "sub_period": null | "Amarna",
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "Between the Monastery and Sekhemkhet's Enclosure",
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

**Every row** in chunk 31 uses `cemetery: "Between the Monastery and Sekhemkhet's Enclosure"` — the PM § II.G banner.

### Dynasty mapping (rule-based, by pharaoh-dynasty class)

| PM dating phrase | dynasty value | sub_period |
|---|---|---|
| `Temp. <King>` where `<King>` is a Dyn. XVIII pharaoh OTHER than Amenophis IV / Akhenaten / Smenkhkareʿ | `"18"` | null |
| `Temp. Amenophis IV` or `Temp. Akhenaten` (or `Temp. Smenkhkareʿ` if it appears) | `"18"` | `"Amarna"` |
| `Temp. <King>` where `<King>` is a Dyn. XIX pharaoh (Sethos I/II, Ramesses I/II, Merenptah, Amenmesse, Siptah, Tawosret) | `"19"` | null |
| `Ramesside` (no specific king named) | `"19"` | null |
| `Temp. <King>` where `<King>` is a Dyn. XXVI pharaoh (Psammetikhos / Psammetichus I/II/III, Necho I/II, Apries, Amasis) | `"26"` | null |
| `probably temp. <King>` | apply the matching class rule above; ADDITIONALLY set `attribution_certainty: "probable"` | — |
| `Dyn. <Roman>` explicit | Arabic numeral string (`"18"`, `"19"`, `"26"`, etc.) | null |
| Range `Dyn. X or Dyn. Y` (or `early/late Dyn. X or Dyn. Y`) | take the **later** dynasty (per chunk-23/30 range-tail convention) | — |
| No dating stated | `null` | — |

Use a dynasty list / Wikipedia / a king-authority lookup mentally to classify any `Temp. <King>` you don't immediately recognize. The chunk's NK material concentrates in Dyns XVIII–XIX; the LP material in Dyn XXVI. If PM gives a king you cannot confidently place in a dynasty (which would be unusual for these dynasties), emit `dynasty: null` rather than guessing.

### Occupant_role mapping (rule-based)

| PM headword title cluster contains | occupant_role |
|---|---|
| `Vizier`, `Governor of the town, Vizier` | `"Vizier"` |
| `King's daughter` + `King's wife` (LP, no other senior title) | `"Royal Family"` |
| `High Priest` | `"High Priest"` |
| Else, when an official title is present (`Overseer of ...`, `Steward of ...`, `General`, `Chief Steward`, `Royal scribe`, `Real royal scribe`, `Treasury`, `Fan-bearer`, `Judge`, etc.) | `"Official"` |

`Vizier` takes precedence when an individual carries both Vizier and other titles (chunk-11 TT29 precedent).

### `occupant_name` policy (PM-faithful, diacritic-stripped for Phase-A matching)

Per source-wide README:
- `occupant_name` strips Egyptological diacritics (underdot, macron, breve below).
- `occupant_name` KEEPS the ayin `ʿ` (U+02BF).
- `notes_from_pm` preserves PM-faithful diacritics verbatim (including underdot-Ḥ, macron-Ē, macron-Ū).

Apply uniformly:
- Underdot-Ḥ → plain `h` in occupant_name. Preserved in notes_from_pm.
- Macron-Ē (Re-compounds) → plain `e` in occupant_name. Preserved in notes_from_pm.
- Macron-Ū (Amūn-compounds) → plain `u` in occupant_name. Preserved in notes_from_pm.
- Ayin `ʿ` → keep in both fields.
- Acute-é, hyphen, apostrophes → keep verbatim.

PM text-layer artifacts in this chunk (apply silently, log only if a row is genuinely uncertain):
- `I:I` or `I;I` → `Ḥ` (underdot-Ḥ). Renders in notes_from_pm; strips to `H` in occupant_name.
- `<` (alone) → `ʿ` (ayin). Renders in both fields as `ʿ`.
- `(` directly after a capital letter with no closing paren in the same word → cartouche-stub, strip.

### `notes_from_pm` policy

Include ONLY the headword block:
- The role cluster following the all-caps name (`Overseer of ...`, etc.).
- The dating phrase (`Temp. <King>.`, `Dyn. <N>.`, etc.).
- Family clauses immediately after the headword (`Wife, X, ...`, `Father, Y, ...`, `Parents, A and B.`, `Mother, M.`).
- `Map LXII` / `Map LXVII` references when present in the headword block.
- Standalone `Position, see <REF>.` lines (these are PM's geo-anchor refs, headword-adjacent).
- `Accounts of excavation, ...` lines that summarize the find context (one line max).

Do NOT include downstream museum-catalog rows ("Stela in Cairo Mus...", "Block in Berlin Mus...", "Sarcophagus, anthropoid, basalt", etc.). Those are body prose.

Use `null` if the headword line genuinely carries only the role cluster + dating and no parenthetical refs / family clauses / Map line / Position line.

### Family-clause → `co_occupants` rule

Per chunks 8/14/15/22/27b/29/30 convention:
- `Wife, <Name>, <role>.` → add to `co_occupants` as `<Name>`, role string `"Wife, <role>"`. Always also keep verbatim in `notes_from_pm`.
- `Father, <Name>, <role>.` → add to `co_occupants` as `<Name>`, role string `"Father, <role>"`. Also in notes.
- `Mother, <Name>.` → add to `co_occupants` as `<Name>`, role string `"Mother"`. Also in notes.
- `Parents, A and B.` (with or without per-parent roles) → add BOTH to `co_occupants`. Use `"Father"` and `"Mother"` if PM does not specify per-parent roles; use `"Father, <role>"` if PM gives one for the father; same for mother.
- If a name carries an `(?)` hedge (e.g. `Degenneit(?)`), drop the `(?)` from the `co_occupants` entry but keep the `(?)` verbatim in `notes_from_pm` to preserve the source hedge.

### Family-clauses for Shape-4 joint multi-burial tombs

For any Shape-4 joint multi-burial tomb (a headword opening `TOMB OF THE <plural-name>S AND <other-name>` followed by `East part. ... West part. ...` or equivalent multi-part structure):
- The co-equal East/West-part **principal occupants** DO go in `co_occupants` (after the first-listed principal which becomes `occupant_name`). Use role string form `"Joint occupant, <their role cluster>"` to mark coordinate burial — parallel to chunk-30 SAQ-SankhenptahPtahshepses precedent.
- `son of <Mother>` / `daughter of <Father>` / `son of <Father>` parentage clauses attached to a principal occupant: the parent goes in `co_occupants` ONLY if PM explicitly states the parent is independently buried in the same tomb. Absent such a statement (the typical case — PM just names a parent for prosopographic context), parent references stay in `notes_from_pm` only, NOT in `co_occupants`.
- `is_joint_burial: true` for these multi-principal tombs (no single principal occupant designation).
- `attribution_certainty` for the row reflects the WEAKEST principal's certainty (if any principal carries `probably`, the row is `"probable"`).

### `attribution_certainty` policy

- `Probably`, `(probably)`, `probably temp.` on the occupant identity / role → `"probable"`.
- `(?)` on the occupant's role OR name → `"uncertain"`.
- `(?)` on a PARENT name (e.g. `Degenneit(?)`) does NOT downgrade the row's attribution_certainty — that's a parent-name hedge captured in `notes_from_pm`. Keep row at `"attested"`.
- `or` between two name forms (PARAḤOTP or RAʿḤOTP) does NOT downgrade — both forms are attested.
- `(altered to ...)` does NOT downgrade — that's a name-change record (Aten alteration), not an attribution hedge.
- Otherwise `"attested"`.

### `source_citation.page` (printed page number from the running header)

Use the **printed page number** shown in the running header on the physical page where the headword first appears. PM III.2 phys ≈ printed − 360 for this chunk; if your arithmetic disagrees with the printed header, trust the printed header.

## Constitutional Rule 1 — scholar-grade source-traced

Every emitted value must trace to the chunk file text. If the chunk text genuinely does not state a field (no dating, no role, no family clause), emit `null` / `[]`. Do NOT synthesize values from prior knowledge of any tombs that happen to be famous (Haremhab's wife Mutnodjmet, Maya's wife Meryt, the Theban TT255 connection, the EES/Leiden joint-excavation history — none of that is in PM III.2's headword block and none of it should appear in your rows).

## Constitutional Rule 2 — no silent picks

If you genuinely can't decide a field value (ambiguous PM phrasing, OCR-noisy character that could resolve two ways), emit the value PM gives most literally in the headword. Do not silently pick "first one I thought of." If two readings are equally supported by the headword text, prefer the shorter / more-conservative reading.

## Stop criterion

Stop after the `H. AROUND PYRAMIDS OF PEPY I, MERENRĒʿ I, AND ISESI` banner. Do not emit any § II.H rows.

A calibration self-check (not a hard rule): the (b) NEW KINGDOM section has ≈ 10 named-tomb headwords; the (c) LATE PERIOD section has ≈ 2 named-tomb headwords. If your count diverges by more than ±2 from this calibration, re-read the chunk file before submitting — you may have accidentally included a FINDS-section partaged-individual headword or missed a small LS-numbered tomb.
