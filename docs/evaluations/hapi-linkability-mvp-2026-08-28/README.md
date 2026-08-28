# HAPI current-authority linkability MVP

**Result:** the current authority layer is **not sufficiently linkable for a general, all-three-museum production enrichment**. A narrow, shadow-mode implementation for exact site aliases and Met Porter–Moss tomb codes is supportable, but ruler coverage outside the Met is nearly absent, the present site representation is only a filtered iDAI source table rather than a canonical graph, and temple and excavation entity types do not have current canonical targets. Those missing authority types are hard blockers for conclusions about comprehensive temple or excavation linkability.

This is an archived evaluation over the verified real corpus, not fixture behavior. The evaluation was originally run in `/tmp`; this directory preserves its report, deterministic scripts, aggregate outputs, and frozen provisional review. Web review is labelled **PROVISIONAL SILVER** throughout; it is neither gold truth nor human validation.

## Scope and reproducibility

- Corpus: `/tmp/hapi-corpus-2026-08-27/data/artifacts.ndjson.gz`, SHA-256 `b69fb207b5775f3fca3e3fe6c1dad13df91b0d90afdf196c17d869721be4ca24`.
- Evaluation population: all 36,245 canonical records, with each joined back to its underlying raw museum payload.
- Canonical counts: Met 27,969; Brooklyn 7,554; Harvard 722.
- Raw counts: Met 27,969; Brooklyn 8,832; Harvard 722. The 1,278 Brooklyn raw-only rows are inventoried but excluded from the canonical-record denominator.
- Every canonical row found its museum/source-id raw payload. No fixture, synthetic row, proxy corpus, or web-adjudicated alias entered the resolver.
- Deterministic scripts are in `scripts/`; `validation_report.json` records a clean rerun and invariant checks, and `SHA256SUMS` covers the deliverable.

Run from any directory with Python 3. `HAPI_ROOT`, `HAPI_CORPUS`, and `HAPI_EVAL_OUT` may override the defaults shown here:

```bash
python /tmp/hapi-linkability-mvp/scripts/inventory_inputs.py
python /tmp/hapi-linkability-mvp/scripts/run_linkability.py
python /tmp/hapi-linkability-mvp/scripts/freeze_review_sample.py
python /tmp/hapi-linkability-mvp/scripts/adjudicate_review.py
python /tmp/hapi-linkability-mvp/scripts/summarize_evaluation.py
python /tmp/hapi-linkability-mvp/scripts/validate_outputs.py
```

The review sample was frozen before web adjudication with seed `hapi-linkability-mvp-review-v1-2026-08-28`; rerunning the sampler reproduces the same frozen file rather than drawing a new sample.

## What authority targets actually exist

| Entity type | Current committed representation used | Target units | Important limitation |
|---|---:|---:|---|
| Ruler | `web-claimgraph/data/claim-graph.json`: approved cluster when present, otherwise singleton scholarly-source node | 974 (124 clusters plus 850 singletons) | 1,159 source nodes are only partly reconciled; duplicate identity units make common strings ambiguous |
| Site | `pipeline/.../idai-gazetteer/reconciled.jsonl` | 1,000 iDAI rows, 3,723 display/alias labels | No consolidated site graph or curated `sites.json`; 566 parent IDs lie outside the filtered file |
| Tomb/monument | Separate Porter–Moss Theban and Memphis registers | 1,357 rows (484 + 873) | No unified tomb/site graph; code and registered-alias scope only |
| Temple | None | 0 | A comprehensive temple-node result is hard blocked; a few PM rows cannot substitute for a typed temple authority |
| Excavation | None | 0 | Canonical excavation resolution is hard blocked; literal excavation strings were retained as evidence, never fabricated as nodes |

The complete audit, source paths, Git-tracked status, checksums, type counts, label collisions, and parent coverage are in `authority_inventory.json`. The adapter deliberately preserves iDAI and Porter–Moss identifiers; it does not invent canonical merges or hierarchy edges.

