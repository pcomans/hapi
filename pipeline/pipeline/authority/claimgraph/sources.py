"""Per-source adapters: map each source's native ``reconciled.jsonl`` row shape to the
canonical :class:`RulerRecord`. Extraction only — no cross-source resolution, no
guessing. A row that isn't an individual ruler (dynasty markers, period headers) is
dropped here (fail-visible in the load report, never fail-silent)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .normalize import NameForm

SOURCE_IDS = ("leprohon", "beckerath", "kitchen", "pharaoh_se", "ryholt")

SOURCE_LABEL: dict[str, str] = {
    "leprohon": "Leprohon 2013",
    "beckerath": "von Beckerath 1997",
    "kitchen": "Kitchen (TIP)",
    "pharaoh_se": "pharaoh.se",
    "ryholt": "Ryholt 1997",
}


@dataclass(frozen=True)
class SourceAuthority:
    scholar_id: str
    scholar_name: str
    publication_id: str
    publication_citation: str
    url: str | None = None


SOURCE_AUTHORITY: dict[str, SourceAuthority] = {
    "leprohon": SourceAuthority(
        "leprohon_rj",
        "Ronald J. Leprohon",
        "leprohon_2013",
        "Leprohon, R. J. (2013). The Great Name: Ancient Egyptian Royal Titulary. "
        "SBL Writings from the Ancient World 33.",
    ),
    "beckerath": SourceAuthority(
        "beckerath_j",
        "Jürgen von Beckerath",
        "beckerath_1997",
        "von Beckerath, J. (1997). Chronologie des pharaonischen Ägypten. "
        "Münchner Ägyptologische Studien 46.",
    ),
    "kitchen": SourceAuthority(
        "kitchen_ka",
        "Kenneth A. Kitchen",
        "kitchen_tipe_1996",
        "Kitchen, K. A. (1996). The Third Intermediate Period in Egypt "
        "(1100–650 BC), 3rd ed.",
    ),
    "pharaoh_se": SourceAuthority(
        "lundstrom_p",
        "Peter Lundström (pharaoh.se)",
        "pharaoh_se",
        "Lundström, P. pharaoh.se — The Kings & Queens of Egypt: an independently "
        "compiled, source-referenced royal titulary (self-published web resource; not "
        "peer-reviewed — weigh below the print references in adjudication).",
        url="https://pharaoh.se/",
    ),
    "ryholt": SourceAuthority(
        "ryholt_k",
        "Kim Ryholt",
        "ryholt_1997",
        "Ryholt, K. (1997). The Political Situation in Egypt during the Second "
        "Intermediate Period, c.1800–1550 B.C.",
    ),
}


@dataclass
class RulerRecord:
    """Canonical, source-attributed ruler record. Every source row is projected to one
    of these WITHOUT collapsing across sources (ADR-018: per-source ``:Ruler`` E21
    nodes). Matching happens later, over the name key-sets — never here."""

    source_id: str
    local_id: str
    display_name: str
    alt_names: list[str]
    dynasty: int | None
    dynasty_label: str | None
    prenomina: list[NameForm]  # throne names — primary corroborator (set-valued)
    horus_names: list[NameForm]  # corroborator for the earliest dynasties
    nomina: list[NameForm]  # birth names — secondary
    reign_start_bce: int | None
    reign_end_bce: int | None
    intra_source_same_as: list[str]
    authority: SourceAuthority
    cited_page: int | None = None
    cited_pdf_page: str | None = None
    stage_group: str | None = None


# --- helpers ---------------------------------------------------------------


def _s(v) -> str | None:
    return v.strip() if isinstance(v, str) and v.strip() else None


def _n(v) -> int | None:
    return v if isinstance(v, int) else None


def _list(v) -> list:
    return v if isinstance(v, list) else []


def _read_jsonl(root: Path, source: str) -> list[dict]:
    path = root / source / "reconciled.jsonl"
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _from_titulary_list(lst) -> list[NameForm]:
    """A Leprohon/pharaoh.se-style titulary list entry → NameForm."""
    out: list[NameForm] = []
    for e in _list(lst):
        if not isinstance(e, dict):
            continue
        surface = _s(e.get("anglicised")) or _s(e.get("name")) or ""
        translit = _s(e.get("transliteration"))
        if surface or translit:
            out.append(NameForm(surface=surface, translit=translit))
    return out


# --- per-source loaders ----------------------------------------------------


def load_leprohon(root: Path) -> list[RulerRecord]:
    auth = SOURCE_AUTHORITY["leprohon"]
    out = []
    for r in _read_jsonl(root, "leprohon-2013-titulary"):
        cite = r.get("source_citation") or {}
        lid = _s(r.get("leprohon_id"))
        if not lid:
            # Fail loud (Rule 2): a ruler node with no stable source id can't be
            # provenance-attributed and would collide with any other id-less row.
            raise ValueError(f"Leprohon row missing leprohon_id: {r!r}")
        out.append(
            RulerRecord(
                source_id="leprohon",
                # Prefix like every other loader so ids are globally unique across sources
                # (the local_id is the web PRIMARY KEY — an unprefixed id risks collision).
                local_id=f"leprohon-{lid}",
                display_name=_s(r.get("display_name")) or lid,
                alt_names=[str(x) for x in _list(r.get("alt_display_names"))],
                dynasty=_n(r.get("dynasty_number")),
                dynasty_label=_s(r.get("dynasty_label")),
                prenomina=_from_titulary_list(r.get("throne_names")),
                horus_names=_from_titulary_list(r.get("horus_names"))
                + _from_titulary_list(r.get("later_horus_names")),
                nomina=_from_titulary_list(r.get("birth_names")),
                reign_start_bce=None,
                reign_end_bce=None,
                intra_source_same_as=[],
                authority=auth,
                cited_page=_n(cite.get("printed_page")),
                cited_pdf_page=(
                    str(cite.get("physical_pdf_page"))
                    if cite.get("physical_pdf_page") is not None
                    else None
                ),
                stage_group=(
                    (_s(r.get("printed_under")) or _s(r.get("display_name")))
                    if _s(r.get("stage_suffix"))
                    else None
                ),
            )
        )
    return out


def load_beckerath(root: Path) -> list[RulerRecord]:
    auth = SOURCE_AUTHORITY["beckerath"]
    out = []
    for r in _read_jsonl(root, "beckerath-1997-chronologie"):
        if r.get("is_dynasty_marker") is True:
            continue  # period header, not a ruler
        name = _s(r.get("name"))
        if not name:
            continue
        prenomina: list[NameForm] = []
        scalar = _s(r.get("prenomen"))
        if scalar:
            prenomina.append(NameForm(surface=scalar))
        for t in _list(r.get("egyptian_titularies")):
            if isinstance(t, dict) and _s(t.get("kind")) == "prenomen" and _s(t.get("name")):
                prenomina.append(NameForm(surface=_s(t.get("name"))))
        if _s(r.get("egyptian_titulary_kind")) == "prenomen" and _s(r.get("egyptian_titulary")):
            prenomina.append(NameForm(surface=_s(r.get("egyptian_titulary"))))
        cite = r.get("source_citation") or {}
        out.append(
            RulerRecord(
                source_id="beckerath",
                local_id=f"beckerath-{_s(r.get('beckerath_id'))}",
                display_name=name,
                alt_names=[str(x) for x in _list(r.get("name_variants"))],
                dynasty=_n(r.get("dynasty")),
                dynasty_label=_s(r.get("period")),
                prenomina=prenomina,
                horus_names=[],
                nomina=[NameForm(surface=name)],
                reign_start_bce=_n(r.get("start_bce_low")) or _n(r.get("start_bce_high")),
                reign_end_bce=_n(r.get("end_bce_low")) or _n(r.get("end_bce_high")),
                intra_source_same_as=[],
                authority=auth,
                cited_pdf_page=_s(cite.get("pdf_pages")),
            )
        )
    return out


def load_kitchen(root: Path) -> list[RulerRecord]:
    auth = SOURCE_AUTHORITY["kitchen"]
    out = []
    for r in _read_jsonl(root, "kitchen-tipe"):
        name = _s(r.get("name"))
        if not name:
            continue
        prenomina: list[NameForm] = []
        # Prefer the structured set; the scalar is a human rendering
        # ("Usimare, then Sneferre") and must not be treated as one name (ADR-020).
        for p in _list(r.get("prenomens")):
            if isinstance(p, dict) and _s(p.get("name")):
                prenomina.append(NameForm(surface=_s(p.get("name"))))
        if not prenomina:
            scalar = _s(r.get("prenomen"))
            if scalar and "," not in scalar and "then" not in scalar.lower():
                prenomina.append(NameForm(surface=scalar))
        same = _s(r.get("same_person_as"))
        out.append(
            RulerRecord(
                source_id="kitchen",
                local_id=f"kitchen-{_s(r.get('kitchen_id'))}",
                display_name=name,
                alt_names=[],
                dynasty=_n(r.get("dynasty")),
                dynasty_label=_s(r.get("polity")),
                prenomina=prenomina,
                horus_names=[],
                nomina=[NameForm(surface=name)],
                reign_start_bce=_n(r.get("start_bce")),
                reign_end_bce=_n(r.get("end_bce")),
                intra_source_same_as=[f"kitchen-{same}"] if same else [],
                authority=auth,
            )
        )
    return out


def load_pharaoh_se(root: Path) -> list[RulerRecord]:
    auth = SOURCE_AUTHORITY["pharaoh_se"]
    out = []
    for r in _read_jsonl(root, "pharaoh-se"):
        display = _s(r.get("display"))
        if not display:
            continue
        prenomina = _from_titulary_list(r.get("throne_names"))
        scalar = _s(r.get("prenomen"))
        if not prenomina and scalar:
            prenomina.append(NameForm(surface=scalar))
        nomina: list[NameForm] = []
        if _s(r.get("nomen")):
            nomina.append(NameForm(surface=_s(r.get("nomen"))))
        nomina += _from_titulary_list(r.get("birth_names"))
        out.append(
            RulerRecord(
                source_id="pharaoh_se",
                local_id=f"pharaoh_se-{_s(r.get('slug'))}",
                display_name=display,
                alt_names=[str(x) for x in _list(r.get("alt_labels"))],
                dynasty=_n(r.get("dynasty_number")),
                dynasty_label=_s(r.get("dynasty_label")),
                prenomina=prenomina,
                horus_names=_from_titulary_list(r.get("horus_names")),
                nomina=nomina,
                reign_start_bce=_n(r.get("start_year")),
                reign_end_bce=_n(r.get("end_year")),
                intra_source_same_as=[],
                authority=auth,
            )
        )
    return out


def load_ryholt(root: Path) -> list[RulerRecord]:
    auth = SOURCE_AUTHORITY["ryholt"]
    out = []
    for r in _read_jsonl(root, "ryholt-1997-sip"):
        nomen = _s(r.get("nomen"))
        prenomen = _s(r.get("prenomen"))
        display = nomen or prenomen
        if not display:
            continue
        prenomina: list[NameForm] = []
        if prenomen or _s(r.get("prenomen_transliterated")):
            prenomina.append(
                NameForm(surface=prenomen or "", translit=_s(r.get("prenomen_transliterated")))
            )
        horus_names: list[NameForm] = []
        if _s(r.get("horus_name_transliterated")):
            horus_names.append(NameForm(surface="", translit=_s(r.get("horus_name_transliterated"))))
        out.append(
            RulerRecord(
                source_id="ryholt",
                local_id=f"ryholt-{_s(r.get('ryholt_id'))}",
                display_name=display,
                alt_names=[],
                dynasty=_n(r.get("dynasty")),
                dynasty_label=_s(r.get("dynasty_label")),
                prenomina=prenomina,
                horus_names=horus_names,
                nomina=[NameForm(surface=nomen or "", translit=_s(r.get("nomen_transliterated")))],
                reign_start_bce=_n(r.get("date_bce_start")),
                reign_end_bce=_n(r.get("date_bce_end")),
                intra_source_same_as=[],
                authority=auth,
            )
        )
    return out


@dataclass
class LoadResult:
    records: list[RulerRecord]
    per_source: dict[str, int] = field(default_factory=dict)


def load_all_sources(authority_root: Path) -> LoadResult:
    groups = [
        load_leprohon(authority_root),
        load_beckerath(authority_root),
        load_kitchen(authority_root),
        load_pharaoh_se(authority_root),
        load_ryholt(authority_root),
    ]
    records = [rec for g in groups for rec in g]
    per_source: dict[str, int] = {}
    for rec in records:
        per_source[rec.source_id] = per_source.get(rec.source_id, 0) + 1
    return LoadResult(records=records, per_source=per_source)
