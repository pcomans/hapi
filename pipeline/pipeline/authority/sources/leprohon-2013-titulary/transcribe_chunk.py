"""Leprohon 2013 chunk-1 deterministic pypdf transcription.

Pulls physical PDF pages 42-50 (= printed pp. 21-29, chapter II *Early Dynastic
Period*) via pypdf, applies a Manuel de Codage (MdC) → Egyptological-Unicode
normalization on transliteration tokens (identified structurally: between a
name-type label like `Horus:` and the parenthetical anglicised gloss `(...)`
that follows), and writes the result to `raw/chunk-p42-p50-pypdf.md`.

Runs in parallel with an OCR-subagent transcription to
`raw/chunk-p42-p50-ocr.md` — the user's choice on 2026-04-20 was to run both
methods and diff the outputs before feeding the 3 extraction subagents. This
script is the deterministic arm of that parallel pair; the OCR path is the
independent-source arm. Both outputs are gitignored.

Invoked from the repo root:

    cd pipeline && uv run python pipeline/authority/sources/leprohon-2013-titulary/transcribe_chunk.py

Future chunks can generalise the PAGES tuple to a CLI arg; chunk 1 hard-codes
it to keep the extractor-validation chunk's scope unambiguous.
"""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

# Chunk 1: physical PDF pages 42-50 (inclusive), = printed pages 21-29.
CHUNK_PAGES: tuple[int, ...] = tuple(range(42, 51))

PDF_PATH = (
    Path(__file__).resolve().parents[5]
    / "proprietary"
    / "books"
    / "Leprohon 2013 - The Great Name.pdf"
)
OUT_PATH = Path(__file__).parent / "raw" / "chunk-p42-p50-pypdf.md"

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
    "Two Ladies",
    "Golden Horus",
    "Seth name",
    "Horus",
    "Throne",
    "Birth",
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


def transcribe(pages: tuple[int, ...], pdf_path: Path, out_path: Path) -> None:
    reader = PdfReader(str(pdf_path))
    parts: list[str] = [
        "<!-- Leprohon 2013 chapter II (Early Dynastic Period), physical pp. "
        f"{pages[0]}-{pages[-1]}, deterministic pypdf+MdC transcription. -->\n\n"
    ]
    for physical_page in pages:
        page = reader.pages[physical_page - 1]  # pypdf is 0-indexed
        text = page.extract_text()
        parts.append(f"<!-- physical page {physical_page} -->\n")
        for raw_line in text.splitlines():
            parts.append(_normalize_line(raw_line) + "\n")
        parts.append("\n")
    out_path.parent.mkdir(exist_ok=True, parents=True)
    out_path.write_text("".join(parts))


if __name__ == "__main__":
    transcribe(CHUNK_PAGES, PDF_PATH, OUT_PATH)
    size = OUT_PATH.stat().st_size
    print(f"wrote {OUT_PATH} ({size} bytes)")
