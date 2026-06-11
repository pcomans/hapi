"""Persist the full per-candidate reviewer interaction to disk (Rules 1 & 13).

Every LLM-backed reviewer/pick run writes one JSONL row per candidate — the exact
prompt, the model's full raw response, the returned model snapshot, the decision,
and the input context — to ``<output_dir>/<run_id>.jsonl``. The matcher run's D1
output node then carries that file's path + content sha256, so the recorded hash
is verifiable against a file that actually exists on disk (not a hash of discarded
in-memory data, which is unverifiable and therefore not provenance).

Rule 13: a decision you cannot replay from a stored request/response is not
reproducible. The committed default location is ``graph/reviewer_outputs/``; tests
pass a ``tmp_path`` so offline runs never write into the repo tree.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# Committed default location for real (live-LLM) runs.
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "reviewer_outputs"


def persist_reviewer_run(
    run_id: str, rows: list[dict], output_dir: Path | str
) -> tuple[str, str]:
    """Write ``rows`` to ``<output_dir>/<run_id>.jsonl``; return (path, sha256).

    ``path`` is relative to the repository root when possible (stable across
    machines); ``sha256`` is the digest of the exact bytes written, so the D1
    node's hash can be re-verified against the committed file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{run_id}.jsonl"
    text = "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows
    )
    path.write_text(text)
    digest = "sha256:" + hashlib.sha256(text.encode()).hexdigest()
    try:
        rel = path.resolve().relative_to(Path(__file__).resolve().parents[5])
        recorded = str(rel)
    except ValueError:
        recorded = str(path)
    return recorded, digest


def model_snapshot_from_rows(rows: list[dict]) -> str | None:
    """The single model snapshot across the run's rows, or None if none recorded.

    Raises if the rows disagree — a run must be one model snapshot (Rule 1: a
    mixed-snapshot run is not a reproducible decision).
    """
    snaps = {r["model_snapshot"] for r in rows if r.get("model_snapshot")}
    if len(snaps) > 1:
        raise ValueError(f"reviewer run recorded mixed model snapshots: {sorted(snaps)}")
    return next(iter(snaps), None)
