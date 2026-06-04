"""Postgres relational adapter: write the graph + DB-level chain constraints.

Skips automatically when no Postgres is reachable (e.g. the SessionStart hook
hasn't run). When it is reachable, it proves the three verdict-chain constraints
are enforced by the DATABASE — UNIQUE, partial UNIQUE, and the BEFORE-INSERT
trigger — independent of the Python verdict loader.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError

from pipeline.authority.graph.adapters import relational_adapter as rel
from pipeline.authority.graph.ir import ClaimGraph, Node
from pipeline.authority.graph.loader import load_poc_graph
from pipeline.authority.graph.matcher.stage1_deterministic import run_stage1_matcher
from pipeline.authority.graph.verdicts import VERDICT_APPROVED, add_verdict, emit_shortcuts

UNAS_MATCH = "stmt::match::leprohon::leprohon-5.09::beckerath::05.09"
TETI_MATCH = "stmt::match::leprohon::leprohon-6.01::beckerath::06.01"


def _full_graph() -> ClaimGraph:
    g = load_poc_graph()
    run_stage1_matcher(g)
    g.add_node(Node("group::hapi_curatorial", ("E74",), {"name": "Hapi curatorial body"}, "Group"))
    g.add_node(Node("document::curator_2026_05", ("E31",),
                    {"kind": "curator_decision_batch", "decided_at": "2026-05-17"}, "Document"))
    add_verdict(g, matcher_stmt_id=UNAS_MATCH, outcome=VERDICT_APPROVED,
                verdict_id="verdict::unas::1",
                curator_actor="group::hapi_curatorial",
                curator_document="document::curator_2026_05")
    emit_shortcuts(g)
    return g


@pytest.fixture(scope="module")
def engine():
    eng = rel.get_engine()
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.skip(f"Postgres not reachable: {exc}")
    return eng


@pytest.fixture
def written(engine):
    counts = rel.write_graph(engine, _full_graph())
    return engine, counts


def _add_node_row(conn, node_id):
    conn.execute(
        text("INSERT INTO claimgraph.node (id, crm_classes) VALUES (:id, ARRAY['E13'])"),
        {"id": node_id},
    )


def test_write_graph_counts(written):
    _, counts = written
    assert counts["node"] == 3358
    assert counts["edge"] == 9942
    # One verdict (the approved Unas root).
    assert counts["verdict_chain"] == 1


def test_constraint_b_unique_root_enforced_by_db(written):
    engine, _ = written
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            _add_node_row(conn, "verdict::unas::rogue_root")
            conn.execute(
                text(
                    "INSERT INTO claimgraph.verdict_chain "
                    "(verdict_id, matcher_claim_id, predecessor_verdict_id, outcome) "
                    "VALUES ('verdict::unas::rogue_root', :claim, NULL, 'hapi:verdict_approved')"
                ),
                {"claim": UNAS_MATCH},
            )


def test_constraint_a_unique_successor_enforced_by_db(written):
    engine, _ = written
    # Valid supersession of the tip (v1) is accepted.
    with engine.begin() as conn:
        _add_node_row(conn, "verdict::unas::v2")
        conn.execute(text(
            "INSERT INTO claimgraph.verdict_chain VALUES "
            "('verdict::unas::v2', :claim, 'verdict::unas::1', 'hapi:verdict_retracted')"
        ), {"claim": UNAS_MATCH})
    # A second verdict superseding the SAME predecessor (v1) forks the chain.
    with pytest.raises((IntegrityError, DBAPIError)):
        with engine.begin() as conn:
            _add_node_row(conn, "verdict::unas::v3")
            conn.execute(text(
                "INSERT INTO claimgraph.verdict_chain VALUES "
                "('verdict::unas::v3', :claim, 'verdict::unas::1', 'hapi:verdict_rejected')"
            ), {"claim": UNAS_MATCH})


def test_constraint_c_trigger_rejects_cross_claim_predecessor(written):
    engine, _ = written
    # Superseding a predecessor that belongs to a DIFFERENT matcher-claim is
    # rejected by the BEFORE-INSERT trigger (predecessor must be same-claim).
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            _add_node_row(conn, "verdict::teti::bad")
            conn.execute(text(
                "INSERT INTO claimgraph.verdict_chain VALUES "
                "('verdict::teti::bad', :teti, 'verdict::unas::1', 'hapi:verdict_approved')"
            ), {"teti": TETI_MATCH})
    assert "not a verdict for matcher claim" in str(exc.value)
