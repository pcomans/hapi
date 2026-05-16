"""Pre-merge corrections runner for the dodson-hilton-queens source.

Applies committed `dh_id_corrections-<chunk>.json` files to the gitignored
`raw/agent-{a,b,c}-<chunk>.jsonl` files BEFORE `merge.py` consumes them.

Why this exists: chunks that use the direct-PDF-Read method deviation (where
the 3 extraction agents call `Read(file_path='raw/source-pNNN-pMMM.pdf',
pages='1-K')` instead of consuming an intermediate Gemini-OCR'd `chunk-*.md`
file) cannot use the `transform_<chunk>.py` pre-extraction text-rewriter
pattern that the OCR-to-markdown chunks use, because there is no markdown
chunk file to rewrite.

Instead, the canonicalization step shifts to AFTER agent extraction and
BEFORE merge: any agent that produced a non-canonical `dh_id` (typically
from a localized OCR-drift on the headword's bold-italic styling — dropped
suffix, dropped J-prefix, dropped middle-letter inside a bracket-lacuna
pattern) is rewritten to the source-verified canonical form. The
corrections JSON is the committed audit trail; this script is the
deterministic applier. Constitutional rule 1 (every fact traces to a
documented source on disk) is satisfied because each correction in the
JSON carries a rationale string with a printed-source citation.

Idempotent: re-running on already-corrected agent files is a no-op
because the canonical dh_id is not a key in the corrections map.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/dodson-hilton-queens/pre_merge.py
    PM_AGENT_DIR=/some/path uv run python \\
        pipeline/authority/sources/dodson-hilton-queens/pre_merge.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
DEFAULT_AGENT_DIR = SOURCE_DIR / "raw"


def _load_corrections() -> dict[str, dict[tuple[str, str], dict[str, str]]]:
    """Load `dh_id_corrections-<chunk>.json` files keyed by chunk name.

    Returns `{chunk_name: {(agent_tag, wrong_dh_id): {canonical_dh_id, rationale}}}`.
    The chunk name is parsed from the filename suffix (e.g.
    `dh_id_corrections-ofkingsandpriests.json` → chunk `ofkingsandpriests`).

    Per-chunk scoping (Gemini PR #218 round-2) ensures corrections do NOT
    cross-apply: if a future chunk happens to share a wrong-spelling string
    with this chunk, only the matching chunk's corrections fire on that
    chunk's agent files.

    Each correction is keyed by `'<agent_tag>|<wrong_dh_id>'` inside the
    file. Top-level keys starting with `_` (e.g. `_doc`) are loader
    directives and skipped.
    """
    by_chunk: dict[str, dict[tuple[str, str], dict[str, str]]] = {}
    for json_path in sorted(SOURCE_DIR.glob("dh_id_corrections-*.json")):
        chunk = json_path.stem.removeprefix("dh_id_corrections-")
        if not chunk or chunk == json_path.stem:
            raise ValueError(
                f"pre_merge: cannot parse chunk name from {json_path.name!r}; "
                f"expected `dh_id_corrections-<chunk>.json`"
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
                    f"separator (expected '<agent_tag>|<wrong_dh_id>')"
                )
            tag, wrong = key.split("|", 1)
            if not tag or not wrong:
                raise ValueError(
                    f"pre_merge: {json_path} key {key!r} has empty agent_tag "
                    f"or wrong_dh_id"
                )
            if not isinstance(value, dict) or "canonical_dh_id" not in value or "rationale" not in value:
                raise ValueError(
                    f"pre_merge: {json_path} key {key!r} value must be a dict "
                    f"with 'canonical_dh_id' and 'rationale' keys"
                )
            chunk_corrections[(tag, wrong)] = value
        by_chunk[chunk] = chunk_corrections
    return by_chunk


def _parse_agent_filename(stem: str) -> tuple[str, str] | None:
    """Parse `agent-<tag>-<chunk>` from a JSONL stem.

    Returns `(tag, chunk)` or `None` for malformed / unsuffixed filenames.
    Bare `agent-<tag>.jsonl` (single-chunk legacy form) returns None and is
    skipped — those files have no per-chunk corrections file.
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

    Only corrections from `dh_id_corrections-<chunk>.json` apply to
    `agent-<tag>-<chunk>.jsonl` — the chunk identifier must match. Returns
    a per-agent count of patches applied.
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
            key = (tag, row["dh_id"])
            if key in chunk_corrections:
                row["dh_id"] = chunk_corrections[key]["canonical_dh_id"]
                row["name"] = chunk_corrections[key]["canonical_dh_id"]
                patched += 1
        if patched:
            jsonl_path.write_text(
                "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                encoding="utf-8",
            )
        counts[jsonl_path.name] = patched
    return counts


def main(agent_dir: Path) -> None:
    counts = apply_corrections(agent_dir)
    total = sum(counts.values())
    print(f"pre_merge: applied {total} dh_id correction(s) across {len(counts)} agent files")
    for filename, n in sorted(counts.items()):
        if n:
            print(f"  {filename}: {n}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent-dir",
        type=Path,
        default=Path(os.environ.get("PM_AGENT_DIR", DEFAULT_AGENT_DIR)),
        help=f"Directory containing agent-*.jsonl (default: {DEFAULT_AGENT_DIR}).",
    )
    args = parser.parse_args()
    main(args.agent_dir)
