"""Cross-museum matching over a run's links, with the authority switched on or off (#338 step 3).

Two records of different museums match when a link of each joins it to the same target. The
switch is the mode whose links are read (`authority_links.MODES`): `authority` matches through
the authority's targets, `literal` through plain text, as #337 and #361 compared them.

`report` measures both modes on one run and what changes between them, by museum, museum pair
and entity type. A record of museum A is *connected* in a pair (A, B) and entity type when it
has a link of that type to a target that also has a record of B. The measures are counts: which
records the authority connects that plain text does not (`gained`), and the reverse (`lost`).
Whether a connection is right is what the evaluations reviewed; a scope's `qualified` flag says
whether one found the authority's changes there to be better (`QUALIFIED_SCOPES`), and an
unqualified scope's changes are unevaluated, not proven.
"""

from __future__ import annotations

import collections
from pathlib import Path

from pipeline.enrich import authority_links, link_files

MUSEUMS = ("met", "brooklyn", "harvard")


def load_links(run: Path, mode: str) -> list[dict]:
    if mode not in authority_links.MODES:
        raise ValueError(f"unknown mode: {mode}")
    return link_files.read_rows(run / f"links-{mode}.ndjson.gz")


def target_records(links: list[dict]) -> dict[tuple[str, str], dict[str, set[str]]]:
    """The records each (entity type, target) is linked from, by museum."""
    out: dict[tuple[str, str], dict[str, set[str]]] = collections.defaultdict(lambda: collections.defaultdict(set))
    for link in links:
        out[(link["entity_type"], link["target_id"])][link["museum"]].add(link["artifact_id"])
    return out


def matches(links: list[dict], artifact_id: str) -> dict[str, list[dict]]:
    """A record's matches in the other museums, by entity type: each the target and the records
    of another museum linked to it."""
    by_target = target_records(links)
    own = [l for l in links if l["artifact_id"] == artifact_id]
    out: dict[str, list[dict]] = collections.defaultdict(list)
    for link in sorted(own, key=lambda l: (l["entity_type"], l["target_id"])):
        others = {museum: sorted(records) for museum, records in by_target[(link["entity_type"], link["target_id"])].items()
                  if museum != link["museum"]}
        if others:
            out[link["entity_type"]].append({"target_id": link["target_id"], "records": others})
    return dict(out)


def connected(links: list[dict]) -> dict[tuple[str, str, str], dict]:
    """For each (entity type, museum A, museum B): the shared targets and the records of A
    connected to B."""
    by_target = target_records(links)
    out: dict[tuple[str, str, str], dict] = collections.defaultdict(lambda: {"targets": set(), "records": set()})
    for (entity, target), sides in by_target.items():
        for a in sides:
            for b in sides:
                if a != b:
                    out[(entity, a, b)]["targets"].add(target)
                    out[(entity, a, b)]["records"] |= sides[a]
    return out


def top_share(by_target: dict, targets: set[str], entity: str, museum: str) -> dict:
    sized = sorted(((len(by_target[(entity, t)][museum]), t) for t in targets), key=lambda x: (-x[0], x[1]))
    total = set().union(*(by_target[(entity, t)][museum] for t in targets)) if targets else set()
    out = {}
    for k in (1, 5):
        union = set().union(*(by_target[(entity, t)][museum] for _, t in sized[:k])) if sized else set()
        out[str(k)] = round(len(union) / len(total), 4) if total else None
    return out


def report(run: Path) -> dict:
    links = {mode: load_links(run, mode) for mode in authority_links.MODES}
    state = {mode: connected(links[mode]) for mode in authority_links.MODES}
    by_target = {mode: target_records(links[mode]) for mode in authority_links.MODES}
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
            on_targets = state["authority"].get((entity, *pair), empty)["targets"]
            off_targets = state["literal"].get((entity, *pair), empty)["targets"]
            pairs[f"{entity}|{pair[0]}|{pair[1]}"] = {
                "qualified": pair in authority_links.QUALIFIED_SCOPES[entity],
                "shared_targets_authority": len(on_targets), "shared_targets_literal": len(off_targets),
                "records": sides,
                # How concentrated the connections are: the share of each side's connected records
                # that the largest 1 and 5 shared targets carry (#337's concentration measure).
                "top_target_share": {mode: {museum: top_share(by_target[mode], targets, entity, museum)
                                            for museum in pair}
                                     for mode, targets in (("authority", on_targets), ("literal", off_targets))},
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
    totals = {entity: {mode: sum(museums[f"{m}|{entity}"][mode]["connected_records"] for m in MUSEUMS)
                       for mode in authority_links.MODES}
              for entity in authority_links.RESOLVED_TYPES}
    return {"by_museum_pair": pairs, "by_museum": museums, "connected_records_by_entity_type": totals}
