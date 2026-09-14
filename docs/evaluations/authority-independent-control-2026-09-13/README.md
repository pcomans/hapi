# Authority-independent cross-museum control

**Evaluation date:** 2026-09-13

**Frozen corpus snapshot:** 2026-08-27

**Resolver snapshot base:** `97f2e610974f0e89b9c03d409b230dff89edbb1f`

> **Scope warning:** the tested resolver is an archived, disposable,
> **non-production** linkability adapter. Production enrichment is unimplemented.
> Its site inputs are archived filtered iDAI rows used as raw, unclosed
> curation-source data, not a production canonical site graph. This experiment can
> support claims only about this adapter and frozen inventory snapshot.

## Answer

**Review status: `NOT_RUN`; quality conclusion: `NOT_AVAILABLE`.**

**Execution readiness: `BLOCKED` pending a genuine immutable provider snapshot and an
authorized explicit API path.**

The experiment now supplies a fair authority-independent mention ledger, two mechanical
arms, and a fresh blinded review population. It does **not** yet answer whether the
archived resolver improves useful cross-museum matching. No prompt-audited, fully
traceable review has been run for the corrected queue, and no LLM judgment is included
in this release.

Earlier review artifacts and their aggregate conclusion were invalidated. They applied
one case-level judgment to arm-native nodes that can have different evidence or record
membership, and their LLM calls did not preserve the full provenance required here.
Those artifacts are not bound by the current manifest, are not scorer inputs, and must
not be cited as evidence. Abstention likewise means that no scored decision was made;
it is not equivalent to an incorrect match.

The unreviewed mechanical inventory is still useful for locating the comparison:

- the complete experimental population has 96 target-by-museum-pair cases: 13
  authority-only transitions, 37 literal-only transitions, and the complete frame of
  46 retained controls;
- those cases represent 84 literal-arm nodes and 59 authority-arm nodes;
- the retained controls contain 47 literal nodes for 46 authority nodes. Eight controls
  have different arm-native record membership, one other control maps two literal nodes
  to one authority node, and all nine therefore require separate native accounting;
- after identical native evidence is deduplicated, Stage 1 contains 106 independently
  shuffled review units. Every arm-native node points to its own frozen evidence and
  review-unit hash.

These are inventory counts, not claims that any gained, lost, or retained connection is
correct or useful.

## Minimal design

The experiment remains a small offline control:

1. `scripts/extract_mentions.py` reads the authenticated archive and freezes one
   deterministic mention ledger. It imports only the Python standard library. Mention
   detection and `[start,end)` spans use raw field structure and fixed syntax; they do
   not read authority labels, aliases, IDs, graph files, or resolver results.
2. `scripts/compare_arms.py` reads that exact ledger once. The literal arm groups by
   `(entity_type, NFC + casefold + collapsed whitespace)` while retaining punctuation
   and diacritics. The authority arm imports the exact archived adapter and refuses
   changed adapter or inventory hashes.
3. `scripts/build_review_queue.py` derives the exhaustive transition/control frame,
   preserves each arm's native nodes and record memberships privately, emits a flat
   Stage 1 evidence queue, and holds proposed authority targets for gated Stage 2.
4. `scripts/review_protocol.py` validates exact prompt, queue, composed-input, model-run,
   raw-response, citation, and reconciliation provenance. Reviewer disagreements require
   an explicit per-field cited override; agreement cannot be silently changed.
5. `scripts/wrap_review_response.py` creates the exact bytes an external launcher must
   send and wraps the exact returned bytes without asking the model to embed its own
   response.
6. `scripts/score_review.py` can score only two independently identified, validated
   reviews and one validated consensus at each stage. It scores literal and authority
   nodes separately and unions each arm's own private record IDs.
7. `scripts/verify_rerun.py` compares every registered private output from two complete
   corpus runs byte-for-byte.

