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
    # Chunk 8 (this PR): chapter VII New Kingdom — Dyn 18. Printed 93-107,
    # offset +21, physical 114-128. The densest per-king chunk in the
    # book — Thutmose III alone has dozens of attested prenomen / epithet
    # variants, Akhenaten has the NK inline-stage convention (10a / 10b).
    # Physical p. 128 is shared with chunk 9 (Ay's Birth name spills
    # over from p. 127 to p. 128, AND Horemheb starts Dyn 19 mid-page);
    # the prompt tells agents to STOP at the `Dynasty 19` header so
    # only Ay's tail is consumed from p. 128.
    "dyn18": (114, 128, "VII. New Kingdom (Dyn 18)"),
    # Chunk 9 (this PR): chapter VII New Kingdom — Dyn 19 + Horemheb
    # scope-recovery. Printed 107-125, offset +21, physical 128-146.
    # Physical p. 128 contains Ay's tail (already extracted in chunk 8)
    # AND Horemheb (Leprohon's Dyn 18 entry 15, missed by chunk 8 — this
    # chunk recovers him with `dynasty_label: "Dynasty 18"`) AND the
    # `Dynasty 19` header opening Ramses I's section. Physical p. 146
    # contains the END of Tausret (Dyn 19 entry 8) AND the `Dynasty 20`
    # header. The prompt tells agents to extract Horemheb + all 8 Dyn 19
    # entries (Ramses I, Sety I, Ramses II, Merenptah/Merneptah, Sety II,
    # Amenmesse, Siptah, Tausret) and STOP at the Dyn 20 header.
    "dyn19": (128, 146, "VII. New Kingdom (Dyn 19)"),
    # Chunk 10 (this PR): chapter VII New Kingdom — Dyn 20. Printed 125-135,
    # offset +21, physical 146-156. Physical p. 146 is shared with chunk 9
    # (Tausret tail at top, then Dyn 20 opening prose). The prompt tells
    # agents to START at the `Dynasty 20` header — Tausret is OUT OF
    # SCOPE for this chunk (already extracted in chunk 9). Includes
    # Sethnakht (Dyn 20 entry 1) + Ramesses III through Ramesses XI.
    "dyn20": (146, 156, "VII. New Kingdom (Dyn 20)"),
    # Chunk 11 (this PR): chapter VIII Third Intermediate Period — Dyn 21
    # + 21a + 22 + 22a (Tanite + HPA Theban parallel + Bubastite Sheshonqs
    # main line + collateral). Printed 136-152, offset +21, physical
    # 157-173. Dyn 22 alone has 28 entries (the long Sheshonq/Osorkon/
    # Takeloth line); chunk 11 totals ~49 entries. The TIP chapter VIII
    # was originally scoped as a single chunk in the README but split
    # into chunks 11 (this) and 12 (Dyn 23+23a+24+25, ~41 entries) to
    # keep agent context loads manageable.
    "tip-early": (157, 173, "VIII. TIP early (Dyn 21 + 21a + 22 + 22a)"),
    # Chunk 12 (this PR): chapter VIII Third Intermediate Period — Dyn 23
    # + 23a + 24 + 25 (Tanite/Theban Dyn 23 split + Saite Dyn 24 +
    # Nubian Dyn 25). Printed 153-163, offset +21, physical 174-184.
    # Dyn 25 is the Nubian/Kushite line (Piye, Shabaka, Shabataka,
    # Taharqa, Tantamani) — culturally significant though Leprohon
    # treats them at typical TIP density (mostly Throne + Birth).
    "tip-late": (174, 184, "VIII. TIP late (Dyn 23 + 23a + 24 + 25)"),
    # Chunk 13 (this PR): chapter IX Late Period — Dyn 26 (Saite) +
    # Dyn 27 (1st Persian) + Dyn 28 + Dyn 29 + Dyn 30 + Dyn 31 (2nd
    # Persian). Printed 164-174, offset +21, physical 185-195.
    # Includes the Saite renaissance kings (Psamtik I-III, Necho I-II,
    # Apries, Amasis), the Persian satrapal "kings" (Cambyses, Darius,
    # Xerxes), and the brief native Dyn 28-30 lines (Amyrtaios,
    # Nepherites, Hakor, Nectanebo I/II).
    "late-period": (185, 195, "IX. Late Period"),
    # Chunk 14 (this PR): chapter X Macedonian and Ptolemaic Dynasties.
    # Printed 175-188, offset +21, physical 196-209. The Macedonian
    # Dynasty (Alexander the Great, Philip Arrhidaeus, Alexander IV) is
    # 3 entries; the Ptolemaic Dynasty runs 17 entries (Ptolemy I Soter
    # through Ptolemy XV Caesarion, with Berenike inserted as entry 12
    # between Ptolemy XI and Ptolemy XII). Total ~20 rows. Per the
    # README schema convention, `dynasty_number: 32` for Macedonian and
    # `dynasty_number: 33` for Ptolemaic (pharaoh.se itself uses null
    # for both — the README's "consistent with pharaoh.se" rationale
    # for `33` is a Leprohon-local extrapolation, not a literal
    # alignment). Headwords in the pypdf text layer are letter-spaced
    # (`a l EXan DEr  t HE g r Eat`, `Ptol Emy  i s ot Er`) — agents
    # must collapse intra-word whitespace and title-case before
    # emitting `display_name`.
    "macedonian-ptolemaic": (196, 209, "X. Macedonian and Ptolemaic Dynasties"),
}
DEFAULT_CHUNK = "macedonian-ptolemaic"

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


