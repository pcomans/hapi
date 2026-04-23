# Reviewer notes — chunk 7 (PM I.2 §§ II + III.A/C/D, pp. 590–605)

**Status: YELLOW.** The 18 SWV-/DAN- rows are broadly well-extracted and the descriptor-id normalisation has landed cleanly, but there are a handful of P1 factual errors (role, occupant, missed headword), several P2 hedge/spelling losses, and one false inclusion to sort out before this chunk merges. Everything below is against PM I.2 2nd ed. 1964, printed pp. 590–606.

## Summary of rows extracted

- SWV-* (§ II.A + II.B): 3 rows — SWV-HatshepsutSouth, SWV-ThreePrincesses, SWV-Neferure.
- DAN-* (§ III.A + III.C + III.D): 15 rows — Antef (Sehertaui, Wahankh, Nubkheperre, Sekhemre-Wepmaet, Sekhemre-Heruhirmaet), Mentuhotp-Sankhibtaui, Ahmose-Nefertari, Kamose, Ahhotep, Ahmosi (son of Seqenenre), Ahmosi Henutempet, Mentuhotp I (wife of Djhuti), Neferhotep, Sebkemsaf II, Ahhor.

## Per-row findings

### P1 — real errors

- **SWV-HatshepsutSouth — `occupant_role: "Queen"` is correct.** PM p. 590 prints "SOUTH TOMB OF Ḥatshepsut" (headword without royal title) and then the diagnostic object is specifically "Sarcophagus **as Queen-Consort**, quartzite, in Cairo Mus. Ent. 47032." The sarcophagus-as-Queen-Consort is PM's own characterisation of the tomb's occupant at the time of cutting; "Queen" is what the evidence names. Keep as is. (Flagging in case a downstream reviewer re-opens this — the prompt explicitly asked.)

- **DAN-Ahhor — `occupant_role: "Royal Family"` is wrong.** PM p. 605 reads: "ʿAḲ-ḤOR … Royal acquaintance. Dyn. XVII." (Note: the headword is "ʿAḲ-ḤOR", not "ʿAḤḤOR" — the glyph is *rḫ-nswt* "king's acquaintance" → read ʿAḳ-ḥr / Aqhor, **not** an "ʿAḥḥor" name.) "Royal acquaintance" (*rḫ-nsw*) is a minor courtier title, not a royal-family affiliation. **Suggested:** `occupant_role: "Official"`, `occupant_name: "ʿAḳ-ḥor"`. Severity P1 (both role and name).

- **DAN-AhmosiNefertari — `occupant_alt_names` is empty; should capture "Amenophis I" as an attribution variant.** PM p. 599 §III.C headword: "TOMB OF QUEEN ʿAḤMOSI NEFERTERE (probably)" with explicit note that Carter attributed it to Amenophis I and Černý revised to equate with Amenophis I again. The hedge "(probably)" is load-bearing and is **missing from `notes_from_pm`** — currently the note says "Tomb of Queen ʿAḤmosi Nefertere (probably)" which is fine, but the Carter/Amenophis I attribution history (explicit in PM) is lost. **Suggested:** add "attributed to Amenophis I by Carter; Černý equates with 'House of Amenophis of the Garden'" to notes. P2.

- **DAN-MentuhotpIWifeOfDjehuti — `notes_from_pm: "Wife of King Djhuti."`** PM p. 604 prints "wife of King **Ḍḥuti**" (underdot-D, underdot-H). As flagged in the task — the OCR lost both diacritics. **Suggested:** restore to `Ḍḥuti` via fix_rows.py. Also the `occupant_name` is "Mentuḥotp I" which is correct, but the "I" here is PM's own footnote-disambiguated numbering ("For coffin of another Queen Mentuḥotp, see infra, p. 605") — keep. P2.

- **DAN-Neferhotep — KEEP this row, `occupant_role: "Official"` is correct.** PM p. 604 gives it a proper BURIAL headword in bold caps: "NEFERḤOTEP … Scribe of the Great Harim, probably temp. Antef (Nubkheperreʿ), rock-tomb, uninscribed. Found by Mariette in 1860, probably near Theb. tb. 13." It is a headword, not an object-entry. No change.

### P1 — missed headword

- **Queen Mentuhotp (daughter of Seneb-henaʿf), p. 605 "FINDS" section.** PM p. 605 prints a separate BURIAL-style entry: "Rectangular coffin of Queen Mentuḥotp, daughter of Seneb-ḥenaʿf, Vizier, and Princess Sebkḥotp, Dyn. XVII, probably from here, now lost." This is PM's "another Queen Mentuḥotp" explicitly cross-referenced from p. 604 footnote 1. It is a **FINDS** entry, not a BURIAL headword — borderline. Recommend **dropping** (it's object-level, not a tomb) but note the ambiguity. If included, it would be `DAN-MentuhotpIIDaughterOfSenebhenaf` with `Royal Family` role, note "probably from here, now lost". P3 (ambiguous scope call).

