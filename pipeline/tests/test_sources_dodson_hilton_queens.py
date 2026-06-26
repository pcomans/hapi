"""Structural value-assertion tests for Dodson & Hilton queens extract.

Per rule 5: every populated field on a fixture row is asserted.
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

# Head of the South chunk (Chapter 2 "The Head of the South" Brief Lives,
# printed pp. 88-89 / physical pp. 81-82). 11th Dynasty transition —
# Mentuhotep II's Deir el-Bahari mortuary-chapel wives plus the Inyotef-
# line kinship web that closes the 1st Intermediate Period.
PDF_PAGES_HEADOFSOUTH = "81-82"
SUB_PERIOD_HEADOFSOUTH = "The Head of the South"
CITATION_HEADOFSOUTH = {"pdf_pages": PDF_PAGES_HEADOFSOUTH, "edition": EDITION}

# Seizers of the Two Lands chunk (Chapter 2 "Seizers of the Two Lands"
# Brief Lives, printed pp. 96-99 / physical pp. 88-91). 12th Dynasty
# Middle Kingdom proper — the dense Amenemhat I → Sobkneferu royal-
# family prosopography, with five Khnemet / Khnemetneferhedjet homonym
# clusters, five lacuna-bearing `dh_id`s, the flagship female-king
# candidate Neferuptah B, and the trailing Unplaced trio of Didit /
# Neferet Q / Sithathor Q (all sisters-of-unknown-kings).
PDF_PAGES_SEIZERS = "88-91"
SUB_PERIOD_SEIZERS = "Seizers of the Two Lands"
CITATION_SEIZERS = {"pdf_pages": PDF_PAGES_SEIZERS, "edition": EDITION}

# The Founders chunk (Chapter 1 "The Founders" Brief Lives,
# printed pp. 48-49 / physical pp. 44-45). 1st/2nd/3rd Dynasty Early
# Dynastic period — the smallest D&H chunk at 26 entries (15 placed + 11
# Unplaced). All rows take `dynasty: 1` per D&H's joint section-title
# treatment of Dyns 1-3; per-row dynasty refinement is Phase-A work
# (prose cues distinguish Dyn 2 individuals like `Shepsetipet`/`Sitba`/
# `Syhefernerer` from Dyn 3 `Redji`). Introduces 5 Early-Dynastic-
# specific role codes (`CTL`, `FW`, `SH`, `SCH`, `ScH`) all on female
# entries, Phase-A likely decodes as women's cult / priestess / lineage
# roles.
PDF_PAGES_FOUNDERS = "44-45"
SUB_PERIOD_FOUNDERS = "The Founders"
CITATION_FOUNDERS = {"pdf_pages": PDF_PAGES_FOUNDERS, "edition": EDITION}

# Kings and Commoners chunk (Chapter 2 "Kings and Commoners" Brief Lives,
# printed pp. 108-113 / physical pp. 98-103). 13th Dynasty, start of the
# Second Intermediate Period — the largest Ch 2 sub-block at 108 entries
# (91 placed + 17 Unplaced). Dense extended-family material around Iy
# and her sisters-in-law, the Sobkhotep / Neferhotep royal lineages, and
# the Nubkhaes A matrilineal cluster. Introduces the cross-section
# duplicate pattern for an 11th/12th↔13th-Dynasty individual (Hetepti —
# listed in both Seizers and here; see CROSS_SECTION_DUPLICATE_IDS).
# Printed p. 110 is a full-bleed photograph with zero entries, so the
# chunk page-header sequence skips 110.
PDF_PAGES_KC = "98-103"
SUB_PERIOD_KC = "Kings and Commoners"
CITATION_KC = {"pdf_pages": PDF_PAGES_KC, "edition": EDITION}


# Chunk 8 — Of Kings and Priests (chapter 4, 21st Dynasty Brief Lives).
# Printed pp.205-209 / physical PDF pp.190-194 (offset +15). The first
# chunk drawn from chapter 4 *The 3rd Intermediate Period*. 84 rows. No
# Unplaced sub-block. Multiple 21st-Dyn individuals (Henttawy Q,
# Pinudjem I, Tentamun B) appear here AND as stub-cross-references in
# Decline of the Ramessides — cross-section-duplicate set is extended.
PDF_PAGES_OKP = "190-194"
SUB_PERIOD_OKP = "Of Kings and Priests"
CITATION_OKP = {"pdf_pages": PDF_PAGES_OKP, "edition": EDITION}


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(json.loads(line) for line in JSONL.read_text().splitlines() if line.strip())


@lru_cache(maxsize=1)
def _fix_rows_module():
    """Path-load `fix_rows.py` as a module (the source dir has a hyphen
    so `importlib.import_module` doesn't work). lru_cached so multiple
    tests share one load. Refactored from per-test importlib boilerplate
    on PR #186 Gemini round-1.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "dh_fix_rows", SOURCE_DIR / "fix_rows.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@lru_cache(maxsize=1)
def _destructure_module():
    """Path-load `destructure_notes.py` (hyphenated source dir)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "dh_destructure_notes", SOURCE_DIR / "destructure_notes.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_destructure_drops_prose_and_is_idempotent() -> None:
    """`destructure_notes` removes prose fields, preserves every other field,
    and is idempotent (re-running on a destructured row is a no-op)."""
    mod = _destructure_module()
    row = {
        "dh_id": "X", "name": "X", "notes": "verbatim D&H prose here",
        "roles": ["KW"], "dynasty": 18,
    }
    once = mod.destructure_row(row)
    assert "notes" not in once
    assert once == {"dh_id": "X", "name": "X", "roles": ["KW"], "dynasty": 18}
    assert mod.destructure_row(once) == once  # idempotent
    assert mod.PROSE_FIELDS == ("notes",)


def test_sanitize_disagreements_branches() -> None:
    """`sanitize_disagreements` drops prose field lines, removes orphaned row
    headers entirely, and never emits a doubled trailing newline (the no-marker
    branch)."""
    mod = _destructure_module()
    # No marker present + a trailing blank after a kept block: must not double \n.
    out = mod.sanitize_disagreements('RowA (RowA):\n  notes: x\n  roles: ["KW"]\n\n')
    assert out == 'RowA (RowA):\n  roles: ["KW"]\n'
    assert not out.endswith("\n\n")
    # A row whose only field was prose is removed entirely (header + line).
    out2 = mod.sanitize_disagreements(
        'RowB (RowB):\n  notes: y\n\nRowC (RowC):\n  roles: ["KM"]\n'
    )
    assert "RowB" not in out2 and "notes:" not in out2
    assert "RowC (RowC):" in out2


def _row(dh_id: str, sub_period: str | None = None) -> dict:
    """Return the unique row matching `dh_id` (+ optional `sub_period`).

    Chunks 1 and 2 row tests pass `dh_id` only — those ids are unique
    across the file. The Ramesside chunk introduced two distinct
    phenomena that can produce the same `dh_id` under two `sub_period`s
    (see `CROSS_SECTION_DUPLICATE_IDS` below and the README § Schema):
    `Takhat A` and `Isetneferet C` are the SAME individual listed under
    two sub-sections; `Ramesses C` is TWO DIFFERENT individuals that
    share D&H's letter via per-sub-section letter-scoping. Either way,
    callers targeting a specific sub_period disambiguate by passing it.
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

    `is_group_entry` (issue #175 / PR #186) is special-cased with a
    default of `False`: the typed flag is uniform-False on 463/465
    rows, so requiring 463 fixtures to explicitly write
    `"is_group_entry": False` is high-noise / low-signal noise.
    Fixtures for the 2 known True rows (`[...]18A–H`, `[...]18K–N`)
    MUST explicitly assert `True` — Rule 5 is satisfied for the
    informative case, and the default still flows through `schema_fields`
    so the row is checked against the actual on-disk value.
    """
    row = _row(dh_id, sub_period=sub_period)
    schema_fields = {
        "dh_id", "name", "alt_names", "roles", "sex",
        "spouse_names", "father_name", "mother_name", "children_names",
        "dynasty", "sub_period", "unplaced",
        "source_citation",
        "is_group_entry",
    }
    expected = dict(expected)
    expected.setdefault("is_group_entry", False)
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
    """Power (59) + Amarna (41) + Ramesside (170) + Head of South (13) + Seizers (48) + Kings and Commoners (108) + Founders (26) + Of Kings and Priests (84) = 549 rows total."""
    assert len(_rows()) == 549, len(_rows())


def test_no_verbatim_notes_prose() -> None:
    """The verbatim D&H Brief-Lives prose (`notes`) is dropped before any
    public release by `destructure_notes.py` — the terminal pipeline stage.
    Names, kinships, titles and dynasty are uncopyrightable facts and live in
    their own structured fields; D&H's specific phrasing of the narrative is
    their protectable expression and must not be reproduced. This closure test
    locks the destructure: no reconciled row may carry a `notes` (or any other
    verbatim-prose) key. See the source README "Rights" section and
    docs/PUBLISH-READINESS.md."""
    prose_fields = {"notes"}
    offenders = [
        (r["dh_id"], r["sub_period"], sorted(prose_fields & r.keys()))
        for r in _rows()
        if prose_fields & r.keys()
    ]
    assert not offenders, f"verbatim-prose field(s) present: {offenders[:5]}"


def test_row_counts_per_chunk() -> None:
    """Per-sub_period row counts:
    - Power and Glory: 47 placed + 12 Unplaced = 59
    - Amarna Interlude: 41 (36 named + 5 lacuna; no Unplaced)
    - House of Ramesses: 125 (Dyn 19 pt 1 — Ramesses II's family is the
      densest sub-block in the book)
    - Feud of the Ramessides: 10
    - Decline of the Ramessides: 35 (33 placed + 2 Unplaced:
      Anuketemheb, Taiay)
    - Head of the South: 13 (12 placed + 1 Unplaced: Neferkayet)
    - Seizers of the Two Lands: 48 (45 placed + 3 Unplaced:
      Didit, Neferet Q, Sithathor Q)
    - Kings and Commoners: 108 (91 placed + 17 Unplaced; Dyn 13, SIP start)
    - The Founders: 26 (15 placed + 11 Unplaced; Dyn 1/2/3 Early
      Dynastic — the smallest D&H chunk).
    - Of Kings and Priests: 84 (no Unplaced; Dyn 21 — first chunk drawn
      from chapter 4 The 3rd Intermediate Period).
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
        SUB_PERIOD_HEADOFSOUTH: 13,
        SUB_PERIOD_SEIZERS: 48,
        SUB_PERIOD_KC: 108,
        SUB_PERIOD_FOUNDERS: 26,
        SUB_PERIOD_OKP: 84,
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
    # Hetepti (KM; M2L; UWC) — mother of Amenemhat IV, possibly wife of
    # Amenemhat III. D&H prints her full Brief Life in the Seizers of
    # the Two Lands section (Dyn 12) and a single-line stub
    # `See previous section.` in Kings and Commoners (Dyn 13). Same
    # individual, two sub_periods. First cross-section duplicate that
    # spans dynasties rather than sharing the same chapter.
    "Hetepti": {SUB_PERIOD_SEIZERS, SUB_PERIOD_KC},
    # Of-Kings-and-Priests (Dyn 21) chunk introduces 3 cross-dynasty
    # duplicates that span chapters 3-4: each has a stub `(see next
    # section)` cross-reference in the Decline of the Ramessides Brief
    # Lives (Dyn 20) AND a full Brief Life in Of Kings and Priests
    # (Dyn 21). Same convention as the Hetepti Seizers↔KC case.
    "Henttawy Q": {SUB_PERIOD_DECLINE, SUB_PERIOD_OKP},
    "Pinudjem I": {SUB_PERIOD_DECLINE, SUB_PERIOD_OKP},
    "Tentamun B": {SUB_PERIOD_DECLINE, SUB_PERIOD_OKP},
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


def test_cross_section_duplicate_pairs_sort_by_sub_period_alphabetically() -> None:
    """Pins the current sort order of cross-section-duplicate pairs so
    a silent _sort_key_for change cannot swap them unnoticed.

    `merge.py._sort_key_for` uses `sub_period` as the final tiebreaker
    (after top_bin / sub_bin / case-insensitive `dh_id`), so pairs with
    the same `dh_id` sort alphabetically by `sub_period` — NOT
    chronologically or by dynasty. For example `Ramesses C` under
    "The Decline of the Ramessides" (Dyn 20, Ramesses IV) sorts BEFORE
    "The House of Ramesses" (Dyn 19, Ramesses II's grandson) because
    `"The Decline..." < "The House..."` in ASCII order. This is
    intentional — the alphabetical tiebreaker is deterministic and
    cheap — but worth asserting so a future reader isn't surprised by
    the reverse-dynasty ordering.
    """
    rows = _rows()
    for dh_id, expected_sub_periods in CROSS_SECTION_DUPLICATE_IDS.items():
        positions = [(i, r["sub_period"]) for i, r in enumerate(rows) if r["dh_id"] == dh_id]
        assert len(positions) == 2, positions
        (idx_a, sp_a), (idx_b, sp_b) = positions
        assert idx_a < idx_b, positions
        assert sp_a < sp_b, (
            f"{dh_id}: expected alphabetical sub_period order, got "
            f"{sp_a!r} before {sp_b!r}"
        )
        # Expected pair still matches the set constant.
        assert {sp_a, sp_b} == expected_sub_periods


def test_every_row_has_complete_citation() -> None:
    """Each row's `source_citation` matches the chunk it came from."""
    citations = {
        SUB_PERIOD_POWER: CITATION_POWER,
        SUB_PERIOD_AMARNA: CITATION_AMARNA,
        SUB_PERIOD_HOUSE: CITATION_HOUSE,
        SUB_PERIOD_FEUD: CITATION_FEUD,
        SUB_PERIOD_DECLINE: CITATION_DECLINE,
        SUB_PERIOD_HEADOFSOUTH: CITATION_HEADOFSOUTH,
        SUB_PERIOD_SEIZERS: CITATION_SEIZERS,
        SUB_PERIOD_KC: CITATION_KC,
        SUB_PERIOD_FOUNDERS: CITATION_FOUNDERS,
        SUB_PERIOD_OKP: CITATION_OKP,
    }
    for r in _rows():
        sub_period = r["sub_period"]
        assert sub_period in citations, (
            f"unknown sub_period {sub_period!r} for row {r}"
        )
        expected = citations[sub_period]
        assert r["source_citation"] == expected, r


def test_dynasty_per_chunk() -> None:
    """Dynasty alignment per sub_period. Most sub_periods have a single
    dynasty; `The Founders` spans Dyns 1/2/3 because D&H's section title
    joins the 1st, 2nd and 3rd Dynasties — the chunk-default is Dyn 1
    (D&H's section placement) with per-row refinements via
    `FOUNDERS_CORRECTIONS` in `fix_rows.py` for the four Unplaced rows
    that D&H's per-entry text places in Dyn 2 (Shepsetipet,
    Sitba, Syhefernerer) or Dyn 3 (Redji).
    """
    expected_dynasty = {
        SUB_PERIOD_POWER: {18},
        SUB_PERIOD_AMARNA: {18},
        SUB_PERIOD_HOUSE: {19},
        SUB_PERIOD_FEUD: {19},
        SUB_PERIOD_DECLINE: {20},
        SUB_PERIOD_HEADOFSOUTH: {11},
        SUB_PERIOD_SEIZERS: {12},
        SUB_PERIOD_KC: {13},
        SUB_PERIOD_FOUNDERS: {1, 2, 3},
        SUB_PERIOD_OKP: {21},
    }
    for r in _rows():
        assert r["dynasty"] in expected_dynasty[r["sub_period"]], r


def test_founders_per_row_dynasty_refinement() -> None:
    """Four Unplaced rows in Founders carry on-row dynasty evidence
    in their notes ("2nd Dynasty;" or "3rd Dynasty.") and the
    `FOUNDERS_CORRECTIONS` in `fix_rows.py` refines their `dynasty`
    field accordingly. All other Founders rows keep the chunk-default
    `dynasty: 1`. This test asserts exact per-row dynasty values for
    the refined rows and the default for a random sample of non-
    refined rows.
    """
    founders = [r for r in _rows() if r["sub_period"] == SUB_PERIOD_FOUNDERS]
    by_id = {r["dh_id"]: r for r in founders}

    refined_to_2 = {"Shepsetipet", "Sitba", "Syhefernerer"}
    refined_to_3 = {"Redji"}
    for dh_id in refined_to_2:
        assert by_id[dh_id]["dynasty"] == 2, by_id[dh_id]
    for dh_id in refined_to_3:
        assert by_id[dh_id]["dynasty"] == 3, by_id[dh_id]

    default_dyn1_sample = {
        "Batirytes", "Benerib", "Herneith", "Meryetneith A",
        "Nymaathap A", "Perneb", "Hotephirnebty", "Intkaes",
        "Khnemetptah", "Menehpet", "Wadjetefni",
    }
    for dh_id in default_dyn1_sample:
        assert by_id[dh_id]["dynasty"] == 1, by_id[dh_id]


POWER_UNPLACED_IDS = frozenset({
    "Amenemhat Q", "Henut Q", "Henutiunu", "Merybennu", "Meryetptah A",
    "Nebetnehat A", "Sithori", "Tatau", "Thutmose Q", "Ti", "Wiay A",
    "[...]pentepkau",
})
DECLINE_UNPLACED_IDS = frozenset({"Anuketemheb", "Taiay"})
HEADOFSOUTH_UNPLACED_IDS = frozenset({"Neferkayet"})
SEIZERS_UNPLACED_IDS = frozenset({"Didit", "Neferet Q", "Sithathor Q"})
KC_UNPLACED_IDS = frozenset({
    "Ahhotepti", "Anuqneferetweben", "Dedetamun", "Dedetsobk", "Dedusobk A",
    "Haankhef Q", "Hatshepsut C", "Horhotep Q", "Iuhetibu Q", "Neferet R",
    "Neferhotep Q", "Neferu Q", "Reniseneb Q", "Reniseneb R", "Senetmut",
    "Sobkhotep Q", "[...]djeb",
})
FOUNDERS_UNPLACED_IDS = frozenset({
    "Khnemetptah", "Menehpet", "Mesenka", "Neithhotep B", "Nysuheqat",
    "Qaienneith", "Redji", "Shepsetipet", "Sitba", "Syhefernerer",
    "Wadjetefni",
})


def test_unplaced_set_is_the_expected_ids() -> None:
    """D&H's Unplaced sub-blocks: 12 at the end of Power (printed p. 141)
    + 2 at the end of Decline (printed p. 194) + 1 at the end of Head of
    South (printed p. 89) + 3 at the end of Seizers (printed p. 99 — Didit,
    Neferet Q, Sithathor Q, all sisters-of-unknown-kings) + 17 at the end
    of Kings and Commoners (printed p. 113 — Ahhotepti through [...]djeb;
    Dyn-13 sisters/daughters/sons/wives of unknown kings) + 11 at the end
    of The Founders (printed p. 49 — Khnemetptah through Wadjetefni;
    Early-Dynastic (Dyn 1/2/3) unplaced princes/princesses/queens) = 46
    unplaced rows total. No Unplaced sub-block in Amarna / House / Feud.
    """
    unplaced = [r for r in _rows() if r["unplaced"]]
    assert len(unplaced) == 46, f"expected 46 unplaced, got {len(unplaced)}"
    assert {r["dh_id"] for r in unplaced} == (
        POWER_UNPLACED_IDS
        | DECLINE_UNPLACED_IDS
        | HEADOFSOUTH_UNPLACED_IDS
        | SEIZERS_UNPLACED_IDS
        | KC_UNPLACED_IDS
        | FOUNDERS_UNPLACED_IDS
    )
    power_unplaced = {r["dh_id"] for r in unplaced if r["sub_period"] == SUB_PERIOD_POWER}
    decline_unplaced = {r["dh_id"] for r in unplaced if r["sub_period"] == SUB_PERIOD_DECLINE}
    hos_unplaced = {r["dh_id"] for r in unplaced if r["sub_period"] == SUB_PERIOD_HEADOFSOUTH}
    seizers_unplaced = {r["dh_id"] for r in unplaced if r["sub_period"] == SUB_PERIOD_SEIZERS}
    kc_unplaced = {r["dh_id"] for r in unplaced if r["sub_period"] == SUB_PERIOD_KC}
    founders_unplaced = {r["dh_id"] for r in unplaced if r["sub_period"] == SUB_PERIOD_FOUNDERS}
    assert power_unplaced == POWER_UNPLACED_IDS
    assert decline_unplaced == DECLINE_UNPLACED_IDS
    assert hos_unplaced == HEADOFSOUTH_UNPLACED_IDS
    assert seizers_unplaced == SEIZERS_UNPLACED_IDS
    assert kc_unplaced == KC_UNPLACED_IDS
    assert founders_unplaced == FOUNDERS_UNPLACED_IDS


def test_unplaced_rows_sort_last_in_reconciled_jsonl() -> None:
    """The 46 unplaced rows must occupy the trailing 46 positions of
    `reconciled.jsonl` — merge.py's sort groups them into a final bin so
    the file reads as placed-alphabetical, then unplaced-alphabetical.
    Regression on the code-reviewer-flagged sort-key bug from PR #38.
    """
    rows = _rows()
    for r in rows[:-46]:
        assert r["unplaced"] is False, r["dh_id"]
    for r in rows[-46:]:
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
    - Kings and Commoners chunk contributes 1 unplaced lacuna (`[...]djeb`).
    - Of Kings and Priests chunk contributes 11 placed lacunae
      (`[...]Jamenweret`, `[...]Janm`, `[...]Jemkheb`, `[...]Jmemsunay`,
      `[...]It[...]`, `[...]21A`–`[...]21F`; no Unplaced sub-block).

    Composite-key detail: `Ramesses C` under House sorts adjacent to
    `Ramesses C` under Decline via the `sub_period` tiebreaker.
    """
    rows = _rows()
    lacuna_prefixes = ("[", "–")

    placed = [r for r in rows if not r["unplaced"]]
    # 549 - 46 unplaced = 503 placed (OKP has no Unplaced sub-block).
    assert len(placed) == 503, len(placed)

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
    assert len(unplaced) == 46, len(unplaced)
    # `[...]djeb` (Kings and Commoners unplaced, lacuna) and
    # `[...]pentepkau` (Power unplaced, lacuna) both sort after every
    # letter-prefixed unplaced entry. The sort key is
    # (unplaced_bin=1, lacuna_sub_bin, dh_id.lower(), sub_period); within
    # the unplaced-lacuna tail the two lacuna ids order alphabetically
    # (`[...]djeb` < `[...]pentepkau`). The trailing two rows of the
    # file are therefore `[...]djeb`, then `[...]pentepkau`.
    assert unplaced[-2]["dh_id"] == "[...]djeb", unplaced[-2]["dh_id"]
    assert unplaced[-1]["dh_id"] == "[...]pentepkau", unplaced[-1]["dh_id"]
    for r in unplaced[:-2]:
        assert not r["dh_id"].startswith(lacuna_prefixes), r["dh_id"]


def test_sex_inference_covers_every_row() -> None:
    for r in _rows():
        assert r["sex"] in ("male", "female"), r


def test_role_tokens_in_known_vocab() -> None:
    """Issue #175: every `roles` token in any row appears in
    `KNOWN_ROLE_TOKENS`. Closure direction (the existing
    `test_role_code_set_spans_the_known_codes` checks the OTHER
    direction — that known codes ARE present in the corpus). Catches
    typos like `OPULE` (was shipping until this PR) and silent
    free-text drift.

    When a new chunk introduces a legitimate new D&H role token,
    update `KNOWN_ROLE_TOKENS` in `fix_rows.py` after verifying the
    token is D&H's, not a typo.
    """
    known = _fix_rows_module().KNOWN_ROLE_TOKENS
    for r in _rows():
        for role in r.get("roles", []):
            assert role in known, (
                f"{r['dh_id']} [{r['sub_period']}]: role token "
                f"{role!r} not in KNOWN_ROLE_TOKENS. Either a typo "
                f"or a new D&H code — verify against the source PDF "
                f"and update fix_rows.py if legitimate."
            )


def test_no_opule_typo() -> None:
    """Issue #175: the OPULE typo was shipping on 1 row (Thutmose B)
    where MULE was intended (8 rows in corpus). Pin that no row carries
    the typo going forward — both as a regression guard and as
    documentation of the historical bug.
    """
    for r in _rows():
        assert "OPULE" not in r.get("roles", []), (
            f"{r['dh_id']} [{r['sub_period']}]: roles contains 'OPULE' "
            f"typo (issue #175). Should be 'MULE'."
        )


def test_is_group_entry_present_on_every_row() -> None:
    """Issue #175 (Shape J): every row carries `is_group_entry: bool`.
    Schema-shape invariant backfilled by `fix_rows.backfill_is_group_entry`.
    """
    for r in _rows():
        assert "is_group_entry" in r, (
            f"{r['dh_id']} [{r['sub_period']}]: missing is_group_entry key"
        )
        assert isinstance(r["is_group_entry"], bool), (
            f"{r['dh_id']} [{r['sub_period']}]: is_group_entry "
            f"{r['is_group_entry']!r} is not a bool"
        )


def test_is_group_entry_matches_canonical_set() -> None:
    """Issue #175 (Shape J): `is_group_entry=True` iff the row's
    (dh_id, sub_period) is in `GROUP_ENTRY_DH_IDS`. The two known
    group entries are `[...]18A–H` and `[...]18K–N` (en-dash range
    notation in D&H — letter-range covers multiple individuals in
    a single Brief Lives entry).

    A new chunk adding a group entry must extend `GROUP_ENTRY_DH_IDS`
    in `fix_rows.py`; this test fails otherwise so the decision is
    explicit, not silent.
    """
    canonical = _fix_rows_module().GROUP_ENTRY_DH_IDS

    actual_true = {
        (r["dh_id"], r["sub_period"]) for r in _rows()
        if r.get("is_group_entry")
    }
    assert actual_true == canonical, (
        f"is_group_entry=True set drift: extra="
        f"{sorted(actual_true - canonical)}, missing="
        f"{sorted(canonical - actual_true)}"
    )


def test_sitre_a_alt_names_cleared() -> None:
    """Issue #175 regression-pin: Sitre A's `alt_names = ['Tia Q']`
    was cleared per the Thutmose B precedent — D&H's text ('She may
    previously have borne the name Tia (Q).') is a hedged identity
    hint, deliberately not promoted to a confirmed alt_name. (The
    verbatim text is no longer reproduced; see destructure_notes.py.)
    """
    sitre = next(
        (r for r in _rows() if r["dh_id"] == "Sitre A"),
        None,
    )
    assert sitre is not None, "Sitre A missing from reconciled.jsonl"
    assert sitre["alt_names"] == [], (
        f"Sitre A alt_names={sitre['alt_names']!r}, expected [] per "
        f"the Thutmose B precedent (cross-row identity hint belongs "
        f"in `notes`, not `alt_names`)."
    )


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
    # Head of the South codes (new in the 11th-Dynasty transition chunk):
    # `PH` appears on most Mentuhotep-II Deir el-Bahari-tomb wives
    # (Ashayet, Henhenet, Kawit, Kemsit, Sadhe) and on Iah; `GS` appears
    # only on Tem; `Nomarch` is the sole male-role token for Inyotef A;
    # `KW?` is the explicit-hedge variant D&H uses on possible-wife
    # classifications (Kawit, Kemsit).
    for expected in ["PH", "GS", "Nomarch", "KW?"]:
        assert expected in all_codes, (
            f"expected Head of South code {expected!r} never extracted"
        )
    # Seizers of the Two Lands codes genuinely new in chunk 5: `GF` (on
    # the father-of-Amenemhat-I entry Senwosret A — a gendered role code
    # not on prior-chunk list), and the long-form role-phrase
    # `Mistress of All Women` (on Kaneferu — preserved as a single
    # verbatim token rather than split on spaces). `UWC` appears heavily
    # on Dyn-12 wives but is NOT new — the Power chunk's Hatshepsut D
    # already carries it (see `test_hatshepsut_d_full_row`), so the
    # Seizers chunk adds new density rather than a new code.
    for expected in ["GF", "Mistress of All Women"]:
        assert expected in all_codes, (
            f"expected Seizers code {expected!r} never extracted"
        )
    # Kings and Commoners codes (Dyn 13 chunk) add one short-token role
    # (`RO` — Royal Ornament; on Inyotef C only) and a cluster of long-
    # form spelled-out role tokens preserved as single-token strings
    # (same treatment as `King of Hittites` / `Mistress of All Women`).
    # The long-form tokens are non-royal administrative roles attached
    # to the extended-family commoners D&H introduces in this chunk
    # (governors, stewards, scribes of the vizier, etc.).
    for expected in [
        "RO",
        "Governor of El-Kab",
        "Overseer of the Fields",
        "Chief Scribe of the Vizier",
        "Elder of the Portal",
        "High Steward",
        "Attendant of Dog-Keepers",
        "Townsman",
        "Royal Representative",
    ]:
        assert expected in all_codes, (
            f"expected Kings and Commoners code {expected!r} never extracted"
        )
    # The Founders codes (Early Dynastic — Dyn 1/2/3). Five short tokens
    # new to the D&H corpus in this chunk, all on female entries. D&H's
    # abbreviation legend (front matter pp. 24–37) defines them; Phase A
    # decodes formally. Likely readings (informal): `CTL` = Companion
    # of the Two Ladies or Consort of the Two Lands; `FW` = First Wife
    # or Favoured of the West; `SH` = She of Horus or Sister of Horus;
    # `SCH`/`ScH` = casing variants of the same code on different rows
    # (Nakhtneith vs Seshemetka) — D&H typographic inconsistency the
    # extractors preserved verbatim.
    for expected in ["CTL", "FW", "SH", "SCH", "ScH"]:
        assert expected in all_codes, (
            f"expected Founders code {expected!r} never extracted"
        )


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
        "source_citation": CITATION_POWER,
    })


def test_tiaa_a_full_row() -> None:
    """Mother of Thutmose IV — KGW, KM, GW. (Tiaa A's old `notes`
    verbatim-prose correction was retired when the `notes` field was
    dropped by destructure_notes.py; the structured fields are asserted
    here as for every other row.)
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
        # Issue #175: en-dash range covers up to 8 daughters A–H of
        # Amenhotep III. One of two True-flagged group entries.
        "is_group_entry": True,
        "sex": 'female',
        "spouse_names": [],
        "father_name": 'Amenhotep III',
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
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
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_18k_n_full_row() -> None:
    _assert_full_row('[...]18K–N', {
        "dh_id": '[...]18K–N',
        "name": '[...]18K–N',
        "alt_names": [],
        "roles": [],
        # Issue #175: en-dash range covers 4 daughters K–N of Anen.
        # Second of two True-flagged group entries.
        "is_group_entry": True,
        "sex": 'female',
        "spouse_names": [],
        "father_name": 'Anen',
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
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
        "source_citation": CITATION_AMARNA,
    })


def test_amarna_thutmose_b_full_row() -> None:
    _assert_full_row('Thutmose B', {
        "dh_id": 'Thutmose B',
        "name": 'Thutmose B',
        "alt_names": [],
        "roles": ['EKSon', 'HPM', 'SPP', 'MULE'],
        "sex": 'male',
        "spouse_names": [],
        "father_name": 'Amenhotep III',
        "mother_name": None,
        "children_names": [],
        "dynasty": 18,
        "sub_period": SUB_PERIOD_AMARNA,
        "unplaced": False,
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
        "source_citation": CITATION_AMARNA,
    })


# ---------------------------------------------------------------------------
# Ramesside fixtures — chunk 3 (House of Ramesses / Feud / Decline)
#
# Generated via /tmp/claude/gen_ramesside_fixtures.py on 2026-04-16 after the
# merge + fix_rows pass (11 overrides: 9 from chunks 1-2 + 2 Ramesside review
# corrections on Khaemwaset C and Iset D Ta-Hemdjert children_names). The
# generator reads reconciled.jsonl, sorts by (sub_period, unplaced, dh_id),
# and emits _assert_full_row calls. Rows whose `dh_id` appears under two
# sub_periods (`Takhat A` and `Isetneferet C` — same individual in two
# sections; `Ramesses C` — two different individuals with reused letter)
# pass `sub_period=` to disambiguate.
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
        "father_name": "Khaemwaset C (probable)",
        "mother_name": None,
        "children_names": ["Hori B"],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
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
        "source_citation": CITATION_HOUSE,
    })

