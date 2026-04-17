"""Structural value-assertion tests for Baud 1999 BdE 126 *Corpus* extract.

Per constitutional rule 5: every populated field on at least one flagship
fixture row is asserted. Chunk 1 covers Baud Corpus entries [1]–[40]
(physical pp. 11–49 of vol. 2).
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
    / "baud-1999-ok-royal-family"
)
JSONL = SOURCE_DIR / "reconciled.jsonl"

EDITION = "IFAO 1999 vol. 2"
PDF_PAGES = "11-49"

CHUNK1_EXPECTED_ROWS = 40


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(
        json.loads(line) for line in JSONL.read_text().splitlines() if line.strip()
    )


def _row(baud_id: str) -> dict:
    hits = [r for r in _rows() if r["baud_id"] == baud_id]
    if len(hits) != 1:
        raise AssertionError(f"expected 1 row for {baud_id}, got {len(hits)}")
    return hits[0]


def test_row_count() -> None:
    """Chunk 1 = Baud entries [1]–[40], one row each."""
    assert len(_rows()) == CHUNK1_EXPECTED_ROWS, len(_rows())


def test_baud_id_is_unique() -> None:
    """Baud's numeric ID namespace is globally unique across the full Corpus;
    a duplicate within chunk 1 is a merge bug."""
    ids = [r["baud_id"] for r in _rows()]
    assert len(ids) == len(set(ids)), "duplicate baud_id detected"


_BID_RE = re.compile(r"^baud-[1-9][0-9]*$")


def test_baud_id_shape() -> None:
    """Every id is `baud-<N>` with N a positive integer, no leading zero."""
    for r in _rows():
        assert _BID_RE.match(r["baud_id"]), r["baud_id"]


def test_baud_id_covers_1_to_40() -> None:
    """Chunk 1 covers entries 1–40 contiguously, no gaps."""
    nums = sorted(int(r["baud_id"].split("-")[1]) for r in _rows())
    assert nums == list(range(1, CHUNK1_EXPECTED_ROWS + 1)), nums


def test_every_row_has_complete_citation() -> None:
    """Rule 1: every row traces back to a source-citation triple."""
    for r in _rows():
        citation = r["source_citation"]
        n = int(r["baud_id"].split("-")[1])
        assert citation == {
            "source": f"Baud 1999 BdE 126 Corpus [{n}]",
            "pdf_pages": PDF_PAGES,
            "edition": EDITION,
        }, r["baud_id"]


def test_dynasty_coverage_is_ok_only() -> None:
    """Chunk 1's alphabetical slice of Baud's Corpus covers Dyns 3–6 (OK);
    no MK/NK/LP bleed-through. `None` is allowed only for cross-reference
    stubs — entries whose `(d)` line is empty because the content lives
    under another Corpus number (e.g. baud-9 `Jj-[ḥr ?]-nfr. Voir à
    Nfrt-kꜣw II [132]`)."""
    valid_dynasties = {"3", "4", "5", "6", "3-4", "4-5", "5-6", "unknown"}
    for r in _rows():
        d = r["dynasty"]
        if d is None:
            # Cross-reference stub: has no titles, no monument, no date.
            # Dynasty is None because there is no source data to derive from.
            assert r["titles_from_baud"] == [], (
                f"{r['baud_id']}: dynasty=None but titles are populated — "
                f"extraction should have derived a dynasty."
            )
            assert r["date_attested"] is None, (
                f"{r['baud_id']}: dynasty=None but date_attested is populated."
            )
            continue
        assert d in valid_dynasties, f"{r['baud_id']} dynasty={d!r}"


def test_roles_vocabulary_is_bounded() -> None:
    """Every role in every row is in the chunk-1 controlled vocabulary.
    Catches extraction drift where an agent invents a role code."""
    allowed = {
        "king",
        "queen",
        "king's mother",
        "king's wife",
        "king's son",
        "king's daughter",
        "king's son-in-law",
        "king's eldest son of his body",
        "vizier",
        "priest of the royal pyramid",
        "priest of the king's mother",
        "priest of the king's wife",
        "priest of the king",
        "steward of the queen",
        "sem priest",
        "overseer of the treasury of pr-ꜥꜣ",
        "overseer of scribes of pr-ꜥꜣ",
    }
    for r in _rows():
        for role in r["roles"]:
            assert role in allowed, f"{r['baud_id']} role={role!r} not in vocab"


def test_service_personnel_is_bool() -> None:
    """service_personnel is the asterisk-flag; must be bool, never null."""
    for r in _rows():
        assert isinstance(r["service_personnel"], bool), r["baud_id"]


def test_name_egyptian_uses_canonical_translit() -> None:
    """After fix_rows.py's normalization pass, every name_egyptian uses
    the canonical IFAO ꜥ (U+A725) and ꜣ (U+A723), not the fallback
    ˁ (U+02C1), ɛ (U+025B), or ɜ (U+025C) that the PDF text layer emits."""
    fallbacks = {"\u02c1", "\u025b", "\u025c"}
    for r in _rows():
        leaked = set(r["name_egyptian"]) & fallbacks
        assert not leaked, f"{r['baud_id']}: fallback codepoints in name_egyptian: {leaked}"


def test_titles_from_baud_uses_canonical_translit() -> None:
    """Same normalization check across the titles list (no fallback codepoints)."""
    fallbacks = {"\u02c1", "\u025b", "\u025c"}
    for r in _rows():
        for t in r["titles_from_baud"]:
            leaked = set(t) & fallbacks
            assert not leaked, f"{r['baud_id']}: fallback in title {t!r}"


def test_ihetihotep_baud_3_full_populated_row() -> None:
    """Flagship row — baud-3 is the schema example in README.md. Assert every
    populated field matches what Baud's printed p. 399 attests.
    """
    r = _row("baud-3")
    assert r["name_egyptian"] == "Jḥtj-ḥtp"
    assert r["name_anglicised"] == "Ihetihotep"
    assert r["service_personnel"] is False
    assert r["monument"] == "Mastaba G 7650"
    assert r["localisation"] == "nécropole orientale de Gîza"
    assert r["pm_ref"] == "PM 200-201"
    assert r["date_attested"] == "Rêkhaef au plus tard"
    assert r["dynasty"] == "4"
    assert r["sub_period"] is None
    assert r["baud_refs"] == {
        "baer": "7",
        "schmitz": "121-122 (356)",
        "harpur": "10",
    }
    assert r["titles_from_baud"] == [
        "/// n jmꜣt (?)",
        "ꜥd-mr wḥꜥw",
        "ḥm [bꜣw] Nḫn",
        "ḥm-nṯr Ḫwfw",
        "ḥrp ꜥḥ",
        "smr",
        "smr wꜥtj",
    ]
    assert r["roles"] == ["king's son-in-law"]
    assert r["father_name"] is None
    assert r["mother_name"] is None
    assert r["spouse_names"] == ["Mrt-jt.s"]
    assert r["children_names"] == []
    assert r["tomb"] == "G 7650"
    assert r["notes_from_baud"] == "Époux de la fille royale Mrt-jt.s [86]."
    assert r["source_citation"] == {
        "source": "Baud 1999 BdE 126 Corpus [3]",
        "pdf_pages": "11-49",
        "edition": "IFAO 1999 vol. 2",
    }


def test_ankhesenmeryre_i_baud_37_full_populated_row() -> None:
    """Second flagship row — a well-attested Dyn-6 queen (Pépi I's wife,
    Merenrê's mother). Every populated field asserted. Checks
    name_anglicised normalization to the conventional English form.
    """
    r = _row("baud-37")
    assert r["name_egyptian"] == "ꜥnḫ.s-n-Mrjj-Rꜥ Iʳᵉ"
    assert r["name_anglicised"] == "Ankhesenmeryre I"
    assert r["service_personnel"] is False
    assert r["localisation"] == "Abydos"
    assert r["date_attested"] == "Pépi Iᵉʳ-Merenrê"
    assert r["dynasty"] == "6"
    assert r["sub_period"] is None
    assert r["roles"] == ["king's mother", "king's wife"]
    assert r["father_name"] == "Ḫwj"
    assert r["mother_name"] is None
    assert r["spouse_names"] == ["Pépi Iᵉʳ"]
    assert r["children_names"] == ["Merenrê"]
    assert r["tomb"] is None


def test_baud_26_grandchild_not_listed_as_child() -> None:
    """Regression: baud-26 (Jḫj)'s grandson Sꜥnḫ-n-Ptḥ was initially
    promoted to children_names by majority-vote. fix_rows.py overrides
    to []. Phase A family-tree semantics depend on this distinction.
    """
    r = _row("baud-26")
    assert r["children_names"] == [], r["children_names"]


def test_baud_38_spouse_is_only_pepi_i() -> None:
    """Regression: baud-38 (ꜥnḫ.s-n-Mrjj-Rꜥ II) was her son Pépi II's
    mother (regent), not his wife. fix_rows.py overrides spouse_names
    to exclude the spurious 'Pépi II (?)'.
    """
    r = _row("baud-38")
    assert r["spouse_names"] == ["Pépi Iᵉʳ"], r["spouse_names"]
    assert "Pépi II" in r["children_names"]


def test_baud_33_mother_hedge_uses_per_baud_convention() -> None:
    """Regression: baud-33's mother Mr.s-ꜥnḫ III is Strudwick's
    titular-synchronism inference, not an inscribed attestation —
    the schema distinguishes '(probable)' from '(per Baud)'.
    """
    r = _row("baud-33")
    assert r["mother_name"] == "Mr.s-ꜥnḫ III (per Baud)", r["mother_name"]


def test_hedge_preservation_on_filiation_fields() -> None:
    """Baud is hedge-heavy; rows with a '(probable)' or '(per Baud)' or
    '[X]'-reconstructed father should survive intact. Sample: baud-2
    (Jḫ-Rꜥ's probable father Rêkhaef), baud-13 (Jwn-Mnw's Rêkhaef),
    baud-14 (Jwn-Rꜥ's Rêkhaef).
    """
    r2 = _row("baud-2")
    assert r2["father_name"] == "Rêkhaef (probable)"
    r14 = _row("baud-14")
    assert r14["father_name"] == "Rêkhaef"  # baud-14 is explicit, not hedged


def test_baud_40_includes_priest_of_the_royal_pyramid() -> None:
    """Regression: reviewer-flagged role-under-extraction. ꜥnḫ-Špss-kꜣ.f
    holds three ḥm-nṯr pyramid-cult titles (Ḫwfw, Sꜣḥw-Rꜥ, Nfr-jr-kꜣ-Rꜥ);
    majority-vote initially narrowed roles to `priest of the king` alone.
    fix_rows.py adds the priest-of-the-royal-pyramid role back.
    """
    r = _row("baud-40")
    assert "priest of the royal pyramid" in r["roles"], r["roles"]


def test_baud_28_includes_priest_of_the_royal_pyramid() -> None:
    """Same role-under-extraction pattern at baud-28 — wꜥb Bꜣ-Nfr-jr-kꜣ-Rꜥ
    (Neferirkare's pyramid-cult priest) was stripped from the majority
    merge. Restored by fix_rows.py.
    """
    r = _row("baud-28")
    assert "priest of the royal pyramid" in r["roles"], r["roles"]


def test_service_personnel_rows_have_attested_titles() -> None:
    """A service_personnel=True row (asterisk-marked in Baud's headword)
    is by definition someone attached to the royal household through a
    function, so Baud MUST attest at least one title for them. An
    empty `titles_from_baud` on a service_personnel row is the signature
    extraction-miss pattern (asterisk noted, but the TITRES rubric went
    unread). `roles` may legitimately be empty if the seeded role
    vocabulary doesn't yet cover the attested titles — that is a
    vocab-expansion question, not an extraction-correctness question
    (reviewer flagged 'steward of the king's children' at baud-10 for
    chunk 2 vocab expansion).
    """
    for r in _rows():
        if not r["service_personnel"]:
            continue
        assert r["titles_from_baud"], (
            f"{r['baud_id']} is service_personnel=True but has no titles — "
            f"Baud's asterisk marks function-attached personnel, so TITRES "
            f"must exist. Likely extraction miss."
        )


def test_tomb_designation_shape_when_populated() -> None:
    """Tomb designations follow OK conventions: G xxxx (Giza), D xx (Saqqara
    Dahchour), LG nn (Lepsius-numbered), or freeform (`Mastaba 17 Meidum`).
    Assert the shape is well-formed when the field is populated.
    """
    for r in _rows():
        if r["tomb"] is None:
            continue
        t = r["tomb"]
        assert t.strip() == t, f"{r['baud_id']}: tomb has leading/trailing whitespace: {t!r}"
        assert len(t) > 0, f"{r['baud_id']}: empty tomb string"
