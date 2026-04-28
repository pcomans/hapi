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


def test_bce_endpoints_obey_high_ge_older_convention() -> None:
    """Within an endpoint pair, `_high` must be older (more negative or
    equal) than `_low`. Beckerath's slash form `X/Y` is normalised so X
    (higher / older) goes into `_high` and Y (lower / younger) into `_low`.
    Surfaced by codex review (PR #113): the Dyn 17 row was inverted due to
    an OCR bleed from the adjacent Dyn 15 line. The fix in `fix_rows.py`
    is locked here as a row-level invariant.
    """
    for r in _rows():
        sh, sl = r["start_bce_high"], r["start_bce_low"]
        eh, el = r["end_bce_high"], r["end_bce_low"]
        if sh is not None and sl is not None:
            assert sh <= sl, (r["beckerath_id"], "start", sh, sl)
        if eh is not None and el is not None:
            assert eh <= el, (r["beckerath_id"], "end", eh, el)


def test_dyn17_marker_row_locked() -> None:
    """Dyn 17 is a marker row (no individual kings enumerated). The OCR
    inserted a phantom `1539` from the adjacent Dyn 15 Hyksos line; the
    real Beckerath text gives a single `1550` endpoint. Lock the
    fix_rows.py correction.
    """
    r = _row("17.01")
    assert r["dynasty"] == 17
    assert r["start_bce_high"] == -1645
    assert r["start_bce_low"] == -1645
    assert r["end_bce_high"] == -1550
    assert r["end_bce_low"] == -1550
    assert r["start_approximate"] is True
    assert r["end_approximate"] is True


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
    """Spot-check Dyn 24 sits under III. Zwischenzeit (NOT Spätzeit) and
    Dyn 26 onward IS Spätzeit. Pre-PR-#138 this required a fix_rows.py
    override (agents looked past `### III. ZWISCHENZEIT` to the closer
    `### SPÄTZEIT` and mis-attributed Dyn 24/25 to Spätzeit). PR #138's
    post-processor emits `<!-- period: III. Zwischenzeit -->` directly
    after the Dyn 24/25 dynasty headings (derived from the canonical
    DYNASTY_PERIOD mapping), so agents now extract the correct period
    unaided — override removed.
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
    Sôuphis (with Greek-form `Mesochris` as nomen) / Ahu (with Greek
    forms `Huni, Aches` as mixed titulary), all sharing the range
    `2663/2613-2639/2589`. Pre-PR-#138, the majority vote produced
    null dates on 03.05 / 03.06 because 2 of 3 agents missed the
    bracket; the override propagates the dates from 03.04 per Beckerath's
    printed bracket. The cross-row scan-context note lives in
    `editorial_notes` (English commentary), not in `notes_from_beckerath`.

    NB: post-PR-#138 re-extraction parses `Sôuphis, Mesochris` as
    name=`Sôuphis` + egyptian_titulary=`Mesochris` (Greek-form nomen)
    and similarly `Ahu (Huni, Aches)` as name=`Ahu` +
    egyptian_titulary=`Huni, Aches`. Cross-references in editorial_notes
    use the canonical `name` field per the README field contract.
    """
    cha_bai = _row("03.04")
    souphis = _row("03.05")
    ahu = _row("03.06")
    for r in (cha_bai, souphis, ahu):
        assert r["start_bce_high"] == -2663
        assert r["start_bce_low"] == -2613
        assert r["end_bce_high"] == -2639
        assert r["end_bce_low"] == -2589
        assert r["notes_from_beckerath"] is None
        assert r["editorial_notes"] is not None
        assert "shared bracket range" in r["editorial_notes"]
        assert "scan-105" in r["editorial_notes"]
    # Cross-row references use the canonical `name` field (which post-PR-#138
    # is the king's bare name, with Greek-form variants in egyptian_titulary).
    assert "Sôuphis (03.05)" in cha_bai["editorial_notes"]
    assert "Ahu (03.06)" in cha_bai["editorial_notes"]
    assert "Hor Cha-bai (03.04)" in souphis["editorial_notes"]
    assert "Ahu (03.06)" in souphis["editorial_notes"]
    assert "Hor Cha-bai (03.04)" in ahu["editorial_notes"]
    assert "Sôuphis (03.05)" in ahu["editorial_notes"]


