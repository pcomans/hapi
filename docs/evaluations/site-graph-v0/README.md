# Site graph v0 evaluation contract

Status: `READY_SNAPSHOT_CONDITIONAL` for issue #327 contract validation;
`downstream_product_verdict` is `NOT_RUN`. This directory defines measurement
only. It does not acquire authority data, construct a graph, use Wikidata, or
change extraction, normalization, or matching.

The contract evaluates a bounded candidate against the verified 36,245-record
Met/Brooklyn/Harvard corpus at base commit
`97f2e610974f0e89b9c03d409b230dff89edbb1f`. Machine rules in
`preregistration.json` and the versioned files in `schemas/` control if prose and
code ever disagree.

## Inputs and provenance

`input-snapshot.json` pins every corpus, adapter, normalizer, and authority byte.
The canonical transport SHA-256 is
`b69fb207b5775f3fca3e3fe6c1dad13df91b0d90afdf196c17d869721be4ca24`;
museum counts are Met 27,969, Brooklyn 7,554, and Harvard 722.

The primary frozen input is the authorized external private archive named by
`HAPI_CORPUS_ARCHIVE`, plus the sidecar named by
`HAPI_CORPUS_ARCHIVE_SHA256`. `input-snapshot.json` pins archive size
13,788,812, SHA-256
`f4aabc2fc03b3ee0b5965bb9b27129e0ac482dae086c6124dd0d73d70276cc5b`,
the sidecar bytes, exact archive member inventory, internal `SHA256SUMS`, bundled
verifier output, and canonical counts. Release execution safely extracts only
that authenticated archive into a disposable directory. A pre-existing `/tmp`
extraction is never an authority input.

Verbatim handoff metadata lives in `corpus-provenance/`. It describes PostgreSQL
16.13 and Alembic `3a1c350217d9`, but the handoff does not record its export
command, producer Git revision, or Dagster run identifiers. Accordingly,
`upstream_production_lineage` is `UNAVAILABLE_DISCLOSED`, never `PASS`. Archive
acquisition integrity and derived baseline reproducibility can pass for this
immutable snapshot; the historical export cannot be regenerated from repository
history. Nothing here establishes that a repository commit or Dagster run
produced the corpus, that canonical mappers reproduced its raw bytes, that it is
the latest or complete production snapshot, or that the historical museum API
export can be regenerated.

## Exact record denominators

For museum `m`:

- `A_m`: all frozen canonical museum records.
- `X_m`: records where the frozen extractor emitted site text and sent it to the
  resolver. `X` deliberately means extracted site text and makes no independent
  evidence-quality judgment.
- `L_m`: records in `X_m` with at least one unique direct baseline site link.

| Museum | `A_m` | `X_m` | Outside `X_m` | `L_m` | `L_m/A_m` | `L_m/X_m` |
|---|---:|---:|---:|---:|---:|---:|
| Met | 27,969 | 27,889 | 80 | 15,018 | 53.6952% | 53.8492% |
| Brooklyn | 7,554 | 2,978 | 4,576 | 1,235 | 16.3490% | 41.4708% |
| Harvard | 722 | 540 | 182 | 267 | 36.9806% | 49.4444% |

The exact immutable classification is regenerated as private runtime file
`private-record-evidence.ndjson.gz` from the authorized corpus. It is not committed
or redistributed. `private-ledger-digests.json` and `preregistration.json` pin its
36,245-row canonical uncompressed SHA-256, deterministic gzip transport SHA-256,
and row Merkle root. These are linkability measurements, not accuracy, precision,
or recall.

## Connectivity and concentration

Connectivity is deduplicated direct artifact–target incidence. A pair target has
at least one eligible linked record on both museum sides; pair membership is
inclusive of all-three targets. The baseline has 47 Met–Brooklyn, 3 Met–Harvard,
4 Brooklyn–Harvard, 3 all-three, and 48 any-two-or-more site targets.

Every pair reports each museum side separately over both `A_m` and `X_m`.
Top-1/top-5/top-10 unique-record union ratios and incidence HHI are computed
independently by museum side with one shared implementation for baseline and
candidate. Pooled values are descriptive only. This matters: the old
Met–Brooklyn pooled top-1 value of 74.99196% hid Met-side values of 78.98833% and
79.32879% under the two previously inconsistent calculations.

Candidate safety compares every side with its own comparable baseline:

- each top-1/top-5/top-10 unique-record union ratio must be no more than its
  comparable baseline + 0.05;
- incidence HHI must be no more than its comparable baseline + 0.05.

The fixed five-percentage-point tolerance is relative to each side and is not fit
to the old pooled 0.75 value. Museum opportunity ceilings may differ; equal
improvement is never required.

## Scope and the narrower-node defense

