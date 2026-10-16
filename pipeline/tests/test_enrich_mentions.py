"""The production mention extractor (#338) is #361's, promoted: every definition it shares with
the frozen #361 script has the same source, and on the museum fixtures and records written to
reach its branches it gives exactly what that script gives.
(`docs/evaluations/authority-bridge-338/results/promotion-check.json` holds the same on the
whole frozen corpus: 148,964 mentions, row for row.)"""

from __future__ import annotations

import importlib.util
import inspect
import json
import re
import sys
from pathlib import Path

import pytest

from pipeline.assets.normalize import cleveland, walters
from pipeline.assets.normalize.brooklyn import BrooklynMapper
from pipeline.assets.normalize.harvard import HarvardMapper
from pipeline.assets.normalize.met import MetMapper
from pipeline.enrich import mentions as production

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "docs/evaluations/ruler-reregistration-2026-10-15/scripts/extract_mentions.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
MAPPERS = {"met": (MetMapper, None), "brooklyn": (BrooklynMapper, None), "harvard": (HarvardMapper, None)}
# The museums whose readers came after #361, with the rule their normalize step keeps a record by.
ADDED = {"cleveland": (cleveland.ClevelandMapper, cleveland.is_egyptian), "walters": (walters.WaltersMapper, walters.is_egyptian)}


@pytest.fixture(scope="module")
def frozen():
    spec = importlib.util.spec_from_file_location("_frozen_361_extract_mentions", FROZEN)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def corpus(extra: dict[str, list[dict]] | None = None, with_cleveland: bool = False,
           with_walters: bool = False) -> tuple[list[dict], dict[str, dict[str, dict]]]:
    """The museum fixtures as a corpus: #361's three museums, and the Cleveland and Walters
    fixtures that their normalize steps keep when `with_cleveland` / `with_walters` (else their
    raw indexes are empty, as a run reads an empty table)."""
    canonical, raw = [], {m: {} for m in (*MAPPERS, *ADDED)}
    museums = {**MAPPERS, **{m: ADDED[m] for m, on in (("cleveland", with_cleveland), ("walters", with_walters)) if on}}
    for museum, (mapper, keep) in museums.items():
        payloads = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((FIXTURES / museum).glob("*.json"))]
        for payload in payloads + (extra or {}).get(museum, []):
            if keep is not None and not keep(payload):
                continue
            artifact = mapper().map_to_canonical(payload).model_dump()
            canonical.append(artifact)
            raw[museum][artifact["source_id"]] = payload
    return canonical, raw


# Records that reach the grammar's branches the fixtures may not: royal-woman cues, an
# uncertain and a multi-king cue, a range reign, tomb codes and a temple.
EXTRA = {
    "met": [
        {"objectID": 900001, "title": "Scarab of Queen Ahmose, Mother of Hatshepsut", "reign": "reign of Amenhotep III",
         "dynasty": "Dynasty 18", "geographyType": "From Egypt", "country": "Egypt",
         "subregion": "Thebes, Valley of the Kings (KV 62)", "locale": "Temple of Hatshepsut",
         "excavation": "Carnarvon/Carter excavations", "objectURL": "https://example.org/900001",
         "isPublicDomain": True},
        {"objectID": 900002, "title": "Relief of King's Great Wife Tiye and King Amenhotep III or Akhenaten",
         "reign": "probably reign of Thutmose IV", "objectURL": "https://example.org/900002", "isPublicDomain": False},
        {"objectID": 900003, "title": "Stela of God's Wife of Amun Shepenwepet", "reign": "reign of Taharqa to Tanutamun",
         "objectURL": "https://example.org/900003", "isPublicDomain": False},
    ],
}


def test_the_production_extractor_gives_what_361s_gives(frozen) -> None:
    canonical, raw = corpus(EXTRA)
    found, diagnostics = production.extract_mentions(canonical, raw)
    expected, expected_diagnostics = frozen.extract_mentions(canonical, raw)
    assert found == expected and diagnostics == expected_diagnostics
    # The extra records reach the branches they were written for.
    by_text = {(m["artifact_id"], m["mention_text"]): m for m in found}
    assert (by_text["met-900001", "Ahmose"]["evidence_role"], by_text["met-900001", "Ahmose"]["record_dynasty"]) == (
        "explicit_royal_text_cue", "Dynasty 18")
    assert by_text["met-900001", "Amenhotep III"]["extraction_method"] == "typed_structured_reign_parser"
    assert by_text["met-900001", "KV 62"]["entity_type"] == "tomb_monument"
    assert by_text["met-900001", "Temple of Hatshepsut"]["entity_type"] == "temple"
    assert by_text["met-900001", "Carnarvon/Carter excavations"]["entity_type"] == "excavation"
    assert by_text["met-900002", "probably reign of Thutmose IV"]["expression_type"] == "uncertain_identity"
    assert by_text["met-900002", "Tiye"]["expression_type"] == "multi_or_range"
    assert by_text["met-900003", "reign of Taharqa to Tanutamun"]["expression_type"] == "multi_or_range"
    assert by_text["met-900003", "Shepenwepet"]["expression_type"] == "single_identity"
    assert {m["museum"] for m in found} == {"met", "brooklyn", "harvard"}


