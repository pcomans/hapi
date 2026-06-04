"""Phase-0 → claim-graph loader (ADR-018 § Consequences).

Reads per-source ``reconciled.jsonl`` and emits per-source E13 Statements into a
substrate-neutral ``ClaimGraph`` — never collapsing across sources. Each row
becomes one ``:Ruler`` (E21) node keyed by ``<source>::<source_id>``; each fact
becomes an E13 with the universal P140/P141/P177 spine plus the human-documentary
provenance shape (P14 → scholar, P70i → publication with page locators).

POC scope: Leprohon (English titulary) + Beckerath (German chronology). The
claim predicates emitted are exactly the ADR registry's primary set that these
two sources populate: ``hapi:display_name``, ``hapi:in_dynastic_period``,
``hapi:horus_name`` (Leprohon), ``hapi:reign_period`` (Beckerath). Throne
names / prenomina are out of slice (no registry predicate yet).

The loader trusts the reconciled value as-is (Rule-2 resolution already happened
upstream per-source) and never re-resolves at the graph layer.
"""

from __future__ import annotations

import json
from pathlib import Path

from .ir import ClaimGraph, Edge, Node
from .registry import load_registry

_SOURCES_DIR = Path(__file__).resolve().parent.parent / "sources"

# -- spine property local names (CIDOC) -------------------------------------
P140 = "P140_assigned_attribute_to"
P141 = "P141_assigned"
P177 = "P177_assigned_property_of_type"
P14 = "P14_carried_out_by"
P70i = "P70i_is_documented_in"


# ---------------------------------------------------------------------------
# Catalogue seeding: scholars (E21), publications (E31), predicate-type E55s
# ---------------------------------------------------------------------------
def _seed_actor_and_document_catalogue(g: ClaimGraph) -> None:
    g.add_node(Node("person::leprohon_rj", ("E21",), {"full_name": "Ronald J. Leprohon"}, "Person"))
    g.add_node(Node("person::beckerath_j", ("E21",), {"full_name": "Jürgen von Beckerath"}, "Person"))
    g.add_node(
        Node(
            "document::leprohon_2013",
            ("E31",),
            {
                "kind": "publication",
                "citation": "Leprohon, The Great Name: Ancient Egyptian Royal Titulary (SBL, 2013)",
                "year": 2013,
                "language": "en",
            },
            "Document",
        )
    )
    g.add_node(
        Node(
            "document::beckerath_1997",
            ("E31",),
            {
                "kind": "publication",
                "citation": "von Beckerath, Chronologie des pharaonischen Ägypten (MÄS 46, von Zabern, 1997)",
                "year": 1997,
                "language": "de",
            },
            "Document",
        )
    )


def _ensure_predicate_type_node(g: ClaimGraph, predicate_id: str) -> str:
    """Ensure the :E55 Type registry node for a primary predicate exists.

    Returns the node id. Loading a P177 target whose predicate is not a primary
    (p177_target) registry entry raises (FK-style enforcement, ADR principle 4).
    """
    reg = load_registry()
    pred = reg.get(predicate_id)
    if pred is None:
        raise ValueError(f"Unknown predicate {predicate_id!r} (not in registry)")
    if not pred.p177_target:
        raise ValueError(
            f"Predicate {predicate_id!r} is derived/query-only; the loader REJECTS "
            f"E13 reifications whose P177 target is a derived predicate (ADR-018)"
        )
    node_id = f"type::{predicate_id}"
    g.add_node(Node(node_id, ("E55",), {"id": predicate_id}, "Type"))
    return node_id


def _ensure_dynasty(g: ClaimGraph, number: int) -> str:
    node_id = f"dynasty::{number}"
    g.add_node(Node(node_id, ("E4",), {"number": number}, "Dynasty"))
    return node_id


