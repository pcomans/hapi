# Handoff — Phase 0 Source Transcription

**Audience:** a Claude Code agent running locally on the user's machine (who has PDFs of the eleven source books listed below that the sandbox agent cannot access).

**Goal:** transcribe eleven Egyptological reference works into committed, reproducible `reconciled.jsonl` files under `pipeline/pipeline/authority/sources/`, so the Phase A authority-curation step can begin from a rigorous scholarly base (constitutional rule 1).

**Not your job:** curate `dynasties.json` / `periods.json` / `rulers.json` / `sites.json`. That is Phase A, done after these sources land. You are producing **raw material**, not the final authority files.

---

## Ground rules (read before starting)

1. **Read `CLAUDE.md` at the repo root first.** All twelve constitutional rules apply, especially:
   - **Rule 1 (Work like a scholar)** — every fact in every `reconciled.jsonl` row must trace to a specific page in the source book, cited in the row itself. No filling gaps from training data. If a page doesn't say something, don't invent it.
   - **Rule 2 (No defensive programming)** — raise on parse errors. No bare `try/except`.
   - **Rule 4 (Single source of truth)** — reconciled JSONL is a faithful extract of the book. If the book is wrong, we need the original to prove it. Don't "correct" facts.
   - **Rule 5 (Tests assert values)** — write structural tests that assert specific field values for at least 3 sampled rows per source.
2. **Also read `docs/harness.md`, `docs/adr/012-authoritative-sources.md`, `docs/mvp-tasks.md` section 3.1.** Note that ADR-012's `_source` block applies to the *curated authority files* (`periods.json`, `dynasties.json`, `rulers.json`, `sites.json`) — not to per-source `reconciled.jsonl` extracts. For each `reconciled.jsonl` you produce, citation lives in the per-row `source_citation` field specified in each source's schema below (with at minimum `{page, edition}`).
3. **One source = one PR = one branch.** Do NOT bundle multiple sources into a single PR. Branch name format: `feat/source-<short-slug>` (e.g. `feat/source-shaw-ohae`).
4. **Each source directory contains:**
   - `README.md` — citation, edition, ISBN, retrieved date, rights verification, method (OCR? manual typing? scraped PDF?), known quirks
   - `raw/` — the raw artifact you extracted from, **only if rights permit**. For most of these ten sources (all in-copyright academic books), commit **only a derived extract** (CSV of plain-text rows), not the book PDF. Document this in the README. Put a `raw/.gitkeep` if empty.
   - `transcribe.py` or `transcribe.md` — the reproducible method. If you wrote a script, commit it. If you typed by hand, write a short protocol describing exactly which pages, what fields, and how you normalised (whitespace, diacritics, etc.).
   - `reconciled.jsonl` — one JSON object per line, following the schema specified below for each source.
5. **Never redistribute copyrighted text you can't license.** Facts (king names, dates, tomb numbers, occupants) are not copyrightable and are the goal of the extract. Prose passages, tables-as-layout, and images are copyrightable; transcribe the facts without copying the book's prose wholesale. If in doubt, cite and paraphrase in a `source_note` field instead of copying.
6. **Every `reconciled.jsonl` row must carry a `source_citation` field** with at minimum `{page: int, edition: string}` so any reader can verify the row against the physical book.
7. **Language:** source material is in English (Shaw, Dodson-Hilton, Kitchen, Hölbl), French (Baud), or German (Beckerath). Transliterations and names in the source's original orthography — do NOT anglicise during transcription. Anglicisation is a Phase A concern (ADR-016). Your job is faithful extract.
8. **Work through the list in the order given below.** It's ordered by (a) ease and (b) unblocking power for Phase A. Stop and ship each PR before starting the next.

---

## Source 1 — Shaw (ed.) 2000, *The Oxford History of Ancient Egypt*

**Citation:** Shaw, I. (ed.) (2000) *The Oxford History of Ancient Egypt*. Oxford University Press. ISBN 978-0192804587.

