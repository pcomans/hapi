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


def test_shoshenq_vi_parenthesised_doubtful_full_row() -> None:
    """Shoshenq VI's whole line is parenthesised in Kitchen's Table 3 —
    he marks the existence itself as doubtful. Full-row assertion per rule 5.
    """
    r = _row("23.08")
    assert r["kitchen_id"] == "23.08"
    assert r["dynasty"] == 23
    assert r["sequence_in_dynasty"] == 8
    assert r["name"] == "Shoshenq VI"
    assert r["prenomen"] == "Wasneterre Setepenre"
    assert r["start_bce"] == -720
    assert r["end_bce"] == -715
    assert r["length_of_reign_years"] == 5
    assert r["approximate"] is True
    assert r["polity"] == "Leontopolis"
    assert r["concurrent_with_kings"] == []
    assert r["notes_from_kitchen"] == "existence, doubtful"


def test_iuput_ii_bracketed_prenomen_unknown_full_row() -> None:
    """Kitchen prints `[Prenomen unknown]` verbatim on Iuput II's row
    (and on Takeloth I's 22.04). The bracketed string is preserved as a
    literal prenomen — NOT normalised to null by the sentinel normaliser —
    because it is Kitchen's positive assertion that the king had a
    prenomen whose content is lost. Full-row assertion on Iuput II per rule 5.
    """
    r = _row("23.07")
    assert r["kitchen_id"] == "23.07"
    assert r["dynasty"] == 23
    assert r["sequence_in_dynasty"] == 7
    assert r["name"] == "Iuput II"
    assert r["prenomen"] == "[Prenomen unknown]"
    assert r["start_bce"] == -731
    assert r["end_bce"] == -720
    assert r["length_of_reign_years"] == 11
    assert r["approximate"] is True
    assert r["polity"] == "Leontopolis"
    assert r["concurrent_with_kings"] == []
    assert r["notes_from_kitchen"] == "11/16 y alternative; end date alternative 715"


def test_takeloth_i_bracketed_prenomen_unknown_full_row() -> None:
    """Kitchen's other `[Prenomen unknown]` row, Dyn 22. Full-row assertion."""
    r = _row("22.04")
    assert r["kitchen_id"] == "22.04"
    assert r["dynasty"] == 22
    assert r["sequence_in_dynasty"] == 4
    assert r["name"] == "Takeloth I"
    assert r["prenomen"] == "[Prenomen unknown]"
    assert r["start_bce"] == -889
    assert r["end_bce"] == -874
    assert r["length_of_reign_years"] == 15
    assert r["approximate"] is False
    assert r["polity"] == "Tanis"
    assert r["concurrent_with_kings"] == []
    assert r["notes_from_kitchen"] is None


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


def test_dyn21_concurrency_matches_deterministic_recomputation() -> None:
    """`concurrent_with_kings` for Dyn 21 + Ramesses XI rows must equal the
    deterministic recomputation from `fix_rows.py`. This catches drift both
    in the extraction (if an agent somehow overwrote the post-processed
    values) and in `fix_rows.py` itself (if someone edits the algorithm
    without re-running it on the committed JSONL).

    Symmetry alone would be too weak an invariant: a stale-but-symmetric
    concurrency list would still pass symmetry checks. Re-deriving from
    the authoritative dates is the real invariant.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "kitchen_fix_rows",
        SOURCE_DIR / "fix_rows.py",
    )
    fix_rows = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(fix_rows)

    expected = fix_rows._compute_concurrency(list(_rows()))
    for r in _rows():
        kid = r["kitchen_id"]
        if kid not in expected:
            continue
        assert r["concurrent_with_kings"] == expected[kid], (
            f"{kid}: stored {r['concurrent_with_kings']} != "
            f"deterministic {expected[kid]}"
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


def test_piankhy_dual_prenomen_full_row() -> None:
    """Kitchen prints Piankhy's prenomen as "Usimare, then Sneferre" (he
    changed it mid-reign). Full-row assertion per rule 5 — especially the
    embedded comma survives the extraction.
    """
    r = _row("25.03")
    assert r["kitchen_id"] == "25.03"
    assert r["dynasty"] == 25
    assert r["sequence_in_dynasty"] == 3
    assert r["name"] == "Piankhy"
    assert r["prenomen"] == "Usimare, then Sneferre"
    assert r["start_bce"] == -747
    assert r["end_bce"] == -716
    assert r["length_of_reign_years"] == 31
    assert r["approximate"] is False
    assert r["polity"] == "Nubia (Napata)"
    assert r["concurrent_with_kings"] == []
    assert r["notes_from_kitchen"] is None


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


# ── Closure tests (#180) — typed flags, list-promote, idempotence ──────

_REQUIRED_180_KEYS = (
    "substream",
    "prenomen_is_kitchen_unknown",
    "is_co_regent_only",
    "existence_doubtful",
    "same_person_as",
    "corrected_end_bce",
    "prenomens",
)


def test_180_every_row_has_typed_flags() -> None:
    """Every row carries all 7 typed fields introduced in #180."""
    for r in _rows():
        for key in _REQUIRED_180_KEYS:
            assert key in r, (r["kitchen_id"], key)


