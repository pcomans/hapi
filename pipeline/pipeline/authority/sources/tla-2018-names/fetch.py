"""Fetch the Thesaurus Linguae Aegyptiae (TLA) lemma list of January 2018 and extract its
personal and royal names.

Source: "Teilauszug der Datenbank des Vorhabens 'Strukturen und Transformationen des
Wortschatzes der ägyptischen Sprache' vom Januar 2018", ed. Tonio Sebastian Richter & Ingelore
Hafemann (BBAW) and Hans-Werner Fischer-Elfert & Peter Dils (SAW Leipzig), 2018,
urn:nbn:de:kobv:b4-opus4-29190, CC BY-SA 4.0. The archive `vocabulary.zip` (committed here,
as the licence allows) holds the lemma list `aaew_wlist.json`, 38,775 lemmas. This script keeps
the lemmas of type `entity_name` with subtype `person_name` or `kings_name`, and copies their
name, translations and relations verbatim.

    cd pipeline && uv run python pipeline/authority/sources/tla-2018-names/fetch.py

The archive is downloaded only if it is not here; either way its SHA-256 must be the pinned one.
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
ARCHIVE = SOURCE_DIR / "vocabulary.zip"
ARCHIVE_SHA256 = "886bfd30d81e73bdd0158caa4eb94f9c047eca02ffac4c1a930e170e7265ce5a"
MEMBER = "aaew_wlist.json"
SUBTYPES = ("person_name", "kings_name")
OUT = SOURCE_DIR / "reconciled.jsonl"
SOURCE = {
    "citation": ("Teilauszug der Datenbank des Vorhabens „Strukturen und Transformationen des Wortschatzes "
                 "der ägyptischen Sprache“ vom Januar 2018, ed. T. S. Richter & I. Hafemann (BBAW) and "
                 "H.-W. Fischer-Elfert & P. Dils (SAW Leipzig), 2018"),
    "urn": "urn:nbn:de:kobv:b4-opus4-29190",
    "url": URL,
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "retrieved": "2026-10-15",
    "raw_file": "sources/tla-2018-names/vocabulary.zip",
    "archive_sha256": ARCHIVE_SHA256,
    "member": MEMBER,
}
# The lemma list's two entries without a `type` (867767 "py", 873713 "ḫꜣw"): neither is a name.
TYPELESS = {"867767", "873713"}


def archive_bytes() -> bytes:
    data = ARCHIVE.read_bytes() if ARCHIVE.exists() else urllib.request.urlopen(URL, timeout=120).read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != ARCHIVE_SHA256:
        raise ValueError(f"vocabulary.zip has SHA-256 {digest}, not the pinned {ARCHIVE_SHA256}")
    if not ARCHIVE.exists():
        ARCHIVE.write_bytes(data)
    return data


def lemmas() -> list[dict]:
    with zipfile.ZipFile(io.BytesIO(archive_bytes())) as archive:
        return json.loads(archive.read(MEMBER).decode("utf-8"))


def _verbatim(entries: list[dict], keys: tuple[str, ...]) -> list[dict]:
    """The entries with only `keys`, each kept exactly as present or absent in the source."""
    return [{k: e[k] for k in keys if k in e} for e in entries]


def rows(all_lemmas: list[dict]) -> list[dict]:
    typeless = {lemma["_id"] for lemma in all_lemmas if "type" not in lemma}
    if typeless != TYPELESS:
        raise ValueError(f"lemmas without a type: {sorted(typeless)}, expected {sorted(TYPELESS)}")
    out = []
    for lemma in all_lemmas:
        if lemma["_id"] in TYPELESS or lemma["type"] != "entity_name" or lemma.get("subtype") not in SUBTYPES:
            continue
        out.append({
            "tla_id": lemma["_id"],
            "subtype": lemma["subtype"],
            "transliteration": lemma["name"],
            "translations": _verbatim(lemma["translations"]["translations"], ("lang", "value")),
            "relations": _verbatim(lemma.get("relations", []), ("type", "objectId")),
            "revision_state": lemma["revisionState"],
        })
    ids = [r["tla_id"] for r in out]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate TLA lemma ids")
    return sorted(out, key=lambda r: (r["subtype"], r["tla_id"]))


def serialise(extracted: list[dict]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in [{"_source": SOURCE}, *extracted])


def main() -> None:
    all_lemmas = lemmas()
    extracted = rows(all_lemmas)
    OUT.write_text(serialise(extracted), encoding="utf-8")
    print(f"{len(all_lemmas)} lemmas; wrote {len(extracted)} names to {OUT}")


if __name__ == "__main__":
    main()
