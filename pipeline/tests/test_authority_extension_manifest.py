"""Integrity tests for the Hapi CRM/CRMdig extension manifest.

The manifest (pipeline/authority/hapi_extension.rdf) is the citable
contract for every Hapi-namespaced term in ADR-018. The whole
manifest-interop story — strict readers applying rdfs:subClassOf /
rdfs:subPropertyOf declarations, OWL readers applying symmetry — only
works if the file actually parses, so well-formedness and term
resolution are enforced mechanically here (Constitutional Rule 3)
rather than left to the cidoc-crm-validator review gate.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

AUTHORITY = Path(__file__).parent.parent / "pipeline" / "authority"
MANIFEST = AUTHORITY / "hapi_extension.rdf"
CIDOC_RDF = AUTHORITY / "spec" / "cidoc_crm_v7.1.3.rdf"
CRMDIG_RDF = AUTHORITY / "spec" / "crmdig_v5.0.rdf"

RDF_NS = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
RDFS_NS = "{http://www.w3.org/2000/01/rdf-schema#}"

CRM_PREFIX = "http://www.cidoc-crm.org/cidoc-crm/"
CRMDIG_PREFIX = "http://www.cidoc-crm.org/extensions/crmdig/"

# The complete term inventory of the manifest, per ADR-018 §"Hapi
# extension manifest". A new term shows up here in the same PR that
# adds it to the manifest; an unexplained diff in either direction
# fails loud.
EXPECTED_TERMS = {
    # Classes (CRMdig-narrowed)
    "#MatcherRun",
    "#MatcherAlgorithm",
    "#SourceData",
    # E13-internal direct-edge properties
    "#derived_by_run",
    "#supersedes",
    # Parent-narrowed relation predicate
    "#same_entity_as",
    # Free-standing P177-target predicates
    "#in_dynastic_period",
    "#tomb_owner",
    "#original_burial_in",
    "#cache_context_at",
    "#display_name",
    "#reign_period",
    "#horus_name",
    "#matcher_review_verdict",
    # Derived / query-only predicate
    "#shares_tomb_with",
    # Verdict-outcome controlled vocabulary (E55 Type instances)
    "#verdict_approved",
    "#verdict_rejected",
    "#verdict_retracted",
}


@pytest.fixture(scope="module")
def manifest_root():
    return ET.parse(MANIFEST).getroot()


def manifest_declarations(root) -> dict[str, ET.Element]:
    """Map each declared term's rdf:about to its declaration element."""
    return {
        el.attrib[f"{RDF_NS}about"]: el
        for el in root
        if el.attrib.get(f"{RDF_NS}about", "").startswith("#")
    }


def spec_terms(path: Path, prefix: str) -> set[str]:
    """All rdf:about URIs declared by a vendored spec RDFS file.

    The CIDOC RDFS declares terms with bare names resolved against its
    xml:base; CRMdig declares a mix of bare names and absolute URIs.
    Both are normalised to absolute URIs under the given prefix.
    """
    terms = set()
    for el in ET.parse(path).getroot():
        about = el.attrib.get(f"{RDF_NS}about")
        if about is None:
            continue
        terms.add(about if about.startswith("http") else prefix + about)
    return terms


class TestManifestWellFormedness:
    def test_manifest_parses(self):
        # The raw-angle-bracket regression: an unescaped <rdf:...> inside
        # an rdfs:comment makes the whole manifest unloadable by any
        # RDF/XML reader.
        ET.parse(MANIFEST)

    def test_vendored_specs_parse(self):
        ET.parse(CIDOC_RDF)
        ET.parse(CRMDIG_RDF)


class TestManifestTermInventory:
    def test_declared_terms_match_adr_inventory(self, manifest_root):
        assert set(manifest_declarations(manifest_root)) == EXPECTED_TERMS

    def test_verdict_vocabulary_is_pure_e55(self, manifest_root):
        decls = manifest_declarations(manifest_root)
        for term in ("#verdict_approved", "#verdict_rejected", "#verdict_retracted"):
            types = {
                t.attrib[f"{RDF_NS}resource"]
                for t in decls[term].findall(f"{RDF_NS}type")
            }
            assert types == {CRM_PREFIX + "E55_Type"}, term


class TestManifestTermResolution:
    def test_referenced_crm_and_crmdig_terms_exist_in_vendored_specs(
        self, manifest_root
    ):
        known = spec_terms(CIDOC_RDF, CRM_PREFIX) | spec_terms(
            CRMDIG_RDF, CRMDIG_PREFIX
        )
        referenced = {
            ref
            for el in manifest_root.iter()
            for ref in el.attrib.values()
            if ref.startswith((CRM_PREFIX, CRMDIG_PREFIX))
        }
        assert referenced, "manifest references no CRM/CRMdig terms — wrong file?"
        missing = referenced - known
        assert not missing, (
            f"manifest references CRM/CRMdig terms absent from the vendored "
            f"specs (stale pin or typo): {sorted(missing)}"
        )

    def test_narrowing_declarations_target_pinned_parents(self, manifest_root):
        decls = manifest_declarations(manifest_root)
        expected_parents = {
            "#MatcherRun": CRMDIG_PREFIX + "D10_Software_Execution",
            "#MatcherAlgorithm": CRMDIG_PREFIX + "D14_Software",
            "#SourceData": CRMDIG_PREFIX + "D1_Digital_Object",
            "#derived_by_run": CRM_PREFIX + "P15_was_influenced_by",
            "#same_entity_as": CRMDIG_PREFIX + "L54_is_same_as",
        }
        for term, parent in expected_parents.items():
            declared = {
                el.attrib[f"{RDF_NS}resource"]
                for tag in ("subClassOf", "subPropertyOf")
                for el in decls[term].findall(f"{RDFS_NS}{tag}")
            }
            assert parent in declared, (term, declared)