ADDED_FOR_CLEVELAND = ("JOINT_REIGN", "cleveland_reign_components", "without_trailing_dates", "cleveland_mentions",
                       "extract_all_mentions")
ADDED_FOR_WALTERS = ("walters_reign_expression", "royal_cue_mentions", "WALTERS_REIGN_FIELD", "WALTERS_CUE_FIELDS",
                     "walters_mentions", "ADDED_READERS")


def test_every_definition_is_361s_verbatim(frozen) -> None:
    """The promotion is a copy: the first edit to a promoted definition fails here, and must
    also change this test and the claim of identity in `mentions.py` and the #338 README.
    The Cleveland and Walters readers and the function that joins them to #361's are additions,
    not edits."""
    imported = {"annotations", "hashlib", "re", "Counter", "Iterable"}
    names = [n for n in vars(production) if not n.startswith("_") and n not in imported]
    assert sorted(names) == sorted([
        "ROYAL_CUE", "TOMB_CODE", "TEMPLE_CUE", "UNCERTAIN", "RANGE_OR_MULTI", "TEMPORAL_CONTEXT", "LEADING_REIGN",
        "LEADING_UNCERTAIN_REIGN", "TRAILING_PHASE", "NAME_TOKEN", "TEXT_STOP", "classify_reign_expression",
        "candidate_after_royal_cue", "component_spans", "component_variants", "make_mention", "extract_mentions",
        *ADDED_FOR_CLEVELAND, *ADDED_FOR_WALTERS])
    for name in sorted(set(names) - set(ADDED_FOR_CLEVELAND) - set(ADDED_FOR_WALTERS)):
        ours, theirs = getattr(production, name), getattr(frozen, name)
        if isinstance(ours, re.Pattern):
            assert (ours.pattern, ours.flags) == (theirs.pattern, theirs.flags), name
        elif inspect.isfunction(ours):
            assert inspect.getsource(ours) == inspect.getsource(theirs), name
        else:
            assert ours == theirs, name


def _cleveland(culture: str) -> dict:
    payload = json.loads((FIXTURES / "cleveland" / "rich_object.json").read_text(encoding="utf-8"))
    return {**payload, "culture": [culture]}


def test_without_cleveland_or_walters_records_the_join_is_361s_extractor() -> None:
    canonical, raw = corpus(EXTRA)
    assert production.extract_all_mentions(canonical, raw) == production.extract_mentions(canonical, raw)


def test_cleveland_mentions_are_its_catalogued_reigns() -> None:
    """Each fixture's reign component: the single identity's name, in its culture entry."""
    canonical, raw = corpus(with_cleveland=True)
    found, diagnostics = production.extract_all_mentions(canonical, raw)
    ours = [(m["artifact_id"], m["field_path"], m["span_start"], m["span_end"], m["mention_text"], m["expression_type"],
             m["extraction_method"], m["evidence_role"], m["record_dynasty"]) for m in found if m["museum"] == "cleveland"]
    assert ours == [
        ("cleveland-101390", "culture[0]", 68, 81, "Tuthmosis III", "single_identity",
         "typed_structured_reign_parser", "catalogued_reign", "Dynasty 18"),
        ("cleveland-130133", "culture[0]", 57, 70, "Amenhotep III", "single_identity",
         "typed_structured_reign_parser", "catalogued_reign", "Dynasty 18"),
    ]
    others, other_diagnostics = production.extract_mentions(
        [row for row in canonical if row["source_museum"] != "cleveland"], raw)
    assert [m for m in found if m["museum"] != "cleveland"] == others
    assert diagnostics == {**other_diagnostics, "records_scanned": len(canonical),
                           "records_with_at_least_one_mention": other_diagnostics["records_with_at_least_one_mention"] + 2,
                           "mentions": len(others) + 2,
                           "mentions_by_museum": {**other_diagnostics["mentions_by_museum"], "cleveland": 2},
                           "mentions_by_entity_type": {**other_diagnostics["mentions_by_entity_type"],
                                                       "ruler": other_diagnostics["mentions_by_entity_type"]["ruler"] + 2}}


