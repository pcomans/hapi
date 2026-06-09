"""Cannot-link constraints for matcher precision (advisor Priority 1, ADR-020).

Deterministic, structured discriminators that say two `:Ruler` (E21) rows
*cannot* be the same person — used to prune candidates and to guard clustering
(see `poc.guarded_same_entity_clusters`). These reject merges from structured
facts already in the graph; they are NOT surface-string similarity (ADR-009
forbids that for acceptance — these are for rejection, the same category as the
dynasty constraint).

Rules:
- 1c regnal-numeral mismatch — both names carry a parseable regnal numeral and
  they differ (Iuput I vs Iuput II). A structured identity discriminator, not an
  edit-distance.
- 1b disjoint reign Time-Spans — both carry `hapi:reign_period` E52 spans that
  don't overlap within a tolerance band (absorbs Beckerath's fuzzy bounds).
- 1a same-source-distinct-rows — two rows from the SAME source are presumptively
  different people UNLESS the source links them (Kitchen `same_person_as`, loaded
  as documentary same_entity_as) OR they are stage-suffix phase siblings of one
  id stem (Leprohon `leprohon-18.10a`/`-18.10b`).
"""

from __future__ import annotations

import re

from ..ir import ClaimGraph

SAME_ENTITY_AS = "hapi:same_entity_as"
P140 = "P140_assigned_attribute_to"
P141 = "P141_assigned"
P177 = "P177_assigned_property_of_type"
P14 = "P14_carried_out_by"
DERIVED_BY_RUN = "hapi:derived_by_run"

# Reign-overlap tolerance: generous, because Beckerath stores fuzzy low/high bounds
# and the loader already takes the maximal span. Require a gap larger than a long
# reign before declaring two spans disjoint.
REIGN_TOLERANCE_YEARS = 25

_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
_STAGE_SUFFIX = re.compile(r"[a-z]+$")  # trailing lowercase letters on a source_id


def _roman_to_int(token: str) -> int | None:
    token = token.rstrip(".").upper()
    if not token or any(c not in _ROMAN for c in token):
        return None
    total = prev = 0
    for ch in reversed(token):
        v = _ROMAN[ch]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


def regnal_number(display_name: str | None) -> int | None:
    """Trailing regnal numeral of a ruler name, e.g. 'Osorkon II.' -> 2; else None."""
    if not display_name:
        return None
    last = display_name.split()[-1] if display_name.split() else ""
    return _roman_to_int(last)


def _display(g: ClaimGraph, rid: str) -> str | None:
    try:
        return g.node(f"appellation::{rid}::display_name").props["symbolic_content"]
    except KeyError:
        return None


def _reign_span(g: ClaimGraph, rid: str) -> tuple[int, int] | None:
    try:
        n = g.node(f"timespan::{rid}::reign")
    except KeyError:
        return None
    b, e = n.props.get("begin_of_the_begin"), n.props.get("end_of_the_end")
    if b is None or e is None:
        return None
    return (min(b, e), max(b, e))


def _stem(source_id: str | None) -> str | None:
    if not source_id:
        return None
    return _STAGE_SUFFIX.sub("", source_id)


def documentary_same_entity_pairs(g: ClaimGraph) -> set[frozenset[str]]:
    """Pairs linked by a source-attributed (documentary) same_entity_as claim.

    Documentary = carries P14 (and not derived_by_run) — i.e. the source's own
    intra-source identity assertion (Kitchen `same_person_as`).
    """
    same_type = f"type::{SAME_ENTITY_AS}"
    out: set[frozenset[str]] = set()
    for n in g.nodes_of_class("E13"):
        ed = {e.predicate: e.object_id for e in g.out_edges(n.id)}
        if ed.get(P177) != same_type:
            continue
        if DERIVED_BY_RUN in ed or P14 not in ed:
            continue  # matcher-derived, not a documentary source assertion
        s, o = ed.get(P140), ed.get(P141)
        if s and o:
            out.add(frozenset((s, o)))
    return out


def regnal_mismatch(g: ClaimGraph, a: str, b: str) -> str | None:
    """Both names carry a regnal numeral and they differ (Iuput I vs Iuput II).

    NOT a hard cannot-link — sources sometimes number the same name differently
    (Leprohon "Ahmose III" = Beckerath "Amosis II" = Amasis). Per ADR-020 §6 this
    routes to human escalation, never a silent block or accept.
    """
    ra, rb = regnal_number(_display(g, a)), regnal_number(_display(g, b))
    if ra is not None and rb is not None and ra != rb:
        return f"regnal-number mismatch ({ra} vs {rb})"
    return None


def same_person(
    g: ClaimGraph, a: str, b: str, doc_pairs: set[frozenset[str]] | None = None
) -> bool:
    """True if a and b are the SAME person within one source — a phase split.

    Either stage-suffix siblings of one id stem (Leprohon 18.10a/18.10b) or
    linked by a documentary same_entity_as (Kitchen same_person_as). Used to
    EXEMPT legitimate many-to-one (phase) cases from the uniqueness constraint.
    """
    na, nb = g.node(a), g.node(b)
    if na.props.get("source") != nb.props.get("source"):
        return False
    stem_a = _stem(na.props.get("source_id"))
    if stem_a is not None and stem_a == _stem(nb.props.get("source_id")):
        return True
    return doc_pairs is not None and frozenset((a, b)) in doc_pairs


def cannot_link(
    g: ClaimGraph, a: str, b: str, *, doc_pairs: set[frozenset[str]] | None = None
) -> str | None:
    """Hard cannot-link reasons (block a merge). Regnal mismatch is NOT here — it
    escalates (see ``regnal_mismatch``). Hard rules: disjoint reign spans, and
    same-source distinct rows not linked by the source."""
    if a == b:
        return None
    na, nb = g.node(a), g.node(b)

    # 1b — disjoint reign Time-Spans (both present, no overlap within tolerance).
    sa, sb = _reign_span(g, a), _reign_span(g, b)
    if sa and sb:
        overlap = sa[0] <= sb[1] + REIGN_TOLERANCE_YEARS and sb[0] <= sa[1] + REIGN_TOLERANCE_YEARS
        if not overlap:
            return f"disjoint reign spans ({sa} vs {sb})"

    # 1a — same-source distinct rows (unless source-linked or phase siblings).
    src = na.props.get("source")
    if src and src == nb.props.get("source") and not same_person(g, a, b, doc_pairs):
        return f"same-source ({src}) distinct rows not linked by the source"

    return None
