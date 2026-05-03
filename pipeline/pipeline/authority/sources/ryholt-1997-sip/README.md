# Ryholt 1997 — *The Political Situation in Egypt During the Second Intermediate Period*

Source of truth for the 13th–17th Dynasty king list with attested titulary, regnal years, polity assignments, and dynastic concurrency.

## Citation

Ryholt, K. S. B. (1997) *The Political Situation in Egypt During the Second Intermediate Period c. 1800–1550 B.C.* CNI Publications 20. Copenhagen: Museum Tusculanum Press. ISBN 87-7289-421-0. 466 pp.

- **Edition used:** first (and only) edition, 1997. Single printing.
- **Retrieved:** 2026-04-14 (scan via ebin.pub). The scan is OCR'd but the embedded text layer corrupts Egyptological transliteration (ꜣ→3, ꜥ→c, ḥ/ḫ→h) and conflates roman numerals with Greek letters (II→Π). Unusable as a sole source for titulary extraction.
- **PDF SHA-256:** `078c0d92bc3310c1044d4b736db6a8af9c309ef6839bd9e96b6864d200bbc972` (also pinned in `transcribe.md`).

## Scope

Two targets, both under the same transcription pipeline:

1. **Part VI — Catalogue of Attestations (pp. 333–407, ~75 pages).** Called "File 1" in the handoff doc. One entry per king in the form:
   ```
   Appellation: <name>     File <dynasty>/<sequence>
   H: <Horus name>
   D: <Nebty name>
   G: <Golden Horus name>
   P: <prenomen>
   N: <nomen> [with filiation to father]
   Turin King-list, <col>/<row>: <...>
   Attestations:
     1) …
     2) …
     …
   Remarks: …
   Notes: …
   ```
2. **Chronological Tables (pp. 408–411, ~4 pages).** Cross-dynasty concurrency diagram that grounds the `concurrent_with` field for Dyns 13–17.

Prose chapters (Part II §2.1–§2.6 on the individual dynasties) are out of scope for this source — their factual content re-surfaces in Part VI's Remarks / Notes sections, and the prose interpretation belongs in Phase A curation rather than Phase 0 raw extract.

**Expected row count:** ~60–80 king entries across Dyns 13–17 plus the Abydos Dynasty.

## Method — Claude Code subagent OCR + three-subagent structured extraction (ADR-017)

Per `docs/adr/017-ocr-pipeline-for-scan-only-sources.md`:

1. **OCR**: Claude Code subagents transcribe the PDF in physical-page chunks (1-indexed, 5 pages per chunk by default). Each chunk is written to `raw/chunk-pNNN-pMMM.md` locally. These chunk files are **not committed** — they contain Ryholt's own prose verbatim and would redistribute copyrighted material. Anyone re-running the pipeline regenerates them from the SHA-pinned PDF.
2. **Structured extraction**: three independent Claude Code subagents each read every chunk and emit JSONL per the schema below. `merge.py` deterministically majority-votes per-field and writes the final `reconciled.jsonl` plus `merge-disagreements.txt` (committed) for audit.
3. `reconciled.jsonl` rows cite the chunk's physical-page range, e.g. `source_citation: {pdf_pages: "340-344", edition: "CNI 20, 1997"}`. A reviewer verifying a row opens the PDF at physical pages 340-344 and reads the content there; the book's running-header printed-page numbers are visible on each page so scholarly cross-reference to the printed edition is trivial.
4. **Review**: the `egyptologist-reviewer` Claude Code subagent walks `merge-disagreements.txt`, cross-checks against the PDF, and flags rows where majority vote picked the wrong answer. The main agent applies the flagged corrections via an override script, recording each change in `merge-disagreements.txt` under `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED`. **This is LLM review.** A human-scholar sign-off pass against the PDF is still owed on this source and has NOT been performed — the extract is provisional until that happens (ADR-017 step 6).

The benchmark that sized this pipeline (physical p. 340, Sobkhotep I / printed p. 336) is documented in ADR-017.

### Target physical range

