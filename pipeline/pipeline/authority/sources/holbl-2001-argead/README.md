# Hölbl 2001 — *A History of the Ptolemaic Empire* (Argead-dynasty bridge)

Source of truth for the three Argead-dynasty rulers of Egypt between the end of HKW 2006's Egyptian king-list coverage (which stops at Alexander) and the start of pharaoh.se's Ptolemaic coverage (which begins at Ptolemy I Soter's kingship, 306 BCE). The three Argead rulers — Alexander the Great, Philip III Arrhidaios, Alexander IV — are otherwise orphaned between those two authorities.

## Citation

Hölbl, G. (2001) *A History of the Ptolemaic Empire*. Translated by Tina Saavedra. London and New York: Routledge. ISBN 0-415-20145-4 (cased) / 978-0-415-20145-2. Translation of *Geschichte des Ptolemäerreiches* (© 1994, Wissenschaftliche Buchgesellschaft, Darmstadt).

- **Edition used:** Routledge 2001 English translation (reprinted 2001; transferred to digital printing 2010).
- **Retrieved:** 2026-04-16 (local scan in `proprietary/`).
- **PDF SHA-256:** `1a18600cb2c271a907a216304d6eed3f982b07adcccce30c3ded2a12ef6def4b` (also pinned in `transcribe.md`).

## Scope

Appendix *Overview of the events discussed in the history of the Ptolemaic kingdom*, the rubric-block for the Argead rulers: physical PDF pp. **348–351** (printed pp. 318–321).

Three rulers, in the order Hölbl's appendix presents them:

| `holbl_id`   | Ruler                     | Hölbl rubric            | Years      | Notes                                |
|--------------|---------------------------|-------------------------|------------|--------------------------------------|
| `argead.01`  | Alexander III (the Great) | ALEXANDER THE GREAT     | 332–323    | Entered Egypt end of 332             |
| `argead.02`  | Philip III Arrhidaios     | PHILIP III ARRHIDAIOS   | 323–317    | Ptolemy as Satrap                    |
| `argead.03`  | Alexander IV              | ALEXANDER IV            | 317–310/09 | Ptolemy as Satrap; murdered 310/309  |

**Explicitly excluded:**

- **INTERREGNUM (310/09–306)**. This is Hölbl's rubric label for the years between Alexander IV's murder and Ptolemy I's assumption of the royal title. It is NOT an Argead ruler — it is the interval in which Ptolemy (still styled Satrap) ruled Egypt de facto without an acknowledged Argead king. Excluded from this extract: neither an Argead nor a Ptolemaic ruler. The gap is real and not closed by this PR; Phase A may layer it as a political-interval record if a curator wants to expose it, but it does not belong in a ruler list.
- **Ptolemy I and all later Ptolemies.** `sources/pharaoh-se/` and `sources/wikipedia-ptolemaic/` cover Ptolemy I onward from his kingship in 306 BCE. Hölbl's table continues well past Alexander IV into the full Ptolemaic period; we stop at the Argead/Interregnum boundary to avoid double-authority.
- **Ptolemy I's satrapal years (323–306).** Hölbl annotates the Philip III and Alexander IV rubrics with "Ptolemy as Satrap" because Ptolemy is the de facto ruler of Egypt while those two are the nominal kings. The existing Ptolemaic authorities (pharaoh.se, wikipedia-ptolemaic) start at Ptolemy's kingship (306), not his satrapy — this is a deliberate separation. Ptolemy's satrapal role is captured in the `notes_from_holbl` field on `argead.02` / `argead.03`, not as its own row.
- **Hölbl's political / ideological / construction events columns.** The appendix is a three-column table (political events, history of ideology and religion, temple construction). We extract only the ruler rubric (who reigned when); the column content belongs in Phase A event / temple / ideology data, not in the ruler authority.

## Schema

```json
{
  "holbl_id": "argead.02",
  "name": "Philip III Arrhidaios",
  "alt_names": ["Philip Arrhidaeus", "Philip III"],
  "start_bce": -323,
  "end_bce": -317,
  "approximate": false,
  "polity": "Argead",
  "notes_from_holbl": "Ptolemy as Satrap of Egypt through this reign. Feeble-minded half-brother of Alexander the Great, acknowledged as joint king with the pregnant Roxane's possible son (under the name Philip).",
  "source_citation": {"pdf_pages": "348-351", "edition": "Routledge 2001"}
}
```

- `holbl_id` = `"argead.{NN}"` zero-padded two-digit sequence in the order Hölbl's rubric presents the three rulers.
- `name` = the ruler's common anglicised name following Hölbl's own spelling for this source (e.g. `"Philip III Arrhidaios"`, not `"Philip III Arrhidaeus"`).
- `alt_names` = other common spellings / forms a cross-reference might use (`"Alexander the Great"`, `"Alexander III"`, `"Philip Arrhidaeus"`). Populated for every row. **Provenance note:** the `alt_names` values are **scholarly-convention anglicisations**, not strings attested in Hölbl's rubric block itself. Hölbl prints only one form per ruler (`ALEXANDER THE GREAT`, `PHILIP III ARRHIDAIOS`, `ALEXANDER IV`); the Macedonian-numbered form for Alexander the Great (`Alexander III of Macedon`), the Latinised `Arrhidaeus`, and `Alexander IV Aegus` come from general Hellenistic-history scholarship, not from pp. 348–351. `source_citation.pdf_pages` refers to the **primary record** (name, dates, dynasty) not to the `alt_names` list. A human reviewer evaluating `alt_names` provenance should cross-check against a reference-grade prosopography (Berve 1926 *Das Alexanderreich*, *Prosopographia Ptolemaica*, or equivalent).
- `start_bce` / `end_bce` = negative integers. Hölbl writes `"332"` meaning `332 BCE → -332`. For the split-year form `"310/09"` on Alexander IV's end, we pick `-310` (the earlier of the two, matching Hölbl's "310/09: Murder of Alexander IV by Kassandros" entry placed immediately after the `310/09` year label) and set `approximate: true`.
- `approximate` = true when Hölbl hedges the year with a `/` (split-year), `c.` prefix, or `?`. True for `argead.03` because of `310/09`; false for `argead.01` and `argead.02` whose endpoints are unhedged single years.
- `polity` = `"Argead"` for all three rulers. This distinguishes them from the Ptolemaic rulers that follow in `sources/pharaoh-se/` and `sources/wikipedia-ptolemaic/`, and from any preceding Late-Period / Achaemenid rulers covered in Shaw 2000 or HKW 2006.
- `notes_from_holbl` = per-row scholarly annotation distilled from Hölbl's rubric block. Captures the ruler's relationship to the Egyptian throne (satrap-of vs king-of), joint-rulership arrangements, and the circumstances of accession / death insofar as Hölbl's table states them in the rubric. Free text; not a controlled vocabulary.
- `source_citation` = `{"pdf_pages": "348-351", "edition": "Routledge 2001"}` for every row. The chunk's full physical-page range, not per-row.

