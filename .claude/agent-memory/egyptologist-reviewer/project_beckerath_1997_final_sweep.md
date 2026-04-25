---
name: Beckerath 1997 final sweep findings
description: P1/P2 errors surviving all prior review passes in the committed reconciled.jsonl (172 rows), including the agree-but-wrong blind spot methodology note
type: project
---

Three errors survived all prior review passes (original merge → 19 fix_rows.py overrides → Gemini/Codex corrections).

**P1 — Row 29.02 Achoris: truncated egyptian_titulary**
Scan-108 shows "Achoris (Hagor, Chnem-maat-rê)" but reconciled.jsonl has `egyptian_titulary="Chnem-maat-rê"` and `kind="prenomen"`. The "Hagor" nomen is missing. Correct values: `"Hagor, Chnem-maat-rê"` with `kind="mixed"`. Invisible to the disagreement log because no two agents had identical titulary values, so majority collapsed to the shortest form with no logged content-gap disagreement.

**P1 — Row 18.05 Hat-schepsut: editorial residue in notes_from_beckerath**
`notes_from_beckerath="start 1479/73"` is not a Beckerath annotation; it is an editorial note left over from the Gemini correction pass that stripped "end date OCR corrupt" but left "start 1479/73". Should be null per Constitutional rule 1.

**P2 — Row 19.07 Si-ptah: incomplete egyptian_titulary mapping**
`prenomen="Sech-en-rê mer-amun"` is correct, but the variants "Sich-ka-rê sotep-en-rê" and "Ach-en-rê sotep-en-rê" are relegated to notes. Beckerath (p. 108) explicitly identifies them as successive names ("anfang" / "später"), not incompatible readings. The mapping issue is that the `egyptian_titulary` field is null but should carry the full Übersicht parenthetical string from scan-108/109 with the successive-name relationship preserved either as a compound titulary or via a structured sub-field.

**P2 — Row 21.02 Amen-em-nisu: wrong egyptian_titulary_kind**
`kind="nomen"` but "Nephercheres" is the Greek form of the prenomen Neferkare. Should be `kind="prenomen"`.

**P2 — Row 31.04 Chabbasch: wrong egyptian_titulary_kind**
`kind="nomen"` but "Senem-sotep-en-ptah" has prenomen morphology (*-sotep-en-X* suffix). Should be `kind="prenomen"`.

**Confirmed clean:** Rows 18.11–18.14 (Nofret-ete, Semench-ka-rê, Tut-anch-amun, Aja) verified against scan-107 — all correct.

**Methodology note:** The agree-but-wrong pattern (agents partially correct on different sub-fields, majority composes an incomplete value, no disagreement logged) is a real blind spot in the three-subagent extraction protocol. It surfaces most often where Beckerath's parenthetical contains a compound value (nomen + prenomen separated by comma). Future extractions should add a post-merge check: any parenthetical containing a comma in the raw scan should produce `kind="mixed"`, not a single-kind value.

**Why:** These were the final unresolved errors before the source was declared production-ready. The two P1s must be fixed before the Beckerath source feeds `build_rulers.py`.

**How to apply:** If asked to review future Beckerath-derived data, check compound titulary parentheticals (comma-separated) for truncation and verify notes_from_beckerath contains no editorial residue.
