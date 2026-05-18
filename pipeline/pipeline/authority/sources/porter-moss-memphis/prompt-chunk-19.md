# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 19

> **Nineteenth chunk drawn from PM Vol III** — Gîza § III.B EAST FIELD trailing rock-cut + § III.C CEMETERY G I S + § III.D QUARRY CEMETERY WEST OF SECOND PYRAMID. PM III.1 physical pp.211–226 / printed pp.214–229. Mixed cohort: 3 trailing East Field rock-cut tombs without numbers (KAWEHEM, INKAF, NEFERKA — use `EF-<Name>` descriptor convention) + Cemetery G I S named tombs (LG 53, 54, 55) + Quarry Cemetery LG 11, 12, 13. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-19-p211-p226-east-trailing-and-gis.txt` and produce a JSONL file with one structured row per **PM-headworded named tomb** in the chunk's page range. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data is committed; PM's expressive prose is dropped. The PDF is not redistributed. Chunks 1–18 have already shipped.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I.* 2nd edition, 1974.
- Sections covered: end of **§ III.B EAST FIELD** rock-cut sub-cluster (pp.214–215) + **§ III.C CEMETERY G I S** (pp.216–227) + start of **§ III.D QUARRY CEMETERY WEST OF SECOND PYRAMID** (pp.228–229).
- PM III.1 offset: **printed = physical + 3**.
- Chunk file: physical pp.211–226 / printed pp.214–229.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk19.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk19.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk19.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. `json.dumps(..., sort_keys=True, ensure_ascii=False)`.

## Schema (per row — 23 keys)

```json
{
  "tomb_id": "EF-<Name>" | "LG<N>",
  "memphite_area": "Giza",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "King" | "Queen" | "Prince" | "Princess" | "Vizier" | "High Priest" | "Official" | "Royal Family" | "Unknown",
  "dynasty": "4" | "5" | "6" | null,
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "G 7000" | "Cemetery G I S" | "Quarry Cemetery",
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "is_uninscribed": false,
  "is_usurped": false,
  "attribution_certainty": "attested" | "probable" | "uncertain",
  "shared_with_tombs": [],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}
}
```

## tomb_id convention

**`EF-<TitleCaseName>` for trailing EAST FIELD rock-cut named tombs without numbers** (KAWEHEM, INKAF, NEFERKA on printed pp.214–215). Parallel to chunk 10's `JKR-` / chunk 13's `JKE-` / chunk 11's `STN-` descriptor conventions. Descriptor is ASCII-only — drop ayin/underdot/macron from descriptor (apply them in occupant_name only).

**`LG<N>` for LG-numbered tombs** (LG 53, LG 54, LG 55 in CEMETERY G I S; LG 11, LG 12, LG 13 in QUARRY CEMETERY). Drop space from PM's `LG <N>`. Precedent: chunks 3 + 18.

## Cemetery field assignment

- `cemetery: "G 7000"` for the 3 EAST FIELD rock-cut tombs (KAWEHEM, INKAF, NEFERKA — continuation of the CEMETERY G 7000 East Field banner from chunks 2/17/18).
- `cemetery: "Cemetery G I S"` for LG 53, LG 54, LG 55 (§ III.C banner).
- `cemetery: "Quarry Cemetery"` for LG 11, LG 12, LG 13 (§ III.D QUARRY CEMETERY WEST OF SECOND PYRAMID banner).

## How to identify a row

**Shape 1 — Named-primary descriptor headword.** Line `<NAME IN CAPS> <Title cluster>. <Dating>.` (no preceding `G <NUM>.` / `LG <N>.` prefix). For trailing EAST FIELD rock-cut tombs: `tomb_id: EF-<TitleCaseName>`. Title-case the name with diacritics. Examples expected: KAWEHEM, INKAF, NEFERKA.

**Shape 1 — Named LG-headword.** Line `LG <N>. <NAME IN CAPS> <Title cluster>. <Dating>.` — same as chunk 18. `tomb_id: LG<N>`.

**Shape 3 — Bracketed-Roman LG headword.** Line `LG <N>. <NAME> [I]/[II]/[III] <title cluster>` — pypdf may render `[II]` as `[11]`. Drop brackets and append Roman with space to occupant_name (e.g., `Niʿankhrēʿ II`).

**Shape 5 — Anonymous LG-headword.** Line `LG <N>. NAME LOST, <descriptor>. <Dating>.` — `occupant_name: null`, `attribution_certainty: "uncertain"`. Examples expected: LG 11 NAME LOST Prophetess of Hathor; LG 13 NAME LOST Sole companion.

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per:
- Each Shape-1 EAST FIELD descriptor headword (KAWEHEM, INKAF, NEFERKA).
- Each Shape-1 / Shape-3 / Shape-5 LG headword in this page range.

Do NOT emit rows for:
- Anonymous rock-cut sub-features that PM lists WITHOUT a name or LG number (e.g., "Rock-cut tomb. Position uncertain." on its own).
- Body-prose object mentions, museum-citation lines, publication references.
- Chapel sub-features (Room I., I. Entrance Room., V. Outer Hall., False-door., etc.).
- Plan / Synopsis references.

**Headword block ends** at the first sub-feature heading or museum-citation line.

## Expected row count

Pre-extraction structural scan: **4 EAST FIELD** rock-cut descriptor tombs (KAWEHEM, INKAF, NEFERKA, ITHER — the prompt-auditor verifies every Shape-1 descriptor headword in the chunk file is named here) + 3 CEMETERY G I S LG-named (LG 53, LG 54, LG 55) + **4 QUARRY CEMETERY LG** (LG 10, LG 11, LG 12, LG 13). **Total expected: 11 rows (acceptable band 9–13).** If your count falls outside that band, re-read the chunk file — you've either missed an LG-numbered tomb or emitted an anonymous-rock-cut body sub-feature out of scope.

## PM III.1 text-layer noise (chunk-19-relevant)

**Raised-ayin in occupant names.** Replace mid-name or leading raised-`a`/`c`/`'` glyphs with `ʿ` (U+02BF). tomb_id descriptor is ASCII-only.

