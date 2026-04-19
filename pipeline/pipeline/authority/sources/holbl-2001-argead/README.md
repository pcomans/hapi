# Hölbl 2001 — *A History of the Ptolemaic Empire* (Argead bridge)

Source of truth for the **Argead bridge** between the end of the Late Period (Dyn 31 Persian rule) and the Ptolemaic dynasty: Alexander the Great, Philip III Arrhidaios, Alexander IV (332–310 BCE). These three kings are absent from both HKW 2006 (which terminates at Alexander with an unanchored entry) and pharaoh.se (which begins at Ptolemy I Soter). Without this source the 332–305 BCE span has no ruler authority.

## Citation

Hölbl, G. (2001) *A History of the Ptolemaic Empire*. Translated by Tina Saavedra. London / New York: Routledge.

- **Edition used:** Routledge 2001 English translation of the 1994 German original (*Geschichte des Ptolemäerreiches*, Wissenschaftliche Buchgesellschaft).
- **Retrieved:** 2026-04-16 (local scan in `proprietary/books/`).
- **PDF SHA-256:** `1a18600cb2c271a907a216304d6eed3f982b07adcccce30c3ded2a12ef6def4b` (also pinned in `transcribe.md`).

## Scope

Appendix (printed pp. 318–353, physical PDF pp. 347–378), *Overview of the events discussed in the history of the Ptolemaic kingdom* — four-column chronological table with rotated left-margin reign banners. This extract covers **only the first three reign banners** spanning **physical PDF pp. 349–351 (printed pp. 320–322)**:

| `holbl_id`   | Banner (verbatim, rotated left margin)              | Dates (BCE)     |
|--------------|-----------------------------------------------------|-----------------|
| `argead.01`  | `ALEXANDER THE GREAT`                               | 332 → 323       |
| `argead.02`  | `PHILIP III ARRHIDAIOS // Ptolemy as Satrap`        | 323 → 317       |
| `argead.03`  | `ALEXANDER IV // Ptolemy as Satrap`                 | 317 → 310       |

**Explicitly excluded:**

