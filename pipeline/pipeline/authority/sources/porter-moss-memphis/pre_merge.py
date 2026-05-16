"""Pre-merge tomb_id corrections runner for the porter-moss-memphis source.

Applies committed `tomb_id_corrections-<chunk>.json` files to the gitignored
`raw/agent-{a,b,c}-<chunk>.jsonl` files BEFORE `merge.py` consumes them.

Why this exists: a single extraction agent may apply an OCR-drift rule
incorrectly on one row (e.g. dropping a `[II]` regnal-number bracket
that pypdf rendered as `Il1`), producing a non-canonical `tomb_id`. The
other two agents converged on the canonical form, so the row's
`tomb_id` SHOULD be the canonical form via 2/1 majority — but merge.py's
singleton-rejection (constitutional rule 2) flags the mis-OCR'd 1/3 row
as a singleton and raises. Without this pre-merge step the only way to
recover would be hand-resolving (silently editing the agent JSONL), which
the Gemini PR #218 P1.1 review flagged as "manufacturing fake unanimity,
no audit trail." This script makes the manufacturing explicit: each
correction has a committed JSON rationale citing the printed source, and
the deterministic applier rewrites the agent JSONLs reproducibly.

Mirrors the `dodson-hilton-queens` PR #218 pre_merge precedent. Per-chunk
scoping ensures corrections do NOT cross-apply: only the matching
`tomb_id_corrections-<chunk>.json` fires on `agent-<tag>-<chunk>.jsonl`.

Each correction sets BOTH `tomb_id` and `occupant_name` (the typical
pattern when an OCR drift on a regnal-number bracket drops both the
descriptor-form suffix AND the occupant-name regnal numeral).

Idempotent: re-running on already-corrected agent files is a no-op
because the canonical tomb_id is not a key in the corrections map.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/porter-moss-memphis/pre_merge.py
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
DEFAULT_AGENT_DIR = SOURCE_DIR / "raw"


def _load_corrections() -> dict[str, dict[tuple[str, str], dict[str, str]]]:
    """Load `tomb_id_corrections-<chunk>.json` files keyed by chunk name.

    Returns `{chunk_name: {(agent_tag, wrong_tomb_id): {canonical_tomb_id, canonical_occupant_name, rationale}}}`.
    """
    by_chunk: dict[str, dict[tuple[str, str], dict[str, str]]] = {}
    for json_path in sorted(SOURCE_DIR.glob("tomb_id_corrections-*.json")):
        chunk = json_path.stem.removeprefix("tomb_id_corrections-")
        if not chunk or chunk == json_path.stem:
            raise ValueError(
                f"pre_merge: cannot parse chunk name from {json_path.name!r}; "
                f"expected `tomb_id_corrections-<chunk>.json`"
            )
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(
                f"pre_merge: {json_path} top-level must be a dict; "
                f"got {type(raw).__name__}"
            )
        chunk_corrections: dict[tuple[str, str], dict[str, str]] = {}
        for key, value in raw.items():
            if key.startswith("_"):
                continue
            if "|" not in key:
                raise ValueError(
                    f"pre_merge: {json_path} key {key!r} missing '|' "
                    f"separator (expected '<agent_tag>|<wrong_tomb_id>')"
                )
            tag, wrong = key.split("|", 1)
            if not tag or not wrong:
                raise ValueError(
                    f"pre_merge: {json_path} key {key!r} has empty agent_tag "
                    f"or wrong_tomb_id"
                )
            required = {"canonical_tomb_id", "canonical_occupant_name", "rationale"}
            if not isinstance(value, dict) or not required.issubset(value.keys()):
                raise ValueError(
                    f"pre_merge: {json_path} key {key!r} value must be a dict "
                    f"with {sorted(required)} keys"
                )
            chunk_corrections[(tag, wrong)] = value
        by_chunk[chunk] = chunk_corrections
    return by_chunk


def _parse_agent_filename(stem: str) -> tuple[str, str] | None:
    """Parse `agent-<tag>-<chunk>` from a JSONL stem.

    Returns `(tag, chunk)` or `None` for malformed / unsuffixed filenames.
    """
    parts = stem.split("-", 2)
    if len(parts) < 3 or parts[0] != "agent":
        return None
    tag, chunk = parts[1], parts[2]
    if not tag or not chunk:
        return None
    return tag, chunk


def apply_corrections(agent_dir: Path) -> dict[str, int]:
    """Apply chunk-scoped corrections to each `agent-<tag>-<chunk>.jsonl`.

    Atomic write-and-replace via `os.replace()` so an interrupted run
    cannot leave the agent JSONL in a corrupted or empty state.
    """
    by_chunk = _load_corrections()
    counts: dict[str, int] = {}
    for jsonl_path in sorted(agent_dir.glob("agent-*.jsonl")):
        parsed = _parse_agent_filename(jsonl_path.stem)
        if parsed is None:
            continue
        tag, chunk = parsed
        chunk_corrections = by_chunk.get(chunk)
        if chunk_corrections is None:
            counts[jsonl_path.name] = 0
            continue
        rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        patched = 0
        for row in rows:
            key = (tag, row["tomb_id"])
            if key in chunk_corrections:
                spec = chunk_corrections[key]
                row["tomb_id"] = spec["canonical_tomb_id"]
                row["occupant_name"] = spec["canonical_occupant_name"]
                patched += 1
        if patched:
            temp_path = jsonl_path.with_suffix(jsonl_path.suffix + ".tmp")
            # `sort_keys=True` mirrors the extraction-prompt instruction
            # (`json.dumps(..., sort_keys=True, ensure_ascii=False)`); ensures
            # byte-deterministic re-writes on re-runs. Per Gemini PR #222
            # round-1 inline review.
            temp_path.write_text(
                "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows) + "\n",
                encoding="utf-8",
            )
            os.replace(temp_path, jsonl_path)
        counts[jsonl_path.name] = patched
    return counts


def main(agent_dir: Path) -> None:
    counts = apply_corrections(agent_dir)
    total = sum(counts.values())
    print(f"pre_merge: applied {total} tomb_id correction(s) across {len(counts)} agent files")
    for filename, n in sorted(counts.items()):
        if n:
            print(f"  {filename}: {n}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent-dir",
        type=Path,
        default=Path(os.environ.get("PM_MEMPHIS_AGENT_DIR", DEFAULT_AGENT_DIR)),
        help=f"Directory containing agent-*.jsonl (default: {DEFAULT_AGENT_DIR}).",
    )
    args = parser.parse_args()
    main(args.agent_dir)
