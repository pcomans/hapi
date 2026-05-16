"""Structural + content tests for the Porter-Moss Vol III (Memphis) extract.

Per CLAUDE.md rule 5: every populated field on every fixture-class row is
asserted, not just the field the test class is "themed" around.

Chunk 1 covers the three Gîza pyramid complexes (Khufu G1, Khephren G2,
Menkaureʿ G3) and their attested queens' subsidiary pyramids. 10 rows total
from PM III.1 § I "PYRAMIDS", physical pp.8–32 / printed pp.11–35.

Chunk 2 covers the Gîza Cemetery G 7000 East Field royal-family mastaba
cluster (Hetepheres I G7000x, Kawab G7120, Khufukhaef I G7140, etc.).
13 rows from PM III.1 § III "NECROPOLIS — B. EAST FIELD",
physical pp.176–187 / printed pp.179–190.
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

# Chunk 2: Cemetery G 7000 East Field royal-family mastaba cluster.
# Source: PM III.1 2nd ed. 1974, § III. NECROPOLIS — B. EAST FIELD,
# physical pp.176–187 / printed pp.179–190.
CHUNK2_TOMB_IDS: frozenset[str] = frozenset({
    "G7000x",                                     # Hetepheres I shaft tomb
    "G7050", "G7060", "G7070", "G7101", "G7102",  # singles
    "G7110", "G7120",                             # twin Hetepheres II / Kawab
    "G7130", "G7140",                             # twin Nefertkau / Khufukhaef I
    "G7112", "G7142",                             # bare-headword shafts
    "G7150",                                      # Khufukhaef II
})

EXPECTED_TOMB_IDS: frozenset[str] = CHUNK1_TOMB_IDS | CHUNK2_TOMB_IDS


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


_VALID_SECTIONS = frozenset({"I", "III"})


def test_source_citation_shape() -> None:
    for row in _rows():
        cit = row["source_citation"]
        assert set(cit.keys()) == {"page", "edition", "section"}, cit
        assert isinstance(cit["page"], int), cit
        assert cit["edition"] == EDITION_PM_III_1, cit
        assert cit["section"] in _VALID_SECTIONS, cit


def test_source_citation_section_matches_chunk() -> None:
    """Chunk 1 rows cite `section: "I"` (§ I. PYRAMIDS). Chunk 2 rows cite
    `section: "III"` (§ III. NECROPOLIS, sub-letter B. EAST FIELD is implicit
    in `cemetery: "G 7000"`)."""
    for row in _rows():
        if row["tomb_id"] in CHUNK1_TOMB_IDS:
            assert row["source_citation"]["section"] == "I", row
        elif row["tomb_id"] in CHUNK2_TOMB_IDS:
            assert row["source_citation"]["section"] == "III", row


def test_source_citation_page_in_expected_range() -> None:
    """Printed page ranges: chunk 1 = 11–35, chunk 2 = 179–190."""
    for row in _rows():
        page = row["source_citation"]["page"]
        if row["tomb_id"] in CHUNK1_TOMB_IDS:
            assert 11 <= page <= 35, f"{row['tomb_id']} page {page} outside chunk-1 [11, 35]"
        elif row["tomb_id"] in CHUNK2_TOMB_IDS:
            assert 179 <= page <= 190, f"{row['tomb_id']} page {page} outside chunk-2 [179, 190]"


# === Phase-0 boundary assertions ============================================


def test_bce_dates_null_at_extraction_stage() -> None:
    """Per CLAUDE.md rules 1 + 7, BCE dates come from king authority at Phase A,
    not from PM headwords (PM does not print BCE reign ranges)."""
    for row in _rows():
        assert row["date_bce_approx_start"] is None, row
        assert row["date_bce_approx_end"] is None, row


def test_cemetery_null_for_chunk1_and_g7000_for_chunk2() -> None:
    """Chunk 1 (pyramid-complex rows) carries `cemetery: null` — the pyramid
    IS its own complex. Chunk 2 (East Field mastabas) carries
    `cemetery: "G 7000"` per PM's `CEMETERY G 7000` banner on printed p.182."""
    for row in _rows():
        if row["tomb_id"] in CHUNK1_TOMB_IDS:
            assert row["cemetery"] is None, row
        elif row["tomb_id"] in CHUNK2_TOMB_IDS:
            assert row["cemetery"] == "G 7000", row


def test_dynasty_assignments() -> None:
    """Chunk 1 (all three pyramid complexes) is Dyn. IV → `"4"`.
    Chunk 2 spans Dyn. IV (royal-family core), Dyn. V (later officials),
    and Dyn. VI (Pepy I priestly clientele on G7101, G7102).
    Bare-headword shafts G7112 / G7142 carry `dynasty: null` (PM gives
    no dating line).
    """
    for row in _rows():
        if row["tomb_id"] in CHUNK1_TOMB_IDS:
            assert row["dynasty"] == "4", row
        elif row["tomb_id"] in {"G7112", "G7142"}:
            assert row["dynasty"] is None, row
        elif row["tomb_id"] in CHUNK2_TOMB_IDS:
            assert row["dynasty"] in {"4", "5", "6"}, row


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


