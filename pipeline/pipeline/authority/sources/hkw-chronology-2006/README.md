# Hornung/Krauss/Warburton (2006) — Chronological Authority

Source: Hornung, E., Krauss, R., & Warburton, D. A. (Eds.). (2006).
*Ancient Egyptian Chronology*. Handbook of Oriental Studies, vol. 83.
Leiden: Brill.

**Extracted sections:**
- **IV.2 + IV.3** — the consensus dynastic chronology table (pp. 490–498). Produced the initial 203-row extract (periods, dynasties, Dyn-1 → Ptolemaic rulers with absolute BCE date ranges + ±25 yr error bars).
- **Ch 2 Hendrickx** — "Predynastic–Early Dynastic Chronology" (pp. 55–93). Added 3 Dyn-0 ruler rows (Iry-Hor, Ka, Scorpion I) to close the pharaoh.se U-j / Dyn-0 authority gap that was previously blocked on Dreyer 1998 *Umm el-Qaab I*.

## Layout

```
pipeline/pipeline/authority/sources/hkw-chronology-2006/   # committed
  README.md        — this file
  prompt.md        — schema and instructions used to produce reconciled.jsonl
  reconciled.jsonl — transcription of record (207 rows)
  raw/             — extraction working files (gitignored)
    chunk-ch2-p55-p93.txt — pypdf text-layer of Hendrickx Ch 2
proprietary/books/                                         # gitignored
  Hornung-Krauss-Warburton 2006 - Ancient Egyptian Chronology.pdf
    — full 530-page book, SHA-256 304a75ce18090cd683fc47650eaf5741dc73c9e4abdd8fbdc13dda707cd47c55
proprietary/hkw-chronology-2006/                           # gitignored
  (original extraction working files — pre-full-book era; historical)
```

Prior layout used an excerpted `hkw-iv-2-iv-3.pdf` (9 pages of the chronology table only). That excerpt has been superseded by the full book PDF at `proprietary/books/` and removed.

`reconciled.jsonl` is the transcription of record (**207 rows total**). The
initial 203 rows were produced by LLM transcription of HKW section IV.2
against the schema in `prompt.md`, with manual spot-checking against the PDF.
The 4 rows added from Hendrickx Ch 2 are: **1 Dyn-0 dynasty row** (`kind:
dynasty`, `number: 0`, page 88) plus **3 Dyn-0 ruler rows** — Iry-Hor (p.89),
Ka (p.89), Scorpion I (p.91) — at the top of the ruler section before the
Nar-mer row that opens Dyn 1. All 4 were hand-extracted from Hendrickx's
narrative prose and Tables II.1.6 (p.89) and II.1.7 (p.92) with explicit
per-row page citations.

The reconciled file is a thin-copyright derivative: structured facts
(ruler names, date ranges, dynasty assignments) reorganized into
JSONL with per-row notes. The repo is private, so this is analogous
to a private research notebook. **If this repo is ever made public,
this file must be scrubbed first** (see the gitignore header in the
repo root).

The PDF itself is Brill copyright and stays under `proprietary/` —
it cannot be committed.

The final curated authority files (`dynasties.json`, `periods.json`,
`rulers.json`) will sit directly in `pipeline/pipeline/authority/`
once derived from `reconciled.jsonl`. The intent is for those files
to contain only the factual data needed by the pipeline (ruler
names, date ranges, dynasty assignments), each row citing its
`_source` PDF and page number, so they can be included in any
eventual public release of the repo.

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
  "Dyns. 16 and 17" covering both dynasties. The reconciled file
  labels the dynasty row with `number: 16` and splits the rulers
  between `dynasty: 16` (Sobekemhotep VIII et al., a multi-ruler
  line) and `dynasty: 17` (Inyotef, two Ta'os, Kamose)
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
  pass interprets this as `start_year: -800, end_year: -760,
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

## Schema (one row per table entry)

All rows share a discriminator `kind` field:

```json
{"kind": "period",  "label": "Old Kingdom",   "start_year": -2543, "end_year": -2120, "approximate": true,  "uncertainty_plus_years": 25, "page": 490}
{"kind": "dynasty", "number": 4, "label": "Dyn. 4",               "start_year": -2543, "end_year": -2436, "approximate": true,  "uncertainty_plus_years": 25, "parent_period": "Old Kingdom", "page": 490}
{"kind": "ruler",   "display": "Khufu", "greek_form": "Cheops",   "prenomen": null,   "start_year": -2509, "end_year": -2483, "approximate": false, "uncertainty_plus_years": 25, "dynasty": 4, "page": 491, "note": null}
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
- `start_year` / `end_year` — negative integers (2543 BCE → `-2543`).
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
