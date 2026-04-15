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

1. **OCR**: Claude Code subagents transcribe the PDF in physical-page chunks (1-indexed, 5 pages per chunk by default). Each chunk is written to `raw/chunk-pNNN-pMMM.md` locally. These chunk files are **not committed** — they contain Ryholt's own prose verbatim and would redistribute copyrighted material. The transcriber regenerates them from the committed-SHA PDF when needed.
2. **Structured extraction**: three independent Claude Code subagents each read every chunk and emit JSONL per the schema below. `merge.py` deterministically majority-votes per-field and writes the final `reconciled.jsonl` plus `merge-disagreements.txt` (committed) for audit.
3. `reconciled.jsonl` rows cite the chunk's physical-page range, e.g. `source_citation: {pdf_pages: "340-344", edition: "CNI 20, 1997"}`. A reviewer verifying a row opens the PDF at physical pages 340-344 and reads the content there; the book's running-header printed-page numbers are visible on each page so scholarly cross-reference to the printed edition is trivial.
4. The transcriber spot-checks ~2-3 king entries against the PDF and corrects `reconciled.jsonl` directly for any disagreements, noting the override in `merge-disagreements.txt`.

The benchmark that sized this pipeline (physical p. 340, Sobkhotep I / printed p. 336) is documented in ADR-017.

### Target physical range

Physical pages **336-416** (81 pages, 17 chunks). This spans File 1 / Catalogue of Attestations (printed pp. 333-407) plus the Chronological Tables appendix (printed pp. 408-411) with generous padding at both ends to absorb offset shifts at Part boundaries.

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
  "source_citation": {"pdf_pages": "340-344", "edition": "CNI Publications 20, Museum Tusculanum Press, 1997"}
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
