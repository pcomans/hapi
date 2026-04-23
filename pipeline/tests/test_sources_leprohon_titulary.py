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
    "mk": {
        "chapter": "Middle Kingdom",
        "rows_by_dynasty_label": {
            # Dyn 11b: 5 rows — Mentuhotep II has 3 titulary stages
            # (5a/5b/5c), Mentuhotep III (entry 6), Mentuhotep IV (entry
            # 7). Sequence continues from Dyn 11a's tail (Dyn 11a ends
            # at entry 4 Intef III in chunk 3 FIP), which is Leprohon's
            # editorial continuation across chapters IV and V.
            "Dynasty 11b": 5,
            # Dyn 12: 9 rows — Amenemhat I has 2 stages (1a/1b), then
            # Senwosret I (2), Amenemhat II (3), Senwosret II (4),
            # Senwosret III (5), Amenemhat III (6), Amenemhat IV (7),
            # Queen Sobekneferu (8). 7 base entries + 2 stages.
            "Dynasty 12": 9,
        },
        "printed_page_range": (54, 60),
        "physical_page_range": (75, 81),
    },
    "dyn13": {
        # Dyn 13 is chapter-V Middle Kingdom per Leprohon's editorial
        # scheme (despite its post-Sobekneferu chronology). Chapter VI
        # SIP is reserved for Dyn 15-17 Hyksos + Theban (future chunk 7).
        "chapter": "Middle Kingdom",
        "rows_by_dynasty_label": {
            # Leprohon numbers Dyn 13 entries 1-38 contiguously, then
            # skips 39-45, then continues 46-55 (with 49 a "one name lost"
            # stub like the Dyn 9-10a.02 stub). 38 + 10 = 48 rows total.
            # All sparse titularies; most with only Throne + Birth.
            "Dynasty 13": 48,
        },
        "printed_page_range": (60, 71),
        "physical_page_range": (81, 92),
    },
    "dyn13a-14": {
        # Chapter V MK tail — Ramesside-added sub-dynasties: Dyn 13a (7
        # rows), Dyn 14 (40 rows — 19 contiguous + 13 + 3 + multi-slot
        # stub "Three Names Lost" at slots 46-48 + 3 + multi-slot stub
        # "Five Names Lost" at slots 52-56; Leprohon's own numbering
        # skips 20-21 and 35-42), Dyn 14a (6 rows). All `chapter:
        # "Middle Kingdom"` per Leprohon's editorial placement.
        "chapter": "Middle Kingdom",
        "rows_by_dynasty_label": {
            "Dynasty 13a": 7,
            "Dynasty 14": 40,
            "Dynasty 14a": 6,
        },
        "printed_page_range": (72, 80),
        "physical_page_range": (93, 101),
    },
    "sip": {
        # Chapter VI Second Intermediate Period — Dyn 15 Hyksos + Dyn 16
        # Theban + Dyn 16a uncertain + Dyn 17 Theban (Abydos-Dynasty-
        # assigned + core Seventeenth) + Dyn 17a. Multi-slot stubs at
        # 16:11-15, 17:3-10, 17:12-14 collapsed to single rows each.
        "chapter": "Second Intermediate Period",
        "rows_by_dynasty_label": {
            "Dynasty 15": 6,
            "Dynasty 16": 11,
            "Dynasty 16a": 5,
            "Dynasty 17": 19,
            "Dynasty 17a": 1,
        },
        "printed_page_range": (81, 92),
        "physical_page_range": (102, 113),
    },
    "dyn18": {
        # Chapter VII New Kingdom Dyn 18. 15 numbered king entries +
        # 2 multi-stage doublings (Thutmose III 5a/5b separately-numbered
        # MK-style + Akhenaten 10a/10b inline-stage NK convention) =
        # 17 rows. Horemheb (Dyn 18 entry 15) was missed by the chunk-8
        # scope and recovered as the first row of chunk 9 — same
        # editorial convention as chunk 1's missed p. 30 (Seneferka,
        # Neferkasokar, Hudjefa) recovered in chunk 2.
        "chapter": "New Kingdom",
        "rows_by_dynasty_label": {
            "Dynasty 18": 17,
        },
        "printed_page_range": (93, 107),
        "physical_page_range": (114, 128),
    },
    "dyn19": {
        # Chapter VII New Kingdom Dyn 19 (Ramesside founders). 8 numbered
        # king entries: Ramesses I, Sety I, Ramesses II, Merenptah,
        # Sety II, Amenmesse, Siptah, Tausret. The chunk-9 scope was
        # extended from physical 145 → 146 specifically to capture
        # Tausret (Leprohon's Dyn 19 entry 8 sits at the top of physical
        # p. 146 just before the Dyn 20 header). The Horemheb scope-
        # recovery row (counted under Dyn 18 above) is also extracted by
        # chunk-9 agents but lives under "Dynasty 18" for tabulation
        # purposes.
        "chapter": "New Kingdom",
        "rows_by_dynasty_label": {
            "Dynasty 19": 8,
        },
        "printed_page_range": (107, 125),
        "physical_page_range": (128, 146),
    },
    "dyn20": {
        # Chapter VII New Kingdom Dyn 20 (the "Ramesside" line). 10
        # numbered king entries: Sethnakht (founder) + Ramesses III
        # through Ramesses XI. All contemporarily attested per Leprohon's
        # prose preamble.
        "chapter": "New Kingdom",
        "rows_by_dynasty_label": {
            "Dynasty 20": 10,
        },
        "printed_page_range": (125, 135),
        "physical_page_range": (146, 156),
    },
    "late-period": {
        # Chapter IX Late Period — Dyn 26 (Saite) + Dyn 27 (1st Persian)
        # + Dyn 28 (Amyrtaios) + Dyn 29 (Mendesian) + Dyn 30 (Sebennytic)
        # + Dyn 31 (2nd Persian). Per-dynasty counts verified
        # post-extraction.
        "chapter": "Late Period",
        "rows_by_dynasty_label": {
            "Dynasty 26": 6,
            "Dynasty 27": 7,  # includes 3 placeholder rows for Xerxes II / Darius II / Artaxerxes II (no hieroglyphic attestation)
            "Dynasty 28": 1,
            "Dynasty 29": 4,
            "Dynasty 30": 3,
            "Dynasty 31": 4,  # includes Khababash (Egyptian rebel during 2nd Persian period)
        },
        "printed_page_range": (164, 174),
        "physical_page_range": (185, 195),
    },
    "tip-late": {
        # Chapter VIII TIP late — Dyn 23 (Tanite/Theban split) + Dyn 23a
        # (collateral) + Dyn 24 (Saite — Tefnakhte, Bakenrenef) + Dyn 25
        # (Nubian/Kushite — Kashta, Piye, Shabaka, Shabataka, Taharqa,
        # Tantamani). Per-dynasty counts verified post-extraction.
        "chapter": "Third Intermediate Period",
        "rows_by_dynasty_label": {
            "Dynasty 23": 9,
            "Dynasty 23a": 5,
            "Dynasty 24": 2,
            "Dynasty 25": 7,
        },
        "printed_page_range": (153, 163),
        "physical_page_range": (174, 184),
    },
    "tip-early": {
        # Chapter VIII Third Intermediate Period — Dyn 21 (Tanite) +
        # Dyn 21a (Theban HPA parallel) + Dyn 22 (Bubastite Sheshonqs,
        # post-Broekman renumbering: 13 numbered kings) + Dyn 22a
        # (collateral). The TIP chapter was originally scoped as one
        # chunk in the README but split into chunks 11 (this) and 12
        # (Dyn 23+23a+24+25) to keep agent context loads manageable.
        # Initial heuristic estimate of ~49 rows was significantly off;
        # all 3 agents converged on 25.
        "chapter": "Third Intermediate Period",
        "rows_by_dynasty_label": {
            "Dynasty 21": 8,
            "Dynasty 21a": 3,
            "Dynasty 22": 13,
            "Dynasty 22a": 1,
        },
        "printed_page_range": (136, 152),
        "physical_page_range": (157, 173),
    },
    "macedonian-ptolemaic": {
        # Chapter X Macedonian and Ptolemaic Dynasties — Dyn 32
        # (Macedonian: Alexander the Great, Philip Arrhidaeus, Alexander
        # II/IV) + Dyn 33 (Ptolemaic: 17 numbered slots — Ptolemies I-XII,
        # Berenike at slot 12, Cleopatra VII at slot 14, Ptolemies XIII-XV
        # — plus 4 queen-consort sub-entries Arsinoe II, Berenike II,
        # Cleopatra I, Cleopatra II at Leprohon's printed `2A. / 3A. /
        # 5A. / 8A.` sub-headwords, emitted with `stage_suffix: "a"`
        # mirroring the literal headword pattern). Per-README schema
        # convention: dynasty_number 32 for Macedonian, 33 for Ptolemaic
        # (pharaoh.se uses null for both — the README's "consistent with
        # pharaoh.se" rationale is a Leprohon-local extrapolation, not a
        # literal alignment).
        "chapter": "Macedonian and Ptolemaic Dynasties",
        "rows_by_dynasty_label": {
            "Macedonian Dynasty": 3,
            "Ptolemaic Dynasty": 21,  # 17 numbered slots + 4 queen-consort sub-entries
        },
        "printed_page_range": (175, 188),
        "physical_page_range": (196, 209),
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


_LID_RE = re.compile(
    r"^leprohon-"
    r"(?P<dyn_group>\d+(?:-\d+)?[a-z]?)"
    r"\.(?P<seq>\d{2})(?P<stage>[a-z]?)$"
)


def test_leprohon_id_shape() -> None:
    """Every id matches `leprohon-{dynasty_group}.{NN}{stage?}` — NN is
    exactly two digits, optional single-letter `stage` suffix.
    `dynasty_group` is one of:
      - a plain integer (`0`, `3`, `18`);
      - integer + single lowercase suffix (`2a`, `3a`, `8a`, `11a`, `11b`) —
        Leprohon's sub-dynasty sections (Ramesside-only reconstructions for
        2a/3a; contemporarily-attested late-Dyn-11 for 11b; see per-section
        treatment);
      - hyphenated range + suffix (`9-10a`, `9-10b`) — Leprohon's chapter-IV
        combined labels for Dynasties 9 and 10 which he treats as inseparable.

    The optional `stage` suffix marks a titulary-stage (same king, successive
    name sets during reign — Mentuhotep II's a/b/c, Amenemhat I's a/b,
    Akhenaten's a/b). Stages are emitted as separate rows so each carries
    its own full cross-name-type titulary."""
    for r in _rows():
        assert _LID_RE.match(r["leprohon_id"]), r["leprohon_id"]


def test_sequence_matches_id() -> None:
    """`sequence_in_chapter_section` matches the NUMERIC seq group of
    leprohon_id; `stage_suffix` matches the letter stage group when
    present or is None when absent.

    Reuses `_LID_RE`'s own named groups (seq / stage) instead of a
    separate tail regex — the reviewer-called-out redundancy is now
    eliminated. `test_leprohon_id_shape` runs first and asserts the
    ID matches `_LID_RE`, so `.match(...)` here is guaranteed non-None."""
    for r in _rows():
        m = _LID_RE.match(r["leprohon_id"])
        assert m is not None, r["leprohon_id"]
        assert r["sequence_in_chapter_section"] == int(m.group("seq")), r
        stage = m.group("stage") or None
        assert r["stage_suffix"] == stage, (
            f"{r['leprohon_id']}: id stage={stage!r} vs row "
            f"stage_suffix={r['stage_suffix']!r}"
        )


VALID_STAGE_SUFFIXES = frozenset({None, "a", "b", "c"})

# English particles allowed to stay lowercase after the first token in
# `display_name` (e.g. `Alexander the Great`). Title-case convention
# keeps short connectives lowercase. Module-scope per code-reviewer PR
# #99 P2 (was loop-local in test_headword_display_names_are_title_cased).
ENGLISH_PARTICLES = frozenset({"the", "of", "and"})


def test_stage_suffix_is_valid_letter_or_none() -> None:
    """Constraint `stage_suffix ∈ {None, 'a', 'b', 'c'}` per the attested
    domain in Leprohon's titulary-stage numbering (Mentuhotep II a/b/c is
    the widest extent; Amenemhat I a/b; Akhenaten a/b in Dyn 18 — anything
    past 'c' or non-lowercase-letter would be an extraction bug or an
    as-yet-unseen Leprohon convention that warrants a deliberate test
    update). Code-reviewer 2026-04-20 PR #87 P2."""
    for r in _rows():
        assert r["stage_suffix"] in VALID_STAGE_SUFFIXES, (
            f"{r['leprohon_id']}: stage_suffix={r['stage_suffix']!r} "
            f"not in {sorted(VALID_STAGE_SUFFIXES, key=lambda x: '' if x is None else x)!r}"
        )


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

    Exception 1: hedge-glyph slashes (two or more consecutive `/`) are
    Leprohon's typography for fragmentary / destroyed readings in the
    Turin Canon, not homonym separators. Rows like `/////` (the Dyn 9–10a
    stub for the destroyed Turin 4,19 entry), `Senen////`, `Shed////`,
    `Hu////`, `Mery///` carry `alt_display_names: []`. Genuine homonyms
    always use a single `/` between alternatives (`Djet/Wadjet`,
    `Khasekhem/Khasekhemwy`, `Qa Hedjet/Hui/Huni`).

    Exception 2: trailing `(?)` uncertainty markers (chunk 5 Dyn 13 entry
    18 `Seb/Sab (?)`) are preserved verbatim in `display_name` but are
    NOT copied into `alt_display_names` — the `(?)` qualifies the whole
    king-identification, not either homonym individually.

    Exception 3: shared-prefix roman-numeral homonyms — `Alexander II/IV`
    (chunk 14 leprohon-32.03) is Leprohon's contracted form for
    `Alexander II / Alexander IV` (his Egyptian-pharaoh numbering vs the
    standard Macedon numbering). The right-hand segment after the slash
    is a bare roman numeral that does NOT stand alone as a king name;
    `alt_display_names` carries the spelled-out form (`["Alexander II",
    "Alexander IV"]`) for downstream museum matching, not the literal
    slash-split (`["Alexander II", "IV"]`). The test detects this case
    when the right-hand segment after the slash matches the bare-roman-
    numeral pattern (`II`, `III`, `IV`, ..., `XV`)."""
    BARE_ROMAN_RE = re.compile(r"^[IVXLCDM]+$")
    for r in _rows():
        if "/" in r["display_name"] and "//" not in r["display_name"]:
            # Strip trailing `(?)` before splitting — it applies to the
            # whole entry, not to an individual homonym. Also strip
            # whitespace from each split segment because Leprohon's
            # typography varies between `X/Y` (no spaces) and `X / Y`
            # (spaces around the slash).
            stripped = re.sub(r"\s*\(\?\)\s*$", "", r["display_name"])
            segments = [s.strip() for s in stripped.split("/")]
            # Exception 3: if the right-hand segment is a bare roman
            # numeral, expand it by inheriting the left-hand segment's
            # name prefix (`Alexander II/IV` → `["Alexander II",
            # "Alexander IV"]`).
            if (
                len(segments) == 2
                and BARE_ROMAN_RE.match(segments[1])
                and " " in segments[0]
            ):
                prefix = segments[0].rsplit(" ", 1)[0]
                segments = [segments[0], f"{prefix} {segments[1]}"]
            assert r["alt_display_names"] == segments, r


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
      6. Square-bracketed partial readings like `[User]kare (II)` — the
         brackets signal epigraphic reconstruction of a damaged segment.
      7. Hyphenated compound names where later segments are Egyptian
         function words that stay lowercase by convention — e.g.
         `Imy-ra Mesha` ("Overseer Mesha", where `imy-ra` is the Egyptian
         title "who is in the mouth of" and the `ra` is a lowercase
         Egyptian particle, not an English word). The test only requires
         the FIRST hyphen-separated segment of each space-delimited token
         to start uppercase, not every sub-segment.

    The test strips leading/trailing non-letter characters from the first
    segment before checking the first letter is uppercase."""
    for r in _rows():
        display = r["display_name"]
        # Exception 1: letter-tagged Horus entries (`Horus "A"`, `Horus "Pe"`)
        if display.startswith("Horus") and '"' in display:
            continue
        # Exception 6: display names containing fragmentary-reading markers
        # (`[///]`, `///`, `////`) are Leprohon's epigraphic-reconstruction
        # typography and defeat any whitespace-based tokenizer. Skip the
        # title-case check for these entries; the extraction has already
        # preserved the structure verbatim per the verbatim-typography
        # rule, and `display_name` for these rows is not a candidate for
        # alphabetical title-casing anyway.
        if "//" in display or "[" in display or "]" in display:
            continue
        # Strip interior parenthetical expressions (e.g. NK inline-stage
        # markers like `Amenhotep IV (Regnal Years 1 to 5)`) before
        # tokenising. The non-parenthesised portion is the actual king
        # name and is what the title-case rule applies to; the
        # parenthetical is descriptive metadata (regnal years, Greek
        # alias, roman-numeral disambiguator, etc.) that may contain
        # digits, lowercase function words, or other non-title content.
        display = re.sub(r"\s*\([^)]*\)", "", display).strip()
        if not display:
            continue  # all-parenthetical display name (e.g. dummy stub)
        # Exception 8: English particles in proper names (chunk 14
        # `Alexander the Great`). Title-case convention keeps short
        # connectives lowercase. Apply only when the particle appears
        # AFTER the first token (the first word always gets cased).
        # Gemini PR #99: don't just skip validation — assert the particle
        # is actually lowercase, so `Alexander THE Great` would still
        # fail. ENGLISH_PARTICLES set is defined at module scope.
        for idx, part in enumerate(display.replace("/", " ").split()):
            if idx > 0 and part.lower() in ENGLISH_PARTICLES:
                assert part == part.lower(), (
                    f"{r['leprohon_id']}: English particle {part!r} in "
                    f"{display!r} must be lowercase."
                )
                continue
            if part.startswith("(") or part.endswith(")"):
                continue  # Exception 3/5: parenthesised groups
            if part.startswith("<"):
                continue  # Exception 2: angle-bracketed
            # Exception: hedge-glyph segments containing `//` are
            # Leprohon's fragmentary-reading typography (e.g. chunk-5
            # Dyn 13 entry 46 `Mer [///]re`) — skip casing check.
            if "//" in part:
                continue
            # Only check the FIRST hyphen-separated segment of each
            # space-delimited token — exception 7 allows subsequent
            # Egyptian-particle segments to stay lowercase.
            segments = part.split("-")
            first_seg = segments[0]
            if first_seg.startswith("<"):
                continue
            # Strip leading/trailing non-alphabetic chars (quotes,
            # brackets, slashes, etc.) — exception 4 / 6.
            strip_set = '"\'[]/,.;:\\-'
            stripped = first_seg.strip(strip_set)
            if not stripped:
                continue
            assert stripped[0].isupper(), (
                f"{r['leprohon_id']}: {display!r} segment {first_seg!r}"
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


def test_tip_late_no_ramesside_only_tags() -> None:
    """All Dyn 23 / 23a / 24 / 25 kings (chunk 12 TIP-late) are
    contemporarily attested per Leprohon's prose preamble. Code-reviewer
    PR #95 P2 guard mirroring the chunk-9/10/11 per-preamble pattern.
    Per CLAUDE.md rule 3, the invariant cannot live only in prose."""
    tip_late_labels = {"Dynasty 23", "Dynasty 23a", "Dynasty 24", "Dynasty 25"}
    rows = [r for r in _rows() if r["dynasty_label"] in tip_late_labels]
    assert len(rows) == 23, len(rows)
    for r in rows:
        sn = _first_source_note(r)
        assert RAMESSIDE_ONLY_TAG not in sn, (
            f"{r['leprohon_id']} ({r['display_name']}): {r['dynasty_label']} "
            f"is contemporarily attested, should not carry the Ramesside-only "
            f"tag — found in source_note: {sn!r}"
        )


def test_tip_early_no_ramesside_only_tags() -> None:
    """All Dyn 21 / 21a / 22 / 22a kings (chunk 11 TIP-early) are
    contemporarily attested — Leprohon's chapter VIII prose preamble
    confirms the post-Ramesside line is uniformly contemporarily
    attested. Code-reviewer PR #94 P2 guard mirroring the chunk-9/10
    Ramesside-exclusion guards. Per CLAUDE.md rule 3, the invariant
    cannot live only in prose / prompt markdown."""
    tip_early_labels = {"Dynasty 21", "Dynasty 21a", "Dynasty 22", "Dynasty 22a"}
    rows = [r for r in _rows() if r["dynasty_label"] in tip_early_labels]
    assert len(rows) == 25, len(rows)
    for r in rows:
        sn = _first_source_note(r)
        assert RAMESSIDE_ONLY_TAG not in sn, (
            f"{r['leprohon_id']} ({r['display_name']}): {r['dynasty_label']} "
            f"is contemporarily attested, should not carry the Ramesside-only "
            f"tag — found in source_note: {sn!r}"
        )


def test_dyn_20_is_contemporarily_attested_no_ramesside_only_tags() -> None:
    """All 10 Dyn 20 kings (Sethnakht + Ramesses III through XI) are
    contemporarily attested per Leprohon's chapter VII NK Dyn 20 prose
    preamble. Code-reviewer PR #93 P2-a guard mirroring the chunk-9
    Dyn 19 guard. Per CLAUDE.md rule 3 (deterministic enforcement),
    the "no Ramesside-only tags in Dyn 20" invariant cannot live only
    in prose / prompt markdown."""
    dyn_20_rows = [r for r in _rows() if r["dynasty_label"] == "Dynasty 20"]
    assert len(dyn_20_rows) == 10, len(dyn_20_rows)
    for r in dyn_20_rows:
        sn = _first_source_note(r)
        assert RAMESSIDE_ONLY_TAG not in sn, (
            f"{r['leprohon_id']} ({r['display_name']}): Dyn 20 is "
            f"contemporarily attested, should not carry the Ramesside-only "
            f"tag — found in source_note: {sn!r}"
        )


def test_dyn_19_is_contemporarily_attested_no_ramesside_only_tags() -> None:
    """Per Leprohon's chapter VII NK Dyn 19 prose preamble, all 8 Dyn 19
    kings (Ramesses I, Sety I, Ramesses II, Merenptah, Sety II,
    Amenmesse, Siptah, Tausret) are contemporarily attested with full
    titularies; none should carry the Ramesside-only tag. Code-reviewer
    PR #92 P2-a guard against future regression."""
    dyn_19_rows = [r for r in _rows() if r["dynasty_label"] == "Dynasty 19"]
    assert len(dyn_19_rows) >= 8, len(dyn_19_rows)
    for r in dyn_19_rows:
        sn = _first_source_note(r)
        assert RAMESSIDE_ONLY_TAG not in sn, (
            f"{r['leprohon_id']} ({r['display_name']}): Dyn 19 is "
            f"contemporarily attested, should not carry the Ramesside-only "
            f"tag — found in source_note: {sn!r}"
        )


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
        # Chunk 5 Dyn 13: 11 headword-asterisked entries
        "leprohon-13.07",  # Iufni
        "leprohon-13.11",  # Sewadjkare (I)
        "leprohon-13.12",  # Nedjemibre
        "leprohon-13.36",  # Ined
        "leprohon-13.37",  # Sobekhotep VII
        "leprohon-13.46",  # Mer [///]re
        "leprohon-13.48",  # Mer Ka [Re]
        "leprohon-13.51",  # Ibi II
        "leprohon-13.52",  # (headword-asterisked entry)
        "leprohon-13.53",  # Se /// Kare
        "leprohon-13.54",  # Se /// Kare sibling
        # Chunk 6 Dyn 14: 28 headword-asterisked entries. Verified
        # tagged per agent-majority vote, per egyptologist-reviewer
        # confirmation, and per code-reviewer P2-c regression guard.
        "leprohon-14.07",
        "leprohon-14.08",
        "leprohon-14.09",
        "leprohon-14.10",
        "leprohon-14.11",
        "leprohon-14.12",
        "leprohon-14.13",
        "leprohon-14.15",
        "leprohon-14.16",
        "leprohon-14.17",
        "leprohon-14.18",
        "leprohon-14.23",
        "leprohon-14.24",
        "leprohon-14.25",
        "leprohon-14.26",
        "leprohon-14.27",
        "leprohon-14.28",
        "leprohon-14.29",
        "leprohon-14.30",
        "leprohon-14.31",
        "leprohon-14.32",
        "leprohon-14.33",
        "leprohon-14.34",
        "leprohon-14.43",
        "leprohon-14.44",
        "leprohon-14.45",
        "leprohon-14.49",
        "leprohon-14.51",
        # Chunk 7 SIP: 7 headword-asterisked entries across Dyn 16 and
        # Dyn 17 (no asterisks in Dyn 15 Hyksos, Dyn 16a, Dyn 17a).
        "leprohon-16.07",  # Nebiryerau II
        "leprohon-16.10",  # Sekhemreshedwaset
        "leprohon-17.01",  # Weser /// Re (I)
        "leprohon-17.02",  # Weser /// Re (II)
        "leprohon-17.11",  # /// Hebre (I)
        "leprohon-17.15",  # /// Heb(?)-Re (II)
        "leprohon-17.16",  # /// Webenre (III)
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
    "leprohon-13.35": (  # Sewadjtu: `Throne and Birth names:` dual
        ("throne_names", 1),
        ("birth_names", 1),
    ),
    # Chunk 7 Dyn 15 Hyksos: `Title and [birth] name:` combined labels
    # (Leprohon's `ḥqꜣ ḫꜣswt` "Ruler of Foreign Lands" ruler-title fused
    # with the king's personal name) — dual-emitted to throne_names +
    # birth_names per chunk-7 convention.
    "leprohon-15.01": (  # Semqen
        ("throne_names", 1),
        ("birth_names", 1),
    ),
    "leprohon-15.02": (  # Aper-anati
        ("throne_names", 1),
        ("birth_names", 1),
    ),
    "leprohon-15.03": (  # Seker-her
        ("throne_names", 1),
        ("birth_names", 1),
    ),
    # Apepi has 2 plain Throne names PLUS the Title-and-birth-name
    # combined entry as Throne variant 3; the dual-emit partner lives
    # at birth_names variant 1.
    "leprohon-15.05": (  # Apepi / Apophis
        ("throne_names", 3),
        ("birth_names", 1),
    ),
    # Chunk 8 Dyn 18: Smenkhkare's `Throne and Birth names:` combined
    # cartouche — same dual-emit pattern as Sewadjtu (13.35) and the
    # chunk-3 Khety IV / Khety VI.
    "leprohon-18.12": (
        ("throne_names", 1),
        ("birth_names", 1),
    ),
}


def test_akhenaten_inline_stage_correlation() -> None:
    """Flagship test for the chunk-8 NK inline-stage convention. Akhenaten
    (`leprohon-18.10`) is printed by Leprohon as a single numbered entry
    with internal `a. Regnal Years 1 to 5` and `b. Regnal Years 5 to 17`
    sub-section markers. Each stage's full titulary differs because the
    king changed his Birth name from Amenhotep IV to Akhenaten mid-reign.
    Constraints:
      - Both stages share the same Throne name (`nfr ḫprw rꜥ wꜥ n rꜥ`,
        Neferkheperure-waenre).
      - Stage 10a's display_name preserves "Amenhotep IV", and 10a's
        `alt_display_names` lists the bare "Amenhotep IV" form.
      - Stage 10b's display_name preserves "Akhenaten", and 10b's
        `alt_display_names` lists the bare "Akhenaten" form.
      - Both stages have `stage_suffix` set to "a" / "b" respectively;
        sequence_in_chapter_section is 10 on both.
      - Stage 10a carries the canonical NK inline-stage marker phrase
        in its first populated name-entry's source_note; 10b does not."""
    a = _row("leprohon-18.10a")
    b = _row("leprohon-18.10b")
    assert a["sequence_in_chapter_section"] == 10
    assert b["sequence_in_chapter_section"] == 10
    assert a["stage_suffix"] == "a"
    assert b["stage_suffix"] == "b"
    assert a["throne_names"][0]["transliteration"] == b["throne_names"][0]["transliteration"], (
        f"Akhenaten 10a/10b throne names differ: "
        f"a={a['throne_names'][0]['transliteration']!r} vs "
        f"b={b['throne_names'][0]['transliteration']!r}"
    )
    assert "Amenhotep IV" in a["alt_display_names"], a["alt_display_names"]
    assert "Akhenaten" in b["alt_display_names"], b["alt_display_names"]
    assert "Amenhotep IV" in a["display_name"], a["display_name"]
    assert "Akhenaten" in b["display_name"], b["display_name"]


def test_thutmose_iii_stage_correlation() -> None:
    """Flagship test for chunk-8 MK-style separately-numbered stages
    (same convention as chunk-4 Mentuhotep II 5a/5b/5c). Thutmose III
    (`leprohon-18.05`) has stages 5a and 5b. Constraints:
      - Both stages share the same display_name root "Thutmose III".
      - sequence_in_chapter_section is 5 on both.
      - stage_suffix is "a" / "b" respectively.
      - Both have populated horus_names (the densest titulary in the
        book — 5b alone has multiple Horus / Throne / Birth variants)."""
    a = _row("leprohon-18.05a")
    b = _row("leprohon-18.05b")
    assert a["sequence_in_chapter_section"] == 5
    assert b["sequence_in_chapter_section"] == 5
    assert a["stage_suffix"] == "a"
    assert b["stage_suffix"] == "b"
    assert "Thutmose III" in a["display_name"], a["display_name"]
    assert "Thutmose III" in b["display_name"], b["display_name"]
    assert len(a["horus_names"]) >= 1
    assert len(b["horus_names"]) >= 2, (
        "Thutmose III stage b is documented as the densest titulary in "
        f"chunk 8; expected ≥2 Horus variants, got {len(b['horus_names'])}"
    )


def test_ay_birth_name_complete() -> None:
    """Regression guard for the chunk-8 scope-recovery: Ay (entry 14)
    has his Birth name spilled across the p. 127 / p. 128 boundary in
    Leprohon's printing. The original chunk scope (114-127) truncated
    Ay before the Birth name; egyptologist-reviewer 2026-04-20 P1 on
    PR #91 flagged this as blocking. Scope was extended to p. 128 to
    capture Ay's complete entry. This test guards that Ay's Birth
    name is populated (matching `it nṯr iy` per Leprohon p. 107)."""
    r = _row("leprohon-18.14")
    assert r["display_name"] == "Ay"
    assert len(r["birth_names"]) >= 1, (
        "Ay's Birth name should be populated — chunk-8 scope was "
        "extended specifically to capture this. Empty birth_names "
        "indicates the chunk-truncation regression has reappeared."
    )
    assert "it nṯr iy" in r["birth_names"][0]["transliteration"], (
        f"Ay's Birth name should contain `it nṯr iy` per Leprohon p. 107; "
        f"got {r['birth_names'][0]['transliteration']!r}"
    )


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


def test_dyn23_sheshonq_rows_preserve_shoshenq_aliases() -> None:
    """Regression lock for PR #96: chunk 13 accidentally cleared
    `alt_display_names` on three Dyn 23 Sheshonq rows, stripping the
    `Shoshenq VI/VIa/VII` museum-spelling variants that chunk 12 added
    for downstream matching. Codex review caught it post-merge; this
    test prevents the same class of regression on future chunks.
    """
    expected = {
        "leprohon-23.03": ["Shoshenq VI"],
        "leprohon-23.07": ["Shoshenq VIa"],
        "leprohon-23.09": ["Shoshenq VII"],
    }
    for lid, aliases in expected.items():
        r = _row(lid)
        assert r["alt_display_names"] == aliases, (
            f"{lid}: expected alt_display_names={aliases}, "
            f"got {r['alt_display_names']}"
        )


def test_chunk14_macedonian_ptolemaic_dynasty_numbering() -> None:
    """Chunk 14 (Ch X Macedonian + Ptolemaic) extends the dynasty-number
    domain beyond the standard 1-31 range. Per the README schema convention:
    dynasty_number=32 for Macedonian, 33 for Ptolemaic. Lock both.
    """
    macedonian = [r for r in _rows() if r["dynasty_number"] == 32]
    ptolemaic = [r for r in _rows() if r["dynasty_number"] == 33]
    assert len(macedonian) == 3, len(macedonian)
    assert len(ptolemaic) == 21, len(ptolemaic)
    for r in macedonian:
        assert r["dynasty_label"] == "Macedonian Dynasty", r
    for r in ptolemaic:
        assert r["dynasty_label"] == "Ptolemaic Dynasty", r


def test_chunk14_queen_consort_sub_entries_use_stage_suffix_a() -> None:
    """Chunk 14 (Ch X Macedonian + Ptolemaic) emits the four queen-consort
    sub-entries (Arsinoe II, Berenike II, Cleopatra I, Cleopatra II) as
    separate rows mirroring Leprohon's printed `2A. / 3A. / 5A. / 8A.`
    sub-headword pattern. They carry `stage_suffix: "a"` to disambiguate
    from the `2 / 3 / 5 / 8`-numbered Ptolemy rows they follow. This is a
    structural extension of `stage_suffix` beyond the README's original
    "same king, successive titulary stages" semantic — flagged by the
    egyptologist-reviewer 2026-04-21 as a semantic overload, deferred to
    a future schema-change PR (see transcribe.md chunk-14 log).
    """
    expected = {
        "leprohon-33.02a": "Arsinoe II",
        "leprohon-33.03a": "Berenike II",
        "leprohon-33.05a": "Cleopatra I",
        "leprohon-33.08a": "Cleopatra II",
    }
    for lid, name in expected.items():
        r = _row(lid)
        assert r["stage_suffix"] == "a", f"{lid}: stage_suffix={r['stage_suffix']!r}"
        assert r["display_name"] == name, f"{lid}: display_name={r['display_name']!r}"
        assert r["dynasty_number"] == 33, lid
        assert r["dynasty_label"] == "Ptolemaic Dynasty", lid


def test_chunk14_alexander_ii_iv_slashed_homonym() -> None:
    """Chunk 14: king 3 of the Macedonian Dynasty has a slashed-homonym
    headword `ALEXANDER II/IV` (Leprohon's chapter preamble names him
    `Alexander II`; modern scholarship calls him `Alexander IV` of Macedon).
    Per chunk-1 slashed-homonym convention, both forms populate
    alt_display_names.
    """
    r = _row("leprohon-32.03")
    assert r["display_name"] == "Alexander II/IV", r["display_name"]
    assert r["alt_display_names"] == ["Alexander II", "Alexander IV"], r["alt_display_names"]


def test_chunk14_ptolemaic_kings_with_no_attested_titulary_have_empty_name_lists() -> None:
    """Leprohon p. 182 / 186 / 188 explicitly print "No royal titulary is
    attested in hieroglyphs" for Ptolemy VII (slot 7), Ptolemy XI (slot
    11), Ptolemy XIII (slot 15), Ptolemy XIV (slot 16). Their reconciled
    rows must be present (the row exists, the king is named) but every
    name-list field must be empty.
    """
    name_fields = (
        "horus_names",
        "nebty_names",
        "golden_horus_names",
        "throne_names",
        "birth_names",
        "later_cartouche_names",
        "later_horus_names",
        "seth_names",
    )
    for lid in ("leprohon-33.07", "leprohon-33.11", "leprohon-33.15", "leprohon-33.16"):
        r = _row(lid)
        for field in name_fields:
            assert r[field] == [], f"{lid}.{field} should be empty, got {r[field]!r}"


def test_chunk14_berenike_has_berenike_iii_alias() -> None:
    """Regression lock for the chunk-14 fix_rows correction: Berenike at
    Ptolemaic slot 12 is `Berenike III` in standard scholarship (daughter
    of Ptolemy IX, brief 81 BCE co-rule). Leprohon prints only `BERENIKE`
    as the headword, so display_name stays bare; the disambiguated form
    lives in alt_display_names for Phase-A museum matching.
    """
    r = _row("leprohon-33.12")
    assert r["display_name"] == "Berenike", r["display_name"]
    assert r["alt_display_names"] == ["Berenike III"], r["alt_display_names"]


def test_chunk14_macedonian_ptolemaic_no_ramesside_only_tags() -> None:
    """All Macedonian and Ptolemaic kings are contemporarily attested
    (Egyptian-era textual, not Ramesside-king-list reconstructions). The
    chunk-14 prompt asserts this in prose; per CLAUDE.md rule 3 the
    invariant needs a deterministic test — matches the chunk-9/10/11/12
    per-preamble pattern. Code-reviewer PR #99 P1.
    """
    chapter_x_labels = {"Macedonian Dynasty", "Ptolemaic Dynasty"}
    rows = [r for r in _rows() if r["dynasty_label"] in chapter_x_labels]
    assert len(rows) == 24, len(rows)
    for r in rows:
        sn = _first_source_note(r)
        assert RAMESSIDE_ONLY_TAG not in sn, (
            f"{r['leprohon_id']} ({r['display_name']}): {r['dynasty_label']} "
            f"is contemporarily attested, should not carry the Ramesside-only "
            f"tag — found in source_note: {sn!r}"
        )


def test_chunk14_cleopatra_i_horus_translit_uses_corrected_khnum_token() -> None:
    """Regression lock for the chunk-14 pypdf-text-layer correction:
    Cleopatra I's Horus name had `ẖḳr(t).n ẖnmw` in the deterministic
    pypdf+MdC output, but Leprohon's PDF p. 181 visually prints
    `ḫkr(t).n ẖnmw` (the text layer mis-encoded `ḫ` as `X` and `k` as
    `q`). fix_rows.py applies the correction; this test prevents a
    regression if the pypdf transcription is ever re-run.
    """
    r = _row("leprohon-33.05a")
    translit = r["horus_names"][0]["transliteration"]
    assert "ḫkr(t).n ẖnmw" in translit, translit
    assert "ẖḳr(t).n ẖnmw" not in translit, translit


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
