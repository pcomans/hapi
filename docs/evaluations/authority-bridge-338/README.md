# #338: museum mentions to authority links, in the pipeline

#337 and #361 showed that linking museum records through the authority beats plain text for
sites (all three museum pairs) and for rulers (Met–Brooklyn). They did it with evaluation
scripts. This work moves that logic into the pipeline package, so production can make the same
links. Per the owner's decision of 2026-10-16, the links are written to files first; a
database table comes later.

## Step 1 (this PR): promote and prove

- **`pipeline/pipeline/enrich/mentions.py`**: #361's mention extractor, copied verbatim (its
  grammar and `extract_mentions`).
  - It reads the raw museum records and is authority-blind.
  - `extract_mentions` names each museum's evidence fields.
- **`pipeline/pipeline/authority/resolver.py`**: the linkability adapter's ruler and site
  resolvers.
  - `graph_kings` now builds on this module. A frozen evaluation still passes in the adapter.
- **`pipeline/pipeline/enrich/authority_links.py`**: resolves mentions in one of two modes, the
  matcher's switch.
  - `authority`: sites against iDAI, rulers against the king graph and Dodson & Hilton's royal
    women, with #369's rules.
  - `literal`: the plain-text baseline.
  - Every mention gets a row giving its status and why: abstained (with the expression, or the
    unsupported entity type), ambiguous (with its alternatives), unmatched, or resolved.
  - `build_links` joins a record to a target only on resolved mentions. A link always records
    `relation: "identity"`, the mentions, their evidence roles and the `resolver_version`.
  - `resolver_version` is the SHA-256 over the code and authority files the resolution reads.

The evaluation scripts stay as they are, because their runs pin them by hash. The production
copies are now the live code.

## The proof

`scripts/check_promotion.py` writes `results/promotion-check.json`. It runs the production step
on the frozen corpus archive (`hapi-museum-corpus-2026-08-27`) and compares it with #361's
stored run.

| Check | Result |
|---|---|
| Mentions | 148,964, identical to #361's ledger row for row |
| Rulers, authority mode | 11,648 compared; 11 differ, all of them #369's changes, none outside |
| Sites, authority mode | 113,738 compared with the adapter's site resolver (#337 v10's); 0 differ |
| Rulers, literal mode | 11,648 compared with #361's typed-literal arm; 0 differ |

The CI tests need no private data:
- the extractor is checked against #361's script on the museum fixtures and on records written
  to reach each branch;
- the resolvers are checked against the adapter on every authority label and variants of it;
- the enrichment rows and links are checked on hand-built mentions.

## Next

- **Step 2:** a Dagster asset that writes versioned resolution and link files. It must make
  deterministic re-runs, remove a link when its source decision is withdrawn, and inventory the
  unsupported entity types.
- **Step 3:** cross-museum linking with the authority switched on and off, run twice on the full
  corpus with hash-stable results. Results go by museum, pair and entity type, and are reported
  as the pipeline's lift on the frozen corpus. A deployed, database-backed run comes later.