def test_180_substream_derives_from_kitchen_id() -> None:
    """Substream letter ∈ {H, E, P} OR None (main-line). Mechanical
    derivation from kitchen_id — every row's substream matches the
    letter (if any) immediately after the dynasty number."""
    import re
    pat = re.compile(r"^\d+([A-Z]?)\.")
    for r in _rows():
        m = pat.match(r["kitchen_id"])
        expected = m.group(1) or None
        assert r["substream"] == expected, (r["kitchen_id"], r["substream"], expected)


def test_180_substream_distribution() -> None:
    """Pin the exact substream distribution for the current TIPE extract:
    42 main-line, 10 H (HPA), 4 E (Sais-Bubastis-East), 4 P (Persian /
    proto-Saite). Total 60 rows."""
    from collections import Counter
    counts = Counter(r["substream"] for r in _rows())
    assert counts == {None: 42, "H": 10, "E": 4, "P": 4}, counts


def test_180_prenomen_is_kitchen_unknown_canonical_set() -> None:
    """Exactly 2 rows where Kitchen prints `[Prenomen unknown]`: 22.04
    Takeloth I and 23.07 Iuput II. Every other null prenomen is a
    table-layout omission, not a Kitchen-asserted unknown."""
    expected = {"22.04", "23.07"}
    actual = {r["kitchen_id"] for r in _rows() if r["prenomen_is_kitchen_unknown"]}
    assert actual == expected, sorted(actual)


def test_180_co_regent_only_canonical_set() -> None:
    """21H.05 Masaharta + 21H.06 Djed-Khons-ef-ankh — both HPA co-regents
    under Pinudjem I per Kitchen's TIPE Table 3 narrative."""
    expected = {"21H.05", "21H.06"}
    actual = {r["kitchen_id"] for r in _rows() if r["is_co_regent_only"]}
    assert actual == expected, sorted(actual)


def test_180_existence_doubtful_canonical_set() -> None:
    """Rows where Kitchen marks the king's existence as uncertain via
    `?` / `??` / quote-glyph wrap on the name. Pinned 2026-05-03:
    24E.01 Pimay (the later king??), 24E.02 Two further governors?,
    24P.01 'Ammeris'."""
    expected = {"24E.01", "24E.02", "24P.01"}
    actual = {r["kitchen_id"] for r in _rows() if r["existence_doubtful"]}
    assert actual == expected, sorted(actual)


def test_180_same_person_pairs_are_symmetric() -> None:
    """Pinudjem I is at 21H.03 (HPA) AND 21H.04 (king titulature).
    The same_person_as field must be symmetric: each row points at the
    other."""
    by_id = {r["kitchen_id"]: r for r in _rows()}
    for r in _rows():
        partner = r["same_person_as"]
        if partner is None:
            continue
        assert partner in by_id, (r["kitchen_id"], partner)
        assert by_id[partner]["same_person_as"] == r["kitchen_id"], (
            r["kitchen_id"], partner,
        )


def test_180_21H_06_corrected_end_bce_pinned() -> None:
    """21H.06 Djed-Khons-ef-ankh: Kitchen's printed `end_bce=-1056` is
    a typographic reversal; the corrected value is `-1045` (predecessor
    Masaharta ends 1046, successor Menkheperre starts 1045, length 1y).
    The typed `corrected_end_bce` field replaces the hardcoded
    DKF_INTERVAL Python constant + notes-prose explanation."""
    r = _row("21H.06")
    assert r["end_bce"] == -1056  # verbatim
    assert r["corrected_end_bce"] == -1045  # the typed correction


def test_180_25_03_piankhy_two_prenomens() -> None:
    """25.03 Piankhy: Kitchen's `Usimare, then Sneferre` decomposes to
    a typed prenomens list with `when` markers. The legacy `prenomen`
    scalar still carries the comma-string for backwards compat."""
    r = _row("25.03")
    assert r["prenomens"] == [
        {"name": "Usimare", "when": "initial"},
        {"name": "Sneferre", "when": "later"},
    ]


def test_180_corrected_end_bce_only_for_known_typo() -> None:
    """Only 21H.06 has a corrected_end_bce. Every other row must carry
    None — silent additions of further `corrected_end_bce` overrides
    must be deliberate and tracked here."""
    for r in _rows():
        if r["kitchen_id"] == "21H.06":
            continue
        assert r["corrected_end_bce"] is None, (r["kitchen_id"], r["corrected_end_bce"])


def test_180_fix_rows_is_file_level_idempotent() -> None:
    """Run fix_rows.py twice in a temporary copy and assert byte-equality
    of the output JSONL. Per the Beckerath #179 regression pattern."""
    import shutil
    import subprocess
    import sys
    import tempfile
    src_dir = (
        Path(__file__).parent.parent
        / "pipeline"
        / "authority"
        / "sources"
        / "kitchen-tipe"
    )
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str) / "src"
        shutil.copytree(src_dir, tmp)
        for _ in range(2):
            subprocess.run(
                [sys.executable, str(tmp / "fix_rows.py")],
                check=True,
                capture_output=True,
            )
        run1 = (tmp / "reconciled.jsonl").read_bytes()
        subprocess.run(
            [sys.executable, str(tmp / "fix_rows.py")],
            check=True,
            capture_output=True,
        )
        run2 = (tmp / "reconciled.jsonl").read_bytes()
        assert run1 == run2, (
            "fix_rows.py is NOT byte-idempotent — re-running on a "
            "fully-migrated reconciled.jsonl produced different bytes."
        )
