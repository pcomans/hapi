"""Structural value-assertion tests for Hölbl 2001 Argead-bridge source extract.

Per rule 5: every populated field on every row is asserted. With only 3 rows,
each row is a flagship row.
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
    / "holbl-2001-argead"
)
JSONL = SOURCE_DIR / "reconciled.jsonl"

EDITION = "Routledge 2001"
PDF_PAGES = "348-351"
POLITY = "Argead"


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(json.loads(line) for line in JSONL.read_text().splitlines() if line.strip())


def _row(holbl_id: str) -> dict:
    hits = [r for r in _rows() if r["holbl_id"] == holbl_id]
    if len(hits) != 1:
        raise AssertionError(f"expected 1 row for {holbl_id}, got {len(hits)}")
    return hits[0]


# -----------------------------------------------------------------------------
# Structural invariants
# -----------------------------------------------------------------------------

def test_row_count_is_exactly_three() -> None:
    """Alexander the Great, Philip III Arrhidaios, Alexander IV — exactly 3.
    INTERREGNUM (310/09–306) and Ptolemy I Soter are explicitly excluded per
    README § Scope.
    """
    assert len(_rows()) == 3, len(_rows())


def test_holbl_id_is_unique() -> None:
    """No duplicate holbl_id in the committed extract."""
    ids = [r["holbl_id"] for r in _rows()]
    assert len(ids) == len(set(ids)), ids


_HID_RE = re.compile(r"^argead\.[0-9]{2}$")


def test_holbl_id_shape() -> None:
    """Every id matches `argead.{NN}` where NN is zero-padded two digits."""
    for r in _rows():
        assert _HID_RE.match(r["holbl_id"]), r["holbl_id"]


def test_holbl_ids_are_exactly_the_expected_three() -> None:
    """Set-equality over the known three rulers."""
    ids = {r["holbl_id"] for r in _rows()}
    assert ids == {"argead.01", "argead.02", "argead.03"}, ids


def test_every_row_has_complete_citation() -> None:
    """Rule 1: every row traces back to a pdf_pages range and edition."""
    for r in _rows():
        citation = r["source_citation"]
        assert citation == {"pdf_pages": PDF_PAGES, "edition": EDITION}, r


def test_every_row_polity_is_argead() -> None:
    """All three Argead rulers carry polity = "Argead". This distinguishes
    them from the Ptolemaic rulers covered by `sources/pharaoh-se/` and
    `sources/wikipedia-ptolemaic/` (which start at Ptolemy I's kingship in
    306 BCE), and from any preceding Achaemenid or Late-Period rulers.
    """
    for r in _rows():
        assert r["polity"] == POLITY, r


def test_every_row_has_all_expected_fields() -> None:
    """Schema completeness: every committed row carries the same field set.
    Catches silent schema drift between rows (e.g. a field dropped on one
    row during a hand-edit).
    """
    expected_fields = {
        "holbl_id", "name", "alt_names", "start_bce", "end_bce",
        "approximate", "polity", "notes_from_holbl", "source_citation",
    }
    for r in _rows():
        assert set(r.keys()) == expected_fields, (r["holbl_id"], set(r.keys()))


def test_reigns_are_sequential_and_ordered() -> None:
    """Argead rulers reign sequentially. argead.01 ends where argead.02
    starts; argead.02 ends where argead.03 starts. Any overlap or gap would
    be an extraction bug.
    """
    a1, a2, a3 = _row("argead.01"), _row("argead.02"), _row("argead.03")
    assert a1["end_bce"] == a2["start_bce"], (a1["end_bce"], a2["start_bce"])
    assert a2["end_bce"] == a3["start_bce"], (a2["end_bce"], a3["start_bce"])


def test_bce_endpoints_are_negative_integers_ordered() -> None:
    """start_bce and end_bce are negative integers with start strictly
    earlier than end (more negative than end — higher absolute-value BCE
    number). No row may have start_bce == end_bce (no single-year reigns in
    this source) and no row may have a positive or zero endpoint.
    """
    for r in _rows():
        s, e = r["start_bce"], r["end_bce"]
        assert isinstance(s, int) and isinstance(e, int), r
        assert s < 0 and e < 0, r
        assert s < e, f"{r['holbl_id']}: start {s} not strictly earlier than end {e}"


# -----------------------------------------------------------------------------
# Per-row flagship assertions (rule 5: every populated field on every row)
# -----------------------------------------------------------------------------

def test_argead_01_alexander_the_great_full_row() -> None:
    """Alexander the Great (Alexander III of Macedon) — first Argead ruler of
    Egypt. Egyptian accession 332 (post-invasion); Macedonian accession 336
    is NOT captured here because Hölbl's Egypt-anchored appendix uses the
    332 invasion year. Died 10 June 323; Hölbl's table states only "Death of
    Alexander", so the notes are faithful to the rubric cell (the Babylon
    setting is consensus scholarship but is deliberately omitted from
    `notes_from_holbl` because it is not attested in this specific table
    cell — see `fix_rows.py` and `test_notes_do_not_add_facts_beyond_holbl_rubric`).
    """
    r = _row("argead.01")
    assert r["holbl_id"] == "argead.01"
    assert r["name"] == "Alexander the Great"
    assert r["alt_names"] == ["Alexander III", "Alexander III of Macedon"]
    assert r["start_bce"] == -332
    assert r["end_bce"] == -323
    assert r["approximate"] is False
    assert r["polity"] == "Argead"
    assert r["notes_from_holbl"] == (
        "Invaded Egypt towards the end of 332 and acceded as pharaoh at the "
        "end of 332. Beginning of 331: foundation of Alexandria and "
        "expedition to the Ammoneion (Siwa), whose royal oracle legitimised "
        "him as pharaoh and confirmed his view of himself as son of "
        "Zeus-Ammon. Departed Egypt spring 331. Died 10 June 323."
    )
    assert r["source_citation"] == {"pdf_pages": PDF_PAGES, "edition": EDITION}


def test_argead_02_philip_iii_arrhidaios_full_row() -> None:
    """Philip III Arrhidaios — feeble-minded half-brother of Alexander the
    Great, nominal king 323–317 while Ptolemy ruled Egypt as Satrap.
    Hölbl uses the spelling "Arrhidaios" (the translator's Greek-faithful
    form); the alt_names list captures "Arrhidaeus" (the Latinised form
    more common in English scholarship).
    """
    r = _row("argead.02")
    assert r["holbl_id"] == "argead.02"
    assert r["name"] == "Philip III Arrhidaios"
    assert r["alt_names"] == ["Philip Arrhidaeus", "Philip III"]
    assert r["start_bce"] == -323
    assert r["end_bce"] == -317
    assert r["approximate"] is False
    assert r["polity"] == "Argead"
    assert r["notes_from_holbl"] == (
        "Feeble-minded half-brother of Alexander the Great, acknowledged as "
        "king at the 323 Division of empire at Babylon, nominally joint "
        "with the pregnant Roxane's possible son. Ptolemy received the "
        "satrapy of Egypt and acts as Satrap through this reign. Murdered "
        "autumn 317 as Polyperchon was deposed and Kassandros became regent."
    )
    assert r["source_citation"] == {"pdf_pages": PDF_PAGES, "edition": EDITION}


def test_argead_03_alexander_iv_full_row() -> None:
    """Alexander IV — posthumous son of Alexander the Great and Roxane.
    Nominal joint king with Philip III Arrhidaios from birth (323); sole
    nominal king after Philip III's murder in 317. Ptolemy acts as Satrap
    throughout. Murdered 310/309 by Kassandros. `approximate: true` because
    Hölbl writes the end as the split-year `310/09`.
    """
    r = _row("argead.03")
    assert r["holbl_id"] == "argead.03"
    assert r["name"] == "Alexander IV"
    assert r["alt_names"] == ["Alexander IV of Macedon", "Alexander IV Aegus"]
    assert r["start_bce"] == -317
    assert r["end_bce"] == -310
    assert r["approximate"] is True
    assert r["polity"] == "Argead"
    assert r["notes_from_holbl"] == (
        "Posthumous son of Alexander the Great and Roxane; nominal joint "
        "king with Philip III Arrhidaios from birth, then sole nominal king "
        "after Philip III's murder in 317. Remained in Kassandros' custody "
        "under the Autumn 311 peace treaty between Ptolemy, Kassandros, "
        "Lysimachos and Antigonos. Murdered 310/309 by Kassandros. Ptolemy "
        "as Satrap of Egypt throughout this reign."
    )
    assert r["source_citation"] == {"pdf_pages": PDF_PAGES, "edition": EDITION}


# -----------------------------------------------------------------------------
# Edge-case / regression tests
# -----------------------------------------------------------------------------

def test_only_alexander_iv_is_approximate() -> None:
    """Hölbl's rubric uses unhedged single years for Alexander the Great's
    332 invasion and Philip III's 317 murder; Alexander IV's end is the
    only split-year (`310/09`). So exactly one row is `approximate: true`.
    """
    approx = [r for r in _rows() if r["approximate"]]
    assert len(approx) == 1, approx
    assert approx[0]["holbl_id"] == "argead.03"


def test_notes_do_not_add_facts_beyond_holbl_rubric() -> None:
    """Regression against the egyptologist-reviewer's two spot corrections
    (applied in `fix_rows.py`):

    1. `argead.01` notes must NOT claim Alexander died "in Babylon" —
       Hölbl's rubric states only "10 June 323: Death of Alexander". The
       Babylon setting is consensus scholarship but is not attested in this
       specific rubric cell. The fix_rows override removed "in Babylon";
       this test guards against a future edit that re-introduces it.
    2. `argead.03` notes must NOT contain the editorial parenthetical
       `(316, per Hölbl`" — Hölbl's `316` entry is the birth of Arsinoe II,
       not Alexander IV. The extractor commentary was removed by fix_rows;
       this test guards against re-introduction.
    """
    assert "in Babylon" not in _row("argead.01")["notes_from_holbl"]
    assert "316, per Hölbl" not in _row("argead.03")["notes_from_holbl"]
    assert "(316" not in _row("argead.03")["notes_from_holbl"]


def test_ptolemy_as_satrap_attested_in_notes_for_both_successor_reigns() -> None:
    """Hölbl's rubric labels the Philip III and Alexander IV blocks with
    "Ptolemy as Satrap" — capturing that Ptolemy, not the nominal king,
    was the de facto ruler of Egypt through both reigns. The
    `notes_from_holbl` field must preserve this. Alexander the Great's own
    rubric does NOT carry the satrap label (he was the direct ruler), so
    argead.01's notes do not mention Satrap status.
    """
    assert "Satrap" in _row("argead.02")["notes_from_holbl"]
    assert "Satrap" in _row("argead.03")["notes_from_holbl"]
    # Argead.01 is Alexander himself — no Satrap there.
    assert "Satrap" not in _row("argead.01")["notes_from_holbl"]


def test_alt_names_populated_for_every_row() -> None:
    """Unlike Kitchen where alt_names is not part of the schema, Hölbl's
    extract carries alt_names for every row: the alternate English spellings
    and the Macedonian-numbered forms. Every row has at least one alt_name.
    """
    for r in _rows():
        assert isinstance(r["alt_names"], list), r
        assert len(r["alt_names"]) >= 1, r
        for alt in r["alt_names"]:
            assert isinstance(alt, str) and alt, (r["holbl_id"], alt)
        # alt_names must not duplicate the canonical name
        assert r["name"] not in r["alt_names"], r


def test_interregnum_row_is_not_present() -> None:
    """Explicit exclusion check: no row for the 310/09–306 INTERREGNUM,
    which is Hölbl's rubric label for the interval between Alexander IV's
    murder and Ptolemy I's assumption of the royal title. An INTERREGNUM
    row would mean the extractor pulled in the label following Alexander IV.
    """
    names = [r["name"].lower() for r in _rows()]
    for n in names:
        assert "interregnum" not in n, names


def test_ptolemy_i_row_is_not_present() -> None:
    """Explicit exclusion check: Ptolemy I Soter is covered by
    `sources/pharaoh-se/` and `sources/wikipedia-ptolemaic/`, not by this
    extract. The Hölbl appendix continues past Alexander IV into the
    Ptolemaic period; we stop at the Argead/Interregnum boundary.
    """
    names = [r["name"].lower() for r in _rows()]
    for n in names:
        assert "ptolemy" not in n, names


def test_length_of_reign_from_bce_endpoints_matches_expectation() -> None:
    """Hölbl does not print regnal-length integers in this table, so the
    schema has no `length_of_reign_years` field. The BCE-endpoint subtraction
    gives an approximate Egyptian-reign length:

    - Alexander the Great: -323 - (-332) = 9 years in Egypt.
    - Philip III Arrhidaios: -317 - (-323) = 6 years.
    - Alexander IV: -310 - (-317) = 7 years.

    These totals sum to 22 years (332 → 310), which matches the
    Argead-rule period of Egypt in Hölbl's own narrative.
    """
    a1, a2, a3 = _row("argead.01"), _row("argead.02"), _row("argead.03")
    assert a1["end_bce"] - a1["start_bce"] == 9
    assert a2["end_bce"] - a2["start_bce"] == 6
    assert a3["end_bce"] - a3["start_bce"] == 7
    # Sum of 22 years total Argead rule 332 → 310.
    total = (
        (a1["end_bce"] - a1["start_bce"])
        + (a2["end_bce"] - a2["start_bce"])
        + (a3["end_bce"] - a3["start_bce"])
    )
    assert total == 22
