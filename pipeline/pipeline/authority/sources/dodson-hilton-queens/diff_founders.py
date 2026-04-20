#!/usr/bin/env python3
"""Diff reconciled Founders rows against the p44-p45 chunk.

Implements Step 11.5 item 0 of the Phase-0 OCR-transcription playbook —
baseline transcription-diff against chunk `raw/chunk-p44-p45.md` for the
`sub_period == "The Founders"` rows. Mirrors `diff_kingsandcommoners.py`
structure (single-sub-block scope).

Usage:
    cd pipeline && uv run python pipeline/authority/sources/dodson-hilton-queens/diff_founders.py

Clean run prints zero mismatches and exits 0.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECON = HERE / "reconciled.jsonl"
CHUNK_FILE = HERE / "raw/chunk-p44-p45.md"
SUB_PERIOD = "The Founders"


ENTRY_RE = re.compile(
    r"^(\*\*\*|\*\*)(?P<name>[^*\n]+?)\1"
    r"(?:\s*\((?P<roles>[^)]+)\))?\.?\s*\n"
    r"(?P<notes>(?:(?!^\*\*|^##|^###|^\[\*\*|^\(|^---\s*$).*\n?)+)",
    re.MULTILINE,
)


_SUPERSCRIPT_TO_ASCII = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


def _norm(s: str) -> str:
    """Collapse whitespace; strip markdown stars; normalise soft-hyphen
    line-break, superscript footnote markers, and D&H's `[^NN]` footnote-
    reference markdown.

    The Founders chunk contains `[^60]`, `[^61]`, `[^62]` footnote
    references. D&H's printed equivalent is an inline superscript digit.
    `diff_ramesside.py`'s `_norm` already converts `¹²⁴ → 124` for the
    Ramesside-era OCR convention; here we normalise `[^60] → 60` so the
    reconciled notes (which may drop the `^` and `[]` brackets during
    extraction, depending on agent judgement) match the chunk's
    markdown-footnote form after stripping.

    Also collapses `"early- 4th"` → `"early 4th"` — D&H's soft-hyphen
    line-break between printed pp. 48 and 49 on Nymaathap A's prose is
    intentionally stripped at both the pre-extraction layer (via
    `transform_founders.py`) and the post-merge layer (via
    `fix_rows.py`'s `FOUNDERS_CORRECTIONS`); this `_norm` tolerance
    makes the diff robust against either side retaining the soft hyphen.
    """
    s = re.sub(r"\*+", "", s)
    s = s.translate(_SUPERSCRIPT_TO_ASCII)
    s = re.sub(r"\[\^(\d+)\]", r"\1", s)  # `[^60]` → `60`
    s = re.sub(r"-\s+", "-", s)
    s = re.sub(r"\bearly-(\d)", r"early \1", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _parse_chunk(path: Path) -> dict[str, dict]:
    if not path.exists():
        sys.exit(
            f"ERROR: chunk file {path} missing. Regenerate via `transform_founders.py` "
            f"or re-OCR from the source PDF per `transcribe.md`."
        )
    text = path.read_text()
    entries: dict[str, dict] = {}
    for m in ENTRY_RE.finditer(text):
        name = m.group("name").strip()
        if name.lower().startswith("brief lives"):
            continue
        roles_raw = m.group("roles")
        roles = [r.strip() for r in roles_raw.split(";")] if roles_raw else []
        notes = _norm(m.group("notes"))
        entries[name] = {"roles": roles, "notes": notes}
    return entries


def _diff_chunk(chunk_file: Path, sub_period: str, rows: list[dict]) -> tuple[int, int, int]:
    entries = _parse_chunk(chunk_file)
    section_rows = [r for r in rows if r["sub_period"] == sub_period]
    print(
        f"=== {sub_period} ({chunk_file.name}) ===\n"
        f"Parsed {len(entries)} entries from transcription; "
        f"loaded {len(section_rows)} rows from reconciled.jsonl.\n"
    )

    mismatches: list[tuple[str, list[str]]] = []
    unmatched: list[str] = []

    for r in section_rows:
        name = r["dh_id"]
        src = entries.get(name)
        if not src:
            unmatched.append(name)
            continue
        problems: list[str] = []
        if set(r["roles"]) != set(src["roles"]):
            problems.append(f"roles: reconciled={r['roles']} vs source={src['roles']}")
        a = _norm(r["notes"] or "")
        b = src["notes"]
        if a != b:
            for i, (ca, cb) in enumerate(zip(a, b)):
                if ca != cb:
                    ctx_a = a[max(0, i - 30): i + 40]
                    ctx_b = b[max(0, i - 30): i + 40]
                    problems.append(
                        f"notes differ at char {i}:\n"
                        f"    RECON:  ...{ctx_a}...\n"
                        f"    SOURCE: ...{ctx_b}..."
                    )
                    break
            else:
                problems.append(f"notes length differ: recon={len(a)} source={len(b)}")
        if problems:
            mismatches.append((name, problems))

    for name, problems in mismatches:
        print(f"{name}")
        for p in problems:
            print(f"  - {p}")

    recon_names = {r["dh_id"] for r in section_rows}
    missing_in_recon = set(entries.keys()) - recon_names
    if missing_in_recon:
        print(f"\n[{sub_period}] In transcription but NOT in reconciled:")
        for n in sorted(missing_in_recon):
            print(f"  {n}")
    if unmatched:
        print(f"\n[{sub_period}] In reconciled but NOT in transcription:")
        for n in unmatched:
            print(f"  {n}")

    print(
        f"\n[{sub_period}] Summary: "
        f"matched={len(section_rows) - len(mismatches) - len(unmatched)} "
        f"mismatches={len(mismatches)} unmatched={len(unmatched)} "
        f"missing_in_recon={len(missing_in_recon)}\n"
    )
    return len(mismatches), len(unmatched), len(missing_in_recon)


def main() -> int:
    rows = [json.loads(line) for line in RECON.read_text().splitlines() if line.strip()]
    m, u, mi = _diff_chunk(CHUNK_FILE, SUB_PERIOD, rows)
    print("=== OVERALL ===")
    print(f"Founders single-chunk totals: mismatches={m} unmatched={u} missing_in_recon={mi}")
    return 1 if (m or u or mi) else 0


if __name__ == "__main__":
    sys.exit(main())
