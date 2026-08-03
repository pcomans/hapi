"""Tests for the claim-graph source adapters (ADR-018/020).

The loaders are the boundary where a scholarly source row becomes a graph node, so the
constitutional rules bite hardest here:

  * Rule 2 — no silent coercion. A field of the wrong type, a missing stable id, a missing
    display name, or a half-populated chronology pair RAISES with source id, row id and
    field path. It is never turned into ``None``/``[]``/``"<source>-None"``.
  * Rule 6 — the only rows that may be skipped are ones the source itself marks as
    non-rulers, and those are reported in the load result, never dropped silently.
  * Rule 5 — the real committed sources are loaded and their exact record counts asserted,
    so a loader that starts swallowing rows fails here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.authority.claimgraph.graph_ir import build_documentary_graph
from pipeline.authority.claimgraph.sources import (
    SourceRowError,
    load_all_sources,
    load_beckerath,
    load_kitchen,
    load_leprohon,
    load_pharaoh_se,
    load_ryholt,
)

AUTHORITY_ROOT = Path(__file__).resolve().parents[1] / "pipeline" / "authority" / "sources"

_DIRS = {
    "leprohon": "leprohon-2013-titulary",
    "beckerath": "beckerath-1997-chronologie",
    "kitchen": "kitchen-tipe",
    "pharaoh_se": "pharaoh-se",
    "ryholt": "ryholt-1997-sip",
}
_LOADERS = {
    "leprohon": load_leprohon,
    "beckerath": load_beckerath,
    "kitchen": load_kitchen,
    "pharaoh_se": load_pharaoh_se,
    "ryholt": load_ryholt,
}


def _write(root: Path, source: str, rows: list[dict]) -> Path:
    d = root / _DIRS[source]
    d.mkdir(parents=True, exist_ok=True)
    (d / "reconciled.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )
    return root


def _load(tmp_path: Path, source: str, rows: list[dict]):
    return _LOADERS[source](_write(tmp_path, source, rows))


# --- the committed sources load exactly as expected -------------------------


def test_all_committed_sources_load_with_exact_counts():
    load = load_all_sources(AUTHORITY_ROOT)
    assert load.per_source == {
        "leprohon": 395,
        "beckerath": 166,
        "kitchen": 60,
        "pharaoh_se": 381,
        "ryholt": 157,
    }
    assert len(load.records) == 1159
    # the ONLY rows not loaded as rulers are Beckerath's 8 period headers, and they are
    # reported by id — the drop report the module promises.
    assert set(load.non_ruler_rows) == {"beckerath"}
    dropped = load.non_ruler_rows["beckerath"]
    assert [rid for rid, _ in dropped] == [
        "00.01", "07.01", "08.01", "09.01", "13.01", "14.01", "16.01", "17.01",
    ]
    assert {why for _, why in dropped} == {"is_dynasty_marker (period header, not a ruler)"}


def test_committed_sources_have_unique_prefixed_local_ids():
    load = load_all_sources(AUTHORITY_ROOT)
    ids = [r.local_id for r in load.records]
    assert len(set(ids)) == len(ids)
    assert all(r.local_id.startswith(f"{r.source_id}-") for r in load.records)
    assert not any(r.local_id.endswith("-None") for r in load.records)


def test_committed_intra_source_identities_all_resolve():
    """Kitchen's four `same_person_as` assertions must all resolve to loaded records —
    build_documentary_graph raises on a dangling one, so this pins that they do."""
    load = load_all_sources(AUTHORITY_ROOT)
    doc = build_documentary_graph(load.records)
    assert sorted((i.subject_id, i.object_id) for i in doc.intra_source_identities) == [
        ("kitchen-21H.03", "kitchen-21H.04"),
        ("kitchen-21H.04", "kitchen-21H.03"),
        ("kitchen-24.01", "kitchen-24E.04"),
        ("kitchen-24E.04", "kitchen-24.01"),
    ]


def test_dangling_intra_source_identity_raises():
    """A sourced identity assertion pointing at an unloaded row is a bug in the loader or
    the source row — it must surface, not be dropped (the assertion would vanish)."""
    load = load_all_sources(AUTHORITY_ROOT)
    records = [r for r in load.records if r.local_id != "kitchen-21H.04"]
    with pytest.raises(ValueError, match="kitchen-21H.04"):
        build_documentary_graph(records)


# --- stable ids and display names are required ------------------------------


_MINIMAL = {
    "leprohon": {"leprohon_id": "1.01", "display_name": "Narmer"},
    "beckerath": {"beckerath_id": "01.01", "name": "Narmer"},
    "kitchen": {"kitchen_id": "21.01", "name": "Smendes"},
    "pharaoh_se": {"slug": "narmer", "display": "Narmer"},
    "ryholt": {"ryholt_id": "13.01", "nomen": "Sobekhotep"},
}
_ID_FIELD = {
    "leprohon": "leprohon_id",
    "beckerath": "beckerath_id",
    "kitchen": "kitchen_id",
    "pharaoh_se": "slug",
    "ryholt": "ryholt_id",
}
_NAME_FIELD = {
    "leprohon": "display_name",
    "beckerath": "name",
    "kitchen": "name",
    "pharaoh_se": "display",
    "ryholt": "nomen",
}


@pytest.mark.parametrize("source", sorted(_MINIMAL))
def test_minimal_row_loads(tmp_path, source):
    load = _load(tmp_path, source, [dict(_MINIMAL[source])])
    assert [r.local_id for r in load.records] == [
        f"{source}-{_MINIMAL[source][_ID_FIELD[source]]}"
    ]
    assert load.records[0].display_name == _MINIMAL[source][_NAME_FIELD[source]]
    assert load.non_ruler_rows == []


@pytest.mark.parametrize("source", sorted(_MINIMAL))
@pytest.mark.parametrize("bad_id", [None, "", "   "])
def test_missing_stable_id_raises(tmp_path, source, bad_id):
    """Regression (codex P1): a row without its stable id used to become
    ``<source>-None``, and several such rows then collided on the web primary key."""
    row = dict(_MINIMAL[source])
    row[_ID_FIELD[source]] = bad_id
    with pytest.raises(SourceRowError, match=_ID_FIELD[source]):
        _load(tmp_path, source, [row])


@pytest.mark.parametrize("source", sorted(_MINIMAL))
def test_missing_display_name_raises(tmp_path, source):
    """Regression (codex P1): a nameless row used to be dropped silently while the module
    claimed drops were reported."""
    row = dict(_MINIMAL[source])
    row[_NAME_FIELD[source]] = None
    with pytest.raises(SourceRowError):
        _load(tmp_path, source, [row])


def test_ryholt_falls_back_to_the_prenomen_for_a_display_name(tmp_path):
    """Ryholt has no display field: the nomen is preferred, the prenomen is the documented
    fallback, and a row with neither raises rather than being dropped."""
    load = _load(tmp_path, "ryholt", [{"ryholt_id": "13.02", "prenomen": "Sekhemre"}])
    assert [r.display_name for r in load.records] == ["Sekhemre"]


# --- schema drift raises, absence does not ----------------------------------


@pytest.mark.parametrize(
    ("source", "field", "value"),
    [
        ("leprohon", "dynasty_number", "26"),  # the codex P2 example: int → str
        ("leprohon", "dynasty_label", 26),
        ("leprohon", "alt_display_names", "Menes"),  # str where a list is expected
        ("leprohon", "alt_display_names", [None]),
        ("leprohon", "throne_names", "Narmer"),
        ("leprohon", "throne_names", ["Narmer"]),  # str entry where an object is expected
        ("beckerath", "dynasty", "1"),
        ("beckerath", "name_variants", [1]),
        ("beckerath", "egyptian_titularies", [{"kind": "prenomen"}]),
        ("kitchen", "start_bce", "1069"),
        ("kitchen", "prenomens", [{"when": "later"}]),
        ("pharaoh_se", "dynasty_number", "1"),
        ("pharaoh_se", "start_year", 3000.5),
        ("pharaoh_se", "horus_names", [{"gardiner": "G5"}]),  # no name, no transliteration
        ("ryholt", "dynasty", "13"),
        ("ryholt", "date_bce_start", True),  # bool is not a year
    ],
)
def test_schema_drift_raises(tmp_path, source, field, value):
    row = dict(_MINIMAL[source])
    row[field] = value
    with pytest.raises(SourceRowError):
        _load(tmp_path, source, [row])


@pytest.mark.parametrize("source", sorted(_MINIMAL))
def test_absent_nullable_fields_stay_none(tmp_path, source):
    """Rule 4 of the project rules: sparse records are valid. Absence is not drift."""
    row = dict(_MINIMAL[source])
    row.update({k: None for k in ("dynasty", "dynasty_number", "dynasty_label")})
    rec = _load(tmp_path, source, [row]).records[0]
    assert rec.dynasty is None
    assert rec.dynasty_label is None


# --- Beckerath chronology bounds --------------------------------------------


def test_beckerath_uses_the_documented_low_bound(tmp_path):
    rec = _load(
        tmp_path,
        "beckerath",
        [
            dict(
                _MINIMAL["beckerath"],
                start_bce_low=-2982,
                start_bce_high=-3032,
                end_bce_low=-2950,
                end_bce_high=-3000,
            )
        ],
    ).records[0]
    assert rec.reign_start_bce == -2982
    assert rec.reign_end_bce == -2950


def test_beckerath_absent_chronology_stays_none(tmp_path):
    rec = _load(
        tmp_path,
        "beckerath",
        [
            dict(
                _MINIMAL["beckerath"],
                start_bce_low=None,
                start_bce_high=None,
                end_bce_low=None,
                end_bce_high=None,
            )
        ],
    ).records[0]
    assert rec.reign_start_bce is None
    assert rec.reign_end_bce is None


@pytest.mark.parametrize(
    "bounds",
    [
        {"start_bce_low": -2982, "start_bce_high": None},
        {"start_bce_low": None, "start_bce_high": -3032},
    ],
)
def test_beckerath_half_populated_bound_pair_raises(tmp_path, bounds):
    """`low or high` used to silently pick whichever bound existed (and to treat year 0 as
    absent). A half-populated pair is ambiguous and must raise."""
    with pytest.raises(SourceRowError, match="start_bce_low/start_bce_high"):
        _load(tmp_path, "beckerath", [dict(_MINIMAL["beckerath"], **bounds)])


def test_beckerath_year_zero_is_a_date_not_an_absence(tmp_path):
    rec = _load(
        tmp_path,
        "beckerath",
        [dict(_MINIMAL["beckerath"], start_bce_low=0, start_bce_high=-50)],
    ).records[0]
    assert rec.reign_start_bce == 0


# --- explicitly-classified non-ruler rows are reported, not swallowed -------


def test_beckerath_dynasty_marker_is_reported_as_a_non_ruler(tmp_path):
    load = _load(
        tmp_path,
        "beckerath",
        [
            dict(_MINIMAL["beckerath"]),
            {"beckerath_id": "00.01", "name": "0. Dynastie", "is_dynasty_marker": True},
        ],
    )
    assert [r.local_id for r in load.records] == ["beckerath-01.01"]
    assert load.non_ruler_rows == [
        ("00.01", "is_dynasty_marker (period header, not a ruler)")
    ]


def test_beckerath_dynasty_marker_still_needs_its_stable_id(tmp_path):
    with pytest.raises(SourceRowError, match="beckerath_id"):
        _load(tmp_path, "beckerath", [{"name": "0. Dynastie", "is_dynasty_marker": True}])


def test_duplicate_local_ids_across_sources_raise(tmp_path):
    """The local_id is the web artifact's PRIMARY KEY — a collision must never ship."""
    for source in _MINIMAL:
        _write(tmp_path, source, [dict(_MINIMAL[source])])
    _write(
        tmp_path,
        "kitchen",
        [dict(_MINIMAL["kitchen"]), dict(_MINIMAL["kitchen"], name="Smendes (dup)")],
    )
    with pytest.raises(ValueError, match="Duplicate ruler local_id"):
        load_all_sources(tmp_path)
