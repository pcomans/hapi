# Egyptologist sweep notes - 2026

Scope: retrospective spot review of `reconciled.jsonl` against Dodson & Hilton 2004 PDF and prior local notes. Read `README.md`, `transcribe.md`, `reviewer-notes-ramesside.md`, and the 2026-04-15 human review files.

Rows spot-checked against PDF images: `Nymaathap A`, `Neithhotep A`, `Redji`, `Khnemetptah`, `Shepsetipet`, `Syhefernerer` (pp. 48-49 / PDF 44-45); `Aat`, `Hetepti`, `Kaneferu`, `Khnemetneferhedjet I Weret`, `Sithathoriunet`, `Didit`, `Neferet Q`, `Sithathor Q` (pp. 96-99 / PDF 88-91); `Amenhotep A`, `Haankhef A`, `Hetepti` stub, `Inni`, `Iuhetibu Q`, `Dedusobk A`, `Sobkhotep Q`, `[...]djeb` (pp. 108-113 / PDF 98-103); `Sethirkopshef B`, `Ramesses C`, `Tawerettenru`, `Tiy C`, `Anuketemheb`, `Taiay` (p. 194 / PDF 180). Prior human-reviewed Power/Amarna rows were also sampled via notes, and `Intkaes` was cross-checked against local Baud 1999.

## P1

None found.

## P2

1. Founders `dynasty` values are internally inconsistent and leave several 2nd/3rd Dynasty rows as Dynasty 1. `fix_rows.py` has corrected only the explicit unplaced rows `Shepsetipet`, `Sitba`, `Syhefernerer` -> 2 and `Redji` -> 3, but the same source page and `transcribe.md` identify `Nymaathap A` as tied to Khasekhemwy / early 4th-Dynasty cult context and `Hotephirnebty` as wife of Djoser. `Hotephirnebty`, `Intkaes`, `Perneb`, `Mesenka`, and `Wadjetefni` remain `dynasty: 1` despite Djoser/Step Pyramid/Hotepsekhemwy cues; local Baud 1999 independently has `Intkaes` as Dynasty 3. This is not just a README caveat: the reconciled file now mixes per-row refined dynasty values with chunk-default values. Either keep all Founders rows coarse with an explicit non-authority `dynasty` convention, or finish per-row refinement for the rows whose own notes anchor them outside Dynasty 1.

## P3

1. Founders footnote markers are not provenance-faithful. D&H prints note markers as superscript numerals on p. 49, and `transcribe.md` says to preserve such markers inline. Three `notes` fields instead carry Markdown footnote syntax: `Khnemetptah` has `[^60]`, `Shepsetipet` has `[^61]`, and `Syhefernerer` has `[^62]`. Other chunks use bare inline numbers (e.g. Ramesside `136`), so this creates source-local drift and can confuse downstream text comparison. Prefer `60`, `61`, `62` or a single documented marker convention.

Positive checks: the sampled Seizers and Kings/Commoners relationship fields preserve the printed hedges (`Kaneferu` probable wife; `Inni` possible wife; `Hetepti` full row plus stub); Ramesside `Sethirkopshef B.roles = ["KSon", "MH"]` matches the PDF exactly, including D&H's unusual `MH`; Unplaced flags on sampled p. 99, p. 113, and p. 194 entries match D&H section headings.
