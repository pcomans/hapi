"""Structural value-assertion tests for HKW 2006 (Hornung-Krauss-Warburton
Ancient Egyptian Chronology) authority source extract.

Per CLAUDE.md rule 5: every populated field on every fixture-class row is
asserted.

Issue #176 audit (Tier 2, 6 P1) introduces a `fix_rows.py` for the first
time on this source. The test set below enforces the new typed schema:
`alt_names`, `rulers`, `is_multi_ruler_entry`, `name_uncertain`,
`is_coregency`/`coregency_with`, `is_rival_claimant`/`rival_claimant_of`,
`start_year_approximate`/`end_year_approximate`, `dynasty_branch`,
`null_dates_reason`.
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
    / "hkw-chronology-2006"
)
JSONL = SOURCE_DIR / "reconciled.jsonl"


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(
        json.loads(line) for line in JSONL.read_text().splitlines() if line.strip()
    )


@lru_cache(maxsize=1)
def _fix_rows_module():
    """Path-load `fix_rows.py` (the source dir has a hyphen so
    `importlib.import_module` doesn't work). lru_cached for shared use.
    """
    spec = importlib.util.spec_from_file_location(
        "hkw_fix_rows", SOURCE_DIR / "fix_rows.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


KIND_VOCAB = {"period", "dynasty", "ruler"}


# ---------------------------------------------------------------------------
# Schema-shape invariants (PR for issue #176)
# ---------------------------------------------------------------------------


def test_every_row_has_every_schema_field() -> None:
    """Issue #176: SCHEMA_FIELD_DEFAULTS keys must be present on every
    row after fix_rows runs. Backfilled by `backfill_schema_fields`.
    """
    defaults = _fix_rows_module().SCHEMA_FIELD_DEFAULTS
    for r in _rows():
        for field in defaults:
            assert field in r, (
                f"{r.get('display') or r.get('label')!r}: missing field {field!r}"
            )


def test_kind_in_known_vocab() -> None:
    """Closure on `kind` (period / dynasty / ruler)."""
    for r in _rows():
        assert r["kind"] in KIND_VOCAB, (r.get("display"), r["kind"])


def test_alt_names_is_list_of_strings() -> None:
    """Issue #176 Shape I: `alt_names` is `list[str]`, never `None`.
    Empty list is the absent-data sentinel.
    """
    for r in _rows():
        alt = r["alt_names"]
        assert isinstance(alt, list), (r.get("display"), alt)
        for item in alt:
            assert isinstance(item, str) and item, (r.get("display"), item)


def test_rulers_is_list_of_dicts() -> None:
    """Issue #176 Shape A+B+I: `rulers` is `list[{name, prenomen,
    alternative_reading, alt_names}]`. Empty list for non-multi-ruler rows."""
    expected_keys = {"name", "prenomen", "alternative_reading", "alt_names"}
    for r in _rows():
        rulers = r["rulers"]
        assert isinstance(rulers, list), (r.get("display"), rulers)
        for i, ru in enumerate(rulers):
            assert isinstance(ru, dict), (r.get("display"), i, ru)
            assert set(ru.keys()) == expected_keys, (
                r.get("display"), i,
                f"ruler entry keys {sorted(ru.keys())} != {sorted(expected_keys)}",
            )
            assert ru["name"] and isinstance(ru["name"], str), (r.get("display"), i, ru)


def test_is_multi_ruler_entry_iff_rulers_non_empty() -> None:
    """Issue #176 Shape J: `is_multi_ruler_entry=True` ⇔ `rulers` non-empty.
    Symmetric contract.
    """
    for r in _rows():
        flag = r["is_multi_ruler_entry"]
        non_empty = bool(r["rulers"])
        assert flag == non_empty, (
            r.get("display"),
            f"is_multi_ruler_entry={flag} but rulers non-empty={non_empty}",
        )


def test_multi_ruler_entries_match_canonical_set() -> None:
    """Issue #176: exactly the 5 known compound HKW chronological-aggregate
    rows have `is_multi_ruler_entry=True`. New compound rows must be
    added to the SPOT_CORRECTIONS migration explicitly.
    """
    canonical = {
        "Swadjtu, Ined, Hori, Dedumose",
        "Sobekhotep VIII, Nebiriau, Rahotep, Sobekemzaf I & II, Bebiankh",
        "Osorkon III, Takelot III",
        "Shoshenq IV, Rudamun, Iny",
        "Petubaste II (?), Osorkon IV",
    }
    actual = {r["display"] for r in _rows() if r.get("is_multi_ruler_entry")}
    assert actual == canonical, (
        f"is_multi_ruler_entry set drift: extra={sorted(actual - canonical)}, "
        f"missing={sorted(canonical - actual)}"
    )


def test_no_compound_display_outside_multi_ruler_set() -> None:
    """Issue #176 Shape B: comma-separated multi-ruler displays are only
    allowed on rows with `is_multi_ruler_entry=True`. Catches a future
    multi-ruler row added to display without the typed flag.
    """
    for r in _rows():
        d = r.get("display")
        if not d:
            continue
        if r.get("is_multi_ruler_entry"):
            continue
        # Per HKW, single-ruler displays don't carry comma + name
        # boundaries (commas are reserved for multi-ruler aggregation).
        # The presence of `, ` between two name-shaped tokens is the
        # signal.
        assert ", " not in d, (
            f"{d!r}: comma in display but is_multi_ruler_entry=False; "
            f"add to MULTI_RULER_MIGRATIONS in fix_rows.py if multi-ruler."
        )


def test_no_slash_display_outside_alt_names_migrations() -> None:
    """Issue #176 Shape A+B: slash-separated displays (`X/Y`) are only
    allowed if the corresponding alt_name has been migrated. Post-fix,
    every slash-display from the original corpus has had its second name
    moved to alt_names — there should be no remaining `X/Y` displays.
    """
    for r in _rows():
        d = r.get("display") or ""
        # Permit slash inside parens (e.g. transliteration apostrophes
        # don't use slash) — but a bare `/` between letters is the
        # multi-name signal.
        assert not re.search(r"\w/\w", d), (
            f"{r.get('display')!r}: slash in display; should be split into "
            f"`display` + `alt_names` via SLASH_ROW_MIGRATIONS."
        )


def test_name_uncertain_only_on_known_hedges() -> None:
    """Issue #176 Shape J: `name_uncertain=True` is HKW's hedge for "we
    don't know which of two candidate names this chronological slot
    belongs to". Currently exactly one row carries the flag (Smenkhkare'
    /Nefernefruaten under prenomen `'Ankhkheprure'` per HKW p.493).
    """
    expected_uncertain = {("Smenkhkare'", "'Ankhkheprure'")}
    actual = {
        (r.get("display"), r.get("prenomen"))
        for r in _rows()
        if r.get("name_uncertain")
    }
    assert actual == expected_uncertain, (
        f"name_uncertain set drift: actual={sorted(actual)}, "
        f"expected={sorted(expected_uncertain)}"
    )


def test_coregency_pair_consistency() -> None:
    """Issue #176 Shape J: typed coregency contract is reciprocal —
    if A.coregency_with includes B, then B.coregency_with includes A.
    """
    by_display = {r.get("display"): r for r in _rows() if r.get("display")}
    for r in _rows():
        if not r.get("is_coregency"):
            continue
        a = r.get("display")
        for b in r["coregency_with"]:
            assert b in by_display, (
                f"{a!r} coregency_with={b!r} but {b!r} not in corpus"
            )
            other = by_display[b]
            assert other.get("is_coregency"), (
                f"{a!r} coregency_with={b!r} but {b!r} has is_coregency=False"
            )
            assert a in other["coregency_with"], (
                f"{a!r} coregency_with={b!r} but {b!r}.coregency_with does NOT contain {a!r} "
                f"(reciprocal-link contract violated)"
            )


def test_rival_claimant_pair_consistency() -> None:
    """Issue #176 Shape J: `is_rival_claimant=True` requires
    `rival_claimant_of` to be non-null. The other side (the king being
    rivaled) is not required to carry the flag — `is_rival_claimant`
    semantically means "this row is the LESS-attested claimant" so the
    asymmetric encoding is intentional.
    """
    for r in _rows():
        if r.get("is_rival_claimant"):
            assert r["rival_claimant_of"], (
                r.get("display"),
                "is_rival_claimant=True requires rival_claimant_of to be non-null",
            )


def test_per_bound_approximate_implies_row_approximate() -> None:
    """Issue #176 Shape D+E: per-bound `start_year_approximate` /
    `end_year_approximate` set TRUE on a row implies the row-level
    `approximate` field is also TRUE (the row-level field is the OR
    of the two per-bound flags after this PR's migration).
    """
    for r in _rows():
        per_bound_any = r["start_year_approximate"] or r["end_year_approximate"]
        if per_bound_any:
            assert r["approximate"], (
                r.get("display"),
                f"per-bound approx set ({r['start_year_approximate']}, "
                f"{r['end_year_approximate']}) but row-level approximate=False",
            )


def test_dynasty_branch_only_on_dynasty_rows() -> None:
    """Issue #176 Shape J: `dynasty_branch` is only meaningful on
    `kind=dynasty` rows. Currently exactly 2 dynasty rows carry it
    (Dyn 23 UE / LE).
    """
    branched = [r for r in _rows() if r.get("dynasty_branch")]
    for r in branched:
        assert r["kind"] == "dynasty", (r.get("label"), r["kind"])
    actual = {(r["number"], r["dynasty_branch"]) for r in branched}
    expected = {(23, "UE"), (23, "LE")}
    assert actual == expected, (
        f"dynasty_branch set drift: actual={sorted(actual)}, expected={sorted(expected)}"
    )


def test_no_compound_display_in_ini_or_tao_dups() -> None:
    """Issue #176 Shape G: `display` is NOT unique on its own — `Ini`
    appears in two different dynasties (5 + 13), `Ta'o` appears twice
    in the same Dyn 17 (different prenomens). Rule-4 single-source-of
    -truth: the prenomen + dynasty disambiguate; `display` alone is
    not the join key. Pin the duplicates explicitly so a future
    re-extraction doesn't accidentally collapse them.
    """
    by_display = {}
    for r in _rows():
        d = r.get("display")
        if not d:
            continue
        by_display.setdefault(d, []).append(r)
    expected_dups = {
        "Ini": [(5, "Neuserre'"), (13, "Merhetepre'")],
        "Ta'o": [(17, "Senakhtenre'"), (17, "Seqenenre'")],
    }
    for display, expected in expected_dups.items():
        rows = by_display[display]
        actual = sorted((r.get("dynasty"), r.get("prenomen")) for r in rows)
        assert actual == sorted(expected), (
            f"{display!r}: dups drift. actual={actual}, expected={sorted(expected)}"
        )


# ---------------------------------------------------------------------------
# Per-row pinning for the 12 restructured rows
# ---------------------------------------------------------------------------


def _row(display: str, dynasty: int | None = None, prenomen: str | None = None) -> dict:
    rows = [
        r for r in _rows()
        if r.get("display") == display
        and (dynasty is None or r.get("dynasty") == dynasty)
        and (prenomen is None or r.get("prenomen") == prenomen)
    ]
    if len(rows) != 1:
        raise AssertionError(
            f"expected 1 row for display={display!r} dynasty={dynasty} prenomen={prenomen!r}, "
            f"got {len(rows)}"
        )
    return rows[0]


def test_pin_amenhotep_iv_split() -> None:
    r = _row("Amenhotep IV", dynasty=18)
    assert r["alt_names"] == ["Akhenaten"]
    assert r["name_uncertain"] is False
    assert r["is_multi_ruler_entry"] is False
    assert r["rulers"] == []


def test_pin_smenkhkare_split_with_uncertainty() -> None:
    r = _row("Smenkhkare'", dynasty=18, prenomen="'Ankhkheprure'")
    assert r["alt_names"] == ["Nefernefruaten"]
    assert r["name_uncertain"] is True


def test_pin_nefernefruaten_separate_row_unaffected() -> None:
    """The L118 standalone `Nefernefruaten` row (different prenomen
    `'Ankhetkheprure'`, different date range) is a SEPARATE ruler from
    the L117 `Smenkhkare'` slot — verify it didn't accidentally inherit
    the alt_names/name_uncertain from L117.
    """
    r = _row("Nefernefruaten", prenomen="'Ankhetkheprure'")
    assert r["alt_names"] == []
    assert r["name_uncertain"] is False


def test_pin_sobekhotep_multi_ruler() -> None:
    r = _row("Sobekhotep VIII, Nebiriau, Rahotep, Sobekemzaf I & II, Bebiankh")
    assert r["is_multi_ruler_entry"] is True
    names = [ru["name"] for ru in r["rulers"]]
    assert names == [
        "Sobekhotep VIII", "Nebiriau", "Rahotep",
        "Sobekemzaf I", "Sobekemzaf II", "Bebiankh",
    ], f"Sobekemzaf I & II should expand to 2 entries; got {names!r}"


def test_pin_petubaste_uncertain_in_multi_ruler() -> None:
    """The `Petubaste II (?)` hedge inside a compound row gets the
    parenthetical preserved verbatim in `alt_names` for traceability;
    canonical name strips the parenthetical.
    """
    r = _row("Petubaste II (?), Osorkon IV", dynasty=23)
    petubaste = r["rulers"][0]
    assert petubaste["name"] == "Petubaste II"
    assert petubaste["alt_names"] == ["Petubaste II (?)"]


def test_pin_djoser_horus_name_migrated() -> None:
    r = _row("Djoser", dynasty=3)
    assert "Netjery-khet" in r["alt_names"]
    assert r["note"] is None  # Note cleared after migration


def test_pin_thutmose_iii_coregency() -> None:
    r = _row("Thutmose III", dynasty=18)
    assert r["is_coregency"] is True
    assert r["coregency_with"] == ["Hatshepsut"]


def test_pin_amenmesses_rival_claimant() -> None:
    r = _row("Amenmesses", dynasty=19)
    assert r["is_rival_claimant"] is True
    assert r["rival_claimant_of"] == "Sety II"


def test_pin_siamun_per_bound_approximate() -> None:
    r = _row("Siamun", dynasty=21)
    assert r["start_year_approximate"] is False
    assert r["end_year_approximate"] is True


def test_pin_dyn23_branches() -> None:
    """Both Dyn 23 dynasty rows carry the typed branch flag."""
    branches = sorted(
        (r["number"], r["dynasty_branch"], r["label"])
        for r in _rows()
        if r.get("kind") == "dynasty" and r.get("dynasty_branch")
    )
    assert branches == [
        (23, "LE", "Dyn. 23 (LE)"),
        (23, "UE", "Dyn. 23 (UE) and Rival Kings"),
    ]
