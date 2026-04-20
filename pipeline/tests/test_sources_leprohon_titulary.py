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

# Per-chunk expectations. As chunks land, add the chunk's row into this
# table rather than editing individual tests — the cross-chunk invariant
# tests (row count, dynasty coverage, chapter labels, citation-page ranges)
# iterate over this table.
#
# Each entry:
#   - chapter:           Leprohon TOC chapter title this chunk covers
#   - rows_by_dynasty_label: dict mapping `dynasty_label` to expected row count
#   - printed_page_range: (min, max) inclusive
#   - physical_page_range: (min, max) inclusive
#
# NOTE: chunk 2 (PR #8x, Old Kingdom) also adds 3 rows on printed p. 30 that
# belong structurally to chunk 1 / Chapter II (recovered from chunk 1's
# scope miss — Seneferka + Neferkasokar + Hudjefa). Those rows are
# accounted for in the "early-dynastic" chunk entry below, not
# "old-kingdom", because their `chapter` field is "Early Dynastic Period".
LANDED_CHUNKS: dict[str, dict] = {
    "early-dynastic": {
        "chapter": "Early Dynastic Period",
        "rows_by_dynasty_label": {
            'Dynasty "0"': 12,
            "Dynasty 1": 7,
            "Dynasty 2": 9,  # 8 chunk-1 rows + Seneferka recovered in chunk 2
            "Dynasty 2a": 2,  # recovered in chunk 2
        },
        "printed_page_range": (21, 30),
        "physical_page_range": (42, 51),
    },
    "old-kingdom": {
        "chapter": "Old Kingdom",
        "rows_by_dynasty_label": {
            "Dynasty 3": 5,
            "Dynasty 3a": 4,
            "Dynasty 4": 7,
            "Dynasty 5": 9,
            "Dynasty 6": 7,
            "Dynasty 8": 17,
            "Dynasty 8a": 8,
        },
        "printed_page_range": (31, 48),
        "physical_page_range": (52, 69),
    },
    "fip": {
        "chapter": "First Intermediate Period",
        "rows_by_dynasty_label": {
            # Leprohon preserves the en-dash `–` in his typeset labels;
            # `dynasty_label` retains it verbatim. ASCII hyphen is used
            # only in `leprohon_id` (`leprohon-9-10a.01`) where regex /
            # filesystem safety matters.
            "Dynasties 9–10a": 9,  # 1 stub + 1 contemporarily-attested + 7 Ramesside-only
            "Dynasties 9–10b": 6,
            "Dynasty 11a": 4,
        },
        "printed_page_range": (49, 53),
        "physical_page_range": (70, 74),
    },
}

EXPECTED_TOTAL_ROWS: int = sum(
    count
    for chunk in LANDED_CHUNKS.values()
    for count in chunk["rows_by_dynasty_label"].values()
)

EXPECTED_CHAPTERS: frozenset[str] = frozenset(
    chunk["chapter"] for chunk in LANDED_CHUNKS.values()
)

EXPECTED_DYNASTY_LABELS: dict[str, str] = {
    # maps dynasty_label → parent chapter (for dynasty-label consistency tests)
    label: chunk["chapter"]
    for chunk in LANDED_CHUNKS.values()
    for label in chunk["rows_by_dynasty_label"]
}

EXPECTED_PRINTED_PAGE_MIN = min(
    chunk["printed_page_range"][0] for chunk in LANDED_CHUNKS.values()
)
EXPECTED_PRINTED_PAGE_MAX = max(
    chunk["printed_page_range"][1] for chunk in LANDED_CHUNKS.values()
)
EXPECTED_PHYSICAL_PAGE_MIN = min(
    chunk["physical_page_range"][0] for chunk in LANDED_CHUNKS.values()
)
EXPECTED_PHYSICAL_PAGE_MAX = max(
    chunk["physical_page_range"][1] for chunk in LANDED_CHUNKS.values()
)


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
    """Total row count matches the sum of expected-rows across landed chunks."""
    assert len(_rows()) == EXPECTED_TOTAL_ROWS, (
        f"got {len(_rows())}, expected {EXPECTED_TOTAL_ROWS}"
    )


def test_chapter_coverage() -> None:
    """Every chapter present in LANDED_CHUNKS appears in the data; nothing else."""
    chapters = {r["chapter"] for r in _rows()}
    assert chapters == EXPECTED_CHAPTERS, chapters


