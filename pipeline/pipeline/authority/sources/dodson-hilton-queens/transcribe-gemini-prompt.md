# Gemini OCR prompt — Dodson & Hilton Brief Lives chunk p126-p130

This is the verbatim prompt used to run the OCR pass on `raw/source-p126-p130.pdf` via Google Gemini, because Claude Opus 4.6 refused the task on copyright grounds (see `transcribe.md` § "Model deviation" and ADR-017 § "Amendment 2026-04-15: external-model fallback for copyright-refusal"). The Gemini model version and the output chunk (`raw/chunk-p126-p130.md`) are recorded in `transcribe.md`.

The prompt below is the scholarly-extraction framing used. It is committed so a future reproducer can re-run the OCR step against the same source PDF (SHA-256 `e636c49f3d0b5b6c6ec072cc6e7af9d605caf52d438c55cd84da9de7b07008a0`) and diff their output against ours.

---

You are OCR-transcribing five pages from Dodson & Hilton (2004) *The Complete Royal Families of Ancient Egypt* (Thames & Hudson, 1st ed. hardback) for a structured-data extraction pipeline. The source pages are 137–141 of the printed book — the "Brief Lives" sub-block of Chapter 3 *The New Kingdom*, section *The Power and the Glory*.

Produce a single Markdown document that I will paste into `raw/chunk-p126-p130.md` of a research repository. No preamble, no explanation, no code fences — the Markdown itself is the whole output.

## What to transcribe

Every **Brief Lives entry** gets transcribed. Each entry is a short prose block starting with a bold name followed by role codes in parentheses. Example format in the book:

```
**Ahmes B** (KM; KGW; KSis)
Wife of Thutmose I; known from a range of monuments, principally
those of her daughter, Hatshepsut, but also from other material,
including a statue of her mortuary priest, Nakht, from Karnak.
```

Render each entry as: one line with the bold name + parenthetical role codes, then the prose paragraph on the next line(s), then a blank line before the next entry.

Pages are laid out in **three columns per page**. Read each page as column 1 top-to-bottom, then column 2 top-to-bottom, then column 3 top-to-bottom. An entry split across columns (prose overflow from col 1 bottom into col 2 top) is one entry.

## Transcription rules

1. **Preserve disambiguator letters on names** exactly as printed. Examples: `Ahmes B`, `Hatshepsut D`, `Iset A`, `Iset B`, `Mutneferet A`, `Nefertiry C`, `[...]pentepkau` (keep the square-bracketed ellipsis for lacunae).
2. **Preserve role-code parentheses verbatim** including semicolons and spacing: `(KM; KGW; KSis)`, `(KSon; Exec; SPP)`, `(EKSon; Overseer of Cattle)`. Codes used in the book include `K`, `KM`, `KW`, `KGW`, `GW`, `KSis`, `KD`, `KSon`, `EKSon`, `HPH`, `Ador`, `Nurse`, `Exec`, `SPP`, `Genmo`, `UWC`, `Overseer of Cattle`, `Captain of the Troops`, `Mayor of Thinis`, `Nurse of the God`, `later king`. Transcribe what's printed — do not normalise or expand.
3. **Preserve museum / tomb / catalogue numbers exactly**: `CM CG57006`, `CM JE37417 = CG42072`, `BM EA43`, `TT64`, `TT143`, `TT226`, `KV32`, `KV35`, `KV42`, `KV43`, `MMA 1021`, `EK3`. These are load-bearing attestation anchors downstream.
4. **Preserve scholarly hedges verbatim**: `probably`, `possibly`, `perhaps`, `apparently`, `conceivably identical with`, `not improbable`, `almost certainly`. Do not paraphrase.
5. **Preserve superscript footnote markers** like `¹⁰¹`, `¹⁰²` inline if they appear in body text (Nebetia on p. 140 has one). Encode as Unicode superscript or as `[^101]`.
6. **Render kings in bold uppercase** when they appear that way in the book: `**AMENHOTEP II**`, `**AMENHOTEP III**`, `**THUTMOSE IV**`. In cross-references inside prose they appear mid-paragraph; preserve the rendering.
7. **Italics within body text** (e.g. `*shabti*`, Latin / Egyptian-transliterated italics) → render with Markdown single-asterisk italics.
8. **Include the section heading `## Brief Lives`** at the top, the one-line key `*Males in bold, females in bold italic.*`, then the entries.
9. **When the `Unplaced` sub-section appears on printed p. 141**, render it as a level-3 heading: `### Unplaced` followed by the `(See also Addenda p. 304)` pointer on the next line. Entries under it are transcribed the same way (they're normal Brief Lives entries that happen to be in the "Unplaced" block).
10. **Include an HTML comment** at the very top of the document:
    ```html
    <!-- OCR chunk: physical PDF pages 126-130 of the source book / printed pages 137-141. Dodson & Hilton 2004, The Complete Royal Families of Ancient Egypt, Thames & Hudson 1st ed. hardback. ISBN 0-500-05128-3. Source PDF SHA-256 e636c49f3d0b5b6c6ec072cc6e7af9d605caf52d438c55cd84da9de7b07008a0. -->
    ```

## What to skip

- **Chapter narrative prose** above the "Brief Lives" header on printed p. 137 (the paragraph starting "lady, Pyihia. Eight other King's Daughters are also known …" and the paragraph about Nebetia / Siatum A that follows). These are chapter body, not Brief Lives entries.
- **Photograph captions** — any italic line beginning with `(left)`, `(below)`, `(above)`, or otherwise describing a visual figure (e.g. `Iset A, mother of Thutmose III; from Karnak (CM JE37417 = CG42072).`, `(below) Queen Mutneferet A, found in the chapel of Wadjmose at Western Thebes (CM CG572).`, `Prince Amenhotep B sits on the lap of his tutor – the Mayor of Thinis, Min – in the latter's tomb at Thebes.`). These are visual-description captions; they are not Brief Lives entries.
- **Page headers / footers** — `3 THE NEW KINGDOM`, `THE POWER AND THE GLORY`, the page numbers `137 138 139 140 141`.
- **Decorative bullet-dot dividers** used as section separators in the book layout.

## Expected output

Roughly 55–65 Brief Lives entries across the 5 pages. The list is alphabetical by name within each page column, running from `Ahmes B` on printed p. 137 to `[...]pentepkau` at the end of the Unplaced block on p. 141.

Produce the Markdown. Nothing else.
