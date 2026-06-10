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

## Constraint-narrowed matching (ADR-009 / ADR-018)

`matcher/constraint_narrowed.py` demonstrates the ADR-sanctioned way to lift
recall beyond exact name matching. ADR-009 forbids surface-string acceptance
(edit distance / token overlap) because those metrics are *anti-correlated* with
identity for Egyptian royal names: the regnal numeral discriminates identity but
is a tiny surface difference (Thutmose III vs IV = distance 1, different kings),
while the stem transliteration preserves identity but varies wildly (Thutmose /
Tuthmosis, Amenhotep / Amenophis). So this module never scores names — it
**constraint-narrows by structured graph facts (shared dynasty), then the LLM
picks the match from the narrowed set** (ADR-018 § Implications for matching).

**Dynasty 18 experiment** (the hardest case — every cross-source pair is
cross-language, so the exact matcher scores **0**):

| Approach | Matches on Dynasty 18 |
|---|---|
| exact normalized-name (stage-1) | 0 / 17 |
| constraint-narrow + LLM pick (17 API calls) | 17 / 17 |

Recovered the cross-language pairs (Amenhotep III == Amenophis III., Thutmose
I–IV == Tuthmosis I–IV, Tutankhamun == Tut-anch-amun, Horemheb == Har-em-hab)
AND the intra-source phase splits as many-to-one (both Leprohon *Amenhotep IV* +
*Akhenaten* rows → the single Beckerath *Amenophis IV. Ach-en-aten*). The
genuinely-contested Smenkhkare / Neferneferuaten identity surfaced honestly. The
deterministic narrowing + candidate emission is tested offline; the LLM pick is
injectable.

## 3-way clustering (Leprohon + Beckerath + Kitchen)

`loader.load_poc_graph_3way()` adds Kitchen (60 Third-Intermediate-Period kings)
as a third source; `poc.build_3way_graph()` runs the exact matcher across all
three source pairs and `poc.same_entity_clusters()` computes connected components
over the approved `hapi:same_entity_as` edges. Cross-source identity is *data*:
**Osorkon I** and **Osorkon II** form clean clusters spanning all three sources
(e.g. `{kitchen::22.02, leprohon::leprohon-22.02, beckerath::22.02}`). Only two
3-source clusters emerge from the *exact* matcher because cross-spelling pairs
(Kitchen "Takeloth" vs Leprohon "Takelot", "Shoshenq" vs Beckerath "Schoschenq")
need the constraint-narrowed LLM pick — adding those is the natural next step.

**LLM 3-way clustering** (constraint-narrowed pick for the Kitchen pairs over the
TIP dynasties 21–25, 106 calls; `run_3way_llm.py` — a *live* run whose
multi-hundred-KB result artifact is **not committed** in this slimmed POC PR, so
the count below is directional, not branch-verifiable; reproduce by running the
script, which persists the full per-pick interaction to `reviewer_outputs/`) lifts
the 3-source clusters from **2 → 27**, recovering deep variation the exact matcher
can't —
Shoshenq/Schoschenq/Sheshonq, Greek↔Egyptian (Bokchoris↔Bakenranef, Psusennes I↔
Pa-Seba-Kha-En-Niut I), and the Nubian Dyn-25 spellings (Piye/Pije/Piankhy,
Shabako/Schabako/Shabaka, Tantamani/Tanot-amun).

**Precision caveat (real):** transitive connected-components over pairwise LLM
picks can over-merge. One of the 27 clusters is a **false merge** — Pinudjem I and
Menkheperre (father and son, two distinct 21st-Dynasty Theban figures) were
conflated. The contradictory-merge guard for this is now **implemented**
(`matcher/constraints.py` + `poc.guarded_same_entity_clusters`, the ADR-020 §6
cannot-link guard) and verified on the Leprohon×Beckerath slice (precision → 1.00;
see `benchmark/README.md`); the 3-way (Kitchen) run above predates persisted edges,
so re-scoring it under the guard is a follow-up. Until then, treat 3-way clusters
as high-recall / unvalidated-precision and not yet authority data.

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
