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
from pipeline.authority.claimgraph.normalize import NameForm as NameFormT
from pipeline.authority.claimgraph import sources as sources_mod
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


# --- absence sentinels ------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        # Every distinct whole-field placeholder spelling found by auditing all five
        # claim-graph sources. `unknown (?)` is Leprohon's hedged form (p. 43, Merenre
        # II) and normalises to exactly the same keys as `(unknown)` — the first guard
        # missed it, so that row kept publishing `unknown` as a Horus corroborator.
        "(unknown)",
        "unknown (?)",
        "[Prenomen unknown]",
        "unknown",
        "UNKNOWN",
        " none ",
        "n/a",
        "[lost]",
        "unbekannt",
        "(lacuna)",
    ],
)
def test_absence_placeholders_are_not_names(value):
    """Placeholder prose in a name field says the name is NOT known. Loaded verbatim it
    normalises into matching keys — `(unknown)` → {unknown, nknwn} — so two kings whose
    names are equally unrecorded would corroborate each other into a fabricated identity."""
    assert sources_mod._is_absence_sentinel(value)
    assert sources_mod._name_form(value) is None


@pytest.mark.parametrize(
    "value",
    [
        "[setep] en [ra/imen]",  # Leprohon brackets a RESTORED reading, not an absence
        "heqa khasut aper-an-ti",  # contains 'a'/'an' — a substring rule would eat it
        "mery nefer-kheperu-ra",
        "Nebkheperure",
        "Hor Aha",
        "unknown-sounding-but-real",
        # `////` is Leprohon's epigraphic lacuna marker, not a placeholder: it appears
        # INSIDE genuine names (`Senen////`, `Se /// Kare`) and marks an attested
        # inscription whose signs are destroyed. Deliberately not a sentinel — and the
        # reason `destroyed` is not an alternative in the pattern.
        "////",
        "Senen////",
        # A whole-field `Missing` / `(destroyed)` is likewise NOT classified as an
        # absence. Both occur only in `translation`, which no loader reads; treating
        # them as absences here would guard an unreachable shape and would silently
        # swallow a future extractor bug that put one in a real name field.
        "Missing",
        "(destroyed)",
    ],
)
def test_real_titulary_is_never_mistaken_for_a_placeholder(value):
    """The match is whole-field only. Real titulary contains these letters, and a
    substring rule would silently delete genuine sourced names."""
    assert not sources_mod._is_absence_sentinel(value)
    assert sources_mod._name_form(value) is not None


def test_committed_sources_emit_no_placeholder_names():
    """Every row whose source STATES the name is unknown must reach the graph with no
    such name at all — Leprohon Teti's throne name, Userkare I's and Merenre II's Horus
    names, Kitchen's Takeloth I and Iuput II throne names."""
    loaded = load_all_sources(AUTHORITY_ROOT)
    records = loaded.records if hasattr(loaded, "records") else loaded
    recs = {(r.source_id, r.local_id): r for r in records}
    for key in (
        ("leprohon", "leprohon-leprohon-6.01"),
        ("kitchen", "kitchen-22.04"),
        ("kitchen", "kitchen-23.07"),
    ):
        assert recs[key].prenomina == [], f"{key} should carry no throne name"
    for key in (
        ("leprohon", "leprohon-leprohon-6.02"),
        ("leprohon", "leprohon-leprohon-6.06"),
    ):
        assert recs[key].horus_names == [], f"{key} should carry no Horus name"

    for r in recs.values():
        for form in [*r.prenomina, *r.horus_names, *r.nomina]:
            assert not sources_mod._is_absence_sentinel(form.surface)
            assert not sources_mod._is_absence_sentinel(form.translit)

    # Independent of the classifier. Asking `_is_absence_sentinel` whether the emitted
    # values are placeholders is circular — it passes for any spelling the classifier
    # does not yet know, which is exactly how `unknown (?)` survived the first version
    # of this guard on 9 committed rows. These literals were found by auditing the
    # committed sources directly; add to the list, never derive it from the pattern.
    KNOWN_PLACEHOLDER_LITERALS = {
        "(unknown)",
        "unknown (?)",
        "[prenomen unknown]",
        "unknown",
        "unattested",
        "unbekannt",
        "n/a",
        "none",
        "null",
        "lost",
        "lacuna",
    }
    for r in recs.values():
        for form in [*r.prenomina, *r.horus_names, *r.nomina]:
            for value in (form.surface, form.translit):
                if value is None:
                    continue
                assert value.strip().casefold() not in KNOWN_PLACEHOLDER_LITERALS, (
                    f"{r.source_id}/{r.local_id} emits placeholder prose {value!r} as a name"
                )


