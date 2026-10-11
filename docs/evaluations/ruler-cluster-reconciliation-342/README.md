# Ruler-cluster reconciliation (#342) — before/after measurement

**Dates:** 2026-10-10 (first run), 2026-10-11 (corrected run after review) ·
**Issue:** [#342](https://github.com/pcomans/hapi/issues/342) ·
**Policy:** ADR-020, amendment 2026-10-10

## What changed

The claim graph (`web-claimgraph/data/claim-graph.json`) was rebuilt with the matcher
rules recorded in the ADR-020 amendment — era gate, sources' own identity statements in
clusters, added epithets as their own claims and never alone as identity evidence,
fragmentary names never corroborating, dynasty-scoped homonym and uniqueness rules — with
DeepSeek V4.1 Flash as the reviewer (maximum reasoning effort requested; Vercel AI Gateway
pinned to DeepSeek's endpoint). Every reviewer request and full response, reasoning
included, is in `web-claimgraph/data/claim-graph.reviewer-run.jsonl`; the changed prompt
passed the Rule-14 leak audit (`prompt-audit-2026-10-11.md`) before the run.

| | Before (graph #337 registered) | After |
|---|---|---|
| Candidates | 2,141 | 2,208 |
| Approved links | 228 | 356 |
| Escalated | 1,348 | 972 |
| Clusters (multi-source) | 124 (124) | 162 (161) |
| Reviewer | GLM 5.2 (OpenRouter) | DeepSeek V4.1 Flash (Vercel → DeepSeek, one build) |

Reviewer run: 1,035 interactions, US$1.19 (gateway-reported). Every answered interaction
was served by `deepseek` with one serving build and carries reasoning text. Three
connection timeouts and eight answers cut off at `max_tokens` (reasoning that never
reached a verdict, all Dyn 13–23 records) were retried; one pair
(`leprohon-13.06` ↔ `ryholt-13.10`) never produced a verdict and is escalated. All attempts
are persisted. These properties are enforced by
`pipeline/tests/test_claimgraph_committed_artifacts.py`, which also replays the run offline
through the current matcher and requires the committed links, escalations and clusters
exactly — a matcher change committed without a rebuild fails CI. The tables below are
copied from `results/ruler-ambiguity.json`, which is the source of record.

## Museum ruler mentions (#337 ledger: 148,871 mentions, 11,555 of them ruler mentions)

Measured by `scripts/measure_ruler_ambiguity.py` with the unchanged #337 resolver over the
byte-identical #337 mention ledger; aggregate output in `results/ruler-ambiguity.json`,
pinned to the committed graph and script by test.

| Status | Before | After |
|---|---|---|
| resolved | 3,931 | 8,279 |
| ambiguous | 5,037 | 689 |
| unmatched | 346 | 346 |
| abstained (expression) | 2,241 | 2,241 |

Transitions: 4,348 ambiguous → resolved; 0 resolved → ambiguous; 0 resolved mentions now
resolve to a target sharing none of their former records.

| King (by claim-graph record ids) | Artifacts ambiguous before | Resolved after |
|---|---|---|
| Amenhotep III | 2,750 | 2,750 |
| Akhenaten | 923 | 923 |
| Ramesses II | 520 | 520 |

The other 154 newly resolved mentions, by the cluster they now resolve to: Tutankhamun 64,
Amenemhat III 28, Thutmose I 27, Amenemhat II 12, Aha 4, Hatshepsut 4, Ramesses IX 4,
Darius I 3, Pinudjem I 3, Qaa 2, Horemheb 1, Khendjer 1, Ramesses VIII 1.

## Safety checks

- **Every merge was reviewed.** `results/ruler-ambiguity.json` → `merged_clusters` lists all
  73 rebuilt clusters that join more than one earlier unit, with their members. Each is one
  king under different spellings, numberings or Greek forms (e.g. Nectanebo I =
  Nakhtnebef, Psammuthis = Pasherimut, Kitchen's Shoshenq VI = Leprohon's Sheshonq VII,
  Beckerath's Psusennes = the High Priest Psusennes III, Leprohon's Herakleopolitan
  Neferkare (III) and Wahkare Khety (V) = pharaoh.se's Neferkara III and Wahkara Khety II),
  or a source's own stage rows. Reviewed by `egyptologist-reviewer` (70, re-review of
  287e3f8) and in this session (the last 3: Pepi II and the two Herakleopolitans).
- **No cluster joins two records of one source** that the source does not itself declare
  one person (the Pinudjem I ↔ Menkheperre false-merge class) — test-enforced.
- **Every era-gate rejection is listed and was reviewed.** `results/era-rejected.json` lists
  all 448, test-pinned to the matcher, each tagged with the earlier graph's verdict for the
  pair: 176 escalated, 252 already rejected, 20 new, none approved. All are distinct kings;
  the per-group review is `results/era-rejected-review.md`. The first version of the gate
  wrongly rejected seven First Intermediate Period same-king pairs (von Beckerath's
  unplaced Dyn 8-era kings: Leprohon "Dynasty 8a", pharaoh.se Dynasty 10); review caught
  it and the Dyn 6–10 band fixes it.
- **Pepi II resolves.** His Neferkare is reused by several Dyn 8 kings; a shared Dyn 6
  clears it because Dyn 6–10 is contested only for the era gate (ADR-020 amendment, item 5).
- **Pilot first** (2026-10-10): 16 calls on the three kings — 10 same-king pairs approved,
  6 homonym traps rejected.
- **Contested identification kept, with its source.** Sanakht ↔ Nebka is newly linked; the
  link rests on Leprohon's own cited statement ("The identification of the Horus Sanakht
  with King Nebka is ascertained by a fragmentary sealing from Beit Khallaf"; Wilkinson
  2001, Baud 2007, Ryholt 2008). Representing scholarly dispute about such equations is tracked
  in [#346](https://github.com/pcomans/hapi/issues/346).

## Reproduce

The ledger is rebuilt from the private corpus archive exactly as in the #337 README
(`extract_mentions.py`), then:

```bash
git show 97f2e610974f0e89b9c03d409b230dff89edbb1f:web-claimgraph/data/claim-graph.json \
  > /tmp/before-claim-graph.json   # the graph #337 registered (compare_arms.BASE_COMMIT)
pipeline/.venv/bin/python docs/evaluations/ruler-cluster-reconciliation-342/scripts/measure_ruler_ambiguity.py \
  --ledger <dir>/mentions.ndjson.gz --extraction-manifest <dir>/extraction-manifest.json \
  --before-graph /tmp/before-claim-graph.json \
  --after-graph web-claimgraph/data/claim-graph.json \
  --out docs/evaluations/ruler-cluster-reconciliation-342/results/ruler-ambiguity.json
pipeline/.venv/bin/python docs/evaluations/ruler-cluster-reconciliation-342/scripts/list_era_rejected.py \
  --out docs/evaluations/ruler-cluster-reconciliation-342/results/era-rejected.json
```

These numbers describe the resolver's potential on the frozen ledger, not deployed
pipeline behaviour (museum records are not yet linked in production, #338). The #337 A/B
itself still runs against the graph it registered.
