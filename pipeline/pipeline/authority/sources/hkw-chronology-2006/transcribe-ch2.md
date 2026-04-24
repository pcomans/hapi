# Transcription method — HKW Ch 2 (Hendrickx) Dyn-0 addendum

Companion to the source-dir `README.md` and the original `prompt.md` (which
covers sections IV.2 and IV.3, the chronological table extraction). This
file documents the separate Ch 2 Hendrickx extraction that produced the
4-row Dyn-0 addendum landed in PR #102.

## Source

- Book: Hornung, E., Krauss, R., & Warburton, D. A. (Eds.). (2006).
  *Ancient Egyptian Chronology*. Handbook of Oriental Studies, vol. 83.
  Leiden: Brill.
- Chapter: **Ch 2 — Stan Hendrickx, "Predynastic–Early Dynastic Chronology,"
  pp. 55–93.**
- Book PDF: `proprietary/books/Hornung-Krauss-Warburton 2006 - Ancient Egyptian Chronology.pdf`
  (SHA-256 `304a75ce18090cd683fc47650eaf5741dc73c9e4abdd8fbdc13dda707cd47c55`).
  Full 530-page book with text layer — `pypdf` extracts Ch 2 prose and tables
  verbatim with the usual late-1990s-scholarly-OCR caveats on diacritics.
- Chunk file: `raw/chunk-ch2-p55-p93.txt` (gitignored; 95 k chars; pdf offset
  physical = printed + 14, so printed p.55 = pdf p.69 and printed p.93 = pdf
  p.107). Produced by a single-agent `pypdf` text-layer dump — not committed.

## Method deviation: hand-extraction, not 3-subagent

The primary 4-row addendum (1 Dyn-0 dynasty row + 3 ruler rows) was **hand-
extracted in the main session** rather than going through the standard 3-
subagent majority-vote + `merge.py` pipeline used for larger chunks. Rationale:

- Only 4 rows, with every field value traceable to specific printed pages
  (88, 89, 91, 92) that I verified via targeted grep against the chunk file.
- Hendrickx's Tables II.1.6 (p.89 — tomb/phase correlation) and II.1.7 (p.92
  — phase chronology) are compact enough that majority-vote across 3 agents
  would add latency without improving reliability for a 4-row extract.
- The 3-subagent discipline is valuable for prose where agents might
  plausibly disagree on field-shape decisions (headword scope, what counts
  as a "tomb row"). This addendum is pure table extraction.

**Trade-off acknowledged:** single-agent extraction lacks the deterministic
majority-vote audit that `merge.py` produces in `merge-disagreements.txt`.
The compensating mitigation is two independent review passes documented in
sibling files:

- `reviewer-notes-ch2.md` — `egyptologist-reviewer` subagent spot-checked
  all 4 rows against Hendrickx's cited pages; flagged the P1 Scorpion I
  `dynasty: 0 → null` correction and two P2 Ka-note / Ka-alternative-reading
  corrections (all applied in the follow-up fix-up PR).
- `code-review-ch2.md` — `code-reviewer` subagent flagged the thin audit
  trail (this file addresses that finding), the `alternative_reading: "Sekhen"`
  provenance leak (now fixed), and three P3 test-coverage gaps.

## Extraction log

1. Full HKW book supplied by user at `/Users/philipp/Downloads/Ancient Egyptian chronology (1).pdf` on 2026-04-23.
2. Copied to `proprietary/books/` under the canonical filename; SHA pinned
   in `README.md` and here.
3. `pypdf` dump of pdf pp.69–107 (printed pp.55–93) to
   `raw/chunk-ch2-p55-p93.txt` (95 k chars).
4. Targeted grep of the chunk text for `Iry-Hor`, `Scorpion I`, `U-j`,
   `Dynasty 0`, and `Naqada III` produced the passages cited in the row
   `note` fields.
5. Hand-wrote 4 rows as JSONL directly into `reconciled.jsonl` via
   idempotent insertion script.
6. `egyptologist-reviewer` subagent pass produced `reviewer-notes-ch2.md`.
7. `code-reviewer` subagent pass produced `code-review-ch2.md`.
8. Follow-up fix-up PR applied the P1 + P2 findings (Scorpion I dynasty
   correction, Ka alt_reading removal, Ka note tightening, this transcribe
   file, test tightening).

## Row provenance summary

| Row | Key fact | Cited page | Verifying passage |
|---|---|---|---|
| `kind: dynasty, number: 0, label: "Dyn. 0"` | Hendrickx defines Dyn 0 | p. 88 | "Dyn. 0 has however been used with different meanings and the only consistency is the inclusion of Iry-Hor and Ka." |
| `Iry-Hor` (dynasty 0) | Naqada IIIB, tomb B1/2 | p. 89 | Table II.1.6: "Iry-Hor IIIB B 1/2" |
| `Ka` (dynasty 0) | Late IIIB / start IIIC1, tomb B7/9 | p. 89 (+ p. 84 fn 101) | Table II.1.6: "Ka IIIC1 ... IIIB/C1 ... IIIB B 7/9"; footnote 101 p.84: "Stufe IIIc1 = Ka—Narmer" |
| `Scorpion I` (dynasty null, not 0) | Naqada IIIA1, tomb U-j | p. 91 | Table II.1.7: "Naqada IIIA1 U-a,k,o,r,qq – Scorpion I"; p.88 caveat on Dyn-0 inclusion |

## Pipeline position

This source serves two authority tiers:

- **IV.2 chronology table (203 rows, pre-existing):** Dyn 1 → Ptolemaic
  rulers with absolute BCE ranges + ±25 yr error bars. Extraction method
  was the LLM-transcription-with-manual-spot-check path documented in the
  original `README.md`.
- **Ch 2 Hendrickx addendum (4 new rows, this file):** Dyn-0 boundary
  rulers + dynasty row. Absolute BCE dates null (Hendrickx's Table II.1.7
  does not give ranges for Naqada IIIA1 or IIIB).

Both tiers land in the same `reconciled.jsonl` with per-row page cites.
