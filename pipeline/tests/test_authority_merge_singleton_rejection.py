"""Tests for the singleton-admission cleanup (issue #114).

The 3-agent majority-vote merge architecture requires every committed row
to be corroborated by ≥2 agents. Each per-source `merge.py` was previously
admitting rows seen by only 1 agent, which silently bypassed the safety
model. This test sweep mechanically verifies that every authority-source
merge.py module:

1. Raises (rather than admitting) when the `len(present) < 2` branch
   triggers — per constitutional rule 2.
2. Has the unreachable `return None, 0` defensive dead-code removed
   from `_majority`.

Per constitutional rule 3 (deterministic enforcement over convention):
the rules are enforceable as tests, so they MUST be tests.

Approach: this is a STATIC source-text check. We collect every
`merge.py` under `pipeline/authority/sources/*/` that uses the
3-agent merge pattern (detected by the presence of the
`len(present) < 2` guard) and inspect its source. We do NOT exec the
merge modules — building synthetic 3-agent JSONL fixtures per source
would couple the test to each source's ID-shape vocabulary. The
text-level invariant is sufficient to catch regressions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

SOURCES_DIR = (
    Path(__file__).parent.parent
    / "pipeline"
    / "authority"
    / "sources"
)

# Marker the test sweep filters on. Every authority-source merge.py that
# implements the 3-agent majority-vote pattern contains this exact line;
# sources that don't (none today) are skipped.
SINGLETON_GUARD = "if len(present) < 2:"


def _all_source_dirs() -> Iterator[Path]:
    """Every source directory whose `merge.py` uses the 3-agent merge
    pattern (detected by the `len(present) < 2` guard)."""
    for src in sorted(SOURCES_DIR.iterdir()):
        merge = src / "merge.py"
        if not merge.is_file():
            continue
        text = merge.read_text()
        if SINGLETON_GUARD not in text:
            continue
        yield src


SOURCE_DIRS = list(_all_source_dirs())


@pytest.mark.parametrize(
    "source_dir",
    SOURCE_DIRS,
    ids=[d.name for d in SOURCE_DIRS],
)
def test_singleton_admission_raises(source_dir: Path) -> None:
    """Every merge.py raises (rather than admitting) when fewer than 2
    agents corroborate a row. Static text check on the body of the
    `if len(present) < 2:` block.
    """
    text = (source_dir / "merge.py").read_text()
    idx = text.find(SINGLETON_GUARD)
    # `_all_source_dirs` filters on the same marker, so this find always
    # succeeds. Defend explicitly against future drift in the filter so
    # an unexpected miss yields a clean test failure rather than ValueError.
    if idx < 0:
        pytest.fail(
            f"{source_dir.name}/merge.py: did not contain "
            f"{SINGLETON_GUARD!r} despite passing the source-dir filter"
        )
    # 600 chars is enough to cover the longest block + a margin.
    block = text[idx : idx + 600]
    assert "raise" in block, (
        f"{source_dir.name}/merge.py: `{SINGLETON_GUARD}` block does not "
        f"raise — must reject singleton rows per issue #114. Block:\n{block}"
    )
    # Reject the prior `final.append(present[0][1])` shape inside the
    # singleton-guard block specifically. We only inspect the first few
    # lines after the guard to avoid matching a legitimate
    # `final.append(merged)` further down in main().
    block_head = "\n".join(block.splitlines()[:8])
    assert "final.append" not in block_head, (
        f"{source_dir.name}/merge.py: `{SINGLETON_GUARD}` still admits "
        f"the row via final.append. Must raise instead per issue #114. "
        f"Block head:\n{block_head}"
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
