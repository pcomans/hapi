# Extraction prompt — Porter & Moss Vol III.2, Chunk 25

> **Twenty-fifth chunk drawn from PM Vol III** — Ṣaqqâra § II.E WEST OF THE STEP PYRAMID continuation + § II.E AROUND THE PYRAMID-COMPLEX OF UNIS opening. PM III.2 physical pp.249–272 / printed pp.609–632. Mixed cohort: continuing Petrie+Murray E/F/H-series + named OK mastabas including Princess Khentkaus, Akhtiḥotp Ipi, Sebkemkhent Sebeky, Pernezu + new sub-banner `AROUND THE PYRAMID-COMPLEX OF UNIS` with named officials (Mery-Isesi, Unis-Ḥaishtef Ḥaishtef, Iynefert, Seshemnufer). EXCLUDES PTOLEMAIC TOMB A/B + LATE PERIOD SHAFT (out of OK + 1st-Int-Period scope). This prompt is **self-contained**.

You are one of three independent extraction subagents.

**Source:** PM III.2 2nd ed. 1978/1981, ed. Málek. **Page offset:** printed = physical + 360.

**Output:** one JSONL line per row sorted by `tomb_id`, `json.dumps(..., sort_keys=True, ensure_ascii=False)`. Write to ONE of `raw/agent-{a,b,c}-chunk25.jsonl`.

## tomb_id convention

