# Extraction prompt — Porter & Moss Vol III.2 (Saqqâra-Dahshûr), Chunk 12

> **Twelfth chunk drawn from PM Vol III** — and the third PM III.2 (Saqqâra) chunk. Closes the back-back half of **§ I. PYRAMIDS** that chunks 4 (sections F-K) and 5 (sections A-E) left open: sections **L–N**. Three royal complexes total: L. Burial-complex of Shepseskaf (Dyn IV, the famous Mastabat Faraoun), M. Pyramid-enclosure of Userkareʿ Khenzer (Dyn XIII), N. Pyramid-enclosure of Dynasty XIII (anonymous, southern). Same shape as chunks 4 + 5 — small royal-complex chunk; 3 rows total. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-12-p73-p76.txt` and produce a JSONL file with one structured row per **section-letter royal complex** in PM III.2 § I.L, I.M, I.N. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (occupant identifier → role → dynasty) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–10 have already shipped (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part II. Ṣaqqâra to Dahshûr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1978/1981).
- Section: **§ I. PYRAMIDS — sections L–N** (Saqqâra Dyn-IV + Dyn-XIII royal complexes; chunks 4-5 covered § I.A-K).
- PM III.2 offset for this chunk: **printed = physical + 360** (verify via right-page running header `$AQQARA -PYRAMIDS` or `Pyramid-enclosure of <Name> <N>`).
- The chunk file covers physical pp.73–76 / printed pp.433–436. Per-page markers `=== PHYS PAGE N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens with `L. BURIAL-COMPLEX OF SHEPSESKAF` (file pre-trimmed before).
- **Bottom boundary:** the chunk file ends just before the `II. Necropolis` (the next major PM section) banner. Pre-trimmed.
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk12.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk12.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk12.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — 23 keys, full schema)

```json
{
  "tomb_id": "SAQ-<DescriptorName>",
  "memphite_area": "Saqqara",
  "occupant_name": "..." | null,
  "occupant_alt_names": [],
  "tomb_aliases": [],
  "co_occupants": [],
  "co_occupant_roles": [],
  "is_joint_burial": false,
  "occupant_role": "King" | "Queen" | "Unknown",
  "dynasty": "4" | "13",
  "sub_period": null,
  "date_bce_approx_start": null,
  "date_bce_approx_end": null,
  "cemetery": null,
  "discovery_year": null,
  "discoverer": null,
  "is_unfinished": false,
  "is_uninscribed": false,
  "is_usurped": false,
  "attribution_certainty": "attested" | "uncertain",
  "shared_with_tombs": [],
  "notes_from_pm": "..." | null,
  "source_citation": {"page": <int>, "edition": "PM III.2 2nd ed. 1978/1981", "section": "I"}
}
```

## tomb_id convention

Per chunk-4/5 SAQ- descriptor convention (no Reisner G-number / Mariette D-number / Lepsius LG for these royal pyramid complexes). Each section-letter L/M/N produces ONE row with `tomb_id: SAQ-<KingOrDescriptorName>`:
- L: PM headword `L. BURIAL-COMPLEX OF <KING NAME>` → tomb_id `SAQ-<KingName>` (title-cased, ASCII only — drop ayin/underdot/macron from the descriptor; they live in `occupant_name`).
- M: PM headword `M. PYRAMID-ENCLOSURE OF <KING NAME>` → tomb_id `SAQ-<KingName>`.
- N: PM headword `N. PYRAMID-ENCLOSURE OF DYNASTY XIII` (anonymous — no king name) → synthesise tomb_id from whatever qualifying adjective PM prints in the headword block after `PYRAMID-ENCLOSURE OF DYNASTY XIII`. If PM gives a geographic adjective (e.g., "southern", "northern"), append the leading letter to the descriptor: `SAQ-DynXIII<Letter>`. If PM gives no qualifying adjective, use `SAQ-DynXIIIAnon`. Parallel to chunk-5's anonymous `SAQ-GreatEnclosure` descriptor convention.

## How to identify a row

This is a small chunk: ONE row per section letter (L, M, N).

**Section L — Burial-complex of Shepseskaf.** PM identifies the Dyn IV king Shepseskaf's tomb as a sarcophagus-shaped mastaba (NOT a pyramid; the well-known Arabic alias `Mastabat el-Faraʿun` / `Mastabet Faraʿun` = "Bench of the Pharaoh" identifies the structure). PM section letter L is the standalone identifier within PM III.2 § I. `occupant_role: "King"`, `dynasty: "4"`. Notes: include section heading + Dyn dating + any Lepsius / Mariette cross-reference clauses PM prints in the section-letter headword block (capture each verbatim — do not invent or omit any).

**Section M — Pyramid-enclosure of Userkareʿ Khenzer.** Dyn XIII king. `occupant_role: "King"`, `dynasty: "13"`. PM section letter M. Capture any Lepsius cross-reference PM prints verbatim.