- The `INTERREGNUM // Ptolemy as Satrap` banner (308–306 BCE) and the `PTOLEMY I SOTER` banner (305/4 →) that follow on physical p. 351. Ptolemaic-dynasty rulers are covered by pharaoh.se and will be reconciled there. Duplicating them here would create cross-source drift.
- The rest of the Appendix (pp. 352–353 in our chunk's frame of reference; full Appendix pp. 318–353 in the book). Those pages cover Ptolemies II–XV and their queens — again, pharaoh.se territory.
- The body of the book (chs. 1–10, pp. 1–317). Hölbl's narrative, footnotes, and analytical prose are out of scope; only the Appendix's table cells are extracted.

**Expected row count:** exactly **3**.

## Schema

```json
{
  "holbl_id": "argead.01",
  "kind": "ruler",
  "display": "Alexander the Great",
  "greek_form": null,
  "alternative_reading": null,
  "prenomen": null,
  "start_year": -332,
  "end_year": -323,
  "approximate": false,
  "uncertainty_plus_years": null,
  "dynasty": null,
  "page": 349,
  "note": "Hölbl banner: 'ALEXANDER THE GREAT'. Accession: end of 332 BCE (invasion of Egypt). Death: 10 June 323 at Babylon. No 'Ptolemy as Satrap' annotation on this banner.",
  "source_citation": {"pdf_pages": "349-351", "edition": "Routledge 2001"}
}
```

- `holbl_id` = `"argead.{NN}"` zero-padded two-digit sequence (`01`, `02`, `03`).
- `kind` = always `"ruler"` for this source. The field is kept for parity with other sources that may mix rulers and events.
- `display` = anglicised Title-Case form. Hölbl prints the banner ALL-CAPS in the rotated margin; that banner wording is preserved in `note` for cross-reference.
- `greek_form`, `alternative_reading`, `prenomen`, `uncertainty_plus_years`, `dynasty` = **always null** for this source. Hölbl's Appendix does not print Greek titulature, alternative readings, Egyptian prenomina, uncertainty spans, or dynasty labels in the banner cells. The fields are present so the schema matches cross-source expectations; they are not data carriers for this extract. Phase A resolves Greek forms and dynasty assignment ("Argead" as a bridge label between Dyn 31 and Ptolemaic) downstream.
- `start_year` / `end_year` = negative integers (1 BCE → `-1`). The pair describes the reign boundaries as Hölbl prints them: Alexander 332→323, Philip III 323→317, Alexander IV 317→310. For the compound date `310/09` on Alexander IV's terminal row, the **earlier boundary** (`-310`) is taken, matching our convention elsewhere in Phase-0 sources (see `transcribe.md` § "Compound dates").
- `approximate` = always `false` for this source. None of the three reign boundaries are hedged with `c.` / `?` / `??`.
- `page` = physical PDF page on which each reign banner **begins** (`349` for Alexander and Philip III, `350` for Alexander IV).
- `note` = 1–3 sentences of verbatim banner context, quoting the rotated-margin banner wording plus the accession/terminus events Hölbl gives in the row cells (invasion, Babylon division, murder).
- `source_citation` = fixed literal `{"pdf_pages": "349-351", "edition": "Routledge 2001"}` — the chunk's full range, not per-row.

## Rights

Routledge (Taylor & Francis), in copyright 2001. This extract contains only factual data — three ruler names with anglicised spelling, three pairs of BCE reign boundaries, three short context sentences paraphrased from the banner cells. Hölbl's argumentation, footnotes, narrative prose, and analytical chapters are not reproduced. Per ADR-017 the source PDF is not committed (lives under `proprietary/books/` behind `.gitignore`); per-chunk OCR markdown and per-agent extraction JSONLs under `raw/` are not committed (see `.gitignore` pattern `pipeline/pipeline/authority/sources/*/raw/*` with `.gitkeep` exemption).

## Method

Per ADR-017 (Claude Code subagent OCR → three-subagent structured extraction → deterministic majority-vote merge). See `transcribe.md` for the specific protocol applied to this Appendix chunk.

**Review.** Because the extract is three rows with unanimous agent agreement on every structured field (only prose `note` cells differ by agent wording), no separate LLM-reviewer override pass was necessary; the merge-disagreements report is committed for audit. **A human Egyptologist sign-off pass has NOT been performed** — the extract is provisional until that happens. Given the small scale (3 rows) and the public-record nature of the Argead reign dates, the confidence band is high, but constitutional rule 1 still requires the sign-off.

## Known gaps / Phase A notes

- **Dynasty label**. Hölbl does not assign a dynasty number to these three kings. Modern Egyptological convention is split: some authorities class them as the "Macedonian Dynasty" or extend Dyn 31 to cover them; others treat the 332–305 BCE span as a bridge with no dynasty label until Ptolemy I is crowned. `dynasty: null` here is deliberate — Phase A makes the canonical label choice and writes it into `dynasties.json`, not into this source extract.
- **Greek titulature**. Hölbl's Appendix does not print Greek forms (`Ἀλέξανδρος`, `Φίλιππος Γ' Ἀρριδαῖος`, `Ἀλέξανδρος Δ'`) in the rotated banners; they appear in the main-text narrative chapters which are out of scope. Phase A can cross-reference pharaoh.se (which begins at Ptolemy I) or Beckerath 1999 *Handbuch* for Argead Greek forms.
- **Egyptian prenomina**. Alexander the Great was crowned pharaoh at Memphis (January 304 is the Ptolemy I crowning, but Alexander's own acclamation dates to end-332 BCE per Hölbl's row) and had an Egyptian titulary (`Setepenre Meryamun` nomen / throne-name tradition); that titulary is not in Hölbl's Appendix and must be sourced from Beckerath 1999 if required. `prenomen: null` here is deliberate.
- **Co-regency / satrap annotation**. Hölbl's `// Ptolemy as Satrap` suffix on banners 02 and 03 records the political fact that Ptolemy son of Lagos governed Egypt as satrap under both Philip III and Alexander IV. This governance fact is preserved in the `note` field as verbatim banner wording; it is **not** encoded as a separate structural field. Phase A may introduce a `governed_by_regent` or similar if cross-source data warrants it.
- **`310/09` terminal date**. Hölbl prints the year of Alexander IV's murder as `310/09`; the `end_year: -310` choice takes the earlier boundary per `transcribe.md` § "Compound dates". The alternative (`-309`) is recorded in prose form in the `note` cell for reviewer audit.
