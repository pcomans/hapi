# Transcription method — Porter & Moss Vol III (Memphis)

Operational notes for the Phase-0 pipeline. The protocol itself lives in `docs/playbook-phase-0-ocr-transcription.md`.

## Source

- **Vol III.1** *Memphis. Part I. Abû Rawâsh to Abûsîr*, 2nd ed., 1974, ed. Málek. PDF SHA-256 `4817c0e09d126f387ffdc6793517caa125946aca1b6f4a5736a8daf32e167e58`. 349 physical pages, ~50 pages front matter (Roman) + 366 pages body + 30 plates + indexes.
- **Vol III.2** *Memphis. Part 2. Ṣaqqâra to Dahshûr*, 2nd ed., 1978/1981 fascicles, ed. Málek. PDF SHA-256 `dabb5c207642f1dd7a47de4f3db28f6c59d16ab3f0db8140c9672de3e7ed77df`. To be exercised at chunk 4+ (Saqqara work).

Both PDFs sit at `proprietary/books/` (gitignored, submodule).

## Method deviation (vs playbook step 3)

PM III PDFs carry an embedded text layer (verified 2026-05-15 for PM III.1 — `pypdf.PdfReader` produces extractable prose for every physical page sampled). Per the playbook's "Method deviation" provision and the Theban precedent (`porter-moss-theban-necropolis/transcribe.md`), the OCR subagent step is replaced by deterministic `pypdf` text-layer extraction:

```python
import pypdf
r = pypdf.PdfReader("proprietary/books/Porter & Moss - PM III Memphis.pdf")
with open("pipeline/pipeline/authority/sources/porter-moss-memphis/raw/chunk-1-p8-p32.txt", "w") as f:
    for i in range(7, 32):  # physical pages 8–32, 0-indexed
        f.write(f"\n=== physical page {i+1} ===\n")
        f.write(r.pages[i].extract_text())
```

The text-layer output goes to `raw/chunk-<n>-p<start>-p<end>.txt` (gitignored under the `raw/chunk-*.txt` pattern; same posture as Theban chunk files).

## Page-offset map (PM III.1)

The front matter consumes physical pages 1–7 (cover, half-title, title, contents i–vii). PM's printed-page numbering then begins at printed `p.1` = physical p.8 (Abû Rawâsh I. Pyramid). The offset is **`physical = printed + 7`** for the body; verify per-chunk because PM III front-matter pagination may drift (the printed contents page itself is `p.vii` in Roman but lives at physical p.5, etc.).

Page anchors confirmed via text-layer header scan (2026-05-15):

| Printed | Physical | Section |
|---|---|---|
| 11 | 8  | Pyramid-field of Gîza — I. PYRAMIDS — A. PYRAMID-COMPLEX OF KHUFU |
| 19 | 17 | B. PYRAMID-COMPLEX OF KHEPHREN |
| 27 | 24 | C. PYRAMID-COMPLEX OF MENKAUREʿ |
| 35 | 32 | (Menkaureʿ tail) → § II. GREAT SPHINX AREA |
| 49 | 46 | § III. NECROPOLIS — A. WEST FIELD (Cemetery G 1000+) |

## Pipeline

1. `pypdf` text-layer extraction → `raw/chunk-<n>-p<start>-p<end>.txt`.
2. Three parallel extraction subagents (general-purpose) run against `prompt-chunk-<n>.md` + the text-layer chunk, write `raw/agent-{a,b,c}-<chunk>.jsonl`.
3. `merge.py` — deterministic majority-vote, `tie-break-overrides.json` resolves 1/1/1 ties with a printed-source citation. Outputs `reconciled.jsonl` + `merge-disagreements.txt`.
4. `egyptologist-reviewer` subagent pass against the printed PDF pages (`reviewer-notes-chunk<n>.md`).
5. `fix_rows.py` applies reviewer corrections + post-merge normalisations to `reconciled.jsonl`.
6. `pipeline/tests/test_sources_porter_moss_memphis.py`.

## Chunk 1 scope

Physical pp.8–32 / printed pp.11–35: the three Gîza pyramid complexes (Khufu G1, Khephren G2, Menkaureʿ G3) and their attested queens' subsidiary pyramids. Expected ~8–12 rows. Establishes the `memphite_area` vocabulary and the Reisner G-number `tomb_id` convention.