Stage 1 exposes only museum pair, entity type, exact museum-side evidence, counts, roles,
and field pointers. It has no arm/class, authority target, mention ID, artifact ID, or
stable cross-side group token. Every museum side is one aggregate evidence block, so a
hidden literal partition cannot create a group-cardinality or ordinal alignment proxy.
The 106 flat review units also prevent case structure from revealing
whether evidence belongs to a transition or retained control.

The score-eligible types are ruler, site, and explicit tomb/monument codes. Temple and
excavation mentions are frozen and reported, but both arms abstain. No committed
canonical temple or excavation authority exists, so constructing substitutes would
answer a different question.

## Frozen inputs and ledger

- Private archive SHA-256:
  `f4aabc2fc03b3ee0b5965bb9b27129e0ac482dae086c6124dd0d73d70276cc5b`
- Canonical gzip member SHA-256:
  `b69fb207b5775f3fca3e3fe6c1dad13df91b0d90afdf196c17d869721be4ca24`
- Records scanned: 36,245 (Met 27,969; Brooklyn 7,554; Harvard 722)
- Records with at least one extracted mention: 31,485
- Mention ledger rows: 148,871
- Deterministic ledger gzip SHA-256:
  `14d2fe2983adcda95051a33943eac070129ee108af508fdfe0b0fee3316923b7`
- Canonical uncompressed ledger SHA-256:
  `b1e7b7ab5d4b64661fc831e125bbe1372f599e87267cb8299119113c9aaf05fd`
- Ordered mention-ID SHA-256:
  `28402aaf80a094a76d35ab3d5281d5380366c55483a253271eb1ebae84d7ed73`

Mention counts are Met 142,008; Brooklyn 5,152; Harvard 1,711. By type they
are site 113,738; ruler 11,555; tomb/monument 4,863; temple 2,312; and
excavation 16,403.

Both arm files contain exactly 148,871 rows in the same mention-ID order and carry the
ordered-ID hash above. `results/real-run-report.json` records the executable equality
proof. `results/real-rerun-proof.json` records two complete runs and byte identity for
all registered outputs.

## Unreviewed mechanical results

### Any two museums, by museum

| Museum | Literal shared records | Authority shared records | Authority gains | Authority losses | In both | Net authority change |
|---|---:|---:|---:|---:|---:|---:|
| Met | 27,330 | 14,411 | 12 | 12,931 | 14,399 | -12,919 |
| Brooklyn | 2,894 | 1,154 | 1 | 1,741 | 1,153 | -1,740 |
| Harvard | 534 | 7 | 0 | 527 | 7 | -527 |

The literal arm mechanically has 72 nodes shared by any two museums; the authority arm
has 53. These counts include broad or possibly incorrect nodes and therefore cannot be
read as quality or treatment effect.

### Inclusive museum pairs

| Pair | Literal nodes | Authority nodes | Literal records by side | Authority records by side | Authority-only nodes | Literal-only nodes |
|---|---:|---:|---|---|---:|---:|
| Met–Brooklyn | 70 | 52 | 27,330 / 2,894 | 14,411 / 1,153 | 11 | 28 |
| Met–Harvard | 7 | 3 | 26,800 / 534 | 506 / 6 | 1 | 5 |
| Brooklyn–Harvard | 7 | 4 | 2,882 / 521 | 332 / 7 | 1 | 4 |

Pair-side mechanical record deltas are Met–Brooklyn: Met +12/-12,931 and Brooklyn
+1/-1,742; Met–Harvard: Met +1/-26,295 and Harvard +0/-528; Brooklyn–Harvard:
Brooklyn +0/-2,550 and Harvard +1/-515.

### Literal-loss attribution

Each literal-only node is assigned one closed resolver-outcome cause. Counts are
pair-inclusive, so a node spanning three museums appears in more than one pair.

| Pair | Ruler absent target | Ruler duplicate unmerged candidates | Site absent target | Site ambiguous target |
|---|---:|---:|---:|---:|
| Met–Brooklyn | 4 | 4 | 19 | 1 |
| Met–Harvard | 0 | 1 | 3 | 1 |
| Brooklyn–Harvard | 0 | 1 | 2 | 1 |

