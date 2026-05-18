# Extraction prompt — Porter & Moss Vol III.2 (Saqqâra-Dahshûr), Chunk 22

> **Twenty-second chunk drawn from PM Vol III** — Ṣaqqâra § II.B AROUND TETI PYRAMID continuation. PM III.2 physical pp.181–200 / printed pp.541–560. Old Kingdom named tombs of Teti-clientele priests + the Firth+Gunn 1926 LATE DYN. VI AND 1ST INT. PERIOD FINDS cluster + (intentionally excluded) the MIDDLE KINGDOM FINDS sub-banner. The famous **RAʿWER** mastaba (Chief Justice and Vizier, name erased in PM, Probably late Dyn VI) sits near the end of this chunk. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-22-p181-p200-teti-rawer-cluster.txt` and produce a JSONL file with one structured row per **PM-headworded named Old Kingdom tomb** in the chunk's page range.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data is committed; PM's expressive prose is dropped. The PDF is not redistributed. Chunks 1–21 have already shipped.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part 2.* 2nd edition, 1978/1981 fascicles, ed. Málek.
- Section covered: **§ II.B AROUND TETI PYRAMID — NORTH OF THE PYRAMID** continuation (pp.541–560).
- PM III.2 offset: **printed = physical + 360**.
- Chunk file: physical pp.181–200 / printed pp.541–560.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk22.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk22.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk22.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. `json.dumps(..., sort_keys=True, ensure_ascii=False)`.

## Schema (per row — 23 keys)

Same 23-key schema as chunks 20–21. New per-row vocabulary in this chunk: `sub_period: "1st Int. Period"` for pure 1st-Int-Period rows.

```json
{
  "tomb_id": "TPC-<TitleCaseName>",
  "memphite_area": "Saqqara",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "King" | "Queen" | "Prince" | "Princess" | "Vizier" | "High Priest" | "Official" | "Royal Family" | "Unknown",
  "dynasty": "5" | "6" | null,
  "sub_period": null | "1st Int. Period",
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "Teti Pyramid Cemetery",
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

## tomb_id convention

`TPC-<TitleCaseName>` descriptor (parallel to chunks 20–21). Descriptor is ASCII-only — drop ayin/underdot/macron. For bracketed-Roman regnal (e.g. RAʿWER [I]), append the Roman with no space: `TPC-RawerI`. For "or <ALT>" idiom, use the longer form. For "(erased)" / "(name partly lost)" annotations, ignore in the descriptor — they live in notes.

## Cemetery field assignment

All chunk-22 rows: `cemetery: "Teti Pyramid Cemetery"` (same banner as chunks 20–21).

## How to identify a row

**Shape 1 — Named-primary descriptor headword.** Line `<NAME IN CAPS> <hieroglyph noise> <Title cluster>. <Dating>.` — emit one row.

**Shape 1e — HMK./Burial-No. prefixed headword.** PM prints `HMK. <N>. <NAME IN CAPS> <hieroglyph noise> <Title cluster>. <Dating>.` (Firth+Gunn 1926 plot numbering) or `Burial No. <N>. <NAME IN CAPS> <Title cluster>. <Dating>.` (their burial-shaft numbering). Both are full Shape-1 headwords — emit one row per headword. Preserve the `HMK. <N>.` / `Burial No. <N>.` prefix verbatim in `notes_from_pm`.

**Shape 5 — Erased-name headword.** PM prints `<NAME> (erased), <Title cluster>. <Dating>.` when the name still survives in the source but was destroyed on the monument (e.g., RAʿWER damnatio memoriae). Emit a normal Shape-1 row with the name in `occupant_name`, the `(erased)` annotation preserved in `notes_from_pm`, and `is_usurped: false` (erasure ≠ usurpation; it's damnatio memoriae). For attribution_certainty: `"attested"` if PM still gives a confident name; `"probable"` if PM hedges (`Probably <Name>`); `"uncertain"` if PM gives only fragments.

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per:
- Each Shape-1 / Shape-1e / Shape-5 headword in this page range whose dating is **Old Kingdom or 1st Int. Period only** (specifically: Dyn V, Dyn VI, Late Dyn VI, End of Dyn VI, 1st Int. Period, Late Dyn VI or 1st Int. Period, End of Dyn VI or 1st Int. Period, Probably late Dyn VI, Early Dyn V, Probably early Dyn VI).

Do NOT emit rows for:
- Anything under the **MIDDLE KINGDOM FINDS** sub-banner (phys p.190+, printed p.550+). Middle-Kingdom tombs are out of scope for this chunk; they land in a future chunk with the post-OK Memphite vocabulary expansion.
- Sub-rooms (Room I., Burial chamber., False-door., (N)-numbered scenes, etc.).
- Body-prose object mentions (`Statue of <Name>`, `Fragment of <Name>`), museum-citation lines, publication references.
- The "LATE DYN. VI AND 1ST INT. PERIOD FINDS" sub-banner itself (it's a structural label, not a headword) — but emit rows for the named tombs UNDER that banner.

**Headword block ends** at the first sub-feature heading or museum-citation line or next Shape-1/1e/5 headword.

## Expected row count

Rule-driven — do NOT use this section as an enumeration of expected names. The chunk file spans phys pp.181–200 (20 printed pages). PM's headword density in the AROUND TETI PYRAMID continuation is roughly 1 named tomb per 1.5 printed pages, so a 20-page chunk yields **roughly 10–18 rows** before the Middle Kingdom cutoff. Re-read the chunk file if your count falls outside the band 8–22.

The chunk file's main structural anchors:
- Continuation of NORTH OF THE PYRAMID sub-section (early pages, Dyn V/VI named tombs).
- LATE DYN. VI AND 1ST INT. PERIOD FINDS sub-banner (mid-chunk, several small Firth+Gunn 1926 publications).
- MIDDLE KINGDOM FINDS sub-banner (cuts to MK; rows EXCLUDED from this chunk).
- Resumption of OK named-tomb sequence after the MK insert (RAʿWER mastaba, ʿAKHPET, others).

## PM III.2 text-layer noise (chunk-22-relevant)

**Raised-ayin in occupant names.** Replace `a` / `c` / `<` / `>` raised glyphs with `ʿ` (U+02BF). tomb_id descriptor is ASCII-only — drop the ayin.

**Underdot-Ḥ.** Apply on ḥ-root names per source-wide convention:
- KAEMḤEST → Kaemḥest (underdot on `ḥst` root)
- PEḤERNUFER → Peḥernufer (underdot on `pḥrr` root)
- KAEMSENU → Kaemsenu (no ḥ)
- RAʿWER → Raʿwer (no ḥ)
- ʿAKHPET → ʿAkhpet (no ḥ)
- HATHOR → Ḥathor (underdot)

**Macron-Ē on Re-deity-compound names.** `REa` / `RE<` → `Rēʿ`; `RAa` / `RA<` → `Raʿ`.

**`(erased)` annotation.** When PM prints `<NAME> (erased), <Title cluster>.` — the `(erased)` is PM's textual note that the name was destroyed on the monument but PM has reconstructed it from secondary sources. Capture the name in `occupant_name`, preserve `(erased)` in `notes_from_pm`. `is_usurped: false`.

**Sub-period for 1st Int. Period.** Same rule as chunk 21:
- `1st Int. Period` (no Dyn VI co-marker) → `sub_period: "1st Int. Period"`, `dynasty: null`.
- `Late Dyn. VI or 1st Int. Period` / `End of Dyn. VI or 1st Int. Period` → `dynasty: "6"`, `sub_period: null` (Dyn-VI tail per range-tail convention).

**HMK. plot numbering.** Same as chunk 21: preserve `HMK. <N>.` / `Burial No. <N>.` prefix in `notes_from_pm`; do NOT extract into tomb_id.

**"Wife, <NAME>" / "Parents, <NAME> and <NAME>" body-prose preservation.** Same as chunks 9–21 — capture in `co_occupants` + role string.

## Field-by-field rules

- **`tomb_id`** — `TPC-<TitleCaseAsciiName>`.
- **`memphite_area`** — Always `"Saqqara"`.
- **`occupant_name`** — Title-cased with diacritics applied.
- **`occupant_alt_names`** — for "good name <ALT>" / `or <ALT>` idiom.
- **`tomb_aliases`** — Empty.
- **`co_occupants`** — Wife/parents body-prose names. Apply diacritics.
- **`co_occupant_roles`** — Length-coupled.
- **`is_joint_burial`** — `false`.
- **`occupant_role`** — `"Vizier"` for Chief Justice and Vizier (RAʿWER and similar). `"High Priest"` for Greatest of the craftsmen (wr-ḫrp-ḥmwt, High Priest of Ptaḥ at Memphis) — none expected here but watch for it. `"Official"` for King's architect / Chief lector-priest / Prophet of Reʿ in Sun-temple / Royal acquaintance / Tenant of the Pyramid / Inspector of prophets etc. `"Royal Family"` only for `King's son/daughter`.
- **`dynasty`** — `Dyn. V or VI` → `"6"` (range-tail). `Probably early Dyn. VI` → `"6"`. `Probably late Dyn. VI` → `"6"`. `1st Int. Period` (pure) → `null` (+ `sub_period: "1st Int. Period"`). `Late Dyn. VI or 1st Int. Period` → `"6"`. `Early Dyn. V` → `"5"`. `Temp. Teti` / `Temp. Pepy I` / `Temp. Pepy II` → `"6"`. `Temp. Userkaf` / `Temp. Sahurēʿ` / `Temp. Neuserrēʿ` / `Temp. Zadkareʿ Isesi` → `"5"`.
- **`sub_period`** — `"1st Int. Period"` for pure 1st-Int-Period rows; `null` for everything else.
- **`date_bce_*`** — `null`.
- **`cemetery`** — Always `"Teti Pyramid Cemetery"`.
- **`discovery_year`** / **`discoverer`** — `null`.
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM HEADWORD literally contains the token. `(erased)` does NOT trigger `is_usurped`.
- **`attribution_certainty`** — `"attested"` for clean Shape-1 named-primary. `"probable"` for `Probably <Dating>` headword dating or `Probably <Name>` hedged-name. `"uncertain"` for fragmentary / anonymous rows (none expected).
- **`shared_with_tombs`** — Empty for all chunk-22 rows (no sub-banner shared-mastaba cases expected).
- **`notes_from_pm`** — Headword block prose (title cluster + dating + family clauses + topographic anchor). Drop occupant name, hieroglyph-noise glyphs, sub-feature headings, museum-citation lines.
- **`source_citation`** — `{"page": <printed page>, "edition": "PM III.2 2nd ed. 1978/1981", "section": "II"}`. Page = physical + 360.

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk22: <count> rows; <shape1>/<shape1e>/<shape5> split; <anomalies or "none">
```

Where shape1 = pure named-primary, shape1e = HMK./Burial-No. prefixed, shape5 = erased-name. Under 100 words.