# ---------------------------------------------------------------------------
# Statement construction (the E13 spine + human-documentary provenance)
# ---------------------------------------------------------------------------
def _add_human_statement(
    g: ClaimGraph,
    *,
    stmt_id: str,
    subject_id: str,
    predicate_id: str,
    value_id: str,
    actor_id: str,
    document_id: str,
    cited_page: object | None = None,
    cited_pdf_page: object | None = None,
) -> str:
    """Create one E13 with P140/P141/P177 + P14 + P70i (page locators on P70i)."""
    type_node = _ensure_predicate_type_node(g, predicate_id)
    g.add_node(Node(stmt_id, ("E13",), {}, "Statement"))
    g.add_edge(Edge(stmt_id, P140, subject_id))
    g.add_edge(Edge(stmt_id, P141, value_id))
    g.add_edge(Edge(stmt_id, P177, type_node))
    g.add_edge(Edge(stmt_id, P14, actor_id))
    locator: dict[str, object] = {}
    if cited_page is not None:
        locator["cited_page"] = cited_page
    if cited_pdf_page is not None:
        locator["cited_pdf_page"] = cited_pdf_page
    g.add_edge(Edge(stmt_id, P70i, document_id, locator))
    return stmt_id


# ---------------------------------------------------------------------------
# Leprohon
# ---------------------------------------------------------------------------
def load_leprohon(g: ClaimGraph, path: Path | None = None) -> int:
    path = path or _SOURCES_DIR / "leprohon-2013-titulary" / "reconciled.jsonl"
    actor = "person::leprohon_rj"
    doc = "document::leprohon_2013"
    rows = 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rid = row["leprohon_id"]
        ruler_id = f"leprohon::{rid}"
        g.add_node(
            Node(ruler_id, ("E21",), {"source": "leprohon", "source_id": rid}, "Ruler")
        )
        cited = row.get("source_citation") or {}
        page = cited.get("printed_page")
        pdf = cited.get("physical_pdf_page")

        # display_name → E41 Appellation (English).
        if row.get("display_name"):
            appel = f"appellation::{ruler_id}::display_name"
            g.add_node(
                Node(
                    appel,
                    ("E41",),
                    {
                        "symbolic_content": row["display_name"],
                        "appellation_kind": "display_name",
                        "language": "en",
                    },
                    "Appellation",
                )
            )
            _add_human_statement(
                g,
                stmt_id=f"stmt::{ruler_id}::display_name",
                subject_id=ruler_id,
                predicate_id="hapi:display_name",
                value_id=appel,
                actor_id=actor,
                document_id=doc,
                cited_page=page,
                cited_pdf_page=pdf,
            )

        # in_dynastic_period → E4 Period.
        if row.get("dynasty_number") is not None:
            dyn = _ensure_dynasty(g, row["dynasty_number"])
            _add_human_statement(
                g,
                stmt_id=f"stmt::{ruler_id}::in_dynastic_period",
                subject_id=ruler_id,
                predicate_id="hapi:in_dynastic_period",
                value_id=dyn,
                actor_id=actor,
                document_id=doc,
                cited_page=page,
                cited_pdf_page=pdf,
            )

        # horus_name(s) → E41 Appellation (transliterated Egyptian), one per variant.
        for i, hn in enumerate(row.get("horus_names") or []):
            translit = hn.get("transliteration") or hn.get("anglicised")
            if not translit:
                continue
            appel = f"appellation::{ruler_id}::horus_name::{i}"
            g.add_node(
                Node(
                    appel,
                    ("E41",),
                    {
                        "symbolic_content": translit,
                        "appellation_kind": "horus_name",
                        "anglicised": hn.get("anglicised"),
                        "translation": hn.get("translation"),
                        "language": "egy-Latn",
                    },
                    "Appellation",
                )
            )
            _add_human_statement(
                g,
                stmt_id=f"stmt::{ruler_id}::horus_name::{i}",
                subject_id=ruler_id,
                predicate_id="hapi:horus_name",
                value_id=appel,
                actor_id=actor,
                document_id=doc,
                cited_page=page,
                cited_pdf_page=pdf,
            )
        rows += 1
    return rows


