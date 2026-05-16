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


def _load_corrections() -> dict[tuple[str, str], dict[str, str]]:
    """Load all `dh_id_corrections-*.json` files in the source dir.

    Each file is keyed by `'<agent_tag>|<wrong_dh_id>'` -> {
        canonical_dh_id: str, rationale: str
    }. Loader merges across all chunk files; duplicate keys across files
    raise loudly (each chunk's corrections are disjoint).

    Top-level keys starting with `_` (e.g. `_doc`) are loader directives and
    skipped.
    """
    merged: dict[tuple[str, str], dict[str, str]] = {}
    source_of: dict[tuple[str, str], Path] = {}
    for json_path in sorted(SOURCE_DIR.glob("dh_id_corrections-*.json")):
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(
                f"pre_merge: {json_path} top-level must be a dict; "
                f"got {type(raw).__name__}"
            )
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
            tuple_key = (tag, wrong)
            if tuple_key in merged:
                raise ValueError(
                    f"pre_merge: duplicate correction key {key!r} in {json_path} "
                    f"(also in {source_of[tuple_key]})"
                )
            merged[tuple_key] = value
            source_of[tuple_key] = json_path
    return merged


def apply_corrections(agent_dir: Path) -> dict[str, int]:
    """Apply corrections to each `agent-<tag>-<chunk>.jsonl` file in agent_dir.

    Returns a per-agent count of patches applied.
    """
    corrections = _load_corrections()
    counts: dict[str, int] = {}
    for jsonl_path in sorted(agent_dir.glob("agent-*.jsonl")):
        name = jsonl_path.stem  # 'agent-a-ofkingsandpriests'
        parts = name.split("-", 2)
        if len(parts) < 2 or parts[0] != "agent":
            continue
        tag = parts[1]
        rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        patched = 0
        for row in rows:
            key = (tag, row["dh_id"])
            if key in corrections:
                row["dh_id"] = corrections[key]["canonical_dh_id"]
                row["name"] = corrections[key]["canonical_dh_id"]
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
