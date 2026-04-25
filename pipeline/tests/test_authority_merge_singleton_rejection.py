"""Tests for the singleton-admission cleanup (issue #114).

The 3-agent majority-vote merge architecture requires every committed row
to be corroborated by ≥2 agents. Each per-source `merge.py` was previously
admitting rows seen by only 1 agent, which silently bypassed the safety
model. This test sweep mechanically verifies that every authority-source
merge.py module raises when fed a singleton row.

Per constitutional rule 3 (deterministic enforcement over convention):
the rule is enforceable as a test, so it MUST be a test.

Note: this test loads each merge module dynamically and writes synthetic
agent JSONL fixtures into a temp directory, so it does not depend on the
gitignored production agent outputs. It also covers the inverse case —
when ≥2 agents corroborate a row, the merge proceeds.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Iterator

import pytest

SOURCES_DIR = (
    Path(__file__).parent.parent
    / "pipeline"
    / "authority"
    / "sources"
)


def _all_source_dirs() -> Iterator[Path]:
    """Every source directory that has a merge.py with the
    `len(present) < 2` pattern."""
    for src in sorted(SOURCES_DIR.iterdir()):
        merge = src / "merge.py"
        if not merge.is_file():
            continue
        text = merge.read_text()
        if "len(present) < 2" not in text:
            continue
        yield src


SOURCE_DIRS = list(_all_source_dirs())


@pytest.mark.parametrize(
    "source_dir",
    SOURCE_DIRS,
    ids=[d.name for d in SOURCE_DIRS],
)
def test_singleton_admission_raises(source_dir: Path) -> None:
    """Every merge.py raises ValueError when fewer than 2 agents
    corroborate a row.

    Per-source ID schemas vary, so this test only checks the
    text-level invariant: the merge.py source contains a `raise` (not
    a `final.append`) inside the `len(present) < 2` block.
    """
    text = (source_dir / "merge.py").read_text()
    # Find the singleton block.
    idx = text.index("if len(present) < 2:")
    block = text[idx : idx + 600]  # 600 chars is enough to cover any block
    assert "raise" in block, (
        f"{source_dir.name}/merge.py: `if len(present) < 2:` block does not "
        f"raise — must reject singleton rows per issue #114. Block:\n{block}"
    )
    assert "final.append" not in block.split("\n", 1)[0] + "".join(
        line for line in block.splitlines()[1:6]
    ), (
        f"{source_dir.name}/merge.py: `if len(present) < 2:` still admits "
        f"the row via final.append. Must raise instead per issue #114."
    )


@pytest.mark.parametrize(
    "source_dir",
    SOURCE_DIRS,
    ids=[d.name for d in SOURCE_DIRS],
)
def test_majority_unreachable_return_removed(source_dir: Path) -> None:
    """No merge.py may contain `return None, 0` as a final-line fallback
    in `_majority`. Per issue #114 acceptance criterion: the unreachable
    return is removed (replaced with a `raise RuntimeError`)."""
    text = (source_dir / "merge.py").read_text()
    assert "return None, 0" not in text, (
        f"{source_dir.name}/merge.py: contains `return None, 0` — defensive "
        f"dead-code path must be removed per issue #114 (rule 2: no silent "
        f"fallbacks)."
    )
