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

from pipeline.assets.normalize.brooklyn import BrooklynMapper
from pipeline.assets.normalize.harvard import HarvardMapper
from pipeline.assets.normalize.met import MetMapper
from pipeline.enrich import mentions as production

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "docs/evaluations/ruler-reregistration-2026-10-15/scripts/extract_mentions.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
MAPPERS = {"met": MetMapper, "brooklyn": BrooklynMapper, "harvard": HarvardMapper}


@pytest.fixture(scope="module")
def frozen():
    spec = importlib.util.spec_from_file_location("_frozen_361_extract_mentions", FROZEN)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def corpus(extra: dict[str, list[dict]] | None = None) -> tuple[list[dict], dict[str, dict[str, dict]]]:
    canonical, raw = [], {m: {} for m in MAPPERS}
    for museum, mapper in MAPPERS.items():
        payloads = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((FIXTURES / museum).glob("*.json"))]
        for payload in payloads + (extra or {}).get(museum, []):
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


def test_every_definition_is_361s_verbatim(frozen) -> None:
    """The promotion is a copy: the first edit to a promoted definition fails here, and must
    also change this test and the claim of identity in `mentions.py` and the #338 README."""
    imported = {"annotations", "hashlib", "re", "Counter", "Iterable"}
    names = [n for n in vars(production) if not n.startswith("_") and n not in imported]
    assert sorted(names) == sorted([
        "ROYAL_CUE", "TOMB_CODE", "TEMPLE_CUE", "UNCERTAIN", "RANGE_OR_MULTI", "TEMPORAL_CONTEXT", "LEADING_REIGN",
        "LEADING_UNCERTAIN_REIGN", "TRAILING_PHASE", "NAME_TOKEN", "TEXT_STOP", "classify_reign_expression",
        "candidate_after_royal_cue", "component_spans", "component_variants", "make_mention", "extract_mentions"])
    for name in names:
        ours, theirs = getattr(production, name), getattr(frozen, name)
        if isinstance(ours, re.Pattern):
            assert (ours.pattern, ours.flags) == (theirs.pattern, theirs.flags), name
        elif inspect.isfunction(ours):
            assert inspect.getsource(ours) == inspect.getsource(theirs), name
        else:
            assert ours == theirs, name
