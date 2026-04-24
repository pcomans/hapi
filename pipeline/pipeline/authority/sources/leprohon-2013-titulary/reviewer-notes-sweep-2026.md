# Sweep egyptologist review — 2026

Source reviewed: `proprietary/books/Leprohon 2013 - The Great Name.pdf`, with `README.md`, `transcribe.md`, `reconciled.jsonl`, and `merge-disagreements.txt`. No prior `reviewer-notes-*.md` files were present. Spot-checked rows against the local PDF-derived chunk text: `leprohon-2.08`, `4.02`, `11b.05a`, `12.01a`, `15.01`, `17.28`, `18.06`, `18.10b`, `19.03`, `22.12`, `25.04`, `30.03`, `33.05a`.

## P1

- `stage_suffix` still conflates true same-king titulary stages with distinct Ptolemaic queen-consort subentries. Leprohon's chapter X subheads `2A. ARSINOE II`, `3A. BERENIKE II`, `5A. CLEOPATRA I`, `8A. CLEOPATRA II` are separate persons, not stages of Ptolemy II/III/V/VIII. Encoding them only as `stage_suffix: "a"` creates a wrong-person risk for Phase A joins; consumers that group by base sequence will treat queen titularies as the preceding king's alternate stage. The row source notes explain the issue, but the schema needs `row_type`/`consort_of` or equivalent before these rows are authority-safe.

## P2

- Several `alt_display_names` are Phase-A matching imports rather than Leprohon attestations, weakening source provenance. Examples: `leprohon-22.12` adds `Shoshenq V`; `leprohon-25.04` adds `Shabako`; `leprohon-33.12` adds `Berenike III`; `merge-disagreements.txt` records similar additions such as `Taharka`/`Tirhakah` and the Shoshenq series. These may be useful aliases, but they are not Leprohon headword/slash/Greek forms in the checked PDF passages. Keep them in a downstream alias layer or mark them with explicit non-Leprohon provenance.

- Non-standard source labels are projected into canonical name lists without a machine-readable record of Leprohon's actual label. Checked case: `leprohon-15.01` has Leprohon's `Title and name: ḥqꜣ ḫꜣswt s-m-ḳ-n`, but the extract dual-emits it into both `throne_names` and `birth_names`. Similar README-documented cases include `Cartouche:` and `Throne and birth:`. The prose `source_note` is not enough for reliable consumers; add `source_label_raw` or equivalent.

## P3

- `source_note` frequently mixes Leprohon footnote content with pipeline/editorial commentary. Examples in checked rows: `leprohon-11b.05a` and `12.01a` append stage-model boilerplate to the Horus-name note; `15.01` explains dual-emission policy; consort rows explain extraction semantics. This is useful audit material, but it blurs source provenance. Prefer separate fields for extractor rationale vs. Leprohon notes.

- Transcription metadata is incomplete across the full merged source. `transcribe.md` has detailed chunk logs for chunks 1, 2, and 14, but the committed `reconciled.jsonl` spans all chapters/chunks. For retrospective reproducibility, add concise chunk-log entries for the intervening chunks or point to the PR logs that supplied their page ranges and reviewer status.

## Spot-check outcome

The checked titulary strings, translations, page citations, and key known hazards matched the PDF text in the sampled rows: Khasekhemwy Horus/Seth dual form and later cartouches; Khufu's two throne forms; Mentuhotep II/Amenemhat I stages; Kamose variants; Hatshepsut; Akhenaten post-year-5 names; Shabaka; Nakhthorhebyt; and the corrected Cleopatra I `ḫkr(t).n ẖnmw`. No new OCR/transliteration misread or wrong-ruler attribution was found in this sample.