PM III text-layer noise classes will accumulate from chunk 1 onwards into `postprocess.py` and per-chunk `CHUNK<N>_CORRECTIONS` tables. The Theban-source `porter-moss-theban-necropolis/postprocess.py` template carries OCR-noise rules portable to PM III where the same Griffith-Institute scan generation produced the same artifacts.

## Chunk 2 scope

Physical pp.176–187 / printed pp.179–190: Gîza Cemetery G 7000 East Field — Khufu's royal-family mastaba cluster opening with G 7000X (Hetepheres I shaft tomb, Khufu's mother) and continuing through the twin mastabas of Kawab+Hetepheres II (G 7110+7120), Khufukhaef I+Nefertkau (G 7130+7140), the Dyn-VI priestly intrusions G 7101 (Meryreanufer) and G 7102 (Iou) tied to the Pyramid-of-Pepy-I establishment, and ending with G 7150 Khufukhaef II under Neuserre. 13 rows from § III. NECROPOLIS — B. EAST FIELD.

Chunk-2 design choices:
- Twin-mastaba compound headwords like `G 7110+7120` emit TWO rows (one per Reisner number) with `shared_with_tombs` cross-reference. The compound is treated as PM's section header, not a row identifier.
- Bare-headword shafts (`G 7112.`, `G 7142.`) emit `occupant_name: null`, `occupant_role: "Unknown"`, `attribution_certainty: "uncertain"` rows. This required diverging from the Theban-source `merge.SENTINEL_NULL_STRINGS` — removing `"unknown"` from that frozenset so `"Unknown"` survives as a controlled-vocab value rather than collapsing to `None`. (The Theban source has the same latent bug — its `merge.SENTINEL_NULL_STRINGS` still includes `"unknown"`, and it papers over the issue with per-row `fix_rows.py` overrides on the (small number of) cases that surface. The Memphis approach fixes it at the merge layer instead. Future merges may consider converging the two sources on the Memphis pattern; for now they intentionally diverge.)
- Cemetery designation `"G 7000"` (formerly `null` in chunk 1) introduced for the East Field mastabas. PM's `CEMETERY G 7000` banner on printed p.182 sets the designation for the entire B. EAST FIELD section.
- The G 7000X Hetepheres I headword opens with a `1/1/1` tie on `notes_from_pm` (three agents truncated the headword block at three different sentence boundaries). Resolved via `tie-break-overrides.json` with a printed-source citation (PM III.1 p.179).

Chunk file text-layer SHA-256 pin: `886973b5663e748f282bb6147cc36d88e98f1f7fb43cda8ab46304cebeb4aa69`.

## Chunk 3 scope

Physical pp.285–289 / printed pp.288–292: Gîza Central Field — LG 100 Khentkaus I (the "Sarcophagus-shaped Tomb", End of Dyn IV or early Dyn V queen-mother) closing § III. E. CENTRAL FIELD Old-Kingdom block, then the Saite (Dyn XXVI) LG-numbered cluster: LG 81 (bare-headword anonymous, OCR-drift `LG 8 I` form), LG 83 (joint burial — Commander ʿAhmosi + his mother Queen Nekhtubasterau, wife of Amasis), LG 84 (Pakap, good name Wehebreʿ-emakhet), LG 97 (joint burial — Harsiesi + Harwoz, both wnrw-priests). 5 rows total.

Chunk-3 design choices:
- First LG-prefix tomb_id rows (Lepsius "Grab" numbering). Extends `merge.AREA_ORDER` with `"LG": 1` (sorts after Reisner G but within the same Gîza memphite_area).
- First joint-burial rows: `co_occupants` non-empty + `is_joint_burial: true`. LG 83 and LG 97 establish the schema for shared-tomb cases.
- First `sub_period` non-null rows: Saite-era Dyn XXVI carries `sub_period: "Saite"`. Old Kingdom rows in this chunk (LG 100) keep `sub_period: null`.
- First `cemetery: "Central Field"` rows (chunk-1 was `null` for pyramid-complexes; chunk-2 was `"G 7000"` for East Field).
- New OCR-drift rule for Saite raised-ayin: pypdf renders PM's Late-Period raised-ayin glyph as a literal `c` (in contrast to the chunks 1-2 raised-`a` for Old Kingdom names). LG 84's `WEHEBREc-EMAKHET` → `Wehebreʿ-emakhet` after U+02BF normalisation. A 1/1/1 tie on the three agents' variants resolved via `tie-break-overrides.json` with a cited PM III.1 p.290 rationale.
- LG-number OCR drift: pypdf renders `LG 81` as `LG 8 I` (Arabic 1 → Roman I with inserted space). The chunk-3 prompt's normalisation rule re-reads the Roman-block as Arabic.
- Out-of-scope no-LG-number tombs (THAIHARPATA, PEDUBASTE, PTAHARDAIS): each Saite-era tomb without a Lepsius / Reisner / Mariette identifier. Deferred to a follow-up chunk with the descriptor-tomb-id scheme (e.g. `CF-Thaiharpata`).

