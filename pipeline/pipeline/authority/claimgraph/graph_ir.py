"""The documentary layer of the source-attributed claim graph. Each source row becomes
one ``:Ruler`` (E21) node plus a set of E13 claims, every claim carrying its full
human-documentary provenance spine (P14 scholar + P70i publication + page locators). No
cross-source collapse happens here (ADR-018)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .normalize import NameForm
from .sources import RulerRecord

PRED_DISPLAY_NAME = "hapi:display_name"
PRED_PRENOMEN = "hapi:prenomen"
PRED_HORUS_NAME = "hapi:horus_name"
PRED_NOMEN = "hapi:nomen"
PRED_IN_DYNASTIC_PERIOD = "hapi:in_dynastic_period"


@dataclass
class RulerNode:
    id: str
    source_id: str
    local_id: str
    display_name: str
    dynasty: int | None
    dynasty_label: str | None
    reign_start_bce: int | None
    reign_end_bce: int | None
    stage_group: str | None


@dataclass
class Claim:
    id: str
    subject_id: str
    predicate: str
    value_text: str
    value_translit: str | None
    is_variant: bool
    scholar_id: str
    scholar_name: str
    publication_id: str
    publication_citation: str
    cited_page: int | None
    cited_pdf_page: str | None


@dataclass
class IntraSourceIdentity:
    subject_id: str
    object_id: str
    scholar_name: str
    publication_citation: str


@dataclass
class DocumentaryGraph:
    rulers: list[RulerNode] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    intra_source_identities: list[IntraSourceIdentity] = field(default_factory=list)


def _name_claims(
    rec: RulerRecord, forms: list[NameForm], predicate: str, seq
) -> list[Claim]:
    claims: list[Claim] = []
    for i, f in enumerate(forms):
        value_text = f.surface or f.translit or ""
        if not value_text:
            continue
        claims.append(
            Claim(
                id=seq(),
                subject_id=rec.local_id,
                predicate=predicate,
                value_text=f.surface or "",
                value_translit=f.translit,
                is_variant=i > 0,
                scholar_id=rec.authority.scholar_id,
                scholar_name=rec.authority.scholar_name,
                publication_id=rec.authority.publication_id,
                publication_citation=rec.authority.publication_citation,
                cited_page=rec.cited_page,
                cited_pdf_page=rec.cited_pdf_page,
            )
        )
    return claims


def build_documentary_graph(records: list[RulerRecord]) -> DocumentaryGraph:
    rulers: list[RulerNode] = []
    claims: list[Claim] = []
    intra: list[IntraSourceIdentity] = []
    counter = 0

    def seq() -> str:
        nonlocal counter
        s = f"stmt-{counter}"
        counter += 1
        return s

    known = {r.local_id for r in records}

    for rec in records:
        rulers.append(
            RulerNode(
                id=rec.local_id,
                source_id=rec.source_id,
                local_id=rec.local_id,
                display_name=rec.display_name,
                dynasty=rec.dynasty,
                dynasty_label=rec.dynasty_label,
                reign_start_bce=rec.reign_start_bce,
                reign_end_bce=rec.reign_end_bce,
                stage_group=rec.stage_group,
            )
        )
        claims += _name_claims(rec, [NameForm(surface=rec.display_name)], PRED_DISPLAY_NAME, seq)
        claims += _name_claims(rec, rec.prenomina, PRED_PRENOMEN, seq)
        claims += _name_claims(rec, rec.horus_names, PRED_HORUS_NAME, seq)
        claims += _name_claims(rec, rec.nomina, PRED_NOMEN, seq)

        if rec.dynasty is not None:
            claims.append(
                Claim(
                    id=seq(),
                    subject_id=rec.local_id,
                    predicate=PRED_IN_DYNASTIC_PERIOD,
                    value_text=rec.dynasty_label or f"Dynasty {rec.dynasty}",
                    value_translit=None,
                    is_variant=False,
                    scholar_id=rec.authority.scholar_id,
                    scholar_name=rec.authority.scholar_name,
                    publication_id=rec.authority.publication_id,
                    publication_citation=rec.authority.publication_citation,
                    cited_page=rec.cited_page,
                    cited_pdf_page=rec.cited_pdf_page,
                )
            )

        for object_id in rec.intra_source_same_as:
            if object_id not in known:
                continue  # referenced row not loaded — drop, don't invent
            intra.append(
                IntraSourceIdentity(
                    subject_id=rec.local_id,
                    object_id=object_id,
                    scholar_name=rec.authority.scholar_name,
                    publication_citation=rec.authority.publication_citation,
                )
            )

    return DocumentaryGraph(rulers=rulers, claims=claims, intra_source_identities=intra)
