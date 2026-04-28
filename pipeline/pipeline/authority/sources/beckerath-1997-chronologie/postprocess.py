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
import os
import re
import tempfile
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

# Canonical Beckerath dynasty → period mapping, sourced from Beckerath's own
# Anhang A section headings as he prints them in the 1997 Chronologie. The
# `<!-- period: ... -->` annotation is derived from THIS mapping, not from
# the OCR-step's section-heading state. Reason: stochastic LLM-OCR can drop
# a section heading entirely (observed: chunk-p105-p109.md missing
# `### II. ZWISCHENZEIT` between Dyn 12 and Dyn 13), and the post-processor
# must not silently amplify that omission into a five-dynasty period mis-
# attribution downstream. Dynasty number is unambiguous in the OCR (every
# dynasty heading carries a leading integer); period derivation from it is
# robust against section-heading omissions.
DYNASTY_PERIOD: dict[int, str] = {
    0: "Vorgeschichte",
    1: "Frühzeit",
    2: "Frühzeit",
    3: "Altes Reich",
    4: "Altes Reich",
    5: "Altes Reich",
    6: "Altes Reich",
    7: "Altes Reich",
    8: "Altes Reich",
    9: "I. Zwischenzeit",
    10: "I. Zwischenzeit",
    11: "Mittleres Reich",
    12: "Mittleres Reich",
    13: "II. Zwischenzeit",
    14: "II. Zwischenzeit",
    15: "II. Zwischenzeit",
    16: "II. Zwischenzeit",
    17: "II. Zwischenzeit",
    18: "Neues Reich",
    19: "Neues Reich",
    20: "Neues Reich",
    21: "III. Zwischenzeit",
    22: "III. Zwischenzeit",
    23: "III. Zwischenzeit",
    24: "III. Zwischenzeit",
    25: "III. Zwischenzeit",
    26: "Spätzeit",
    27: "Spätzeit",
    28: "Spätzeit",
    29: "Spätzeit",
    30: "Spätzeit",
    31: "Spätzeit",
}

# Leading-dynasty-number extractor for both bolded `**N. Dynastie ...**` and
# compound `N./M. Dynastie ...` headings. The first integer is the canonical
# dynasty key (compound `9./10.` resolves to 9 — the period is the same for
# both halves of a compound heading anyway).
_LEADING_DYN_NUM_RE = re.compile(r"^(\d+)")

# A section heading line in the OCR markdown is `### <UPPERCASE NAME>`.
_SECTION_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$")