`type-crosswalk.json` maps all actual hyphenated iDAI types and actual
Porter–Moss record representations to the candidate E55/type vocabulary. Broad
types take precedence. A node with any child in the complete pinned available
hierarchy is broad even if that child is omitted from the evaluated slice.

Baseline classification uses all 2,075 rows in pinned iDAI `raw.json`, not only the
filtered 1,000-target file. `baseline-node-scope.json` quantifies known
incompleteness: 43 filtered targets have children hidden by the 1,000-target
filter, totaling 299 omitted child edges. Two different parent-gap measures are
reported: 566 filtered targets have a parent absent from the filtered 1,000,
whereas 699 raw records have a parent reference absent from all 2,075 available
raw records. “Complete” means complete over these pinned available bytes, not over
the external gazetteer or world.

The resulting crosswalk-driven baseline classes are 200 broad, 799 specific
candidates, and 1 unclassified. A class is descriptive, never evidence that a
link is correct.
Broad/administrative or unclassified new links receive zero improvement credit.
A narrower candidate receives zero credit unless independent evidence and two
independent reviews support the direct identity and, for a reassignment, the exact
strict-refinement relation. Gained nodes count unique identity classes so
equivalent IDs cannot inflate improvement. Every equivalence claim itself requires
the same two structured independent reviews; unsupported equivalence cannot
preserve retention. Equal normalized authority locators auto-union; any other pair
of classes whose separation could inflate gains requires two reviewed positive
distinctness decisions. Broad-only partitions use the resulting identity-class
scope, so a candidate-specific alias equivalent to a frozen broad identity remains
broad. A reviewed equivalent direct-edge replacement is reported as unchanged.

## Intent-to-treat queue and measurable upper bounds

The generator creates private runtime files `private-opportunity-source.ndjson.gz`
and `private-opportunity-ledger.json`. They contain exact source and artifact
membership and are never committed. `planned-opportunity-summary.json` publishes
only the selection rule, counts, opaque rank IDs, expansion hashes, and numeric
ceilings; `private-ledger-digests.json` authenticates the private ledgers. Selection
uses baseline results only:

1. group unmatched/ambiguous site mentions by museum and exact ordered normalized
   keys;
2. rank by descending distinct artifact count, then museum and normalized key;
3. take each museum’s top 10 groups;
4. fill globally to exactly 50 groups;
5. freeze every selected group’s complete private artifact expansion and SHA-256;
6. materialize exact private pair+museum-side membership with category
   `no_baseline_pair_connection` or `broad_only_pair_connection`, plus the exact
   selecting opportunity ID and mention-binding hash for every artifact.

This selects 30 Met, 10 Brooklyn, and 10 Harvard signatures. Expanded
intent-to-treat records are 27,181 Met, 2,968 Brooklyn, and 539 Harvard. Research
failure, abstention, disagreement, unsupported scope, and broad/administrative
results stay in these denominators and earn zero credit.
Candidate credit requires the exact frozen opportunity/mention binding; another
mention on the same artifact cannot borrow that artifact’s ITT eligibility.

The fixed per-museum maximum credited affected-record upper bounds (new-link
eligible plus baseline broad-only reassignment eligible) are:

| Museum | ITT records | New-link ceiling | Reassignment ceiling | Total ceiling | Total / `A_m` | Total / `X_m` |
|---|---:|---:|---:|---:|---:|---:|
| Met | 27,181 | 12,526 | 8,278 | 20,804 | 74.3824% | 74.5957% |
| Brooklyn | 2,968 | 1,733 | 864 | 2,597 | 34.3791% | 87.2062% |
| Harvard | 539 | 272 | 5 | 277 | 38.3657% | 51.2963% |

These are maximum measurable bounds, not expected effects, accuracy claims, or
forecasts. Pair-side numeric ceilings and 10% thresholds are frozen in the public
summary and authenticated private membership. `top-unmatched-components.json`
reports opaque component IDs plus counts/statuses for each museum so ceilings are
interpretable without redistributing extracted text.

The queue size is a bounded research-workload heuristic: ten signatures protect
each museum before a frequency fill to fifty. The 10% affected floor is a
precommitted product decision relative to each side’s own opportunity ceiling, not
a power calculation or empirical truth; museums need not improve equally.

## Mutually exclusive comparison events

`scripts/compare_candidate.py` produces exactly one queue-record event with this
precedence: loss, strict-refinement reassignment, genuinely new link, additional
identity, uncredited change, unchanged.

A supported strict refinement is not an ordinary loss. The old broad direct edge
may be replaced; the authenticated source-derived hierarchy must preserve its
ancestor semantics. The report distinguishes replacement from retaining the old
direct edge. Any other uncovered baseline identity is a loss. New links require an
empty baseline set. Additional identities on linked records are never counted as
new linked records.

