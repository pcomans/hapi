"""Fetch and reconcile Wikidata pharaoh data into authority source JSONL.

Queries the Wikidata SPARQL endpoint for all entities classified as pharaohs
of ancient Egypt, then reconciles the results into the standard authority
source schema (matching HKW and Wikipedia Ptolemaic sources) with an added
`qid` field for Wikidata entity linking.

Usage:
    cd pipeline && uv run python pipeline/authority/sources/wikidata-pharaohs/fetch.py

Output:
    raw.json          — deduplicated SPARQL records (intermediate pre-reconciliation dump)
    reconciled.jsonl  — one JSON object per line in authority source schema
"""

import json
import sys
import urllib.request
import urllib.parse
from collections import Counter
from pathlib import Path

SOURCE_DIR = Path(__file__).parent

SPARQL_QUERY = """
SELECT DISTINCT
  ?pharaoh
  ?pharaohLabel
  ?pharaohDescription
  (GROUP_CONCAT(DISTINCT ?altLabel; SEPARATOR="||") AS ?altLabels)
  ?familyLabel
  ?periodLabel
  ?reignStart
  ?reignEnd
  ?birthDate
  ?deathDate
  ?replacesLabel
  ?replacedByLabel
WHERE {
  # Entities that held the position of pharaoh OR are instance of pharaoh
  {
    ?pharaoh wdt:P31 wd:Q12097 .
  }
  UNION
  {
    ?pharaoh p:P39 ?posStmt .
    ?posStmt ps:P39 wd:Q37110 .
    OPTIONAL { ?posStmt pq:P580 ?reignStart . }
    OPTIONAL { ?posStmt pq:P582 ?reignEnd . }
    OPTIONAL { ?posStmt pq:P1365 ?replaces . }
    OPTIONAL { ?posStmt pq:P1366 ?replacedBy . }
  }

  OPTIONAL { ?pharaoh wdt:P53 ?family . }
  OPTIONAL { ?pharaoh wdt:P2348 ?period . }
  OPTIONAL { ?pharaoh wdt:P569 ?birthDate . }
  OPTIONAL { ?pharaoh wdt:P570 ?deathDate . }

  OPTIONAL {
    ?pharaoh skos:altLabel ?altLabel .
    FILTER(LANG(?altLabel) = "en")
  }

  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
GROUP BY ?pharaoh ?pharaohLabel ?pharaohDescription ?familyLabel ?periodLabel
         ?reignStart ?reignEnd ?birthDate ?deathDate ?replacesLabel ?replacedByLabel
ORDER BY ?reignStart ?birthDate
"""

# Dynasty label → number mapping
_ORDINALS = {
    "First": 1, "Second": 2, "Third": 3, "Fourth": 4, "Fifth": 5,
    "Sixth": 6, "Seventh": 7, "Eighth": 8, "Ninth": 9, "Tenth": 10,
    "Eleventh": 11, "Twelfth": 12, "Thirteenth": 13, "Fourteenth": 14,
    "Fifteenth": 15, "Sixteenth": 16, "Seventeenth": 17, "Eighteenth": 18,
    "Nineteenth": 19, "Twentieth": 20, "Twenty-first": 21, "Twenty-second": 22,
    "Twenty-third": 23, "Twenty-fourth": 24, "Twenty-fifth": 25,
    "Twenty-sixth": 26, "Twenty-seventh": 27, "Twenty-eighth": 28,
    "Twenty-ninth": 29, "Thirtieth": 30, "Thirty-first": 31,
}
DYNASTY_MAP = {f"{name} Dynasty of Egypt": num for name, num in _ORDINALS.items()}
DYNASTY_MAP["Dynasty 00"] = 0
DYNASTY_MAP["Protodynastic Period of Egypt"] = 0

# QIDs that Wikidata erroneously classifies as pharaohs. Excluded at reconciliation time.
# Q113564932 — "Aknamkanon" is a fictional Yu-Gi-Oh! character, not a historical ruler.
# Q136446547 — "Milkyaton" is a Cypriot king, not an Egyptian pharaoh.
# Q471255    — Pothinus was a Ptolemaic court official/regent, not a pharaoh.
KNOWN_NON_PHARAOHS: frozenset[str] = frozenset({
    "Q113564932",
    "Q136446547",
    "Q471255",
})