def test_rows_per_dynasty_label() -> None:
    """Row count per `dynasty_label` matches the per-chunk expectation table.

    Keys on `dynasty_label` rather than `dynasty_number` because a single
    dynasty_number (e.g. 2) spans multiple sub-dynasty labels (Dynasty 2,
    Dynasty 2a) and they should be counted separately.
    """
    expected = {
        label: count
        for chunk in LANDED_CHUNKS.values()
        for label, count in chunk["rows_by_dynasty_label"].items()
    }
    actual: dict[str, int] = {}
    for r in _rows():
        actual[r["dynasty_label"]] = actual.get(r["dynasty_label"], 0) + 1
    assert actual == expected, f"expected {expected}, got {actual}"


def test_dynasty_label_matches_chapter() -> None:
    """Each row's `dynasty_label` is consistent with its `chapter` field —
    no row has `dynasty_label: "Dynasty 3a"` (an Old-Kingdom sub-dynasty) but
    `chapter: "Early Dynastic Period"`."""
    for r in _rows():
        label, chapter = r["dynasty_label"], r["chapter"]
        expected_chapter = EXPECTED_DYNASTY_LABELS.get(label)
        assert expected_chapter == chapter, (
            f"{r['leprohon_id']}: dynasty_label {label!r} expected chapter "
            f"{expected_chapter!r}, got {chapter!r}"
        )


def test_dyn0_label_is_quoted() -> None:
    """Dyn 0 rows carry the quoted form `Dynasty "0"` — Leprohon's own
    typographic convention for the uncertain pre-dynastic status."""
    dyn0_rows = [r for r in _rows() if r["dynasty_number"] == 0]
    for r in dyn0_rows:
        assert r["dynasty_label"] == 'Dynasty "0"', r


# ---------------------------------------------------------------------------
# ID invariants
# ---------------------------------------------------------------------------


def test_leprohon_id_is_unique() -> None:
    ids = [r["leprohon_id"] for r in _rows()]
    assert len(ids) == len(set(ids)), "duplicate leprohon_id detected"


_LID_RE = re.compile(r"^leprohon-\d+(?:-\d+)?[a-z]?\.\d{2}$")


def test_leprohon_id_shape() -> None:
    """Every id matches `leprohon-{dynasty_group}.{NN}` — NN is exactly two
    digits. `dynasty_group` is one of:
      - a plain integer (`0`, `3`, `18`);
      - integer + single lowercase suffix (`2a`, `3a`, `8a`, `11a`) — Leprohon's
        sub-dynasty sections (typeset as "Dynasty 2a" etc. in the book,
        sometimes Ramesside-only reconstructions, sometimes contemporarily
        attested — see per-section treatment);
      - hyphenated range + suffix (`9-10a`, `9-10b`) — Leprohon's chapter-IV
        combined labels for Dynasties 9 and 10 which he treats as inseparable.
    """
    for r in _rows():
        assert _LID_RE.match(r["leprohon_id"]), r["leprohon_id"]


def test_sequence_matches_id() -> None:
    """`sequence_in_chapter_section` equals the numeric tail of leprohon_id.

    `.split(".", 1)` so that any future `.` in the dynasty-group segment
    (none today — all groups are hyphen-separated) would not confuse the
    tail extraction.
    """
    for r in _rows():
        _, tail = r["leprohon_id"].rsplit(".", 1)
        assert r["sequence_in_chapter_section"] == int(tail), r


# ---------------------------------------------------------------------------
# Citation completeness
# ---------------------------------------------------------------------------


def test_every_row_has_complete_citation() -> None:
    """Rule 1: every row traces back to book + edition + printed/physical pages.
    Printed/physical page ranges are union of all landed chunks; +21 offset
    is invariant across chapters II and III (verified at chunk 1 and chunk 2
    boundaries).
    """
    for r in _rows():
        c = r["source_citation"]
        assert c["book"] == BOOK, r
        assert c["edition"] == EDITION, r
        assert isinstance(c["printed_page"], int), r
        assert isinstance(c["physical_pdf_page"], int), r
        assert EXPECTED_PRINTED_PAGE_MIN <= c["printed_page"] <= EXPECTED_PRINTED_PAGE_MAX, r
        assert EXPECTED_PHYSICAL_PAGE_MIN <= c["physical_pdf_page"] <= EXPECTED_PHYSICAL_PAGE_MAX, r
        # +21 offset is invariant across chapters II and III.
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
    "later_horus_names",
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