Physical pages **336-416** (81 pages, 17 chunks). This spans File 1 / Catalogue of Attestations (printed pp. 333-407) plus the Chronological Tables appendix (printed pp. 408-411) with generous padding at both ends to absorb offset shifts at Part boundaries.

## Schema (per handoff Source 2 spec)

```json
{
  "ryholt_id": "13.22",
  "dynasty": 13,
  "sequence_in_dynasty": 22,
  "sequence_suffix": null,
  "nomen": "Khendjer",
  "prenomen": "Woserkare",
  "horus_name_transliterated": "[...]-ꜥnḫ",
  "nebty_name_transliterated": null,
  "golden_horus_name_transliterated": null,
  "prenomen_transliterated": "wsr-kꜣ-rꜥ",
  "nomen_transliterated": "ḫ-n-d-r, var. ḫ-d-r (syllabic)",
  "date_bce_start": -1764,
  "date_bce_end": -1759,
  "polity": "Memphite",
  "concurrent_with": ["14"],
  "source_citation": {"pdf_pages": "340-344", "edition": "CNI Publications 20, Museum Tusculanum Press, 1997"}
}
```

- `ryholt_id` = `{dynasty}.{sequence}{optional-suffix}` derived from Ryholt's `File X/Y` label. Suffix is lettered (`a`, `b`) for Ryholt's appendix sub-entries.
- `dynasty` is 13-17, or `null` for `File N/...` unattributed entries.
- `nomen` / `prenomen` carry Ryholt's anglicised forms from Chronological Tables 94-98. Homonymous kings across dynasties keep Ryholt's Roman-numeral disambiguators (e.g. `"Sewadjkare (III)"` at 14.11 to distinguish from the Sewadjkare at 13.11).
- `*_transliterated` fields carry the Unicode-correct Egyptological rendering with ꜣ ꜥ ḥ ḫ etc., taken verbatim from Ryholt's File 1 `H: / D: / G: / P: / N:` lines. These are for display and for cross-reference with Beckerath 1999 / pharaoh.se; the authority layer's match/enrich path normalises them away.
- `date_bce_start` / `_end` come from Ryholt's Chronological Tables and may be absent for kings whose reigns he does not date absolutely. A row with only `date_bce_end` populated (e.g. Sewadjkare at 13.11 with `-1781`) reflects Ryholt's own single-value entry, not a data error.
- `polity` ∈ {`"Memphite"` (Dyn 13), `"Avaris"` (Dyn 14), `"Avaris (Hyksos)"` (Dyn 15), `"Theban"` (Dyns 16, 17), `"Abydos"` (Abydos Dynasty), `null` (unattributed)}.
- `concurrent_with` is a list of dynasty-number strings per Ryholt's Table 1 (Chronological/Geographical Arrangement): 13 → ["14"]; 14 → ["13", "15"]; 15 → ["16", "17", "Abydos"]; 16 → ["15", "17"]; 17 → ["15", "16"]; Abydos → ["15", "16"]; unattributed → [].

### Issue #177 schema additions (2026-05-03 audit-fix, PR #189)

The audit-fix introduced these typed fields. Every row carries every field after `fix_rows.py` runs (closure-tested by `test_every_row_has_every_schema_field`):

