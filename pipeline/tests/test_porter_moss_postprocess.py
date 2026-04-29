"""Unit tests for Porter-Moss Vol I chunk-file post-processing.

The post-processor moves Egyptian-glyph normalisation from "the prompt asks
each agent to apply it" to "applied by code, deterministic". The tests below
cover each of the four phases plus idempotence and the bidirectional digit
hazard (catalog numbers like ``5I109`` and years like ``I922`` must NOT be
rewritten by the king-name-anchored Roman-numeral fix).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_PP_PATH = (
    Path(__file__).parent.parent
    / "pipeline"
    / "authority"
    / "sources"
    / "porter-moss-theban-necropolis"
    / "postprocess.py"
)
_spec = importlib.util.spec_from_file_location("pm_postprocess", _PP_PATH)
pp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pp)


# === Phase 1: substring fixes ===============================================


def test_capital_h_underdot_at_word_start() -> None:
    """``J:I`` and ``I:I`` are the publisher's substitutes for capital ``Ḥ``
    at word start (the OCR varies between runs; both occur in the same
    chunk for the same word). Global replacement is safe because neither
    bigram occurs in normal English prose in this source."""
    assert pp.process_chunk("J:Iatshepsut") == "Ḥatshepsut"
    assert pp.process_chunk("I:Iatshepsut") == "Ḥatshepsut"
    assert pp.process_chunk("I:Iarakhti") == "Ḥarakhti"
    assert pp.process_chunk("I:IATSHEPSUT") == "ḤATSHEPSUT"
    assert pp.process_chunk("Sarcophagus of J:Iatshepsut as King") == (
        "Sarcophagus of Ḥatshepsut as King"
    )


def test_capital_h_underdot_rare_ij_variant() -> None:
    """``I:J`` is a rare third variant for capital ``Ḥ`` (3 occurrences in
    chunk 3 only). Same glyph, different OCR run."""
    assert pp.process_chunk("I:Jarakhti") == "Ḥarakhti"
    assert pp.process_chunk("I:Jarsiesi") == "Ḥarsiesi"


def test_capital_h_underdot_in_all_caps_heading() -> None:
    """``I;I`` is the same glyph in all-caps tomb headings."""
    assert pp.process_chunk("MERNEPTAI;I-SIPTAI;I") == "MERNEPTAḤ-SIPTAḤ"
    assert pp.process_chunk("MAI;IIRPER") == "MAḤIRPER"
    assert pp.process_chunk("47· MERNEPTAI;I-SIPTAI;I") == "47· MERNEPTAḤ-SIPTAḤ"


def test_capital_h_underdot_mid_word() -> None:
    """``l:I`` is the same glyph mid-word (after a hyphen, in
    ``Re<-l:Iarakhti``). The ayin and the underdot-H both fix in the same
    pass."""
    assert pp.process_chunk("Re<-l:Iarakhti") == "Reʿ-Ḥarakhti"


def test_sit_dhout_special_case() -> None:
    """QV47's mother-of field reads ``Sit-ḍḥout`` in PM; the publisher OCR
    mangles it to ``Sit-gQ.out``. Single-token whitelist replacement."""
    assert pp.process_chunk(
        "daughter of Seḳenenreʿ-Taʿa and Sit-gQ.out"
    ) == "daughter of Seḳenenreʿ-Taʿa and Sit-ḍḥout"


def test_first_ed_bracket_cross_reference() -> None:
    """``[1st ed. N]`` cross-references render as ``[Ist ed.``, ``[rst ed.``,
    or ``[xst ed.`` arbitrarily. All three normalise."""
    assert pp.process_chunk("[Ist ed. 24]") == "[1st ed. 24]"
    assert pp.process_chunk("[rst ed. 5]") == "[1st ed. 5]"
    assert pp.process_chunk("[xst ed. 3]") == "[1st ed. 3]"


# === Phase 2: inline ayin ===================================================


def test_inline_ayin_between_letters() -> None:
    """``<`` adjacent to a letter is the publisher's ayin. Replaces in all
    common positions: between letters, before hyphen, before punctuation."""
    assert pp.process_chunk("Re<-J:Iarakhti") == "Reʿ-Ḥarakhti"
    assert pp.process_chunk("Ma<et") == "Maʿet"
    assert pp.process_chunk("Kha<emweset") == "Khaʿemweset"
    assert pp.process_chunk("Bent<anta") == "Bentʿanta"
    assert pp.process_chunk("Litany of Re<.") == "Litany of Reʿ."
    assert pp.process_chunk("offering wine to Re<,") == "offering wine to Reʿ,"


def test_inline_ayin_does_not_fire_without_left_letter() -> None:
    """A ``<`` not preceded by a letter is not an ayin; left untouched.
    (E.g. an XML-like tag ``</thing>`` would NOT be in this source's prose,
    but the anchor still protects against it.)"""
    assert pp.process_chunk("a < b") == "a < b"
    assert pp.process_chunk("</thing>") == "</thing>"


def test_inline_ayin_fires_after_phase1_underdot_h() -> None:
    """Phase-2 lookbehind admits Phase-1 output ``Ḥ`` / ``ḥ`` (Unicode word
    class) so a ``<`` immediately after the substituted underdot-H also
    converts to ayin. Defends against the latent class where chunk text
    placed `<` adjacent to the J:I/I:I/I;I/l:I bigram."""
    # Synthetic: ``J:I<arakhti`` → Phase 1 → ``Ḥ<arakhti`` → Phase 2 →
    # ``Ḥʿarakhti`` (a literal sequence the agent could read).
    assert pp.process_chunk("J:I<arakhti") == "Ḥʿarakhti"


def test_inline_ayin_simple_token() -> None:
    """Smallest possible ayin token: bare ``Re<`` between word boundaries."""
    assert pp.process_chunk("Re<") == "Reʿ"


def test_word_initial_ayin() -> None:
    """``<`` at the start of an Egyptian transliteration token (`<Ahhotp`,
    `<Ankhef`, `<Aqmosi`) is also an ayin glyph. Lookahead anchor admits
    word-initial position. All chunk-text occurrences of ``<[A-Za-z]`` are
    Egyptian transliteration — no HTML/math/citation false positives."""
    assert pp.process_chunk("<Ahhotp") == "ʿAhhotp"
    assert pp.process_chunk("<Ankhefenamiin") == "ʿAnkhefenamiin"
    assert pp.process_chunk("<Aqmosi") == "ʿAqmosi"


def test_word_initial_ayin_admits_phase1_underdot() -> None:
    """The lookahead is symmetric with the lookbehind — both admit Phase-1
    substitution products (`Ḥ`/`ḥ`/`ḍ`/`Ḍ`) AND chunk-text transliteration
    consonants (`ḳ`/`Ḳ`) so that a future chunk shape with ``<``
    immediately before an underdot consonant (e.g. a hypothetical
    ``<Ḥtp`` if PM ever transliterates the king's name with leading
    ayin + underdot-H, or ``<ḳ...``) does not silently survive
    untranslated. Synthetic tests cover both Phase-1-product and
    chunk-text-content classes."""
    assert pp.process_chunk("<Ḥtp") == "ʿḤtp"
    assert pp.process_chunk("<ḥtp") == "ʿḥtp"
    # Chunk-text-content: `Seḳenenreʿ-Taʿa` style — ḳ adjacency.
    assert pp.process_chunk("Seḳ<") == "Seḳʿ"
    assert pp.process_chunk("<ḳ") == "ʿḳ"
    # Capital underdot-D variant (Ḍ): rare but admits for symmetry.
    assert pp.process_chunk("Ḍ<") == "Ḍʿ"


def test_ayin_does_not_fire_on_digit_lookbehind() -> None:
    """Lookbehind explicitly excludes digits — chunk text contains
    digit-cluster citation noise like ``pp. 22<)-47`` where ``<`` is a
    misread digit, not an ayin. Firing there would corrupt page numbers."""
    assert pp.process_chunk("pp. 22<)-47") == "pp. 22<)-47"
    assert pp.process_chunk("(195<)") == "(195<)"


# === Phase 3: whitelisted token-exact rewrites ==============================


def test_whitelisted_egyptian_c_rewrite() -> None:
    """``c`` as the alternate ayin rendering — rewritten only for the
    closed Egyptian-name whitelist, never for English words."""
    assert pp.process_chunk("Smenkhkarec") == "Smenkhkareʿ"
    assert pp.process_chunk("Menkheperrec") == "Menkheperreʿ"
    assert pp.process_chunk("Litany of Rec.") == "Litany of Reʿ."
    assert pp.process_chunk("Takhact offering") == "Takhaʿt offering"


def test_english_c_words_survive() -> None:
    """English words ending in ``c`` must NOT be rewritten by the Egyptian-
    name ayin rule. This is the central regression test for the post-
    processor's context-sensitivity."""
    survivors = [
        "Cairo",
        "Asiatic",
        "Canopic",
        "Demotic",
        "Hieratic",
        "Hieroglyphic",
        "Mimic",
        "Photographic",
        "Cryptographic",
        "Ceramic",
        "Dec. 9, 1922",
        "Cmc. OR. INST. photos.",
    ]
    for word in survivors:
        assert pp.process_chunk(word) == word, (
            f"English word {word!r} was modified by the post-processor"
        )


# === Phase 4: king-name-anchored Roman numerals =============================


def test_roman_numeral_after_king_name() -> None:
    """Roman regnal numerals after a recognized king name normalise. The
    publisher OCR renders ``III`` as ``Ill`` (cap-I + lowercase-l + lower-l)
    and ``II`` as ``Il`` or ``11`` arbitrarily."""
    assert pp.process_chunk("Amenophis Ill") == "Amenophis III"
    assert pp.process_chunk("Ramesses Ill") == "Ramesses III"
    assert pp.process_chunk("Sethos II") == "Sethos II"  # already correct
    assert pp.process_chunk("Sethos 11") == "Sethos II"
    assert pp.process_chunk("Tuthmosis Il") == "Tuthmosis II"


def test_roman_numeral_does_not_touch_catalog_numbers() -> None:
    """Bidirectional ``I``↔``1``↔``l`` confusion: the SAME character class
    that produces ``Ill`` for ``III`` also produces ``5I109`` for ``51109``
    and ``I922`` for ``1922``. The Roman-numeral fix is king-name-anchored
    so these stay alone."""
    assert pp.process_chunk("Cairo Mus. Ent. 5I109.") == (
        "Cairo Mus. Ent. 5I109."
    )
    assert pp.process_chunk("Dec. 9, I922") == "Dec. 9, I922"
    assert pp.process_chunk("BLACKMAN in Discovery, iv (I923)") == (
        "BLACKMAN in Discovery, iv (I923)"
    )
    # `Il` standalone (not after a king name) stays untouched.
    assert pp.process_chunk("plate Il [3]") == "plate Il [3]"


def test_roman_numeral_through_multiple_kings_in_one_line() -> None:
    """A line with multiple king-numeral pairs fixes both."""
    assert pp.process_chunk("Vases of Ramesses 11 and Sethos II") == (
        "Vases of Ramesses II and Sethos II"
    )
    assert pp.process_chunk("Amenophis Ill and Tuthmosis Il") == (
        "Amenophis III and Tuthmosis II"
    )


def test_roman_numeral_all_caps_pm_headword() -> None:
    """PM headwords are typeset in all caps; the publisher OCR renders the
    Roman three as multi-token ``I Il`` (cap-I + space + cap-I + lower-l).
    The rule must fire on the all-caps form too. KV22 is the canonical
    case — `22. AMENOPHIS I Il` → `22. AMENOPHIS III`."""
    assert pp.process_chunk("22. AMENOPHIS I Il") == "22. AMENOPHIS III"
    assert pp.process_chunk("AMENOPHIS Ill") == "AMENOPHIS III"
    assert pp.process_chunk("RAMESSES 11") == "RAMESSES II"
    assert pp.process_chunk("TUTHMOSIS Il") == "TUTHMOSIS II"


def test_empty_input_passes_through() -> None:
    """Empty string input yields empty string output (degenerate base case)."""
    assert pp.process_chunk("") == ""


# === Idempotence ============================================================


def test_idempotent_on_clean_input() -> None:
    """Running on already-fixed text is a no-op."""
    fixed = "Ḥatshepsut, Reʿ-Ḥarakhti, Smenkhkareʿ, Amenophis III"
    assert pp.process_chunk(fixed) == fixed


def test_idempotent_on_dirty_input() -> None:
    """Running twice equals running once on a representative dirty input."""
    dirty = (
        "47· MERNEPTAI;I-SIPTAI;I [Ist ed. 24]\n"
        "(Re<-l:Iarakhti, Litany of Re<. Ramesses Ill, Smenkhkarec)\n"
        "Cairo Mus. Ent. 5I109. Dec. 9, I922.\n"
        "Sit-gQ.out (J:Iatshepsut)\n"
    )
    once = pp.process_chunk(dirty)
    twice = pp.process_chunk(once)
    assert once == twice


# === End-to-end smoke test on a representative dirty paragraph ==============


def test_representative_paragraph_round_trip() -> None:
    """Combine the most common noise classes in a single paragraph and
    assert the expected canonical Unicode output."""
    dirty = (
        "47· MERNEPTAI;I-SIPTAI;I, Plan, p. 558.\n"
        "King receiving life from Re<-l:Iarakhti. Litany of Re<.\n"
        "Vase of Ramesses Ill, Sethos 11, in Cairo Mus. Ent. 39712.\n"
        "Smenkhkarec attribution, [Ist ed. 24].\n"
    )
    expected = (
        "47· MERNEPTAḤ-SIPTAḤ, Plan, p. 558.\n"
        "King receiving life from Reʿ-Ḥarakhti. Litany of Reʿ.\n"
        "Vase of Ramesses III, Sethos II, in Cairo Mus. Ent. 39712.\n"
        "Smenkhkareʿ attribution, [1st ed. 24].\n"
    )
    assert pp.process_chunk(dirty) == expected
