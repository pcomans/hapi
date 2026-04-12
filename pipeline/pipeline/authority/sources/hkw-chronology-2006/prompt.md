# Transcription prompt

Use this prompt verbatim against each model (Claude, Gemini, GPT) with
`hkw-iv-2-iv-3.pdf` as input. Output goes to `{model}.jsonl` in this
directory.

---

You are transcribing a chronological table from Hornung, Krauss &
Warburton (2006), *Ancient Egyptian Chronology* (Brill), sections IV.2
and IV.3. Output is JSONL — one JSON object per line, no wrapper
array, no prose commentary.

## Row kinds

Each row in the source table is one of three kinds, discriminated by a
`kind` field:

- `"period"` — bold period heading (e.g. "Early Dynastic Period",
  "Old Kingdom", "New Kingdom")
- `"dynasty"` — bold dynasty heading (e.g. "Dyn. 1", "Dyn. 18",
  "(Theban) Dyn. 11", "Dyn. 15 (Hyksos)")
- `"ruler"` — non-bold row listing a single ruler

## Column 1 conventions

Column 1 for ruler rows contains:

- A **display name** in Roman type (e.g. "Khufu", "Amenhotep III")
- An **italicized prenomen** after the display name (e.g.
  "Amenhotep III *Nebma'atre'*"). The italics denote the throne name
- A **Greek form in parentheses** (e.g. "Khufu (Cheops)",
  "Menkaure (Mycerinus)")
- An **alternative reading in square brackets** (e.g.
  "Piankhi [Piye]")
- Some rulers have a slash-separated list (e.g.
  "Ra'djedef/Djedefre"). Treat the whole string as the `display`
  field and leave `prenomen` null unless part of the string is
  italicized
- Multi-ruler combined lines (e.g. "Swadjtu, Ined, Hori, Dedumose" in
  Dyn. 13) are a single row with the comma-separated list as
  `display` and a `note` explaining

## Column 3 (dates)

- Dates are BCE. Store as negative integers: `2543 BCE → -2543`
- A range `2543–2436` becomes `{start_bce: -2543, end_bce: -2436}`
- A `?` on either bound becomes `null` for that field
- The `+25`, `+16`, `+3` superscripts are the `uncertainty_plus_years`
  (25, 16, 3)
- `ca.` in column 2 → `approximate: true`
- IV.3 uses prose ranges like "c. 885–835 BC", "2nd half of 7th cent.
  BC", "early 6th cent. BC", "late 4th cent. to 2nd third of 3rd cent.
  BC". For these:
  - If the date is a numeric range like "c. 885–835 BC", parse as
    `{start_bce: -885, end_bce: -835, approximate: true}`
  - If the date is prose ("2nd half of 7th cent. BC"), leave
    `start_bce` and `end_bce` null and put the prose in `note`
  - AD dates in IV.3 (late Meroitic rulers) become positive integers

## Output schema

```json
{"kind": "period",  "label": "string", "start_bce": int|null, "end_bce": int|null, "approximate": bool, "uncertainty_plus_years": int|null, "page": int}
{"kind": "dynasty", "number": int|null, "label": "string", "start_bce": int|null, "end_bce": int|null, "approximate": bool, "uncertainty_plus_years": int|null, "parent_period": "string", "page": int}
{"kind": "ruler",   "display": "string", "greek_form": "string"|null, "alternative_reading": "string"|null, "prenomen": "string"|null, "start_bce": int|null, "end_bce": int|null, "approximate": bool, "uncertainty_plus_years": int|null, "dynasty": int|null, "page": int, "note": "string"|null}
```

For dynasty headings that are not plain integers (Hyksos, Theban Dyn.
11, Dyn. 23 UE/LE, 2nd Persian Period), use the simplest integer you
can and put the qualifier in `label`. For "2nd Persian Period",
"Alexander the Great", and other non-dynasty rows that appear at the
dynasty level, use `kind: "period"` with `number: null` on the
dynasty row or treat as period — whichever matches the bold styling
in the PDF.

## Output rules

- One JSON object per line, no commentary, no markdown fences
- Preserve the order of the PDF (rows in reading order)
- Do not invent dates or names. If a cell is ambiguous or you cannot
  read it, emit `null` and add a `note` field explaining
- Preserve diacritics (ʿ, ʾ, ' for ayin/alef) exactly as shown in the
  PDF. The PDF uses ' for ayin and ' for alef — copy them verbatim
