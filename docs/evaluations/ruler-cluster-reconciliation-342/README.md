# Ruler-cluster reconciliation (#342) — before/after measurement

**Date:** 2026-10-10 · **Issue:** [#342](https://github.com/pcomans/hapi/issues/342) ·
**Policy:** ADR-020, amendment 2026-10-10

## What changed

The claim graph (`web-claimgraph/data/claim-graph.json`) was rebuilt with the matcher
rules recorded in the ADR-020 amendment — era gate, Leprohon titulary stages as one
person, added epithets matched only as compounds, dynasty-scoped homonym and uniqueness
rules — and with DeepSeek V4.1 Flash (max reasoning effort, Vercel AI Gateway pinned to
DeepSeek's endpoint) as the reviewer. Every reviewer request and full response, reasoning
included, is in `web-claimgraph/data/claim-graph.reviewer-run.jsonl`.

| | Before (graph #337 registered) | After |
|---|---|---|
| Candidates | 2,141 | 2,301 |
| Approved links | 228 | 341 |
| Escalated | 1,348 | 1,049 |
| Clusters (multi-source) | 124 (124) | 164 (161) |
| Reviewer | GLM 5.2 (OpenRouter) | DeepSeek V4.1 Flash (Vercel → DeepSeek) |

Reviewer run: 1,087 calls, US$1.26 (gateway-reported), every response served by
`deepseek`, every response carrying reasoning text.

## Museum ruler mentions (#337 ledger, 148,871 mentions; 11,555 ruler mentions)

Measured by `scripts/measure_ruler_ambiguity.py` with the unchanged #337 resolver over the
byte-identical #337 mention ledger; aggregate output in `results/ruler-ambiguity.json`.

| Status | Before | After |
|---|---|---|
| resolved | 3,931 | 8,279 |
| ambiguous | 5,037 | 689 |
| unmatched | 346 | 346 |
| abstained (expression) | 2,241 | 2,241 |

Transitions: 4,348 ambiguous → resolved; 0 resolved → ambiguous; 0 resolved mentions
moved to a different king.

| King (by claim-graph record ids) | Artifacts ambiguous before | Resolved after |
|---|---|---|
| Amenhotep III | 2,750 | 2,750 |
| Akhenaten | 923 | 923 |
| Ramesses II | 520 | 520 |

## Safety checks on the rebuilt graph

- **No cluster joins two records of one source** that the source itself does not declare
  one person (the Pinudjem I ↔ Menkheperre false-merge class, ADR-020 finding 1).
- **Pilot first:** 16 reviewer calls on the three kings' candidates — 10 same-king pairs
  approved, 6 homonym traps (Dyn 17 Nebmaatre ×5 against Amenhotep III; Ramesses IV
  against Ramesses II) rejected. Pilot verdicts were reused in the full run only through
  the request-digest-checked cache.
- **Links approved before but not after (10)** are all escalated, none rejected:
  fragmentary Dyn 13–14 throne names (`Mer[///]re`, `Djed[...]re`, …) that fit several
  kings, and Smenkhkare / Neferneferuaten, a disputed identification. None affected a
  resolved museum mention.
- **Cross-dynasty links gained (2):** Osorkon IV (Dyn 22/23) and Merykare (Dyn 9/10) —
  the same king under the sources' differing dynasty numbering.

## Reproduce

The ledger is rebuilt from the private corpus archive exactly as in the #337 README
(`extract_mentions.py`), then:

```bash
git show 7a7db48:web-claimgraph/data/claim-graph.json > /tmp/before-claim-graph.json
pipeline/.venv/bin/python docs/evaluations/ruler-cluster-reconciliation-342/scripts/measure_ruler_ambiguity.py \
  --ledger <dir>/mentions.ndjson.gz --extraction-manifest <dir>/extraction-manifest.json \
  --before-graph /tmp/before-claim-graph.json \
  --after-graph web-claimgraph/data/claim-graph.json \
  --out docs/evaluations/ruler-cluster-reconciliation-342/results/ruler-ambiguity.json
```

These numbers describe the resolver's potential on the frozen ledger, not deployed
pipeline behaviour (museum records are not yet linked in production, #338). The #337 A/B
itself still runs against the graph it registered (`compare_arms.BASE_COMMIT`).
