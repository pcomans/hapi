"""Pre-extraction OCR-chunk post-processor for the Kings and Commoners chunk.

**Why this exists.** The Claude Code subagent OCR on `source-p98-p103.pdf`
was content-filter-refused (same pattern as chunk 1 Power and chunk 5
Seizers). The Claude Opus 4.7 main-session Read succeeded in surfacing
all 6 pages but the main-session Write of the transcribed prose into
`raw/chunk-p98-p103.md` was also content-filter-blocked. Per ADR-017 §
"Amendment 2026-04-15: external-model fallback for copyright-refusal",
the user pasted the PDF + the verbatim `transcribe-gemini-prompt.md`
into Gemini 3.1 Pro via web UI, saved the output to
`/Users/philipp/Downloads/source-p98-p103.txt`. This script then
transforms that Gemini output into the canonical `raw/chunk-p98-p103.md`.

This is a **pre-extraction** post-processor — it runs against the OCR
chunk file before the 3 extraction subagents read it. That is distinct
from `fix_rows.py`, which runs **post-extraction** against
`reconciled.jsonl`. The `fix_rows.py` pattern is the standard audit-
trail hook for Phase-0 corrections; this script is a one-off handler
for OCR-stage drifts specific to Gemini's rendering of this chunk. It
is committed (not ephemeral) so the transformations are auditable.

**What this script does** — five categories of operation, each with its
verifier's rationale:

1. **Systematic character-level OCR-drift corrections.** Gemini
   rendered capital-I as lowercase-l and Roman-numeral-I as digit-1
   in five specific name tokens. Each correction restores the standard
   D&H printed form, independently verifiable against:
     - the source PDF at `proprietary/books/Dodson & Hilton 2004 -
       Complete Royal Families.pdf` pp. 108–113 (physical 98–103).
     - standard Egyptological sources (Ryholt 1997 SIP, Beckerath 1999
       Handbuch) which use the same capital-I spellings.
     - the egyptologist-reviewer PR #78 review ("OCR drift fixes are
       all correct. … lowercase-l/digit-1 substitutions are classic
       Gemini hallucination patterns.").

   The five substitutions:

   a. `luhetibu → Iuhetibu`. Affects 4 entry `dh_id`s (Iuhetibu A,
      Iuhetibu B Fendy, Iuhetibu C, Iuhetibu Q) and ~10 cross-
      reference mentions in other entries' `notes` prose ("mother
      of Iuhetibu B", "daughter of Iuhetibu Q", etc.).
   b. `ly → Iy` (word-boundary). Affects 1 entry `dh_id` (Iy KW) and
      ~14 cross-reference mentions in other entries' `notes`
      ("sister-in-law of Iy", "brother of Iy", etc.). Word-boundary
      match so it doesn't mangle words like `"only"` or `"formally"`.
   c. `laib → Iaib` (word-boundary). Appears only as a cross-
      reference in `Nubkhaes A.spouse_names` as one of three
      candidate husbands ("either Sobkhotep V, Sobkhotep VI or Iaib").
   d. `Nedjesankh-lu → Nedjesankh-Iu`. Appears in `Hatshepsut C`'s
      notes as the name of her husband.
   e. `Neferhotep 1 → Neferhotep I`. Digit-1 → Roman-numeral-I. The
      regnal-name cross-reference appears in several entries' notes
      (Kemi A, Kemi B, Haankhef A, Nehy, Senebsen, Senebtisi).

2. **Bold-italic typography restoration.** Gemini flattened D&H's
   `***Name***` (bold italic, female) to plain `**Name**` (bold upright,
   male) on every entry. The script restores the italic wrapper on
   every female-typographic entry, using an explicit pre-committed
   `MALES` set of 44 entry names derived from:
     - role-code evidence on the entry (`GF`, `KSon`, `EKSon`, `EKSonB`,
       `Viz`, `Governor of El-Kab`, etc. → male; `KM`, `KW`, `KGW`, `KD`,
       `KDB`, `KSis`, `UWC`, `M2L`, `RO` → female).
     - prose kinship clauses ("son of X", "husband of Y", "father of Z"
       → male; "wife of X", "daughter of Y", "mother of Z" → female).
     - cross-reference evidence ("Husband of Neferhotep A" in Ressonbe's
       notes → Neferhotep A is female; similar for other no-role rows).
   **Note on downstream redundancy.** The new `prompt-kingsandcommoners.md`
   uses a **role-code-first** `sex` inference rule (typography is a
   last-resort tiebreaker only), so the typography restoration below is
   NOT load-bearing for the committed `sex` values — the 3 extraction
   agents independently reported zero typography fallbacks used on the
   108 rows. The restoration is retained for cross-chunk consistency
   with Power / Amarna / Ramesside / Head of South / Seizers, so a
   future consumer who does need typography (e.g. human PDF cross-
   check) sees the same structural markup across all chunks.

3. **Page-header insertion.** The Gemini output does not separate the
   transcription into printed-page chunks. The script inserts `## p. 108`
   through `## p. 113` at the right entry boundaries based on the
   pre-committed `PAGE_BREAKS` table (first-Brief-Life-on-each-page
   pointers derived from the main-session's earlier Read of the PDF).
   **Printed page 110 is skipped** — physical PDF page 100 is a full-
   bleed photograph of the Black Pyramid at Dahshur with zero Brief
   Lives entries, so the page-header sequence jumps p. 109 → p. 111.

4. **Styled-heading replacement.** The Gemini output emits `## Brief
   Lives` and `### Unplaced` as plain markdown headings. The script
   upgrades these to the D&H-styled variants used by other chunks'
   OCR chunk files (`**Brief Lives** • • • • …` and `### Unplaced
   • • • • …`) — the styled forms preserve the visual spacer-dot
   ornament D&H prints around each Brief Lives subsection opener.

5. **Footer append.** The script appends a `## Row count` section
   listing placed / unplaced counts + male names + unplaced names,
   mirroring the footer format other chunks ship.

**Reproducibility.** Re-running this script on the same input
`/Users/philipp/Downloads/source-p98-p103.txt` produces byte-identical
output. The pre-committed `MALES` and `PAGE_BREAKS` tables encode the
main-session's inference decisions once; re-execution honours them.

**Idempotence.** Running this script a second time against the
already-transformed `chunk-p98-p103.md` as input is NOT supported — the
script assumes the raw Gemini-output format as input. The canonical
output path is fixed; re-running with a different source file requires
the raw Gemini output to be present at the SRC path below.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# SRC: Gemini web-UI paste output file. Defaults to the user's Downloads
# folder (the obvious drop zone for Gemini web-UI paste) with a
# predictable filename, but accepts `DH_KC_INPUT` env-var override for
# CI reruns or non-default user layouts. The default path uses
# `Path.home()` so the script is portable across contributor machines.
SRC = Path(
    os.environ.get(
        "DH_KC_INPUT",
        str(Path.home() / "Downloads" / "source-p98-p103.txt"),
    )
)
# DST: committed chunk-file path, resolved repo-relative from this
# script's own location (script sits in the source directory, chunk
# lives in `./raw/` relative to the script).
DST = Path(__file__).resolve().parent / "raw" / "chunk-p98-p103.md"

# Male entry names for typography restoration. Each entry not in this set
# gets `***Name***` bold-italic; entries in this set keep `**Name**` bold
# upright. Derived from role-code evidence + prose kinship + cross-
# reference evidence as documented in the module docstring above.
MALES = {
    # Page 1 (printed 108)
    "Amenhotep A",                  # (KSon) — male
    "Ankhu A",                      # (Overseer of the Fields) — son of Merestekhi
    "Ankhu B",                      # (Viz) — father of wife of brother of Iy
    "Aya A",                        # (Governor of El-Kab) — son-in-law of Nubkhaes A
    "Aya B",                        # (Viz; Governor of El-Kab) — husband of Reditenes B
    "Aya C",                        # (Governor of El-Kab) — son of Aya B
    "Ayameru A",                    # (no role) — father of Aya A
    "Ayameru B",                    # (Viz; Governor of El-Kab) — son of Aya B
    "Bebi C",                       # (EKSon) — son of Sobkhotep VII
    "Dedusobk Bebi",                # (Chief Scribe of the Vizier) — father of Nubkhaes A
    "Haankhef A",                   # (GF) — father of Neferhotep I etc.
    "Haankhef B",                   # (KSon) — son of Neferhotep I
    "Haankhef C Ikherneferet",      # (KSon) — son of Sobkhotep IV
    "Inyotef B",                    # (no role) — son of Amenemhat V, father of Amenemhat VI
    # Page 2 (printed 109)
    "Kay",                          # (no role) — father of Amenemhat VII
    "Kebsi",                        # (Governor of El-Kab) — son of Ayameru B
    "Khakau",                       # (KSon) — brother of Sobkhotep III
    "Mentuhotep A",                 # (GF) — father of Sobkhotep III
    "Mentuhotep B",                 # (Attendant of Dog-Keepers) — nephew of Sobkhotep III
    "Nebankh",                      # (High Steward) — uncle of Nubkhaes A
    # Page 4 (printed 111)
    "Nehy",                         # (Townsman) — grandfather of Neferhotep I etc.
    "Nen?[...]",                    # (no role) — father of Sobkhotep II
    "Redienef",                     # (KSon) — son of Iy
    "Reniseneb B",                  # (no role) — husband of descendant of Senebsen
    "Ressonbe",                     # (no role) — husband of Neferhotep A
    "Sankhptahi",                   # (KSon) — probably later king
    "Seb",                          # (no role) — grandfather of Amenemhat VII
    "Seneb B",                      # (KSon) — brother of Sobkhotep III
    "Sihathor",                     # (KSon) — brother of Neferhotep I
    # Page 5 (printed 112)
    "Sobkhotep A",                  # (Elder of the Portal) — nephew of Sobkhotep III
    "Sobkhotep B",                  # (High Steward) — grandfather of Nubkhaes A
    "Sobkhotep C",                  # (KSon) — later Sobkhotep IV
    "Sobkhotep D Miu",              # (KSon) — son of Sobkhotep IV
    "Sobkhotep E Djadja",           # (KSon) — son of Sobkhotep IV
    "Sobkhotep F",                  # (KSon) — probable son of Sihathor
    "Sobkhotep G",                  # (KSon) — son of Sobkhotep VII
    "Wepwawethotep",                # (Royal Representative) — brother of Iy
    "[...]13A",                     # (no role) — non-royal father of Imyromesha or Inyotef IV
    "[...]13B",                     # (no role) — brother of Iy
    "[...]13C",                     # (no role) — second husband of Iuhetibu A
    "[...]13D",                     # (GF) — father of Sobkhotep V
    # Page 6 Unplaced
    "Dedusobk A",                   # (GF) — father of unknown king, husband of Iuhetibu Q
    "Haankhef Q",                   # (KSon) — son of unknown king
    "Horhotep Q",                   # (KSon) — son of unknown king
    "Sobkhotep Q",                  # (KSon) — son of unknown king
}


# First bold name of each printed-page break in the Gemini output reading
# order. Printed page 110 / physical 100 is photo-only (no entries), hence
# the jump from p. 109 → p. 111.
PAGE_BREAKS = {
    108: "Amenhotep A",
    109: "Iuhetibu A",  # post-(I/l correction)
    111: "Nehy",
    112: "Senebhenas B",
    113: "[...]13D",
}


HEADER = """\
# Kings and Commoners — Brief Lives (printed pp. 108–113; physical PDF pp. 98–103)

