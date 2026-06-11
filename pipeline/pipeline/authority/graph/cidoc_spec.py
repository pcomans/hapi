"""Authoritative CIDOC CRM 7.1.3 + CRMdig 5.0 + Hapi-extension catalogue.

Everything here is derived by parsing the *vendored* RDFS files on disk
(``pipeline/pipeline/authority/spec/*.rdf`` and ``hapi_extension.rdf``) — never
from model recall. That keeps the catalogue traceable to a committed source
(Constitutional rule 1) and makes a spec-pin move automatically re-derive it.

Exposes the class/property universe keyed by CIDOC short code (``"E21"``,
``"P140"``, ``"D10"``, ``"L54"``) with full local names, namespaces, IS-A
(subClassOf / subPropertyOf) relations, and property domain/range — the inputs
the registry validator and the strict-RDF adapter both need.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rdflib import RDF, RDFS, Graph, URIRef
from rdflib.namespace import OWL

CRM_NS = "http://www.cidoc-crm.org/cidoc-crm/"
CRMDIG_NS = "http://www.cidoc-crm.org/extensions/crmdig/"
HAPI_NS = "https://pcomans.github.io/hapi-crm#"

_AUTHORITY_DIR = Path(__file__).resolve().parent.parent
_SPEC_DIR = _AUTHORITY_DIR / "spec"
_MANIFEST = _AUTHORITY_DIR / "hapi_extension.rdf"

# CIDOC short code embedded at the start of a local name: E21_Person -> E21,
# P82a_begin_of_the_begin -> P82a, D10_Software_Execution -> D10, L54_is_same_as -> L54.
_CODE_RE = re.compile(r"^([EPDL]\d+[a-z]?)(?:_|$)")


def _local_name(uri: str) -> str:
    frag = uri.split("#")[-1] if "#" in uri else uri.rstrip("/").split("/")[-1]
    return frag


def _short_code(local: str) -> str | None:
    m = _CODE_RE.match(local)
    return m.group(1) if m else None


@dataclass(frozen=True)
class Term:
    """A class or property term from one of the loaded specs."""

    code: str | None          # CIDOC short code, e.g. "E21" / "P140" / None for hapi-only terms
    local_name: str           # full local name, e.g. "E21_Person"
    uri: str                  # full URI
    namespace: str            # CRM_NS / CRMDIG_NS / HAPI_NS
    is_class: bool
    domain: str | None = None # property domain local name (if a property)
    range: str | None = None  # property range local name (if a property)


class CidocCatalogue:
    """Parsed union of CRM 7.1.3, CRMdig 5.0, and the Hapi extension manifest."""

    def __init__(self, graph: Graph) -> None:
        self._g = graph
        self._classes_by_code: dict[str, Term] = {}
        self._props_by_code: dict[str, Term] = {}
        self._classes_by_local: dict[str, Term] = {}
        self._props_by_local: dict[str, Term] = {}
        self._subclass: dict[str, set[str]] = {}     # local -> direct super locals
        self._subproperty: dict[str, set[str]] = {}  # local -> direct super locals
        self._index()

    @staticmethod
    def _ns_of(uri: str) -> str | None:
        for ns in (CRM_NS, CRMDIG_NS, HAPI_NS):
            if uri.startswith(ns):
                return ns
        return None

    def _index(self) -> None:
        g = self._g
        # Classes: anything typed rdfs:Class or owl:Class in a known namespace.
        class_uris: set[URIRef] = set()
        for cls_type in (RDFS.Class, OWL.Class):
            for s in g.subjects(RDF.type, cls_type):
                if isinstance(s, URIRef) and self._ns_of(str(s)):
                    class_uris.add(s)
        # Properties: rdf:Property / owl:*Property in a known namespace.
        prop_uris: set[URIRef] = set()
        for prop_type in (
            RDF.Property,
            OWL.ObjectProperty,
            OWL.DatatypeProperty,
            OWL.SymmetricProperty,
        ):
            for s in g.subjects(RDF.type, prop_type):
                if isinstance(s, URIRef) and self._ns_of(str(s)):
                    prop_uris.add(s)

        for uri in class_uris:
            term = self._make_term(uri, is_class=True)
            self._classes_by_local[term.local_name] = term
            if term.code:
                self._classes_by_code[term.code] = term

        for uri in prop_uris:
            dom = g.value(uri, RDFS.domain)
            rng = g.value(uri, RDFS.range)
            term = self._make_term(
                uri,
                is_class=False,
                domain=_local_name(str(dom)) if dom else None,
                range_=_local_name(str(rng)) if rng else None,
            )
            self._props_by_local[term.local_name] = term
            if term.code:
                self._props_by_code[term.code] = term

        for sub, _, sup in g.triples((None, RDFS.subClassOf, None)):
            if isinstance(sub, URIRef) and isinstance(sup, URIRef):
                self._subclass.setdefault(_local_name(str(sub)), set()).add(
                    _local_name(str(sup))
                )
        for sub, _, sup in g.triples((None, RDFS.subPropertyOf, None)):
            if isinstance(sub, URIRef) and isinstance(sup, URIRef):
                self._subproperty.setdefault(_local_name(str(sub)), set()).add(
                    _local_name(str(sup))
                )

    def _make_term(
        self,
        uri: URIRef,
        *,
        is_class: bool,
        domain: str | None = None,
        range_: str | None = None,
    ) -> Term:
        s = str(uri)
        local = _local_name(s)
        return Term(
            code=_short_code(local),
            local_name=local,
            uri=s,
            namespace=self._ns_of(s),  # type: ignore[arg-type]
            is_class=is_class,
            domain=domain,
            range=range_,
        )

    # -- public API ---------------------------------------------------------
    def has_class(self, code_or_local: str) -> bool:
        return (
            code_or_local in self._classes_by_code
            or code_or_local in self._classes_by_local
        )

    def has_property(self, code_or_local: str) -> bool:
        return (
            code_or_local in self._props_by_code
            or code_or_local in self._props_by_local
        )

    def class_term(self, code_or_local: str) -> Term:
        if code_or_local in self._classes_by_code:
            return self._classes_by_code[code_or_local]
        if code_or_local in self._classes_by_local:
            return self._classes_by_local[code_or_local]
        raise KeyError(f"No CIDOC class {code_or_local!r} in catalogue")

    def property_term(self, code_or_local: str) -> Term:
        if code_or_local in self._props_by_code:
            return self._props_by_code[code_or_local]
        if code_or_local in self._props_by_local:
            return self._props_by_local[code_or_local]
        raise KeyError(f"No CIDOC property {code_or_local!r} in catalogue")

    def is_a(self, sub_local: str, super_local: str) -> bool:
        """True if ``sub_local`` IS-A ``super_local`` via subClassOf* (reflexive)."""
        if sub_local == super_local:
            return True
        seen: set[str] = set()
        stack = list(self._subclass.get(sub_local, ()))
        while stack:
            cur = stack.pop()
            if cur == super_local:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(self._subclass.get(cur, ()))
        return False

    def controlled_vocab_e55(self) -> set[str]:
        """Hapi local names that are pure ``crm:E55_Type`` instances.

        These are the controlled-vocabulary verdict outcomes (verdict_approved /
        _rejected / _retracted) — typed ``crm:E55_Type`` in the manifest but NOT
        ``rdf:Property`` (which is how they differ from the punned P177-target
        predicate URIs). Read straight from the manifest RDF, so the set is
        traceable to the committed contract, not hardcoded.
        """
        e55 = URIRef(CRM_NS + "E55_Type")
        out: set[str] = set()
        for s in self._g.subjects(RDF.type, e55):
            if not (isinstance(s, URIRef) and str(s).startswith(HAPI_NS)):
                continue
            if (s, RDF.type, RDF.Property) in self._g:
                continue  # punned predicate URI, not a pure vocabulary instance
            out.add(_local_name(str(s)))
        return out

    @property
    def class_codes(self) -> set[str]:
        return set(self._classes_by_code)

    @property
    def property_codes(self) -> set[str]:
        return set(self._props_by_code)


@lru_cache(maxsize=1)
def load_catalogue() -> CidocCatalogue:
    """Parse and cache the vendored CRM + CRMdig + Hapi-extension RDFS union."""
    g = Graph()
    crm = _SPEC_DIR / "cidoc_crm_v7.1.3.rdf"
    crmdig = _SPEC_DIR / "crmdig_v5.0.rdf"
    for path in (crm, crmdig, _MANIFEST):
        if not path.exists():
            raise FileNotFoundError(f"Required spec file missing: {path}")
        g.parse(path.as_posix(), format="xml")
    return CidocCatalogue(g)
