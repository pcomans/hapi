"""The production resolver (#338) is the evaluations' linkability adapter, promoted: the same
targets, indexes and catalogs, and the same answer for every ruler, site and tomb label the
authority holds and for variants of them. (`docs/evaluations/authority-bridge-338/results/
promotion-check.json` holds the same on every site and tomb mention of the frozen corpus.)"""

from __future__ import annotations

import json

import pytest

from pipeline.authority import resolver
from pipeline.authority.graph_kings import load_linkability


@pytest.fixture(scope="module")
def adapter():
    return load_linkability()


@pytest.fixture(scope="module")
def graph() -> dict:
    return json.loads(resolver.GRAPH.read_text(encoding="utf-8"))


def variants(label: str) -> list[str]:
    """The label, and renderings the normalized tier is for: case, spacing, hyphens, accents."""
    return [label, label.upper(), f"  {label}  ", label.replace("-", " "), label.replace(" ", "-"),
            label.replace("e", "é"), label + " II"]


def test_the_paths_are_the_adapters(adapter) -> None:
    assert (resolver.GRAPH, resolver.IDAI, resolver.PM_THEBAN, resolver.PM_MEMPHIS) == (
        adapter.GRAPH, adapter.IDAI, adapter.PM_THEBAN, adapter.PM_MEMPHIS)
    assert resolver.NAME_PREDICATES == adapter.NAME_PREDICATES


def test_the_ruler_resolver_is_the_adapters(adapter, graph) -> None:
    ours, our_catalog = resolver.build_ruler_resolver(graph)
    theirs, their_catalog = adapter.build_ruler_resolver(graph)
    assert our_catalog == their_catalog and len(our_catalog) > 800
    assert (dict(ours.exact), dict(ours.normalized)) == (dict(theirs.exact), dict(theirs.normalized))
    labels = sorted({label for claim in graph["claims"] if claim["predicate"] in resolver.NAME_PREDICATES
                     for label in (claim.get("value_text"), claim.get("value_translit")) if label}
                    | {r["display_name"] for r in graph["rulers"]})
    assert len(labels) > 3000
    for label in labels:
        for text in variants(label):
            assert ours.resolve(text, resolver.ruler_norm) == theirs.resolve(text, adapter.ruler_norm), text


def test_the_site_resolver_is_the_adapters(adapter) -> None:
    rows = resolver.load_jsonl(resolver.IDAI)
    ours, our_catalog = resolver.build_site_resolver(rows)
    theirs, their_catalog = adapter.build_site_resolver(adapter.load_jsonl(adapter.IDAI))
    assert our_catalog == their_catalog and len(our_catalog) == 1000
    labels = sorted({label for r in rows if r.get("kind") == "site" for label in (r["display"], *(r.get("alt_labels") or []))})
    for label in labels:
        for text in variants(label):
            assert ours.resolve(text, resolver.place_norm_set) == theirs.resolve(text, adapter.place_norm_set), text


def test_the_tomb_resolver_is_the_adapters(adapter) -> None:
    ours, our_catalog = resolver.build_pm_resolver()
    theirs, their_catalog = adapter.build_pm_resolver()
    assert our_catalog == their_catalog and len(our_catalog) > 1000
    assert (dict(ours.exact), dict(ours.normalized)) == (dict(theirs.exact), dict(theirs.normalized))
    labels = sorted({label for path in (resolver.PM_THEBAN, resolver.PM_MEMPHIS) for r in resolver.load_jsonl(path)
                     for label in (r["tomb_id"], *(r.get("tomb_aliases") or []))})
    for label in labels:
        for text in variants(label):
            assert ours.resolve(text, resolver.place_norm_set) == theirs.resolve(text, adapter.place_norm_set), text


def test_a_resolution_is_exact_first_then_normalized_and_counts_its_targets() -> None:
    r = resolver.Resolver()
    r.add(resolver.Target("a", "Thebes", "site", "x"), ["Thebes", "Luxor"], resolver.place_norm_set)
    r.add(resolver.Target("b", "Thebes (Boeotia)", "site", "x"), ["Thebes (Boeotia)", "LUXOR"], resolver.place_norm_set)
    assert r.resolve("Thebes", resolver.place_norm_set) == {
        "raw_exact_status": "unique", "raw_exact_target_ids": ["a"], "normalized_keys": ["thebes"],
        "resolution_method": "raw_exact", "status": "resolved", "target_ids": ["a"]}
    assert r.resolve("thebes  (boeotia)", resolver.place_norm_set) == {
        "raw_exact_status": "unique", "raw_exact_target_ids": ["b"], "normalized_keys": ["thebesboeotia"],
        "resolution_method": "raw_exact", "status": "resolved", "target_ids": ["b"]}
    assert r.resolve("Thébes-Boeotia", resolver.place_norm_set) == {
        "raw_exact_status": "unmatched", "raw_exact_target_ids": [], "normalized_keys": ["thebesboeotia"],
        "resolution_method": "committed_normalized", "status": "resolved", "target_ids": ["b"]}
    assert r.resolve("Luxor", resolver.place_norm_set) == {
        "raw_exact_status": "ambiguous", "raw_exact_target_ids": ["a", "b"], "normalized_keys": ["luxor"],
        "resolution_method": "raw_exact", "status": "ambiguous", "target_ids": ["a", "b"]}
    assert r.resolve("Karnak", resolver.place_norm_set) == {
        "raw_exact_status": "unmatched", "raw_exact_target_ids": [], "normalized_keys": ["karnak"],
        "resolution_method": None, "status": "unmatched", "target_ids": []}
