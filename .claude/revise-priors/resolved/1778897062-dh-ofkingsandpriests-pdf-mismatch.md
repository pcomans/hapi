# Revise priors: DH "Of Kings and Priests" sub-PDF page/print mismatch

- **Date**: 2026-05-15T00:00:00Z
- **Agent**: extraction agent B (subagent, dodson-hilton-queens / Of Kings and Priests / Dyn 21)
- **Triggered by**: Spawn from parent agent to run the 3-way parallel D&H Brief Lives extraction (`agent-b-ofkingsandpriests.jsonl`).

## Scope

Running extraction agent B over `pipeline/pipeline/authority/sources/dodson-hilton-queens/raw/source-p191-p195.pdf` per `pipeline/pipeline/authority/sources/dodson-hilton-queens/prompt-ofkingsandpriests.md`. Prompt asserts sub-PDF physical pp. 1-5 = printed pp. 205-209 (Brief Lives sub-block of D&H ch. 4, "Of Kings and Priests", 21st Dynasty). Output is to be written to `raw/agent-b-ofkingsandpriests.jsonl` with `source_citation.pdf_pages: "191-195"` baked into every row.

## Assumption suspected

The prompt's stated page mapping is off-by-one: the sub-PDF actually covers printed pp. **206-210**, not 205-209. Printed p.205 (Brief Lives section header `Brief Lives ●●●●…` plus the early entries — almost certainly the start of the Henttawy cluster including the Henttawy Q headword) is NOT in the sub-PDF, and printed p.210 ("The Rise and Fall of the House of Shoshenq / 22nd Dynasty") IS in the sub-PDF but is out of scope per the prompt's own termination rule ("Do not extract anything after that [decorative-bullet] terminator").

## Evidence

- `Read(file_path=".../raw/source-p191-p195.pdf", pages="1")` shows footer page number **206**, not 205. Verified twice.
- Sub-PDF page 1 left-column text begins mid-paragraph: `"Pasebkhanut I, Maatkare A, and one or more of Masaharta B, Djedkhonsiufankh I or Menkheperre B, and probably daughter of Ramesses XI; name written in full is Duahathor-Henttawy. A goblet from tomb NRTIII at Tanis..."` — i.e. continuation of an entry whose headword and opening sentence are on the missing prior page.
- Image caption on sub-PDF page 1 reads `"Henttawy Q was reburied in TT320, from which tomb come this shabti (above, Berlin) and her mummy (below, CM CG61090)."` — the Henttawy Q entry headword and opening sentences must therefore be on printed p.205.
- Sub-PDF page 5 footer is **210**, and the page content is the start of the **22nd Dynasty** chapter ("The Rise and Fall of the House of Shoshenq" / "Royal Succession" / "Historical Background") — explicitly out of scope (terminator is the decorative-bullet row at the bottom of p.209).
- Prompt structural hint, line 99: "Multiple `Henttawy` entries (some letter-suffixed, one `Q`-suffixed). Each is a distinct individual." — only Henttawy Q's paragraph tail and Isetemkheb A onward are visible. Henttawy A/B/C and the Henttawy Q headword + opening prose are absent.

## Decision needed from user

How should the page mismatch be resolved before extraction proceeds? Two options:

1. **Re-slice the sub-PDF** to start at printed p.205 (so the Brief Lives section header + Henttawy headword cluster are included). Optionally drop p.210 as well. Then update `prompt-ofkingsandpriests.md` so the `pdf_pages` claim and every row's `source_citation.pdf_pages` match the actual physical-page span on disk.
2. **Treat the current sub-PDF as authoritative** and update the prompt to acknowledge that printed-p.205 entries are out of scope for this chunk (to be covered by a separate fix-up chunk). Update `source_citation.pdf_pages` to the correct span (e.g. "192-194" or whatever the true physical → printed map yields).

Either way, the prompt's `pdf_pages: "191-195"` literal is currently inconsistent with both the file on disk and the printed-page numbering it claims; it needs to be corrected before any of the three agents finalises output.

## Recommendation

Option 1 (re-slice to include p.205). Rationale: the Henttawy cluster is explicitly called out in the prompt's parsing-hazard list as a load-bearing structural feature; producing a chunk where the headword for Henttawy Q is absent means downstream merge / authority-resolution / cross-source matching steps will see a row whose `dh_id` and `name` cannot be set from the printed source. The Henttawy Q entry is *partially* present (the prose continuation) but the headword and role-codes parenthetical are on the missing page — without them, agent B (and A, C) would have to either invent a `dh_id` from the caption ("Henttawy Q") and the in-prose `Duahathor-Henttawy` mention (which is an alt_name, not the headword), or skip the entry entirely. Both options violate the rule "preserve every entry."

If forced to ship without re-slicing, the deterministic fallback is to (a) skip the Henttawy-Q-tail orphan paragraph entirely, (b) start extraction at "Isetemkheb A" which is the first complete entry visible on sub-PDF page 1, and (c) note the gap explicitly in the final-line report. The user may decide differently — e.g. they may have a separate fix-up chunk already planned that covers printed p.205 with its own sub-PDF, in which case option 2 is fine.

No JSONL has been written. Sister extraction agents A and C will hit the identical mismatch when they read the same sub-PDF.