**Section N — Pyramid-enclosure of Dynasty XIII (anonymous).** No occupant name in PM headword. `occupant_name: null`, `occupant_role: "Unknown"` (parallel to chunk-5's anonymous Great Enclosure precedent which used `Unknown`), `attribution_certainty: "uncertain"`, `dynasty: "13"`. Capture any Lepsius cross-reference PM prints verbatim.

## Expected row count

**Total expected: exactly 3 rows** (L + M + N). Each is a single royal complex per PM section-letter. If your final count is below 2 or above 5, re-read the chunk file — § I.L-N is a small, well-defined cluster.

## PM III.2 text-layer noise (chunk-12-relevant)

**Macron-Ē + ayin on Re-deity compound names.** PM uses macron-Ē + ayin for Re-compound royal names (per chunks 4 + 8 precedent: Merenrēʿ I, Meryrēʿ-Meryptaḥʿankh, Saḥurēʿ, etc.). For § M's Dyn-XIII king `USERKAREʿ KHENZER`, PM prints `USERKARE< KHENZER` in the text-layer (text-layer renders raised-ayin glyph as `<` here per the M section heading line). Normalise to `Userkareʿ Khenzer` (ayin + ASCII Khenzer). The pypdf rendering may also show `Userkarer Khenzer` (raised-`r` for ayin). Per source-wide convention, all → `Userkareʿ`.

**Arabic-name aliases.** PM occasionally prints Arabic place-name aliases (e.g., the well-known `Mastabat el-Faraʿun` for Shepseskaf's tomb, or `Mastabet Faraʿun`). Capture these in `tomb_aliases` as the conventional English transliteration form.

**Lepsius cross-references.** PM prints `Lepsius, <Roman-numeral>` (e.g., `Lepsius, XLIII`) as a cross-reference. Capture this in `tomb_aliases` as `["LG <N>"]` per chunk-3 / chunk-8 precedent — but only if PM gives a clean Lepsius Grab number; if PM only mentions `Lepsius, <Roman>` without LG-number, retain it in `notes_from_pm` verbatim and leave `tomb_aliases` empty.

**Mariette D-numbers as cross-references.** PM occasionally prints `Mariette, D <N>` (Mariette's Saqqâra mastaba catalog number — distinct from the chunk-11 Steindorff `D. <N>` Gîza Cemetery numbers, which are unrelated). When PM prints such a Mariette cross-reference within a section-letter sub-structure prose, capture it verbatim in `notes_from_pm`; do NOT use the Mariette number as a `tomb_id`-form (it's a cross-reference within a section-letter complex, not the primary ID).

## Field-by-field rules

- **`tomb_id`** — `SAQ-<DescriptorName>` ASCII-only descriptor.
- **`memphite_area`** — Always `"Saqqara"`.
- **`occupant_name`** — Title-cased with ayin/macron-Ē applied to royal names. `null` for the anonymous N section.
- **`occupant_alt_names`** — Empty `[]` unless PM gives an explicit alternative-name clause.
- **`tomb_aliases`** — Capture Arabic place-name aliases and Lepsius-LG numbers here.
- **`co_occupants`** / **`co_occupant_roles`** — Empty `[]` for typical rows (royal pyramids have no headword-level co-occupants).
- **`is_joint_burial`** — `false`.
- **`occupant_role`** — `"King"` for L (Shepseskaf) and M (Userkareʿ Khenzer); `"Unknown"` for N (anonymous Dyn XIII).
- **`dynasty`** — `"4"` for Shepseskaf (Dyn IV); `"13"` for Userkareʿ Khenzer + anonymous Dyn XIII pyramid.
- **`sub_period`** / **`date_bce_*`** — `null`.
- **`cemetery`** — `null` for pyramid complexes (the complex IS the cemetery; parallel to chunks 4 + 5).
- **`discovery_year`** / **`discoverer`** — `null`.
- **`is_unfinished`** / **`is_uninscribed`** / **`is_usurped`** — `false` unless PM HEADWORD literally contains the token.
- **`attribution_certainty`** — `"attested"` for L and M (PM gives the king-name explicitly); `"uncertain"` for N (anonymous).
- **`shared_with_tombs`** — Empty.
- **`notes_from_pm`** — Verbatim PM headword block prose: section letter + complex-type + king-name + dating + Lepsius/Mariette cross-references + Arabic alias. Publication-citation ribbon dropped. Per chunks 4–10 convention, the OCCUPANT NAME is dropped from notes (already in `occupant_name`); royal-name aliases captured separately.
- **`source_citation`** — `{"page": <int>, "edition": "PM III.2 2nd ed. 1978/1981", "section": "I"}`. Use the printed page (physical + 360 offset; verify against the right-page running header).

## Report format

After writing the JSONL file, return ONE LINE in this format:

```
agent-<X>-chunk12: <count> rows; L/M/N section letters all covered (<yes/no>); <anomalies or "none">
```

Under 80 words.
