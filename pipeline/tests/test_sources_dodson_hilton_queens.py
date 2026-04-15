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

# Legacy aliases kept so the Power-and-Glory test block below (which was
# written first and references these names) stays untouched. New tests
# should use the `_POWER` / `_AMARNA` suffixed constants.
SUB_PERIOD = SUB_PERIOD_POWER
CITATION = CITATION_POWER


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(json.loads(line) for line in JSONL.read_text().splitlines() if line.strip())


def _row(dh_id: str) -> dict:
    hits = [r for r in _rows() if r["dh_id"] == dh_id]
    if len(hits) != 1:
        raise AssertionError(f"expected 1 row for {dh_id!r}, got {len(hits)}")
    return hits[0]


def _assert_full_row(dh_id: str, expected: dict) -> None:
    """Assert full-row equality per rule 5. Every schema field must be
    present in `expected`; the row must match key-for-key, value-for-value.
    """
    row = _row(dh_id)
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
    """Power-and-Glory (59) + Amarna-Interlude (41) = 100 rows total."""
    assert len(_rows()) == 100, len(_rows())


def test_row_counts_per_chunk() -> None:
    """Power-and-Glory = 47 placed + 12 Unplaced = 59. Amarna = 41 rows
    (36 named + 5 lacuna group entries; no Unplaced sub-block)."""
    by_period: dict[str, int] = {}
    for r in _rows():
        by_period[r["sub_period"]] = by_period.get(r["sub_period"], 0) + 1
    assert by_period == {SUB_PERIOD_POWER: 59, SUB_PERIOD_AMARNA: 41}, by_period


def test_dh_id_is_unique() -> None:
    """No duplicate dh_id in the extract. D&H disambiguator letters
    (Ahmes A, Ahmes B, Iset A, Iset B, Iset C, ...) guarantee this."""
    ids = [r["dh_id"] for r in _rows()]
    assert len(ids) == len(set(ids)), "duplicate dh_id detected"


def test_every_row_has_complete_citation() -> None:
    """Each row's `source_citation` matches the chunk it came from."""
    citations = {
        SUB_PERIOD_POWER: CITATION_POWER,
        SUB_PERIOD_AMARNA: CITATION_AMARNA,
    }
    for r in _rows():
        expected = citations[r["sub_period"]]
        assert r["source_citation"] == expected, r


def test_every_row_has_dyn18_and_known_sub_period() -> None:
    allowed = {SUB_PERIOD_POWER, SUB_PERIOD_AMARNA}
    for r in _rows():
        assert r["dynasty"] == 18, r
        assert r["sub_period"] in allowed, r


def test_unplaced_set_is_the_twelve_expected_ids() -> None:
    """D&H's 'Unplaced' sub-block on printed p. 141 has exactly 12 entries."""
    unplaced = [r for r in _rows() if r["unplaced"]]
    assert len(unplaced) == 12, f"expected 12 unplaced, got {len(unplaced)}"
    assert {r["dh_id"] for r in unplaced} == {
        "Amenemhat Q", "Henut Q", "Henutiunu", "Merybennu", "Meryetptah A",
        "Nebetnehat A", "Sithori", "Tatau", "Thutmose Q", "Ti", "Wiay A",
        "[...]pentepkau",
    }


def test_unplaced_rows_sort_last_in_reconciled_jsonl() -> None:
    """The 12 unplaced rows must occupy the trailing 12 positions of
    `reconciled.jsonl` — merge.py's sort groups them into a final bin so
    the file reads as placed-alphabetical, then unplaced-alphabetical.
    This is a regression on the issue code-reviewer flagged on the first
    sort key implementation (which pushed only `Q`-suffix and `[`-prefix
    ids, leaving `Henutiunu`, `Sithori`, etc. interleaved in the main
    alphabetical block).
    """
    rows = _rows()
    for r in rows[:-12]:
        assert r["unplaced"] is False, r["dh_id"]
    for r in rows[-12:]:
        assert r["unplaced"] is True, r["dh_id"]


def test_sex_inference_covers_every_row() -> None:
    for r in _rows():
        assert r["sex"] in ("male", "female"), r


