r"""Porter-Moss Vol I (Theban Necropolis) — Unicode-fixup post-processor.

Runs AFTER the pypdf text-layer dump produces ``raw/chunk-*.txt`` and BEFORE
the 3-subagent extraction reads it. The Griffith Institute's publisher OCR is
deterministic but has reproducible glyph-class noise that the extraction
agents cannot resolve unanimously: three agents reading ``MAI;IIRPER`` will
disagree on whether to read it as ``Mahirper`` or ``Maihirper`` because the
``I;I`` bigram has no canonical interpretation outside the rule book each
agent half-remembers from the prompt.

This post-processor moves the Egyptian-glyph rules from "the prompt asks
agents to apply them" to "applied by code, deterministic, and visible in the
diff". After running, the agents see canonical Unicode (``Ḥ``, ``ʿ``, ``ḍ``,
``ḥ``, ``ḳ``) instead of pre-Unicode lithographic substitutes; their existing
diacritic-stripping policy then yields a unanimous ASCII form.

Three classes of fix, in fixed order:

1. Character-class substring fixes that are unambiguous regardless of
   surrounding context. ``J:I`` is the publisher's substitute for capital
   underdot ``Ḥ`` at word start (``J:Iatshepsut``); ``I;I`` is the same glyph
   in all-caps headings (``MERNEPTAI;I-SIPTAI;I``); ``l:I`` is the mid-word
   variant after the ayin glyph (``Re<-l:Iarakhti``). None of these bigrams
   occur in normal English prose in this source — verified by grep over
   ``raw/chunk-*.txt``.

2. Inline ayin (``<`` adjacent to a letter → ``ʿ``). The ``<`` character
   appears nowhere else in this source's prose (no math, no XML); it is
   reserved entirely for the Egyptological ayin. Anchored to a letter on
   one side so an angle-bracket-like character in citation noise (rare
   ``[<-rotation>``) doesn't accidentally fire.

3. Whitelisted token-exact substitutions for Egyptian transliterations whose
   trailing ``c`` is the alternate ayin rendering (the publisher OCR
   inconsistently substitutes ``c`` for ``<`` in roughly 5% of ayin
   occurrences). The whitelist covers occupant-name tokens that hit the
   reconciled output (``Smenkhkarec``, ``Menkheperrec``, ``Rec``,
   ``Takhact``); English ``c``-trailing tokens like ``Cairo``, ``Asiatic``,
   ``Canopic`` are NOT whitelisted and survive untouched.

Plus two narrower fixes:

- ``[Ist ed. N]`` / ``[rst ed. N]`` / ``[xst ed. N]`` cross-references
  (running-header digit-class noise, where ``1`` rendered as ``I``/``r``/
  ``x`` arbitrarily) → ``[1st ed. N]``. The agents disagree on the right
  reading otherwise, and there is no other ``Xst ed.`` form in this source.

- King-name-anchored Roman numerals: ``Amenophis Ill`` → ``Amenophis III``
  (and ``Il`` → ``II``, ``11`` → ``II``) when the preceding token is a
  recognized royal name. This is anchored because the ``I``↔``1``↔``l``
  confusion is bidirectional in this source — catalog numbers like
  ``5I109`` and years like ``I922`` use the SAME character class as the
  Roman numeral suffix but must NOT be rewritten. The king-name anchor is
  the only reliable signal that the trailing token is a regnal numeral.

Phase ordering matters as well as phase-internal ordering. Phase 2 (inline
ayin) anchors on a word character to its left; Phase 1's substitution product
``Ḥ``/``ḥ`` is the immediately-preceding character in some inputs (e.g.
``Re<-l:Iarakhti`` becomes ``Reʿ-Ḥ<arakhti`` mid-pass), so Phase 2's
lookbehind uses ``\w`` (Unicode word class) rather than ``[A-Za-z]`` to admit
the underdot-H. Running phases out of order would leave dangling ``<``s.

Idempotence: every rule's right-hand side does not contain the rule's left-
hand side, so re-running the post-processor on its own output is a no-op.
This is asserted by the test suite and is the reason no explicit "strip
previous annotations" pass is needed (cf. Beckerath ``postprocess.py``,
which DOES inject ``<!--`` comments and therefore needs the strip step).

Invocation:

    uv run --project pipeline python \\
        pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/postprocess.py \\
        --input raw/chunk-p89-p106.txt   # in-place by default

The chunk file is gitignored (``raw/*``); the post-processed file lives at
the same path so the 3-subagent extraction continues to read
``raw/chunk-*.txt`` without changing the agent prompt's input path.
"""

from __future__ import annotations

import argparse
import os
import re
import tempfile
from pathlib import Path

