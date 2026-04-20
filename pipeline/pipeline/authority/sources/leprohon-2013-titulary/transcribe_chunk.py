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
    # Chunk 5 (this PR): chapter V Middle Kingdom continuation — the late
    # MK Dynasty 13 ephemeral line. Printed 60-71, offset +21, physical
    # 81-92. Physical p. 81 is shared with chunk 4 (Queen Sobekneferu
    # tail of Dyn 12 is on the same page as the Dyn 13 opening header);
    # the prompt tells agents to START at the `Dynasty 13` header and
    # skip the Sobekneferu row already extracted in chunk 4. Expected
    # ~37 kings making this the densest-king-count chunk in the book;
    # most are fragmentary (`////` wildcards, Ramesside-list-only) and
    # most name-types-per-king are much sparser than MK proper (Throne
    # name + Birth name is typical; full fivefold titulary is rare).
    "dyn13": (81, 92, "V. Middle Kingdom (Dyn 13 ephemeral line)"),
    # Chunk 6 (this PR): chapter V Middle Kingdom tail — the Ramesside-
    # added sub-dynasties Dyn 13a + Dyn 14 + Dyn 14a. Printed 72-80,
    # offset +21, physical 93-101. Dyn 13a is a small Ramesside-list
    # group (7 kings) not attested contemporarily; Dyn 14 (40 rows — 38
    # numbered king-entries with gaps at 20-21, 35-42 plus 2 multi-slot
    # "N names lost" stubs at slots 46-48 and 52-56) and Dyn 14a (6 rows,
    # Semitic-origin kings whose position in the dynasty is uncertain)
    # are additional late-MK material Leprohon places at the end of
    # chapter V before the chapter VI SIP boundary. 53 total rows.
    "dyn13a-14": (93, 101, "V. Middle Kingdom (Dyn 13a + 14 + 14a tail)"),
    # Chunk 7 (this PR): chapter VI Second Intermediate Period — Dyn 15
    # (Hyksos), Dyn 16, Dyn 17 (Theban). Printed 81-92, offset +21,
    # physical 102-113. This is where Leprohon's chapter VI actually
    # starts (not at the Dyn 13 opening as the pre-chunk-4 README had
    # wrong). The Hyksos kings have partial titularies drawn from
    # scarabs + royal-statuary inscriptions; Dyn 17 is Theban and
    # includes Senakhtenre, Seqenenre, Kamose — the immediate
    # predecessors of Ahmose I.
    "sip": (102, 113, "VI. Second Intermediate Period"),
}
DEFAULT_CHUNK = "sip"

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
# NOTE: earlier revisions of this module used a monolithic `NAME_ROW_RE`
# that captured transliteration and gloss in a single match. That
# approach failed on transliterations with embedded parens (filiation
# markers like `(sꜣ)`, morphological markers like `(y)` / `(.w)`) because
# the lazy-match boundary `\s+\(.*$` would stop at the FIRST space-paren,
# mis-identifying the gloss boundary. `_normalize_line` now uses a
# smaller `prefix_match` for the label + colon, and a dedicated
# reverse-scanning `_find_gloss_open_paren` for the gloss boundary.


def mdc_to_unicode(text: str) -> str:
    """Apply MdC → Egyptological Unicode on a single transliteration token-span.

    Operates character-by-character on the MdC-substitution subset. Non-MdC
    characters (digits, punctuation, already-Unicode diacritics, parenthesised
    optional glyphs, angle-bracketed partial readings) pass through unchanged.
    """
    return "".join(MDC_MAP.get(ch, ch) for ch in text)


