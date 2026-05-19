# Extraction prompt — Porter & Moss Vol III.2, Chunk 29

> **Twenty-ninth chunk drawn from PM Vol III** — Ṣaqqâra § II.H AROUND PYRAMIDS OF PEPY I, MERENRĒʿ I, ISESI + § II.I AROUND PYRAMIDS OF IBI AND PEPY II + MASTABET FARAʿUN. PM III.2 physical pp.311–328 / printed pp.671–688. Late OK officials clustered around the late-Dyn-V and Dyn-VI royal pyramids of South Saqqâra: priestly clientele of Pepy I/Merenrēʿ I/Isesi (§ II.H), then Ibi (Dyn VIII transitional), Pepy II, and the queens' enclosures Neit / Iput II / Wezebten (§ II.I). Dating skews Late Dyn V → Dyn VI → End of Dyn VI → 1st Int. Period. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-29-p311-p328-ibi-pepy2.txt`.

**Source:** PM III.2 2nd ed. 1978/1981, ed. Málek. **Page offset:** printed = physical + 360.

**Output:** one JSONL line per row sorted by `tomb_id`, `json.dumps(..., sort_keys=True, ensure_ascii=False)`. Write to ONE of `raw/agent-{a,b,c}-chunk29.jsonl`.

## tomb_id convention

Bare-named OK officials use the `SAQ-<TitleCaseAsciiName>` descriptor form (chunks 22/25/26/28 convention).

Royal-family tombs in sub-banner enclosures inherit context (Neit/Iput II/Wezebten queen-enclosures: any tombs INSIDE these are already covered by chunk-4 SAQ-Neit, SAQ-IputII, SAQ-Wezebten — do NOT re-emit those; only emit private named tombs INSIDE the enclosure).

Joint-burial twin headwords use Shape-4 convention: primary occupant + secondary in `co_occupants` + `is_joint_burial: true`. Example: `Tombs of IBI ... Dyn. VI (destroyed), ḤENENI ... Tenant of the Pyramid of Isesi(?), etc., Dyn. VI, and tomb re-used by MENTUḤOTP ... Dyn. XI or XII.` — this is a Shape-4 IBI+ḤENENI joint headword; tomb_id `SAQ-IbiHeneni`, co_occupants=["Ḥeneni"]. The Mentuḥotp re-use clause is a MK intrusion — note in notes_from_pm but do NOT emit a separate row.

## Cemetery field

All chunk-29 rows in § II.H sub-section: `cemetery: "Around Pyramids of Pepy I, Merenrēʿ I, and Isesi"`.
All chunk-29 rows in § II.I sub-section: `cemetery: "Around Pyramids of Ibi and Pepy II"`.
The exact section banner determines the cemetery field. Sub-sub-banners (WEST OF PYRAMID OF PEPY I, AROUND PYRAMID OF IBI, NORTH-EAST OF PYRAMID OF PEPY II, etc.) are topographic anchors preserved in `notes_from_pm`, not cemetery values.

## Schema (23 keys, same as chunks 20–28)