@pytest.mark.parametrize("culture, text, expression", [
    # A range keeps both ends: only the last parenthesis (the second reign's dates) is cut.
    ("Egypt, New Kingdom (1540–1069 BCE), Dynasty 18, reign of Tuthmosis III (1479–1425 BCE)–reign of Amenhotep III "
     "(1390–1352 BCE)", "reign of Tuthmosis III (1479–1425 BCE)–reign of Amenhotep III", "multi_or_range"),
    ("Egypt, Old Kingdom (2647–2124 BCE), Dynasty 5, reign of Nyuserre (2445–2422 BCE) or later",
     "reign of Nyuserre (2445–2422 BCE) or later", "temporal_context"),
    ("Egypt, Middle Kingdom (2030–1650 BCE), Dynasty 12, probably reign of Senusret I",
     "probably reign of Senusret I", "uncertain_identity"),
    ("Egypt, Middle Kingdom (2030–1650 BCE), Dynasty 12, reign of Amenemhat II to Sesostris III",
     "reign of Amenemhat II to Sesostris III", "multi_or_range"),
    # A doubt mark is not dates: it stays, and the reign is uncertain.
    ("Egypt, Dynasty 19, reign of Ramesses II(?)", "reign of Ramesses II(?)", "uncertain_identity"),
    # A joint reign is read whole, never as one ruler.
    ("Egypt, Dynasty 18, joint reign of Hatshepsut and Tuthmosis III",
     "joint reign of Hatshepsut and Tuthmosis III", "unparsed_structured_value"),
    # A doubtful place does not make the reign doubtful.
    ("Egypt, Thebes(?), Dynasty 21, reign of Osorkon I (924–889 BCE)", "Osorkon I", "single_identity"),
])
def test_a_cleveland_reign_that_is_not_one_ruler_is_kept_whole(culture, text, expression) -> None:
    payload = _cleveland(culture)
    artifact = cleveland.ClevelandMapper().map_to_canonical(payload).model_dump()
    (mention,) = production.cleveland_mentions(artifact, payload)
    assert (mention["mention_text"], mention["expression_type"]) == (text, expression)
    assert culture[mention["span_start"]:mention["span_end"]] == text


def test_a_cleveland_record_without_a_reign_has_no_mention() -> None:
    payload = json.loads((FIXTURES / "cleveland" / "sparse_no_image.json").read_text(encoding="utf-8"))
    artifact = cleveland.ClevelandMapper().map_to_canonical(payload).model_dump()
    assert production.cleveland_mentions(artifact, payload) == []


def test_royal_cue_mentions_is_the_extractors_cue_grammar() -> None:
    """The one-field cue reader the Walters uses gives, field by field, exactly the cue mentions
    and the cues without a name that `extract_mentions` gives on the museums it reads."""
    brooklyn = json.loads(sorted((FIXTURES / "brooklyn").glob("*.json"))[0].read_text(encoding="utf-8"))
    # A record reaching the loop's other branches: a cue in several fields, a cue with no name, a
    # possessive cue ("King's"), the same name cued twice, a doubt and a range.
    brooklyn = {**brooklyn, "sourceId": 900010, "title": "Statue of King", "inscribed": "King's sandals; King Seti I (?)",
                "dates": "reign of Ramesses II to Merenptah", "objectDate": "Pharaoh Pharaoh Taharqa",
                "provenance": "Queen Mother Tiye, then Princess Meritamun"}
    canonical, raw = corpus({**EXTRA, "brooklyn": [brooklyn]})
    found, diagnostics = production.extract_mentions(canonical, raw)
    fields = {"met": ("title",), "brooklyn": ("title", "inscribed", "dates", "objectDate", "provenance"),
              "harvard": ("title", "description", "labeltext", "commentary", "dated", "contextualtext")}
    ours, missed = [], {}
    for artifact in canonical:
        payload = raw[artifact["source_museum"]][artifact["source_id"]]
        for field in fields[artifact["source_museum"]]:
            value = payload.get(field)
            if isinstance(value, str) and value.strip():
                cued, misses = production.royal_cue_mentions(artifact, field, value)
                ours += cued
                if misses:
                    key = f"{artifact['source_museum']}|{field}"
                    missed[key] = missed.get(key, 0) + misses
    theirs = [m for m in found if m["extraction_method"] == "explicit_royal_cue_grammar"]
    assert sorted((m["artifact_id"], m["field_path"], m["mention_text"], m["expression_type"])
                  for m in theirs if m["artifact_id"] == "brooklyn-900010") == [
        ("brooklyn-900010", "dates", "Ramesses II", "multi_or_range"),
        ("brooklyn-900010", "inscribed", "Seti I", "uncertain_identity"),
        ("brooklyn-900010", "objectDate", "Pharaoh Taharqa", "single_identity"),
        ("brooklyn-900010", "objectDate", "Taharqa", "single_identity"),
        ("brooklyn-900010", "provenance", "Meritamun", "single_identity"),
        ("brooklyn-900010", "provenance", "Tiye", "single_identity"),
    ]
    key = lambda m: (m["artifact_id"], m["field_path"], m["span_start"], m["span_end"])  # noqa: E731
    assert sorted(ours, key=key) == sorted(theirs, key=key)
    assert missed == diagnostics["royal_cues_without_syntactic_candidate"]