The ruler loss is dominated by duplicate, unmerged claim-graph candidates: 6 of 10
ruler loss pair cases, versus four absent/unmatched cases. Across pair-side memberships,
the duplicate-candidate cases account for 1,016 lost ruler-record memberships, versus
35 for absent targets. The site loss is dominated by absent targets (24 of 27 cases),
with three ambiguous cases. These are resolver-outcome attributions, not adjudications
that the literal connection was useful or correct.

### Concentration

Top-1 is the unique-record union on the highest-incidence shared node divided by all
connected records on that museum side. HHI uses direct node-incidence counts.

| Pair side | Literal top-1 | Authority top-1 | Literal HHI | Authority HHI |
|---|---:|---:|---:|---:|
| Met in Met–Brooklyn | 97.23% | 79.22% | 0.2664 | 0.2329 |
| Brooklyn in Met–Brooklyn | 99.55% | 27.75% | 0.5350 | 0.1575 |
| Met in Met–Harvard | 99.15% | 90.12% | 0.8911 | 0.8215 |
| Harvard in Met–Harvard | 100.00% | 66.67% | 0.4908 | 0.5000 |
| Brooklyn in Brooklyn–Harvard | 99.97% | 96.39% | 0.7951 | 0.9296 |
| Harvard in Brooklyn–Harvard | 97.89% | 57.14% | 0.9583 | 0.3878 |

The authority arm usually lowers top-1 concentration because its unmatched inventory
omits the dominant broad literal node. HHI does not improve on every side, and removing
a broad node is not evidence that a replacement is more accurate.

### Abstention and unresolved outcomes

Both arms make the same 20,956 mention-level abstentions: 18,715 unavailable-authority
mentions (16,403 excavation; 2,312 temple) and 2,241 ruler-expression abstentions
(uncertain, multi/range, temporal, or unparsed structured expressions). In addition,
the authority arm has 5,239 ambiguous and 78,875 unmatched score-eligible mentions.
The literal arm has no ambiguous/unmatched status by construction. Complete museum,
type, status, and distinct-record counts are in the report.

## Reproduce the corpus control

The private row-level ledger and arm outputs are not committed because the archive is a
private working-data handoff with museum-specific redistribution terms. From the
repository root, using the locked pipeline environment:

```bash
mkdir -p /tmp/hapi-authority-control-2026-09-13-a
pipeline/.venv/bin/python docs/evaluations/authority-independent-control-2026-09-13/scripts/extract_mentions.py \
  --archive /workspaces/content/dropbox/hapi-museum-corpus-2026-08-27.tar.gz \
  --ledger /tmp/hapi-authority-control-2026-09-13-a/mentions.ndjson.gz \
  --manifest /tmp/hapi-authority-control-2026-09-13-a/extraction-manifest.json
pipeline/.venv/bin/python docs/evaluations/authority-independent-control-2026-09-13/scripts/compare_arms.py \
  --repo-root . \
  --ledger /tmp/hapi-authority-control-2026-09-13-a/mentions.ndjson.gz \
  --extraction-manifest /tmp/hapi-authority-control-2026-09-13-a/extraction-manifest.json \
  --out /tmp/hapi-authority-control-2026-09-13-a
pipeline/.venv/bin/python docs/evaluations/authority-independent-control-2026-09-13/scripts/build_review_queue.py \
  build --repo-root . \
  --run /tmp/hapi-authority-control-2026-09-13-a \
  --out /tmp/hapi-authority-control-2026-09-13-a/review
```

Repeat in an independent `-b` directory, then run:

```bash
pipeline/.venv/bin/python docs/evaluations/authority-independent-control-2026-09-13/scripts/verify_rerun.py \
  --first /tmp/hapi-authority-control-2026-09-13-a \
  --second /tmp/hapi-authority-control-2026-09-13-b \
  --out /tmp/hapi-authority-control-2026-09-13-rerun-proof.json
```

## Traceable review protocol (blocked; not run)