**Schema deviations from Kitchen TIPE** (closest structural reference):

- No `dynasty` field. The Argead rulers are not an Egyptian numbered dynasty; they are Macedonian-Greek rulers over Egypt in the interval between the Achaemenid Late Period and the Ptolemaic period. Adding `dynasty: null` everywhere would be noise; omitting the field is cleaner.
- No `sequence_in_dynasty` field. The `holbl_id` suffix (`.01` / `.02` / `.03`) already encodes sequence; a second field is redundant.
- No `prenomen` field. Hölbl's appendix is a political-events-by-year table, not a titulary table. He does not print Egyptian prenomina for any of the three Argead rulers. (Alexander the Great and Alexander IV do have Egyptian cartouches attested on surviving monuments — Hölbl mentions "bark shrine in the temple of Luxor" under Alexander the Great and "gate of the temple of Khnum on Elephantine" under Alexander IV — but the titulary transliterations belong in a different source, not this table.)
- No `length_of_reign_years` field. Hölbl does not print regnal-length integers in this table. `end_bce - start_bce` gives the Egyptian-reign length, but only approximately (because of the split-year hedges).
- No `concurrent_with_kings` field. The three rulers reign sequentially, not concurrently, and there is no Theban-HPA-style parallel line in the Argead period. (Ptolemy as Satrap is a regent, not a concurrent king; captured in `notes_from_holbl`.)