def test_role_code_set_spans_the_known_codes() -> None:
    """Every known D&H code in the two chunks appears on at least one row."""
    all_codes: set[str] = set()
    for r in _rows():
        all_codes.update(r["roles"])
    # Power-and-Glory codes:
    for expected in ["KM", "KW", "KGW", "GW", "KSis", "KD", "KSon", "EKSon"]:
        assert expected in all_codes, f"expected code {expected!r} never extracted"
    # Amarna-Interlude codes (new in this chunk):
    for expected in ["KDB", "L2L", "KSonN", "MULE", "GBW", "King of Mitanni"]:
        assert expected in all_codes, f"expected Amarna code {expected!r} never extracted"


def test_kings_cross_referenced_in_bold_caps_not_extracted_as_entries() -> None:
    """`AMENHOTEP II`, `AMENHOTEP III`, `THUTMOSE IV` are cross-references
    inside other rows' prose, not Brief Lives entries of their own.
    """
    king_refs = {"AMENHOTEP II", "AMENHOTEP III", "THUTMOSE IV"}
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
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose I; known from a range of monuments, principally "
            "those of her daughter, Hatshepsut, but also from other material, "
            "including a statue of her mortuary priest, Nakht, from Karnak."
        ),
        "source_citation": CITATION,
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
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Daughter of Thutmose I, wife of Thutmose II and later king. A "
            "range of monuments date to her period as queen, and also as "
            "regent for Thutmose III. These include inscriptions from Karnak, "
            "Nubia and Sinai, and an (unused) tomb and sarcophagus in the "
            "Wadi Siqqat Taqa el-Zeide at Thebes."
        ),
        "source_citation": CITATION,
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
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Mother of Thutmose III; she was given the title of KGW during "
            "his reign, as well as GW after her death. Possessor of a statue "
            "from Karnak, and mentioned a number of times on her son's "
            "funerary monuments and equipment."
        ),
        "source_citation": CITATION,
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
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Daughter of Thutmose III and Meryetre-Hatshepsut. Represented on "
            "the statue of her grandmother, Huy, in the British Museum."
        ),
        "source_citation": CITATION,
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
        "sub_period": SUB_PERIOD,
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
        "source_citation": CITATION,
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
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose I, mother of Thutmose II and probable daughter "
            "of Ahmose I. Represented by the leg of her son on a colossus in "
            "front of the south face of the Eighth Pylon, in the temple of "
            "Thutmose III at Deir el-Bahari and on a stela found near the "
            "Ramesseum. She was also the owner of a statue found in the "
            "chapel of Wadjmose."
        ),
        "source_citation": CITATION,
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
        "sub_period": SUB_PERIOD,
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
        "source_citation": CITATION,
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
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose III, probably of Syrian extraction. Buried in "
            "a tomb in Wadi Gabbanet el-Qurud together with Menwi and Merti; "
            "much of the funerary equipment is now in the Metropolitan "
            "Museum of Art."
        ),
        "source_citation": CITATION,
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
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose III, probably of Syrian extraction. Buried with "
            "Menhet and Merti."
        ),
        "source_citation": CITATION,
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
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Wife of Thutmose III, probably of Syrian extraction. Buried with "
            "Menhet and Menwi."
        ),
        "source_citation": CITATION,
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
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Daughter of Thutmose IV. One of the group of princesses reburied "
            "during the 21st Dynasty on Sheikh Abd el-Qurna."
        ),
        "source_citation": CITATION,
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
        "sub_period": SUB_PERIOD,
        "unplaced": True,
        "notes": (
            "Unplaced, probably mid-18th Dynasty. Known only from a fragment "
            "of sphinx-stela from near the Second Pyramid of Giza."
        ),
        "source_citation": CITATION,
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
        "sub_period": SUB_PERIOD,
        "unplaced": False,
        "notes": (
            "Son of Thutmose III. Named upon the statuette of the Chancellor, "
            "Sennefer, in the Cairo Museum."
        ),
        "source_citation": CITATION,
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

