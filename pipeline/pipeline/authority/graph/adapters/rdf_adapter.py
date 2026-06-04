"""Strict-CIDOC-RDF adapter (ADR-018 § encoding conventions, §reader modes).

Serialises the IR ClaimGraph to an rdflib Graph that carries BOTH:

  1. The strict CIDOC/CRMdig view — ``rdf:type`` on the full class URIs, the
     value-literal encoding conventions materialised through their canonical CRM
     properties (E41 symbolic_content → P190; E52 boundaries → P82a/P82b; the
     E41 ``appellation_kind`` type-tag → P2_has_type → an E55 Type), and every
     spine/provenance/shortcut edge on its proper CRM / CRMdig / Hapi predicate
     URI; and
  2. A lossless ``hapi-data`` self-describing layer — every node property as a
     ``hapidata:<prop>`` literal (with an explicit null-marker), which is what
     ``from_rdf`` reconstructs the exact IR from.

The round-trip ``to_rdf → from_rdf`` is asserted equal to the source IR — the
proof that the property-graph inlining is lossless. Loading the vendored CRM +
CRMdig + manifest RDFS alongside this graph yields the three reader modes the
ADR describes (the manifest's subPropertyOf rewrites e.g. hapi:same_entity_as
shortcuts to crmdig:L54_is_same_as under an RDFS reasoner).

Boundary note: reconstruction reads the hapi-data layer (lossless), while the
strict-CRM triples are asserted present/correct by the tests. Proving
invertibility from the strict triples *alone* (without the hapi-data layer) is a
deeper validation deferred with the loader specification.
"""

from __future__ import annotations

from urllib.parse import quote, unquote

from rdflib import RDF, Graph, Literal, Namespace, URIRef

from ..cidoc_spec import _local_name, _short_code, load_catalogue
from ..ir import ClaimGraph, Edge, Node

DATA = Namespace("https://pcomans.github.io/hapi-data#")
HAPIDATA = Namespace("https://pcomans.github.io/hapi-data-prop#")
HAPI = Namespace("https://pcomans.github.io/hapi-crm#")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")

_NULL = HAPIDATA["__null__"]
_KIND_PREFIX = "_kind/"
_EDGE_PREFIX = "_edge/"

# Value-literal encoding conventions: (crm_class, prop) → CRM property code.
_P190 = "P190_has_symbolic_content"
_P82A = "P82a_begin_of_the_begin"
_P82B = "P82b_end_of_the_end"
_P2 = "P2_has_type"


def _node_uri(node_id: str) -> URIRef:
    return DATA[quote(node_id, safe="")]


def _node_id_from_uri(uri: URIRef) -> str:
    return unquote(str(uri)[len(str(DATA)):])


def _is_helper(uri: URIRef) -> bool:
    frag = str(uri)[len(str(DATA)):]
    return frag.startswith(_KIND_PREFIX) or frag.startswith(_EDGE_PREFIX)


def _class_uri(code: str) -> URIRef:
    return URIRef(load_catalogue().class_term(code).uri)


def _predicate_uri(predicate: str) -> URIRef:
    if predicate.startswith("hapi:"):
        return HAPI[predicate.split(":", 1)[1]]
    return URIRef(load_catalogue().property_term(predicate).uri)


def _predicate_from_uri(uri: URIRef) -> str:
    s = str(uri)
    if s.startswith(str(HAPI)):
        return "hapi:" + s[len(str(HAPI)):]
    return _local_name(s)


