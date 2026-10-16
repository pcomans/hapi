# #338: museum mentions to authority links, in the pipeline

#337 and #361 showed that linking museum records through the authority beats plain text for
sites (all three museum pairs) and for rulers (Met–Brooklyn). They did it with evaluation
scripts. This work moves that logic into the pipeline package, so production can make the same
links. Per the owner's decision of 2026-10-16, the links are written to files first; a
database table comes later.

## Step 1 (this PR): promote and prove

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
- **The run ID** hashes the inputs, both resolver versions and the writer. The manifest
  hashes each file's content: a gzip file's decompressed NDJSON, so the hash does not depend on
  the zlib build. The same inputs and code give the same content; an existing run directory is
  checked against it, never rewritten.
  - A test runs `write_run` in two interpreters with different `PYTHONHASHSEED`s and requires
    the same manifest and file contents.
- **Writes are crash-safe.** A run is written beside its place and renamed into it, and
  `CURRENT` is replaced in one step, so a crash leaves no half-written run, only a scratch
  directory that the next run replaces. A run directory that lacks a file, holds a stray one or
  differs in content fails loud, with a message saying which.
- **Withdrawal.** `<root>/CURRENT` names the run in force. When a new run replaces it,
  `<root>/diffs/<previous>-to-<run>.json` lists, for each mode, the links added, removed and
  changed.
  - A removal gives its reason: `record_gone`, `mentions_gone`, or `resolves_otherwise` (with
    each mention's new status and reason).
  - A kept link whose mentions changed is listed as `changed`, with each lost mention's new
    resolution, so a withdrawal inside a link that several mentions make is visible too.
  - `record_gone` cannot happen in production yet. The ingest and normalize assets upsert and
    never delete, so a record a museum withdraws stays in the tables.
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
- **Per-museum field inventory.** A test pins the exact fields each museum's fixtures give
  mentions from. A museum without an inventory fails loud in the extractor.

## Left for step 3

- Cross-museum linking with the authority on and off, over a run's links, reported by museum,
  pair and entity type against `QUALIFIED_SCOPES`, and two hash-stable full-corpus runs.

The proof above covers the code in its recorded snapshot only. Any later edit to a file in the
snapshot (`results/promotion-check.json`, `snapshot`) needs a new `check_promotion` run before
the proof covers it.
