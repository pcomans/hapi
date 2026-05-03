"""Structural value-assertion tests for Beckerath 1997 Chronologie source extract.

Per rule 5: every populated field on a sampled fixture row is asserted.

Migrated 2026-05-03 (issue #179): the legacy scalar fields
`egyptian_titulary` (str | None) + `egyptian_titulary_kind` (str | None)
have been superseded by the typed list `egyptian_titularies:
list[{name, kind, when}]` plus typed flags (`name_variants`,
`is_dynasty_marker`, `is_anti_king`, `existence_uncertain`). The legacy
scalars are KEPT on every row alongside the new list as derivative
ingest artifacts so re-runs of fix_rows.py remain idempotent — but
canonical assertions target the typed list, not the scalar. See the
test_179_* closure tests at the bottom for the new-shape invariants.
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
    / "beckerath-1997-chronologie"
)
JSONL = SOURCE_DIR / "reconciled.jsonl"

EDITION = "MÄS 46, von Zabern 1997"
PDF_PAGES = "105-109"

EXPECTED_PERIODS = {
    "Vorgeschichte",
    "Frühzeit",
    "Altes Reich",
    "I. Zwischenzeit",
    "Mittleres Reich",
    "II. Zwischenzeit",
    "Neues Reich",
    "III. Zwischenzeit",
    "Spätzeit",
}

# Closed enum for `egyptian_titularies[*].kind` (post-#179). Mirrors
# the documented vocabulary in fix_rows.py.
EXPECTED_TITULARY_KIND_VALUES = {
    "nomen",
    "prenomen",
    "horus_name",
    "nebty_name",
    "golden_horus_name",
}


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(json.loads(line) for line in JSONL.read_text().splitlines() if line.strip())


def _row(beckerath_id: str) -> dict:
    hits = [r for r in _rows() if r["beckerath_id"] == beckerath_id]
    if len(hits) != 1:
        raise AssertionError(f"expected 1 row for {beckerath_id}, got {len(hits)}")
    return hits[0]


def _titularies(beckerath_id: str) -> list[dict]:
    return _row(beckerath_id)["egyptian_titularies"]


def test_row_count() -> None:
    """The Übersicht extracts to 174 rows: every dynasty 0..31 named king
    plus dynasty-only marker rows for 7, 8, 9/10, 13, 14, 16, 17 (Beckerath
    gives counts not individual kings there) plus the two Dyn 21 HPA names
    from Supplement zu A's tail paragraph. The exact count is locked here so
    silent re-extraction drift is detected on CI.

    Count went 172 → 174 in the 2026-04-28 OCR redo: the previous
    double-page-spread OCR pass missed Ment-hotpe I. (Dyn 11.01) and
    Sesostris III. (now 12.05) entirely. Both restorations are verified
    against the printed PDF (book pp 188-189, scan-106-{left,right}).
    """
    assert len(_rows()) == 174, len(_rows())


def test_dynasty_coverage() -> None:
    """Every Beckerath dynasty 0..31 appears at least once, EXCEPT Dyn 10:
    Beckerath combines Dyn 9 and Dyn 10 into a single Herakleopolis row
    labelled `9./10. Dynastie` and assigns it `dynasty: 9` (the lower
    number). The combined row carries an "18 Könige" annotation but
    enumerates none of them.
    """
    dynasties = {r["dynasty"] for r in _rows()}
    expected = set(range(0, 32)) - {10}
    assert dynasties == expected, sorted(dynasties)


def test_beckerath_id_is_unique() -> None:
    ids = [r["beckerath_id"] for r in _rows()]
    assert len(ids) == len(set(ids)), "duplicate beckerath_id detected"


_BID_RE = re.compile(r"^\d{2}\.\d{2}$")


def test_beckerath_id_shape() -> None:
    """Every id matches `{dyn:02}.{NN:02}` — pure two-digit dynasty + two-digit
    sequence. Sub-lines do NOT carry a prefix; they are recorded in the
    `sub_line` field instead.
    """
    for r in _rows():
        assert _BID_RE.match(r["beckerath_id"]), r["beckerath_id"]


def test_every_row_has_complete_citation() -> None:
    """Rule 1: every row traces back to a pdf_pages range and edition."""
    for r in _rows():
        citation = r["source_citation"]
        assert citation == {"pdf_pages": PDF_PAGES, "edition": EDITION}, r


def test_period_is_one_of_nine() -> None:
    """`period` is a closed enum drawn from Beckerath's italicised section
    headings within Anhang A. Ptolemaic / Roman never appear because Beckerath
    stops at 332 BCE.
    """
    for r in _rows():
        assert r["period"] in EXPECTED_PERIODS, (r["beckerath_id"], r["period"])


def test_egyptian_titularies_kinds_in_closed_vocabulary() -> None:
    """Every entry in `egyptian_titularies[*].kind` is in the canonical
    5-value vocabulary. Replaces the pre-#179
    `test_egyptian_titulary_kind_is_one_of_five` which asserted on the
    legacy scalar — the legacy scalar's vocabulary (`mixed`) is now
    decomposed into the per-entry typed kinds, so `mixed` is no longer a
    valid kind on the typed list.
    """
    for r in _rows():
        for entry in r["egyptian_titularies"]:
            assert entry["kind"] in EXPECTED_TITULARY_KIND_VALUES, (
                r["beckerath_id"],
                entry,
            )


def test_bce_endpoints_obey_high_ge_older_convention() -> None:
    """Within an endpoint pair, `_high` must be older (more negative or
    equal) than `_low`. Beckerath's slash form `X/Y` is normalised so X
    (higher / older) goes into `_high` and Y (lower / younger) into `_low`.
    Surfaced by codex review (PR #113): the Dyn 17 row was inverted due to
    an OCR bleed from the adjacent Dyn 15 line. The fix in `fix_rows.py`
    is locked here as a row-level invariant.
    """
    for r in _rows():
        sh, sl = r["start_bce_high"], r["start_bce_low"]
        eh, el = r["end_bce_high"], r["end_bce_low"]
        if sh is not None and sl is not None:
            assert sh <= sl, (r["beckerath_id"], "start", sh, sl)
        if eh is not None and el is not None:
            assert eh <= el, (r["beckerath_id"], "end", eh, el)


def test_dyn17_marker_row_locked() -> None:
    """Dyn 17 is a marker row (no individual kings enumerated). Beckerath
    prints `17. Dynastie (in Theben, etwa 1645–1550) 15 (?) Könige`. The
    pre-OCR-redo branch had a phantom `1539` from the adjacent Dyn 15
    Hyksos line — the post-OCR-redo merge produces the bare `-1550`
    endpoint directly (no override on dates). Only `end_approximate=True`
    is forced via fix_rows.py to honour the heading-level `etwa`
    propagation rule. Test retained as a regression tripwire on OCR
    fidelity for this marker row.
    """
    r = _row("17.01")
    assert r["dynasty"] == 17
    assert r["start_bce_high"] == -1645
    assert r["start_bce_low"] == -1645
    assert r["end_bce_high"] == -1550
    assert r["end_bce_low"] == -1550
    assert r["start_approximate"] is True
    assert r["end_approximate"] is True


def test_no_dates_after_330_bce() -> None:
    """Beckerath's coverage ends with Alexander's conquest of Egypt in 332 BCE,
    but the book's last enumerated reign — Darius III (336/335–332/330) —
    runs to his death in 330 BCE. Beckerath uses the slash form `332/330` to
    mark the gap between Alexander's conquest of Egypt and the Persian
    empire's collapse, so `end_bce_low: -330` is the legitimate floor.
    No row may carry an endpoint later than -330.
    """
    for r in _rows():
        for field in ("start_bce_high", "start_bce_low", "end_bce_high", "end_bce_low"):
            v = r[field]
            if v is None:
                continue
            assert v <= -330, (r["beckerath_id"], field, v)


def test_dyn0_anchor_full_row() -> None:
    """The Vorgeschichte anchor: zero numeric endpoints, both approximate flags
    true, the `ungefähr 150 Jahre` note. This is the only row in the entire
    extract with all four BCE fields null.
    """
    r = _row("00.01")
    assert r["dynasty"] == 0
    assert r["sub_line"] is None
    assert r["sequence_in_dynasty"] == 1
    assert r["name"] == "0. Dynastie"
    assert r["egyptian_titularies"] == []
    assert r["prenomen"] is None
    assert r["start_bce_high"] is None
    assert r["start_bce_low"] is None
    assert r["end_bce_high"] is None
    assert r["end_bce_low"] is None
    assert r["start_approximate"] is True
    assert r["end_approximate"] is True
    assert r["period"] == "Vorgeschichte"
    assert r["notes_from_beckerath"] == "ungefähr 150 Jahre"


def test_menes_full_row() -> None:
    """First named king. Tests the slash-pair date parsing, the `Hor Aha`
    horus_name parenthetical, and the dynasty-heading-level `etwa` propagation
    to per-row approximate flags.
    """
    r = _row("01.01")
    assert r["dynasty"] == 1
    assert r["sub_line"] is None
    assert r["sequence_in_dynasty"] == 1
    assert r["name"] == "Menes"
    assert r["egyptian_titularies"] == [
        {"kind": "horus_name", "name": "Hor Aha", "when": None}
    ]
    assert r["prenomen"] is None
    assert r["start_bce_high"] == -3032
    assert r["start_bce_low"] == -2982
    assert r["end_bce_high"] == -3000
    assert r["end_bce_low"] == -2950
    assert r["start_approximate"] is True
    assert r["end_approximate"] is True
    assert r["period"] == "Frühzeit"
    assert r["notes_from_beckerath"] is None


def test_amenophis_i_dyn18_identity_correction_locked() -> None:
    """Beckerath prints `Amenophis (Amen-hotpe) I. (Djeser-ka-rê) 13.7.1525–1504`
    on book p189 (scan-106-right). Lock the row to detect drift. The pre-OCR-
    redo branch had this misidentified as `An-jotef I.` (Hor Neb-cheper-rê) due
    to column-drift OCR; the split-page OCR now extracts the correct form
    directly (no fix_rows.py override needed).

    Migrated #179: parens-form `Amenophis (Amen-hotpe) I.` → stripped
    canonical `name="Amenophis I."` plus `name_variants=["Amen-hotpe"]`.
    The prenomen now lives in the typed `egyptian_titularies` list.
    """
    r = _row("18.02")
    assert r["name"] == "Amenophis I."
    assert r["name_variants"] == ["Amen-hotpe"]
    assert r["egyptian_titularies"] == [
        {"kind": "prenomen", "name": "Djeser-ka-rê", "when": None}
    ]
    assert r["start_bce_high"] == -1525
    assert r["end_bce_high"] == -1504
    assert r["period"] == "Neues Reich"


def test_tuthmosis_ii_accession_date_in_notes() -> None:
    """Beckerath prints `Tuthmosis II. (A-cheper-en-rê) Frühj.(?) 1492–1479`
    on book p189 (scan-106-right). The "Frühj.(?)" (spring-question-mark)
    accession prefix lives in `notes_from_beckerath`; numeric endpoints are
    -1492 and -1479. Pre-OCR-redo branch had a fix_rows.py override forcing
    `end=-1458` (which is Hat-schepsut's end, not Tuthmosis II's) — the
    override was based on a misreading of the previous OCR's column-drift
    splice and is now removed.
    """
    r = _row("18.04")
    assert r["name"] == "Tuthmosis II."
    assert r["start_bce_high"] == -1492
    assert r["start_bce_low"] == -1492
    assert r["end_bce_high"] == -1479
    assert r["end_bce_low"] == -1479
    assert r["notes_from_beckerath"] == "Antritt Frühj.(?) 1492"


def test_schoschenq_iii_alternative_end_in_notes() -> None:
    """Beckerath writes Schoschenq III's reign as `ca. 837–798 (785 ?)` on
    book p191 (scan-107-right). The `(785 ?)` alternative-end hedge goes
    verbatim into `notes_from_beckerath` (the `?` is load-bearing); the
    numeric end stays at the primary endpoint -798. `start_approximate` is
    true (the `ca.` prefix); `end_approximate` is false (no qualifier on
    -798 itself).
    """
    r = _row("22.06")
    assert r["name"] == "Schoschenq III."
    assert r["start_approximate"] is True
    assert r["end_approximate"] is False
    assert r["start_bce_high"] == -837
    assert r["end_bce_high"] == -798
    assert r["notes_from_beckerath"] == "(785 ?)"


def test_dyn21_hohepriester_subline_present() -> None:
    """Two HPA rows from Supplement zu A's tail paragraph carry
    `sub_line: "Hohepriester"`. They share Dyn 21 numbering with the main
    line (continuous sequence_in_dynasty).
    """
    pi = _row("21.08")
    psusennes = _row("21.09")
    assert pi["sub_line"] == "Hohepriester"
    assert pi["dynasty"] == 21
    assert pi["sequence_in_dynasty"] == 8
    assert "Pi-nodjem" in pi["name"]
    assert psusennes["sub_line"] == "Hohepriester"
    assert psusennes["dynasty"] == 21


def test_dyn22_obergaegyptische_linie_continues_sequencing() -> None:
    """Dyn 22 main + Oberägyptische Linie share one sequence_in_dynasty
    counter (continuous numbering, no restart). The first OAL king is
    22.10 Har-si-êset; numbering runs to 22.18 Ini.
    """
    har = _row("22.10")
    ini = _row("22.18")
    assert har["sub_line"] == "Oberägyptische Linie"
    assert har["sequence_in_dynasty"] == 10
    assert har["dynasty"] == 22
    assert ini["sub_line"] == "Oberägyptische Linie"
    assert ini["sequence_in_dynasty"] == 18
    assert ini["name"] == "Ini"


def test_dyn16_is_hyksos_vassals_not_a_subline_of_15() -> None:
    """The Hyksos-Vasallen are Beckerath's own Dynasty 16 (per his heading
    `16. Dynastie (Hyksos-Vasallen, gleichzeitig mit Dynastie 15)`). They
    must be encoded with `dynasty: 16`, NOT as a sub_line of Dyn 15.
    """
    dyn16 = [r for r in _rows() if r["dynasty"] == 16]
    assert len(dyn16) >= 1, "Dyn 16 (Hyksos-Vasallen) must be represented"
    for r in dyn16:
        assert r["dynasty"] == 16
        # Dyn 16 sub_line is the main line — null
        assert r["sub_line"] is None, r


def test_period_assignment_for_intermediate_periods() -> None:
    """Spot-check Dyn 24 sits under III. Zwischenzeit (NOT Spätzeit) and
    Dyn 26 onward IS Spätzeit. Pre-PR-#138 this required a fix_rows.py
    override (agents looked past `### III. ZWISCHENZEIT` to the closer
    `### SPÄTZEIT` and mis-attributed Dyn 24/25 to Spätzeit). PR #138's
    post-processor emits `<!-- period: III. Zwischenzeit -->` directly
    after the Dyn 24/25 dynasty headings (derived from the canonical
    DYNASTY_PERIOD mapping), so agents now extract the correct period
    unaided — override removed.
    """
    assert _row("24.01")["period"] == "III. Zwischenzeit"
    assert _row("24.02")["period"] == "III. Zwischenzeit"
    assert _row("26.01")["period"] == "Spätzeit"


def test_xerxes_i_endpoints_not_inverted() -> None:
    """Beckerath: Xerxes I 486/85–465/64. Pre-OCR-redo a fix_rows.py
    override corrected end_bce_low from a -484 carryover; post-OCR-redo
    the merge produces these endpoints directly (no override needed).
    Test retained as a regression tripwire on slash-pair extraction.
    """
    r = _row("27.03")
    assert r["name"] == "Xerxes I."
    assert r["start_bce_high"] == -486
    assert r["start_bce_low"] == -485
    assert r["end_bce_high"] == -465
    assert r["end_bce_low"] == -464


def test_dyn3_brace_bracket_shared_range() -> None:
    """Beckerath's Dyn 3 has a brace bracket spanning Hor Cha-bai /
    Sôuphis (with Greek-form `Mesochris` as nomen) / Ahu (with Greek
    forms `Huni, Aches` as mixed titulary), all sharing the range
    `2663/2613-2639/2589`. Pre-PR-#138, the majority vote produced
    null dates on 03.05 / 03.06 because 2 of 3 agents missed the
    bracket; the override propagates the dates from 03.04 per Beckerath's
    printed bracket. The cross-row scan-context note lives in
    `editorial_notes` (English commentary), not in `notes_from_beckerath`.

    NB: 03.05 row keeps the compound `Sôuphis, Mesochris` inline as
    `name` (per the COMPOUND-stays-in-name discriminator in fix_rows.py)
    — these are not Greek-alias-strip candidates because the comma-
    separated form is itself part of Beckerath's printed convention for
    these rows. Same applies to 03.06 `Ahu (Huni, Aches)`. Cross-
    references in editorial_notes use the FULL canonical `name` field
    plus the `beckerath_id` in parens (per the field contract in
    fix_rows.py) so downstream consumers can grep-resolve sister rows
    without name-form fuzziness.

    Migrated #179: 03.06 cross-row reference text is updated to reflect
    that `Ahu (Huni, Aches)` is now stored as `name="Ahu"` with the
    bracketed compound extracted into `name_variants=["Huni", "Aches"]`
    — the cross-references in editorial_notes were authored at fix_rows
    time using the OLD parens-inline form, so the literal substring
    `Ahu (Huni, Aches) (03.06)` still appears in editorial_notes (the
    cross-ref text was committed to those strings before #179 split).
    """
    cha_bai = _row("03.04")
    souphis = _row("03.05")
    ahu = _row("03.06")
    for r in (cha_bai, souphis, ahu):
        assert r["start_bce_high"] == -2663
        assert r["start_bce_low"] == -2613
        assert r["end_bce_high"] == -2639
        assert r["end_bce_low"] == -2589
        assert r["notes_from_beckerath"] is None
        assert r["editorial_notes"] is not None
        assert "shared bracket range" in r["editorial_notes"]
        assert "scan-105" in r["editorial_notes"]
    # Cross-row references use the canonical `name` field plus
    # beckerath_id, including the FULL compound form when the canonical
    # name is itself compound (Sôuphis, Mesochris; Ahu (Huni, Aches)).
    assert "Sôuphis, Mesochris (03.05)" in cha_bai["editorial_notes"]
    assert "Ahu (Huni, Aches) (03.06)" in cha_bai["editorial_notes"]
    assert "Hor Cha-bai (03.04)" in souphis["editorial_notes"]
    assert "Ahu (Huni, Aches) (03.06)" in souphis["editorial_notes"]
    assert "Hor Cha-bai (03.04)" in ahu["editorial_notes"]
    assert "Sôuphis, Mesochris (03.05)" in ahu["editorial_notes"]


def test_compound_parenthetical_negative_class_post_179() -> None:
    """**Updated #179** — the negative-class discriminator from fix_rows.py
    `_GREEK_ALIAS_NOTE` (issue #149 follow-up) split asymmetrically when
    the typed-list extractor landed:

    - **03.05 `Sôuphis, Mesochris`** (no parens) — keeps the comma-
      compound INLINE in `name`, no name_variants extraction, empty
      `egyptian_titularies`. Unchanged by #179 (no parens to extract
      from).
    - **03.06 `Ahu (Huni, Aches)`** — now decomposed: `name="Ahu"` (bare
      Egyptian nomen), with the bracketed two-Greek-variant compound
      extracted into `name_variants=["Huni", "Aches"]` per the #179
      paren-extraction rule. `egyptian_titularies=[]` (the inner
      compound is a name-form variant pair, NOT a titulary entry).

    The test retains its regression-tripwire purpose against
    fix_rows.py drift on these two rows — only the asserted shape of
    03.06 has migrated. The pre-#179 form (compound inline in `name`,
    egyptian_titulary=None, egyptian_titulary_kind=None) is no longer
    valid on the typed list.

    The positive class (Greek-alias + Egyptian-prenomen pair) continues
    to be exercised by `test_dyn29_dyn30_greek_egyptian_pair_split` and
    `test_taharqo_mixed_titulary` against the typed list shape.
    """
    # 03.05 — comma-compound no-parens form stays inline.
    r0305 = _row("03.05")
    assert r0305["name"] == "Sôuphis, Mesochris"
    assert r0305["name_variants"] == []
    assert r0305["egyptian_titularies"] == []
    # 03.06 — paren-compound is decomposed into name + name_variants.
    r0306 = _row("03.06")
    assert r0306["name"] == "Ahu"
    assert r0306["name_variants"] == ["Huni", "Aches"]
    assert r0306["egyptian_titularies"] == []


def test_te_wosret_coregent_row_extracted() -> None:
    """19.08 Kgin. Te-wosret: Beckerath chains her on Si-ptah's row as
    `Si-ptah und Kgin. Te-wosret (Thuoris)`. The Co-regent queen prompt
    rule (PR following PR #138) extracts her as a separate row preserving
    Beckerath's `Kgin.` honorific and the Greek-form `Thuoris` as
    egyptian_titulary. Per the rule, her notes_from_beckerath records
    the co-regency in German verbatim form (`Mitregentin von Si-ptah`),
    NOT as English editorial prose. Pre-PR-#138 baseline used a different
    `notes=null + editorial_notes="co-regent..."` shape derived from
    incomplete agent extraction; the new shape is more faithful to
    Beckerath's printed text.
    """
    r = _row("19.08")
    # Kgin. spacing is standardised to no-space across all 5 queen rows
    # (matches the printed PDF's typography on scan-107-left).
    assert r["name"] == "Kgin.Te-wosret"
    assert r["egyptian_titularies"] == [
        {"kind": "nomen", "name": "Thuoris", "when": None}
    ]
    # German verbatim co-regency annotation (the Co-regent queen rule
    # mandates "Mitregentin von <king>"), NOT English editorial prose.
    assert r["notes_from_beckerath"] == "Mitregentin von Si-ptah"
    # Te-wosret inherits Si-ptah's BCE range (Co-regent queen rule).
    si_ptah = _row("19.07")
    assert r["start_bce_high"] == si_ptah["start_bce_high"]
    assert r["start_bce_low"] == si_ptah["start_bce_low"]
    assert r["end_bce_high"] == si_ptah["end_bce_high"]
    assert r["end_bce_low"] == si_ptah["end_bce_low"]


def test_editorial_notes_field_present_on_every_row() -> None:
    """`editorial_notes` is part of the source schema and must be present
    on every row (default null). Locks the fix_rows.py setdefault pass.
    """
    for r in _rows():
        assert "editorial_notes" in r, r["beckerath_id"]


def test_taharqo_mixed_titulary() -> None:
    """Beckerath gives Taharqo's parenthetical as `Tarakos, Chu-nefertem-rê`
    — a comma-separated nomen+prenomen pair. Per the typed list (#179),
    this decomposes into two entries: `Tarakos` (nomen) and
    `Chu-nefertem-rê` (prenomen). The legacy scalar kind=`mixed` was the
    pre-typed-list compound label; it is no longer canonical.
    """
    r = _row("25.05")
    assert r["name"] == "Taharqo"
    assert r["egyptian_titularies"] == [
        {"kind": "nomen", "name": "Tarakos", "when": None},
        {"kind": "prenomen", "name": "Chu-nefertem-rê", "when": None},
    ]


def test_psamtik_i_dyn26_full_row() -> None:
    """Late Period flagship: prenomen `Wah-ib-rê` is the parenthetical; both
    approximate flags false (Beckerath gives bare numbers); Spätzeit period.
    Beckerath spells the name `Psametik (Psammêtichos) I.` on book p192
    (scan-108-left).

    Migrated #179: `Psametik (Psammêtichos) I.` is decomposed into bare
    `name="Psametik I."` plus `name_variants=["Psammêtichos"]`.
    """
    r = _row("26.01")
    assert r["dynasty"] == 26
    assert r["sub_line"] is None
    assert r["sequence_in_dynasty"] == 1
    assert r["name"] == "Psametik I."
    assert r["name_variants"] == ["Psammêtichos"]
    assert r["egyptian_titularies"] == [
        {"kind": "prenomen", "name": "Wah-ib-rê", "when": None}
    ]
    assert r["start_bce_high"] == -664
    assert r["end_bce_high"] == -610
    assert r["start_approximate"] is False
    assert r["end_approximate"] is False
    assert r["period"] == "Spätzeit"


def test_supplement_prenomens_merged_for_dyn19_23() -> None:
    """The Supplement zu A pulls additional prenomen forms for Dyn 19-23
    kings. Those should be merged into the main row's `prenomen` field, not
    emitted as separate rows. Spot-check a few canonical entries.
    """
    # Schoschenq III (22.06) gets `User-maat-rê sotep-en-rê` from the Supplement.
    assert _row("22.06")["prenomen"] == "User-maat-rê sotep-en-rê"


# ── Tests pinning fix_rows.py overrides not covered above ────────────────
# Each of these locks a specific reviewer-applied correction. If someone
# re-runs merge.py and forgets fix_rows.py, these tests fail loudly.

def test_dyn4_etwa_propagation_locked() -> None:
    """Dyn-4 rows 04.02 through 04.08 must all have start_approximate=true
    and end_approximate=true because Beckerath's heading
    `4. Dynastie (etwa 2639/2589–2504/2454)` propagates `etwa` to every
    row. Pre-PR-#138 this required fix_rows.py overrides on all 7 rows
    (agents lost the `etwa` qualifier when crossing the book p187 → p188
    page break). PR #138's post-processor emits a
    `<!-- dynasty-context: 4. Dynastie (etwa 2639/2589–2504/2454) -->`
    refresh comment after the page break, so agents now propagate `etwa`
    correctly unaided — overrides removed.
    """
    for kid in ("04.02", "04.03", "04.04", "04.05", "04.06", "04.07", "04.08"):
        r = _row(kid)
        assert r["start_approximate"] is True, kid
        assert r["end_approximate"] is True, kid


def test_late_period_adjacent_half_split_sweep() -> None:
    """Issue #150 — Late Period rows on book p192 (scan-108-left) adjacent
    to the Dyn 29-30 cohort that exhibit a half-split state. Egyptologist
    printed-source review on PR #148 retro flagged 4 rows; PR closing
    #150 verified each directly against the printed PDF on book p192.

    NB: rows in this cohort have INVERSE-DIRECTION linguistic semantics
    vs the Old Kingdom + Dyn 21 single-alias cohort. The discriminator's
    structural shape (single alias → `nomen`; alias-pair → `mixed`)
    still applies; only the LANGUAGE of each side flips. See the same
    NB block in fix_rows.py.

    - 28.01 Amyrtaios — single Egyptian nomen `(Amen-ir-di-su)` in
      parens (Amyrtaios is the Greek/Manethonic display form). Apply
      the SINGLE-alias rule structurally: name=Greek display lemma,
      titulary=Egyptian nomen, kind=`nomen`.
    - 26.02 Nekaw — `(Nekôs/Nechaô, Uhem-ib-rê)`: TWO Greek transcriptions
      (Manetho's Νεχώς vs Herodotus's Νεκώς) + Egyptian prenomen. `Nekaw`
      itself is Egyptian. → typed list: nomen Nekôs + nomen Nechaô +
      prenomen Uhem-ib-rê (three entries).
    - 26.05 Amosis II. — `(Amasis, Chnem-ib-rê)`: Greek/Manethonic-alias
      + Egyptian-prenomen → typed list: nomen Amasis + prenomen
      Chnem-ib-rê.
    - 29.02 Achoris — `(Hagor, Chnem-maat-rê)`: Egyptian-nomen `Hagor`
      (Beckerath's rendering of Egyptian Ḥgr; `Achoris` is the Greek
      display form) + Egyptian-prenomen → typed list: nomen Hagor +
      prenomen Chnem-maat-rê.

    Migrated #179: assertions target the typed `egyptian_titularies`
    list rather than the legacy scalar pair.
    """
    expected = {
        "28.01": (
            "Amyrtaios",
            [{"kind": "nomen", "name": "Amen-ir-di-su", "when": None}],
        ),
        "26.02": (
            "Nekaw",
            [
                {"kind": "nomen", "name": "Nekôs", "when": None},
                {"kind": "nomen", "name": "Nechaô", "when": None},
                {"kind": "prenomen", "name": "Uhem-ib-rê", "when": None},
            ],
        ),
        "26.05": (
            "Amosis II.",
            [
                {"kind": "nomen", "name": "Amasis", "when": None},
                {"kind": "prenomen", "name": "Chnem-ib-rê", "when": None},
            ],
        ),
        "29.02": (
            "Achoris",
            [
                {"kind": "nomen", "name": "Hagor", "when": None},
                {"kind": "prenomen", "name": "Chnem-maat-rê", "when": None},
            ],
        ),
    }
    for bid, (name, titularies) in expected.items():
        r = _row(bid)
        assert r["name"] == name, (bid, r["name"])
        assert r["egyptian_titularies"] == titularies, (bid, r["egyptian_titularies"])


def test_dyn29_dyn30_greek_egyptian_pair_split() -> None:
    """Issue #147 — four Late Period rows on book p192 (scan-108-left) print
    with the SAME `<Greek-name> (<Egyptian-nomen>, <Egyptian-prenomen>)`
    typography as the verified-precedent 15.04 Chajan / 26.04 Apries / 06.04
    Nemti-em-saf I. The 3-agent merge produces an inconsistent half-split
    state; fix_rows.py realigns to the canonical typed-list shape (name=bare
    Greek lemma, two typed-list entries: nomen + prenomen).

    Egyptologist printed-source review on PR #146 verified the discriminator
    applies to all four rows. The pre-#147 state had `Necht-nebef`
    unfindable on Nektanebês because titulary held only `Cheper-ka-rê`.

    Migrated #179: assertions target the typed `egyptian_titularies` list
    rather than the legacy scalar pair.
    """
    expected = {
        "29.03": ("Psamuthis", "Pe-sche[re-n-]mut", "User-rê"),
        "30.01": ("Nektanebês", "Necht-nebef", "Cheper-ka-rê"),
        "30.02": ("Teôs", "Djed-hor", "Iri-maat-en-rê"),
        "30.03": ("Nektanebôs", "Necht-har-ehbojet", "Senedjem-ib-rê"),
    }
    for bid, (name, nomen, prenomen) in expected.items():
        r = _row(bid)
        assert r["name"] == name, (bid, r["name"])
        assert r["egyptian_titularies"] == [
            {"kind": "nomen", "name": nomen, "when": None},
            {"kind": "prenomen", "name": prenomen, "when": None},
        ], (bid, r["egyptian_titularies"])


def test_29_03_psamuthis_gegenkoenig_note_preserved() -> None:
    """29.03 is preceded by `Gegenkönig` in print on book p192. The split
    in #147 only realigns name vs titulary; the German prefix stays in
    notes_from_beckerath as set by the 3-agent merge."""
    r = _row("29.03")
    assert r["notes_from_beckerath"] == "Gegenkönig"


def test_chajan_dyn15_end_date_locked() -> None:
    """Beckerath prints a brace bracket on book p189 (scan-106-right) spanning
    Bêôn / Apachnas / Chajan with shared range 1648/1645–1590/1587. Chajan
    inherits the bracket dates via fix_rows.py (the brace glyph is invisible
    to OCR). The pre-OCR-redo branch had Chajan's end overridden to
    -1549/-1546 (which are Apophis's dates) — that override was based on a
    misreading of the brace span and is removed.
    """
    r = _row("15.04")
    assert "Chajan" in r["name"]
    assert r["start_bce_high"] == -1648
    assert r["start_bce_low"] == -1645
    assert r["end_bce_high"] == -1590
    assert r["end_bce_low"] == -1587


def test_hatschepsut_end_date_locked() -> None:
    """Beckerath prints `Kgin.Hat-schepsut (Maat-ka-rê) 1479/1473–1458/57` on
    book p189 (scan-106-right). The slash-pair end `1458/57` expands to
    -1458 (high) / -1457 (low). Pre-OCR-redo branch had a fix_rows.py
    override forcing end_low=-1458, which collapsed the slash pair — the
    override was based on the previous OCR's garble (`341/837`) and is now
    removed (clean OCR produces the slash pair correctly).
    """
    r = _row("18.05")
    assert "Hat-schepsut" in r["name"]
    assert r["end_bce_high"] == -1458
    assert r["end_bce_low"] == -1457
    assert r["end_approximate"] is False


def test_amen_mes_su_prenomen_supplement_locked() -> None:
    """Amen-mes-su's Thronname per Supplement zu A is `Men-mi-rê
    sotep-en-rê`. Pre-OCR-redo a fix_rows.py override forced this against
    a splice with Sethós II's row; post-OCR-redo the merge extracts it
    directly (no override needed). Test retained as a regression tripwire.
    """
    r = _row("19.05")
    assert r["name"] == "Amen-mes-su"
    assert r["prenomen"] == "Men-mi-rê sotep-en-rê"


def test_sethos_ii_prenomen_supplement_locked() -> None:
    """Beckerath prints `Sethôs II.: User-chepru-rê mer-amun, Setoy mer-en-ptah`
    in the Supplement zu A (book p193, scan-108-right). The 2026-04-28 OCR
    redo extracts the prenomen cleanly without a fix_rows.py override.
    Note: the diacritic is `ô` (circumflex), not `ó` (acute).
    """
    r = _row("19.06")
    assert r["name"] == "Sethôs II."
    assert r["prenomen"] == "User-chepru-rê mer-amun"


def test_necho_ii_prenomen_locked() -> None:
    """Beckerath prints `Nekaw (Nekôs/Nechaô, Uhem-ib-rê)` on book p192
    (scan-108-left) — the parenthetical contains TWO Greek alternatives
    `Nekôs/Nechaô` separated by `/` followed by the Egyptian prenomen
    `Uhem-ib-rê` after a comma. The pre-OCR-redo branch had a fix_rows.py
    override forcing `Wahem-ib-rê` based on a hieroglyphic-transliteration
    argument (Egyptian Wḥm-ib-rꜥ → Wahem-ib-rê), but Beckerath's printed
    text says Uhem. Per the constitutional rule "data is sacred", follow
    what Beckerath actually prints.

    Migrated #179: typed list now decomposes the compound into 3 entries
    (nomen Nekôs + nomen Nechaô + prenomen Uhem-ib-rê). The legacy
    scalar `egyptian_titulary == "Nekôs/Nechaô, Uhem-ib-rê"` is retained
    as a derivative artifact (covered by test_179_legacy_scalars_still_present).
    """
    r = _row("26.02")
    assert r["name"] == "Nekaw"
    titularies = r["egyptian_titularies"]
    # Uhem-ib-rê must be findable as a typed prenomen entry.
    prenomen_entries = [e for e in titularies if e["kind"] == "prenomen"]
    assert prenomen_entries == [
        {"kind": "prenomen", "name": "Uhem-ib-rê", "when": None}
    ], titularies


def test_chabbasch_dyn31_locked() -> None:
    """Beckerath prints `Chababasch (Senen-sotep-en-ptah)` under the
    `Ägypt. Gegenkönig:` sub-block of Dyn 31 (book p192, scan-108-left).
    Note: `Chababasch` (b-a-b-a, four-syllable spelling Beckerath uses) and
    `Senen-` (with N, not M). The pre-OCR-redo branch had a fix_rows.py
    override forcing `Chabbasch` (one syllable shorter) and `Senem-` (with
    M) based on alternative scholarly transliterations; per constitutional
    rule "data is sacred", follow Beckerath's printed text. The
    `-sotep-en-X` suffix is prenomen morphology; fix_rows.py corrects only
    the kind (the underlying titulary is already extracted correctly).
    """
    r = _row("31.04")
    assert r["name"] == "Chababasch"
    assert r["egyptian_titularies"] == [
        {"kind": "prenomen", "name": "Senen-sotep-en-ptah", "when": None}
    ]


def test_schoschenq_spelling_systematic() -> None:
    """`fix_rows.py` runs a systematic Schoscheng→Schoschenq fix because
    OCR mis-read q→g on every occurrence in Dyn 22. No row may contain
    `Schoscheng`; every Schoschenq row must spell it correctly.

    Migrated #179: include scanning the typed list entries' `name` field
    in addition to the legacy scalar pair (which is still present).
    """
    for r in _rows():
        for field in ("name", "prenomen", "egyptian_titulary", "notes_from_beckerath"):
            v = r.get(field)
            if isinstance(v, str):
                assert "Schoscheng" not in v, (r["beckerath_id"], field, v)
        for entry in r["egyptian_titularies"]:
            assert "Schoscheng" not in entry["name"], (r["beckerath_id"], entry)
        for variant in r["name_variants"]:
            assert "Schoscheng" not in variant, (r["beckerath_id"], variant)
    # Spot-check that the Dyn 22 Schoschenq rows are present and spelled correctly.
    assert _row("22.01")["name"] == "Schoschenq I."


def test_notes_have_no_editorial_prose() -> None:
    """`notes_from_beckerath` must contain only Beckerath's own annotations.
    `fix_rows.py` strips agent editorial fragments. Lock that no known
    agent-prose fragment survives.

    The check has two layers — both run inside this single test so there
    is one inventory and one row-iteration:

    **Forbidden-substring inventory** (literal patterns surfaced by
    reviewer rounds on PR #113 + #117 — the egyptologist post-merge
    sweep, issue #115 — and the editorial_notes-separation PR #119):

    - `"end date not given"` / `"end date"` — agent meta-comment about
      missing data (rule 1 violation: notes must be Beckerath's own text).
    - `"combined Dyn"` — agent meta-comment about Beckerath's Dyn 9/10
      combination (the placement is content; the meta-comment is not).
    - `"supplement notes:"` — agent prefix introducing Supplement zu A
      content; the content stays, the prefix goes.
    - `"start "` — leftover residue from a date-correction pass on 18.05.
    - `"later form"` — agent paraphrase of Beckerath's anfang/später
      annotations.
    - `"; später "` (specific pattern, NOT bare `"später"`) — agent merge
      filler reconciling alternative throne names. Bare "später" is
      legitimate German prose Beckerath might use (e.g. "späterer Zusatz",
      "später in Theben"); only the comma-separator merge artifact is the
      defect.
    - `"Antrittsjahr"` — agent prose; Beckerath writes bare
      "Antritt N.M.YYYY" instead.
    - `"(reign change)"` — agent hedge prose.
    - `"OCR"` / `"garbled"` — agent meta-comments about OCR quality.
    - `"shared bracket range"` — auditor commentary from PR #119; belongs
      in `editorial_notes`, not here.

    **Shape-based regex tripwires** (enumeration-free, phrasing-
    independent — added in PR #119 to catch future regressions the
    literal-substring list misses):

    1. `\\(scan-\\d+` — any `(scan-NNN)` tag is a transcriber/auditor
       artifact (the agents do not see scan numbers; only the
       fix_rows.py editorial pass adds them). Migrated rows
       (03.04/03.05/03.06) carried this shape; this regex catches any
       future re-introduction regardless of wording.
    2. `\\bco-(regents?|rulers?|kings?|regenc(?:y|ies))\\b` — English
       co-rulership prose. 19.08 migration cleared one such instance;
       locking the broader morphological family catches "co-ruler
       with…", "co-king of…", or the abstract-noun "co-regency with…"
       rephrasings the literal-substring list would miss. Singular and
       plural forms (`co-regents`, `co-regencies`) are both covered so
       a `\\b`-locked tail vowel cannot leak past the tripwire.

    A harder positive whitelist of legitimate German cell idioms
    (Antritt, Mitregent, Gegenkönig, in Sais, …) is tracked as #120 for
    next-round hardening.
    """
    forbidden_substrings = (
        "end date",  # also catches "end date not given"
        "combined Dyn",
        "supplement notes:",
        "start ",  # used as residue in 18.05
        "later form",
        "; später ",  # narrow: bare "später" is legitimate German
        "Antrittsjahr",
        "(reign change)",
        "OCR",
        "garbled",
        "shared bracket range",  # PR #119 — belongs in editorial_notes
    )
    forbidden_patterns = (
        # `(scan-NNN)` editorial tag — strictly more general than the
        # literal `(scan-` substring; covers future digit variants.
        re.compile(r"\(scan-\d+"),
        # English co-rulership prose. Strictly more general than the
        # literal `co-regent` substring; catches `co-ruler` / `co-king`.
        re.compile(r"\bco-(regents?|rulers?|kings?|regenc(?:y|ies))\b", re.IGNORECASE),
    )
    for r in _rows():
        notes = r.get("notes_from_beckerath")
        if not isinstance(notes, str):
            continue
        for sub in forbidden_substrings:
            assert sub.lower() not in notes.lower(), (r["beckerath_id"], sub, notes)
        for pat in forbidden_patterns:
            assert not pat.search(notes), (r["beckerath_id"], pat.pattern, notes)


def test_akhenaten_prenomen_typo_fixed() -> None:
    """Akhenaten's prenomen per Beckerath book p190 is `Nefer-cheprurê
    wa-en-rê`. The pre-OCR-redo branch had a fix_rows.py override
    correcting an OCR `r`-drop (`Nefer-chepruê` → `Nefer-cheprurê`); the
    split-page OCR reads the `r` correctly (no override needed). Test
    retained as a regression tripwire on this typography-sensitive row.
    """
    r = _row("18.10")
    assert "Ach-en-aten" in r["name"]
    assert r["egyptian_titularies"] == [
        {"kind": "prenomen", "name": "Nefer-cheprurê wa-en-rê", "when": None}
    ]


def test_compound_titulary_decomposes_into_typed_entries() -> None:
    """**Methodology invariant (post-#179)** — when Beckerath prints a
    compound parenthetical containing a comma (e.g. `(Hagor, Chnem-maat-rê)`,
    `(Tarakos, Chu-nefertem-rê)`, `(Wah-ib-rê, Haa-ib-rê)`), the typed
    `egyptian_titularies` list must contain MULTIPLE entries (one per
    comma-separated component), each with its own `kind` (typically
    nomen + prenomen).

    Replaces the pre-#179 `test_compound_titulary_implies_mixed_kind`
    which asserted on the legacy scalar `kind=mixed`. The legacy scalar
    is still emitted (with `kind=mixed`) but the typed list — which is
    canonical — must show a real decomposition. Catches the compound-
    titulary truncation class flagged by the egyptologist post-merge
    sweep (issue #115): if a future fix_rows edit silently emits a
    single-entry titularies list when the legacy scalar contains a
    comma, this test fires.
    """
    for r in _rows():
        tit = r.get("egyptian_titulary")
        if not (isinstance(tit, str) and "," in tit):
            continue
        # Legacy scalar shows a comma-compound → typed list must have
        # multiple entries (the compound has been decomposed).
        assert len(r["egyptian_titularies"]) >= 2, (
            r["beckerath_id"],
            tit,
            r["egyptian_titularies"],
        )


# test_no_editorial_prefixes_in_notes_extended — DELETED 2026-04-25 per
# Gemini PR #117 review (3142716688). Its forbidden-substring list has
# been merged into `test_notes_have_no_editorial_prose` above so we have
# one test, one inventory, one source of truth for editorial-prose
# detection in `notes_from_beckerath`.


# ── Closure tests (#179) — typed-list shape and flag invariants ──────────
# These pin the new typed fields (`egyptian_titularies`, `name_variants`,
# `is_dynasty_marker`, `is_anti_king`, `existence_uncertain`) added by
# the #179 migration. Each canonical-set test pins the EXACT set of
# beckerath_ids carrying a flag so silent additions/removals fire.

_REQUIRED_TYPED_KEYS = (
    "egyptian_titularies",
    "name_variants",
    "is_dynasty_marker",
    "is_anti_king",
    "existence_uncertain",
)


def test_179_every_row_has_typed_flags() -> None:
    """Every row carries all 5 typed fields introduced in #179. Locks the
    fix_rows.py setdefault pass for the new shape so a row missing the
    flag (rather than carrying a False default) fires loud."""
    for r in _rows():
        for key in _REQUIRED_TYPED_KEYS:
            assert key in r, (r["beckerath_id"], key)


def test_179_egyptian_titularies_kind_in_vocab() -> None:
    """Every typed-list entry's `kind` is one of the 5 canonical
    titulary kinds. Stricter than the legacy scalar enum (which had
    `mixed` as a 5th value) — `mixed` was a compound-label artifact and
    is invalid on the typed list. Covers nomen, prenomen, horus_name,
    nebty_name, golden_horus_name."""
    for r in _rows():
        for entry in r["egyptian_titularies"]:
            assert entry["kind"] in EXPECTED_TITULARY_KIND_VALUES, (
                r["beckerath_id"],
                entry,
            )


def test_179_egyptian_titularies_shape() -> None:
    """Every typed-list entry has exactly the 3 keys {name, kind, when}.
    `name` is a non-empty str; `kind` is a str (vocabulary checked
    separately); `when` is str or None. Locks the schema shape so a
    drift to {name, kind} (missing `when`) or extra keys fires loud."""
    for r in _rows():
        for entry in r["egyptian_titularies"]:
            assert set(entry.keys()) == {"name", "kind", "when"}, (
                r["beckerath_id"],
                entry,
            )
            assert isinstance(entry["name"], str) and entry["name"], (
                r["beckerath_id"],
                entry,
            )
            assert isinstance(entry["kind"], str), (r["beckerath_id"], entry)
            assert entry["when"] is None or isinstance(entry["when"], str), (
                r["beckerath_id"],
                entry,
            )


def test_179_dynasty_markers_canonical_set() -> None:
    """Exact set of beckerath_ids whose `is_dynasty_marker==True`.
    Beckerath's marker rows (dynasty-only, no individual king):
    Dyn 0, 7, 8, 9/10 (combined), 13, 14, 16 (Hyksos-Vasallen header),
    17 (in Theben). The 9/10 combined row is keyed at 09.01."""
    expected = {"00.01", "07.01", "08.01", "09.01", "13.01", "14.01", "16.01", "17.01"}
    actual = {r["beckerath_id"] for r in _rows() if r["is_dynasty_marker"]}
    assert actual == expected, sorted(actual)


def test_179_anti_king_canonical_set() -> None:
    """Exact set of beckerath_ids whose `is_anti_king==True`. Probe pinned
    2026-05-03: 02.09 / 02.10 (Dyn 2 Seth Per-ib-sen + Hor-Seth Cha-sechemui
    sharing Beckerath's "Gegenkönig der 3 vorigen" annotation), 29.03
    (Psamuthis, Gegenkönig), 31.04 (Chababasch, Ägypt. Gegenkönig).

    11.07 Ment-hotpe IV. is NOT included — his note "und Gegenkönige"
    (plural) means he had anti-kings besides him, not that he is one.
    The detection regex uses negative lookahead `(?!e)` to exclude the
    plural form. Per egyptologist + code-reviewer P1.

    22.07 (Schoschenq IIIa.) is NOT included — Beckerath's parens-wrap
    is an existence-uncertainty marker, not an anti-king marker. Per
    audit, 22.07 belongs only in `existence_uncertain`. Per egyptologist
    P1-3."""
    expected = {"02.09", "02.10", "29.03", "31.04"}
    actual = {r["beckerath_id"] for r in _rows() if r["is_anti_king"]}
    assert actual == expected, sorted(actual)


def test_179_existence_uncertain_canonical_set() -> None:
    """Exact set of beckerath_ids whose `existence_uncertain==True`. Probe
    pinned 2026-05-03: 02.08 (Dyn 2 hedge), 22.07 (Schoschenq IIIa. —
    Beckerath parenthesises the entire name), 23.04 (Dyn 23 hedge)."""
    expected = {"02.08", "22.07", "23.04"}
    actual = {r["beckerath_id"] for r in _rows() if r["existence_uncertain"]}
    assert actual == expected, sorted(actual)


def test_179_03_02_djoser_horus_name_split() -> None:
    """Anchor: 03.02 Djoser must carry both a nomen Tosorthros AND a
    horus_name Hor Netri-chet on the typed list. This was the audit's
    headline mixed-shape correction — pre-#179 the horus_name was
    silently lost when the legacy scalar collapsed the pair into a
    single comma-compound under kind=`mixed`."""
    titularies = _titularies("03.02")
    kinds = {e["kind"]: e["name"] for e in titularies}
    assert kinds.get("nomen") == "Tosorthros", titularies
    assert kinds.get("horus_name") == "Hor Netri-chet", titularies


def test_179_19_07_siptah_temporal_prenomen() -> None:
    """Anchor: 19.07 Si-ptah carries TWO prenomen entries with German
    temporal markers. Beckerath's `anfangs Secha-en-rê mer-amun, später
    Ach-en-rê sotep-en-rê` (a within-reign throne-name change) decomposes
    to the typed list as two entries with `when` populated."""
    titularies = _titularies("19.07")
    prenomen_entries = [e for e in titularies if e["kind"] == "prenomen"]
    assert len(prenomen_entries) == 2, titularies
    whens = {e["when"] for e in prenomen_entries}
    assert whens == {"anfangs", "später"}, prenomen_entries


def test_179_15_05_apophis_slash_alternatives() -> None:
    """Anchor: 15.05 Apophis carries TWO prenomen entries — Beckerath's
    `A-qen-en-rê/A-user-rê` slash-alternative form decomposes to two
    typed-list entries (both prenomen, no `when` qualifier)."""
    titularies = _titularies("15.05")
    assert titularies == [
        {"kind": "prenomen", "name": "A-qen-en-rê", "when": None},
        {"kind": "prenomen", "name": "A-user-rê", "when": None},
    ], titularies


def test_179_26_02_mixed_with_slash() -> None:
    """Anchor: 26.02 Nekaw carries 3 entries — two Greek-nomen alternates
    (Nekôs / Nechaô) split on `/`, plus the Egyptian prenomen Uhem-ib-rê
    after the comma. The combined slash+comma form is the most complex
    shape the typed-list extractor handles in this source."""
    titularies = _titularies("26.02")
    assert titularies == [
        {"kind": "nomen", "name": "Nekôs", "when": None},
        {"kind": "nomen", "name": "Nechaô", "when": None},
        {"kind": "prenomen", "name": "Uhem-ib-rê", "when": None},
    ], titularies


def test_179_22_07_existence_uncertain_anchor() -> None:
    """Anchor: 22.07 Schoschenq IIIa. — Beckerath parenthesises the entire
    name as an existence-hedge marker. Per the bare-paren rule, the
    `name` keeps the parens (not stripped). `existence_uncertain` is
    True; `is_anti_king` is FALSE — the parens-wrap is an existence
    marker, not an anti-king marker (per egyptologist P1-3 + audit
    Shape J classification). The typed-list `egyptian_titularies` is
    empty (the prenomen Hedj-cheper-rê sotep-en-rê lives on the
    `prenomen` field, not the typed list, because Beckerath gave it as
    a Supplement-zu-A entry rather than an inline parenthetical)."""
    r = _row("22.07")
    assert r["name"] == "(Schoschenq IIIa.)"
    assert r["is_anti_king"] is False
    assert r["existence_uncertain"] is True
    assert r["egyptian_titularies"] == []


def test_179_18_02_amenophis_paren_extracted() -> None:
    """Anchor: 18.02 Amenophis I. — the parens-form `Amenophis (Amen-hotpe)
    I.` is decomposed into bare canonical `name="Amenophis I."` plus
    `name_variants=["Amen-hotpe"]` per the #179 paren-extraction rule."""
    r = _row("18.02")
    assert r["name"] == "Amenophis I."
    assert r["name_variants"] == ["Amen-hotpe"]


def test_179_19_01_ramses_multi_variant() -> None:
    """Anchor: 19.01 Ramses I. — multi-variant parens form. Beckerath
    prints `Ramses (Ra-mes-su, griech. Ramessês) I.`. The comma-separated
    inner compound decomposes to TWO `name_variants` entries (the
    Egyptian transliteration AND the Greek-prefixed alternative). Pins
    that the variant extractor honours intra-paren commas."""
    r = _row("19.01")
    assert r["name"] == "Ramses I."
    assert r["name_variants"] == ["Ra-mes-su", "griech. Ramessês"]


def test_179_legacy_scalars_still_present() -> None:
    """The legacy scalar fields `egyptian_titulary` and
    `egyptian_titulary_kind` are KEPT on every row alongside the typed
    list. They are derivative ingest artifacts (consumers must use the
    typed list, but the scalars stay so `fix_rows.py` re-runs are
    idempotent — re-reading and re-emitting a row with the legacy
    keys present must not change the row). This test pins their
    continued presence; if a future schema cleanup decides to drop the
    legacy scalars, this test is the deletion checkpoint."""
    for r in _rows():
        assert "egyptian_titulary" in r, r["beckerath_id"]
        assert "egyptian_titulary_kind" in r, r["beckerath_id"]


def test_179_fix_rows_is_file_level_idempotent() -> None:
    """Regression for code-reviewer P1-1 (round 1): early `_extract_name_variants`
    unconditionally overwrote `name_variants` on each run, so once the parens
    were stripped from `name`, the variants were silently wiped. This test
    runs `fix_rows.py` twice in a temporary copy and asserts byte-equality
    of the output JSONL.

    Per Rule 3 (deterministic enforcement): a passing claim of "idempotent"
    must be backed by a test that actually does the round-trip.
    """
    import shutil
    import subprocess
    import tempfile
    src_dir = (
        Path(__file__).parent.parent
        / "pipeline"
        / "authority"
        / "sources"
        / "beckerath-1997-chronologie"
    )
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str) / "src"
        shutil.copytree(src_dir, tmp)
        for _ in range(2):
            subprocess.run(
                ["python3", str(tmp / "fix_rows.py")],
                check=True,
                capture_output=True,
            )
        run1 = (tmp / "reconciled.jsonl").read_bytes()
        # Run a third time and compare to the second run's output (the
        # "second-run guard" — reconciled is already in fully-migrated
        # form, so a re-run must be a no-op at the byte level).
        subprocess.run(
            ["python3", str(tmp / "fix_rows.py")],
            check=True,
            capture_output=True,
        )
        run2 = (tmp / "reconciled.jsonl").read_bytes()
        assert run1 == run2, (
            "fix_rows.py is NOT byte-idempotent — re-running on a "
            "fully-migrated reconciled.jsonl produced different bytes. "
            "Likely cause: a migration unconditionally overwrites a typed "
            "field that the source-of-truth no longer carries (e.g. parens "
            "stripped from `name` make `_extract_name_variants` return [], "
            "wiping the typed `name_variants`)."
        )
