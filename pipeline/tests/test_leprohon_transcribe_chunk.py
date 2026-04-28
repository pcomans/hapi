"""Unit tests for Leprohon transcribe_chunk.py page-processing helpers.

The script wraps pypdf text-layer extraction, applies MdC normalisation, and
post-processes each page to (a) strip EBSCO watermark + running headers,
(b) detect & merge multi-line footnote bodies, (c) annotate inline footnote
anchors. These tests exercise the page-level post-processing on hand-rolled
line lists modelled on real chunk-7 (SIP) output.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_TRANSCRIBE_PY = (
    Path(__file__).parent.parent
    / "pipeline"
    / "authority"
    / "sources"
    / "leprohon-2013-titulary"
    / "transcribe_chunk.py"
)
_spec = importlib.util.spec_from_file_location("leprohon_transcribe", _TRANSCRIBE_PY)
tc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tc)


def test_strips_ebsco_watermark_three_lines() -> None:
    page = [
        "1. s Em QEn 4",
        "1. For discussions of these, see Redford 1970 and 1997.",
        "EBSCO Publishing : eBook Collection (EBSCOhost) - printed on 3/30/2017 9:11 PM via TEXAS STATE UNIV",
        "AN: 663423 ; Leprohon, Ronald J., Doxey, Denise M..; The Great Name : Ancient Egyptian Royal Titulary",
        "Account: s8329666",
    ]
    body, footnotes = tc._split_page(page)
    assert body == ["1. s Em QEn 4"]
    assert footnotes == [(1, "For discussions of these, see Redford 1970 and 1997.")]


def test_strips_leading_running_header_bare_page_number() -> None:
    page = [
        "81",
        "VI",
        "s Econ D i nt Erm EDiat E PErio D",
        "Dynasty  15 (1663–1555 b .c .E.)",
    ]
    body, footnotes = tc._split_page(page)
    assert body == [
        "s Econ D i nt Erm EDiat E PErio D",
        "Dynasty  15 (1663–1555 b .c .E.)",
    ]
    assert footnotes == []


def test_strips_running_header_caps_then_pagenum() -> None:
    page = [
        " SECO ND INTERMEDIATE PERIOD  83",
        "Two Ladies: /// ḏḥwty (/// djehuty), /// Thoth",
    ]
    body, _ = tc._split_page(page)
    assert body == ["Two Ladies: /// ḏḥwty (/// djehuty), /// Thoth"]


def test_strips_running_header_pagenum_then_caps() -> None:
    page = [
        "82 THE GR EAT NAME",
        "2. a PEr -anati 6",
    ]
    body, _ = tc._split_page(page)
    assert body == ["2. a PEr -anati 6"]


def test_merges_multi_line_footnote_bodies() -> None:
    page = [
        "Body line.",
        "1. For discussions of these, see Redford 1970 and 1997.",
        "2. For an e",
        "asily accessible description of the site, see Bietak 1999.",
        "3. Davi",
        "es 2003.",
    ]
    body, footnotes = tc._split_page(page)
    assert body == ["Body line."]
    assert footnotes == [
        (1, "For discussions of these, see Redford 1970 and 1997."),
        (2, "For an easily accessible description of the site, see Bietak 1999."),
        (3, "Davies 2003."),
    ]


def test_merges_split_footnote_number_pre_pass_shape_a() -> None:
    """fn.34 in chunk 7 splits as `34\\n. Turi\\nn 11,9 ...` — number alone,
    period+body on next line."""
    page = [
        "Body line for known-fns prose.",
        "33. Ibid.",
        "34",
        ". Turi",
        "n 11,9 (= KRI II, 843:1); von Beckerath 1999, 128–29.",
    ]
    body, footnotes = tc._split_page(page)
    assert body == ["Body line for known-fns prose."]
    assert footnotes == [
        (33, "Ibid."),
        (34, "Turin 11,9 (= KRI II, 843:1); von Beckerath 1999, 128–29."),
    ]


def test_merges_split_footnote_number_pre_pass_shape_b() -> None:
    """fn.56/62 in chunk old-kingdom split as `56.\\n The na\\nme...` —
    number+period alone, body on next line."""
    page = [
        "Body line for known-fns prose.",
        "55. The name nfr.f ra is a contemporary reinterpretation; see Verner.",
        "56.",
        " The na",
        "me may simply be another diminutive; see Scheele-Schweitzer 2007.",
    ]
    body, footnotes = tc._split_page(page)
    assert body == ["Body line for known-fns prose."]
    assert footnotes == [
        (55, "The name nfr.f ra is a contemporary reinterpretation; see Verner."),
        (56, "The name may simply be another diminutive; see Scheele-Schweitzer 2007."),
    ]


def test_merges_split_three_digit_footnote_number_shape_c() -> None:
    """fn 122 / fn 167 split as `12\\n2. Ibid` and `16\\n7. Lit. ...`."""
    page = [
        "Body line for known-fns prose.",
        "121. Ibid.",
        "12",
        "2. Ibid",
        "., 106–7.",
    ]
    body, footnotes = tc._split_page(page)
    assert body == ["Body line for known-fns prose."]
    assert footnotes == [
        (121, "Ibid."),
        (122, "Ibid., 106–7."),
    ]


def test_shape_c_does_not_merge_body_anchor_followed_by_headword() -> None:
    """`42` (body anchor) + `1. KHa S EKHEm` (king headword) must NOT merge
    to `421. KHa...`. The 100-250 range cap rejects the merge."""
    # Combined number is `421` — exceeds 250 cap, so no merge happens.
    page = [
        "Throne: hr-skht.f (her sekhet.ef ), Horus has felled him42",
        "42",
        "1. KHa S EKHEm",
        "Horus: ḥtp nbwy (hetep nebuy).",
    ]
    body, footnotes = tc._split_page(page)
    # Page has only headword content; no real footnotes detected.
    assert footnotes == []
    # Body preserved without false-merge of `42` + `1.`.
    assert "1. KHa S EKHEm" in body
    assert "42" in body


def test_excludes_page_line_citation_tail_from_footnote_starts() -> None:
    """`KRI IV, 31:1–\\n13. ` — `13.` is a citation tail (the wrapped end
    of `31:1–13.`), not a start of fn 13. The en-dash on the previous line
    excludes the match."""
    page = [
        "Body line.",
        "124. Found at the site of Qaha; for the text, see KRI IV, 31:1–",
        "13. ",
        "One of the faces of the obelisk had been cut away; see Daressy 1920.",
        "125. Or “as.”",
        "126. For the texts, see KRI IV, 54–55.",
    ]
    body, footnotes = tc._split_page(page)
    assert body == ["Body line."]
    nums = [n for n, _ in footnotes]
    assert nums == [124, 125, 126]
    # fn 124's body merges across the wrapped `1:1–\n13.` boundary cleanly.
    assert "31:1–13." in dict(footnotes)[124]


def test_does_not_misidentify_four_digit_year_as_footnote_start() -> None:
    """A footnote body line starting with `1985. The reading...` (year +
    period + sentence start) must not be mis-detected as fn-1985 start."""
    page = [
        "Body prose with some discussion.",
        "55. The name nfr.f ra is a contemporary reinterpretation; see Verner",
        "1985. The reading Renefer/Reneferef, with a meaning of Re is perfect.",
        "56. The name may simply be another diminutive; see Scheele-Schweitzer 2007.",
    ]
    body, footnotes = tc._split_page(page)
    # Both fn 55 and fn 56 should be detected; fn 1985 must NOT appear.
    nums = {n for n, _ in footnotes}
    assert 1985 not in nums
    assert 55 in nums
    assert 56 in nums


def test_excludes_king_headwords_from_footnote_block() -> None:
    """Page with king headwords in body + footnote block at end.

    The walk-back-monotonic detector starts at the last `\\d+. ` and
    decrements; the king-headword `\\d+. ` interleave breaks the sequence
    so headwords stay in body.
    """
    page = [
        "2. a PEr -anati 6",
        "Title and name: HqA xAswt apr-an-ti.",
        "3. s EKEr -HEr 8",
        "Two Ladies: wꜥf pḏwt.",
        "6. Von Beckerath 1999, 116–17.",
        "7. For a discussion of the name, see T. Schneider 1998, 133.",
        "8. Von Beckerath 1999, 116–17.",
    ]
    body, footnotes = tc._split_page(page)
    assert "2. a PEr -anati 6" in body
    assert "3. s EKEr -HEr 8" in body
    assert {n for n, _ in footnotes} == {6, 7, 8}


def test_no_footnotes_page_with_only_headwords() -> None:
    """Prose safeguard: page with only king-headword `\\d+. ` lines must
    not have headwords misidentified as footnotes."""
    page = [
        "1. KHa S EKHEm",
        "Horus: ḥtp nbwy (hetep nebuy).",
        "2. n Eb Ka",
        "Horus: bꜣ-nb (ba-neb).",
    ]
    body, footnotes = tc._split_page(page)
    assert footnotes == []
    assert body == page


def test_annotates_standalone_digit_line_as_footnote_anchor() -> None:
    body = ["Throne: sꜥnḫ.n rꜥ (sankh.en ra), The one whom Re has sustained", "27"]
    out = tc._annotate_anchors(body, known_fns={27})
    assert out == [
        "Throne: sꜥnḫ.n rꜥ (sankh.en ra), The one whom Re has sustained",
        '<sup data-fn="27">27</sup>',
    ]


def test_annotates_end_of_line_digit_glued_to_word() -> None:
    body = ["Horus: hr nṯrw (?) (her netjeru), The one who has pleased the gods26"]
    out = tc._annotate_anchors(body, known_fns={26})
    assert out == [
        'Horus: hr nṯrw (?) (her netjeru), The one who has pleased the gods<sup data-fn="26">26</sup>'
    ]


def test_annotates_continuation_line_with_leading_anchor() -> None:
    body = [
        "texts,",
        "1 has been revised in the light of recent archaeological work.",
    ]
    out = tc._annotate_anchors(body, known_fns={1})
    assert out == [
        "texts,",
        '<sup data-fn="1">1</sup> has been revised in the light of recent archaeological work.',
    ]


def test_annotates_continuation_with_uppercase_sentence_start() -> None:
    """Anchor at the start of a wrap-line followed by capital-letter sentence."""
    body = ["2 In the south, the ruler of Upper Nubia took advantage of the"]
    out = tc._annotate_anchors(body, known_fns={2})
    assert out == [
        '<sup data-fn="2">2</sup> In the south, the ruler of Upper Nubia took advantage of the'
    ]


def test_annotates_mid_line_anchor_after_sentence_end() -> None:
    """`Lands. 16 King` — digit between period+space and space+capital."""
    body = ['"the Two Lands." Thus they claimed. 16 King Sekhem-']
    out = tc._annotate_anchors(body, known_fns={16})
    assert out == [
        '"the Two Lands." Thus they claimed. <sup data-fn="16">16</sup> King Sekhem-'
    ]


def test_annotates_mid_line_anchor_after_comma() -> None:
    """`today, 14 Ryholt` — digit between comma+space and space+capital."""
    body = ["today, 14 Ryholt has reconstructed this group"]
    out = tc._annotate_anchors(body, known_fns={14})
    assert out == [
        'today, <sup data-fn="14">14</sup> Ryholt has reconstructed this group'
    ]


def test_does_not_misannotate_dynasty_number() -> None:
    """`Dynasty 16 (1663–1555...)` — digit not preceded by punctuation+space."""
    body = ["Dynasty 16 (1663–1555 b .c .E.)"]
    out = tc._annotate_anchors(body, known_fns={16})
    assert out == ["Dynasty 16 (1663–1555 b .c .E.)"]


def test_does_not_misidentify_king_headword_as_anchor() -> None:
    """`2. a PEr -anati 6` is a king headword, NOT a footnote anchor — the
    `.` after the digit must prevent case-3 wrapping."""
    body = ["2. a PEr -anati 6"]
    # 2 IS in known_fns (e.g. fn.2 also appears on this page) but the
    # `.` discriminator prevents case-3 wrapping.
    out = tc._annotate_anchors(body, known_fns={2, 6})
    assert out == ["2. a PEr -anati <sup data-fn=\"6\">6</sup>"]


def test_does_not_annotate_year_range_endpoints() -> None:
    """Year ranges like `1999, 116–17` end in a digit but the en-dash before
    `17` excludes them from anchor wrapping."""
    body = ["Beckerath 1999, 116–17"]
    out = tc._annotate_anchors(body, known_fns={17})
    assert out == ["Beckerath 1999, 116–17"]


def test_does_not_annotate_unknown_footnote_numbers() -> None:
    body = ["Some line ending in 99"]
    out = tc._annotate_anchors(body, known_fns={1, 2, 3})
    assert out == ["Some line ending in 99"]


def test_full_page_processing_emits_structured_block() -> None:
    raw = [
        "81",
        "VI",
        "s Econ D i nt Erm EDiat E PErio D",
        "Dynasty  15 (1663–1555 b .c .E.)",
        "1. s Em QEn 4",
        'Title and name: HqA xAswt s-m-q-n ( heqa khasut semqen ), The Ruler of Foreign Lands Semqen ("He is my gift")5',
        "1. For discussions of these, see Redford 1970 and 1997.",
        "4. Von Be",
        "ckerath 1999, 116–17.",
        "5. For t",
        "he rendering, see T. Schneider 1998, 137–38.",
        "EBSCO Publishing : eBook Collection (EBSCOhost) - printed on 3/30/2017 9:11 PM via TEXAS STATE UNIV",
        "AN: 663423 ; Leprohon, Ronald J., Doxey, Denise M..; The Great Name : Ancient Egyptian Royal Titulary",
        "Account: s8329666",
    ]
    out = tc._process_page(102, raw)
    assert out.startswith("<!-- physical page 102 -->\n")
    # Header + footnote-block separator both present.
    assert "<!-- footnotes -->" in out
    # Smallcap chapter title preserved (NOT stripped as a header).
    assert "s Econ D i nt Erm EDiat E PErio D" in out
    # EBSCO + bare-page-number 81 stripped.
    assert "EBSCO Publishing" not in out
    assert "\n81\n" not in out
    # Footnote 5 anchor is wrapped in body line ending with `Gift")5`.
    assert 'Semqen ("He is my gift")<sup data-fn="5">5</sup>' in out
    # Footnote bodies merged + emitted as <fn> elements.
    assert '<fn id="4">Von Beckerath 1999, 116–17.</fn>' in out
    assert '<fn id="5">For the rendering, see T. Schneider 1998, 137–38.</fn>' in out


def test_mdc_normalisation_still_applied_inside_processed_page() -> None:
    """`_process_page` must keep applying MdC mapping to name-row lines."""
    raw = [
        "Dynasty  16",
        "1. DEDumos E i 36",
        "Horus: wAD-xaw (wadj khau), Flourishing of appearances",
        "36. Von Be",
        "ckerath 1999, 100–101.",
    ]
    out = tc._process_page(106, raw)
    # `wAD-xaw` MdC must be normalised to `wꜣḏ-ḫꜥw`.
    assert "wꜣḏ-ḫꜥw" in out
    assert "wAD-xaw" not in out
