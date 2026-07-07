---
name: diacritics-section-leaks-real-names
description: Phase-0 prompts' "Diacritics / OCR normalisation" section is a recurring leak vector — worked examples that look like generic noise-pattern documentation often use the actual occupant/king names of rows in the current chunk.
metadata:
  type: feedback
---

When auditing a Phase-0 extraction prompt's OCR/diacritics-normalisation section, do not
assume a `<noisy form> → <clean form>` example is generic just because it's phrased like
one. Cross-check every named token in the example against the raw chunk text
(`raw/chunk-*.txt`) and against `reconciled.jsonl` (grep `occupant_name`) to see whether
that name is actually the answer for one of this chunk's rows.

**Why:** Found in `porter-moss-memphis/prompt-chunk-36.md` (Abûsîr, PM III.1). The
Diacritics/OCR section gave ayin/underdot/macron worked examples using `Neuserre`,
`Sahure`(ʿ), and `Raneferef` — which are not incidental filler, they are the literal
occupants of 3 of the chunk's 4 royal pyramid-complex rows (§ II Shape 2: Pyramid A =
Sahureʿ, B = Neuserreʿ, D = Raneferef). Grepping `reconciled.jsonl` confirmed these names
had never appeared as `occupant_name` in chunks 1–35, so they weren't "established
precedent from an earlier chunk" (which would have been fine) — they were fresh answers
for this chunk's own rows, handed to all three extraction agents identically. Also found
in the same prompt's tomb_id "Homonym discipline" bullet, which named the exact two
excavator numbers (`mR6`/`mR8`) holding a real homonym pair (Ḥarshefḥotp I/II) in this
chunk — same leak class as "confirm whether TT6/TT10 are joint," just dressed as an ID
convention example. And the prompt separately baked one royal name into a concrete
tomb_id itself ("the Abûsîr sun-temple id `ABU-SunTempleUserkaf` is deliberately
distinct") — leaking the § I Sun-temple's king outright.

**How to apply:** For every worked example in a Diacritics/OCR section, a tomb_id
disambiguation section, or a "homonym discipline" bullet:
1. Is the named token (king, occupant, tomb number) actually a row-owner in *this*
   chunk's raw text? If yes → P1 leak, regardless of how boilerplate the surrounding
   prose reads.
2. Is the example instead cited as "chunk-N precedent" (an earlier, already-committed
   chunk)? That's allowed per the audit brief's "examples from earlier chunks" exception
   — but verify the cited chunk number really is earlier and really is the source of that
   name (grep `reconciled.jsonl`), since a prompt author can mis-cite.
3. Watch specifically for: (a) OCR ayin/underdot/macron examples reusing a king name that
   also appears in a `PYRAMID-COMPLEX OF <KING>` banner in this chunk; (b) "homonym
   discipline" bullets that name the specific excavator numbers/ordinals of a real
   duplicate-name pair instead of using `<N>`/`<M>` placeholders; (c) tomb_id-collision
   bullets that resolve the collision by naming which king occupies the new section's
   row instead of just stating the naming *rule*.

Related: [[reference_pm_memphis_source]]
