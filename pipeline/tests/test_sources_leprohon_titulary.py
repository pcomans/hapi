"""Structural value-assertion tests for Leprohon 2013 titulary source extract.

Per rule 5: every populated field on a sampled fixture row is asserted.
Chunk 1 = Early Dynastic Period (Dyn 0/1/2, 27 kings, physical pp. 42-50).
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
    / "leprohon-2013-titulary"
)
JSONL = SOURCE_DIR / "reconciled.jsonl"

BOOK = "Leprohon 2013"
EDITION = "SBL Writings from the Ancient World 33"
CHAPTER = "Early Dynastic Period"


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(
        json.loads(line) for line in JSONL.read_text().splitlines() if line.strip()
    )


def _row(lid: str) -> dict:
    hits = [r for r in _rows() if r["leprohon_id"] == lid]
    if len(hits) != 1:
        raise AssertionError(f"expected 1 row for {lid!r}, got {len(hits)}")
    return hits[0]


# ---------------------------------------------------------------------------
# Row-count + dynasty-coverage invariants
# ---------------------------------------------------------------------------


def test_row_count() -> None:
    """Chapter II covers Dyn 0 (12 kings), Dyn 1 (7), Dyn 2 (8) = 27 total."""
    assert len(_rows()) == 27, len(_rows())


def test_dynasty_coverage() -> None:
    """Every chapter-II dynasty (0, 1, 2) is represented; nothing else."""
    dynasties = {r["dynasty_number"] for r in _rows()}
    assert dynasties == {0, 1, 2}, dynasties


def test_rows_per_dynasty() -> None:
    """Dyn 0: 12 kings (Iry-Hor through Horus \"Pe\"). Dyn 1: 7 (Aha through
    Qa'a). Dyn 2: 8 (Hetepsekhemwy through Khasekhem/Khasekhemwy)."""
    counts = {d: sum(1 for r in _rows() if r["dynasty_number"] == d) for d in (0, 1, 2)}
    assert counts == {0: 12, 1: 7, 2: 8}, counts


def test_chapter_label_uniform() -> None:
    """Every chunk-1 row is tagged with the chapter-II label."""
    for r in _rows():
        assert r["chapter"] == CHAPTER, r


def test_dynasty_label_shape() -> None:
    """Dyn 0 rows carry the quoted form `Dynasty "0"` (Leprohon's own
    convention); Dyn 1/2 rows use bare `Dynasty 1` / `Dynasty 2`."""
    labels = {r["dynasty_number"]: r["dynasty_label"] for r in _rows()}
    assert labels[0] == 'Dynasty "0"', labels[0]
    assert labels[1] == "Dynasty 1", labels[1]
    assert labels[2] == "Dynasty 2", labels[2]


# ---------------------------------------------------------------------------
# ID invariants
# ---------------------------------------------------------------------------


def test_leprohon_id_is_unique() -> None:
    ids = [r["leprohon_id"] for r in _rows()]
    assert len(ids) == len(set(ids)), "duplicate leprohon_id detected"


_LID_RE = re.compile(r"^leprohon-\d+\.\d{2}$")


def test_leprohon_id_shape() -> None:
    """Every id matches `leprohon-{dynasty}.{NN}` — NN is exactly two digits."""
    for r in _rows():
        assert _LID_RE.match(r["leprohon_id"]), r["leprohon_id"]


def test_sequence_matches_id() -> None:
    """`sequence_in_chapter_section` equals the numeric tail of leprohon_id."""
    for r in _rows():
        _, tail = r["leprohon_id"].split(".")
        assert r["sequence_in_chapter_section"] == int(tail), r


# ---------------------------------------------------------------------------
# Citation completeness
# ---------------------------------------------------------------------------


def test_every_row_has_complete_citation() -> None:
    """Rule 1: every row traces back to book + edition + printed/physical pages."""
    for r in _rows():
        c = r["source_citation"]
        assert c["book"] == BOOK, r
        assert c["edition"] == EDITION, r
        assert isinstance(c["printed_page"], int), r
        assert isinstance(c["physical_pdf_page"], int), r
        assert 21 <= c["printed_page"] <= 29, r
        assert 42 <= c["physical_pdf_page"] <= 50, r
        # Chunk-1 offset is +21 at both ends; no drift within the chunk.
        assert c["physical_pdf_page"] == c["printed_page"] + 21, r


# ---------------------------------------------------------------------------
# Per-name-entry schema invariants
# ---------------------------------------------------------------------------

NAME_LIST_FIELDS = (
    "horus_names",
    "nebty_names",
    "golden_horus_names",
    "throne_names",
    "birth_names",
    "later_cartouche_names",
    "seth_names",
)

NAME_ENTRY_FIELDS = frozenset(
    {
        "transliteration",
        "anglicised",
        "translation",
        "variant_index",
        "is_variant",
        "attested_in",
        "source_note",
    }
)


def test_name_lists_are_lists() -> None:
    """Every name-type field is a list (possibly empty), never null."""
    for r in _rows():
        for field in NAME_LIST_FIELDS:
            assert isinstance(r[field], list), f"{r['leprohon_id']}.{field}"


def test_name_entries_have_required_fields() -> None:
    """Every name entry exposes the 7-field schema exactly."""
    for r in _rows():
        for field in NAME_LIST_FIELDS:
            for entry in r[field]:
                missing = NAME_ENTRY_FIELDS - set(entry)
                extra = set(entry) - NAME_ENTRY_FIELDS
                assert not missing, f"{r['leprohon_id']}.{field}: missing {missing}"
                assert not extra, f"{r['leprohon_id']}.{field}: extra {extra}"


def test_variant_index_starts_at_one() -> None:
    """First entry in every name list has variant_index=1, is_variant=False."""
    for r in _rows():
        for field in NAME_LIST_FIELDS:
            if not r[field]:
                continue
            first = r[field][0]
            assert first["variant_index"] == 1, f"{r['leprohon_id']}.{field}[0]"
            assert first["is_variant"] is False, f"{r['leprohon_id']}.{field}[0]"


def test_variant_index_is_monotonic() -> None:
    """variant_index values increment by 1 within each list: 1, 2, 3, ..."""
    for r in _rows():
        for field in NAME_LIST_FIELDS:
            for i, entry in enumerate(r[field], start=1):
                assert entry["variant_index"] == i, (
                    f"{r['leprohon_id']}.{field}[{i-1}]: "
                    f"variant_index={entry['variant_index']}, expected {i}"
                )


def test_is_variant_matches_position() -> None:
    """is_variant is False iff variant_index == 1; True otherwise."""
    for r in _rows():
        for field in NAME_LIST_FIELDS:
            for entry in r[field]:
                expected = entry["variant_index"] > 1
                assert entry["is_variant"] == expected, (
                    f"{r['leprohon_id']}.{field}: "
                    f"variant_index={entry['variant_index']}, "
                    f"is_variant={entry['is_variant']}"
                )


def test_attested_in_is_list() -> None:
    """attested_in is always a list (possibly empty), never null."""
    for r in _rows():
        for field in NAME_LIST_FIELDS:
            for entry in r[field]:
                assert isinstance(entry["attested_in"], list), (
                    f"{r['leprohon_id']}.{field}"
                )


# ---------------------------------------------------------------------------
# Flagship row: leprohon-0.01 Iry-Hor (Dyn 0 minimal single-Horus shape)
# ---------------------------------------------------------------------------


def test_iry_hor_full_row() -> None:
    r = _row("leprohon-0.01")
    assert r["dynasty_number"] == 0
    assert r["dynasty_label"] == 'Dynasty "0"'
    assert r["sequence_in_chapter_section"] == 1
    assert r["display_name"] == "Iry-Hor"
    assert r["alt_display_names"] == []
    assert r["nebty_names"] == []
    assert r["golden_horus_names"] == []
    assert r["throne_names"] == []
    assert r["birth_names"] == []
    assert r["later_cartouche_names"] == []
    assert r["seth_names"] == []
    assert len(r["horus_names"]) == 1
    horus = r["horus_names"][0]
    assert horus["transliteration"] == "iry-ḥr"
    assert horus["anglicised"] == "iry-hor"
    assert horus["translation"] == "The companion of Horus"
    assert horus["variant_index"] == 1
    assert horus["is_variant"] is False
    assert horus["attested_in"] == []
    assert horus["source_note"] == "Von Beckerath 1999, 36–37."
    assert r["source_citation"]["printed_page"] == 22
    assert r["source_citation"]["physical_pdf_page"] == 43


# ---------------------------------------------------------------------------
# Flagship row: leprohon-0.07 Ny-<Hor> (angle-bracket preservation)
# ---------------------------------------------------------------------------


def test_ny_hor_preserves_angle_brackets() -> None:
    r = _row("leprohon-0.07")
    assert r["display_name"] == "Ny-<Hor>"
    horus = r["horus_names"][0]
    assert horus["transliteration"] == "n(y)-<ḥr>", horus["transliteration"]
    assert horus["anglicised"] == "ny-<hor>"
    assert horus["translation"] == "The one who belongs to <Horus>"


# ---------------------------------------------------------------------------
# Flagship row: leprohon-1.03 Djet/Wadjet (slashed homonym)
# ---------------------------------------------------------------------------


def test_djet_wadjet_slashed_homonym() -> None:
    r = _row("leprohon-1.03")
    assert r["display_name"] == "Djet/Wadjet"
    assert r["alt_display_names"] == ["Djet", "Wadjet"]
    assert r["horus_names"][0]["transliteration"] == "ḏt/wꜣḏt"
    assert r["horus_names"][0]["anglicised"] == "djet/wadjet"
    assert r["horus_names"][0]["translation"] == "The cobra"
    assert len(r["later_cartouche_names"]) == 2
    lc = r["later_cartouche_names"]
    assert lc[0]["transliteration"] == "[i]ty"
    assert lc[0]["anglicised"] == "[i]ty"
    assert lc[0]["translation"] == "The sovereign"
    assert lc[0]["attested_in"] == ["Turin 2,15"]
    assert lc[0]["variant_index"] == 1
    assert lc[1]["transliteration"] == "itꜣ"
    assert lc[1]["anglicised"] == "ita"
    assert lc[1]["translation"] == "Ita"
    assert lc[1]["variant_index"] == 2
    assert lc[1]["is_variant"] is True


# ---------------------------------------------------------------------------
# Flagship row: leprohon-1.04 Den (full Early-Dynastic titulary)
# ---------------------------------------------------------------------------


def test_den_full_titulary() -> None:
    """Den carries Horus + Golden Horus + Throne + 2 Later cartouche names.
    No Nebty, Birth, or Seth.
    """
    r = _row("leprohon-1.04")
    assert r["display_name"] == "Den"
    assert r["dynasty_number"] == 1
    assert r["sequence_in_chapter_section"] == 4
    assert r["nebty_names"] == []
    assert r["birth_names"] == []
    assert r["seth_names"] == []
    assert len(r["horus_names"]) == 1
    assert r["horus_names"][0]["transliteration"] == "dn"
    assert r["horus_names"][0]["translation"] == "The severer (of heads)"
    assert len(r["golden_horus_names"]) == 1
    assert r["golden_horus_names"][0]["transliteration"] == "iꜥrt nbw"
    assert r["golden_horus_names"][0]["anglicised"] == "iaret nebu"
    assert r["golden_horus_names"][0]["translation"] == "The golden uraeus"
    assert len(r["throne_names"]) == 1
    assert r["throne_names"][0]["transliteration"] == "ḫꜣsty"
    assert r["throne_names"][0]["anglicised"] == "khasety"
    assert r["throne_names"][0]["translation"] == "The highlander"
    assert len(r["later_cartouche_names"]) == 2
    lc = r["later_cartouche_names"]
    assert lc[0]["transliteration"] == "spꜣty"
    assert lc[0]["anglicised"] == "sepaty"
    assert lc[0]["translation"] == "He of the two districts"
    assert lc[0]["attested_in"] == ["Abydos 5"]
    assert lc[1]["transliteration"] == "zmty"
    assert lc[1]["anglicised"] == "zemty"
    assert lc[1]["translation"] == "The desert man"
    assert lc[1]["attested_in"] == ["Turin 2,16"]
    assert lc[1]["is_variant"] is True


# ---------------------------------------------------------------------------
# Flagship row: leprohon-2.05 Sened (only Early-Dynastic Birth name)
# ---------------------------------------------------------------------------


def test_sened_has_birth_name_entry() -> None:
    r = _row("leprohon-2.05")
    assert r["horus_names"] == []
    assert r["nebty_names"] == []
    assert len(r["birth_names"]) == 1
    birth = r["birth_names"][0]
    assert birth["transliteration"] == "snd"
    assert birth["anglicised"] == "sened"
    assert birth["translation"] == "The frightful one"
    assert len(r["later_cartouche_names"]) == 1
    lc = r["later_cartouche_names"][0]
    assert lc["transliteration"] == "sndi"
    assert lc["anglicised"] == "sendi"
    assert sorted(lc["attested_in"]) == ["Abydos 13", "Saqqara 7", "Turin 2,24"]


# ---------------------------------------------------------------------------
# Flagship row: leprohon-2.07 Peribsen (Seth name replaces Horus name)
# ---------------------------------------------------------------------------


def test_peribsen_seth_replaces_horus() -> None:
    r = _row("leprohon-2.07")
    assert r["display_name"] == "Peribsen"
    assert r["horus_names"] == [], (
        "Peribsen broke with precedent: Seth name replaces Horus name"
    )
    assert len(r["seth_names"]) == 1
    seth = r["seth_names"][0]
    assert seth["transliteration"] == "stẖ pr(w) ib.sn"
    # Per egyptologist-reviewer 2026-04-20: the anglicised gloss is the
    # parenthetical-only form `per(u) ib.sen`; the `Seth,` prefix belongs
    # to the translation column (fix_rows correction).
    assert seth["anglicised"] == "per(u) ib.sen"
    assert seth["translation"] == "Seth, (for whom ?) their will has come forth"
    # Leprohon also gives matching Nebty and Throne entries with the same
    # underlying text form (without the preceding Seth glyph); the extractors
    # emitted each one to its respective name-type list.
    assert len(r["nebty_names"]) == 1
    assert r["nebty_names"][0]["transliteration"] == "pr ib.sn"
    assert len(r["throne_names"]) == 1
    assert r["throne_names"][0]["transliteration"] == "pr ib.sn"


# ---------------------------------------------------------------------------
# Flagship row: leprohon-2.08 Khasekhem/Khasekhemwy (dual Horus+Seth)
# ---------------------------------------------------------------------------


def test_khasekhemwy_slashed_display_name() -> None:
    r = _row("leprohon-2.08")
    assert r["display_name"] == "Khasekhem/Khasekhemwy"
    assert r["alt_display_names"] == ["Khasekhem", "Khasekhemwy"]


def test_khasekhemwy_horus_seth_dual_classification() -> None:
    """Leprohon labels one Khasekhemwy name-entry `Horus/Seth 2:` — the king
    reconciled the Seth and Horus traditions with a serekh topped by both
    animals. The entry appears in BOTH `horus_names` (is_variant=True,
    variant_index=2) AND `seth_names` (is_variant=False, variant_index=1).
    """
    r = _row("leprohon-2.08")
    assert len(r["horus_names"]) == 2
    assert r["horus_names"][0]["transliteration"] == "ḫꜥ sḫm", (
        "first Horus form: 'ḫꜥ sḫm' — 'The powerful one has appeared'"
    )
    assert r["horus_names"][0]["variant_index"] == 1
    assert r["horus_names"][0]["is_variant"] is False
    horus2 = r["horus_names"][1]
    assert horus2["transliteration"] == "ḫꜥ sḫmy nbwy ḥtp(.w) im.f"
    assert horus2["variant_index"] == 2
    assert horus2["is_variant"] is True
    # seth_names duplicates the Horus/Seth 2 entry — first entry in seth list
    assert len(r["seth_names"]) == 1
    seth = r["seth_names"][0]
    assert seth["transliteration"] == horus2["transliteration"], (
        "seth_names[0] should duplicate horus_names[1] (the Horus/Seth 2 entry)"
    )
    assert seth["translation"] == horus2["translation"]
    assert seth["variant_index"] == 1
    assert seth["is_variant"] is False


def test_khasekhemwy_later_cartouche_hedged_attestation() -> None:
    """Leprohon hedges one Ramesside-list attestation: `Abydos 14;
    according to Kitchen (1993, 154), this refers to King Khasekhemwy`.
    The hedge must be preserved verbatim in `attested_in` (single string),
    NOT stripped to just `Abydos 14`.
    """
    r = _row("leprohon-2.08")
    lc = r["later_cartouche_names"]
    assert len(lc) == 2
    assert lc[0]["transliteration"] == "ḏꜣḏꜣy"
    assert lc[0]["attested_in"] == [
        "Abydos 14; according to Kitchen (1993, 154), this refers to King Khasekhemwy"
    ]
    assert lc[1]["transliteration"] == "bby/bbty"
    assert sorted(lc[1]["attested_in"]) == ["Saqqara 11", "Turin 3,3"]


# ---------------------------------------------------------------------------
# Cross-row invariants
# ---------------------------------------------------------------------------


def test_only_dyn0_uses_quoted_dynasty_label() -> None:
    """The `Dynasty "0"` label with quotes appears exclusively on Dyn-0 rows —
    agents must not leak the Leprohon convention into Dyn 1/2 labels."""
    for r in _rows():
        if '"0"' in r["dynasty_label"]:
            assert r["dynasty_number"] == 0, r


def test_slashed_display_names_have_alt_forms() -> None:
    """Rows whose `display_name` contains `/` must have matching
    `alt_display_names` split on `/`. Rows without `/` must have
    empty `alt_display_names`."""
    for r in _rows():
        if "/" in r["display_name"]:
            assert r["alt_display_names"] == r["display_name"].split("/"), r
        else:
            assert r["alt_display_names"] == [], r


def test_headword_display_names_are_title_cased() -> None:
    """Leprohon prints headwords in SMALLCAP (`1. IRY-HOR`). Agents must
    normalise to Title Case (`Iry-Hor`) — with three explicit exceptions:
      1. Letter-tagged variants like `Horus "A"` / `Horus "Pe"` (the `A`/`Pe`
         suffix carries its own casing).
      2. Angle-bracketed partial readings like `Ny-<Hor>` (brackets preserved
         verbatim per the partial-reading convention).
      3. Parenthesised prefixes like `(Two Ladies) Weneg` where Leprohon
         flags an absent Horus name and substitutes the Two Ladies name as
         the headword form."""
    for r in _rows():
        display = r["display_name"]
        # Exception 1: letter-tagged Horus entries
        if display.startswith("Horus") and '"' in display:
            continue
        # Exception 3: Leprohon-parenthesised prefixes — skip the parenthetical
        # group, test remaining tokens. `(Two Ladies) Weneg` → skip `(Two`, skip
        # `Ladies)`, require `Weneg` to start uppercase.
        for part in display.replace("/", " ").split():
            if part.startswith("(") or part.endswith(")"):
                continue
            # Exception 2: angle-bracketed segments
            if part.startswith("<"):
                continue
            for seg in part.split("-"):
                if seg.startswith("<"):
                    continue
                assert seg[0].isupper(), f"{r['leprohon_id']}: {display!r}"


def test_later_cartouche_is_separate_from_birth_names() -> None:
    """The `Later cartouche name:` attestation class is distinct from
    contemporary `Birth:` names. No entry appears in both lists for the same
    king (they are semantically different attestation classes — the Ramesside
    king-list reconstruction is not the same category of evidence as a
    contemporary birth-name inscription)."""
    for r in _rows():
        birth_translits = {e["transliteration"] for e in r["birth_names"]}
        lc_translits = {e["transliteration"] for e in r["later_cartouche_names"]}
        overlap = birth_translits & lc_translits
        assert not overlap, f"{r['leprohon_id']}: overlap {overlap}"


def test_only_peribsen_has_empty_horus_with_populated_seth() -> None:
    """Peribsen is the only Early-Dynastic king whose Horus name was
    REPLACED by a Seth name. Khasekhemwy reconciled the two traditions
    (Horus + Seth side by side). Other kings have no Seth name at all."""
    seth_kings = [r for r in _rows() if r["seth_names"]]
    assert {r["leprohon_id"] for r in seth_kings} == {
        "leprohon-2.07",  # Peribsen
        "leprohon-2.08",  # Khasekhem/Khasekhemwy
    }, {r["leprohon_id"] for r in seth_kings}
    # Peribsen: empty horus, populated seth
    peribsen = _row("leprohon-2.07")
    assert peribsen["horus_names"] == []
    assert peribsen["seth_names"] != []
    # Khasekhemwy: BOTH populated (the reconciliation)
    khas = _row("leprohon-2.08")
    assert khas["horus_names"] != []
    assert khas["seth_names"] != []


def test_every_populated_field_on_flagship_den_asserted() -> None:
    """Rule 5 sentinel: this test exists so the flagship row's field count
    is re-verified when the schema changes. If `test_den_full_titulary`
    stops asserting every populated field, this test fails — making it
    impossible to silently under-test Den.
    """
    r = _row("leprohon-1.04")
    populated_top_level = [
        k
        for k, v in r.items()
        if v not in ([], "", None, {})
        and not (isinstance(v, list) and len(v) == 0)
    ]
    # Top-level populated fields on Den: leprohon_id, dynasty_number,
    # dynasty_label, chapter, sequence_in_chapter_section, display_name,
    # horus_names, golden_horus_names, throne_names, later_cartouche_names,
    # source_citation. (alt_display_names, nebty_names, birth_names,
    # seth_names are all empty, correctly.)
    assert set(populated_top_level) == {
        "leprohon_id",
        "dynasty_number",
        "dynasty_label",
        "chapter",
        "sequence_in_chapter_section",
        "display_name",
        "horus_names",
        "golden_horus_names",
        "throne_names",
        "later_cartouche_names",
        "source_citation",
    }, sorted(populated_top_level)