## Museum evidence audit

Canonical authority fields are sparse: the Met alone has `ruler_display_name` (11,256 records) and excavation literals (16,403); `origin_site_raw` occurs for 27,889 Met, 2,978 Brooklyn, and 540 Harvard records; every canonical ruler/site/tomb authority-ID field is null. That does **not** mean Brooklyn or Harvard lack evidence. The raw-payload audit found and processed the following explicit fields:

| Museum | Ruler evidence actually extracted | Site evidence actually extracted | Tomb / excavation evidence |
|---|---|---|---|
| Met | structured `reign` (11,256 mentions) and explicit royal title cues (232) | structured `country`, `region`, `subregion`, `locale`, `locus` (110,810 mentions total) | 4,841 explicit tomb-code mentions; 16,403 structured excavation literals |
| Brooklyn | explicit ruler cues in `title` (50) and `inscribed` (8) | `geographicalLocations[*].name` with museum role retained (5,095) | 22 explicit tomb codes in structured locations |
| Harvard | explicit ruler cues in `title`, `labeltext`, `commentary`, and `dated` (9 total) | `places[*].displayname` with museum role retained (1,702) | no extracted explicit tomb or excavation value |

`corpus_inventory.json` reports non-empty and domain-cue counts for every candidate raw text/structured field, even where the conservative extractor emitted no mention. `field_provenance_metrics.json` reports every observed museum/entity/field cell. Every row in `mentions.ndjson.gz` retains the raw field value, field path, source layer, museum evidence role, exact `[span_start, span_end)` offsets, extraction method, source URL, and resolution trace.

## Disposable adapter and denominators

The resolver is intentionally conservative and independent of the web review:

1. Extract explicit structured values and authority-bounded text after royal cues. Parse only obvious typed reign qualifiers, uncertainty, ranges/alternatives, and explicit tomb codes.
2. Try case-folded raw equality against committed labels/aliases.
3. If exact equality has no candidate, try the committed ruler normalizer without its lossy skeleton, or deterministic Unicode/spacing/punctuation normalization for places and tomb codes.
4. One current target means `resolved`; zero means `unmatched`; more than one means `ambiguous`. Uncertain, temporal, and multi-entity expressions abstain. A joint reign or range is never collapsed to one ruler.
5. Deduplicate artifact–authority links. Web findings never modify extraction, normalization, aliases, targets, or links.

The `mentions_with_resolution_attempt_denominator` excludes statuses for which a unique identity was deliberately not attempted (`uncertain_identity`, `multi_or_range`, `temporal_context`, `unparsed_structured_value`, and `authority_unavailable`). Record-link rates always use all canonical records for that museum as denominator.

## Linkability now

| Museum / entity | Canonical records | Records with extracted evidence | Mentions attempted | Unique mentions | Ambiguous | Unmatched | Artifacts linked | Artifact link rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Brooklyn ruler | 7,554 | 53 | 56 | 6 | 18 | 32 | 6 | 0.08% |
| Brooklyn site | 7,554 | 2,978 | 5,095 | 1,293 | 32 | 3,770 | 1,235 | 16.35% |
| Brooklyn tomb | 7,554 | 22 | 22 | 0 | 0 | 22 | 0 | 0.00% |
| Harvard ruler | 722 | 5 | 8 | 5 | 1 | 2 | 3 | 0.42% |
| Harvard site | 722 | 540 | 1,702 | 267 | 2 | 1,433 | 267 | 36.98% |
| Harvard tomb | 722 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00% |
| Met ruler | 27,969 | 11,284 | 9,284 | 3,935 | 5,022 | 327 | 3,879 | 13.87% |
| Met site | 27,969 | 27,889 | 110,810 | 35,272 | 168 | 75,370 | 15,018 | 53.70% |
| Met tomb | 27,969 | 4,780 | 4,841 | 3,227 | 0 | 1,614 | 3,199 | 11.44% |
| Met excavation | 27,969 | 16,403 | 0 | 0 | 0 | 0 | 0 | 0.00% |

