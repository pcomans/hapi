# Extraction prompt — Porter & Moss Vol III.2, Chunk 24

> **Twenty-fourth chunk drawn from PM Vol III** — Ṣaqqâra § II.E WEST OF THE STEP PYRAMID, (a) OLD KINGDOM portion. PM III.2 physical pp.233–248 / printed pp.593–608. Contains the iconic **PTAḤḤOTP [I]** (D 62) + **AKHTIḤOTP / PTAḤḤOTP [II]** mastaba complex (D 64) + **Ḥetepḥerakhti D 60** + Petrie+Murray cluster D 59 / E 8 / E 9 + bare-named tombs Sekhemka + Thefu. This prompt is **self-contained**.

You are one of three independent extraction subagents.

**Source:** PM III.2 2nd ed. 1978/1981, ed. Málek. **Page offset:** printed = physical + 360.

**Output:** one JSONL line per row sorted by `tomb_id`, `json.dumps(..., sort_keys=True, ensure_ascii=False)`. Write to ONE of `raw/agent-{a,b,c}-chunk24.jsonl`.

## tomb_id convention

Same prefix scheme as chunk-23:
- `SAQD<N>` — Petrie+Murray Saqqâra D-numbered (D 59, D 60, D 62, D 63 → SAQD59, SAQD60, SAQD62, SAQD63).
- `SAQE<N>` — Petrie+Murray Saqqâra E-numbered (E 8, E 9 → SAQE8, SAQE9). **NEW prefix this chunk** (parallel to SAQD/SAQF).
- `SAQD<N>a` / `SAQD<N>b` — lowercase letter suffix for sub-banner-(a)/(b) sub-occupants within a mastaba-complex (e.g., D 64 mastaba-complex has (a) AKHTIḤOTP + (b) PTAḤḤOTP [II] → `SAQD64a` + `SAQD64b`). Parallel to chunk-7's `G2156b` convention. The two rows share `shared_with_tombs: ["SAQD64a", "SAQD64b"]` cross-references.
- `SAQ-<TitleCaseName>` for bare-named tombs without a D/E number (e.g., SEKHEMKA → `SAQ-Sekhemka`, THEFU → `SAQ-Thefu`, AKHTIḤOTP IPI-UZA → `SAQ-AkhtihotpIpiUza`).

## Cemetery field

