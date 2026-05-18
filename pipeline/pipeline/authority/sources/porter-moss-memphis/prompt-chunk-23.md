# Extraction prompt — Porter & Moss Vol III.2, Chunk 23

> **Twenty-third chunk drawn from PM Vol III** — Ṣaqqâra § II.C EAST OF THE STEP PYRAMID. PM III.2 physical pp.215–232 / printed pp.575–592. Mixed cohort: Old Kingdom Petrie+Murray excavated D-numbered mastabas (D 45 → D 58 + F 3) + Lepsius LS-numbered tombs (LS 17 OK, LS 22 OK, LS 23 + LS 24 Saite) + the anonymous DOUBLE TOMB ABOVE MORTUARY TEMPLE OF USERKAF (Late Dyn XXVI / early Dyn XXVII). This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-23-p215-p232-east-of-step-pyramid.txt`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part 2.* 2nd edition, 1978/1981 fascicles, ed. Málek.
- Section covered: **§ II.C EAST OF THE STEP PYRAMID** (pp.575–592).
- PM III.2 offset: **printed = physical + 360**.
- Chunk file: physical pp.215–232 / printed pp.575–592.

## Output

Write to **EXACTLY ONE** of `agent-a-chunk23.jsonl` / `agent-b-chunk23.jsonl` / `agent-c-chunk23.jsonl` in the `raw/` directory. One JSON object per line, sort by `tomb_id` ascending, `json.dumps(..., sort_keys=True, ensure_ascii=False)`.

## tomb_id convention (NEW PREFIX `SAQD<N>`)

PM uses `D. <N>.` headwords for the Petrie+Murray 1952 publication's Step Pyramid East Cemetery excavation numbering. **This is NOT the same D-numbering as chunk-11's Steindorff Cemetery in Giza** (which uses tomb_id prefix `D<N>` for Steindorff Leipzig+Pelizaeus 1903-7). To disambiguate the two D-numbering schemes:

- **`SAQD<N>` for PM III.2 § II.C Petrie+Murray D-numbered mastabas** (chunk-23 NEW prefix). Drop the space from PM's `D <N>.` and prepend `SAQD`. Examples expected: `SAQD45`, `SAQD46`, ..., `SAQD58`.
- **`LS<N>` for Lepsius Saqqâra numbers** (parallel to chunk-20's LS 10 Kagemni). Examples expected: `LS17`, `LS22`, `LS23`, `LS24`.
- **`F<N>` for Petrie+Murray F-numbered mastabas** — these are a separate F-series in the same publication. Use `SAQF<N>` to keep the same SAQ prefix family. Example expected: `SAQF3` for F 3 Minnufer.
- **`SAQ-<TitleCaseName>` for anonymous / descriptor-only** tombs like the DOUBLE TOMB. Example expected: `SAQ-DoubleTombUserkaf` for the anonymous Saite intrusion above the Mortuary Temple of Userkaf.

## Cemetery field

All chunk-23 OK rows: `cemetery: "East of the Step Pyramid"` (new descriptor parallel to chunks 3/10/11/20's `"Central Field"` / `"Junker West"` / `"Steindorff"` / `"Teti Pyramid Cemetery"`). Saite rows ALSO use the same cemetery field — they sit physically in the same area, just chronologically later.

## Schema (per row — 23 keys)

```json
{
  "tomb_id": "SAQD<N>" | "SAQF<N>" | "LS<N>" | "SAQ-<Name>",
  "memphite_area": "Saqqara",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "King" | "Queen" | "Prince" | "Princess" | "Vizier" | "High Priest" | "Official" | "Royal Family" | "Unknown",
  "dynasty": "5" | "6" | "12" | "26" | "27" | null,
  "sub_period": null | "Saite" | "1st Int. Period",
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": "East of the Step Pyramid",
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

**Shape 1 — Named-primary D-numbered.** Line `D <N>. <NAME IN CAPS> <hieroglyphs>, <Title cluster>. <Dating>.`. Emit one row with `tomb_id: SAQD<N>` (e.g., `SAQD45`).

**Shape 1 — Named-primary F-numbered.** Line `F <N>. <NAME IN CAPS> ...`. Emit one row with `tomb_id: SAQF<N>`.

**Shape 1 — Named-primary LS-numbered.** Line `LS <N>. <NAME IN CAPS> ...`. Emit one row with `tomb_id: LS<N>` (no SAQ prefix — keeps parallelism with chunk-20 LS 10 Kagemni).

**Shape 1c — Bracketed alternate-numbering.** PM often prints `LS <N> [<Letter><M>]. <NAME>` where `[<Letter><M>]` is the Petrie+Murray cross-reference number. The Letter+M number goes into `tomb_aliases` (e.g., LS 17 [H 2] → tomb_aliases: ["H 2"]). Same for `D <N> [<Letter><M>]`.

**Shape 5 — Anonymous descriptor.** Block like `DOUBLE TOMB ABOVE MORTUARY TEMPLE OF USERKAF. Late Dyn. XXVI or early Dyn. XXVII.` — emit one row with `tomb_id: SAQ-DoubleTombUserkaf` (or similar TitleCase descriptor), `occupant_name: null`, `attribution_certainty: "uncertain"`, `dynasty: "26"` (Late Dyn-XXVI tail-or-early-XXVII → `"26"` per source-wide range-tail convention; sub_period: "Saite").

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per:
- Each Shape-1 (D/F/LS named-primary) headword in this page range.
- Each Shape-5 anonymous descriptor block (DOUBLE TOMB-style).

Do NOT emit rows for:
- Sub-rooms / sub-features (Façade., Room I., False-door., (N)-scene numbers).
- Body-prose mentions in sub-features (`Wife <Name>` clauses get captured as co_occupants on the parent row).
- Surface finds / object catalogs with no headworded named tomb.
- D-numbered cross-references in body prose (e.g., `D. 46. SETHU is a Middle Kingdom tomb` mentioned as a cross-reference INTO this chunk — only emit if it has its own PM headword block; if it does AND the date is MK, emit it).

**Special case: Middle Kingdom D 46 SETHU.** PM's `D 46. SETHU, King's son of his body, Count in Nekhen, ..., Middle Kingdom.` — this IS a PM-headworded tomb but dated to the Middle Kingdom (Dyn XII per source-wide convention). Emit a row with `tomb_id: SAQD46`, `dynasty: "12"` (Middle Kingdom default), `sub_period: null`.

## Expected row count

Rule-driven; do NOT use enumeration to bound row count. Chunk file spans 18 printed pages. Expected total: **~15–18 rows** (acceptable band 12–22), split roughly:
- ~12 Petrie+Murray D-numbered OK rows (Dyn V predominantly, with some Dyn VI tail and 1 Middle Kingdom D 46 SETHU).
- 1–2 LS-numbered OK rows (e.g., LS 17 Manufer Dyn V/VI).
- ~2 LS-numbered Saite rows (LS 23 Irʿaḥor, LS 24 Bekenrenef — both Saite Dyn XXVI).
- 1–2 F-numbered or descriptor rows.

If your count falls outside band 12–22, re-read the chunk file.

## PM III.2 text-layer noise (chunk-23-relevant)

**Raised-ayin.** Replace `a`/`c`/`<`/`>` raised glyphs with `ʿ` (U+02BF). Examples in this chunk: `NIKACANKH` → `Nikaʿankh`, `RACMOSI` → `Raʿmosi`, `SENENUCANKH` → `Senenuʿankh`, `IRCAHOR` → `Irʿaḥor`.

**Underdot-Ḥ.** Apply on ḥ-root names: KHNEMḤOTP → Khnemḥotp, PTAḤSHEPSES → Ptaḥshepses, PTAḤHOTP → Ptaḥhotp, NEFERIRTPTAḤ → Neferirtptaḥ, MENKAUḤOR → Menkauḥor (Re-compound but `kʿw-ḥr` root with ḥ), HATHOR → Ḥathor (single underdot), IRʿAḤOR → Irʿaḥor, SAḤUREʿ → Saḥurēʿ.

**Macron-Ē on Re-deity compounds.** `Reʿ` → `Rēʿ` always (when the `re` is the Egyptian sun-god). `RAʿNEFEREFʿANKH` → `Raʿneferefʿankh` (Re-compound `rʿ-nfr-f`-root + ayin, but the FIRST element `rʿ` per PM-convention vowel rule = `Raʿ` no macron; the Neferef element = `Neferef`; the trailing `ʿankh` = ayin). `NEFERIRKAREʿ` → `Neferirkarēʿ` (macron-Ē on Re-compound terminus). `Sun-temple of NEFERIRKARE` headword forms → `Sun-temple of Neferirkarēʿ`.

**Dating-period mappings.**
- `Temp. Userkaf` / `Temp. Saḥurēʿ` / `Temp. Neferirkarēʿ` / `Temp. Neuserrēʿ` / `Temp. Menkauḥor` / `Temp. Zadkareʿ Isesi` / `Temp. Raʿneferef` → `"5"` (Dyn V kings).
- `Temp. Teti` / `Temp. Pepy I` / `Temp. Pepy II` / `End of Dyn. V or early Dyn. VI` (range-tail) → `"6"`.
- `Dyn. V` → `"5"`. `Dyn. V or later` / `Dyn. V-VI` → `"6"` (range-tail).
- `Dyn. VI` → `"6"`. `Probably early Dyn. V` → `"5"` (+ `attribution_certainty: "probable"`).
- `Middle Kingdom` → `"12"` (Dyn XII default for MK headwords without finer dating).
- `Late Dyn. XXVI or early Dyn. XXVII` → `"26"` (range-tail-equivalent: pick the earlier full dynasty + `sub_period: "Saite"` + `attribution_certainty: "uncertain"` if PM-hedged).
- `Dyn. XXVI` → `"26"` + `sub_period: "Saite"`.
- `Temp. Necho II to Apries` → `"26"` + `sub_period: "Saite"`.
- `Temp. Psammetikhos I` → `"26"` + `sub_period: "Saite"`.

**LS / D / F cross-reference brackets.** PM prints `LS 17 [H 2]` or `D 47 [G 5]` to give the Petrie+Murray cross-reference number alongside the Lepsius/Mariette number. Capture in `tomb_aliases: ["H 2"]` / `tomb_aliases: ["G 5"]` (PM-verbatim with space).

**"good name <ALT>" idiom + `or <ALT>`** — same as chunks 8/20. Primary → `occupant_name`, alt → `occupant_alt_names`.

## Field-by-field rules

- **`tomb_id`** — Use the new prefix scheme above.
- **`memphite_area`** — Always `"Saqqara"`.
- **`occupant_name`** — Title-cased + diacritics. `null` for anonymous.
- **`tomb_aliases`** — PM bracketed cross-reference number if present.
- **`co_occupants`** / **`co_occupant_roles`** — Wife/parents body-prose clauses, PM-faithful order, length-coupled.
- **`is_joint_burial`** — `false` unless PM headword has `<NAME1> and <NAME2>` joint form.
- **`occupant_role`** — Standard controlled vocab. `Vizier` for Chief Justice and Vizier. `Royal Family` for King's son/daughter (e.g., D 46 SETHU King's son of his body). `Official` for everything else non-royal. `Unknown` for anonymous Shape-5.
- **`dynasty`** — Per mappings above.
- **`sub_period`** — `"Saite"` for Dyn XXVI, `"1st Int. Period"` for pure 1st-Int-Period rows; `null` for everything else.
- **`cemetery`** — Always `"East of the Step Pyramid"`.
- **`attribution_certainty`** — `"attested"` default, `"probable"` for `Probably <...>`, `"uncertain"` for anonymous Shape-5.
- **`notes_from_pm`** — Headword block prose; drop occupant name, hieroglyph noise, cartographic refs, sub-feature headings.
- **`source_citation`** — `{"page": <printed page>, "edition": "PM III.2 2nd ed. 1978/1981", "section": "II"}`. Use the printed page where the HEADWORD opens.

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk23: <count> rows; <SAQD>/<SAQF>/<LS>/<SAQ->/<other> split; <anomalies or "none">
```

Under 100 words.