# ---------------------------------------------------------------------------
# IR → RDF
# ---------------------------------------------------------------------------
def to_rdf(g: ClaimGraph) -> Graph:
    rdf = Graph()
    rdf.bind("crm", CRM)
    rdf.bind("hapi", HAPI)
    rdf.bind("hapidata", HAPIDATA)

    for node in g.nodes:
        subj = _node_uri(node.id)
        for code in node.crm_classes:
            rdf.add((subj, RDF.type, _class_uri(code)))
        if node.hapi_label is not None:
            rdf.add((subj, HAPIDATA["__label__"], Literal(node.hapi_label)))

        for prop, val in node.props.items():
            # Lossless self-describing layer.
            if val is None:
                rdf.add((subj, _NULL, Literal(prop)))
            else:
                rdf.add((subj, HAPIDATA[prop], Literal(val)))

            # Strict-CRM value-literal conventions.
            if "E41" in node.crm_classes and prop == "symbolic_content" and val is not None:
                rdf.add((subj, _predicate_uri(_P190), Literal(val)))
            elif "E41" in node.crm_classes and prop == "appellation_kind" and val is not None:
                kind_uri = DATA[_KIND_PREFIX + quote(str(val), safe="")]
                rdf.add((kind_uri, RDF.type, _class_uri("E55")))
                rdf.add((subj, _predicate_uri(_P2), kind_uri))
            elif "E52" in node.crm_classes and prop == "begin_of_the_begin" and val is not None:
                rdf.add((subj, _predicate_uri(_P82A), Literal(val)))
            elif "E52" in node.crm_classes and prop == "end_of_the_end" and val is not None:
                rdf.add((subj, _predicate_uri(_P82B), Literal(val)))

    for edge in g.edges:
        subj = _node_uri(edge.subject_id)
        obj = _node_uri(edge.object_id)
        pred = _predicate_uri(edge.predicate)
        rdf.add((subj, pred, obj))
        if edge.props:
            # Reify so edge-level locators (cited_page/cited_pdf_page) round-trip.
            reif = DATA[
                _EDGE_PREFIX
                + quote(f"{edge.subject_id}|{edge.predicate}|{edge.object_id}", safe="")
            ]
            rdf.add((reif, RDF.type, RDF.Statement))
            rdf.add((reif, RDF.subject, subj))
            rdf.add((reif, RDF.predicate, pred))
            rdf.add((reif, RDF.object, obj))
            for p, v in edge.props.items():
                if v is None:
                    rdf.add((reif, _NULL, Literal(p)))
                else:
                    rdf.add((reif, HAPIDATA[p], Literal(v)))
    return rdf


# ---------------------------------------------------------------------------
# RDF → IR
# ---------------------------------------------------------------------------
def _py(value: Literal):
    """rdflib Literal → native Python (int/float/bool/str)."""
    return value.toPython()


def from_rdf(rdf: Graph) -> ClaimGraph:
    g = ClaimGraph()

    # Identify real node URIs: DATA-ns subjects with an rdf:type that is NOT a
    # helper (kind/edge-reification) node.
    node_uris: set[URIRef] = set()
    for s, _, o in rdf.triples((None, RDF.type, None)):
        if not isinstance(s, URIRef) or not str(s).startswith(str(DATA)):
            continue
        if _is_helper(s) or o == RDF.Statement:
            continue
        node_uris.add(s)

    # Rebuild nodes.
    for uri in node_uris:
        codes: list[str] = []
        for _, _, o in rdf.triples((uri, RDF.type, None)):
            code = _short_code(_local_name(str(o)))
            if code:
                codes.append(code)
        props: dict[str, object] = {}
        label: str | None = None
        for _, p, o in rdf.triples((uri, None, None)):
            if p == HAPIDATA["__label__"]:
                label = str(o)
            elif p == _NULL:
                props[str(o)] = None
            elif str(p).startswith(str(HAPIDATA)):
                props[str(p)[len(str(HAPIDATA)):]] = _py(o)
        g.add_node(
            Node(_node_id_from_uri(uri), tuple(sorted(codes)), props, label)
        )

    # Reified edge-property lookup: (subj, pred, obj) → props dict.
    edge_props: dict[tuple[str, str, str], dict[str, object]] = {}
    for reif, _, _ in rdf.triples((None, RDF.type, RDF.Statement)):
        s = rdf.value(reif, RDF.subject)
        p = rdf.value(reif, RDF.predicate)
        o = rdf.value(reif, RDF.object)
        key = (
            _node_id_from_uri(s),
            _predicate_from_uri(p),
            _node_id_from_uri(o),
        )
        props: dict[str, object] = {}
        for _, pp, vv in rdf.triples((reif, None, None)):
            if pp == _NULL:
                props[str(vv)] = None
            elif str(pp).startswith(str(HAPIDATA)):
                props[str(pp)[len(str(HAPIDATA)):]] = _py(vv)
        edge_props[key] = props

    # Rebuild edges: triples between two real node URIs (object is a node URI),
    # excluding rdf:type and the helper relations.
    for s, p, o in rdf:
        if p == RDF.type or not isinstance(o, URIRef):
            continue
        if s not in node_uris or o not in node_uris:
            continue
        predicate = _predicate_from_uri(p)
        key = (_node_id_from_uri(s), predicate, _node_id_from_uri(o))
        g.add_edge(Edge(key[0], predicate, key[2], edge_props.get(key, {})))
    return g
