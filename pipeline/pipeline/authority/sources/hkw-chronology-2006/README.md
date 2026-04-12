# Hornung/Krauss/Warburton (2006) — Chronological Table

Source: Hornung, E., Krauss, R., & Warburton, D. A. (Eds.). (2006).
*Ancient Egyptian Chronology*. Handbook of Oriental Studies, vol. 83.
Leiden: Brill. Sections IV.2 and IV.3 (pp. 490–498).

## Layout

```
pipeline/pipeline/authority/sources/hkw-chronology-2006/   # committed
  README.md        — this file, explaining source and workflow
  prompt.md        — the transcription prompt for Claude/Gemini/GPT
  reconciled.jsonl — final reconciled transcription (source of truth)
proprietary/hkw-chronology-2006/                           # gitignored
  hkw-iv-2-iv-3.pdf — excerpted source PDF (Brill copyright)
  claude.jsonl    — Claude's raw transcription pass
  gemini-raw.json — Gemini's raw transcription (different schema)
  gpt-raw.json    — GPT's raw transcription (different schema)
  compare.py      — local diff script used during reconciliation
  reconciliation-report.md — notes from the reconciliation pass
```

The PDF itself is Brill copyright and stays under `proprietary/` —
it cannot be committed. The raw per-model transcriptions also live
under `proprietary/` to minimise copyright surface area; they are
regeneratable by re-running the models against the PDF if ever
needed.

The reconciled transcription IS committed. It is a thin-copyright
derivative — structured facts (ruler names, date ranges, dynasty
assignments) extracted from the table, reorganized into JSONL with
per-row notes. The repo is private, so this is analogous to a
private research notebook. **If this repo is ever made public, this
file must be scrubbed first** (see the gitignore header in the
repo root).

The final curated authority files (`dynasties.json`, `periods.json`,
`rulers.json`) will sit directly in `pipeline/pipeline/authority/`
once derived from `reconciled.jsonl` — those are facts about ancient
Egypt, not creative expression, and are committable in a public repo
with `_source` blocks citing this PDF and its page numbers.

## Table structure

Section IV.2 is the consensus dynastic chronology (Early Dynastic →
Alexander the Great). The table is a three-column layout:

1. **Column 1** — either a period label (bold), dynasty label (bold),
   or a ruler name. Italics in column 1 indicate the ruler's prenomen
   (throne name). Parentheses after a name are Greek forms (e.g.
   "Khufu (Cheops)"). Square brackets are alternative readings.
2. **Column 2** — `ca.` marker when dates are approximate.
3. **Column 3** — date range in BCE, possibly with a superscript `+N`
   error bar (e.g. `2900–2545⁺²⁵` means ±25 years).

Section IV.3 is a separate table of Kushite rulers (pre-25th dynasty,
25th dynasty, Napatan and Meroitic). **Out of scope for this first
transcription pass** — the 25th dynasty rulers are already covered in
IV.2, and everything else (Napatan, Meroitic) falls outside Hapi's
ancient Egyptian remit. If we later decide to model Nubian material,
IV.3 can be transcribed as a follow-up using the same schema with a
separate source file.

## Known transcription ambiguities

These are rows where the source data is itself ambiguous, multi-valued,
or hard to fit into the flat schema. Flagged here so the reconciliation
pass can decide how to handle them rather than re-discovering them
each round.

