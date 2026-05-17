"""Normalize chunk-7 notes_from_pm to drop the occupant_name prefix.

Aligns chunk-7 with the chunk-1/2/3/6 convention: notes_from_pm holds
the title cluster + dating + cross-refs, NOT the occupant name (which
lives in occupant_name).

Strategy: drop the leading "<Name>[ good name <Alt>][,]?\s+" prefix
that matches `occupant_name`. Uses occupant_name as the per-row key
rather than a generic regex.
"""
import json
import pathlib
import re

corrections = []
for tag in "abc":
    p = pathlib.Path(
        f"/Users/philipp/code/hapi/pipeline/pipeline/authority/sources/"
        f"porter-moss-memphis/raw/agent-{tag}-chunk7.jsonl"
    )
    rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    changed = 0
    for r in rows:
        notes = r.get("notes_from_pm")
        name = r.get("occupant_name")
        if notes is None or name is None:
            continue
        # Build a regex: case-insensitive match of the name (or ALL-CAPS form),
        # optionally followed by " good name <ALT>", optionally followed by
        # comma/period, then whitespace.
        # Match the leading name pattern liberally.
        # Form 1: "<Name>, " | "<Name>. " | "<Name> "
        # Form 2: "<Name> good name <Alt>, " | etc.
        # Form 3: ALL-CAPS variants.

        # Just try to strip the name prefix.
        # Approach: find the name (or all-caps name) at start; strip up to and
        # including the trailing comma/period/space cluster.
        name_pattern = re.compile(
            r"^\s*(?:" + re.escape(name) + r"|" + re.escape(name.upper()) + r")"
            r"(?:\s+good\s+name\s+\S+(?:[,]?)?)?[,.\s]*",
            re.IGNORECASE,
        )
        m = name_pattern.match(notes)
        if m and m.end() > 0:
            stripped = notes[m.end():]
            if stripped and stripped != notes:
                r["notes_from_pm"] = stripped
                changed += 1
                if len(corrections) < 15:
                    corrections.append(
                        (tag, r["tomb_id"], notes[:60], stripped[:60])
                    )
    p.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows)
        + "\n",
        encoding="utf-8",
    )
    print(f"agent-{tag}: {changed} rows normalized")

print("--- sample corrections ---")
for tag, tid, before, after in corrections:
    print(f"  {tag} {tid}: {before!r} -> {after!r}")
