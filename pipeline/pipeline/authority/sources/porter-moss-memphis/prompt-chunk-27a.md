# Extraction prompt — Porter & Moss Vol III.2, Chunk 27a

> **Twenty-seventh chunk (front half) drawn from PM Vol III** — Ṣaqqâra § II.A NORTH OF THE STEP PYRAMID, sub-section `OLD KINGDOM TOMBS NOS. I-88 OF MARIETTE` (front half). PM III.2 physical pp.88–108 / printed pp.448–468. This is the famous Mariette numbered series at North Saqqâra — Mariette excavated 88 OK mastabas north of the Step Pyramid and assigned sequential numbers Nos. 1–88 (with a secondary letter-code classification `[A]`, `[B]`, `[C]`, `[D]`, `[E]`). The headword **Ti's tomb (Mariette No. 60 [D 22])** sits at the boundary of this chunk and the next; this front-half chunk stops at No. 59. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-27a-p88-p108-mariette-ok-front.txt`.

**Source:** PM III.2 2nd ed. 1978/1981, ed. Málek. **Page offset:** printed = physical + 360.

**Output:** one JSONL line per row sorted by `tomb_id`, `json.dumps(..., sort_keys=True, ensure_ascii=False)`. Write to ONE of `raw/agent-{a,b,c}-chunk27a.jsonl`.

## tomb_id convention (NEW prefix: `MAR<N>`)

Primary tomb_id for Mariette numbered tombs Nos. 1–88:
- `MAR<N>` where `<N>` is the Mariette sequential number (e.g. `MAR1`, `MAR6`, `MAR60`).
- PM's bracketed letter-classification (e.g. `[B 5]`, `[C 15]`, `[D 22]`) goes into `tomb_aliases`, formatted as the literal PM string `"<letter> <num>"` (e.g. `"B 5"`, `"C 15"`, `"D 22"`).
- Compound bracketed forms like `[A 2; S 3073]` go in `tomb_aliases` as TWO entries: `["A 2", "S 3073"]`.
- Sub-cluster S-numbered tombs at the top of phys p.88 (S 3510, S 3511 KAIḤAP, S 3513 ITISEN, S 3514, S 3518) belong to the PRECEDING sub-section `S 2146-3518`. **Do NOT emit rows for the S 3510-3518 cluster** — those are part of chunk 28's scope (PM TOC: `Early Dynastic and Old Kingdom tombs S 2146-3518` printed pp.436-447).

**Start banner:** `OLD KINGDOM TOMBS NOS. I-88 OF MARIETTE` (chunk file ~line 27 in extracted text).
**End boundary:** stop AT (do not include) Mariette No. 60 TY — Ti's tomb is a mega-block whose body spans phys pp.108–117, deferred to chunk-27b. Emit rows ONLY for Nos. 1–59.

## Cemetery field

All chunk-27a rows: `cemetery: "North of the Step Pyramid"` (per PM § II.A banner; matches the TOC sub-section heading).

## Schema (23 keys, same as chunks 20–26)

