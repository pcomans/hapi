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

## Method — Gemini OCR + human spot-check (ADR-017)

Per `docs/adr/017-ocr-pipeline-for-scan-only-sources.md`:

1. `fetch.py --pages 333-411` runs **Gemini 3.1 Pro preview** in 5-page batches on the target printed-page range.
2. Per-page output lands directly in `raw/page-NNN.md` — one file per page, committed as the canonical OCR.
3. The transcriber spot-checks a sample of ~5 pages against the PDF (focused on titulary diacritics, dates, File N/M labels) and makes any corrections inline in the affected `raw/page-NNN.md` with a short comment.
4. `reconciled.jsonl` is derived from the committed `raw/page-NNN.md` files.

The benchmark that sized this pipeline (p. 336, Sobkhotep I) is documented in ADR-017: Gemini 3.1 Pro correctly rendered every Egyptological transliteration character on a representative titulary page; Mistral and Gemini 3 Flash did not. The earlier plan for a two-model Claude + Gemini cross-check was dropped once it became clear that model disagreements clustered on bibliographic details outside the extraction schema.

## Schema (per handoff Source 2 spec)

```json
{
  "ryholt_id": "13.17",
  "dynasty": 13,
  "sequence_in_dynasty": 17,
  "appellation": "Khendjer",
  "horus_name": "Djedkheperu",
  "nebty_name": null,
  "golden_horus_name": null,
  "prenomen": "Userkare",
  "nomen": "Khendjer",
  "nomen_transliterated": "hnḏr",
  "father_name": null,
  "regnal_years_attested": "at least 4 years 3 months",
  "date_bce_start": -1764,
  "date_bce_end": -1759,
  "polity": "Memphite",
  "concurrent_with": [],
  "source_citation": {"page": 340, "edition": "CNI Publications 20, Museum Tusculanum Press, 1997"}
}
```

- `ryholt_id` = `{dynasty}.{zero-padded sequence}` derived from Ryholt's `File X/Y` label.
- Egyptological transliteration fields (`*_transliterated`) carry the Unicode-correct rendering with ꜣ ꜥ ḥ ḫ etc.
- Anglicised display-style names (`appellation`, `horus_name`, `prenomen`, `nomen`) use Ryholt's own anglicisation where he provides one, and are null where he does not.
- `date_bce_start` / `_end` come from Ryholt's Chronological Tables and may be absent for kings whose reigns he does not date absolutely.
- `polity` ∈ {`Memphite`, `Xois`, `Theban`, `Avaris (Hyksos)`, `Abydos`, null}.
- `concurrent_with` lists Ryholt's dynasty numbers as strings (e.g. `["14", "15"]`) per the concurrency diagram.

## Rights

CNI Publications / Museum Tusculanum Press, in copyright. This extract contains only **factual data** — king names, regnal years, attestation locations, dynasty numbers, date ranges. Ryholt's scholarly argumentation and prose analysis are not reproduced. Per handoff rule 4 and ADR-017, the source PDF is not committed; per-page OCR markdown in `raw/` consists of transcribed data plus bibliographic references (both factual), with no chapter-body prose from Ryholt's main Parts II–V.

## Known gaps / Phase A notes

- **Anglicisation variance.** Ryholt's anglicisations (e.g. "Sobkhotep I" vs "Sobekhotep I" vs "Sobhotep I") differ from pharaoh.se and from Kitchen 1996. Phase A reconciles; Phase 0 preserves Ryholt's wording verbatim.
- **File assignments for unattributed kings.** Ryholt places some kings (especially Dyn 14) in an "unattributed" bucket at the end of the catalogue; those rows carry `dynasty: null, sequence_in_dynasty: null, ryholt_id: "unattributed.N"` and require Phase A judgment.
- **Dates that Ryholt flags uncertain.** Kings whose reign-length Ryholt records as "at least N years" or "N months" are not point-datable; `date_bce_start`/`_end` are populated only where Ryholt himself gives a bracketed BCE interval in the Chronological Tables.
- **Polity boundaries.** Ryholt distinguishes Memphis (Dyn 13 main seat), Xois (Dyn 14), Avaris (Dyn 15 — the Hyksos), Thebes (Dyn 16 and 17), and Abydos (the Abydos Dynasty). His typology underpins `polity` and differs from some older literature that treats Dyns 14 and 16 as "minor". Phase A should not flatten.