Protocol v2 is fail-closed. Every exact model invocation must contain the persisted launcher
system prompt, role prompt, role-specific raw-response JSON Schema, and queue; a
reconciler invocation additionally contains both complete source-review packages. The
wrapper validates the final JSON against that exact schema and requires both the final
agent-message bytes and a transport-capture JSONL containing the bound request metadata,
provider/CLI events, terminal usage, and paired web calls/results where research is
required. Validation rejects a changed or truncated capture or a final transcript
message that is not byte-for-byte identical to the saved final response. A wrapped
artifact is validated in a same-directory temporary file and published atomically only
when the destination does not already exist. The synthetic
transport records in unit tests test this contract only; they are not captured provider
runs and do not establish provider compatibility or a complete real interaction.

A Claude prompt audit must use `claude --bare --print` with an explicit persisted system
prompt, no agent profile, and archived stream-JSON outer/result events. Bare mode requires
`ANTHROPIC_API_KEY` or a configured `apiKeyHelper`; neither authorized path is available
in this environment. Claude OAuth safe mode is not equivalent and is not accepted. A tool-using
review must use an explicit Responses API rollout that exposes the exact instructions,
all output/tool events, terminal usage, and final agent message. Codex CLI JSONL is not
an accepted production transport because it does not yet bind the provider-native model
snapshot and base instructions required by this protocol.

Every run must also bind genuine provider evidence for a distinct, immutable, dated
model snapshot. Merely appending the observation date to a mutable model name fails
validation. As of 2026-09-14, no pinned snapshot identifier is exposed for
`gpt-5.6-sol`, and this environment has no authorized direct Responses API credential.
Review execution is therefore **BLOCKED**. Do not launch or score a data judgment until
both conditions are satisfied and a new prompt audit passes.

One v1 prompt-auditor attempt on 2026-09-14 failed before any reviewer ran. Its complete
available files remain preserved outside this release as failed evidence. The returned
Markdown is neither contract-valid JSON nor a complete launcher transcript, so it cannot
be wrapped, repaired, or reused as a passing audit.

### Near-duplicate census units

The population is a finite census, not a sample of statistically independent rows.
Exactly identical museum-side evidence is deduplicated, but similar-looking units remain
separate when visible evidence or private arm-native node/record membership differs.
Collapsing them would erase a literal node, authority node, or its supporting records and
would reintroduce the accounting defect this repair fixes. Versioned auditor, reviewer,
and reconciler prompts neutrally note that recurrence may occur and require each unit to
be judged independently without naming its mechanism, copying outcomes, merging units,
or inferring an arm/class from recurrence. Scoring
continues to union each arm's native records, so no inferential independence claim is
made.

The current bindings are in `results/real-review-protocol-manifest.json`; raw-response
contracts are in `raw-response-contracts/`, and exact launcher system prompts are in
`launcher-instructions/`. Once the runtime blocker is genuinely cleared,
`scripts/wrap_review_response.py --help` and `scripts/review_protocol.py --help`
enumerate the fail-closed compose, wrap, and validation inputs.

## Limitations

- This is a deterministic control, not a gold-standard evaluation. A literal match can
  be broad or homonymous; an authority match can still be wrong.
- Text ruler extraction requires an explicit royal cue and bounds at three syntactic
  name tokens. Longer royal names may be truncated; it is not general NER.
- Location parsing splits only top-level commas/semicolons and emits at most one leading
  pre-parenthesis child. It does not interpret arbitrary nesting or prose.
- Within a location variant, a temple cue takes type precedence and suppresses site
  scoring. A separately emitted pre-parenthesis child can still be a site, but this rule
  can omit mixed temple/site readings.
- Tomb detection is restricted to explicit code syntax. Free-text names cannot become
  mentions merely because a current authority knows them.
- Temple and excavation conclusions are fundamentally unavailable until canonical
  authorities exist. Their counts are inventory only, and abstention is not an
  incorrect-match judgment.
- This cannot validate production enrichment: that path is unimplemented, and the
  archived adapter's site inventory is raw, unclosed curation-source data.
- The authenticated archive establishes this 36,245-record snapshot, not upstream
  production lineage or current museum API contents.
