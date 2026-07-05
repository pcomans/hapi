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

ONTOLOGY_URI = "https://pcomans.github.io/hapi-crm"

# Element-tag identities a declaration can have (the ELEMENT KIND is itself
# an implicit rdf:type: <rdf:Property> ⇒ rdf:Property, <rdfs:Class> ⇒
# rdfs:Class; <rdf:Description> is generic and asserts no implicit type).
RDF_PROPERTY = f"{RDF_NS}Property"
RDFS_CLASS = f"{RDFS_NS}Class"
RDF_DESCRIPTION = f"{RDF_NS}Description"

E55_TYPE = CRM_PREFIX + "E55_Type"
SYMMETRIC = "http://www.w3.org/2002/07/owl#SymmetricProperty"

# The complete typing matrix of the manifest, per ADR-018 §"Hapi extension
# manifest" — the single source of truth for the inventory AND for each
# term's (element kind, explicit rdf:type set). This encodes ADR-018's
# load-bearing punning invariant as deterministic enforcement (Rule 3):
#   * the 9 P177-target predicates MUST carry crm:E55_Type (so a P177 value
#     is a well-typed E55 instance), declared as rdf:Property + the pun;
#   * derived_by_run / supersedes are E13-internal direct edges and MUST NOT
#     carry E55_Type (they are never P177 targets);
#   * shares_tomb_with is derived/query-only — owl:SymmetricProperty but
#     NOT E55_Type (never persisted as a P177 target);
#   * the verdict vocabulary are pure E55 *instances* — rdf:Description (no
#     implicit rdf:Property typing) carrying only crm:E55_Type.
# A new term, a lost pun, a verdict instance silently promoted to a
# predicate, or a symmetric flag dropped each fails loud.
EXPECTED_TYPING: dict[str, tuple[str, frozenset[str]]] = {
    # Classes (CRMdig-narrowed) — rdfs:Class element, no explicit rdf:type
    "#MatcherRun": (RDFS_CLASS, frozenset()),
    "#MatcherAlgorithm": (RDFS_CLASS, frozenset()),
    "#SourceData": (RDFS_CLASS, frozenset()),
    # E13-internal direct-edge properties — rdf:Property, NO E55 pun
    "#derived_by_run": (RDF_PROPERTY, frozenset()),
    "#supersedes": (RDF_PROPERTY, frozenset()),
    # Parent-narrowed relation predicate — P177 target (pun) AND symmetric
    "#same_entity_as": (RDF_PROPERTY, frozenset({E55_TYPE, SYMMETRIC})),
    # Free-standing P177-target predicates — rdf:Property + E55 pun
    "#in_dynastic_period": (RDF_PROPERTY, frozenset({E55_TYPE})),
    "#tomb_owner": (RDF_PROPERTY, frozenset({E55_TYPE})),
    "#original_burial_in": (RDF_PROPERTY, frozenset({E55_TYPE})),
    "#cache_context_at": (RDF_PROPERTY, frozenset({E55_TYPE})),
    "#display_name": (RDF_PROPERTY, frozenset({E55_TYPE})),
    "#reign_period": (RDF_PROPERTY, frozenset({E55_TYPE})),
    "#horus_name": (RDF_PROPERTY, frozenset({E55_TYPE})),
    "#matcher_review_verdict": (RDF_PROPERTY, frozenset({E55_TYPE})),
    # Derived / query-only predicate — symmetric, but NOT a P177 target
    "#shares_tomb_with": (RDF_PROPERTY, frozenset({SYMMETRIC})),
    # Verdict-outcome controlled vocabulary — pure E55 Type INSTANCES
    "#verdict_approved": (RDF_DESCRIPTION, frozenset({E55_TYPE})),
    "#verdict_rejected": (RDF_DESCRIPTION, frozenset({E55_TYPE})),
    "#verdict_retracted": (RDF_DESCRIPTION, frozenset({E55_TYPE})),
    "#verdict_escalated": (RDF_DESCRIPTION, frozenset({E55_TYPE})),
}

# Inventory is derived from the typing matrix — single source of truth (Rule 4).
EXPECTED_TERMS = set(EXPECTED_TYPING)


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


def term_typing(el: ET.Element) -> tuple[str, frozenset[str]]:
    """A term's (element-kind tag, explicit rdf:type resource set).

    The element tag is the implicit type (rdf:Property / rdfs:Class /
    generic rdf:Description); the explicit <rdf:type rdf:resource=...>
    children carry the punned crm:E55_Type and owl:SymmetricProperty.
    """
    explicit = {
        t.attrib[f"{RDF_NS}resource"] for t in el.findall(f"{RDF_NS}type")
    }
    return el.tag, frozenset(explicit)


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

    def test_no_duplicate_or_stray_top_level_declarations(self, manifest_root):
        # A dict keyed by rdf:about silently last-write-wins on a duplicate,
        # and the "#"-prefix filter would hide a stray absolute-URI term —
        # so assert the raw top-level about list directly.
        abouts = [
            el.attrib[f"{RDF_NS}about"]
            for el in manifest_root
            if f"{RDF_NS}about" in el.attrib
        ]
        duplicates = sorted({a for a in abouts if abouts.count(a) > 1})
        assert not duplicates, f"duplicate rdf:about declarations: {duplicates}"
        assert set(abouts) == EXPECTED_TERMS | {ONTOLOGY_URI}

    def test_term_typing_matrix(self, manifest_root):
        # ADR-018's full punning invariant: every term's element kind AND
        # exact rdf:type set — P177-target predicates carry E55, the two
        # E13-internal edges and shares_tomb_with do NOT, and the verdict
        # vocabulary are pure E55 rdf:Description instances (not predicates).
        decls = manifest_declarations(manifest_root)
        actual = {about: term_typing(el) for about, el in decls.items()}
        assert actual == EXPECTED_TYPING


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
            "#original_burial_in": CRM_PREFIX + "P53_has_former_or_current_location",
            "#cache_context_at": CRM_PREFIX + "P53_has_former_or_current_location",
        }
        for term, parent in expected_parents.items():
            declared = {
                el.attrib[f"{RDF_NS}resource"]
                for tag in ("subClassOf", "subPropertyOf")
                for el in decls[term].findall(f"{RDFS_NS}{tag}")
            }
            # Exact equality, not membership: a spurious second (real-but-wrong)
            # parent pin would slip past an `in` check and term-resolution.
            assert declared == {parent}, (term, declared)
