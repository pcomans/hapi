# Beckerath 1997 — *Chronologie des pharaonischen Ägypten*, MÄS 46

Source of truth for the BCE chronology of Egyptian rulers from the predynastic period through Dynasty 31 (332 BCE). Beckerath gives explicit **high / low alternative endpoints** for almost every reign — a defining feature of his chronology that no other Phase-0 source captures.

## Citation

Beckerath, Jürgen von (1997) *Chronologie des pharaonischen Ägypten: Die Zeitbestimmung der ägyptischen Geschichte von der Vorzeit bis 332 v. Chr.* Münchner Ägyptologische Studien 46. Mainz am Rhein: Philipp von Zabern. ISBN 3-8053-2310-7.

- **Edition used:** 1st edition, von Zabern 1997.
- **Retrieved:** 2026-04-25 (local scan in `proprietary/`).
- **PDF SHA-256:** `f407eb4123872d875cb80590a2e840a50069c3596b06f79146a13e170968ca1c` (also pinned in `transcribe.md`).

## Scope

Part III. Anhang, Section A — *Chronologische Übersicht über die Geschichte Altägyptens*, printed pp. 187–193 (physical PDF pp. 105–108). Plus the *Supplement zu A* on printed pp. 193–194 (physical PDF pp. 108–109) which lists the full Egyptian titularies (Thron- + Eigenname) for kings of Dynasties 19–23 — the Übersicht itself shortens these.

**Explicitly excluded:**

- **Anhang B** (printed pp. 195–196, PDF p109) — *Tabelle zur Umrechnung julianischer in gregorianische Daten* (calendar-conversion, not chronology).
- **Anhang C** (printed p197+, PDF p110+) — *Tabelle zur Veranschaulichung der Verschiebung des ägyptischen Kalenders gegenüber dem julianischen* (calendar-drift, not chronology).
- **Tabellen 1–11** (printed throughout the body chapters, PDF pp. ~10–100) — per-period summary tables. They reproduce subsets of Anhang A with extra prose; we extract the synoptic table once and avoid double-counting.
- **Index der Königsnamen** (printed pp. 231+) — name-form index, not chronology.

