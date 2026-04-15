# Kitchen 1996 — *The Third Intermediate Period in Egypt (1100–650 BC)*, 3rd ed.

Source of truth for the Third Intermediate Period (Dyns 21–25) king list — Kitchen's **Preferred-Dates** chronology with regnal lengths, polity assignments, and Tanite↔Theban-HPA concurrency.

## Citation

Kitchen, K. A. (1996) *The Third Intermediate Period in Egypt (1100–650 BC)*, 3rd ed. with new preface. Warminster: Aris & Phillips. ISBN 0-85668-001-X / 978-0856682988.

- **Edition used:** 3rd ed. reprint, 1996 (the version Aris & Phillips issued with a new preface over the 2nd-ed. 1986 text plus 1st-ed. 1973 body).
- **Retrieved:** 2026-04-14 (local scan in `proprietary/`).
- **PDF SHA-256:** `18605ca79b5dbd0149280e243ef4219f557c5603305796d51ad17a25e3bf42bb` (also pinned in `transcribe.md`).

## Scope

Part VI, Section I — *Dates of Kings* (Tables 1, 3, 4), printed pp. 465–468 (physical PDF pp. 240–243).

- **Table 1** — *Preferred Dates: 'Renaissance Era', 21st Dynasty, and Theban Pontiffs.* Tanite kings (Smendes I → Psusennes II) alongside the parallel line of Theban High Priests of Amun (Herihor → Psusennes 'III'), plus Ramesses XI / 'Renaissance Era' at the top.
- **Table 3** — *The 22nd and 23rd Dynasties.*
- **Table 4** — *The 24th–26th Dynasties* (Early Saite Princes, 24th, Proto-Saite, 25th Nubian, 26th Saite).

**Explicitly excluded:**

- **Table 2** — *Alternative Dates* for Dyn 21 + Renaissance Era. Kitchen presents this as a competing chronological hypothesis covering the same kings already in Table 1. Including both would double-count rows. Table 2 content is preserved via a README note; Phase A can layer it as an alternative-dates overlay if a curator wants to expose both hypotheses.
- **Tables 5–6** (Ready-reckoners for contemporaneous regnal years). Useful for Phase A concurrency work but add no new kings.
- **Tables 7–12** (Royal Genealogies). Graph-shaped data; belongs in a separate queen / royal-family transcription (Dodson-Hilton 2004 is the Phase 0 source for genealogies).
- **Tables 13–23** (Chief Dignitaries). High Priests of Ptah, Theban 2nd/3rd/4th Prophets, viziers, Delta chiefs — officials, not rulers.
- **Table 24** (Near-Eastern contemporary rulers). Non-Egyptian.

**Kitchen 2009 revisions are a separate source (not this PR).** The mvp-tasks catalogue treats "Kitchen 1996 + 2009 revisions" as a combined slot; per ADR-017 and the focused Phase 0 execution plan, Kitchen's own 2009 reassessments (Broekman/Demarée/Kaper eds. *The Libyan Period in Egypt*) land in `sources/kitchen-2009-libyan/` as a revisions-only delta that supersedes specific rows from this source. Aston 1989 (*JEA* 75) and Jansen-Winkeln *Inschriften der Spätzeit* are further Phase 0 sources for TIP revisions.

**Expected row count:** ~55–65 rulers. Our three-subagent extraction produced 60 rows across:

| Stream | `kitchen_id` prefix | dynasty | rows | polity |
|---|---|---|---|---|
| 'Renaissance Era' | `20.*` | 20 | 1 | Tanite (late Dyn 20) |
| 21st Dynasty (Tanite kings) | `21.*` | 21 | 7 | Tanis |
| Theban HPAs (Dyn 21) | `21H.*` | 21 | 10 | Theban (HPA) |
| 22nd Dynasty | `22.*` | 22 | 11 | Tanis / Bubastis |
| 23rd Dynasty | `23.*` | 23 | 8 | Theban / Leontopolite |
| Early Saite Princes (pre-Dyn 24) | `24E.*` | 24 | 4 | Sais (Mā) |
| 24th Dynasty | `24.*` | 24 | 2 | Sais |
| Proto-Saite Dynasty | `24P.*` | 24 | 4 | Sais |
| 25th Dynasty | `25.*` | 25 | 7 | Nubia / Napata |
| 26th Dynasty | `26.*` | 26 | 6 | Sais |

