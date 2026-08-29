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
preserve retention. Exact authority-locator string equality auto-unions (v0 does
not perform additional locator normalization); any other pair
of classes whose separation could inflate gains requires two reviewed positive
distinctness decisions. The complete gained-root census is derived before pair-side
credit and checks every gained root against every other gained root and the full
relevant baseline universe; crossed additions and one-sided specific identities
cannot evade it. Broad-only partitions use the resulting identity-class
scope, so a candidate-specific alias equivalent to a frozen broad identity remains
broad. A reviewed equivalent direct-edge replacement is reported as unchanged.

## Intent-to-treat queue and measurable upper bounds

The generator creates private runtime files `private-opportunity-source.ndjson.gz`
and `private-opportunity-ledger.json`. They contain exact source and artifact
membership and are never committed. `planned-opportunity-summary.json` publishes
only the selection rule, stable rank IDs, aggregate counts, and numeric ceilings;
`private-ledger-digests.json` authenticates the complete private ledgers. The v0
release contains no bulk artifact-ID expansion and no raw mention rows. Existing
aggregate and sampled repository data can correlate labels with ranks or counts,
so the rank IDs and counts are not claimed opaque or unlinkable. Selection uses
baseline results only:

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
The candidate result must exhaustively emit exactly one closed disposition for
every required binding (`linked`, `ambiguous`, `abstained`, `unmatched`,
`unresolved`, or `research_failure`). Omitted, duplicated, or substituted bindings
make the run `INVALID`; ambiguity and abstention counts are computed from this
binding-level census rather than a single aggregate artifact status.
Each record separately declares its complete final supported direct-link set and
the exact complementary set of removed frozen baseline links. Selected outcomes
can justify additions and update only their exact selected mentions; unrelated
resolved links and unselected mention statuses carry forward. A disputed or
unsupported attempted link must be reported as an uncredited claim under an
`unresolved` outcome and cannot suppress ambiguity.
Candidate dispositions do not themselves change mention state. Any change from a
frozen selected status requires a separate subject-bound, two-review
`mention_status_resolution` decision over the exact mention IDs, prior statuses,
and proposed status. Abstention, unresolved work, and research failure preserve
the frozen status.

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
reports component identifiers plus counts/statuses for each museum so ceilings are
interpretable without redistributing extracted text; those identifiers are not
claimed opaque or unlinkable.

The queue size is a bounded research-workload heuristic: ten signatures protect
each museum before a frequency fill to fifty. The 10% affected floor is a
precommitted product decision relative to each side’s own opportunity ceiling, not
a power calculation or empirical truth; museums need not improve equally.

## Mutually exclusive comparison events

`scripts/compare_candidate.py` produces exactly one queue-record event with this
precedence: loss, strict-refinement reassignment, genuinely new link, additional
identity, uncredited change, unchanged.
Retention/loss and post-candidate linkability, pair connectivity, all-three,
any-two-or-more, broad-only, top-k, and HHI metrics all consume the complete final
record-level identity-class link sets. Equivalent alias replacements are unchanged
and never satisfy an affected-record floor. Retention compares identity roots after
authenticated locator/equivalence union: removing a duplicate raw direct edge while
retaining the same identity is unchanged, and raw edge removals remain separately
visible in the report.

A supported strict refinement is not an ordinary loss. The old broad direct edge
may be replaced; the authenticated source-derived hierarchy must preserve its
ancestor semantics. The report distinguishes replacement from retaining the old
direct edge. Any other uncovered baseline identity is a loss. New links require an
empty baseline set. Additional identities on linked records are never counted as
new linked records.

Candidate hierarchy, relation ledger, and every complete authority source export
triplet (exact export bytes, trusted-exporter attestation, and detached signature)
must be committed before the candidate run. The freeze manifest records every
SHA-256 and Git blob OID. Candidate source records supply raw source types, not
candidate E55 labels; they also supply the exact preferred label and sorted alias
census used by the leakage guard. The comparator maps raw types through the
authenticated crosswalk and verifies the exact source-record census plus inverse
parent/child closure.
`trusted-source-exporters.json` is release-authenticated and candidate-authored
completeness claims have no authority without one of its signatures.

