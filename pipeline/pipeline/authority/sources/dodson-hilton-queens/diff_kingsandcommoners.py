#!/usr/bin/env python3
"""Diff reconciled Kings and Commoners rows against the p98-p103 chunk.

Implements Step 11.5 item 0 of the Phase-0 OCR-transcription playbook:
the baseline transcription-diff that compares reconciled-row fields
(`roles`, `notes`) against the chunk file's parsed header-tuple and
prose block. Mirrors `diff_ramesside.py`'s pattern but simplified for a
single-sub-block chunk (Kings and Commoners is a 13th-Dynasty
contiguous run, not three non-contiguous sub-blocks like Ramesside).

The chunk file's markdown is parsed into `{name → {roles, notes}}`; the
script iterates reconciled rows filtered by `sub_period`, looks up the
corresponding entry by `dh_id`, and surfaces mismatches.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/dodson-hilton-queens/diff_kingsandcommoners.py

Requires the OCR chunk file to exist at `raw/chunk-p98-p103.md`
(gitignored per ADR-017; reproduce via `transform_kc.py` against the
Gemini-output text file at `/Users/philipp/Downloads/source-p98-p103.txt`
per `transcribe.md`). A clean run prints zero mismatches and exits 0.

Expected divergences from the raw Gemini OCR output (the `.txt` file,
not the chunk file): five systematic character-level corrections
applied by `transform_kc.py` before the chunk was fed to the extraction
agents. See `transform_kc.py`'s module docstring for per-substitution
rationale. Those corrections are already baked into the chunk file this
script reads against, so the diff here is reconciled ↔ corrected-chunk,
not reconciled ↔ raw-Gemini.

Follow-up: when remaining chapters land with their own chunk files, this
and the earlier `diff_*.py` scripts can be consolidated into a generic
`diff.py` that iterates every `(chunk, sub_period)` pair. Keeping them
as per-chunk scripts for now matches the playbook's expectation that
each chunk ships its own mechanical check.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECON = HERE / "reconciled.jsonl"

CHUNK_FILE = HERE / "raw/chunk-p98-p103.md"
SUB_PERIOD = "Kings and Commoners"


# Matches `**Name**` (male, bold upright) or `***Name***` (female, bold
# italic) at a line start. Tolerates:
# - OPTIONAL role parenthetical (entries like Ayameru A, Bebires,
#   Duaneferet A, Duaneferet B, Hapyu, Hatshepsut B, Henut A, Iuhetibu
#   C, Inyotef B, Kay, Nebtit, Neferhotep A, Neferhotep B, Nen?[...],
#   Neshemethotepti, Reditenes A, Reniseneb A, Reniseneb B, Ressonbe,
#   Seb, Senebhenas B, Senebtisi, Sithathormeryet, [...]13A, [...]13B,
#   [...]13C, [...]13E have no role parens at all).
# - OPTIONAL trailing period after the role parens.
# The prose body captures up to the next entry / H2 / H3 / editorial
# parenthetical-footer / continuation marker.
ENTRY_RE = re.compile(
    r"^(\*\*\*|\*\*)(?P<name>[^*\n]+?)\1"
    r"(?:\s*\((?P<roles>[^)]+)\))?\.?\s*\n"
    r"(?P<notes>(?:(?!^\*\*|^##|^###|^\[\*\*|^\(|^---\s*$).*\n?)+)",
    re.MULTILINE,
)


_SUPERSCRIPT_TO_ASCII = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


def _norm(s: str) -> str:
    """Collapse whitespace and strip markdown stars for comparison.

    Also normalises Unicode superscript footnote markers (`¹²⁴` in the
    OCR vs `124` in reconciled, no factual difference) and hyphen-soft-
    break whitespace (`rock- carving` from line-wrap vs `rock-carving`
    reassembled) — same presentation-artefact normalisation as
    `diff_ramesside.py._norm`.
    """
    s = re.sub(r"\*+", "", s)
    s = s.translate(_SUPERSCRIPT_TO_ASCII)
    s = re.sub(r"-\s+", "-", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _parse_chunk(path: Path) -> dict[str, dict]:
    if not path.exists():
        sys.exit(
            f"ERROR: chunk file {path} missing. Expected at `raw/chunk-p98-p103.md` "
            f"(gitignored per ADR-017). Re-OCR from the source PDF via `transform_kc.py` "
            f"per `transcribe.md` before running this diff."
        )
    text = path.read_text()
    entries: dict[str, dict] = {}
    for m in ENTRY_RE.finditer(text):
        name = m.group("name").strip()
        # Skip the styled heading (`**Brief Lives** • • • • …`) — the
        # `^` anchor matches its line but it's not an entry.
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
    print(
        f"Kings and Commoners single-chunk totals: "
        f"mismatches={m} unmatched={u} missing_in_recon={mi}"
    )
    # Exit non-zero if any row-level mismatch surfaces so CI / the playbook
    # Step-11.5 gate treats a dirty diff as a failure.
    return 1 if (m or u or mi) else 0


if __name__ == "__main__":
    sys.exit(main())