def test_sitre_a_house_full_row() -> None:
    _assert_full_row("Sitre A", {
        "dh_id": "Sitre A",
        "name": "Sitre A",
        # Issue #175: alt_names cleared per Thutmose B precedent — D&H's
        # hedged "She may previously have borne the name Tia (Q)" identity
        # hint is deliberately not promoted to a confirmed alt_name.
        "alt_names": [],
        "roles": ["GW", "KGW", "L2L", "GM", "KM", "MULE"],
        "sex": "female",
        "spouse_names": ["Ramesses I"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Sety I"],
        "dynasty": 19,
        "sub_period": SUB_PERIOD_HOUSE,
        "unplaced": False,
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
        "source_citation": CITATION_DECLINE,
    }, sub_period=SUB_PERIOD_DECLINE)

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
        "source_citation": CITATION_DECLINE,
    }, sub_period=SUB_PERIOD_DECLINE)

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
        "source_citation": CITATION_DECLINE,
    }, sub_period=SUB_PERIOD_DECLINE)

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
        "source_citation": CITATION_DECLINE,
    })



def test_headofsouth_ashayet_full_row() -> None:
    _assert_full_row('Ashayet', {
        'dh_id': 'Ashayet',
        'name': 'Ashayet',
        'alt_names': [],
        'roles': ['PH', 'KW'],
        'sex': 'female',
        'spouse_names': ['Mentuhotep II'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 11,
        "sub_period": SUB_PERIOD_HEADOFSOUTH,
        'unplaced': False,
        'source_citation': CITATION_HEADOFSOUTH,
    })


def test_headofsouth_henhenet_full_row() -> None:
    _assert_full_row('Henhenet', {
        'dh_id': 'Henhenet',
        'name': 'Henhenet',
        'alt_names': [],
        'roles': ['PH', 'KW'],
        'sex': 'female',
        'spouse_names': ['Mentuhotep II'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 11,
        "sub_period": SUB_PERIOD_HEADOFSOUTH,
        'unplaced': False,
        'source_citation': CITATION_HEADOFSOUTH,
    })


def test_headofsouth_iah_full_row() -> None:
    _assert_full_row('Iah', {
        'dh_id': 'Iah',
        'name': 'Iah',
        'alt_names': [],
        'roles': ['KM', 'KD', 'PH'],
        'sex': 'female',
        'spouse_names': ['Inyotef III'],
        'father_name': 'Inyotef II',
        'mother_name': None,
        'children_names': ['Mentuhotep II', 'Neferu II'],
        'dynasty': 11,
        "sub_period": SUB_PERIOD_HEADOFSOUTH,
        'unplaced': False,
        'source_citation': CITATION_HEADOFSOUTH,
    })


def test_headofsouth_ikui_full_row() -> None:
    _assert_full_row('Ikui', {
        'dh_id': 'Ikui',
        'name': 'Ikui',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Inyotef A'],
        'dynasty': 11,
        "sub_period": SUB_PERIOD_HEADOFSOUTH,
        'unplaced': False,
        'source_citation': CITATION_HEADOFSOUTH,
    })


def test_headofsouth_imi_full_row() -> None:
    _assert_full_row('Imi', {
        'dh_id': 'Imi',
        'name': 'Imi',
        'alt_names': [],
        'roles': ['KM'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Mentuhotep IV'],
        'dynasty': 11,
        "sub_period": SUB_PERIOD_HEADOFSOUTH,
        'unplaced': False,
        'source_citation': CITATION_HEADOFSOUTH,
    })


def test_headofsouth_inyotef_a_full_row() -> None:
    """Sole male entry in the Head-of-South chunk (Nomarch role).
    D&H describes him as `son of Ikui` and `probable father of
    Mentuhotep I`. The probability hedge is preserved verbatim on
    `children_names` per the abstract-rule encoding in the prompt:
    `"Mentuhotep I (probably)"` rather than an unhedged `"Mentuhotep I"`.
    """
    _assert_full_row('Inyotef A', {
        'dh_id': 'Inyotef A',
        'name': 'Inyotef A',
        'alt_names': [],
        'roles': ['Nomarch'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': 'Ikui',
        'children_names': ['Mentuhotep I (probably)'],
        'dynasty': 11,
        "sub_period": SUB_PERIOD_HEADOFSOUTH,
        'unplaced': False,
        'source_citation': CITATION_HEADOFSOUTH,
    })


def test_headofsouth_kawit_full_row() -> None:
    _assert_full_row('Kawit', {
        'dh_id': 'Kawit',
        'name': 'Kawit',
        'alt_names': [],
        'roles': ['PH', 'KW?'],
        'sex': 'female',
        'spouse_names': ['Mentuhotep II (possibly)'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 11,
        "sub_period": SUB_PERIOD_HEADOFSOUTH,
        'unplaced': False,
        'source_citation': CITATION_HEADOFSOUTH,
    })


def test_headofsouth_kemsit_full_row() -> None:
    _assert_full_row('Kemsit', {
        'dh_id': 'Kemsit',
        'name': 'Kemsit',
        'alt_names': [],
        'roles': ['PH', 'KW?'],
        'sex': 'female',
        'spouse_names': ['Mentuhotep II (possibly)'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 11,
        "sub_period": SUB_PERIOD_HEADOFSOUTH,
        'unplaced': False,
        'source_citation': CITATION_HEADOFSOUTH,
    })


def test_headofsouth_neferu_i_full_row() -> None:
    _assert_full_row('Neferu I', {
        'dh_id': 'Neferu I',
        'name': 'Neferu I',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Inyotef II'],
        'dynasty': 11,
        "sub_period": SUB_PERIOD_HEADOFSOUTH,
        'unplaced': False,
        'source_citation': CITATION_HEADOFSOUTH,
    })


def test_headofsouth_neferu_ii_full_row() -> None:
    _assert_full_row('Neferu II', {
        'dh_id': 'Neferu II',
        'name': 'Neferu II',
        'alt_names': [],
        'roles': ['KW', 'KD'],
        'sex': 'female',
        'spouse_names': ['Mentuhotep II'],
        'father_name': 'Inyotef III',
        'mother_name': 'Iah',
        'children_names': [],
        'dynasty': 11,
        "sub_period": SUB_PERIOD_HEADOFSOUTH,
        'unplaced': False,
        'source_citation': CITATION_HEADOFSOUTH,
    })


def test_headofsouth_sadhe_full_row() -> None:
    _assert_full_row('Sadhe', {
        'dh_id': 'Sadhe',
        'name': 'Sadhe',
        'alt_names': [],
        'roles': ['PH', 'KW'],
        'sex': 'female',
        'spouse_names': ['Mentuhotep II'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 11,
        "sub_period": SUB_PERIOD_HEADOFSOUTH,
        'unplaced': False,
        'source_citation': CITATION_HEADOFSOUTH,
    })


def test_headofsouth_tem_full_row() -> None:
    _assert_full_row('Tem', {
        'dh_id': 'Tem',
        'name': 'Tem',
        'alt_names': [],
        'roles': ['KW', 'GS', 'KM'],
        'sex': 'female',
        'spouse_names': ['Mentuhotep II'],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Mentuhotep III'],
        'dynasty': 11,
        "sub_period": SUB_PERIOD_HEADOFSOUTH,
        'unplaced': False,
        'source_citation': CITATION_HEADOFSOUTH,
    })


def test_headofsouth_neferkayet_full_row() -> None:
    """Sole Unplaced entry in the Head-of-South chunk. D&H's prose
    reads `"Daughter and wife of unknown kings"` — plural `"kings"`
    covers two distinct unidentifiable relationships (the unknown
    father and the unknown husband). The extract uses `father_name:
    null` and `spouse_names: []` per the abstract-rule encoding for
    unresolvable relatives: no specific individual is named, so no
    placeholder entity is invented. Phase A's authority-matcher
    correctly treats null/empty as `"no resolvable target"`.
    """
    _assert_full_row('Neferkayet', {
        'dh_id': 'Neferkayet',
        'name': 'Neferkayet',
        'alt_names': [],
        'roles': ['KW', 'KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 11,
        "sub_period": SUB_PERIOD_HEADOFSOUTH,
        'unplaced': True,
        'source_citation': CITATION_HEADOFSOUTH,
    })


def test_seizers_lac12a_full_row() -> None:
    _assert_full_row('[...]12A', {
        'dh_id': '[...]12A',
        'name': '[...]12A',
        'alt_names': [],
        'roles': ['KD', 'UWC'],
        'sex': 'female',
        'spouse_names': ['Senwosret III'],
        'father_name': 'Senwosret II',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_lac12b_full_row() -> None:
    _assert_full_row('[...]12B', {
        'dh_id': '[...]12B',
        'name': '[...]12B',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': ['Amenemhat III'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_aat_full_row() -> None:
    _assert_full_row('Aat', {
        'dh_id': 'Aat',
        'name': 'Aat',
        'alt_names': [],
        'roles': ['KW', 'UWC'],
        'sex': 'female',
        'spouse_names': ['Amenemhat III'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_amenemhatankh_full_row() -> None:
    _assert_full_row('Amenemhatankh', {
        'dh_id': 'Amenemhatankh',
        'name': 'Amenemhatankh',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Amenemhat II (probable)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_ameny_a_full_row() -> None:
    """Ameny A's `alt_names: ['Amenemhat II']` is restored via
    `SEIZERS_CORRECTIONS` in `fix_rows.py` — his prose explicitly names
    him as "later king as AMENEMHAT II", matching the regnal-alias
    aliasing convention Paramessu / Ramesses A / Amenhotep E set in
    earlier chunks. Finding surfaced by Codex retrospective review on
    the merged PR #77 (run 2026-04-19).
    """
    _assert_full_row('Ameny A', {
        'dh_id': 'Ameny A',
        'name': 'Ameny A',
        'alt_names': ['Amenemhat II'],
        'roles': ['EKSonB'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Senwosret I',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_hathorhetepet_full_row() -> None:
    _assert_full_row('Hathorhetepet', {
        'dh_id': 'Hathorhetepet',
        'name': 'Hathorhetepet',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Amenemhat III (possibly)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_hetepti_full_row() -> None:
    """Hetepti is a cross-section duplicate: full Brief Life here
    (Seizers of the Two Lands / Dyn 12) + stub `See previous section.`
    in Kings and Commoners / Dyn 13. The composite key resolves both;
    this test explicitly passes `sub_period` so `_row` picks the
    Seizers row.
    """
    _assert_full_row('Hetepti', {
        'dh_id': 'Hetepti',
        'name': 'Hetepti',
        'alt_names': [],
        'roles': ['KM', 'M2L', 'UWC'],
        'sex': 'female',
        'spouse_names': ['Amenemhat III (possibly)'],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Amenemhat IV'],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    }, sub_period=SUB_PERIOD_SEIZERS)


def test_seizers_ita_full_row() -> None:
    _assert_full_row('Ita', {
        'dh_id': 'Ita',
        'name': 'Ita',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Amenemhat II',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_itakayet_a_full_row() -> None:
    _assert_full_row('Itakayet A', {
        'dh_id': 'Itakayet A',
        'name': 'Itakayet A',
        'alt_names': [],
        'roles': ['KDB'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Senwosret I (probable)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_itakayet_b_full_row() -> None:
    _assert_full_row('Itakayet B', {
        'dh_id': 'Itakayet B',
        'name': 'Itakayet B',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Amenemhat II (probably)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_itakayet_c_full_row() -> None:
    _assert_full_row('Itakayet C', {
        'dh_id': 'Itakayet C',
        'name': 'Itakayet C',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Senwosret II (probably)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_itaweret_full_row() -> None:
    _assert_full_row('Itaweret', {
        'dh_id': 'Itaweret',
        'name': 'Itaweret',
        'alt_names': [],
        'roles': ['KD', 'UWC'],
        'sex': 'female',
        'spouse_names': ['Senwosret II (probably)'],
        'father_name': 'Amenemhat II',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_kaneferu_full_row() -> None:
    _assert_full_row('Kaneferu', {
        'dh_id': 'Kaneferu',
        'name': 'Kaneferu',
        'alt_names': [],
        'roles': ['Mistress of All Women'],
        'sex': 'female',
        'spouse_names': ['Amenemhat II (probably)'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_kayet_full_row() -> None:
    _assert_full_row('Kayet', {
        'dh_id': 'Kayet',
        'name': 'Kayet',
        'alt_names': [],
        'roles': ['KDB'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Amenemhat I',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_keminub_full_row() -> None:
    _assert_full_row('Keminub', {
        'dh_id': 'Keminub',
        'name': 'Keminub',
        'alt_names': [],
        'roles': ['KW'],
        'sex': 'female',
        'spouse_names': ['Amenemhat II'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_khnemet_full_row() -> None:
    _assert_full_row('Khnemet', {
        'dh_id': 'Khnemet',
        'name': 'Khnemet',
        'alt_names': [],
        'roles': ['KD', 'UWC'],
        'sex': 'female',
        'spouse_names': ['Senwosret II (probably)'],
        'father_name': 'Amenemhat II',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_khnemetlac_full_row() -> None:
    _assert_full_row('Khnemet[...]', {
        'dh_id': 'Khnemet[...]',
        'name': 'Khnemet[...]',
        'alt_names': [],
        'roles': ['KDB'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Senwosret III',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_khnemetneferhedjet_a_full_row() -> None:
    _assert_full_row('Khnemetneferhedjet A', {
        'dh_id': 'Khnemetneferhedjet A',
        'name': 'Khnemetneferhedjet A',
        'alt_names': [],
        'roles': ['KDB'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Amenemhat II',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_khnemetneferhedjet_i_weret_full_row() -> None:
    _assert_full_row('Khnemetneferhedjet I Weret', {
        'dh_id': 'Khnemetneferhedjet I Weret',
        'name': 'Khnemetneferhedjet I Weret',
        'alt_names': [],
        'roles': ['KM', 'KW', 'M2L'],
        'sex': 'female',
        'spouse_names': ['Senwosret II'],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Senwosret III'],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_khnemetneferhedjet_ii_weret_full_row() -> None:
    _assert_full_row('Khnemetneferhedjet II Weret', {
        'dh_id': 'Khnemetneferhedjet II Weret',
        'name': 'Khnemetneferhedjet II Weret',
        'alt_names': [],
        'roles': ['GS', 'KW'],
        'sex': 'female',
        'spouse_names': ['Senwosret III'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_menet_full_row() -> None:
    _assert_full_row('Menet', {
        'dh_id': 'Menet',
        'name': 'Menet',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Senwosret III',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_mereret_b_full_row() -> None:
    _assert_full_row('Mereret B', {
        'dh_id': 'Mereret B',
        'name': 'Mereret B',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Senwosret III',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_mertseger_full_row() -> None:
    _assert_full_row('Mertseger', {
        'dh_id': 'Mertseger',
        'name': 'Mertseger',
        'alt_names': [],
        'roles': ['KW', 'KGW'],
        'sex': 'female',
        'spouse_names': ['Senwosret III'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_neferet_b_full_row() -> None:
    _assert_full_row('Neferet B', {
        'dh_id': 'Neferet B',
        'name': 'Neferet B',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Senwosret II (probably)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_neferet_i_full_row() -> None:
    _assert_full_row('Neferet I', {
        'dh_id': 'Neferet I',
        'name': 'Neferet I',
        'alt_names': [],
        'roles': ['KM'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Amenemhat I (probable)'],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_neferet_ii_full_row() -> None:
    _assert_full_row('Neferet II', {
        'dh_id': 'Neferet II',
        'name': 'Neferet II',
        'alt_names': [],
        'roles': ['KDB', 'GS', 'M2L'],
        'sex': 'female',
        'spouse_names': ['Senwosret II'],
        'father_name': 'Amenemhat II',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_neferhenut_full_row() -> None:
    _assert_full_row('Neferhenut', {
        'dh_id': 'Neferhenut',
        'name': 'Neferhenut',
        'alt_names': [],
        'roles': ['KW', 'UWC'],
        'sex': 'female',
        'spouse_names': ['Senwosret III'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_neferitatjenen_full_row() -> None:
    _assert_full_row('Neferitatjenen', {
        'dh_id': 'Neferitatjenen',
        'name': 'Neferitatjenen',
        'alt_names': [],
        'roles': ['KM'],
        'sex': 'female',
        'spouse_names': ['Amenemhat I'],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Senwosret I'],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_neferu_iii_full_row() -> None:
    _assert_full_row('Neferu III', {
        'dh_id': 'Neferu III',
        'name': 'Neferu III',
        'alt_names': [],
        'roles': ['KD', 'KW', 'KM'],
        'sex': 'female',
        'spouse_names': ['Senwosret I'],
        'father_name': 'Amenemhat I',
        'mother_name': None,
        'children_names': ['Amenemhat II'],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_neferuptah_a_full_row() -> None:
    _assert_full_row('Neferuptah A', {
        'dh_id': 'Neferuptah A',
        'name': 'Neferuptah A',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Senwosret I (probable)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_neferuptah_b_full_row() -> None:
    _assert_full_row('Neferuptah B', {
        'dh_id': 'Neferuptah B',
        'name': 'Neferuptah B',
        'alt_names': [],
        'roles': ['GS', 'KDB'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Amenemhat III',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_neferusherit_full_row() -> None:
    _assert_full_row('Neferusherit', {
        'dh_id': 'Neferusherit',
        'name': 'Neferusherit',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Amenemhat I',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_neferusobk_full_row() -> None:
    _assert_full_row('Neferusobk', {
        'dh_id': 'Neferusobk',
        'name': 'Neferusobk',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Senwosret I (probable)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_nensedlac_full_row() -> None:
    _assert_full_row('Nensed[...]', {
        'dh_id': 'Nensed[...]',
        'name': 'Nensed[...]',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Senwosret I (probable)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_nubhotepet_full_row() -> None:
    _assert_full_row('Nubhotepet', {
        'dh_id': 'Nubhotepet',
        'name': 'Nubhotepet',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Amenemhat III (possibly)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_sebat_full_row() -> None:
    _assert_full_row('Sebat', {
        'dh_id': 'Sebat',
        'name': 'Sebat',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Senwosret I',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_senetsenbetes_full_row() -> None:
    _assert_full_row('Senetsenbetes', {
        'dh_id': 'Senetsenbetes',
        'name': 'Senetsenbetes',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Senwosret III',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_senwosret_a_full_row() -> None:
    _assert_full_row('Senwosret A', {
        'dh_id': 'Senwosret A',
        'name': 'Senwosret A',
        'alt_names': [],
        'roles': ['GF'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Amenemhat I (probable)'],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_senwosretsonbe_full_row() -> None:
    _assert_full_row('Senwosretsonbe', {
        'dh_id': 'Senwosretsonbe',
        'name': 'Senwosretsonbe',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Senwosret II',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_sitlacja_full_row() -> None:
    _assert_full_row('Sit[...]JA', {
        'dh_id': 'Sit[...]JA',
        'name': 'Sit[...]JA',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Senwosret III',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_sithathor_a_full_row() -> None:
    _assert_full_row('Sithathor A', {
        'dh_id': 'Sithathor A',
        'name': 'Sithathor A',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Senwosret III (probably)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_sithathor_b_full_row() -> None:
    _assert_full_row('Sithathor B', {
        'dh_id': 'Sithathor B',
        'name': 'Sithathor B',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Amenemhat III (possible)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_sithathoriunet_full_row() -> None:
    _assert_full_row('Sithathoriunet', {
        'dh_id': 'Sithathoriunet',
        'name': 'Sithathoriunet',
        'alt_names': [],
        'roles': ['KD', 'KW'],
        'sex': 'female',
        'spouse_names': ['Senwosret III (probably)'],
        'father_name': 'Senwosret II',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_sithathormeryet_full_row() -> None:
    _assert_full_row('Sithathormeryet', {
        'dh_id': 'Sithathormeryet',
        'name': 'Sithathormeryet',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_sobkneferu_full_row() -> None:
    _assert_full_row('Sobkneferu', {
        'dh_id': 'Sobkneferu',
        'name': 'Sobkneferu',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Amenemhat III',
        'mother_name': None,
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': False,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_didit_full_row() -> None:
    """Didit's `mother_name: 'Sithathor Q'` is restored via
    `SEIZERS_CORRECTIONS` in `fix_rows.py` — `Sithathor Q`'s Brief Life
    in the same Unplaced sub-block opens `Mother of Didit…`. The cross-
    entry-inference rule established in chunk-2 Amarna (Gilukhipa /
    Shuttarna II) and chunk-3 Ramesside (Hattusilis III / Pudukhepa)
    requires the symmetric kinship edge; Seizers extraction missed the
    parent→child direction. Finding surfaced by Codex retrospective
    review on the merged PR #77 (run 2026-04-19).
    """
    _assert_full_row('Didit', {
        'dh_id': 'Didit',
        'name': 'Didit',
        'alt_names': [],
        'roles': ['KSis'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': 'Sithathor Q',
        'children_names': ['Neferet Q'],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': True,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_neferet_q_full_row() -> None:
    _assert_full_row('Neferet Q', {
        'dh_id': 'Neferet Q',
        'name': 'Neferet Q',
        'alt_names': [],
        'roles': ['KSis'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': 'Didit',
        'children_names': [],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': True,
        'source_citation': CITATION_SEIZERS,
    })


def test_seizers_sithathor_q_full_row() -> None:
    _assert_full_row('Sithathor Q', {
        'dh_id': 'Sithathor Q',
        'name': 'Sithathor Q',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Didit'],
        'dynasty': 12,
        "sub_period": SUB_PERIOD_SEIZERS,
        'unplaced': True,
        'source_citation': CITATION_SEIZERS,
    })


def test_kc_lac13a_full_row() -> None:
    _assert_full_row('[...]13A', {
        'dh_id': '[...]13A',
        'name': '[...]13A',
        'alt_names': [],
        'roles': [],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_lac13b_full_row() -> None:
    _assert_full_row('[...]13B', {
        'dh_id': '[...]13B',
        'name': '[...]13B',
        'alt_names': [],
        'roles': [],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_lac13c_full_row() -> None:
    _assert_full_row('[...]13C', {
        'dh_id': '[...]13C',
        'name': '[...]13C',
        'alt_names': [],
        'roles': [],
        'sex': 'male',
        'spouse_names': ['Iuhetibu A'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_lac13d_full_row() -> None:
    _assert_full_row('[...]13D', {
        'dh_id': '[...]13D',
        'name': '[...]13D',
        'alt_names': [],
        'roles': ['GF'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Sobkhotep V'],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_lac13e_full_row() -> None:
    _assert_full_row('[...]13E', {
        'dh_id': '[...]13E',
        'name': '[...]13E',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': ['Reniseneb B'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_amenhotep_a_full_row() -> None:
    _assert_full_row('Amenhotep A', {
        'dh_id': 'Amenhotep A',
        'name': 'Amenhotep A',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Sobkhotep IV',
        'mother_name': 'Tjin',
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_ankhu_a_full_row() -> None:
    _assert_full_row('Ankhu A', {
        'dh_id': 'Ankhu A',
        'name': 'Ankhu A',
        'alt_names': [],
        'roles': ['Overseer of the Fields'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': 'Merestekhi',
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_ankhu_b_full_row() -> None:
    _assert_full_row('Ankhu B', {
        'dh_id': 'Ankhu B',
        'name': 'Ankhu B',
        'alt_names': [],
        'roles': ['Viz'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_aya_a_full_row() -> None:
    _assert_full_row('Aya A', {
        'dh_id': 'Aya A',
        'name': 'Aya A',
        'alt_names': [],
        'roles': ['Governor of El-Kab'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_aya_b_full_row() -> None:
    _assert_full_row('Aya B', {
        'dh_id': 'Aya B',
        'name': 'Aya B',
        'alt_names': [],
        'roles': ['Viz', 'Governor of El-Kab'],
        'sex': 'male',
        'spouse_names': ['Reditenes B'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_aya_c_full_row() -> None:
    _assert_full_row('Aya C', {
        'dh_id': 'Aya C',
        'name': 'Aya C',
        'alt_names': [],
        'roles': ['Governor of El-Kab'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Aya B',
        'mother_name': 'Reditenes B',
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_ayameru_a_full_row() -> None:
    _assert_full_row('Ayameru A', {
        'dh_id': 'Ayameru A',
        'name': 'Ayameru A',
        'alt_names': [],
        'roles': [],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Aya A'],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_ayameru_b_full_row() -> None:
    _assert_full_row('Ayameru B', {
        'dh_id': 'Ayameru B',
        'name': 'Ayameru B',
        'alt_names': [],
        'roles': ['Viz', 'Governor of El-Kab'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Aya B',
        'mother_name': 'Reditenes B',
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_bebi_a_full_row() -> None:
    _assert_full_row('Bebi A', {
        'dh_id': 'Bebi A',
        'name': 'Bebi A',
        'alt_names': [],
        'roles': ['KSis'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_bebi_b_full_row() -> None:
    _assert_full_row('Bebi B', {
        'dh_id': 'Bebi B',
        'name': 'Bebi B',
        'alt_names': [],
        'roles': ['KSis'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_bebi_c_full_row() -> None:
    _assert_full_row('Bebi C', {
        'dh_id': 'Bebi C',
        'name': 'Bebi C',
        'alt_names': [],
        'roles': ['EKSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Sobkhotep VII',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_bebires_full_row() -> None:
    _assert_full_row('Bebires', {
        'dh_id': 'Bebires',
        'name': 'Bebires',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': 'Nubkhaes A',
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_dedetanuq_full_row() -> None:
    _assert_full_row('Dedetanuq', {
        'dh_id': 'Dedetanuq',
        'name': 'Dedetanuq',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Sobkhotep III',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_dedusobk_bebi_full_row() -> None:
    _assert_full_row('Dedusobk Bebi', {
        'dh_id': 'Dedusobk Bebi',
        'name': 'Dedusobk Bebi',
        'alt_names': [],
        'roles': ['Chief Scribe of the Vizier'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Nubkhaes A'],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_duaneferet_a_full_row() -> None:
    _assert_full_row('Duaneferet A', {
        'dh_id': 'Duaneferet A',
        'name': 'Duaneferet A',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Nubkhaes A'],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_duaneferet_b_full_row() -> None:
    _assert_full_row('Duaneferet B', {
        'dh_id': 'Duaneferet B',
        'name': 'Duaneferet B',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': 'Nubkhaes A',
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_haankhef_a_full_row() -> None:
    _assert_full_row('Haankhef A', {
        'dh_id': 'Haankhef A',
        'name': 'Haankhef A',
        'alt_names': [],
        'roles': ['GF'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Neferhotep I', 'Sihathor', 'Sobkhotep IV'],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_haankhef_b_full_row() -> None:
    _assert_full_row('Haankhef B', {
        'dh_id': 'Haankhef B',
        'name': 'Haankhef B',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Neferhotep I',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_haankhef_c_ikherneferet_full_row() -> None:
    _assert_full_row('Haankhef C Ikherneferet', {
        'dh_id': 'Haankhef C Ikherneferet',
        'name': 'Haankhef C Ikherneferet',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Sobkhotep IV',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_hapyu_full_row() -> None:
    _assert_full_row('Hapyu', {
        'dh_id': 'Hapyu',
        'name': 'Hapyu',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_hatshepsut_b_full_row() -> None:
    _assert_full_row('Hatshepsut B', {
        'dh_id': 'Hatshepsut B',
        'name': 'Hatshepsut B',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': ['Neferhotep B'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_henut_a_full_row() -> None:
    _assert_full_row('Henut A', {
        'dh_id': 'Henut A',
        'name': 'Henut A',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Seneb B',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_hetepti_full_row() -> None:
    """Hetepti is a cross-section duplicate: the stub here (Kings and
    Commoners / Dyn 13) points back to her full Brief Life in the
    Seizers of the Two Lands / Dyn 12 chunk. The composite key resolves
    both; this test explicitly passes `sub_period` so `_row` picks the
    Kings and Commoners stub row.
    """
    _assert_full_row('Hetepti', {
        'dh_id': 'Hetepti',
        'name': 'Hetepti',
        'alt_names': [],
        'roles': ['KM', 'M2L', 'UWC'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    }, sub_period=SUB_PERIOD_KC)


def test_kc_horemheb_a_full_row() -> None:
    _assert_full_row('Horemheb A', {
        'dh_id': 'Horemheb A',
        'name': 'Horemheb A',
        'alt_names': [],
        'roles': ['KSis'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_inni_full_row() -> None:
    _assert_full_row('Inni', {
        'dh_id': 'Inni',
        'name': 'Inni',
        'alt_names': [],
        'roles': ['KGW', 'UWC'],
        'sex': 'female',
        'spouse_names': ['Aya (possible)'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_inyotef_b_full_row() -> None:
    _assert_full_row('Inyotef B', {
        'dh_id': 'Inyotef B',
        'name': 'Inyotef B',
        'alt_names': [],
        'roles': [],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Amenemhat V (probable)',
        'mother_name': None,
        'children_names': ['Amenemhat VI'],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_inyotef_c_full_row() -> None:
    _assert_full_row('Inyotef C', {
        'dh_id': 'Inyotef C',
        'name': 'Inyotef C',
        'alt_names': [],
        'roles': ['RO'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_iuhetibu_a_full_row() -> None:
    _assert_full_row('Iuhetibu A', {
        'dh_id': 'Iuhetibu A',
        'name': 'Iuhetibu A',
        'alt_names': [],
        'roles': ['KM'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Sobkhotep III'],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_iuhetibu_b_fendy_full_row() -> None:
    _assert_full_row('Iuhetibu B Fendy', {
        'dh_id': 'Iuhetibu B Fendy',
        'name': 'Iuhetibu B Fendy',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Sobkhotep III',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_iuhetibu_c_full_row() -> None:
    _assert_full_row('Iuhetibu C', {
        'dh_id': 'Iuhetibu C',
        'name': 'Iuhetibu C',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Seneb B',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_iy_full_row() -> None:
    _assert_full_row('Iy', {
        'dh_id': 'Iy',
        'name': 'Iy',
        'alt_names': [],
        'roles': ['KW'],
        'sex': 'female',
        'spouse_names': ['Imyromesha (either) (probably)', 'Inyotef IV (either) (probably)'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_kay_full_row() -> None:
    _assert_full_row('Kay', {
        'dh_id': 'Kay',
        'name': 'Kay',
        'alt_names': [],
        'roles': [],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Amenemhat VII'],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_kebsi_full_row() -> None:
    _assert_full_row('Kebsi', {
        'dh_id': 'Kebsi',
        'name': 'Kebsi',
        'alt_names': [],
        'roles': ['Governor of El-Kab'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Ayameru B',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_kemi_a_full_row() -> None:
    _assert_full_row('Kemi A', {
        'dh_id': 'Kemi A',
        'name': 'Kemi A',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Neferhotep I', 'Sihathor', 'Sobkhotep IV'],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_kemi_b_full_row() -> None:
    _assert_full_row('Kemi B', {
        'dh_id': 'Kemi B',
        'name': 'Kemi B',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Neferhotep I',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_khakau_full_row() -> None:
    _assert_full_row('Khakau', {
        'dh_id': 'Khakau',
        'name': 'Khakau',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_khemmet_full_row() -> None:
    _assert_full_row('Khemmet', {
        'dh_id': 'Khemmet',
        'name': 'Khemmet',
        'alt_names': [],
        'roles': ['KSis'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_khonskhufsy_full_row() -> None:
    _assert_full_row('Khonskhufsy', {
        'dh_id': 'Khonskhufsy',
        'name': 'Khonskhufsy',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': ['Aya A'],
        'father_name': None,
        'mother_name': 'Nubkhaes A',
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_mentuhotep_a_full_row() -> None:
    _assert_full_row('Mentuhotep A', {
        'dh_id': 'Mentuhotep A',
        'name': 'Mentuhotep A',
        'alt_names': [],
        'roles': ['GF'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Sobkhotep III'],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_mentuhotep_b_full_row() -> None:
    _assert_full_row('Mentuhotep B', {
        'dh_id': 'Mentuhotep B',
        'name': 'Mentuhotep B',
        'alt_names': [],
        'roles': ['Attendant of Dog-Keepers'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Seneb B',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_merestekhi_full_row() -> None:
    _assert_full_row('Merestekhi', {
        'dh_id': 'Merestekhi',
        'name': 'Merestekhi',
        'alt_names': [],
        'roles': ['KSis'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Ankhu A'],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_minemaes_full_row() -> None:
    _assert_full_row('Minemaes', {
        'dh_id': 'Minemaes',
        'name': 'Minemaes',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Se[...]kare (possibly)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_nebankh_full_row() -> None:
    _assert_full_row('Nebankh', {
        'dh_id': 'Nebankh',
        'name': 'Nebankh',
        'alt_names': [],
        'roles': ['High Steward'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_nebetiunet_a_full_row() -> None:
    _assert_full_row('Nebetiunet A', {
        'dh_id': 'Nebetiunet A',
        'name': 'Nebetiunet A',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Sobkhotep IV',
        'mother_name': 'Tjin',
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_nebtit_full_row() -> None:
    _assert_full_row('Nebtit', {
        'dh_id': 'Nebtit',
        'name': 'Nebtit',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': ['Seneb B'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_neferetiu_full_row() -> None:
    _assert_full_row('Neferetiu', {
        'dh_id': 'Neferetiu',
        'name': 'Neferetiu',
        'alt_names': [],
        'roles': ['KSis'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_neferhotep_a_full_row() -> None:
    _assert_full_row('Neferhotep A', {
        'dh_id': 'Neferhotep A',
        'name': 'Neferhotep A',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': ['Ressonbe'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_neferhotep_b_full_row() -> None:
    _assert_full_row('Neferhotep B', {
        'dh_id': 'Neferhotep B',
        'name': 'Neferhotep B',
        'alt_names': [],
        'roles': [],
        'sex': 'male',
        'spouse_names': ['Hatshepsut B'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_neferu_a_full_row() -> None:
    _assert_full_row('Neferu A', {
        'dh_id': 'Neferu A',
        'name': 'Neferu A',
        'alt_names': [],
        'roles': ['KSis'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_nehy_full_row() -> None:
    _assert_full_row('Nehy', {
        'dh_id': 'Nehy',
        'name': 'Nehy',
        'alt_names': [],
        'roles': ['Townsman'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_nenqlac_full_row() -> None:
    _assert_full_row('Nen?[...]', {
        'dh_id': 'Nen?[...]',
        'name': 'Nen?[...]',
        'alt_names': [],
        'roles': [],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Sobkhotep II'],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_neni_full_row() -> None:
    _assert_full_row('Neni', {
        'dh_id': 'Neni',
        'name': 'Neni',
        'alt_names': [],
        'roles': ['KW'],
        'sex': 'female',
        'spouse_names': ['Sobkhotep III'],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Iuhetibu B', 'Dedetanuq'],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_neshemethotepti_full_row() -> None:
    _assert_full_row('Neshemethotepti', {
        'dh_id': 'Neshemethotepti',
        'name': 'Neshemethotepti',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_nubhotepti_a_full_row() -> None:
    _assert_full_row('Nubhotepti A', {
        'dh_id': 'Nubhotepti A',
        'name': 'Nubhotepti A',
        'alt_names': [],
        'roles': ['KGW', 'UWC', 'KM'],
        'sex': 'female',
        'spouse_names': ['Hor (probable)'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_nubhotepti_b_full_row() -> None:
    _assert_full_row('Nubhotepti B', {
        'dh_id': 'Nubhotepti B',
        'name': 'Nubhotepti B',
        'alt_names': [],
        'roles': ['KM'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Sobkhotep V'],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_nubhoteptikhered_full_row() -> None:
    _assert_full_row('Nubhoteptikhered', {
        'dh_id': 'Nubhoteptikhered',
        'name': 'Nubhoteptikhered',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Hor (probable)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_nubkhaes_a_full_row() -> None:
    _assert_full_row('Nubkhaes A', {
        'dh_id': 'Nubkhaes A',
        'name': 'Nubkhaes A',
        'alt_names': [],
        'roles': ['KGW', 'UWC'],
        'sex': 'female',
        'spouse_names': ['Sobkhotep V (probable)', 'Sobkhotep VI (probable)', 'Iaib (probable)'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_peshu_full_row() -> None:
    _assert_full_row('Peshu', {
        'dh_id': 'Peshu',
        'name': 'Peshu',
        'alt_names': [],
        'roles': ['KSis'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_redienef_full_row() -> None:
    _assert_full_row('Redienef', {
        'dh_id': 'Redienef',
        'name': 'Redienef',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': 'Iy',
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_reditenes_a_full_row() -> None:
    _assert_full_row('Reditenes A', {
        'dh_id': 'Reditenes A',
        'name': 'Reditenes A',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': ['Ayameru A'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_reditenes_b_full_row() -> None:
    _assert_full_row('Reditenes B', {
        'dh_id': 'Reditenes B',
        'name': 'Reditenes B',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': ['Aya B'],
        'father_name': 'King Aya (probable)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_reniseneb_a_full_row() -> None:
    _assert_full_row('Reniseneb A', {
        'dh_id': 'Reniseneb A',
        'name': 'Reniseneb A',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_reniseneb_b_full_row() -> None:
    _assert_full_row('Reniseneb B', {
        'dh_id': 'Reniseneb B',
        'name': 'Reniseneb B',
        'alt_names': [],
        'roles': [],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_resi_full_row() -> None:
    _assert_full_row('Resi', {
        'dh_id': 'Resi',
        'name': 'Resi',
        'alt_names': [],
        'roles': ['KSis'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_ressonbe_full_row() -> None:
    _assert_full_row('Ressonbe', {
        'dh_id': 'Ressonbe',
        'name': 'Ressonbe',
        'alt_names': [],
        'roles': [],
        'sex': 'male',
        'spouse_names': ['Neferhotep A'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_sankhptahi_full_row() -> None:
    _assert_full_row('Sankhptahi', {
        'dh_id': 'Sankhptahi',
        'name': 'Sankhptahi',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Se[...]kare (possibly)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_seb_full_row() -> None:
    _assert_full_row('Seb', {
        'dh_id': 'Seb',
        'name': 'Seb',
        'alt_names': [],
        'roles': [],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_seneb_a_full_row() -> None:
    _assert_full_row('Seneb A', {
        'dh_id': 'Seneb A',
        'name': 'Seneb A',
        'alt_names': [],
        'roles': ['KSis'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_seneb_b_full_row() -> None:
    _assert_full_row('Seneb B', {
        'dh_id': 'Seneb B',
        'name': 'Seneb B',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_senebhenas_a_full_row() -> None:
    _assert_full_row('Seneb[henas A]', {
        'dh_id': 'Seneb[henas A]',
        'name': 'Seneb[henas A]',
        'alt_names': [],
        'roles': ['KW'],
        'sex': 'female',
        'spouse_names': ['Khendjer (probable)'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_senebhenas_b_full_row() -> None:
    _assert_full_row('Senebhenas B', {
        'dh_id': 'Senebhenas B',
        'name': 'Senebhenas B',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_senebhenas_c_full_row() -> None:
    _assert_full_row('Senebhenas C', {
        'dh_id': 'Senebhenas C',
        'name': 'Senebhenas C',
        'alt_names': [],
        'roles': ['KW', 'UWC'],
        'sex': 'female',
        'spouse_names': ['Sobkhotep III'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_senebsen_full_row() -> None:
    _assert_full_row('Senebsen', {
        'dh_id': 'Senebsen',
        'name': 'Senebsen',
        'alt_names': [],
        'roles': ['KW'],
        'sex': 'female',
        'spouse_names': ['Neferhotep I'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_senebtisi_full_row() -> None:
    _assert_full_row('Senebtisi', {
        'dh_id': 'Senebtisi',
        'name': 'Senebtisi',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_sihathor_full_row() -> None:
    _assert_full_row('Sihathor', {
        'dh_id': 'Sihathor',
        'name': 'Sihathor',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_sitlacb_full_row() -> None:
    _assert_full_row('Sit[...]B', {
        'dh_id': 'Sit[...]B',
        'name': 'Sit[...]B',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Se[...]kare (possibly)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_sithathor_c_full_row() -> None:
    _assert_full_row('Sithathor C', {
        'dh_id': 'Sithathor C',
        'name': 'Sithathor C',
        'alt_names': [],
        'roles': ['KSis'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_sobkhotep_a_full_row() -> None:
    _assert_full_row('Sobkhotep A', {
        'dh_id': 'Sobkhotep A',
        'name': 'Sobkhotep A',
        'alt_names': [],
        'roles': ['Elder of the Portal'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Seneb B',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_sobkhotep_b_full_row() -> None:
    _assert_full_row('Sobkhotep B', {
        'dh_id': 'Sobkhotep B',
        'name': 'Sobkhotep B',
        'alt_names': [],
        'roles': ['High Steward'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_sobkhotep_c_full_row() -> None:
    _assert_full_row('Sobkhotep C', {
        'dh_id': 'Sobkhotep C',
        'name': 'Sobkhotep C',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_sobkhotep_d_miu_full_row() -> None:
    _assert_full_row('Sobkhotep D Miu', {
        'dh_id': 'Sobkhotep D Miu',
        'name': 'Sobkhotep D Miu',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Sobkhotep IV',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_sobkhotep_e_djadja_full_row() -> None:
    _assert_full_row('Sobkhotep E Djadja', {
        'dh_id': 'Sobkhotep E Djadja',
        'name': 'Sobkhotep E Djadja',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Sobkhotep IV',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_sobkhotep_f_full_row() -> None:
    _assert_full_row('Sobkhotep F', {
        'dh_id': 'Sobkhotep F',
        'name': 'Sobkhotep F',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Sihathor (probable)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_sobkhotep_g_full_row() -> None:
    _assert_full_row('Sobkhotep G', {
        'dh_id': 'Sobkhotep G',
        'name': 'Sobkhotep G',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': 'Sobkhotep VII',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_tjin_full_row() -> None:
    _assert_full_row('Tjin', {
        'dh_id': 'Tjin',
        'name': 'Tjin',
        'alt_names': [],
        'roles': ['KW'],
        'sex': 'female',
        'spouse_names': ['Sobkhotep IV'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_wepwawethotep_full_row() -> None:
    _assert_full_row('Wepwawethotep', {
        'dh_id': 'Wepwawethotep',
        'name': 'Wepwawethotep',
        'alt_names': [],
        'roles': ['Royal Representative'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': False,
        'source_citation': CITATION_KC,
    })


def test_kc_lacdjeb_full_row() -> None:
    _assert_full_row('[...]djeb', {
        'dh_id': '[...]djeb',
        'name': '[...]djeb',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_ahhotepti_full_row() -> None:
    _assert_full_row('Ahhotepti', {
        'dh_id': 'Ahhotepti',
        'name': 'Ahhotepti',
        'alt_names': [],
        'roles': ['KW', 'KM'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_anuqneferetweben_full_row() -> None:
    _assert_full_row('Anuqneferetweben', {
        'dh_id': 'Anuqneferetweben',
        'name': 'Anuqneferetweben',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_dedetamun_full_row() -> None:
    _assert_full_row('Dedetamun', {
        'dh_id': 'Dedetamun',
        'name': 'Dedetamun',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': ['Nebsenet'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_dedetsobk_full_row() -> None:
    _assert_full_row('Dedetsobk', {
        'dh_id': 'Dedetsobk',
        'name': 'Dedetsobk',
        'alt_names': [],
        'roles': ['KSis'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Dedusobk A',
        'mother_name': 'Iuhetibu Q',
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_dedusobk_a_full_row() -> None:
    _assert_full_row('Dedusobk A', {
        'dh_id': 'Dedusobk A',
        'name': 'Dedusobk A',
        'alt_names': [],
        'roles': ['GF'],
        'sex': 'male',
        'spouse_names': ['Iuhetibu Q'],
        'father_name': 'Bebiankh (Q)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_haankhef_q_full_row() -> None:
    _assert_full_row('Haankhef Q', {
        'dh_id': 'Haankhef Q',
        'name': 'Haankhef Q',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_hatshepsut_c_full_row() -> None:
    _assert_full_row('Hatshepsut C', {
        'dh_id': 'Hatshepsut C',
        'name': 'Hatshepsut C',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': ['Nedjesankh-Iu'],
        'father_name': None,
        'mother_name': 'Neferet R',
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_horhotep_q_full_row() -> None:
    _assert_full_row('Horhotep Q', {
        'dh_id': 'Horhotep Q',
        'name': 'Horhotep Q',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_iuhetibu_q_full_row() -> None:
    _assert_full_row('Iuhetibu Q', {
        'dh_id': 'Iuhetibu Q',
        'name': 'Iuhetibu Q',
        'alt_names': [],
        'roles': ['KM'],
        'sex': 'female',
        'spouse_names': ['Dedusobk A'],
        'father_name': 'Senwosret (Q)',
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_neferet_r_full_row() -> None:
    _assert_full_row('Neferet R', {
        'dh_id': 'Neferet R',
        'name': 'Neferet R',
        'alt_names': [],
        'roles': ['KW'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Hatshepsut C'],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_neferhotep_q_full_row() -> None:
    _assert_full_row('Neferhotep Q', {
        'dh_id': 'Neferhotep Q',
        'name': 'Neferhotep Q',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_neferu_q_full_row() -> None:
    _assert_full_row('Neferu Q', {
        'dh_id': 'Neferu Q',
        'name': 'Neferu Q',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': ['Sobkhotep'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_reniseneb_q_full_row() -> None:
    _assert_full_row('Reniseneb Q', {
        'dh_id': 'Reniseneb Q',
        'name': 'Reniseneb Q',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_reniseneb_r_full_row() -> None:
    _assert_full_row('Reniseneb R', {
        'dh_id': 'Reniseneb R',
        'name': 'Reniseneb R',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_senetmut_full_row() -> None:
    _assert_full_row('Senetmut', {
        'dh_id': 'Senetmut',
        'name': 'Senetmut',
        'alt_names': [],
        'roles': ['KSis'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Dedusobk A',
        'mother_name': 'Iuhetibu Q',
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_kc_sobkhotep_q_full_row() -> None:
    _assert_full_row('Sobkhotep Q', {
        'dh_id': 'Sobkhotep Q',
        'name': 'Sobkhotep Q',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 13,
        "sub_period": SUB_PERIOD_KC,
        'unplaced': True,
        'source_citation': CITATION_KC,
    })


def test_founders_lac1a_full_row() -> None:
    _assert_full_row('[...]1A', {
        'dh_id': '[...]1A',
        'name': '[...]1A',
        'alt_names': [],
        'roles': ['SH'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': False,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_batirytes_full_row() -> None:
    _assert_full_row('Batirytes', {
        'dh_id': 'Batirytes',
        'name': 'Batirytes',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Semerkhet'],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': False,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_benerib_full_row() -> None:
    _assert_full_row('Benerib', {
        'dh_id': 'Benerib',
        'name': 'Benerib',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': ['Hor-Aha (presumably)'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': False,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_herneith_full_row() -> None:
    _assert_full_row('Herneith', {
        'dh_id': 'Herneith',
        'name': 'Herneith',
        'alt_names': [],
        'roles': ['CTL', 'FW'],
        'sex': 'female',
        'spouse_names': ['Djer (probable)'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': False,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_hotephirnebty_full_row() -> None:
    _assert_full_row('Hotephirnebty', {
        'dh_id': 'Hotephirnebty',
        'name': 'Hotephirnebty',
        'alt_names': [],
        'roles': ['SH', 'KD', 'GS'],
        'sex': 'female',
        'spouse_names': ['Djoser'],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': False,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_intkaes_full_row() -> None:
    _assert_full_row('Intkaes', {
        'dh_id': 'Intkaes',
        'name': 'Intkaes',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': 'Djoser',
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': False,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_khenthap_full_row() -> None:
    _assert_full_row('Khenthap', {
        'dh_id': 'Khenthap',
        'name': 'Khenthap',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Djer'],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': False,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_meryetneith_a_full_row() -> None:
    _assert_full_row('Meryetneith A', {
        'dh_id': 'Meryetneith A',
        'name': 'Meryetneith A',
        'alt_names': [],
        'roles': ['FW', 'KM'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': ['Den'],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': False,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_nakhtneith_full_row() -> None:
    _assert_full_row('Nakhtneith', {
        'dh_id': 'Nakhtneith',
        'name': 'Nakhtneith',
        'alt_names': [],
        'roles': ['SCH'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': False,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_neithhotep_a_full_row() -> None:
    _assert_full_row('Neithhotep A', {
        'dh_id': 'Neithhotep A',
        'name': 'Neithhotep A',
        'alt_names': [],
        'roles': ['CTL', 'FW'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': False,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_nymaathap_a_full_row() -> None:
    _assert_full_row('Nymaathap A', {
        'dh_id': 'Nymaathap A',
        'name': 'Nymaathap A',
        'alt_names': [],
        'roles': ['GS', 'KM', 'KW'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': False,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_perneb_full_row() -> None:
    _assert_full_row('Perneb', {
        'dh_id': 'Perneb',
        'name': 'Perneb',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': False,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_semat_full_row() -> None:
    _assert_full_row('Semat', {
        'dh_id': 'Semat',
        'name': 'Semat',
        'alt_names': [],
        'roles': ['SH'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': False,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_serethor_full_row() -> None:
    _assert_full_row('Serethor', {
        'dh_id': 'Serethor',
        'name': 'Serethor',
        'alt_names': [],
        'roles': [],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': False,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_seshemetka_full_row() -> None:
    _assert_full_row('Seshemetka', {
        'dh_id': 'Seshemetka',
        'name': 'Seshemetka',
        'alt_names': [],
        'roles': ['SH', 'ScH'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': False,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_khnemetptah_full_row() -> None:
    _assert_full_row('Khnemetptah', {
        'dh_id': 'Khnemetptah',
        'name': 'Khnemetptah',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': True,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_menehpet_full_row() -> None:
    _assert_full_row('Menehpet', {
        'dh_id': 'Menehpet',
        'name': 'Menehpet',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': True,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_mesenka_full_row() -> None:
    _assert_full_row('Mesenka', {
        'dh_id': 'Mesenka',
        'name': 'Mesenka',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': True,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_neithhotep_b_full_row() -> None:
    _assert_full_row('Neithhotep B', {
        'dh_id': 'Neithhotep B',
        'name': 'Neithhotep B',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': True,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_nysuheqat_full_row() -> None:
    _assert_full_row('Nysuheqat', {
        'dh_id': 'Nysuheqat',
        'name': 'Nysuheqat',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': True,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_qaienneith_full_row() -> None:
    _assert_full_row('Qaienneith', {
        'dh_id': 'Qaienneith',
        'name': 'Qaienneith',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': True,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_redji_full_row() -> None:
    """Redji — `dynasty: 3` refined via `FOUNDERS_CORRECTIONS` from the
    notes cue 'dated stylistically to the 3rd Dynasty.'. Default is
    `dynasty: 1` (D&H's Ch-1-joint-dynasties section placement); the
    refinement preserves on-row evidence per rule 1.
    """
    _assert_full_row('Redji', {
        'dh_id': 'Redji',
        'name': 'Redji',
        'alt_names': [],
        'roles': ['KDB'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 3,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': True,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_shepsetipet_full_row() -> None:
    """Shepsetipet — `dynasty: 2` refined from the notes cue."""
    _assert_full_row('Shepsetipet', {
        'dh_id': 'Shepsetipet',
        'name': 'Shepsetipet',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 2,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': True,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_sitba_full_row() -> None:
    """Sitba — `dynasty: 2` refined from the notes cue."""
    _assert_full_row('Sitba', {
        'dh_id': 'Sitba',
        'name': 'Sitba',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 2,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': True,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_syhefernerer_full_row() -> None:
    """Syhefernerer — `dynasty: 2` refined from the notes cue."""
    _assert_full_row('Syhefernerer', {
        'dh_id': 'Syhefernerer',
        'name': 'Syhefernerer',
        'alt_names': [],
        'roles': ['KD'],
        'sex': 'female',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 2,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': True,
        'source_citation': CITATION_FOUNDERS,
    })


def test_founders_wadjetefni_full_row() -> None:
    _assert_full_row('Wadjetefni', {
        'dh_id': 'Wadjetefni',
        'name': 'Wadjetefni',
        'alt_names': [],
        'roles': ['KSon'],
        'sex': 'male',
        'spouse_names': [],
        'father_name': None,
        'mother_name': None,
        'children_names': [],
        'dynasty': 1,
        "sub_period": SUB_PERIOD_FOUNDERS,
        'unplaced': True,
        'source_citation': CITATION_FOUNDERS,
    })


# ---------------------------------------------------------------------------
# Audit-trail invariants on merge-disagreements.txt
# ---------------------------------------------------------------------------


DIFF_FILE = SOURCE_DIR / "merge-disagreements.txt"
LLM_OVERRIDE_MARKER = "LLM-APPLIED OVERRIDES — NOT HUMAN-VALIDATED"


_ROW_HEADER_RE = re.compile(r".+\(.+\):$")


def _disagreement_blocks() -> list[list[str]]:
    """Return the per-row disagreement-field-line lists from the
    pre-LLM-OVERRIDES portion of merge-disagreements.txt.

    Each block is the consecutive `  <field>: ...` lines under a row
    header (e.g. `Henttawy Q (Henttawy Q):`). Blocks with a single
    field line are still returned (the sortedness invariant on those
    blocks is trivial but cheap).

    Raises on a non-indented, non-blank line that doesn't match the
    canonical row-header shape — a malformed boundary would silently
    skip the affected block under a permissive parser, and the
    sortedness invariant would pass vacuously on whatever survived.
    """
    pre, _, _ = DIFF_FILE.read_text().partition(LLM_OVERRIDE_MARKER)
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in pre.splitlines():
        if line.startswith("  "):
            current.append(line)
            continue
        if current:
            blocks.append(current)
            current = []
        if line.strip() and not _ROW_HEADER_RE.match(line):
            raise AssertionError(
                f"unexpected non-indented line in merge-disagreements.txt: {line!r}"
            )
    if current:
        blocks.append(current)
    return blocks


def test_merge_disagreements_field_lines_are_sorted_within_each_row() -> None:
    """Per `merge.py`'s sorted `all_fields` iteration (issue #142):
    within each row's disagreement block, the field lines must be
    alphabetically ordered. Iterating an unsorted set produces a noisy
    diff every time merge.py regenerates the audit log even when the
    underlying disagreements are unchanged.
    """
    blocks = _disagreement_blocks()
    multi_field_blocks = [b for b in blocks if len(b) >= 2]
    assert multi_field_blocks, (
        "expected at least one multi-field disagreement block to exercise "
        "the sortedness invariant"
    )
    for block in multi_field_blocks:
        # `merge.py` emits each field line as `  <field>: <values>...`
        # so split on the first `: ` (colon-space) which only matches
        # the field-name terminator. Bare `.index(":")` would silently
        # extract a value substring if a value ever contained `:`.
        field_names = [line.lstrip().split(": ", 1)[0] for line in block]
        assert field_names == sorted(field_names), (
            f"disagreement-field lines not sorted within block: {field_names}"
        )


def test_llm_applied_overrides_section_describes_every_spot_correction() -> None:
    """Per `fix_rows.py`'s state-not-delta log (issue #54 bug 2): the
    LLM-APPLIED OVERRIDES section must describe every entry in
    `SPOT_CORRECTIONS` — not just the entries that this run mutated.
    A delta-style log breaks idempotence: re-running fix_rows.py after
    corrections are already applied silently turns the on-disk audit
    trail into "No overrides applied", lying about whether overrides
    are present.

    Each entry's per-row header (`- {dh_id} [{sub_period}]: {field}
    corrected`) must be followed by either `value:` (already-applied)
    or `was:` (run-applied) — pinning both halves of the audit shape
    so a regression that emits only headers without the trailing
    detail line would still fail loud.
    """
    import importlib.util

    fix_rows_path = SOURCE_DIR / "fix_rows.py"
    spec = importlib.util.spec_from_file_location("dh_fix_rows", fix_rows_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    text = DIFF_FILE.read_text()
    _, _, override_section = text.partition(LLM_OVERRIDE_MARKER)
    assert override_section, "merge-disagreements.txt is missing the LLM-APPLIED OVERRIDES section"
    assert "No overrides applied." not in override_section, (
        "LLM-APPLIED OVERRIDES section reports 'No overrides applied' even "
        "though SPOT_CORRECTIONS is non-empty — the delta-style log bug "
        "from issue #54 has regressed."
    )
    for dh_id, sub_period, field, _new_val, _rationale in mod.SPOT_CORRECTIONS:
        header = f"- {dh_id} [{sub_period}]: {field} corrected"
        idx = override_section.find(header)
        assert idx != -1, (
            f"missing audit entry for {(dh_id, sub_period, field)} — "
            f"the on-disk log no longer describes the full SPOT_CORRECTIONS set"
        )
        # The block following the header must carry either `value:`
        # (already-applied) or `was:` (run-applied) — header alone
        # would mean the per-entry detail line was silently dropped.
        tail_lines = override_section[idx:].splitlines()[1:6]
        assert any(
            line.lstrip().startswith(("value:", "was:")) for line in tail_lines
        ), (
            f"audit entry for {(dh_id, sub_period, field)} has no "
            f"value:/was: detail line — header without body is a regression"
        )


# ===========================================================================
# Of Kings and Priests (Dyn 21) full-row content tests — PR #218
# ===========================================================================
# Anchor the 5 flagship rows + the 2 P1-corrected rows so a future revert of
# either the `OFKINGSANDPRIESTS_CORRECTIONS` in fix_rows.py OR the
# `dh_id_corrections-ofkingsandpriests.json` pre-merge layer fails loud.


def test_okp_henttawy_q_full_row() -> None:
    """P1 correction anchor: relation-token roles + Duahathor-Henttawy alt_name."""
    _assert_full_row("Henttawy Q", {
        "dh_id": "Henttawy Q",
        "name": "Henttawy Q",
        "alt_names": ["Duahathor-Henttawy"],
        "roles": ["KD", "KW", "KM", "L2L", "M2L", "Daughter of: KGW", "1ChHA", "Mother of: KGW, HPA & Genmo"],
        "sex": "female",
        "spouse_names": ["Pinudjem I"],
        "father_name": "Ramesses XI",
        "mother_name": None,
        "children_names": ["Pasebkhanut I", "Maatkare A", "Masaharta B", "Djedkhonsiufankh I", "Menkheperre B"],
        "dynasty": 21,
        "sub_period": SUB_PERIOD_OKP,
        "unplaced": False,
        "source_citation": CITATION_OKP,
    }, sub_period=SUB_PERIOD_OKP)


def test_okp_maatkare_a_full_row() -> None:
    """P1 correction anchor: GWA: prenomen-Mutemhat colon-annotation split."""
    _assert_full_row("Maatkare A", {
        "dh_id": "Maatkare A",
        "name": "Maatkare A",
        "alt_names": ["Mutemhat"],
        "roles": ["KDB", "Ador", "GWA"],
        "sex": "female",
        "spouse_names": [],
        "father_name": "Pinudjem I",
        "mother_name": "Henttawy Q",
        "children_names": [],
        "dynasty": 21,
        "sub_period": SUB_PERIOD_OKP,
        "unplaced": False,
        "source_citation": CITATION_OKP,
    })


def test_okp_pinudjem_i_full_row() -> None:
    """Pinudjem I OKP — full Brief Life (contrasts with the stub
    `(see next section)` row in Decline of the Ramessides).
    """
    _assert_full_row("Pinudjem I", {
        "dh_id": "Pinudjem I",
        "name": "Pinudjem I",
        "alt_names": [],
        "roles": ["Viz", "HPA", "Genmo"],
        "sex": "male",
        "spouse_names": [],
        "father_name": "Piankh",
        "mother_name": None,
        "children_names": [],
        "dynasty": 21,
        "sub_period": SUB_PERIOD_OKP,
        "unplaced": False,
        "source_citation": CITATION_OKP,
    }, sub_period=SUB_PERIOD_OKP)


def test_okp_nesikhonsu_a_full_row() -> None:
    """Nesikhonsu A — TT320 cache burial cohort (year 5 Siamun). Pins the
    new `1ChHA` and `KSonK` role tokens added to KNOWN_ROLE_TOKENS.
    """
    _assert_full_row("Nesikhonsu A", {
        "dh_id": "Nesikhonsu A",
        "name": "Nesikhonsu A",
        "alt_names": [],
        "roles": ["1ChHA", "KSonK"],
        "sex": "female",
        "spouse_names": ["Pinudjem II"],
        "father_name": None,
        "mother_name": None,
        "children_names": ["Nesitanebetashru A"],
        "dynasty": 21,
        "sub_period": SUB_PERIOD_OKP,
        "unplaced": False,
        "source_citation": CITATION_OKP,
    })


def test_okp_shoshenq_b_full_row() -> None:
    """Shoshenq B — Libyan-chief nephew-of-Osorkon-the-Elder who became
    SHOSHENQ I (founder of Dyn 22). Anchors the `ChMa` (Chief of the Ma)
    role and the alt_names titlecase-from-BOLD-CAPITALS rule.
    """
    _assert_full_row("Shoshenq B", {
        "dh_id": "Shoshenq B",
        "name": "Shoshenq B",
        "alt_names": ["Shoshenq I"],
        "roles": ["ChMa"],
        "sex": "male",
        "spouse_names": [],
        "father_name": None,
        "mother_name": None,
        "children_names": [],
        "dynasty": 21,
        "sub_period": SUB_PERIOD_OKP,
        "unplaced": False,
        "source_citation": CITATION_OKP,
    })


# ===========================================================================
# pre_merge.py chunk-scoping (Gemini PR #218 round-2)
# ===========================================================================


def test_pre_merge_corrections_are_chunk_scoped(tmp_path, monkeypatch) -> None:
    """`apply_corrections` must only apply `dh_id_corrections-<chunk>.json`
    corrections to `agent-<tag>-<chunk>.jsonl` files where the chunk
    identifier matches. A future chunk that happens to share a wrong-
    spelling string with OKP must NOT silently inherit OKP's correction.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "pm_pre_merge",
        Path(__file__).parent.parent / "pipeline" / "authority" / "sources" / "dodson-hilton-queens" / "pre_merge.py",
    )
    assert spec is not None and spec.loader is not None
    pre_merge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pre_merge)

    # Two-chunk fixture: chunk A has corrections, chunk B has the same
    # wrong-spelling string but no corrections file. Expected: chunk A row
    # patched, chunk B row left untouched.
    fake_source = tmp_path / "source"
    fake_source.mkdir()
    fake_agent_dir = tmp_path / "raw"
    fake_agent_dir.mkdir()

    # Corrections file for chunk A only.
    (fake_source / "dh_id_corrections-chunka.json").write_text(
        json.dumps({"a|Mutnodjmet": {"canonical_dh_id": "Mutnodjmet B", "rationale": "test fixture"}}),
        encoding="utf-8",
    )

    chunka_path = fake_agent_dir / "agent-a-chunka.jsonl"
    chunkb_path = fake_agent_dir / "agent-a-chunkb.jsonl"
    chunka_path.write_text(
        json.dumps({"dh_id": "Mutnodjmet", "name": "Mutnodjmet", "other": "x"}) + "\n",
        encoding="utf-8",
    )
    chunkb_path.write_text(
        json.dumps({"dh_id": "Mutnodjmet", "name": "Mutnodjmet", "other": "y"}) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(pre_merge, "SOURCE_DIR", fake_source)

    counts = pre_merge.apply_corrections(fake_agent_dir)

    chunka_rows = [json.loads(l) for l in chunka_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    chunkb_rows = [json.loads(l) for l in chunkb_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    assert chunka_rows[0]["dh_id"] == "Mutnodjmet B", chunka_rows
    assert chunkb_rows[0]["dh_id"] == "Mutnodjmet", chunkb_rows
    assert counts[chunka_path.name] == 1
    assert counts[chunkb_path.name] == 0


def test_pre_merge_parse_agent_filename() -> None:
    """`_parse_agent_filename` extracts (tag, chunk) from suffix-bearing
    JSONL stems and rejects malformed forms."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "pm_pre_merge_parse",
        Path(__file__).parent.parent / "pipeline" / "authority" / "sources" / "dodson-hilton-queens" / "pre_merge.py",
    )
    assert spec is not None and spec.loader is not None
    pre_merge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pre_merge)

    assert pre_merge._parse_agent_filename("agent-a-ofkingsandpriests") == ("a", "ofkingsandpriests")
    assert pre_merge._parse_agent_filename("agent-b-power") == ("b", "power")
    assert pre_merge._parse_agent_filename("agent-c-chunk-with-dashes") == ("c", "chunk-with-dashes")
    # Bare single-chunk legacy form — no chunk suffix.
    assert pre_merge._parse_agent_filename("agent-a") is None
    # Wrong prefix.
    assert pre_merge._parse_agent_filename("merge-a-chunkfoo") is None
    # Empty tag.
    assert pre_merge._parse_agent_filename("agent--chunk") is None