Chapter 2 *The 1st Intermediate Period, the Middle Kingdom and 2nd Intermediate Period* → section *Kings and Commoners* (13th Dynasty, the start of the Second Intermediate Period) → Brief Lives sub-block + trailing Unplaced.

Source: Dodson & Hilton 2004 *The Complete Royal Families of Ancient Egypt* (Thames & Hudson), 1st ed. hardback, pp. 108–113.

OCR by Google Gemini 3.1 Pro (web UI paste, 2026-04-19) after the Claude Code subagent OCR and the Claude Opus 4.7 main-session Write were both blocked by content-filtering policy on the Brief Lives prose. Same Gemini-fallback path as chunk 1 (Power and Glory, PR #37) and chunk 5 (Seizers of the Two Lands, PR #77). Gemini's output lost D&H's bold-italic-for-females typographic convention; main-session post-processing restored `***Name***` for every female entry (inferred from role codes, prose pronouns, and cross-references — e.g. another entry's "Wife of Y" fixes Y as male). Gemini's OCR also introduced two systematic character-level drifts that the post-processing corrected: `luhetibu → Iuhetibu` (4 entries), `ly → Iy` (1 primary entry plus many cross-references), `laib → Iaib` (1 cross-reference), `Nedjesankh-lu → Nedjesankh-Iu` (1 entry), and `Neferhotep 1 → Neferhotep I` (1 entry) — Gemini rendered D&H's capital-I as lowercase-l and Roman-numeral I as digit 1 in specific positions. Photo-caption text and genealogical-chart figure contents are excluded per the chunk-1 OCR rules.

The post-processing is implemented as the committed `transform_kc.py` script in this source directory, auditable from source. Running it against the Gemini-output text file produces this chunk file byte-identically.

Reading order: column 1 → column 2 → column 3 across each printed page. Six printed pages total; **printed page 110 / physical page 100 is a full-bleed photograph of the Black Pyramid at Dahshur and contains no Brief Lives entries**, so it has no `## p. 110` section header below. The page headers match the printed page numbers (physical 98–103 map to printed 108–113, offset +10; no mid-chunk drift).

The chunk also contains a **cross-section duplicate**: `Hetepti` (KM; M2L; UWC) appears here as a one-line stub `See previous section` with a pointer back to the Seizers of the Two Lands chunk, where her full Brief Life is printed. Per the composite-key convention established in chunk 3 (Ramesside — `Takhat A`, `Isetneferet C`), both rows are emitted: the full-prose row sits in the Seizers chunk's extract, and this chunk emits the stub row with `notes: "See previous section."` and its own `sub_period: "Kings and Commoners"`. Phase A reconciles them downstream to a single canonical individual.

---

"""


FOOTER_TEMPLATE = """

---

## Row count

{placed} placed + {unplaced} unplaced = **{total} entries**.

Males ({male_count}): {male_list}. All other entries female.

Unplaced: {unplaced_list}.
"""


def main() -> None:
    raw = SRC.read_text(encoding="utf-8")

    # Step 1: systematic OCR fixes (see module docstring § 1 for rationale).
    fixed = raw
    fixed = fixed.replace("luhetibu", "Iuhetibu")
    fixed = re.sub(r"\bly\b", "Iy", fixed)
    fixed = re.sub(r"\blaib\b", "Iaib", fixed)
    fixed = fixed.replace("Nedjesankh-lu", "Nedjesankh-Iu")
    fixed = fixed.replace("Neferhotep 1", "Neferhotep I")

    # Step 4: upgrade bare headings to D&H-styled variants.
    fixed = fixed.replace(
        "## Brief Lives",
        "**Brief Lives** • • • • • • • • • • • • • •",
    ).replace(
        "### Unplaced",
        "### Unplaced • • • • • • • • • • •",
    )

    # Step 2: restore bold-italic on females.
    def _promote_to_italic(match: re.Match) -> str:
        name = match.group(1)
        if name in MALES:
            return f"**{name}**"
        # All-caps cross-reference (e.g. `SOBKHOTEP IV`) — leave as-is.
        if name.isupper() and len(name) >= 3:
            return f"**{name}**"
        return f"***{name}***"

    fixed = re.sub(
        r"(?m)^\*\*([^\*\n]+?)\*\*(?=\s*(?:\(|\n))",
        _promote_to_italic,
        fixed,
    )

    # Step 3: insert page headers.
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

    # Step 5: count rows for the footer.
    placed_names: list[str] = []
    unplaced_names: list[str] = []
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
        # Drop the all-caps skip — `[...]13A` and similar lacuna-bracketed
        # names have isupper()=True (the only cased chars are uppercase)
        # but they ARE legitimate entry heads. The `^` line-anchor on the
        # regex already filters inline cross-reference `**SOBKHOTEP IV**`.
        (unplaced_names if in_unplaced else placed_names).append(name)

    male_list = ", ".join(sorted(MALES, key=str.lower))
    footer = FOOTER_TEMPLATE.format(
        placed=len(placed_names),
        unplaced=len(unplaced_names),
        total=len(placed_names) + len(unplaced_names),
        male_count=len(MALES),
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