# --- Phase 1: substring fixes (context-free, safe everywhere) ---------------
# Each (src, dst) pair: ``src`` does not appear in normal English prose in
# this source (verified by ``grep`` over raw/chunk-*.txt) AND ``src`` does
# not appear inside any ``dst``, so re-running the substitution is a no-op.
#
# Order matters only when one rule's ``dst`` could be a substring of another
# rule's ``src``. None of the entries here have that property, but the list
# is kept in priority/length order anyway for readability.
_SUBSTRING_FIXES: list[tuple[str, str]] = [
    # Capital underdot Ḥ. Five publisher-OCR substitutes for the same
    # glyph; observed positions: ``J:I`` at word start (``J:Iatshepsut``),
    # ``I:I`` at word start (``I:Iatshepsut``, ``I:Iarakhti`` — same glyph,
    # different OCR run), ``I;I`` inside all-caps tokens (``MERNEPTAI;I``,
    # ``MAI;IIRPER``), ``l:I`` mid-word after a hyphen (``Re<-l:Iarakhti``),
    # ``I:J`` rare variant (3 occurrences in chunk 3: ``I:Jarakhti``,
    # ``I:Jarsiesi``, ``I:Jatl``).
    ("J:I", "Ḥ"),
    ("I:I", "Ḥ"),
    ("I;I", "Ḥ"),
    ("l:I", "Ḥ"),
    ("I:J", "Ḥ"),
    # Underdot ḍ + ḥ digraph. Single high-impact case is QV47's mother-of
    # field, ``Sit-ḍḥout``; the publisher OCR drops the underdot-D entirely
    # and renders the ḥ as ``Q.``. The exact source token ``Sit-gQ.out``
    # is the only place this bigram appears in any chunk.
    ("Sit-gQ.out", "Sit-ḍḥout"),
    # Running-header cross-reference: ``[1st ed. N]`` digit-class noise.
    # Three observed mis-renders, all unique to this bracket position.
    ("[Ist ed.", "[1st ed."),
    ("[rst ed.", "[1st ed."),
    ("[xst ed.", "[1st ed."),
]

# --- Phase 2: inline ayin ---------------------------------------------------
# ``<`` adjacent to a letter is the publisher's ayin substitute. Anchored on
# at least one alphabetic side so that a stray ``<`` in citation noise does
# not fire. Most occurrences in this source have letters on both sides
# (``Re<-J:Iarakhti``, ``Ma<et``, ``Kha<emweset``); a handful are word-final
# (``Re<.``, ``Re<,``) and the right-anchor `(?=[\W])` would still fire via
# the left anchor alone. We use ``(?<=[A-Za-z])<`` so that any ``<`` with a
# letter immediately before it is replaced; the right side is unconstrained
# because punctuation, spaces, hyphens, and following letters are all
# legitimate ayin contexts.
# Two anchors so ``<`` fires both as a word-internal/trailing ayin (`Re<`,
# `Ma<et`) AND as a word-initial ayin (`<Ahhotp`, `<Ankhef...`, `<Aqmosi`).
# Both anchors admit ASCII letters AND the Egyptological transliteration
# consonants this source uses or this postprocessor produces:
# ``Ḥ``/``ḥ`` (Phase-1 product), ``ḍ``/``Ḍ`` (Phase-1 product, plus
# possible Sit-ḍḥ shape), ``ḳ``/``Ḳ`` (chunk-text content for names like
# ``Seḳenenreʿ``). Symmetric so neither side silently misses a glyph the
# other admits. ``\w`` is rejected because it admits digits and chunk
# text contains digit-cluster noise like ``pp. 22<)-47`` where ``<`` is
# a misread digit, not an ayin — firing there would corrupt page-citation
# pages. Verified safe by ``grep -hoE '<[A-Za-z]'`` over all raw chunks:
# every word-initial hit is Egyptian transliteration (`<a`, `<A`,
# `<Ankh*`, `<Anen`, `<Aqmosi`, etc.) — no HTML/math/citation false
# positives.
_AYIN_RE = re.compile(r"(?<=[A-Za-zḤḥḍḌḳḲ])<|<(?=[A-Za-zḤḥḍḌḳḲ])")

# --- Phase 3: whitelisted token-exact substitutions -------------------------
# Tokens whose trailing ``c`` is the ayin glyph rendered as a letter ``c``
# rather than ``<``. The publisher OCR renders the ayin inconsistently; both
# forms appear in the same chunk for the same word. We restrict the ``c → ʿ``
# rewrite to a closed set of Egyptian transliteration tokens so English
# ``c``-trailing words (``Cairo``, ``Asiatic``, ``Canopic``, ``Demotic``,
# ``Hieratic``, ``Hieroglyphic``, ``Mimic``, ``Photographic``, ``Dec``,
# ``Cmc``, ``Hic``, ``Fac``, ``Passalac``) survive untouched.
#
# The match is anchored with ``\b`` boundaries so ``Recto`` (English "recto",
# right-hand page) and ``Recommended`` etc. would not match ``Rec`` — they
# don't end at the ``c``.
_WORD_FIXES: dict[str, str] = {
    "Smenkhkarec": "Smenkhkareʿ",
    "Menkheperrec": "Menkheperreʿ",
    "Rec": "Reʿ",
    "Takhact": "Takhaʿt",
}
_WORD_FIXES_RE = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in _WORD_FIXES) + r")\b",
    re.IGNORECASE,
)
# Lookup is case-insensitive on the matched token; the dict keys are stored
# in their canonical Title-Case form, but lower-folding both sides handles
# any all-caps variant a future chunk may surface (e.g. ``SMENKHKAREC`` in
# a PM section heading) and any lower-case variant in body prose.
_WORD_FIXES_LOWER: dict[str, str] = {k.lower(): v for k, v in _WORD_FIXES.items()}