def test_name_list_fields_present_on_every_row() -> None:
    """Rule 4 (single source of truth): every row carries every name-type
    field with `[]` default when empty, so downstream consumers don't need
    to branch on present-vs-absent. Backfilled by `fix_rows.backfill_
    name_list_fields` across chunks that pre-date a newly-introduced
    name-type field (e.g. chunk 3 added `later_horus_names`)."""
    for r in _rows():
        missing = set(NAME_LIST_FIELDS) - set(r)
        assert not missing, f"{r['leprohon_id']}: missing name-list keys {missing!r}"


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
    """Rows whose `display_name` contains `/` (Leprohon's authorial
    homonym convention) must have `alt_display_names` equal to the
    slash-split parts. Rows without `/` MAY still have `alt_display_names`
    populated — for example, Greek aliases that Leprohon prints in the
    SMALLCAP headword parenthetical (`KHUFU (CHEOPS)` → display_name
    "Khufu", alt_display_names ["Cheops"]).

    Exception: hedge-glyph slashes (two or more consecutive `/`) are
    Leprohon's typography for fragmentary / destroyed readings in the
    Turin Canon, not homonym separators. Rows like `/////` (the Dyn 9–10a
    stub for the destroyed Turin 4,19 entry), `Senen////`, `Shed////`,
    `Hu////`, `Mery///` carry `alt_display_names: []`. Genuine homonyms
    always use a single `/` between alternatives (`Djet/Wadjet`,
    `Khasekhem/Khasekhemwy`, `Qa Hedjet/Hui/Huni`)."""
    for r in _rows():
        if "/" in r["display_name"] and "//" not in r["display_name"]:
            assert r["alt_display_names"] == r["display_name"].split("/"), r


def test_headword_display_names_are_title_cased() -> None:
    """Leprohon prints headwords in SMALLCAP (`1. IRY-HOR`). Agents must
    normalise to Title Case (`Iry-Hor`) — with documented exceptions for
    Leprohon's own typographic conventions:
      1. Letter-tagged Horus entries like `Horus "A"` / `Horus "Pe"`.
      2. Angle-bracketed partial readings like `Ny-<Hor>`.
      3. Parenthesised prefixes like `(Two Ladies) Weneg` (absent Horus).
      4. Quote-wrapped names like `"Hudjefa" (I)` / `"Hudjefa" (II)` used
         for Ramesside-only kings whose names Leprohon flags as uncertain.
      5. Roman-numeral disambiguators in parentheses like `(I)`, `(II)`.

    The test strips leading/trailing non-letter characters from each segment
    before checking the first letter is uppercase."""
    for r in _rows():
        display = r["display_name"]
        # Exception 1: letter-tagged Horus entries (`Horus "A"`, `Horus "Pe"`)
        if display.startswith("Horus") and '"' in display:
            continue
        for part in display.replace("/", " ").split():
            if part.startswith("(") or part.endswith(")"):
                continue  # Exception 3/5: parenthesised groups
            if part.startswith("<"):
                continue  # Exception 2: angle-bracketed
            for seg in part.split("-"):
                if seg.startswith("<"):
                    continue
                # Strip leading/trailing non-alphabetic chars (quotes, etc.).
                stripped = seg.lstrip('"\'').rstrip('"\',.;:')
                if not stripped:
                    continue
                assert stripped[0].isupper(), (
                    f"{r['leprohon_id']}: {display!r} segment {seg!r}"
                )


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


RAMESSIDE_ONLY_TAG = (
    "Ramesside-attested only — no contemporary attestation per "
    "Leprohon's headword asterisk."
)


def _first_source_note(row: dict) -> str:
    """Return the source_note of the first populated name-entry, or empty."""
    for field in NAME_LIST_FIELDS:
        if row[field]:
            return row[field][0].get("source_note") or ""
    return ""


# ---------------------------------------------------------------------------
# Flagship row: leprohon-2.09 Seneferka (recovered from chunk-1 scope miss)
# ---------------------------------------------------------------------------