```json
{
  "tomb_id": "SAQ-<Name>",
  "memphite_area": "Saqqara",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "Vizier" | "High Priest" | "Official" | "Royal Family" | "Princess" | "Prince" | "Queen" | "King" | "Unknown",
  "dynasty": "5" | "6" | null,
  "sub_period": null | "1st Int. Period",
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "Around Pyramids of Pepy I, Merenrēʿ I, and Isesi" | "Around Pyramids of Ibi and Pepy II",
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

**Shape 1 — Named OK.** `<NAME IN CAPS>, <Title cluster>. <Dating>.` → tomb_id `SAQ-<TitleCaseName>`.

**Shape 1b — Bracketed sub-letter (Pepy II adjacent finds).** Some sub-section entries are `(a) <name>, <title>.` / `(b) <name>, <title>.` (e.g. line 400 `(a) Niḥebsed-pepy ... Coffin-fragment`, `(b) Idi, Lector-priest. Offering-text from lid of wooden rectangular coffin`). These are OBJECT findspots from un-attributed tombs — do NOT emit rows for these; they're sub-section object catalogs, not tomb headwords.

**Shape 4 — Joint twin/family-tomb headword.** Per chunks 21-22/28 convention.

**Shape 5 — Anonymous tomb with sub-letter format.** `(a) Penu`, `(b) Senti`, `(c) ...` where multiple named individuals are listed under a single tomb-context banner. If they share a single tomb (e.g., MASTABA N.II with multiple owners), use primary-name tomb_id; if they're separate findspots under "VARIOUS FINDS", do not emit.

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per Shape-1 / 4 headword whose dating is OK (Dyn V/VI) or 1st Int. Period. Do NOT emit rows for:
- Sub-rooms (Chapel., Burial chamber., Room I., (N)-numbered scenes).
- Body-prose object findspots / museum-citation lines / cartographic refs.
- `FINDS FROM NEAR PYRAMIDS OF PEPY I AND MERENRĒʿ I` sub-banner (line ~144) — loose-object catalog.
- `VARIOUS FINDS. Dyn. VI to 1st Int. Period` sub-banner (line ~219) — loose-object catalog.
- Late Period intrusions: `NEBRĒʿ ... Late Period.` (line ~215) — out of MVP scope.
- MK re-use clauses in joint headwords (mention in notes only, do not emit MK rows).
- Cross-reference body-prose tomb mentions ("see No. <N>").

## Expected row count

Rule-driven; ~15–30 rows expected (band 12–35). The chunk spans 18 dense pages with multiple sub-banners. Re-read the chunk file if your count falls outside the band 12–35.

## PM III.2 text-layer noise — same rules as chunks 19–28

- Raised-ayin → U+02BF `ʿ`; ASCII descriptor drops the glyph.
- Underdot-Ḥ on ḥ-roots per source-wide convention (Ḥathor single-underdot per the 44-vs-6 majority).
- Macron-Ē on Re-deity compounds: Rēʿ, Saḥurēʿ, Neuserrēʿ, Neferirkarēʿ, Menkauḥor (no macron), Merenrēʿ. OCR vowel rule: capital R+E = macron; capital R+A = no macron.
- OCR `<` and `>` and `(` artifacts around ayin glyphs — normalise to `ʿ`.

## Dating mappings

- `Temp. Isesi` → `"5"` (end of Dyn V).
- `Temp. Pepy I`, `Temp. Merenrēʿ I`, `Temp. Pepy II` → `"6"`.
- `Probably Dyn. VI` → `"6"` + `attribution_certainty: "probable"`.
- `Late Dyn. V or Dyn. VI` → `"6"` (range-tail).
- `End of Dyn. VI` / `Late Dyn. VI` → `"6"`.
- `End of Dyn. VI or 1st Int. Period` → `"6"` (range-tail) + `sub_period: null`.
- `1st Int. Period` alone → `null` + `sub_period: "1st Int. Period"`.
- `Dyn. VI to 1st Int. Period` (banner-only, not row-emitting).
- `Neferkarēʿ of Dyn. VII or VIII` — borderline. If a row's headword cites this king specifically (Dyn VIII transitional king Neferkarēʿ III between Pepy II and 1st Int.), treat as `null` + `sub_period: "1st Int. Period"` per the 1st-Int. convention.

## Field-by-field rules

Same as chunks 24–28. Wife/parents body-prose clauses → MUST be captured in BOTH `co_occupants` / `co_occupant_roles` AND preserved in `notes_from_pm`. `co_occupant_roles` MUST be `<Relation>, <title>` (e.g. `"Wife, Tenant of the Pyramid of Merenrēʿ I, etc."`), NOT `"Official"`.

**`occupant_role`** — `"Vizier"` for Chief Justice and Vizier. `"Princess"` for King's daughter; `"Prince"` for King's son. `"Queen"` for King's wife. `"High Priest"` for `Greatest of the directors of craftsmen` / `Greatest of the seers` / `Greatest of the physicians`. `"Official"` for everything else.

**`notes_from_pm`** — Headword block prose; drop body-prose object catalog / museum citations / cartographic refs / sub-feature room headings. PRESERVE the sub-sub-banner topographic anchor (e.g. `North-east of Pyramid of Pepy II.`) as the leading sentence to disambiguate location.

**`source_citation`** — printed = physical + 360.

## Report format

```
agent-<X>-chunk29: <count> rows; <H-section>/<I-section> split; <anomalies or "none">
```

Under 100 words.