def test_fix_rows_skips_noop_corrections(tmp_path, monkeypatch) -> None:
    """When a `CHUNK<N>_CORRECTIONS` entry's target value already matches the
    row's current value, fix_rows.py must not record a `X → X` no-op in
    the audit trail. Gemini round-2 PR #217.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "pm_memphis_fix_rows_noop",
        SOURCE_DIR / "fix_rows.py",
    )
    assert spec is not None and spec.loader is not None
    fix_rows = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fix_rows)

    fake_reconciled = tmp_path / "reconciled.jsonl"
    fake_diff = tmp_path / "merge-disagreements.txt"
    fake_reconciled.write_text(
        json.dumps({"tomb_id": "G2", "occupant_name": "Khephren"}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fake_diff.write_text("baseline diff\n", encoding="utf-8")

    monkeypatch.setattr(fix_rows, "RECONCILED", fake_reconciled)
    monkeypatch.setattr(fix_rows, "DIFF", fake_diff)
    monkeypatch.setattr(
        fix_rows,
        "CHUNK1_CORRECTIONS",
        {("G2", "occupant_name"): {"value": "Khephren", "rationale": "PM III.1 p.25"}},
    )

    fix_rows.main()
    after_reconciled = fake_reconciled.read_text(encoding="utf-8")
    after_diff = fake_diff.read_text(encoding="utf-8")

    # Reconciled stays semantically identical.
    assert json.loads(after_reconciled.strip()) == {
        "tomb_id": "G2",
        "occupant_name": "Khephren",
    }
    # No audit-trail section appended because the correction was a no-op.
    assert "LLM-APPLIED OVERRIDES" not in after_diff
    assert after_diff == "baseline diff\n"


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


# === chunk-2 content / value assertions =====================================


def test_chunk2_g7000x_hetepheres_i_full_row() -> None:
    """G 7000X — Hetepheres I shaft tomb (Khufu's mother). PM III.1 § III B.
    EAST FIELD opens with this row on printed p.179. The `1/1/1` tie on
    `notes_from_pm` is broken via `tie-break-overrides.json` with a cited
    rationale (longest faithful capture of the headword block stops before
    the first `REISNER and SMITH,` bibliographic-ribbon line).
    """
    row = _by_id("G7000x")
    assert row == {
        "tomb_id": "G7000x",
        "memphite_area": "Giza",
        "occupant_name": "Hetepheres I",
        "occupant_alt_names": [],
        "tomb_aliases": [],
        "co_occupants": [],
        "is_joint_burial": False,
        "occupant_role": "Queen",
        "dynasty": "4",
        "sub_period": None,
        "date_bce_approx_start": None,
        "date_bce_approx_end": None,
        "cemetery": "G 7000",
        "discovery_year": None,
        "discoverer": None,
        "is_unfinished": False,
        "is_uninscribed": False,
        "is_usurped": False,
        "attribution_certainty": "attested",
        "shared_with_tombs": [],
        "notes_from_pm": (
            "TOMB OF HETEPHERES [I]. Temp. Khufu. Husband, Snefru. Son, Khufu. "
            "No superstructure. Re-burial, transferred from unidentified tomb "
            "probably at Dahshûr. Reisner Excavation. Harvard-Boston Expedition "
            "(1925-7)."
        ),
        "source_citation": {"page": 179, "edition": EDITION_PM_III_1, "section": "III"},
    }


def test_chunk2_twin_mastaba_pairing_g7110_g7120() -> None:
    """G 7110 (Hetepheres II) + G 7120 (Kawab) are twin mastabas in PM's
    compound `G 7110+7120` headword. Each emits its own row with the OTHER
    Reisner number in `shared_with_tombs`. PM lists Kawab as the primary
    occupant (King's eldest son of Khufu); Hetepheres II is his wife (later
    queen via remarriage to King Ra-djedef).
    """
    g7110 = _by_id("G7110")
    g7120 = _by_id("G7120")
    assert g7110["occupant_name"] == "Hetepheres II"
    assert g7110["occupant_role"] == "Queen"
    assert g7110["shared_with_tombs"] == ["G7120"]
    assert g7120["occupant_name"] == "Kawab"
    assert g7120["occupant_role"] == "Prince"
    assert g7120["shared_with_tombs"] == ["G7110"]
    # Architectural link, NOT a joint burial.
    assert g7110["is_joint_burial"] is False
    assert g7120["is_joint_burial"] is False


def test_chunk2_twin_mastaba_pairing_g7130_g7140() -> None:
    """G 7130 (Nefertkau) + G 7140 (Khufukhaef I, King's son and Vizier) —
    second twin-mastaba pair in chunk 2.
    """
    g7130 = _by_id("G7130")
    g7140 = _by_id("G7140")
    assert g7130["occupant_name"] == "Nefertkau"
    assert g7130["shared_with_tombs"] == ["G7140"]
    assert g7140["occupant_name"] == "Khufukhaef I"
    assert g7140["occupant_role"] == "Prince"
    assert g7140["shared_with_tombs"] == ["G7130"]


def test_chunk2_bare_headword_rows_are_unknown_and_uncertain() -> None:
    """G 7112 and G 7142 are PM-printed bare Reisner-number headwords with
    no occupant name. They emit rows with `occupant_name: null`,
    `occupant_role: "Unknown"`, and `attribution_certainty: "uncertain"`.

    Regression-pin for the `merge.SENTINEL_NULL_STRINGS` divergence: PM
    Memphis treats `"Unknown"` as a legitimate controlled-vocab value, NOT
    as a sentinel-null string (unlike the Theban-source merge.py). If a
    future edit re-adds `"unknown"` to that frozenset, these rows would
    collapse `occupant_role` to `None` and break this test.
    """
    for tid in ("G7112", "G7142"):
        row = _by_id(tid)
        assert row["occupant_name"] is None, row
        assert row["occupant_role"] == "Unknown", row
        assert row["attribution_certainty"] == "uncertain", row
        assert row["dynasty"] is None, row
        assert row["notes_from_pm"] is None, row


def test_chunk2_g7060_nefermaet_lg_cross_reference() -> None:
    """G 7060 Nefermaet (King's son, Vizier of Khephren). PM cites the
    Lepsius cross-number `LG 57` in the headword body — extracted into
    `tomb_aliases` for cross-reference to other catalogs that index by
    Lepsius's earlier numbering.
    """
    row = _by_id("G7060")
    assert row["occupant_name"] == "Nefermaet"
    assert row["occupant_role"] == "Prince"
    assert "LG 57" in row["tomb_aliases"]
    assert row["dynasty"] == "4"
    assert row["attribution_certainty"] == "attested"


def test_chunk2_g7150_khufukhaef_ii_late_dynasty_v() -> None:
    """G 7150 Khufukhaef II — PM dates `Temp. Neuserrea` (Neuserre, Dyn V).
    Despite carrying the name of a Dyn-IV royal (Khufukhaef I = G 7140's
    occupant), the [II] regnal-style numbering is for a later official
    whose role is non-royal (`Greatest of the Ten of Upper Egypt`).
    """
    row = _by_id("G7150")
    assert row["occupant_name"] == "Khufukhaef II"
    assert row["occupant_role"] == "Official"
    assert row["dynasty"] == "5"
    assert row["attribution_certainty"] == "attested"


def test_chunk2_dyn_vi_overseer_priests_of_pepy_i() -> None:
    """G 7101 Meryreanufer and G 7102 Idu are Pepy I-period (Dyn VI)
    officials buried in the Khufu-era East Field cemetery — late
    intrusions tied to the Pyramid-of-Pepy-I priestly establishment.
    """
    for tid in ("G7101", "G7102"):
        row = _by_id(tid)
        assert row["dynasty"] == "6", row
        assert row["occupant_role"] == "Official", row
        assert row["attribution_certainty"] == "attested", row


def test_chunk2_g7102_is_idu_not_iou() -> None:
    """G 7102 occupant_name is `"Idu"`, NOT `"Iou"`.

    The pypdf text-layer extraction misread PM's printed `IDU` headword as
    `IOU` (D→O confusion in the all-caps font). All three extraction
    agents inherited the misread and majority-voted `Iou`. The
    egyptologist-reviewer pass verified against the rendered PM III.1
    printed p.185 — the headword unambiguously reads `IDU`. The
    `fix_rows.py` `CHUNK2_CORRECTIONS` table applies the correction with a
    cited rationale (PM III.1 p.185 + Simpson 1980 + the corroborating
    p.184 footnote `Textual evidence also permits Meryrēᶜnūfer Kar to be
    son of Idu (tomb G 7102)`).

    Regression-pin: if a future merge run or refactor reverts this back to
    `Iou`, this test fails loud — a P1-finding from the egyptologist pass
    must not silently regress.
    """
    row = _by_id("G7102")
    assert row["occupant_name"] == "Idu", row
    # The verbatim headword form in notes_from_pm also gets the D restored:
    assert row["notes_from_pm"].startswith("IDU "), row
    assert "IOU" not in (row["notes_from_pm"] or ""), row
