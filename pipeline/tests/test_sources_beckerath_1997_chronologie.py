"""Structural value-assertion tests for Beckerath 1997 Chronologie source extract.

Per rule 5: every populated field on a sampled fixture row is asserted.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

SOURCE_DIR = (
    Path(__file__).parent.parent
    / "pipeline"
    / "authority"
    / "sources"
    / "beckerath-1997-chronologie"
)
JSONL = SOURCE_DIR / "reconciled.jsonl"

EDITION = "MÄS 46, von Zabern 1997"
PDF_PAGES = "105-109"

EXPECTED_PERIODS = {
    "Vorgeschichte",
    "Frühzeit",
    "Altes Reich",
    "I. Zwischenzeit",
    "Mittleres Reich",
    "II. Zwischenzeit",
    "Neues Reich",
    "III. Zwischenzeit",
    "Spätzeit",
}

EXPECTED_TITULARY_KINDS = {None, "horus_name", "prenomen", "nomen", "mixed"}


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(json.loads(line) for line in JSONL.read_text().splitlines() if line.strip())


def _row(beckerath_id: str) -> dict:
    hits = [r for r in _rows() if r["beckerath_id"] == beckerath_id]
    if len(hits) != 1:
        raise AssertionError(f"expected 1 row for {beckerath_id}, got {len(hits)}")
    return hits[0]


def test_row_count() -> None:
    """The Übersicht extracts to ~170 rows: every dynasty 0..31 named king
    plus dynasty-only marker rows for 7, 8, 9/10, 13, 14, 16, 17 (Beckerath
    gives counts not individual kings there) plus the two Dyn 21 HPA names
    from Supplement zu A's tail paragraph. The exact count is locked here so
    silent re-extraction drift is detected on CI.
    """
    assert len(_rows()) == 172, len(_rows())


def test_dynasty_coverage() -> None:
    """Every Beckerath dynasty 0..31 appears at least once, EXCEPT Dyn 10:
    Beckerath combines Dyn 9 and Dyn 10 into a single Herakleopolis row
    labelled `9./10. Dynastie` and assigns it `dynasty: 9` (the lower
    number). The combined row carries an "18 Könige" annotation but
    enumerates none of them.
    """
    dynasties = {r["dynasty"] for r in _rows()}
    expected = set(range(0, 32)) - {10}
    assert dynasties == expected, sorted(dynasties)


def test_beckerath_id_is_unique() -> None:
    ids = [r["beckerath_id"] for r in _rows()]
    assert len(ids) == len(set(ids)), "duplicate beckerath_id detected"


_BID_RE = re.compile(r"^\d{2}\.\d{2}$")


def test_beckerath_id_shape() -> None:
    """Every id matches `{dyn:02}.{NN:02}` — pure two-digit dynasty + two-digit
    sequence. Sub-lines do NOT carry a prefix; they are recorded in the
    `sub_line` field instead.
    """
    for r in _rows():
        assert _BID_RE.match(r["beckerath_id"]), r["beckerath_id"]


def test_every_row_has_complete_citation() -> None:
    """Rule 1: every row traces back to a pdf_pages range and edition."""
    for r in _rows():
        citation = r["source_citation"]
        assert citation == {"pdf_pages": PDF_PAGES, "edition": EDITION}, r


def test_period_is_one_of_nine() -> None:
    """`period` is a closed enum drawn from Beckerath's italicised section
    headings within Anhang A. Ptolemaic / Roman never appear because Beckerath
    stops at 332 BCE.
    """
    for r in _rows():
        assert r["period"] in EXPECTED_PERIODS, (r["beckerath_id"], r["period"])


def test_egyptian_titulary_kind_is_one_of_five() -> None:
    """`egyptian_titulary_kind` is null whenever `egyptian_titulary` is null,
    and otherwise one of horus_name / prenomen / nomen / mixed.
    """
    for r in _rows():
        assert r["egyptian_titulary_kind"] in EXPECTED_TITULARY_KINDS, r
        if r["egyptian_titulary"] is None:
            assert r["egyptian_titulary_kind"] is None, r


def test_no_dates_after_330_bce() -> None:
    """Beckerath's coverage ends with Alexander's conquest of Egypt in 332 BCE,
    but the book's last enumerated reign — Darius III (336/335–332/330) —
    runs to his death in 330 BCE. Beckerath uses the slash form `332/330` to
    mark the gap between Alexander's conquest of Egypt and the Persian
    empire's collapse, so `end_bce_low: -330` is the legitimate floor.
    No row may carry an endpoint later than -330.
    """
    for r in _rows():
        for field in ("start_bce_high", "start_bce_low", "end_bce_high", "end_bce_low"):
            v = r[field]
            if v is None:
                continue
            assert v <= -330, (r["beckerath_id"], field, v)


def test_dyn0_anchor_full_row() -> None:
    """The Vorgeschichte anchor: zero numeric endpoints, both approximate flags
    true, the `ungefähr 150 Jahre` note. This is the only row in the entire
    extract with all four BCE fields null.
    """
    r = _row("00.01")
    assert r["dynasty"] == 0
    assert r["sub_line"] is None
    assert r["sequence_in_dynasty"] == 1
    assert r["name"] == "0. Dynastie"
    assert r["egyptian_titulary"] is None
    assert r["egyptian_titulary_kind"] is None
    assert r["prenomen"] is None
    assert r["start_bce_high"] is None
    assert r["start_bce_low"] is None
    assert r["end_bce_high"] is None
    assert r["end_bce_low"] is None
    assert r["start_approximate"] is True
    assert r["end_approximate"] is True
    assert r["period"] == "Vorgeschichte"
    assert r["notes_from_beckerath"] == "ungefähr 150 Jahre"


def test_menes_full_row() -> None:
    """First named king. Tests the slash-pair date parsing, the `Hor Aha`
    horus_name parenthetical, and the dynasty-heading-level `etwa` propagation
    to per-row approximate flags.
    """
    r = _row("01.01")
    assert r["dynasty"] == 1
    assert r["sub_line"] is None
    assert r["sequence_in_dynasty"] == 1
    assert r["name"] == "Menes"
    assert r["egyptian_titulary"] == "Hor Aha"
    assert r["egyptian_titulary_kind"] == "horus_name"
    assert r["prenomen"] is None
    assert r["start_bce_high"] == -3032
    assert r["start_bce_low"] == -2982
    assert r["end_bce_high"] == -3000
    assert r["end_bce_low"] == -2950
    assert r["start_approximate"] is True
    assert r["end_approximate"] is True
    assert r["period"] == "Frühzeit"
    assert r["notes_from_beckerath"] is None


def test_amenophis_i_dyn18_identity_correction_locked() -> None:
    """The egyptologist-reviewer override pass corrected this row from a
    misidentified `An-jotef I.` (Hor Neb-cheper-rê) to the correct
    `Amenophis I.` (Djeser-ka-rê). Lock the corrected row so a re-merge
    can't silently re-introduce the OCR confusion.
    """
    r = _row("18.02")
    assert r["name"] == "Amenophis I."
    assert r["egyptian_titulary"] == "Djeser-ka-rê"
    assert r["egyptian_titulary_kind"] == "prenomen"
    assert r["start_bce_high"] == -1525
    assert r["end_bce_high"] == -1504
    assert r["period"] == "Neues Reich"


def test_tuthmosis_ii_accession_date_in_notes() -> None:
    """Beckerath gives Tuthmosis II's accession date as `14.8.1473`. The
    day.month.year prefix lives in `notes_from_beckerath`; the numeric BCE
    endpoint is `-1473`.
    """
    r = _row("18.04")
    assert r["name"] == "Tuthmosis II."
    assert r["start_bce_high"] == -1473
    assert r["end_bce_high"] == -1458
    assert r["notes_from_beckerath"] == "Antritt 14.8.1473"


def test_schoschenq_iii_alternative_end_in_notes() -> None:
    """Beckerath writes Schoschenq III's reign as `ca. 837–798 (785?)`. The
    `(785?)` alternative goes in `notes_from_beckerath` while the numeric
    end stays at the primary endpoint -798. `start_approximate` is true (the
    `ca.` prefix); `end_approximate` is false (no qualifier on -798 itself).
    """
    r = _row("22.06")
    assert r["name"] == "Schoschenq III."
    assert r["start_approximate"] is True
    assert r["end_approximate"] is False
    assert r["start_bce_high"] == -837
    assert r["end_bce_high"] == -798
    assert r["notes_from_beckerath"] == "alternative end 785"


def test_dyn21_hohepriester_subline_present() -> None:
    """Two HPA rows from Supplement zu A's tail paragraph carry
    `sub_line: "Hohepriester"`. They share Dyn 21 numbering with the main
    line (continuous sequence_in_dynasty).
    """
    pi = _row("21.08")
    psusennes = _row("21.09")
    assert pi["sub_line"] == "Hohepriester"
    assert pi["dynasty"] == 21
    assert pi["sequence_in_dynasty"] == 8
    assert "Pi-nodjem" in pi["name"]
    assert psusennes["sub_line"] == "Hohepriester"
    assert psusennes["dynasty"] == 21


def test_dyn22_obergaegyptische_linie_continues_sequencing() -> None:
    """Dyn 22 main + Oberägyptische Linie share one sequence_in_dynasty
    counter (continuous numbering, no restart). The first OAL king is
    22.10 Har-si-êset; numbering runs to 22.18 Ini.
    """
    har = _row("22.10")
    ini = _row("22.18")
    assert har["sub_line"] == "Oberägyptische Linie"
    assert har["sequence_in_dynasty"] == 10
    assert har["dynasty"] == 22
    assert ini["sub_line"] == "Oberägyptische Linie"
    assert ini["sequence_in_dynasty"] == 18
    assert ini["name"] == "Ini"


def test_dyn16_is_hyksos_vassals_not_a_subline_of_15() -> None:
    """The Hyksos-Vasallen are Beckerath's own Dynasty 16 (per his heading
    `16. Dynastie (Hyksos-Vasallen, gleichzeitig mit Dynastie 15)`). They
    must be encoded with `dynasty: 16`, NOT as a sub_line of Dyn 15.
    """
    dyn16 = [r for r in _rows() if r["dynasty"] == 16]
    assert len(dyn16) >= 1, "Dyn 16 (Hyksos-Vasallen) must be represented"
    for r in dyn16:
        assert r["dynasty"] == 16
        # Dyn 16 sub_line is the main line — null
        assert r["sub_line"] is None, r


def test_period_assignment_for_intermediate_periods() -> None:
    """Spot-check that the egyptologist override on Dyn 24 (period was wrongly
    `Spätzeit` per agent vote, corrected to `III. Zwischenzeit`) is locked.
    Dyn 26 onward IS Spätzeit.
    """
    assert _row("24.01")["period"] == "III. Zwischenzeit"
    assert _row("24.02")["period"] == "III. Zwischenzeit"
    assert _row("26.01")["period"] == "Spätzeit"


def test_xerxes_i_endpoints_not_inverted() -> None:
    """Beckerath: Xerxes I 486/85–465/64. The merge initially produced
    end_bce_low=-484 (a carryover of start_bce_low). The override corrected
    end_bce_low to -464.
    """
    r = _row("27.03")
    assert r["name"] == "Xerxes I."
    assert r["start_bce_high"] == -486
    assert r["start_bce_low"] == -485
    assert r["end_bce_high"] == -465
    assert r["end_bce_low"] == -464


def test_dyn3_brace_bracket_shared_range() -> None:
    """Beckerath's Dyn 3 has a brace bracket spanning Hor Cha-bai /
    Sôuphis,Mesochris / Ahu (Huni,Aches), all sharing the range
    `2663/2613-2639/2589`. The egyptologist override corrected this from
    null (which the majority vote produced because 2 of 3 agents missed
    the bracket) to the shared values.
    """
    cha_bai = _row("03.04")
    souphis = _row("03.05")
    ahu = _row("03.06")
    for r in (cha_bai, souphis, ahu):
        assert r["start_bce_high"] == -2663
        assert r["start_bce_low"] == -2613
        assert r["end_bce_high"] == -2639
        assert r["end_bce_low"] == -2589


def test_taharqo_mixed_titulary() -> None:
    """Beckerath gives Taharqo's parenthetical as `Tarakos, Chu-nefertem-rê`
    — a comma-separated nomen+prenomen pair. The mixed-kind label captures
    that.
    """
    r = _row("25.05")
    assert r["name"] == "Taharqo"
    assert r["egyptian_titulary"] == "Tarakos, Chu-nefertem-rê"
    assert r["egyptian_titulary_kind"] == "mixed"


def test_psamtik_i_dyn26_full_row() -> None:
    """Late Period flagship: prenomen `Wah-ib-rê` is the parenthetical; both
    approximate flags false (Beckerath gives bare numbers); Spätzeit period."""
    r = _row("26.01")
    assert r["dynasty"] == 26
    assert r["sub_line"] is None
    assert r["sequence_in_dynasty"] == 1
    assert "Psamtik" in r["name"]
    assert r["egyptian_titulary"] == "Wah-ib-rê"
    assert r["egyptian_titulary_kind"] == "prenomen"
    assert r["start_bce_high"] == -664
    assert r["end_bce_high"] == -610
    assert r["start_approximate"] is False
    assert r["end_approximate"] is False
    assert r["period"] == "Spätzeit"


def test_supplement_prenomens_merged_for_dyn19_23() -> None:
    """The Supplement zu A pulls additional prenomen forms for Dyn 19-23
    kings. Those should be merged into the main row's `prenomen` field, not
    emitted as separate rows. Spot-check a few canonical entries.
    """
    # Schoschenq III (22.06) gets `User-maat-rê sotep-en-rê` from the Supplement.
    assert _row("22.06")["prenomen"] == "User-maat-rê sotep-en-rê"


# ── Tests pinning fix_rows.py overrides not covered above ────────────────
# Each of these locks a specific reviewer-applied correction. If someone
# re-runs merge.py and forgets fix_rows.py, these tests fail loudly.

def test_dyn4_etwa_propagation_locked() -> None:
    """`fix_rows.py` corrected start_approximate / end_approximate to True
    on every Dyn-4 row (04.02 through 04.08) because Beckerath's heading
    `4. Dynastie (etwa 2639/2589–2504/2454)` propagates to all rows.
    Agent C's 'false' votes had tipped the merge majority on 6 of these.
    """
    for kid in ("04.02", "04.03", "04.04", "04.05", "04.06", "04.07", "04.08"):
        r = _row(kid)
        assert r["start_approximate"] is True, kid
        assert r["end_approximate"] is True, kid


def test_chajan_dyn15_end_date_locked() -> None:
    """`fix_rows.py` corrected `end_bce_high` for Chajan from -1149 (a
    400-year OCR corruption) to -1549 (matching scan-106 left's
    `1590/87–1549/1546`).
    """
    r = _row("15.04")
    assert r["name"] == "Chajan"
    assert r["end_bce_high"] == -1549
    assert r["end_bce_low"] == -1546


def test_hatschepsut_end_date_locked() -> None:
    """`fix_rows.py` recovered Hat-schepsut's end dates from the OCR-garbled
    `341/837` to the correct `1458` per scan-107 left's `1479/73–1458`.
    """
    r = _row("18.05")
    assert r["name"] == "Kgin. Hat-schepsut"
    assert r["end_bce_high"] == -1458
    assert r["end_bce_low"] == -1458
    assert r["end_approximate"] is False


def test_amen_mes_su_prenomen_supplement_locked() -> None:
    """`fix_rows.py` corrected Amen-mes-su's prenomen from `Amen-mes-su
    mer-amun` (which is Beckerath's Eigenname) to `Men-mi-rê sotep-en-rê`
    (the actual Thronname from Supplement zu A).
    """
    r = _row("19.05")
    assert r["name"] == "Amen-mes-su"
    assert r["prenomen"] == "Men-mi-rê sotep-en-rê"


def test_sethos_ii_prenomen_supplement_locked() -> None:
    """`fix_rows.py` corrected Sethós II's prenomen from
    `Ba-en-rê-meri-netjeru` (which is Merenptah's prenomen — a splice
    error) to `User-chepru-rê mer-amun` per Supplement zu A.
    """
    r = _row("19.06")
    assert r["name"] == "Sethós II."
    assert r["prenomen"] == "User-chepru-rê mer-amun"


def test_necho_ii_prenomen_locked() -> None:
    """Gemini-flagged: `fix_rows.py` corrected Necho II's titulary from
    `Nefer-ib-rê` (a splice from Psamtik II's row) to `Wahem-ib-rê`.
    """
    r = _row("26.02")
    assert "Nech" in r["name"]
    assert r["egyptian_titulary"] == "Wahem-ib-rê"


def test_chabbasch_dyn31_locked() -> None:
    """Gemini-flagged: `fix_rows.py` corrected the Dyn 31 Egyptian
    counter-king's name to `Chabbasch` and titulary to
    `Senem-sotep-en-ptah`.
    """
    r = _row("31.04")
    assert r["name"] == "Chabbasch"
    assert r["egyptian_titulary"] == "Senem-sotep-en-ptah"


def test_schoschenq_spelling_systematic() -> None:
    """`fix_rows.py` runs a systematic Schoscheng→Schoschenq fix because
    OCR mis-read q→g on every occurrence in Dyn 22. No row may contain
    `Schoscheng`; every Schoschenq row must spell it correctly.
    """
    for r in _rows():
        for field in ("name", "prenomen", "egyptian_titulary", "notes_from_beckerath"):
            v = r.get(field)
            if isinstance(v, str):
                assert "Schoscheng" not in v, (r["beckerath_id"], field, v)
    # Spot-check that the Dyn 22 Schoschenq rows are present and spelled correctly.
    assert _row("22.01")["name"] == "Schoschenq I."


def test_notes_have_no_editorial_prose() -> None:
    """`notes_from_beckerath` must contain only Beckerath's own annotations.
    `fix_rows.py` strips agent editorial fragments like "end date not given",
    "combined Dyn 9/10", "supplement notes:". Lock that no such fragment
    survives.
    """
    forbidden_substrings = (
        "end date not given",
        "combined Dyn",
        "supplement notes:",
        "OCR",
        "garbled",
    )
    for r in _rows():
        notes = r.get("notes_from_beckerath")
        if not isinstance(notes, str):
            continue
        for sub in forbidden_substrings:
            assert sub.lower() not in notes.lower(), (r["beckerath_id"], sub, notes)


def test_akhenaten_prenomen_typo_fixed() -> None:
    """`fix_rows.py` corrected Akhenaten's prenomen from `Nefer-chepruê
    wa-en-rê` (OCR dropped the `r`) to `Nefer-cheprurê wa-en-rê`.
    """
    r = _row("18.10")
    assert "Ach-en-aten" in r["name"]
    assert r["egyptian_titulary"] == "Nefer-cheprurê wa-en-rê"
