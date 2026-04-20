"""Apply post-merge corrections to Leprohon's reconciled.jsonl.

Two classes of correction (per the Phase-0 playbook):

1. **Spot corrections** — specific rows the `egyptologist-reviewer` subagent
   flagged against the PDF. Hard-coded in `EARLY_DYNASTIC_CORRECTIONS` as
   `(leprohon_id, json_path, new_value, rationale)` tuples. Every rationale
   is scholar-legible — "book p. X shows Y, not Z" rather than "LLM said so".

2. **Deterministic recomputation** — fields that are a pure function of
   other extracted fields. Leprohon's schema does NOT currently have such
   fields (unlike Kitchen's `concurrent_with_kings`, which derives from
   BCE date intervals); the `variant_index` is extractor-driven, not a
   post-merge derivation. This section is empty for now and reserved for
   future chunks (e.g. a cross-source `pharaoh_se_join_key` if Phase A
   demands one).

`json_path` is a dotted-path string used by `_set_by_path` to address
nested dict/list entries. Examples:
  - `"display_name"` — set top-level scalar.
  - `"horus_names.0.translation"` — set the translation of the first
    `horus_names` entry.
  - `"later_cartouche_names.2.attested_in"` — set the attested_in list
    of the third later_cartouche_names entry.

Every applied correction is appended to `merge-disagreements.txt` under
the heading `LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED`. Re-running
`fix_rows.py` is idempotent — the log section is replaced in place, not
duplicated.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/leprohon-2013-titulary/fix_rows.py

Outputs:
    reconciled.jsonl                 (rewritten in place with corrections)
    merge-disagreements.txt          (override-log section appended/replaced)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"
DIFF = SOURCE_DIR / "merge-disagreements.txt"

OVERRIDE_HEADER = "=== LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED ===\n"


# Per-chunk correction lists. Concatenated into SPOT_CORRECTIONS below.
#
# Format: (leprohon_id, json_path, new_value, rationale)

EARLY_DYNASTIC_CORRECTIONS: list[tuple[str, str, object, str]] = [
    # Egyptologist-reviewer 2026-04-20: page range transcription error in
    # agent-merged source_note. Leprohon p. 22 fn. 12 opens with "Gauthier
    # 1907, 1–3, 17–19" — pypdf extracted this correctly; OCR misread "1–3"
    # as "4–5" and the merge majority-voted for OCR. Restore the pypdf form.
    (
        "leprohon-0.03",
        "horus_names.0.source_note",
        (
            "Gauthier 1907, 1–3, 17–19; von Beckerath 1999, 36–37. "
            "Narmer is possibly the King Menes—Egyptian mni (meni), "
            '"The established one"—of tradition, although some scholars '
            "equate the Horus Aha with Menes. See, lately, the discussion "
            "in Raffaele 2003, 106–7."
        ),
        "Leprohon p. 22 fn. 12 opens with 'Gauthier 1907, 1–3, 17–19'; OCR "
        "misread as '4–5', pypdf had it correctly. Egyptologist-reviewer "
        "2026-04-20 confirmed against the PDF.",
    ),
    # NOTE: the original egyptologist-reviewer 2026-04-20 pass flagged
    # leprohon-1.06 Semerkhet's Horus transliteration `smr ẖt` as wanting
    # `smr ḫt` instead. That correction was WRONG and has been removed
    # after user-directed re-verification (2026-04-20):
    #
    # 1. The publisher's embedded PDF text layer for Leprohon p. 26 is
    #    `smr Xt` (capital X). In Manuel de Codage, `X` → ẖ (h-with-line-
    #    below, "body"); `x` → ḫ (h-with-breve-below, "thing"). pypdf
    #    read the text layer faithfully and the MdC normalizer applied
    #    the correct `X → ẖ` mapping.
    # 2. The reviewer argued `kh` in the anglicised gloss `(semer khet)`
    #    implied ḫ — but `kh` is an anglicisation of BOTH ẖ and ḫ, so
    #    the gloss alone doesn't disambiguate.
    # 3. Semantic check: ẖt = "body", ḫt = "thing / matter". Leprohon's
    #    own translation reads "Friend of the (divine) body (i.e., the
    #    Ennead)" — "body" maps to ẖt, confirming pypdf.
    # 4. Visual inspection of the rendered PDF page 26 (user request,
    #    2026-04-20) confirms the glyph is h-with-line-below (ẖ), not
    #    h-with-breve (ḫ). The reviewer misread the rendered diacritic.
    #
    # Lesson recorded in user feedback memory: don't silently apply
    # reviewer corrections that contradict deterministic pipeline output
    # plus the source's own translation. Over-trusting a single reviewer
    # verdict against corroborating evidence produced a regression here.
    # Future MdC `X` vs `x` disagreements: verify text layer + gloss +
    # translation semantics BEFORE overriding pypdf.
    # Egyptologist-reviewer 2026-04-20: the extractors included the
    # translation's leading "Seth, " in the anglicised column. Leprohon
    # p. 29 prints only `(per(u) ib.sen)` in the parenthetical gloss; the
    # "Seth," prefix belongs to the translation column.
    (
        "leprohon-2.07",
        "seth_names.0.anglicised",
        "per(u) ib.sen",
        "Leprohon p. 29: parenthetical gloss is '(per(u) ib.sen)' only. The "
        "'Seth,' prefix the agents concatenated belongs to the translation "
        "column ('Seth, (for whom ?) their will has come forth'), not the "
        "anglicised field. Egyptologist-reviewer 2026-04-20 high-confidence.",
    ),
    # Egyptologist-reviewer 2026-04-20: translator-glosses (fn. 60) from
    # the *translation* column leaked into source_note. "Horus and Seth."
    # is fn. 60 glossing the "two powers" in the translation — not a
    # scholarly source-note.
    (
        "leprohon-2.01",
        "horus_names.0.source_note",
        "Gauthier 1907, 37; von Beckerath 1999, 42–43.",
        "Trim trailing 'Horus and Seth.' — fn. 60 is a translator-gloss on "
        "'two powers', not scholarly commentary. Belongs dropped per schema "
        "'source_note = non-attestation scholarly commentary'.",
    ),
    # Egyptologist-reviewer 2026-04-20: same pattern as 2.01 — chained
    # translator-glosses from fns. 81 and 82 leaked into source_note.
    (
        # Canonical Khasekhemwy Horus/Seth 2 source_note. Applied to all
        # THREE dual-emit copies (horus_names[1], nebty_names[0],
        # seth_names[0]) so the symmetry invariant holds — the fn. 83
        # honorific-transposition note is scholarly commentary on the
        # entry's meaning, not Nebty-specific, and belongs on every copy.
        # Code-reviewer 2026-04-20 PR #86 P2-2 (dual-emit symmetry).
        "leprohon-2.08",
        "horus_names.1.source_note",
        (
            "Horus/Seth 2 form: the king reconciled the Seth and Horus "
            "traditions; the serekh is topped by BOTH Horus and Seth "
            "animals. See the accompanying Two Ladies entries which "
            "repeat this dual form. If the two signs nbwy in the last "
            "phrase were placed in honorific transposition, this part "
            "of the name might read ḥtp nbwy im.f, \"The two lords "
            "within him are satisfied.\""
        ),
        "Trim fn. 81/82 translator-glosses leaked from the translation "
        "column; mirror fn. 83 honorific-transposition note across all "
        "three Horus/Seth 2 copies for dual-emit symmetry.",
    ),
    (
        "leprohon-2.08",
        "nebty_names.0.source_note",
        (
            "Horus/Seth 2 form: the king reconciled the Seth and Horus "
            "traditions; the serekh is topped by BOTH Horus and Seth "
            "animals. See the accompanying Two Ladies entries which "
            "repeat this dual form. If the two signs nbwy in the last "
            "phrase were placed in honorific transposition, this part "
            "of the name might read ḥtp nbwy im.f, \"The two lords "
            "within him are satisfied.\""
        ),
        "Canonical Horus/Seth 2 source_note — identical to horus_names[1] "
        "and seth_names[0] per dual-emit symmetry (code-reviewer P2-2).",
    ),
    (
        "leprohon-2.08",
        "seth_names.0.source_note",
        (
            "Horus/Seth 2 form: the king reconciled the Seth and Horus "
            "traditions; the serekh is topped by BOTH Horus and Seth "
            "animals. See the accompanying Two Ladies entries which "
            "repeat this dual form. If the two signs nbwy in the last "
            "phrase were placed in honorific transposition, this part "
            "of the name might read ḥtp nbwy im.f, \"The two lords "
            "within him are satisfied.\""
        ),
        "Canonical Horus/Seth 2 source_note — identical to horus_names[1] "
        "and nebty_names[0] per dual-emit symmetry (code-reviewer P2-2).",
    ),
]

FIP_CORRECTIONS: list[tuple[str, str, object, str]] = [
    # Gemini Code Assist 2026-04-20 (PR #86 review): the pypdf MdC
    # normaliser only normalises transliteration spans inside name-rows,
    # NOT prose or footnote text. Leprohon's footnotes reference the
    # Egyptian word being discussed in MdC shorthand — `Xt`, `tAwy`,
    # `sA ra` — and those bare references leak into source_note fields
    # when agents pull footnote text. Spot-normalise each occurrence to
    # the Egyptological Unicode form to match the transliteration
    # convention used everywhere else.
    (
        "leprohon-9-10a.01",
        "birth_names.0.source_note",
        (
            "Although the name is missing in the Turin Canon (col. 4,18), "
            "Manetho's Ninth Dynasty consisted of \"nineteen kings of "
            "Herakleopolis,\" the first of whom was a \"King Achthoes\" "
            "(Waddell 1940, 60–61). Hence, it is possible that the missing "
            "name in Turin 4,18 was a King Khety, as the original Egyptian "
            "name read, who is numbered as the First here. The name "
            "Achthoes is sometimes rendered as Akhtoy in history books. "
            "For the term ẖt meaning \"the (divine) Corporation,\" "
            "referring to the Ennead, see Wb III, 357:18 and Hannig 2006b, "
            "1972. Ramesside-attested only — no contemporary attestation "
            "per Leprohon's headword asterisk. Leprohon marks this king's "
            "headword with square brackets, indicating a reconstructed name."
        ),
        "Normalise MdC `Xt` → Unicode `ẖt` inside footnote prose. Gemini "
        "Code Assist 2026-04-20 P2 inline comment on line 88.",
    ),
    (
        "leprohon-9-10b.05",
        "nebty_names.0.source_note",
        (
            "The Two Ladies name is known from the previously mentioned "
            "staff as well as a fragmentary inlaid ivory chest from Lisht, "
            "where the end of the cobra over the basket hieroglyphs is "
            "clear immediately before the mry ib tꜣwy elements (Hayes "
            "1953, 143, fig. 86). Henceforth, the Two Ladies name becomes "
            "a regular part of the royal titulary; see von Beckerath 1999, "
            "74 n. 6."
        ),
        "Three fixes: grammar `names is known` → `name is known`; `are "
        "clear` → `is clear`; MdC `tAwy` → Unicode `tꜣwy`. Gemini Code "
        "Assist 2026-04-20 P2 inline comment on line 101.",
    ),
    # Egyptologist-reviewer 2026-04-20 P2-3 (chunk 3 PR #86): the Intef I
    # footnote-30 content attaches biographic / etymology commentary about
    # the name "Intef" that belongs on the Birth name entry (where "Intef"
    # is the actual name being qualified), not on the Horus name
    # `shr tꜣwy`. Move the etymology content to birth_names, and merge it
    # with the existing Tod-chapel / Postel 2003 note there (which also
    # needed the Gemini MdC+typo fixes).
    (
        "leprohon-11a.02",
        "horus_names.0.source_note",
        None,
        "Relocate king-level etymology content to birth_names where the "
        "name 'Intef' is the entry subject. Egyptologist-reviewer "
        "2026-04-20 P2-3.",
    ),
    (
        "leprohon-11a.02",
        "birth_names.0.source_note",
        (
            "Gauthier 1907, 204–5; von Beckerath 1999, 76–77. The name "
            "\"Intef\" is sometimes rendered \"Inyotef\"; the latter name "
            "reflects the Coptic word for father, eiwt. At Tod, in a "
            "chapel erected by Mentuhotep II, the epithet sꜣ rꜥ (sa ra), "
            "\"The son of Re,\" is added within the cartouche; see Postel "
            "2003, 409, fig. 3."
        ),
        "Merge etymology content from horus_names[0] (egyptologist P2-3 "
        "relocation) with existing Postel 2003 chapel note; fix MdC `sA "
        "ra` → `sꜣ rꜥ` and typo `fig, 3` → `fig. 3` (Gemini Code Assist "
        "2026-04-20 P2 inline comment on line 104).",
    ),
    # Egyptologist-reviewer 2026-04-20 (chunk 3 PR #86): dual-emitted
    # `Throne and birth:` entries must carry SYMMETRIC source_notes on both
    # copies. Agents consistently emitted the Ramesside-only tag / bracket-
    # reconstruction note / footnote context only on the `throne_names`
    # copy, leaving the `birth_names` copy with just the "Throne and Birth"
    # dual-emission note. Fix: copy the full throne_names source_note into
    # birth_names so downstream consumers see the same provenance regardless
    # of which side of the dual-emission they read from.
    (
        "leprohon-9-10a.07",
        "birth_names.0.source_note",
        (
            "Ramesside-attested only — no contemporary attestation per "
            "Leprohon's headword asterisk. Leprohon marks this king's "
            "headword with square brackets, indicating a reconstructed "
            "name. Leprohon labels as 'Throne and Birth' — a combined "
            "prenomen/nomen where fragmentary evidence prevents separation."
        ),
        "Khety IV is dual-emitted to throne_names + birth_names (combined "
        "'Throne and birth:' label); both copies must carry identical "
        "provenance. birth_names copy was missing the Ramesside-only tag "
        "and bracket-reconstruction note present on throne_names. "
        "Egyptologist-reviewer 2026-04-20 P2-1.",
    ),
    (
        "leprohon-9-10b.03",
        "birth_names.0.source_note",
        (
            "The cartouche is found in the same quarry as the preceding "
            "entry (= Anthes 1928, pl. 6, no. X). The word, a noun or a "
            "verb, is unreadable. Leprohon labels as 'Throne and Birth' — "
            "a combined prenomen/nomen where fragmentary evidence "
            "prevents separation."
        ),
        "Khety VI is dual-emitted to throne_names + birth_names (combined "
        "'Throne and birth:' label); both copies must carry identical "
        "provenance. birth_names copy was missing the fn. 16–17 Anthes-"
        "quarry context present on throne_names. "
        "Egyptologist-reviewer 2026-04-20 P2-2.",
    ),
]

DYN13_CORRECTIONS: list[tuple[str, str, object, str]] = [
    # Gemini Code Assist 2026-04-20 PR #88: entry 13.35 Sewadjtu is a
    # combined "Throne and Birth names" row that should dual-emit to both
    # throne_names and birth_names (same pattern as chunk-3 Khety IV /
    # Khety VI, chunk-1 Khasekhemwy Horus/Seth 2). Two of three agents
    # did dual-emit but with slightly different source_note phrasings; the
    # merge JSON-string-equality vote split 1:1:1 and picked `[]` for
    # birth_names by first-seen. fix_rows restores the dual-emission with
    # a canonical source_note matching the chunk-3 convention exactly so
    # the `test_dual_emit_source_notes_are_symmetric` invariant holds.
    (
        "leprohon-13.35",
        "throne_names.0.source_note",
        (
            "Gauthier 1912, 46; von Beckerath 1999, 98–99. Leprohon "
            "labels as 'Throne and Birth' — a combined prenomen/nomen "
            "where fragmentary evidence prevents separation."
        ),
        "Canonical source_note for dual-emitted Throne-and-Birth entry, "
        "matching the chunk-3 Khety IV/VI convention exactly for symmetry.",
    ),
    (
        "leprohon-13.35",
        "birth_names",
        [
            {
                "transliteration": "sꜥnḫ.n rꜥ swꜣḏ.tw",
                "anglicised": "sankh.en ra, sewadj.tu",
                "translation": "The one whom Re has sustained (when?) <He> was made to flourish",
                "variant_index": 1,
                "is_variant": False,
                "attested_in": [],
                "source_note": (
                    "Gauthier 1912, 46; von Beckerath 1999, 98–99. Leprohon "
                    "labels as 'Throne and Birth' — a combined prenomen/nomen "
                    "where fragmentary evidence prevents separation."
                ),
            }
        ],
        "Restore missing dual-emission to birth_names (Gemini Code Assist "
        "2026-04-20 PR #88). 3-way agent disagreement on source_note "
        "phrasing caused merge to pick `[]` by first-seen; this override "
        "mirrors the canonical throne_names entry verbatim.",
    ),
]

DYN18_CORRECTIONS: list[tuple[str, str, object, str]] = [
    # Egyptologist-reviewer 2026-04-20 PR #91 P2: Akhenaten's two stages
    # (10a/10b) currently have display_name = "Amenhotep IV (Regnal Years
    # 1 to 5)" / "Akhenaten (Regnal Years 5 to 17)". Phase-A museum-record
    # matching needs the bare king names too — museums catalog under plain
    # "Amenhotep IV" or "Akhenaten", not the parenthetical-included form.
    (
        "leprohon-18.10a",
        "alt_display_names",
        ["Amenhotep IV"],
        "Add bare king-name alt for Phase-A museum-record matching. "
        "Egyptologist-reviewer 2026-04-20 PR #91 P2.",
    ),
    (
        "leprohon-18.10b",
        "alt_display_names",
        ["Akhenaten"],
        "Add bare king-name alt for Phase-A museum-record matching. "
        "Egyptologist-reviewer 2026-04-20 PR #91 P2.",
    ),
    # Code-reviewer 2026-04-20 PR #91 P1: Smenkhkare (18.12) is a
    # `Throne and Birth names:` combined-cartouche dual-emit (same
    # convention as Sewadjtu 13.35, Khety IV/VI, Khasekhemwy). The 3
    # agents emitted divergent source_note phrasings; canonicalize
    # both copies to a single text matching the chunk-3/5 convention
    # so `test_dual_emit_source_notes_are_symmetric` (after Smenkhkare
    # is added to DUAL_EMIT_PAIRS) holds.
    (
        "leprohon-18.12",
        "throne_names.0.source_note",
        (
            "Gauthier 1912, 362–64. Leprohon labels as 'Throne and Birth' "
            "— a combined entry where Throne and Birth names share a "
            "single cartouche. Horus, Two Ladies, and Golden Horus names "
            "are not attested for this king."
        ),
        "Canonical source_note for Smenkhkare dual-emit (chunk-3/5 "
        "convention). Agents disagreed on phrasing; canonicalize to a "
        "single richer text on both copies for symmetry-test compliance.",
    ),
    (
        "leprohon-18.12",
        "birth_names.0.source_note",
        (
            "Gauthier 1912, 362–64. Leprohon labels as 'Throne and Birth' "
            "— a combined entry where Throne and Birth names share a "
            "single cartouche. Horus, Two Ladies, and Golden Horus names "
            "are not attested for this king."
        ),
        "Canonical source_note for Smenkhkare dual-emit (matches "
        "throne_names copy exactly per dual-emit symmetry).",
    ),
]

DYN13A14_CORRECTIONS: list[tuple[str, str, object, str]] = [
    # Egyptologist-reviewer 2026-04-20 PR #89 P2-4: Dyn 14 entry 3 Qareh
    # was previously catalogued by museums as "Qar" (per Leprohon p. 95
    # fn. 140 "this king, whose name was previously read as Qar").
    # Museums catalogued before Ryholt 1997 still use "Qar"; Phase-A
    # matching needs both forms.
    (
        "leprohon-14.03",
        "alt_display_names",
        ["Qar"],
        "Add historical alt-spelling `Qar` (Leprohon p. 95 fn. 140, "
        "pre-Ryholt reading) for Phase-A museum-record matching. "
        "Egyptologist-reviewer 2026-04-20 P2-4.",
    ),
]

MK_CORRECTIONS: list[tuple[str, str, object, str]] = [
    # Egyptologist-reviewer 2026-04-20 (PR #87): Leprohon's own section
    # header on PDF p. 81 line 320 reads `(Queen) Sobeknefru` (no 'e'
    # between f and r); footnote 46 explicitly argues FOR this spelling
    # over `Nefrusobek` on Greek-version (Scemiophris) grounds. The
    # reconciled display_name is the museum-matching default `Sobekneferu`
    # (Met, Brooklyn, BM), but `alt_display_names` should carry the
    # Leprohon-preferred `Sobeknefru` plus the older `Nefrusobek` /
    # `Neferusobek` forms that appear in older museum records. Phase-A
    # matching needs all three to resolve museum catalog entries.
    (
        "leprohon-12.08",
        "alt_display_names",
        ["Sobeknefru", "Nefrusobek", "Neferusobek"],
        "Add Leprohon-endorsed spelling `Sobeknefru` (per Leprohon p. 81 "
        "§ header line 320 + fn. 46 Greek-version argument) plus older "
        "forms `Nefrusobek` / `Neferusobek` for Phase-A matching against "
        "older museum catalogs. Egyptologist-reviewer 2026-04-20 P2-1.",
    ),
]

SPOT_CORRECTIONS: list[tuple[str, str, object, str]] = [
    *EARLY_DYNASTIC_CORRECTIONS,
    *FIP_CORRECTIONS,
    *MK_CORRECTIONS,
    *DYN13_CORRECTIONS,
    *DYN13A14_CORRECTIONS,
    *DYN18_CORRECTIONS,
]


# Deterministic post-pass: the 3-agent extraction prompt told agents to flag
# OCR-vs-pypdf transliteration disagreements via a debug string appended to
# `source_note`. Majority vote propagated that debug string into the merged
# output for ~10 rows. The egyptologist-reviewer 2026-04-20 flagged this as
# schema-level debug-string leakage; we strip it deterministically across
# every name-entry `source_note` before spot corrections run.
OCR_PYPDF_DEBUG_RE = re.compile(
    r"\s*(?:^|\. )?OCR vs pypdf (?:transliteration )?disagreement:.*?$",
    flags=re.DOTALL,
)


def _strip_ocr_pypdf_debug(text: str | None) -> str | None:
    if not text:
        return text
    cleaned = OCR_PYPDF_DEBUG_RE.sub("", text).strip()
    return cleaned if cleaned else None


def _set_by_path(row: dict, path: str, value: object) -> None:
    """Set a nested field in a row by dotted-path string.

    Numeric path segments index into lists; non-numeric segments key into
    dicts. Raises KeyError / IndexError on unreachable paths — we do NOT
    silently succeed on a typo'd path because that would hide broken
    corrections.
    """
    parts = path.split(".")
    *parents, leaf = parts
    cursor: object = row
    for part in parents:
        if part.isdigit():
            assert isinstance(cursor, list), (
                f"path {path!r}: expected list at segment {part!r}, got {type(cursor).__name__}"
            )
            cursor = cursor[int(part)]
        else:
            assert isinstance(cursor, dict), (
                f"path {path!r}: expected dict at segment {part!r}, got {type(cursor).__name__}"
            )
            cursor = cursor[part]
    if leaf.isdigit():
        assert isinstance(cursor, list)
        cursor[int(leaf)] = value
    else:
        assert isinstance(cursor, dict)
        cursor[leaf] = value


NAME_LIST_FIELDS = (
    "horus_names",
    "nebty_names",
    "golden_horus_names",
    "throne_names",
    "birth_names",
    "later_cartouche_names",
    "later_horus_names",
    "seth_names",
)


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

# All MdC codes in the MDC_MAP are normalisation targets in the
# transliteration safety net. Lowercase codes (`a`/`q`/`x`) ARE
# applied here even though they're ambiguous with English letters —
# this function only runs on `transliteration` fields, which are pure
# Egyptological text (no English prose), so the ambiguity doesn't
# apply. The earlier uppercase-only restriction was too conservative;
# it left `xa`, `xprw`, `smnx`, `iwa ra` etc. unnormalised in the
# Dyn 18 epithets-added blocks (Gemini PR #91 high-priority finding).
# frozenset for O(1) membership checks in the per-character generator.
_TRANSLIT_MDC_CODES = frozenset(MDC_MAP)


def _apply_mdc_on_transliteration(text: str) -> str:
    """Apply MdC → Egyptological Unicode normalisation across the full
    MdC subset (uppercase A/H/X/S/T/D + lowercase a/q/x).

    Safety net for transliteration fields that slipped past
    transcribe_chunk.py's gloss-boundary detection. Egyptological
    Unicode transliterations are all-lowercase Latin + diacritical
    marks; ANY MdC code character in a `transliteration` field is an
    unnormalised gap.

    Lowercase ambiguity caveat: `a`, `q`, `x` are valid English letters.
    This function MUST NOT be applied to `source_note` / `translation` /
    `anglicised` fields — only to `transliteration`, which is pure
    Egyptological text where the ambiguity doesn't arise.
    """
    return "".join(MDC_MAP[ch] if ch in _TRANSLIT_MDC_CODES else ch for ch in text)


def normalize_translit_mdc(rows: list[dict]) -> list[str]:
    """Walk every name-entry's `transliteration` field and apply the uppercase-
    MdC safety net. Logs every actual normalisation; silent on fields that
    already contain no uppercase MdC codes.

    Addresses transcribe_chunk.py regex gaps where embedded-paren filiation
    markers (`(sꜣ)`) or post-colon-label patterns (`Throne and Birth names:`)
    previously escaped the gloss-boundary detection; those are fixed upstream
    in transcribe_chunk.py, but committed reconciled.jsonl rows that were
    extracted before the fix still need normalisation.
    """
    log_lines: list[str] = []
    for row in rows:
        lid = row["leprohon_id"]
        for field in NAME_LIST_FIELDS:
            for idx, entry in enumerate(row.get(field, [])):
                translit = entry.get("transliteration")
                if not isinstance(translit, str):
                    continue
                normalised = _apply_mdc_on_transliteration(translit)
                if normalised != translit:
                    entry["transliteration"] = normalised
                    log_lines.append(
                        f"  {lid} / {field}.{idx}.transliteration: "
                        f"{translit!r} → {normalised!r}"
                    )
    return log_lines


def backfill_stage_suffix(rows: list[dict]) -> list[str]:
    """Ensure every row has the `stage_suffix` top-level field.

    Chunk 4 (Middle Kingdom) introduces `stage_suffix: str | None` to
    represent Leprohon's titulary-stage numbering (Mentuhotep II's a/b/c,
    Amenemhat I's a/b). Chunks 1/2/3 rows have no stages and need
    `stage_suffix: None` backfilled so the schema shape is uniform and
    downstream consumers don't need to branch on present-vs-absent.

    Code-reviewer-style consistency with the `backfill_name_list_fields`
    pattern — rule 4 (single source of truth) requires the schema shape
    be invariant across all rows.
    """
    log_lines: list[str] = []
    for row in rows:
        if "stage_suffix" not in row:
            row["stage_suffix"] = None
            log_lines.append(
                f"  {row['leprohon_id']}: backfilled stage_suffix=None"
            )
    return log_lines


def backfill_name_list_fields(rows: list[dict]) -> list[str]:
    """Ensure every row has every key in `NAME_LIST_FIELDS`, defaulting `[]`.

    Chunk-3 introduced `later_horus_names` as a new top-level name-type
    field. Chunk-1 / chunk-2 rows were extracted before the field existed
    and their reconciled entries are missing the key. Constitutional rule
    4 (single source of truth) requires the schema shape be consistent
    across all rows so tests can iterate `r[field]` directly without
    `.get(field, [])` masking missing-vs-empty distinctions.

    Gemini / code-reviewer 2026-04-20 PR #86: "add a deterministic pass in
    fix_rows.py that ensures every row has every key in NAME_LIST_FIELDS".
    """
    log_lines: list[str] = []
    for row in rows:
        lid = row["leprohon_id"]
        added: list[str] = []
        for field in NAME_LIST_FIELDS:
            if field not in row:
                row[field] = []
                added.append(field)
        if added:
            log_lines.append(
                f"  {lid}: backfilled missing name-list fields "
                f"{added!r} as []"
            )
    return log_lines


def strip_debug_leakage(rows: list[dict]) -> list[str]:
    """Walk every name-entry in every row and strip the OCR-vs-pypdf debug
    string from `source_note`. Returns log lines describing each strip.

    Runs BEFORE spot corrections so that the spot corrections operate on
    already-cleaned text (simplifying their rationale descriptions).
    """
    log_lines: list[str] = []
    for row in rows:
        lid = row["leprohon_id"]
        for field in NAME_LIST_FIELDS:
            for idx, entry in enumerate(row.get(field, [])):
                before = entry.get("source_note")
                after = _strip_ocr_pypdf_debug(before)
                if after != before:
                    entry["source_note"] = after
                    log_lines.append(
                        f"  {lid} / {field}.{idx}.source_note:\n"
                        f"    stripped OCR-vs-pypdf debug tail\n"
                        f"    before: {json.dumps(before, ensure_ascii=False)}\n"
                        f"    after:  {json.dumps(after, ensure_ascii=False)}"
                    )
    return log_lines


def apply_corrections() -> list[str]:
    """Apply deterministic debug-string strip + every SPOT_CORRECTIONS entry
    to reconciled.jsonl in place.

    Returns a list of human-readable log lines describing each applied
    correction, for appending to merge-disagreements.txt.
    """
    rows = [json.loads(line) for line in RECONCILED.read_text().splitlines() if line.strip()]
    log_lines: list[str] = []

    # Deterministic passes first — normalise schema shape + strip debug-string
    # leakage uniformly so that any spot corrections that follow operate on
    # clean, fully-keyed rows.
    log_lines.extend(backfill_name_list_fields(rows))
    log_lines.extend(backfill_stage_suffix(rows))
    log_lines.extend(strip_debug_leakage(rows))
    log_lines.extend(normalize_translit_mdc(rows))

    by_id = {r["leprohon_id"]: r for r in rows}
    for lid, path, new_value, rationale in SPOT_CORRECTIONS:
        if lid not in by_id:
            raise KeyError(f"SPOT_CORRECTIONS references unknown leprohon_id: {lid!r}")
        row = by_id[lid]
        _set_by_path(row, path, new_value)
        log_lines.append(
            f"  {lid} / {path}:\n"
            f"    new value: {json.dumps(new_value, ensure_ascii=False, sort_keys=True)}\n"
            f"    rationale: {rationale}"
        )
    RECONCILED.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows)
        + "\n"
    )
    return log_lines


def update_diff_log(log_lines: list[str]) -> None:
    """Append / replace the override-log section in merge-disagreements.txt."""
    existing = DIFF.read_text() if DIFF.exists() else ""
    if OVERRIDE_HEADER in existing:
        body_before = existing.split(OVERRIDE_HEADER, 1)[0]
    else:
        body_before = existing
    if not body_before.endswith("\n"):
        body_before += "\n"
    new_body = body_before + "\n" + OVERRIDE_HEADER
    if log_lines:
        new_body += "\n".join(log_lines) + "\n"
    else:
        new_body += "(no overrides applied)\n"
    DIFF.write_text(new_body)


def main() -> None:
    log_lines = apply_corrections()
    update_diff_log(log_lines)
    print(f"Applied {len(log_lines)} SPOT_CORRECTIONS.")


if __name__ == "__main__":
    main()