- **Dyns. 16 and 17 combined header.** HKW prints a single bold header
  "Dyns. 16 and 17" covering both dynasties. Claude's pass labels the
  dynasty row with `number: 16` and splits the rulers between
  `dynasty: 16` (Sobekemhotep VIII et al., a multi-ruler line) and
  `dynasty: 17` (Inyotef, two Ta'os, Kamose). Gemini and GPT may
  pick differently; the reconciliation pass should decide whether
  `number` on the combined header is `null`, `16`, or two separate
  rows
- **Dyn. 23 (UE) vs Dyn. 23 (LE).** Two separate dynasty headers
  both numbered 23 — one for Upper Egypt, one for Lower Egypt. Both
  kept with `number: 23` and distinguished by `label`
- **Multi-ruler rows** (`"Swadjtu, Ined, Hori, Dedumose"`,
  `"Sobekemhotep VIII, Nebiriau, Rahotep, Sobekemzaf I & II, Bebiankh"`,
  `"Shoshenq IV, Rudamun, Iny"`, `"Petubaste II (?), Osorkon IV"`) are
  kept as single JSONL rows matching the PDF layout. The final
  `rulers.json` authority file will almost certainly want them
  expanded one-ruler-per-entry; that's a reconciliation decision
- **`"Osorkon III, Takelot III"`** is shown with `ca. 780 ± 20` — a
  midpoint with symmetric uncertainty rather than a range. Claude's
  pass interprets this as `start_bce: -800, end_bce: -760,
  uncertainty_plus_years: 20`. This is an interpretation, not a
  verbatim reading; reconciliation should verify
- **`"Dyn. 8" ruler Neferirkare'`** — the PDF text layer and visual
  rendering both show `2119–2218+25`, which is chronologically
  impossible (a 99-year reign running backwards through time).
  Verified against Baud's chapter II.5 "The Relative Chronology of
  Dynasties 6 and 8" (same volume, pp. 144-158): the entire Dyn. 8
  spans "about one generation" (~20-25 years, at most ~50 years),
  and individual Dyn. 8 reigns run 1-4 years. Reconciled to
  `2119–2118+25` (1-year reign at dynasty end). The `2218` is
  almost certainly a Brill typesetting error for `2118`. Flagged
  in the row's `note` field

## Transcription workflow

Per the normalization plan, the chronology table is transcribed
*three* times — once each by Claude, Gemini, and GPT — and the three
JSONL outputs are diffed. Any row where the three disagree on
`start_bce`, `end_bce`, dynasty assignment, or ruler display name is
flagged for manual check against the PDF.

Outputs:

- `claude.jsonl` — this repo's Claude pass
- `gemini.jsonl` — Gemini pass (run by human operator)
- `gpt.jsonl` — GPT pass (run by human operator)
- `reconciled.jsonl` — final authoritative transcription

The schema and the exact prompt given to each model are in `prompt.md`
so the three runs are directly comparable.

## Schema (one row per table entry)

All rows share a discriminator `kind` field:

```json
{"kind": "period",  "label": "Old Kingdom",   "start_bce": -2543, "end_bce": -2120, "approximate": true,  "uncertainty_plus_years": 25, "page": 490}
{"kind": "dynasty", "number": 4, "label": "Dyn. 4",               "start_bce": -2543, "end_bce": -2436, "approximate": true,  "uncertainty_plus_years": 25, "parent_period": "Old Kingdom", "page": 490}
{"kind": "ruler",   "display": "Khufu", "greek_form": "Cheops",   "prenomen": null,   "start_bce": -2509, "end_bce": -2483, "approximate": false, "uncertainty_plus_years": 25, "dynasty": 4, "page": 491, "note": null}
```

### Field semantics

- `kind` — `"period"`, `"dynasty"`, or `"ruler"`
- `label` — column 1 text as printed (period/dynasty rows only)
- `display` — column 1 non-italic text (ruler rows only), stripped of
  parentheses and brackets. Greek forms and alternative readings go
  into their own fields
- `greek_form` — text inside parentheses after a ruler name (e.g.
  `"Cheops"` for Khufu). `null` when absent
- `alternative_reading` — text inside square brackets (e.g. `"Piye"`
  for Piankhi in IV.3). `null` when absent
- `prenomen` — italicized text in column 1 for ruler rows (e.g.
  `"Menkheperre"` for Thutmose III). Multiple prenomen variants
  separated by `/` in the PDF are preserved as a single string with
  `/` as separator. `null` when absent
- `start_bce` / `end_bce` — negative integers (2543 BCE → `-2543`).
  `null` when the PDF shows `?` for that bound
- `approximate` — `true` if column 2 has `ca.` for this row
- `uncertainty_plus_years` — the `+N` superscript (25, 16, 3, or
  `null` if absent)
- `dynasty` — integer for ruler rows, linking to the parent dynasty
- `parent_period` — string for dynasty rows, linking to the parent
  period header
- `page` — integer page number in the PDF excerpt (490, 491, 492,
  493, 494, or 495 for IV.2; 496, 497, 498 for IV.3)
- `note` — free text for anything the schema can't capture (joint
  rulers, co-regencies, multi-ruler dynasty 14 lines like
  `"Swadjtu, Ined, Hori, Dedumose"`)