Candidate hierarchy, relation ledger, and at least one nonempty structured source
snapshot must be committed before the candidate run. The freeze manifest records
every SHA-256 and Git blob OID. Candidate source records supply raw source types,
not candidate E55 labels; the comparator maps them through the authenticated
crosswalk and verifies the exact source-record census plus inverse parent/child
closure. Production comparison additionally requires an Ed25519 run-start receipt
from a release-pinned trusted attestor, binding the exact release, freeze
commit/manifest/nonce, candidate, and invocation. Git ancestry and mutable
timestamps alone cannot establish ordering. `trusted-run-attestors.json` is
currently honestly `NOT_CONFIGURED`, so production candidate comparison fails
closed until a separately reviewed release migration pins a real trust root;
test-only keys never satisfy production binding. Existing baseline targets retain
frozen scope, while new-target scope/topology is derived from authenticated
snapshots, never self-attested by the result or inferred from slice leafness.

## Review census and abstention

Every credited changed link, strict refinement, and equivalence receives a census
review, not a sample gate. Each decision has exactly two distinct structured,
subject/outcome-bound artifacts from reviewer IDs and independence groups that are
both distinct. Each artifact carries structured independent non-originating-museum
citations. LLM review additionally records unique nonempty exact prompt, input, and
full raw response bytes; Git blob OIDs and SHA-256 values; model selector; exact
backend snapshot or an enumerated non-exposure sentinel; a full parameter object;
and a subject/decision/review-bound prompt-leakage audit using opaque shuffled
candidate IDs. The exact prompt and audit must be frozen in the ancestor commit
before invocation and cannot be reused across reviews or decisions. Disagreement or
uncertainty remains unresolved and receives no credit. This provisional census is
decision support, not gold truth.

A held-out sample may be added only as a descriptive audit using the exact
hash-ranked seed/algorithm in `preregistration.json`. It cannot gate credit or
support population precision/recall. Candidate ambiguity and closed-reason
abstentions are reported separately. Blocking ambiguity may rise by no more than
5/1000 of `X_m` in any museum. That allowance and the two-identity minimum are
precommitted product guardrails, not statistical significance thresholds.

## Ordered outcome

The comparator applies one ordered result:

1. `INVALID`: any schema, hash, exact-population, freeze-order, review-artifact, or
   other integrity failure; no product conclusion.
2. `REDESIGN`: integrity passes but there is a baseline loss, an ambiguity safety
   failure, or any top-1/top-5/top-10/HHI limit fails on any museum side.
3. `CONTINUE`: safety passes and at least one pair gains at least two credited
   distinct specific identities; each side affects at least
   `max(1, ceil(0.10 * fixed O_pair_side))` records; and broad-only share over
   `X_m` falls on at least one side without rising on the other.
4. `STOP`: integrity and safety pass but no pair satisfies every utility rule.

Raw link growth, narrowness alone, or equal-museum assumptions cannot pass.

## Immutable corrections

`correction-policy.json` defines the immutable primary policy. An actual correction
ledger is private and append-only; every nonempty record is schema-validated,
hash-chained, RFC3339-dated, cites evidence, names at least two reviewers, and
changes one exact site-mention resolution primitive over existing frozen targets.
Resolved mentions have exactly one target, ambiguous mentions at least two,
unmatched mentions none, and unique record targets cannot exceed resolved mentions.
A repeated primitive requires explicit supersession. The sensitivity generator
recomputes every dependent record field plus all headline, connectivity,
concentration, and pair aggregates. Its primary sensitivity estimand retains exact
frozen ITT membership and denominators; a separately labeled corrected-source
counterfactual reports additions, removals, and denominator changes without
rewriting the frozen ITT. Corrected rows/memberships remain private; only aggregate
metrics and hashes may be released. Primary bytes are never rewritten.

## Integrity, reproduction, and CI

`scripts/release_contract.py` is the immutable versioned required-file inventory outside
the generated manifest. `release-manifest.json` must match it exactly. Read-only
validation authenticates every byte before parsing any deliverable and rejects
missing, extra, or changed release files. It never repairs hashes or regenerates a
manifest. Cache exclusions are limited and documented; a required-file change is a
separately reviewed contract-version migration. Only the explicit release command
writes the manifest.

Create and authenticate two fresh deterministic reproductions in one operation:

```bash
uv run --project pipeline python docs/evaluations/site-graph-v0/scripts/corpus_archive.py \
  --repo-root /path/to/hapi \
  --corpus-archive "$HAPI_CORPUS_ARCHIVE" \
  --corpus-archive-sidecar "$HAPI_CORPUS_ARCHIVE_SHA256" \
  --attestation-output /tmp/hapi-corpus-archive-attestation.json
uv run --project pipeline python docs/evaluations/site-graph-v0/scripts/run_two_baselines.py \
  --repo-root /path/to/hapi \
  --corpus-archive "$HAPI_CORPUS_ARCHIVE" \
  --corpus-archive-sidecar "$HAPI_CORPUS_ARCHIVE_SHA256" \
  --output-root /tmp/hapi-327-final-reruns \
  --evidence docs/evaluations/site-graph-v0/baseline-rerun-evidence.json
```

