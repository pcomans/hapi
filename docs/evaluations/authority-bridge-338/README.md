# #338: museum mentions to authority links, in the pipeline

#337 and #361 showed that linking museum records through the authority beats plain text for
sites (all three museum pairs) and for rulers (Met–Brooklyn). They did it with evaluation
scripts. This work moves that logic into the pipeline package, so production can make the same
links. Per the owner's decision of 2026-10-16, the links are written to files first; a
database table comes later.

## Step 1 (#372): promote and prove

- **`pipeline/pipeline/enrich/mentions.py`**: #361's mention extractor, copied verbatim (its
  grammar and `extract_mentions`). A test fails on the first edit to any copied definition.
  - It reads the raw museum records and is authority-blind.
  - `extract_mentions` names each museum's evidence fields.
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
- **The asset** is `pipeline/pipeline/assets/enrich/authority_links_asset.py`, after the three
  normalize assets. It reads the canonical and raw tables and writes to
  `HAPI_AUTHORITY_LINKS_DIR` (default `data/authority-links/`, which is gitignored).
  - These files are a working store, not durable storage; the database table comes later.
  - This devcontainer has no database, so the asset itself has not run, only its core. It
    should run once against a real Postgres before anything relies on it.
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

## Step 3: cross-museum matching, authority on and off

- **`pipeline/pipeline/enrich/cross_museum.py`** reads a run's links in one mode; the mode is
  the switch. Two records of different museums match when each is linked to the same target.
  - `matches(links, artifact_id)` gives a record's matches.
  - `report(run)` measures both modes and the change between them, by museum, museum pair and
    entity type. For each pair it gives the shared targets, the records connected on each side,
    the records the authority connects that plain text does not (`gained`) and the reverse
    (`lost`), and how much of each side the largest 1 and 5 shared targets carry.
  - Each scope is flagged `qualified` per `QUALIFIED_SCOPES`.
- **`scripts/run_end_to_end.py`** writes `results/end-to-end.json`. It runs `write_run` twice
  on the frozen corpus, in two interpreters with different `PYTHONHASHSEED`s and into fresh
  directories. It requires both runs to have the same manifest and file contents, then reports
  on the run.

### Result on the frozen corpus

148,964 mentions; 48,994 authority links; 127,711 literal links. Both runs were identical.

| Scope | Qualified | Shared targets (authority / literal) | Records connected, first museum (authority / literal; gained, lost) | Second museum |
|---|---|---|---|---|
| ruler, Met–Brooklyn | yes | 14 / 13 | Met 1,957 / 1,981; +33, −57 | Brooklyn 20 / 19; +2, −1 |
| ruler, Met–Harvard | no (unevaluated) | 2 / 2 | Met 920 / 921; +0, −1 | Harvard 2 / 2 |
| ruler, Brooklyn–Harvard | no (unevaluated) | 2 / 2 | Brooklyn 6 / 6 | Harvard 2 / 2 |
| site, Met–Brooklyn | yes | 47 / 58 | Met 14,393 / 27,198; +136, −12,941 | Brooklyn 1,151 / 2,890; +0, −1,739 |
| site, Met–Harvard | yes | 3 / 6 | Met 506 / 26,628; +1, −26,123 | Harvard 6 / 534; +0, −528 |
| site, Brooklyn–Harvard | yes | 4 / 6 | Brooklyn 332 / 2,881; +0, −2,549 | Harvard 7 / 520; +1, −514 |
| tomb, any pair | no (unevaluated) | 0 / 0 | none | none |

Reading it:

- **These are counts of connections, not of right ones.** Whether a change is better was
  judged by review in #337 (sites) and #361 (rulers), on the same resolutions. Step 1 shows the
  pipeline makes those resolutions exactly, apart from #369's 11 changes. So the reviewed
  verdicts carry over to the qualified scopes here. Nothing here judges the unqualified scopes.
- **Most site "losses" are one plain-text target, "Egypt".**
  - It joins 26,573 Met records with 2,881 Brooklyn and 510 Harvard records. In plain text it
    carries 97.7% of Met's and 99.7% of Brooklyn's connected site records in Met–Brooklyn.
  - The authority leaves "Egypt" unmatched (30,161 mentions): the iDAI site layer holds sites,
    not countries.
  - #337's reviewers judged links of that breadth not useful (its e class). The next largest are
    "Upper Egypt" and "Thebes" (Met–Brooklyn) and "Saqqara" (Met–Harvard).
- **Rulers, Met–Brooklyn.** The authority connects 33 Met and 2 Brooklyn records that plain
  text does not, and drops 57 and 1 that it does. #361 reviewed those changes and scored the
  scope as qualifying.
- **This is the pipeline code's lift on a frozen export of the museum tables, not a deployed
  run.** The asset reads the database, which this environment lacks (owner, 2026-10-16: files
  first). #337 measured potential lift with evaluation scripts; this measures the same lift
  through the production code. Deployed lift needs the asset run against the live database
  (#375 and #374 apply there).

The proof above covers the code it recorded only: `snapshot` for the resolution and
`check_inputs.code_sha256` for the input check (`results/promotion-check.json`). Any later edit
to a file in either needs a new `check_promotion` run before the proof covers it.
