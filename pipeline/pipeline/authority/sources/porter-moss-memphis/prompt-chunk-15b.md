# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 15b

> **Chunk 15b (second half of CEMETERY EN ECHELON. SOUTH PART)** — Reisner-numbered G-series mastabas G 5232 through G 5560. PM III.1 physical pp.154–165 / printed pp.157–168. Chunk 15a covered G 4911 → G 5230. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-15b-p154-p165-en-echelon-south.txt` and produce a JSONL file with one structured row per **PM-headworded Reisner-numbered mastaba** in Cemetery en Echelon South Part (G 5232 → G 5560). The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–14 + chunk 15a have already shipped or are in flight (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — A. WEST FIELD** continuation, `CEMETERY EN ECHELON. SOUTH PART` banner — second half.
- PM III.1 offset for this chunk: **printed = physical + 3**.
- The chunk file covers physical pp.154–165 / printed pp.157–168. Per-page markers `=== PHYS PAGE N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens at physical p.154. The first IN-SCOPE row is `G 5232.` near the top of physical p.154.
- **Bottom boundary:** the chunk file ends at physical p.165 just BEFORE the `CEMETERY G 6000` banner. The last IN-SCOPE row is `G 5560. KAKHERPTAH good name FETEKTA ...` on physical p.163. Do NOT emit rows for the `CEMETERY G 6000` banner itself or anything after it (G 6010, G 6014, G 6020, etc. are chunk-16 territory).
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk15b.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk15b.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk15b.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — 23 keys, full schema)

```json
{
  "tomb_id": "G<NUM>",
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
  "cemetery": "Cemetery en Echelon South",
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

## How to identify a row

Same Five shapes as chunk 15a / chunks 7/8/14. For chunk 15b specifically:

**Shape 1 — Named-primary.** Most common. Example pattern: `G 5270. RAaWER [I] ...`, `G 5280. PEHENPTAH ...`.

**Shape 2 — Bare-numeric.** Examples in chunk 15b: G 5232, G 5245, G 5332, G 5350, G 5482.

**Shape 3 — Bracketed Roman regnal.** Examples in chunk 15b: G 5270 RAaWER [I], G 5470 RAaWER [II] (pypdf may render `[II]` as `[11]`). Drop brackets, append Roman with space in occupant_name: `Rēʿwer I`, `Rēʿwer II`.

**Shape 4 — Joint-named twin headword.** None expected in chunk 15b.

**Shape 5 — Anonymous "NAME UNKNOWN, <descriptor>" headword.** None expected in chunk 15b.

**ROW-EMITTING vs OUT-OF-SCOPE.** Same as chunk 15a. Do NOT emit for `CEMETERY G 6000` banner or G 6010+ headwords (chunk-16).

**Headword block ends** at sub-feature headings as in chunk 15a.

## Expected row count

Pre-extraction structural scan: PM prints ~14–17 Reisner-numbered headwords in physical pp.154–165 from G 5232 through G 5560. Mix of Shape-1 named-primary + Shape-2 bare-numeric (G 5232, G 5245, G 5332, G 5350, G 5482) + 2 Shape-3 bracketed Roman (G 5270 RAaWER [I], G 5470 RAaWER [II]). **Total expected: ~14–17 rows (acceptable band 12–20).** If your final count is below 10 or above 22, re-read the chunk file.

## PM III.1 text-layer noise (chunk-15b-relevant)

Same source-wide conventions as chunk 15a — raised-ayin → U+02BF, underdot-Ḥ on ḥ-roots, macron-Ē on Re-compounds. For chunk 15b specifically:

**`RAaWER` (G 5270, G 5470).** Egyptian *rʿ-wr* — Re-deity compound. Apply macron-Ē + ayin → `Rēʿwer`. With Roman regnal: `Rēʿwer I` (G 5270), `Rēʿwer II` (G 5470).

**`SaANKHENPTAH` (G 5520).** Egyptian *sʿnḫ-n-ptḥ*. Apply raised-a ayin → `Sʿankhenptaḥ` (also underdot-Ḥ on the ptḥ root).

**`HETEPNIPTAH` (G 5290).** Egyptian *ḥtp-n-ptḥ*. Apply underdot-Ḥ on both ḥ-roots → `Ḥetepniptaḥ`. Chunk-9 / chunk-10 precedent for this name form.

**`SHEPSESKAFaANKH` (G 6040 — chunk-16, listed for cross-reference only; out of scope for chunk 15b).** Already a chunk-16 example for the same `<NAME>aANKH` raised-ayin pattern.

**`SESHETHOTP called HETI` (G 5150 is chunk-15a — listed for cross-reference).**

**`BABAF (sometimes called Khnembaf)` (G 5230 is chunk-15a; listed here as form reference for chunk-15b similar idioms.)**

**`NUFER good name IDU [I]` (G 5550).** Apply chunk-3 / chunk-8 `good name` idiom: `occupant_name: Nufer`, `occupant_alt_names: ["Idu I"]` (drop brackets on the Roman regnal).

**`KAKHERPTAH good name FETEKTA` (G 5560).** Same `good name` idiom: `occupant_name: Kakherptaḥ` (underdot on ptḥ root), `occupant_alt_names: ["Feteḳta"]` (or `Fetekta` without underdot — verify per PM headword; chunk-13 JKE-Meruka's father was `Kakherptah` per chunk-13 reconciled.jsonl — same name root, same underdot convention).

**Hereditary prince / Royal-family controlled vocab.** PM `Hereditary prince` is an OK rank title (Egyptian *iry-pʿt*) carried by both royal kin and high officials. Default to `"Royal Family"` ONLY if PM also says `King's son of his body` or similar; otherwise `"Official"`.

**`wrt Hts` / `warbt` / `ma-priest` / `sma-priest` drift.** Source-wide normalisations per chunk 14 conventions.

**Page boundaries:** physical p.154 = printed p.157, ..., physical p.165 = printed p.168.

## Field-by-field rules

Same as chunk 15a. cemetery = `"Cemetery en Echelon South"` for every row.

## Report format

```
agent-<X>-chunk15b: <count> rows; <shape1>/<shape2>/<shape3>/<shape4>/<shape5> split; <anomalies or "none">
```

Under 100 words.
