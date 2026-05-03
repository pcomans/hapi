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

# Per-chunk physical-page range in the original Baud vol. 2 PDF. Each row's
# `source_citation.pdf_pages` records the sub-PDF range the row was
# extracted from (ADR-017 § "Cite physical pages"). Chunk boundaries are
# inclusive on both ends; the overlap pages (e.g. p. 49 shared between
# chunks 1 and 2) carry the pdf_pages of whichever chunk emitted the row.
CHUNK_PDF_PAGES: dict[range, str] = {
    range(1, 41): "11-49",
    range(41, 81): "49-82",
    range(81, 121): "82-109",
    range(121, 161): "109-141",
    range(161, 201): "142-179",
    range(201, 241): "179-213",
    range(241, 283): "214-244",
}


_BID_INT_RE = re.compile(r"^baud-(\d+)[a-z]?$")


def _pdf_pages_for(baud_id: str) -> str:
    m = _BID_INT_RE.match(baud_id)
    assert m, f"Malformed baud_id {baud_id!r}"
    n = int(m.group(1))
    for r, pages in CHUNK_PDF_PAGES.items():
        if n in r:
            return pages
    raise AssertionError(f"No chunk pdf_pages range covers {baud_id}")


CHUNK1_EXPECTED_ROWS = 40
# Chunk 2 emits 41 rows: [41]–[80] (40 integer-numbered) plus Baud's
# sub-entry [60a] Pn-mdw (physical p. 63, one graffito-attested prince).
CHUNK2_EXPECTED_ROWS = 41
# Chunk 3 emits 42 rows: [81]–[120] (40 integer-numbered) plus two
# sub-entries [94b] Nj-ꜥnḫ-Ḥwt-Ḥr and [101a] N(j)-s(w)-jr(w).
CHUNK3_EXPECTED_ROWS = 42
# Chunk 4 emits 43 rows: [121]–[160] (40 integer-numbered) plus three
# sub-entries [126a], [133b], [139a].
CHUNK4_EXPECTED_ROWS = 43
# Chunk 5 covers [161]-[200] — 40 rows; no sub-entries surfaced.
CHUNK5_EXPECTED_ROWS = 40
# Chunk 6 emits 41 rows: [201]-[240] (40 integer-numbered) plus one
# sub-entry [206a].
CHUNK6_EXPECTED_ROWS = 41
# Chunk 7 emits 42 rows: [241]-[282] (final chunk, 42 integer-numbered
# entries, no sub-entries).
CHUNK7_EXPECTED_ROWS = 42


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
    """Merged Corpus = sum of every chunk's expected row count."""
    expected = (
        CHUNK1_EXPECTED_ROWS
        + CHUNK2_EXPECTED_ROWS
        + CHUNK3_EXPECTED_ROWS
        + CHUNK4_EXPECTED_ROWS
        + CHUNK5_EXPECTED_ROWS
        + CHUNK6_EXPECTED_ROWS
        + CHUNK7_EXPECTED_ROWS
    )
    assert len(_rows()) == expected, len(_rows())


def test_baud_id_is_unique() -> None:
    """Baud's numeric ID namespace is globally unique across the full Corpus;
    a duplicate within chunk 1 is a merge bug."""
    ids = [r["baud_id"] for r in _rows()]
    assert len(ids) == len(set(ids)), "duplicate baud_id detected"


_BID_RE = re.compile(r"^baud-[1-9][0-9]*[a-z]?$")


def test_baud_id_shape() -> None:
    """Every id is `baud-<N>` (N positive, no leading zero) or
    `baud-<N><letter>` (single a-z suffix for Baud's rare sub-entries
    like [60a] Pn-mdw)."""
    for r in _rows():
        assert _BID_RE.match(r["baud_id"]), r["baud_id"]


def test_baud_id_is_contiguous_to_running_total() -> None:
    """Merged chunks cover every integer entry number 1..last contiguously,
    with no gaps. Letter-suffix sub-entries (e.g. `baud-60a`) are additional
    and do not replace their parent `baud-<N>`.
    """
    # Last integer in the integer-numbered namespace. CHUNK*_EXPECTED_ROWS
    # counts include sub-entries, so we derive `last_n` from the chunk
    # integer-ranges in CHUNK_PDF_PAGES instead.
    last_n = max(max(r) for r in CHUNK_PDF_PAGES.keys())
    nums = sorted(
        int(_BID_INT_RE.match(r["baud_id"]).group(1)) for r in _rows()
    )
    # Each integer 1..last_n must appear at least once; sub-entries may
    # cause the same integer to appear twice (baud-60 and baud-60a).
    distinct = sorted(set(nums))
    assert distinct == list(range(1, last_n + 1)), distinct


def test_every_row_has_complete_citation() -> None:
    """Rule 1: every row traces back to a source-citation triple.
    pdf_pages varies by chunk — chunk-1 rows cite "11-49",
    chunk-2 rows cite "49-82", etc. Letter-suffixed sub-entries
    (e.g. `baud-60a`) cite `[60a]` in the source field.
    """
    for r in _rows():
        citation = r["source_citation"]
        # Baud's own bracket-number form: strip the `baud-` prefix to
        # reconstruct whatever follows (digit-only or digit+letter).
        baud_bracket = r["baud_id"].removeprefix("baud-")
        assert citation == {
            "source": f"Baud 1999 BdE 126 Corpus [{baud_bracket}]",
            "pdf_pages": _pdf_pages_for(r["baud_id"]),
            "edition": EDITION,
        }, r["baud_id"]


