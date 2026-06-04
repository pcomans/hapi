# ADR-018 claim-graph POC

A working proof-of-concept for [ADR-018: Authority Layer as Source-Attributed
Claim Graph](../../../../docs/adr/018-authority-as-claim-graph.md), built on the
**Leprohon + Beckerath** vertical slice.

## What it proves

The POC exercises every structural claim in ADR-018 on real reconciled data:

- **Source-attributed claims, no collapse.** Both sources load as per-source
  `:Ruler` (E21) nodes with E13 claims carrying the full human-documentary spine
  (P140/P141/P177 + P14 scholar + P70i publication, page locators on P70i).
  Amenhotep III (Leprohon) and Amenophis III. (Beckerath) stay distinct.
- **Two-stage matcher.** A deterministic stage-1 matcher (`normalized_name_v1`)
  proposes 11 cross-source `same_entity_as` candidates with replayable CRMdig
  provenance (D10 run → D14 algorithm + D1 inputs/output). A single stage-2 LLM
  reviewer (Anthropic SDK, pinned provenance) emits verdict-E13s, **escalating to
  a human curator** when unsure.
- **Verdict supersession chain** with all three integrity constraints (unique
  successor, unique root, insert-time tip-only) — enforced both in Python and as
  **real Postgres constraints** (UNIQUE, partial UNIQUE, BEFORE-INSERT trigger).
- **Gated shortcut emission.** A matcher claim's direct `hapi:same_entity_as`
  edge materialises only when its verdict-chain tip is `hapi:verdict_approved`;
  human-documentary claims emit unconditionally.
- **Per-predicate resolution policy.** `hapi:display_name` resolves to the
  curator-decision-batch claim, else fails loud (no silent fallback).
- **CIDOC conformance, verifiable.** The strict-RDF adapter round-trips losslessly
  and emits genuine CIDOC/CRMdig triples (P190, P82a/P82b, E13 typing, the
  `hapi:same_entity_as` shortcut that an RDFS reasoner rewrites to `crmdig:L54`).

## Anti-lock-in architecture

The **substrate-neutral IR** (`ir.ClaimGraph`) is the single canonical artifact.
Every storage target is a swappable adapter, so the deferred storage decision
(ADR-019) stays genuinely open and backed by comparative evidence:

| Adapter | Status | Role |
|---|---|---|
| `adapters/rdf_adapter.py` | ✅ | strict CIDOC RDF + lossless round-trip (the neutral canonical form) |
| `adapters/relational_adapter.py` | ✅ | Postgres relational E13 + the three chain constraints as DB constraints |
| `adapters/neo4j_adapter.py` | ✅ | Neo4j property graph + constraint-narrowed Cypher queries |
| Apache AGE | ⏭️ skipped | best-effort; the `master` build fails against PG16 headers (pin the `PG16` release branch to revisit) |

## Headline numbers (full slice)

```
rulers=563  statements=1675  appellations=929  same_entity_shortcuts=11
nodes=3379  edges=10032
rdf_triples=33568   postgres={node:3379, edge:10032, verdict_chain:11}   neo4j={nodes:3379, rels:10032}
```

## Layout

```
graph/
  ir.py                  substrate-neutral ClaimGraph IR
  cidoc_spec.py          CRM 7.1.3 + CRMdig 5.0 + manifest catalogue (parsed from vendored RDFS)
  registry.py            predicate-registry loader + validator
  loader.py              reconciled.jsonl → E13 claims (Leprohon + Beckerath)
  matcher/
    stage1_deterministic.py   normalized_name_v1 (replayable, no LLM)
    stage2_reviewer.py        single LLM reviewer (SDK) + human escalation
  verdicts.py            verdict-E13s, supersession chain, gated shortcuts
  resolution.py          hapi:display_name resolution policy + curator loader
  adapters/              rdf / relational / neo4j
  poc.py                 end-to-end orchestration (build_poc_graph / export_all)
../predicate_registry.json
../curator_decisions/hapi_display_names_2026_05.json
```

## Running it

The environment (Postgres + Neo4j + rdflib) is provisioned by the SessionStart
hook (`.claude/hooks/session-start.sh`). Then:

```bash
cd pipeline
uv run pytest tests/test_authority_graph/        # all POC tests
uv run python -c "from pipeline.authority.graph.poc import build_poc_graph, export_all; print(export_all(build_poc_graph()))"
```

The relational / neo4j tests auto-skip when their services are down.

## Known boundaries (not yet done)

- **Live stage-2 reviewer needs `ANTHROPIC_API_KEY`.** The Claude Code OAuth proxy
  is not exposed to the SDK; without a key the live path raises loudly. The POC
  demonstrates verdict gating end-to-end via the human-escalation (curator)
  approval path instead.
- **RDF round-trip reconstructs from the hapi-data layer** (lossless); proving
  invertibility from the strict-CRM triples alone is deferred with the loader spec.
- **Apache AGE** is unbuilt (see table above).
- **Dagster wiring**: the loader/adapters are importable modules validated by
  pytest; wrapping them as Dagster assets is a production follow-up.
- **Scope**: Leprohon + Beckerath only; `tomb_owner` / `original_burial_in` /
  `cache_context_at` / `shares_tomb_with` predicates are registered but these two
  sources don't populate burial data.