# Trailing EBSCO watermark — three lines that appear at the bottom of every
# PDF page. Not transcribed content; stripped per the policy in transcribe.md.
EBSCO_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^EBSCO Publishing\s*:\s*eBook"),
    re.compile(r"^AN:\s*\d+\s*;"),
    re.compile(r"^Account:\s*s\d+"),
)

# Per-page running headers. Examples encountered in chunk 7:
#   `81`                                  bare page number (chapter opener)
#   `VI`                                  bare roman chapter marker
#   `82 THE GR EAT NAME`                  even-page header
#   ` SECO ND INTERMEDIATE PERIOD  83`    odd-page header
# The chapter-opening smallcap title (e.g. `s Econ D i nt Erm EDiat E PErio D`)
# is NOT a running header — it's content the agents need to identify the chapter
# context, so it stays. Running-header stripping only applies to the leading
# lines of a page (top of page is where pypdf places these).
_RUNNING_HEADER_RE = re.compile(
    r"^\s*("
    r"\d{1,3}"  # bare page number
    r"|[IVX]{1,4}"  # bare roman numeral chapter marker
    r"|\d{1,3}\s+(?:THE\s+)?[A-Z][A-Z\s]{2,}"  # even-page: page-num + caps
    r"|[A-Z][A-Z\s]{2,}\s+\d{1,3}"  # odd-page: caps + page-num
    r")\s*$"
)

# Footnote-number detection. Footnote numbers in Leprohon are 1-3 digits
# (chapter VII is the largest chapter at 132 footnotes). Capping at 3 digits
# excludes 4-digit years like `1985. The reading Renefer/Reneferef...` which
# appear inside footnote bodies and would otherwise be mis-detected as a
# footnote start.
_FOOTNOTE_START_RE = re.compile(r"^(\d{1,3})\.\s")
_FOOTNOTE_NUM_ONLY_RE = re.compile(r"^(\d{1,3})\s*$")
# pypdf occasionally splits a footnote's `N.` from its body. Two observed
# shapes (handled by `_merge_split_footnote_numbers`):
#   `34\n. Turi\nn 11,9 (= KRI II, 843:1); von Beckerath 1999, 128–29.`
#   `56.\n The na\nme may simply be...`
_NUM_PERIOD_ONLY_RE = re.compile(r"^(\d{1,3})\.\s*$")
_PERIOD_CONTINUATION_RE = re.compile(r"^\.\s")
_YEAR_RE = re.compile(r"\b(?:1[5-9]|20)\d{2}\b")
# Tokens that strongly imply a footnote body (vs. a king-headword smallcap
# name). Includes scholarly-citation abbreviations common in Egyptology
# (KRI = Kitchen, Ramesside Inscriptions; LÄ; Wb; PM; ANET; Urk.; LD =
# Lepsius Denkmäler) and the most-cited authors in Leprohon's references.
_PROSE_TOKEN_RE = re.compile(
    r"\b(see|cf\.|ibid|von\s+Beckerath|et\s+al|Schneider|Ryholt|Kitchen|Gauthier"
    r"|Redford|Bietak|Davies|Turin|Waddell|Aufrère|Dobrev|Spalinger"
    r"|KRI|LÄ|Wb|PM|ANET|Urk|LD)\b",
    re.IGNORECASE,
)


