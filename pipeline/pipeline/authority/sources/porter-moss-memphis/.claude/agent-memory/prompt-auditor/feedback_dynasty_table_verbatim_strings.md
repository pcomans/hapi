---
name: feedback_dynasty_table_verbatim_strings
description: Dynasty-mapping tables that quote verbatim PM "Temp. <King>" strings are per-row answer leaks — always rewrite as rule-based king-dynasty classes
metadata:
  type: feedback
---

Dynasty-mapping tables in PM Memphis extraction prompts MUST use rule-based king classes, not verbatim source strings.

**Why:** PM headwords carry `Temp. <King>` dating strings that are unique per row. A table that enumerates `Temp. Ramesses II → "19"`, `Temp. Psammetikhos I → "26"` etc. gives each agent the answer for each named-tomb headword before they read the chunk — same leak class as per-row answer enumerations (PR #66/#68/#70/#196).

**How to apply:** Replace `| \`Temp. <KingName>\` | dynasty | sub_period |` rows with rule classes:
- `Temp. <King>` where King is a Dyn. XVIII pharaoh (not Amenophis IV) → `"18"` / null
- `Temp. Amenophis IV` or `Temp. Akhenaten` → `"18"` / `"Amarna"`
- `Temp. <King>` where King is a Dyn. XIX pharaoh → `"19"` / null
- `Temp. <King>` where King is a Dyn. XXVI pharaoh → `"26"` / null
- `Ramesside` (no specific king) → `"19"` / null
- `Dyn. <N>` explicit → Arabic numeral
- Range `Dyn. X or Dyn. Y` → later dynasty (range-tail convention)

First caught in chunk-31 audit (2026-05-19). The specific kings that appeared were Ramesses II (Dyn XIX), Tutankhamun/Ay (Dyn XVIII), Amenophis IV (Dyn XVIII Amarna), Sethos I (Dyn XIX), Psammetikhos I (Dyn XXVI), Amasis (Dyn XXVI). Table had Sethos I missing even before the verbatim-leak problem.
