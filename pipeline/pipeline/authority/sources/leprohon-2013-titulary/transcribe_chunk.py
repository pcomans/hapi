"""Leprohon 2013 deterministic pypdf transcription (chunk-agnostic).

Pulls a physical-PDF-page range via pypdf, applies a Manuel de Codage (MdC)
→ Egyptological-Unicode normalization on transliteration tokens (identified
structurally: between a name-type label like `Horus:` and the parenthetical
anglicised gloss `(...)` that follows), and writes the result to
`raw/chunk-p<start>-p<end>-pypdf.md`.

Per the chunk-1 validation (PR #83), the OCR subagent step is skipped for
chunks 2+ — pypdf+MdC is strictly more accurate on transliteration content
for this born-digital InDesign PDF, and the 3-agent extraction majority
vote downstream provides the redundancy layer. See transcribe.md for the
policy.

Invocation:

    # Run the default (latest) chunk:
    uv run --project pipeline python \\
        pipeline/pipeline/authority/sources/leprohon-2013-titulary/transcribe_chunk.py

    # Run a specific chunk by name (defined in CHUNKS below):
    uv run --project pipeline python \\
        pipeline/pipeline/authority/sources/leprohon-2013-titulary/transcribe_chunk.py \\
        --chunk old-kingdom

    # Run an ad-hoc page range (useful for scoping future chunks):
    uv run --project pipeline python \\
        pipeline/pipeline/authority/sources/leprohon-2013-titulary/transcribe_chunk.py \\
        --pages 51-68
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from pypdf import PdfReader

# Registered chunks. Each entry: chunk-name → (physical_start, physical_end,
# chapter_label). Physical-page ranges verified at the chunk's FIRST and LAST
# page per the playbook, with the printed-to-physical offset noted alongside.
CHUNKS: dict[str, tuple[int, int, str]] = {
    # Chunk 1 (PR #83): chapter II Early Dynastic Period (Dyn 0/1/2),
    # printed 21-29, offset +21. NOTE: this range silently omitted printed
    # p. 30 (Dyn 2 tail `9. SENEFERKA` + `Dynasty 2a` sub-section with 2
    # Ramesside-only entries). Chunk 2 picks those up.
    "early-dynastic": (42, 50, "II. Early Dynastic Period"),
    # Chunk 2 (this PR): Dyn 2 tail + Dyn 2a (missed from chunk 1) + chapter
    # III Old Kingdom (Dyn 3-8 + Dyn 3a + Dyn 8a). Printed 30-48, offset +21,
    # physical 51-69. Initial extraction run scoped to 51-68 (printed 30-47)
    # cut off mid-Dyn-8a after entry 2; extended to 51-69 to include Dyn 8a
    # entries 3-8 (Iti, Imhotep, Hotep, Khui, Isu, Iytjenu) on printed p. 48.
    "old-kingdom": (51, 69, "III. Old Kingdom (+ Dyn 2/2a tail)"),
    # Chunk 3: chapter IV First Intermediate Period. Printed 49-53, offset
    # +21, physical 70-74. Contains Dyn 9-10a (9 entries, 8 Ramesside-only +
    # 1 contemporarily-attested Neferkare III; entry 2 is a `/////` stub for
    # a Turin-Canon name-missing row), Dyn 9-10b (6 entries, all
    # contemporarily attested), and Dyn 11a (4 entries: Mentuhotep I +
    # Intef I/II/III, all contemporarily attested — though Mentuhotep I's
    # `Later Horus name: tp a*` is itself flagged as a Ramesside fabrication
    # per Leprohon's footnote 27).
    "fip": (70, 74, "IV. First Intermediate Period"),
    # Chunk 4 (this PR): chapter V Middle Kingdom — the "classical" MK
    # proper. Printed 54-60, offset +21, physical 75-81. Dyn 11b
    # (Mentuhotep II/III/IV — the late Eleventh Dynasty, paired with the
    # early Dyn 11a that landed in chunk 3 FIP) + Dyn 12 (Amenemhat I-IV,
    # Senwosret I-III, Queen Sobekneferu). ~19 kings but with very dense
    # per-king titularies (Mentuhotep II alone has three successive
    # titulary reforms during his 51-year reign; Dyn 12 kings routinely
    # have 3-5 variant entries per name type). The chunk boundary stops
    # at physical p. 81 which contains both the last Dyn 12 entry
    # (Queen Sobekneferu) AND the opening of Dyn 13 — the prompt
    # explicitly tells agents to stop at the Dyn 13 header.
    #
    # Note: Leprohon places Dyn 13, 13a, 14, 14a all in chapter V MK
    # (despite their "post-Sobekneferu" chronology), because only Dyn
    # 15-17 are chapter VI SIP per his editorial choice. These later MK
    # ephemeral dynasties ship as their own chunks (future chunk 5 = Dyn
    # 13 alone ~37 kings; future chunk 6 = Dyn 13a+14+14a ~32 kings).
    "mk": (75, 81, "V. Middle Kingdom (Dyn 11b + Dyn 12)"),
}
DEFAULT_CHUNK = "mk"

PDF_PATH = (
    Path(__file__).resolve().parents[5]
    / "proprietary"
    / "books"
    / "Leprohon 2013 - The Great Name.pdf"
)
RAW_DIR = Path(__file__).parent / "raw"


def _out_path(physical_start: int, physical_end: int) -> Path:
    return RAW_DIR / f"chunk-p{physical_start}-p{physical_end}-pypdf.md"

# Manuel de Codage → Egyptological Unicode. Applied only inside transliteration
# tokens, never to surrounding prose or to the anglicised parenthetical gloss.
MDC_MAP: dict[str, str] = {
    "A": "ꜣ",
    "a": "ꜥ",
    "H": "ḥ",
    "x": "ḫ",
    "X": "ẖ",
    "S": "š",
    "T": "ṯ",
    "D": "ḏ",
    "q": "ḳ",
}

# Name-type labels Leprohon uses in chapter II (Early Dynastic Period). The
# regex below also matches a trailing variant-number (`Horus 1`, `Two Ladies
# 3`) without hardcoding each one.
NAME_LABELS: tuple[str, ...] = (
    "Horus/Seth",
    "Later cartouche name",
    "Later Horus name",
    "Two Ladies",
    "Golden Horus",
    "Seth name",
    "Throne and birth",
    "Throne and Birth",
    "Horus",
    "Throne",
    "Birth",
    "Cartouche",
)

# A single Leprohon name row, after pypdf text-layer extraction, looks like:
#
#     Horus: iry-Hr (iry-hor), The companion of Horus9
#
# Regex groups:
#   1: label, optional trailing variant digit  (e.g. "Horus", "Two Ladies 3")
#   2: whitespace after the colon
#   3: the transliteration token-span BEFORE the anglicised gloss
#   4: the rest of the line (parenthetical gloss + translation + footnote digit)
#
# The transliteration boundary is " (" (whitespace + opening paren) rather than
# a bare "(" because transliterations themselves contain embedded parens for
# optional glyphs: `n(y)-<ḥr>`, `htp(.w)`, `pr(w)`, `mr(y)`. Anchoring to the
# whitespace-paren boundary correctly separates translit from gloss in all
# chunk-1 cases.
#
# The label alternation is sorted longest-first so that "Horus/Seth" wins over
# "Horus" and "Later cartouche name" wins over "Seth name" even though they
# share no suffix — regex alternation is first-match-wins.
NAME_ROW_RE: re.Pattern[str] = re.compile(
    r"^((?:"
    + "|".join(re.escape(lbl) for lbl in NAME_LABELS)
    + r")(?:\s\d+)?):(\s*)(.+?)(\s+\(.*)$"
)


def mdc_to_unicode(text: str) -> str:
    """Apply MdC → Egyptological Unicode on a single transliteration token-span.

    Operates character-by-character on the MdC-substitution subset. Non-MdC
    characters (digits, punctuation, already-Unicode diacritics, parenthesised
    optional glyphs, angle-bracketed partial readings) pass through unchanged.
    """
    return "".join(MDC_MAP.get(ch, ch) for ch in text)


def _normalize_line(line: str) -> str:
    """Apply MdC mapping to the transliteration span of a Leprohon name row.

    Lines that are not name rows (prose paragraphs, headwords, footnotes,
    section headers, empty lines) pass through unchanged — the MdC substitutions
    would corrupt regular English text (`a` → `ꜥ` would turn "and" into "ꜥnd").
    """
    match = NAME_ROW_RE.match(line)
    if match is None:
        return line
    label, whitespace, translit, rest = match.groups()
    return f"{label}:{whitespace}{mdc_to_unicode(translit)}{rest}"


def transcribe(
    physical_start: int,
    physical_end: int,
    chapter_label: str,
    pdf_path: Path,
    out_path: Path,
) -> None:
    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    # Loud-failure bounds check: give a descriptive error before pypdf would
    # raise an opaque IndexError on `reader.pages[physical_page - 1]`. The
    # CLI accepts arbitrary `--pages <start>-<end>` values, so this is the
    # right layer to validate rather than the argparse parser.
    if physical_start < 1 or physical_end > total_pages:
        raise ValueError(
            f"requested physical pages {physical_start}-{physical_end} "
            f"exceed PDF bounds 1-{total_pages} "
            f"({pdf_path.name!r})"
        )
    parts: list[str] = [
        f"<!-- Leprohon 2013 {chapter_label}, physical pp. "
        f"{physical_start}-{physical_end}, deterministic pypdf+MdC "
        f"transcription. -->\n\n"
    ]
    for physical_page in range(physical_start, physical_end + 1):
        page = reader.pages[physical_page - 1]  # pypdf is 0-indexed
        text = page.extract_text()
        parts.append(f"<!-- physical page {physical_page} -->\n")
        for raw_line in text.splitlines():
            parts.append(_normalize_line(raw_line) + "\n")
        parts.append("\n")
    out_path.parent.mkdir(exist_ok=True, parents=True)
    out_path.write_text("".join(parts))


def _parse_pages(spec: str) -> tuple[int, int]:
    """Parse `START-END` into an inclusive (start, end) tuple."""
    match = re.match(r"^(\d+)-(\d+)$", spec)
    if match is None:
        raise ValueError(f"--pages must be `START-END` format, got {spec!r}")
    start, end = int(match.group(1)), int(match.group(2))
    if start > end:
        raise ValueError(f"--pages start {start} must be ≤ end {end}")
    return start, end


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--chunk",
        choices=sorted(CHUNKS),
        default=DEFAULT_CHUNK,
        help=f"Registered chunk name (default: {DEFAULT_CHUNK}).",
    )
    group.add_argument(
        "--pages",
        type=_parse_pages,
        help="Ad-hoc physical-page range, e.g. '51-68'. Writes to "
        "raw/chunk-p<start>-p<end>-pypdf.md without a chapter label.",
    )
    args = parser.parse_args()
    if args.pages is not None:
        start, end = args.pages
        label = f"ad-hoc p{start}-p{end}"
    else:
        start, end, label = CHUNKS[args.chunk]
    out = _out_path(start, end)
    transcribe(start, end, label, PDF_PATH, out)
    size = out.stat().st_size
    print(f"wrote {out} ({size} bytes) — {label}")
