# Egyptologist sweep review, 2026

Scope read: `README.md`, `transcribe.md`, `merge-disagreements.txt`, and `reconciled.jsonl`. No prior `reviewer-notes-*.md` files were present. Spot checks used `proprietary/books/Ryholt 1997 - Political Situation SIP.pdf`, especially catalogue pp. 336-405 and chronological tables pp. 408-410. Rows checked included 13.1, 13.21, 14.6, 14.32, 14.f, 14.g, 15.1, 15.3, 15.5, 16.4, 17.8, 17.9, Abyd.a-c, N.6, and P.6.

## P1

None found in this sample.

## P2

- `14.32` Hapu(...?) is missing its anglicised prenomen. Ryholt File 14/32 prints `P: s.mn-n-rꜥ`, and Table 95 gives the corresponding prenomen as `Semenenre`. The row has `prenomen_transliterated: "s.mn-n-rꜥ"` but `prenomen: null`. This is a field-value loss from an explicit source value, not merely an uncertain restoration.

- `15.3` Sakir-Har still contains merge markup and loses part of Ryholt's qualification. File 15/3 reads the nomen as `s-k-r-ḥ-r (syllabic), not preceded by sꜣ-rꜥ, but ḥqꜣ-ḫꜣswt`; `reconciled.jsonl` has `s-k-r-ḥ-r* (syllabic), not preceded by *sꜣ-rꜥ`. The stray asterisks are markdown/OCR artefacts and the `but ḥqꜣ-ḫꜣswt` clause is omitted, weakening the identification/provenance fidelity for the row.

## P3

- README/prompt/source-data polity statements conflict for Dynasty 14. The schema and prompt map Dyn. 14 to `"Avaris"`, and all sampled Dyn. 14 rows use that. The README "Polity boundaries" note instead says Ryholt distinguishes "Xois (Dyn 14), Avaris (Dyn 15)". This is a Phase-0 documentation contradiction. Either the note should be corrected to the Ryholt interpretation being encoded, or the `polity` mapping should be revisited with a citation to the relevant Ryholt table/prose.

- Hyksos rows `15.1` and `15.2` omit the transliterated `Name:` values from File 1 (`s-m-q-n (syllabic)` and `ꜥpr-ꜥn-ti (syllabic)` in normalised rendering). Because these rulers are listed as `Name:` rather than `N:`, the current schema has no obvious home and leaves `nomen_transliterated` null. This is defensible only if intentional; otherwise add a schema convention for non-cartouche `Name:` entries.

- Several table-only/appendix rows use File 1 transliteration while leaving the corresponding anglicised `prenomen` null, e.g. `14.f` Yaꜥqub-Har has `P: mr-wsr-rꜥ` but `prenomen: null`. This follows the README rule that anglicised names come from chronological tables, but downstream users may misread null as "no prenomen attested." Consider documenting this distinction explicitly for appendix/unplaced rows.

Positive controls: sampled core rows 13.1, 13.21, 14.6, 15.5, 16.4, 17.8, 17.9, Abyd.a-c, N.6, and P.6 matched the cited PDF in identification, dynasty/scope assignment, dates where applicable, and main titulary values within expected OCR-normalisation limits.