- `dynasty_label: str | None` — `"13" .. "17"` for numbered dynasties, `"Abydos"` for Abyd rows, `None` for truly-unattributed N/P/H/D/G rows. Replaces the convention of inferring dynasty class from `dynasty is None` + ryholt_id-prefix scrutiny.
- `attestation_class: str` — typed enum from the ryholt_id prefix. `"king"` for numbered-dynasty rows; `"abydos"` for Abyd; `"nomen_only"` / `"prenomen_only"` / `"horus_only"` / `"nebty_only"` / `"golden_horus_only"` / `"djed_only"` for the unattributed N/P/H/Nb/G/D rows. Closure-tested by `test_attestation_class_matches_ryholt_id_prefix`.
- `is_unattributed: bool` — True iff prefix is N/P/H/Nb/D/G (23 rows).
- `is_abydos_dynasty: bool` — True iff prefix is `Abyd` (8 rows).
- `is_uncertain_attribution: bool` — True for `(?)` / `(..?)` / `(...?)` uncertainty markers and bare trailing `?` in any name field (7 rows: 13.17, 13.53, 14.32, 14.g, 16.5, 17.7, Abyd.15). The marker is **KEPT** in the name string (preserved for re-derivability — PR #189 round-2 design change); the typed flag is the queryable surface.
- `is_lacunose: bool` — True for any row whose name fields contain `[...]` lacuna markers (~37 rows). Marker is KEPT in the name string (it shows position of missing characters); the flag is the typed query surface.
- `is_syllabic_nomen: bool` — True for nomen-transliterated rows in Ryholt's syllabic orthography (24 rows). Trailing `(syllabic)` is stripped where it cleanly trails; non-trailing forms (`(syllabic)⁽¹⁾`, `(syllabic), not preceded by *sꜣ-rꜥ`, `(syllabic?)`) are kept verbatim because stripping would lose the qualifier.
- `homonym_index: int | None` — Roman-numeral homonym disambiguator (4 rows: Sewadjkare I/III, Awibre II, Sankhibre II). Replaces the in-string `(I)/(II)/(III)` glyph in `nomen`; consumers querying for "all Sewadjkare kings" should join on `nomen` alone, then disambiguate via `homonym_index`.
- `date_attestation: str` — enum of `"both" | "start_only" | "end_only" | "none"`. Replaces the silent-null convention where `(start=None, end=None)` could mean "no date" OR "Ryholt couldn't reconcile single-cell entry to a range."
- `nomen_transliterated_variants: list[str]` — split from `, var. <alt>` in `nomen_transliterated` (3 rows: 13.22, 14.2, 14.4). Empty list when none.

### Display-name non-uniqueness (Shape G — documented characteristic)

`nomen` is NOT unique across the corpus — homonymous kings exist within and across dynasties. Use `(ryholt_id)` as the unique join key; for cross-source joins (pharaoh.se, Beckerath), use `(nomen, dynasty, homonym_index)` as the disambiguating composite key. The 23 unattributed N/P/H/D/G rows in particular will collide with Old Kingdom homonyms on a naive `nomen` join — Phase-A consumers must check `is_unattributed` and `dynasty_label` before treating the row as a king-record match.

## Rights

CNI Publications / Museum Tusculanum Press, in copyright. This extract contains only **factual data** — king names, regnal years, attestation locations, dynasty numbers, date ranges. Ryholt's scholarly argumentation and prose analysis are not reproduced. Per handoff rule 4 and ADR-017, the source PDF is not committed; per-page OCR markdown in `raw/` consists of transcribed data plus bibliographic references (both factual), with no chapter-body prose from Ryholt's main Parts II–V.

## Known gaps / Phase A notes

- **Anglicisation variance.** Ryholt's anglicisations (e.g. "Sobkhotep I" vs "Sobekhotep I" vs "Sobhotep I") differ from pharaoh.se and from Kitchen 1996. Phase A reconciles; Phase 0 preserves Ryholt's wording verbatim.
- **File assignments for unattributed kings.** Ryholt places some kings (especially Dyn 14) in an "unattributed" bucket at the end of the catalogue; those rows carry `dynasty: null, sequence_in_dynasty: null, ryholt_id: "unattributed.N"` and require Phase A judgment.
- **Dates that Ryholt flags uncertain.** Kings whose reign-length Ryholt records as "at least N years" or "N months" are not point-datable; `date_bce_start`/`_end` are populated only where Ryholt himself gives a bracketed BCE interval in the Chronological Tables.
- **Polity boundaries.** Ryholt distinguishes Memphis (Dyn 13 main seat), Xois (Dyn 14), Avaris (Dyn 15 — the Hyksos), Thebes (Dyn 16 and 17), and Abydos (the Abydos Dynasty). His typology underpins `polity` and differs from some older literature that treats Dyns 14 and 16 as "minor". Phase A should not flatten.