**Coverage end:** Beckerath stops at 332 BCE (Alexander's conquest). No Ptolemaic, no Roman period.

**Expected row count:** ~225 rulers across Dynasties 0–31. Parallel sub-lines that Beckerath structurally separates *within* the Übersicht: Dyn 22 *Oberägyptische Linie* (`sub_line: "Oberägyptische Linie"`). Dyn 16 *Hyksos-Vasallen* are Beckerath's own Dyn 16 (`dynasty: 16`), not a sub-line of Dyn 15. Dyn 21 has **no separate Theban HPA column** in the Übersicht — only two HPA names appear in a tail paragraph of *Supplement zu A* and we capture those as Dyn-21 rows with a `sub_line: "Hohepriester"` marker, not a Kitchen-style parallel stream.

## Schema

Field order in this section is the on-disk JSONL order (`json.dumps(..., sort_keys=True)` — strict alphabetical at every nesting level), so a reader can scan the example top-to-bottom against any committed row.

```json
{
  "beckerath_id": "01.01",
  "dynasty": 1,
  "editorial_notes": null,
  "egyptian_titulary": "Hor Aha",
  "egyptian_titulary_kind": "horus_name",
  "end_approximate": true,
  "end_bce_high": -3000,
  "end_bce_low": -2950,
  "name": "Menes",
  "notes_from_beckerath": null,
  "period": "Frühzeit",
  "prenomen": null,
  "sequence_in_dynasty": 1,
  "source_citation": {"edition": "MÄS 46, von Zabern 1997", "pdf_pages": "105-109"},
  "start_approximate": true,
  "start_bce_high": -3032,
  "start_bce_low": -2982,
  "sub_line": null
}
```

- `beckerath_id` = `"{dyn:02}.{NN:02}"` zero-padded. Sequence is continuous within the dynasty, regardless of `sub_line` (i.e. Dyn 22 main + Oberägyptische Linie share one numbering 22.01 → 22.NN). Predynastic anchor is `"00.01"`.
- `dynasty` = integer 0..31. Beckerath uses `0. Dynastie` for the predynastic anchor; Dyn 16 is the *Hyksos-Vasallen* dynasty (Beckerath's own labelling), not a sub-line of 15.
- `editorial_notes` = nullable string for free-text editorial commentary added during transcription/review that is NOT in Beckerath's text. Examples: cross-row context discovered during scan review (`"shared bracket range with Sôuphis, Mesochris (03.05) and Ahu (Huni, Aches) (03.06) (scan-105)"`), explicit cross-references in English (`"co-regent with Si-ptah (19.07)"`). When referencing sister rows, use the row's canonical `name` field plus its `beckerath_id` in parentheses so a downstream consumer can grep-resolve. Null when absent.
- `egyptian_titulary` = the parenthetical Egyptian-language royal name Beckerath gives in the Übersicht. Heterogeneous: in Dyn 1–3 it is typically the Horus name (`"Hor Aha"` for Menes); in Dyn 4 the Eigenname/nomen (`"Chufu"` for Cheops); in Dyn 18+ frequently the Thronname/prenomen (`"Nefer-cheprurê wa-en-rê"` for Akhenaten). Preserve verbatim. Null when Beckerath gives none.
- `egyptian_titulary_kind` ∈ {`"horus_name"`, `"nomen"`, `"prenomen"`, `"mixed"`, `null`}. Records *what kind* of name Beckerath put in the parenthetical. Use `"horus_name"` when the parenthetical begins with `Hor` or contains a Horus-name pattern; `"prenomen"` when it ends with `-rê` / `-rî` (cartouche-style throne name); `"nomen"` otherwise; `"mixed"` when Beckerath gives both (Dyn 19–20 Supplement format). Null when `egyptian_titulary` is null.
- `end_approximate` / `start_approximate` = booleans. True when Beckerath prefixes the corresponding endpoint with `ca.` / `etwa` / `vor` / `nach` / `um` / hedges with `"?"`, OR when the row sits in a section Beckerath introduces with `"etwa N Jahre"` (e.g. Dyn 0 *ungefähr 150 Jahre*). Otherwise false. **Dyn 0** has no numeric endpoints — set both `*_bce_*` to null and both `*_approximate` to true with `notes_from_beckerath: "ungefähr 150 Jahre"`.
- `end_bce_high` / `end_bce_low` / `start_bce_high` / `start_bce_low` = negative integers, individually nullable. Beckerath writes `"3032/2982–3000/2950"` meaning start-range 3032 BCE high / 2982 BCE low → end-range 3000 BCE high / 2950 BCE low. When Beckerath gives a single endpoint (e.g. `"ca. 880"`) populate both high and low with the same value. When only one half of a slash pair is given (e.g. `"1186/85–1183/82"` where the right-hand side is a 2-digit short form for `1185`), expand to the full 4-digit year. **Mixed-certainty rules:**
  - `vor ca. 746` (terminus ante quem on a single endpoint) → `start_bce_high: null, start_bce_low: null, start_approximate: true, end_bce_high: -746, end_bce_low: -746, end_approximate: true, notes_from_beckerath: "vor ca. 746"`.
  - `664–ca.655` (per-endpoint certainty differs) → `start_bce_high: -664, start_bce_low: -664, start_approximate: false, end_bce_high: -655, end_bce_low: -655, end_approximate: true`.
  - `ca. 837–798 (785?)` (alternative endpoint in parens) → `start_approximate: true, end_bce_high: -798, end_bce_low: -798, end_approximate: false, notes_from_beckerath: "alternative end 785"`.
  - `Herbst 1337–1333` (season prefix) → drop "Herbst" from numeric fields; record in `notes_from_beckerath: "Herbst 1337"`.
  - `31.5.1279` (day.month.year accession date) → record full date in `notes_from_beckerath: "Antritt 31.5.1279"`; numeric endpoint is `-1279`.
- `name` = Beckerath's main rendering of the king's primary identifier (typically the Greek/manethonic form, e.g. `"Menes"`, `"Cheops"`, `"Schoschenq I."`). Preserve diacritics and capitalisation verbatim.
- `notes_from_beckerath` = free-text string for per-row annotations Beckerath adds *in the Anhang A cell itself* (e.g. `"Mitregent"`, `"in Sais"`, `"Antritt 31.5.1279"`, `"Herbst 1337"`, `"Gegenkönig der 3 vorigen"`). Null when absent. Per Constitutional rules 1 and 6 (raw data is sacred), this field must contain ONLY Beckerath's verbatim cell text — no editorial commentary, scan-context tags, agent meta-prose, or English paraphrase. Editorial commentary belongs in `editorial_notes`.
- `period` ∈ {"Vorgeschichte", "Frühzeit", "Altes Reich", "I. Zwischenzeit", "Mittleres Reich", "II. Zwischenzeit", "Neues Reich", "III. Zwischenzeit", "Spätzeit"}. Drives from Beckerath's italicised section headings within Anhang A. *Note:* `"Vorgeschichte"` truncates Beckerath's full heading `VORGESCHICHTE (PRÄDYNASTISCHE ZEIT)` for brevity; the parenthetical is dropped.
- `prenomen` = the Thronname when Beckerath gives one *in addition to* the Übersicht parenthetical (i.e. the Supplement zu A pulls in an extra prenomen for Dyn 19–23 kings). Null otherwise.
- `sequence_in_dynasty` = integer `NN`, 1-indexed continuously within the dynasty.
- `source_citation` = constant object identifying the print source for every row in this JSONL: `{"edition": "MÄS 46, von Zabern 1997", "pdf_pages": "105-109"}`. Same value on every row — Anhang A + Supplement zu A together span PDF pp. 105–109 of the pinned scan (see *Citation* and *Scope* above). `edition` is the verbatim Citation-block string; `pdf_pages` is the physical-PDF page span (not the printed page numbers, which are 187–194). Not nullable.
- `sub_line` = nullable string. `null` for the main line. Set to `"Oberägyptische Linie"` for Dyn 22 OAL kings (Har-si-ëset → Ini), and to `"Hohepriester"` for the two HPA names appearing in the *Supplement zu A* tail paragraph (PDF p.109). No other sub-lines exist in Beckerath's Anhang A.

**Dyn 2 *Gegenkönig* row.** Beckerath prints a composite annotation `Gegenkönig der 3 vorigen: Seth Per-ib-sen / Hor-Seth Cha-sechemui` spanning two physical name lines. Extract as **two rows** — `02.NN` Seth Per-ib-sen and `02.NN+1` Hor-Seth Cha-sechemui — with `notes_from_beckerath: "Gegenkönig der 3 vorigen"` on both, both sharing Beckerath's bracketed date range covering the 3 contested kings.

## Rights

von Zabern 1997 (in copyright). This extract contains only factual data — king names, Egyptian titulary transliterations, BCE date endpoints (high/low), dynasty numbers, period labels. Beckerath's argumentation, prose analysis, footnotes, and the book's substantive chapters are not reproduced. Per ADR-017 the source PDF is not committed; per-page OCR markdown in `raw/` is not committed (gitignored via `pipeline/pipeline/authority/sources/*/raw/chunk-*.md`).

## Method

Per ADR-017 (Claude Code subagent OCR → three-subagent structured extraction → deterministic majority-vote merge → LLM reviewer pass). See `transcribe.md` for the specific protocol applied to Beckerath.

**Review.** The `egyptologist-reviewer` Claude Code subagent walks `merge-disagreements.txt` against the PDF and flags rows where the majority vote is wrong; overrides are recorded under `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED` at the bottom of `merge-disagreements.txt`. **A human Egyptologist sign-off pass has NOT been performed** — the extract is provisional until that happens.

## Known gaps / Phase A notes

- **Anhang A is the synoptic table; per-period Tabellen 1-11 are not separately extracted.** Beckerath's body chapters reproduce subsets of Anhang A with additional commentary; the synoptic Übersicht is the canonical source we extract.
- **Index der Königsnamen (printed pp. 231+) not extracted.** Cross-reference index, useful for name-form variants in Phase A but not chronology.
- **Beckerath stops at 332 BCE.** The Ptolemaic and Roman periods come from other sources (pharaoh.se for now; eventually Hölbl 2001 / Pfeiffer 2010 for Ptolemaic and a Roman-imperial source for emperors-as-pharaohs).
- **Plural-chronology consumer.** Per ADR-017's revised ruler-chronology architecture, Beckerath becomes the **lead** chronology in `rulers.json::chronologies.beckerath_1997`, with Hornung/Krauss/Warburton 2006 as **fallback** (`chronologies.hkw_2006`). The merge phase that fuses these per-ruler sits in `pipeline/authority/build_rulers.py` and is downstream of this transcription.
