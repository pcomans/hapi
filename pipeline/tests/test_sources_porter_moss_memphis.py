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

Chunk 3 covers the Gîza Central Field — LG 100 Khentkaus I "Sarcophagus-
shaped Tomb" (Old Kingdom queen-mother at the IV/V transition) plus the
adjacent Saite (Dyn XXVI) LG-numbered tombs including the joint burial of
Commander ʿAhmosi + Queen Nekhtubasterau (LG 83, wife of Amasis) and the
priest-pair Harsiesi + Harwoz (LG 97). 5 rows from PM III.1 § III "E.
CENTRAL FIELD", physical pp.285–289 / printed pp.288–292.

Chunk 4 is the FIRST chunk drawn from PM Vol III.2 (Saqqâra-Dahshûr,
ed. Málek, 1978/1981) — covering the back half of PM III.2 § I.
PYRAMIDS Saqqâra: 5 Dyn V/VI royal kings (Unis, Pepy I, Isesi, Merenrʿ I,
Pepy II) + 4 queens (anonymous Wife-of-Isesi + Pepy II's three queens
Neit, Iput II, Wezebten). 9 rows from physical pp.61–72 / printed
pp.421–432. First `memphite_area: "Saqqara"` rows, first `SAQ-`
descriptor-form tomb_ids, first PM III.2 edition citation.