def test_seneferka_recovered_from_chunk_1_scope_miss() -> None:
    """Leprohon prints a Dyn-2 entry `9. SENEFERKA` on printed p. 30, which
    chunk 1 (PR #83) silently dropped because its scope ended at printed p.
    29. Chunk 2 recovers it: `chapter: "Early Dynastic Period"`, `dynasty_
    label: "Dynasty 2"`, printed_page 30, physical 51."""
    r = _row("leprohon-2.09")
    assert r["display_name"] == "Seneferka"
    assert r["dynasty_number"] == 2
    assert r["dynasty_label"] == "Dynasty 2"
    assert r["chapter"] == "Early Dynastic Period"
    assert r["source_citation"]["printed_page"] == 30
    assert r["source_citation"]["physical_pdf_page"] == 51
    assert r["horus_names"][0]["transliteration"] == "snfr kꜣ"
    assert r["horus_names"][0]["anglicised"] == "senefer ka"
    assert r["horus_names"][0]["translation"] == "The one whom a ka has made perfect"


# ---------------------------------------------------------------------------
# Flagship row: leprohon-4.02 Khufu (Greek alias from headword parenthetical)
# ---------------------------------------------------------------------------


def test_khufu_has_greek_alias_cheops() -> None:
    """Leprohon prints `2. KHUFU (CHEOPS)` in the chapter-III Dyn-4 list.
    The parenthesised Greek form goes into `alt_display_names`."""
    r = _row("leprohon-4.02")
    assert r["display_name"] == "Khufu"
    assert r["alt_display_names"] == ["Cheops"]
    assert r["dynasty_number"] == 4
    assert r["chapter"] == "Old Kingdom"


# ---------------------------------------------------------------------------
# Dyn 8a is contemporarily attested — no Ramesside-only tags despite being
# a sub-dynasty. This test locks in the lesson from the chunk-2 prompt error.
# ---------------------------------------------------------------------------


def test_dyn_8a_is_contemporarily_attested_not_ramesside_only() -> None:
    """Leprohon's Dyn 8a section is titled `Dynasty 8a – attested names` and
    opens `eight rulers who are attested contemporaneously` (p. 44). The
    extraction prompt for chunk 2 incorrectly framed Dyn 8a as Ramesside-
    only (conflating it with Dyn 2a's opening); all three agents correctly
    ignored the wrong instruction per constitutional rule 1 (`work like a
    scholar` — prefer the primary source over the task framing).

    This test locks that in: no Dyn-8a row carries the Ramesside-only tag."""
    dyn_8a_rows = [r for r in _rows() if r["dynasty_label"] == "Dynasty 8a"]
    assert len(dyn_8a_rows) == 8, len(dyn_8a_rows)
    for r in dyn_8a_rows:
        sn = _first_source_note(r)
        assert RAMESSIDE_ONLY_TAG not in sn, (
            f"{r['leprohon_id']} ({r['display_name']}): Dyn 8a is "
            f"contemporarily attested, should not carry the Ramesside-only "
            f"tag — found in source_note: {sn!r}"
        )


# ---------------------------------------------------------------------------
# Dyn 2a, 3a, and the asterisked individual kings ARE Ramesside-only
# ---------------------------------------------------------------------------


def test_ramesside_only_tagging_is_applied_where_expected() -> None:
    """Ramesside-only tag is applied on every headword-asterisked king and
    on every Dyn 2a / 3a entry. Dyn 4.05 Baufre and Dyn 6.07 Queen Neith-
    Iqeret/Nitocris are asterisked-in-parenthetical exceptions that the
    extractors correctly tag."""
    expected_tagged = {
        "leprohon-2a.01",  # Neferkasokar
        "leprohon-2a.02",  # "Hudjefa" (I)
        "leprohon-3.05",  # Qa Hedjet/Hui/Huni (headword asterisk)
        "leprohon-3a.01",  # Sedjes
        "leprohon-3a.02",  # "Hudjefa" (II)
        "leprohon-3a.03",  # Neferkare (I)
        "leprohon-3a.04",  # Nebkare
        "leprohon-4.05",  # Baufre
        "leprohon-6.07",  # Queen Neith-Iqeret / Nitocris
        # Chunk 3 FIP (Dyn 9–10a): 7 explicitly-asterisked headwords plus
        # 1 Senen//// (headword asterisk `5. SENEN ////*`). All except
        # `/////` stub (9-10a.02 — no name entries to attach a tag to)
        # and Neferkare III (9-10a.03 — contemporarily attested per fn. 6)
        # carry the Ramesside-only tag.
        "leprohon-9-10a.01",  # Khety I
        "leprohon-9-10a.04",  # Khety II
        "leprohon-9-10a.05",  # Senen////
        "leprohon-9-10a.06",  # Khety III
        "leprohon-9-10a.07",  # Khety IV
        "leprohon-9-10a.08",  # Shed////
        "leprohon-9-10a.09",  # Hu////
    }
    for lid in expected_tagged:
        r = _row(lid)
        sn = _first_source_note(r)
        assert RAMESSIDE_ONLY_TAG in sn, (
            f"{lid} ({r['display_name']}): expected Ramesside-only tag in "
            f"source_note, got: {sn[:120]!r}"
        )