# Per-QID alt_labels to drop. Used to remove Wikidata cross-contamination where one
# pharaoh's Wikidata page incorrectly lists another pharaoh's name as an alias.
# Q39938 (Ptolemy XIII) has "Ptolemy XII" as an alt_label — a different ruler entirely.
BAD_ALT_LABELS: dict[str, set[str]] = {
    "Q39938": {"Ptolemy XII"},
}


def _get_val(binding: dict, key: str) -> str | None:
    return binding.get(key, {}).get("value")


def _parse_year(datestr: str | None) -> int | None:
    """Extract year from Wikidata ISO 8601 date like '-1478-01-01T00:00:00Z'.

    Raises on unparseable dates — the fetch script runs manually and
    unexpected formats should crash loudly so the parser gets updated.
    """
    if not datestr:
        return None
    # Wikidata sometimes returns blank node URIs instead of date literals
    # for unknown/disputed dates. These are not parseable.
    if datestr.startswith("http"):
        return None
    if datestr.startswith("-"):
        year = -int(datestr[1:].split("-")[0])
    elif datestr.startswith("+"):
        year = int(datestr[1:].split("-")[0])
    else:
        # Unprefixed dates from Wikidata (e.g. '2965-01-01T00:00:00Z').
        # Parsed as-is; the reconcile step will negate and warn if positive.
        year = int(datestr.split("-")[0])
    return year


def _parse_dynasty(families: list[str]) -> int | None:
    for fam in families:
        if fam in DYNASTY_MAP:
            return DYNASTY_MAP[fam]
    return None


def _parse_dynasty_label(families: list[str]) -> str | None:
    for fam in families:
        if fam in DYNASTY_MAP:
            return fam
    return families[0] if families else None


def fetch_sparql() -> list[dict]:
    """Execute SPARQL query against Wikidata and return raw bindings."""
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({
        "query": SPARQL_QUERY,
        "format": "json",
    })
    req = urllib.request.Request(url, headers={
        "User-Agent": "HapiProject/0.1 (https://github.com/pcomans/hapi; Egyptian artifacts index)",
        "Accept": "application/sparql-results+json",
    })
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["results"]["bindings"]


def deduplicate(bindings: list[dict]) -> list[dict]:
    """Merge multiple SPARQL rows per pharaoh into single records."""
    by_qid: dict[str, dict] = {}

    for r in bindings:
        qid = _get_val(r, "pharaoh").split("/")[-1]
        if qid not in by_qid:
            by_qid[qid] = {
                "qid": qid,
                "label": _get_val(r, "pharaohLabel"),
                "description": _get_val(r, "pharaohDescription"),
                "alt_labels": set(),
                "families": set(),
                "periods": set(),
                "reign_start": None,
                "reign_end": None,
                "birth_year": None,
                "death_year": None,
                "replaces": None,
                "replaced_by": None,
            }

        rec = by_qid[qid]

        alts = _get_val(r, "altLabels")
        if alts:
            rec["alt_labels"].update(a.strip() for a in alts.split("||") if a.strip())

        fam = _get_val(r, "familyLabel")
        if fam:
            rec["families"].add(fam)

        per = _get_val(r, "periodLabel")
        if per:
            rec["periods"].add(per)

        rs = _parse_year(_get_val(r, "reignStart"))
        re_ = _parse_year(_get_val(r, "reignEnd"))
        if rs is not None and (rec["reign_start"] is None or rs < rec["reign_start"]):
            rec["reign_start"] = rs
        if re_ is not None and (rec["reign_end"] is None or re_ > rec["reign_end"]):
            rec["reign_end"] = re_

        by_ = _parse_year(_get_val(r, "birthDate"))
        dy = _parse_year(_get_val(r, "deathDate"))
        if by_ is not None:
            rec["birth_year"] = by_
        if dy is not None:
            rec["death_year"] = dy

        rep = _get_val(r, "replacesLabel")
        repby = _get_val(r, "replacedByLabel")
        if rep:
            rec["replaces"] = rep
        if repby:
            rec["replaced_by"] = repby

    # Convert sets to sorted lists
    records = []
    for rec in by_qid.values():
        rec["alt_labels"] = sorted(rec["alt_labels"])
        rec["families"] = sorted(rec["families"])
        rec["periods"] = sorted(rec["periods"])
        records.append(rec)

    return records