def _find_gloss_open_paren(after_colon: str) -> int | None:
    """Return the character index of the opening `(` of the anglicised gloss.

    Transliterations can contain embedded parentheticals like `(sꜣ)` for
    filiation, `(y)` / `(.w)` / `(w)` for morphological optional glyphs.
    The anglicised gloss is always the LAST `(...)` group that ends
    immediately before the `, <TRANSLATION>` boundary (comma + uppercase
    letter starting the English translation) or end-of-line.

    Algorithm: scan from right to left. Find the `)` that precedes `, [A-Z]`
    or end-of-line; then walk back to its matching `(` accounting for
    balanced nesting (the gloss itself can contain nested parens like
    `(imeny (sa) qemau)`).

    Returns None if no balanced paren group is found before the translation
    boundary — caller falls back to no normalisation.
    """
    # Trim trailing footnote digits and whitespace — they sit after the gloss
    # but shouldn't affect the scan.
    stripped = after_colon.rstrip()
    # Preferred rule: the gloss ends at the LAST `), ` (close-paren + comma-
    # space) in the line — that's the translit → gloss → translation
    # boundary. Translations can themselves contain parens (e.g.
    # `, (Possessor of?) The kas...`), so we can't just use "last close
    # paren". Lines like `(gloss), translation (?)<footnote>` have TWO
    # `)` characters: one that terminates the gloss (before `, `) and
    # one that terminates the `(?)` uncertainty marker inside the
    # translation. Picking the LAST `)` would wrongly absorb the
    # translation into the transliteration.
    gloss_end = None
    for i in range(len(stripped) - 1, -1, -1):
        if stripped[i] != ")":
            continue
        if stripped[i + 1:].startswith(", "):
            gloss_end = i
            break
    # Fallback: if no `), ` separator exists, the gloss runs to end-of-line
    # (no translation, e.g. `Label: TRANSLIT (GLOSS)`). Use the LAST `)`
    # followed only by optional footnote digits.
    if gloss_end is None:
        for i in range(len(stripped) - 1, -1, -1):
            if stripped[i] != ")":
                continue
            if re.match(r"^\d*$", stripped[i + 1:]):
                gloss_end = i
                break
    if gloss_end is None:
        return None
    # Walk backwards to find the matching `(`, balancing nested parens.
    depth = 1
    for i in range(gloss_end - 1, -1, -1):
        if stripped[i] == ")":
            depth += 1
        elif stripped[i] == "(":
            depth -= 1
            if depth == 0:
                # The `(` must be preceded by whitespace (transliteration
                # embedded parens are glued to the previous character).
                if i == 0 or stripped[i - 1].isspace():
                    return i
                return None
    return None


def _normalize_line(line: str) -> str:
    """Apply MdC mapping to the transliteration span of a Leprohon name row.

    Lines that are not name rows (prose paragraphs, headwords, footnotes,
    section headers, empty lines) pass through unchanged — the MdC substitutions
    would corrupt regular English text (`a` → `ꜥ` would turn "and" into "ꜥnd").

    Handles embedded parentheticals in transliterations (e.g. `imny (sA)
    qmAw (imeny (sa) qemau)`) by scanning backward from the end to find the
    gloss's opening `(`, accounting for balanced nested parens inside the
    gloss itself.
    """
    # Match just the label + colon + whitespace prefix; everything after
    # that is handled by `_find_gloss_open_paren` which accounts for
    # embedded-paren transliterations.
    prefix_match = re.match(
        r"^((?:"
        + "|".join(re.escape(lbl) for lbl in NAME_LABELS)
        + r")(?:\s+names?)?(?:\s\d+)?):(\s*)",
        line,
    )
    if prefix_match is None:
        return line
    prefix_end = prefix_match.end()
    after_colon = line[prefix_end:]
    gloss_start_rel = _find_gloss_open_paren(after_colon)
    if gloss_start_rel is None:
        # Could not locate a gloss — either it's `none attested` (no gloss
        # expected) or unusual formatting. Return line unchanged to avoid
        # mis-normalising non-translit text.
        return line
    # Transliteration runs from start-of-after-colon to the gloss opener
    # (exclusive of the space separator).
    translit_end_rel = gloss_start_rel
    # Strip trailing whitespace from translit span.
    translit = after_colon[:translit_end_rel].rstrip()
    rest = after_colon[len(translit):]
    return f"{line[:prefix_end]}{mdc_to_unicode(translit)}{rest}"


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
