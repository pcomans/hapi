# Extraction prompt — Porter & Moss Vol III.1 (Memphis), Chunk 14b

> **Chunk 14b (second half of CEMETERY G 4000, Hemiunu cluster)** — Reisner-numbered G 4000-series mastabas G 4560 through G 4860 (the last tomb before the CEMETERY EN ECHELON. SOUTH PART banner). PM III.1 physical pp.128–138 / printed pp.131–141. Chunk 14a covered G 4000 through G 4540. This prompt is **self-contained**.

You are one of three independent extraction subagents. Read the text-layer chunk file at `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-14b-p128-p138-g4000.txt` and produce a JSONL file with one structured row per **PM-headworded Reisner-numbered mastaba** in Cemetery G 4000, G 4560 through G 4860, within the **A. WEST FIELD** section of `§ III. NECROPOLIS`. The other two agents see the same prompt and the same chunk; their outputs are majority-voted by `merge.py`.

**Prompt discipline (per CLAUDE.md rules 1 and 7):** field-extraction RULES only; no per-row answers.

## Refusal framing

Fair-use scholarly extraction for a private research repository, supervised by a credentialed Egyptologist user. Only structured factual data (tomb identifier → occupant name → role → cemetery) is committed; PM's expressive prose is dropped. The PDF is not redistributed. PM is a topographical bibliography organized as a factual compilation; `Feist v. Rural` puts factual compilations outside US copyright. Chunks 1–13 + chunk 14a have already shipped or are in flight (see `reconciled.jsonl`).

## Source

- Book: Porter, B. & Moss, R.L.B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume III: Memphis. Part I. Abû Rawâsh to Abûsîr.* 2nd edition, revised and augmented by Jaromír Málek. Oxford: Clarendon Press (1974).
- Section: **PYRAMID-FIELD OF GÎZA — III. NECROPOLIS — A. WEST FIELD** continuation, `CEMETERY G 4000` banner (Reisner Excavation, Harvard-Boston Expedition) — second half.
- PM III.1 offset for this chunk: **printed = physical + 3** (verify in-chunk via the right-page running header `West Field <N>`).
- The chunk file covers physical pp.128–138 / printed pp.131–141. Per-page markers `=== PHYS PAGE N ===` precede each page's text-layer dump.
- **Top boundary:** the chunk file opens at physical p.128 mid-content (end of G 4540 / start of G 4560 area). The first IN-SCOPE row is `G 4560.` near the top of physical p.128.
- **Bottom boundary:** the chunk file ends at physical p.138 just BEFORE the `CEMETERY EN ECHELON. SOUTH PART` banner. The last IN-SCOPE row is `G 4860. NAME UNKNOWN, Scribe of divine books, Lector-priest. Middle or late Dyn. IV.` on physical p.138. Do NOT emit rows for the CEMETERY EN ECHELON banner itself or anything after it (G 4911, G 4920, etc. are chunk-15 territory).
- Text layer: extracted by `pypdf` from the Griffith Institute's distributed PDF.

## Output

