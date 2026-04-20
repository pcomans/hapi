"""Pre-extraction OCR-chunk post-processor for the Ch 1 'The Founders' chunk.

Unlike the Seizers and Kings-and-Commoners chunks, **Gemini 3.1 Pro's OCR on
this 2-page sub-block preserved D&H's bold-italic-for-females typography
correctly** — `***Name***` for female entries, `**Name**` for males. The
post-processing here is therefore lighter than `transform_kc.py`:

  1. Prepend the standard H1 title + OCR-header block.
  2. Insert two page headers (`## p. 48`, `## p. 49`) at the right entry
     boundaries.
  3. Normalise the styled `## Brief Lives` and `### Unplaced` headings to
     the D&H-styled dotted variants used by prior chunks.
  4. Footnote markers (`[^60]`, `[^61]`, `[^62]`) are preserved verbatim in
     `notes`; `diff_founders.py`'s whitespace/superscript normaliser
     handles them in the mechanical diff.
  5. Append a `## Row count` footer.

**No systematic OCR-drift corrections needed for this chunk.** Unlike
Seizers (where Gemini rendered capital-I as lowercase-l) and Kings and
Commoners (same I/l + I/1 drifts), the Founders output has no
character-level artefacts that require correction. Verified by spot-check
against the source PDF at printed pp. 48–49 (physical 44–45); the Hor-Aha
/ Djer / Djet / Den / Qaa / Djoser / Semerkhet / Nymaathap / Meryetneith
/ Khasekhemwy / Nysuheqat name spellings all match D&H's printed form.

**One page-break continuation restored.** D&H's Nymaathap A prose
continues across the printed page break at pp. 48 → 49. The end of the
entry on p. 48 reads `"Her posthumous cult is referred to in the early-"`
and its continuation `"4th Dynasty tomb of Metjen at Saqqara (LS6)."`
sits at the top of printed p. 49 before Perneb's entry. Gemini's OCR
dropped the continuation; the main-session `Read` on the PDF pages
captured both halves. The script concatenates the two halves so the
chunk file emits `Nymaathap A.notes` as the complete D&H paragraph. This
is analogous to the `diff_ramesside.py`-observed `[**Name** continued]`
OCR convention for page-break-wrapped entries in the Ramesside chunks,
but applied pre-extraction (inside the transform) rather than mid-chunk
(inside the OCR output) because Gemini produced a fully-flat output
without the continuation marker the Opus subagent pass used for
Ramesside.

**Reproducibility.** Re-running this script on the same input produces
byte-identical output. No `MALES` table is needed because Gemini
preserved typography.
"""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path("/Users/philipp/Downloads/source-p44-p45.txt")
DST = Path(
    "/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/"
    "dodson-hilton-queens/raw/chunk-p44-p45.md"
)


# First bold-name entry on each printed page, used as a marker to insert
# the page-header `## p. NNN` at that line.
PAGE_BREAKS = {
    48: "Batirytes",    # first entry on printed p. 48 (physical 44)
    49: "Perneb",       # first entry on printed p. 49 (physical 45)
}


HEADER = """\
# The Founders — Brief Lives (printed pp. 48–49; physical PDF pp. 44–45)

Chapter 1 *The Early Dynastic Period and Old Kingdom* → section *The Founders* (1st, 2nd and 3rd Dynasties) → Brief Lives sub-block + trailing Unplaced.

Source: Dodson & Hilton 2004 *The Complete Royal Families of Ancient Egypt* (Thames & Hudson), 1st ed. hardback, pp. 48–49.

OCR by Google Gemini 3.1 Pro (web UI paste, 2026-04-19) after the Claude Code subagent OCR and the Claude Opus 4.7 main-session Write were blocked by content-filtering policy on the Brief Lives prose on the prior two chunks (Seizers PR #77, Kings and Commoners PR #78); same Gemini-fallback path chosen pre-emptively for this chunk. Unlike the two prior Gemini passes, the Founders output **preserved D&H's bold-italic-for-females typographic convention correctly** (`***Name***` italic for females, `**Name**` upright for males) — no main-session typography restoration was needed. Post-processing: prepend this header, insert the two page headers (`## p. 48`, `## p. 49`) at entry boundaries, normalise the styled headings, and append the row-count footer. Implemented as the committed `transform_founders.py` script in this source directory.

Reading order: column 1 → column 2 → column 3 across each printed page. Two printed pages total; both carry Brief Lives entries (no photo-only page in this chunk, unlike K&C which had a full-bleed photograph at printed p. 110). The Unplaced sub-heading sits mid-page on printed p. 49. The page headers match the printed page numbers (physical 44–45 map to printed 48–49, offset +4 uniform, no mid-chunk drift).

**Dynasty scope note**: D&H's section title lists the **1st, 2nd and 3rd Dynasties** jointly under "The Founders". Every row in this extract takes `dynasty: 1` because the chunk is keyed by sub_period rather than by per-row dynasty assignment, and D&H's section placement is the authoritative signal across all six D&H chunks so far. Phase A authority-resolution can refine the per-individual dynasty by reading `notes` cues (e.g. `Shepsetipet`'s notes explicitly say "2nd Dynasty"; `Redji`'s notes say "3rd Dynasty") — the extract preserves those cues verbatim but leaves dynasty assignment coarse here.

---

"""