All chunk-24 rows: `cemetery: "West of the Step Pyramid"` (new descriptor parallel to chunk-23's `"East of the Step Pyramid"`).

## Schema (23 keys, same as chunks 20–23)

```json
{
  "tomb_id": "SAQD<N>" | "SAQE<N>" | "SAQD<N><letter>" | "SAQ-<Name>",
  "memphite_area": "Saqqara",
  "occupant_name": "...",
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "Vizier" | "High Priest" | "Official" | "Royal Family" | "Unknown",
  "dynasty": "5" | "6" | null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "West of the Step Pyramid",
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "is_uninscribed": false,
  "is_usurped": false,
  "attribution_certainty": "attested" | "probable",
  "shared_with_tombs": [],
  "notes_from_pm": "...",
  "source_citation": {"page": <int>, "edition": "PM III.2 2nd ed. 1978/1981", "section": "II"}
}
```

## How to identify a row

**Shape 1 — Named D/E numbered.** `D <N>. <NAME IN CAPS>, <Title cluster>. <Dating>.` or `E <N>. <NAME IN CAPS>...`. Emit one row.

**Shape 1b — bare-named (no number).** `<NAME IN CAPS>, <Title cluster>. <Dating>.` without D/E/LS prefix. Emit one row with `tomb_id: SAQ-<TitleCaseName>`. Examples: SEKHEMKA, THEFU, AKHTIḤOTP IPI-UZA.

**Shape 1c — sub-banner (a)/(b) within mastaba-complex.** PM prints `D <N>. MASTABA-COMPLEX.` (or just `D <N>. <COMPLEX-NAME>.`) followed by `(a) <NAME1>, <Title>. <Dating>.` and `(b) <NAME2>, <Title>. <Dating>.` Emit ONE ROW PER sub-banner with `tomb_id: SAQD<N>a` / `SAQD<N>b` and `shared_with_tombs: ["SAQD<N>a", "SAQD<N>b"]` (excluding the row's own ID — agents may differ on inclusion, that's fine, merge will resolve).

**Shape 3 — Bracketed Roman regnal.** `<NAME> [I]` / `[II]`. Drop the brackets, append Roman to occupant_name with space, append to descriptor without space (e.g., `Ptaḥḥotp I`, descriptor `SAQ-PtahhotpI`). For D-numbered, the bracketed regnal goes into occupant_name as `Ptaḥḥotp I` (no descriptor change since tomb_id is SAQD<N>).

**Shape 1d — "or" idiom.** PM `<NAME1> (or <NAME2>) <NAME3>`. Per chunks 20–22 convention, longer/primary form in `occupant_name`, alternates in `occupant_alt_names`.

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per Shape-1/1b/1c/1d headword in this page range. Do NOT emit rows for sub-rooms (Room V., Offering-room., (N)-numbered scenes), body-prose object mentions, museum-citation lines.

## Expected row count

Rule-driven; ~10–14 rows expected (band 8–18). The chunk file spans 16 printed pages, with PTAḤḤOTP+AKHTIḤOTP D 64 mastaba-complex being the densest sub-feature block. Do NOT emit rows for sub-rooms or scene-numbered decoration of the D 64 mastaba-complex; those roll up into the SAQD64a + SAQD64b rows.

## Dating mappings

- `Temp. Userkaf` / `Temp. Saḥurēʿ` / `Temp. Neferirkarēʿ` / `Temp. Neuserrēʿ` / `Temp. Menkauḥor` / `Temp. Zadkareʿ Isesi` → `"5"` (Dyn V kings).
- `Temp. Isesi` → `"5"`. `Temp. Isesi to Unis` → `"5"` (range-start, since Unis is Dyn V's last king). `Temp. Isesi or later` → `"5"`.
- `Temp. Teti` / `Temp. Pepy I` / `Temp. Pepy II` → `"6"`.
- `Dyn. V` → `"5"`. `Dyn. V or later` / `Dyn. V-VI` → `"6"` (range-tail).
- `Dyn. VI` → `"6"`. `End of Dyn. V or Dyn. VI` → `"6"` (range-tail).
- `Probably <Dyn V/VI>` → as above + `attribution_certainty: "probable"`.

## PM III.2 text-layer noise (chunk-24-relevant)

**Raised-ayin.** Replace `a` / `c` / `<` / `>` raised glyphs with `ʿ` (U+02BF). Drop in tomb_id descriptors.

**Underdot-Ḥ.** Apply on ḥ-root names. Examples expected:
- HETEPḤERAKHTI → Ḥetepḥerakhti (double underdot on `ḥtp-ḥr` compound)
- PTAḤḤOTP → Ptaḥḥotp (double underdot: ptḥ + ḥtp)
- AKHTIḤOTP → Akhtiḥotp (single underdot on `ḥtp`)
- DUAḤAP → Duaḥap (underdot on `dwʿ-ḥʿpy` root)
- IPI-UZA → Ipi-uza (no ḥ)
- SEKHEMKA → Sekhemka (no ḥ)
- THEFU → Thefu (no ḥ)
- SESHEMNUFER → Seshemnufer (no ḥ)
- HEBA → Ḥeba (initial underdot, Ḥb-root)
- HATHOR → Ḥathor (single underdot per source convention; 44 occurrences vs 6 for Ḥatḥor — use single)
- HEMET-Rʿ → Ḥemet-rēʿ (initial underdot on Ḥmt + macron on Re terminus)

**Macron-Ē on Re-deity compounds.** `Reʿ` → `Rēʿ` (sun-god); `MERYRE<` → `Meryrēʿ`; `RA<NEFEREF` → `Raʿneferef` (per OCR vowel rule: capital R+A = no macron, capital R+E = macron).

**Wife/parents body-prose preservation.** Same as chunks 8–22.

## Field-by-field rules

- **`occupant_role`** — `"Vizier"` for Chief Justice and Vizier (Ptaḥḥotp I, Akhtiḥotp, Ptaḥḥotp II). `"Official"` for Judge and Elder of the Hall / Prophet / Overseer / Royal chamberlain / Lector-priest / Inspector etc. `"Royal Family"` only for King's son/daughter.
- **`dynasty`** — Per mappings above.
- **`sub_period`** — `null`.
- **`cemetery`** — Always `"West of the Step Pyramid"`.
- **`attribution_certainty`** — `"attested"` default; `"probable"` for `Probably <Dyn X>` headwords.
- **`shared_with_tombs`** — Only for Shape-1c sub-banner rows. Empty for everything else.
- **`notes_from_pm`** — Headword block prose; drop occupant name, hieroglyph noise, cartographic refs, sub-feature headings, museum-citation lines.
- **`source_citation`** — printed = physical + 360.

## Report format

```
agent-<X>-chunk24: <count> rows; <SAQD>/<SAQE>/<SAQD<N>letter>/<SAQ->/<other> split; <anomalies or "none">
```

Under 100 words.
