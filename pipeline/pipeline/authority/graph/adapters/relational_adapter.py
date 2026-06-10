"""Postgres relational adapter (ADR-018 § Storage candidates → Postgres).

Encodes the IR as generic ``node`` / ``edge`` tables in a dedicated
``claimgraph`` schema (kept separate from the pipeline-owned ``catalog`` schema;
production integration is a follow-up), PLUS a ``verdict_chain`` projection that
enforces the three verdict-chain integrity constraints as REAL Postgres
constraints — the whole reason Postgres is a serious storage candidate:

  (a) unique successor per predecessor → UNIQUE(predecessor_verdict_id)
  (b) unique root per matcher-claim    → partial UNIQUE(matcher_claim_id)
                                          WHERE predecessor_verdict_id IS NULL
  (c) insert-time tip-only rule        → BEFORE INSERT trigger (a CHECK cannot
                                          query other rows; ADR says so explicitly)

This adapter proves the constraints hold at the database layer, independent of
the Python verdict loader.
"""

from __future__ import annotations

import json
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from ..ir import ClaimGraph
from ..verdicts import SUPERSEDES, VERDICT_TYPE

DEFAULT_DSN = "postgresql+psycopg2://hapi:hapi@127.0.0.1:5432/hapi_poc"

P140 = "P140_assigned_attribute_to"
P141 = "P141_assigned"
P177 = "P177_assigned_property_of_type"

_SCHEMA_DDL = """
CREATE SCHEMA IF NOT EXISTS claimgraph;

CREATE TABLE IF NOT EXISTS claimgraph.node (
    id           text PRIMARY KEY,
    crm_classes  text[] NOT NULL,
    hapi_label   text,
    props        jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS claimgraph.edge (
    id          bigserial PRIMARY KEY,
    subject_id  text NOT NULL REFERENCES claimgraph.node(id),
    predicate   text NOT NULL,
    object_id   text NOT NULL REFERENCES claimgraph.node(id),
    props       jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS claimgraph.verdict_chain (
    verdict_id              text PRIMARY KEY REFERENCES claimgraph.node(id),
    matcher_claim_id        text NOT NULL REFERENCES claimgraph.node(id),
    predecessor_verdict_id  text REFERENCES claimgraph.verdict_chain(verdict_id),
    outcome                 text NOT NULL,
    -- (a) unique successor per predecessor (NULLs are distinct in Postgres, so
    --     this does NOT block multiple roots — (b) handles that).
    CONSTRAINT verdict_unique_successor UNIQUE (predecessor_verdict_id),
    -- outcome is restricted to the three-term verdict vocabulary (ADR-018).
    CONSTRAINT verdict_outcome_vocabulary CHECK (
        outcome IN ('hapi:verdict_approved', 'hapi:verdict_rejected', 'hapi:verdict_retracted')
    ),
    -- 'retracted' is valid ONLY as a superseding verdict (it withdraws a prior
    --     tip); a root verdict can never be a retraction (ADR-018). Same-row
    --     columns, so a plain CHECK suffices.
    CONSTRAINT verdict_retracted_must_supersede CHECK (
        outcome <> 'hapi:verdict_retracted' OR predecessor_verdict_id IS NOT NULL
    )
);

-- (b) unique root per matcher-claim.
CREATE UNIQUE INDEX IF NOT EXISTS verdict_unique_root
    ON claimgraph.verdict_chain (matcher_claim_id)
    WHERE predecessor_verdict_id IS NULL;

-- (c) insert-time tip-only rule: a non-root verdict must supersede the CURRENT
--     tip of its own matcher-claim's chain. A CHECK constraint cannot query
--     other rows, so this is a trigger (per ADR-018 verdict-vocabulary section).
CREATE OR REPLACE FUNCTION claimgraph.verdict_tip_check() RETURNS trigger AS $$
BEGIN
    IF NEW.predecessor_verdict_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM claimgraph.verdict_chain p
            WHERE p.verdict_id = NEW.predecessor_verdict_id
              AND p.matcher_claim_id = NEW.matcher_claim_id
        ) THEN
            RAISE EXCEPTION
              'supersedes target % is not a verdict for matcher claim %',
              NEW.predecessor_verdict_id, NEW.matcher_claim_id;
        END IF;
        IF EXISTS (
            SELECT 1 FROM claimgraph.verdict_chain s
            WHERE s.predecessor_verdict_id = NEW.predecessor_verdict_id
        ) THEN
            RAISE EXCEPTION
              'supersedes target % is not the current chain tip (already superseded)',
              NEW.predecessor_verdict_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- BEFORE INSERT OR UPDATE: an UPDATE that re-pointed predecessor_verdict_id
--     would otherwise bypass the tip rule (the trigger only fired on INSERT).
DROP TRIGGER IF EXISTS verdict_tip_trigger ON claimgraph.verdict_chain;
CREATE TRIGGER verdict_tip_trigger
    BEFORE INSERT OR UPDATE ON claimgraph.verdict_chain
    FOR EACH ROW EXECUTE FUNCTION claimgraph.verdict_tip_check();
"""