def reconcile(records: list[dict]) -> list[dict]:
    """Transform deduplicated records into authority source schema."""
    reconciled = []

    for rec in records:
        qid = rec["qid"]
        label = rec["label"]

        # Skip known non-pharaohs (Wikidata misclassifications)
        if qid in KNOWN_NON_PHARAOHS:
            continue

        # Skip unresolved entities (label is just the QID)
        if label and label.startswith("Q") and label == qid:
            continue

        dynasty = _parse_dynasty(rec["families"])
        dynasty_label = _parse_dynasty_label(rec["families"])

        # Prefer reign dates; fall back to birth/death
        start_year = rec["reign_start"]
        end_year = rec["reign_end"]
        approximate = False
        if start_year is None and end_year is None:
            if rec["birth_year"] is not None or rec["death_year"] is not None:
                start_year = rec["birth_year"]
                end_year = rec["death_year"]
                approximate = True

        # Negate positive years (Wikidata data quality issue — some BCE dates
        # stored with '+' prefix). Log each case so it's auditable.
        for date_val, date_name in [(start_year, "start"), (end_year, "end")]:
            if date_val is not None and date_val > 0:
                print(
                    f"  WARNING: {label} ({rec['qid']}): {date_name}_year={date_val} "
                    f"is positive — negating to {-date_val}",
                    file=sys.stderr,
                )
        if start_year is not None and start_year > 0:
            start_year = -start_year
        if end_year is not None and end_year > 0:
            end_year = -end_year

        # Fix inverted date ranges (Wikidata data quality issues)
        if start_year is not None and end_year is not None and start_year > end_year:
            start_year, end_year = end_year, start_year

        notes = []
        if approximate and (start_year is not None or end_year is not None):
            notes.append("Dates from birth/death, not reign")
        if rec["replaces"]:
            notes.append(f"Replaces: {rec['replaces']}")
        if rec["replaced_by"]:
            notes.append(f"Replaced by: {rec['replaced_by']}")

        bad = BAD_ALT_LABELS.get(qid, set())
        alt_labels = [a for a in rec["alt_labels"]
                      if len(a) > 1 and not a.isdigit() and a != label and a not in bad]

        reconciled.append({
            "kind": "ruler",
            "qid": rec["qid"],
            "display": label,
            "alt_labels": alt_labels if alt_labels else None,
            "prenomen": None,
            "start_year": start_year,
            "end_year": end_year,
            "approximate": approximate,
            "uncertainty_plus_years": None,
            "dynasty": dynasty,
            "dynasty_label": dynasty_label,
            "page": None,
            "note": "; ".join(notes) if notes else None,
        })

    # Sort by dynasty then start date
    reconciled.sort(key=lambda r: (
        r["dynasty"] if r["dynasty"] is not None else 999,
        r["start_year"] if r["start_year"] is not None else 9999,
    ))

    return reconciled


def main():
    print("Fetching pharaohs from Wikidata SPARQL endpoint...")
    bindings = fetch_sparql()
    print(f"  Raw SPARQL rows: {len(bindings)}")

    records = deduplicate(bindings)
    print(f"  Unique entities: {len(records)}")

    # Save intermediate dump (deduplicated records, pre-reconciliation)
    raw_path = SOURCE_DIR / "raw.json"
    with open(raw_path, "w") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"  Saved intermediate dump → {raw_path}")

    # Reconcile
    reconciled = reconcile(records)
    print(f"  Reconciled rulers: {len(reconciled)}")

    # Save reconciled JSONL
    jsonl_path = SOURCE_DIR / "reconciled.jsonl"
    with open(jsonl_path, "w") as f:
        for row in reconciled:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"  Saved reconciled → {jsonl_path}")

    # Stats
    has_dynasty = sum(1 for r in reconciled if r["dynasty"] is not None)
    has_dates = sum(1 for r in reconciled
                    if r["start_year"] is not None or r["end_year"] is not None)
    has_alts = sum(1 for r in reconciled if r["alt_labels"] is not None)

    print(f"\nStats:")
    print(f"  With dynasty number: {has_dynasty}")
    print(f"  With dates: {has_dates}")
    print(f"  With alt labels: {has_alts}")

    dyn_counts = Counter(r["dynasty"] for r in reconciled if r["dynasty"] is not None)
    print(f"\nBy dynasty:")
    for dyn in sorted(dyn_counts):
        print(f"  Dynasty {dyn}: {dyn_counts[dyn]}")
    print(f"  No dynasty: {sum(1 for r in reconciled if r['dynasty'] is None)}")


if __name__ == "__main__":
    main()
