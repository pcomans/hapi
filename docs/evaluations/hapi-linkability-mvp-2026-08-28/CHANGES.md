# Changes after the 2026-08-28 deliverable

`SHA256SUMS` and `README.md` describe the deliverable as it was produced, at commit
`97f2e61`. They are not edited; a test checks every `SHA256SUMS` line against the file at
that commit.

## 2026-10-14: the scripts read their own repository

`run_linkability.py`, `inventory_inputs.py` and `validate_outputs.py` took their repository
root from `HAPI_ROOT`, defaulting to the devcontainer's checkout path. Later evaluations
load `run_linkability.py` as the resolver library, and a load without `HAPI_ROOT` read the
claim graph of whatever branch that checkout had out: an ad-hoc probe on 2026-10-14 read a
stale graph that way and reported a false ambiguity. The root is now the repository the
script is in; `HAPI_ROOT`, which callers still pass, must name that same repository, and
`run_linkability.py` refuses a `pipeline` package imported from another checkout, or the
script raises.

The README's run procedure is retired: it copies the scripts to `/tmp/hapi-linkability-mvp`,
where they no longer find a repository, and `validate_outputs.py` runs those copies and
rewrites `SHA256SUMS`. To reproduce the deliverable, run the README's procedure in a
worktree at `97f2e61`:

```bash
git worktree add /tmp/hapi-linkability-97f2e61 97f2e61
```

`run_linkability.py` stays usable as the resolver library from this repository, which is
how the later evaluations load it. `pipeline/tests/test_structure.py` keeps it so: no
tracked code names the checkout path, and each script's root is its own repository.
