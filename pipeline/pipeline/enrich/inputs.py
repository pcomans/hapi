"""The inputs of an authority-links run must be the normalize step's output for the raw rows read (#338).

A run reads the canonical records and the raw payloads they were normalized from. The ingest
assets commit raw rows batch by batch and the normalize assets write canonical rows later, so
tables read while either is running can pair a new raw payload with an old canonical row, or hold
raw rows not yet normalized; one database snapshot does not prevent that. `check_inputs`
refuses such inputs: every canonical row must be exactly what its museum's normalize step makes
of its raw payload (its mapper's row, of a payload the step keeps), and every raw row the step
keeps must have its canonical row. That is what is checked; whether the raw rows read are a
complete ingest is not (a half re-ingested raw table, fully normalized, passes). A refused run
fails; nothing retries it, and the operator re-materializes it once upstream is done (in a job
with the normalize assets, `deps` already orders it after them). With the code recorded in
`docs/evaluations/authority-bridge-338/results/promotion-check.json` (`check_inputs.code_sha256`),
all 36,245 canonical rows of the frozen corpus of 2026-08-27 passed; after an edit to a mapper or
the canonical model, that holds only once the check is re-run.
"""

from __future__ import annotations

from collections.abc import Callable

from pipeline.assets.normalize.brooklyn import BrooklynMapper, is_egyptian
from pipeline.assets.normalize.harvard import HarvardMapper
from pipeline.assets.normalize.met import MetMapper

# Each museum's mapper, and the rule its normalize asset keeps a raw record by (None: all).
NORMALIZERS: dict[str, tuple[type, Callable[[dict], bool] | None]] = {
    "met": (MetMapper, None),
    "brooklyn": (BrooklynMapper, is_egyptian),
    "harvard": (HarvardMapper, None),
}
SHOWN = 5


def normalized(raw_indexes: dict[str, dict[str, dict]]) -> list[dict]:
    """The canonical rows the normalize assets make of these raw payloads."""
    rows = []
    for museum, payloads in sorted(raw_indexes.items()):
        mapper, keep = NORMALIZERS[museum]
        rows += [mapper().map_to_canonical(p).model_dump() for _, p in sorted(payloads.items()) if keep is None or keep(p)]
    return rows


def check_inputs(canonical: list[dict], raw_indexes: dict[str, dict[str, dict]]) -> None:
    if set(raw_indexes) != set(NORMALIZERS):
        raise ValueError(f"raw payloads of {sorted(raw_indexes)}, not of every normalized museum {sorted(NORMALIZERS)}")
    stale, orphaned = [], []
    seen: dict[str, set[str]] = {museum: set() for museum in NORMALIZERS}
    mappers = {museum: mapper() for museum, (mapper, _) in NORMALIZERS.items()}
    for row in canonical:
        museum, source_id = row["source_museum"], row["source_id"]
        seen[museum].add(source_id)
        payload = raw_indexes[museum].get(source_id)
        keep = NORMALIZERS[museum][1]
        if payload is None:
            orphaned.append(row["id"])
        elif (keep is not None and not keep(payload)) or mappers[museum].map_to_canonical(payload).model_dump() != row:
            stale.append(row["id"])
    pending = sorted(f"{museum}:{source_id}" for museum, (_, keep) in NORMALIZERS.items()
                     for source_id, payload in raw_indexes[museum].items()
                     if source_id not in seen[museum] and (keep is None or keep(payload)))
    problems = []
    if stale:
        problems.append(f"{len(stale)} canonical rows are not what the normalize step makes of their raw payload "
                        f"(e.g. {sorted(stale)[:SHOWN]})")
    if orphaned:
        problems.append(f"{len(orphaned)} canonical rows have no raw payload (e.g. {sorted(orphaned)[:SHOWN]})")
    if pending:
        problems.append(f"{len(pending)} raw rows are not normalized yet (e.g. {pending[:SHOWN]})")
    if problems:
        raise ValueError("the canonical rows are not the normalize step's output for the raw rows read "
                         "(ingest or normalize mid-run?): "
                         + "; ".join(problems))
