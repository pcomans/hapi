"""The TLA 2018 lemma-list extract: personal and royal names, verbatim, with provenance."""

from __future__ import annotations

import collections
import importlib.util
import json
from functools import lru_cache
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parents[1] / "pipeline" / "authority" / "sources" / "tla-2018-names"
CITATION = {"archive_sha256": "886bfd30d81e73bdd0158caa4eb94f9c047eca02ffac4c1a930e170e7265ce5a",
            "license": "CC BY-SA 4.0", "member": "aaew_wlist.json", "urn": "urn:nbn:de:kobv:b4-opus4-29190"}


@lru_cache(maxsize=1)
def rows() -> tuple[dict, ...]:
    return tuple(json.loads(line) for line in (SOURCE_DIR / "reconciled.jsonl").read_text(encoding="utf-8").splitlines())


def fetch_module():
    spec = importlib.util.spec_from_file_location("tla_fetch", SOURCE_DIR / "fetch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def by_id(tla_id: str) -> dict:
    (row,) = [r for r in rows() if r["tla_id"] == tla_id]
    return row


def test_counts_and_shape() -> None:
    assert len(rows()) == 3362
    assert collections.Counter(r["subtype"] for r in rows()) == {"person_name": 2944, "kings_name": 418}
    assert collections.Counter(r["revision_state"] for r in rows()) == {"published": 3280, "published-obsolete": 82}
    assert sum(1 for r in rows() if not r["en"]) == 1504
    assert sum(1 for r in rows() if not r["de"]) == 1
    keys = {"tla_id", "subtype", "transliteration", "de", "en", "revision_state", "source_citation"}
    assert all(set(r) == keys and r["source_citation"] == CITATION and r["transliteration"] for r in rows())
    ids = [r["tla_id"] for r in rows()]
    assert len(set(ids)) == len(ids)
    assert [(r["subtype"], r["tla_id"]) for r in rows()] == sorted((r["subtype"], r["tla_id"]) for r in rows())


def test_the_fetch_pins_the_archive_the_rows_cite() -> None:
    fetch = fetch_module()
    assert fetch.ARCHIVE_SHA256 == CITATION["archive_sha256"]
    assert fetch.URL == "https://edoc.bbaw.de/files/2919/vocabulary.zip"
    assert fetch.SUBTYPES == ("person_name", "kings_name")
    assert CITATION["archive_sha256"] in (SOURCE_DIR / "README.md").read_text(encoding="utf-8")


def test_the_extraction_keeps_names_only_and_fields_verbatim() -> None:
    fetch = fetch_module()
    lemmas = [
        {"_id": "9", "type": "entity_name", "subtype": "person_name", "name": "Tjy", "revisionState": "published",
         "translations": {"translations": [{"lang": "de", "value": "Teje"}, {"lang": "en", "value": "Tiy"},
                                           {"lang": "en"}]}},
        {"_id": "8", "type": "entity_name", "subtype": "gods_name", "name": "Ptḥ"},
        {"_id": "7", "type": "substantive", "subtype": "substantive_masc", "name": "ꜣ"},
    ]
    assert fetch.rows(lemmas) == [{"tla_id": "9", "subtype": "person_name", "transliteration": "Tjy", "de": ["Teje"],
                                   "en": ["Tiy"], "revision_state": "published",
                                   "source_citation": CITATION}]


def test_rows_of_royal_women() -> None:
    assert by_id("600465") == {"tla_id": "600465", "subtype": "person_name", "transliteration": "Jꜥḥ-ms.w-nfr.t-jr.j",
                               "de": ["Ahmes-Nefertari (Frau des Ahmose)"], "en": ["Ahmose-Nofretari (a queen of Ahmose)"],
                               "revision_state": "published", "source_citation": CITATION}
    assert by_id("853479") == {"tla_id": "853479", "subtype": "kings_name", "transliteration": "Tꜣ-wsr.t",
                               "de": ["Ta-useret (Königin)"], "en": ["Ta-useret (queen)"],
                               "revision_state": "published", "source_citation": CITATION}
    assert by_id("600385") == {"tla_id": "600385", "subtype": "person_name", "transliteration": "Ḥn.wt-tꜣ.wj",
                               "de": ["Henut-tawi"], "en": [], "revision_state": "published",
                               "source_citation": CITATION}


def test_one_name_can_be_two_lemmas() -> None:
    """A lemma is a name, not a person, and the same transliteration can be two lemmas."""
    assert (by_id("400020")["subtype"], by_id("400020")["de"]) == ("kings_name", ["Mentuhotep"])
    assert (by_id("400025")["subtype"], by_id("400025")["de"]) == ("person_name", ["Month-hetepu"])
    assert by_id("400020")["transliteration"] == by_id("400025")["transliteration"] == "Mnṯ.w-ḥtp.w"