def test_dynasty_coverage_is_ok_only() -> None:
    """Chunk 1's alphabetical slice of Baud's Corpus covers Dyns 3–6 (OK);
    no MK/NK/LP bleed-through. `None` is allowed only for cross-reference
    stubs — entries whose `(d)` line is empty because the content lives
    under another Corpus number (e.g. baud-9 `Jj-[ḥr ?]-nfr. Voir à
    Nfrt-kꜣw II [132]`)."""
    # `"unknown"` is NOT in the valid set — `merge.py`'s SENTINEL_NULL_STRINGS
    # collapses the "unknown" string to None, so the final output should
    # never carry `"unknown"` as a dynasty value. Including it here would
    # let a merge regression that skipped normalization slip through.
    # `2-3` admitted for the Early-Dynastic / OK transition — Baud
    # includes some figures like baud-98 Nj-mꜣꜥt-Ḥp I at "Fin IIᵉ à début
    # IIIᵉ dynastie". Conservative: still no bare `2`.
    valid_dynasties = {"2-3", "3", "4", "5", "6", "3-4", "4-5", "5-6"}
    # Baud himself declines to date some entries, writing `Date?` in the
    # (d) line. Those rows carry `date_attested == "Date ?"` (or similar)
    # and `dynasty == None` is the only honest mapping — scholarly
    # rigour beats forcing a date Baud himself refused.
    baud_declines_to_date_re = re.compile(r"^Date\s*\?", re.IGNORECASE)
    # Baud also uses 'PPI' (Première Période Intermédiaire / First
    # Intermediate Period) for a small number of entries whose style
    # dates them post-OK. These are outside the OK dynasty range
    # (3-6); dynasty = null is the honest mapping, with the FIP
    # information captured in `sub_period` and the verbatim 'PPI' in
    # `date_attested`. Sample: baud-213 Sntj (Firth/Gunn's "miserable
    # little stela" secteur Téti).
    baud_fip_re = re.compile(r"^PPI\b", re.IGNORECASE)
    for r in _rows():
        d = r["dynasty"]
        if d is None:
            da = r["date_attested"]
            if da is None:
                # Cross-reference stub: no titles, no monument, no date.
                assert r["titles_from_baud"] == [], (
                    f"{r['baud_id']}: dynasty=None and date=None but "
                    f"titles are populated — extraction bug."
                )
                continue
            if baud_declines_to_date_re.match(da):
                # Baud's explicit "I can't date this" — honest mapping.
                continue
            if baud_fip_re.match(da):
                # Baud dates to First Intermediate Period; outside OK
                # dynasty range. Expect sub_period to carry the FIP
                # info.
                assert r["sub_period"] == "First Intermediate Period", (
                    f"{r['baud_id']}: date_attested={da!r} (FIP) but "
                    f"sub_period={r['sub_period']!r} — expected 'First "
                    f"Intermediate Period'."
                )
                continue
            raise AssertionError(
                f"{r['baud_id']}: dynasty=None but date_attested={da!r} — "
                f"dynasty should have been derived."
            )
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
        "steward of the king's children",
        # Added in chunk 2 after the egyptologist-reviewer pass:
        "steward of the king's mother",
        "high priest of Ptah",
        "overseer of the king's ornaments",
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
        "ꜥḏ-mr wḥꜥw",
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
    Merenrê's mother). Every populated field asserted per rule 5. Checks
    name_anglicised normalization to the conventional English form.
    """
    r = _row("baud-37")
    assert r["name_egyptian"] == "ꜥnḫ.s-n-Mrjj-Rꜥ Iʳᵉ"
    assert r["name_anglicised"] == "Ankhesenmeryre I"
    assert r["service_personnel"] is False
    assert r["monument"] == "Stèle (ou pilier ?) du vizir Ḏꜥw"
    assert r["localisation"] == "Abydos"
    assert r["pm_ref"] == "PM V, p. 95"
    assert r["date_attested"] == "Pépi Iᵉʳ-Merenrê"
    assert r["dynasty"] == "6"
    assert r["sub_period"] is None
    assert r["baud_refs"] == {
        "schmitz": "138 (359)",
        "seipel": "6.4.1",
        "troy": "6.6",
    }
    assert r["titles_from_baud"] == [
        "wrt ḥzt",
        "wrt ḥts",
        "mwt nswt (3)",
        "mwt nswt Ḫꜥ-nfr-Mrjj-n-Rꜥ (2)",
        "mwt nswt-bjtj Ḫꜥ-nfr-Mrjj-n-Rꜥ",
        "ḥmt nswt Mn-nfr-Mrjj-Rꜥ",
        "ḥt Wr",
        "smrt Ḥr",
        "tjst Ḥr",
    ]
    assert r["roles"] == ["king's mother", "king's wife"]
    assert r["father_name"] == "Ḫwj"
    assert r["mother_name"] is None
    assert r["spouse_names"] == ["Pépi Iᵉʳ"]
    assert r["children_names"] == ["Merenrê"]
    assert r["tomb"] is None
    assert r["notes_from_baud"] == (
        "Épouse de Pépi Iᵉʳ et mère de Merenrê; fille du vizir Ḫwj, "
        "représentant d'une puissante famille abydénienne."
    )
    assert r["source_citation"] == {
        "source": "Baud 1999 BdE 126 Corpus [37]",
        "pdf_pages": "11-49",
        "edition": "IFAO 1999 vol. 2",
    }


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


def test_baud_33_mother_is_null_not_hedged() -> None:
    """Regression: baud-33's mother is Strudwick's hypothesis ('la mère
    Mr.s-ꜥnḫ III est hypothétique d'après Strudwick'), not Baud's own
    attribution. First-pass reviewer wrote `(per Baud)`; second-pass
    pushed back noting Baud is reporting Strudwick's hypothesis, not
    asserting it. Resolved to null — the mother-connection in the
    structured field is not attested by Baud; notes_from_baud captures
    Strudwick's hypothesis verbatim for the reader's benefit.
    """
    r = _row("baud-33")
    assert r["mother_name"] is None, r["mother_name"]
    # The Strudwick hypothesis must still be visible to readers via notes.
    assert "Strudwick" in (r["notes_from_baud"] or ""), r["notes_from_baud"]


def test_hedge_preservation_on_filiation_fields() -> None:
    """Baud is hedge-heavy; rows with a '(probable)' or '(per Baud)' or
    '[X]'-reconstructed father should survive intact. Samples: baud-2
    (Jḫ-Rꜥ's probable father Rêkhaef), baud-13 (Jwn-Mnw's hedged
    Rêkhaef-by-synchronism father), baud-14 (Jwn-Rꜥ's explicit
    inscription-attested Rêkhaef father).
    """
    r2 = _row("baud-2")
    assert r2["father_name"] == "Rêkhaef (probable)"
    r13 = _row("baud-13")
    assert r13["father_name"] == "Rêkhaef (probable)"
    r14 = _row("baud-14")
    assert r14["father_name"] == "Rêkhaef"  # baud-14 is explicit, not hedged


def test_baud_40_roles_full_list_preserved() -> None:
    """Regression: reviewer-flagged role-under-extraction. ꜥnḫ-Špss-kꜣ.f
    holds three ḥm-nṯr pyramid-cult titles (Ḫwfw, Sꜣḥw-Rꜥ, Nfr-jr-kꜣ-Rꜥ);
    majority-vote initially narrowed roles to `priest of the king` alone.
    fix_rows.py adds `priest of the royal pyramid` back. Chunk-2 vocab
    expansion appends `steward of the king's children` (see
    `CHUNK1_BACKFILL`); the full three-role list is pinned so a later
    regression dropping any element fails loud.
    """
    r = _row("baud-40")
    assert r["roles"] == [
        "priest of the king",
        "priest of the royal pyramid",
        "steward of the king's children",
    ], r["roles"]


def test_baud_28_roles_full_list_preserved() -> None:
    """Same role-under-extraction pattern at baud-28 — wꜥb Bꜣ-Nfr-jr-kꜣ-Rꜥ
    (Neferirkare's pyramid-cult priest) was stripped from the majority
    merge. Restored by fix_rows.py. Pin the full list for regression.
    """
    r = _row("baud-28")
    assert r["roles"] == [
        "priest of the king's mother",
        "priest of the royal pyramid",
    ], r["roles"]


def test_baud_20_steward_of_the_queen_restored() -> None:
    """2nd-pass egyptologist-reviewer correction: baud-20 (Jmnj) has
    `jmꜣḫw ḫr ḥnwt.f` + queen-funerary-complex attachment, establishing
    queen-attached service — roles must include `steward of the queen`.
    Majority-vote left the list empty.
    """
    r = _row("baud-20")
    assert r["roles"] == ["steward of the queen"], r["roles"]


def test_baud_36_children_neferkare_no_hedge() -> None:
    """2nd-pass egyptologist-reviewer correction: baud-36's title list
    explicitly attests mwt nswt Ḏd-ꜥnḫ-Nfr-kꜣ-Rꜥ — the mother-of-Neferkare
    kinship is title-attested, not inferred. The `(probable)` hedge on
    `children_names` is wrong. Drop it.
    """
    r = _row("baud-36")
    assert r["children_names"] == ["Néferkarê"], r["children_names"]


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
    # Baud sometimes explicitly notes "titres non conservés" — the
    # monument is damaged and the titles are lost. Asterisk-status
    # survives because Baud can still identify the figure as service
    # personnel from context (tomb location, iconography), but TITRES
    # is honestly empty. Sample: baud-138 Nṯr(.j)-pw-nswt.
    titles_lost_re = re.compile(
        r"(titres non conservés|titres perdus|titres non préservés|titres non attestés)",
        re.IGNORECASE,
    )
    for r in _rows():
        if not r["service_personnel"]:
            continue
        if r["titles_from_baud"]:
            continue
        notes = r["notes_from_baud"] or ""
        if titles_lost_re.search(notes):
            continue
        raise AssertionError(
            f"{r['baud_id']} is service_personnel=True but has no titles "
            f"and no titres-non-conservés note — Baud's asterisk marks "
            f"function-attached personnel, so TITRES must exist unless "
            f"Baud explicitly notes the titles were lost. Likely "
            f"extraction miss."
        )


def test_ptahshepses_baud_68_flagship_row() -> None:
    """Chunk-2 flagship — baud-68 is Ptahshepses of Saqqara, the High Priest
    of Ptah whose biography (Urk. I 51–53) documents his career from
    Menkaourê to Niouserrê and his marriage to the king's daughter
    Ḫꜥ-Mꜣꜥt. Every populated field is asserted per rule 5.
    """
    r = _row("baud-68")
    assert r["name_egyptian"] == "Ptḥ-špss"
    assert r["name_anglicised"] is None
    assert r["service_personnel"] is False
    assert r["monument"] == (
        "Mastaba C 1 (nᵒ 48), secteur au nord de la pyramide à degrés, Saqqara"
    )
    assert r["localisation"] == "Saqqara"
    assert r["pm_ref"] == "PM 464"
    assert r["date_attested"] == "Niouserrê"
    assert r["dynasty"] == "5"
    assert r["sub_period"] is None
    assert r["baud_refs"] == {"baer": "164"}
    assert r["titles_from_baud"] == [
        "jzw nj ḥwt Ptḥ",
        "jmj-r wꜥbw Ptḥ",
        "jmj-r wꜥbt",
        "jmj-r pr Zkr",
        "jmj-r st ḏfꜣw",
        "wr ḫrp ḥmwwt",
        "wr ḫrp ḥmwwt m pruj (var. nj rꜥ ḥb)",
        "mhnk nswt (var. nj rꜥ ḥb)",
        "ḥm-nṯr (jmj-ḫnt-wr, Ptḥ, Mꜣꜥt, etc.)",
        "ḥm-nṯr Rꜥ m Nḫn-Rꜥ",
        "ḥm-nṯr Rꜥ m Sḫt-Rꜥ",
        "ḥm-nṯr Rꜥ m Szp-jb-Rꜥ",
        "ḥm-nṯr Rꜥ Ḥwt-Ḥr m St-jb-Rꜥ m swt.f (j)ptn",
        "ḥrj-sštꜣ",
        "ḥrj-sštꜣ n nṯr.f",
        "ḥrp ḥwt ṯhnwt",
        "ḥrp ḥmwwt",
        "ḥrp sm",
    ]
    assert r["roles"] == [
        "sem priest",
        "king's son-in-law",
        "priest of the king",
        "high priest of Ptah",
    ]
    assert r["father_name"] is None
    assert r["mother_name"] is None
    assert r["spouse_names"] == ["Ḫꜥ-Mꜣꜥt"]
    assert r["children_names"] == []
    assert r["tomb"] is None
    assert r["notes_from_baud"] == (
        "Époux de la fille royale Ḫꜥ-Mꜣꜥt [170]. "
        "Sa biographie relate les grandes étapes de sa vie depuis Menkaourê."
    )
    assert r["source_citation"] == {
        "source": "Baud 1999 BdE 126 Corpus [68]",
        "pdf_pages": "49-82",
        "edition": "IFAO 1999 vol. 2",
    }


def test_baud_60a_sub_entry_shape() -> None:
    """Baud's rare sub-entry numbering: `[60a] Pn-mdw` sits between [60]
    and [61] on physical p. 63 — a graffito-only attested prince in
    Pépi I's funerary complex. Minimal attestation: zꜣ nswt smsw alone.
    """
    r = _row("baud-60a")
    assert r["name_egyptian"] == "Pn-mdw"
    assert r["service_personnel"] is False
    assert r["titles_from_baud"] == ["zꜣ nswt smsw"]
    assert r["source_citation"]["source"] == "Baud 1999 BdE 126 Corpus [60a]"


def test_baud_42_drops_eldest_son_without_smsw() -> None:
    """CHUNK2_CORRECTIONS regression: baud-42's TITRES has `[zꜣ nswt] nj
    ẖt.f mrr jt.f` — `nj ẖt.f` attests body-son, but without `smsw` the
    `king's eldest son of his body` vocab term is not attested. Drop to
    `king's son` only.
    """
    r = _row("baud-42")
    assert r["roles"] == ["king's son"], r["roles"]


def test_baud_55_father_is_null_not_per_baud() -> None:
    """CHUNK2_CORRECTIONS regression: parallel to chunk-1 baud-33. Baud
    reports Reisner's hypothesis of Dwꜣ-n-Rꜥ as father, not himself
    endorsing — third-party hypothesis → null, not `(per Baud)`.
    """
    r = _row("baud-55")
    assert r["father_name"] is None, r["father_name"]
    assert "Reisner" in (r["notes_from_baud"] or "")


def test_baud_57_adds_priest_of_royal_pyramid() -> None:
    """CHUNK2_CORRECTIONS regression: baud-57's `ḥm-nṯr Rꜥ-ḏd.f` (priest
    of Rêdjedef's cult) attests `priest of the royal pyramid` —
    additive role, same pattern as chunk-1 baud-28/40.
    """
    r = _row("baud-57")
    assert "priest of the royal pyramid" in r["roles"]


def test_baud_62_ornaments_not_treasury() -> None:
    """CHUNK2_CORRECTIONS regression: baud-62's TITRES (`ḥkr nswt`) is
    king's-ornaments, not treasury. Chunk-2 vocab adds `overseer of the
    king's ornaments`; majority-vote had miscoded as the treasury term.
    """
    r = _row("baud-62")
    assert r["roles"] == ["overseer of the king's ornaments"], r["roles"]


def test_baud_64_steward_not_priest_of_mother() -> None:
    """CHUNK2_CORRECTIONS regression: baud-64's `ḥqꜣ ḥwt-ꜥꜣt ḥwt Mr.s-ꜥnḫ`
    is estate-administrator of the king's mother's funerary domain —
    steward, not priest. Chunk-2 vocab expands to `steward of the king's
    mother`.
    """
    r = _row("baud-64")
    assert r["roles"] == ["steward of the king's mother"], r["roles"]


def test_baud_66_spouse_hedge_preserved() -> None:
    """CHUNK2_CORRECTIONS regression: Baud wrote `Époux (?) de la fille
    royale Mrwt Zšzšt` — the literal question mark is Baud's own
    hedge. README hedge-level 4 preserves `X (?)` verbatim.
    """
    r = _row("baud-66")
    assert r["spouse_names"] == ["Mrwt Zšzšt (?)"], r["spouse_names"]


def test_baud_68_high_priest_of_ptah() -> None:
    """CHUNK2_CORRECTIONS regression: `wr ḫrp ḥmwwt` is the canonical
    title of the High Priest of Ptah at Memphis. Baud-68 Ptahshepses is
    the paradigmatic holder. Vocab added in this chunk.
    """
    r = _row("baud-68")
    assert "high priest of Ptah" in r["roles"]


def test_baud_43_drops_wrong_steward_of_queen() -> None:
    """CHUNK2_CORRECTIONS regression: baud-43's `jmj-r ḥmw-kꜣ (nw zꜣt
    nswt...?)` overseer-of-ka-priests scopes to a king's daughter, not
    a queen — `steward of the queen` was semantically wrong. Role
    dropped.
    """
    r = _row("baud-43")
    assert "steward of the queen" not in r["roles"]


def test_baud_10_steward_of_kings_children() -> None:
    """Chunk-2 vocab backfill (CHUNK1_BACKFILL): baud-10's `jmj-r pr ...
    msw nswt` title scopes to the king's children's household. Role
    added in the chunk-2 PR once the controlled vocab accepts it.
    """
    r = _row("baud-10")
    assert r["roles"] == ["steward of the king's children"], r["roles"]


def test_baud_25_steward_of_kings_children() -> None:
    """CHUNK1_BACKFILL: baud-25's `jmj-r sbꜣ n msw nswt nw ẖt.f` maps to
    the same vocabulary role as baud-10/34/40."""
    r = _row("baud-25")
    assert r["roles"] == ["steward of the king's children"], r["roles"]


def test_baud_34_steward_of_kings_children() -> None:
    """CHUNK1_BACKFILL: baud-34 holds `jmj-r prw msw nswt` — the canonical
    Egyptian form of the role."""
    r = _row("baud-34")
    assert r["roles"] == ["steward of the king's children"], r["roles"]


def _load_fix_rows_module():
    """Load fix_rows.py by file path — the source dir name has hyphens,
    so it's not importable via `importlib.import_module`."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "baud_fix_rows", SOURCE_DIR / "fix_rows.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_all_corrections_includes_every_correction_list() -> None:
    """Every module-level `*_CORRECTIONS` / `*_BACKFILL` list in
    fix_rows.py MUST appear in ALL_CORRECTIONS. Dropping one silently
    destroys that correction set's audit trail.

    Predicate covers any module-level constant whose name ends in
    `_CORRECTIONS` or `_BACKFILL` and whose value is a list — not
    just `CHUNK*` lists. Sweep-2026 introduced `SWEEP_2026_CORRECTIONS`,
    a non-CHUNK list; the original `name.startswith("CHUNK")` filter
    silently failed to cover it (PR #123 code-reviewer P1). Broadened
    here so any future review-round / sweep / backfill list with the
    same shape is mechanically verified.

    Excludes the aggregator itself (`ALL_CORRECTIONS`), the flattened
    output (`SPOT_CORRECTIONS`), and any list whose values are not the
    `(baud_id, field, value, rationale)` correction tuple shape.
    """
    mod = _load_fix_rows_module()
    # Filter by name + type only. The shape-validation moves into the
    # loop body so that a malformed list (e.g. someone adding a
    # 3-tuple instead of a 4-tuple) fails LOUD instead of getting
    # silently excluded by the predicate. The whole point of this
    # tripwire is "no silent skips" — applying the shape check as a
    # filter would create a hole exactly the kind of hole the test
    # exists to prevent (Gemini round-3 finding on PR #123).
    correction_lists = {
        name: getattr(mod, name)
        for name in dir(mod)
        if (name.endswith("_CORRECTIONS") or name.endswith("_BACKFILL"))
        and name not in ("ALL_CORRECTIONS", "SPOT_CORRECTIONS", "SPOT_CORRECTION")
        and isinstance(getattr(mod, name), list)
    }
    aggregator = mod.ALL_CORRECTIONS
    for name, lst in correction_lists.items():
        # Shape check first — every correction-list entry MUST be a
        # 4-tuple (baud_id, field, value, rationale). A malformed list
        # is its own bug; surface it here loudly rather than letting
        # it slip through.
        for idx, entry in enumerate(lst):
            assert isinstance(entry, tuple) and len(entry) == 4, (
                f"{name}[{idx}] is not a 4-tuple "
                f"(baud_id, field, value, rationale): got "
                f"type={type(entry).__name__} value={entry!r}"
            )
        assert lst in aggregator, (
            f"{name} is a module-level correction list but does not appear "
            f"in ALL_CORRECTIONS. Add it, or its overrides will silently "
            f"stop applying. (Predicate matches any *_CORRECTIONS / "
            f"*_BACKFILL list of correction tuples — not just CHUNK* lists.)"
        )


def test_chunk_expected_rows_constants_match_row_count() -> None:
    """Omission-catch for CHUNK*_EXPECTED_ROWS — every module-level constant
    of that shape contributes to the running total; a missing one
    de-syncs test_row_count from actual row count on a subsequent chunk.
    """
    import sys

    mod = sys.modules[__name__]
    chunk_counts = {
        name: getattr(mod, name)
        for name in dir(mod)
        if name.startswith("CHUNK") and name.endswith("_EXPECTED_ROWS")
    }
    assert sum(chunk_counts.values()) == len(_rows()), (
        f"row-count sum {sum(chunk_counts.values())} != actual "
        f"{len(_rows())}; chunk counts: {chunk_counts}"
    )


def test_baud_29_full_row_after_sweep() -> None:
    """Sweep-2026 P1 (code-review L29). baud-29 (Jdw)'s titulary is
    `[jrj-pꜥt, zꜣ nswt smsw]` — `smsw` alone, no `nj ẖt.f` marker. The
    `king's eldest son of his body` vocab term requires BOTH markers
    in the SAME title string. Drop the role; `king's son` retained.

    Pins every populated field per Rule 5 — not just the `roles` field
    the correction touched, so a regression in any other field on this
    row would surface here.
    """
    r = _row("baud-29")
    assert r["baud_id"] == "baud-29"
    assert r["baud_refs"] == {}
    assert r["children_names"] == []
    assert r["date_attested"] == "Pépi II (ou plus)"
    assert r["dynasty"] == "6"
    assert r["father_name"] is None
    assert r["localisation"] == "Saqqara-Sud"
    assert r["monument"] == (
        "Table d'offrandes découverte près du mastaba M 15"
    )
    assert r["mother_name"] is None
    assert r["name_anglicised"] is None
    assert r["name_egyptian"] == "Jdw"
    assert r["notes_from_baud"] == (
        "Peut-être le même personnage que Jdw-tp-kꜣw [30], "
        "hypocoristique en Jdw."
    )
    assert r["pm_ref"] == "PM 684"
    assert r["roles"] == ["king's son"]
    assert r["service_personnel"] is False
    assert r["source_citation"] == {
        "edition": "IFAO 1999 vol. 2",
        "pdf_pages": "11-49",
        "source": "Baud 1999 BdE 126 Corpus [29]",
    }
    assert r["spouse_names"] == []
    assert r["sub_period"] is None
    assert r["titles_from_baud"] == ["jrj-pꜥt", "zꜣ nswt smsw"]
    assert r["tomb"] is None


def test_baud_30_full_row_after_sweep() -> None:
    """Sweep-2026 P1 (code-review L30). baud-30 (Jdw-tp-kꜣw) mirrors
    baud-29 — `[jrj-pꜥt, zꜣ nswt smsw]`, no `nj ẖt.f`. Same conjunction-
    rule violation. `king's eldest son of his body` dropped.

    Pins every populated field per Rule 5.
    """
    r = _row("baud-30")
    assert r["baud_id"] == "baud-30"
    assert r["baud_refs"] == {"baer": "80", "schmitz": "36 (358)"}
    assert r["children_names"] == []
    assert r["date_attested"] == "Pépi II (ou plus)"
    assert r["dynasty"] == "6"
    assert r["father_name"] is None
    assert r["localisation"] == "Saqqara-Sud"
    assert r["monument"] == "Obélisque découvert à proximité du mastaba M 13"
    assert r["mother_name"] is None
    assert r["name_anglicised"] is None
    assert r["name_egyptian"] == "Jdw-tp-kꜣw"
    assert r["notes_from_baud"] is None
    assert r["pm_ref"] == "PM 683"
    assert r["roles"] == ["king's son"]
    assert r["service_personnel"] is False
    assert r["source_citation"] == {
        "edition": "IFAO 1999 vol. 2",
        "pdf_pages": "11-49",
        "source": "Baud 1999 BdE 126 Corpus [30]",
    }
    assert r["spouse_names"] == []
    assert r["sub_period"] is None
    assert r["titles_from_baud"] == ["jrj-pꜥt", "zꜣ nswt smsw"]
    assert r["tomb"] is None


def test_baud_57_full_row_after_sweep() -> None:
    """Sweep-2026 P1 (code-review L57). baud-57 (Bꜣ-kꜣ.j) carries
    `zꜣ nswt nj ẖt.f mrjj.f` AND `zꜣ nswt smsw` as TWO SEPARATE title
    strings — neither single string contains both markers. The
    conjunction rule fails. Drop `king's eldest son of his body`;
    `priest of the king` + `priest of the royal pyramid` remain
    (set by CHUNK2_CORRECTIONS — SWEEP_2026 supersedes via the
    `(baud-57, roles)` `_ALLOWED_DUPLICATES` entry).

    Pins every populated field per Rule 5.
    """
    r = _row("baud-57")
    assert r["baud_id"] == "baud-57"
    assert r["baud_refs"] == {"baer": "126", "schmitz": "22-23 (359)"}
    assert r["children_names"] == []
    assert r["date_attested"] == "Rêdjedef"
    assert r["dynasty"] == "4"
    assert r["father_name"] == "Rêdjedef"
    assert r["localisation"] == "Abou Rawash"
    assert r["monument"] == (
        "Socle de statue accroupie, découvert dans le temple "
        "funéraire de Rêdjedef à Abou Rawash"
    )
    assert r["mother_name"] is None
    assert r["name_anglicised"] is None
    assert r["name_egyptian"] == "Bꜣ-kꜣ.j"
    assert r["notes_from_baud"] == (
        "Étant donné les titres, il s'agit certainement d'un fils de "
        "Rêdjedef."
    )
    assert r["pm_ref"] == "PM 3"
    assert r["roles"] == [
        "king's son",
        "priest of the king",
        "priest of the royal pyramid",
    ]
    assert r["service_personnel"] is False
    assert r["source_citation"] == {
        "edition": "IFAO 1999 vol. 2",
        "pdf_pages": "49-82",
        "source": "Baud 1999 BdE 126 Corpus [57]",
    }
    assert r["spouse_names"] == []
    assert r["sub_period"] is None
    assert r["titles_from_baud"] == [
        "ḥm-nṯr Rꜥ-ḏd.f",
        "ḥrj-wdb ḥwt-ꜥnḫ",
        "ḥrj-tp Nḫb",
        "ḥrp ꜥḥ",
        "smr",
        "smr wꜥtj",
        "zꜣ nswt nj ẖt.f mrjj.f",
        "zꜣ nswt smsw",
        "nb jmꜣḫ ḫr jt.f",
    ]
    assert r["tomb"] is None


def test_baud_126_full_row_after_sweep() -> None:
    """Sweep-2026 P1 (reviewer-notes baud-126). Baud's fig. 40 (vol. 2
    pp. 496–498) separates Mḥw's two wives' children — Nbt is mother
    of Kꜣ.j-ḥtp; Nfr-kꜣw.s Jkw (this row) is mother of Mrwt only.
    Strip Kꜣ.j-ḥtp from this row's `children_names`.

    Pins every populated field per Rule 5.
    """
    r = _row("baud-126")
    assert r["baud_id"] == "baud-126"
    assert r["baud_refs"] == {}
    assert r["children_names"] == ["Mrwt"]
    assert r["date_attested"] == "Pépi Iᵉʳ"
    assert r["dynasty"] == "6"
    assert r["father_name"] is None
    assert r["localisation"] == "nécropole d'Ounas, Saqqara"
    assert r["monument"] == (
        "Représentée dans le mastaba de son époux Mḥw [89], "
        "nécropole d'Ounas, Saqqara"
    )
    assert r["mother_name"] is None
    assert r["name_anglicised"] is None
    assert r["name_egyptian"] == "Nfr-kꜣw.s Jkw"
    assert r["notes_from_baud"] == (
        "Peut-être fille d'Ounas en vertu de la localisation "
        "(Strudwick); Baud ne s'engage pas."
    )
    assert r["pm_ref"] == "PM 619-622"
    assert r["roles"] == ["king's daughter"]
    assert r["service_personnel"] is False
    assert r["source_citation"] == {
        "edition": "IFAO 1999 vol. 2",
        "pdf_pages": "109-141",
        "source": "Baud 1999 BdE 126 Corpus [126]",
    }
    assert r["spouse_names"] == ["Mḥw"]
    assert r["sub_period"] is None
    assert r["titles_from_baud"] == ["zꜣt nswt nt ẖt.f"]
    assert r["tomb"] is None


def test_baud_89_notes_pointer_to_kahetep_filiation() -> None:
    """Sweep-2026 P2 (egyptologist-reviewer PR #123): when baud-126
    stripped Kꜣ.j-ḥtp from Nfr-kꜣw.s Jkw's children, his filiation
    became invisible in the corpus (Mḥw's other wife Nbt is not yet
    a Baud headword). Append a pointer to baud-89 (Mḥw)'s
    notes_from_baud so readers see where the missing filiation
    lives in Baud, with a tracking-issue link (#125) for the
    eventual headword.
    """
    r = _row("baud-89")
    assert r["name_egyptian"] == "Mḥw"
    assert r["spouse_names"] == ["Nfr-kꜣw.s Jkw"]
    notes = r["notes_from_baud"]
    assert notes is not None
    assert "Nbt" in notes
    assert "Kꜣ.j-ḥtp" in notes
    assert "fig. 40" in notes
    assert "issue #125" in notes


def test_eldest_son_role_requires_smsw_and_nj_khet_f_in_same_title() -> None:
    """Deterministic invariant (code-review-sweep-2026 P2 / Rule 3
    coverage). For every row carrying `king's eldest son of his body`
    in `roles`, at least ONE entry in `titles_from_baud` must contain
    BOTH `smsw` and `nj ẖt.f` substrings within the SAME single title
    string. This catches the systemic over-claim pattern fixed in
    chunks 2/3/4/5/7 and the sweep-2026 PR (baud-29, baud-30, baud-57)
    across ALL rows, not just the ones flagged by individual reviewer
    passes.

    Rationale: Baud's vocabulary (and OK Egyptian titulary in general)
    distinguishes:
      - `zꜣ nswt smsw` — "king's eldest son" (an ordinal claim).
      - `zꜣ nswt nj ẖt.f` — "king's son of his body" (an attestation
        of biological direct kinship, distinguishing from titular sons).
      - `zꜣ nswt smsw nj ẖt.f` (or its variants `zꜣ nswt nj ẖt.f
        smsw`, `zꜣ nswt nj ẖt.f smsw mrjj.f`, etc.) — "king's eldest
        son of his body", the conjunction.
    The vocab term `king's eldest son of his body` corresponds ONLY to
    the conjunction. Two separate titles each carrying one marker do
    not satisfy it.

    Caveat — proxy: "BOTH markers in the SAME single title string" is
    a deterministic proxy for "the composite title `smsw n(j) ẖt.f`
    is attested for this person as one morphological unit." Baud's
    TITRES rubric reliably emits each composite title as a single
    list item, so the proxy holds in practice for this corpus. A
    line-broken composite (which Baud doesn't produce) would slip
    past — accept that loss; it has not occurred in 282 rows. The
    role-derivation policy itself is documented in the source's
    README.md ("Role-derivation conventions").
    """
    # Strip editorial brackets `[]` and `<>` before the substring check
    # so reconstructed/restored titles like `zꜣ nsw[t] nj ẖt.f` or
    # `zꜣ nswt nj ẖt.f <smsw>` still match. Per Gemini round-3 feedback
    # on PR #123: brackets are a documented Baud convention for
    # reconstructed text and are NOT semantic content; they should not
    # cause false negatives in this conjunction test.
    bracket_strip = str.maketrans("", "", "[]<>")
    for r in _rows():
        if "king's eldest son of his body" not in r["roles"]:
            continue
        conjoined = [
            t for t in r["titles_from_baud"]
            if "smsw" in t.translate(bracket_strip)
            and "nj ẖt.f" in t.translate(bracket_strip)
        ]
        assert conjoined, (
            f"{r['baud_id']}: roles include `king's eldest son of his "
            f"body` but no titles_from_baud entry contains both `smsw` "
            f"and `nj ẖt.f` in the same string (after stripping "
            f"editorial brackets `[]` and `<>`). "
            f"titles_from_baud={r['titles_from_baud']}"
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


# =============================================================================
# Issue #178 schema-audit closure tests
# =============================================================================
#
# Per the strict-all-P1 policy (#176/#177): every typed field exists on every
# row, every enum is bounded, every cross-ref resolves to an existing baud_id.

ISSUE_178_NEW_FIELDS = (
    "is_joint_entry",
    "co_holders",
    "entry_kind",
    "name_status",
    "candidate_baud_ids",
    "pm_refs",
    "monuments",
    "father_baud_id",
    "father_confidence",
    "mother_baud_id",
    "mother_confidence",
    "spouse_baud_ids",
    "children_baud_ids",
)
ENTRY_KIND_VOCAB = {"person", "joint_persons", "collective_monument", "attribution_pending"}
NAME_STATUS_VOCAB = {"attested", "lost", "tentative", "anonymous"}
CONFIDENCE_VOCAB = {None, "probable", "per_baud", "uncertain"}


def test_178_every_row_has_every_new_field() -> None:
    """Closure: every issue-#178 typed field is present on every row."""
    for r in _rows():
        missing = [f for f in ISSUE_178_NEW_FIELDS if f not in r]
        assert not missing, f"{r['baud_id']}: missing fields {missing!r}"


def test_178_entry_kind_is_in_vocab() -> None:
    for r in _rows():
        assert r["entry_kind"] in ENTRY_KIND_VOCAB, (
            f"{r['baud_id']}: entry_kind={r['entry_kind']!r} not in vocab"
        )


def test_178_name_status_is_in_vocab() -> None:
    for r in _rows():
        assert r["name_status"] in NAME_STATUS_VOCAB, (
            f"{r['baud_id']}: name_status={r['name_status']!r} not in vocab"
        )


def test_178_confidence_enums_bounded() -> None:
    for r in _rows():
        for f in ("father_confidence", "mother_confidence"):
            assert r[f] in CONFIDENCE_VOCAB, (
                f"{r['baud_id']}: {f}={r[f]!r} not in vocab"
            )


def test_178_pm_refs_is_list_of_str() -> None:
    for r in _rows():
        assert isinstance(r["pm_refs"], list), f"{r['baud_id']}: pm_refs not list"
        for ref in r["pm_refs"]:
            assert isinstance(ref, str) and ref.strip() == ref and ref, (
                f"{r['baud_id']}: pm_refs entry {ref!r} malformed"
            )


def test_178_monuments_is_structured_list() -> None:
    for r in _rows():
        assert isinstance(r["monuments"], list)
        for m in r["monuments"]:
            assert set(m.keys()) == {"document_id", "monument", "localisation"}, (
                f"{r['baud_id']}: monuments entry has unexpected keys {set(m.keys())!r}"
            )
            assert isinstance(m["document_id"], int)
            assert isinstance(m["monument"], str) and m["monument"]


def test_178_baud_id_cross_refs_resolve() -> None:
    """Every father_baud_id / mother_baud_id / spouse / children / candidate /
    co_holders id must point to a row that exists."""
    all_ids = {r["baud_id"] for r in _rows()}
    for r in _rows():
        for f in ("father_baud_id", "mother_baud_id"):
            v = r[f]
            if v is not None:
                assert v in all_ids, f"{r['baud_id']}: {f}={v!r} unresolved"
        for f in ("spouse_baud_ids", "children_baud_ids", "candidate_baud_ids"):
            for v in r[f]:
                if v is not None:
                    assert v in all_ids, f"{r['baud_id']}: {f} entry {v!r} unresolved"


def test_178_joint_entry_has_co_holders() -> None:
    """If is_joint_entry is True, co_holders must have ≥ 2 entries and
    entry_kind must be joint_persons."""
    for r in _rows():
        if r["is_joint_entry"]:
            assert len(r["co_holders"]) >= 2, (
                f"{r['baud_id']}: joint entry has <2 co_holders"
            )
            assert r["entry_kind"] == "joint_persons", (
                f"{r['baud_id']}: joint entry has entry_kind={r['entry_kind']!r}"
            )


def test_178_baud_209_joint_entry_canonical() -> None:
    """Anchor: baud-209 is the documented Snj + Zzj joint entry."""
    r = _row("baud-209")
    assert r["is_joint_entry"] is True
    assert r["entry_kind"] == "joint_persons"
    assert r["co_holders"] == [
        {"name": "Snj", "service_personnel": True},
        {"name": "Zzj", "service_personnel": True},
    ]


def test_178_baud_39_attribution_pending_canonical() -> None:
    r = _row("baud-39")
    assert r["entry_kind"] == "attribution_pending"
    assert r["candidate_baud_ids"] == ["baud-37", "baud-38"]


def test_178_collective_monument_canonical_set() -> None:
    """Anchor: rows whose entry_kind is collective_monument exactly match the
    audit-documented monument-as-occupant set. baud-256 is NOT in this set
    — it is an anonymous person on a Sinai relief, not a monument."""
    expected = {"baud-257", "baud-267", "baud-276", "baud-279"}
    actual = {r["baud_id"] for r in _rows() if r["entry_kind"] == "collective_monument"}
    assert actual == expected, f"collective_monument set drift: {actual ^ expected}"


def test_178_baud_256_is_anonymous_person_not_monument() -> None:
    """baud-256 = "Représentation anonyme, expedition leader, Sinaï" is an
    anonymous PERSON on a relief, not a monument-as-occupant. Regression
    against the initial draft that mis-routed it to collective_monument."""
    r = _row("baud-256")
    assert r["entry_kind"] == "person"
    assert r["name_status"] == "anonymous"


def test_178_per_document_localisation_extracted() -> None:
    """Anchor: baud-22 doc 2 says "à Héliopolis" — per-document localisation
    overrides the row's "Saqqara" default. Regression against the initial
    draft that copied the row-level localisation to all documents."""
    r = _row("baud-22")
    assert r["localisation"] == "Saqqara"
    docs = {m["document_id"]: m for m in r["monuments"]}
    assert docs[1]["localisation"] == "Saqqara"
    assert docs[2]["localisation"] == "Héliopolis", docs[2]


def test_178_lost_name_canonical_set() -> None:
    """Anchor: lost-name rows exactly match the audit-documented set."""
    expected = {
        "baud-258", "baud-260", "baud-262", "baud-263", "baud-264",
        "baud-269", "baud-270", "baud-271", "baud-272", "baud-274",
        "baud-277", "baud-282",
    }
    actual = {r["baud_id"] for r in _rows() if r["name_status"] == "lost"}
    assert actual == expected, f"lost-name set drift: {actual ^ expected}"


def test_178_pm_refs_pm_prefix_continuation_restored() -> None:
    """`PM 407 et 414` must split to ['PM 407', 'PM 414'] — the elided
    PM prefix on the continuation token is restored."""
    r = _row("baud-22")
    assert "PM 407 et 414" == r["pm_ref"]
    assert r["pm_refs"] == ["PM 407", "PM 414"], r["pm_refs"]


def test_178_father_confidence_extracts_hedge_token() -> None:
    """Per-row sanity: every father_confidence value matches its hedge token."""
    candidates = [r for r in _rows() if r["father_confidence"] == "per_baud"]
    assert candidates, "no per_baud-hedged father rows found"
    for r in candidates:
        assert r["father_name"] is not None
        assert "per baud" in r["father_name"].lower(), (
            f"{r['baud_id']}: father_confidence=per_baud but father_name "
            f"{r['father_name']!r} lacks the marker"
        )