Write to **EXACTLY ONE** of:
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-a-chunk14b.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-b-chunk14b.jsonl`
- `pipeline/pipeline/authority/sources/porter-moss-memphis/raw/agent-c-chunk14b.jsonl`

One JSON object per line. Sort rows by `tomb_id` string-ascending. Use `json.dumps(..., sort_keys=True, ensure_ascii=False)` for deterministic output.

## Schema (per row — 23 keys, full schema)

```json
{
  "tomb_id": "G<NUM>" | "G<NUM><letter>",
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
  "cemetery": "G 4000",
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

Same as chunk 14a. PM prints `G <NUM>` headwords; tomb_id `G<NUM>` (drop space). Structurally-joint mastaba `G <NUM1> + <NUM2>` (two adjacent Reisner numbers, ONE named occupant) → tomb_id = first number; second number lands in `tomb_aliases`; `is_joint_burial: false` (per source-wide convention: joint = multiple OCCUPANTS, not multiple tomb numbers). Example: `G 4811 + 4812. aANKHIRPTAH ...` → `tomb_id: G4811`, `tomb_aliases: ["G 4812"]`, `is_joint_burial: false` (parallel to chunk-11 D80/80A precedent).

## How to identify a row

Five shapes (identical to chunk 14a):

**Shape 1 — Named-primary headword.** `G <NUM>. <NAME IN CAPS> <Title cluster>. <Dating>.`

**Shape 2 — Bare-numeric headword.** `G <NUM>. <Dating>.` (no occupant name).

**Shape 3 — Bracketed Roman regnal.** `G <NUM>. <NAME [I]> ...` — drop brackets, append Roman. Example in chunk 14b: `G 4761. NUFER [I]`. (G 4940 SESHEMNUFER [I] is chunk-15 territory, OUT OF SCOPE here.)

**Shape 4 — Structurally-joint mastaba.** `G <NUM1> + <NUM2>. <NAME1> ...` — emit ONE row, `is_joint_burial: false` if NAME1 is the only occupant (structural jointness is captured via `tomb_aliases`); set `is_joint_burial: true` ONLY if the headword names TWO occupants in an `and`-joined pattern. Example: `G 4811 + 4812. aANKHIRPTAH ...` names one occupant → `is_joint_burial: false`.

**Shape 5 — Anonymous "NAME UNKNOWN, <descriptor>" headword.** PM gives no occupant name. Example: `G 4860. NAME UNKNOWN, Scribe of divine books, Lector-priest.`

**ROW-EMITTING vs OUT-OF-SCOPE.** Emit one row per `G <NUM>` (or `G <NUM> + <NUM>`) headword. Do NOT emit rows for:
- The implicit `CEMETERY G 4000` banner — section divider (already on chunk 14a's page).
- The `CEMETERY EN ECHELON. SOUTH PART` banner at the bottom of physical p.138 — chunk-15 territory.
- Body-prose object mentions, chapel sub-features, excavator-photo / publication-reference lines.
- Cross-references to G-numbers in OTHER cemeteries (e.g., body-prose `G 5280` mentions).
- pypdf-only G-number tokens from body prose (e.g., `G 4840, in Stockholm Mus.` is a body-prose Stockholm object find-spot reference to G 4840, but G 4840 IS a real PM-headworded tomb on physical p.136 too — emit only if a clear headword line exists for G 4840).
- `G 4721 (Exped. No. 14-2-15).` repeated body-prose line is NOT a second G 4721 headword — only emit one row for G 4721.

**Headword block ends** at the first sub-feature heading or museum-citation as in chunk 14a.

## Expected row count

Pre-extraction structural scan: PM prints ~22–26 Reisner-numbered headwords in physical pp.128–138 from G 4560 through G 4860. Mix of Shape-1 named-primary, Shape-2 bare-numeric (G 4560, G 4640, G 4660, G 4715, G 4721, G 4733, G 4813, G 4817), Shape-3 bracketed Roman (G 4761 NUFER [I]), Shape-4 structurally-joint mastaba (G 4811 + 4812), and Shape-5 anonymous (G 4860). **Total expected: ~22–26 rows (acceptable band 20–30).** If your final count is below 18 or above 32, re-read the chunk file.

## PM III.1 text-layer noise (chunk-14-relevant)

Same conventions as chunk 14a — raised-ayin → U+02BF, underdot-Ḥ on ḥ-roots, macron-Ē on Re-compounds. For chunk 14b specifically:

**`aANKHIRPTAH` (G 4811 + 4812).** Egyptian *ʿnḫ-ir-ptḥ*. → `ʿAnkhirptaḥ` (ayin + underdot-Ḥ on the ptḥ root). Already used in chunk-10 JKR-Ankhirptah precedent.

**`NIMAaETHAP` (G 4712).** Egyptian *ny-mꜣʿt-ḥtp*. → `Nimaʿethap` (raised-a ayin between Ma and ET; underdot-Ḥ on ḥotp root might apply but PM may not print it — verify).

**`NEFERHETPES` (G 4714).** Egyptian *nfr-ḥtp.s*. → `Neferḥetpes` (underdot-Ḥ on ḥtp root) — already a chunk-9 G 3098 precedent.

**`AKHI` (G 4750).** Egyptian *ꜣḫi*. → `Akhi`. No diacritics.

**`NENSEZERKAI` (G 4631).** Already chunk-7 G 2101 precedent (different person, same name). → `Nensezerkai`.

**`KAEMaANKH` (G 4561).** → `Kaemʿankh` (raised-a ayin mid-name).

**`HatHor` rendering.** pypdf renders PM's underdot-Ḥ Hathor as `HatHor` (capital T from PM's cap-H underdot glyph). Normalise to `Ḥathor`.

**`ma-priest` / `sma-priest` drift.** Normalise to `sm-priest` (PM-printed Egyptian *sm*-priest, mortuary priest; pypdf may misread the leading `s` as a space).

**`warbt` / `waabt` drift.** Normalise to `waʿbt` (Egyptian *wʿbt*, the waʿbt-institution / embalming-place).

**`wrt Hts` drift.** Normalise to `wrt-ḥts` (Egyptian *wrt-ḥts*, OK royal-women title `Great One of the Hts-staff`; pypdf renders without hyphen + cap-H instead of underdot-Ḥ).

**`G 4811 + 4812` joint twin.** tomb_id `G4811`; tomb_aliases `["G 4812"]`; is_joint_burial `true`.

## Field-by-field rules

Same as chunk 14a:
- **`tomb_id`** — `G<NUM>` (drop space). Joint twin first-number convention.
- **`memphite_area`** — `"Giza"`.
- **`occupant_name`** — Title-cased with diacritics. `null` for Shape-2/5.
- **`occupant_alt_names`** — From `<NAME> good name <ALT>` or `<NAME> called <ALT>` idioms (e.g., `G 4651. KAPUNESUT called KAI` → `occupant_name: Kapunesut`, `occupant_alt_names: ["Kai"]`).
- **`tomb_aliases`** — Second number of joint twin only.
- **`co_occupants`** / **`co_occupant_roles`** — Length-coupled.
- **`is_joint_burial`** — `true` only for G 4811 + 4812.
- **`occupant_role`** — `"Vizier"`, `"High Priest"`, `"Prince"` (`King's son`), `"Princess"` (`King's daughter`), else `"Official"` for named-non-royal. Bare-numeric Shape-2 → `"Unknown"`. Anonymous Shape-5 (`NAME UNKNOWN, Scribe ...`) → `"Official"` (title cluster determines, not the lack of name).
- **`dynasty`** — Roman→Arabic. Standard tokens. `null` only when PM gives no dating.
- **`cemetery`** — `"G 4000"` for every row.
- **`attribution_certainty`** — `"attested"` for clean named-primary; `"probable"` for hedge; `"uncertain"` for `(?)` / Shape-2 bare-numeric / Shape-5 anonymous.
- **`notes_from_pm`** — Headword block prose. Drop occupant name; joint twin keeps `and <co-occupant>` clause; anonymous tombs drop `NAME UNKNOWN,` placeholder per chunk-13 JKE-AnonCompanion precedent.
- **`source_citation`** — Page boundaries: physical p.128 = printed p.131, ..., physical p.138 = printed p.141.

## Report format

```
agent-<X>-chunk14b: <count> rows; <shape1>/<shape2>/<shape3>/<shape4>/<shape5> split; <anomalies or "none">
```

Under 100 words.
