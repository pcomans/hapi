"""Deterministic cross-convention name normalization.

ADR-020 §6 fixes as *policy* that prenomen/throne-name corroboration must run on a
DETERMINISTICALLY NORMALIZED form via a "committed cross-convention normalization
table" — otherwise the promoted structured signal silently inherits the very
surface-string problem (ADR-009) it exists to escape. The committed sources spell one
throne name ``Chnem-ib-rê`` (Beckerath, German transcription) vs ``khnum ib ra``
(Leprohon, anglicised) vs ``ẖnm-ib-rꜥ`` (Egyptological transliteration); all three must
collapse to one key or a true match is missed.

This module is that table. It is intentionally small, explicit, and committed so the
normalization is reproducible and auditable — never model-guessed. THREE normalization
paths are produced per name and ALL are kept, so a record's key-set is the union:

* ``translit_key`` — from an Egyptological transliteration (glyphs → ASCII, diacritics
  stripped). Consonantal-skeleton oriented (``nb mꜣꜥt rꜥ`` → ``nbmaatra``).
* ``phon_key`` — from a vowelled/anglicised rendering, with a canonical-element table
  applied so cross-convention spellings of the same element collapse
  (``Neb-maat-rê`` → ``nbmaatra``; ``re``/``ra``/``rê`` → ``ra``; ``neb`` → ``nb``).
* consonantal *skeleton* (opt-in, ``skeleton=True``) — the ASCII form with plain vowels
  dropped, so the epenthetic-vowel divergence that no element table can reach collapses:
  German ``Chnem`` / anglicised ``khnum`` / consonantal ``ẖnm`` all → ``khnmbr``. This
  path is deliberately lossy and *recall*-oriented — it is enabled only for the throne-
  name / Horus-name corroborators (never the loose name blocker), and precision is
  enforced downstream by the committed homonym list + the reviewer's escalate-on-doubt.

Two name forms corroborate iff their key-sets intersect (set-valued, per ADR-020).

German (Beckerath 1997) is the one non-anglicised, non-transliterated source: it writes
digraphs (``ch``=ḫ/ẖ, ``sch``=š, ``dsch``/``tsch``=ḏ/ṯ) that must be folded to the ASCII
skeleton BEFORE the transliteration glyph pass, or the entire German tradition silently
fails to match (and, worse, evades the homonym guard: ``Men-cheper-Rê`` would not meet
``menkheperra``). ``j`` is intentionally NOT rewritten: German uses it for the semivowel
but anglicised sources use it in the ``dj``/``tj`` digraphs, so a blanket rule would
break more than it fixes.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# German transcription digraphs → ASCII skeleton (Beckerath 1997). Ordered longest-first
# so ``dsch``/``tsch`` win before ``sch``, and ``sch`` before ``ch``. Applied to the
# lowercased string BEFORE the transliteration glyph pass and diacritic stripping.
_GERMAN_DIGRAPHS: list[tuple[str, str]] = [
    ("dsch", "dj"),
    ("tsch", "tj"),
    ("sch", "sh"),
    ("ch", "kh"),
]

# Egyptological transliteration glyphs → ASCII skeleton. Applied before diacritic
# stripping so multi-glyph mappings win. Deliberately lossy toward a consonantal core.
_GLYPH_MAP: list[tuple[str, str]] = [
    ("ꜣ", "a"),
    ("Ꜣ", "a"),  # aleph
    ("ꜥ", "a"),
    ("Ꜥ", "a"),  # ayin
    ("ꜧ", "h"),
    ("Ꜧ", "h"),
    ("ḥ", "h"),
    ("Ḥ", "h"),
    ("ḫ", "kh"),
    ("Ḫ", "kh"),
    ("ẖ", "kh"),
    ("š", "sh"),
    ("Š", "sh"),
    ("ṯ", "tj"),
    ("Ṯ", "tj"),
    ("č", "tj"),
    ("ḏ", "dj"),
    ("Ḏ", "dj"),
    ("ḳ", "q"),
    ("Ḳ", "q"),
    ("ṱ", "t"),
    ("ṭ", "t"),
    ("Ṭ", "t"),
    ("ś", "s"),
    ("Ś", "s"),
    ("ꞽ", "i"),
    ("Ꞽ", "i"),
]

# Canonical-element table for vowelled/anglicised forms. Whole-token substitutions
# applied after tokenization. Each maps a set of attested cross-convention spellings of
# one Egyptian element to a single canonical token. Extend deliberately, with a source
# in mind — this is committed vocabulary, not a heuristic.
_ELEMENT_CANON: dict[str, str] = {
    # The sun-god Re/Ra — the single most common cross-convention divergence.
    "re": "ra",
    "rê": "ra",
    "ra": "ra",
    "rah": "ra",
    # Amun / Amen / Imen / Amon.
    "amun": "amn",
    "amen": "amn",
    "amon": "amn",
    "imen": "amn",
    "imn": "amn",
    "amn": "amn",
    # Maat / Ma'at / Maet.
    "maat": "maat",
    "maet": "maat",
    "mat": "maat",
    "ma'at": "maat",
    # Ptah.
    "ptah": "ptah",
    # common vowel-carrier neb / nb.
    "neb": "nb",
    "nb": "nb",
}

_TOKEN_SPLIT = re.compile(r"[\s.\-·]+")
_BRACKETS = re.compile(r"\[[^\]]*\]")
_NONALNUM = re.compile(r"[^a-z0-9]+")
_PLAIN_VOWELS = re.compile(r"[aeiou]")

# A skeleton shorter than this is too collision-prone to be a useful blocking key, so it
# is not emitted (e.g. a two-consonant residue).
_MIN_SKELETON_LEN = 4


def _strip_diacritics(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def _apply_german(s: str) -> str:
    """Fold German transcription digraphs (Beckerath) on an already-lowercased string."""
    for src, rep in _GERMAN_DIGRAPHS:
        s = s.replace(src, rep)
    return s


def _alnum(s: str) -> str:
    return _NONALNUM.sub("", s)


def translit_key(raw: str) -> str:
    """Transliteration → compact ASCII consonantal key."""
    s = _apply_german(raw.lower())
    for glyph, rep in _GLYPH_MAP:
        s = s.replace(glyph, rep)
    s = _strip_diacritics(s)
    s = _BRACKETS.sub("", s).replace("?", "")
    return _alnum(s)


def phon_key(raw: str) -> str:
    """Vowelled/anglicised → canonical-element key."""
    s = _strip_diacritics(_apply_german(raw.lower()))
    s = _BRACKETS.sub("", s).replace("?", "")
    tokens = [t for t in _TOKEN_SPLIT.split(s) if t]
    canon = []
    for t in tokens:
        a = _alnum(t)
        canon.append(_ELEMENT_CANON.get(a, a))
    return "".join(canon)


def skeleton_key(raw: str) -> str:
    """Consonantal skeleton: the transliteration key with plain vowels dropped. Collapses
    epenthetic-vowel divergence (``khnum`` / ``chnem`` / ``ẖnm`` → ``khnmbr``). Lossy and
    recall-oriented — returns ``""`` when the residue is too short to block on."""
    sk = _PLAIN_VOWELS.sub("", translit_key(raw))
    return sk if len(sk) >= _MIN_SKELETON_LEN else ""


@dataclass(frozen=True)
class NameForm:
    """A single attested name form (one prenomen variant, one horus name, ...)."""

    surface: str
    translit: str | None = None


def keys_for_form(form: NameForm, *, skeleton: bool = False) -> set[str]:
    """All normalized keys derivable from one name form (union of the paths). With
    ``skeleton=True`` the consonantal-skeleton key is also included — enabled only for the
    throne-name / Horus-name corroborators, never the loose name blocker (see module doc).
    """
    keys: set[str] = set()
    for src in (form.translit, form.surface):
        if not src:
            continue
        for k in (translit_key(src), phon_key(src)):
            if k:
                keys.add(k)
        if skeleton:
            sk = skeleton_key(src)
            if sk:
                keys.add(sk)
    return keys


def key_set(forms: list[NameForm], *, skeleton: bool = False) -> set[str]:
    """Union of normalized keys across a set of name forms."""
    s: set[str] = set()
    for f in forms:
        s |= keys_for_form(f, skeleton=skeleton)
    return s


def intersects(a: set[str], b: set[str]) -> list[str]:
    """Sorted shared keys (set-valued corroboration, ADR-020 §6)."""
    return sorted(a & b)
