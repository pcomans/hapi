# Retrospective scholarly review — `dodson-hilton-queens` (sweep, 2026-04-24)

Source reviewed by `egyptologist-reviewer` subagent as part of the Phase-0
sweep audit (see `docs/handoff-sweep-audit-2026.md`). The source was merged
in prior PRs without running an egyptologist-reviewer subagent during the
cycle. Builds on `reviewer-notes-ramesside.md`; non-duplicative.

Note on provenance: the subagent returned findings inline (its own
system-reminder forbade writing `.md` analysis files); the coordinator
persisted the text to this file verbatim per the sweep-doc deliverable spec.

**Scope reality-check.** Coordinator brief asked for OK/TIP rows. Neither is
in scope per README line 32: Ch 4 (OK) and Ch 5 (TIP/Late) are explicitly
deferred; Ch 1 (Early Dynastic = "The Founders"), Ch 2 (MK), Ch 3 (NK
through Dyn 20) are complete. Spot-checks re-scoped to Early-Dyn / MK /
NK-Amarna / NK-Ramesside (2 rows per band). This was a coordinator-brief
error — the sweep-doc template in CLAUDE.md should not assume OK/TIP are
present just because the source is about queens.

## P1 — must-fix before downstream enrich

1. **OCR role-code corruption `OPULE` on `Thutmose B` (line 372).** `"roles": ["EKSon","HPM","SPP","OPULE"]`. `OPULE` appears on zero other rows; README's enumerated codes include `MULE` but not `OPULE`. Near-certainly OCR drift of `MULE` (D&H's chart-legend code) with leading "O" bleed from adjacent "Overseer" column or similar. Verify against printed p. 155 and correct via `fix_rows.py`.

2. **Role-code `KGD` on `Sitamun B` (line 341).** Not in README's enumerated code list. Likely OCR of `KD` or possibly `KGW` collapsed. D&H p. 155 prints Sitamun B's roles in parens; spot-verify. Other Sitamun-B roles (`KW`, `KGW`) are fine.

3. **Leaked footnote markers in `notes`.** Multiple rows carry trailing D&H footnote reference numerals or markdown footnote syntax inside the verbatim prose:
   - `Amenhirkhopshef B` (line 20): `…died young as heir presumptive.136`
   - `Khaemwaset C` (line 142): `…year 55 and probably buried at Saqqara, perhaps below his hilltop sanctuary between Abusir and Saqqara.124`
   - `Tawosret` (line 366): `…Nothing is known about the fate of the queen's body,132`
   - `Khnemetptah` (line 434): `…tomb 175 H8 at Helwan.[^60]`
   - `Shepsetipet` (line 452): `[^61]` markdown footnote marker
   - `Syhefernerer` (line 457): `…stela, now in Cairo.[^62]`
   OCR post-processing should strip trailing digits and `[^NN]` markdown footnote syntax. Not scholarship-breaking but pollutes downstream text indexing and museum-catalog matching.

## P2 — curation-level issues