# Unified dynasty heading regex. Matches BOTH
#   `N. Dynastie (etwa ...)` / `N. Dynaste` (single, with Beckerath's
#       spelling drift `Dynaste` in chapters Dyn 28-31)
#   `N./M. Dynastie (...)`     (compound, e.g. `9./10. Dynastie (...)`)
# with optional `**...**` bold markers anywhere on the line — bolding the
# whole heading, just the dynasty name, or none of it. Stochastic LLM-OCR
# may emit any of these variants on future regenerations of the chunk.
#
# Group 1 captures the entire heading text (possibly with embedded `**`
# markers when bolding wraps only part of the line, e.g.
# `**N. Dynastie** (etwa ...)`). The caller strips any embedded `**` from
# the captured text before using it as the dynasty-context comment value.
_DYNASTY_HEADING_RE = re.compile(
    r"^\*{0,2}\s*"
    r"((?:\d+\.?/\d+\.?|\d+(?:\.\s*[a-z])?\.?)\s*Dynast(?:ie|e)\b.*?)"
    r"\s*\*{0,2}\s*$"
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

    Handles all OCR-formatting variants: single (`N. Dynastie ...`) or
    compound (`N./M. Dynastie ...`); bolded entirely (`**...**`), partially
    (`**N. Dynastie** (etwa ...)`), or not at all. Strips embedded `**`
    markers from the captured text before returning so the dynasty-context
    comment never contains stray bold markers (which would confuse agents
    looking for the verbatim heading text).
    """
    m = _DYNASTY_HEADING_RE.match(line)
    if not m:
        return None
    return m.group(1).replace("**", "").strip()


def _dynasty_number(heading: str) -> int | None:
    """Extract the leading integer dynasty number from a heading string.

    Handles `4. Dynastie (...)`, `28. Dynaste`, `9./10. Dynastie (...)`,
    `0. Dynastie (...)`. Returns None if no leading integer is found.
    """
    m = _LEADING_DYN_NUM_RE.match(heading)
    if m:
        return int(m.group(1))
    return None


def _period_for_dynasty(heading: str) -> str | None:
    """Look up the canonical period for a dynasty heading.

    Returns the title-cased period name from `DYNASTY_PERIOD`, or None if
    the dynasty number cannot be parsed or is not in the canonical mapping.
    Per constitutional rule 2 (loud failures), an unknown dynasty number is
    surfaced as None so the caller can decide whether to omit the annotation
    or raise.
    """
    n = _dynasty_number(heading)
    if n is None:
        return None
    return DYNASTY_PERIOD.get(n)


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
    # `inside_main_uebersicht` flips from False (before Anhang A's first
    # canonical section heading) to True (after Frühzeit/Vorgeschichte etc.
    # is seen) and back to False on an unrecognised `### ...` heading
    # (Supplement zu A and similar). Period annotations are suppressed
    # outside the main Übersicht because supplement entries merge by name
    # into Anhang A rows per the prompt's existing rule.
    inside_main_uebersicht: bool = False
    current_dynasty_heading: str | None = None
    current_period: str | None = None

    i = 0
    while i < len(lines):
        line = lines[i]

        is_section, section = _is_section_heading(line)
        if is_section:
            # Recognised period heading flips us into the main Übersicht;
            # unrecognised heading (Supplement zu A, the chapter title
            # `### A. CHRONOLOGISCHE ÜBERSICHT ...`) flips us out. In both
            # cases the dynasty context is reset.
            inside_main_uebersicht = section is not None
            current_dynasty_heading = None
            current_period = None
            out.append(line)
            i += 1
            continue

        dynasty = _is_dynasty_heading(line)
        if dynasty is not None:
            current_dynasty_heading = dynasty
            # Period is derived from the dynasty number via the canonical
            # mapping, NOT from the surrounding section heading. This makes
            # the post-processor robust against OCR-step omissions of a
            # section heading (observed: `### II. ZWISCHENZEIT` missing
            # between Dyn 12 and Dyn 13 in the current chunk-p105-p109.md).
            current_period = _period_for_dynasty(dynasty)
            out.append(line)
            if inside_main_uebersicht and current_period:
                out.append(f"<!-- period: {current_period} -->")
            i += 1
            continue

        if _is_page_boundary(line):
            out.append(line)
            # Look ahead: if the next non-blank line is itself a section or
            # dynasty heading, the agent will get fresh context from that
            # heading; no refresh needed.
            j = i + 1
            while j < len(lines) and _is_blank(lines[j]):
                j += 1
            # Refresh only if the next non-blank line exists AND is neither
            # a section heading (any `### ...`) nor a dynasty heading. When
            # either heading is the immediate next content line, the agent
            # gets fresh context from that heading itself; an additional
            # comment refresh would just be noise.
            need_refresh = (
                j < len(lines)
                and not _is_section_heading(lines[j])[0]
                and _is_dynasty_heading(lines[j]) is None
            )
            if need_refresh and current_dynasty_heading:
                out.append(
                    f"<!-- dynasty-context: {current_dynasty_heading} -->"
                )
                if inside_main_uebersicht and current_period:
                    out.append(f"<!-- period: {current_period} -->")
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
    # Atomic write: stage to a temp file in the same directory, then rename
    # over the destination. Prevents data loss if the script is interrupted
    # mid-write (the destination either holds the previous content or the
    # new content, never a partial write). The temp file lives in the same
    # directory so the final `os.replace` is a same-filesystem rename.
    output_path = output_path.resolve()
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        tmp.write(annotated)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, output_path)
    print(f"wrote {output_path} ({len(annotated)} bytes)")


if __name__ == "__main__":
    main()
