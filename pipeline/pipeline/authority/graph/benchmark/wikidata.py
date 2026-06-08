"""Wikidata silver-standard benchmark for cross-source ruler matching (ADR-020).

Wikidata is a SILVER standard, never gold: it is not independent of the same
scholarly sources and is least reliable on the contested identities that drive
matcher error (ADR-020). We use it for a cheap, directional precision/recall
estimate and to surface disagreements — not as authority truth.

Method: fetch the ~518 entities with `P39 = Q37110` (position held = pharaoh)
with their en/de labels + aliases, cache the snapshot on disk (reproducible), and
align each source ruler to a QID by exact-normalized name match against Wikidata's
OWN curated label/alias set (which aggregates cross-language spellings). Same QID
⇒ same entity ⇒ the gold equivalence relation. Ambiguous names (matching >1 QID)
are dropped, conservatively, and counted.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import requests

from ..matcher.stage1_deterministic import normalize_name

_PAREN = re.compile(r"\([^)]*\)")

_CACHE = Path(__file__).resolve().parent / "wikidata_pharaohs.json"
_SPARQL = "https://query.wikidata.org/sparql"
_UA = "hapi-poc-benchmark/0.1 (research; github pcomans/hapi)"

# Entities whose "position held" (P39) is "pharaoh" (Q37110), with en/de labels
# and aliases. The query IS the method-on-disk; the cached result is the snapshot.
_QUERY = """
SELECT ?p ?lab_en ?lab_de
  (GROUP_CONCAT(DISTINCT ?ae; separator="|") AS ?al_en)
  (GROUP_CONCAT(DISTINCT ?ad; separator="|") AS ?al_de)
WHERE {
  ?p wdt:P39 wd:Q37110 .
  OPTIONAL { ?p rdfs:label ?lab_en FILTER(lang(?lab_en)="en") }
  OPTIONAL { ?p rdfs:label ?lab_de FILTER(lang(?lab_de)="de") }
  OPTIONAL { ?p skos:altLabel ?ae FILTER(lang(?ae)="en") }
  OPTIONAL { ?p skos:altLabel ?ad FILTER(lang(?ad)="de") }
}
GROUP BY ?p ?lab_en ?lab_de
"""


def fetch_pharaohs(force: bool = False) -> list[dict]:
    """Return [{qid, names:[...]}], from the on-disk snapshot or a fresh SPARQL pull."""
    if _CACHE.exists() and not force:
        return json.loads(_CACHE.read_text())
    resp = requests.get(
        _SPARQL,
        params={"query": _QUERY},
        headers={"User-Agent": _UA, "Accept": "application/sparql-results+json"},
        timeout=90,
    )
    resp.raise_for_status()
    rows = resp.json()["results"]["bindings"]
    out: list[dict] = []
    for r in rows:
        qid = r["p"]["value"].rsplit("/", 1)[-1]
        names: list[str] = []
        for key in ("lab_en", "lab_de"):
            if key in r and r[key]["value"]:
                names.append(r[key]["value"])
        for key in ("al_en", "al_de"):
            if key in r and r[key]["value"]:
                names.extend(s for s in r[key]["value"].split("|") if s)
        out.append({"qid": qid, "names": sorted(set(names))})
    out.sort(key=lambda e: e["qid"])
    _CACHE.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    return out


@lru_cache(maxsize=1)
def _alias_index() -> dict[frozenset[str], set[str]]:
    """normalized-name-token-set → set of QIDs carrying that name."""
    index: dict[frozenset[str], set[str]] = {}
    for entry in fetch_pharaohs():
        for name in entry["names"]:
            toks = normalize_name(name)
            if toks:
                index.setdefault(toks, set()).add(entry["qid"])
    return index


def align(name: str) -> tuple[str | None, str]:
    """Align a ruler display name to a Wikidata QID via Wikidata's own aliases.

    Tries the full name, then a parenthetical-stripped form (to recover Leprohon
    phase rows like "Akhenaten (Regnal Years 5 to 17)" → "Akhenaten"). Returns
    (qid_or_None, status): 'matched', 'none', or 'ambiguous' (>1 QID — dropped
    conservatively).
    """
    index = _alias_index()
    candidates = [name]
    stripped = _PAREN.sub("", name).strip()
    if stripped and stripped != name:
        candidates.append(stripped)
    for candidate in candidates:
        qids = index.get(normalize_name(candidate), set())
        if len(qids) == 1:
            return next(iter(qids)), "matched"
        if len(qids) > 1:
            return None, "ambiguous"
    return None, "none"
