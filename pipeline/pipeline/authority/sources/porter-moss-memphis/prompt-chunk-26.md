# Extraction prompt — Porter & Moss Vol III.2, Chunk 26

> Continuation of § II.F AROUND THE PYRAMID-COMPLEX OF UNIS. PM III.2 physical pp.273–294 / printed pp.633–654. Same conventions as chunk 25: SAQ-/SAQD/SAQE/SAQF/SAQH/SAQ-<Name>, cemetery `"Around the Pyramid-complex of Unis"`. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-26-p273-p294-around-unis-tail.txt`.

**Source:** PM III.2 2nd ed. 1978/1981, ed. Málek. **Page offset:** printed = physical + 360.

**Output:** one JSONL line per row sorted by `tomb_id`, `json.dumps(..., sort_keys=True, ensure_ascii=False)`. Write to ONE of `raw/agent-{a,b,c}-chunk26.jsonl`.

## tomb_id convention (continuing chunk 25)

- `SAQD<N>`, `SAQE<N>`, `SAQF<N>`, `SAQH<N>` — Petrie+Murray Saqqâra letter-numbered.
- `SAQ-<TitleCaseAsciiName>` for bare-named tombs. Descriptor is ASCII-only — drop ayin/underdot/macron.

## Cemetery field

All chunk-26 rows: `cemetery: "Around the Pyramid-complex of Unis"` (continuation of chunk-25's banner). PM repeats this header as a page-margin label on every page in the chunk.

## Schema (23 keys, same as chunks 20–25)

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
  "occupant_role": "Vizier" | "High Priest" | "Official" | "Royal Family" | "Princess" | "Prince" | "Queen" | "King" | "Unknown",
  "dynasty": "5" | "6" | null,
  "sub_period": null | "1st Int. Period",
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "Around the Pyramid-complex of Unis",
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

**Shape 1 — Named D/E/F/H numbered.** `<Letter> <N>. <NAME IN CAPS>, <Title cluster>. <Dating>.`.

**Shape 1b — Bare-named.** `<NAME IN CAPS>, <Title cluster>. <Dating>.` → `tomb_id: SAQ-<TitleCaseName>`.

**Shape 1c — "or" / "good name" idiom.** Per chunks 20-25 convention.

**Shape 4 — Joint twin/family-tomb headword.** Per chunks 21-22 convention.

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per Shape-1/1b/1c/4 headword whose dating is OK or 1st Int. Period. Do NOT emit rows for:
- Sub-rooms (Room I., Burial chamber., (N)-numbered scenes).
- Body-prose object mentions / sub-feature decoration / museum-citation lines.
- Anonymous numbered shafts without a name (Shape-2 bare-suffix) unless explicit named occupants.
- Cross-reference body-prose mentions ("see above", "tomb X").

## Expected row count

Rule-driven; ~15–25 rows expected (band 10–30). The chunk spans 22 dense pages; expect mostly bare-named OK officials.

## PM III.2 text-layer noise — same rules as chunks 19–25

- Raised-ayin → U+02BF `ʿ`; ASCII descriptor drops the glyph.
- Underdot-Ḥ on ḥ-roots per source-wide convention (Ḥathor single-underdot per the 44-vs-6 majority).
- Macron-Ē on Re-deity compounds: Rēʿ, Saḥurēʿ, Neuserrēʿ, Neferirkarēʿ, Menkauḥor (no macron, kʿw-ḥr), Merenrēʿ. OCR vowel rule: capital R+E = macron; capital R+A = no macron.

## Dating mappings

- `Temp. <Dyn V king>` → `"5"`. `Temp. <Dyn VI king>` → `"6"`.
- `Temp. Unis or later` → `"5"` (Unis is Dyn V's last king; `or later` keeps within Dyn V tail).
- `Dyn. V or later` / `Dyn. V-VI` / `End of Dyn. V or Dyn. VI` → `"6"` (range-tail).
- `Dyn. VI` / `Late Dyn. VI` / `End of Dyn. VI` / `Probably <Dyn V/VI>` → `"6"` (+ probable if hedged).
- `1st Int. Period` (no Dyn-VI co-marker) → `null` + `sub_period: "1st Int. Period"`.
- `Late Dyn. VI or 1st Int. Period` / `End of Dyn. VI or 1st Int. Period` → `"6"` (range-tail) + `sub_period: null`.

## Field-by-field rules

Same as chunks 24–25. Wife/parents body-prose clauses → MUST be captured in both `co_occupants`/`co_occupant_roles` AND preserved in `notes_from_pm` (per chunks 8-25 + PR #247 Codex P2 lesson).

**`occupant_role`** — `"Vizier"` for Chief Justice and Vizier. `"Princess"` for King's daughter; `"Prince"` for King's son. `"Royal Family"` only when PM uses `Royal family` literal but no Chief-X title. `"High Priest"` for `Greatest of the craftsmen` (wr-ḫrp-ḥmwt) / `Greatest of the seers` (wr-mꜣw, High Priest of Re at Heliopolis). `"Official"` for everything else.

**`notes_from_pm`** — Headword block prose; drop body-prose object catalog / museum citations / cartographic refs / sub-feature room headings; preserve title cluster + dating + wife/parents clauses + topographic anchor.

**`source_citation`** — printed = physical + 360.

## Report format

```
agent-<X>-chunk26: <count> rows; <SAQD>/<SAQE>/<SAQF>/<SAQH>/<SAQ->/<other> split; <anomalies or "none">
```

Under 100 words.
