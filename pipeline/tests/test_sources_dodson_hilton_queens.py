"""Structural value-assertion tests for Dodson & Hilton queens extract.

Per rule 5: every populated field on a fixture row is asserted.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SOURCE_DIR = (
    Path(__file__).parent.parent
    / "pipeline"
    / "authority"
    / "sources"
    / "dodson-hilton-queens"
)
JSONL = SOURCE_DIR / "reconciled.jsonl"

EDITION = "Thames & Hudson 2004 hardback"

# Pre-Amarna chunk (Chapter 3 "The Power and the Glory" Brief Lives,
# printed pp. 137-141 / physical pp. 126-130).
PDF_PAGES_POWER = "126-130"
SUB_PERIOD_POWER = "The Power and the Glory"
CITATION_POWER = {"pdf_pages": PDF_PAGES_POWER, "edition": EDITION}

# Amarna chunk (Chapter 3 "The Amarna Interlude" Brief Lives,
# printed pp. 154-157 / physical pp. 142-145).
PDF_PAGES_AMARNA = "142-145"
SUB_PERIOD_AMARNA = "The Amarna Interlude"
CITATION_AMARNA = {"pdf_pages": PDF_PAGES_AMARNA, "edition": EDITION}

# Ramesside chunk (Chapter 3 House / Feud / Decline Brief Lives across
# three non-contiguous sub-blocks).
PDF_PAGES_HOUSE = "157-162"
PDF_PAGES_FEUD = "169-170"
PDF_PAGES_DECLINE = "178-180"
SUB_PERIOD_HOUSE = "The House of Ramesses"
SUB_PERIOD_FEUD = "The Feud of the Ramessides"
SUB_PERIOD_DECLINE = "The Decline of the Ramessides"
CITATION_HOUSE = {"pdf_pages": PDF_PAGES_HOUSE, "edition": EDITION}
CITATION_FEUD = {"pdf_pages": PDF_PAGES_FEUD, "edition": EDITION}
CITATION_DECLINE = {"pdf_pages": PDF_PAGES_DECLINE, "edition": EDITION}


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(json.loads(line) for line in JSONL.read_text().splitlines() if line.strip())


def _row(dh_id: str, sub_period: str | None = None) -> dict:
    """Return the unique row matching `dh_id` (+ optional `sub_period`).

    Chunks 1 and 2 row tests pass `dh_id` only — those ids are unique
    across the file. The Ramesside chunk introduced cross-section
    duplicates (`Takhat A`, `Isetneferet C`, `Ramesses C` each appear
    in two `sub_period`s); callers targeting a specific sub_period
    disambiguate by passing `sub_period`.
    """
    if sub_period is not None:
        hits = [r for r in _rows() if r["dh_id"] == dh_id and r["sub_period"] == sub_period]
        if len(hits) != 1:
            raise AssertionError(
                f"expected 1 row for ({dh_id!r}, {sub_period!r}), got {len(hits)}"
            )
        return hits[0]
    hits = [r for r in _rows() if r["dh_id"] == dh_id]
    if len(hits) != 1:
        raise AssertionError(
            f"expected 1 row for {dh_id!r}, got {len(hits)} "
            f"(sub_periods: {sorted({r['sub_period'] for r in hits})}). "
            f"Pass sub_period= to disambiguate cross-section duplicates."
        )
    return hits[0]


def _assert_full_row(dh_id: str, expected: dict, sub_period: str | None = None) -> None:
    """Assert full-row equality per rule 5. Every schema field must be
    present in `expected`; the row must match key-for-key, value-for-value.
    """
    row = _row(dh_id, sub_period=sub_period)
    schema_fields = {
        "dh_id", "name", "alt_names", "roles", "sex",
        "spouse_names", "father_name", "mother_name", "children_names",
        "dynasty", "sub_period", "unplaced",
        "notes", "source_citation",
    }
    missing = schema_fields - expected.keys()
    assert not missing, f"{dh_id}: test fixture missing schema field(s) {missing}"
    extra = expected.keys() - schema_fields
    assert not extra, f"{dh_id}: test fixture has non-schema field(s) {extra}"
    for k in schema_fields:
        assert row[k] == expected[k], (
            f"{dh_id}.{k}: stored {row[k]!r} != expected {expected[k]!r}"
        )


# ---------------------------------------------------------------------------
# Cross-file invariants
# ---------------------------------------------------------------------------


def test_row_count() -> None:
    """Power (59) + Amarna (41) + Ramesside (170) = 270 rows total."""
    assert len(_rows()) == 270, len(_rows())


def test_row_counts_per_chunk() -> None:
    """Per-sub_period row counts:
    - Power and Glory: 47 placed + 12 Unplaced = 59
    - Amarna Interlude: 41 (36 named + 5 lacuna; no Unplaced)
    - House of Ramesses: 125 (Dyn 19 pt 1 — Ramesses II's family is the
      densest sub-block in the book)
    - Feud of the Ramessides: 10
    - Decline of the Ramessides: 35 (33 placed + 2 Unplaced:
      Anuketemheb, Taiay)
    """
    by_period: dict[str, int] = {}
    for r in _rows():
        by_period[r["sub_period"]] = by_period.get(r["sub_period"], 0) + 1
    assert by_period == {
        SUB_PERIOD_POWER: 59,
        SUB_PERIOD_AMARNA: 41,
        SUB_PERIOD_HOUSE: 125,
        SUB_PERIOD_FEUD: 10,
        SUB_PERIOD_DECLINE: 35,
    }, by_period


CROSS_SECTION_DUPLICATE_IDS = {
    # D&H lists these individuals under two Brief Lives sub-sections each.
    # The composite `(dh_id, sub_period)` is the row key; `dh_id` alone
    # is not unique across the file.
    "Takhat A": {SUB_PERIOD_HOUSE, SUB_PERIOD_FEUD},
    "Isetneferet C": {SUB_PERIOD_HOUSE, SUB_PERIOD_FEUD},
    # Ramesses C is a reuse of the D&H letter across two genealogies:
    # Ramesses-II's grandson in House vs Ramesses-III's heir
    # (later Ramesses IV) in Decline. The same dh_id refers to TWO
    # different individuals; Phase A does not reconcile these.
    "Ramesses C": {SUB_PERIOD_HOUSE, SUB_PERIOD_DECLINE},
}


def test_composite_key_is_unique() -> None:
    """`(dh_id, sub_period)` is the row key. Duplicates on this key
    would indicate an extraction / merge bug. The chunks 1-2 tests
    used to assert `dh_id` alone was unique — replaced because chunk 3
    introduced cross-section duplicates (see CROSS_SECTION_DUPLICATE_IDS).
    """
    keys = [(r["dh_id"], r["sub_period"]) for r in _rows()]
    assert len(keys) == len(set(keys)), "duplicate (dh_id, sub_period) detected"


def test_cross_section_duplicate_ids_match_expected_set() -> None:
    """Exactly three `dh_id`s appear under two `sub_period`s each.
    Guards against accidental introduction of additional duplicates
    (which would indicate an extraction ambiguity) or loss of one
    (which would indicate a merge / fix_rows bug collapsing legitimate
    D&H-authorial cases).
    """
    from collections import defaultdict
    by_id: dict[str, set[str]] = defaultdict(set)
    for r in _rows():
        by_id[r["dh_id"]].add(r["sub_period"])
    actual_duplicates = {k: v for k, v in by_id.items() if len(v) > 1}
    assert actual_duplicates == CROSS_SECTION_DUPLICATE_IDS, actual_duplicates


def test_every_row_has_complete_citation() -> None:
    """Each row's `source_citation` matches the chunk it came from."""
    citations = {
        SUB_PERIOD_POWER: CITATION_POWER,
        SUB_PERIOD_AMARNA: CITATION_AMARNA,
        SUB_PERIOD_HOUSE: CITATION_HOUSE,
        SUB_PERIOD_FEUD: CITATION_FEUD,
        SUB_PERIOD_DECLINE: CITATION_DECLINE,
    }
    for r in _rows():
        sub_period = r["sub_period"]
        assert sub_period in citations, (
            f"unknown sub_period {sub_period!r} for row {r}"
        )
        expected = citations[sub_period]
        assert r["source_citation"] == expected, r


def test_dynasty_per_chunk() -> None:
    """Dynasty alignment: chunks 1-2 are Dyn 18; House + Feud are Dyn 19;
    Decline (incl. Unplaced heading `in 19th and 20th Dynasties`) is
    Dyn 20 by default unless a row's prose anchors it to 19. Nothing
    in the current extract falls into that escape hatch.
    """
    expected_dynasty = {
        SUB_PERIOD_POWER: 18,
        SUB_PERIOD_AMARNA: 18,
        SUB_PERIOD_HOUSE: 19,
        SUB_PERIOD_FEUD: 19,
        SUB_PERIOD_DECLINE: 20,
    }
    for r in _rows():
        assert r["dynasty"] == expected_dynasty[r["sub_period"]], r


POWER_UNPLACED_IDS = frozenset({
    "Amenemhat Q", "Henut Q", "Henutiunu", "Merybennu", "Meryetptah A",
    "Nebetnehat A", "Sithori", "Tatau", "Thutmose Q", "Ti", "Wiay A",
    "[...]pentepkau",
})
DECLINE_UNPLACED_IDS = frozenset({"Anuketemheb", "Taiay"})


def test_unplaced_set_is_the_expected_ids() -> None:
    """D&H's Unplaced sub-blocks: 12 at the end of Power (printed p. 141)
    + 2 at the end of Decline (printed p. 194) = 14 unplaced rows total.
    No Unplaced sub-block in Amarna / House / Feud.
    """
    unplaced = [r for r in _rows() if r["unplaced"]]
    assert len(unplaced) == 14, f"expected 14 unplaced, got {len(unplaced)}"
    assert {r["dh_id"] for r in unplaced} == POWER_UNPLACED_IDS | DECLINE_UNPLACED_IDS
    power_unplaced = {r["dh_id"] for r in unplaced if r["sub_period"] == SUB_PERIOD_POWER}
    decline_unplaced = {r["dh_id"] for r in unplaced if r["sub_period"] == SUB_PERIOD_DECLINE}
    assert power_unplaced == POWER_UNPLACED_IDS
    assert decline_unplaced == DECLINE_UNPLACED_IDS


def test_unplaced_rows_sort_last_in_reconciled_jsonl() -> None:
    """The 14 unplaced rows must occupy the trailing 14 positions of
    `reconciled.jsonl` — merge.py's sort groups them into a final bin so
    the file reads as placed-alphabetical, then unplaced-alphabetical.
    Regression on the code-reviewer-flagged sort-key bug from PR #38.
    """
    rows = _rows()
    for r in rows[:-14]:
        assert r["unplaced"] is False, r["dh_id"]
    for r in rows[-14:]:
        assert r["unplaced"] is True, r["dh_id"]


def test_lacuna_prefixed_ids_sort_last_within_each_bin() -> None:
    """Regression test for the sort-key lacuna bug fixed on PR #38.
    Names starting with `[` or `–` are D&H's lacuna/tentative-identity
    markers; ASCII/Unicode default ordering would put `[` BEFORE every
    letter (sort first) and `–` AFTER every letter (sort last),
    scattering lacunae to both ends. The `_sort_key_for` closure must
    place lacuna-prefixed ids at the END of whichever top-level bin
    (placed / unplaced) they belong to.

    - Amarna chunk contributes 5 placed lacunae (`[...]18A–H`, `[...]18J`,
      `[...]18K–N`, `–18P`, `–18Q`).
    - House chunk contributes 7 placed lacunae (`[...]Jheb`,
      `[...]khesbed`, `[...]taweret`, `[...]19A`, `[...]19B`, plus
      one inside-name-brackets like `[Mut]metennefer`, `[R]uia`,
      `[Set]emnakhte` — but those are letter-prefixed under
      LACUNA_PREFIXES, since LACUNA_PREFIXES is defined as starts-with
      `[` or `–`, which includes all of them).
    - Feud chunk contributes 1 placed lacuna (`[...]19C`).
    - Decline chunk contributes 0 lacunae (both unplaced entries are
      letter-prefixed).
    - Power chunk contributes 1 unplaced lacuna (`[...]pentepkau`).

    Composite-key detail: `Ramesses C` under House sorts adjacent to
    `Ramesses C` under Decline via the `sub_period` tiebreaker.
    """
    rows = _rows()
    lacuna_prefixes = ("[", "–")

    placed = [r for r in rows if not r["unplaced"]]
    # 270 - 14 unplaced = 256 placed.
    assert len(placed) == 256, len(placed)

    # All lacuna-prefixed placed rows must be at the tail of the placed
    # block. Count them and assert no lacuna-prefixed row appears before
    # the final run.
    lacuna_placed = [i for i, r in enumerate(placed) if r["dh_id"].startswith(lacuna_prefixes)]
    assert lacuna_placed, "expected at least some lacuna-prefixed placed rows"
    # All lacuna indices must be contiguous and at the end of the placed
    # block — i.e. the run covers exactly `placed[-len(lacuna_placed):]`.
    tail_len = len(lacuna_placed)
    assert lacuna_placed == list(range(len(placed) - tail_len, len(placed))), (
        f"lacuna-prefixed placed rows are not contiguous at the tail: {lacuna_placed}"
    )

    unplaced = [r for r in rows if r["unplaced"]]
    assert len(unplaced) == 14, len(unplaced)
    # `[...]pentepkau` (Power unplaced, lacuna) sorts after the other
    # Power unplaced entries (letter-prefixed) but before Decline's
    # Unplaced entries (letter-prefixed: Anuketemheb, Taiay).
    # The sort key is (unplaced_bin=1, lacuna_sub_bin, dh_id.lower(),
    # sub_period); within the unplaced bin, letter-prefixed rows from
    # both Power and Decline sort before `[...]pentepkau` regardless of
    # sub_period.
    assert unplaced[-1]["dh_id"] == "[...]pentepkau", unplaced[-1]["dh_id"]
    for r in unplaced[:-1]:
        assert not r["dh_id"].startswith(lacuna_prefixes), r["dh_id"]


def test_sex_inference_covers_every_row() -> None:
    for r in _rows():
        assert r["sex"] in ("male", "female"), r


def test_role_code_set_spans_the_known_codes() -> None:
    """Every known D&H code asserted-present across the three chunks."""
    all_codes: set[str] = set()
    for r in _rows():
        all_codes.update(r["roles"])
    # Power-and-Glory codes:
    for expected in ["KM", "KW", "KGW", "GW", "KSis", "KD", "KSon", "EKSon"]:
        assert expected in all_codes, f"expected Power code {expected!r} never extracted"
    # Amarna-Interlude codes (first introduced there):
    for expected in ["KDB", "L2L", "KSonN", "MULE", "GBW", "King of Mitanni"]:
        assert expected in all_codes, f"expected Amarna code {expected!r} never extracted"
    # Ramesside codes (new in chunk 3 across House / Feud / Decline).
    # Includes D&H's distinctive leading-digit form (`1KSonB`, `1KSon`,
    # `1Genmo`) for first-born sons and some niche roles the earlier
    # chunks didn't exercise.
    for expected in [
        "1KSonB", "1KSon", "1Genmo", "EKSonB", "KSonB", "KSonK",
        "HPH", "HPM", "HPA", "SPP", "Exec", "ExecH2L", "Genmo", "MoH",
        "GWA", "Ador", "King of Hittites", "Fanbearer",
    ]:
        assert expected in all_codes, f"expected Ramesside code {expected!r} never extracted"