**Target directory:** `pipeline/pipeline/authority/sources/shaw-ohae-2000/`

**What to transcribe:** the period date-ranges at the head of each of the 12 chapters. Each chapter opens with a banner or first paragraph stating the period name and its date range.

**Why:** Shaw gives chapter-level period boundaries that HKW does not enumerate as sub-periods (Amarna, Ramesside, Saite). Source of truth for sub-period spans in `periods.json`.

**Schema** — one row per chapter / period entry:

```json
{
  "period_name": "Naqada Period",
  "chapter_number": 3,
  "chapter_title": "The Naqada Period (c.4000-3200 bc)",
  "date_range_start_bce": -4000,
  "date_range_end_bce": -3200,
  "date_qualifier": "c.",
  "sub_periods": [
    {"name": "Naqada I (Amratian)", "start_bce": -4000, "end_bce": -3500},
    {"name": "Naqada II (Gerzean)", "start_bce": -3500, "end_bce": -3200}
  ],
  "source_citation": {"page": 41, "edition": "OUP 2000 hardback"}
}
```

If a chapter covers multiple periods or a period spans multiple chapters, use one row per period. If sub-periods are listed in the chapter opening, include them; otherwise `"sub_periods": []`.

**Expected row count:** ~12–16 rows (one per chapter, plus sub-periods).

**Rights:** OUP, in copyright. Commit only derived extract (the rows above are facts). Do not commit the chapter text itself. Note in README: "Shaw ed. 2000 is in copyright; this extract carries chapter titles and factual date ranges only; no prose is reproduced."

---

## Source 2 — Ryholt 1997, *The Political Situation in Egypt During the Second Intermediate Period*

**Citation:** Ryholt, K. S. B. (1997) *The Political Situation in Egypt During the Second Intermediate Period c. 1800–1550 B.C.* CNI Publications 20. Copenhagen: Museum Tusculanum Press. ISBN 87-7289-421-0.

**Target directory:** `pipeline/pipeline/authority/sources/ryholt-1997-sip/`

**What to transcribe:** Chapter 5 concurrency tables + File 1 (appendix: complete list of 13th–17th Dynasty kings with regnal-year attestations). The relevant pages are approximately 293–408 (File 1) and Chapter 5 text plus tables. Focus on the appendix tables — they are structured.

**Why:** source of truth for `polity` and `concurrent_with` on Dyns 13–17 in `dynasties.json`.

**Schema** — one row per king:

```json
{
  "ryholt_id": "13.17",
  "dynasty": 13,
  "sequence_in_dynasty": 17,
  "nomen": "Khendjer",
  "prenomen": "Userkare",
  "horus_name": "Djedkheperu",
  "nebty_name": null,
  "golden_horus_name": null,
  "regnal_years_attested": "at least 4 years 3 months",
  "date_bce_start": -1764,
  "date_bce_end": -1759,
  "polity": "Memphite",
  "concurrent_with": [],
  "source_citation": {"page": 340, "edition": "CNI Publications 20, 1997"}
}
```

For the 14th Dynasty (Xois) and 15th (Hyksos) overlap, Ryholt's concurrency tables will list which dynasties ran in parallel; populate `concurrent_with` with Ryholt's dynasty numbers as strings (`"14"`, `"15"`).

**Expected row count:** ~60–80 rows (all attested kings of Dyns 13–17).

**Rights:** CNI / Museum Tusculanum, in copyright. Extract facts only — king names, dates, polity assignments. Do NOT transcribe Ryholt's prose arguments.

---

## Source 3 — Kitchen 1996, *The Third Intermediate Period in Egypt*, 3rd ed.

**Citation:** Kitchen, K. A. (1996) *The Third Intermediate Period in Egypt (1100–650 BC)*, 3rd ed. with new preface. Warminster: Aris & Phillips. ISBN 978-0856682988.

**Target directory:** `pipeline/pipeline/authority/sources/kitchen-tipe/`

