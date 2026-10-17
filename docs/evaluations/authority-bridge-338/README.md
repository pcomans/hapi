# #338: museum mentions to authority links, in the pipeline

#337 and #361 showed that linking museum records through the authority beats plain text for
sites (all three museum pairs) and for rulers (Met–Brooklyn). They did it with evaluation
scripts. This work moves that logic into the pipeline package, so production can make the same
links. Per the owner's decision of 2026-10-16, the links are written to files first; a
database table comes later.

**Later (2026-10-17).** The ruler re-registration of 2026-10-16
(`../ruler-reregistration-2026-10-16/`) replaced #361's ruler result: rulers now qualify in
Met–Walters only, and Met–Brooklyn rulers are unevaluated (`QUALIFIED_SCOPES`). The frozen
reports here keep the flags of the code they record.

## Step 1 (#372): promote and prove

- **`pipeline/pipeline/enrich/mentions.py`**: #361's mention extractor, copied verbatim (its
  grammar and `extract_mentions`). A test fails on the first edit to any copied definition.
  - It reads the raw museum records and is authority-blind.
  - `extract_mentions` names the evidence fields of the three museums the evaluations measured.
    Cleveland and the Walters, added later (`docs/museum-sources/cleveland.md`, `walters.md`),
    have their own readers beside it, `cleveland_mentions` and `walters_mentions`;
    `extract_all_mentions` joins them, and a run calls that.
- **`pipeline/pipeline/authority/resolver.py`**: the linkability adapter's ruler, site and
  Porter & Moss tomb resolvers.
  - `graph_kings` now builds on this module. A frozen evaluation still passes in the adapter.
- **`pipeline/pipeline/enrich/authority_links.py`**: resolves mentions in one of two modes, the
  matcher's switch.
  - `authority`: sites against iDAI, tombs against Porter & Moss, rulers against the king
    graph and Dodson & Hilton's royal women, with #369's rules.
  - `literal`: the plain-text baseline.
  - Every mention gets a row giving its status and why: abstained (with the expression, or an
    entity type with no authority: temples, excavations), ambiguous, unmatched, or resolved.
    The row keeps the resolver's own answer whole (`resolution`): its candidates, the keys it
    tried, and the context rule that chose or refused.
  - `build_links` joins a record to a target only on resolved mentions. A link always records
    `relation: "identity"`, the mentions, their evidence roles and the `resolver_version`.
  - `resolver_version`, in both modes, is the SHA-256 over the code and data files the mode
    reads plus the Unicode version. A test checks that every module a fresh interpreter loads
    for the step is covered.
  - `QUALIFIED_SCOPES` records where the evaluations found the authority beats plain text:
    sites in all three museum pairs (#337), rulers in Met–Brooklyn (#361). Tombs and the Harvard
    ruler pairs are unevaluated, not failed: no case of theirs reached review. Every type with an
    authority is resolved, and step 3 reports unevaluated scopes separately, never as proven.

The evaluation scripts stay as they are, because their runs pin them by hash. The production
copies are now the live code.

## The proof

`scripts/check_promotion.py` writes `results/promotion-check.json`. It runs the production step
on the frozen corpus archive (`hapi-museum-corpus-2026-08-27`) and compares it with #361's
stored run.

| Check | Result |
|---|---|
| Mentions | 148,964, identical to #361's ledger row for row |
| Rulers, authority mode | 11,648 compared; 11 differ, each exactly as #369 measured it; none otherwise |
| Sites and tombs, authority mode | 113,738 sites and 4,863 tombs compared with the adapter's resolvers (#337 v10's); 0 differ |
| Rulers, literal mode | 11,648 compared with #361's typed-literal arm; 0 differ |
| Sites and tombs, literal mode | 118,601 compared with #337's typed-literal arm (its own code); 0 differ |

The #361 run files it compares against are checked against the hashes in #361's run manifest.
The result records the per-file snapshot of the code it measured.

The CI tests need no private data:
- the extractor is checked against #361's script on the museum fixtures and on records written
  to reach each branch;
- the resolvers are checked against the adapter on every authority label and variants of it;
- the enrichment rows and links are checked on hand-built mentions.

## Step 2: versioned link files

