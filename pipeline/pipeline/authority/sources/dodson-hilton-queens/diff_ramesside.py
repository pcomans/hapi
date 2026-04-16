#!/usr/bin/env python3
"""Diff reconciled Ramesside rows against the three transcription chunks.

Implements Step 11.5 item 0 of the Phase-0 OCR-transcription playbook:
the baseline transcription-diff that compares reconciled-row fields
(`roles`, `notes`) against each chunk file's parsed header-tuple and
prose block. Mirrors `diff_power.py`'s pattern, extended for three
non-contiguous sub-blocks with a `(chunk_file, sub_period)` config.

Each chunk file's markdown is parsed into `{name → {roles, notes}}`;
the script iterates reconciled rows filtered by `sub_period`, looks up
the corresponding entry by `dh_id`, and surfaces mismatches.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/dodson-hilton-queens/diff_ramesside.py

Requires the OCR chunk files to exist at `raw/chunk-*.md` (gitignored
per ADR-017; re-OCR from the source PDF per `transcribe.md` if they
are missing). A clean run prints zero mismatches.

Follow-up: when chapters 1 / 2 / 4 / 5 land with their own chunk files,
this script and `diff_power.py` can be merged into a generic
`diff.py` that iterates every `(chunk, sub_period)` pair across the
source. Keeping them as per-chunk scripts for now matches the
playbook's expectation that each chunk ships its own mechanical check.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECON = HERE / "reconciled.jsonl"

# (chunk markdown file, sub_period string) for each Ramesside sub-block.
CHUNKS: list[tuple[Path, str]] = [
    (HERE / "raw/chunk-p157-p162.md", "The House of Ramesses"),
    (HERE / "raw/chunk-p169-p170.md", "The Feud of the Ramessides"),
    (HERE / "raw/chunk-p178-p180.md", "The Decline of the Ramessides"),
]

# Matches `**Name**` (male, bold upright) or `***Name***` (female, bold
# italic) at a line start. Tolerates:
# - OPTIONAL trailing superscript digits between the closing `**` and the
#   opening `(` (D&H prints footnote markers inline in unicode
#   superscript: `**Ramesses-meryamun-Nebweben**¹²⁵ (KSon)`).
# - OPTIONAL role parenthetical (entries like Amenwahsu, Benanath,
#   Iryet, Hemdjert, Pentaweret, Nesibanebdjedet, Tentamun A / B,
#   Tiye C have no role parens at all).
# - OPTIONAL trailing period after the role parens (D&H p. 194
#   Sethirkopshef B prints `(KSon; MH).` with the period inside the
#   line, not an OCR artefact).
# The prose body captures up to the next entry / H2 / H3 / continuation
# marker / editorial parenthetical-footer boundary.
ENTRY_RE = re.compile(
    r"^(\*\*\*|\*\*)(?P<name>[^*\n]+?)\1"
    r"[^\s(]*"
    r"(?:\s*\((?P<roles>[^)]+)\))?\.?\s*\n"
    r"(?P<notes>(?:(?!^\*\*|^##|^###|^\[\*\*|^\().*\n?)+)",
    re.MULTILINE,
)

# Matches `[**Name** continued] <prose…>` at a line start — D&H entries
# that wrap across a page break have their continuation marked by the
# OCR convention `[**Khaemwaset E** continued] the Queens tomb QV44;…`.
# The continuation prose must be concatenated with the initial entry's
# `notes` to produce a single verbatim D&H paragraph.
CONTINUATION_RE = re.compile(
    r"^\[(\*\*\*|\*\*)(?P<name>[^*]+?)\1\s+continued\]\s*(?P<notes>(?:(?!^\*\*|^##|^###|^\[\*\*).*\n?)+)",
    re.MULTILINE,
)


_SUPERSCRIPT_TO_ASCII = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


def _norm(s: str) -> str:
    """Collapse whitespace and strip markdown stars for comparison.

    Also normalises two OCR-vs-extraction presentation artefacts that
    don't represent information loss: Unicode superscript footnote
    markers (`¹²⁴` in the OCR vs `124` in reconciled, no factual
    difference) and hyphen-soft-break whitespace (`rock- carving` in
    the OCR from a line-wrap vs `rock-carving` in reconciled where the
    extraction agent reassembled the word).
    """
    s = re.sub(r"\*+", "", s)
    s = s.translate(_SUPERSCRIPT_TO_ASCII)
    s = re.sub(r"-\s+", "-", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _parse_chunk(path: Path) -> dict[str, dict]:
    if not path.exists():
        sys.exit(
            f"ERROR: chunk file {path} missing. Expected at `raw/chunk-*.md` "
            f"(gitignored per ADR-017). Re-OCR from the source PDF per "
            f"`transcribe.md` before running this diff."
        )
    text = path.read_text()
    entries: dict[str, dict] = {}
    for m in ENTRY_RE.finditer(text):
        name = m.group("name").strip()
        roles_raw = m.group("roles")
        roles = [r.strip() for r in roles_raw.split(";")] if roles_raw else []
        notes = _norm(m.group("notes"))
        entries[name] = {"roles": roles, "notes": notes}

    # Fold in page-break continuations ("[**Name** continued] …").
    for m in CONTINUATION_RE.finditer(text):
        name = m.group("name").strip()
        continuation = _norm(m.group("notes"))
        if name in entries:
            entries[name]["notes"] = _norm(entries[name]["notes"] + " " + continuation)
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
    totals = (0, 0, 0)
    for chunk_file, sub_period in CHUNKS:
        m, u, mi = _diff_chunk(chunk_file, sub_period, rows)
        totals = (totals[0] + m, totals[1] + u, totals[2] + mi)

    print("=== OVERALL ===")
    print(
        f"Ramesside totals across 3 sub-blocks: "
        f"mismatches={totals[0]} unmatched={totals[1]} missing_in_recon={totals[2]}"
    )
    # Exit non-zero if any row-level mismatch surfaces so CI / the playbook
    # Step-11.5 gate treats a dirty diff as a failure.
    return 1 if any(totals) else 0


if __name__ == "__main__":
    sys.exit(main())