4. **`alt_names: []` is systemically under-populated for museum-match use.** README § "Known gaps" already flags this for Phase A, but the following rows will badly hurt cross-museum matching if not backfilled:
   - `Tawosret` — missing `Tausret` (Kitchen/HKW), `Twosre` (older literature), `Tawseret` (Manetho via Josephus → `Thuoris`).
   - `Iaret` — D&H's own prose admits reading uncertainty; `alt_names` should include `Aret`, `Jaret`.
   - `Neithhotep A` — missing `Neith-hotep`, `Neithotep`, `Hetep-Neith`. Museum catalogs (Brooklyn, Louvre) split these.
   - `Mertseger` (line 174) — README already flags `Meresger`/`Meretseger` variants; still `alt_names: []`.
   - `Maathorneferure` — missing `Maathornefrure`, `Mathornefrure` (Hittite studies variants).
   - `Neferitatjenen` — missing `Nefertatjenen`, `Nefertitotenen`.
   - `Sitre A` — only `Tia Q` recorded; missing the widely-used `Sat-Re` / `Satre`.
   These are not Phase-0 bugs per rule 1 (D&H doesn't inline them), but the Phase-A backfill is load-bearing for the Hapi cross-museum index.

5. **Cross-entry inference direction asymmetry.** `reviewer-notes-ramesside.md` § 4 flagged this; reconfirmed source-wide. `Tjia.father_name="Amenwahsu"` (child's row inherits from parent's silent-child entry) is the *reverse* direction of the README's documented rule (parent inherits from child). Both directions are applied inconsistently across rows. README convention needs a formal symmetry-update paragraph, and an audit pass to confirm all bidirectional inferences are either sanctioned or reverted.

6. **`Herneith` identity hedge under-specified.** Row 89 states "Probable wife of Djer" — D&H p. 48 *is* hedged, but downstream Phase-A reconciliation must handle the major competing identification with *Merneith* that Petrie/Wilkinson raised. `alt_names` is empty; even the spelling `Hornerti` (older literature) is absent. Flag for Phase-A, not a Phase-0 correction.

7. **`Neithhotep A` extraction-faithfulness trade-off.** Notes say only "Known from the Royal Tomb at Naqada…" — D&H's Brief Life *is* this terse, but the main narrative on pp. 46–47 identifies her as probable wife of Narmer and probable mother of Hor-Aha. `spouse_names: []` and `children_names: []` is faithful to the Brief Lives but a significant data gap. Per README's Brief-Lives-only scope this is correct, but Phase-A enrich must pick up the narrative-chapter kinship from a supplementary source (Wilkinson 1999 is the cleanest).

8. **`SH` role-code ambiguity on Founders (Hotephirnebty, Semat, Seshemetka, `[...]1A`).** README flags "Stela Holder / Subsidiary-Harem" as candidates; neither is scholarly-standard. Wilkinson 1999 (*Early Dynastic Egypt*) consistently uses "Seal-bearer" for the sealed-vessel contexts from Den's funerary complex, which would map `SH` → seal-holder. Not a Phase-0 fix (D&H's legend p. 24–37 is authoritative), but flag for Phase-A legend decoding that the most likely answer isn't in the two candidates README lists.

9. **`Ahhotepti` entry (line 420)** is typographically unusual. D&H likely prints `Ahhotep-ti` or `Ahhotep Q` — verify dh_id construction against printed p. 113. Low-to-mid confidence; worth a spot-check.

## P3 — observations, no action required

10. **Cross-dynasty reign-order sanity** (HKW/Ryholt cross-check): `Hetepti` twin-row (lines 90, 91) under Dyn 12 and Dyn 13 — README documents this as intentional (D&H cross-references between sub-sections); composite key handles it correctly. No Ryholt-SIP conflict. `Ameny A = Amenemhat II` placement Dyn 12 matches HKW. `Sobkneferu` Dyn 12 matches HKW/Ryholt. `Tiye B Mereniset` mother of Ramesses III matches Kitchen-TIP. `Pudukhepa` → Hattusilis III matches Bryce Hittite chronology. No dynasty-attribution contradictions found.

11. **Hedge-suffix inventory reconfirmed.** README enumerates `(probable)`, `(probably)`, `(possible)`, `(possibly)`. Spot-check confirmed all four forms are in use (`Nubhotepti A` "Hor (probable)", `Itakayet B` "Amenemhat II (probably)", `Hetepti` "Amenemhat III (possibly)"). Phase-A normaliser spec is correct.

12. **`Ramesses C` composite-key collision** (Dyn 19 grandson of Ramesses II vs Dyn 20 son of Ramesses III = later Ramesses IV) handled correctly via `(dh_id, sub_period)`. Confirmed both rows present (lines 283, 284).

13. **`Tiye A.children_names = ["Akhenaten"]`** omits Thutmose B (attested eldest son of Amenhotep III, line 372). Extraction-faithful — D&H's Tiye-A Brief Life names only Akhenaten. Phase-A cross-entry inference rule could populate `["Thutmose B","Akhenaten","Iset C","Henuttaneb A","Beketaten","Sitamun B"]` from those children's own entries; not a Phase-0 correction.

## Methodology concern for future Phase-0 sources

14. The Phase-0 OCR protocol produced systemic leaked-footnote artifacts (P1 item 3). A pre-commit text-quality check (regex for trailing `\d{1,3}$` in notes, `\[\^\d+\]` anywhere) would catch these deterministically per constitutional rule 3. Recommend adding to `diff_*.py` gate scripts before the remaining Ch 5 chunk.

## Sources consulted

- Complete Royal Families of Ancient Egypt – archive.org
- PalArch review – Dodson & Hilton 2004
- Mutnedjmet – Wikipedia
- Tjuyu – Wikipedia