For Met excavation, all 16,403 evidence mentions are explicitly `authority_unavailable`, so the attempted denominator is zero. Across entity types, 17,063 of 36,245 artifacts (47.08%) link at least once: Met 15,556/27,969 (55.62%), Brooklyn 1,237/7,554 (16.38%), Harvard 270/722 (37.40%). These are deterministic link rates, not accuracy estimates.

The full status accounting, including Met ruler `multi_or_range` (810), `temporal_context` (53), `uncertain_identity` (192), and `unparsed_structured_value` (1,149), is in `linkability_metrics.json`.

## Cross-museum shared-node signal

The product signal is node incidence, not an artifact all-pairs table. The adapter emitted 43,930 deduplicated artifact–node links to 280 current authority nodes. Fifty-six nodes receive artifacts from at least two museums: 48 sites and 8 rulers. Those shared nodes touch 15,595 distinct artifacts (Met 14,431; Brooklyn 1,154; Harvard 10), meaning those artifacts would have at least one cross-museum discovery route through a shared current node. This does not claim that the routes are new relative to any existing product feature.

Only three nodes receive artifacts from all three museums. Shared-node museum combinations are: Brooklyn+Met 49, Harvard+Met 3, Brooklyn+Harvard 1, and all three 3. The entity-specific artifact counts are 15,551 site-linked and 464 ruler-linked; an artifact may occur in both entity totals. No tomb node is shared across museums.

| Highest-volume shared node | Museums | Artifacts |
|---|---:|---:|
| iDAI Thebes (`idai:2042921`) | Brooklyn, Met | 11,656 |
| iDAI Upper Egypt (`idai:2379505`) | Brooklyn, Met | 11,434 |
| iDAI Deir el-Bahri (`idai:2110510`) | Brooklyn, Met | 3,050 |
| iDAI Malkata (`idai:2042871`) | Brooklyn, Met | 2,482 |
| iDAI Asasif (`idai:2751494`) | Brooklyn, Met | 1,531 |
| iDAI Amarna (`idai:2296218`) | Brooklyn, Met | 1,066 |
| iDAI Saqqara (`idai:2042907`) | all three | 780 |

This apparent connectivity is strongly concentrated and often broad: Thebes alone touches 11,656/15,595 (74.74%) of all discoverable artifacts; the top ten shared nodes jointly touch 14,031 (89.97%). Nested place fields can link one artifact to several geographic levels. `authority_node_connectivity.json` gives every linked node's museum/artifact counts; `connectivity_detail.json` gives shared combinations, concentration, and the top 50 nodes.

## Minimal ablation: exact labels versus current normalization

| Entity | Attempted mentions | Exact-only unique mentions | Current unique mentions | Incremental unique mentions | Incremental linked artifacts |
|---|---:|---:|---:|---:|---:|
| Ruler | 9,348 | 3,903 | 3,946 | +43 | +39 |
| Site | 117,607 | 34,961 | 36,832 | +1,871 | +212 |
| Tomb/monument | 4,863 | 7 | 3,227 | +3,220 | +3,192 |

The large tomb increment is almost entirely the intended normalization of explicit catalogue-code syntax and spacing. For ruler and site names, deterministic normalization adds little compared with the unresolved volume; the missing capability is not chiefly more punctuation folding.

## Dominant gaps, weighted by artifacts