```json
{
  "tomb_id": "MAR<N>",
  "memphite_area": "Saqqara",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": ["<letter-code>", "S <S-num>"],  // PM bracketed forms
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "Vizier" | "High Priest" | "Official" | "Royal Family" | "Princess" | "Prince" | "Queen" | "King" | "Unknown",
  "dynasty": "3" | "4" | "5" | "6" | null,
  "sub_period": null | "1st Int. Period",
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "North of the Step Pyramid",
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

**Shape 1 — Standard Mariette numbered.** `No. <N> [<letter-code>]. <NAME IN CAPS>, <Title cluster>. <Dating>.`
- The Mariette number may be Roman (`No. I [B 5].`) or Arabic (`No. 6 [C 15].`) — OCR drift from PM's old-style typography. Normalise to Arabic in `tomb_id` (`MAR1`, `MAR6`).
- Compound bracketed codes: `No. 5 [A 2; s 3073].` → tomb_aliases `["A 2", "S 3073"]`. The `s` (lowercase) in OCR output is PM's "S " prefix.
- The bracketed-Roman pattern `<NAME> [I]` / `<NAME> [II]` after the name (e.g. `No. 58 [E 6]. SNEFRUNUFER [I]`) indicates ordinal-numbering when PM has multiple individuals with the same name — preserve in `occupant_name` as `"Snefrunufer [I]"` (chunks 11/15/17 bracketed-Roman precedent).

**Shape 4 — Joint twin / family-tomb headword.** When PM prints two names in the headword (`No. 5 KHAʿBAUSOKAR ... and wife NEFERḤOTEP-ḤATḤOR`), use the PRIMARY name as `tomb_id` and set `is_joint_burial: true`, with the secondary name in `co_occupants` and their role in `co_occupant_roles`.

**Shape 1c — "or" / "good name" idiom.** When PM prints `IFEFI ... FEFI` (No. 2) with a second name in caps and no relational connector, that's PM's "good name <ALT>" idiom (Egyptian *rn nfr*): primary is `occupant_name`, the alt goes in `occupant_alt_names`. Per chunks 8-25 source-wide convention.

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per Shape-1 / 1c / 4 headword whose dating is OK (Dyn III, IV, V, VI), 1st Int. Period, or pre-OK Late Dyn III/early Dyn IV. Do NOT emit rows for:
- Sub-rooms (Chapel., Burial chamber., Room I., Niche., (N)-numbered scenes).
- Body-prose object mentions / sub-feature decoration / museum-citation lines.
- Cross-reference body-prose "No. <N>" mentions like "see No. 205" — only the literal `No. <N> [<bracketed-code>]. <NAME>` headword form is row-emitting.
- The S 3510-3518 cluster at the top of phys p.88 (belongs to preceding sub-section).
- No. 60 TY (Ti's tomb) — defer to chunk-27b.

## Expected row count

Rule-driven; ~30–55 rows expected (band 25–60). The chunk spans 21 dense pages and Mariette skipped some numbers (No. 11 may be absent, etc.). PM has gaps in the sequence (e.g., `No. 17` may or may not appear — emit only what PM prints as a headword). Re-read the chunk file if your count falls outside the band 25–60.

## PM III.2 text-layer noise — same rules as chunks 19–26

- Raised-ayin → U+02BF `ʿ`; ASCII descriptor drops the glyph.
- Underdot-Ḥ on ḥ-roots per source-wide convention (Ḥathor single-underdot per the 44-vs-6 majority).
- Macron-Ē on Re-deity compounds: Rēʿ, Saḥurēʿ, Neuserrēʿ, Neferirkarēʿ, Menkauḥor (no macron, kʿw-ḥr), Merenrēʿ. OCR vowel rule: capital R+E = macron; capital R+A = no macron.
- OCR `<` and `>` and `(` artifacts around ayin glyphs — normalise to `ʿ`.
- OCR `\1` `~` `}` etc. between the Roman ordinal and the title are hieroglyphic-cartouche garbage from PM's inline cartouche-typography. Strip; preserve only the romanized name and titles.

## Dating mappings

- `Temp. <Dyn V king>` → `"5"`. `Temp. <Dyn VI king>` → `"6"`.
- `Probably Dyn. V` / `Probably Dyn. VI` → `"5"` / `"6"` + `attribution_certainty: "probable"`.
- `Dyn. V or later` → `"6"` (range-tail convention).
- `Middle Dyn. III to early Dyn. IV` → `"4"` (range-tail; mid-range late Dyn III + early Dyn IV → settle on `"4"`).
- `Late Dyn. IV or early Dyn. V` → `"5"` (range-tail).
- `Late Dyn. V` / `Middle Dyn. V` / `Early Dyn. V` → `"5"`.
- `Dyn. V-VI` → `"6"` (range-tail).
- `1st Int. Period` (no Dyn-VI co-marker) → `null` + `sub_period: "1st Int. Period"`.

## Field-by-field rules

Same as chunks 24–26. Wife/parents body-prose clauses → MUST be captured in BOTH `co_occupants` / `co_occupant_roles` AND preserved in `notes_from_pm` (per chunks 8-26 + PR #247/248 Codex P2 lesson). `co_occupant_roles` MUST be `<Relation>, <title>` (e.g. `"Wife, Prophetess of Ḥathor"`), NOT `"Official"`.

**`occupant_role`** — `"Vizier"` for Chief Justice and Vizier. `"Princess"` for King's daughter; `"Prince"` for King's son. `"Queen"` for King's wife / King's principal wife. `"Royal Family"` only when PM uses `Royal family` literal but no Chief-X title. `"High Priest"` for `Greatest of the directors of craftsmen` (wr-ḫrp-ḥmwt) / `Greatest of the seers` (wr-mꜣw) / `Greatest of the physicians`. `"Official"` for everything else.

**`tomb_aliases`** — Mariette's bracketed letter-code (e.g. `[D 22]` for Ti) goes here. Format: PM-literal string `"<letter> <num>"` (single space, no period). When PM prints multiple bracketed codes separated by `;` (e.g. `[A 2; S 3073]`), each becomes its own array entry.

**`notes_from_pm`** — Headword block prose; drop body-prose object catalog / museum citations / cartographic refs / sub-feature room headings; preserve title cluster + dating + wife/parents/king-cult clauses + topographic anchor. Keep PM-literal capitalization on king names (Saḥurēʿ, Neuserrēʿ, etc.).

**`source_citation`** — printed = physical + 360.

## Report format

```
agent-<X>-chunk27a: <count> rows; <MAR-numeric-range>; <anomalies or "none">
```

Under 100 words.
