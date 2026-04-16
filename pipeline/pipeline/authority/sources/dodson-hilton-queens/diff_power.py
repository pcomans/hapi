#!/usr/bin/env python3
"""Diff reconciled Power rows against the transcription chunk."""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECON = HERE / "reconciled.jsonl"
CHUNK = HERE / "raw/chunk-p126-p130.md"

# Parse markdown into {name: {roles: [...], notes: "..."}}
text = CHUNK.read_text()
entries = {}
# Match ***Name*** (Roles)\nNotes...  or **Name** (Roles)\nNotes...
pattern = re.compile(
    r"^(\*\*\*|\*\*)(?P<name>[^*]+?)\1\s*\((?P<roles>[^)]+)\)\s*\n(?P<notes>(?:(?!^\*\*|^##|^###).*\n?)+)",
    re.MULTILINE,
)
for m in pattern.finditer(text):
    name = m.group("name").strip()
    roles = [r.strip() for r in m.group("roles").split(";")]
    notes = m.group("notes").strip()
    # Strip markdown bold inside notes for comparison
    notes_clean = re.sub(r"\*+", "", notes).strip()
    entries[name] = {"roles": roles, "notes": notes_clean}

print(f"Parsed {len(entries)} entries from transcription")

rows = [json.loads(l) for l in RECON.read_text().splitlines()]
power = [r for r in rows if r["sub_period"] == "The Power and the Glory"]
print(f"Loaded {len(power)} Power rows from reconciled.jsonl\n")

mismatches = []
unmatched = []

def norm(s):
    # Collapse whitespace, strip markdown stars
    s = re.sub(r"\*+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

for r in power:
    name = r["dh_id"]
    src = entries.get(name)
    if not src:
        unmatched.append(name)
        continue
    problems = []
    # Roles
    if set(r["roles"]) != set(src["roles"]):
        problems.append(f"roles: reconciled={r['roles']} vs source={src['roles']}")
    # Notes (exact after whitespace/markdown normalization)
    a = norm(r["notes"] or "")
    b = norm(src["notes"])
    if a != b:
        # Show first diff location
        for i, (ca, cb) in enumerate(zip(a, b)):
            if ca != cb:
                ctx_a = a[max(0, i-30):i+40]
                ctx_b = b[max(0, i-30):i+40]
                problems.append(f"notes differ at char {i}:\n    RECON:  ...{ctx_a}...\n    SOURCE: ...{ctx_b}...")
                break
        else:
            problems.append(f"notes length differ: recon={len(a)} source={len(b)}")
    if problems:
        mismatches.append((name, problems))

print(f"=== UNMATCHED (in reconciled but not in transcription) ===")
for n in unmatched:
    print(f"  {n}")
print()
print(f"=== MISMATCHES ({len(mismatches)}) ===")
for name, problems in mismatches:
    print(f"\n{name}")
    for p in problems:
        print(f"  - {p}")

print(f"\n=== SUMMARY ===")
print(f"Total rows: {len(power)}")
print(f"Matched cleanly: {len(power) - len(mismatches) - len(unmatched)}")
print(f"Mismatches: {len(mismatches)}")
print(f"Unmatched: {len(unmatched)}")

# Also list transcription entries not in reconciled
recon_names = {r['dh_id'] for r in power}
missing_in_recon = set(entries.keys()) - recon_names
if missing_in_recon:
    print(f"\n=== In transcription but NOT in reconciled ===")
    for n in sorted(missing_in_recon):
        print(f"  {n}")