DUAL_EMIT_PAIRS: dict[str, tuple[tuple[str, int], ...]] = {
    # Extraction-pipeline dual-emissions where a single Leprohon-labelled
    # entry is duplicated into multiple name-type lists. Enumerated
    # explicitly (rather than inferred from shared transliteration) because
    # many kings have COINCIDENTAL text overlaps across name types that
    # are NOT dual-emits — e.g. Qaa's Horus `ḳꜣ-ꜥ` and Nebty `ḳꜣ-ꜥ` are two
    # separate Leprohon entries with different footnote commentary, not a
    # single entry duplicated.
    #
    # Tuple elements are `(field, variant_index)` identifying each copy;
    # all copies must share a single `source_note`.
    "leprohon-2.08": (
        # Khasekhemwy: `Horus/Seth 2` form — the Horus name entry (variant 2),
        # the Nebty name entry (variant 1), and the Seth name entry (variant 1)
        # are all the SAME Leprohon-labelled entry. Historically the Nebty
        # copy carried an additional `nbwy` honorific-transposition footnote
        # that horus/seth did not; the fix_rows pass reconciled them.
        ("horus_names", 2),
        ("nebty_names", 1),
        ("seth_names", 1),
    ),
    "leprohon-9-10a.07": (  # Khety IV: `Throne and birth:` dual
        ("throne_names", 1),
        ("birth_names", 1),
    ),
    "leprohon-9-10b.03": (  # Khety VI: `Throne and birth:` dual
        ("throne_names", 1),
        ("birth_names", 1),
    ),
}


def test_dual_emit_source_notes_are_symmetric() -> None:
    """When the extraction pipeline dual-emits a single Leprohon-labelled
    entry to TWO or more name-type lists (Khasekhemwy's `Horus/Seth 2`;
    Khety IV / Khety VI's `Throne and birth:`), every copy must carry the
    SAME `source_note`. Rule 4 (single source of truth): Ramesside-only
    tags, bracket-reconstruction notes, footnote provenance, and dual-
    classification commentary live on the entry regardless of which list
    a consumer reads from. Regression guard — a future extraction that
    forgets to mirror a tag fails here before the data ships."""
    for lid, pairs in DUAL_EMIT_PAIRS.items():
        r = _row(lid)
        notes = []
        for field, variant_index in pairs:
            candidates = [e for e in r[field] if e["variant_index"] == variant_index]
            assert len(candidates) == 1, (
                f"{lid}: {field}[variant_index={variant_index}] "
                f"expected 1 match, got {len(candidates)}"
            )
            notes.append((field, candidates[0].get("source_note")))
        distinct = {n for _, n in notes}
        assert len(distinct) == 1, (
            f"{lid}: dual-emit source_notes diverge across "
            f"{[f for f, _ in notes]}:\n  " + "\n  ".join(
                f"{f}: {n!r}" for f, n in notes
            )
        )
        # Guard against a future regression where both copies drop their
        # source_note to None — symmetric-but-empty would trivially pass
        # the distinct-values check above without actually preserving the
        # Ramesside-only / bracket / dual-classification tags the pair
        # is supposed to carry. Dual-emits by construction have non-None
        # notes because the dual-emission marker phrase itself (e.g.
        # "Horus/Seth 2 form", "Throne and Birth") is required.
        # Codex review 2026-04-20 PR #86 P2.
        for field, note in notes:
            assert note is not None, (
                f"{lid}: dual-emit entry in {field} has source_note=None; "
                f"dual-emits must carry the canonical marker phrase."
            )


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
