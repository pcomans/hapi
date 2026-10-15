"""The weak-sign key's hill-climb, protocol v2 (docs/evaluations/weak-sign-key-hillclimb/):
every committed result is rebuilt from its key snapshot with the frozen normalizer, the
acceptance rule is re-applied, and the committed key is v2-4: the protocol accepted v2-1, and
the project owner then dropped its c/q -> k rule."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from functools import lru_cache
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "docs" / "evaluations" / "weak-sign-key-hillclimb"
CANDIDATES = ("v2-1-j-weak-in-transliterations", "v2-2-z-as-s", "v2-3-tj-as-t", "v2-4-no-c-q-as-k")
FROZEN_NORMALIZER_SHA256 = "ca59b734db3f67511c9e58f16eaf8769e998c5e480d18c8be49a575390b16939"


@lru_cache(maxsize=1)
def harness():
    spec = importlib.util.spec_from_file_location("weak_sign_hillclimb_v2", EVAL / "measure.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def rows() -> tuple[dict, ...]:
    return tuple(harness().tla_rows())


def result(name: str) -> dict:
    return json.loads((EVAL / "results" / f"{name}.json").read_text(encoding="utf-8"))


def measured(name: str) -> dict:
    return harness().measure(harness().load_key(EVAL / "keys" / f"{name}.py"), list(rows()))


def test_the_normalizer_the_keys_are_measured_with_is_the_frozen_copy() -> None:
    assert hashlib.sha256((EVAL / "normalize_frozen.py").read_bytes()).hexdigest() == FROZEN_NORMALIZER_SHA256


def test_the_baseline_is_rebuilt() -> None:
    assert measured("v2-0-baseline") == result("v2-0-baseline")


@pytest.mark.parametrize("name", CANDIDATES)
def test_each_candidate_is_rebuilt_and_its_decision_follows_the_rule(name: str) -> None:
    committed = result(name)
    against, accepted = committed.pop("against"), committed.pop("accepted")
    assert measured(name) == committed
    assert harness().accepted(result(against) if against == "v2-0-baseline" else
                              {k: v for k, v in result(against).items() if k not in ("against", "accepted")},
                              committed) is accepted


def test_the_order_and_the_decisions() -> None:
    decisions = {n: (result(n)["against"], result(n)["accepted"]) for n in CANDIDATES}
    assert decisions == {
        "v2-1-j-weak-in-transliterations": ("v2-0-baseline", True),
        "v2-2-z-as-s": ("v2-1-j-weak-in-transliterations", False),
        "v2-3-tj-as-t": ("v2-1-j-weak-in-transliterations", False),
        "v2-4-no-c-q-as-k": ("v2-1-j-weak-in-transliterations", False),
    }
    assert [result(n)["strong_merges"]["names"] for n in ("v2-0-baseline", *CANDIDATES)] == [246, 244, 283, 263, 226]


def test_the_held_out_check_and_the_spent_test_split() -> None:
    held = json.loads((EVAL / "results" / "held-out-king-spellings.json").read_text(encoding="utf-8"))
    for name, committed in held.items():
        assert harness().held_out(harness().load_key(EVAL / "keys" / f"{name}.py")) == committed
    assert {n: (h["met"], h["pairs"]) for n, h in held.items()} == {
        "v2-0-baseline": (106, 206), "v2-1-j-weak-in-transliterations": (106, 206),
        "v2-4-no-c-q-as-k": (105, 206)}  # v2-4 scored after the owner's decision: reported, not chosen on
    tla_test = json.loads((EVAL / "results" / "tla-test-split-not-held-out.json").read_text(encoding="utf-8"))
    assert tla_test == {n: result(n)["splits"]["test"] for n in tla_test}
    assert {n: t["recall"] for n, t in tla_test.items()} == {
        "v2-0-baseline": 0.8264, "v2-1-j-weak-in-transliterations": 0.8646, "v2-4-no-c-q-as-k": 0.8583}


def test_the_committed_key_is_v2_4_by_the_project_owners_decision() -> None:
    """The protocol accepted v2-1. Its acceptance rule could not admit the removal C4 (removing
    a fold never raises recall); read as an addition, c/q → k fails the same rule (code review
    of the climb), and on 2026-10-15 the project owner dropped it. The committed key is v2-4."""
    def code(path: Path) -> str:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        tree.body = tree.body[1:]  # the module docstring
        return ast.dump(tree)
    assert code(EVAL / "keys" / "v2-4-no-c-q-as-k.py") == code(
        REPO / "pipeline" / "pipeline" / "authority" / "weak_sign_skeleton.py")
    v2_1, v2_4 = result("v2-1-j-weak-in-transliterations"), result("v2-4-no-c-q-as-k")
    for r in (v2_1, v2_4):
        r.pop("against"), r.pop("accepted")
    # c/q → k as an addition to v2-4 is v2-1, and the acceptance rule rejects it.
    assert harness().accepted(v2_4, v2_1) is False
    assert (v2_4["strong_merges"]["names"], v2_1["strong_merges"]["names"]) == (226, 244)


def test_the_live_normalizer_is_the_frozen_one() -> None:
    """The key is deployed with the live normalizer and was measured with the frozen copy; if
    the live one changes, the climb must be re-measured."""
    assert (REPO / "pipeline" / "pipeline" / "authority" / "claimgraph" / "normalize.py").read_bytes() == (
        EVAL / "normalize_frozen.py").read_bytes()