Same prefix scheme as chunks 23–24 plus NEW `SAQH<N>` prefix:
- `SAQD<N>`, `SAQE<N>` — Petrie+Murray Saqqâra D/E-numbered (chunks 23-24).
- `SAQH<N>` — NEW prefix this chunk for Petrie+Murray H-numbered (e.g., H 1 Nisusert → `SAQH1`).
- `SAQF<N>` — F-numbered (chunk 23 already used SAQF1, SAQF3).
- `SAQ-<TitleCaseName>` for bare-named tombs (parallel to chunk-24's SAQ-Sekhemka etc.).

## Cemetery field

Two cemeteries in this chunk's page range:
- `"West of the Step Pyramid"` for rows on phys pp.249–255 (continuation of chunk-24's banner).
- `"Around the Pyramid-complex of Unis"` for rows on phys pp.256+ (NEW sub-banner; matches PM literal phrasing).

## Schema (23 keys, same as chunks 20–24)

```json
{
  "tomb_id": "SAQD<N>" | "SAQE<N>" | "SAQF<N>" | "SAQH<N>" | "SAQ-<Name>",
  "memphite_area": "Saqqara",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "Vizier" | "High Priest" | "Official" | "Royal Family" | "Princess" | "Unknown",
  "dynasty": "5" | "6" | null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "West of the Step Pyramid" | "Around the Pyramid-complex of Unis",
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

## How to identify a row

**Shape 1 — Named D/E/F/H numbered.** `<Letter> <N>. <NAME IN CAPS>, <Title cluster>. <Dating>.`. Emit one row.

**Shape 1b — bare-named.** `<NAME IN CAPS>, <Title cluster>. <Dating>.` Emit one row with `tomb_id: SAQ-<TitleCaseName>`.

**Shape 1d — "or" idiom + "good name" idiom.** Per chunks 20-24 convention.

**Shape 4 — Joint twin/family-tomb headword.** `<NAME1> and <NAME2>` joint emit one row with `is_joint_burial: true`.

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per Shape-1/1b/1d/4 headword in this page range whose dating is **Old Kingdom OR 1st Int. Period** (Dyn V, Dyn V or later, Dyn V-VI, Dyn VI, Late Dyn VI, End of Dyn VI, 1st Int. Period, Probably <Dyn V/VI>, Temp. <Dyn V/VI king>).

Do NOT emit rows for:
- `LATE PERIOD SHAFT.` sub-banner contents.
- `PTOLEMAIC TOMB A.` / `PTOLEMAIC TOMB B.` (out of OK scope).
- Anonymous `TOMB A.` / `TOMB B.` under the `FINDS FROM WEST OF THE STEP PYRAMID` sub-banner (no Shape-1 named-occupant headword — these are anonymous Shape-5 deferred to a future chunk).
- Sub-rooms (Room I., Burial chamber., (N)-numbered scenes).
- Body-prose object mentions in sub-features.
- Museum-citation lines, publication references.
- Body-prose `Mastaba usurped by <NAME>` cross-references — emit a usurper row ONLY if the usurper has a separate Shape-1 headword block.

## Expected row count

Rule-driven; ~12–20 rows expected (band 8–25). The chunk spans 24 printed pages (denser than chunk-24's 16 pages but with more sub-feature content per tomb). Watch for: continuing E-numbered + new H-numbered + many bare-named tombs in the "Around the Pyramid-complex of Unis" sub-section.

## PM III.2 text-layer noise (chunk-25-relevant)

**Raised-ayin.** Replace `a` / `c` / `<` / `>` raised glyphs with `ʿ` (U+02BF). Drop in tomb_id descriptors.

**Underdot-Ḥ.** Apply on ḥ-root names per source-wide convention (chunks 19-24). Notable in this chunk:
- AKHTIḤOTP → Akhtiḥotp
- ḤAISHTEF → Ḥaishtef
- NIʿANKH-ḤATHOR → Niʿankh-ḥathor
- ʿANKHI ITHI → ʿAnkhi Ithi (no ḥ)
- IḤḤOTP → Iḥḥotp (double underdot)
- ḤARSHEPSES → Ḥarshepses
- NEFERḤETPES → Neferḥetpes

**Macron-Ē on Re-deity compounds.** `Rēʿ`, `Menkauḥor` (no macron, kʿw-ḥr root), `Merenrēʿ` (macron-Ē + ayin), `Saḥurēʿ`, `Neuserrēʿ`, `Neferirkarēʿ`. OCR vowel rule: capital R+A = no macron (Raʿ), capital R+E = macron (Rēʿ).

**Dating mappings (continuing chunks 23-24 vocabulary).** `Temp. Merenrēʿ I` → `"6"`. `Temp. Pepy II or later` → `"6"`. `Temp. Unis or Dyn. VI` → `"6"` (range-tail). `Probably Dyn. VI` → `"6"` + `attribution_certainty: "probable"`. `Probably late Dyn. V` → `"5"` + probable.

**Wife/parents body-prose preservation.** Same as chunks 8-24.

## Field-by-field rules

- **`occupant_role`** — `"Vizier"` for Chief Justice and Vizier (Iynefert, Akhtiḥotp Ipi). `"Princess"` for `King's eldest daughter` (KHENTKAUS) / `King's daughter of his body` (SESHSESHET IDUT). `"Royal Family"` for `King's son` only. `"Official"` for everything else non-royal (Overseer, Prophet, Inspector, Real count, Lector-priest, etc.).
- **`dynasty`** — Per mappings above.
- **`sub_period`** — `null` for all chunk-25 rows (no Saite intrusions expected; 1st Int Period gets sub_period set only if pure 1st-IP dating with no Dyn-VI co-marker).
- **`cemetery`** — Per page boundary: `"West of the Step Pyramid"` (phys pp.249-255) or `"Around the Pyramid-complex of Unis"` (phys pp.256+).
- **`attribution_certainty`** — `"attested"` default; `"probable"` for hedged headwords.
- **`shared_with_tombs`** — Empty unless PM uses sub-banner-letter form (none expected this chunk).
- **`notes_from_pm`** — Headword block prose. Per chunks 19-24 convention, drop body-prose object catalog / museum citations / cartographic refs / sub-feature room headings; preserve title cluster + dating + wife/parents clauses + topographic anchor.
- **`source_citation`** — printed = physical + 360.

## Report format

```
agent-<X>-chunk25: <count> rows; <SAQD>/<SAQE>/<SAQF>/<SAQH>/<SAQ->/<other> split; <anomalies or "none">
```

Under 100 words.