# --- Phase 4: king-name-anchored Roman numerals -----------------------------
# The Griffith Institute text layer confuses ``I``, ``1``, and ``l`` in both
# directions: catalog numbers like ``51109`` render as ``5I109``; years like
# ``1922`` render as ``I922``; conversely Roman ``III`` after a king name
# renders as ``Ill`` (cap-I + lowercase-l + lowercase-l) and ``II`` renders
# as ``Il`` or ``11``. A general-purpose ``I→1`` or ``Il→II`` rewrite would
# corrupt catalog numbers and years; we therefore restrict the rewrite to
# the position immediately after a recognized royal name, where the trailing
# token is necessarily a regnal numeral.
#
# King-name list: roots that take Roman regnal numerals in PM headwords or
# bibliographic ribbon. Order does not matter (regex alternation is greedy
# but the list does not contain prefixes of each other).
_KING_NAMES: tuple[str, ...] = (
    "Amenophis",
    "Tuthmosis",
    "Ramesses",
    "Sethos",
    "Merneptah",
    "Mentuhotp",
    "Senwosret",
    "Sesostris",
    "Psammetichus",
    "Nectanebo",
    "Ptolemy",
)
# `re.IGNORECASE` covers both Title-Case body prose (`Amenophis Ill`) and
# the all-caps PM headword form (`22. AMENOPHIS I Il`); the multi-token
# `I\s+Il` alternative captures the headword shape where PM typesets the
# Roman three as `I` (a separate capital) followed by `Il` (cap-I + l).
_ROMAN_FIX_RE = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in _KING_NAMES)
    + r")(\s+)(I\s+Il|Ill|III|Il|II|11)\b",
    re.IGNORECASE,
)
# Lookup keyed on the lowercase form of the captured numeral. ``re.IGNORECASE``
# matches the king-name AND the numeral case-insensitively, so the captured
# group can be ``Ill`` or ``ILL`` or ``ill``; lower-fold + whitespace-collapse
# normalises both axes before the dict lookup. The map's RHS is the canonical
# Roman III/II spelling regardless of input case.
_ROMAN_NORMALIZE: dict[str, str] = {
    "i il": "III",
    "ill": "III",
    "iii": "III",
    "il": "II",
    "ii": "II",
    "11": "II",
}


def _roman_sub(m: "re.Match[str]") -> str:
    # Lower-fold + whitespace-collapse so ``I  Il`` and ``i il`` both map.
    key = " ".join(m.group(3).lower().split())
    return f"{m.group(1)}{m.group(2)}{_ROMAN_NORMALIZE[key]}"


def process_chunk(text: str) -> str:
    """Apply Porter-Moss text-layer fixups in fixed order.

    Pure function: same input always yields same output. Idempotent: running
    twice is the same as running once (each rule's RHS does not contain its
    own LHS, so a second pass finds nothing to replace).
    """
    out = text
    # Phase 1: substring fixes
    for src, dst in _SUBSTRING_FIXES:
        out = out.replace(src, dst)
    # Phase 2: inline ayin
    out = _AYIN_RE.sub("ʿ", out)
    # Phase 3: whitelisted token-exact rewrites (post-Phase-1-and-2 forms).
    # Single combined-regex pass; one scan over the text, mapping each match
    # to its canonical form via the dict.
    def _word_sub(m: "re.Match[str]") -> str:
        # Preserve the input's case style — an all-caps heading token
        # (`SMENKHKAREC`) stays all-caps in the substituted form
        # (`SMENKHKAREʿ`); a Title-Case body-prose token stays Title-
        # Case (`Smenkhkareʿ`). Forcing Title-Case on every match would
        # silently mutate source heading casing, which the postprocessor
        # is not authorised to do.
        word = m.group(1)
        fixed = _WORD_FIXES_LOWER[word.lower()]
        return fixed.upper() if word.isupper() else fixed
    out = _WORD_FIXES_RE.sub(_word_sub, out)
    # Phase 4: king-name-anchored Roman numerals
    out = _ROMAN_FIX_RE.sub(_roman_sub, out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to a raw chunk file (e.g. raw/chunk-p89-p106.txt).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path. Defaults to overwriting --input in place.",
    )
    args = parser.parse_args()
    output_path = (
        args.output if args.output is not None else args.input
    ).resolve()
    text = args.input.read_text(encoding="utf-8")
    fixed = process_chunk(text)
    # Atomic write: stage to a temp file in the same directory, then rename.
    # If the script is interrupted mid-write the destination still holds
    # either the previous content or the new content — never a partial.
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(fixed)
        os.replace(tmp_path, output_path)
        tmp_path = None
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
    byte_size = len(fixed.encode("utf-8"))
    print(f"wrote {output_path} ({byte_size} bytes)")


if __name__ == "__main__":
    main()