@pytest.mark.parametrize("value", ["Na", "na", "Ka", "Iy", "Ay", "In"])
def test_short_real_names_are_not_treated_as_placeholders(value):
    """`n/a` must never be spelled `n/?a`. Bare `na` is a plausible Egyptian name or
    transliteration — this corpus already carries the equally short genuine names Ka,
    Iy, Ay and In — so matching it would silently delete sourced authority data."""
    assert not sources_mod._is_absence_sentinel(value)
    assert sources_mod._name_form(value) is not None


@pytest.mark.parametrize("value", ["unknown (?)", "unknown?", "(unknown)", "n.a.", "N/A"])
def test_every_placeholder_spelling_found_in_committed_data_is_caught(value):
    """`unknown (?)` appears on 9 committed Leprohon rows and the first version of this
    guard missed all of them."""
    assert sources_mod._is_absence_sentinel(value)


# --- typed absence ----------------------------------------------------------


_PLACEHOLDER_KEYS = frozenset(
    {"unknown", "nknwn", "none", "null", "lost", "lacuna", "missing", "mssng",
     "destroyed", "dstryd", "prenomenunknown"}
)


def test_no_committed_name_normalises_to_a_placeholder_key():
    """The end-to-end invariant the whole change exists to guarantee: no name form
    reaching the matcher may normalise to a key that means "not known".

    This is stronger than the string guard — it tests the KEYS, which is where the harm
    happens. `(unknown)` and `unknown (?)` are different strings that both produce
    {unknown, nknwn}; a future third spelling would be caught here even if the sentinel
    regex missed it."""
    from pipeline.authority.claimgraph.normalize import keys_for_form

    offenders = []
    for r in load_all_sources(AUTHORITY_ROOT).records:
        for form in [*r.prenomina, *r.horus_names, *r.nomina]:
            for k in keys_for_form(form, skeleton=True) & _PLACEHOLDER_KEYS:
                offenders.append((r.source_id, r.local_id, k, form))
    assert offenders == [], offenders


_LOST_ENTRY_IDS = (
    "leprohon-leprohon-13.49",
    "leprohon-leprohon-14.14",
    "leprohon-leprohon-14.46",
    "leprohon-leprohon-14.52",
    "leprohon-leprohon-16.01",
    "leprohon-leprohon-16.11",
    "leprohon-leprohon-17.03",
    "leprohon-leprohon-17.12",
)

_LOST_ENTRY_KEYS = frozenset(
    {"namelost", "nmlst", "onenamelost", "threenameslost", "fivenameslost",
     "eightnameslost", "nnmslst", "thrnmslst", "fvnmslst", "ghtnmslst"}
)


def test_no_cross_source_candidate_rests_on_a_placeholder_key():
    """No candidate pair may be generated on a key meaning "not known" — including the
    lost-entry designations. This is the tripwire kept from the previous round; it now
    guards the fix rather than a deferral."""
    from pipeline.authority.claimgraph.matcher import generate_candidates

    bad = _PLACEHOLDER_KEYS | _LOST_ENTRY_KEYS
    for c in generate_candidates(load_all_sources(AUTHORITY_ROOT).records):
        shared = set(c.shared_prenomen_keys) | set(c.shared_name_keys)
        assert not (shared & bad), (c.id, sorted(shared & bad))


def test_lost_entry_rows_still_render_their_printed_display_name():
    """The value is KEPT. `display_name` is required, the row must render, and "Name
    Lost" is genuinely what Leprohon calls the entry — only its second role, supplying a
    matching key, is withdrawn."""
    recs = {r.local_id: r for r in load_all_sources(AUTHORITY_ROOT).records}
    expected = {
        "leprohon-leprohon-13.49": "One Name Lost",
        "leprohon-leprohon-14.14": "Name Lost",
        "leprohon-leprohon-14.46": "Three Names Lost",
        "leprohon-leprohon-14.52": "Five Names Lost",
        "leprohon-leprohon-16.01": "Name Lost",
        "leprohon-leprohon-16.11": "Five Names Lost",
        "leprohon-leprohon-17.03": "Eight Names Lost",
        "leprohon-leprohon-17.12": "Three Names Lost",
    }
    for local_id, printed in expected.items():
        rec = recs[local_id]
        assert rec.display_name == printed
        # The distinction is carried on the record's TYPE, not re-derived from the
        # string by whichever consumer remembers to.
        assert rec.display_name_absence is not None
        assert rec.display_name_absence.kind == "stated_unknown"
        assert rec.display_name_absence.printed_as == printed


