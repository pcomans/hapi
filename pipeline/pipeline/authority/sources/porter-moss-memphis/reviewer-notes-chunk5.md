# PM III.2 chunk 5 — egyptologist review against printed PDF

Ground-truth source: `proprietary/books/Porter & Moss - PM III Part 2 Saqqara-Dahshur.pdf`, physical pages 33–45 + 53–57 read at native resolution.

## P1 — merge-blocker

### F1. SAQ-IputI — `occupant_name: "Iput I"` does not match PM's printed headword
Verified against printed source p.396: PM prints **"PYRAMID-ENCLOSURE OF IPUT¹"** — bare `IPUT` with a superscript footnote. There is NO `[I]` bracketed numeral on the heading line. The footnote at the bottom of p.396 reads "1 [King's daughter of his] body, King's wife (of Teti), King's mother (of Pepy I)." — that's the prosopography establishing she's Pepy I's mother (i.e. Iput I in modern scholarship), but PM does not print the numeral in the heading.

Compare against the row's own provenance discipline: `notes_from_pm` reads `"PYRAMID-ENCLOSURE OF IPUT I. Dyn. VI. PYRAMID."` — the `I` after `IPUT` is an interpolation, not PM's text. This is a faithfulness violation (ADR-017).

**Fix:** `occupant_name` should be `"Iput"`; `occupant_alt_names` should include `"Iput I"` as the modern-scholarship disambiguation; `notes_from_pm` should drop the inserted `I` and instead append the footnote prosopography (e.g. `"King's wife of Teti, King's mother of Pepy I (per PM footnote 1)."`).

Note SAQ-IputII (row 31) is fine — PM does paginate Iput II separately on p.432, and that's a different printed entry which I have not paged here, but it has its own headword in PM III.2.

### F2. SAQ-Teti — `notes_from_pm` lost PM's Lepsius/Perring tomb-identification clause
Verified against printed source p.395 (running header "Pyramid-complex of Teti"): the row's bibliographic identification line is **"PYRAMID. Lepsius, XXX; Perring and Vyse, 1."** This is PM's standard tomb-ID line and it IS present in the reconciled `notes_from_pm` ("Lepsius, XXX; Perring and Vyse, 1") so this is actually fine. Withdrawing.

### F3. SAQ-Khuit — `notes_from_pm` is too thin and drops PM's footnote prosopography
Verified against printed source p.397: PM prints "PYRAMID-ENCLOSURE OF KHUIT¹ [hieroglyph] Dyn. VI" with footnote 1 "King's wife (of Teti)." The reconciled row has `notes_from_pm: "PYRAMID-ENCLOSURE OF KHUIT. Dyn. VI"` — the footnote is the entire prosopographic justification for `occupant_role: "Queen"` and it has been silently dropped. Per rule 1 (work like a scholar), if the role classification depends on a footnote, the footnote text must be captured.

**Fix:** append `" (King's wife of Teti, per PM footnote 1)"` to `notes_from_pm`.

## P2 — same-cycle preferred

### F4. SAQ-Neterikhet — alias ordering is defensible but check Djoser
Verified against printed source p.399: PM prints "C. STEP PYRAMID ENCLOSURE OF NETERIKHET [hieroglyph] (Zoser [hieroglyph]). Dyn. III". PM's primary is `Neterikhet` with `Zoser` parenthetical — the row reflects this correctly. However the modern museum-catalog spelling is overwhelmingly `Djoser`, not `Zoser` (Brooklyn, Met, Harvard all use Djoser). For Phase-A matching, `occupant_alt_names` should also contain `"Djoser"` (the variant museum cataloguers will write) alongside PM's printed `"Zoser"`. Without `Djoser`, this row will fail to match the bulk of museum attributions to him.

### F5. SAQ-Userkaf — verify `el-Haram el-Makharbish` spelling
Verified against printed source p.398: PM literally prints "el-Haram el-Makharbish". The reconciled `tomb_aliases` matches PM exactly. **Verified clean.**

### F6. SAQ-Neterikhet — verify `el-Haram el-Mudarrag` spelling
Verified against printed source p.399: PM literally prints "el-Haram el-Mudarrag" (terminal `g`, not `j`). The reconciled `tomb_aliases` matches. **Verified clean.**

## P3 — nits

### F7. SAQ-GreatEnclosure — `notes_from_pm` could include PM's cross-reference
Verified against printed source p.417: full printed entry is "E. 'GREAT ENCLOSURE'. Probably Dyn. III" plus a "MARAGIOGLIO and RINALDI..." reference line plus "See vertical aerial views of Step Pyramid enclosure of Sekhemkhet, supra." The row captures the heading + dynasty hedge correctly. P3 because the bibliographic reference adds little for matching purposes.

### F8. SAQ-Sekhemkhet — `is_unfinished: true` verified
Verified against printed source p.416: under the heading "STEP PYRAMID." PM prints "Unfinished." literally. ✓

## Other rows verified clean against printed source

- SAQ-Teti (p.393–395): heading `A. PYRAMID-COMPLEX OF TETI. Dyn. VI` + Lepsius XXX, Perring & Vyse 1 — matches.
- SAQ-Userkaf (p.397–398): heading `B. PYRAMID-COMPLEX OF USERKAF. Dyn. V.` + Lepsius XXXI, Perring & Vyse 2 + el-Haram el-Makharbish — matches exactly.
- SAQ-Sekhemkhet (p.415–417): heading `D. STEP PYRAMID ENCLOSURE OF SEKHEMKHET. Dyn. III` + Unfinished — matches.
- SAQ-GreatEnclosure (p.417): heading `E. 'GREAT ENCLOSURE'. Probably Dyn. III` + attribution_certainty uncertain — matches PM's hedge.

## Verdict

**FIX-AND-SHIP**

Three P1 findings worth addressing before merge — but they're all faithfulness-to-PM issues (interpolated `[I]` numeral on Iput, dropped footnote prosopography on Khuit, missing `Djoser` alias on Neterikhet) rather than wrong-person or schema risks. Fix in-PR; don't defer. The Iput interpolation is the most important because it sets precedent for whether the extractor is allowed to silently insert disambiguating numerals that PM doesn't print — that's a Phase-0 faithfulness principle and should be settled here, not later.