def test_walters_mentions_are_its_reign_and_its_title_and_date_cues() -> None:
    canonical, raw = corpus(with_walters=True)
    found, diagnostics = production.extract_all_mentions(canonical, raw)
    ours = [(m["artifact_id"], m["field_path"], m["span_start"], m["span_end"], m["mention_text"], m["expression_type"],
             m["extraction_method"], m["record_dynasty"]) for m in found if m["museum"] == "walters"]
    reign, cue = "typed_structured_reign_parser", "explicit_royal_cue_grammar"
    assert ours == [
        ("walters-1605", "object.DateText", 53, 62, "Psamtek I", "single_identity", cue, "26th Dynasty"),
        # A hyphen without spaces is not a range: one name, which no ruler matches.
        ("walters-1605", "object.Reign", 0, 19, "Psametik I-Necho II", "single_identity", reign, "26th Dynasty"),
        ("walters-24458", "object.Reign", 0, 48, "Shabako (715-700 BC), Psammetichus I (664-10 BC)", "multi_or_range",
         reign, "25th-26th Dynasty"),
        ("walters-481", "object.DateText", 50, 63, "Amenhotep III", "single_identity", cue, "18th Dynasty"),
        ("walters-481", "object.Reign", 0, 13, "Amenhotep III", "single_identity", reign, "18th Dynasty"),
        ("walters-481", "object.Title", 43, 47, "Tiye", "multi_or_range", cue, "18th Dynasty"),
        ("walters-5104", "object.Reign", 0, 24, "Seti I (1290-1279/8) (?)", "uncertain_identity", reign, "19th Dynasty"),
    ]
    assert {m["evidence_role"] for m in found if m["museum"] == "walters" and m["extraction_method"] == reign} == {
        "catalogued_reign"}
    others, other_diagnostics = production.extract_mentions(
        [row for row in canonical if row["source_museum"] != "walters"], raw)
    assert [m for m in found if m["museum"] != "walters"] == others
    # "Kneeling King" (walters-1200): a cue with no name after it.
    assert diagnostics["royal_cues_without_syntactic_candidate"] == {
        **other_diagnostics["royal_cues_without_syntactic_candidate"], "walters|object.Title": 1}
    assert diagnostics["mentions_by_museum"] == {**other_diagnostics["mentions_by_museum"], "walters": 7}


@pytest.mark.parametrize("reign, text, expression", [
    ("Ramesses II (1279-1213 BC)", "Ramesses II", "single_identity"),
    ("Thutmose III", "Thutmose III", "single_identity"),
    # The doubt mark is the final parenthesis, so the dates before it stay; the reign is uncertain.
    ("Amenhotep III (1388-1348 BC) (?)", "Amenhotep III (1388-1348 BC) (?)", "uncertain_identity"),
    ("Tutankhamen or Ay", "Tutankhamen or Ay", "multi_or_range"),
    ("Ptolemy II Philadelphos; Ptolemy IV Philopator", "Ptolemy II Philadelphos; Ptolemy IV Philopator",
     "multi_or_range"),
    ("Sesostris III-Amenemhat III, Ramesses II", "Sesostris III-Amenemhat III, Ramesses II", "multi_or_range"),
    # Only the final parenthesis is cut.
    ("Apries (589-570 BC)-Amasis (570-526 BC)", "Apries (589-570 BC)-Amasis", "single_identity"),
    ("Kashtar (ca. 746 BC)", "Kashtar", "single_identity"),
    ("Ramesses II-Merenptah", "Ramesses II-Merenptah", "single_identity"),
])
def test_a_walters_reign_is_read_as_the_mets(reign, text, expression) -> None:
    payload = json.loads((FIXTURES / "walters" / "rich_object.json").read_text(encoding="utf-8"))
    payload = {**payload, "object": {**payload["object"], "Reign": reign, "Title": "Vase", "DateText": "ca. 1370 BCE"}}
    artifact = walters.WaltersMapper().map_to_canonical(payload).model_dump()
    (mention,), missed = production.walters_mentions(artifact, payload)
    assert (mention["mention_text"], mention["expression_type"]) == (text, expression)
    assert reign[mention["span_start"]:mention["span_end"]] == text
    assert not missed


def test_a_walters_record_without_a_reign_or_cue_has_no_mention() -> None:
    payload = json.loads((FIXTURES / "walters" / "sparse_no_image.json").read_text(encoding="utf-8"))
    artifact = walters.WaltersMapper().map_to_canonical(payload).model_dump()
    assert production.walters_mentions(artifact, payload) == ([], {})
