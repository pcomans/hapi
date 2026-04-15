"""Structural value-assertion tests for Kitchen 1996 TIPE source extract.

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
    / "kitchen-tipe"
)
JSONL = SOURCE_DIR / "reconciled.jsonl"

EDITION = "Aris & Phillips 3rd ed. 1996"
PDF_PAGES = "240-243"


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(json.loads(line) for line in JSONL.read_text().splitlines() if line.strip())


def _row(kitchen_id: str) -> dict:
    hits = [r for r in _rows() if r["kitchen_id"] == kitchen_id]
    if len(hits) != 1:
        raise AssertionError(f"expected 1 row for {kitchen_id}, got {len(hits)}")
    return hits[0]


def test_row_count() -> None:
    """Tables 1, 3, 4 together = 60 kings: 1 (Dyn 20 Ramesses XI) + 7 Tanite +
    10 HPA + 11 Dyn 22 + 8 Dyn 23 + 4 Early Saite + 2 Dyn 24 + 4 Proto-Saite
    + 7 Dyn 25 + 6 Dyn 26 = 60.
    """
    assert len(_rows()) == 60, len(_rows())


def test_dynasty_coverage() -> None:
    """Every target dynasty (20 + 21–26) is represented."""
    dynasties = {r["dynasty"] for r in _rows()}
    assert dynasties == {20, 21, 22, 23, 24, 25, 26}, dynasties


def test_kitchen_id_is_unique() -> None:
    """No duplicate kitchen_id in the committed extract."""
    ids = [r["kitchen_id"] for r in _rows()]
    assert len(ids) == len(set(ids)), "duplicate kitchen_id detected"


_KID_RE = re.compile(r"^[0-9]+[A-Za-z]*\.[0-9]{2}$")


def test_kitchen_id_shape() -> None:
    """Every id matches `{prefix}.{NN}` where NN is zero-padded two digits."""
    for r in _rows():
        assert _KID_RE.match(r["kitchen_id"]), r["kitchen_id"]


def test_every_row_has_complete_citation() -> None:
    """Rule 1: every row traces back to a pdf_pages range and edition."""
    for r in _rows():
        citation = r["source_citation"]
        assert citation == {"pdf_pages": PDF_PAGES, "edition": EDITION}, r


def test_ramesses_xi_dyn20_row() -> None:
    """Kitchen's Table 1 opens with Ramesses XI (Late Dyn 20) because the
    'Renaissance Era' anchors the whole Dyn 21 chronology. Dyn 20 is
    out-of-scope for TIP strictly but preserved verbatim from Table 1.
    """
    r = _row("20.01")
    assert r["dynasty"] == 20
    assert r["sequence_in_dynasty"] == 1
    assert r["name"] == "Ramesses XI"
    assert r["prenomen"] is None
    assert r["start_bce"] == -1098
    assert r["end_bce"] == -1069
    assert r["length_of_reign_years"] == 29
    assert r["approximate"] is False
    assert r["polity"] == "Tanis"
    assert r["concurrent_with_kings"] == ["21H.01", "21H.02", "21H.03"]
    assert r["notes_from_kitchen"] is None


def test_osorkon_i_22_02_full_titulary() -> None:
    """Osorkon I is the handoff doc's schema example — assert every populated field."""
    r = _row("22.02")
    assert r["dynasty"] == 22
    assert r["sequence_in_dynasty"] == 2
    assert r["name"] == "Osorkon I"
    assert r["prenomen"] == "Sekhemkheperre Setepenre"
    assert r["start_bce"] == -924
    assert r["end_bce"] == -889
    assert r["length_of_reign_years"] == 35
    assert r["approximate"] is False
    assert r["polity"] == "Tanis"
    assert r["concurrent_with_kings"] == []
    assert r["notes_from_kitchen"] is None


def test_harsiese_a_is_theban_hpa_polity() -> None:
    """Harsiese A sits in Kitchen's 22nd-Dyn table but is explicitly marked
    "co-rgt only" at Thebes. Polity must be "Theban (HPA)", not "Tanis".
    This is the one schema-level exception in the 22.* stream.
    """
    r = _row("22.06")
    assert r["name"] == "Harsiese"
    assert r["polity"] == "Theban (HPA)"
    assert r["approximate"] is True  # "c. 870–860" and "c. 10 y?"
    assert r["notes_from_kitchen"] == "co-rgt only"
    assert r["prenomen"] == "Hedjkheperre Setepenamun"
    # Distinguish from Takeloth II (22.07) whose prenomen ends "Setepenre"
    assert _row("22.07")["prenomen"] == "Hedjkheperre Setepenre"


def test_dkf_kitchen_typo_preserved_verbatim() -> None:
    """Kitchen's Table 1 prints Djed-Khons-ef-ankh's date range as
    "1046–1056" — typographically reversed; predecessor Masaharta ends 1046
    and successor Menkheperre starts 1045, so the printed 1056 is a Kitchen
    typo. ADR-017 says "preserve Kitchen verbatim" → end_bce stays -1056.
    The notes_from_kitchen field flags the anomaly so downstream consumers
    don't silently compute a -11 year reign. Concurrency is computed
    against the *corrected* 1046–1045 interval (via fix_rows.py), which is
    why 21.01 Smendes I (not 21.03 Psusennes I) appears in the concurrency.
    """
    r = _row("21H.06")
    assert r["name"] == "Djed-Khons-ef-ankh"
    assert r["start_bce"] == -1046
    assert r["end_bce"] == -1056  # verbatim Kitchen typo, flagged in notes
    assert r["length_of_reign_years"] == 1
    assert r["approximate"] is True
    assert "typographic reversal" in (r["notes_from_kitchen"] or "")
    assert r["concurrent_with_kings"] == ["21.01"]