**What to transcribe:**
1. The **Summary Chronological Table** at the front of the book (lists all TIP rulers with dates, approximately pages xxix–xxxviii in the 3rd edition).
2. Any appendices that list rulers with dates.

**Why:** TIP chronology (Dyns 21–25), baseline for `dynasties.json` entries for those dynasties and for TIP rulers in `rulers.json`.

**Important:** Kitchen's 3rd edition (1996) has been revised by Kitchen himself — *use together with Source 10 (Kitchen 2009)*. Do not treat Kitchen 1996 as final; flag any date Kitchen 2009 revises.

**Schema** — one row per ruler:

```json
{
  "kitchen_id": "22.03",
  "dynasty": 22,
  "sequence_in_dynasty": 3,
  "name": "Osorkon I",
  "prenomen": "Sekhemkheperre Setepenre",
  "start_bce": -924,
  "end_bce": -889,
  "length_of_reign_years": 35,
  "approximate": false,
  "polity": "Tanis",
  "concurrent_with_kings": [],
  "notes_from_kitchen": "",
  "source_citation": {"page": "xxxi", "edition": "Aris & Phillips 3rd ed. 1996"}
}
```

**Expected row count:** ~40–50 rows (TIP rulers across Dyns 21–25, including parallel lines at Tanis / Leontopolis / Thebes).

**Rights:** Aris & Phillips, in copyright. Facts only.

---

## Source 4 — Dodson & Hilton 2004, *The Complete Royal Families of Ancient Egypt*

**Citation:** Dodson, A. & Hilton, D. (2004) *The Complete Royal Families of Ancient Egypt*. London: Thames & Hudson. ISBN 978-0500051283.

**Target directory:** `pipeline/pipeline/authority/sources/dodson-hilton-queens/`

**What to transcribe:** royal family members **other than kings already in pharaoh.se** — primarily Great Royal Wives (queens), Kings' Mothers, secondary consorts, heir-apparent princes, and princesses. The book has per-dynasty charts on (roughly) pages 20–267 and an index on ~270–295.

**Why:** pharaoh.se covers pharaohs only. The missing-queens gap (Nefertiti, Nefertari, Tiye, Ahmose-Nefertari, Ankhesenamun, etc.) closes here.

**Schema** — one row per non-king royal-family member:

```json
{
  "name": "Nefertiti",
  "alt_names": ["Neferneferuaten-Nefertiti", "Nefer-neferu-Aten Nefertiti"],
  "role": "Great Royal Wife",
  "spouse_name": "Akhenaten",
  "father_name": "Ay (probable)",
  "mother_name": null,
  "dynasty": 18,
  "career_start_bce": -1353,
  "career_end_bce": -1336,
  "approximate": true,
  "children_names": ["Meritaten", "Meketaten", "Ankhesenpaaten", "Neferneferuaten-tasherit", "Neferneferure", "Setepenre"],
  "notes": "Identification with the king Neferneferuaten disputed",
  "source_citation": {"page": 142, "edition": "Thames & Hudson 2004 hardback"}
}
```

**Priority for MVP:** Dyn 18 + Dyn 19 queens first (Ahmose-Nefertari, Hatshepsut-as-queen-consort, Tiye, Nefertiti, Ankhesenamun, Nefertari, Tausret). Then back-fill earlier/later dynasties.

**Expected row count:** ~150–250 rows across all dynasties; ~30 rows for MVP priority.

**Rights:** Thames & Hudson, in copyright. Facts (name, role, spouse, parentage, dates) are not copyrightable; the book's genealogical charts as visual compositions are. Extract facts into rows; do not reproduce chart images.

---

## Source 5 — Porter-Moss Vol I, *The Theban Necropolis*

**Citation:** Porter, B. & Moss, R. L. B. *Topographical Bibliography of Ancient Egyptian Hieroglyphic Texts, Reliefs, and Paintings. Volume I: The Theban Necropolis*. Oxford: Griffith Institute. (Vol I.1 = Private Tombs; Vol I.2 = Royal Tombs and Smaller Cemeteries.) Check the Griffith Institute website for the latest revised-edition PDFs and their licence terms before proceeding.