def test_kings_cross_referenced_in_bold_caps_not_extracted_as_entries() -> None:
    """BOLD CAPITALS king-names inside other rows' prose are cross-references,
    not Brief Lives entries of their own. The corresponding princes
    appear under their letter-suffixed `dh_id` (e.g. `Amenhirkopshef C`
    whose prose says "later king as RAMESSES VI" — the Brief Lives
    entry carries the prince name, not the regnal cross-reference).
    """
    king_refs = {
        "AMENHOTEP II", "AMENHOTEP III", "THUTMOSE IV",
        "RAMESSES I", "RAMESSES II", "RAMESSES III", "RAMESSES IV",
        "RAMESSES V", "RAMESSES VI", "RAMESSES VII", "RAMESSES VIII",
        "RAMESSES IX", "RAMESSES X", "RAMESSES XI",
        "SETY I", "SETY II", "MERENPTAH", "AMENMESSE", "SIPTAH",
        "SETNAKHTE", "TAWOSRET", "AKHENATEN", "TUTANKHAMUN",
    }
    for r in _rows():
        assert r["dh_id"] not in king_refs, r


# ---------------------------------------------------------------------------
# Full-row fixture assertions (per rule 5)
# ---------------------------------------------------------------------------


def test_ahmes_b_full_row() -> None:
    """Wife of Thutmose I / mother of Hatshepsut — KM, KGW, KSis."""
    _assert_full_row("Ahmes B", {
        "dh_id": "Ahmes B",
        "name": "Ahmes B",
        "alt_names": [],
        "roles": ["KM", "KGW", "KSis"],
        "sex": "female",
        "spouse_names": ["Thutmose I"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Hatshepsut"],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_POWER,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose I; known from a range of monuments, principally "
            "those of her daughter, Hatshepsut, but also from other material, "
            "including a statue of her mortuary priest, Nakht, from Karnak."
        ),
        "source_citation": CITATION_POWER,
    })


def test_hatshepsut_d_full_row() -> None:
    """D&H's Hatshepsut-as-queen-and-later-king carries five role codes."""
    _assert_full_row("Hatshepsut D", {
        "dh_id": "Hatshepsut D",
        "name": "Hatshepsut D",
        "alt_names": [],
        "roles": ["GW", "KGW", "KD", "KSis", "UWC"],
        "sex": "female",
        "spouse_names": ["Thutmose II"],
        "father_name": "Thutmose I",
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_POWER,
        "unplaced": False,
        "notes": (
            "Daughter of Thutmose I, wife of Thutmose II and later king. A "
            "range of monuments date to her period as queen, and also as "
            "regent for Thutmose III. These include inscriptions from Karnak, "
            "Nubia and Sinai, and an (unused) tomb and sarcophagus in the "
            "Wadi Siqqat Taqa el-Zeide at Thebes."
        ),
        "source_citation": CITATION_POWER,
    })


def test_iset_a_full_row() -> None:
    """Mother of Thutmose III. Note: Iset A and Iset B are distinct; see test below."""
    _assert_full_row("Iset A", {
        "dh_id": "Iset A",
        "name": "Iset A",
        "alt_names": [],
        "roles": ["GW", "KM", "KW", "KGW"],
        "sex": "female",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Thutmose III"],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_POWER,
        "unplaced": False,
        "notes": (
            "Mother of Thutmose III; she was given the title of KGW during "
            "his reign, as well as GW after her death. Possessor of a statue "
            "from Karnak, and mentioned a number of times on her son's "
            "funerary monuments and equipment."
        ),
        "source_citation": CITATION_POWER,
    })


def test_iset_b_full_row() -> None:
    """Daughter of Thutmose III + Meryetre-Hatshepsut — distinct from Iset A."""
    _assert_full_row("Iset B", {
        "dh_id": "Iset B",
        "name": "Iset B",
        "alt_names": [],
        "roles": ["KD"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Thutmose III",
        "mother_name": "Meryetre-Hatshepsut",
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_POWER,
        "unplaced": False,
        "notes": (
            "Daughter of Thutmose III and Meryetre-Hatshepsut. Represented on "
            "the statue of her grandmother, Huy, in the British Museum."
        ),
        "source_citation": CITATION_POWER,
    })


def test_mutemwia_full_row() -> None:
    """Wife of Thutmose IV, mother of Amenhotep III — flagship Power-and-Glory queen."""
    _assert_full_row("Mutemwia", {
        "dh_id": "Mutemwia",
        "name": "Mutemwia",
        "alt_names": [],
        "roles": ["KGW", "KM"],
        "sex": "female",
        "spouse_names": ["Thutmose IV"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Amenhotep III"],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_POWER,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose IV and mother of Amenhotep III; shown in the "
            "'divine birth' scenes of her son in Luxor temple. A statue of her "
            "probably came from his mortuary temple, with a figure of her in "
            "a boat found adjacent to the granite sanctuary of the Karnak "
            "temple (British Museum); she is also represented with her son on "
            "the Colossi of Memnon and in the tomb of Heqareshu (TT226, now "
            "in the Luxor Museum)."
        ),
        "source_citation": CITATION_POWER,
    })


def test_mutneferet_a_full_row() -> None:
    """Wife of Thutmose I / mother of Thutmose II. Hedged father_name
    ("probable daughter of Ahmose I") preserved verbatim.
    """
    _assert_full_row("Mutneferet A", {
        "dh_id": "Mutneferet A",
        "name": "Mutneferet A",
        "alt_names": [],
        "roles": ["KM", "KW", "KSis", "KD"],
        "sex": "female",
        "spouse_names": ["Thutmose I"],
        "father_name": "Ahmose I (probable)",
        "mother_name": None,
        "children_names": ["Thutmose II"],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_POWER,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose I, mother of Thutmose II and probable daughter "
            "of Ahmose I. Represented by the leg of her son on a colossus in "
            "front of the south face of the Eighth Pylon, in the temple of "
            "Thutmose III at Deir el-Bahari and on a stela found near the "
            "Ramesseum. She was also the owner of a statue found in the "
            "chapel of Wadjmose."
        ),
        "source_citation": CITATION_POWER,
    })