def test_te_wosret_coregent_row_extracted() -> None:
    """19.08 Kgin. Te-wosret: Beckerath chains her on Si-ptah's row as
    `Si-ptah und Kgin. Te-wosret (Thuoris)`. The Co-regent queen prompt
    rule (PR following PR #138) extracts her as a separate row preserving
    Beckerath's `Kgin.` honorific and the Greek-form `Thuoris` as
    egyptian_titulary. Per the rule, her notes_from_beckerath records
    the co-regency in German verbatim form (`Mitregentin von Si-ptah`),
    NOT as English editorial prose. Pre-PR-#138 baseline used a different
    `notes=null + editorial_notes="co-regent..."` shape derived from
    incomplete agent extraction; the new shape is more faithful to
    Beckerath's printed text.
    """
    r = _row("19.08")
    assert r["name"] == "Kgin. Te-wosret"
    assert r["egyptian_titulary"] == "Thuoris"
    assert r["egyptian_titulary_kind"] == "nomen"
    # German verbatim co-regency annotation (the Co-regent queen rule
    # mandates "Mitregentin von <king>"), NOT English editorial prose.
    assert r["notes_from_beckerath"] == "Mitregentin von Si-ptah"
    # Te-wosret inherits Si-ptah's BCE range (Co-regent queen rule).
    si_ptah = _row("19.07")
    assert r["start_bce_high"] == si_ptah["start_bce_high"]
    assert r["start_bce_low"] == si_ptah["start_bce_low"]
    assert r["end_bce_high"] == si_ptah["end_bce_high"]
    assert r["end_bce_low"] == si_ptah["end_bce_low"]


def test_editorial_notes_field_present_on_every_row() -> None:
    """`editorial_notes` is part of the source schema and must be present
    on every row (default null). Locks the fix_rows.py setdefault pass.
    """
    for r in _rows():
        assert "editorial_notes" in r, r["beckerath_id"]


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
    """Dyn-4 rows 04.02 through 04.08 must all have start_approximate=true
    and end_approximate=true because Beckerath's heading
    `4. Dynastie (etwa 2639/2589–2504/2454)` propagates `etwa` to every
    row. Pre-PR-#138 this required fix_rows.py overrides on all 7 rows
    (agents lost the `etwa` qualifier when crossing the book p187 → p188
    page break). PR #138's post-processor emits a
    `<!-- dynasty-context: 4. Dynastie (etwa 2639/2589–2504/2454) -->`
    refresh comment after the page break, so agents now propagate `etwa`
    correctly unaided — overrides removed.
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
    `fix_rows.py` strips agent editorial fragments. Lock that no known
    agent-prose fragment survives.

    The check has two layers — both run inside this single test so there
    is one inventory and one row-iteration:

    **Forbidden-substring inventory** (literal patterns surfaced by
    reviewer rounds on PR #113 + #117 — the egyptologist post-merge
    sweep, issue #115 — and the editorial_notes-separation PR #119):

    - `"end date not given"` / `"end date"` — agent meta-comment about
      missing data (rule 1 violation: notes must be Beckerath's own text).
    - `"combined Dyn"` — agent meta-comment about Beckerath's Dyn 9/10
      combination (the placement is content; the meta-comment is not).
    - `"supplement notes:"` — agent prefix introducing Supplement zu A
      content; the content stays, the prefix goes.
    - `"start "` — leftover residue from a date-correction pass on 18.05.
    - `"later form"` — agent paraphrase of Beckerath's anfang/später
      annotations.
    - `"; später "` (specific pattern, NOT bare `"später"`) — agent merge
      filler reconciling alternative throne names. Bare "später" is
      legitimate German prose Beckerath might use (e.g. "späterer Zusatz",
      "später in Theben"); only the comma-separator merge artifact is the
      defect.
    - `"Antrittsjahr"` — agent prose; Beckerath writes bare
      "Antritt N.M.YYYY" instead.
    - `"(reign change)"` — agent hedge prose.
    - `"OCR"` / `"garbled"` — agent meta-comments about OCR quality.
    - `"shared bracket range"` — auditor commentary from PR #119; belongs
      in `editorial_notes`, not here.

    **Shape-based regex tripwires** (enumeration-free, phrasing-
    independent — added in PR #119 to catch future regressions the
    literal-substring list misses):

    1. `\\(scan-\\d+` — any `(scan-NNN)` tag is a transcriber/auditor
       artifact (the agents do not see scan numbers; only the
       fix_rows.py editorial pass adds them). Migrated rows
       (03.04/03.05/03.06) carried this shape; this regex catches any
       future re-introduction regardless of wording.
    2. `\\bco-(regents?|rulers?|kings?|regenc(?:y|ies))\\b` — English
       co-rulership prose. 19.08 migration cleared one such instance;
       locking the broader morphological family catches "co-ruler
       with…", "co-king of…", or the abstract-noun "co-regency with…"
       rephrasings the literal-substring list would miss. Singular and
       plural forms (`co-regents`, `co-regencies`) are both covered so
       a `\\b`-locked tail vowel cannot leak past the tripwire.

    A harder positive whitelist of legitimate German cell idioms
    (Antritt, Mitregent, Gegenkönig, in Sais, …) is tracked as #120 for
    next-round hardening.
    """
    forbidden_substrings = (
        "end date",  # also catches "end date not given"
        "combined Dyn",
        "supplement notes:",
        "start ",  # used as residue in 18.05
        "later form",
        "; später ",  # narrow: bare "später" is legitimate German
        "Antrittsjahr",
        "(reign change)",
        "OCR",
        "garbled",
        "shared bracket range",  # PR #119 — belongs in editorial_notes
    )
    forbidden_patterns = (
        # `(scan-NNN)` editorial tag — strictly more general than the
        # literal `(scan-` substring; covers future digit variants.
        re.compile(r"\(scan-\d+"),
        # English co-rulership prose. Strictly more general than the
        # literal `co-regent` substring; catches `co-ruler` / `co-king`.
        re.compile(r"\bco-(regents?|rulers?|kings?|regenc(?:y|ies))\b", re.IGNORECASE),
    )
    for r in _rows():
        notes = r.get("notes_from_beckerath")
        if not isinstance(notes, str):
            continue
        for sub in forbidden_substrings:
            assert sub.lower() not in notes.lower(), (r["beckerath_id"], sub, notes)
        for pat in forbidden_patterns:
            assert not pat.search(notes), (r["beckerath_id"], pat.pattern, notes)


