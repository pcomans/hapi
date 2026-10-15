"""Fetch the Thesaurus Linguae Aegyptiae (TLA) lemma list of January 2018 and extract its
personal and royal names.

Source: "Teilauszug der Datenbank des Vorhabens 'Strukturen und Transformationen des
Wortschatzes der ägyptischen Sprache' vom Januar 2018", ed. Tonio Sebastian Richter & Ingelore
Hafemann (BBAW) and Hans-Werner Fischer-Elfert & Peter Dils (SAW Leipzig), 2018,
urn:nbn:de:kobv:b4-opus4-29190, CC BY-SA 4.0. The archive `vocabulary.zip` holds the lemma
list `aaew_wlist.json` (38,775 lemmas); this script keeps the lemmas of type `entity_name`
with subtype `person_name` or `kings_name`, each field verbatim.

    cd pipeline && uv run python pipeline/authority/sources/tla-2018-names/fetch.py

Writes `reconciled.jsonl` (committed) and keeps the archive in `raw/` (gitignored).
"""

from __future__ import annotations

import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
URL = "https://edoc.bbaw.de/files/2919/vocabulary.zip"
ARCHIVE = SOURCE_DIR / "raw" / "vocabulary.zip"
ARCHIVE_SHA256 = "886bfd30d81e73bdd0158caa4eb94f9c047eca02ffac4c1a930e170e7265ce5a"
MEMBER = "aaew_wlist.json"
SUBTYPES = ("person_name", "kings_name")
OUT = SOURCE_DIR / "reconciled.jsonl"


def archive_bytes() -> bytes:
    if not ARCHIVE.exists():
        with urllib.request.urlopen(URL, timeout=120) as response:
            ARCHIVE.write_bytes(response.read())
    data = ARCHIVE.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != ARCHIVE_SHA256:
        raise ValueError(f"{ARCHIVE} has SHA-256 {digest}, not the pinned {ARCHIVE_SHA256}")
    return data


def translations(lemma: dict, lang: str) -> list[str]:
    return [t["value"] for t in (lemma.get("translations") or {}).get("translations", [])
            if t.get("lang") == lang and t.get("value")]


def rows(lemmas: list[dict]) -> list[dict]:
    out = []
    for lemma in lemmas:
        if lemma.get("type") != "entity_name" or lemma.get("subtype") not in SUBTYPES:
            continue
        out.append({
            "tla_id": lemma["_id"],
            "subtype": lemma["subtype"],
            "transliteration": lemma["name"],
            "de": translations(lemma, "de"),
            "en": translations(lemma, "en"),
            "revision_state": lemma.get("revisionState"),
            "source_citation": {"urn": "urn:nbn:de:kobv:b4-opus4-29190", "member": MEMBER,
                                "archive_sha256": ARCHIVE_SHA256, "license": "CC BY-SA 4.0"},
        })
    ids = [r["tla_id"] for r in out]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate TLA lemma ids")
    return sorted(out, key=lambda r: (r["subtype"], r["tla_id"]))


def main() -> None:
    with zipfile.ZipFile(io.BytesIO(archive_bytes())) as archive:
        lemmas = json.loads(archive.read(MEMBER).decode("utf-8"))
    extracted = rows(lemmas)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in extracted),
                   encoding="utf-8")
    print(f"{len(lemmas)} lemmas; wrote {len(extracted)} names to {OUT}")


if __name__ == "__main__":
    main()