## Rights

Routledge / Taylor & Francis Group (in copyright 2001 edition of 1994 German text). This extract contains only factual data — three ruler names, their common alt-name spellings, BCE date endpoints, the `Argead` polity label, and short factual notes about their relationship to the Egyptian throne. Hölbl's 300+ pages of prose analysis, the full appendix table (political events / religion / temples columns), the stemmata, the maps, and the bibliographical apparatus are not reproduced.

Per ADR-017 the source PDF is not committed; per-chunk OCR markdown in `raw/` is not committed (`pipeline/pipeline/authority/sources/*/raw/*` gitignore pattern with a `!raw/.gitkeep` exception). The derived-extract path (per `docs/playbook-phase-0-ocr-transcription.md` § "Rights policy") is this project's default rights basis: US *Feist v. Rural* establishes that facts are not copyrightable; the PDF itself is never redistributed through this repo.

## Method

Per ADR-017 (Claude Code subagent OCR → three-subagent structured extraction → deterministic majority-vote merge → LLM reviewer pass). See `transcribe.md` for the specific protocol applied to Hölbl.

**Review.** The playbook's default is a post-merge pass by the `egyptologist-reviewer` Claude Code subagent; that subagent was NOT invoked on this source. See `transcribe.md` § "Model deviation" — the harness exposed no `Task` / `Agent` tool, so the review step (like the OCR and extraction steps) ran in the main session. The main-session self-review flagged two `notes_from_holbl` interpolations which `fix_rows.py` applies. **A human Egyptologist sign-off pass has ALSO NOT been performed** — the extract is provisional until that happens. The corrections themselves are scholar-legible and the rationales are recorded in `merge-disagreements.txt`, but the review is self-review-by-the-same-model rather than independent review.

## Known gaps / Phase A notes

- **310/09 → 306 BCE interregnum is genuinely open.** After Alexander IV is murdered in 310/09, Ptolemy rules Egypt as Satrap without an Argead king overhead; he does not take the title of King until autumn 306 (after the naval battle at Salamis). Neither this extract nor `sources/wikipedia-ptolemaic/` (which starts at Ptolemy's kingship) covers those ~4 years. Phase A can layer an explicit "Interregnum" interval record, or extend one of the two authorities by one row — architectural decision deferred.
- **Ptolemy's satrapal years (323–306) are not separately indexed.** Hölbl's table attests "Ptolemy as Satrap" under the Philip III and Alexander IV rubrics. For an Egypt-provenance index, Ptolemy is the de facto ruler of Egypt through those 13 years even though the nominal kingship rested with the Argeads in Babylon. The `notes_from_holbl` field on `argead.02` / `argead.03` records this. If Phase A needs satrap-as-ruler rows, they are added there, not here.
- **Alexander the Great's pre-Egyptian reign (336–332) is not represented.** Alexander acceded to the Macedonian throne in 336 BCE but did not enter Egypt until late 332. HKW 2006's coverage of this period uses the 332 anchor as the start of his Egyptian reign; we follow Hölbl's Egypt-anchored 332 for consistency. A cross-authority reconciliation (Alexander's Macedonian 336 → Egyptian 332) belongs in Phase A.
- **Titulary (prenomen/nomen cartouches) not extracted.** Alexander the Great, Philip III Arrhidaios, and Alexander IV all have attested Egyptian cartouches from their monumental building work (Luxor bark shrine, Karnak shrine, Hermopolis hypostyle, Elephantine Khnum gate, Spos Artemidos). A titulary source for the Argead period (Beckerath's *Handbuch der ägyptischen Königsnamen* 2nd ed. covers this; Leprohon 2013 *The Great Name* as well) lands in a separate PR.
- **Double-dating of Alexander IV's death.** Hölbl writes `310/09` because the year of Alexander IV's murder is disputed in the scholarship (Diodorus places it before Kassandros's assumption of royal title; the assumption itself is disputed between 310 and 306). We pick `-310` with `approximate: true`; HKW 2006 or other sources may give `-309`. Phase A reconciliation is a normalisation task, not an extraction bug.
