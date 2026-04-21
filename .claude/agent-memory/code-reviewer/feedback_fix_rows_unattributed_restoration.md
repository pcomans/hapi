---
name: fix_rows.py corrections must cite a traceable verifier, not assert PM-prints-X unattributed
description: Rule 1 failure mode where a correction inserts characters the text-layer evidence doesn't show, with no egyptologist-reviewer attribution
type: feedback
---

A `fix_rows.py` CHUNK*_CORRECTIONS entry that inserts a character (macron, ayin, diacritic, alt-spelling) the text-layer evidence in `raw/chunk-*.txt` doesn't contain MUST cite who verified against the printed PDF. The good pattern: chunk-3's KV36 correction cites "egyptologist-reviewer second-pass on PR #69 confirmed no published Egyptological form reads 'Maihirper'". The bad pattern: PR #70 chunk-4's KV55 correction asserts "PM p.565 prints 'Smenkhkarēʿ' with macron-e and trailing ayin" without naming the reviewer — the text layer shows `Smenkhkarec` (ayin-as-c, NO macron), so the correction is inserting a character whose source trace ends at the rationale string itself.

**Why:** constitutional rule 1. "Every authoritative fact must trace to a clear, documented, reproducibly-acquired source on disk. ... 'The model knows' is not a source." An unattributed editorial restoration in `fix_rows.py` is exactly the "the model knows" failure — we can't reproduce who checked PM p.565 against the printed book vs the text layer. When the text layer clearly shows a different form, the gap between "what's in raw/" and "what ships in reconciled.jsonl" must be closed with an explicit verifier citation.

**How to apply:** when reviewing any `CHUNK*_CORRECTIONS` entry on a Phase-0 PR, cross-check the correction value against the relevant `raw/chunk-*.txt` line. If the correction inserts a character the text layer doesn't show, the rationale must name the egyptologist-reviewer pass (by PR# or by date) that verified against the PDF. Absent attribution, flag as blocking and offer two remediation paths: (a) add the reviewer citation, or (b) back the correction off to what the text layer supports.
