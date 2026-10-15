"""The TLA 2018 lemma-list extract: personal and royal names, verbatim, rebuilt from the
committed archive."""

from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
from functools import lru_cache
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parents[1] / "pipeline" / "authority" / "sources" / "tla-2018-names"


@lru_cache(maxsize=1)
def fetch():
    spec = importlib.util.spec_from_file_location("tla_fetch", SOURCE_DIR / "fetch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def lines() -> tuple[dict, ...]:
    return tuple(json.loads(line) for line in (SOURCE_DIR / "reconciled.jsonl").read_text(encoding="utf-8").splitlines())


def rows() -> tuple[dict, ...]:
    return lines()[1:]


def by_id(tla_id: str) -> dict:
    (row,) = [r for r in rows() if r["tla_id"] == tla_id]
    return row


def test_the_committed_archive_is_the_pinned_one_and_rebuilds_the_extract() -> None:
    archive = (SOURCE_DIR / "vocabulary.zip").read_bytes()
    assert len(archive) == 11_268_762
    assert hashlib.sha256(archive).hexdigest() == fetch().ARCHIVE_SHA256 == lines()[0]["_source"]["archive_sha256"]
    lemmas = fetch().lemmas()
    assert len(lemmas) == 38_775
    assert fetch().serialise(fetch().rows(lemmas)) == (SOURCE_DIR / "reconciled.jsonl").read_text(encoding="utf-8")
    left_out = collections.Counter(l.get("subtype") for l in lemmas
                                   if l.get("type") == "entity_name" and l.get("subtype") not in fetch().SUBTYPES)
    assert left_out == {"gods_name": 3319, "place_name": 1747, "artifact_name": 650, "org_name": 489,
                        "animal_name": 19, None: 8}


def test_the_source_header() -> None:
    assert lines()[0] == {"_source": {
        "archive_sha256": "886bfd30d81e73bdd0158caa4eb94f9c047eca02ffac4c1a930e170e7265ce5a",
        "citation": ("Teilauszug der Datenbank des Vorhabens „Strukturen und Transformationen des Wortschatzes "
                     "der ägyptischen Sprache“ vom Januar 2018, ed. T. S. Richter & I. Hafemann (BBAW) and "
                     "H.-W. Fischer-Elfert & P. Dils (SAW Leipzig), 2018"),
        "license": "CC BY-SA 4.0", "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "member": "aaew_wlist.json", "raw_file": "sources/tla-2018-names/vocabulary.zip", "retrieved": "2026-10-15",
        "url": "https://edoc.bbaw.de/files/2919/vocabulary.zip", "urn": "urn:nbn:de:kobv:b4-opus4-29190"}}


def test_counts_as_the_readme_states() -> None:
    assert len(rows()) == 3362
    assert collections.Counter(r["subtype"] for r in rows()) == {"person_name": 2944, "kings_name": 418}
    assert collections.Counter(r["revision_state"] for r in rows()) == {"published": 3280, "published-obsolete": 82}
    translations = collections.Counter((t["lang"], "value" in t, bool(t.get("value"))) for r in rows()
                                       for t in r["translations"])
    assert translations == {("de", True, True): 3362, ("en", True, True): 1858, ("en", True, False): 322,
                            ("en", False, False): 33}
    assert collections.Counter(rel.get("type") for r in rows() for rel in r["relations"]) == {
        "successor": 93, "referencedBy": 91, "referencing": 85, "contains": 5, "partOf": 5, None: 1}
    obsolete = [r for r in rows() if r["revision_state"] == "published-obsolete"]
    assert all(any(rel.get("type") == "referencing" for rel in r["relations"]) for r in obsolete)


def test_the_extraction_copies_fields_verbatim_and_names_the_typeless_lemmas() -> None:
    import pytest
    typeless = [{"_id": "867767"}, {"_id": "873713"}]
    lemma = {"_id": "9", "type": "entity_name", "subtype": "person_name", "name": "Tjy", "revisionState": "published",
             "translations": {"translations": [{"lang": "de", "value": "Teje", "eClass": "x"}, {"lang": "en"}]},
             "relations": [{"type": "referencing", "objectId": "1", "_id": "y", "eClass": "z"}, {"_id": "w"}]}
    others = [{"_id": "8", "type": "entity_name", "subtype": "gods_name"}, {"_id": "7", "type": "substantive"}]
    assert fetch().rows([lemma, *others, *typeless]) == [{
        "tla_id": "9", "subtype": "person_name", "transliteration": "Tjy",
        "translations": [{"lang": "de", "value": "Teje"}, {"lang": "en"}],
        "relations": [{"type": "referencing", "objectId": "1"}, {}], "revision_state": "published"}]
    with pytest.raises(ValueError, match="lemmas without a type"):
        fetch().rows([lemma, {"_id": "5"}, *typeless])


def test_rows_of_royal_women_and_names_shared_by_lemmas() -> None:
    assert by_id("600465") == {"tla_id": "600465", "subtype": "person_name", "transliteration": "Jꜥḥ-ms.w-nfr.t-jr.j",
                               "translations": [{"lang": "de", "value": "Ahmes-Nefertari (Frau des Ahmose)"},
                                                {"lang": "en", "value": "Ahmose-Nofretari (a queen of Ahmose)"}],
                               "relations": [{"objectId": "853140", "type": "referencedBy"}],
                               "revision_state": "published"}
    assert by_id("853479") == {"tla_id": "853479", "subtype": "kings_name", "transliteration": "Tꜣ-wsr.t",
                               "translations": [{"lang": "de", "value": "Ta-useret (Königin)"},
                                                {"lang": "en", "value": "Ta-useret (queen)"}],
                               "relations": [], "revision_state": "published"}
    assert by_id("600348") == {"tla_id": "600348", "subtype": "person_name", "transliteration": "Tjy",
                               "translations": [{"lang": "de", "value": "Teje"}, {"lang": "en", "value": "Tiy"}],
                               "relations": [{"objectId": "708799", "type": "referencing"}],
                               "revision_state": "published-obsolete"}
    assert sorted(r["tla_id"] for r in rows() if r["transliteration"] == "Tjy") == ["600348", "708792", "708799"]
    assert (by_id("400020")["subtype"], by_id("400025")["subtype"]) == ("kings_name", "person_name")
    assert by_id("400020")["transliteration"] == by_id("400025")["transliteration"] == "Mnṯ.w-ḥtp.w"
