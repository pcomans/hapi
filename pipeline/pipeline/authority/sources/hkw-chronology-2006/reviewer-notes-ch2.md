# Reviewer notes — Hendrickx Ch 2 additions (PR #102 / c1570928)

Retroactive scholarly review of the 4 Dyn 0-era rows added to `reconciled.jsonl`
from Hornung-Krauss-Warburton 2006, Ch II.1 (Hendrickx), pp. 55–93.
Source verified against `raw/chunk-ch2-p55-p93.txt` (text layer of the
committed PDF). Severities: **P1** = blocker / factual error; **P2** =
should-fix / materially misleading; **P3** = nit / defensible as-is.

---

## Row: Dyn. 0 (dynasty, number:0, page 88)

**P3 — `parent_period: null`.** Defensible. Hendrickx's Table II.1.7 (p.92)
treats Naqada IIIA1–IIIB as the stratum that Dyn 0 occupies, and Ch 2 sits
under the Chronological Tables' "Early Dynastic" umbrella only loosely; the
chapter title itself is "Predynastic—Early Dynastic." If an upstream
"Predynastic" period row is ever introduced, this FK should be reconciled;
until then, `null` is honest. Note text correctly cites p.88.

**P3 — Null BCE dates.** Correct. Table II.1.7 provides bounded cal-BC
ranges for IIIA2 (3350–3150) and IIIC1 (3150–3100) but **not** for IIIA1 or
IIIB — exactly the phases Dyn 0 sits across. Inferring "IIIB ≈ 3150 ± n" by
sandwiching is not Hendrickx's own claim and would fabricate precision he
explicitly avoided (p.91: "preliminary and approximate only"). Leave null.

---

## Row: Iry-Hor (ruler, dynasty:0, page 89)

**P3 — `alternative_reading: "Irj-Hor"`.** Defensible but slightly
mischaracterised. On p.89 Hendrickx writes "Irj-Hor (B1–2)" — this is not a
distinct reading of the name, it is a francophone/German-convention
transliteration of the same consonants (*j* for *y*). Consider relabeling the
field semantics (it is a transliteration variant, not an alternative Horus
name like "Netjery-khet" for Djoser). For downstream matching against Met /
Brooklyn / Harvard catalogues the string is still useful.

**P3 — Naqada IIIB assignment.** Confirmed by Table II.1.6 (p.89 row: "Iry-Hor
IIIB B 1/2") and Table II.1.7 (p.92: "Naqada IIIB U-t, Iry-Hor – Ka") and
p.89 narrative ("can be dated to Naqada IIIB on more reliable basis"). All
three sources converge. Note text is accurate.

**P3 — Tomb B1/2.** Confirmed at Table II.1.6 and p.89 prose.

---

## Row: Ka (ruler, dynasty:0, page 89)

**P2 — Naqada-phase ambiguity in note is slightly overstated.** The submitter
read Table II.1.6 as showing Ka at "IIIC1" in a main-column cell and "IIIB" in
a tomb row. Looking at the table as reconstructed from the text layer, the
rows for Ka are:
- IIIC1 Tarkhan 261
- IIIB/C1 Turah 1627, 1651
- IIIB B 7/9 Abydos

This is **not** a table inconsistency — it is Hendrickx deliberately tabulating
Ka's *finds across multiple sites and phases*, because his reign spans the
IIIB→IIIC1 transition. Confirmed by footnote 101 (p.84): "Stufe IIIc1 =
Ka—Narmer" (Kaiser's correlation) and by Table II.1.7 placing Ka as the
terminus of IIIB. So the defensible reading is: Ka **straddles late IIIB /
early IIIC1**, not "IIIB with a typo for IIIC1." Recommend tightening the
note to "late IIIB / start of IIIC1" and removing the "apparent inconsistency"
framing.

**P2 — `alternative_reading: "Sekhen"`.** Problematic for source fidelity.
Hendrickx does **not** use "Sekhen" anywhere in Ch 2 — the note correctly
admits this. Per the project's "scholarly" rule (CLAUDE.md constitutional
rule 1: every authoritative fact traces to a documented source), putting
"Sekhen" in `alternative_reading` on an **HKW-sourced row** is a category
error: the row's provenance is Hendrickx, but the alt-reading is not. "Sekhen"
*is* a widely-attested older reading (Petrie, Kaplony) and is useful for
museum-catalog matching, but it belongs on a pharaoh.se row or in a separate
aliases authority — not attributed to HKW. Options: (a) set to null and move
"Sekhen" into aliases layer; (b) keep the string but change `page` semantics
/ add a provenance flag; (c) leave as-is and accept the minor fidelity leak.
My recommendation: (a).

**P3 — Tomb B7/9.** Confirmed at Table II.1.6.

---

## Row: Scorpion I (ruler, dynasty:0, page 91)

**P1 — `dynasty: 0` is not supported by Hendrickx.** On p.88 Hendrickx
explicitly says "Dyn. 0 has however been used with different meanings and the
**only consistency is the inclusion of Iry-Hor and Ka.**" Scorpion I is never
placed in Dyn 0 by Hendrickx; he sits in cemetery U (tomb U-j) at Naqada
IIIA1, a generation or two **earlier** than the cemetery-B cluster that
defines Dyn 0. Putting him in `dynasty:0` overstates what HKW asserts and
silently resolves the Dyn 0 / Dyn 00 question that Hendrickx deliberately
leaves open. Options: (a) `dynasty: null` with a note that Hendrickx places
him at Naqada IIIA1 in cemetery U pre-dating the Dyn 0 kings; (b) invent
`dynasty: -1` or similar sentinel (ugly; breaks downstream); (c) keep
`dynasty: 0` but add a prominent caveat. **Recommend (a)** — null is the most
truthful representation of Hendrickx's stance. Downstream museum records that
tag Scorpion I as "Dynasty 0" can still match via fuzzy alias, but the
authority row should not launder a contested attribution as fact.

**P3 — Naqada IIIA1 assignment.** Confirmed Table II.1.7 (p.92): "Naqada
IIIA1 U-a,k,o,r,qq – Scorpion I" and Table II.1.6 (p.89): "Scorpion I IIIA1
U-j".

**P3 — Null BCE dates.** Correct per the Dyn 0 reasoning above.

**P3 — Note text accurate** on U-j, Dreyer 1998, and the old-wood radiocarbon
issue (verified at p.91).

---

## Summary

| Row         | P1 | P2 | P3 |
|-------------|----|----|----|
| Dyn. 0      | 0  | 0  | 2  |
| Iry-Hor     | 0  | 0  | 3  |
| Ka          | 0  | 2  | 1  |
| Scorpion I  | 1  | 0  | 3  |

**One P1** (Scorpion I dynasty assignment) and **two P2s** on Ka warrant a
follow-up edit. The rest is defensible. Overall the transcription is careful,
the note fields are appropriately hedged, and the decision to leave BCE dates
null is the right call given Hendrickx's own reticence.