**Underdot-Ḥ glyph.** Apply on ḥ-root names per source-wide convention: HATHOR → Ḥathor, NEBEMAKHET → Nebemakhet (no ḥ), HETEPHERES → Ḥetepḥeres (double underdot), KAWEHEM → no ḥ. NEFERKA → no ḥ. INKAF → no ḥ.

**Macron-Ē on Re-deity-compound names.** `NIaANKHREa` → `Niʿankhrēʿ` (Re-compound). `SaHurea` → `Saḥurēʿ` (Re-compound + ḥ-root). OCR vowel rule: `REa` → `Rēʿ` (macron); `RAa` → `Raʿ` (no macron).

**Bracketed Roman regnal pypdf drift.** `[II]` may render as `[11]`; `[IV]` may render as `[IV]` correctly or as `[Iv]`. Normalise back to Roman.

**`waab-priest` / `wad-priest` drift.** Source-wide ayin-normalisation: `waab` or `wad` → `waʿb`.

**"Wife, <NAME>" body-prose preservation.** Per chunks 9-18 convention — capture wife in `co_occupants` + her title cluster in `co_occupant_roles` (`"Wife, <title>"` form). Preserve `, etc.` markers.

## Field-by-field rules

- **`tomb_id`** — `EF-<TitleCaseName>` for trailing EAST FIELD descriptor tombs (ASCII, no diacritics); `LG<N>` (drop space) for LG-numbered.
- **`memphite_area`** — Always `"Giza"`.
- **`occupant_name`** — Title-cased with diacritics applied. `null` for Shape-5 NAME LOST anonymous.
- **`tomb_aliases`** — Empty.
- **`co_occupants`** — Wife, parents per body-prose clauses. PM-faithful order. Apply diacritics.
- **`co_occupant_roles`** — Length-coupled. `"Wife, <title>"`, etc.
- **`is_joint_burial`** — `false` for all chunk-19 rows (no joint-named twins expected).
- **`occupant_role`** — Controlled vocab. `"Vizier"` for Chief Justice and Vizier. `"Prince"` for King's son. `"Princess"` for King's daughter. `"High Priest"` for Greatest of the ḥm-nṯr / Greatest of the craftsmen (wr-ḫrp-ḥmwt = High Priest of Ptah at Memphis) / chief of the .... `"Prophet of <X>"` alone is NOT `High Priest` — generic priestly title → `"Official"`. Most named tombs → `"Official"`. Shape-5 anonymous → `"Unknown"` (or `"Official"` if PM gives an occupational title cluster despite anonymous name; e.g., LG 11 NAME LOST `Prophetess of Hathor` → `"Official"` since `Prophetess` is a title; her `Prophetess` is captured but role is `Official` not `Unknown`).
- **`dynasty`** — Roman→Arabic. `Dyn. V` → `"5"`, `Dyn. VI` → `"6"`, `Dyn. V-VI` → `"6"` (range tail), `Temp. Khephren to Menkaurēʿ` → `"4"` (start of range).
- **`sub_period`** / **`date_bce_*`** — `null`.
- **`cemetery`** — Per assignment above: `"G 7000"` for EF- descriptor tombs (printed pp.214-215), `"Cemetery G I S"` for the 3 LG tombs after the `C. CEMETERY G I S` banner (printed pp.216-227), `"Quarry Cemetery"` for LG 11-13 after the `D. QUARRY CEMETERY WEST OF SECOND PYRAMID` banner (printed p.228+).
- **`discovery_year`** / **`discoverer`** — `null`.
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM HEADWORD literally contains the token.
- **`attribution_certainty`** — `"attested"` for clean Shape-1 / Shape-3. `"uncertain"` for Shape-5 NAME LOST.
- **`shared_with_tombs`** — Empty.
- **`notes_from_pm`** — Headword block prose (title cluster + dating + parents/wife clauses). Drop occupant name, `Rock-cut tomb.` / `Stone-built mastaba.` body trailers, `Plan ...` references, sub-feature headings, museum-citation lines.
- **`source_citation`** — `{"page": <printed page>, "edition": "PM III.1 2nd ed. 1974", "section": "III"}`. Page boundary rule: printed = physical + 3.

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk19: <count> rows; <shape1>/<shape3>/<shape5> split; <anomalies or "none">
```

Where shape1 = named-primary (EF- + LG-named), shape3 = bracketed-Roman LG, shape5 = NAME LOST anonymous. Under 100 words.