Chunk file text-layer SHA-256 pin: `83c4c224ca022c9e62a5563d1535a35e7ff3240d80cab6b5769306678abda8e7`.

## Chunk 4 scope (FIRST PM III.2 chunk)

Physical pp.61–72 / printed pp.421–432 of PM III.2 (Saqqâra-Dahshûr): the back half of § I. PYRAMIDS at Saqqâra — the Dyn V/VI royal pyramid-complexes from F. Unis (Dyn V's last king) through K. Pepy II (Dyn VI's longest-reigning king), plus Pepy II's three queens' pyramid-enclosures (Neit, Iput II, Wezebten) and the anonymous Wife-of-Isesi queen-enclosure under H. 9 rows total: 5 kings + 4 queens.

Chunk-4 design choices:
- First chunk drawn from PM Vol III.2 (not III.1). Introduces `edition: "PM III.2 2nd ed. 1978/1981"` alongside chunks 1-3's `PM III.1 2nd ed. 1974`.
- First `memphite_area: "Saqqara"` rows (chunks 1-3 were all `Giza`).
- First `SAQ-`-prefix descriptor-form `tomb_id`s (machine-readable identifiers in `SAQ-<DescriptorName>` shape, e.g. `SAQ-Unis`, `SAQ-PepyII`, `SAQ-WifeOfIsesi`). Saqqâra pyramids lack a uniform Reisner-style or Lepsius-style numeric ID — the descriptor synthesises from the section's named royal occupant.
- `tomb_id` descriptors stay ASCII-only (no U+02BF ayin in identifiers — `SAQ-MerenreI`, NOT `SAQ-MerenrʿI`). The U+02BF ayin lives in `occupant_name` (`Merenrʿ I` per the 2/1 majority strict-rule normalisation; egyptologist-reviewer may post-process to the conventional `Merenreʿ I` form via fix_rows.py CHUNK4_CORRECTIONS).
- Extends `merge.AREA_ORDER` with `"SAQ": 2` (sorts after Reisner `G` and Lepsius `LG` numbered forms).
- New `pre_merge.py` mechanism for PM Memphis (cloned from D&H queens PR #218 precedent): `tomb_id_corrections-<chunk>.json` files apply OCR-drift tomb_id fixes BEFORE merge so a singleton-rejected mis-OCR'd row routes back into the canonical majority. Chunk-4 uses this for Agent B's `IPUT [II]¹` → `IPUT Il1` → `IPUT` mis-OCR and for Agent B's U+02BF-in-descriptor non-conformance on `MerenreI`.
- New `tomb_aliases` content: Saqqâra pyramids carry Arabic popular-names appended to their Lepsius identification line (e.g. Isesi's `Haram el-Shawwaf` — "the Sentinel Pyramid"). Extracted into `tomb_aliases` per the chunk-4 prompt's alias rule.
- Three new `tie-break-overrides.json` entries for chunk-4 1/1/1 ties on `notes_from_pm` (SAQ-IputII, SAQ-Neit, SAQ-MerenreI — agents disagreed on period-before-PYRAMID sentence-boundary preservation + raised-ayin normalisation).
- Out-of-scope `J. PYRAMID OF KAKAREʿ IBI` (Dyn VIII transitional king on printed p.426) — explicitly excluded from chunk 4 per the prompt's OUT-OF-SCOPE rule. Regression-pin in `test_chunk4_no_jay_kakare_ibi_row` guards against accidental inclusion.

Chunk file text-layer SHA-256 pin: `7c2a4a712c4419eb2b479c2f0e07a7ee350ad68989af2a08dbc17a16678916e3`.