# ---------------------------------------------------------------------------
# Beckerath
# ---------------------------------------------------------------------------
def load_beckerath(g: ClaimGraph, path: Path | None = None) -> int:
    path = path or _SOURCES_DIR / "beckerath-1997-chronologie" / "reconciled.jsonl"
    actor = "person::beckerath_j"
    doc = "document::beckerath_1997"
    rows = 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        # Skip dynasty-marker rows: they are period headers, not rulers
        # (ADR-018 cites Beckerath as "174 rows, 166 non-marker").
        if row.get("is_dynasty_marker"):
            continue
        rid = row["beckerath_id"]
        ruler_id = f"beckerath::{rid}"
        g.add_node(
            Node(ruler_id, ("E21",), {"source": "beckerath", "source_id": rid}, "Ruler")
        )
        cited = row.get("source_citation") or {}
        pdf = cited.get("pdf_pages")

        # display_name → E41 Appellation (German form).
        if row.get("name"):
            appel = f"appellation::{ruler_id}::display_name"
            g.add_node(
                Node(
                    appel,
                    ("E41",),
                    {
                        "symbolic_content": row["name"],
                        "appellation_kind": "display_name",
                        "language": "de",
                    },
                    "Appellation",
                )
            )
            _add_human_statement(
                g,
                stmt_id=f"stmt::{ruler_id}::display_name",
                subject_id=ruler_id,
                predicate_id="hapi:display_name",
                value_id=appel,
                actor_id=actor,
                document_id=doc,
                cited_pdf_page=pdf,
            )

        # in_dynastic_period → E4 Period.
        if row.get("dynasty") is not None:
            dyn = _ensure_dynasty(g, row["dynasty"])
            _add_human_statement(
                g,
                stmt_id=f"stmt::{ruler_id}::in_dynastic_period",
                subject_id=ruler_id,
                predicate_id="hapi:in_dynastic_period",
                value_id=dyn,
                actor_id=actor,
                document_id=doc,
                cited_pdf_page=pdf,
            )

        # reign_period → E52 Time-Span (when boundary years present).
        # Beckerath already stores BCE as signed astronomical years (Menes =
        # -2982). "low"/"high" are magnitude bounds of a fuzzy estimate, so the
        # MAXIMAL span runs from the earliest possible start (start_bce_high, the
        # more-negative) to the latest possible end (end_bce_low). These map to
        # CIDOC E52 P82a begin_of_the_begin / P82b end_of_the_end (encoding
        # convention #3). No negation — the source is already astronomical.
        start_hi = row.get("start_bce_high")
        start_lo = row.get("start_bce_low")
        end_lo = row.get("end_bce_low")
        end_hi = row.get("end_bce_high")
        begin = start_hi if start_hi is not None else start_lo
        end = end_lo if end_lo is not None else end_hi
        if begin is not None or end is not None:
            ts = f"timespan::{ruler_id}::reign"
            g.add_node(
                Node(
                    ts,
                    ("E52",),
                    {
                        "begin_of_the_begin": begin,
                        "end_of_the_end": end,
                        "calendar": "astronomical_year",
                    },
                    "TimeSpan",
                )
            )
            _add_human_statement(
                g,
                stmt_id=f"stmt::{ruler_id}::reign_period",
                subject_id=ruler_id,
                predicate_id="hapi:reign_period",
                value_id=ts,
                actor_id=actor,
                document_id=doc,
                cited_pdf_page=pdf,
            )
        rows += 1
    return rows


def load_poc_graph() -> ClaimGraph:
    """Load the Leprohon + Beckerath vertical slice into a fresh ClaimGraph."""
    g = ClaimGraph()
    _seed_actor_and_document_catalogue(g)
    load_leprohon(g)
    load_beckerath(g)
    return g