Production comparison additionally requires two Ed25519 statements from the same
release-pinned trusted attestor: a start receipt binding the exact release, freeze,
nonce, candidate, invocation, CPython 3.12.13 runtime, and dependency lock; and a
completion attestation binding that receipt to the exact result commit, candidate
output, review ledger, source exports, and result-manifest path/hash/blob. Git
ancestry and mutable timestamps alone cannot establish ordering, and an unsigned
result is never comparable. `trusted-run-attestors.json` and
`trusted-source-exporters.json` are currently honestly `NOT_CONFIGURED`, so
production candidate comparison fails closed until a separately reviewed release
migration pins genuine trust roots; test-only keys never satisfy production
binding. Existing baseline targets retain frozen scope, while new-target
scope/topology is derived from authenticated exports, never self-attested by the
result or inferred from slice leafness.

## Review census and abstention

Every credited changed link, strict refinement, and equivalence receives a census
review, not a sample gate. Each decision has exactly two distinct structured,
subject/outcome-bound, signed artifacts from reviewer IDs and independence groups
that are both distinct and registered in the release-authenticated
`trusted-reviewers.json`. Human review has the same signature and provenance gate;
an arbitrary reviewer string cannot bypass it. Each artifact carries structured
independent non-originating-museum citations bound to exact authenticated authority
export bytes. Collectively, a review's cited source records must cover every target
in its signed subject; an unrelated export row cannot support a link, equivalence,
distinctness, or strict-refinement decision. LLM review additionally records unique
nonempty exact prompt, input,
and full raw response bytes; the raw response must be canonical JSON with exactly
`assessment` and `reasoning`, and both must exactly equal the signed wrapper values.
Git blob OIDs and SHA-256 values; model selector;
exact backend snapshot or an enumerated non-exposure sentinel; a full parameter
object; and separate registered auditors' detached signatures over pre-invocation,
subject/decision/review-bound deterministic and human semantic prompt audits.
Prompt and input are canonical JSON envelopes. The task/instructions are an
immutable release-owned hash-bound template, never caller-authored. It selects one
release-defined decision-kind task and claim, binds the exact subject only by its
canonical hash, and admits no candidate-authored task, instruction, example, or hint.
Input items use
hash-derived opaque labels only in schema-defined option slots and a deterministic
non-identity SHA-256-ranked presentation order. The seed derives from the canonical
decision key, kind, and subject rather than a caller-chosen invocation value. The
signed audit retains the hidden canonical payload-hash order, seed, and exact
presented-order hashes so the comparator can reproduce the shuffle without revealing
source order to the model. Deterministic
guards scan the exact request for authenticated preferred labels and aliases, answer
names, IDs, locators, and verifier-owned decision/order proxies such as `yes`,
`approve`, or `first item`. Prompt, input, response, audit, signature, or invocation
reuse fails closed. Disagreement
or uncertainty remains unresolved and receives no credit. This provisional census
is decision support, not gold truth. The additional signed semantic audit reduces
known leakage risk but does not prove semantic perfection. The reviewer registry is currently
`NOT_CONFIGURED`, so no production decision can receive review credit.