The archive verifier refuses unsafe paths, links/devices, duplicates/overwrites,
unexpected members, corrupt sidecars, internal checksum mismatches, verifier
failures, and count mismatches. The runner consumes the same verified temporary
extraction and includes the exact deterministic archive attestation and its hash in
every run manifest. It preflights before output creation, builds in temporary sibling
directories, validates the exact output set, and publishes by atomic rename. The
comparator rejects the same resolved directory, duplicate run IDs, stale manifests,
actual-byte corruption, and missing/extra outputs. “Two” means sequential
deterministic reproduction with distinct directories/run IDs, not statistical or
operational independence.

Release sequence after copying deterministic derivatives from either authenticated
run:

```bash
uv run --project pipeline python docs/evaluations/site-graph-v0/scripts/generate_validation_report.py \
  --repo-root /path/to/hapi \
  --corpus-archive "$HAPI_CORPUS_ARCHIVE" \
  --corpus-archive-sidecar "$HAPI_CORPUS_ARCHIVE_SHA256" \
  --private-run /tmp/hapi-327-final-reruns/run-a
uv run --project pipeline python docs/evaluations/site-graph-v0/scripts/freeze_release.py \
  --repo-root /path/to/hapi --replace
uv run --project pipeline python docs/evaluations/site-graph-v0/scripts/validate_contract.py \
  --repo-root /path/to/hapi \
  --corpus-archive "$HAPI_CORPUS_ARCHIVE" \
  --corpus-archive-sidecar "$HAPI_CORPUS_ARCHIVE_SHA256" \
  --private-run /tmp/hapi-327-final-reruns/run-a
uv run --project pipeline pytest -q pipeline/tests/test_site_graph_v0_*.py
```

The final two-run and test results are recorded in `validation-report.json` and the
implementation handoff. Logic-only adversarial unit inputs test comparator behavior;
they make no corpus claim. Corpus headline assertions are recomputed from
authenticated private runtime ledgers and pinned source bytes; no fixture supports
a corpus conclusion.

## Review provenance

`reviews/round-1/` and `reviews/round-2/` preserve each original prompt and raw
output verbatim alongside CLI/model/tool metadata and per-finding dispositions.
Both historical reviews requested changes on earlier SHAs. Implementer
dispositions document repairs; they are not reviewer approval. Exact-HEAD external
review occurs after the commit and is reported outside that commit, so checked-in
self-validation never claims a final reviewer `PASS`.
Backend details not exposed by the Claude CLI are explicitly recorded as not
exposed rather than inferred. Reviewed SHAs are preserved in local implementation
history; the final public branch is constructed from the base with the final tree so
removed private derivatives never enter public Git history.

## Acceptance map

| #327 requirement | Executable evidence |
|---|---|
| Exact snapshots and immutable classification | `input-snapshot.json`, private-ledger canonical/Merkle hashes, exact static release contract |
| Exact formulas and museum denominators | `preregistration.json`, recomputation in `validate_contract.py` and CI |
| Pair/all-three and per-side concentration | `baseline-metrics.json`; side-specific top-k/HHI recomputation and gates |
| Result-blind planned maximum | private regenerated source/membership authenticated by public aggregate hashes and numeric museum/pair ceilings |
| Narrower-node defense | one type crosswalk, source-derived frozen hierarchy context, reviewed equivalence union-find, adversarial tests |
| New link versus reassignment | mutually exclusive comparator events; replacement/ancestor semantics report |
| Ambiguity and abstention | closed statuses/reasons, fixed denominators, museum safety gates |
| Independent review safety | structured subject-bound artifact/hash/model/leakage-audit validation and census credit logic |
| Immutable corrections | private primitive append-only correction schema and full sensitivity recomputation/test |
| Precommitted continue/stop/redesign | ordered executable comparator outcome and adversarial tests |
| Two deterministic reproductions | exact-output/rehash/provenance evidence in `baseline-rerun-evidence.json` |
| Corpus provenance limits | verbatim handoff metadata/verifier and explicit missing export/run provenance |

## Limitations

- The pinned available iDAI hierarchy is not a global closed graph; exact known gaps
  are reported and candidate work must version any stronger source snapshot.
- No candidate research or candidate graph exists in #327, so the comparator schemas
  are preregistered and tested on logic-only adversarial cases, not presented as a
  candidate result.
- No expected effect, population precision, or population recall is inferred from
  the provisional silver process or the optimistic measurable ceilings.
- Changing corpus, extractor, matcher, normalization, authority snapshots,
  opportunities, formulas, or denominators creates a new evaluation version.