def test_akhenaten_prenomen_typo_fixed() -> None:
    """`fix_rows.py` corrected Akhenaten's prenomen from `Nefer-chepruê
    wa-en-rê` (OCR dropped the `r`) to `Nefer-cheprurê wa-en-rê`.
    """
    r = _row("18.10")
    assert "Ach-en-aten" in r["name"]
    assert r["egyptian_titulary"] == "Nefer-cheprurê wa-en-rê"


def test_compound_titulary_implies_mixed_kind() -> None:
    """**Methodology invariant** — when Beckerath prints a compound
    parenthetical containing a comma (e.g. `(Hagor, Chnem-maat-rê)`,
    `(Tarakos, Chu-nefertem-rê)`, `(Wah-ib-rê, Haa-ib-rê)`), the
    `egyptian_titulary_kind` must be `"mixed"`. This is enforceable as a
    pure derivation from the parenthetical text — no content judgement
    needed — and catches the compound-titulary truncation class flagged
    by the egyptologist post-merge sweep (issue #115). Two-component
    parentheticals where the agents disagreed which half to extract
    historically slipped through the disagreement-log reviewer because
    the agents AGREED on a wrong/partial value.

    Carve-out: Beckerath also writes Greek-disambiguator alternates with
    a comma (e.g. `(Nikku, Nechao II.)` in Supplement zu A). Those are
    name-form variants, not nomen+prenomen compounds. The current data
    does not contain any such carve-out case, so this test asserts the
    strict comma → mixed rule. If a future re-extraction surfaces a
    true name-variant carve-out, refine the test rather than relax the
    invariant — the test failure will document the case.
    """
    for r in _rows():
        tit = r.get("egyptian_titulary")
        if isinstance(tit, str) and "," in tit:
            assert r["egyptian_titulary_kind"] == "mixed", (
                r["beckerath_id"],
                tit,
                r["egyptian_titulary_kind"],
            )


# test_no_editorial_prefixes_in_notes_extended — DELETED 2026-04-25 per
# Gemini PR #117 review (3142716688). Its forbidden-substring list has
# been merged into `test_notes_have_no_editorial_prose` above so we have
# one test, one inventory, one source of truth for editorial-prose
# detection in `notes_from_beckerath`.
