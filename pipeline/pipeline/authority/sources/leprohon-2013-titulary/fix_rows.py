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

DYN19_CORRECTIONS: list[tuple[str, str, object, str]] = [
    # Egyptologist + Gemini PR #92: Ramesses II Golden Horus variant 14
    # has a real ASCII typo in the anglicised field (`sekehm` should be
    # `sekhem`) AND was missing the trailing `der pedjut 9` portion of
    # Leprohon's parenthetical anglicisation. Source on physical p. 130:
    # `Golden Horus 14: sḫm-ḫpš dr pḏwt 9 (sekehm khepesh, der pedjut 9),
    # The powerful of arm/sword, who has repelled the Nine Bows`. Restore
    # the full anglicised string with the typo corrected.
    (
        "leprohon-19.03",
        "golden_horus_names.13.anglicised",
        "sekhem khepesh, der pedjut 9",
        "Fix ASCII typo `sekehm` → `sekhem` AND restore missing "
        "`der pedjut 9` suffix per Leprohon's anglicisation. "
        "Egyptologist + Gemini PR #92.",
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

TIP_LATE_CORRECTIONS: list[tuple[str, str, object, str]] = [
    # Gemini Code Assist PR #95 high-priority finding: 6 rows in Dyn 23
    # have throne-name epithets duplicated into the `birth_names` list
    # (in addition to their correct placement in `throne_names`). The
    # duplicates carry source_note "Epithet added to the Throne name."
    # — the agents extracted the epithet block once for throne_names
    # and wrongly emitted it again for birth_names. Remove the
    # duplicates and re-index variant_index on the remaining birth_names
    # entries. The throne_names placement is correct and unchanged.
    (
        "leprohon-23.01",
        "birth_names",
        [
            {"transliteration": "pꜣ di bꜣstt", "anglicised": "pa di bastet", "translation": "He whom Bastet has given", "variant_index": 1, "is_variant": False, "attested_in": [], "source_note": None},
            {"transliteration": "sꜣ ꜣst", "anglicised": "sa aset", "translation": "Son of Isis", "variant_index": 2, "is_variant": True, "attested_in": [], "source_note": "Epithet added to the Birth name."},
            {"transliteration": "mry imn", "anglicised": "mery imen", "translation": "Beloved of Amun", "variant_index": 3, "is_variant": True, "attested_in": [], "source_note": "Epithet added to the Birth name."},
        ],
        "Remove throne-epithet `stp n imn` wrongly duplicated into "
        "birth_names; re-index remaining birth entries. Gemini PR #95 P1.",
    ),
    (
        "leprohon-23.03",
        "birth_names",
        [
            {"transliteration": "ššnḳ", "anglicised": "shesheneq", "translation": "Sheshonq", "variant_index": 1, "is_variant": False, "attested_in": [], "source_note": "The epithet pr-aA, \"Pharaoh,\" was sometimes written before the name inside the cartouche."},
            {"transliteration": "mry imn", "anglicised": "mery imen", "translation": "Beloved of Amun", "variant_index": 2, "is_variant": True, "attested_in": [], "source_note": "Epithet added to the Birth name."},
        ],
        "Remove throne-epithet duplicate; re-index. Gemini PR #95 P1.",
    ),
    (
        "leprohon-23.04",
        "birth_names",
        [
            {"transliteration": "wsrkn", "anglicised": "weserken", "translation": "Osorkon", "variant_index": 1, "is_variant": False, "attested_in": [], "source_note": "As with the previous ruler, the epithet pr-aA, \"Pharaoh,\" was sometimes written before the name inside the cartouche."},
            {"transliteration": "sꜣ ꜣst mry imn", "anglicised": "sa aset, mery imen", "translation": "Son of Isis, beloved of Amun", "variant_index": 2, "is_variant": True, "attested_in": [], "source_note": "Epithet added to the Birth name."},
            {"transliteration": "nṯr ḥḳꜣ wꜣst", "anglicised": "netjer heqa waset", "translation": "The divine ruler of Thebes", "variant_index": 3, "is_variant": True, "attested_in": [], "source_note": "Epithet added to the Birth name."},
        ],
        "Remove throne-epithet `stp n imn` duplicate from Osorkon III "
        "birth_names; re-index. Gemini PR #95 second-pass HIGH P1.",
    ),
    (
        "leprohon-23.05",
        "birth_names",
        [
            {"transliteration": "tklt", "anglicised": "takelot", "translation": "Takelot", "variant_index": 1, "is_variant": False, "attested_in": [], "source_note": None},
            {"transliteration": "sꜣ ꜣst mry imn nṯr ḥḳꜣ wꜣst", "anglicised": "sa aset, mery imen, netjer heqa waset", "translation": "Son of Isis, beloved of Amun, the divine ruler of Thebes", "variant_index": 2, "is_variant": True, "attested_in": [], "source_note": "Epithet added to the Birth name."},
        ],
        "Remove throne-epithet duplicate; re-index. Gemini PR #95 P1.",
    ),
    (
        "leprohon-23.08",
        "birth_names",
        [
            {"transliteration": "iwpwt", "anglicised": "iuput", "translation": "Iuput", "variant_index": 1, "is_variant": False, "attested_in": [], "source_note": None},
            {"transliteration": "sꜣ bꜣstt mry imn", "anglicised": "sa bastet, mery imen", "translation": "Son of Bastet, beloved of Amun", "variant_index": 2, "is_variant": True, "attested_in": [], "source_note": "Epithet added to the Birth name."},
        ],
        "Remove throne-epithet duplicate; re-index. Gemini PR #95 P1.",
    ),
    (
        "leprohon-23.09",
        "birth_names",
        [
            {"transliteration": "ššnḳ", "anglicised": "shesheneq", "translation": "Sheshonq", "variant_index": 1, "is_variant": False, "attested_in": [], "source_note": None},
            {"transliteration": "mry imn", "anglicised": "mery imen", "translation": "Beloved of Amun", "variant_index": 2, "is_variant": True, "attested_in": [], "source_note": "Epithet added to the Birth name."},
            {"transliteration": "nṯr ḥḳꜣ wꜣst", "anglicised": "netjer heqa waset", "translation": "The divine ruler of Thebes", "variant_index": 3, "is_variant": True, "attested_in": [], "source_note": "Epithet added to the Birth name."},
        ],
        "Remove throne-epithet duplicate; re-index. Gemini PR #95 P1.",
    ),
    (
        "leprohon-23a.01",
        "birth_names",
        [
            {"transliteration": "pꜣ di bꜣstt", "anglicised": "pa di bastet", "translation": "He whom Bastet has given", "variant_index": 1, "is_variant": False, "attested_in": [], "source_note": None},
            {"transliteration": "sꜣ ꜣst", "anglicised": "sa aset", "translation": "Son of Isis", "variant_index": 2, "is_variant": True, "attested_in": [], "source_note": "Epithet added to the Birth name."},
            {"transliteration": "sꜣ bꜣstt", "anglicised": "sa bastet", "translation": "Son of Bastet", "variant_index": 3, "is_variant": True, "attested_in": [], "source_note": "Epithet added to the Birth name."},
            {"transliteration": "mry imn", "anglicised": "mery imen", "translation": "Beloved of Amun", "variant_index": 4, "is_variant": True, "attested_in": [], "source_note": "Epithet added to the Birth name."},
            {"transliteration": "stp n imn-rꜥ mꜣꜥt", "anglicised": "setep en imen-ra, maat", "translation": "Chosen by Amun-Re of Maat", "variant_index": 5, "is_variant": True, "attested_in": [], "source_note": "Epithet added to the Birth name."},
        ],
        "Remove throne-epithet duplicate; re-index. Gemini PR #95 P1.",
    ),
    # PR #97 root-cause fix: the three Dyn 23 Sheshonq alt_display_names
    # entries (Shoshenq VI / VIa / VII) were originally patched directly
    # into reconciled.jsonl in PR #97 rather than added here. That made
    # the aliases survive only as long as the file wasn't re-merged —
    # the chunk-14 re-merge (this PR) correctly blew them away because
    # the agent files don't carry them. Add the corrections here so
    # they're durable across future re-merges. Test
    # `test_dyn23_sheshonq_rows_preserve_shoshenq_aliases` locks the
    # invariant.
    (
        "leprohon-23.03",
        "alt_display_names",
        ["Shoshenq VI"],
        "Restore `Shoshenq VI` museum-spelling alias (Met / Brooklyn / "
        "Harvard / Kitchen-TIPE convention). PR #97 patched this into "
        "reconciled.jsonl directly; chunk-14 re-merge made it clear "
        "fix_rows.py is the durable place. Egyptologist 2026-04-20 PR #95.",
    ),
    (
        "leprohon-23.07",
        "alt_display_names",
        ["Shoshenq VIa"],
        "Restore `Shoshenq VIa` museum-spelling alias. See 23.03 note.",
    ),
    (
        "leprohon-23.09",
        "alt_display_names",
        ["Shoshenq VII"],
        "Restore `Shoshenq VII` museum-spelling alias. See 23.03 note.",
    ),
    # Egyptologist-reviewer 2026-04-20 PR #95 P2 (Dyn 25 aliases): 4
    # museum/scholarly aliases for the Nubian kings, attributed per
    # rule 1 (scholarly traceability) per code-reviewer PR #95 P1
    # demand.
    (
        "leprohon-25.06",
        "alt_display_names",
        ["Taharka", "Tirhakah"],
        "Add `Taharka` (Leclant/Kitchen orthography per egyptologist) "
        "and `Tirhakah` (biblical form, Isaiah 37:9 — appears in older "
        "museum catalogs that use biblical names). Egyptologist-reviewer "
        "2026-04-20 PR #95.",
    ),
    (
        "leprohon-25.07",
        "alt_display_names",
        ["Tantamani", "Tanutamani", "Tanwetamani"],
        "Add `Tantamani` (von Beckerath standard transliteration), "
        "`Tanutamani` (Gemini PR #95: missed alias from prompt's own "
        "alias enumeration), and `Tanwetamani` (post-Kitchen scholarly "
        "form). Leprohon's `Tanutamun` is the rarer reading; museums "
        "consistently use Tantamani or Tanwetamani.",
    ),
    (
        "leprohon-25.04",
        "alt_display_names",
        ["Shabako"],
        "Add `Shabako` (Leclant orthography per egyptologist; standard "
        "in Kitchen-TIPE and post-Kitchen Kushite scholarship). "
        "Egyptologist-reviewer 2026-04-20 PR #95.",
    ),
]

TIP_EARLY_CORRECTIONS: list[tuple[str, str, object, str]] = [
    # leprohon-21.02 page-citation: previously a fix_rows
    # SPOT_CORRECTION setting source_citation.printed_page=138 because
    # the merge silently picked agent A's wrong 139. Issue #128
    # promoted source_citation tie resolution to a TIE_BREAK_OVERRIDES
    # entry (consulted DURING merge), so the manual fix here is now
    # obsolete — see `tie-break-overrides.json` entry for
    # `leprohon-21.02|source_citation` carrying both printed=138 and
    # physical=159 in one shot. Removed from this file to avoid
    # double-correction.
    #
    # Egyptologist-reviewer 2026-04-20 PR #94 P1-2: Shoshenq is the
    # museum-standard transliteration variant of Sheshonq (Met / Brooklyn
    # / Harvard / Kitchen-TIPE all use Shoshenq). Per the prompt's
    # "transliteration-variant ≠ Greek alias" distinction, populate
    # alt_display_names for every Dyn 22 Sheshonq entry.
    *[
        (
            f"leprohon-22.{seq:02d}",
            "alt_display_names",
            [shoshenq_form],
            f"Add `{shoshenq_form}` to alt_display_names for Phase-A "
            f"museum-record matching (Met / Brooklyn / Harvard / "
            f"Kitchen-TIPE all use Shoshenq spelling). "
            f"Egyptologist-reviewer 2026-04-20 PR #94 P1-2.",
        )
        for seq, shoshenq_form in [
            (1, "Shoshenq I"),
            (3, "Shoshenq IIa"),
            (4, "Shoshenq IIb"),
            (8, "Shoshenq IIc"),
            (9, "Shoshenq III"),
            (10, "Shoshenq IV"),
            (12, "Shoshenq V"),
        ]
    ],
    # Egyptologist-reviewer 2026-04-20 PR #94 P2: Psousennes is the
    # older Bonhême/Montet spelling used in Met catalog entries
    # pre-Kitchen. Add to alt_display_names alongside the existing
    # Psusennes entries.
    (
        "leprohon-21.04",
        "alt_display_names",
        ["Psusennes I", "Psousennes I"],
        "Add older `Psousennes I` spelling for Phase-A matching "
        "(Bonhême/Montet publications used in older Met catalogs). "
        "Egyptologist-reviewer 2026-04-20 PR #94 P2.",
    ),
    (
        "leprohon-21.08",
        "alt_display_names",
        ["Psusennes II", "Psousennes II"],
        "Add older `Psousennes II` spelling. Egyptologist 2026-04-20 PR #94 P2.",
    ),
    (
        "leprohon-21a.03",
        "alt_display_names",
        ["Psusennes III", "Psousennes III"],
        "Add older `Psousennes III` spelling. Egyptologist 2026-04-20 PR #94 P2.",
    ),
]

DYN20_CORRECTIONS: list[tuple[str, str, object, str]] = [
    # Egyptologist-reviewer 2026-04-20 PR #93 P2-1: Ramesses III Horus
    # variants 9-15 are listed in Leprohon under the subheading "Various
    # monuments found outside the Royal Palace" (PDF p. 149, line 165),
    # explicitly distinct from the preceding Medinet-Habu-tagged block
    # (variants 1-8). The "Medinet Habu, " prefix mis-attributes them
    # back to the preceding block. Use the author's own subheading text
    # verbatim. (Royal Palace IS at Medinet Habu temple complex per
    # Hölscher 1941, but Leprohon's editorial choice was to separate
    # them; preserve that distinction.)
    *[
        (
            "leprohon-20.02",
            f"horus_names.{idx}.attested_in",
            ["Various monuments found outside the Royal Palace"],
            f"Replace incorrect 'Medinet Habu, ...' prefix on Horus "
            f"variant {idx + 1} with Leprohon's own subheading text. "
            f"Egyptologist-reviewer 2026-04-20 PR #93 P2-1.",
        )
        for idx in range(8, 15)  # H9 (idx 8) through H15 (idx 14)
    ],
    # Egyptologist-reviewer 2026-04-20 PR #93 P2-2: Sethnakht GH2 has
    # `attested_in: []` despite the source_note saying "Stela from the
    # Sinai (Gardiner and Peet 1955, no. 271)". Move the attestation
    # citation into the structured field for consistency with how
    # Ramesses III variants capture provenance.
    (
        "leprohon-20.01",
        "golden_horus_names.1.attested_in",
        ["Sinai stela (Gardiner and Peet 1955, no. 271)"],
        "Move Sinai-stela attestation from source_note prose into "
        "structured `attested_in` field. Egyptologist-reviewer "
        "2026-04-20 PR #93 P2-2.",
    ),
    # Gemini Code Assist PR #93: standard Egyptological lexicon has
    # `ḥd` (verb "to smite/attack") for the MdC `Hd`. The chunk file
    # extracted lowercase `hd` (not `Hd`), so the MdC safety net did
    # not normalize it — pypdf likely lost the diacritic on the
    # original `ḥd` glyph. Spot-correct the affected entries.
    (
        "leprohon-20.02",
        "horus_names.7.transliteration",
        "sḫm-pḥty ḥd ḥfnw dḫ nꜣ pḥw sw dmḏ (ẖr) ṯbwy.f(y)",
        "Fix `hd` → `ḥd` (smite). Gemini PR #93.",
    ),
    (
        "leprohon-20.05",
        "nebty_names.0.transliteration",
        "wsr-ḫpš ḥd ḥfnw",
        "Fix `hd` → `ḥd` (smite). Gemini PR #93.",
    ),
    (
        "leprohon-20.10",
        "nebty_names.0.transliteration",
        "wsr-ḫpš ḥd ḥfnw",
        "Fix `hd` → `ḥd` (smite). Gemini PR #93.",
    ),
    # Gemini Code Assist PR #93: standard Egyptological transliteration
    # of Tehenu (Libyan ethnonym) is `ṯḥnw`, not `tḥnw`. The MdC source
    # should have been `THnw` (both uppercase) but pypdf extracted
    # lowercase t.
    (
        "leprohon-20.02",
        "nebty_names.3.transliteration",
        "[wr-ḥbw-sd mi tꜣ-ṯnn] ptpt ṯḥnw m iwnw ḥr st.sn",
        "Fix `tḥnw` → `ṯḥnw` (Tehenu Libyan ethnonym). Gemini PR #93.",
    ),
]

MACEDONIAN_PTOLEMAIC_CORRECTIONS: list[tuple[str, str, object, str]] = [
    # Egyptologist-reviewer 2026-04-21 (PR for chunk 14): Cleopatra I's
    # Horus name has a pypdf text-layer corruption in the Khnum-ornamented
    # token. The pypdf+MdC pipeline produces `ẖḳr(t).n ẖnmw` — but the
    # PDF visual rendering on p. 181 shows `ḫkr(t).n ẖnmw` (verified
    # against the user-supplied screenshot 2026-04-21). The text layer
    # mis-encoded `ḫ` as `X` (capital, → ẖ) and `k` as `q` (→ ḳ); the
    # second token (`ẖnmw` Khnum) is correct. Fix the transliteration
    # only; the anglicised gloss `kheqer(et).en khnemu` is Leprohon's
    # own printed gloss (which has its own internal-vs-translit
    # divergence Leprohon never resolves) and stays as-is.
    (
        "leprohon-33.05a",
        "horus_names.0.transliteration",
        "ḥwn(t) sꜣt ḥḳꜣ ir(t).n ḥḳꜣ mr(t) nṯrw bꜣḳt ḫkr(t).n ẖnmw "
        "ṯꜣtt sꜣt ḏḥwty wr(t)-pḥty shr(t) tꜣwy rdi n.s nbty rḫyt n nfrw "
        "ḳni sy nt nb(t) sꜣw ṯni sy ḥt-ḥr m mrwt.s",
        "Fix pypdf text-layer corruption: `ẖḳr(t).n` → `ḫkr(t).n` "
        "(`ḫ` mis-encoded as `X`/ẖ, `k` mis-encoded as `q`/ḳ). PDF "
        "visual on p. 181 verified via user screenshot 2026-04-21. "
        "Egyptologist-reviewer P0/P1 finding.",
    ),
    # Egyptologist-reviewer 2026-04-21: Berenike at Ptolemaic slot 12 is
    # Berenike III in standard scholarship (daughter of Ptolemy IX, brief
    # 81 BCE co-rule). Leprohon prints only `BERENIKE` as the headword
    # (no roman numeral), so display_name stays `Berenike`, but Phase-A
    # matching against museum catalogs needs the disambiguated form.
    (
        "leprohon-33.12",
        "alt_display_names",
        ["Berenike III"],
        "Add `Berenike III` alias (standard Ptolemaic-history numbering: "
        "daughter of Ptolemy IX). Leprohon prints headword as bare "
        "`BERENIKE`. Egyptologist-reviewer P1.",
    ),
    # Gemini Code Assist PR #99 medium-priority finding: Ptolemy V's
    # Throne 1 transliteration has a stray comma after `it` — this is
    # the ONLY transliteration in the entire 395-row extract containing
    # a comma (verified by grep). The comma was carried over verbatim
    # from Leprohon's PDF text layer (chunk-p196-p209-pypdf.md line 309
    # reads `stp(n) ptH wsr kA ra sxm anx imn` preceded by `mrwy it,`).
    # Egyptological transliteration by convention does not use commas
    # for clause separation — this is a text-layer artifact, not a
    # Leprohon typesetting choice. Strip.
    (
        "leprohon-33.05",
        "throne_names.0.transliteration",
        "iwꜥ n nṯrwy mrwy it stp(n) ptḥ wsr kꜣ rꜥ sḫm ꜥnḫ imn",
        "Remove stray comma after `it` in transliteration "
        "(text-layer artifact, not Leprohon convention). "
        "Gemini Code Assist PR #99 medium finding.",
    ),
    # Gemini Code Assist PR #99 medium-priority finding: three chunk-14
    # Birth names encode alternative phonetic forms as slash-separated
    # tokens in a single entry (Alexander the Great, Alexander II/IV,
    # Cleopatra I). The established schema convention (e.g. Ptolemy XV
    # Caesarion birth_names at leprohon-33.17) splits these into
    # separate entries with `is_variant` / `variant_index` progression.
    # Normalize the three offenders.
    (
        "leprohon-32.01",
        "birth_names",
        [
            {"transliteration": "ꜣlksndrs", "anglicised": "aleksendres", "translation": "Alexander", "variant_index": 1, "is_variant": False, "attested_in": [], "source_note": None},
            {"transliteration": "ꜣlksindrs", "anglicised": "aleksindres", "translation": "Alexander", "variant_index": 2, "is_variant": True, "attested_in": [], "source_note": "Phonetic variant of the Birth name."},
        ],
        "Split slash-separated Birth name variants into separate entries "
        "(schema convention established in Ptolemy XV Caesarion). "
        "Gemini Code Assist PR #99 medium finding.",
    ),
    (
        "leprohon-32.03",
        "birth_names",
        [
            {"transliteration": "ꜣlksndrs", "anglicised": "aleksendres", "translation": "Alexander", "variant_index": 1, "is_variant": False, "attested_in": [], "source_note": None},
            {"transliteration": "ꜣlksindrs", "anglicised": "aleksindres", "translation": "Alexander", "variant_index": 2, "is_variant": True, "attested_in": [], "source_note": "Phonetic variant of the Birth name."},
        ],
        "Split slash-separated Birth name variants into separate entries. "
        "Gemini Code Assist PR #99 medium finding.",
    ),
    (
        "leprohon-33.05a",
        "birth_names",
        [
            {"transliteration": "ḳlw-pꜣ-trꜣ", "anglicised": "qlu-pa-tra", "translation": "Cleopatra", "variant_index": 1, "is_variant": False, "attested_in": [], "source_note": None},
            {"transliteration": "ḳlꜣw-pꜣ-drꜣ", "anglicised": "qliu-pa-dra", "translation": "Cleopatra", "variant_index": 2, "is_variant": True, "attested_in": [], "source_note": "Phonetic variant of the Birth name."},
        ],
        "Split slash-separated Birth name variants into separate entries. "
        "Gemini Code Assist PR #99 medium finding.",
    ),
    # Gemini Code Assist PR #99 medium-priority finding: five chunk-14
    # rows put row-level "none known/attested" narrative metadata into
    # an individual name-entry's `source_note`, which misuses the field
    # (source_note is for scholarly footnote text specific to the name
    # entry, not a row-level description of which OTHER name types are
    # absent). The empty name-list itself is the canonical "none known"
    # semantic — the narrative is redundant at best, schema-wrong at
    # worst. Strip the redundant narrative from these five rows.
    #
    # An identical pattern exists on leprohon-27.02 and leprohon-29.02
    # (chunk 13) — tracked as a follow-up sweep; the proper long-term
    # fix (adding a top-level `notes` field) is a schema design that
    # belongs in its own PR. This correction addresses only the 5
    # rows introduced in chunk 14, per constitutional rule 12
    # ("existing violations do not justify new ones").
    # scope-accountability-enforcer review 2026-04-21 PR #99.
    (
        "leprohon-32.01",
        "throne_names.0.source_note",
        None,
        "Strip row-level `Two Ladies and Golden Horus names: none known.` "
        "narrative from individual name-entry source_note. Empty name-lists "
        "are the canonical absence semantic. Gemini PR #99 medium.",
    ),
    (
        "leprohon-33.01",
        "throne_names.0.source_note",
        None,
        "Strip row-level `Golden Horus name: none known.` narrative. "
        "Gemini PR #99 medium.",
    ),
    (
        "leprohon-33.12",
        "birth_names.0.source_note",
        "Gauthier 1916, 389–91; von Beckerath 1999, 244–45.",
        "Strip trailing `Horus, Two Ladies, Golden Horus, and Throne names: "
        "none attested.` narrative; preserve the bibliographic chain. "
        "Gemini PR #99 medium.",
    ),
    (
        "leprohon-33.14",
        "birth_names.0.source_note",
        None,
        "Strip row-level `Two Ladies, Golden Horus, and Throne names: "
        "none attested.` narrative. Gemini PR #99 medium.",
    ),
    (
        "leprohon-33.17",
        "throne_names.0.source_note",
        None,
        "Strip row-level `Two Ladies and Golden Horus names: none attested.` "
        "narrative. Gemini PR #99 medium.",
    ),
    # Egyptologist-reviewer 2026-04-21: the Alexander II/IV row's Horus
    # source_note was carrying pipeline-internal denoising commentary
    # (`Leprohon's chapter preamble names this king 'Alexander II'; the
    # SMALLCAP headword in the pypdf transcription reads 'ALEXANDER II/IV'
    # (denoised from 'a l EXan DEr  ii /i V')`). source_note is for
    # Leprohon's own scholarly footnote text, not pipeline meta-commentary
    # — trim to just the bibliographic chain. The slashed-display-name
    # decision is documented in the chunk log of transcribe.md instead.
    (
        "leprohon-32.03",
        "horus_names.0.source_note",
        "Gauthier 1916, 207–11; von Beckerath 1999, 232–33.",
        "Trim pipeline-internal denoising commentary out of source_note "
        "(belongs in transcribe.md chunk log, not the per-row scholarly "
        "footnote field). Egyptologist-reviewer P2.",
    ),
]

# Issue #174 fix (PR for that). The 6 row-level prose notes that agent-b
# emitted on Late-Period rows but `merge.py` majority-voted to None
# because the other two agents didn't extract them. Restored verbatim
# from `raw/agent-b-late-period.jsonl` per CLAUDE.md rule 6 (data is
# sacred — agent-b's reading of these rows is part of the authority
# extract; the silent-loss-on-tie failure had no documented rule
# backing it).
#
# Three of the six prose strings are SHARED across multiple kings
# because Leprohon's printed footnote covers the whole grouping
# ("Kings X, Y, and Z are not known from Egyptian hieroglyphic texts.").
# Agent-b correctly emitted the same string on each affected king's
# row.
NOTES_RESTORATIONS: list[tuple[str, str, object, str]] = [
    (
        "leprohon-27.05",
        "notes",
        "Kings Xerxes II, Darius II, and Artaxerxes II are not known from Egyptian hieroglyphic texts.",
        "Issue #174: restore agent-b prose lost to majority-vote on tie. "
        "Source: raw/agent-b-late-period.jsonl.",
    ),
    (
        "leprohon-27.06",
        "notes",
        "Kings Xerxes II, Darius II, and Artaxerxes II are not known from Egyptian hieroglyphic texts.",
        "Issue #174: restore agent-b prose lost to majority-vote on tie. "
        "Source: raw/agent-b-late-period.jsonl.",
    ),
    (
        "leprohon-27.07",
        "notes",
        "Kings Xerxes II, Darius II, and Artaxerxes II are not known from Egyptian hieroglyphic texts.",
        "Issue #174: restore agent-b prose lost to majority-vote on tie. "
        "Source: raw/agent-b-late-period.jsonl.",
    ),
    (
        "leprohon-29.04",
        "notes",
        "King Nepherites II is not known from hieroglyphic sources.",
        "Issue #174: restore agent-b prose lost to majority-vote on tie. "
        "Source: raw/agent-b-late-period.jsonl. Display name in this row "
        "is `Nefaarudu II`; agent-b wrote `Nepherites II` in the prose "
        "(both are Leprohon-printed forms — Nefaarud is the Egyptian "
        "transcription, Nepherites the Greek). Preserved verbatim.",
    ),
    (
        "leprohon-31.01",
        "notes",
        "Kings Artaxerxes III and Arses are not known from hieroglyphic sources.",
        "Issue #174: restore agent-b prose lost to majority-vote on tie. "
        "Source: raw/agent-b-late-period.jsonl.",
    ),
    (
        "leprohon-31.02",
        "notes",
        "Kings Artaxerxes III and Arses are not known from hieroglyphic sources.",
        "Issue #174: restore agent-b prose lost to majority-vote on tie. "
        "Source: raw/agent-b-late-period.jsonl.",
    ),
]


SPOT_CORRECTIONS: list[tuple[str, str, object, str]] = [
    *EARLY_DYNASTIC_CORRECTIONS,
    *FIP_CORRECTIONS,
    *MK_CORRECTIONS,
    *DYN13_CORRECTIONS,
    *DYN13A14_CORRECTIONS,
    *DYN18_CORRECTIONS,
    *DYN19_CORRECTIONS,
    *DYN20_CORRECTIONS,
    *TIP_EARLY_CORRECTIONS,
    *TIP_LATE_CORRECTIONS,
    *MACEDONIAN_PTOLEMAIC_CORRECTIONS,
    *NOTES_RESTORATIONS,
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


def backfill_notes(rows: list[dict]) -> list[str]:
    """Ensure every row has the `notes` top-level field, defaulting `None`.

    Issue #174 fix (PR for that). Pre-fix: only 6/395 rows had the
    `notes` key, all with value `None`. The 6 rows are agent-b-emitted
    Late-Period rows where the agent recorded a row-level prose note
    ("Kings Xerxes II, Darius II, and Artaxerxes II are not known from
    Egyptian hieroglyphic texts.") that the other two agents did not
    extract — `merge.py`'s majority-vote on `notes` produced `None`,
    and the prose was silently lost from `reconciled.jsonl` (it still
    lives in `raw/agent-b-late-period.jsonl`).

    Two-part fix:
    1. This backfill — every row now carries `notes: <str|None>` so the
       schema shape is uniform across all 395 rows.
    2. `NOTES_RESTORATIONS` (defined above) — restore the 6 lost
       prose values from agent-b's extraction.

    Constitutional rule 4 (single source of truth) + rule 6 (data is
    sacred): the `notes` prose is part of the authority extract; the
    earlier majority-vote-to-None failure had no documented rule
    backing it (just "two agents didn't extract" — silent ambiguity
    resolution).
    """
    log_lines: list[str] = []
    for row in rows:
        if "notes" not in row:
            row["notes"] = None
            log_lines.append(
                f"  {row['leprohon_id']}: backfilled notes=None"
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
    # `backfill_notes` runs before SPOT_CORRECTIONS for Rule-4 schema
    # uniformity: every row has the `notes` key with `None` default
    # BEFORE `NOTES_RESTORATIONS` overrides 6 of them. Without the
    # backfill, `_set_by_path` would still work (top-level dict
    # assignment creates the key), but the other 389 rows would carry
    # no `notes` key at all — schema inhomogeneity, the exact bug
    # issue #174 fixes. Backfill order vs the other backfill_* passes
    # is independent (they touch disjoint fields).
    log_lines.extend(backfill_notes(rows))
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
