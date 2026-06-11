"""Foundation tests: vendored-spec catalogue + predicate registry.

Asserts specific values against the real vendored CRM 7.1.3 / CRMdig 5.0 RDFS
and the committed predicate_registry.json (Constitutional rule 5 — assert values,
not absence of errors).
"""

from __future__ import annotations

import pytest

from pipeline.authority.graph.cidoc_spec import load_catalogue
from pipeline.authority.graph.registry import (
    Predicate,
    derived_predicates,
    load_registry,
    primary_predicates,
)


# --------------------------------------------------------------------------
# CIDOC catalogue parsed from the vendored RDFS
# --------------------------------------------------------------------------
def test_core_crm_classes_present():
    cat = load_catalogue()
    for code in ["E1", "E4", "E13", "E21", "E27", "E31", "E39", "E41", "E52", "E55", "E74"]:
        assert cat.has_class(code), f"CRM class {code} missing from catalogue"


def test_crmdig_classes_and_properties_present():
    cat = load_catalogue()
    for code in ["D1", "D7", "D10", "D14"]:
        assert cat.has_class(code), f"CRMdig class {code} missing"
    for code in ["L10", "L11", "L23", "L54"]:
        assert cat.has_property(code), f"CRMdig property {code} missing"


def test_core_crm_properties_present():
    cat = load_catalogue()
    for code in ["P14", "P70i", "P140", "P141", "P177", "P190"]:
        assert cat.has_property(code), f"CRM property {code} missing"


def test_is_a_chains():
    cat = load_catalogue()
    # E21 Person IS-A E1 CRM Entity (E21 ⊂ E20 ⊂ E19 ⊂ E18 ⊂ ... ⊂ E1).
    assert cat.is_a("E21_Person", "E1_CRM_Entity")
    # E13 Attribute Assignment IS-A E1 (satisfies P140/P141 E1 range).
    assert cat.is_a("E13_Attribute_Assignment", "E1_CRM_Entity")
    # D10 Software Execution IS-A E7 Activity (D10 ⊂ D7 ⊂ E11/E65 ⊂ E7).
    assert cat.is_a("D10_Software_Execution", "E7_Activity")
    # Negative control: E27 Site is NOT IS-A E53 Place (the reason the tomb
    # predicates can't subPropertyOf P53 — ADR-018 § Implications for matching).
    assert not cat.is_a("E27_Site", "E53_Place")


def test_hapi_extension_terms_present():
    cat = load_catalogue()
    for cls in ["MatcherRun", "MatcherAlgorithm", "SourceData"]:
        assert cat.has_class(cls), f"hapi class {cls} missing from manifest parse"
    for prop in ["same_entity_as", "derived_by_run", "supersedes", "matcher_review_verdict"]:
        assert cat.has_property(prop), f"hapi predicate {prop} missing"


# --------------------------------------------------------------------------
# Predicate registry
# --------------------------------------------------------------------------
def test_registry_loads_all_predicates():
    reg = load_registry()
    expected = {
        "hapi:same_entity_as",
        "hapi:in_dynastic_period",
        "hapi:tomb_owner",
        "hapi:original_burial_in",
        "hapi:cache_context_at",
        "hapi:display_name",
        "hapi:reign_period",
        "hapi:horus_name",
        "hapi:matcher_review_verdict",
        "hapi:shares_tomb_with",
    }
    assert set(reg) == expected


def test_same_entity_as_entry():
    p: Predicate = load_registry()["hapi:same_entity_as"]
    assert p.subject_class == "E1"
    assert p.value_class == "E1"
    assert p.is_symmetric is True
    assert p.derived is False
    assert p.p177_target is True
    assert p.emit_shortcut is True
    assert p.crm_nearest == "L54_is_same_as"
    assert p.value_cardinality == "multi"


def test_shares_tomb_with_is_derived_and_not_p177_target():
    p = load_registry()["hapi:shares_tomb_with"]
    assert p.derived is True
    assert p.p177_target is False
    assert p.emit_shortcut is False
    assert p.is_symmetric is True
    assert p.crm_nearest is None


def test_verdict_predicate_does_not_emit_shortcut():
    p = load_registry()["hapi:matcher_review_verdict"]
    assert p.p177_target is True
    assert p.emit_shortcut is False  # gating-recursion + vocabulary not a query target
    assert p.subject_class == "E13"
    assert p.value_class == "E55"
    assert p.crm_nearest == "L43_annotates"


def test_primary_and_derived_partition():
    primary = primary_predicates()
    derived = derived_predicates()
    assert len(primary) == 9
    assert len(derived) == 1
    assert "hapi:shares_tomb_with" in derived
    assert "hapi:shares_tomb_with" not in primary
    # The two partitions are disjoint and cover the whole registry.
    assert set(primary).isdisjoint(derived)
    assert set(primary) | set(derived) == set(load_registry())
