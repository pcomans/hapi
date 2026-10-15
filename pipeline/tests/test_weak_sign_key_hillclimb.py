"""The weak-sign key's TLA hill-climb record (docs/evaluations/weak-sign-key-hillclimb/):
every committed result is rebuilt from its key snapshot, and the final snapshot is the
committed key."""

from __future__ import annotations

import ast
import importlib.util
import json
from functools import lru_cache
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "docs" / "evaluations" / "weak-sign-key-hillclimb"
KEYS = ("iteration-0", "iteration-1", "iteration-2", "iteration-3-rejected", "iteration-4-rejected")


@lru_cache(maxsize=1)
def harness():
    spec = importlib.util.spec_from_file_location("weak_sign_hillclimb", EVAL / "measure.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def rows() -> tuple[dict, ...]:
    return tuple(harness().tla_rows())


@pytest.mark.parametrize("key", KEYS)
def test_each_iterations_result_is_rebuilt_from_its_key(key: str) -> None:
    measured = {split: harness().measure(harness().load_key(EVAL / "keys" / f"{key}.py"), list(rows()), split)
                for split in ("train", "validation")}
    assert measured == json.loads((EVAL / "results" / f"{key}.json").read_text(encoding="utf-8"))


def test_the_test_split_scores_as_reported() -> None:
    committed = json.loads((EVAL / "results" / "test-final.json").read_text(encoding="utf-8"))
    assert set(committed) == {"iteration-0.py", "iteration-2.py"}
    for key, result in committed.items():
        assert harness().measure(harness().load_key(EVAL / "keys" / key), list(rows()), "test") == result
    assert (committed["iteration-0.py"]["recall"], committed["iteration-2.py"]["recall"]) == (0.7859, 0.8644)
    assert committed["iteration-0.py"]["strong_merges"] == committed["iteration-2.py"]["strong_merges"] == {
        "nkhr": ["njkꜣwḥrw", "njẖrt"]}


def test_the_accepted_iterations_meet_the_acceptance_rule_and_the_rejected_do_not() -> None:
    results = {k: json.loads((EVAL / "results" / f"{k}.json").read_text(encoding="utf-8")) for k in KEYS}

    def accepted(before: str, after: str) -> bool:
        b, a = results[before], results[after]
        return (a["train"]["recall"] > b["train"]["recall"]
                and a["validation"]["recall"] >= b["validation"]["recall"]
                and a["train"]["names_in_strong_merges"] <= b["train"]["names_in_strong_merges"]
                and a["validation"]["names_in_strong_merges"] <= b["validation"]["names_in_strong_merges"])

    assert accepted("iteration-0", "iteration-1") and accepted("iteration-1", "iteration-2")
    assert not accepted("iteration-2", "iteration-3-rejected")
    assert not accepted("iteration-2", "iteration-4-rejected")


def test_the_final_snapshot_is_the_committed_keys_code() -> None:
    def code(path: Path) -> str:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        tree.body = tree.body[1:]  # the module docstring
        return ast.dump(tree)
    assert code(EVAL / "keys" / "iteration-2.py") == code(REPO / "pipeline" / "pipeline" / "authority" / "weak_sign_skeleton.py")