A held-out sample may be added only as a descriptive audit using the exact
hash-ranked seed/algorithm in `preregistration.json`. It cannot gate credit or
support population precision/recall. Candidate ambiguity and closed-reason
abstentions are reported separately. The safety numerator is newly blocking records
(baseline nonblocking, candidate blocking), not net prevalence change; resolved
blockers cannot offset new regressions. Newly blocking records may be no more than
5/1000 of `X_m` in any museum. Authenticated resolved blockers and net change are
descriptive outputs. That allowance and the two-identity minimum are
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
hash-chained, RFC3339-dated, and changes one exact site-mention resolution primitive
over existing frozen targets. The release policy must pin an exact canonical
registration artifact from a strict ancestor Git commit. That artifact binds the
genuine genesis, exact prior ledger head, and both private baseline hashes; the
verified release-policy activation commit must strictly follow registration and
strictly precede every review decision, and the proposed ledger must follow those
decisions while preserving its prior canonical-entry prefix. This is equality of
canonical JSON decision entries, not preservation of original transport bytes. Each decision is bound to
the chain ID and both private baseline hashes, cites exact content-addressed source
bytes from a strict ancestor of the decision commit, and has signed support from
exactly two registered human reviewers
with distinct identities, credentials, and independence groups. Arbitrary reviewer
strings, same-commit/post-hoc evidence, invented citations, caller-created
sequence-one roots, and zero commit IDs fail closed. The current policy is
deliberately `NOT_CONFIGURED`, so no production
correction sensitivity can run; the primary preregistered analysis has zero
corrections.
Resolved mentions have exactly one target, ambiguous mentions at least two,
unmatched mentions none, and unique record targets cannot exceed resolved mentions.
A repeated primitive requires explicit supersession. The sensitivity generator
recomputes every dependent record field plus all headline, connectivity,
concentration, and pair aggregates. Its primary sensitivity estimand retains exact
frozen ITT membership and denominators; a separately labeled corrected-source
counterfactual reports additions, removals, and denominator changes without
rewriting the frozen ITT. Corrected rows/memberships remain private; only aggregate
metrics and hashes may be released. Primary bytes are never rewritten.

## Integrity and reproduction

`scripts/release_contract.py` is the immutable versioned required-file inventory outside
the generated manifest. `release-manifest.json` must match it exactly. Read-only
validation uses a deliberately small standard-library bootstrap to authenticate the
manifest inventory and every listed byte before importing or executing any semantic
release module from the requested repository root. The bootstrap itself and the
manifest bytes it initially parses are therefore trusted validation code; the
contract does not claim an impossible self-authentication of that bootstrap. Missing,
extra, changed, syntactically corrupt, or top-level-side-effect release modules fail
in the integrity phase before semantic import. Validation never repairs hashes or
regenerates a manifest. Cache exclusions are limited and documented; a required-file
change is a separately reviewed contract-version migration. Only the explicit
release command writes the manifest.

The same validation performs a recursive current-tree scan and an all-ancestor Git
name/blob scan from every local `HEAD` ancestor for the narrowly forbidden private
bulk derivative and mention/artifact-dump patterns. This is not a blanket claim that
the repository contains no museum data. If Git metadata is unavailable, historical
boundary verification reports that inability and fails closed. Runtime
`__pycache__`, `.pytest_cache`, `.pyc`, and `.pyo` products are excluded only as stated
in the static release contract and must not be committed.

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
  --evidence /tmp/hapi-327-final-rerun-evidence.json
```

The ordinary two-run command refuses both outputs and evidence inside the tracked
release directory and refuses to overwrite an existing evidence path. An intentional
release update requires the explicit `--release-maintainer-mode`; the reproducibility
workflow above is read-only with respect to tracked release files.

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
The committed two-run identities remain release-authenticated historical evidence.
Read-only validation separately accepts any fresh authenticated reproduction whose
19 deterministic output hashes, archive/runtime/lock bindings, input snapshot, and
tool hashes match that release; absolute output path, fresh UUID, and provenance-file
hash are not equivalence inputs. The original `/tmp` run directories are therefore
not prerequisites for the documented validation command.

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
a corpus conclusion. This branch has no CI run before a PR exists: the commands
above are local repository-owned test execution, not a CI status. Any later PR CI
and exact-HEAD external review remain `PENDING_OUTSIDE_COMMIT` until independently
run after the commit.

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
| Exact formulas and museum denominators | `preregistration.json`; recomputation in `validate_contract.py` and the collected repository test |
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
  are reported and candidate work must version any stronger authenticated source export.
- No candidate research or candidate graph exists in #327, so the comparator schemas
  are preregistered and tested on logic-only adversarial cases, not presented as a
  candidate result.
- No expected effect, population precision, or population recall is inferred from
  the provisional silver process or the optimistic measurable ceilings.
- Changing corpus, extractor, matcher, normalization, authority snapshots,
  opportunities, formulas, or denominators creates a new evaluation version.
