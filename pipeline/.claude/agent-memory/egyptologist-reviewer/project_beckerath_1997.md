---
name: Project: Beckerath 1997 extraction
description: Phase-0 transcription of Beckerath 1997 Anhang A + Supplement; reviewer pass completed; fix_rows.py written
type: project
---

3-subagent majority-vote merge of Beckerath 1997 Chronologie des pharaonischen Ägypten (MÄS 46) Anhang A is complete. The reconciled.jsonl (172 rows) has been reviewed by the egyptologist-reviewer subagent against JPEG scans (scan-105 through scan-109).

**Why:** Beckerath is the lead chronology source (ADR-017); errors here propagate to all ruler enrichment downstream.

**Key corrections applied in fix_rows.py:**
- 18.02: CRITICAL identity error — merge produced "An-jotef I." (Dyn-17 Antef) for what is actually Amenophis I. (Djeser-ka-rê) 1525–1504 BCE. Full row overhaul.
- 18.04/18.05 Tuthmosis II / Hat-schepsut: OCR-corrupt "341/837" → correct end date -1458/-1458 for both.
- 15.04 Chajan: end_bce_high -1149 → -1549 (OCR corrupt; scan shows 1590/87–1549/1546).
- 19.05/19.06 Amen-mes-su/Sethós II: garbled Supplement prenomens corrected from scan-108 (Sethós II had Merenptah's prenomen by splice error).
- 04.02–04.08: Dyn-4 "etwa" propagation; all 7 rows both approximate flags → true.
- 24.01–24.02: period "Spätzeit" → "III. Zwischenzeit" (SPÄTZEIT heading sits above Dyn 26, not Dyn 24).
- 27.03 Xerxes I.: end_bce_low -484 → -464 (inverted carry-over error).
- 03.04–03.06: audit notes added for Dyn-3 brace bracket.

**How to apply:** When reviewing future Beckerath-derived data, watch for: (1) Dyn 18 early sequence (Amenophis I., not any Antef); (2) Supplement prenomens for Dyn 19-23 are Thronname only (do not confuse with Eigenname); (3) "etwa" in dynasty headings propagates to all individual rows.
