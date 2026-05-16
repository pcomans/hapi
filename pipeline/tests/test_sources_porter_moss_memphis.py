"""Structural + content tests for the Porter-Moss Vol III (Memphis) extract.

Per CLAUDE.md rule 5: every populated field on every fixture-class row is
asserted, not just the field the test class is "themed" around.

Chunk 1 covers the three Gîza pyramid complexes (Khufu G1, Khephren G2,
Menkaureʿ G3) and their attested queens' subsidiary pyramids. 10 rows total
from PM III.1 § I "PYRAMIDS", physical pp.8–32 / printed pp.11–35.
"""

from __future__ import annotations

import importlib.util
import json
import re
from functools import lru_cache
from pathlib import Path

SOURCE_DIR = (
    Path(__file__).parent.parent
    / "pipeline"
    / "authority"
    / "sources"
    / "porter-moss-memphis"
)
JSONL = SOURCE_DIR / "reconciled.jsonl"

EDITION_PM_III_1 = "PM III.1 2nd ed. 1974"


CHUNK1_TOMB_IDS: frozenset[str] = frozenset({
    "G1", "G1a", "G1b", "G1c",
    "G2", "G2a",
    "G3", "G3a", "G3b", "G3c",
})

EXPECTED_TOMB_IDS: frozenset[str] = CHUNK1_TOMB_IDS


@lru_cache(maxsize=1)
def _rows() -> list[dict]:
    return [json.loads(line) for line in JSONL.read_text().splitlines() if line.strip()]


def _by_id(tid: str) -> dict:
    for row in _rows():
        if row["tomb_id"] == tid:
            return row
    raise AssertionError(f"tomb_id {tid!r} not in reconciled.jsonl")


# === structural tests =======================================================


def test_row_count_matches_expected_set() -> None:
    assert len(_rows()) == len(EXPECTED_TOMB_IDS)


def test_tomb_ids_match_expected_set() -> None:
    assert {r["tomb_id"] for r in _rows()} == EXPECTED_TOMB_IDS


def test_tomb_id_is_unique() -> None:
    ids = [r["tomb_id"] for r in _rows()]
    assert len(ids) == len(set(ids))


# Reisner G-number form: prefix `G`, 1+ digits, optional lowercase letter OR
# trailing capital X (Reisner's `G7000X` convention). The PM-Memphis chunk 1
# only emits the `G<num>` / `G<num><lower>` shapes; the capital-X tail is
# pre-registered for chunk 3+ (Cemetery G 7000X Hetepheres).
_TOMB_ID_RE = re.compile(r"^(?P<prefix>[A-Z]+)(?P<num>\d+)(?P<suffix>[a-zA-Z]?)$")


def test_tomb_id_shape() -> None:
    for tid in EXPECTED_TOMB_IDS:
        assert _TOMB_ID_RE.match(tid), tid


