"""Cross-museum connections over a run's links, with the authority switched on or off (#338 step 3).

Two records of different museums are connected when a link of each joins it to the same target.
The switch is the mode whose links are read (`authority_links.MODES`): `authority` connects
through the authority's targets, `literal` through plain text, as #337 and #361 compared them.
This is the measurement; no deployed matcher reads these links yet (matching is the web query
layer's, ADR-008).

`report` measures both modes on one run and what changes between them, by museum, museum pair
and entity type. A record of museum A is *connected* in a pair (A, B) and entity type when it has
a link of that type to a target that also has a record of B. The measures are counts: which
records the authority connects that plain text does not (`gained`), and the reverse (`lost`).
Whether a connection is right is what the evaluations reviewed; a scope's `qualified` flag says
whether one found the authority's changes there to be better (`QUALIFIED_SCOPES`), and an
unqualified scope's changes are unevaluated, not proven. The flag is policy: it does not say the
review saw the population measured. Whoever reports a run says which connected records the
review did not see (`run_end_to_end.py`, `scope_status`).
"""

from __future__ import annotations

import collections
from pathlib import Path

from pipeline.enrich import authority_links, link_files

MUSEUMS = tuple(sorted({m for pair in authority_links.MUSEUM_PAIRS for m in pair}))
TOP = (1, 5)


def load_links(run: Path, mode: str) -> list[dict]:
    if mode not in authority_links.MODES:
        raise ValueError(f"unknown mode: {mode}")
    links = link_files.read_rows(run / f"links-{mode}.ndjson.gz")
    unknown = {l["museum"] for l in links} - set(MUSEUMS)
    if unknown:
        raise ValueError(f"{run}: links of museums no pair covers: {sorted(unknown)}")
    return links


def target_records(links: list[dict]) -> dict[tuple[str, str], dict[str, set[str]]]:
    """The records each (entity type, target) is linked from, by museum."""
    out: dict[tuple[str, str], dict[str, set[str]]] = collections.defaultdict(lambda: collections.defaultdict(set))
    for link in links:
        out[(link["entity_type"], link["target_id"])][link["museum"]].add(link["artifact_id"])
    return out


def connected(by_target: dict[tuple[str, str], dict[str, set[str]]]) -> dict[tuple[str, str, str], dict]:
    """For each (entity type, museum A, museum B): the shared targets and the records of A
    connected to B."""
    out: dict[tuple[str, str, str], dict] = collections.defaultdict(lambda: {"targets": set(), "records": set()})
    for (entity, target), sides in by_target.items():
        for a in sides:
            for b in sides:
                if a != b:
                    out[(entity, a, b)]["targets"].add(target)
                    out[(entity, a, b)]["records"] |= sides[a]
    return out


def top_targets(by_target: dict, targets: set[str], entity: str, museum: str) -> dict:
    """The largest 1 and 5 shared targets on one side (by records, ties by target id) and the
    share of the side's connected records they carry."""
    sized = sorted(((len(by_target[(entity, t)][museum]), t) for t in targets), key=lambda x: (-x[0], x[1]))
    total = set().union(*(by_target[(entity, t)][museum] for t in targets)) if targets else set()
    out = {}
    for k in TOP:
        chosen = [t for _, t in sized[:k]]
        union = set().union(*(by_target[(entity, t)][museum] for t in chosen)) if chosen else set()
        out[str(k)] = {"target_ids": chosen, "share": round(len(union) / len(total), 4) if total else None}
    return out


def report(run: Path) -> dict:
    """Both modes on one run."""
    link_files.verify_run(run)
    links = {mode: load_links(run, mode) for mode in authority_links.MODES}
    by_target = {mode: target_records(links[mode]) for mode in authority_links.MODES}
    state = {mode: connected(by_target[mode]) for mode in authority_links.MODES}
    empty = {"targets": set(), "records": set()}
    pairs = {}
    for entity in authority_links.RESOLVED_TYPES:
        for pair in authority_links.MUSEUM_PAIRS:
            sides = {}
            for a, b in (pair, pair[::-1]):
                on, off = state["authority"].get((entity, a, b), empty), state["literal"].get((entity, a, b), empty)
                sides[a] = {
                    "connected_authority": len(on["records"]), "connected_literal": len(off["records"]),
                    "gained": len(on["records"] - off["records"]), "lost": len(off["records"] - on["records"]),
                }
            targets = {mode: state[mode].get((entity, *pair), empty)["targets"] for mode in authority_links.MODES}
            pairs[f"{entity}|{pair[0]}|{pair[1]}"] = {
                "qualified": pair in authority_links.QUALIFIED_SCOPES[entity],
                "shared_targets_authority": len(targets["authority"]),
                "shared_targets_literal": len(targets["literal"]),
                "shared_target_ids": {mode: sorted(targets[mode]) for mode in authority_links.MODES},
                "records": sides,
                "top_targets": {mode: {museum: top_targets(by_target[mode], targets[mode], entity, museum)
                                       for museum in pair}
                                for mode in authority_links.MODES},
            }
    museums = {}
    for museum in MUSEUMS:
        for entity in authority_links.RESOLVED_TYPES:
            row = {}
            for mode in authority_links.MODES:
                linked = {l["artifact_id"] for l in links[mode] if l["museum"] == museum and l["entity_type"] == entity}
                to_others = set().union(*(state[mode].get((entity, museum, b), empty)["records"]
                                          for b in MUSEUMS if b != museum))
                row[mode] = {"linked_records": len(linked), "connected_records": len(to_others)}
            museums[f"{museum}|{entity}"] = row
    # #337's headline measure: a museum's records on a target shared with any other museum, any
    # entity type.
    any_type = {mode: {museum: len(set().union(*(state[mode].get((entity, museum, b), empty)["records"]
                                                 for entity in authority_links.RESOLVED_TYPES
                                                 for b in MUSEUMS if b != museum)))
                       for museum in MUSEUMS}
                for mode in authority_links.MODES}
    return {"by_museum_pair": pairs, "by_museum": museums, "records_on_shared_targets_any_type": any_type}