def test_lost_entry_rows_contribute_no_name_key():
    """None of the eight contributes a matching key at all: their titulary lists are
    empty and the headword is withdrawn, so there is nothing left to block on."""
    from pipeline.authority.claimgraph.matcher import _name_keys

    recs = {r.local_id: r for r in load_all_sources(AUTHORITY_ROOT).records}
    for local_id in _LOST_ENTRY_IDS:
        assert _name_keys(recs[local_id]) == set(), local_id


def test_every_other_record_still_matches_on_its_display_name():
    """The withdrawal is surgical. Every record WITHOUT a typed display-name absence
    still contributes its headword to the blocker — otherwise this change would quietly
    gut the loose name matcher for 1151 records."""
    from pipeline.authority.claimgraph.matcher import _name_keys
    from pipeline.authority.claimgraph.normalize import keys_for_form

    checked = 0
    for r in load_all_sources(AUTHORITY_ROOT).records:
        if r.display_name_absence is not None:
            continue
        expected = keys_for_form(NameFormT(surface=r.display_name))
        assert expected <= _name_keys(r), r.local_id
        checked += 1
    assert checked == 1151, checked


@pytest.mark.parametrize(
    "value",
    [
        # iDAI gazetteer place names. `Kloster` CONTAINS "lost" — a substring rule would
        # strike real places out of the blocker. The gate is the typed field, never the
        # string, so these are untouched.
        "Katharinenkloster",
        "Simeonskloster",
        "Jeremias-Kloster",
        # `Na` was matched by the earlier `n/?a` alternative in the sentinel — a real
        # name element that an absence pattern must never be able to swallow.
        "Na",
        "Nay",
    ],
)
def test_lost_like_and_na_like_real_names_are_unaffected(value):
    """An absence pattern must never swallow a name that merely resembles it."""
    assert not sources_mod._is_absence_sentinel(value)
    assert sources_mod._name_form(value) is not None
    from pipeline.authority.claimgraph.matcher import _name_keys

    rec = _record_with_display_name(value)
    assert _name_keys(rec) != set()


def _record_with_display_name(name: str):
    from pipeline.authority.claimgraph.sources import RulerRecord, SOURCE_AUTHORITY

    return RulerRecord(
        source_id="leprohon",
        local_id="x",
        display_name=name,
        display_name_absence=None,
        alt_names=[],
        dynasty=None,
        dynasty_label=None,
        prenomina=[],
        horus_names=[],
        nomina=[],
        reign_start_bce=None,
        reign_end_bce=None,
        intra_source_same_as=[],
        authority=SOURCE_AUTHORITY["leprohon"],
    )


def test_committed_absence_kinds_are_all_in_the_vocabulary():
    """Rule 3: the controlled vocabulary is enforced, not documented. Every typed
    absence in every committed claim-graph source must parse — an off-vocabulary `kind`
    or a missing `printed_as` raises rather than being quietly ignored."""
    from pipeline.authority.claimgraph.absence import (
        ABSENCE_KINDS,
        iter_absence_fields,
        parse_absence,
    )

    seen: set[tuple[str, str]] = set()
    for source, directory in _DIRS.items():
        path = AUTHORITY_ROOT / directory / "reconciled.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            for dotted, _key, value in iter_absence_fields(row):
                if value is None:
                    # Kitchen carries `prenomen_absence: null` on every row for schema
                    # uniformity. Null means "no absence asserted here" — which is the
                    # ordinary not-printed case, and carries no vocabulary term.
                    continue
                kind, printed = parse_absence(value, where=f"{source}:{dotted}")
                seen.add((kind, printed))

    assert {k for k, _ in seen} <= ABSENCE_KINDS
    # Pin the exact printed tokens the committed sources assert, so a silent
    # re-transcription that drops or invents one fails here (rule 5).
    assert seen == {
        # titulary slots — the scholar prints "the name is not known" in the slot
        ("stated_unknown", "(unknown)"),
        ("stated_unknown", "unknown"),
        ("stated_unknown", "unknown (?)"),
        ("stated_unknown", "[Prenomen unknown]"),
        # display headwords — Leprohon's designation for a lost king-list entry. Same
        # fact, same vocabulary term; only the value survives, because the row must
        # render.
        ("stated_unknown", "One Name Lost"),
        ("stated_unknown", "Name Lost"),
        ("stated_unknown", "Three Names Lost"),
        ("stated_unknown", "Five Names Lost"),
        ("stated_unknown", "Eight Names Lost"),
    }, sorted(seen)


