"""Beckerath 1997 chronology — chunk-file post-processing.

Runs AFTER the OCR subagent emits `raw/chunk-p105-p109.md` and BEFORE the
3-subagent extraction step reads it.

The OCR step produces structured Markdown that mostly preserves Beckerath's
typography (italic section headings, dynasty headings with parenthetical date
ranges, tab-separated king rows). What it loses, and this post-processor
restores, is **persistent context across page boundaries**:

- Dynasty heading context. Beckerath's heading e.g. `**4. Dynastie (etwa
  2639/2589–2504/2454)**` carries an `etwa` (German "approximately") qualifier
  that applies to every king row in that dynasty's span. When the dynasty
  spans a page break (book p187/p188 in the Dyn-4 case), agents reading the
  later page have lost the heading context and silently flip rows to
  `start_approximate=false`. Observed in PR #128's tie-break audit:
  rows 04.02–04.08 all needed `fix_rows.py` overrides to restore the `etwa`
  qualifier. (Other dynasties propagated correctly because their spans don't
  cross a page break.)
- Section (Reich/Zwischenzeit) heading context. The eight italic section
  headings (`FRÜHZEIT`, `ALTES REICH`, `I. ZWISCHENZEIT`, `MITTLERES REICH`,
  `II. ZWISCHENZEIT`, `NEUES REICH`, `III. ZWISCHENZEIT`, `SPÄTZEIT`) drive
  the `period` field. Dyn 24 and 25 sit under `### III. ZWISCHENZEIT`; the
  next section heading `### SPÄTZEIT` opens Dyn 26. Agents reading the
  short Dyn-24/25 cluster look ahead for the next section heading and
  mis-attribute these rows to `Spätzeit`. Observed in PR #128 fix_rows.py
  overrides 24.01 and 24.02.

The post-processor emits two HTML-comment annotations:

1. After every `**N. Dynastie ...**` heading line, emit
   `<!-- period: <SectionTitleCase> -->` so the section is *directly attached*
   to the dynasty heading. Defeats the look-ahead-too-far misfile.

2. After every `## Book pNNN` page boundary that falls *inside* a dynasty's
   span (i.e. the next non-empty line is NOT itself a section heading or new
   dynasty heading), emit
   `<!-- dynasty-context: <full-dynasty-heading-text> -->` and
   `<!-- period: <SectionTitleCase> -->`
   so agents reading the second page of a multi-page dynasty have the
   heading context refreshed inline. Defeats the page-break-loses-`etwa`
   case.

The agents' existing extraction rules (already documented in `prompt.md`)
interpret the dynasty heading's `etwa` / `ca.` qualifier per the per-heading
rules. The post-processor does NOT add new agent-facing semantics — it just
makes the existing context inescapably visible at every page within a span.

Invocation:

    uv run --project pipeline python \\
        pipeline/pipeline/authority/sources/beckerath-1997-chronologie/postprocess.py \\
        --input raw/chunk-p105-p109.md \\
        --output raw/chunk-p105-p109.md   # in-place by default

The OCR step's output is gitignored; the post-processed file lives at the
same path so the 3-subagent extraction can continue to read
`raw/chunk-p105-p109.md` without changing the agent prompt's input path.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

# Italicised section heading shapes Beckerath uses. Keys are the chunk-file
# uppercase form (as the OCR subagent renders the italic headings); values are
# the title-case form expected in the `period` field of the canonical schema.
# Per the agent prompt:
#   `"Vorgeschichte"`, `"Frühzeit"`, `"Altes Reich"`, `"I. Zwischenzeit"`,
#   `"Mittleres Reich"`, `"II. Zwischenzeit"`, `"Neues Reich"`,
#   `"III. Zwischenzeit"`, `"Spätzeit"`.
SECTION_TITLE_CASE: dict[str, str] = {
    "VORGESCHICHTE (PRÄDYNASTISCHE ZEIT)": "Vorgeschichte",
    "FRÜHZEIT": "Frühzeit",
    "ALTES REICH": "Altes Reich",
    "I. ZWISCHENZEIT": "I. Zwischenzeit",
    "MITTLERES REICH": "Mittleres Reich",
    "II. ZWISCHENZEIT": "II. Zwischenzeit",
    "NEUES REICH": "Neues Reich",
    "III. ZWISCHENZEIT": "III. Zwischenzeit",
    "SPÄTZEIT": "Spätzeit",
}

# A section heading line in the OCR markdown is `### <UPPERCASE NAME>`.
_SECTION_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$")

# A dynasty heading is bolded: `**N. Dynastie (...)**` or
# `**N. Dynaste (...)**` (Beckerath's spelling drift in late dynasties; see
# chunk lines 246/249/256/261). Also handles compound headings
# `9./10. Dynastie (in Herakleopolis, etwa ...)` which are NOT bolded in the
# OCR output. The compound case is matched by `_DYNASTY_HEADING_COMPOUND_RE`.
#
# Group 1 = bolded inner text (`N. Dynastie (etwa ...)`); group 2 = remainder
# of the line AFTER the closing `**`. Capturing the remainder defensively
# preserves the dynasty's parenthetical qualifier (`etwa`, `ca.`, dynastic
# placement notes) when a future OCR variant emits `**N. Dynastie** (etwa ...)`
# with the parenthetical OUTSIDE the bold markers.
_DYNASTY_HEADING_BOLD_RE = re.compile(
    r"^\*\*(\d+(?:\.\s*[a-z])?\.?\s*Dynast(?:ie|e)\b.*?)\*\*(.*)$"
)
# Compound headings like `9./10. Dynastie (...)` are NOT bolded in the
# current OCR output, but stochastic LLM-OCR variants may introduce bold
# markers on future regenerations. Optional `**…**` wrapping is matched
# defensively without changing the captured inner text.
_DYNASTY_HEADING_COMPOUND_RE = re.compile(
    r"^(?:\*\*)?(\d+\.?/\d+\.?\s*Dynast(?:ie|e)\b.*?)(?:\*\*)?$"
)

_PAGE_BOUNDARY_RE = re.compile(r"^##\s+Book\s+p\d+\s*$")

# Annotations this post-processor injects. Stripped on a re-run so the
# function is idempotent (running twice yields the same output as once).
_INJECTED_COMMENT_RE = re.compile(
    r"^<!--\s+(period|dynasty-context):\s.*-->\s*$"
)


def _is_section_heading(line: str) -> tuple[bool, str | None]:
    """Classify a line as a section heading.

    Returns `(is_heading, title_cased_name)`:
    - `(False, None)` — not a `### ...` heading at all (e.g. a king row, page
      boundary, dynasty heading)
    - `(True, "Frühzeit")` — recognised section heading; second value is the
      title-cased period name from `SECTION_TITLE_CASE`
    - `(True, None)` — looks like a section heading (`### Something`) but
      `Something` is not one of the eight canonical period headings. Beckerath
      uses `### Supplement zu A` for the prenomen-supplement appendix; treating
      the supplement as a section boundary is the right call (it resets the
      dynasty context too, defeating the leak from the preceding `### SPÄTZEIT`
      block into the supplement's `**19. Dynastie**` heading).
    """
    m = _SECTION_HEADING_RE.match(line)
    if not m:
        return False, None
    raw = m.group(1).strip(" .").upper()
    return True, SECTION_TITLE_CASE.get(raw)


def _is_dynasty_heading(line: str) -> str | None:
    """Return the dynasty heading inner text if `line` is a dynasty heading.

    For the bolded form, concatenates the inside-`**` text with any text that
    follows the closing `**` on the same line (defensively preserves an
    OCR-variant where the parenthetical qualifier is outside the bold markers).
    For the compound form (`9./10. Dynastie ...`), returns the line verbatim.
    Strips whitespace.
    """
    m = _DYNASTY_HEADING_BOLD_RE.match(line)
    if m:
        return (m.group(1) + m.group(2)).strip()
    m = _DYNASTY_HEADING_COMPOUND_RE.match(line)
    if m:
        return m.group(1).strip()
    return None


def _is_page_boundary(line: str) -> bool:
    return bool(_PAGE_BOUNDARY_RE.match(line))


def _is_blank(line: str) -> bool:
    return not line.strip()


def process_chunk(md: str) -> str:
    """Annotate the OCR markdown with persistent dynasty + section context.

    See the module docstring for what this restores and why. Pure function:
    same input always yields same output.
    """
    # Strip any previously-injected comments first so the function is
    # idempotent. A re-run on its own output produces the same result.
    raw_lines = md.splitlines()
    lines = [ln for ln in raw_lines if not _INJECTED_COMMENT_RE.match(ln)]
    out: list[str] = []
    current_section: str | None = None
    current_dynasty_heading: str | None = None

    i = 0
    while i < len(lines):
        line = lines[i]

        is_section, section = _is_section_heading(line)
        if is_section:
            # Update section state on EVERY `### ...` heading, recognised or
            # not. An unrecognised heading (e.g. `### Supplement zu A`) sets
            # `current_section = None` and resets the dynasty context, which
            # prevents the previous section's period from leaking onto the
            # supplement's `**19. Dynastie**` etc. headings.
            current_section = section
            current_dynasty_heading = None
            out.append(line)
            i += 1
            continue

        dynasty = _is_dynasty_heading(line)
        if dynasty is not None:
            current_dynasty_heading = dynasty
            out.append(line)
            # Attach the section directly to the dynasty heading so agents
            # don't have to look upward for it. Defeats the Dyn-24/25
            # mis-attribution to Spätzeit case. Skipped when current_section
            # is None — the supplement's dynasty headings inherit period via
            # the existing prompt rule that supplement entries merge by name
            # into the main Übersicht rows.
            if current_section:
                out.append(f"<!-- period: {current_section} -->")
            i += 1
            continue

        if _is_page_boundary(line):
            out.append(line)
            # Look ahead: if the next non-blank line is itself a section or
            # dynasty heading, the agent will get fresh context from that
            # heading; no refresh needed. `_is_section_heading` returns
            # `(True, ...)` for any `### ...` line whether the name is
            # recognised or not, so unrecognised section headings still
            # suppress the duplicate refresh.
            j = i + 1
            while j < len(lines) and _is_blank(lines[j]):
                j += 1
            need_refresh = True
            if j < len(lines):
                if (
                    _is_section_heading(lines[j])[0]
                    or _is_dynasty_heading(lines[j]) is not None
                ):
                    need_refresh = False
            else:
                need_refresh = False
            if need_refresh and current_dynasty_heading:
                out.append(
                    f"<!-- dynasty-context: {current_dynasty_heading} -->"
                )
                if current_section:
                    out.append(f"<!-- period: {current_section} -->")
            i += 1
            continue

        out.append(line)
        i += 1

    # Preserve the trailing newline from the input if it had one.
    result = "\n".join(out)
    if md.endswith("\n"):
        result += "\n"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).parent / "raw" / "chunk-p105-p109.md",
        help="Path to the OCR chunk file (default: raw/chunk-p105-p109.md).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path. Defaults to overwriting --input in place.",
    )
    args = parser.parse_args()
    output_path = args.output if args.output is not None else args.input
    md = args.input.read_text(encoding="utf-8")
    annotated = process_chunk(md)
    output_path.write_text(annotated, encoding="utf-8")
    print(f"wrote {output_path} ({len(annotated)} bytes)")


if __name__ == "__main__":
    main()