FOOTER_TEMPLATE = """

---

## Row count

{placed} placed + {unplaced} unplaced = **{total} entries**.

Males ({male_count}): {male_list}. All other entries female.

Unplaced: {unplaced_list}.
"""


NYMAATHAP_CONTINUATION = "4th Dynasty tomb of Metjen at Saqqara (LS6)."


def main() -> None:
    raw = SRC.read_text(encoding="utf-8")

    # Step 0 (pre-transform): restore Nymaathap A's page-break continuation.
    # See the module docstring § "One page-break continuation restored"
    # for the full rationale (OCR recovery + soft-hyphen resolution
    # to plain space per D&H's intended reading of the reassembled
    # line-break).
    raw = raw.replace(
        "Her posthumous cult is referred to in the early-\n",
        "Her posthumous cult is referred to in the early " + NYMAATHAP_CONTINUATION + "\n",
    )

    # Step 1: upgrade bare headings to D&H-styled dotted variants.
    fixed = raw.replace(
        "## Brief Lives",
        "**Brief Lives** • • • • • • • • • • • • • •",
    ).replace(
        "### Unplaced",
        "### Unplaced • • • • • • • • • • •",
    )

    # Step 2: insert page headers at entry boundaries.
    out_lines: list[str] = []
    for line in fixed.splitlines():
        m = re.match(r"^\*\*\*?([^\*\n]+?)\*\*\*?(?=\s*(?:\(|$))", line)
        if m:
            name = m.group(1)
            for printed_page, first_name in PAGE_BREAKS.items():
                if name == first_name:
                    out_lines.append(f"## p. {printed_page}")
                    out_lines.append("")
                    break
        out_lines.append(line)

    body = "\n".join(out_lines)

    # Step 3: count rows and male names for the footer.
    placed_names: list[str] = []
    unplaced_names: list[str] = []
    males: list[str] = []
    in_unplaced = False
    for line in body.splitlines():
        if line.startswith("### Unplaced"):
            in_unplaced = True
            continue
        m = re.match(r"^\*\*\*?([^\*\n]+?)\*\*\*?(?=\s*(?:\(|$))", line)
        if not m:
            continue
        name = m.group(1)
        if name.strip().lower().startswith("brief lives"):
            continue
        # Male entries are `**Name**` (upright bold, no italic asterisks);
        # female entries are `***Name***` (bold italic). We can detect sex
        # from the raw markdown: a line starting with `***` is female.
        if line.startswith("***"):
            pass  # female
        else:
            males.append(name)
        (unplaced_names if in_unplaced else placed_names).append(name)

    male_list = ", ".join(males) if males else "(none)"
    footer = FOOTER_TEMPLATE.format(
        placed=len(placed_names),
        unplaced=len(unplaced_names),
        total=len(placed_names) + len(unplaced_names),
        male_count=len(males),
        male_list=male_list,
        unplaced_list=", ".join(unplaced_names),
    )

    DST.write_text(HEADER + body + footer, encoding="utf-8")
    print(
        f"Wrote {DST} — {len(placed_names)} placed + "
        f"{len(unplaced_names)} unplaced = {len(placed_names) + len(unplaced_names)} entries"
    )


if __name__ == "__main__":
    main()