def test_tiaa_a_full_row_with_egyptologist_override_applied() -> None:
    """Tiaa A's `notes` was corrected by fix_rows.py to restore the article
    "a" in "including a number of usurpations" (Gemini OCR had dropped it
    and left a stray colon). This test locks in the corrected verbatim-
    prose and would break if fix_rows.py stopped running.
    """
    _assert_full_row("Tiaa A", {
        "dh_id": "Tiaa A",
        "name": "Tiaa A",
        "alt_names": [],
        "roles": ["KGW", "KM", "GW"],
        "sex": "female",
        "spouse_names": ["Amenhotep II"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Thutmose IV"],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_POWER,
        "unplaced": False,
        "notes": (
            "Wife of Amenhotep II and mother of Thutmose IV. A number of "
            "monuments were created for her by the latter at Giza, Thebes and "
            "the Fayoum, including a number of usurpations of material "
            "belonging to Meryetre-Hatshepsut. She was buried in tomb KV32, "
            "where many fragments of her funerary equipment have been found; "
            "some material was washed by floodwater into the adjacent tomb "
            "KV47, where it was for a long time thought to belong to a "
            "like-named mother of Siptah."
        ),
        "source_citation": CITATION_POWER,
    })


def test_menhet_full_row() -> None:
    """One of the three Syrian wives of Thutmose III buried together."""
    _assert_full_row("Menhet", {
        "dh_id": "Menhet",
        "name": "Menhet",
        "alt_names": [],
        "roles": ["KW"],
        "sex": "female",
        "spouse_names": ["Thutmose III"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_POWER,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose III, probably of Syrian extraction. Buried in "
            "a tomb in Wadi Gabbanet el-Qurud together with Menwi and Merti; "
            "much of the funerary equipment is now in the Metropolitan "
            "Museum of Art."
        ),
        "source_citation": CITATION_POWER,
    })


def test_menwi_full_row() -> None:
    _assert_full_row("Menwi", {
        "dh_id": "Menwi",
        "name": "Menwi",
        "alt_names": [],
        "roles": ["KW"],
        "sex": "female",
        "spouse_names": ["Thutmose III"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_POWER,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose III, probably of Syrian extraction. Buried with "
            "Menhet and Merti."
        ),
        "source_citation": CITATION_POWER,
    })


def test_merti_full_row() -> None:
    _assert_full_row("Merti", {
        "dh_id": "Merti",
        "name": "Merti",
        "alt_names": [],
        "roles": ["KW"],
        "sex": "female",
        "spouse_names": ["Thutmose III"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_POWER,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose III, probably of Syrian extraction. Buried with "
            "Menhet and Menwi."
        ),
        "source_citation": CITATION_POWER,
    })


def test_pyihia_full_row() -> None:
    """Regular placed KD reburied during the 21st Dynasty — tests that the
    repeated reburial-prose stencil doesn't collapse to `unplaced: true`.
    (Pyihia is a placed daughter of Thutmose IV; Wiay A et al. are unplaced.)
    """
    _assert_full_row("Pyihia", {
        "dh_id": "Pyihia",
        "name": "Pyihia",
        "alt_names": [],
        "roles": ["KD"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Thutmose IV",
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_POWER,
        "unplaced": False,
        "notes": (
            "Daughter of Thutmose IV. One of the group of princesses reburied "
            "during the 21st Dynasty on Sheikh Abd el-Qurna."
        ),
        "source_citation": CITATION_POWER,
    })


def test_lacuna_name_full_row() -> None:
    """`[...]pentepkau` — the square-bracketed lacuna in the name must
    survive transcription + extraction + sort order (it now sits in the
    trailing unplaced bin, not at the very end of the whole file).
    """
    _assert_full_row("[...]pentepkau", {
        "dh_id": "[...]pentepkau",
        "name": "[...]pentepkau",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_POWER,
        "unplaced": True,
        "notes": (
            "Unplaced, probably mid-18th Dynasty. Known only from a fragment "
            "of sphinx-stela from near the Second Pyramid of Giza."
        ),
        "source_citation": CITATION_POWER,
    })


def test_siamun_b_full_row() -> None:
    """KSon placed by D&H — tests the male-inference branch + father-from-prose
    extraction (`Son of Thutmose III` → father_name).
    """
    _assert_full_row("Siamun B", {
        "dh_id": "Siamun B",
        "name": "Siamun B",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Thutmose III",
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_POWER,
        "unplaced": False,
        "notes": (
            "Son of Thutmose III. Named upon the statuette of the Chancellor, "
            "Sennefer, in the Cairo Museum."
        ),
        "source_citation": CITATION_POWER,
    })


# ---------------------------------------------------------------------------
# Full-row fixture assertions — The Amarna Interlude chunk (41 rows)
# (per rule 5: every populated field asserted for every row)
# ---------------------------------------------------------------------------


def test_amarna_18a_h_full_row() -> None:
    _assert_full_row('[...]18A–H', {
        "dh_id": '[...]18A–H',
        "name": '[...]18A–H',
        "alt_names": [],
        "roles": [],
        "sex": 'female',
        "spouse_names": [],
        "father_name": 'Amenhotep III',
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Daughters of Amenhotep III, shown in the tomb of Kheruef (TT192; see '
            'p. 30); some may be identical with named daughters.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_18j_full_row() -> None:
    _assert_full_row('[...]18J', {
        "dh_id": '[...]18J',
        "name": '[...]18J',
        "alt_names": [],
        "roles": [],
        "sex": 'male',
        "spouse_names": [],
        "father_name": 'Anen',
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": 'Son of Anen; depicted with his siblings in tomb TT120.',
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_18k_n_full_row() -> None:
    _assert_full_row('[...]18K–N', {
        "dh_id": '[...]18K–N',
        "name": '[...]18K–N',
        "alt_names": [],
        "roles": [],
        "sex": 'female',
        "spouse_names": [],
        "father_name": 'Anen',
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": 'Daughters of Anen; depicted with their siblings in tomb TT120.',
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_amenhotep_e_full_row() -> None:
    _assert_full_row('Amenhotep E', {
        "dh_id": 'Amenhotep E',
        "name": 'Amenhotep E',
        "alt_names": ['Amenhotep IV', 'Akhenaten'],
        "roles": ['KSon'],
        "sex": 'male',
        "spouse_names": [],
        "father_name": 'Amenhotep III',
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Son of Amenhotep III; his estate is mentioned on a wine-jar seal from '
            'Malqata, and he later became king as AMENHOTEP IV/AKHENATEN.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_amenia_full_row() -> None:
    _assert_full_row('Amenia', {
        "dh_id": 'Amenia',
        "name": 'Amenia',
        "alt_names": [],
        "roles": ['ChA'],
        "sex": 'female',
        "spouse_names": ['Horemheb'],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Wife of Horemheb; named on a column in his Saqqara tomb, and possibly '
            'buried in the upper suite in shaft IV, perhaps dated to the reign of '
            'Ay.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_anen_full_row() -> None:
    _assert_full_row('Anen', {
        "dh_id": 'Anen',
        "name": 'Anen',
        "alt_names": [],
        "roles": ['2PA'],
        "sex": 'male',
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Brother of Tiye A; left office some time during the final decade of '
            "Amenhotep III's reign when he was replaced by Simut, previously "
            'Fourth Prophet. Owner of tomb TT120 on Sheikh Abd el-Qurna, where his '
            'figure has been mutilated, a shabti in The Hague and a statue in '
            'Turin.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_ankhesenpaaten_full_row() -> None:
    _assert_full_row('Ankhesenpaaten', {
        "dh_id": 'Ankhesenpaaten',
        "name": 'Ankhesenpaaten',
        "alt_names": ['Ankhesenamun'],
        "roles": ['KDB', 'KGW', 'L2L'],
        "sex": 'female',
        "spouse_names": ['Tutankhamun', 'Ay (perhaps, brief marriage)'],
        "father_name": 'Akhenaten',
        "mother_name": 'Nefertiti',
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Third daughter of Akhenaten and Nefertiti and wife of Tutankhamun, '
            'later known as Ankhesenamun. Known as a princess from numerous '
            'depictions from Amarna and others at Karnak; as queen, she is '
            "depicted or mentioned on various items from her husband's tomb, in "
            "his 'resthouse' at Giza, scenes in the colonnade of the temple of "
            'Luxor, on a lintel in Berlin and a number of faience items. Amongst '
            'these last items is a ring in Berlin that joins her cartouche with '
            'that of King Ay, perhaps indicating a brief marriage.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_ankhesenpaaten_tasherit_full_row() -> None:
    _assert_full_row('Ankhesenpaaten-tasherit', {
        "dh_id": 'Ankhesenpaaten-tasherit',
        "name": 'Ankhesenpaaten-tasherit',
        "alt_names": [],
        "roles": [],
        "sex": 'female',
        "spouse_names": [],
        "father_name": 'Akhenaten (or Smenkhkare)',
        "mother_name": 'Kiya (or Meryetaten)',
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Perhaps a daughter of Akhenaten and Kiya, or Smenkhkare and '
            'Meryetaten; named on blocks from Hermopolis, originally deriving from '
            'Amarna.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_ay_a_full_row() -> None:
    _assert_full_row('Ay A', {
        "dh_id": 'Ay A',
        "name": 'Ay A',
        "alt_names": [],
        "roles": ['GF', 'MoH', 'Viz?'],
        "sex": 'male',
        "spouse_names": [],
        "father_name": 'Yuya (perhaps)',
        "mother_name": None,
        "children_names": ['Nefertiti (possibly)'],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Possibly father of Nefertiti and perhaps son of Yuya; owner of tomb '
            'TA25 at Amarna and later king. He may have become Vizier under '
            'Tutankhamun, if a fragment of gold leaf from KV58 refers to him.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_ay_b_full_row() -> None:
    _assert_full_row('Ay B', {
        "dh_id": 'Ay B',
        "name": 'Ay B',
        "alt_names": [],
        "roles": ['2PA', '1PMut', 'Steward of Queen Tiye A/Tey'],
        "sex": 'male',
        "spouse_names": [],
        "father_name": 'Nakhtmin A',
        "mother_name": 'Mutemnub',
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Probably a nephew of Ay; depicted by a block statue in the Brooklyn '
            'Museum, probably from Dahamsha.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_beketaten_full_row() -> None:
    _assert_full_row('Beketaten', {
        "dh_id": 'Beketaten',
        "name": 'Beketaten',
        "alt_names": [],
        "roles": ['KDB'],
        "sex": 'female',
        "spouse_names": [],
        "father_name": 'Amenhotep III',
        "mother_name": 'Tiye A',
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Youngest daughter of Amenhotep III and Tiye A; depicted with her '
            'mother (and once near her father) in the tomb of Huya at Amarna '
            '(TA1). A statue of the princess is shown being painted in another '
            'scene in the tomb.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_gilukhipa_full_row() -> None:
    _assert_full_row('Gilukhipa', {
        "dh_id": 'Gilukhipa',
        "name": 'Gilukhipa',
        "alt_names": [],
        "roles": [],
        "sex": 'female',
        "spouse_names": ['Amenhotep III'],
        "father_name": 'Shuttarna II',
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Wife of Amenhotep III and daughter of Shuttarna II of Mitanni. A '
            'series of scarabs record that she arrived in Egypt with a retinue of '
            "317 women in year 10 of her husband's reign."
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_henuttaneb_a_full_row() -> None:
    _assert_full_row('Henuttaneb A', {
        "dh_id": 'Henuttaneb A',
        "name": 'Henuttaneb A',
        "alt_names": [],
        "roles": ['KD'],
        "sex": 'female',
        "spouse_names": [],
        "father_name": 'Amenhotep III',
        "mother_name": 'Tiye A',
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Daughter of Amenhotep III and Tiye A; shown with her parents and '
            'sister, Iset C, in the temple at Soleb, on a carnelian plaque '
            '(Metropolitan Museum of Art) and on a colossus from Medinet Habu '
            '(Cairo). Mentioned on a stela from Malqata and owner of faience '
            'fragments, two once in private collections and one from Gurob.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_horemheb_full_row() -> None:
    _assert_full_row('Horemheb', {
        "dh_id": 'Horemheb',
        "name": 'Horemheb',
        "alt_names": ['Paatenemheb'],
        "roles": ['Exec', 'Gen'],
        "sex": 'male',
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Army officer who may have been designated heir to Ay, and later king. '
            'Possibly began his career as Paatenemheb (Amarna tomb TA24), but '
            'certainly originally from the Herakleopolitan area. Acted as Deputy '
            'under Tutankhamun, when he also led military expeditions and built a '
            'tomb at Saqqara.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_iset_c_full_row() -> None:
    _assert_full_row('Iset C', {
        "dh_id": 'Iset C',
        "name": 'Iset C',
        "alt_names": [],
        "roles": ['KD', 'KW'],
        "sex": 'female',
        "spouse_names": ['Amenhotep III'],
        "father_name": 'Amenhotep III',
        "mother_name": 'Tiye A',
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            "Daughter of Amenhotep III and Tiye A; shown as her father's wife on a "
            'statue in the G. Ortiz Collection, and as a simple princess at Soleb '
            'and on a carnelian plaque (Metropolitan Museum of Art). Also probably '
            'hers are a box from Gurob and a pair of kohl-tubes, all now in Cairo.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_kiya_full_row() -> None:
    _assert_full_row('Kiya', {
        "dh_id": 'Kiya',
        "name": 'Kiya',
        "alt_names": ['Tadukhipa (conceivably)'],
        "roles": ['GBW'],
        "sex": 'female',
        "spouse_names": ['Akhenaten'],
        "father_name": 'Tushratta (conceivably)',
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Wife of Akhenaten, and conceivably the former Tadukhipa – the '
            'daughter of Tushratta, king of Mitanni. Kiya is named and depicted on '
            'various blocks originating at Amarna, on vases in London and New '
            'York, four fragmentary kohl-tubes in Berlin and London, and a '
            'wine-jar docket. She may also be depicted by three uninscribed '
            "sculptor's studies. Her coffin and canopic jars were taken over for "
            'the burial of a king (probably Smenkhkare), which was ultimately '
            'discovered in tomb KV55 in the Valley of the Kings. Almost all of '
            "Kiya's monuments were usurped for daughters of Akhenaten, making it "
            'fairly certain that she was disgraced some time after year 11, '
            'although one researcher has suggested that she actually became king '
            'as Smenkhkare.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_meketaten_full_row() -> None:
    _assert_full_row('Meketaten', {
        "dh_id": 'Meketaten',
        "name": 'Meketaten',
        "alt_names": [],
        "roles": ['KDB'],
        "sex": 'female',
        "spouse_names": [],
        "father_name": 'Akhenaten',
        "mother_name": 'Nefertiti',
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Second daughter of Akhenaten and Nefertiti; known from a large number '
            'of reliefs from or at Amarna and Karnak, and a writing palette in New '
            'York. Her death (interpreted by some as in childbirth) and mourning '
            "are shown in chamber 'gamma' of the Royal Tomb at Amarna."
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_meryetaten_full_row() -> None:
    _assert_full_row('Meryetaten', {
        "dh_id": 'Meryetaten',
        "name": 'Meryetaten',
        "alt_names": ['Neferneferuaten'],
        "roles": ['KDB', 'KGW'],
        "sex": 'female',
        "spouse_names": ['Smenkhkare'],
        "father_name": 'Akhenaten',
        "mother_name": 'Nefertiti',
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Eldest daughter of Akhenaten and Nefertiti; wife of Smenkhkare. Known '
            'as a princess from a large number of reliefs from or at Amarna and '
            'Karnak, together with others usurped from Kiya, and a writing pallet '
            "found in Tutankhamun's tomb (KV62). As a queen, she is shown with her "
            'husband in tomb TA2 at Amarna (belonging to a nobleman called Meryre '
            'ii), and named alongside Smenkhkare on a block from Memphis (lost) '
            'and a box from tomb KV62. She seems to have become female king '
            "NEFERNEFERUATEN towards the end of her father's reign."
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_meryetaten_tasherit_full_row() -> None:
    _assert_full_row('Meryetaten-tasherit', {
        "dh_id": 'Meryetaten-tasherit',
        "name": 'Meryetaten-tasherit',
        "alt_names": [],
        "roles": [],
        "sex": 'female',
        "spouse_names": [],
        "father_name": 'Akhenaten (or Smenkhkare)',
        "mother_name": 'Kiya (or Meryetaten)',
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Perhaps a daughter of Akhenaten and Kiya, or Smenkhkare and '
            'Meryetaten; named on blocks from Hermopolis, originally from Amarna.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_mutemnub_full_row() -> None:
    _assert_full_row('Mutemnub', {
        "dh_id": 'Mutemnub',
        "name": 'Mutemnub',
        "alt_names": [],
        "roles": [],
        "sex": 'female',
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": ['Ay B'],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": 'Mother of Ay B, and probably sister of Tey; named on the statue of her son.',
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_mutnodjmet_a_full_row() -> None:
    _assert_full_row('Mutnodjmet A', {
        "dh_id": 'Mutnodjmet A',
        "name": 'Mutnodjmet A',
        "alt_names": [],
        "roles": ['Sister of KGW'],
        "sex": 'female',
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            "Sister of Nefertiti; depicted adjacent to Nefertiti's daughters, and "
            'attended by two dwarfs in the tombs of Ay, Panehsy, Parennefer, Tutu, '
            'and May at Amarna (tombs TA25, 6, 7, 8 and 14); perhaps identical '
            'with Mutnodjmet Q.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_mutnodjmet_q_full_row() -> None:
    _assert_full_row('Mutnodjmet Q', {
        "dh_id": 'Mutnodjmet Q',
        "name": 'Mutnodjmet Q',
        "alt_names": [],
        "roles": ['KGW', 'MULE', 'L2L'],
        "sex": 'female',
        "spouse_names": ['Horemheb'],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Wife of Horemheb, and possibly identical with Mutnodjmet A. She '
            'appears with her husband on the Coronation Statue in Turin, in the '
            'tomb of Roy (TT255), and was the usurper of a number of inscriptions '
            'of Ankhesenamun at Luxor temple. A statue and other items of hers '
            'were found in the substructure of the tomb of Horemheb at Saqqara, '
            'suggesting that she may have been buried there. Human remains found '
            'near the lower burial chamber of shaft IV may thus be hers, '
            'accompanied by the bones of a foetus or newborn child. If so, '
            'Mutnodjmet may have been in her mid-40s at death, having lost all her '
            'teeth early in life; this burial may be dated soon after year 13 by a '
            'wine-jar docket found in the burial chamber. A canopic jar of the '
            'queen is in the British Museum.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_nakhtmin_a_full_row() -> None:
    _assert_full_row('Nakhtmin A', {
        "dh_id": 'Nakhtmin A',
        "name": 'Nakhtmin A',
        "alt_names": [],
        "roles": [],
        "sex": 'male',
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": ['Ay B'],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": 'Father of Ay B; named on the statue of his son.',
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_nakhtmin_b_full_row() -> None:
    _assert_full_row('Nakhtmin B', {
        "dh_id": 'Nakhtmin B',
        "name": 'Nakhtmin B',
        "alt_names": [],
        "roles": ['Genmo', 'KSon', 'Exec'],
        "sex": 'male',
        "spouse_names": [],
        "father_name": 'Ay (probable)',
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Probable son of Ay; represented on one, and possibly another, statue '
            'in Cairo. He donated five shabtis to the burial of Tutankhamun.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_nebetiah_full_row() -> None:
    _assert_full_row('Nebetiah', {
        "dh_id": 'Nebetiah',
        "name": 'Nebetiah',
        "alt_names": [],
        "roles": ['KD'],
        "sex": 'female',
        "spouse_names": [],
        "father_name": 'Amenhotep III',
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": 'Daughter of Amenhotep III, shown on a colossal statue from Medinet Habu (Cairo).',
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_neferneferuaten_tasherit_full_row() -> None:
    _assert_full_row('Neferneferuaten-tasherit', {
        "dh_id": 'Neferneferuaten-tasherit',
        "name": 'Neferneferuaten-tasherit',
        "alt_names": [],
        "roles": ['KDB'],
        "sex": 'female',
        "spouse_names": [],
        "father_name": 'Akhenaten',
        "mother_name": 'Nefertiti',
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Fourth daughter of Akhenaten and Nefertiti; known from reliefs from '
            'or at Amarna. She may be the now-anonymous person buried in chamber '
            "'alpha' in the royal tomb."
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_neferneferure_full_row() -> None:
    _assert_full_row('Neferneferure', {
        "dh_id": 'Neferneferure',
        "name": 'Neferneferure',
        "alt_names": [],
        "roles": ['KDB'],
        "sex": 'female',
        "spouse_names": [],
        "father_name": 'Akhenaten',
        "mother_name": 'Nefertiti',
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Fifth daughter of Akhenaten and Nefertiti; known from a large number '
            'of reliefs from or at Amarna, a seal-impression from the Royal Wadi '
            'there, and a box-lid from the tomb of Tutankhamun. It is possible '
            "that she may be the now-anonymous person buried in chamber 'alpha' in "
            'the royal tomb.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_nefertiti_full_row() -> None:
    _assert_full_row('Nefertiti', {
        "dh_id": 'Nefertiti',
        "name": 'Nefertiti',
        "alt_names": ['Neferneferuaten-Nefertiti'],
        "roles": ['KGW', 'L2L'],
        "sex": 'female',
        "spouse_names": ['Akhenaten'],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Wife of Akhenaten; known from year 5 onwards as '
            'Neferneferuaten-Nefertiti. Represented in many reliefs from or at '
            'Amarna and Karnak alongside her husband and daughters, and by large '
            'numbers of statues and statuettes, including the famous bust in '
            'Berlin. She appears to have married her husband soon after he came to '
            'the throne and is constantly at his side until around year 13, when '
            'she disappears from view. It has been suggested that she then became '
            'king as first Neferneferuaten, and later as Smenkhkare, but it seems '
            'more likely that she had died. There is no evidence to substantiate '
            'the assertion that her disappearance was the result of disgrace – the '
            'alleged data in fact refers to Kiya (see p. 148). Shabti-fragments of '
            'Nefertiti are in the Louvre and Brooklyn. Attempts to identify '
            "Nefertiti's mummy as one of two bodies in KV35 (Amenhotep II's tomb) "
            'are not based on any compelling evidence.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_setpenre_a_full_row() -> None:
    _assert_full_row('Setpenre A', {
        "dh_id": 'Setpenre A',
        "name": 'Setpenre A',
        "alt_names": [],
        "roles": [],
        "sex": 'female',
        "spouse_names": [],
        "father_name": 'Akhenaten',
        "mother_name": 'Nefertiti',
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Sixth daughter of Akhenaten and Nefertiti; known from a number of '
            'reliefs from or at Amarna. It is possible that she may be the '
            "now-anonymous person buried in chamber 'alpha' in the royal tomb."
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_shuttarna_ii_full_row() -> None:
    _assert_full_row('Shuttarna II', {
        "dh_id": 'Shuttarna II',
        "name": 'Shuttarna II',
        "alt_names": [],
        "roles": ['King of Mitanni'],
        "sex": 'male',
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": ['Gilukhipa'],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": 'Father-in-law of Amenhotep III.',
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_sitamun_b_full_row() -> None:
    _assert_full_row('Sitamun B', {
        "dh_id": 'Sitamun B',
        "name": 'Sitamun B',
        "alt_names": [],
        "roles": ['KGD', 'KW', 'KGW'],
        "sex": 'female',
        "spouse_names": ['Amenhotep III'],
        "father_name": 'Amenhotep III (probable)',
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Wife and probable daughter of Amenhotep III; shown as a princess from '
            'Abydos and on a chair from the tomb of Yuya and Tjuiu (all now in '
            'Cairo). The pedestal of a statue of the senior nobleman '
            "Amenhotep-son-of-Hapu, from Karnak (Cairo), names her as a King's "
            'Wife, showing that she attained the rank before the former died '
            'between years 30 and 34. She is named as Great Wife on a kohl-tube '
            'and a disc now in Oxford.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_tadukhipa_full_row() -> None:
    _assert_full_row('Tadukhipa', {
        "dh_id": 'Tadukhipa',
        "name": 'Tadukhipa',
        "alt_names": [],
        "roles": [],
        "sex": 'female',
        "spouse_names": ['Amenhotep III', 'Akhenaten'],
        "father_name": 'Tushratta',
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Wife of Amenhotep III and later of Akhenaten; daughter of Tushratta, '
            'king of Mitanni, whose arrival is mentioned in Amarna Letter 17. It '
            'is possible that she was the same person as Kiya.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_tey_full_row() -> None:
    _assert_full_row('Tey', {
        "dh_id": 'Tey',
        "name": 'Tey',
        "alt_names": [],
        "roles": ['KGW'],
        "sex": 'female',
        "spouse_names": ['Ay A'],
        "father_name": None,
        "mother_name": None,
        "children_names": ['Nakhtmin B (if she were his mother)'],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            "Wife of Ay A and 'nurse' (= stepmother?) of Nefertiti; shown with her "
            'husband in his tomb at Amarna and later became his queen. As such, '
            'she is depicted with Ay in his royal tomb in the Valley of the Kings '
            '(WV23) and in the rock-chapel of Min at Akhmim. If she were the '
            'mother of Nakhtmin B, she will also have held the title of Adorer of '
            'Min.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_thutmose_b_full_row() -> None:
    _assert_full_row('Thutmose B', {
        "dh_id": 'Thutmose B',
        "name": 'Thutmose B',
        "alt_names": [],
        "roles": ['EKSon', 'HPM', 'SPP', 'OPULE'],
        "sex": 'male',
        "spouse_names": [],
        "father_name": 'Amenhotep III',
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Eldest son of Amenhotep III, and conceivably identical with Thutmose '
            'Q (p. 141); known in particular from material from the burial of Apis '
            'I at the Serapeum at Saqqara, carried out while he was our only '
            'Sem-Priest at Memphis. A small figure of the prince as a miller is in '
            'the Louvre, while a recumbent mummiform figure is in Berlin; the '
            'coffin of a cat, dedicated by him, is in Cairo. The prince seems to '
            "have died some time during the third decade of his father's reign."
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_tiye_a_full_row() -> None:
    _assert_full_row('Tiye A', {
        "dh_id": 'Tiye A',
        "name": 'Tiye A',
        "alt_names": [],
        "roles": ['KGW', 'MULE', 'M2L', 'L2L', 'KM'],
        "sex": 'female',
        "spouse_names": ['Amenhotep III'],
        "father_name": 'Yuya',
        "mother_name": 'Tjuiu',
        "children_names": ['Akhenaten'],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Wife of Amenhotep III, her union with whom was commemorated by the '
            'series of marriage scarabs; mother of Akhenaten. Known from a wide '
            'variety of sources, including temple reliefs at Soleb and Sedeinga. '
            'Sculptures of her together with her husband include a colossus from '
            'Medinet Habu and the Colossi of Memnon. Individual heads from '
            'particularly fine statuettes of Tiye are in Cairo (from Sinai) and '
            'Berlin (Gurob), with small objects in various collections. Tiye is '
            'also depicted in the tombs of Userhat (TT47), Kheruef (TT192) and '
            'Huya (TA1), the last suggesting that she may have resided at Amarna '
            "later in her son's reign. Shabtis of hers were found in Amenhotep "
            "III's tomb, but a broken sarcophagus made for her was found in the "
            'Royal Tomb at Amarna, and a gilded funerary shrine (showing her with '
            'Akhenaten) ultimately found its way to tomb KV55 in the Valley of the '
            "Kings. A lock of Tiye's hair was found in a nest of miniature coffins "
            'in the tomb of Tutankhamun; it seems very unlikely that her mummy '
            "could be the so-called 'Elder Lady' in the tomb of Amenhotep II."
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_tjuiu_full_row() -> None:
    _assert_full_row('Tjuiu', {
        "dh_id": 'Tjuiu',
        "name": 'Tjuiu',
        "alt_names": [],
        "roles": ['KM of KGW'],
        "sex": 'female',
        "spouse_names": ['Yuya'],
        "father_name": None,
        "mother_name": None,
        "children_names": ['Tiye A'],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Mother of Tiye A; buried with her husband in Valley of the Kings tomb '
            'KV46; her mummy and funerary equipment now in the Cairo Museum.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_tushratta_full_row() -> None:
    _assert_full_row('Tushratta', {
        "dh_id": 'Tushratta',
        "name": 'Tushratta',
        "alt_names": [],
        "roles": ['King of Mitanni'],
        "sex": 'male',
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": ['Tadukhipa'],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": 'Possible father-in-law of Akhenaten.',
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_tutankhuaten_full_row() -> None:
    _assert_full_row('Tutankhuaten', {
        "dh_id": 'Tutankhuaten',
        "name": 'Tutankhuaten',
        "alt_names": ['Tutankhaten', 'Tutankhamun'],
        "roles": ['KSonN'],
        "sex": 'male',
        "spouse_names": [],
        "father_name": 'Akhenaten (probable)',
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Probable son of Akhenaten, later king as TUTANKHATEN/AMUN. Named on a '
            "block from Hermopolis, and possibly shown as a baby in his nurse's "
            "arms in chambers 'alpha' and 'gamma' in the royal tomb at Amarna."
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_yuya_full_row() -> None:
    _assert_full_row('Yuya', {
        "dh_id": 'Yuya',
        "name": 'Yuya',
        "alt_names": [],
        "roles": ['GF', 'MoH'],
        "sex": 'male',
        "spouse_names": ['Tjuiu'],
        "father_name": None,
        "mother_name": None,
        "children_names": ['Tiye A'],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Father of Tiye A; buried with his wife in tomb KV46; his mummy and '
            'funerary equipment now in the Cairo Museum.'
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_18p_full_row() -> None:
    _assert_full_row('–18P', {
        "dh_id": '–18P',
        "name": '–18P',
        "alt_names": [],
        "roles": [],
        "sex": 'female',
        "spouse_names": [],
        "father_name": 'Tutankhamun',
        "mother_name": 'Ankhesenamun',
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Unnamed, still-born daughter of Tutankhamun and Ankhesenamun, found '
            "in her father's tomb and now in Cairo."
        ),
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_18q_full_row() -> None:
    _assert_full_row('–18Q', {
        "dh_id": '–18Q',
        "name": '–18Q',
        "alt_names": [],
        "roles": [],
        "sex": 'female',
        "spouse_names": [],
        "father_name": 'Tutankhamun',
        "mother_name": 'Ankhesenamun',
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
        "notes": (
            'Unnamed, still-born daughter of Tutankhamun and Ankhesenamun, found '
            "in her father's tomb and now in Cairo."
        ),
        "source_citation": CITATION_AMARNA,
    })


# ---------------------------------------------------------------------------
# Ramesside fixtures — chunk 3 (House of Ramesses / Feud / Decline)
#
# Generated via /tmp/claude/gen_ramesside_fixtures.py on 2026-04-16 after the
# merge + fix_rows pass (11 overrides: 9 from chunks 1-2 + 2 Ramesside review
# corrections on Khaemwaset C and Iset D Ta-Hemdjert children_names). The
# generator reads reconciled.jsonl, sorts by (sub_period, unplaced, dh_id),
# and emits _assert_full_row calls. Cross-section-duplicate rows
# (Takhat A, Isetneferet C, Ramesses C) pass sub_period= to disambiguate.
# ---------------------------------------------------------------------------

def test_p_rehirwenemef_a_house_full_row() -> None:
    _assert_full_row("(P)rehirwenemef A", {
        "dh_id": "(P)rehirwenemef A",
        "name": "(P)rehirwenemef A",
        "alt_names": [],
        "roles": ["KSonB", "MoH"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": "Nefertiry D",
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and Nefertiry D, and number 3 in the processions of sons. Also depicted at Abu Simbel and in the triumph that followed the Battle of Qadesh.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_meryastarte_house_full_row() -> None:
    _assert_full_row("(Ramesses-)Meryastarte", {
        "dh_id": "(Ramesses-)Meryastarte",
        "name": "(Ramesses-)Meryastarte",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 26 in the Abydos procession of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_merymaat_house_full_row() -> None:
    _assert_full_row("(Ramesses-)Merymaat", {
        "dh_id": "(Ramesses-)Merymaat",
        "name": "(Ramesses-)Merymaat",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 25 in the Abydos procession of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_siptah_a_house_full_row() -> None:
    _assert_full_row("(Ramesses-)Siptah A", {
        "dh_id": "(Ramesses-)Siptah A",
        "name": "(Ramesses-)Siptah A",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": "Sutererey (probable)",
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and probably Sutererey, and number 26 in the processions of sons. A Book of the Dead probably belonging to him is in the Florence Museum, while a relief of the prince and his mother is in the Louvre.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_userkhepesh_house_full_row() -> None:
    _assert_full_row("(Ramesses-)Userkhepesh", {
        "dh_id": "(Ramesses-)Userkhepesh",
        "name": "(Ramesses-)Userkhepesh",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 22 in the Abydos procession of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_pre_house_full_row() -> None:
    _assert_full_row("(Ramesses-...)pre", {
        "dh_id": "(Ramesses-...)pre",
        "name": "(Ramesses-...)pre",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 20 in the Abydos procession of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_19a_house_full_row() -> None:
    _assert_full_row("[...]19A", {
        "dh_id": "[...]19A",
        "name": "[...]19A",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": None,
        "mother_name": "Bintanath",
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Bintanath; depicted with her mother in tomb QV71.",
        "source_citation": CITATION_HOUSE,
    })

def test_19b_house_full_row() -> None:
    _assert_full_row("[...]19B", {
        "dh_id": "[...]19B",
        "name": "[...]19B",
        "alt_names": [],
        "roles": [],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Tjia",
        "mother_name": "Tia C",
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Tjia and Tia C; depicted in her parents' tomb at Saqqara.",
        "source_citation": CITATION_HOUSE,
    })

def test_jheb_house_full_row() -> None:
    _assert_full_row("[...]Jheb", {
        "dh_id": "[...]Jheb",
        "name": "[...]Jheb",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 13 in the Luxor procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_khesbed_house_full_row() -> None:
    _assert_full_row("[...]khesbed", {
        "dh_id": "[...]khesbed",
        "name": "[...]khesbed",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 16 in the second Abydos procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_taweret_house_full_row() -> None:
    _assert_full_row("[...]taweret", {
        "dh_id": "[...]taweret",
        "name": "[...]taweret",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 3 on the Louvre ostrakon list.",
        "source_citation": CITATION_HOUSE,
    })

def test_mut_metennefer_house_full_row() -> None:
    _assert_full_row("[Mut]metennefer", {
        "dh_id": "[Mut]metennefer",
        "name": "[Mut]metennefer",
        "alt_names": [],
        "roles": [],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Tjia",
        "mother_name": "Tia C",
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Tjia and Tia C; depicted in their tomb at Saqqara.",
        "source_citation": CITATION_HOUSE,
    })

def test_r_uia_house_full_row() -> None:
    _assert_full_row("[R]uia", {
        "dh_id": "[R]uia",
        "name": "[R]uia",
        "alt_names": [],
        "roles": [],
        "sex": "female",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Mother-in-law of Sety I. Known from a block at Medinet Habu.",
        "source_citation": CITATION_HOUSE,
    })

def test_set_emnakhte_house_full_row() -> None:
    _assert_full_row("[Set]emnakhte", {
        "dh_id": "[Set]emnakhte",
        "name": "[Set]emnakhte",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; depicted on a block from the Ramesseum, reused at Medinet Habu, and on a doorway from Qantir (Cairo).",
        "source_citation": CITATION_HOUSE,
    })

def test_amenemopet_c_house_full_row() -> None:
    _assert_full_row("Amenemopet C", {
        "dh_id": "Amenemopet C",
        "name": "Amenemopet C",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 19 in the processions of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_amenemwia_setemwia_house_full_row() -> None:
    _assert_full_row("Amenemwia/Setemwia", {
        "dh_id": "Amenemwia/Setemwia",
        "name": "Amenemwia/Setemwia",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 8 in the processions of sons; changed his name – perhaps at the same time as Amen/Sethirkopshef A. Present at the siege of the Syrian city of Dapur in year 10.",
        "source_citation": CITATION_HOUSE,
    })

def test_amenhirwenemef_amenhirkopshef_a_house_full_row() -> None:
    _assert_full_row("Amenhirwenemef/Amenhirkopshef A", {
        "dh_id": "Amenhirwenemef/Amenhirkopshef A",
        "name": "Amenhirwenemef/Amenhirkopshef A",
        "alt_names": ["Sethirkopshef A"],
        "roles": ["1KSonB", "EKSonB", "Genmo"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": "Nefertiry D",
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Eldest Son of Ramesses II and Nefertiry D, and number 1 in the processions of sons; changed his name early in the reign. First heir to the throne, he took part in his father's early campaigns, appearing on the wall of the temple of Beit el-Wali along with Khaemwaset C, and in the triumph that followed the Battle of Qadesh. Depicted with his father lassoing a bull in the Sety I temple at Abydos, and frequently on Ramesses II's statues, but seems to have changed his name once again around year 20 to Sethirkopshef (A). Involved in the exchange of correspondence following the Hittite peace treaty in year 21, but died around year 25. Buried in tomb KV5 in the Valley of the Kings, his interment being apparently inspected in year 53 of his father's reign.",
        "source_citation": CITATION_HOUSE,
    })

def test_amenhotep_f_house_full_row() -> None:
    _assert_full_row("Amenhotep F", {
        "dh_id": "Amenhotep F",
        "name": "Amenhotep F",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 14 in the processions of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_amenwahsu_house_full_row() -> None:
    _assert_full_row("Amenwahsu", {
        "dh_id": "Amenwahsu",
        "name": "Amenwahsu",
        "alt_names": [],
        "roles": [],
        "sex": "male",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Tjia"],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Father of Tjia; shown with him, Ramesses II, and Sety B on a block in Chicago.",
        "source_citation": CITATION_HOUSE,
    })

def test_astarthirwenemef_house_full_row() -> None:
    _assert_full_row("Astarthirwenemef", {
        "dh_id": "Astarthirwenemef",
        "name": "Astarthirwenemef",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; depicted on a block from the Ramesseum, reused at Medinet Habu.",
        "source_citation": CITATION_HOUSE,
    })

def test_bakmut_house_full_row() -> None:
    _assert_full_row("Bakmut", {
        "dh_id": "Bakmut",
        "name": "Bakmut",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 2 in the processions of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_benanath_house_full_row() -> None:
    _assert_full_row("Benanath", {
        "dh_id": "Benanath",
        "name": "Benanath",
        "alt_names": [],
        "roles": [],
        "sex": "male",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Iryet"],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Syrian ship's captain and father-in-law of Simentu.",
        "source_citation": CITATION_HOUSE,
    })

def test_bintanath_house_full_row() -> None:
    _assert_full_row("Bintanath", {
        "dh_id": "Bintanath",
        "name": "Bintanath",
        "alt_names": [],
        "roles": ["KDB", "KGW", "L2L", "MULE"],
        "sex": "female",
        "spouse_names": ["Ramesses II"],
        "father_name": "Ramesses II",
        "mother_name": "Isetneferet A",
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Eldest daughter of Ramesses II and Isetneferet A. Served as one of her father's Great Wives following her mother's death and was represented on a number of monuments throughout Ramesses II's reign. Survived into the reign of her brother, Merenptah, when she was depicted on a statue usurped by him, and buried in tomb QV71 in the Valley of the Queens.",
        "source_citation": CITATION_HOUSE,
    })

def test_geregtawi_house_full_row() -> None:
    _assert_full_row("Geregtawi", {
        "dh_id": "Geregtawi",
        "name": "Geregtawi",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; depicted on a block from the Ramesseum, reused at Medinet Habu.",
        "source_citation": CITATION_HOUSE,
    })

def test_hattusilis_iii_house_full_row() -> None:
    _assert_full_row("Hattusilis III", {
        "dh_id": "Hattusilis III",
        "name": "Hattusilis III",
        "alt_names": [],
        "roles": ["King of Hittites"],
        "sex": "male",
        "spouse_names": ["Pudukhepa"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Maathorneferure"],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Father-in-law of Ramesses II.",
        "source_citation": CITATION_HOUSE,
    })

def test_henttawy_a_house_full_row() -> None:
    _assert_full_row("Henttawy A", {
        "dh_id": "Henttawy A",
        "name": "Henttawy A",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 7 in the processions of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_henut_house_full_row() -> None:
    _assert_full_row("Henut[...]", {
        "dh_id": "Henut[...]",
        "name": "Henut[...]",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 20 in the Abydos procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_henutmire_house_full_row() -> None:
    _assert_full_row("Henutmire", {
        "dh_id": "Henutmire",
        "name": "Henutmire",
        "alt_names": [],
        "roles": ["KD", "KGW"],
        "sex": "female",
        "spouse_names": ["Ramesses II"],
        "father_name": "Sety I (probable)",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Wife of Ramesses II and probably daughter of Sety I. Depicted on a statue of Tuy A in the Vatican and statues of Ramesses II from Abukir and Hermopolis. Buried in tomb QV75 in the Valley of the Queens; the trough of her coffin was later usurped by Harsiese A for his interment at Medinet Habu.",
        "source_citation": CITATION_HOUSE,
    })

def test_henutpahuro_house_full_row() -> None:
    _assert_full_row("Henutpahuro[...]", {
        "dh_id": "Henutpahuro[...]",
        "name": "Henutpahuro[...]",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 26 in the Abydos procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_henutpre_house_full_row() -> None:
    _assert_full_row("Henutpre[...]", {
        "dh_id": "Henutpre[...]",
        "name": "Henutpre[...]",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 58 in the Wadi el-Sebua procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_henutsekhemu_house_full_row() -> None:
    _assert_full_row("Henutsekhemu", {
        "dh_id": "Henutsekhemu",
        "name": "Henutsekhemu",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 25 in the Abydos procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_henuttadesh_house_full_row() -> None:
    _assert_full_row("Henuttadesh", {
        "dh_id": "Henuttadesh",
        "name": "Henuttadesh",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 6 on the Louvre ostrakon list.",
        "source_citation": CITATION_HOUSE,
    })

def test_henuttamehu_b_house_full_row() -> None:
    _assert_full_row("Henuttamehu B", {
        "dh_id": "Henuttamehu B",
        "name": "Henuttamehu B",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 9 on the Louvre ostrakon list.",
        "source_citation": CITATION_HOUSE,
    })

def test_henuttaneb_b_house_full_row() -> None:
    _assert_full_row("Henuttaneb B", {
        "dh_id": "Henuttaneb B",
        "name": "Henuttaneb B",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 4 on the Louvre ostrakon list.",
        "source_citation": CITATION_HOUSE,
    })

def test_hetepuemamun_house_full_row() -> None:
    _assert_full_row("Hetepuemamun", {
        "dh_id": "Hetepuemamun",
        "name": "Hetepuemamun",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 7 on the Louvre ostrakon list.",
        "source_citation": CITATION_HOUSE,
    })

def test_horhirwenemef_house_full_row() -> None:
    _assert_full_row("Horhirwenemef", {
        "dh_id": "Horhirwenemef",
        "name": "Horhirwenemef",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; number 12 in the processions of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_hori_a_house_full_row() -> None:
    _assert_full_row("Hori A", {
        "dh_id": "Hori A",
        "name": "Hori A",
        "alt_names": [],
        "roles": ["HPM"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Khaemwaset C",
        "mother_name": None,
        "children_names": ["Hori B"],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Probably a grandson of Ramesses II and son of Khaemwaset C. Depicted on a pillar from his tomb at Saqqara (Cairo Museum), and a stela from Memphis. His probable sarcophagus and canopic jars are in Berlin and the British Museum/Liège respectively.",
        "source_citation": CITATION_HOUSE,
    })

def test_hori_b_house_full_row() -> None:
    _assert_full_row("Hori B", {
        "dh_id": "Hori B",
        "name": "Hori B",
        "alt_names": [],
        "roles": ["Viz"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Hori A",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Hori A, shown with him on a stela from Memphis. First northern, and then southern, Vizier.",
        "source_citation": CITATION_HOUSE,
    })

def test_iryet_house_full_row() -> None:
    _assert_full_row("Iryet", {
        "dh_id": "Iryet",
        "name": "Iryet",
        "alt_names": [],
        "roles": [],
        "sex": "female",
        "spouse_names": ["Simentu"],
        "father_name": "Benanath",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Wife of Simentu and daughter of Benanath, a Syrian ship's captain. Possibly died in year 42 of Ramesses II's reign.",
        "source_citation": CITATION_HOUSE,
    })

def test_isetneferet_a_house_full_row() -> None:
    _assert_full_row("Isetneferet A", {
        "dh_id": "Isetneferet A",
        "name": "Isetneferet A",
        "alt_names": [],
        "roles": ["KGW", "L2L"],
        "sex": "female",
        "spouse_names": ["Ramesses II"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Merenptah", "Khaemwaset C"],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Wife of Ramesses II and mother of Merenptah. Seen on a number of mounuments, and appears to have died around year 34. Her tomb has not been identified, but work on it (and that of Meryatum A) is recorded on an ostrakon that may imply her burial in the area of the Valley of the Queens. Otherwise, she is commemorated alongside her son, Khaemwaset C, on a number of his monuments, as well as others at Saqqara.",
        "source_citation": CITATION_HOUSE,
    })

def test_isetneferet_b_house_full_row() -> None:
    _assert_full_row("Isetneferet B", {
        "dh_id": "Isetneferet B",
        "name": "Isetneferet B",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 6 in the processions of daughters. A letter from two palace singers to the princess enquiring after her health survives. It is possible that she may have been the wife of Merenptah, rather than Isetneferet C.",
        "source_citation": CITATION_HOUSE,
    })

def test_isetneferet_c_house_full_row() -> None:
    _assert_full_row("Isetneferet C", {
        "dh_id": "Isetneferet C",
        "name": "Isetneferet C",
        "alt_names": [],
        "roles": ["KGW"],
        "sex": "female",
        "spouse_names": ["Merenptah (possibly)"],
        "father_name": "Khaemwaset C",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Granddaughter of Ramesses II, daughter of Khaemwaset C and possibly wife of Merenptah (see next section).",
        "source_citation": CITATION_HOUSE,
    }, sub_period=SUB_PERIOD_HOUSE)

def test_itamun_a_house_full_row() -> None:
    _assert_full_row("Itamun A", {
        "dh_id": "Itamun A",
        "name": "Itamun A",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 15 in the processions of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_khaemwaset_b_house_full_row() -> None:
    _assert_full_row("Khaemwaset B", {
        "dh_id": "Khaemwaset B",
        "name": "Khaemwaset B",
        "alt_names": [],
        "roles": ["Fanbearer"],
        "sex": "male",
        "spouse_names": ["Taemwadjy"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Uncle of Ramesses I, mentioned on a stela of his brother, Sety A. He seems to have been the owner of a statue from Kawa, now in Khartoum.",
        "source_citation": CITATION_HOUSE,
    })

def test_khaemwaset_c_house_full_row() -> None:
    _assert_full_row("Khaemwaset C", {
        "dh_id": "Khaemwaset C",
        "name": "Khaemwaset C",
        "alt_names": [],
        "roles": ["KSonB", "SPP", "HPM", "ExecH2L"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": "Isetneferet A",
        "children_names": ["Hori A", "Isetneferet C", "Ramesses C"],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and Isetneferet A, and number 4 in the processions of sons. By far the best-known son of the king, remembered for centuries after his death, and the hero of a cycle of stories written in Late/Ptolemaic times. Crown Prince during the early 50s of his father's reign, but died soon after year 55 and probably buried at Saqqara, perhaps below his hilltop sanctuary between Abusir and Saqqara.124",
        "source_citation": CITATION_HOUSE,
    })

def test_maathorneferure_house_full_row() -> None:
    _assert_full_row("Maathorneferure", {
        "dh_id": "Maathorneferure",
        "name": "Maathorneferure",
        "alt_names": [],
        "roles": ["KGW"],
        "sex": "female",
        "spouse_names": ["Ramesses II"],
        "father_name": "Hattusilis III",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Hattusilis III of Hatti and wife of Ramesses II from year 34. The marriage is commemorated in a contemporary stela at Abu Simbel, but also remembered in the so-called Bentresh stela of Ptolemaic times. She is represented on a colossus of Ramesses II, but seems to have retired to Gurob later in the reign.",
        "source_citation": CITATION_HOUSE,
    })

def test_mahiranat_house_full_row() -> None:
    _assert_full_row("Mahiranat", {
        "dh_id": "Mahiranat",
        "name": "Mahiranat",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; depicted on a block from the Ramesseum, reused at Medinet Habu.",
        "source_citation": CITATION_HOUSE,
    })

def test_mentuemwaset_house_full_row() -> None:
    _assert_full_row("Mentuemwaset", {
        "dh_id": "Mentuemwaset",
        "name": "Mentuemwaset",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 24 in the processions of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_mentuenheqau_house_full_row() -> None:
    _assert_full_row("Mentuenheqau", {
        "dh_id": "Mentuenheqau",
        "name": "Mentuenheqau",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 28 in the processions of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_mentuhirkopshef_a_house_full_row() -> None:
    _assert_full_row("Mentuhirkopshef A", {
        "dh_id": "Mentuhirkopshef A",
        "name": "Mentuhirkopshef A",
        "alt_names": [],
        "roles": ["KSonB", "MoH"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 5 in the processions of sons. Owner of a statue from Bubastis, and depicted on a stela in Copenhagen. Present at the siege of the Syrian city of Dapur in year 10.",
        "source_citation": CITATION_HOUSE,
    })

def test_merenptah_a_house_full_row() -> None:
    _assert_full_row("Merenptah A", {
        "dh_id": "Merenptah A",
        "name": "Merenptah A",
        "alt_names": [],
        "roles": ["KSonB", "EKSonB", "ExecH2L", "Genmo"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": "Isetneferet A",
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and Isetneferet A, and number 13 in the processions of sons; heir to the throne and effective regent during the last ten years of Ramesses II's reign. Early in the reign he was explicitly called the 'younger brother' of Khaemwaset C, Bintanath and Ramesses B on a rock-carving at Aswan, and also appeared with them and their parents on a stela in the rock-temple at Gebel el-Silsila. During the fifth decade of his father's reign he obtained the title of Generalissimo, and finally an heir's titles after year 55. As such, he is known from monuments at Karnak, the Serapeum, Memphis, Tanis (ex-Piramesse) and Athribis. Other monuments, attributed to Merenptah B, may also be his. He later became king.",
        "source_citation": CITATION_HOUSE,
    })

def test_meryamun_a_house_full_row() -> None:
    _assert_full_row("Meryamun A", {
        "dh_id": "Meryamun A",
        "name": "Meryamun A",
        "alt_names": ["Ramesses-Meryamun"],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Also known as Ramesses-Meryamun. Son of Ramesses II and number 7 in the processions of sons. Present at the triumph that followed the Battle of Qadesh and at the siege of the Syrian city of Dapur in year 10, and buried in tomb KV5 in the Valley of the Kings, where remains of his canopic jars were found.",
        "source_citation": CITATION_HOUSE,
    })

def test_meryatum_a_house_full_row() -> None:
    _assert_full_row("Meryatum A", {
        "dh_id": "Meryatum A",
        "name": "Meryatum A",
        "alt_names": [],
        "roles": ["KSonB", "HPH"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": "Nefertiry D",
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and Nefertiry D, and number 16 in the processions of sons. Appears to have visited Sinai during the second decade of his father's reign, and been appointed Heliopolitan High Priest in the late 20s; two statues of him are in Berlin, plus a stela in Hildesheim. He served for around twenty years, work on his tomb (and that of Isetneferet A) being recorded on an ostrakon that may imply his burial in the area of the Valley of the Queens. On the other hand, a fragment of canopic jar found in tomb KV5 may be his.",
        "source_citation": CITATION_HOUSE,
    })

def test_meryetamun_e_house_full_row() -> None:
    _assert_full_row("Meryetamun E", {
        "dh_id": "Meryetamun E",
        "name": "Meryetamun E",
        "alt_names": [],
        "roles": ["KDB", "KGW", "L2L", "MULE"],
        "sex": "female",
        "spouse_names": ["Ramesses II"],
        "father_name": "Ramesses II",
        "mother_name": "Nefertiry D",
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II and Nefertiry D; number 4 in the processions of daughters. Served as one of her father's Great Wives following her mother's death and appears on a number of monuments; buried in tomb QV68 in the Valley of the Queens.",
        "source_citation": CITATION_HOUSE,
    })

def test_meryetkhet_house_full_row() -> None:
    _assert_full_row("Meryetkhet", {
        "dh_id": "Meryetkhet",
        "name": "Meryetkhet",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 13 in the Luxor procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_meryetmihapi_house_full_row() -> None:
    _assert_full_row("Meryetmihapi", {
        "dh_id": "Meryetmihapi",
        "name": "Meryetmihapi",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 22 in the Abydos procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_meryetnetjer_house_full_row() -> None:
    _assert_full_row("Meryetnetjer", {
        "dh_id": "Meryetnetjer",
        "name": "Meryetnetjer",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 32 in the Abydos procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_meryetptah_b_house_full_row() -> None:
    _assert_full_row("Meryetptah B", {
        "dh_id": "Meryetptah B",
        "name": "Meryetptah B",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 16 in the Luxor procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_meryetyotes_b_house_full_row() -> None:
    _assert_full_row("Meryetyotes B", {
        "dh_id": "Meryetyotes B",
        "name": "Meryetyotes B",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 23 in the Abydos procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_merymentu_house_full_row() -> None:
    _assert_full_row("Merymentu", {
        "dh_id": "Merymentu",
        "name": "Merymentu",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; depicted at Wadi el-Sebua and Abydos.",
        "source_citation": CITATION_HOUSE,
    })

def test_meryre_a_house_full_row() -> None:
    _assert_full_row("Meryre A", {
        "dh_id": "Meryre A",
        "name": "Meryre A",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": "Nefertiry D",
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and Nefertiry D; number 11 in the processions of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_meryre_b_house_full_row() -> None:
    _assert_full_row("Meryre B", {
        "dh_id": "Meryre B",
        "name": "Meryre B",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; number 18 in the processions of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_mut_tuy_b_house_full_row() -> None:
    _assert_full_row("Mut-Tuy B", {
        "dh_id": "Mut-Tuy B",
        "name": "Mut-Tuy B",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 15 in the Luxor procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_neben_house_full_row() -> None:
    _assert_full_row("Neben[...]", {
        "dh_id": "Neben[...]",
        "name": "Neben[...]",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; named on an ostrakon in the Cairo Museum.",
        "source_citation": CITATION_HOUSE,
    })

def test_nebenkharu_house_full_row() -> None:
    _assert_full_row("Nebenkharu", {
        "dh_id": "Nebenkharu",
        "name": "Nebenkharu",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; number 6 in the processions of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_nebet_h_a_house_full_row() -> None:
    _assert_full_row("Nebet[...]h[...]a", {
        "dh_id": "Nebet[...]h[...]a",
        "name": "Nebet[...]h[...]a",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 14 in the Luxor procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_nebetananash_house_full_row() -> None:
    _assert_full_row("Nebetananash", {
        "dh_id": "Nebetananash",
        "name": "Nebetananash",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 10 on the Louvre ostrakon list.",
        "source_citation": CITATION_HOUSE,
    })

def test_nebetimmunedjem_house_full_row() -> None:
    _assert_full_row("Nebetimmunedjem", {
        "dh_id": "Nebetimmunedjem",
        "name": "Nebetimmunedjem",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 8 on the Louvre ostrakon list.",
        "source_citation": CITATION_HOUSE,
    })

def test_nebetiunet_c_house_full_row() -> None:
    _assert_full_row("Nebetiunet C", {
        "dh_id": "Nebetiunet C",
        "name": "Nebetiunet C",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 11 in the Luxor procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_nebetnehat_b_house_full_row() -> None:
    _assert_full_row("Nebetnehat B", {
        "dh_id": "Nebetnehat B",
        "name": "Nebetnehat B",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 59 in the Wadi el-Sebua procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_nebettawy_a_house_full_row() -> None:
    _assert_full_row("Nebettawy A", {
        "dh_id": "Nebettawy A",
        "name": "Nebettawy A",
        "alt_names": [],
        "roles": ["KDB", "KGW", "L2L", "MULE"],
        "sex": "female",
        "spouse_names": ["Ramesses II"],
        "father_name": "Ramesses II",
        "mother_name": "Nefertiry D",
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II and Nefertiry D; number 5 in the processions of daughters. Served as one of her father's Great Wives and buried in tomb QV60 in the Valley of the Queens.",
        "source_citation": CITATION_HOUSE,
    })

def test_nebtaneb_house_full_row() -> None:
    _assert_full_row("Nebtaneb", {
        "dh_id": "Nebtaneb",
        "name": "Nebtaneb",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 17 in the processions of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_nedjemmut_a_house_full_row() -> None:
    _assert_full_row("Nedjemmut A", {
        "dh_id": "Nedjemmut A",
        "name": "Nedjemmut A",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 9 in the processions of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_nefertiry_d_meryetmut_house_full_row() -> None:
    _assert_full_row("Nefertiry D Meryetmut", {
        "dh_id": "Nefertiry D Meryetmut",
        "name": "Nefertiry D Meryetmut",
        "alt_names": [],
        "roles": ["KGW", "L2L", "MULE"],
        "sex": "female",
        "spouse_names": ["Ramesses II"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Wife of Ramesses II; perhaps a descendant of Ay. Numerous monuments known, including the small temple at Abu Simbel, and others from sites throughout Egypt. Corresponded with her Hittite counterpart, Pudukhepa, in year 21, and attended the inauguration of the Abu Simbel temples in year 24. Appears to have died soon afterwards and buried in tomb QV66 in the Valley of the Queens; her sarcophagus lid and various remains of her funerary equipment are in Turin, along with the knees from her mummy.",
        "source_citation": CITATION_HOUSE,
    })

def test_nefertiry_e_house_full_row() -> None:
    _assert_full_row("Nefertiry E", {
        "dh_id": "Nefertiry E",
        "name": "Nefertiry E",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 3 in the processions of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_nefertiry_f_house_full_row() -> None:
    _assert_full_row("Nefertiry F", {
        "dh_id": "Nefertiry F",
        "name": "Nefertiry F",
        "alt_names": [],
        "roles": [],
        "sex": "female",
        "spouse_names": ["Amenhirkopshef (Sethirkopshef A)"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Sety C"],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Wife of Amenhirkopshef (Sethirkopshef A) and mother of Sety C; mentioned on an ostrakon in the Louvre; conceivably identical with Nefertiry E.",
        "source_citation": CITATION_HOUSE,
    })

def test_neferure_b_house_full_row() -> None:
    _assert_full_row("Neferure B", {
        "dh_id": "Neferure B",
        "name": "Neferure B",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 31 in the Abydos procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_nubemiunu_house_full_row() -> None:
    _assert_full_row("Nubemiunu", {
        "dh_id": "Nubemiunu",
        "name": "Nubemiunu",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 24 in the Abydos procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_nubemweskhet_house_full_row() -> None:
    _assert_full_row("Nubemweskhet", {
        "dh_id": "Nubemweskhet",
        "name": "Nubemweskhet",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 15 on the Louvre ostrakon list.",
        "source_citation": CITATION_HOUSE,
    })

def test_nubhir_house_full_row() -> None:
    _assert_full_row("Nubhir[...]", {
        "dh_id": "Nubhir[...]",
        "name": "Nubhir[...]",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 18 in the Abydos procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_paramessu_house_full_row() -> None:
    _assert_full_row("Paramessu", {
        "dh_id": "Paramessu",
        "name": "Paramessu",
        "alt_names": ["Ramesses I"],
        "roles": ["Viz", "Exec"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Sety A",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Sety A and later king as RAMESSES I. Known from two statues from Karnak and his unused stone coffins from Medinet Habu and Gurob.",
        "source_citation": CITATION_HOUSE,
    })

def test_prerenpetnefer_house_full_row() -> None:
    _assert_full_row("Prerenpetnefer", {
        "dh_id": "Prerenpetnefer",
        "name": "Prerenpetnefer",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 12 in the Luxor procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_pudukhepa_house_full_row() -> None:
    _assert_full_row("Pudukhepa", {
        "dh_id": "Pudukhepa",
        "name": "Pudukhepa",
        "alt_names": [],
        "roles": [],
        "sex": "female",
        "spouse_names": ["Hattusilis III"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Wife of Hattusilis III; corresponded with Nefertiry D.",
        "source_citation": CITATION_HOUSE,
    })

def test_pypuy_house_full_row() -> None:
    _assert_full_row("Pypuy", {
        "dh_id": "Pypuy",
        "name": "Pypuy",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 10 in the processions of daughters. Perhaps the princess of the name, the daughter of a lady named Iwy, whose mummy was reburied with others during the 21st Dynasty on Sheikh Abd el-Qurna (see pp. 135–37).",
        "source_citation": CITATION_HOUSE,
    })

def test_raia_house_full_row() -> None:
    _assert_full_row("Raia", {
        "dh_id": "Raia",
        "name": "Raia",
        "alt_names": [],
        "roles": ["Adjutant of the Chariotry"],
        "sex": "male",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Father-in-law of Sety I. Known from a block at Medinet Habu.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_a_house_full_row() -> None:
    _assert_full_row("Ramesses A", {
        "dh_id": "Ramesses A",
        "name": "Ramesses A",
        "alt_names": ["Ramesses II"],
        "roles": ["EKSon", "Exec"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Sety I",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Eldest son of Sety I, and later king as RAMESSES II. Depicted with his father in the latter's Abydos temple.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_b_house_full_row() -> None:
    _assert_full_row("Ramesses B", {
        "dh_id": "Ramesses B",
        "name": "Ramesses B",
        "alt_names": [],
        "roles": ["KSonB", "EKSonB", "1Genmo"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": "Isetneferet A",
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and Isetneferet A, and number 2 in the processions of sons. Heir to the throne from around year 25 to year 50. Attested in various inscriptions and sculptures, including the triumph that followed the Battle of Qadesh. Buried in tomb KV5 in the Valley of the Kings.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_c_house_full_row() -> None:
    _assert_full_row("Ramesses C", {
        "dh_id": "Ramesses C",
        "name": "Ramesses C",
        "alt_names": [],
        "roles": ["KSon", "SPP"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Khaemwaset C",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Grandson of Ramesses II. Dedicator at Memphis of a statue of his father, Khaemwaset C, now in Vienna.",
        "source_citation": CITATION_HOUSE,
    }, sub_period=SUB_PERIOD_HOUSE)

def test_ramesses_maatptah_house_full_row() -> None:
    _assert_full_row("Ramesses-Maatptah", {
        "dh_id": "Ramesses-Maatptah",
        "name": "Ramesses-Maatptah",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Known only from a letter in which the palace servant Meryotef rebukes him for failing to respond to his communications.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_merenre_house_full_row() -> None:
    _assert_full_row("Ramesses-Merenre", {
        "dh_id": "Ramesses-Merenre",
        "name": "Ramesses-Merenre",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 21 in the processions of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_meretmirre_house_full_row() -> None:
    _assert_full_row("Ramesses-Meretmirre", {
        "dh_id": "Ramesses-Meretmirre",
        "name": "Ramesses-Meretmirre",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 48 in the Wadi el-Sebua procession of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_meryamun_nebweben_house_full_row() -> None:
    _assert_full_row("Ramesses-meryamun-Nebweben", {
        "dh_id": "Ramesses-meryamun-Nebweben",
        "name": "Ramesses-meryamun-Nebweben",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; does not appear in the surviving processions of sons, and therefore likely to have been one of the king's younger children. Known only from the addition of his name to two stone coffins of his grandfather, Ramesses I, made while the latter was still only Vizier. The outer one was used for the prince's interment in tomb W5 at Gurob: bones found alongside it were those of a man with a badly deformed spine. The inner coffin was found in a pit at Medinet Habu.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_meryset_house_full_row() -> None:
    _assert_full_row("Ramesses-Meryset", {
        "dh_id": "Ramesses-Meryset",
        "name": "Ramesses-Meryset",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; depicted on a block from the Ramesseum, reused at Medinet Habu; at Abydos (number 23 in the procession); on a door lintel from Qantir (Hildesheim); on a doorjamb in Cairo; and on a stela in Berlin.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_payotnetjer_house_full_row() -> None:
    _assert_full_row("Ramesses-Payotnetjer", {
        "dh_id": "Ramesses-Payotnetjer",
        "name": "Ramesses-Payotnetjer",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; named on an ostrakon in the Cairo Museum.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_siatum_house_full_row() -> None:
    _assert_full_row("Ramesses-Siatum", {
        "dh_id": "Ramesses-Siatum",
        "name": "Ramesses-Siatum",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 19 in the Abydos procession of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_sikhepri_house_full_row() -> None:
    _assert_full_row("Ramesses-Sikhepri", {
        "dh_id": "Ramesses-Sikhepri",
        "name": "Ramesses-Sikhepri",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 24 in the Abydos procession of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_ramesses_userpehty_house_full_row() -> None:
    _assert_full_row("Ramesses-Userpehty", {
        "dh_id": "Ramesses-Userpehty",
        "name": "Ramesses-Userpehty",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II (probable)",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Probably a son of Ramesses II, named on a plaque formerly in the Fraser Collection and on a column-base at Memphis.",
        "source_citation": CITATION_HOUSE,
    })

def test_renpetnefer_house_full_row() -> None:
    _assert_full_row("Renpetnefer", {
        "dh_id": "Renpetnefer",
        "name": "Renpetnefer",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 12 in the Luxor procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_senakhtenamen_house_full_row() -> None:
    _assert_full_row("Senakhtenamen", {
        "dh_id": "Senakhtenamen",
        "name": "Senakhtenamen",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 20 in the processions of sons. A faience votive plaque showing Ptah and Sekhmet, dedicated by one Amenmose who was employed in the prince's household, suggests that the latter may have been resident at Memphis.",
        "source_citation": CITATION_HOUSE,
    })

def test_seshnesuen_house_full_row() -> None:
    _assert_full_row("Seshnesuen[...]", {
        "dh_id": "Seshnesuen[...]",
        "name": "Seshnesuen[...]",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; named on an ostrakon in the Cairo Museum.",
        "source_citation": CITATION_HOUSE,
    })

def test_setem_hir_house_full_row() -> None:
    _assert_full_row("Setem[hir...]", {
        "dh_id": "Setem[hir...]",
        "name": "Setem[hir...]",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; named on an ostrakon in the Cairo Museum.",
        "source_citation": CITATION_HOUSE,
    })

def test_setpenre_b_house_full_row() -> None:
    _assert_full_row("Setpenre B", {
        "dh_id": "Setpenre B",
        "name": "Setpenre B",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; and number 10 in the processions of sons. Present at the siege of the Syrian city of Dapur in year 10.",
        "source_citation": CITATION_HOUSE,
    })

def test_sety_a_house_full_row() -> None:
    _assert_full_row("Sety A", {
        "dh_id": "Sety A",
        "name": "Sety A",
        "alt_names": [],
        "roles": ["Troop Commander"],
        "sex": "male",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Ramesses I"],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Father of Ramesses I. Named on the latter's statues as Vizier, a stela of Sety is in the Oriental Institute, Chicago. He may have been a royal envoy in Palestine during the Amarna Period.",
        "source_citation": CITATION_HOUSE,
    })

def test_sety_b_house_full_row() -> None:
    _assert_full_row("Sety B", {
        "dh_id": "Sety B",
        "name": "Sety B",
        "alt_names": ["Sutiy"],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Name spelled Sutiy in his funerary equipment. Son of Ramesses II; number 9 in the processions of sons. Present at the triumph that followed the Battle of Qadesh, and the siege of the Syrian city of Dapur in year 10. Buried in tomb KV5 in the Valley of the Kings, where two of his canopic jars were found; his interment was apparently inspected in year 53 of his father's reign.",
        "source_citation": CITATION_HOUSE,
    })

def test_sety_c_house_full_row() -> None:
    _assert_full_row("Sety C", {
        "dh_id": "Sety C",
        "name": "Sety C",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Amenhirkopshef (Sethirkopshef) A",
        "mother_name": "Nefertiry F",
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Amenhirkopshef (Sethirkopshef) A and Nefertiry F; mentioned on an ostrakon in the Louvre.",
        "source_citation": CITATION_HOUSE,
    })

def test_sety_d_house_full_row() -> None:
    _assert_full_row("Sety D", {
        "dh_id": "Sety D",
        "name": "Sety D",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; named on an ostrakon in the Cairo Museum and conceivably identical with Sety B.",
        "source_citation": CITATION_HOUSE,
    })

def test_shepsemiunu_house_full_row() -> None:
    _assert_full_row("Shepsemiunu", {
        "dh_id": "Shepsemiunu",
        "name": "Shepsemiunu",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; depicted on a block from the Ramesseum, reused at Medinet Habu.",
        "source_citation": CITATION_HOUSE,
    })

def test_siamun_c_house_full_row() -> None:
    _assert_full_row("Siamun C", {
        "dh_id": "Siamun C",
        "name": "Siamun C",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 25 in the processions of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_simentu_house_full_row() -> None:
    _assert_full_row("Simentu", {
        "dh_id": "Simentu",
        "name": "Simentu",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": ["Iryet"],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II and number 23 in the processions of sons; husband of Iryet.",
        "source_citation": CITATION_HOUSE,
    })

def test_sitamun_c_house_full_row() -> None:
    _assert_full_row("Sitamun C", {
        "dh_id": "Sitamun C",
        "name": "Sitamun C",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 11 on the Louvre ostrakon list.",
        "source_citation": CITATION_HOUSE,
    })

def test_sitre_a_house_full_row() -> None:
    _assert_full_row("Sitre A", {
        "dh_id": "Sitre A",
        "name": "Sitre A",
        "alt_names": ["Tia Q"],
        "roles": ["GW", "KGW", "L2L", "GM", "KM", "MULE"],
        "sex": "female",
        "spouse_names": ["Ramesses I"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Sety I"],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Wife of Ramesses I and mother of Sety I. Her statue is depicted in the Abydos temple of her son, while her tomb is number QV38 in the Valley of the Queens. She may previously have borne the name Tia (Q).",
        "source_citation": CITATION_HOUSE,
    })

def test_sutererey_house_full_row() -> None:
    _assert_full_row("Sutererey", {
        "dh_id": "Sutererey",
        "name": "Sutererey",
        "alt_names": [],
        "roles": ["KW"],
        "sex": "female",
        "spouse_names": ["Ramesses II (probable)"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["(Ramesses-)Siptah A"],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Mother of a Prince Ramesses-Siptah and probably a wife of Ramesses II. Shown with her son on a relief in the Louvre.",
        "source_citation": CITATION_HOUSE,
    })

def test_syhiryotes_house_full_row() -> None:
    _assert_full_row("Syhiryotes", {
        "dh_id": "Syhiryotes",
        "name": "Syhiryotes",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 19 in the Abydos procession of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_taemwadjy_house_full_row() -> None:
    _assert_full_row("Taemwadjy", {
        "dh_id": "Taemwadjy",
        "name": "Taemwadjy",
        "alt_names": [],
        "roles": [],
        "sex": "female",
        "spouse_names": ["Khaemwaset B"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Aunt of Ramesses I. Shown on a statue with her husband, Khaemwaset B.",
        "source_citation": CITATION_HOUSE,
    })

def test_takhat_a_house_full_row() -> None:
    _assert_full_row("Takhat A", {
        "dh_id": "Takhat A",
        "name": "Takhat A",
        "alt_names": [],
        "roles": ["KDB", "KGW", "KM"],
        "sex": "female",
        "spouse_names": ["Sety II (probable)"],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 14 on the Louvre ostrakon list. Probable wife of Sety II (see next section).",
        "source_citation": CITATION_HOUSE,
    }, sub_period=SUB_PERIOD_HOUSE)

def test_thutmose_c_house_full_row() -> None:
    _assert_full_row("Thutmose C", {
        "dh_id": "Thutmose C",
        "name": "Thutmose C",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; number 22 in the processions of sons.",
        "source_citation": CITATION_HOUSE,
    })

def test_tia_c_house_full_row() -> None:
    _assert_full_row("Tia C", {
        "dh_id": "Tia C",
        "name": "Tia C",
        "alt_names": [],
        "roles": ["KSis"],
        "sex": "female",
        "spouse_names": ["Tjia"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Sister of Ramesses II. Buried with her husband, Tjia, in a tomb at Saqqara, and shown alongside him and her mother on a block in Toronto.",
        "source_citation": CITATION_HOUSE,
    })

def test_tia_q_house_full_row() -> None:
    _assert_full_row("Tia Q", {
        "dh_id": "Tia Q",
        "name": "Tia Q",
        "alt_names": [],
        "roles": ["Songstress of Pre"],
        "sex": "female",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Vizier Sety"],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Stated to be the mother of Vizier Sety on the Year 400 stela from Tanis; if Vizier Sety is to be equated with King Sety I, Tia may be identical with Sitre.",
        "source_citation": CITATION_HOUSE,
    })

def test_tia_sitre_house_full_row() -> None:
    _assert_full_row("Tia-Sitre", {
        "dh_id": "Tia-Sitre",
        "name": "Tia-Sitre",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 12 on the Louvre ostrakon list.",
        "source_citation": CITATION_HOUSE,
    })

def test_tjia_house_full_row() -> None:
    _assert_full_row("Tjia", {
        "dh_id": "Tjia",
        "name": "Tjia",
        "alt_names": [],
        "roles": ["Overseer of Treasurers"],
        "sex": "male",
        "spouse_names": ["Tia C"],
        "father_name": "Amenwahsu",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Brother-in-law of Ramesses II. Shown along with his mother-in-law and wife on a block in Toronto. Buried with his wife in a tomb at Saqqara.",
        "source_citation": CITATION_HOUSE,
    })

def test_tuia_house_full_row() -> None:
    _assert_full_row("Tuia", {
        "dh_id": "Tuia",
        "name": "Tuia",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 5 on the Louvre ostrakon list.",
        "source_citation": CITATION_HOUSE,
    })

def test_tuia_nebettawy_house_full_row() -> None:
    _assert_full_row("Tuia-Nebettawy", {
        "dh_id": "Tuia-Nebettawy",
        "name": "Tuia-Nebettawy",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 13 on the Louvre ostrakon list.",
        "source_citation": CITATION_HOUSE,
    })

def test_tuy_a_house_full_row() -> None:
    _assert_full_row("Tuy A", {
        "dh_id": "Tuy A",
        "name": "Tuy A",
        "alt_names": ["Mut-Tuy"],
        "roles": ["KW", "KM", "GW"],
        "sex": "female",
        "spouse_names": ["Sety I"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Ramesses II"],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Name also found with the longer form Mut-Tuy. Wife of Sety I and mother of Ramesses II; named on many of her son's monuments and represented amongst the colossi at Abu Simbel, and on a broken statue at Tanis. A number of blocks involving her, including a divine birth scene, were reused at Medinet Habu in Ptolemaic times. Buried in tomb QV80 in the Valley of the Queens.",
        "source_citation": CITATION_HOUSE,
    })

def test_werenro_house_full_row() -> None:
    _assert_full_row("Werenro", {
        "dh_id": "Werenro",
        "name": "Werenro",
        "alt_names": [],
        "roles": ["KDB"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Daughter of Ramesses II; number 8 in the processions of daughters.",
        "source_citation": CITATION_HOUSE,
    })

def test_wermaa_house_full_row() -> None:
    _assert_full_row("Wermaa[...]", {
        "dh_id": "Wermaa[...]",
        "name": "Wermaa[...]",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
        "notes": "Son of Ramesses II; named on an ostrakon in the Cairo Museum.",
        "source_citation": CITATION_HOUSE,
    })

def test_19c_feud_full_row() -> None:
    _assert_full_row("[...]19C", {
        "dh_id": "[...]19C",
        "name": "[...]19C",
        "alt_names": [],
        "roles": ["KGW"],
        "sex": "female",
        "spouse_names": ["Amenmesse"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_FEUD,
        "unplaced": False,
        "notes": "Wife of Amenmesse; represented on a statue of the king at Karnak.",
        "source_citation": CITATION_FEUD,
    })

def test_isetneferet_c_feud_full_row() -> None:
    _assert_full_row("Isetneferet C", {
        "dh_id": "Isetneferet C",
        "name": "Isetneferet C",
        "alt_names": [],
        "roles": ["KGW"],
        "sex": "female",
        "spouse_names": ["Merenptah"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_FEUD,
        "unplaced": False,
        "notes": "Wife of Merenptah. Depicted on a statue usurped for her husband from Amenhotep III in his chapel at Gebel el-Silsila, on the stelae of the Vizier Panehsy at the same site, and on a statuette dedicated by Panehsy.",
        "source_citation": CITATION_FEUD,
    }, sub_period=SUB_PERIOD_FEUD)

def test_isetneferet_d_feud_full_row() -> None:
    _assert_full_row("Isetneferet D", {
        "dh_id": "Isetneferet D",
        "name": "Isetneferet D",
        "alt_names": [],
        "roles": ["KD"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Merenptah (probable)",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_FEUD,
        "unplaced": False,
        "notes": "Probably a daughter of Merenptah, named in a ship's log in Leiden.",
        "source_citation": CITATION_FEUD,
    })

def test_khaemwaset_d_feud_full_row() -> None:
    _assert_full_row("Khaemwaset D", {
        "dh_id": "Khaemwaset D",
        "name": "Khaemwaset D",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Merenptah",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_FEUD,
        "unplaced": False,
        "notes": "Son of Merenptah. Depicted in his father's war reliefs in the Cour de Cachette in the Karnak temple.",
        "source_citation": CITATION_FEUD,
    })

def test_merenptah_b_feud_full_row() -> None:
    _assert_full_row("Merenptah B", {
        "dh_id": "Merenptah B",
        "name": "Merenptah B",
        "alt_names": [],
        "roles": ["KSon", "ExecH2L", "Genmo"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Merenptah (probable)",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_FEUD,
        "unplaced": False,
        "notes": "Probable son of Merenptah. Known from reliefs on two statues of Senwosret I (usurped by Merenptah and found at Alexandria and Tanis) and on three statue fragments from Bubastis. Assumed a uraeus at some point in his career.",
        "source_citation": CITATION_FEUD,
    })

def test_messuy_feud_full_row() -> None:
    _assert_full_row("Messuy", {
        "dh_id": "Messuy",
        "name": "Messuy",
        "alt_names": ["Amenmesse"],
        "roles": ["KSonK"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Sety II (probable)",
        "mother_name": "Takhat A (probable)",
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_FEUD,
        "unplaced": False,
        "notes": "Probably identical with King AMENMESSE, and thus probably a son of Sety II and Takhat A. Served as Viceroy during much of Merenptah's reign, but was succeeded by Khaemtjitry (who was promoted to Vizier under Amenmesse) prior to Merenptah's death. Commemorated by a number of kneeling figures and inscriptions in the Nubian temples at Amada, Aksha and Beit el-Wali, plus shabti figures from Wadi el-Sebua and Aniba, as well as a doorjamb inscribed by one of his subordinates at Aniba. In Egypt proper, an Aswan/Philae road inscription shows the chariot-borne Merenptah, while Messuy's name appears on the island of Bigeh, near Aswan. It was doubtless the power-base provided by his viceregal background and his close relationship with the current Viceroy, Khaemtjitry, which allowed Messuy/Amenmesse's bid for power to be backed by the resources of Nubia, and explain how he managed to maintain his position for nearly four years.",
        "source_citation": CITATION_FEUD,
    })

def test_sety_merenptah_a_feud_full_row() -> None:
    _assert_full_row("Sety-Merenptah A", {
        "dh_id": "Sety-Merenptah A",
        "name": "Sety-Merenptah A",
        "alt_names": ["Sety II"],
        "roles": ["KSonB", "ExecH2L", "Genmo"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Merenptah",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_FEUD,
        "unplaced": False,
        "notes": "Son of Merenptah; depicted on the side of the rear pillar of six of his father's statues, and on two stelae of the Vizier Panehsy at Gebel el-Silsila. Also shown in battle scenes where, given Merenptah's advanced age, he may have been in actual charge. Later king as SETY II.",
        "source_citation": CITATION_FEUD,
    })

def test_sety_merenptah_b_feud_full_row() -> None:
    _assert_full_row("Sety-Merenptah B", {
        "dh_id": "Sety-Merenptah B",
        "name": "Sety-Merenptah B",
        "alt_names": [],
        "roles": ["EKSon", "Exec"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Sety II",
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_FEUD,
        "unplaced": False,
        "notes": "Son of Sety II; depicted behind his father in the small temple of the latter at Karnak, possibly replacing a figure of the Chancellor Bay. It has recently been suggested that he was actually a baby, born in the last year of his father's reign, who died in year 4 of Siptah; this, however, remains doubtful.",
        "source_citation": CITATION_FEUD,
    })

def test_takhat_a_feud_full_row() -> None:
    _assert_full_row("Takhat A", {
        "dh_id": "Takhat A",
        "name": "Takhat A",
        "alt_names": [],
        "roles": ["KGW", "KD", "KM"],
        "sex": "female",
        "spouse_names": ["Sety II"],
        "father_name": "Ramesses II (probable)",
        "mother_name": None,
        "children_names": ["Amenmesse"],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_FEUD,
        "unplaced": False,
        "notes": "Wife of Sety II, mother of Amenmesse, and probable daughter of Ramesses II. Depicted on a number of statues of her husband and son. Probably buried in the former tomb of Amenmesse (KV10), with a sarcophagus lid that once belonged to an otherwise-unknown King's Daughter and King's Wife, Anuketemheb. The tomb was subsequently usurped for Takhat B and Baketwernel A (pp. 191, 192, 194).",
        "source_citation": CITATION_FEUD,
    }, sub_period=SUB_PERIOD_FEUD)

def test_tawosret_feud_full_row() -> None:
    _assert_full_row("Tawosret", {
        "dh_id": "Tawosret",
        "name": "Tawosret",
        "alt_names": [],
        "roles": ["KGW", "L2L", "MULE", "GW"],
        "sex": "female",
        "spouse_names": ["Sety II"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_FEUD,
        "unplaced": False,
        "notes": "Wife of Sety II, regent for Siptah and later king. Jointly provided jewellery with Sety II to a burial in tomb KV56 in the Valley of the Kings; depicted during the regency with the Chancellor Bay in the temple of Amada, and also on various small items. Assumed full pharaonic titles around the time of Siptah's death and ruled for two years — continuing Siptah's regnal numbering sequence — until apparently overthrown by Setnakhte. Owner of tomb KV14 in the Valley of the Kings, apparently begun in the second regnal year of Sety II, enlarged during the regency, and then once again extended during Tawosret's reign; the tomb was later usurped for Setnakhte. Nothing is known about the fate of the queen's body,132 although her original sarcophagus was later reused for the burial of Amenhirkopshef D in tomb KV13 under Ramesses VI.",
        "source_citation": CITATION_FEUD,
    })

def test_dua_tentopet_decline_full_row() -> None:
    _assert_full_row("(Dua)tentopet", {
        "dh_id": "(Dua)tentopet",
        "name": "(Dua)tentopet",
        "alt_names": [],
        "roles": ["Ador", "KD", "KW", "KM"],
        "sex": "female",
        "spouse_names": ["Ramesses IV"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Wife of Ramesses IV, buried in Valley of the Queens tomb QV74. Appears as Adoratrix, probably under Ramesses III, in the temple of Khonsu at Karnak. Her steward, Amunhotep, was the owner of tomb TT346.",
        "source_citation": CITATION_DECLINE,
    })

def test_amenhirkhopshef_b_decline_full_row() -> None:
    _assert_full_row("Amenhirkhopshef B", {
        "dh_id": "Amenhirkhopshef B",
        "name": "Amenhirkhopshef B",
        "alt_names": ["Ramesses-Amenhirkhopshef"],
        "roles": ["EKSon", "ExecH2L"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses III",
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Name also found as Ramesses-Amenhirkhopshef. Son of Ramesses III. Depicted in the Medinet Habu procession and owner of tomb QV55 in the Valley of the Queens; died young as heir presumptive.136",
        "source_citation": CITATION_DECLINE,
    })

def test_amenhirkopshef_c_decline_full_row() -> None:
    _assert_full_row("Amenhirkopshef C", {
        "dh_id": "Amenhirkopshef C",
        "name": "Amenhirkopshef C",
        "alt_names": ["Ramesses VI"],
        "roles": ["KSon", "MoH"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses III",
        "mother_name": "Iset D",
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Son of Ramesses III and Iset D. Depicted in the Medinet Habu procession and to be seen in two sets of temple reliefs dating to his father's reign: in the forecourt of the Ramesses III temple in the first court of the Amun temple at Karnak, and in a scene of games under the Window of Appearances at Medinet Habu. Later king as RAMESSES VI.",
        "source_citation": CITATION_DECLINE,
    })

def test_amenhirkopshef_d_decline_full_row() -> None:
    _assert_full_row("Amenhirkopshef D", {
        "dh_id": "Amenhirkopshef D",
        "name": "Amenhirkopshef D",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses VI",
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Son of Ramesses VI. Buried in an extension of tomb KV13 in the Valley of the Kings.",
        "source_citation": CITATION_DECLINE,
    })

def test_baketwernel_a_decline_full_row() -> None:
    _assert_full_row("Baketwernel A", {
        "dh_id": "Baketwernel A",
        "name": "Baketwernel A",
        "alt_names": [],
        "roles": ["KGW"],
        "sex": "female",
        "spouse_names": ["Ramesses IX (possibly)"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Possible wife of Ramesses IX. Buried in the former tomb of Amenmesse (KV10), where one chamber was plastered and redecorated for her.",
        "source_citation": CITATION_DECLINE,
    })

def test_hemdjert_decline_full_row() -> None:
    _assert_full_row("Hemdjert", {
        "dh_id": "Hemdjert",
        "name": "Hemdjert",
        "alt_names": ["Hebnerdjent"],
        "roles": [],
        "sex": "female",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Iset D"],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Mother of Iset D. Given the variant spellings of her name (e.g. 'Hebnerdjent'), she may have been of foreign extraction.",
        "source_citation": CITATION_DECLINE,
    })

def test_henttawy_q_decline_full_row() -> None:
    _assert_full_row("Henttawy Q", {
        "dh_id": "Henttawy Q",
        "name": "Henttawy Q",
        "alt_names": [],
        "roles": ["KD", "KW", "KM"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses XI (probable)",
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Probable daughter of Ramesses XI (see next section).",
        "source_citation": CITATION_DECLINE,
    })

def test_henutwati_decline_full_row() -> None:
    _assert_full_row("Henutwati", {
        "dh_id": "Henutwati",
        "name": "Henutwati",
        "alt_names": [],
        "roles": ["KGW"],
        "sex": "female",
        "spouse_names": ["Ramesses V"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Wife of Ramesses V; mentioned in Papyrus Wilbour.",
        "source_citation": CITATION_DECLINE,
    })

def test_iset_d_ta_hemdjert_decline_full_row() -> None:
    _assert_full_row("Iset D Ta-Hemdjert", {
        "dh_id": "Iset D Ta-Hemdjert",
        "name": "Iset D Ta-Hemdjert",
        "alt_names": [],
        "roles": ["KGW", "KM", "GW"],
        "sex": "female",
        "spouse_names": ["Ramesses III"],
        "father_name": None,
        "mother_name": "Hemdjert",
        "children_names": ["Amenhirkopshef C", "Ramesses C"],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Wife of Ramesses III. Depicted on a statue of the king in the temple of Mut at Karnak, and participated under Ramesses VI in the installation of her granddaughter, Iset E, as God's Wife of Amun. Owner of tomb QV51 in the Valley of the Queens.",
        "source_citation": CITATION_DECLINE,
    })

def test_iset_e_decline_full_row() -> None:
    _assert_full_row("Iset E", {
        "dh_id": "Iset E",
        "name": "Iset E",
        "alt_names": [],
        "roles": ["KD", "Ador", "GWA"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Ramesses VI",
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Daughter of Ramesses VI; name written with the Adoratrix title within the cartouche. Depicted on a stela from Koptos, now in the Manchester Museum, while her installation as God's Wife of Amun is recorded on a block from Deir el-Bakhit, on Dira Abu'l-Naga.",
        "source_citation": CITATION_DECLINE,
    })

def test_khaemwaset_e_decline_full_row() -> None:
    _assert_full_row("Khaemwaset E", {
        "dh_id": "Khaemwaset E",
        "name": "Khaemwaset E",
        "alt_names": ["Ramesses-Khaemwaset"],
        "roles": ["1KSonB", "SPP"],
        "sex": "male",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Name also found as Ramesses-Khaemwaset. Depicted in the Medinet Habu procession and buried in Valley of the Queens tomb QV44; a canopic jar is in the Cairo Museum, while his sarcophagus lid and possible mummy are in Turin.",
        "source_citation": CITATION_DECLINE,
    })

def test_mentuhirkopshef_b_decline_full_row() -> None:
    _assert_full_row("Mentuhirkopshef B", {
        "dh_id": "Mentuhirkopshef B",
        "name": "Mentuhirkopshef B",
        "alt_names": [],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses III",
        "mother_name": None,
        "children_names": ["Ramesses IX (possibly)"],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Son of Ramesses III. Depicted in the Medinet Habu procession and possibly the father of Ramesses IX. Probably the prince of the name buried in the Valley of the Kings tomb KV13.",
        "source_citation": CITATION_DECLINE,
    })

def test_mentuhirkopshef_c_decline_full_row() -> None:
    _assert_full_row("Mentuhirkopshef C", {
        "dh_id": "Mentuhirkopshef C",
        "name": "Mentuhirkopshef C",
        "alt_names": ["Ramesses-Mentuhirkopshef"],
        "roles": ["1KSonB", "EKSonB", "1Genmo", "ExecH2L"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses IX",
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Name also found as Ramesses-Mentuhirkopshef. Son of Ramesses IX; took over tomb KV19 for his burial.",
        "source_citation": CITATION_DECLINE,
    })

def test_meryamun_b_decline_full_row() -> None:
    _assert_full_row("Meryamun B", {
        "dh_id": "Meryamun B",
        "name": "Meryamun B",
        "alt_names": ["Ramesses-Meryamun"],
        "roles": ["KSonB"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses III",
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Name given in full as Ramesses-Meryamun. Son of Ramesses III; nothing of his life or death known, other than his representation in the Medinet Habu list.",
        "source_citation": CITATION_DECLINE,
    })

def test_meryatum_b_decline_full_row() -> None:
    _assert_full_row("Meryatum B", {
        "dh_id": "Meryatum B",
        "name": "Meryatum B",
        "alt_names": ["Ramesses-Meryatum"],
        "roles": ["KSonB", "HPH"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses III",
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Name also found as Ramesses-Meryatum. Son of Ramesses III; depicted in the Medinet Habu procession. Outlived his father, and occupied the High Priesthood of the Sun at Heliopolis on into the reigns of Ramesses IV and V, when he is mentioned in Papyrus Wilbour.",
        "source_citation": CITATION_DECLINE,
    })

def test_nebmaatre_decline_full_row() -> None:
    _assert_full_row("Nebmaatre", {
        "dh_id": "Nebmaatre",
        "name": "Nebmaatre",
        "alt_names": [],
        "roles": ["KSonB", "HPH"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses IX",
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Son of Ramesses IX. Named together with his father on two gateways which they reinscribed in a temple at Arab el-Hisn, Heliopolis.",
        "source_citation": CITATION_DECLINE,
    })

def test_nebseny_decline_full_row() -> None:
    _assert_full_row("Nebseny", {
        "dh_id": "Nebseny",
        "name": "Nebseny",
        "alt_names": [],
        "roles": [],
        "sex": "male",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Tentamun A"],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Father of Tentamun A. Possibly buried in tomb TT320 at Thebes.",
        "source_citation": CITATION_DECLINE,
    })

def test_nesibanebdjedet_decline_full_row() -> None:
    _assert_full_row("Nesibanebdjedet", {
        "dh_id": "Nesibanebdjedet",
        "name": "Nesibanebdjedet",
        "alt_names": [],
        "roles": [],
        "sex": "male",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Governor of Tanis and possible son-in-law of Ramesses XI. Later king.",
        "source_citation": CITATION_DECLINE,
    })

def test_nubkhesbed_decline_full_row() -> None:
    _assert_full_row("Nubkhesbed", {
        "dh_id": "Nubkhesbed",
        "name": "Nubkhesbed",
        "alt_names": [],
        "roles": ["KGW"],
        "sex": "female",
        "spouse_names": ["Ramesses VI"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Wife of Ramesses VI. Mentioned on a stela of Iset E from Koptos, and also in tomb KV13 in the Valley of the Kings.",
        "source_citation": CITATION_DECLINE,
    })

def test_panebenkemyt_decline_full_row() -> None:
    _assert_full_row("Panebenkemyt", {
        "dh_id": "Panebenkemyt",
        "name": "Panebenkemyt",
        "alt_names": [],
        "roles": ["KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses VI",
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Son of Ramesses VI. Shown on a statues of the king, now in the Luxor Museum.",
        "source_citation": CITATION_DECLINE,
    })

def test_pentaweret_decline_full_row() -> None:
    _assert_full_row("Pentaweret", {
        "dh_id": "Pentaweret",
        "name": "Pentaweret",
        "alt_names": [],
        "roles": [],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses III",
        "mother_name": "Tiye C",
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Son of Ramesses III and Tiye C. In the Turin Judicial Papyrus, recording the trial of those involved in the plot against the king, the following is stated: 'Pentaweret, to whom had been given that other name (perhaps referring to his putative name as pharaoh?): He was brought in because of his collusion with Tiye, his mother, when she had plotted the matters with the women of the harem, concerning rebellion against his lord. He was placed before the (court commissioners) in order to examine him; they found him guilty; they left him in his place; he took his own life.'",
        "source_citation": CITATION_DECLINE,
    })

def test_pinudjem_i_decline_full_row() -> None:
    _assert_full_row("Pinudjem I", {
        "dh_id": "Pinudjem I",
        "name": "Pinudjem I",
        "alt_names": [],
        "roles": ["HPA"],
        "sex": "male",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Probable son-in-law of Ramesses XI (see next section).",
        "source_citation": CITATION_DECLINE,
    })

def test_prehirwenemef_b_decline_full_row() -> None:
    _assert_full_row("Prehirwenemef B", {
        "dh_id": "Prehirwenemef B",
        "name": "Prehirwenemef B",
        "alt_names": [],
        "roles": ["1KSon"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses III",
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Son of Ramesses III. Depicted in the Medinet Habu procession; predeceased his father and was buried in the Valley of the Queens (QV42).",
        "source_citation": CITATION_DECLINE,
    })

def test_ramesses_c_decline_full_row() -> None:
    _assert_full_row("Ramesses C", {
        "dh_id": "Ramesses C",
        "name": "Ramesses C",
        "alt_names": ["Ramesses IV"],
        "roles": ["KSon", "Genmo"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses III",
        "mother_name": "Iset D",
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Son of Ramesses III and Iset D. Depicted in the Medinet Habu procession and heir to the throne for much of his father's reign. He is to be seen in two sets of temple reliefs dating to his father's reign: in the forecourt of the Ramesses III temple in the first court of the Amun temple at Karnak, and in a scene of games under the Window of Appearances at Medinet Habu. As Crown Prince, he seems to have taken an increasingly important role in the rule of Egypt during the closing years of his father's reign. For example, as early as year 27 he is depicted as being responsible for the appointment of one Amenemopet as High Priest of Mut at Karnak in the latter's tomb (TT148) on Dira Abu'l-Naga at Western Thebes. A tomb was constructed for the prince in the Valley of the Queens (QV53), but remained unused when he ascended the throne as RAMESSES IV.",
        "source_citation": CITATION_DECLINE,
    }, sub_period=SUB_PERIOD_DECLINE)

def test_ramesses_d_decline_full_row() -> None:
    _assert_full_row("Ramesses D", {
        "dh_id": "Ramesses D",
        "name": "Ramesses D",
        "alt_names": [],
        "roles": ["1KSon", "Genmo"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses VII",
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Son of Ramesses VII. The foundation of his tomb, presumably in the Valley of the Queens, is mentioned on an ostrakon in the Louvre.",
        "source_citation": CITATION_DECLINE,
    })

def test_sethirkopshef_b_decline_full_row() -> None:
    _assert_full_row("Sethirkopshef B", {
        "dh_id": "Sethirkopshef B",
        "name": "Sethirkopshef B",
        "alt_names": ["Ramesses VIII"],
        "roles": ["KSon", "MH"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Ramesses III",
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Son of Ramesses III, and depicted in the Medinet Habu procession. Except for his tomb in the Valley of the Queens (QV43), little is known of this prince during his father's lifetime, but he survived into the reigns of his elder brothers and began a new tomb in the Valley of the Kings (KV19). However, he ultimately became king as RAMESSES VIII.",
        "source_citation": CITATION_DECLINE,
    })

def test_takhat_b_decline_full_row() -> None:
    _assert_full_row("Takhat B", {
        "dh_id": "Takhat B",
        "name": "Takhat B",
        "alt_names": [],
        "roles": ["KM"],
        "sex": "female",
        "spouse_names": ["Mentuhirkopshef B (probable)"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Ramesses IX"],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Probable wife of Mentuhirkopshef B and mother of Ramesses IX. Probably buried in the former tomb of Amenmesse (KV10), where one chamber was plastered and redecorated for her. Parts of her probable mummy were found in the tomb from 1996 onwards.",
        "source_citation": CITATION_DECLINE,
    })

def test_tawerettenru_decline_full_row() -> None:
    _assert_full_row("Tawerettenru", {
        "dh_id": "Tawerettenru",
        "name": "Tawerettenru",
        "alt_names": [],
        "roles": ["KW"],
        "sex": "female",
        "spouse_names": ["Ramesses V"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Wife of Ramesses V; mentioned in Papyrus Wilbour.",
        "source_citation": CITATION_DECLINE,
    })

def test_tentamun_a_decline_full_row() -> None:
    _assert_full_row("Tentamun A", {
        "dh_id": "Tentamun A",
        "name": "Tentamun A",
        "alt_names": [],
        "roles": [],
        "sex": "female",
        "spouse_names": ["Ramesses XI (probable)"],
        "father_name": "Nebseny",
        "mother_name": None,
        "children_names": ["Henttawy Q"],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Mother of Henttawy Q and probably wife of Ramesses XI; mentioned in the funerary papyrus of her daughter.",
        "source_citation": CITATION_DECLINE,
    })

def test_tentamun_b_decline_full_row() -> None:
    _assert_full_row("Tentamun B", {
        "dh_id": "Tentamun B",
        "name": "Tentamun B",
        "alt_names": [],
        "roles": [],
        "sex": "female",
        "spouse_names": ["Nesibanebdjedet I"],
        "father_name": "Ramesses XI (probable)",
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Probable daughter of Ramesses XI and wife of Nesibanebdjedet I (see next section).",
        "source_citation": CITATION_DECLINE,
    })

def test_tiye_b_mereniset_decline_full_row() -> None:
    _assert_full_row("Tiye B Mereniset", {
        "dh_id": "Tiye B Mereniset",
        "name": "Tiye B Mereniset",
        "alt_names": [],
        "roles": ["KGW", "KM"],
        "sex": "female",
        "spouse_names": ["Setnakhte"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Ramesses III"],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Wife of Setnakhte, with whom she is adored by a priest named Meresyotef on a stela from Abydos, now in Cairo. Shown with her son, Ramesses III, on another block from the site.",
        "source_citation": CITATION_DECLINE,
    })

def test_tiye_c_decline_full_row() -> None:
    _assert_full_row("Tiye C", {
        "dh_id": "Tiye C",
        "name": "Tiye C",
        "alt_names": [],
        "roles": [],
        "sex": "female",
        "spouse_names": ["Ramesses III"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Pentaweret"],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Wife of Ramesses III; conspired with others to place her son, Pentaweret, on the throne. Final fate unknown, but presumably tried and condemned.",
        "source_citation": CITATION_DECLINE,
    })

def test_tyti_decline_full_row() -> None:
    _assert_full_row("Tyti", {
        "dh_id": "Tyti",
        "name": "Tyti",
        "alt_names": [],
        "roles": ["KD", "KSis", "KW", "KM", "GW"],
        "sex": "female",
        "spouse_names": ["Ramesses X (possibly)"],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": False,
        "notes": "Possible wife of Ramesses X. Owner of tomb QV52 in the Valley of the Queens.",
        "source_citation": CITATION_DECLINE,
    })

def test_anuketemheb_decline_full_row() -> None:
    _assert_full_row("Anuketemheb", {
        "dh_id": "Anuketemheb",
        "name": "Anuketemheb",
        "alt_names": [],
        "roles": ["KD", "KW", "KGW"],
        "sex": "female",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": True,
        "notes": "Original owner of a sarcophagus and canopic jars later usurped for Takhat B in KV10.",
        "source_citation": CITATION_DECLINE,
    })

def test_taiay_decline_full_row() -> None:
    _assert_full_row("Taiay", {
        "dh_id": "Taiay",
        "name": "Taiay",
        "alt_names": [],
        "roles": ["KW"],
        "sex": "female",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 20,
        "sub_period": SUB_PERIOD_DECLINE,
        "unplaced": True,
        "notes": "Name and title appears written in ink on an ostrakon found in the Valley of the Kings, between the tombs of Amenmesse and Ramesses III.",
        "source_citation": CITATION_DECLINE,
    })