- **`pipeline/pipeline/enrich/link_files.py`, `write_run`**: one run writes these under
  `<root>/<run_id>/`:
  - the mentions;
  - both modes' resolutions and links;
  - a manifest. It holds the inputs' digest, both snapshots, this module's SHA-256, every
    file's hash and row count, outcomes by entity type, status and reason, and the inventory of
    what is not resolved (temples and excavations with their reasons and counts, and the
    unevaluated scopes).
- **The run ID** is the manifest's own digest: the SHA-256 of the manifest without its
  `run_id`. It therefore covers the inputs, both resolver versions, the writer, the rows set
  aside, the counts, outcomes and inventory, and every file. The manifest hashes each file's
  content (a gzip file's decompressed NDJSON), so the hash does not depend on the zlib build. The
  same inputs and code give the same content; an existing run directory is checked against
  its manifest (`verify_run`), never rewritten.
  - A test runs `write_run` in two interpreters with different `PYTHONHASHSEED`s and requires
    the same manifest and file contents.
- **Writes survive a process crash.** A run is written beside its place and renamed into it,
  and `CURRENT` is replaced in one step, so a crashed process leaves no half-written run, only a
  scratch directory, which the next run removes. (There is no fsync, so a power loss can leave
  one; these files are a working store.)
  - A run directory that lacks a file, holds a stray one or differs in content fails loud,
    with a message saying which.
  - Before writing anything, a run checks `CURRENT` and the previous run. The previous run's
    manifest must digest to its run ID, and its files must be exactly the ones the manifest
    names, with the recorded content. A mismatch fails loud and leaves the root as it was.
  - A pending diff is written whole and then named. One left by a killed process is published
    if its run became current; otherwise it is discarded unread, so a truncated file never
    blocks the root.
- **Withdrawal.** `<root>/CURRENT` names the run in force. When a new run replaces it,
  `<root>/diffs/<previous>-to-<run>.json` lists, for each mode, the links added, removed and
  changed.
  - A removal gives its reason: `set_aside` (the record's canonical row was set aside, see
    above), `record_gone`, `mentions_gone`, or `resolves_otherwise` (with each mention's new
    status and reason).
  - A kept link whose mentions, evidence roles or kind changed is listed as `changed`, with the
    old and new values and each lost mention's new resolution. A withdrawal inside a link that
    several mentions make is therefore visible, and so is a role change alone (a role is not
    part of a mention's ID).
  - Replacing `CURRENT` is the commit. A diff is published only once its run is current; one
    left pending by a run that died is published or removed by the next run, depending on
    whether the commit happened.
  - `record_gone` needs a canonical row to leave the table. The ingest and normalize assets
    upsert and never delete (#374), so in production a withdrawn record does not yet leave; a
    record the normalize step drops is `set_aside`.
  - `diffs/` holds one file per transition (previous run, new run), not a log: a transition made
    twice is the same file, and the order of transitions is not kept.
- **`target_kind`** keeps queens distinct from kings. The kinds are `king`, `royal_woman`,
  `site`, `tomb` and `literal`; a royal woman who reigned is her king. `relation` is `identity`
  only: no resolver produces containment or a close match. #333's vocabulary is needed when
  one does.
- **The asset** is `pipeline/pipeline/assets/enrich/authority_links_asset.py`, after every
  museum's normalize asset (a structural test holds the deps to that). It reads the canonical and raw tables and writes to
  `HAPI_AUTHORITY_LINKS_DIR` (default `data/authority-links/`, which is gitignored).
  - These files are a working store, not durable storage; the database table comes later.
  - It has run against a real Postgres (Neon), on the frozen corpus; see "The database run (2026-10-16)" below.
  - Runs under one root hold an exclusive lock; a second materialization at the same time
    fails loud and changes nothing. The operating system releases the lock if a run dies.
  - `write_run` takes the lock before it calls the caller's `read_inputs`. A run therefore
    cannot read older inputs than a run that became current before it, and no entry point
    writes without the lock.
  - The asset's `read_inputs` reads all the tables in one `REPEATABLE READ` transaction, so
    its canonical rows and raw payloads come from the same moment.
  - One moment is not one pipeline generation: ingest commits raw rows batch by batch, and
    normalize writes canonical rows later. So `write_run` checks the inputs
    (`pipeline/pipeline/enrich/inputs.py`) and refuses inputs where:
    - a canonical row is not what its museum's normalize step makes of its raw payload;
    - a canonical row has no raw payload;
    - a raw row the step keeps has no canonical row yet.

    A canonical row whose raw payload the step no longer keeps (a Brooklyn object re-ingested
    as not Egyptian) is not refused. The normalize assets never delete (#374), so such a row
    would otherwise block every run; it is left out instead and listed in the manifest
    (`canonical_rows_set_aside`).

    That is all it checks, and it sees a change only through the mapper. A change confined to
    raw fields the extractor reads but the mapper does not map (Harvard `labeltext`,
    `commentary`, `contextualtext`) leaves the mapped row equal. Such a payload, read before
    normalize re-runs, passes, and so does a raw table half re-ingested and fully normalized. The
    raw tables carry no generation id or ingest time to tell. A complete-ingest marker is #375
    (database step); a test pins the gap so that #375 has to change it. With the code recorded in
    `results/promotion-check.json` (`check_inputs.code_sha256`: every `pipeline` module the
    check loads, plus the pydantic version and the `uv.lock` hash), all 36,245 records of the
    frozen corpus passed. A refused run fails and nothing retries it; the operator
    re-materializes it once upstream is done.
- **Per-museum field inventory.** A test pins the exact fields each museum's fixtures give
  mentions from. A museum without an inventory fails loud in the extractor.

## Step 3: cross-museum connections, authority on and off

- **`pipeline/pipeline/enrich/cross_museum.py`, `report(run)`.** It reads a verified run's
  links in both modes; the mode is the switch. Two records of different museums are connected
  when each is linked to the same target. It gives, by museum, museum pair and entity type:
  - the shared targets, and the records connected on each side;
  - the records the authority connects that plain text does not (`gained`), and the reverse
    (`lost`);
  - the largest 1 and 5 shared targets (by ID) and their share of each side;
  - #337's headline measure: each museum's records on a target shared with any other museum.

  Each scope is flagged `qualified` per `QUALIFIED_SCOPES`. That is the policy flag: an
  evaluation found the authority helps there. It does not say a review saw the population
  measured, which `report()` cannot know of an arbitrary run. For this frozen run, the result's
  `review_coverage` says so per qualified scope:
  - the sites' reviews cover it, by the identity test above;
  - #361's review does not cover the three Met–Brooklyn ruler records #369's Ahmes B connects.

  This is the measurement; no deployed
  matcher reads these links yet. Matching is the web query layer's (ADR-008), and that
  integration comes with the database step.
- **`scripts/run_end_to_end.py`** writes `results/end-to-end.json`. It runs `write_run` twice on
  the frozen corpus, in two interpreters with different `PYTHONHASHSEED`s and into fresh
  directories, then reports on each. The two runs must have the same manifest, file contents and
  report; both run IDs are recorded.
  - The result also records the hashes of the report code. A test binds its resolver versions to
    the ones the step 1 proof measured.
  - The result also names #369's tuned-on records (brooklyn-3634, met-566763, brooklyn-3599),
    records each scope's shared target IDs, and includes #337's and #361's committed headlines.

### Result on the frozen corpus

148,964 mentions; 48,994 authority links; 127,711 literal links. Both runs were identical.

| Scope | Qualified | Shared targets (authority / literal) | First museum: connected (authority / literal); gained, lost | Second museum |
|---|---|---|---|---|
| ruler, Met–Brooklyn | yes (#361), but 3 connected records unreviewed | 14 / 13 | Met 1,957 / 1,981; +33, −57 (−59 before #369) | Brooklyn 20 / 19; +2, −1 (−2 before #369) |
| ruler, Met–Harvard | no (unevaluated) | 2 / 2 | Met 920 / 921; +0, −1 | Harvard 2 / 2 |
| ruler, Brooklyn–Harvard | no (unevaluated) | 2 / 2 | Brooklyn 6 / 6 | Harvard 2 / 2 |
| site, Met–Brooklyn | yes | 47 / 58 | Met 14,393 / 27,198; +136, −12,941 | Brooklyn 1,151 / 2,890; +0, −1,739 |
| site, Met–Harvard | yes | 3 / 6 | Met 506 / 26,628; +1, −26,123 | Harvard 6 / 534; +0, −528 |
| site, Brooklyn–Harvard | yes | 4 / 6 | Brooklyn 332 / 2,881; +0, −2,549 | Harvard 7 / 520; +1, −514 |
| tomb, any pair | no (unevaluated) | 0 / 0 | none | none |

### Against what the evaluations reviewed

The counts here are of connections, not of right ones. Rightness was judged by review, so what
matters is whether these are the populations that were reviewed.

- **Sites: #337's reviewed population, record for record.**
  - #361's mention ledger holds every one of #337 v10's 148,871 mentions unchanged, and adds 93
    royal-woman-cued ruler mentions (`ruler-reregistration-2026-10-15/results/ledger-diff.json`).
  - The step 1 proof found the pipeline's site resolutions equal to #337's resolver, and its
    site literal targets equal to #337's own code, on every one of those mentions.
  - So every site link, and every record it connects, is the one #337 made. The counts agree
    accordingly, in both modes, with #337's committed report:
    - plain text: Met 27,198, Brooklyn 2,890, Harvard 534;
    - authority: Met 14,393, Brooklyn 1,152, Harvard 7.

    So do the largest 1 and 5 shared targets of every site pair, side and mode.
  - Tests check all of this against those files. The site scopes #337 qualified are therefore
    this population, and its review's verdicts apply to it.
  - Tomb connections are 0 in both, so the difference between #337's authority headline (Met
    14,502 / Brooklyn 1,156 / Harvard 8) and this run's is in rulers, which have changed since.
- **Rulers, Met–Brooklyn: #361's reviewed population, plus one unreviewed target from #369.**
  - The step 1 proof found every ruler resolution equal to #361's except #369's 11 measured
    changes, and every literal target equal.
  - **Plain text is exactly #361's committed arm:** 13 shared targets, Met 1,981, Brooklyn 19.
  - **The authority is #361's with one shared target more,** D&H's Ahmes B. It joins three
    records:
    - the two Queen Ahmose records, brooklyn-3634 and met-566763, which #369 newly resolved to
      her;
    - a third Met record, met-547683, which #369 did not change. It resolved to her before but
      had no Brooklyn record to share her with.
  - **Those three records are #361's reviewed losses that now connect.** Each is connected
    through Ahmes B alone and was connected by plain text, and the authority only grows from
    #361's (step 1, and #369's result: none of its changes was resolved before). Counts: Met's losses go from
    59 to 57 and Brooklyn's from 2 to 1. The gains are #361's in number (Met 33, Brooklyn 2).
  - **The change is unreviewed,** found on #361's deciding case. The scope's qualified flag
    rests on #361's review of the population before it.
  - **A next registration must flag the tuned-on records (#358).** These are brooklyn-3634,
    met-566763, and brooklyn-3599 (Neferu, which makes no link), and met-547683 with them.
  - Tests check all of this against #361's committed report and #369's result.
- **Ruler and tomb scopes not qualified** are unevaluated. Nothing here judges them.
- **The large site "losses" are mostly broad plain-text targets the authority does not hold.**
  These are bound by their literal target hashes, so no museum text is committed. The authority
  resolves neither name.
  - Plain text's largest site target in Met–Brooklyn and Met–Harvard is "Egypt". In
    Met–Brooklyn it holds 97.7% of Met's connected site records.
  - Harvard's largest in Met–Harvard is "Africa", which holds all 534 of them.

  Whether such a loss is good or bad is #337's review's to say. Its site losses were 12 judged
  correct and useful (d) and 15 wrong or not useful (e); it named the Fayum, a whole region, as
  too broad to be useful. That review, not this count, is the evidence.
- **This is the pipeline code's result on a frozen export of the museum tables, not a deployed
  run.** The asset, run against a database holding that export, later reproduced it exactly (see
  "The database run" below). Deployed lift still needs the asset to run on live, ingested data
  (see #374 and #375) and a matcher in the web layer that reads the links.

## The database run (2026-10-16)

The `authority_links` asset has now run against a real database: Neon, provisioned through the
Vercel integration on project `web-claim-graph-hapi`, Postgres 18.6. Local compose pins 16.
- **Setup.** The `catalog` and `web` schemas were created (`docker/init-schemas.sql`) and Alembic
  ran to head.
- **Load.** `scripts/load_frozen_corpus.py` loaded the frozen corpus into the empty catalog
  tables: 36,245 canonical rows, and 27,969 Met, 8,832 Brooklyn and 722 Harvard raw payloads.
  - The archive holds the raw payloads parsed. Their `data` column is therefore `json.dumps` of
    each payload, as the ingest assets write it, not the stored bytes themselves.
  - The asset parses that column again, so the run does not depend on the bytes.
- **Run.** Dagster materialized the asset (`uv run dagster asset materialize -m
  pipeline.definitions --select authority_links`, with `DATABASE_URL` set to the database) in
  about 20 seconds.

**It made the same run as the frozen one: run ID `f13f590d…`.** The run ID is the digest of the
run's manifest, which covers the inputs, the resolver and writer versions, and every output
file's content. So the asset, reading the tables, made exactly the mentions, resolutions and
links measured above (`results/database-run.json`).
- **Committed evidence.** The run's own manifest is committed
  (`results/database-run-manifest.json`; it holds hashes, counts and the authority code's
  reasons, no museum text). A test recomputes its digest, which is the run ID. Dagster's record
  of the materialization (its run `06010d54…`, with the asset's metadata) is in
  `database-run.json`.
- **What this does not prove.** By design, the manifest is the same as the frozen run's. These
  files show what the run produced; they cannot by themselves prove that it ran against the
  database. That rests on this record and can be repeated with the commands below.

It was a one-off run from the devcontainer
against a database loaded by hand with the August export, not a deployment: there is no deployed
Dagster, no schedule and no live data, and the run went to local files.

It does not cover:
- the search index (Typesense);
- a web matcher reading the links;
- live ingest (#374, #375).

To reproduce: `vercel env pull` in `web-claimgraph/` (linked to the project), then use
`DATABASE_URL_UNPOOLED` as `DATABASE_URL` for Alembic, the loader and Dagster.

The Neon database no longer holds the August export alone. On 2026-10-16, Cleveland and the
Walters were ingested into it live (`catalog.raw_cleveland`, `catalog.raw_walters` and their
canonical rows). The loader refuses tables that already hold rows, Cleveland's and the Walters'
included, so to repeat this run, load the export into an empty database.

The proofs cover the code they recorded only:
- `results/promotion-check.json` records `snapshot` for the resolution and
  `check_inputs.code_sha256` for the input check;
- `results/end-to-end.json` records `resolver_versions`, `writer_sha256` and `report_sha256`.

Any later edit to a file in them needs a new run before the proof covers it, of
`scripts/check_promotion.py` or `scripts/run_end_to_end.py --archive <corpus archive> --out
results/end-to-end.json`.

Adding Cleveland edited them. Both scripts were re-run on the frozen corpus with that code, and
the output is in `results/rerun-after-cleveland/`. A test compares it with the committed results:
- every figure is the same, and the mention ledger is byte for byte the same;
- the inventory's unevaluated-scope lists only gain the Cleveland pairs at their end;
- what differs is only what names the code (hashes, resolver versions, run ids, the files whose
  rows carry the resolver version);
- Cleveland's own rows are new and empty, since the corpus predates it.

Adding the Walters edited them again, and `results/rerun-after-walters/` is the re-run with that
code. The same test holds it to the committed results, with the Walters' pairs and rows new and
empty beside Cleveland's.

Resolving kings in their record's context (`pipeline/pipeline/authority/king_context.py`,
`../king-context-2026-10-17/`) edited them again; `results/rerun-after-king-context/` is the re-run.
`check_promotion.py` now passes each record's dates. It counts a ruler mention the context chose,
refused or narrowed apart (`differ_by_king_context`: 13), beside #369's 11, and nothing differs
otherwise. A test holds the re-run to the previous one: only the ruler figures the measurement
reports changed, and the ruler scope qualified by #383 (`run_end_to_end.QUALIFIED_BY` now credits
the 2026-10-16 re-registration; the frozen corpus has no Walters records, so that pair connects
nothing here).

The committed `results/end-to-end.json` and `database-run.json` stay the records of the run they
describe. Tests compare the committed results with the evaluations' files, not
with the live code, so an edit does not turn main red; it leaves the result describing the code
it recorded.