def _is_ebsco(line: str) -> bool:
    return any(p.match(line) for p in EBSCO_PATTERNS)


def _is_running_header(line: str) -> bool:
    """Match the three running-header line shapes used in Leprohon 2013."""
    return bool(_RUNNING_HEADER_RE.match(line))


def _merge_split_footnote_numbers(lines: list[str]) -> list[str]:
    """Pre-pass: merge split-number footnote starts into `\\d+. <body>`.

    pypdf occasionally emits a footnote whose number is broken away from its
    body by a soft line break. Two shapes seen in real chunks:

      Shape A — number alone, period+body on next line:
        `34`
        `. Turi`
        `n 11,9 (= KRI II, 843:1); von Beckerath 1999, 128–29.`

      Shape B — number+period alone, body on next line:
        `56.`
        ` The na`
        `me may simply be...`

      Shape C — 3-digit footnote number split across the line break:
        `12`
        `2. Ibid`
        `., 106–7.`
        →  `122. Ibid., 106-7.`  (body merged later by the block detector)

    Reconstruct all three into `\\d+. <body>` so the downstream footnote-
    block detector sees a normal start pattern. The 3-digit cap on the
    matching regexes prevents 4-digit years like `1985.` from being
    treated as footnote-number prefixes.
    """
    merged: list[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        # Shape A: `34` + `. Turi`.
        if (
            i + 1 < len(lines)
            and _FOOTNOTE_NUM_ONLY_RE.match(cur)
            and _PERIOD_CONTINUATION_RE.match(lines[i + 1])
        ):
            num = _FOOTNOTE_NUM_ONLY_RE.match(cur).group(1)
            after_dot = lines[i + 1][1:].lstrip()
            merged.append(f"{num}. {after_dot}")
            i += 2
            continue
        # Shape B: `56.` + ` The na`. The continuation line must start with
        # whitespace or a letter (not another `\d+\.` footnote start).
        m_b = _NUM_PERIOD_ONLY_RE.match(cur)
        if (
            m_b
            and i + 1 < len(lines)
            and lines[i + 1]
            and not _FOOTNOTE_START_RE.match(lines[i + 1])
            and not _FOOTNOTE_NUM_ONLY_RE.match(lines[i + 1])
        ):
            merged.append(f"{m_b.group(1)}. {lines[i + 1].lstrip()}")
            i += 2
            continue
        # Shape C: `12` + `2. Ibid` → `122. Ibid` (3-digit footnote-number
        # split across the line break). Restricted to combined numbers in
        # 100-250 to exclude (a) body-text footnote anchors `42\n1. headword`
        # — `421` exceeds the range — and (b) anything below 100 where the
        # digit-only line is more plausibly a standalone anchor.
        m_c_prefix = _FOOTNOTE_NUM_ONLY_RE.match(cur)
        if m_c_prefix and i + 1 < len(lines):
            m_c_next = _FOOTNOTE_START_RE.match(lines[i + 1])
            if m_c_next:
                combined_str = f"{m_c_prefix.group(1)}{m_c_next.group(1)}"
                combined_num = int(combined_str)
                if 100 <= combined_num <= 250:
                    rest = lines[i + 1][m_c_next.end():]
                    merged.append(f"{combined_num}. {rest}")
                    i += 2
                    continue
        merged.append(cur)
        i += 1
    return merged


def _looks_like_footnote_body(text: str) -> bool:
    """Heuristic: does this look like a footnote body (prose) vs a king headword?

    Footnote bodies are prose: typically > 20 chars, contain a year, "see" /
    "cf." / "ibid", or a recognizable scholarly author. King headwords are
    smallcap-rendered names: short, with the spaced-mixed-case typography
    pattern. The discriminator protects pages that have only headwords (no
    footnotes) from being misidentified as all-footnote.
    """
    if len(text) > 60:
        return True
    if _YEAR_RE.search(text):
        return True
    if _PROSE_TOKEN_RE.search(text):
        return True
    return False


def _split_page(
    lines: list[str],
) -> tuple[list[str], list[tuple[int, str]]]:
    """Split a page into (body_lines, [(footnote_num, footnote_body)]).

    1. Strip trailing EBSCO watermark.
    2. Strip leading running-header lines.
    3. Detect the trailing footnote block: longest sequence of `\\d+\\. `
       starts whose numbers form a contiguous, monotonically increasing run
       (decreasing-by-1 when walked backward from the last footnote start).
       The detection trusts the increasing-by-1 invariant of Leprohon's
       per-chapter footnote numbering — king-headword `\\d+\\. ` lines that
       appear earlier on the same page break the sequence and are correctly
       excluded from the block.
    4. Apply a prose safeguard: if the candidate block's first body fails
       `_looks_like_footnote_body`, the page has no footnotes (return body
       only).
    5. Merge each footnote's multi-line body into a single string.
    """
    lines = _merge_split_footnote_numbers(lines)

    # Strip trailing EBSCO watermark + any trailing blank lines before/after it.
    while lines and (not lines[-1].strip() or _is_ebsco(lines[-1])):
        lines.pop()

    # Strip leading running-header lines (only at top-of-page; never elsewhere
    # because a bare-digit line in the body is a footnote anchor).
    while lines and (not lines[0].strip() or _is_running_header(lines[0])):
        lines.pop(0)

    if not lines:
        return [], []

    # Locate every `\d+. ` start across the page. Exclude matches where the
    # PREVIOUS line ends with an en-dash or em-dash — those signal a wrapped
    # page-line citation (e.g. `KRI IV, 31:1–\n13. ` where `13.` is the
    # citation tail of fn 124, not the start of fn 13). The plain hyphen `-`
    # is intentionally NOT in this exclusion set: `bet-\nter` style word-wrap
    # hyphens at line ends are common in body prose and unrelated to
    # citation continuations.
    starts: list[tuple[int, int]] = []
    for i, line in enumerate(lines):
        m = _FOOTNOTE_START_RE.match(line)
        if not m:
            continue
        if i > 0 and lines[i - 1].rstrip().endswith(("–", "—")):
            continue
        starts.append((i, int(m.group(1))))

    if not starts:
        return lines, []

    # Walk backwards from the last `\d+. ` start, accumulating the longest
    # contiguous block of decrementing-by-1 numbers.
    block: list[tuple[int, int]] = [starts[-1]]
    expected = starts[-1][1] - 1
    for idx, num in reversed(starts[:-1]):
        if num == expected:
            block.insert(0, (idx, num))
            expected -= 1
        else:
            break

    # Merge each candidate footnote body, then apply a majority prose
    # safeguard: at least half of the merged candidates must look like
    # prose (carry an author/year/see-cf./Kitchen-citation token). This
    # protects pages of only king-headwords (smallcap names with no
    # scholarly tokens) from being misidentified as footnotes, while
    # tolerating a single short citation like `KRI II, 842:9–843:6.`
    # inside a real footnote block.
    fn_start_line = block[0][0]
    candidate: list[tuple[int, str]] = []
    for i, (start_idx, num) in enumerate(block):
        end_idx = block[i + 1][0] if i + 1 < len(block) else len(lines)
        first = lines[start_idx]
        prefix = f"{num}. "
        first_body = first[len(prefix):] if first.startswith(prefix) else first
        chunks = [first_body] + lines[start_idx + 1 : end_idx]
        merged = re.sub(r"\s+", " ", "".join(chunks)).strip()
        candidate.append((num, merged))

    # At-least-one prose match is the safeguard. King-headword bodies are
    # smallcap names (`s Em QEn`, `n am E lost`) — no year, no scholarly
    # author/abbreviation token, no `see`/`cf.`/`ibid` — so a pure-headword
    # block reliably has zero prose matches and is rejected. Real footnote
    # blocks reliably have at least one entry with a year or citation token,
    # even when individual footnotes are short (`Lit. "possessor."`,
    # `Or "crowns."`).
    prose_count = sum(
        1 for _, body_text in candidate if _looks_like_footnote_body(body_text)
    )
    if prose_count == 0:
        return lines, []

    body = lines[:fn_start_line]
    return body, candidate


def _annotate_anchors(body: list[str], known_fns: set[int]) -> list[str]:
    """Wrap inline footnote anchors in body text as `<sup data-fn="N">N</sup>`.

    Three positional patterns are handled:

    1. Standalone-digit line `27` where `27` is in `known_fns` (pypdf
       sometimes places a body-text superscript on its own line).
    2. Line ending in `\\d+` glued to a non-digit, non-en/em-dash char
       (e.g. `gods26`, `Re30`, `wAst).17`). The non-en-dash exclusion guards
       against year ranges like `1999, 116–17`. The non-digit exclusion
       guards against multi-digit page numbers — but NB: footnote numbers
       are themselves multi-digit in late chunks.
    3. Line of shape `<digit>+ <lowercase-letter-prose>` where the digit
       starts a continuation of the previous body line's sentence (the
       superscript was placed at the wrap-line start by pypdf).
    """
    out: list[str] = []
    for line in body:
        # Case 1: standalone digit line.
        stripped = line.strip()
        if stripped.isdigit() and int(stripped) in known_fns:
            out.append(f'<sup data-fn="{int(stripped)}">{int(stripped)}</sup>')
            continue
        # Case 3: digit+space+sentence-continuation (anchor at line start +
        # rest of wrapped sentence). Discriminated from king-headwords like
        # `2. a PEr -anati 6` by requiring no `.` after the digit. Allows
        # both lowercase mid-word continuation (`asily accessible`) and
        # uppercase sentence start (`In the south, the ruler...`).
        m = re.match(r"^(\d+)\s+(?!\.)([A-Za-z].*)$", line)
        if m and int(m.group(1)) in known_fns:
            num = int(m.group(1))
            out.append(f'<sup data-fn="{num}">{num}</sup> {m.group(2)}')
            continue
        # Case 2: end-of-line digit run preceded by non-digit, non-dash.
        m2 = re.search(r"(?<=[^\d–—\-])(\d+)\s*$", line)
        if m2 and int(m2.group(1)) in known_fns:
            num = int(m2.group(1))
            head = line[: m2.start(1)]
            tail = line[m2.end(1) :]
            line = f'{head}<sup data-fn="{num}">{num}</sup>{tail}'
            # fall through to case 4 (the same line may also have a mid-line
            # anchor before the end-of-line one)
        # Case 4: mid-line digit run preceded by sentence-end punctuation
        # (`. ` or `, `) and followed by a space + capitalised word. This
        # catches inline footnote anchors that pypdf preserved within a
        # paragraph, like `Lands. 16 King ...` or `today, 14 Ryholt ...`.
        # Excluding the `Dynasty 16` and `(1663–1555 b .c .E.)` patterns by
        # requiring punctuation+space context.
        def _replace_mid(m: re.Match[str]) -> str:
            num = int(m.group("num"))
            if num not in known_fns:
                return m.group(0)
            return f'{m.group("pre")}<sup data-fn="{num}">{num}</sup>{m.group("post")}'

        line = re.sub(
            r"(?P<pre>[.,;]\s)(?P<num>\d+)(?P<post>\s+[A-Z])",
            _replace_mid,
            line,
        )
        out.append(line)
    return out


def _process_page(
    physical_page: int, raw_lines: list[str]
) -> str:
    """Apply page-level processing: strip headers/EBSCO, merge footnotes,
    annotate inline footnote anchors, emit a structured block.
    """
    # MdC normalisation is line-level and unchanged from the original method.
    normalised = [_normalize_line(ln) for ln in raw_lines]
    body, footnotes = _split_page(normalised)
    known_fns = {num for num, _ in footnotes}
    annotated_body = _annotate_anchors(body, known_fns)
    parts: list[str] = [f"<!-- physical page {physical_page} -->\n"]
    for ln in annotated_body:
        parts.append(ln + "\n")
    if footnotes:
        parts.append("<!-- footnotes -->\n")
        for num, body_text in footnotes:
            parts.append(f'<fn id="{num}">{body_text}</fn>\n')
    parts.append("\n")
    return "".join(parts)


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
        parts.append(_process_page(physical_page, text.splitlines()))
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