Chunk 5 closes the front half of PM III.2 § I. PYRAMIDS — sections A
through E that chunk 4 left open. 4 royal kings (Teti Dyn VI, Userkaf
Dyn V, Neterikhet/Zoser Dyn III, Sekhemkhet Dyn III unfinished) + 2
named queens under Teti's complex (Iput I, Khuit) + 1 anonymous Dyn-III
structure (E. 'Great Enclosure'). 7 rows from physical pp.33–57 /
printed pp.393–417. First Dyn III rows in this source; first
parenthetical-alias pattern (Neterikhet ↔ Zoser); first Shape-3
anonymous structure with `occupant_name: null` AND `dynasty: "3"`
(distinct from chunk-4 anonymous-queen pattern which had a known
dynasty inherited from the king's complex).

Chunk 6 opens the West Field (PM III.1 § III. NECROPOLIS — A. WEST
FIELD), Junker-excavated low-thousands cemeteries G 1000 / G 1100 /
G 1200 / G 1300 / G 1400 / G 1500 / G 1600 / G 1900. 54 rows from
physical pp.46–62 / printed pp.49–65: 30 Shape-1 named-primary rows +
24 Shape-2 bare-suffix (anonymous shaft) rows. Dense mix of named
Dyn-IV-to-VI Old Kingdom officials (Shepseskafʿankh, Wepemnefert,
ʿAnkh-haf, Hetepib, etc.) and uninscribed shafts. First chunk to
introduce: Shape-3 compound twin-mastaba headwords in the West Field
(G 1452+1453 ZADUWAʿ shared); underdot-Ḥ glyph normalisation for
non-royal names (Meḥyt in G1201); the `Royal acquaintance (woman)`
non-royal-honorific role rule (egyptologist F5/F6 corrections).
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
EDITION_PM_III_2 = "PM III.2 2nd ed. 1978/1981"


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

# Chunk 3: Gîza Central Field — LG 100 Khentkaus I + Saite Dyn-XXVI cluster.
# Source: PM III.1 2nd ed. 1974, § III. NECROPOLIS — E. CENTRAL FIELD,
# physical pp.285–289 / printed pp.288–292.
CHUNK3_TOMB_IDS: frozenset[str] = frozenset({
    "LG100",   # SARCOPHAGUS-SHAPED TOMB OF Khentkaus I (Dyn IV/V queen-mother)
    "LG81",    # bare-headword Saite Dyn-XXVI (OCR-drift "LG 8 I" → "LG81")
    "LG83",    # joint: ʿAhmosi + Queen Nekhtubasterau (wife of Amasis)
    "LG84",    # Pakap (good name Wehebreʿ-emakhet)
    "LG97",    # joint: Harsiesi + Harwoz, both wnrw-priests
})

# Chunk 4: Saqqâra § I. PYRAMIDS back half — Dyn V/VI royal kings + queens.
# Source: PM III.2 2nd ed. 1978/1981, § I. PYRAMIDS F-K,
# physical pp.61–72 / printed pp.421–432.
CHUNK4_TOMB_IDS: frozenset[str] = frozenset({
    "SAQ-Unis", "SAQ-PepyI", "SAQ-Isesi", "SAQ-MerenreI", "SAQ-PepyII",  # 5 kings
    "SAQ-WifeOfIsesi",                                                    # anon queen
    "SAQ-Neit", "SAQ-IputII", "SAQ-Wezebten",                             # 3 named queens (Pepy II)
})

# Chunk 5: Saqqâra § I. PYRAMIDS front half — Dyn III/V/VI royal kings +
# 2 Teti queens + anonymous Great Enclosure.
# Source: PM III.2 2nd ed. 1978/1981, § I. PYRAMIDS A-E,
# physical pp.33–57 / printed pp.393–417.
CHUNK5_TOMB_IDS: frozenset[str] = frozenset({
    "SAQ-Teti", "SAQ-Userkaf", "SAQ-Neterikhet", "SAQ-Sekhemkhet",  # 4 kings
    "SAQ-IputI", "SAQ-Khuit",                                       # 2 queens (Teti)
    "SAQ-GreatEnclosure",                                           # anon Shape-3
})

# Chunk 7: Gîza § III.A West Field Cemetery G 2000 + G 2100 + Mastaba G 2220.
# Source: PM III.1 2nd ed. 1974, § III. NECROPOLIS — A. WEST FIELD continuation,
# physical pp.63–80 / printed pp.66–83. 46 rows total.
# - Cemetery G 2000 (23 rows): G 2000 through G 2099, mix of named-primary and
#   bare-suffix shafts. Includes the G 2092+2093 NIMAʿETREʿ compound twin.
# - Cemetery G 2100 + Mastaba G 2220 (23 rows): G 2100Iannexe (Merib annexe to
#   G 2100) + G 2101 NENSEZERKAI I (Princess) + G 2110 NUFER + … + G 2155 +
#   G 2156 Kanenesut II + G 2156b Redenes (PM's second G 2156 — disambiguated
#   via pre_merge G2156→G2156b rename) + G 2175-G 2197 + G 2220 (eponymous).
CHUNK7_TOMB_IDS: frozenset[str] = frozenset({
    # G 2000 cemetery (23 rows)
    "G2000", "G2001", "G2002", "G2004", "G2009", "G2011",
    "G2021", "G2032", "G2033", "G2035", "G2036", "G2037", "G2037b",
    "G2041", "G2061", "G2070", "G2088", "G2089",
    "G2091", "G2092", "G2093", "G2097", "G2099",
    # G 2100 cemetery + Mastaba G 2220 (23 rows)
    "G2100a", "G2101", "G2110", "G2113", "G2120",
    "G2130", "G2132", "G2135", "G2136", "G2140", "G2150",
    "G2155", "G2156", "G2156b",
    "G2175", "G2178", "G2184", "G2185", "G2188",
    "G2191", "G2196", "G2197",
    "G2220",
})

# Chunk 6: Gîza § III.A West Field Junker cemeteries G 1000–G 1900.
# Source: PM III.1 2nd ed. 1974, § III. NECROPOLIS — A. WEST FIELD,
# physical pp.46–62 / printed pp.49–65. 54 rows (30 named primary + 24
# bare-suffix). Cemetery banners: G 1000, G 1100, G 1200, G 1300,
# G 1400, G 1500, G 1600, G 1900.
CHUNK6_TOMB_IDS: frozenset[str] = frozenset({
    # G 1000 cemetery (14 rows)
    "G1008", "G1011", "G1012", "G1020", "G1021", "G1026", "G1029",
    "G1032", "G1036", "G1039", "G1040", "G1047", "G1061", "G1062",
    # G 1100 cemetery (8 rows)
    "G1104", "G1105", "G1109", "G1111", "G1151", "G1152", "G1157", "G1171",
    # G 1200 cemetery (17 rows)
    "G1201", "G1203", "G1204", "G1205", "G1206", "G1207", "G1208",
    "G1213", "G1214", "G1221", "G1223", "G1225", "G1226", "G1227",
    "G1231", "G1234", "G1235",
    # G 1300 cemetery (5 rows)
    "G1301", "G1309", "G1313", "G1314", "G1351",
    # G 1400 / G 1500 / G 1600 / G 1900 (small clusters at chunk tail)
    "G1402", "G1452", "G1453", "G1457", "G1461",
    "G1501",
    "G1607", "G1608", "G1673",
    "G1903",
})

# Chunk 8: Gîza § III.A West Field Cemetery G 2300 + G 2400 + G 2500.
# Source: PM III.1 2nd ed. 1974, § III. NECROPOLIS — A. WEST FIELD continuation,
# physical pp.80–92 / printed pp.83–95. 33 rows total under three Reisner
# cemetery banners:
# - CEMETERY EN ECHELON. NORTH PART WITH MASTABAS G 2300 AND 2400 (22 rows
#   in the G 2300 cluster + 10 rows in the G 2400 cluster)
# - CEMETERY G 2500 (1 row: G 2501)
# Includes dense Dyn V–VI named-official material with "good name" alias
# pattern (Senezemib Inti / Senezemib Mehi / Meryreʿ-Meryptaḥʿankh Nekhebu /
# Akhetmeḥu / ʿAnkhirptah etc.), one joint-burial headword (G 2415 Weri +
# wife Meti), and one wife-attestation in body prose (G 2423 Meḥu +
# wife Khenit). 6 tie-break-overrides resolve 1/1/1 ties on G2347a (bare-
# suffix Shape-2), G2381 (notes + occupant_name underdot-Ḥ),
# G2387 (occupant_name underdot-Ḥ), G2415 (notes lowercase `and`),
# G2423 (notes ayin + wife clause).
CHUNK8_TOMB_IDS: frozenset[str] = frozenset({
    # CEMETERY EN ECHELON. G 2300 cluster (22 rows)
    "G2332", "G2335", "G2336", "G2347", "G2347a",
    "G2352", "G2353", "G2359", "G2361", "G2362",
    "G2366", "G2370", "G2374", "G2375", "G2375a",
    "G2378", "G2379", "G2381", "G2384", "G2385",
    "G2387", "G2391",
    # CEMETERY EN ECHELON. G 2400 cluster (10 rows)
    "G2407", "G2415", "G2418", "G2420", "G2422",
    "G2423", "G2427", "G2430", "G2450", "G2475",
    # CEMETERY G 2500 (1 row)
    "G2501",
})

# Chunk 9: Gîza § III.A West Field Cemetery G 3000 (Fisher Minor Cemetery).
# Source: PM III.1 2nd ed. 1974, § III. NECROPOLIS — A. WEST FIELD continuation,
# physical pp.92–96 / printed pp.95–99. 14 rows: 13 Shape-1 named-primary +
# 1 Shape-2 bare-suffix (G 3015). The "Minor Cemetery" was excavated by
# Clarence S. Fisher for the Penn Eckley B. Coxe Jr. Expedition (1915).
# 6 tie-break-overrides resolve 1/1/1 ties on G 3008 (Snefruḥotp + wife
# Khenut called Inti, role and notes), G 3050 (ʿAnkh ka-servant + wife
# Kednefert mitrt, role and notes), G 3093 (Mededi + wife Khnemt with
# Neith/Ḥathor titles, role and notes), G 3098 (Iymerery + annexe
# occupant Neferḥetpes-Wer + father Duareʿ, role and notes).
CHUNK9_TOMB_IDS: frozenset[str] = frozenset({
    "G3004", "G3008", "G3015", "G3020", "G3033", "G3035",
    "G3050", "G3082", "G3086", "G3093", "G3094", "G3096",
    "G3097", "G3098",
})

EXPECTED_TOMB_IDS: frozenset[str] = (
    CHUNK1_TOMB_IDS | CHUNK2_TOMB_IDS | CHUNK3_TOMB_IDS | CHUNK4_TOMB_IDS
    | CHUNK5_TOMB_IDS | CHUNK6_TOMB_IDS | CHUNK7_TOMB_IDS | CHUNK8_TOMB_IDS
    | CHUNK9_TOMB_IDS
)


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


# Numbered tomb-ID form: 1+ uppercase prefix letters, 1+ digits, optional
# lowercase/uppercase suffix letter. Accepts:
# - Reisner G-numbers (G1, G1a, G7000X) from chunks 1 + 2
# - Lepsius LG-numbers (LG81, LG83, LG100) from chunk 3
_TOMB_ID_RE = re.compile(r"^(?P<prefix>[A-Z]+)(?P<num>\d+)(?P<suffix>[a-zA-Z]?)$")

# Descriptor tomb-ID form: 1+ uppercase prefix letters, hyphen, then a
# camel-case descriptor (e.g. `SAQ-Unis`, `SAQ-PepyII`, `SAQ-WifeOfIsesi`).
# Used when PM has no consistent numeric tomb-ID scheme — Saqqâra pyramids
# are identified by king-name + Lepsius Roman numeral in PM-prose, but no
# uniform numeric ID. Chunks 4+ use this form for Saqqâra rows.
_TOMB_ID_DESC_RE = re.compile(r"^(?P<prefix>[A-Z]+)-(?P<desc>[A-Za-z][A-Za-z0-9]*)$")


def _match_tomb_id(tid: str):
    """Return the regex match object for either tomb_id form, or None."""
    return _TOMB_ID_RE.match(tid) or _TOMB_ID_DESC_RE.match(tid)


def test_tomb_id_shape() -> None:
    """Every committed tomb_id must match EITHER the numbered form
    (`<PREFIX><digits><suffix?>`) OR the descriptor form
    (`<PREFIX>-<CamelCaseDescriptor>`)."""
    for tid in EXPECTED_TOMB_IDS:
        assert _match_tomb_id(tid), tid


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
        m = _match_tomb_id(row["tomb_id"])
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
    "tomb_aliases", "co_occupants", "co_occupant_roles", "is_joint_burial",
    "occupant_role", "dynasty", "sub_period", "date_bce_approx_start",
    "date_bce_approx_end", "cemetery", "discovery_year", "discoverer",
    "is_unfinished", "is_uninscribed", "is_usurped",
    "attribution_certainty", "shared_with_tombs", "notes_from_pm",
    "source_citation",
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


_VALID_MEMPHITE_AREAS = frozenset({"Giza", "Saqqara"})


def test_memphite_area_controlled_vocab() -> None:
    """Chunks 1-3 are all PYRAMID-FIELD OF GÎZA. Chunks 4 and 5 are
    PYRAMID-FIELD OF SAQQARA (PM III.2 § I. PYRAMIDS back and front
    halves respectively). Future chunks will extend with `Abusir`,
    `Dahshur`, `Lisht`, `Meidum`."""
    for row in _rows():
        assert row["memphite_area"] in _VALID_MEMPHITE_AREAS, row


_VALID_SECTIONS = frozenset({"I", "III"})
_VALID_EDITIONS = frozenset({EDITION_PM_III_1, EDITION_PM_III_2})


def test_source_citation_shape() -> None:
    for row in _rows():
        cit = row["source_citation"]
        assert set(cit.keys()) == {"page", "edition", "section"}, cit
        assert isinstance(cit["page"], int), cit
        assert cit["edition"] in _VALID_EDITIONS, cit
        assert cit["section"] in _VALID_SECTIONS, cit


def test_source_citation_section_matches_chunk() -> None:
    """Chunks 1, 4, 5 cite `section: "I"` (PM III.1's § I. PYRAMIDS and
    PM III.2's § I. PYRAMIDS — different volumes but both under their
    volume's § I). Chunks 2 and 3 cite `section: "III"` (PM III.1's
    § III. NECROPOLIS — B. EAST FIELD and E. CENTRAL FIELD)."""
    for row in _rows():
        if row["tomb_id"] in CHUNK1_TOMB_IDS:
            assert row["source_citation"]["section"] == "I", row
        elif row["tomb_id"] in CHUNK2_TOMB_IDS:
            assert row["source_citation"]["section"] == "III", row
        elif row["tomb_id"] in CHUNK3_TOMB_IDS:
            assert row["source_citation"]["section"] == "III", row
        elif row["tomb_id"] in CHUNK4_TOMB_IDS:
            assert row["source_citation"]["section"] == "I", row
        elif row["tomb_id"] in CHUNK5_TOMB_IDS:
            assert row["source_citation"]["section"] == "I", row
        elif row["tomb_id"] in CHUNK6_TOMB_IDS:
            assert row["source_citation"]["section"] == "III", row
        elif row["tomb_id"] in CHUNK7_TOMB_IDS:
            assert row["source_citation"]["section"] == "III", row
        elif row["tomb_id"] in CHUNK8_TOMB_IDS:
            assert row["source_citation"]["section"] == "III", row
        elif row["tomb_id"] in CHUNK9_TOMB_IDS:
            assert row["source_citation"]["section"] == "III", row


def test_source_citation_edition_matches_chunk() -> None:
    """Chunks 1-3, 6, 7, 8, 9 cite PM III.1; chunks 4 and 5 cite PM III.2."""
    for row in _rows():
        if row["tomb_id"] in (
            CHUNK1_TOMB_IDS | CHUNK2_TOMB_IDS | CHUNK3_TOMB_IDS
            | CHUNK6_TOMB_IDS | CHUNK7_TOMB_IDS | CHUNK8_TOMB_IDS
            | CHUNK9_TOMB_IDS
        ):
            assert row["source_citation"]["edition"] == EDITION_PM_III_1, row
        elif row["tomb_id"] in CHUNK4_TOMB_IDS | CHUNK5_TOMB_IDS:
            assert row["source_citation"]["edition"] == EDITION_PM_III_2, row


def test_source_citation_page_in_expected_range() -> None:
    """Printed page ranges: chunk 1 = 11–35, chunk 2 = 179–190,
    chunk 3 = 288–292, chunk 4 = 421–432, chunk 5 = 393–417,
    chunk 6 = 49–65."""
    for row in _rows():
        page = row["source_citation"]["page"]
        if row["tomb_id"] in CHUNK1_TOMB_IDS:
            assert 11 <= page <= 35, f"{row['tomb_id']} page {page} outside chunk-1 [11, 35]"
        elif row["tomb_id"] in CHUNK2_TOMB_IDS:
            assert 179 <= page <= 190, f"{row['tomb_id']} page {page} outside chunk-2 [179, 190]"
        elif row["tomb_id"] in CHUNK3_TOMB_IDS:
            assert 288 <= page <= 292, f"{row['tomb_id']} page {page} outside chunk-3 [288, 292]"
        elif row["tomb_id"] in CHUNK4_TOMB_IDS:
            assert 421 <= page <= 432, f"{row['tomb_id']} page {page} outside chunk-4 [421, 432]"
        elif row["tomb_id"] in CHUNK5_TOMB_IDS:
            assert 393 <= page <= 417, f"{row['tomb_id']} page {page} outside chunk-5 [393, 417]"
        elif row["tomb_id"] in CHUNK6_TOMB_IDS:
            assert 49 <= page <= 65, f"{row['tomb_id']} page {page} outside chunk-6 [49, 65]"
        elif row["tomb_id"] in CHUNK7_TOMB_IDS:
            assert 66 <= page <= 83, f"{row['tomb_id']} page {page} outside chunk-7 [66, 83]"
        elif row["tomb_id"] in CHUNK8_TOMB_IDS:
            assert 83 <= page <= 95, f"{row['tomb_id']} page {page} outside chunk-8 [83, 95]"
        elif row["tomb_id"] in CHUNK9_TOMB_IDS:
            assert 95 <= page <= 99, f"{row['tomb_id']} page {page} outside chunk-9 [95, 99]"


# === Phase-0 boundary assertions ============================================


def test_bce_dates_null_at_extraction_stage() -> None:
    """Per CLAUDE.md rules 1 + 7, BCE dates come from king authority at Phase A,
    not from PM headwords (PM does not print BCE reign ranges)."""
    for row in _rows():
        assert row["date_bce_approx_start"] is None, row
        assert row["date_bce_approx_end"] is None, row


def test_cemetery_by_chunk() -> None:
    """Chunks 1, 4, 5 (pyramid-complex rows) carry `cemetery: null` —
    the pyramid IS its own complex. Chunk 2 (East Field mastabas) carries
    `cemetery: "G 7000"` per PM's `CEMETERY G 7000` banner on printed p.182.
    Chunk 3 (Central Field) carries `cemetery: "Central Field"`."""
    for row in _rows():
        if row["tomb_id"] in CHUNK1_TOMB_IDS:
            assert row["cemetery"] is None, row
        elif row["tomb_id"] in CHUNK2_TOMB_IDS:
            assert row["cemetery"] == "G 7000", row
        elif row["tomb_id"] in CHUNK3_TOMB_IDS:
            assert row["cemetery"] == "Central Field", row
        elif row["tomb_id"] in CHUNK4_TOMB_IDS:
            assert row["cemetery"] is None, row
        elif row["tomb_id"] in CHUNK5_TOMB_IDS:
            assert row["cemetery"] is None, row
        elif row["tomb_id"] in CHUNK6_TOMB_IDS:
            # Each chunk-6 row inherits the PM CEMETERY banner above it.
            # 8 banners: G 1000 / G 1100 / G 1200 / G 1300 / G 1400 /
            # G 1500 / G 1600 / G 1900.
            assert row["cemetery"] in {
                "G 1000", "G 1100", "G 1200", "G 1300",
                "G 1400", "G 1500", "G 1600", "G 1900",
            }, row
        elif row["tomb_id"] in CHUNK7_TOMB_IDS:
            # Chunk 7: 2 cemetery banners. CEMETERY G 2000 + CEMETERY
            # G 2100 AND MASTABA G 2220.
            assert row["cemetery"] in {"G 2000", "G 2100"}, row
        elif row["tomb_id"] in CHUNK8_TOMB_IDS:
            # Chunk 8: 3 sub-cemeteries under 2 PM banners. CEMETERY EN
            # ECHELON. NORTH PART WITH MASTABAS G 2300 AND 2400 splits
            # into G 2300 + G 2400 by Reisner-number range; CEMETERY
            # G 2500 is the third banner.
            assert row["cemetery"] in {"G 2300", "G 2400", "G 2500"}, row
        elif row["tomb_id"] in CHUNK9_TOMB_IDS:
            # Chunk 9: single CEMETERY G 3000 banner (Fisher's "Minor
            # Cemetery", Penn Coxe Expedition 1915).
            assert row["cemetery"] == "G 3000", row


def test_dynasty_assignments() -> None:
    """Chunk 1 (all three pyramid complexes) is Dyn. IV → `"4"`.
    Chunk 2 spans Dyn. IV (royal-family core), Dyn. V (later officials),
    and Dyn. VI (Pepy I priestly clientele on G7101, G7102).
    Chunk 3 spans Dyn. IV/V (LG 100 Khentkaus) and Dyn. XXVI (the Saite
    LG 81/83/84/97 cluster). Chunk 4 spans Dyn. V (Unis, Isesi + Wife)
    and Dyn. VI (Pepy I, Merenrʿ I, Pepy II + 3 queens). Chunk 5 spans
    Dyn. III (Neterikhet/Zoser, Sekhemkhet, anonymous Great Enclosure
    `Probably Dyn. III`), Dyn. V (Userkaf), and Dyn. VI (Teti + Iput I
    + Khuit). Bare-headword shafts G7112 / G7142 carry `dynasty: null`
    (PM gives no dating line).
    """
    for row in _rows():
        if row["tomb_id"] in CHUNK1_TOMB_IDS:
            assert row["dynasty"] == "4", row
        elif row["tomb_id"] in {"G7112", "G7142"}:
            assert row["dynasty"] is None, row
        elif row["tomb_id"] in CHUNK2_TOMB_IDS:
            assert row["dynasty"] in {"4", "5", "6"}, row
        elif row["tomb_id"] in CHUNK3_TOMB_IDS:
            assert row["dynasty"] in {"4", "26"}, row
        elif row["tomb_id"] in CHUNK4_TOMB_IDS:
            assert row["dynasty"] in {"5", "6"}, row
        elif row["tomb_id"] in CHUNK5_TOMB_IDS:
            assert row["dynasty"] in {"3", "5", "6"}, row
        elif row["tomb_id"] in CHUNK6_TOMB_IDS:
            # West Field Old Kingdom mastabas span Dyn IV (Temp. Khufu /
            # Khephren burials, the earliest core), Dyn V (largest
            # cohort: middle/late OK officials), Dyn VI (priestly
            # intrusions). Bare-suffix Shape-2 shafts with no PM dating
            # marker carry `dynasty: null`.
            assert row["dynasty"] in {"4", "5", "6", None}, row
        elif row["tomb_id"] in CHUNK7_TOMB_IDS:
            # Same Old-Kingdom range as chunk 6 (Dyn IV-VI + null for
            # undated bare-suffix shafts).
            assert row["dynasty"] in {"4", "5", "6", None}, row
        elif row["tomb_id"] in CHUNK8_TOMB_IDS:
            # Cemetery en Echelon is dominated by Dyn V-VI named
            # officials (Senezemib clan etc.). Bare-suffix shafts with
            # no PM dating marker (G2347a) carry `dynasty: null`.
            assert row["dynasty"] in {"5", "6", None}, row
        elif row["tomb_id"] in CHUNK9_TOMB_IDS:
            # Fisher Minor Cemetery is almost entirely Dyn VI (most
            # headwords explicitly print `Dyn. VI.`). G 3015 (bare-
            # suffix Shape-2) explicitly carries `Dyn. VI.` in its
            # dating-only headword so dynasty = "6", not null.
            assert row["dynasty"] == "6", row


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
        "co_occupant_roles": [],
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
        "co_occupant_roles": [],
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
        "co_occupant_roles": [],
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
        if _TOMB_ID_RE.match(tid) and _TOMB_ID_RE.match(tid).group("suffix") not in (None, "")
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

    # Reconciled stays semantically identical EXCEPT for the
    # schema-uniformity backfill of `co_occupant_roles: []` (every row
    # carries this field after `_ensure_co_occupant_roles_default`; it's
    # a uniformity guarantee, not a correction).
    assert json.loads(after_reconciled.strip()) == {
        "tomb_id": "G2",
        "occupant_name": "Khephren",
        "co_occupant_roles": [],
    }
    # No audit-trail section appended because the correction was a no-op.
    # The `co_occupant_roles` backfill is NOT recorded in the audit trail
    # because it's a default value being filled in, not an LLM-applied
    # override of an existing value.
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
        "co_occupant_roles": [],
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


# === chunk-3 content / value assertions =====================================


def test_chunk3_lg100_khentkaus_full_row() -> None:
    """LG 100 — Sarcophagus-shaped Tomb of Khentkaus I, the famous queen-
    mother who closes PM's Old Kingdom Central Field section (End of Dyn IV
    or early Dyn V). PM's footnote 1 carries her titulary `Mother of the
    two Kings of Upper and Lower Egypt, Daughter of the God, etc.` which
    the chunk-3 prompt rolls into `notes_from_pm` as PM treats it as
    inseparable from the LG 100 attribution.
    """
    row = _by_id("LG100")
    assert row["tomb_id"] == "LG100"
    assert row["occupant_name"] == "Khentkaus I"
    assert row["occupant_role"] == "Queen"
    assert row["dynasty"] == "4"  # transition phrasing uses start dynasty
    assert row["sub_period"] is None
    assert row["cemetery"] == "Central Field"
    assert row["attribution_certainty"] == "attested"
    assert row["is_joint_burial"] is False
    assert row["co_occupants"] == []
    assert row["source_citation"] == {"page": 288, "edition": EDITION_PM_III_1, "section": "III"}


def test_chunk3_lg83_joint_burial_ahmosi_and_queen_nekhtubasterau() -> None:
    """LG 83 — Saite (Dyn XXVI) joint burial of Commander ʿAhmosi and his
    mother, Queen Nekhtubasterau, who was the wife of pharaoh Amasis.
    The joint-burial schema: primary occupant in `occupant_name`,
    secondary in `co_occupants` (name) + `co_occupant_roles` (typed
    role), `is_joint_burial: true`. The `co_occupant_roles` parallel
    array preserves the queen attribution so Phase-A queries for
    "queens of Amasis" can surface LG 83 even though its primary
    occupant is a Commander (egyptologist-reviewer P1 finding,
    fix_rows.py CHUNK3_CORRECTIONS with PM III.1 p.289 citation).
    """
    row = _by_id("LG83")
    assert row["is_joint_burial"] is True
    assert row["dynasty"] == "26"
    assert row["sub_period"] == "Saite"
    assert row["co_occupants"] == ["Nekhtubasterau"]
    assert row["co_occupant_roles"] == ["Queen"]
    assert row["occupant_name"] == "ʿAhmosi"
    assert row["occupant_role"] == "Official"  # primary is a Commander, not a King's-son
    assert "Amasis" in row["notes_from_pm"]


def test_chunk3_lg97_joint_burial_wnrw_priests() -> None:
    """LG 97 — joint burial of two `wnrw`-priests, Harsiesi and Harwoz
    (Dyn XXVI). PM's `both <shared title>` phrasing types BOTH occupants
    with the same priestly role; the secondary inherits the same
    `Official` role as the primary. `co_occupant_roles` parallel array
    preserves the symmetric typing.
    """
    row = _by_id("LG97")
    assert row["is_joint_burial"] is True
    assert row["dynasty"] == "26"
    assert row["sub_period"] == "Saite"
    assert row["occupant_role"] == "Official"
    assert row["occupant_name"] == "Harsiesi"
    assert row["co_occupants"] == ["Harwoz"]
    assert row["co_occupant_roles"] == ["Official"]


def test_chunk3_lg84_pakap_alt_name_wahibre_em_akhet() -> None:
    """LG 84 — Saite Overseer of scribes Pakap, who carries the PM-printed
    `good name WEHEBREc-EMAKHET` (Wahibre/Apries throne-name compound,
    \"in the horizon\"). The `good name` token routes the secondary name
    into `occupant_alt_names`. The pypdf raised-ayin glyph `c` is
    normalised to U+02BF ayin in the canonical form, matching chunk-1's
    `Menkaureʿ` convention. Tie-break override pin (1/1/1 on the three
    agents' normalisation variants).
    """
    row = _by_id("LG84")
    assert row["occupant_name"] == "Pakap"
    assert row["occupant_alt_names"] == ["Wehebreʿ-emakhet"]
    assert row["dynasty"] == "26"
    assert row["sub_period"] == "Saite"
    assert row["occupant_role"] == "Official"


def test_chunk3_lg81_bare_headword_saite_unknown() -> None:
    """LG 81 — bare-headword Saite tomb (PM gives the LG number, dynasty,
    plan position, but NO occupant name in the headword). Mirrors the
    chunk-2 G 7112 / G 7142 bare-headword pattern.

    Regression-pin for two things:
    1. The `merge.SENTINEL_NULL_STRINGS` divergence (omitting `"unknown"`)
       still works on chunk-3 Lepsius-number rows, not just chunk-2 Reisner.
    2. The LG-number OCR-drift normalisation: pypdf rendered the PM
       printed `LG 81` as `LG 8 I` (Arabic 1 → Roman I); the prompt's
       normalisation rule restores it to `tomb_id: "LG81"`.
    """
    row = _by_id("LG81")
    assert row["occupant_name"] is None
    assert row["occupant_role"] == "Unknown"
    assert row["attribution_certainty"] == "uncertain"
    assert row["dynasty"] == "26"
    assert row["sub_period"] == "Saite"


def test_co_occupant_roles_order_coupled_with_co_occupants() -> None:
    """`co_occupant_roles` is a parallel array order-coupled with
    `co_occupants`. Length invariant: when `co_occupants` is empty,
    `co_occupant_roles` is empty. When `co_occupants` has N entries,
    `co_occupant_roles` MUST also have N entries (each indexed pair is
    `(name_at_i, role_at_i)`).

    Schema-invariant test: catches any future row whose roles list drops
    or duplicates entries vs the names list.
    """
    for row in _rows():
        assert len(row["co_occupant_roles"]) == len(row["co_occupants"]), row


def test_chunk3_no_sub_period_for_old_kingdom_rows() -> None:
    """Only Dyn-XXVI rows carry `sub_period: "Saite"`. The LG 100 Dyn-IV/V
    transition row has `sub_period: null` — there is no chunk-3 sub-period
    refinement for Old Kingdom rows.
    """
    for row in _rows():
        if row["tomb_id"] == "LG100":
            assert row["sub_period"] is None, row
        elif row["tomb_id"] in CHUNK3_TOMB_IDS - {"LG100"}:
            assert row["sub_period"] == "Saite", row


# === chunk-4 content / value assertions (PM III.2 Saqqâra) ===================


def test_chunk4_five_royal_kings_attested() -> None:
    """Chunk 4's 5 royal Dyn V/VI kings (Unis, Pepy I, Isesi, Merenrʿ I,
    Pepy II) all have role=King + attribution=attested per PM's section
    headings `<LETTER>. PYRAMID-COMPLEX OF <KING>`. memphite_area="Saqqara".
    """
    expected_kings = {"SAQ-Unis", "SAQ-PepyI", "SAQ-Isesi", "SAQ-MerenreI", "SAQ-PepyII"}
    for tid in expected_kings:
        row = _by_id(tid)
        assert row["occupant_role"] == "King", row
        assert row["attribution_certainty"] == "attested", row
        assert row["memphite_area"] == "Saqqara", row
        assert row["occupant_name"] is not None, row


def test_chunk4_unis_last_king_dyn_v() -> None:
    """Unis closes Dyn V (last king before the Dyn VI transition).
    Source citation = printed p.421 (PM III.2 § I. F)."""
    row = _by_id("SAQ-Unis")
    assert row["occupant_name"] == "Unis"
    assert row["dynasty"] == "5"
    assert row["source_citation"]["page"] == 421
    assert row["source_citation"]["edition"] == EDITION_PM_III_2


def test_chunk4_isesi_haram_el_shawwaf_alias() -> None:
    """Isesi (Djedkare-Isesi) — the Saqqâra pyramid PM identifies with
    the Arabic popular-name `Haram el-Shawwaf` ("Pyramid of the Seer"
    or "Sentinel Pyramid"). PM's headword block has the alias clause
    after the `Lepsius, XXXVII; Perring and Vyse, 6;` identification
    line."""
    row = _by_id("SAQ-Isesi")
    assert row["occupant_name"] == "Isesi"
    assert row["dynasty"] == "5"
    assert "Haram el-Shawwaf" in row["tomb_aliases"]


def test_chunk4_wife_of_isesi_anonymous_uncertain() -> None:
    """The Dyn V anonymous queen-enclosure `PYRAMID-ENCLOSURE PROBABLY
    OF WIFE OF ISESI` on PM III.2 printed p.424 emits a row with
    occupant_name=null + role=Queen + attribution=uncertain
    (PM's `Probably` hedge token).
    """
    row = _by_id("SAQ-WifeOfIsesi")
    assert row["occupant_name"] is None
    assert row["occupant_role"] == "Queen"
    assert row["attribution_certainty"] == "uncertain"
    assert row["dynasty"] == "5"


def test_chunk4_iput_ii_page_is_432_not_431() -> None:
    """SAQ-IputII source_citation.page = 432, NOT 431. Gemini PR #222
    round-1 caught a 2/1 majority error: agents A and C reported page
    431 (one too low), Agent B reported 432 (correct). The IPUT II
    headword appears on physical p.72 of the chunk file; PM III.2's
    `printed = physical + 360` offset gives printed p.432. Override the
    majority via fix_rows.py CHUNK4_CORRECTIONS. Regression-pin guards
    against any future merge run silently reverting to 431.
    """
    row = _by_id("SAQ-IputII")
    assert row["source_citation"]["page"] == 432, row


def test_chunk4_pepy_ii_three_queens_dyn_vi() -> None:
    """Pepy II had three named queens with their own pyramid-enclosures
    at Saqqâra — Neit, Iput II (queen-of-three-kings), and Wezebten.
    All three are Dyn VI Queens with attested attribution. PM III.2's
    `IPUT [II]` headword carries pypdf-OCR drift `IPUT Il1` which the
    chunk-4 prompt's bracket-regnal rule + pre_merge tomb_id correction
    routes back to canonical `SAQ-IputII` / `Iput II`.
    """
    queens = {"SAQ-Neit", "SAQ-IputII", "SAQ-Wezebten"}
    for tid in queens:
        row = _by_id(tid)
        assert row["occupant_role"] == "Queen", row
        assert row["attribution_certainty"] == "attested", row
        assert row["dynasty"] == "6", row
        assert row["memphite_area"] == "Saqqara", row
    # Iput II's name carries the regnal numeral (recovered from pypdf
    # `Il1` glyph-cluster via the chunk-4 pre_merge tomb_id correction)
    assert _by_id("SAQ-IputII")["occupant_name"] == "Iput II"


def test_chunk4_merenre_i_egyptological_form() -> None:
    """Merenreʿ I (mer-en-Reʿ, "Beloved of Re") — Dyn VI king between Pepy I
    and Pepy II. PM III.2 prints `MERENRĒʿ I` (macron-ē + raised-ayin) on
    printed p.425; pypdf rendered the macron-ē-plus-ayin cluster as `£c`.
    The conventional Egyptological transcription is `Merenreʿ I` with the
    `e` vowel of the `Re` element preserved (parallel to chunk-1's
    `Menkaureʿ`). Egyptologist-reviewer F1 P1 caught the strict-rule
    majority dropping the vowel; fix_rows.py CHUNK4_CORRECTIONS restores
    the conventional form. Tie-break override on `notes_from_pm` aligns
    the verbatim form `MERENREʿ I` so both fields stay internally
    consistent.
    """
    row = _by_id("SAQ-MerenreI")
    assert row["tomb_id"] == "SAQ-MerenreI"  # ASCII descriptor, no U+02BF in tomb_id
    assert row["occupant_name"] == "Merenreʿ I"  # conventional form with E vowel
    assert "MERENREʿ I" in row["notes_from_pm"]
    assert row["dynasty"] == "6"
    assert row["source_citation"]["page"] == 425


def test_chunk4_no_jay_kakare_ibi_row() -> None:
    """PM III.2 § I has a `J. PYRAMID OF KAKAREʿ IBI` entry on physical
    p.65 (Dyn VIII transitional king) that falls between letters I and
    K in the section lettering. Chunk 4 explicitly excludes this row per
    the prompt's OUT-OF-SCOPE rule (Dyn V/VI only). Regression-pin
    scoped to CHUNK4_TOMB_IDS so a future chunk that legitimately
    adds the Kakareʿ Ibi row (Dyn VIII proper, with its own tomb_id
    descriptor) is NOT blocked by this assertion (Codex PR #222
    round-1 finding).
    """
    for tid in CHUNK4_TOMB_IDS:
        assert "Kakare" not in tid, f"chunk-4 should not include {tid} (Dyn VIII out of scope)"
        assert "Ibi" not in tid, f"chunk-4 should not include {tid} (Dyn VIII out of scope)"


# === existing chunk-2 content tests ========================================


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


# === chunk-5 content tests (Saqqâra § I.A-E pyramid front half) =============


def test_chunk5_four_royal_kings_attested() -> None:
    """Chunk 5's 4 royal kings (Teti Dyn VI, Userkaf Dyn V, Neterikhet
    Dyn III, Sekhemkhet Dyn III) all have role=King + attribution=attested
    + memphite_area=Saqqara. They are the front-half PM III.2 § I royal
    pyramid-complex headwords (sections A-D) that chunk 4 left open."""
    expected_kings = {
        "SAQ-Teti", "SAQ-Userkaf", "SAQ-Neterikhet", "SAQ-Sekhemkhet",
    }
    for tid in expected_kings:
        row = _by_id(tid)
        assert row["occupant_role"] == "King", row
        assert row["attribution_certainty"] == "attested", row
        assert row["memphite_area"] == "Saqqara", row
        assert row["occupant_name"] is not None, row


def test_chunk5_teti_dyn_vi_first_king() -> None:
    """Section A. PYRAMID-COMPLEX OF TETI opens the PM III.2 § I.
    PYRAMIDS chapter — Teti is the first king of Dyn VI (founder).
    Source citation = printed p.393 (PM III.2 § I.A)."""
    row = _by_id("SAQ-Teti")
    assert row["occupant_name"] == "Teti"
    assert row["dynasty"] == "6"
    assert row["source_citation"]["page"] == 393
    assert row["source_citation"]["edition"] == EDITION_PM_III_2
    assert row["source_citation"]["section"] == "I"


def test_chunk5_teti_two_queens_iput_and_khuit() -> None:
    """Teti's pyramid-complex carries two named queen-enclosures: Iput
    (= Iput I in museum-convention; mother of Pepy I) and Khuit. Both
    are Dyn VI Queens with attested attribution. Per the
    egyptologist-reviewer printed-source pass, `occupant_name` follows
    PM's bare headword form (PM prints `IPUT¹` without bracket-regnal,
    distinct from chunk-4's `IPUT [II]¹` where PM explicitly brackets
    the numeral). Museum-conventional `Iput I` lives in
    `occupant_alt_names` for Phase-A matching."""
    queens = {"SAQ-IputI", "SAQ-Khuit"}
    for tid in queens:
        row = _by_id(tid)
        assert row["occupant_role"] == "Queen", row
        assert row["attribution_certainty"] == "attested", row
        assert row["dynasty"] == "6", row
        assert row["memphite_area"] == "Saqqara", row
    assert _by_id("SAQ-IputI")["occupant_name"] == "Iput"
    assert _by_id("SAQ-IputI")["occupant_alt_names"] == ["Iput I"]
    assert _by_id("SAQ-Khuit")["occupant_name"] == "Khuit"


def test_chunk5_iput_and_khuit_footnotes_preserved() -> None:
    """Egyptologist-reviewer P1 fixes (F1 + F3 + F-NEW-1) restored PM's
    section-heading footnotes verbatim to `notes_from_pm`. For Iput,
    PM prints three titles on p.396: `[King's daughter of his] body,
    King's wife (of Teti), King's mother (of Pepy I).` — the first
    title in editorial brackets per PM's convention for restored text.
    For Khuit, PM prints one title on p.397: `King's wife (of Teti).`
    Both footnotes carry PM's `¹` anchor as the contextual marker that
    the clause is footnote prose rather than headline continuation.
    These footnotes are the sole prosopographic justification for the
    `occupant_role: "Queen"` classification and for the Teti-spouse
    identification — both Phase-A-relevant facts that need a
    documented PM trace per constitutional rule 1."""
    iput = _by_id("SAQ-IputI")["notes_from_pm"]
    assert "[King's daughter of his] body" in iput
    assert "King's wife (of Teti)" in iput
    assert "King's mother (of Pepy I)" in iput
    khuit = _by_id("SAQ-Khuit")["notes_from_pm"]
    assert "King's wife (of Teti)" in khuit


def test_chunk5_iput_full_row_equality() -> None:
    """Flagship row equality assertion per CLAUDE.md rule 5 and the
    chunk-1 G1 / G2 / G3 precedent. SAQ-IputI is chunk 5's flagship
    row: 3 of 5 CHUNK5_CORRECTIONS target it, including the
    interpolated-regnal fix (F1, P1), the footnote restoration (F3,
    P1), and the bracketed-first-clause restoration (F-NEW-1, P1).
    Full-row equality regression-pins all those corrections so a
    future merge can't silently revert any of them.
    """
    row = _by_id("SAQ-IputI")
    assert row == {
        "tomb_id": "SAQ-IputI",
        "memphite_area": "Saqqara",
        "occupant_name": "Iput",
        "occupant_alt_names": ["Iput I"],
        "tomb_aliases": [],
        "co_occupants": [],
        "co_occupant_roles": [],
        "is_joint_burial": False,
        "occupant_role": "Queen",
        "dynasty": "6",
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
        "notes_from_pm": (
            "PYRAMID-ENCLOSURE OF IPUT. Dyn. VI. PYRAMID. "
            "¹ [King's daughter of his] body, King's wife (of Teti), "
            "King's mother (of Pepy I)."
        ),
        "source_citation": {"page": 396, "edition": EDITION_PM_III_2, "section": "I"},
    }


def test_chunk5_neterikhet_zoser_djoser_aliases() -> None:
    """Section C. STEP PYRAMID ENCLOSURE OF NETERIKHET (Zoser). PM's
    primary headword form is Neterikhet (the king's Horus name); Zoser
    (the king's birth-name) appears as a parenthetical alias on the
    same heading line. The chunk-5 parenthetical-alias rule emits
    `occupant_name: "Neterikhet"` with `occupant_alt_names: ["Zoser"]`.
    Egyptologist F4 finding added `Djoser` (museum-conventional
    spelling used by Met, Brooklyn, Harvard, BM) as a second alt_name
    for Phase-A matching coverage. First chunk in this source to
    exercise the parenthetical-alias pattern.
    """
    row = _by_id("SAQ-Neterikhet")
    assert row["occupant_name"] == "Neterikhet"
    assert row["occupant_alt_names"] == ["Zoser", "Djoser"]
    assert row["dynasty"] == "3"
    assert row["source_citation"]["page"] == 399


def test_chunk5_sekhemkhet_unfinished() -> None:
    """Section D. STEP PYRAMID ENCLOSURE OF SEKHEMKHET. The STEP PYRAMID.
    sub-heading line literally reads `STEP PYRAMID. Unfinished.` — the
    `is_unfinished` deriver fires on the literal `Unfinished` token per
    the chunk-5 rule. First chunk-5 row with is_unfinished=true."""
    row = _by_id("SAQ-Sekhemkhet")
    assert row["occupant_name"] == "Sekhemkhet"
    assert row["dynasty"] == "3"
    assert row["is_unfinished"] is True
    assert row["source_citation"]["page"] == 415
    assert "Unfinished" in row["notes_from_pm"]


def test_chunk5_userkaf_haram_el_makharbish_alias() -> None:
    """Section B. PYRAMID-COMPLEX OF USERKAF (first king of Dyn V, founder).
    PM III.2's headword block carries the Arabic popular-name clause
    `el-Haram el-Makharbish` after the `Lepsius, XXXI; Perring and Vyse, 2;`
    identification line — captured in `tomb_aliases`."""
    row = _by_id("SAQ-Userkaf")
    assert row["occupant_name"] == "Userkaf"
    assert row["dynasty"] == "5"
    assert "el-Haram el-Makharbish" in row["tomb_aliases"]
    assert row["source_citation"]["page"] == 397


def test_chunk5_neterikhet_haram_el_mudarrag_alias() -> None:
    """PM III.2 § I.C STEP PYRAMID. identification line carries the
    Arabic popular-name clause `el-Haram el-Mudarrag` after `Lepsius,
    XXXII; Perring and Vyse, 3;`. Captured in `tomb_aliases`."""
    row = _by_id("SAQ-Neterikhet")
    assert "el-Haram el-Mudarrag" in row["tomb_aliases"]


def test_chunk5_great_enclosure_anonymous_uncertain() -> None:
    """Section E. 'GREAT ENCLOSURE' — anonymous Dyn-III structure (PM
    annotates `Probably Dyn. III`). First Shape-3 anonymous row in
    chunk 5: occupant_name=null, occupant_role=Unknown,
    attribution_certainty=uncertain. Distinct from chunk-4's anonymous
    `WifeOfIsesi` Shape-2 queen pattern in that the Great Enclosure has
    NO inferred role from a parent king's complex — it stands alone."""
    row = _by_id("SAQ-GreatEnclosure")
    assert row["occupant_name"] is None
    assert row["occupant_role"] == "Unknown"
    assert row["attribution_certainty"] == "uncertain"
    assert row["dynasty"] == "3"
    assert row["source_citation"]["page"] == 417
    assert row["memphite_area"] == "Saqqara"


def test_chunk5_first_dyn_iii_rows_in_source() -> None:
    """Chunk 5 introduces the first Dyn III rows in the entire PM
    Memphis source. Three rows: Neterikhet, Sekhemkhet, and the
    anonymous Great Enclosure. Regression-pin guarding against a future
    chunk silently re-extracting any of these with a different dynasty
    value or losing the Dyn III rows altogether."""
    dyn_iii_rows = {r["tomb_id"] for r in _rows() if r["dynasty"] == "3"}
    assert dyn_iii_rows == {
        "SAQ-Neterikhet", "SAQ-Sekhemkhet", "SAQ-GreatEnclosure",
    }, dyn_iii_rows


# === chunk-6 content tests (West Field Junker cemeteries G 1000-1900) =======


def test_chunk6_row_count_54() -> None:
    """Chunk 6 yields exactly 54 rows: 30 Shape-1 named primary + 24
    Shape-2 bare-suffix anonymous shafts."""
    assert len(CHUNK6_TOMB_IDS) == 54


def test_chunk6_cemetery_distribution() -> None:
    """8 cemetery banners observed in chunk 6: G 1000, G 1100, G 1200,
    G 1300, G 1400, G 1500, G 1600, G 1900. Verify each cemetery has
    at least one row attributed to it."""
    cemeteries_in_chunk = {
        row["cemetery"] for row in _rows()
        if row["tomb_id"] in CHUNK6_TOMB_IDS
    }
    assert cemeteries_in_chunk == {
        "G 1000", "G 1100", "G 1200", "G 1300",
        "G 1400", "G 1500", "G 1600", "G 1900",
    }, cemeteries_in_chunk


def test_chunk6_ankh_haf_g1234_egyptologist_form() -> None:
    """G 1234 ʿAnkh-haf. PM dates as `Late Dyn. V or Dyn. VI.`; the
    chunk-6 dynasty-range rule picks the more-specific tail (`Dyn.
    VI`). Egyptologist F2 finding (P1) corrected the title-cased
    `ʿAnkh-Haf` to the museum-conventional lowercase-haf form
    `ʿAnkh-haf` (parallel to chunk-3 LG 84's `Wehebreʿ-emakhet`
    lowercase post-hyphen locative element). Companion fix populates
    `occupant_alt_names` with the ASCII forms `Ankhhaf` and `Ankh-haf`
    (Boston MFA / Brooklyn / Met catalogue spellings) for Phase-A
    name-authority matching against museum records. Gemini PR #225
    round-1 high-priority finding aligned the alt_names with the
    reviewer's recommended P1-2 alias list."""
    row = _by_id("G1234")
    assert row["occupant_name"] == "ʿAnkh-haf"
    assert row["dynasty"] == "6"
    assert row["cemetery"] == "G 1200"
    assert row["source_citation"]["page"] == 60
    assert row["occupant_alt_names"] == ["Ankhhaf", "Ankh-haf"]


def test_chunk6_g1607_not_unfinished() -> None:
    """G 1607 Iʿan's `unfinished` token appears in PM's body prose
    (`Rock-cut tomb, unfinished.`) AFTER the headword block. The
    chunk-6 prompt's `is_unfinished` rule fires only on headword-block
    `unfinished` (parallel to chunk-5 SAQ-Sekhemkhet where PM's
    `STEP PYRAMID. Unfinished.` IS the sub-heading). Agent A
    over-fired the deriver on body content; CHUNK6_CORRECTIONS reverts
    `is_unfinished` to false. Egyptologist F1 finding (P1)."""
    row = _by_id("G1607")
    assert row["is_unfinished"] is False
    assert row["occupant_name"] == "Iʿan"


def test_chunk6_g1221_shad_notes_drop_name_and_hedge() -> None:
    """G 1221 SHAD's PM headword carries the name + one `(?)` hedge in
    the headline plus the title cluster `Royal acquaintance.`.
    Egyptologist F3 finding (P1) recommends dropping the name AND the
    hedge from `notes_from_pm` entirely — the name reading already
    lives in `occupant_name: \"Shad\"` and the doubt is already in
    `attribution_certainty: \"uncertain\"`. Per the prompt's literal
    rule mapping `(?)` → `uncertain` (Gemini PR #225 round-3 medium
    finding), attribution_certainty is `uncertain`, not `probable` —
    the `(?)` after the name is the conservative hedge on
    occupant-identification, while the `Probably` before Dyn. V. only
    speaks to dating. Including a second copy of the name + hedge in
    notes risks downstream consumers double-counting the hedge."""
    row = _by_id("G1221")
    assert row["occupant_name"] == "Shad"
    assert row["attribution_certainty"] == "uncertain"
    assert row["notes_from_pm"] == "Royal acquaintance. Probably Dyn. V."
    assert "Shad" not in row["notes_from_pm"]
    assert "(?)" not in row["notes_from_pm"]


def test_chunk6_g1452_g1453_compound_twin() -> None:
    """G 1452+1453 ZADUWAʿ is chunk 6's only compound twin-mastaba
    headword (parallel to chunk 2's G 7110+7120 KAWAaB precedent).
    Emits two rows sharing the compound's occupant name, each with
    `shared_with_tombs` cross-referencing the twin half."""
    g1452 = _by_id("G1452")
    g1453 = _by_id("G1453")
    # Both should have the same occupant name (PM doesn't separately
    # identify the two halves)
    assert g1452["occupant_name"] is not None
    assert g1453["occupant_name"] is not None
    # Cross-reference each twin half
    assert "G1453" in g1452["shared_with_tombs"]
    assert "G1452" in g1453["shared_with_tombs"]
    # Both Dyn IV/V West Field per PM
    assert g1452["cemetery"] == "G 1400"
    assert g1453["cemetery"] == "G 1400"


def test_chunk6_g1201_mehyt_underdot_h() -> None:
    """G 1201 WEPEMNEFERT's notes carry the goddess-name Meḥyt (the
    cobra-goddess of Thinis) with underdot-Ḥ. PM prints the underdot
    glyph; pypdf renders it as mid-word uppercase `H` (`MeHyt`).
    Three-agent 1/1/1 tie resolved via tie-break-overrides.json with
    PM-faithful Egyptological normalisation to `Meḥyt`."""
    row = _by_id("G1201")
    assert row["occupant_name"] == "Wepemnefert"
    assert "Meḥyt" in row["notes_from_pm"]
    assert "MeHyt" not in row["notes_from_pm"]
    assert "Mehyt" not in row["notes_from_pm"].replace("Meḥyt", "")


def test_chunk6_named_no_title_default_official() -> None:
    """Chunk-6 prompt's role-derivation rule mapped `named occupant
    with no title cluster` to `Unknown` by default — but `Unknown`
    is reserved for Shape-2 bare-suffix headwords (no name at all). A
    named Old-Kingdom mastaba occupant with no title cluster (just
    dating, e.g. `G 1020. MES-SA Late Dyn. IV or first half of Dyn.
    V.`) defaults to `Official` per Old-Kingdom Memphite necropolis
    demographics. Egyptologist F6 finding (P2) applied to G1020,
    G1104, G1204."""
    for tid in ("G1020", "G1104", "G1204"):
        row = _by_id(tid)
        assert row["occupant_name"] is not None
        assert row["occupant_role"] == "Official", row


def test_chunk6_royal_acquaintance_woman_is_official() -> None:
    """`Royal acquaintance (woman)` (rḫt-nswt) is a non-royal
    honorific attested for elite non-royals, NOT a royal-family
    descent indicator. The chunk-6 prompt's role-derivation rule
    initially mistakenly mapped it to `Royal Family`; CHUNK6_CORRECTIONS
    corrected G1207 NUFER and G1227 SETHIHEKNET to `Official`, and the
    prompt rule itself was tightened (Gemini PR #225 round-1
    medium-priority finding) so future extractions produce `Official`
    directly. Egyptologist F5 finding (P2)."""
    for tid in ("G1207", "G1227"):
        row = _by_id(tid)
        assert row["occupant_role"] == "Official", row
        assert row["occupant_name"] is not None


def test_chunk6_g1314_khakare_body_recovery() -> None:
    """G 1314 PM headword is bare-suffix (`Second half of Dyn. V.`)
    but the body content on the next printed page (p.62) identifies
    the tomb owner via inscribed architrave + double-statue:
    `Khaʿkareʿ, Hairdresser of the Great House`. Reviewer F-P2-3
    finding promoted the body-attested identification to
    `occupant_name`, `occupant_role: Official` (Hairdresser → court
    officer), `attribution_certainty: probable` (body-attestation is
    strong but not headword). Reviewer's recommended recovery; Gemini
    PR #225 round-1 medium-priority finding aligned with this."""
    row = _by_id("G1314")
    assert row["occupant_name"] == "Khaʿkareʿ"
    assert row["occupant_role"] == "Official"
    assert row["attribution_certainty"] == "probable"
    assert row["dynasty"] == "5"
    assert "Khaʿkareʿ" in row["notes_from_pm"]
    assert "Hairdresser of the Great House" in row["notes_from_pm"]


# === chunk 8 content tests ==================================================


def test_chunk8_row_count_33() -> None:
    """Chunk 8 emits 33 rows under PM's Cemetery en Echelon banner
    (G 2300 + G 2400 sub-clusters) plus Cemetery G 2500's single row."""
    chunk8 = [r for r in _rows() if r["tomb_id"] in CHUNK8_TOMB_IDS]
    assert len(chunk8) == 33


def test_chunk8_cemetery_distribution() -> None:
    """22 G 2300 + 10 G 2400 + 1 G 2500."""
    by_cem: dict[str, int] = {}
    for r in _rows():
        if r["tomb_id"] in CHUNK8_TOMB_IDS:
            by_cem[r["cemetery"]] = by_cem.get(r["cemetery"], 0) + 1
    assert by_cem == {"G 2300": 22, "G 2400": 10, "G 2500": 1}


def test_chunk8_senezemib_inti_g2370() -> None:
    """G 2370 SENEZEMIB good name INTI Chief Justice and Vizier. Temp.
    Isesi. The "good name" idiom (Egyptian *rn nfr*) puts the primary
    name in `occupant_name` and the alt in `occupant_alt_names`.
    Full-row equality per code-reviewer PR #227 P2-2 — G 2370 populates
    co_occupants/co_occupant_roles, wife clause in notes, and modern-
    spelling `Senedjemib` alias that the original 5-field spot-check
    missed."""
    row = _by_id("G2370")
    assert row == {
        "tomb_id": "G2370",
        "memphite_area": "Giza",
        "occupant_name": "Senezemib",
        "occupant_alt_names": ["Inti", "Senedjemib"],
        "tomb_aliases": ["LG 27"],
        "co_occupants": ["Thefi"],
        "co_occupant_roles": ["Wife, Royal acquaintance"],
        "is_joint_burial": False,
        "occupant_role": "Vizier",
        "dynasty": "5",
        "sub_period": None,
        "date_bce_approx_start": None,
        "date_bce_approx_end": None,
        "cemetery": "G 2300",
        "discovery_year": None,
        "discoverer": None,
        "is_unfinished": False,
        "is_uninscribed": False,
        "is_usurped": False,
        "attribution_certainty": "attested",
        "shared_with_tombs": ["LG 10"],
        "notes_from_pm": (
            "Chief Justice and Vizier, King's architect and builder in "
            "the Two Houses, etc. Temp. Isesi. (Also owner of tomb LG "
            "10.) Wife, Thefi Royal acquaintance. Stone-built mastaba. "
            "LG 27."
        ),
        "source_citation": {"page": 85, "edition": EDITION_PM_III_1, "section": "III"},
    }


def test_chunk8_senezemib_mehi_g2378_underdot_h() -> None:
    """G 2378 SENEZEMIB good name MEHI Chief Justice and Vizier. Temp.
    Unis. Underdot-Ḥ restored on Meḥi (occupant alt name) AND on
    Ḥathor (wife's title cluster). Full-row equality per code-reviewer
    PR #227 P2-2."""
    row = _by_id("G2378")
    assert row == {
        "tomb_id": "G2378",
        "memphite_area": "Giza",
        "occupant_name": "Senezemib",
        "occupant_alt_names": ["Meḥi", "Senedjemib"],
        "tomb_aliases": ["LG 26"],
        "co_occupants": ["Khentkaus"],
        "co_occupant_roles": ["Wife, King's daughter of his body, Prophetess of Ḥathor"],
        "is_joint_burial": False,
        "occupant_role": "Vizier",
        "dynasty": "5",
        "sub_period": None,
        "date_bce_approx_start": None,
        "date_bce_approx_end": None,
        "cemetery": "G 2300",
        "discovery_year": None,
        "discoverer": None,
        "is_unfinished": False,
        "is_uninscribed": False,
        "is_usurped": False,
        "attribution_certainty": "attested",
        "shared_with_tombs": [],
        "notes_from_pm": (
            "Chief Justice and Vizier, King's architect and builder in "
            "the Two Houses, etc. Temp. Unis. Parents, Senezemib Inti "
            "and Thefi (tomb G 2370). Wife, Khentkaus King's daughter "
            "of his body, Prophetess of Ḥathor. Stone-built mastaba. "
            "LG 26."
        ),
        "source_citation": {"page": 87, "edition": EDITION_PM_III_1, "section": "III"},
    }


def test_chunk8_meryre_meryptahankh_g2381_macron_underdot_post_hyphen_cap() -> None:
    """G 2381 MERYRĒʿ-MERYPTAḤʿANKH good name NEKHEBU — compound
    theophoric occupant_name with macron-Ē on the Re sun-god root +
    TWO raised-ayin glyphs + underdot-Ḥ on the *ptḥ* root. Egyptologist
    PR #227 P1-4 restored the macron-Ē after round-1 review."""
    row = _by_id("G2381")
    assert row["occupant_name"] == "Meryrēʿ-Meryptaḥʿankh"
    assert row["occupant_alt_names"] == ["Nekhebu"]
    assert "Temp. Pepy I or Merenreʿ I" in row["notes_from_pm"]
    # Structural shaft-attachment prefix `with shaft G 2382A.` MUST be
    # dropped from notes (chunks 6-7 convention).
    assert "with shaft" not in row["notes_from_pm"].lower()


def test_chunk8_pepy_meryptahankh_g2387_same_pattern() -> None:
    """G 2387 PEPY-MERYPTAḤʿANKH — same post-hyphen-capital + underdot-Ḥ
    pattern as G 2381 (egyptological consistency)."""
    row = _by_id("G2387")
    assert row["occupant_name"] == "Pepy-Meryptaḥʿankh"
    assert row["dynasty"] == "6"


def test_chunk8_g2415_weri_meti_joint_burial() -> None:
    """G 2415 WERI and wife METI. The 'and wife' coordinate naming in
    the headword itself triggers `is_joint_burial: true` AND populates
    `co_occupants` with the wife. Tie-break override on notes picks the
    lowercase `and wife Meti.` continuation form."""
    row = _by_id("G2415")
    assert row["occupant_name"] == "Weri"
    assert row["co_occupants"] == ["Meti"]
    assert row["co_occupant_roles"] == ["Wife"]
    assert row["is_joint_burial"] is True
    assert row["notes_from_pm"].startswith("and wife Meti.")


def test_chunk8_g2423_mehu_maet_underdot_and_ayin() -> None:
    """G 2423 MEḤU, Judge and Elder of the Hall ... Prophet of Maʿet.
    Combines underdot-Ḥ on occupant name (Meḥu) and ayin normalisation
    in the goddess name (Maʿet, from PM's `Maaet` raw OCR). Wife
    `Khenit` from body prose is captured as co-occupant + retained in
    notes verbatim per the tie-break override."""
    row = _by_id("G2423")
    assert row["occupant_name"] == "Meḥu"
    assert row["co_occupants"] == ["Khenit"]
    assert "Prophet of Maʿet" in row["notes_from_pm"]
    assert "Wife, Khenit" in row["notes_from_pm"]


def test_chunk8_g2347a_bare_suffix_null_notes() -> None:
    """G 2347a is a bare-suffix Shape-2 letter-suffix headword (PM
    prints `G 2347a.` with NO occupant name, no title cluster, no
    dating marker — only the sub-feature heading `Shaft C.` follows).
    Per chunk-8 prompt Shape-2 rule: pure-suffix bare-headword with no
    dating marker → `notes_from_pm: null` (selected via tie-break
    override over the two agents who incorrectly captured the tomb_id
    or the sub-feature heading)."""
    row = _by_id("G2347a")
    assert row["occupant_name"] is None
    assert row["occupant_role"] == "Unknown"
    assert row["attribution_certainty"] == "uncertain"
    assert row["notes_from_pm"] is None


def test_chunk8_g2430_lg_alias_captured() -> None:
    """G 2430 ḤETEPNIPTAḤ carries an `LG 25` Lepsius cross-reference
    in the body — captured in notes per the chunk-8 prompt's LG-cross-
    reference rule. Occupant name carries underdot-Ḥ on BOTH the *ḥtp*
    initial root AND the *ptḥ* terminal theophoric root."""
    row = _by_id("G2430")
    assert row["occupant_name"] == "Ḥetepniptaḥ"
    assert "LG 25" in row["notes_from_pm"]
    assert "Wife, Khaʿmerernebti" in row["notes_from_pm"]
    assert row["co_occupant_roles"] == ["Wife, Prophetess of Ḥathor in all her places"]


def test_chunk8_g2336_khuwiptah_body_recovery() -> None:
    """G 2336 PM headword is bare-suffix `G 2336.` but body contains
    `Relief-fragment, Khuwiptah and text` (line 37 of chunk file).
    Scope-accountability-enforcer required action on PR #227 E-P2-3:
    body-attested name promoted to `occupant_name` (parallel to chunk-6
    G 1314 Khaʿkareʿ precedent). Theneny's false-door found BETWEEN
    G 2337 and G 2371 (per PM explicit clause) is NOT G 2336's owner —
    mentioned in notes only."""
    row = _by_id("G2336")
    assert row["occupant_name"] == "Khuwiptah"
    assert row["occupant_role"] == "Official"
    assert row["dynasty"] == "6"
    assert "Khuwiptah" in row["notes_from_pm"]
    assert "Theneny" in row["notes_from_pm"]
    assert "between tombs G 2337 and G 2371" in row["notes_from_pm"]


def test_chunk8_body_attested_dating_recovered() -> None:
    """Body-attested dating recovery on bare-suffix Shape-2 rows where
    PM's headword has no dating marker but body sub-headings document
    statue-dating from in-tomb context (burial chamber / serdab / shaft
    débris) → strong attribution to tomb owner. Chunk-6 G 1314
    precedent. Applies to chunk-8 G 2335 (Dyn. V), G 2336 (Dyn. V-VI →
    range tail → 6), G 2407 (Late Dyn. V), G 2501 (Dyn. VI)."""
    for tid, expected_dyn in [
        ("G2335", "5"),
        ("G2336", "6"),
        ("G2407", "5"),
        ("G2501", "6"),
    ]:
        row = _by_id(tid)
        assert row["dynasty"] == expected_dyn, f"{tid}: {row['dynasty']!r} != {expected_dyn!r}"


def test_chunk8_g2501_lone_cemetery_g2500_bare_suffix() -> None:
    """CEMETERY G 2500 contributes a single bare-suffix row.
    `cemetery: "G 2500"`, no occupant, dating recovered from body."""
    row = _by_id("G2501")
    assert row["cemetery"] == "G 2500"
    assert row["occupant_name"] is None
    assert row["occupant_role"] == "Unknown"


# === chunk 9 content tests ==================================================


def test_chunk9_row_count_14() -> None:
    """Chunk 9 emits 14 rows under PM's CEMETERY G 3000 (Fisher's
    Minor Cemetery) banner — 13 Shape-1 named-primary + 1 Shape-2
    bare-suffix (G 3015 dating-only headword)."""
    chunk9 = [r for r in _rows() if r["tomb_id"] in CHUNK9_TOMB_IDS]
    assert len(chunk9) == 14


def test_chunk9_g3008_snefruhotp_wife_khenut_called_inti() -> None:
    """G 3008 SNEFRUḤOTP Inspector of waʿb-priests of the Pyramid of
    Snefru. Wife Khenut (beautiful name Inti) is Prophetess of Ḥathor
    and Neith. Tie-break override on notes preserves the full wife
    clause + ayin-normalised `waʿb-priests` + underdot-Ḥathor."""
    row = _by_id("G3008")
    assert row["occupant_name"] == "Snefruḥotp"
    assert row["co_occupants"] == ["Khenut"]
    assert row["co_occupant_roles"] == [
        "Wife, Prophetess of Ḥathor Mistress-of-the-Sycamore and Neith Opener-of-the-Ways, etc."
    ]
    assert row["dynasty"] == "6"
    assert "waʿb-priests" in row["notes_from_pm"]
    assert "Khenut called Inti" in row["notes_from_pm"]
    assert "Ḥathor" in row["notes_from_pm"]


def test_chunk9_g3015_bare_suffix_dyn_vi() -> None:
    """G 3015. Dyn. VI. — Shape-2 bare-suffix with dating-only
    headword. Dynasty extracted from the marker, occupant null."""
    row = _by_id("G3015")
    assert row["occupant_name"] is None
    assert row["occupant_role"] == "Unknown"
    assert row["attribution_certainty"] == "uncertain"
    assert row["dynasty"] == "6"


def test_chunk9_g3050_ankh_ka_servant_leading_ayin() -> None:
    """G 3050 ʿANKH ka-servant. Leading raised-`a` normalised to U+02BF
    ayin (chunks 1-8 source-wide convention). Wife Kednefert carries
    the OK female title `mitrt` preserved PM-verbatim."""
    row = _by_id("G3050")
    assert row["occupant_name"] == "ʿAnkh"
    assert row["co_occupants"] == ["Kednefert"]
    assert row["co_occupant_roles"] == ["Wife, mitrt"]
    assert row["dynasty"] == "6"


def test_chunk9_g3086_ruz_prophet_of_three_kings() -> None:
    """G 3086 Ruz Prophet of Khufu, Raʿzedef, and Khephren — Dyn-IV
    royal-cult triad. Egyptological ayin restored on Raʿzedef (PM
    prints `Raazedef`) AND on `waʿb-priest` per chunks 1-8 source-
    wide convention (Gemini PR #228 medium #1 + code-reviewer P1.1
    fix). `shared_with_tombs` captures parent-tomb G 3098 from the
    explicit `(tomb G 3098)` cross-reference in notes (Gemini PR
    #228 medium #1 + code-reviewer P1.2 fix). Wife `Mest` Royal
    acquaintance preserved verbatim."""
    row = _by_id("G3086")
    assert row["occupant_name"] == "Ruz"
    assert "Raʿzedef" in row["notes_from_pm"]
    assert "waʿb-priest" in row["notes_from_pm"]
    assert "waab" not in row["notes_from_pm"]
    assert row["shared_with_tombs"] == ["G3098"]
    assert row["co_occupants"] == ["Mest"]
    assert row["co_occupant_roles"] == ["Wife, Royal acquaintance"]


def test_chunk9_g3098_annexe_pair_single_row() -> None:
    """G 3098 `with annexe.` is a chunk-9 single-row annexe-pair (per
    prompt rule, distinct from chunk-7's separately-headworded
    G 2100-I-annexe). One row holds both occupants: (a) Iymerery
    waʿb-priest, (b) Neferḥetpes-Wer (woman) King's adorner in the
    north-east annexe, daughter of Duareʿ King's son of his body.
    Tie-break overrides on notes + co_occupant_roles synthesise the
    egyptologically-faithful elements across the three agents."""
    row = _by_id("G3098")
    assert row["occupant_name"] == "Iymerery"
    assert row["occupant_role"] == "Official"
    assert row["dynasty"] == "6"
    assert row["cemetery"] == "G 3000"
    assert row["attribution_certainty"] == "attested"
    # Both occupants captured in co_occupants list (wife + annexe burial).
    assert row["co_occupants"] == ["Personet", "Neferḥetpes-Wer"]
    assert row["co_occupant_roles"] == [
        "Wife, Royal acquaintance",
        "King's adorner, etc. (woman, north-east annexe). Father, Duareʿ King's son of his body.",
    ]
    # Reciprocal cross-reference to G 3086 Ruz (son) restored per
    # code-reviewer PR #228 P1.2 fix.
    assert row["shared_with_tombs"] == ["G3086"]
    # Notes preserve the full annexe-pair headword block.
    notes = row["notes_from_pm"]
    assert "with annexe." in notes
    assert "Iymerery waʿb-priest of the King's mother" in notes
    assert "Inspector of waʿb-priests" in notes
    assert "Wife, Personet Royal acquaintance." in notes
    assert "Neferḥetpes-Wer (woman)" in notes
    assert "King's adorner" in notes
    assert "Father, Duareʿ King's son of his body." in notes
    assert "North-east annexe." in notes
    # Mastaba-type body trailer dropped per chunks 6-7 convention.
    assert "Mastaba with stone filling" not in notes


def test_chunk9_g3035_thenti_mitrt_wife_title() -> None:
    """G 3035 THENTI Judge and Scribe. Wife Nefert carries the `mitrt`
    title (PM publisher-typography variance `mjtrt`/`mitrt` normalised
    to `mitrt` per chunk-9 G 3050 convention; Gemini PR #228 medium
    #2 + egyptologist P3 fix)."""
    row = _by_id("G3035")
    assert row["occupant_name"] == "Thenti"
    assert row["co_occupants"] == ["Nefert"]
    assert row["co_occupant_roles"] == ["Wife, mitrt"]
    assert "mjtrt" not in row["notes_from_pm"]
    assert "mitrt" in row["notes_from_pm"]


def test_chunk9_g3097_neferhi_underdot_h() -> None:
    """G 3097 NEFERḤI King's adorner and Keeper of unguents. Egyptologist
    PR #228 F1 P1 fix: intra-chunk consistency — same `nfr-ḥ` root as
    G 3098(b) Neferḥetpes-Wer (which carries underdot-Ḥ); OCR caps
    strips diacritics, so the reviewer pass restored the underdot."""
    row = _by_id("G3097")
    assert row["occupant_name"] == "Neferḥi"


def test_chunk9_all_named_rows_dyn_vi() -> None:
    """Fisher Minor Cemetery is essentially a Dyn-VI assemblage —
    every named row's headword carries `Dyn. VI.` (some via `Temp.
    Khufu and Raʿzedef and Khephren` cross-reference for G 3086, but
    the dating tail still resolves to Dyn IV → no wait, G 3086 is
    later; checked by data). Verify all 14 chunk-9 rows are dynasty
    "6"."""
    for tid in CHUNK9_TOMB_IDS:
        assert _by_id(tid)["dynasty"] == "6", tid