def test_shoshenq_vi_parenthesised_doubtful() -> None:
    """Shoshenq VI's whole line is parenthesised — Kitchen marks the
    existence itself as doubtful. approximate=true; notes record "existence,
    doubtful".
    """
    r = _row("23.08")
    assert r["name"] == "Shoshenq VI"
    assert r["start_bce"] == -720
    assert r["end_bce"] == -715
    assert r["length_of_reign_years"] == 5
    assert r["approximate"] is True
    assert "doubtful" in (r["notes_from_kitchen"] or "").lower()


def test_iuput_ii_bracketed_prenomen_unknown() -> None:
    """Kitchen prints `[Prenomen unknown]` verbatim on Iuput II's row
    (and on Takeloth I's 22.04). The bracketed string is preserved as a
    literal prenomen value — NOT normalised to null by the sentinel
    normaliser, because it is Kitchen's positive assertion that he knows
    the king had a prenomen but its content is lost.
    """
    assert _row("23.07")["prenomen"] == "[Prenomen unknown]"
    assert _row("22.04")["prenomen"] == "[Prenomen unknown]"


def test_approximate_flag_on_c_prefixed_rows() -> None:
    """Every row whose OCR line begins with `c.` must carry approximate:true.
    Sampling: 22.03 Shoshenq II ("c. 890"), 22.06 Harsiese ("c. 870–860"),
    23.06 Rudamun ("c. 3 y?"), 23.07 Iuput II ("c. 11/16 y"), 23.08
    Shoshenq VI, 25.01 Alara, 25.02 Kashta, and all four Early Saite Princes.
    """
    for kid in [
        "22.03", "22.06", "23.06", "23.07", "23.08",
        "25.01", "25.02", "24E.01", "24E.02", "24E.03", "24E.04",
    ]:
        assert _row(kid)["approximate"] is True, kid


def test_polity_by_prefix() -> None:
    """Polity assignments follow prompt.md:
    20.* and 21.* = Tanis; 21H.* = Theban (HPA); 22.* = Tanis
    except 22.06 Harsiese = Theban (HPA); 23.* = Leontopolis;
    24E.* = Sais (Mā); 24.* and 24P.* = Sais; 25.* = Nubia (Napata);
    26.* = Sais.
    """
    expected: dict[str, str] = {
        "20": "Tanis",
        "21": "Tanis",
        "21H": "Theban (HPA)",
        "23": "Leontopolis",
        "24E": "Sais (Mā)",
        "24": "Sais",
        "24P": "Sais",
        "25": "Nubia (Napata)",
        "26": "Sais",
    }
    for r in _rows():
        prefix = r["kitchen_id"].split(".")[0]
        if prefix == "22":
            if r["kitchen_id"] == "22.06":
                assert r["polity"] == "Theban (HPA)", r
            else:
                assert r["polity"] == "Tanis", r
        else:
            assert r["polity"] == expected[prefix], (prefix, r)


def test_dyn21_concurrency_is_symmetric() -> None:
    """If Tanite king X lists HPA H in concurrent_with_kings, H must list X.
    This is the deterministic-overlap invariant enforced by fix_rows.py —
    any future drift breaks this test.
    """
    rows = {r["kitchen_id"]: r for r in _rows()}
    for kid, row in rows.items():
        if not (kid.startswith("21.") or kid == "20.01" or kid.startswith("21H.")):
            continue
        for peer in row["concurrent_with_kings"]:
            assert kid in rows[peer]["concurrent_with_kings"], (
                f"asymmetry: {kid} → {peer} but {peer} ↛ {kid}"
            )


def test_tables_3_and_4_have_empty_concurrency() -> None:
    """Per prompt.md, concurrent_with_kings is populated ONLY for Dyn 21
    (Tables 3 & 4 deferred to Phase A via Kitchen's Table 6 ready-reckoner).
    """
    for r in _rows():
        if r["kitchen_id"].startswith(("20.", "21.", "21H.")):
            continue
        assert r["concurrent_with_kings"] == [], r


def test_taharqa_full_row() -> None:
    """25th Dyn flagship row; tests absolute dates, prenomen, and Nubia polity."""
    r = _row("25.06")
    assert r["dynasty"] == 25
    assert r["sequence_in_dynasty"] == 6
    assert r["name"] == "Taharqa"
    assert r["prenomen"] == "Nefertumkhure"
    assert r["start_bce"] == -690
    assert r["end_bce"] == -664
    assert r["length_of_reign_years"] == 26
    assert r["approximate"] is False
    assert r["polity"] == "Nubia (Napata)"
    assert r["concurrent_with_kings"] == []
    assert r["notes_from_kitchen"] is None


def test_piankhy_dual_prenomen_preserved() -> None:
    """Kitchen prints Piankhy's prenomen as "Usimare, then Sneferre" (he
    changed it). The string is preserved verbatim.
    """
    r = _row("25.03")
    assert r["name"] == "Piankhy"
    assert r["prenomen"] == "Usimare, then Sneferre"
    assert r["length_of_reign_years"] == 31


def test_tefnakht_i_appears_twice() -> None:
    """Tefnakht I shows up once as Chief of Mā (24E.04, c. 740-727) then
    again as king (24.01, 727-720) — Kitchen explicitly brackets this
    transition with "(c. 13 y; then, kg)". Both rows must be present with
    matching name string.
    """
    early = _row("24E.04")
    king = _row("24.01")
    assert early["name"] == king["name"] == "Tefnakht I"
    assert early["polity"] == "Sais (Mā)"
    assert king["polity"] == "Sais"
    assert early["approximate"] is True
    assert king["approximate"] is False
