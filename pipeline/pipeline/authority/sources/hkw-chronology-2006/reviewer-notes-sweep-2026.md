# Reviewer notes - sweep 2026

Retrospective egyptologist sweep of HKW 2006 source directory. Read `README.md`,
`transcribe-ch2.md`, `reviewer-notes-ch2.md`, and `reconciled.jsonl`; checked
the full Brill PDF in `proprietary/books/`. Spot-checked more than 10 rows:
Dyn. 0, Iry-Hor, Ka, Scorpion I, Nar-mer, Djoser, Neferirkare Dyn. 8,
Senwosret III, Amenemhet IV, Ta'o/Senakthenre, Merneptah, Hakoris, and the
Alexander terminus.

## P1

None found. The prior Ch. 2 P1/P2 issues documented in `reviewer-notes-ch2.md`
appear to have been applied: Scorpion I is now `dynasty: null`, Ka no longer
imports "Sekhen", and Ka's note correctly frames late IIIB / start IIIC1.

## P2

**Transliteration/prenomen drift in IV.2 rows.** Several checked prenomina do
not faithfully reproduce HKW's printed/text-layer form and look like silent
normalization or OCR repair without notes. On p.492 HKW prints Senwosret III
as `Kha'kaure'`, but JSON has `Kha'kawre'`; Amenemhet IV is `Ma'kherure'`, but
JSON has `Ma'kherwre'`. On p.494 HKW prints Hakoris as `Khnemma'atre'`, but
JSON has `Khnema'atre'`. HKW also prints `Baenre'` for Merneptah and Nepherites
I, while JSON has `Ba'enre'`. These may be defensible Egyptological
normalizations, but this source is supposed to be a transcription of HKW; either
preserve HKW spellings or add notes/provenance for normalized forms. Recommend
a mechanical audit of all `prenomen` values against pp.490-495.

**Scope/provenance contradiction: README/transcribe overclaim Ptolemaic
coverage.** `README.md` and `transcribe-ch2.md` say the initial IV.2 extract
runs "Dyn-1 -> Ptolemaic rulers" and covers pp.490-498. The PDF shows IV.2 ends
on p.495 with Alexander the Great (332-323); pp.496-498 are IV.3 Kushite,
Napatan, and Meroitic rulers. `reconciled.jsonl` correctly ends at Alexander and
contains no Ptolemaic rows. The data is scope-faithful, but the documentation is
not; this can mislead Phase-0 consumers into assuming Ptolemaic authority
coverage that is absent.

## P3

**Ta'o/Senakthenre row silently modernizes HKW.** On p.492 HKW prints `Ta'o
Senakthenre'`; JSON has `Senakhtenre'`. Cross-source sanity favors the JSON
form: Leprohon and Ryholt both use Senakhtenre/Senakhtenra for the Dyn. 17
Ahmose/Ta'o problem. But for an HKW-sourced row this is still an uncited
general-knowledge correction. Add a note or preserve HKW spelling.

**Row-level `approximate` cannot express bound-specific `ca.`.** Rows such as
Second Intermediate Period (`1759-ca.1539`), Dyn. 13 (`1759-ca.1630`), Siamun
(`986-ca.968`), Osorkon I (`922-ca.888`), and Tantamani (`664-ca.655`) are
represented with `approximate: true` for the whole row. Several notes already
acknowledge this; no immediate data correction is required, but downstream
consumers should not read row-level `approximate` as applying equally to both
bounds.

Overall: dates, dynasty assignments, Ch. 2 Dyn-0 handling, and the Dyn. 8
Neferirkare typographical correction are broadly sound. The remaining risk is
source-fidelity drift in name/prenomen strings, not chronology.
