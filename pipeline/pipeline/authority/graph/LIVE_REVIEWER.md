# Running the live stage-2 reviewer

The stage-2 LLM reviewer (ADR-018 schema 4b) makes real Anthropic API calls. It
is fully wired and gated solely on `ANTHROPIC_API_KEY`.

## Setup (once, in the environment configuration)

Claude Code on the web has **no dedicated secrets store** — environment variables
are stored in the environment configuration and are *visible to anyone who can
edit that environment*. Add the key there (NOT in chat, NOT committed), in
`.env` format, no quotes:

```
ANTHROPIC_API_KEY=sk-ant-...
```

`ANTHROPIC_BASE_URL` is already `https://api.anthropic.com`, so a standard key
works as-is. Use a key you can scope/rotate, given the visibility caveat.

## Important: start a fresh session

Environment variables are injected when the **container starts**. A session that
was already running when you added the variable will NOT see it — start a new web
session (or `--teleport`) on this branch so the key is present in `os.environ`.

## Run it

```bash
cd pipeline
uv run python -m pipeline.authority.graph.live_review        # prints verdicts + escalations
uv run pytest tests/test_authority_graph/test_live_reviewer_integration.py -q   # now runs (was skipped)
```

Without the key both paths fail loud / skip — no silent fallback
(Constitutional rule 2). The harness's Claude Code OAuth token is deliberately
NOT repurposed for direct API calls.

## What you get vs the curator path

The curator-approval path (`build_poc_graph()`) proves verdict gating end-to-end
without any API calls. The live path (`build_poc_graph_live()`) additionally
produces **faithful CRMdig provenance**: the reviewer `:D14` records the actual
returned `model_snapshot`, and verdict-E13s carry real `:D10` run metadata —
exactly as ADR case-4b specifies.

## Cost note

One API call per stage-1 candidate (11 on the Leprohon+Beckerath slice —
trivial). If the slice is widened to more sources the candidate count grows;
add batching before running at scale.