- **Absent current targets:** `Egypt` is unmatched for 26,573 Met artifacts, 2,881 Brooklyn artifacts, and 510 Harvard artifacts because the live iDAI Egypt root is outside the committed filtered target file. Excavation authority is absent for 16,403 Met records. Temple authority is absent; examples such as `Temple of Hatshepsut` (570 artifacts) remain site-string evidence, not resolved temple nodes.
- **Site scope and granularity:** `Memphite Region` (4,634), `Lisht North` (3,006), `Cemetery` (1,927), `Palace of Amenhotep III` (1,518), and `Southern Asasif` (1,359) are high-volume unmatched Met values. Harvard's broad `Africa` occurs on 534 artifacts.
- **Incomplete ruler reconciliation:** common unambiguous Met strings are ambiguous across unreconciled current units: `Amenhotep III` (2,750 artifacts), `Akhenaten` (917), and `Ramesses II` (518).
- **Typed expression parsing:** `Joint reign of Hatshepsut and Thutmose III` occurs on 1,020 Met artifacts and needs two emitted ruler assertions, not one collapsed target. Qualifiers and record context also matter.
- **Tomb-register scope:** Met Porter–Moss codes perform well within scope, but Brooklyn's 22 explicit tomb codes resolve to none; local MMA tomb/locus strings are outside the current registers or alias granularity.

`top_gaps.json` contains the top 500 museum/entity/status/signature gaps with artifact frequencies, field provenance, and an example object URL.

## Frozen provisional SILVER review

The deterministic 46-case sample was frozen before web work. It covers Met 22, Brooklyn 13, Harvard 11; rulers 23, sites 16, tombs 5, excavations 2; and resolved, ambiguous, unmatched, uncertainty, range, unparsed, and authority-unavailable statuses. Within every observed museum/entity/status cell it selects the highest-frequency signature, then a deterministic minimum-frequency signature where the design permits. This deliberate stratification is useful for failure discovery but is not population representative.