def test_migrated_rows_have_their_exact_post_migration_values():
    """Pin the migrated rows field-by-field (rule 5). `printed_as` is what makes the
    migration lossless: Leprohon's three spellings and Kitchen's bracketed form all
    survive verbatim, they just no longer live in the field that means "this IS the
    name"."""
    lep = {
        json.loads(line)["leprohon_id"]: json.loads(line)
        for line in (AUTHORITY_ROOT / _DIRS["leprohon"] / "reconciled.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    }
    expected = {
        ("leprohon-4.07", "golden_horus_names"): ("(unknown)", "See Dobrev 1993, 189 n. 37."),
        ("leprohon-5.04", "nebty_names"): ("unknown", None),
        ("leprohon-5.04", "golden_horus_names"): ("unknown", None),
        ("leprohon-6.01", "throne_names"): (
            "(unknown)",
            "See Aufrère (1982, 53–54), who, on the analogy of Pepy I, has proposed an "
            "unattested Throne name of *Sehetepre for Teti.",
        ),
        ("leprohon-6.02", "horus_names"): ("(unknown)", None),
        ("leprohon-6.02", "nebty_names"): ("(unknown)", None),
        ("leprohon-6.02", "golden_horus_names"): ("(unknown)", None),
        ("leprohon-6.06", "horus_names"): ("unknown (?)", None),
        ("leprohon-6.06", "nebty_names"): ("unknown (?)", None),
        ("leprohon-6.06", "golden_horus_names"): ("unknown (?)", None),
    }
    for (lid, field), (printed_as, source_note) in expected.items():
        entry = lep[lid][field][0]
        assert entry["absence"] == {"kind": "stated_unknown", "printed_as": printed_as}
        assert entry["transliteration"] is None
        assert entry["anglicised"] is None
        assert entry["translation"] is None
        assert entry["attested_in"] == []
        assert entry["is_variant"] is False
        assert entry["variant_index"] == 1
        # The footnote is scholarship ABOUT the absence (Aufrère's proposed but
        # unattested *Sehetepre) — the one thing that must NOT be lost.
        assert entry["source_note"] == source_note, (lid, field)

    kit = {
        json.loads(line)["kitchen_id"]: json.loads(line)
        for line in (AUTHORITY_ROOT / _DIRS["kitchen"] / "reconciled.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    }
    for kid in ("22.04", "23.07"):
        assert kit[kid]["prenomen"] is None
        assert kit[kid]["prenomens"] == []
        assert kit[kid]["prenomen_absence"] == {
            "kind": "stated_unknown",
            "printed_as": "[Prenomen unknown]",
        }


def test_leprohon_lacuna_marker_row_is_kept_and_matches_on_nothing():
    """leprohon-19.02 Sety I keeps its `////` Horus variant, and this pins BOTH halves of
    the claim that it is a different fact from "the name is unknown".

    `////` is an ATTESTED inscription (Abydos, King's chapel (e)) whose signs are
    destroyed, with a real `attested_in`. So: (a) the attestation survives into the graph
    as a name form rather than being dropped as an absence — which is why `destroyed` is
    not an alternative in `_ABSENCE_SENTINEL` — and (b) it still contributes no matching
    key, because the normalizer strips non-alphanumerics, so keeping it corroborates
    nothing with anyone."""
    from pipeline.authority.claimgraph.normalize import keys_for_form

    rec = next(
        r
        for r in load_all_sources(AUTHORITY_ROOT).records
        if r.local_id == "leprohon-leprohon-19.02"
    )
    kept = [f for f in rec.horus_names if f.surface == "////"]
    assert len(kept) == 1, "the attested-but-destroyed Horus variant must survive"
    assert kept[0].translit == "////"
    assert keys_for_form(kept[0], skeleton=True) == set(), (
        "it must nonetheless be unmatchable — a lacuna marker is not a corroborator"
    )

    row = next(
        json.loads(line)
        for line in (AUTHORITY_ROOT / _DIRS["leprohon"] / "reconciled.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and json.loads(line)["leprohon_id"] == "leprohon-19.02"
    )
    entry = next(e for e in row["horus_names"] if e["transliteration"] == "////")
    assert entry["anglicised"] == "////"
    assert entry["translation"] == "(destroyed)"
    assert entry["attested_in"] == [
        "Abydos, Great Temple, Seven Chapels — King's chapel (e)"
    ]
    assert "absence" not in entry


def test_unconsulted_absence_flag_raises(tmp_path):
    """THE regression this registry exists for. Kitchen shipped a correct, page-cited
    `prenomen_is_kitchen_unknown` boolean and the loader never read it — for the entire
    life of the field — while happily loading the placeholder string beside it as a
    throne name. A typed absence nobody consults is worse than none: it looks like the
    distinction is being honoured. So it must be loud (rule 2)."""
    row = dict(_MINIMAL["kitchen"], prenomen_is_kitchen_unknown=True)
    with pytest.raises(SourceRowError, match="does not consult"):
        _load(tmp_path, "kitchen", [row])


def test_unconsulted_absence_flag_raises_on_a_source_with_none_registered(tmp_path):
    """The guard is per-source: Beckerath registers no absence fields at all, so ANY
    such field on a Beckerath row is unconsulted by construction."""
    row = dict(
        _MINIMAL["beckerath"],
        prenomen_absence={"kind": "stated_unknown", "printed_as": "x"},
    )
    with pytest.raises(SourceRowError, match="does not consult"):
        _load(tmp_path, "beckerath", [row])


def test_nested_unconsulted_absence_flag_raises(tmp_path):
    """The scan reaches into nested name-list entries, not just top-level keys — an
    absence buried in `birth_names[0]` on a source that does not consume it is exactly
    as invisible as Kitchen's was."""
    row = dict(
        _MINIMAL["pharaoh_se"],
        birth_names=[{"name": "Khufu", "absence": {"kind": "stated_unknown", "printed_as": "x"}}],
    )
    with pytest.raises(SourceRowError, match="does not consult"):
        _load(tmp_path, "pharaoh_se", [row])


def test_off_vocabulary_absence_kind_raises(tmp_path):
    """An unrecognised `kind` is not tolerated: it means the source drew a distinction
    the loader would silently discard. Extending the vocabulary requires a page
    citation, not a new string appearing in the data."""
    row = dict(
        _MINIMAL["leprohon"],
        throne_names=[{"absence": {"kind": "vibes", "printed_as": "?"}}],
    )
    with pytest.raises(ValueError, match="unknown absence kind"):
        _load(tmp_path, "leprohon", [row])


def test_absence_without_a_printed_token_raises(tmp_path):
    """`printed_as` is mandatory. Without it the migration would erase what the page
    actually shows, which is the Rule-6 violation the typed sibling exists to avoid."""
    row = dict(
        _MINIMAL["leprohon"],
        throne_names=[{"absence": {"kind": "stated_unknown"}}],
    )
    with pytest.raises(ValueError, match="printed_as"):
        _load(tmp_path, "leprohon", [row])


def test_absence_alongside_a_name_raises(tmp_path):
    """A source cannot both state the name is unknown and supply it. That is a
    contradiction in the reconciled row, and reconciled data is sacred — it must fail
    loudly rather than have the loader pick a winner."""
    row = dict(
        _MINIMAL["leprohon"],
        throne_names=[
            {
                "anglicised": "Sehetepre",
                "absence": {"kind": "stated_unknown", "printed_as": "(unknown)"},
            }
        ],
    )
    with pytest.raises(SourceRowError, match="AND a name"):
        _load(tmp_path, "leprohon", [row])


def test_kitchen_absence_alongside_a_prenomen_raises(tmp_path):
    """Same contradiction on Kitchen's scalar-field shape."""
    row = dict(
        _MINIMAL["kitchen"],
        prenomen="Usimare",
        prenomen_absence={"kind": "stated_unknown", "printed_as": "[Prenomen unknown]"},
    )
    with pytest.raises(SourceRowError, match="Both cannot be true"):
        _load(tmp_path, "kitchen", [row])


def test_typed_absence_emits_no_name_but_keeps_the_row(tmp_path):
    """The point of the whole design: the king still exists as a node, he just carries
    no throne-name claim. Dropping the ROW would lose the king; dropping only the claim
    is what the source actually says."""
    row = dict(
        _MINIMAL["leprohon"],
        throne_names=[{"absence": {"kind": "stated_unknown", "printed_as": "(unknown)"}}],
    )
    load = _load(tmp_path, "leprohon", [row])
    assert len(load.records) == 1
    assert load.records[0].prenomina == []
