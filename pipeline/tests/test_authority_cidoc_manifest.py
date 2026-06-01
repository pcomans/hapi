"""Deterministic CIDOC/RDFS checks for the Hapi extension manifest.

The cidoc-crm-validator subagent handles conceptual review. These tests cover
the mechanical invariants that should fail in CI without needing an LLM.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from urllib.parse import urljoin


PIPELINE_ROOT = Path(__file__).parent.parent
REPO_ROOT = PIPELINE_ROOT.parent
AUTHORITY_ROOT = PIPELINE_ROOT / "pipeline" / "authority"
SPEC_ROOT = AUTHORITY_ROOT / "spec"

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
OWL = "http://www.w3.org/2002/07/owl#"
CRM = "http://www.cidoc-crm.org/cidoc-crm/"
CRMDIG = "http://www.cidoc-crm.org/extensions/crmdig/"
CRMSCI = "http://www.cidoc-crm.org/extensions/crmsci/"
HAPI = "https://pcomans.github.io/hapi-crm#"

SUBCLASS_OF = f"{RDFS}subClassOf"
SUBPROPERTY_OF = f"{RDFS}subPropertyOf"
DOMAIN = f"{RDFS}domain"
RANGE = f"{RDFS}range"
RDF_TYPE = f"{RDF}type"
OWL_SYMMETRIC_PROPERTY = f"{OWL}SymmetricProperty"

VENDORED_RDF_FILES = [
    SPEC_ROOT / "cidoc_crm_v7.1.3.rdf",
    SPEC_ROOT / "crmdig_v5.0.rdf",
    AUTHORITY_ROOT / "hapi_extension.rdf",
]


def _resolve_uri(value: str, base: str | None) -> str:
    if not re.match(r"^[a-z][a-z0-9+.-]*:", value, re.IGNORECASE):
        assert base, f"Relative URI {value!r} has no xml:base"
        return urljoin(base, value)
    return value


def _rdf_graph(paths: list[Path]) -> dict[str, dict[str, set[str]]]:
    graph: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for path in paths:
        text = path.read_text(encoding="utf-8-sig")
        base_match = re.search(r'xml:base="([^"]+)"', text)
        base = base_match.group(1) if base_match else None

        block_pattern = re.compile(
            r'<(?P<tag>rdfs:Class|rdf:Property|rdf:Description)\b'
            r'(?P<attrs>[^>]*)>(?P<body>.*?)</(?P=tag)>',
            re.DOTALL,
        )
        child_pattern = re.compile(
            r'<(?P<predicate>rdf:type|rdfs:subClassOf|rdfs:subPropertyOf|rdfs:domain|rdfs:range)\b'
            r'[^>]*rdf:resource="(?P<resource>[^"]+)"',
            re.DOTALL,
        )

        for block in block_pattern.finditer(text):
            subject_match = re.search(r'rdf:about="([^"]+)"', block.group("attrs"))
            if subject_match is None:
                continue
            subject = _resolve_uri(subject_match.group(1), base)
            element_type = {
                "rdfs:Class": f"{RDFS}Class",
                "rdf:Property": f"{RDF}Property",
                "rdf:Description": f"{RDF}Description",
            }[block.group("tag")]
            if element_type != f"{RDF}Description":
                graph[subject][RDF_TYPE].add(element_type)
            for child in child_pattern.finditer(block.group("body")):
                predicate = {
                    "rdf:type": RDF_TYPE,
                    "rdfs:subClassOf": SUBCLASS_OF,
                    "rdfs:subPropertyOf": SUBPROPERTY_OF,
                    "rdfs:domain": DOMAIN,
                    "rdfs:range": RANGE,
                }[child.group("predicate")]
                graph[subject][predicate].add(_resolve_uri(child.group("resource"), base))
    return graph


def _closure(graph: dict[str, dict[str, set[str]]], predicate: str, subject: str) -> set[str]:
    seen: set[str] = set()
    stack = list(graph[subject].get(predicate, set()))
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(graph[current].get(predicate, set()) - seen)
    return seen


def _is_same_or_subclass(graph: dict[str, dict[str, set[str]]], child: str, parent: str) -> bool:
    return child == parent or parent in _closure(graph, SUBCLASS_OF, child)


def _hapi_subjects(graph: dict[str, dict[str, set[str]]]) -> set[str]:
    return {subject for subject in graph if subject.startswith(HAPI)}


def test_hapi_and_crmdig_rdf_files_are_parseable_xml():
    for path in [SPEC_ROOT / "crmdig_v5.0.rdf", AUTHORITY_ROOT / "hapi_extension.rdf"]:
        ET.parse(path)


def test_cidoc_version_pins_are_coherent_across_docs_and_specs():
    adr = (REPO_ROOT / "docs" / "adr" / "018-authority-as-claim-graph.md").read_text(
        encoding="utf-8"
    )
    readme = (SPEC_ROOT / "README.md").read_text(encoding="utf-8")
    cidoc_rdf = (SPEC_ROOT / "cidoc_crm_v7.1.3.rdf").read_text(encoding="utf-8")
    crmdig_rdf = (SPEC_ROOT / "crmdig_v5.0.rdf").read_text(encoding="utf-8")

    assert "CIDOC CRM | 7.1.3" in adr
    assert "CRMdig (digital-provenance extension) | 5.0" in adr
    assert "Conceptual CRM 7.1.3" in readme
    assert "CRMdig 5.0" in readme
    assert "7.1.3" in cidoc_rdf
    assert "CRMdig 5.0" in crmdig_rdf


def test_hapi_manifest_references_resolve_and_parent_declarations_narrow():
    graph = _rdf_graph(VENDORED_RDF_FILES)
    subjects = set(graph)

    for subject in _hapi_subjects(graph):
        for predicate in (SUBCLASS_OF, SUBPROPERTY_OF, DOMAIN, RANGE, RDF_TYPE):
            for target in graph[subject].get(predicate, set()):
                if target.startswith((CRM, CRMDIG, HAPI)):
                    assert target in subjects, f"{subject} references undeclared {target}"

        for parent in graph[subject].get(SUBCLASS_OF, set()):
            assert parent in subjects, f"{subject} subClassOf target is missing: {parent}"

        for parent in graph[subject].get(SUBPROPERTY_OF, set()):
            parent_domains = graph[parent].get(DOMAIN, set())
            parent_ranges = graph[parent].get(RANGE, set())
            child_domains = graph[subject].get(DOMAIN, set())
            child_ranges = graph[subject].get(RANGE, set())

            assert parent_domains, f"{parent} has no rdfs:domain to validate {subject}"
            assert parent_ranges, f"{parent} has no rdfs:range to validate {subject}"
            assert child_domains, f"{subject} subPropertyOf {parent} needs rdfs:domain"
            assert child_ranges, f"{subject} subPropertyOf {parent} needs rdfs:range"

            for child_domain in child_domains:
                assert any(
                    _is_same_or_subclass(graph, child_domain, parent_domain)
                    for parent_domain in parent_domains
                ), f"{subject} domain {child_domain} does not narrow {parent}'s domain"

            for child_range in child_ranges:
                assert any(
                    _is_same_or_subclass(graph, child_range, parent_range)
                    for parent_range in parent_ranges
                ), f"{subject} range {child_range} does not narrow {parent}'s range"


def test_hapi_symmetric_properties_have_identical_domain_and_range():
    graph = _rdf_graph(VENDORED_RDF_FILES)

    for subject in _hapi_subjects(graph):
        if OWL_SYMMETRIC_PROPERTY not in graph[subject].get(RDF_TYPE, set()):
            continue
        assert graph[subject].get(DOMAIN) == graph[subject].get(RANGE), (
            f"{subject} is owl:SymmetricProperty; Hapi policy requires identical "
            "rdfs:domain and rdfs:range declarations"
        )


def test_hapi_manifest_does_not_use_crmsci_without_vendoring_crmsci():
    manifest = (AUTHORITY_ROOT / "hapi_extension.rdf").read_text(encoding="utf-8")
    assert CRMSCI not in manifest


def test_agent_definition_lists_deterministic_manifest_check():
    agent = (REPO_ROOT / ".claude" / "agents" / "cidoc-crm-validator.md").read_text(
        encoding="utf-8"
    )
    assert "tests/test_authority_cidoc_manifest.py" in agent
    assert "not a substitute for mechanical tests" in agent


def test_agent_team_playbook_lists_cidoc_validator():
    playbook = (REPO_ROOT / "docs" / "playbook-agent-teams.md").read_text(
        encoding="utf-8"
    )
    assert re.search(r"\|\s*`cidoc-crm-validator`\s*\|", playbook)