def get_engine(dsn: str | None = None) -> Engine:
    return create_engine(dsn or os.environ.get("HAPI_PG_DSN", DEFAULT_DSN), future=True)


def init_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        for stmt in _split_ddl(_SCHEMA_DDL):
            conn.execute(text(stmt))


def _split_ddl(ddl: str) -> list[str]:
    """Split DDL on ';' but keep the plpgsql function body ($$ ... $$) intact."""
    parts: list[str] = []
    buf: list[str] = []
    in_body = False
    for line in ddl.splitlines():
        if "$$" in line:
            in_body = not in_body if line.count("$$") == 1 else in_body
        buf.append(line)
        if not in_body and line.rstrip().endswith(";"):
            parts.append("\n".join(buf))
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        parts.append(tail)
    return [p for p in (s.strip() for s in parts) if p]


def _verdict_rows(g: ClaimGraph) -> list[dict[str, object]]:
    """Project verdict-E13s + supersedes edges into verdict_chain rows."""
    verdict_type = f"type::{VERDICT_TYPE}"
    supersedes = {e.subject_id: e.object_id for e in g.edges_with_predicate(SUPERSEDES)}
    rows: list[dict[str, object]] = []
    for n in g.nodes_of_class("E13"):
        edges = {e.predicate: e.object_id for e in g.out_edges(n.id)}
        if edges.get(P177) != verdict_type:
            continue
        rows.append(
            {
                "verdict_id": n.id,
                "matcher_claim_id": edges[P140],
                "predecessor_verdict_id": supersedes.get(n.id),
                "outcome": g.node(edges[P141]).props["id"],
            }
        )
    # Roots first so a successor's FK/predecessor already exists on insert.
    rows.sort(key=lambda r: r["predecessor_verdict_id"] is not None)
    return rows


def write_graph(engine: Engine, g: ClaimGraph) -> dict[str, int]:
    """Truncate and rewrite the whole graph. Returns row counts."""
    init_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE claimgraph.verdict_chain, claimgraph.edge, claimgraph.node"))
        conn.execute(
            text(
                "INSERT INTO claimgraph.node (id, crm_classes, hapi_label, props) "
                "VALUES (:id, :classes, :label, CAST(:props AS jsonb))"
            ),
            [
                {
                    "id": n.id,
                    "classes": list(n.crm_classes),
                    "label": n.hapi_label,
                    "props": json.dumps(n.props),
                }
                for n in g.nodes
            ],
        )
        conn.execute(
            text(
                "INSERT INTO claimgraph.edge (subject_id, predicate, object_id, props) "
                "VALUES (:s, :p, :o, CAST(:props AS jsonb))"
            ),
            [
                {"s": e.subject_id, "p": e.predicate, "o": e.object_id, "props": json.dumps(e.props)}
                for e in g.edges
            ],
        )
        vrows = _verdict_rows(g)
        if vrows:
            conn.execute(
                text(
                    "INSERT INTO claimgraph.verdict_chain "
                    "(verdict_id, matcher_claim_id, predecessor_verdict_id, outcome) "
                    "VALUES (:verdict_id, :matcher_claim_id, :predecessor_verdict_id, :outcome)"
                ),
                vrows,
            )
    with engine.connect() as conn:
        counts = {
            "node": conn.execute(text("SELECT count(*) FROM claimgraph.node")).scalar_one(),
            "edge": conn.execute(text("SELECT count(*) FROM claimgraph.edge")).scalar_one(),
            "verdict_chain": conn.execute(
                text("SELECT count(*) FROM claimgraph.verdict_chain")
            ).scalar_one(),
        }
    return counts