def test_prefix_vocabulary_consistent() -> None:
    """`merge.AREA_ORDER` keys must equal the prefix set this test recognises
    AND the prefix set actually present in `reconciled.jsonl`.

    Mirrors `porter-moss-theban-necropolis` precedent — keeping the merge
    sort-order dict and the test regex in lockstep ensures a chunk that
    introduces a new prefix (e.g. `D` for Mariette-Saqqara, `LS` for Lepsius)
    cannot land without extending both pieces of machinery. Tightened from
    subset to equality per PR #217 code-reviewer P2 — a stale entry in
    `AREA_ORDER` that no row uses should also surface.
    """
    spec = importlib.util.spec_from_file_location(
        "merge_pm_memphis",
        SOURCE_DIR / "merge.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Derive prefixes from the JSONL itself, not from a hand-maintained
    # constant — the only source of truth is what's committed.
    prefixes_in_data = set()
    for row in _rows():
        m = _TOMB_ID_RE.match(row["tomb_id"])
        assert m is not None, row["tomb_id"]
        prefixes_in_data.add(m.group("prefix"))

    declared_prefixes = set(module.AREA_ORDER.keys())
    assert prefixes_in_data == declared_prefixes, (
        f"reconciled.jsonl uses prefixes {sorted(prefixes_in_data)} but "
        f"merge.AREA_ORDER declares {sorted(declared_prefixes)} — must be "
        f"identical sets, not subset"
    )


def test_tomb_id_regex_accepts_reisner_extension_form() -> None:
    """Reisner's `G7000X` (Hetepheres I shaft tomb, future chunks) — the
    trailing capital X is the published convention and the regex must
    accept it. Pre-PR-#217 the suffix group was `[a-z]?|[A-Z]?` which
    matched correctly but read non-idiomatically; the post-fix regex
    `[a-zA-Z]?` should preserve acceptance."""
    m = _TOMB_ID_RE.match("G7000X")
    assert m is not None
    assert m.group("prefix") == "G"
    assert m.group("num") == "7000"
    assert m.group("suffix") == "X"


def test_tomb_id_regex_rejects_two_suffix_letters() -> None:
    """`G1aB` is malformed — Reisner uses exactly one suffix character
    (lowercase for subsidiary pyramids, uppercase X for extensions).
    Regression-pin for the `[a-zA-Z]?` quantifier ('?' = zero or one,
    not '*' = zero or more)."""
    assert _TOMB_ID_RE.match("G1aB") is None
    assert _TOMB_ID_RE.match("G1ab") is None


# === required-field + controlled-vocab tests ================================


_REQUIRED_KEYS = frozenset({
    "tomb_id", "memphite_area", "occupant_name", "occupant_alt_names",
    "tomb_aliases", "co_occupants", "is_joint_burial", "occupant_role",
    "dynasty", "sub_period", "date_bce_approx_start", "date_bce_approx_end",
    "cemetery", "discovery_year", "discoverer", "is_unfinished",
    "is_uninscribed", "is_usurped", "attribution_certainty",
    "shared_with_tombs", "notes_from_pm", "source_citation",
})


def test_required_fields_present_on_every_row() -> None:
    for row in _rows():
        missing = _REQUIRED_KEYS - row.keys()
        assert not missing, f"{row['tomb_id']} missing keys: {sorted(missing)}"
        extra = row.keys() - _REQUIRED_KEYS
        assert not extra, f"{row['tomb_id']} has unexpected keys: {sorted(extra)}"


_VALID_ROLES = frozenset({
    "King", "Queen", "Royal Family", "Vizier", "Official", "High Priest",
    "Princess", "Prince", "Unknown",
})


def test_occupant_role_controlled_vocab() -> None:
    for row in _rows():
        assert row["occupant_role"] in _VALID_ROLES, row


_VALID_CERTAINTY = frozenset({"attested", "probable", "uncertain"})


def test_attribution_certainty_controlled_vocab() -> None:
    for row in _rows():
        assert row["attribution_certainty"] in _VALID_CERTAINTY, row


def test_memphite_area_is_giza_in_chunk1() -> None:
    """All chunk-1 rows are PYRAMID-FIELD OF GÎZA. Future chunks extend the
    Memphite-area vocabulary (Saqqara, Abusir, Dahshur, …)."""
    for row in _rows():
        assert row["memphite_area"] == "Giza", row


def test_source_citation_shape() -> None:
    for row in _rows():
        cit = row["source_citation"]
        assert set(cit.keys()) == {"page", "edition", "section"}, cit
        assert isinstance(cit["page"], int), cit
        assert cit["edition"] == EDITION_PM_III_1, cit
        assert cit["section"] == "I", cit


def test_source_citation_page_in_chunk1_range() -> None:
    """Printed page range for chunk 1 is 11–35 (PM III.1 § I PYRAMIDS)."""
    for row in _rows():
        page = row["source_citation"]["page"]
        assert 11 <= page <= 35, f"{row['tomb_id']} page {page} outside [11, 35]"


# === Phase-0 boundary assertions ============================================


def test_bce_dates_null_at_extraction_stage() -> None:
    """Per CLAUDE.md rules 1 + 7, BCE dates come from king authority at Phase A,
    not from PM headwords (PM does not print BCE reign ranges)."""
    for row in _rows():
        assert row["date_bce_approx_start"] is None, row
        assert row["date_bce_approx_end"] is None, row


def test_cemetery_null_for_pyramid_complex_chunk() -> None:
    """Chunk 1 is the three pyramid complexes themselves — the pyramid IS
    its own complex. Cemetery designation belongs to surrounding mastabas,
    which will land in chunk 2+."""
    for row in _rows():
        assert row["cemetery"] is None, row


def test_dynasty_is_four_for_chunk1() -> None:
    """PM III.1 prints `Dyn. IV` under every chunk-1 pyramid-complex section
    heading (Khufu, Khephren, Menkaureʿ all Dyn IV). Roman→Arabic
    normalisation gives `"4"`."""
    for row in _rows():
        assert row["dynasty"] == "4", row


# === content / value assertions =============================================


def test_chunk1_g1_khufu() -> None:
    row = _by_id("G1")
    assert row == {
        "tomb_id": "G1",
        "memphite_area": "Giza",
        "occupant_name": "Khufu",
        "occupant_alt_names": [],
        "tomb_aliases": ["Great Pyramid", "First Pyramid"],
        "co_occupants": [],
        "is_joint_burial": False,
        "occupant_role": "King",
        "dynasty": "4",
        "sub_period": None,
        "date_bce_approx_start": None,
        "date_bce_approx_end": None,
        "cemetery": None,
        "discovery_year": None,
        "discoverer": None,
        "is_unfinished": False,
        "is_uninscribed": False,
        "is_usurped": False,
        "attribution_certainty": "attested",
        "shared_with_tombs": [],
        "notes_from_pm": "Lepsius, IV; Perring and Vyse, I of Giza; Reisner, G I; called Great or First Pyramid.",
        "source_citation": {"page": 13, "edition": EDITION_PM_III_1, "section": "I"},
    }


def test_chunk1_g2_khephren() -> None:
    row = _by_id("G2")
    assert row["occupant_name"] == "Khephren"
    assert row["occupant_role"] == "King"
    assert row["attribution_certainty"] == "attested"
    assert row["tomb_aliases"] == ["Second Pyramid"]
    assert "Reisner, G II" in row["notes_from_pm"]
    assert "G 11" not in row["notes_from_pm"]  # post-fix_rows OCR-drift check


def test_chunk1_g3_menkaure() -> None:
    row = _by_id("G3")
    assert row["occupant_name"] == "Menkaureʿ"  # ayin U+02BF
    assert row["occupant_role"] == "King"
    assert row["attribution_certainty"] == "attested"
    assert row["tomb_aliases"] == ["Third Pyramid"]
    assert "Reisner, G III" in row["notes_from_pm"]
    assert "G 111" not in row["notes_from_pm"]  # post-fix_rows OCR-drift check


def test_chunk1_g1c_henutsen_attribution() -> None:
    """G1c Khufu South Subsidiary Pyramid — PM 1974 attributes to Henutsen.

    PM's text-layer carries `Attributed to Henutsen (wife of Khufu).` in the
    headword block. All three extraction agents extracted this attribution
    correctly, overriding the prompt's incorrect "PM 1974 names no subsidiary
    occupants" structural claim per CLAUDE.md rule 1. Verified by the
    egyptologist-reviewer pass against the printed source.

    Full-row equality per PR #217 code-reviewer P2 (Henutsen is the
    flagship row from the egyptologist pass; deserves the same coverage
    as G1).
    """
    row = _by_id("G1c")
    assert row == {
        "tomb_id": "G1c",
        "memphite_area": "Giza",
        "occupant_name": "Henutsen",
        "occupant_alt_names": [],
        "tomb_aliases": [],
        "co_occupants": [],
        "is_joint_burial": False,
        "occupant_role": "Queen",
        "dynasty": "4",
        "sub_period": None,
        "date_bce_approx_start": None,
        "date_bce_approx_end": None,
        "cemetery": None,
        "discovery_year": None,
        "discoverer": None,
        "is_unfinished": False,
        "is_uninscribed": False,
        "is_usurped": False,
        "attribution_certainty": "probable",
        "shared_with_tombs": [],
        "notes_from_pm": "South Subsidiary Pyramid. Lepsius, VII; Perring and Vyse, 9 of Giza; Reisner, G I-c. Attributed to Henutsen (wife of Khufu).",
        "source_citation": {"page": 16, "edition": EDITION_PM_III_1, "section": "I"},
    }


def test_chunk1_g3a_fourth_pyramid_full_row() -> None:
    """G3a East Subsidiary Pyramid — second edge-case row from the
    egyptologist pass, full-row equality per PR #217 code-reviewer P2.
    PM's `sometimes called Fourth Pyramid.` clause populates `tomb_aliases`."""
    row = _by_id("G3a")
    assert row == {
        "tomb_id": "G3a",
        "memphite_area": "Giza",
        "occupant_name": None,
        "occupant_alt_names": [],
        "tomb_aliases": ["Fourth Pyramid"],
        "co_occupants": [],
        "is_joint_burial": False,
        "occupant_role": "Queen",
        "dynasty": "4",
        "sub_period": None,
        "date_bce_approx_start": None,
        "date_bce_approx_end": None,
        "cemetery": None,
        "discovery_year": None,
        "discoverer": None,
        "is_unfinished": False,
        "is_uninscribed": False,
        "is_usurped": False,
        "attribution_certainty": "uncertain",
        "shared_with_tombs": [],
        "notes_from_pm": "East Subsidiary Pyramid. Lepsius, XII; Perring and Vyse, 5 of Giza; Reisner, G III-a; sometimes called Fourth Pyramid.",
        "source_citation": {"page": 34, "edition": EDITION_PM_III_1, "section": "I"},
    }


def test_chunk1_subsidiary_pyramids_are_queens() -> None:
    """The seven subsidiary pyramid rows (G<num><letter>) all have role
    `Queen` per PM's convention for subsidiary pyramids in a king's pyramid
    complex."""
    subsidiary_ids = {
        tid for tid in CHUNK1_TOMB_IDS
        if _TOMB_ID_RE.match(tid).group("suffix") not in (None, "")
    }
    assert subsidiary_ids == {"G1a", "G1b", "G1c", "G2a", "G3a", "G3b", "G3c"}
    for tid in subsidiary_ids:
        row = _by_id(tid)
        assert row["occupant_role"] == "Queen", row


def test_chunk1_anonymous_subsidiary_pyramids_are_uncertain() -> None:
    """Of the seven subsidiary pyramids, six have no occupant named in PM's
    headword (G1a, G1b, G2a, G3a, G3b, G3c). These carry `occupant_name: null`
    and `attribution_certainty: "uncertain"` per the prompt's hedge rule
    (silent attribution = uncertain). G1c (Henutsen) is the exception —
    attested but hedged via "Attributed to".
    """
    anonymous = {"G1a", "G1b", "G2a", "G3a", "G3b", "G3c"}
    for tid in anonymous:
        row = _by_id(tid)
        assert row["occupant_name"] is None, row
        assert row["attribution_certainty"] == "uncertain", row


# === regression tests against fix_rows.py OCR-drift correction ==============


def test_fix_rows_is_idempotent_on_substantive_input(tmp_path, monkeypatch) -> None:
    """`fix_rows.py` must be byte-identical across consecutive runs even
    when there is OCR-drift to apply (not just empirically because
    `CHUNK1_CORRECTIONS` is empty). Constitutional rule 2 + playbook
    idempotence guard. Code-reviewer P1 on PR #217.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "pm_memphis_fix_rows",
        SOURCE_DIR / "fix_rows.py",
    )
    assert spec is not None and spec.loader is not None
    fix_rows = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fix_rows)

    # Pre-fix-state fixture: two rows, one with the `G 11`/`G 111` OCR drift
    # that fix_rows.py should normalise, plus a pre-existing audit-trail
    # section the guard must strip before re-appending.
    pre_reconciled = (
        json.dumps({"tomb_id": "G2", "notes_from_pm": "Reisner, G 11"}, sort_keys=True)
        + "\n"
        + json.dumps({"tomb_id": "G3", "notes_from_pm": "Reisner, G 111"}, sort_keys=True)
        + "\n"
    )
    pre_diff = (
        "G3a (None):\n  notes_from_pm: a=\"x\" | b=\"y\" | c=\"x\"  → chose \"x\"\n"
    )

    fake_reconciled = tmp_path / "reconciled.jsonl"
    fake_diff = tmp_path / "merge-disagreements.txt"
    fake_reconciled.write_text(pre_reconciled, encoding="utf-8")
    fake_diff.write_text(pre_diff, encoding="utf-8")

    monkeypatch.setattr(fix_rows, "RECONCILED", fake_reconciled)
    monkeypatch.setattr(fix_rows, "DIFF", fake_diff)

    fix_rows.main()
    after_run_1_reconciled = fake_reconciled.read_text(encoding="utf-8")
    after_run_1_diff = fake_diff.read_text(encoding="utf-8")

    # Sanity: run 1 actually applied substantive fixes (otherwise the
    # idempotence assertion below would pass vacuously).
    assert "Reisner, G II" in after_run_1_reconciled
    assert "Reisner, G III" in after_run_1_reconciled
    assert "LLM-APPLIED OVERRIDES" in after_run_1_diff

    fix_rows.main()
    after_run_2_reconciled = fake_reconciled.read_text(encoding="utf-8")
    after_run_2_diff = fake_diff.read_text(encoding="utf-8")

    assert after_run_1_reconciled == after_run_2_reconciled, (
        "fix_rows.py is not idempotent on reconciled.jsonl"
    )
    assert after_run_1_diff == after_run_2_diff, (
        "fix_rows.py is not idempotent on merge-disagreements.txt — the "
        "audit-trail section must be stripped before re-appending."
    )
    # The pre-existing audit-trail prefix in the merge-disagreements fixture
    # is preserved across both runs (only the auto-appended section after
    # the marker is rewritten).
    assert after_run_2_diff.startswith("G3a (None):\n"), after_run_2_diff


def test_notes_from_pm_carries_pm_faithful_roman_numerals() -> None:
    """`fix_rows.py` rewrites text-layer `G 11` / `G 111` → `G II` / `G III`
    to match what PM III prints (verified against the PDF by the egyptologist-
    reviewer pass). Regression test ensures the substitution stuck and no
    future merge inadvertently reverts.
    """
    for row in _rows():
        notes = row["notes_from_pm"] or ""
        assert "Reisner, G 11" not in notes, row
        assert "Reisner, G 111" not in notes, row
        # The PM-faithful Roman forms ARE present on the expected rows.
        if row["tomb_id"] in {"G2", "G2a"}:
            assert "Reisner, G II" in notes, row
        if row["tomb_id"] in {"G3", "G3a", "G3b", "G3c"}:
            assert "Reisner, G III" in notes, row
