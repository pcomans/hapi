# Extraction prompt — Porter & Moss Vol III.2 (Saqqâra-Dahshûr), Chunk 21

> **Twenty-first chunk drawn from PM Vol III** — Ṣaqqâra § II.B AROUND TETI PYRAMID, MERERUKA MEGA-BLOCK + immediate followers. PM III.2 physical pp.165–180 / printed pp.525–540. The single most-decorated OK private tomb (Mereruka, 32+ rooms, 80+ scene numbers) plus son Meryteti's chapel (sub-banner C within Mereruka's mastaba) plus the small Late-Dyn-VI / 1st-Int-Period cluster published by Firth+Gunn 1926 (Kanenebfui Khenu, Thethu, Duauḥotp, Sitinteti, Ipiʿankhu family-tomb, Khuit-khnum, plus two named Burial-No.-X occupants). This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-21-p165-p180-mereruka-meryteti-kanenebfui.txt` and produce a JSONL file with one structured row per **PM-headworded named tomb** in the chunk's page range.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data is committed; PM's expressive prose is dropped. The PDF is not redistributed. Chunks 1–20 have already shipped.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part 2.* 2nd edition, 1978/1981 fascicles, ed. Málek.
- Section covered: **§ II.B AROUND TETI PYRAMID — NORTH OF THE PYRAMID** continuation (pp.525–540).
- PM III.2 offset: **printed = physical + 360**.
- Chunk file: physical pp.165–180 / printed pp.525–540.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk21.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk21.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk21.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. `json.dumps(..., sort_keys=True, ensure_ascii=False)`.

## Schema (per row — 23 keys)

```json
{
  "tomb_id": "TPC-<TitleCaseName>",
  "memphite_area": "Saqqara",
  "occupant_name": "..." ,
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

`TPC-<TitleCaseName>` descriptor (parallel to chunk-20). Descriptor is ASCII-only — drop ayin/underdot/macron. For bracketed-Roman names (e.g. KHENU [I]), append the Roman with no space: `TPC-KhenuI`. For multi-element names with a hyphen in PM (e.g. KHUIT-KHNUM), preserve a single capital after the hyphen in the descriptor: `TPC-KhuitKhnum`. For "or <ALT>" idiom (SITINTETI or SITIN), use the longer form: `TPC-Sitinteti` (alt → `occupant_alt_names: ["Sitin"]`).

## Cemetery field assignment

All chunk-21 rows: `cemetery: "Teti Pyramid Cemetery"` (same banner as chunk 20).

## How to identify a row

**Shape 1 — Named-primary descriptor headword.** Line `<NAME IN CAPS> <hieroglyph noise> <Title cluster>. <Dating>.` — emit one row.

**Shape 1c — Sub-banner-C son row inside Mereruka mega-complex.** PM prints `C. Son <NAME IN CAPS> <hieroglyph noise> <NAME2 IN CAPS> <hieroglyph noise>, <Title cluster>. <Dating>.` for Mereruka's son's chapel (sub-banner C within the Mereruka mastaba complex). Emit this as a SEPARATE row (`tomb_id: TPC-Meryteti`) with `shared_with_tombs: ["TPC-Mereruka"]`. The son has his own Chief-Justice-and-Vizier title cluster, so this is NOT a co-occupant of the father; it's a structurally-distinct chapel-with-occupant.

**Shape 1d — Mereruka primary row.** PM's Mereruka headword on phys p.165 names the man + wife Waʿtetkhet-hor Seshseshet in the same prose block. Emit ONE row `tomb_id: TPC-Mereruka` with the wife captured as a single entry in `co_occupants` (`"Waʿtetkhet-hor Seshseshet"`) and her title cluster in `co_occupant_roles` (`"Wife, King's eldest daughter of his body"`). Do NOT emit a separate `TPC-Watetkhethor` row (she has no sub-banner of her own at the row-emission level; her chapels B are sub-features within Mereruka's mastaba).

**Shape 1e — HMK./Burial-No. prefixed headword.** PM prints `HMK. <N>. <NAME IN CAPS>, <Title cluster>. <Dating>.` (Firth+Gunn 1926 Teti Pyramid Cemetery I plot numbering) or `Burial No. <N>. <NAME IN CAPS>, <Title cluster>. <Dating>.` (the same publication's burial-shaft numbering). Both are full Shape-1 named-primary headwords — emit one row per headword. The HMK / Burial-No. number itself does NOT go in `tomb_id` (use `TPC-<Name>` descriptor as usual). Preserve the `HMK. <N>.` / `Burial No. <N>.` prefix verbatim in `notes_from_pm` as the topographic anchor.

**Shape 1f — Family-tomb headword.** PM prints `HMK. <N>. Family-tomb of <NAME IN CAPS>. <Dating>.` for shared family tombs — emit ONE row with `tomb_id: TPC-<PrimaryName>`, `notes_from_pm` preserving the `Family-tomb of ...` phrasing, and `is_joint_burial: false` (the family-tomb designation does NOT trigger joint-burial; that flag is reserved for PM `<NAME1> and <NAME2>` joint-headword form per chunk-2/11 convention). Capture multiple-occupant body-prose names in `co_occupants` if PM names them in the headword block.

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per:
- Each Shape-1 / 1c / 1d / 1e / 1f headword in this page range.

Do NOT emit rows for:
- Sub-rooms of Mereruka (Room I., Room VII., Burial chamber., (1)/(2)/(N) scene numbers, etc.) — Mereruka's mastaba has 80+ such sub-features, all rolled up into the single TPC-Mereruka row.
- Sub-rooms of Meryteti (his sub-banner C contains rooms M.I, M.II, etc.) — rolled up into TPC-Meryteti.
- Body-prose mentions of usurpers / re-users (e.g., `Burial chamber. Usurping shaft of Sitinteti, see above.` — that's a cross-reference to a separately-headworded Sitinteti, not a new row).
- Family-tomb body-prose secondary occupants without their own headword.
- Museum-citation lines, publication references.
- `False-door of <Name>` / `Statue of <Name>` / `Fragment of <Name>` references inside a larger headword block.

**Headword block ends** at the first sub-feature heading (`Room I.`, `Façade.`, `(1)`, `False-door.`, `Burial chamber.`, etc.) or at the next Shape-1/1c/1e/1f headword.

## Expected row count

Pre-extraction structural scan: ~10 rows. Chunk file spans phys pp.165–180 (Mereruka mega-block + immediate followers).

- 1 Mereruka mega-block primary row (Shape 1d).
- 1 Meryteti son sub-banner C row (Shape 1c).
- ~2 immediate-cluster Vizier-level rows (Kanenebfui Khenu [I], Thethu).
- ~6 small Late-Dyn-VI / 1st-Int-Period rows from Firth+Gunn 1926 (Duauḥotp, Ḥerimeru Burial No. 81, Sitinteti, Ipiʿankhu family-tomb, Khuit-khnum, Ptaḥemḥet Burial No. 227).

**Total expected: ~10 rows (acceptable band 8–13).** If your count falls outside that band, re-read the chunk file. Sub-rooms of Mereruka and Meryteti must NOT emit rows.

## PM III.2 text-layer noise (chunk-21-relevant)

**Raised-ayin in occupant names.** Replace `a` / `c` / `<` / `>` raised glyphs with `ʿ` (U+02BF). tomb_id descriptor is ASCII-only — drop the ayin.

**Underdot-Ḥ.** Apply on ḥ-root names per source-wide convention. Examples in this chunk:
- MERERUKA → no underdot
- WATETKHETHOR → no underdot (WAʿTETKHET-HOR is the ḫt-ḥr-name "she who is the body of Horus" — no ḥ in the name proper, only -hor which is the god name)
- MERYTETI → no underdot
- KANENEBFUI KHENU → no underdot
- THETHU → no underdot
- DUAUḤOTP → Duauḥotp (underdot on `ḥtp` root)
- ḤERIMERU → Ḥerimeru (initial underdot on `ḥry`)
- SITINTETI / SITIN → no underdot
- IPIʿANKHU → no underdot
- KHUIT-KHNUM → no underdot
- PTAḤEMḤET → Ptaḥemḥet (double underdot — `ptḥ` theophoric + `ḥt` root)

**Bracketed Roman regnal.** PM uses `[I]` / `[II]` to disambiguate same-name individuals. pypdf may render `[I]` as `[I]` correctly or as `[1]`. Normalise to Roman, drop brackets, append with NO space to descriptor (`TPC-KhenuI`) and WITH space to occupant_name (`Khenu I`).

**"or <ALT>" idiom.** PM `SITINTETI or SITIN` puts both names in the headword. Capture longer form in `occupant_name`, shorter as a single entry in `occupant_alt_names`.

**Sub-period for 1st Int. Period.** PM prints `1st Int. Period` or `Late Dyn. VI or 1st Int. Period` or `End of Dyn. VI or 1st Int. Period`. For rows where the dating is explicitly `1st Int. Period` (no Dyn VI co-marker), set `sub_period: "1st Int. Period"` and `dynasty: null`. For rows with `Late Dyn. VI or 1st Int. Period` or `End of Dyn. VI or 1st Int. Period`, set `dynasty: "6"` (Dyn-VI tail per source-wide range-tail convention) and `sub_period: null` (the Dyn-VI half wins because it's the earlier attestation window).

**HMK. plot numbering.** PM uses `HMK. <N>.` for Firth+Gunn 1926 plot numbers in Teti Pyramid Cemetery I. These are NOT Lepsius LS numbers. Do NOT extract them into tomb_id; preserve in `notes_from_pm`.

**Family-tomb single-row rule.** `Family-tomb of <NAME>` emits one row (per Shape 1f above), NOT one per body-prose secondary occupant.

## Field-by-field rules

- **`tomb_id`** — `TPC-<TitleCaseAsciiName>` always.
- **`memphite_area`** — Always `"Saqqara"`.
- **`occupant_name`** — Title-cased with diacritics applied.
- **`occupant_alt_names`** — for `or <ALT>` idiom or `[II]/[III]` regnal where alt form exists.
- **`tomb_aliases`** — Empty (no Lepsius LS cross-refs expected in this page range).
- **`co_occupants`** — Wife clause for Mereruka. Otherwise empty unless PM headword block names body-prose family members.
- **`co_occupant_roles`** — Length-coupled.
- **`is_joint_burial`** — `false` for all chunk-21 rows (family-tomb headwords do NOT trigger this flag per Shape 1f rule).
- **`occupant_role`** — `"Vizier"` for Chief Justice and Vizier (Mereruka, Meryteti, Thethu). `"Official"` for Overseer of Upper Egypt / Royal chamberlain / Inspector of King's hairdressers / Steward / Noblewoman of the King / Prophetess of Ḥathor + King's sole adorner. For 1st-Int-Period rows with priestly-only titles → `"Official"`. Use `"Royal Family"` ONLY for explicit `King's son/daughter` titles (none expected; the only royal-family connection is Waʿtetkhet-hor who appears as co_occupant of Mereruka).
- **`dynasty`** — `Temp. Teti` / `Late Dyn. VI` / `End of Dyn. VI or 1st Int. Period` / `Late Dyn. VI or 1st Int. Period` → `"6"`. `1st Int. Period` (no Dyn-VI co-marker) → `null` (+ `sub_period: "1st Int. Period"`). `Probably late Dyn. VI` → `"6"` + `attribution_certainty: "probable"`.
- **`sub_period`** — `"1st Int. Period"` for pure 1st-Int-Period rows; `null` for everything else.
- **`date_bce_*`** — `null`.
- **`cemetery`** — Always `"Teti Pyramid Cemetery"`.
- **`discovery_year`** / **`discoverer`** — `null`.
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM HEADWORD literally contains the token (Sitinteti's `Usurping shaft of Sitinteti` body-prose mention does NOT trigger `is_usurped` because that's a body-prose cross-reference, not a headword attribute).
- **`attribution_certainty`** — `"attested"` for clean Shape-1 named-primary. `"probable"` for `Probably late Dyn. VI` (RAʿWER if it lands in scope, but it doesn't here). `"uncertain"` for anonymous (none expected).
- **`shared_with_tombs`** — `["TPC-Mereruka"]` for the Meryteti son row (Shape 1c). Empty for everyone else.
- **`notes_from_pm`** — Headword block prose (title cluster + dating + wife clause + sub-banner letter + HMK./Burial-No. prefix + topographic anchor). Drop occupant name, hieroglyph-noise glyphs, `Map LII.` / `Plan LV.` cartographic refs, sub-feature headings, museum-citation lines.
- **`source_citation`** — `{"page": <printed page>, "edition": "PM III.2 2nd ed. 1978/1981", "section": "II"}`. Page = physical + 360. Use the printed page where the HEADWORD opens.

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk21: <count> rows; <shape1>/<shape1c>/<shape1d>/<shape1e>/<shape1f> split; <anomalies or "none">
```

Where shape1 = pure named-primary (Kanenebfui, Thethu, Sitinteti), shape1c = sub-banner C son (Meryteti), shape1d = Mereruka mega-primary, shape1e = HMK./Burial-No. prefixed (Duauḥotp, Ḥerimeru, Khuit-khnum, Ptaḥemḥet), shape1f = Family-tomb (Ipiʿankhu). Under 100 words.