Dyn 26 sits beyond the book's formal 1100–650 BC scope but Kitchen includes it in Table 4; we preserve verbatim rather than split the table. Dyn 20 (Ramesses XI) is similarly captured because Table 1 opens with it — the 'Renaissance Era' anchors the Dyn 21 chronology.

## Schema

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
  "notes_from_kitchen": null,
  "source_citation": {"pdf_pages": "240-243", "edition": "Aris & Phillips 3rd ed. 1996"}
}
```

- `kitchen_id` = `"{prefix}.{NN}"` zero-padded two-digit sequence within the stream. Prefixes map to dynasty streams as above.
- `dynasty` = integer (20, 21, 22, 23, 24, 25, 26). For HPAs and Early-Saite/Proto-Saite streams we record the dynasty Kitchen places them in (21 for HPAs; 24 for both Early-Saite Princes and Proto-Saite).
- `sequence_in_dynasty` = the `NN` integer, 1-indexed within the stream.
- `name` = Kitchen's anglicised form from the table cell, including Roman-numeral disambiguators (e.g. `"Shoshenq I"`, `"Psusennes 'III'"`, `"Necho I"`).
- `prenomen` = Kitchen's anglicised prenomen when the table gives one (format `"{name}, {prenomen} (…)"`); null otherwise. Preserve Kitchen's own punctuation, including bracketed hedges like `"[Prenomen unknown]"`.
- `start_bce` / `end_bce` = negative integers (1 BCE → `-1`). Kitchen writes `"945–924"` meaning `945 BCE → 924 BCE` → `start_bce: -945, end_bce: -924`. If Kitchen gives only one endpoint (e.g. Alara `c. 780–760`) both are populated; if he gives a range opening with `c.` the value is still the numeric endpoint and `approximate: true`.
- `length_of_reign_years` = integer Kitchen gives in parentheses after the name (e.g. `(35 y)`). Null when absent. For hedged lengths like `"(c. 15 y?)"` the integer is the value (15) and `approximate: true`.
- `approximate` = true when Kitchen prefixes the date with `"c."` or hedges with `"?"` or `"??"` on the year value. Otherwise false.
- `polity` ∈ `{"Tanis"`, `"Theban (HPA)"`, `"Sais"`, `"Sais (Mā)"`, `"Nubia (Napata)"`, `"Leontopolis"`, `"Bubastis"`}`. Section headings within Tables 1/3/4 drive the value. Dyn 22 is split: Shoshenq I through Osorkon IV all sit in Kitchen's "22nd Dynasty" table with the main seat at Tanis/Bubastis; we tag all as `"Tanis"` for Phase 0 simplicity. Phase A disambiguates Bubastis vs Tanis using §§ 66–79 of Kitchen's prose. Harsiese A (22-Theban) is tagged `"Theban (HPA)"` because Kitchen explicitly marks him "co-rgt only" at Thebes (line in Table 3 "c. 870–860: Harsiese, Hedjkheperre Setepenamun (c. 10 y?; co-rgt only)"). Dyn 23 kings are tagged `"Leontopolis"` (the modern scholarly consensus; Kitchen's prose §§ 97–110 discusses Leontopolite placement).
- `concurrent_with_kings` = list of `kitchen_id` strings of contemporaries. Populated only for the Dyn 21 Tanite↔HPA pairs that Table 1 itself lays out horizontally. Left as `[]` for all other rows; cross-dynasty TIP concurrency (shown in Table 6 ready-reckoner) is deferred to Phase A. When Kitchen's printed `start_bce`/`end_bce` endpoints are internally inconsistent (currently only 21H.06 Djed-Khons-ef-ankh's "1046–1056"), concurrency is computed from the *intended* interval — not the verbatim endpoints — so the contemporaneity list reflects Kitchen's actual chronology rather than his typographic reversal. Corrected intervals for any such row are hard-coded at the top of `fix_rows.py`; the `end_bce` field itself stays verbatim.
- `notes_from_kitchen` = free-text string for per-row annotations Kitchen adds in the table cell (e.g. `"co-rgt only"`, `"existence, doubtful"`, `"Start of Dyn. 23."`). Null when absent.

## Rights

Aris & Phillips (in copyright 1996 reprint of 1973/1986 text). This extract contains only factual data — king names, prenomen transliterations, regnal lengths in years, BCE date endpoints, dynasty numbers, polity labels. Kitchen's argumentation, prose analysis, footnotes, and the book's substantive chapters are not reproduced. Per ADR-017 the source PDF is not committed; per-page OCR markdown in `raw/` is not committed (see `.gitignore` pattern `pipeline/pipeline/authority/sources/*/raw/chunk-*.md`).

## Method

Per ADR-017 (Claude Code subagent OCR → three-subagent structured extraction → deterministic majority-vote merge → LLM reviewer pass). See `transcribe.md` for the specific protocol applied to Kitchen.

**Review.** The `egyptologist-reviewer` Claude Code subagent walked `merge-disagreements.txt` against the PDF and flagged rows where the majority vote was wrong; overrides are recorded under `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED` at the bottom of `merge-disagreements.txt`. **A human Egyptologist sign-off pass has NOT been performed** — the extract is provisional until that happens.

## Known gaps / Phase A notes

- **Table 2 alternative dates not extracted.** Kitchen gives alternative dates for Dyn 21 + Renaissance Era that push each reign forward by ~20 years. We used Table 1 (Preferred Dates). Phase A can layer Table 2 as an alternative-dates overlay if scholarly dispute exposure is required.
- **Dyn 22/23 polity split deferred.** Bubastis vs Tanis for specific Dyn 22 kings (Shoshenq I's seat, etc.) and the Tanite/Leontopolite/Theban tri-partition of Dyn 23 are argued in Kitchen §§ 66–110 but not split in Tables 3/4. Phase A uses Kitchen's prose to refine `polity`.
- **Kitchen 2009 will supersede rows.** Several Table-3 kings (especially Osorkon II, Shoshenq III, and the early Dyn 22 positioning) have been revised by Kitchen himself in the 2009 Broekman/Demarée/Kaper volume. That source lands in a separate PR as a revisions-only delta. Until then, this extract represents Kitchen 1996 verbatim and should be treated as Kitchen's pre-2009 view.
- **Aston 1989 Dyn 22/23 length revisions not applied.** Aston reassigned several TIP reign-lengths (especially Shoshenq III → 39 y not 52 y) based on Karnak Priestly Annals re-readings. Same Phase-0 separation as Kitchen 2009 — a separate PR lands Aston deltas.
- **Jansen-Winkeln *Inschriften der Spätzeit* (2007–2014)** is the current working reference for TIP royal attestations and supersedes Kitchen on several titulary readings. Phase 0 source planned; not this PR.
- **Dyn 26 is technically out of TIP scope.** Kitchen includes Psammetichus I → Psammetichus III in Table 4 to close the 'lineage reconnection' narrative; we preserve verbatim. Phase A may drop them or reclassify once a Late-Period authority lands.
- **HPA numbering.** Kitchen's Table 1 interleaves the HPA column with the Tanite column rather than numbering HPAs independently. Our `21H.01`–`21H.10` ordering follows the top-to-bottom reading of the HPA column. Pinudjem I appears twice (as `"hp"` and as `"'kg'"`) so the stream has two entries for him (`21H.03` and `21H.04`); the `notes_from_kitchen` field records `"hp"` / `"'kg'"` respectively.
