# Hapi · Claim Graph (Vercel POC)

A deployable proof of concept of the **source-attributed claim graph** (ADR-018) with
**best-effort cross-source ruler matching** (ADR-020). It reunifies Egyptian rulers across
five scholarly sources — keeping every source's record intact and drawing a cross-source
identity link only when a shared, normalized **throne name** corroborates it, precision-first,
escalating to a human when in doubt.

- **Standalone Next.js 16 app** — deploys to Vercel with the repo subdirectory `web-claimgraph/`
  as the project root.
- **Embedded database** — the baked graph is served from **PGlite** (Postgres in WASM), seeded
  in-process from a committed JSON artifact. No external DB, no connection string, no secret at
  runtime. Turnkey.
- **The matcher runs at build time, not runtime** — the deployed app needs **no API key**.

## Architecture

```
pipeline/pipeline/authority/claimgraph/   (Python — the generator; runs at build time)
  sources.py     per-source adapters  -> canonical ruler records (5 sources)
  normalize.py   committed cross-convention name normalization table (ADR-020)
  matcher.py     stage-1 candidate generation + set-valued prenomen corroboration
  reviewer.py    stage-2 LIVE Anthropic reviewer (precision-first) + Rule-13 capture
  verdicts.py    verdict + gated same_entity_as shortcut emission
  clusters.py    connected components (navigation/visualization only)
  build_graph.py entrypoint -> web-claimgraph/data/claim-graph.json  (+ .reviewer-run.jsonl)

web-claimgraph/                            (TypeScript — the deployed app)
  data/claim-graph.json   the baked artifact — the ONLY thing the app reads
  lib/db.ts               seeds embedded PGlite from the artifact
  lib/queries.ts          typed SQL query layer
  app/…                   overview · reunifications · rulers · escalations · about
  components/Constellation.tsx   the node-link "constellation" visualization
```

## Regenerate the graph (the matching step)

The live LLM reviewer is the matcher. Run it from the repo's `pipeline/`:

```bash
cd pipeline
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env.local      # gitignored; never on the command line
uv run python -m pipeline.authority.claimgraph.build_graph                       # Anthropic (default)

# …or a cheaper OpenRouter reviewer (GLM 5.2). In a benchmark it matched Sonnet 5 on every
# throne-name-corroborated case and was stricter on name-only pairs — see the ADR-020 note.
echo 'OPENROUTER_API_KEY=sk-or-...' >> .env.local
uv run python -m pipeline.authority.claimgraph.build_graph --provider openrouter  # GLM 5.2
```

- Writes `web-claimgraph/data/claim-graph.json` (served) + `claim-graph.reviewer-run.jsonl`
  (the full reviewer interaction — incl. the model's reasoning — for replay, Constitutional Rule 13).
- **No key → the build STOPS** loudly; it will not silently fall back (that would ship a
  compromised graph). `meta.reviewer` records `llm` vs `deterministic`, `meta.provider`/`meta.model`
  record the backend, and the app shows a DRAFT banner whenever the data was not live-reviewed.
- Only prenomen/Horus-corroborated candidates cost a reviewer call; **name-only pairs are escalated
  deterministically without one** (see "What it demonstrates").
- Options: `--provider {anthropic,openrouter}`, `--model <id>`, `--limit N` (thin-slice),
  `--workers N`, `--fresh` (ignore the resume cache), `--deterministic` (explicit non-LLM mode).

## Run the app locally

```bash
cd web-claimgraph
pnpm install
pnpm dev        # http://localhost:3000
# or: pnpm build && pnpm start
```

## Deploy to Vercel

1. Set the **Root Directory** to `web-claimgraph`.
2. Framework preset: **Next.js**. No environment variables are required — the graph is baked
   into the committed artifact.
3. Deploy. (To ship a freshly-reviewed graph, run the generator above and commit the updated
   `data/claim-graph.json` first.)

## What it demonstrates

- **No cross-source collapse** — each source keeps its own `:Ruler` record; identity links are
  parallel claims, never a silent merge.
- **Precision-first matching** — name agreement alone never approves; a shared prenomen that is a
  known homonym (Menkheperre, Nebmaatre, Usermaatre, Neferkare, Sekhemre-\*) escalates rather than
  merges; no transitive auto-merge.
- **Name-only pairs need external evidence, not a model's word** — records that share only a name
  (no throne-name/Horus corroborator) are escalated **deterministically and never sent to the
  reviewer**: confirming an identity like `Usaphais` = Den requires a cited scholarly source added
  by a curator, because per Rule 1 "the model knows" is not a source.
- **Provenance everywhere** — every claim carries its scholar + page citation; every link is
  gated on an approved verdict and shows the reviewer's reasoning.