- **Queen Mentuhotp (p. 605 FINDS), Princess Sebkhotp (same entry), Thuiu (throwstick, son of Seqenenre-Taʿa), Minemhēt (Mayor), Idi (Overseer of prophets):** these all appear under p. 605 "Dynasty XVII Cemetery — BURIALS" object-list but are **not** bold-caps headwords; they are ownership-attributions of single objects (coffin, throwstick, linen-chest, perfume-vase). Correctly excluded. No action.

### P2 — spelling / hedge fidelity

- **DAN-KamoseWadjkheperre — `occupant_alt_names: ["Wazkheperreʿ"]`, `occupant_name: "Kamosi"`.** PM p. 600 headword: "KAMOSI (WAZKHEPERREʿ)". Correct. Descriptor-id `DAN-KamoseWadjkheperre` however uses the modernised "Kamose" + "Wadj-" forms — inconsistent with the PM-faithful spelling convention applied to Ahmosi/Mentuhotp. **Suggested:** rename descriptor to `DAN-KamosiWazkheperre` for internal consistency. P2.

- **DAN-AntefNubkheperre — `notes_from_pm: "Found by Mariette in 1860. Pyramid, see Hay MSS. 29816."`** PM p. 602 headword is "ANTEF (NUBKHEPERRĒʿ)" and the text notes the discovery and "Two obelisks, probably originally in front of tomb, lost at sea in 1881." The obelisks-lost-at-sea detail is a memorable PM hedge; consider adding. P3 (nice-to-have).

- **SWV-ThreePrincesses — `occupant_role: "Royal Family"` and `occupant_name: "Menhet, Merti, and Menwi"`.** PM p. 591 headword: "TOMB OF THREE PRINCESSES, MENHET … MERTI … and MENWI. Temp. Tuthmosis III." The three are princesses (foreign-wives of Thutmosis III per Winlock). `"Princess"` role would be more accurate per the controlled vocab; `Royal Family` is broader but acceptable. P3.

- **DAN-AhmosiSonOfSeqenenre — `occupant_role: "Royal Family"`.** PM p. 604: "ʿAḤMOSI, eldest son of King Seḳenenreʿ-Taʿa and ʿAḥḥotp." Could be `"Prince"`; `"Royal Family"` acceptable. P3.

### Descriptor-id findings

- `DAN-AhmosiNefertari` — descriptor uses modernised "Nefertari" despite PM printing "Nefertere". **Suggested:** `DAN-AhmosiNefertere`. P2, consistent-convention issue.
- `DAN-KamoseWadjkheperre` — see above; should be `DAN-KamosiWazkheperre`. P2.
- `DAN-MentuhotpIWifeOfDjehuti` — descriptor uses "Djehuti"; PM prints "Ḍḥuti". **Suggested:** `DAN-MentuhotpIWifeOfDjhuti` (ASCII-safe) to match the Ahmosi/Mentuhotp precedent. P3.

### False-inclusion findings

None confirmed. DAN-Neferhotep is a legitimate headword. DAN-Ahhor is legitimate as a tomb but misclassified (see P1 above).

### Scope check

No § III.B rock-stelae entries were included (correct — the rock-stela of Apries and the Tueris-sketches on p. 599 are object-level). No § III.E Petrie-excavation rows included (correct). § III.A Antef Cemetery has all five Winlock-numbered royal Antef tombs covered between the two clusters (Sehertaui p.594, Wahankh p.595, Nubkheperre p.602, Sekhemre-Wepmaet p.603, Sekhemre-Heruhirmaet p.603) plus Mentuhotp-Sankhibtaui p.595 — all present.

---

**Three-sentence summary:** Chunk 7 is in reasonable shape — the 18 descriptor-id rows cover every PM headword in §§ II + III.A/C/D with faithful role/dating, and the earlier pre-merge normalisation of Ahmosi/Mentuhotp/Sebkemsaf descriptors held. The two real issues are `DAN-Ahhor` (mis-read name "ʿAḥḥor" should be "ʿAḳ-ḥor" and role should be `Official` not `Royal Family` — PM literally says "Royal acquaintance", a *rḫ-nsw* title), and the `Djhuti` → `Ḍḥuti` underdot loss in DAN-MentuhotpIWifeOfDjehuti's notes. A handful of P2/P3 descriptor-spelling inconsistencies (`Kamose`/`Nefertari` modernised while sibling descriptors are PM-faithful) should be fixed for convention, plus the Carter/Amenophis-I attribution history is missing from the Ahmose-Nefertari note.
