---
name: Dodson-Hilton queens chunk-review recurring patterns
description: Recurring downstream-matching risks in D&H Brief Lives extractions across chunks
type: project
---

Recurring patterns in Dodson-Hilton `dodson-hilton-queens` Brief Lives chunk extractions (Ramesside, Power, Amarna, Head of the South, Seizers of the Two Lands, etc.):

1. **Hedge strings baked into name fields.** Extraction prompts specify `"X (possibly)"` as the canonical hedge form, faithful to D&H. Four variants observed: `(probable)`, `(probably)`, `(possible)`, `(possibly)` — inconsistent even within one chunk (Seizers: Itakayet A has `(probable)`, Itakayet B has `(probably)`, Sithathor B has `(possible)`, Hathorhetepet has `(possibly)`). Appears in `spouse_names`, `father_name`, `mother_name`, **and now `children_names`** (Seizers: Neferet I → `["Amenemhat I (probable)"]`; Senwosret A → same). Will NOT string-match the clean ruler name during the enrich-stage authority resolution. The hedge should ideally live in a separate confidence field; the name string itself needs to stay clean for matching.

2. **`KW?` / hedged role tokens.** Prompt preserves `?`-suffixed role codes verbatim as distinct tokens from their unhedged form. Need a controlled role vocabulary (or `KW?` will be its own untracked value forever).

3. **`alt_names: []` across every row.** The extraction prompts explicitly say to return `[]` because D&H Brief Lives rarely carries `"Also known as …"` inline. But museum catalogues (Met, BM, Brooklyn, Harvard) use heavy variant spellings — Inyotef/Intef/Antef, Ashayet/Ashait, Kawit/Kauit, Sadhe/Sadeh, Kemsit/Kemsyt, Henhenet/Henhenit, Khnemetneferhedjet / Khenemetneferhedjet, Neferuptah / Neferu-Ptah, Sobkneferu / Neferusobk / Sebeknefrure. Authority matching will suffer unless `alt_names` is backfilled from a separate pass (pharaoh.se, Wikidata, or a variant-table).

4. **Sentinel strings for unknown referents.** `"unknown king"` in `father_name`/`spouse_names` (Neferkayet, and Seizers-chunk Didit/Neferet Q in notes). Faithful to D&H's "unknown kings" phrase. Consistency question: does every D&H chunk use the same sentinel, and will the enrich stage treat it as null vs attempt to resolve it as a literal name?

5. **Non-regnal individuals carrying a dynasty number.** Inyotef A (nomarch) and his mother Ikui stamped `dynasty: 11` because D&H places them in that section. Seizers-chunk: Senwosret A (GF, probable father of Amenemhat I) and Neferet I (KM, probable mother) stamped `dynasty: 12` though they strictly pre-date Dyn 12. Other authorities (pharaoh.se, Beckerath) may not carry them at all — reconciliation question for the enrich stage.

6. **Long-form role strings leaking into `roles`.** Seizers chunk: Kaneferu carries `["Mistress of All Women"]` — a full English phrase D&H prints out rather than a coded abbreviation. Unlike short codes (KW, KD, UWC, KSonB), this one is untokenised and will not match any controlled vocab.

7. **Sex-inference provenance weaker on Gemini-OCR'd chunks.** Chunks 1 and 5 (Seizers) used Gemini web-UI paste after Claude content-filter refusal. Gemini flattens bold-italic → bold; sex is then re-inferred from role codes + prose pronouns in main session. Internally consistent vs the raw chunk file (4 male `**bold**` + 44 female `***bold-italic***` in Seizers match reconciled), but the final loop against printed typography is un-closable without the PDF in-session (D&H PDF is >100MB, beyond Read limit).

8. **Cross-role individuals (princess → later king).** Seizers chunk: Sobkneferu appears here as KD/dynasty 12, but she's also the terminal Dyn-12 sole-ruling female pharaoh; similarly Ameny A (= Amenemhat II) and Amenhotep B (= Amenhotep II) in other chunks. Enrich stage needs a rule merging these `dh_id`s with their pharaoh counterparts rather than treating them as distinct entities.

**How to apply:** When reviewing future D&H chunks, don't re-flag (1)–(5) as extraction bugs — they're prompt-specified. Frame them as downstream/enrich-stage concerns. Do audit whether the extraction matches the prompt's hedge convention; flag any drift. New pattern (6), (7), (8) should be actively watched.

9. **Gemini OCR drops short prepositional phrases, not just soft-hyphens.** Founders chunk (PR #79): Perneb's notes read "Seal-impressions bearing his name were found in Hotepsekhemwy at Saqqara." — grammatically impossible ("in" a person). D&H almost certainly prints "in the funerary complex of Hotepsekhemwy" or "in the tomb of Hotepsekhemwy". Gemini dropped ~5 words mid-sentence. The Nymaathap A restoration script only catches page-break continuations; mid-sentence drops need a semantic proofreading pass. **How to apply:** on any Gemini-OCR'd D&H chunk, sanity-read each notes string for grammatical impossibility (prepositions "in"/"at"/"of" with a king-name directly following are the giveaway).

10. **New hedge variant `(presumably)`.** Founders chunk: Benerib's `spouse_names: ["Hor-Aha (presumably)"]`. Brings the total hedge variants to 5. Catalogue centrally or a downstream cleaner will miss one.