**Target directory:** `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/`

**What to transcribe:** the tomb index — KV1 through KV65, QV1 through QV~80 (those with known occupants), and selected TT tombs (TT1, TT52, TT55, TT69, TT96, TT100, TT279, TT353 at minimum; aim for the first ~40 with named occupants).

**Why:** iDAI.gazetteer has only 3 KV tombs and no TT tombs. This closes the Theban-tomb gap in `sites.json`.

**Schema** — one row per tomb:

```json
{
  "tomb_id": "KV62",
  "valley": "Valley of the Kings",
  "occupant_name": "Tutankhamun",
  "occupant_role": "King",
  "dynasty": 18,
  "date_bce_approx": -1323,
  "location_sub_area": "East Valley",
  "coordinates_lat": 25.7403,
  "coordinates_lon": 32.6014,
  "discovery_year": 1922,
  "discoverer": "Howard Carter",
  "source_citation": {"page": 569, "edition": "PM I.2 2nd ed. 1964 (or Griffith Institute revised edition 2012)"}
}
```

Coordinates: PM does not typically give decimal coordinates; use the Griffith Institute's revised PDF if it includes them, or mark `coordinates_lat: null, coordinates_lon: null` if the source doesn't provide them. Do not fabricate.

**Expected row count:** ~65 KV rows, ~20 QV rows, ~40 TT rows = ~125 total.

**Rights:** **Critical.** Griffith Institute publishes PM Vol I scans for free download under a restrictive redistribution licence. Facts (tomb numbers, occupants, dynasties) are not copyrightable in most jurisdictions. Layout and Moss's index prose are. In the README, document: (a) edition used, (b) licence terms of the PDF, (c) jurisdiction in which you are distributing the extract, (d) that the extract contains factual rows only. Commit only the `reconciled.jsonl` — not the PM PDF itself.

---

## Source 6 — Porter-Moss Vol III, *Memphis*

**Citation:** Porter, B. & Moss, R. L. B. (Málek, J. revision) *Topographical Bibliography … Volume III: Memphis*. Oxford: Griffith Institute, 2nd edition 1974–1981, with ongoing updates.

**Target directory:** `pipeline/pipeline/authority/sources/porter-moss-memphis/`

**What to transcribe:** the site index for Giza (III.1, pp. 1–310), Saqqara (III.2, pp. 391–897), Abusir (pp. 311–390), Dahshur (pp. 876–897), and Abu Roash (pp. 1–16 of III.1). Entries for each named tomb, mastaba, pyramid complex, and temple with their owner and dynasty.

**Why:** the three MVP museums (Met, Brooklyn, Harvard) hold substantial Memphite material that iDAI.gazetteer under-resolves. This closes that gap.

**Schema** — one row per named site/monument:

```json
{
  "monument_id": "G 7000X",
  "site": "Giza",
  "sub_area": "East Field",
  "type": "mastaba",
  "owner_name": "Hetepheres I",
  "owner_role": "Queen mother",
  "dynasty": 4,
  "date_bce_approx": -2600,
  "notes": "Shaft tomb, funerary equipment in Cairo CG 1-47",
  "source_citation": {"page": 179, "edition": "PM III.1 2nd ed. 1974"}
}
```

**Expected row count:** ~400–600 monuments for the priority sites. This is the largest source by row count. Scope down to named, attested monuments; skip small anonymous tombs unless they're held in the MVP-museum collections.

**Rights:** same as Vol I. Facts only.

---

## Source 7 — Baud 1999, *Famille royale et pouvoir sous l'Ancien Empire égyptien*

**Citation:** Baud, M. (1999) *Famille royale et pouvoir sous l'Ancien Empire égyptien*. Bibliothèque d'Étude (BdE) 126. Cairo: IFAO. 2 volumes.

**Target directory:** `pipeline/pipeline/authority/sources/baud-1999-ok-royal-family/`