All 46 cases were provisionally adjudicated using the direct museum record plus an institutional authority/catalogue or scholarly reference when one was available. Examples include the [iDAI Gazetteer](https://gazetteer.dainst.org/), the Griffith Institute's [Porter–Moss I.1](https://www.griffith.ox.ac.uk/topbib/pdf/pm1-1.pdf) and [I.2](https://www.griffith.ox.ac.uk/topbib/pdf/pm1-2.pdf), and direct [Met](https://www.metmuseum.org/art/collection/search/545948) and [Brooklyn](https://www.brooklynmuseum.org/objects/3317) object pages. Current pharaoh.se graph-source pages are explicitly marked self-published/corroborative, never treated as sole gold authority. Harvard object pages blocked automated retrieval; their direct institutional URLs and values verified in the supplied raw Harvard API payload are retained, and the limitation is explicit rather than replaced with a proxy.

Resolution judgments are 12 supported, 2 false links, 10 underresolved, 19 correct abstentions, and 3 not applicable. Among the 14 deliberately sampled resolved cases, 12 were supported and 2 false (85.7% descriptive support, 14.3% false). **This is not estimated precision** because of the stratified selection. Recall is not reported: the review frame starts from extracted mentions and therefore has no defensible negative/no-mention denominator. Span review found 43 supported, 2 minor punctuation boundaries, and 1 unsupported overlapping boundary.

The two sampled false links are concrete warnings:

- Brooklyn `Maatkare` was linked to Hatshepsut, but the object denotes the Dynasty 21 princess Maatkare, daughter of Painedjem I: a homonym plus entity-typing failure. The direct institutional comparison is recorded in `review_adjudications.json`.
- A Harvard comparator sentence mentioning Amasis was incorrectly treated as an artifact–ruler assertion: a reference-only relation failure.

A post-hoc sensitivity removes only those two sampled links; it is **not** a corrected population estimate. Shared nodes fall from 56 to 55 and discoverable artifacts from 15,595 to 15,577. The lost shared ruler node is `cluster-beckerath-26.05` (`Ahmose III`), which had become cross-museum only through the false Harvard Amasis link. All unreviewed links remain untouched.

`review_sample.json`, `review_sample_manifest.json`, `review_adjudications.json`, `review_metrics.json`, and `web_search_log.json` preserve the selection, citations, evidence notes, abstentions, source-access caveats, and descriptive accounting.

## Output map

| Output | Contents |
|---|---|
| `corpus_inventory.json` | canonical/raw counts, field coverage, raw-field/cue audit, input checksum |
| `authority_inventory.json` | actual committed target representations, counts, checksums, absent types |
| `adapter_catalog_summary.json` | resolver keys, targets, and collision counts |
| `mentions.ndjson.gz` | all 150,428 extracted mentions with field/span and resolver provenance |
| `artifact_authority_links.ndjson.gz` | all 43,930 deduplicated artifact–node links |
| `linkability_metrics.json` | per museum/entity evidence, mention statuses, exact denominators, ablation |
| `artifact_link_coverage.json` | record-level links and rates by museum/entity |
| `field_provenance_metrics.json` | actual extracted field cells and outcomes |
| `authority_node_connectivity.json` | node-level museum and artifact incidence |
| `connectivity_metrics.json`, `connectivity_detail.json` | shared-node totals, museum combinations, concentration |
| `top_gaps.json` | top 500 unresolved/ambiguous/unavailable signatures weighted by artifacts |
| `review_sample.*`, `review_sample_manifest.json` | frozen stratified provisional SILVER sample |
| `review_adjudications.*`, `review_metrics.json`, `web_search_log.json` | cited provisional SILVER decisions and limitations |
| `silver_false_link_sensitivity.json` | explicitly post-hoc, sample-only sensitivity |
| `scripts/` | full deterministic inventory, adapter, sample, review, summary, validation code |
| `validation_report.json`, `SHA256SUMS` | invariant/rerun checks and deliverable hashes |

### Repository archive boundary

The two bulk, record-level derivatives (`mentions.ndjson.gz` and `artifact_authority_links.ndjson.gz`) are intentionally not committed. They reproduce substantial information from museum bulk data whose redistribution terms differ by museum. They can be regenerated from the separately retained corpus with the scripts above. All aggregate metrics, weighted gaps, the frozen 46-case sample, adjudications, provenance logs, and validation evidence are committed here.

## Decision table

| Decision gate | Evidence | Decision / next build |
|---|---|---|
| Is current authority sufficiently linkable across all three museums? | Ruler-linked artifacts: Met 3,879, Brooklyn 6, Harvard 3; sites link only 16.35% of Brooklyn and 36.98% of Harvard; no shared tomb node; temple/excavation targets absent | **No** for comprehensive production enrichment |
| Can a bounded capability ship now? | Exact/current site matches yield 15,551 artifacts on cross-museum site nodes; Met tomb codes link 3,199 artifacts; sampled resolved site/tomb cases were supported but not population-estimated | Build only a **shadow-mode, provenance-visible exact site + Met PM-code prototype**, with ambiguity/abstention preserved |
| Dominant ruler blocker | 5,022 ambiguous Met mentions; high-frequency duplicates include Amenhotep III 2,750, Akhenaten 917, Ramesses II 518; B/H evidence extraction is sparse and sampled text produced entity/relation false links | Reconcile ruler clusters first, then add museum-context entity typing and relation-aware extraction |
| Dominant site blocker | No site graph; 566/1,000 iDAI parents outside the file; `Egypt` alone unmatched on 29,964 artifacts across museums; broad nodes dominate shared connectivity | Build a versioned canonical site graph with complete roots/hierarchy, typed aliases, museum field-role mappings, and local-place crosswalks |
| Temple/excavation blocker | No dedicated canonical target type; 16,403 Met excavation records cannot be resolved | **Hard blocker:** model and curate these entity types before evaluating or shipping them; do not substitute literal strings or PM proxies |
| Production-enrichment gate | Review is provisional SILVER and stratified; no defensible recall denominator; two sampled ruler false links materially affect one shared node | Require a blinded human-labelled evaluation over records including no-mention negatives after the authority/extractor builds above |