**What to transcribe:** the prosopographical catalogue (volume 2) — entries for every attested Old Kingdom queen, king's son, king's daughter, and immediate-family member of Dyns 3–8. Each entry in Baud's catalogue is numbered.

**Why:** Dodson & Hilton is weaker for the Old Kingdom; Baud is the reference. Without this, OK consort coverage in `rulers.json` will be systematically thinner than NK/LP.

**Schema** — one row per family member (French source, keep French diacritics in names):

```json
{
  "baud_catalogue_number": 47,
  "name_transliterated": "Mérésânkh III",
  "name_egyptian": "mr.s-anx",
  "role": "Great Royal Wife",
  "spouse_name": "Khafra",
  "father_name": "Kawab",
  "mother_name": "Hetepheres II",
  "dynasty": 4,
  "date_bce_approx": -2500,
  "burial_monument": "G 7530-7540 (Giza East Field)",
  "notes_fr": "Fille de Kawab (fils aîné de Khéops) et de Hétep-hérès II",
  "source_citation": {"page": 444, "edition": "IFAO BdE 126, vol 2, 1999"}
}
```

**Expected row count:** ~500–700 entries (Baud's catalogue is comprehensive).

**Rights:** IFAO. Check https://www.ifao.egnet.net/publications/catalogue/BdE/ — IFAO has put many older BdE volumes into open-access; if BdE 126 is in the open-access tranche, note this in the README and commit a PDF link reference. Otherwise, facts-only extract with rights note.

---

## Source 8 — Beckerath 1999, *Handbuch der ägyptischen Königsnamen*, 2nd ed.

**Citation:** Beckerath, J. von (1999) *Handbuch der ägyptischen Königsnamen*, 2nd ed. Münchner Ägyptologische Studien (MÄS) 49. Mainz: Philipp von Zabern. German.

**Target directory:** `pipeline/pipeline/authority/sources/beckerath-1999-hak/`

**What to transcribe:** the titulary tables for every king — Horus name, Nebty name, Golden Horus name, prenomen, nomen, with Beckerath's ID number. This is a large reference; transcribe all kings from Dyn 1 through Dyn 31 (Ptolemaic is covered by other sources).

**Why:** pharaoh.se derives from Beckerath. Having the primary available means a curator can verify pharaoh.se entries or fill gaps where pharaoh.se is silent.

**Schema** — one row per king:

```json
{
  "beckerath_id": "18.9",
  "dynasty": 18,
  "sequence_in_dynasty": 9,
  "name_anglophone": "Amenhotep III",
  "horus_name": ["Ḫꜥ-m-mꜣꜥt"],
  "horus_name_translation": "Erscheinender in der Maat",
  "nebty_name": ["smn-ḥpw-sgrḥ-tꜣwy"],
  "golden_horus_name": ["ꜥꜣ-ḫpš-ḥw-sttjw"],
  "prenomen": ["Nb-mꜣꜥt-Rꜥ"],
  "nomen": ["Jmn-ḥtp-ḥqꜣ-Wꜣst"],
  "beckerath_notes_de": "",
  "source_citation": {"page": 141, "edition": "MÄS 49, 2nd ed. 1999"}
}
```

Keep transliterated Egyptian in its original Beckerath form (with ꜣ, ꜥ, etc.). German annotations in `beckerath_notes_de` stay German.

**Expected row count:** ~220–250 rows (all attested kings Dyns 1–31).

**Rights:** von Zabern / Wissenschaftliche Buchgesellschaft. In copyright. Names and titularies are factual; transcribe as rows. Do not reproduce Beckerath's commentary prose.

---

## Source 9 — Hölbl 2001, *A History of the Ptolemaic Empire*

**Citation:** Hölbl, G. (2001) *A History of the Ptolemaic Empire* (tr. T. Saavedra). London: Routledge. ISBN 978-0415201452.

**Target directory:** `pipeline/pipeline/authority/sources/holbl-2001-argead-ptolemaic/`

**What to transcribe:** the opening chronological table (lists Alexander III, Philip III Arrhidaeus, Alexander IV — the Argead bridge — and then the full Ptolemaic sequence). Chapter 1 covers the Argead period in detail; for the MVP focus on the chronological-table data.

**Why:** HKW stops at Alexander's conquest (332 BCE). pharaoh.se doesn't cover the Argead rulers. Hölbl's chronological table is the source for the 332–305 BCE bridge dynasty absent from other sources.

**Schema** — one row per ruler:

```json
{
  "holbl_sequence": 1,
  "name": "Alexander III (the Great)",
  "alt_names": ["Alexander the Great", "Alexandros III"],
  "period": "Argead",
  "start_bce": -332,
  "end_bce": -323,
  "status_in_egypt": "Conqueror; satrap of Egypt = Ptolemy I 323 onwards",
  "parentage": "Son of Philip II of Macedon and Olympias",
  "source_citation": {"page": "xx", "edition": "Routledge 2001 paperback"}
}
```

Also include Ptolemy I through Cleopatra VII and Caesarion from Hölbl's chronological table — this overlaps with the existing `wikipedia-ptolemaic` source but provides a second, scholarly-quality cross-reference. Transcribe and let Phase A reconcile.

**Expected row count:** ~20 rows (Argead 3 + Ptolemies 15 + major queens 5).

**Rights:** Routledge, in copyright. Facts only.

---

## Source 10 — Kitchen 2009, *The Libyan Period in Egypt* (Broekman/Demarée/Kaper eds.)

**Citation:** Kitchen, K. A. (2009) "The Third Intermediate Period in Egypt: An overview of fact and fiction," in G. P. F. Broekman, R. J. Demarée & O. E. Kaper (eds.) *The Libyan Period in Egypt: Historical and Cultural Studies into the 21st–24th Dynasties*. Egyptologische Uitgaven 23. Leiden: NINO. ISBN 978-90-6258-223-5.

**Target directory:** `pipeline/pipeline/authority/sources/kitchen-2009-tip-revisions/`

**What to transcribe:** Kitchen's own revisions to the 1996 TIPE chronology, specifically the dates and ordering changes he now accepts. Focus on his revised table if he provides one, and any explicit "read X for Y" statements. This source **supplements Source 3 (Kitchen 1996)** — produce a sibling JSONL of revisions rather than a complete new ruler list.

**Why:** Kitchen's 1996 3rd edition has been superseded on specific points by Kitchen himself. Committing only Kitchen 1996 would bake in a chronology he has revised. This source captures the deltas.

**Schema** — one row per revised entry. Structure as diffs against Kitchen 1996:

```json
{
  "kitchen_1996_ref": "22.06 Takeloth II",
  "revised_field": "dynasty_assignment",
  "kitchen_1996_value": "Dyn 22 (Tanite)",
  "kitchen_2009_value": "Dyn 23 (Theban/Upper Egyptian)",
  "rationale_summary_en": "Accepts the Aston 1989 argument that Takeloth II is a Theban ruler of the Upper Egyptian line, not a Tanite Dyn 22 ruler",
  "source_citation": {"page": 173, "edition": "NINO Egyptologische Uitgaven 23, 2009"}
}
```

**Expected row count:** ~10–30 revisions (Kitchen's 2009 paper is an overview, not a new ruler list).

**Rights:** NINO, in copyright. Facts only. In the README, note that this source is a delta layer — Phase A must apply these on top of Kitchen 1996.

---

## Source 11 — Dreyer 1998, *Umm el-Qaab I: Das prädynastische Königsgrab U-j*

**Citation:** Dreyer, G. (1998) *Umm el-Qaab I: Das prädynastische Königsgrab U-j und seine frühen Schriftzeugnisse*. Archäologische Veröffentlichungen (AV) 86. Mainz: Philipp von Zabern (for DAI). German.

**Target directory:** `pipeline/pipeline/authority/sources/dreyer-1998-umm-el-qaab/`

**What to transcribe:** the Dynasty 0 / late-Predynastic ruler list (Iry-Hor, Ka / Sekhen, Narmer) and the tomb U-j chamber catalogue of early script finds that carry ruler serekhs. Focus on Dreyer's synthesis tables that enumerate attested Dyn 0 rulers with their tombs and dates. Chapter II and the Abydos cemetery U catalogue are the relevant sections.

**Why:** Hendrickx in HKW Ch. 2 gives the Naqada seriation framework but does not enumerate the Dyn 0 ruler list. Dreyer is the reference for Iry-Hor, Ka, Narmer and the Abydos U-j tomb that anchors the Dyn 0 / early-writing chronology. Without this source the Dyn 0 entries in `dynasties.json` and the Dyn 0 rulers in `rulers.json` would have no scholarly backing.

**Schema** — one row per Dyn 0 ruler or attested serekh-bearer. Keep German annotations and the original transliteration (ꜣ, ꜥ, ḥ, etc.):

```json
{
  "dreyer_catalogue_ref": "U-j / Serekh A",
  "ruler_name_transliterated": "Iry-Hor",
  "ruler_name_alt": ["Jrj-Ḥr"],
  "attested_monuments": ["Abydos tomb B1/B2", "U-j ivory tags"],
  "tomb_id": "B1/B2",
  "cemetery": "Umm el-Qaab (Abydos)",
  "naqada_stufe": "IIIc1",
  "date_bce_approx_start": -3200,
  "date_bce_approx_end": -3150,
  "approximate": true,
  "notes_de": "Vorangehender Herrscher des Narmer-Horizonts; Serech auf Tonsiegelungen",
  "source_citation": {"page": 173, "edition": "AV 86, von Zabern 1998"}
}
```

Also include one or two rows for the U-j tomb itself as a monument / site entry — this will feed both `rulers.json` (the ruler) and `sites.json` (the monument via Abydos hierarchy).

**Expected row count:** ~5–12 rows (Dyn 0 rulers are few; the tomb catalogue adds a handful of anchor entries). Small but high-value — this source alone closes the Dyn 0 gap the sandbox agent had flagged as unresolved.

**Rights:** Philipp von Zabern / DAI. In copyright. **Before transcribing, check https://publications.dainst.org** — DAI has been putting older AV volumes into open-access PDF; AV 86 may be available under a Creative Commons licence. If so, note the licence in the README and commit the raw PDF reference. If not, facts-only extract.

**Language note:** Dreyer's text is in German. Transliterations of Egyptian names use standard Egyptological orthography (Jrj-Ḥr, Kꜣ, Nꜥr-mr) — preserve these in the JSONL. Do not anglicise; Phase A handles the display-name Anglophone convention (ADR-016).

---

## Workflow

For each of the eleven sources, in the order above:

1. **Create the branch.** `git checkout main && git pull && git checkout -b feat/source-<slug>` (e.g. `feat/source-shaw-ohae`).
2. **Scaffold the directory.** `mkdir -p pipeline/pipeline/authority/sources/<slug>/raw` and create `README.md`, `transcribe.py` or `transcribe.md`, `reconciled.jsonl`.
3. **Write the README first.** Citation, edition, ISBN, retrieved-date, rights verification, method. This forces you to think about rights before you start extracting.
4. **Transcribe.** Use OCR + manual verification for scanned PDFs, or direct copy-paste + normalisation for text PDFs. Whichever method, document it in `transcribe.md` step by step so a reviewer can reproduce.
5. **Validate.** Run the existing structural tests: `cd pipeline && uv run pytest tests/test_structure.py` should stay green (you're not touching tested files, but sanity-check). Write a source-specific test in `pipeline/tests/test_sources_<slug>.py` that loads your JSONL and asserts specific field values for 3 known rows (e.g. for Shaw, assert that the row for Predynastic has `date_range_start_bce == -4000`).
6. **Commit, push, open PR.** Title: `feat: transcribe <source short name> → sources/<slug>`. Body: cite the source, row count, pages covered, rights verification summary, any known gaps.
7. **Request Copilot review.** `gh pr edit <n> --add-reviewer @copilot`. Wait, reply to every comment on thread per `CLAUDE.md` PR workflow. Invoke the `scope-accountability-enforcer` subagent before the batch reply.
8. **Ensure CI green.** `gh pr checks <n> --watch`.
9. **Move to the next source only after the PR is merged.** Do not pile up eleven branches in parallel — a reviewer will drown.

---

## Constitutional enforcement you must not skip

- If you cannot find a fact in the source, **do not look it up elsewhere.** Leave the field null and add a `"source_note"` explaining what Shaw/Kitchen/Baud doesn't cover. That null is a known gap; a guess is a silent bug.
- If two sources disagree (e.g. Dodson-Hilton says Nefertiti's father is Ay, Beckerath implicit position is different), **do not reconcile.** Each source's extract records what that source says. Reconciliation happens in Phase A with every source visible side by side.
- If a book's edition number matters (Kitchen 1996 vs Kitchen 1986, Beckerath 1st vs 2nd ed.), the edition goes in every `source_citation` row. Page numbers without edition are worthless.
- Before committing any raw artifact, document the rights check in the README. If unclear, commit only the JSONL, not the raw PDF.

---

## Structural test additions (required)

When you finish all eleven sources, the final PR should add a parametrized test in `pipeline/tests/test_structure.py`:

```python
@pytest.mark.parametrize("source_dir", sorted(SOURCES_ROOT.iterdir()))
def test_source_reconciled_jsonl_has_citations(source_dir: Path):
    """Every source/*/reconciled.jsonl row must carry source_citation with page and edition."""
    jsonl = source_dir / "reconciled.jsonl"
    if not jsonl.exists():
        return  # dir may be a future source
    for i, line in enumerate(jsonl.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        assert "source_citation" in row, (
            f"{source_dir.name}/reconciled.jsonl row {i} missing source_citation. "
            f"Per ADR-012 and constitutional rule 1, every fact must trace to a page."
        )
        cit = row["source_citation"]
        assert cit.get("page") is not None and cit.get("edition"), (
            f"{source_dir.name}/reconciled.jsonl row {i} source_citation incomplete: "
            f"must have page and edition."
        )
```

This test will then enforce citation traceability for every source going forward.

---

## Minor gaps you are NOT expected to close

These remain as known gaps after your eleven-source push and will be handled by the sandbox agent:

- **Dynasty 7 / Manetho fragments** — Waddell 1940 / attalus.org. Sandbox agent can do this directly (public-domain digital text).
- **Aston 1989 JEA 75** — Kitchen 2009 (your Source 10) captures the revisions that matter.
- **Jansen-Winkeln *Inschriften der Spätzeit* 2007–2014** — 4-vol German reference; defer to post-MVP refinement if TIP royal attestation becomes a hot spot in the review queue.
- **Kaiser 1990 MDAIK 46** — Naqada Stufe terminology; covered adequately by Hendrickx in HKW Ch. 2 and now by Dreyer 1998 (your Source 11) for Dyn 0 seriation.

---

## Handoff back

When all eleven PRs are merged, post a single comment in the Hapi repo on a new issue titled `Phase 0 transcription complete` listing:
- The eleven PR numbers
- Total row counts per source
- Any rights-verification edge cases that ended up deferring a raw-artifact commit
- Any scholarly inconsistencies noted (e.g. spots where Baud and Dodson-Hilton disagree on a queen's parentage)

The sandbox agent will pick up from there and re-attempt Phase A with these sources as the ground truth.

---

## What this unblocks

Once Sources 1–11 land, Phase A (MVP section 3.2) can re-start with every structured fact in `dynasties.json`, `periods.json`, `rulers.json`, and `sites.json` traceable to a page in one of these books. That turns the authority layer from "model knowledge with citations" into "transcriptions with citations" — the difference between slop and scholarship (constitutional rule 1).

Thank you for doing this carefully.
