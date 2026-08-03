"""Per-source adapters: map each source's native ``reconciled.jsonl`` row shape to the
canonical :class:`RulerRecord`. Extraction only — no cross-source resolution, no guessing.

Every row is read against an explicit schema (:func:`_req_str`, :func:`_opt_int`, …): a
field of the wrong type is schema drift and RAISES with source id, row id and field path
— it is never coerced to ``None``/``[]``. A silently-erased ``dynasty: 26 → "26"`` would
delete a sourced claim and leave no trace that it ever existed (Rule 2/6). A genuinely
absent nullable field stays ``None``; that is legitimate sparseness, not drift.

The only rows that may be skipped are ones EXPLICITLY classified as non-rulers by the
source itself (Beckerath's dynasty-marker/period-header rows). Those are counted and
returned in :class:`LoadResult.non_ruler_rows` — a visible drop report, never a silent
one. A row that is neither a ruler nor an explicitly-marked non-ruler raises."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .absence import ABSENCE_KEY, iter_absence_fields, parse_absence
from .normalize import NameForm

SOURCE_IDS = ("leprohon", "beckerath", "kitchen", "pharaoh_se", "ryholt")

# Every typed-absence field this loader KNOWS ABOUT, per source, as a dotted path with
# list indices elided. A row carrying an absence-signalling key that is NOT listed here
# raises (:func:`_assert_absence_consulted`).
#
# This registry exists because of a specific rot: Kitchen shipped
# ``prenomen_is_kitchen_unknown`` — a correct, page-cited typed assertion that the king
# exists but his throne name is not recorded — and the loader never read it, while
# reading the placeholder string in the adjacent ``prenomen`` field as if it were a name.
# A flag nobody consults is worse than no flag: it looks like the distinction is being
# honoured. Silence is not acceptable here; an unconsulted absence flag is a loud error.
_ABSENCE_CONSULTED: dict[str, frozenset[str]] = {
    "leprohon": frozenset(
        {
            "throne_names.absence",
            "horus_names.absence",
            "later_horus_names.absence",
            "birth_names.absence",
            "nebty_names.absence",
            "golden_horus_names.absence",
            "later_cartouche_names.absence",
            "seth_names.absence",
        }
    ),
    "beckerath": frozenset(),
    "kitchen": frozenset({"prenomen_absence"}),
    "pharaoh_se": frozenset(),
    "ryholt": frozenset(),
}

_LIST_INDEX = re.compile(r"\[\d+\]")


def _assert_absence_consulted(row: dict, *, source: str, row_id: str) -> None:
    """RAISE if the row ships an absence-signalling field the loader does not consult."""
    for path, _key, _value in iter_absence_fields(row):
        generic = _LIST_INDEX.sub("", path)
        if generic not in _ABSENCE_CONSULTED[source]:
            raise _err(
                source,
                row_id,
                path,
                "is a typed-absence flag that this loader does not consult. Either read "
                "it where the claim is built and register it in _ABSENCE_CONSULTED, or "
                "remove it from the source — an absence assertion nobody reads silently "
                "rots while the placeholder it describes keeps being loaded as a name.",
            )

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


# --- strict row-schema accessors -------------------------------------------


class SourceRowError(ValueError):
    """A source row violates the committed row schema for its source."""


def _err(source: str, row_id: str, path: str, msg: str) -> SourceRowError:
    return SourceRowError(f"[{source}] row {row_id}: field {path!r} {msg}")


def _opt_str(row: dict, path: str, *, source: str, row_id: str) -> str | None:
    """``None``/absent/empty → ``None``; a present non-string value is drift → raise."""
    v = row.get(path)
    if v is None:
        return None
    if not isinstance(v, str):
        raise _err(source, row_id, path, f"must be a string or null, got {type(v).__name__} ({v!r})")
    return v.strip() or None


def _req_str(row: dict, path: str, *, source: str, row_id: str) -> str:
    v = _opt_str(row, path, source=source, row_id=row_id)
    if v is None:
        raise _err(source, row_id, path, "is required but missing/empty")
    return v


def _opt_int(row: dict, path: str, *, source: str, row_id: str) -> int | None:
    v = row.get(path)
    if v is None:
        return None
    # bool is a subclass of int — a flag landing in a numeric field is drift, not a number.
    if isinstance(v, bool) or not isinstance(v, int):
        raise _err(source, row_id, path, f"must be an integer or null, got {type(v).__name__} ({v!r})")
    return v


def _opt_bool(row: dict, path: str, *, source: str, row_id: str) -> bool | None:
    v = row.get(path)
    if v is None:
        return None
    if not isinstance(v, bool):
        raise _err(source, row_id, path, f"must be a boolean or null, got {type(v).__name__} ({v!r})")
    return v


def _opt_dict(row: dict, path: str, *, source: str, row_id: str) -> dict:
    v = row.get(path)
    if v is None:
        return {}
    if not isinstance(v, dict):
        raise _err(source, row_id, path, f"must be an object or null, got {type(v).__name__} ({v!r})")
    return v


def _str_list(row: dict, path: str, *, source: str, row_id: str) -> list[str]:
    v = row.get(path)
    if v is None:
        return []
    if not isinstance(v, list):
        raise _err(source, row_id, path, f"must be a list or null, got {type(v).__name__} ({v!r})")
    out: list[str] = []
    for i, e in enumerate(v):
        if not isinstance(e, str) or not e.strip():
            raise _err(source, row_id, f"{path}[{i}]", f"must be a non-empty string, got {e!r}")
        out.append(e.strip())
    return out


def _dict_list(row: dict, path: str, *, source: str, row_id: str) -> list[dict]:
    v = row.get(path)
    if v is None:
        return []
    if not isinstance(v, list):
        raise _err(source, row_id, path, f"must be a list or null, got {type(v).__name__} ({v!r})")
    for i, e in enumerate(v):
        if not isinstance(e, dict):
            raise _err(source, row_id, f"{path}[{i}]", f"must be an object, got {type(e).__name__} ({e!r})")
    return v


def _paired_year(
    row: dict, low_path: str, high_path: str, *, source: str, row_id: str
) -> int | None:
    """Beckerath states every absolute date as a LOW/HIGH estimate pair.

    Committed policy (Rule 2 — a documented deterministic rule, not an arbitrary pick):
    the pair is represented by its LOW-estimate bound, i.e. the smaller BCE year number /
    later calendar date; the same bound is taken for every row, so the resulting series is
    internally consistent. The pair must be fully populated or fully absent — a
    half-populated pair is ambiguous (is the missing side unknown, or equal to the other?)
    and RAISES rather than falling through to whichever bound happens to exist. Note this
    is a value test, not a truth test: year ``0`` is a date, not "absent"."""
    low = _opt_int(row, low_path, source=source, row_id=row_id)
    high = _opt_int(row, high_path, source=source, row_id=row_id)
    if (low is None) != (high is None):
        raise _err(
            source,
            row_id,
            f"{low_path}/{high_path}",
            f"is a half-populated chronology bound pair (low={low!r}, high={high!r}); "
            f"cannot tell whether the missing bound is unknown or equal to the other",
        )
    return low


def _read_jsonl(root: Path, source: str) -> list[dict]:
    path = root / source / "reconciled.jsonl"
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# Placeholder text a source may print IN a name field to say "this name is not known".
# It is prose, not a name. Loaded verbatim it becomes a matching key — `(unknown)`
# normalises to {unknown, nknwn} — so two kings whose names are equally UNrecorded
# corroborate each other into an identity. That is a fabricated corroborator, and the
# absence of a fact must never behave like a fact (rule 2).
#
# Matched only as a WHOLE field, never as a substring: real titulary contains these
# letters (`heqa khasut aper-an-ti`, `mery nefer-kheperu-ra`), and a substring rule
# would delete genuine names.
# The trailing `(?)` alternative is Leprohon's own hedge (p. 43, Merenre II: `Horus:
# unknown (?)`). It is NOT cosmetic: `unknown (?)` normalises to exactly the same keys
# as `(unknown)` — {unknown, nknwn} — because the normalizer strips `?` and punctuation.
# The first version of this guard missed the hedged spelling, so Merenre II went on
# publishing `unknown` as a live Horus-name corroborator after the guard shipped.
_ABSENCE_SENTINEL = re.compile(
    r"^[\[\(\{]?\s*(?:prenomen|nomen|horus[\s-]?name|name)?\s*"
    r"(?:unknown|unattested|unbekannt|not\s+known|n/?a|none|null|lost|lacuna"
    r"|missing|destroyed)"
    r"\s*[\]\)\}]?\s*(?:\(\s*\?\s*\))?\s*[\]\)\}]?$",
    re.IGNORECASE,
)


def _is_absence_sentinel(value: str | None) -> bool:
    return bool(value and _ABSENCE_SENTINEL.match(value.strip()))


def _name_form(surface: str | None, translit: str | None = None) -> NameForm | None:
    """A NameForm, or ``None`` when every form present is placeholder prose.

    Returning ``None`` drops the claim rather than rewriting the committed row: the
    source faithfully records what its page prints, and editing `reconciled.jsonl`
    to erase that would be the rule-6 violation this guard exists to avoid.
    """
    s = None if _is_absence_sentinel(surface) else (surface or None)
    t = None if _is_absence_sentinel(translit) else (translit or None)
    if s is None and t is None:
        return None
    return NameForm(surface=s or "", translit=t)


def _append(forms: list[NameForm], surface: str | None) -> None:
    """Append a NameForm unless the value is placeholder prose (see _name_form)."""
    form = _name_form(surface)
    if form is not None:
        forms.append(form)


def _from_titulary_list(row: dict, path: str, *, source: str, row_id: str) -> list[NameForm]:
    """A Leprohon/pharaoh.se-style titulary list → NameForms. Every entry must be an object
    carrying at least one of an anglicised/native surface form or a transliteration; an
    entry with neither is a titulary claim that would vanish without trace → raise."""
    out: list[NameForm] = []
    for i, e in enumerate(_dict_list(row, path, source=source, row_id=row_id)):
        item = f"{path}[{i}]"
        surface = (
            _opt_str(e, "anglicised", source=source, row_id=row_id)
            or _opt_str(e, "name", source=source, row_id=row_id)
            or ""
        )
        translit = _opt_str(e, "transliteration", source=source, row_id=row_id)
        if ABSENCE_KEY in e:
            # The scholar states this name is not recorded. That is a claim ABOUT the
            # titulary slot, not a name in it — so the slot is loaded as carrying no
            # name claim at all. It is deliberately NOT dropped upstream in the data:
            # "Leprohon prints `(unknown)` here" and "Leprohon prints nothing here" are
            # different facts, and only the typed sibling keeps them apart.
            kind, printed_as = parse_absence(
                e[ABSENCE_KEY], where=f"[{source}] row {row_id}: {item}"
            )
            if surface or translit:
                raise _err(
                    source,
                    row_id,
                    item,
                    f"carries a typed absence ({kind}, printed as {printed_as!r}) AND a "
                    f"name ({surface or translit!r}). The source cannot both state the "
                    f"name is unknown and supply it; one of the two is wrong.",
                )
            continue
        if not surface and not translit:
            raise _err(source, row_id, item, f"has neither a name nor a transliteration: {e!r}")
        form = _name_form(surface, translit)
        if form is not None:
            out.append(form)
    return out


# --- per-source loaders ----------------------------------------------------


@dataclass
class SourceLoad:
    """One source's records plus the explicit, reported reasons rows were NOT loaded."""

    source_id: str
    records: list[RulerRecord]
    non_ruler_rows: list[tuple[str, str]] = field(default_factory=list)  # (row id, why)


def load_leprohon(root: Path) -> SourceLoad:
    src = "leprohon"
    auth = SOURCE_AUTHORITY[src]
    out = []
    for i, r in enumerate(_read_jsonl(root, "leprohon-2013-titulary"), 1):
        # The stable source id is REQUIRED (Rule 2): a ruler node with no stable id can't
        # be provenance-attributed, and every id-less row would collapse onto the same
        # ``<source>-None`` primary key in the web artifact.
        rid = _req_str(r, "leprohon_id", source=src, row_id=f"line {i}")
        _assert_absence_consulted(r, source=src, row_id=rid)
        cite = _opt_dict(r, "source_citation", source=src, row_id=rid)
        pdf_page = _opt_int(cite, "physical_pdf_page", source=src, row_id=rid)
        stage_suffix = _opt_str(r, "stage_suffix", source=src, row_id=rid)
        display_name = _req_str(r, "display_name", source=src, row_id=rid)
        out.append(
            RulerRecord(
                source_id=src,
                # Prefix like every other loader so ids are globally unique across sources
                # (the local_id is the web PRIMARY KEY — an unprefixed id risks collision).
                local_id=f"{src}-{rid}",
                display_name=display_name,
                alt_names=_str_list(r, "alt_display_names", source=src, row_id=rid),
                dynasty=_opt_int(r, "dynasty_number", source=src, row_id=rid),
                dynasty_label=_opt_str(r, "dynasty_label", source=src, row_id=rid),
                prenomina=_from_titulary_list(r, "throne_names", source=src, row_id=rid),
                horus_names=_from_titulary_list(r, "horus_names", source=src, row_id=rid)
                + _from_titulary_list(r, "later_horus_names", source=src, row_id=rid),
                nomina=_from_titulary_list(r, "birth_names", source=src, row_id=rid),
                reign_start_bce=None,
                reign_end_bce=None,
                intra_source_same_as=[],
                authority=auth,
                cited_page=_opt_int(cite, "printed_page", source=src, row_id=rid),
                cited_pdf_page=str(pdf_page) if pdf_page is not None else None,
                stage_group=(
                    (_opt_str(r, "printed_under", source=src, row_id=rid) or display_name)
                    if stage_suffix
                    else None
                ),
            )
        )
    return SourceLoad(source_id=src, records=out)


def load_beckerath(root: Path) -> SourceLoad:
    src = "beckerath"
    auth = SOURCE_AUTHORITY[src]
    out = []
    non_ruler: list[tuple[str, str]] = []
    for i, r in enumerate(_read_jsonl(root, "beckerath-1997-chronologie"), 1):
        rid = _req_str(r, "beckerath_id", source=src, row_id=f"line {i}")
        _assert_absence_consulted(r, source=src, row_id=rid)
        if _opt_bool(r, "is_dynasty_marker", source=src, row_id=rid) is True:
            # The ONLY sanctioned drop: the source itself marks this row as a period
            # header rather than a king. Reported, never silent.
            non_ruler.append((rid, "is_dynasty_marker (period header, not a ruler)"))
            continue
        name = _req_str(r, "name", source=src, row_id=rid)
        prenomina: list[NameForm] = []
        scalar = _opt_str(r, "prenomen", source=src, row_id=rid)
        if scalar:
            _append(prenomina, scalar)
        for j, t in enumerate(_dict_list(r, "egyptian_titularies", source=src, row_id=rid)):
            kind = _opt_str(t, "kind", source=src, row_id=rid)
            tname = _opt_str(t, "name", source=src, row_id=rid)
            if kind is None or tname is None:
                raise _err(
                    src, rid, f"egyptian_titularies[{j}]", f"needs both 'kind' and 'name': {t!r}"
                )
            if kind == "prenomen":
                _append(prenomina, tname)
        if _opt_str(r, "egyptian_titulary_kind", source=src, row_id=rid) == "prenomen":
            _append(prenomina, _req_str(r, "egyptian_titulary", source=src, row_id=rid))
        cite = _opt_dict(r, "source_citation", source=src, row_id=rid)
        out.append(
            RulerRecord(
                source_id=src,
                local_id=f"{src}-{rid}",
                display_name=name,
                alt_names=_str_list(r, "name_variants", source=src, row_id=rid),
                dynasty=_opt_int(r, "dynasty", source=src, row_id=rid),
                dynasty_label=_opt_str(r, "period", source=src, row_id=rid),
                prenomina=prenomina,
                horus_names=[],
                nomina=[NameForm(surface=name)],
                reign_start_bce=_paired_year(
                    r, "start_bce_low", "start_bce_high", source=src, row_id=rid
                ),
                reign_end_bce=_paired_year(
                    r, "end_bce_low", "end_bce_high", source=src, row_id=rid
                ),
                intra_source_same_as=[],
                authority=auth,
                cited_pdf_page=_opt_str(cite, "pdf_pages", source=src, row_id=rid),
            )
        )
    return SourceLoad(source_id=src, records=out, non_ruler_rows=non_ruler)


def load_kitchen(root: Path) -> SourceLoad:
    src = "kitchen"
    auth = SOURCE_AUTHORITY[src]
    out = []
    for i, r in enumerate(_read_jsonl(root, "kitchen-tipe"), 1):
        rid = _req_str(r, "kitchen_id", source=src, row_id=f"line {i}")
        _assert_absence_consulted(r, source=src, row_id=rid)
        name = _req_str(r, "name", source=src, row_id=rid)
        # Kitchen states, for two kings, that the throne name is not recorded (Table 3;
        # kitchen-tipe README §prenomen_absence). Consulting it here is the whole point
        # of the registry above: the flag is READ, and reading it means the row
        # contributes no prenomen claim rather than a placeholder one.
        prenomen_absence = r.get("prenomen_absence")
        if prenomen_absence is not None:
            parse_absence(prenomen_absence, where=f"[{src}] row {rid}: prenomen_absence")
        prenomina: list[NameForm] = []
        # Prefer the structured set; the scalar is a human rendering
        # ("Usimare, then Sneferre") and must not be treated as one name (ADR-020).
        for j, p in enumerate(_dict_list(r, "prenomens", source=src, row_id=rid)):
            pname = _opt_str(p, "name", source=src, row_id=rid)
            if pname is None:
                raise _err(src, rid, f"prenomens[{j}]", f"needs a 'name': {p!r}")
            _append(prenomina, pname)
        if not prenomina:
            scalar = _opt_str(r, "prenomen", source=src, row_id=rid)
            if scalar and "," not in scalar and "then" not in scalar.lower():
                _append(prenomina, scalar)
        if prenomen_absence is not None and prenomina:
            raise _err(
                src,
                rid,
                "prenomen_absence",
                f"states the throne name is not recorded, yet the row also supplies "
                f"{[f.surface for f in prenomina]!r}. Both cannot be true.",
            )
        same = _opt_str(r, "same_person_as", source=src, row_id=rid)
        out.append(
            RulerRecord(
                source_id=src,
                local_id=f"{src}-{rid}",
                display_name=name,
                alt_names=[],
                dynasty=_opt_int(r, "dynasty", source=src, row_id=rid),
                dynasty_label=_opt_str(r, "polity", source=src, row_id=rid),
                prenomina=prenomina,
                horus_names=[],
                nomina=[NameForm(surface=name)],
                reign_start_bce=_opt_int(r, "start_bce", source=src, row_id=rid),
                reign_end_bce=_opt_int(r, "end_bce", source=src, row_id=rid),
                intra_source_same_as=[f"{src}-{same}"] if same else [],
                authority=auth,
            )
        )
    return SourceLoad(source_id=src, records=out)


def load_pharaoh_se(root: Path) -> SourceLoad:
    src = "pharaoh_se"
    auth = SOURCE_AUTHORITY[src]
    out = []
    for i, r in enumerate(_read_jsonl(root, "pharaoh-se"), 1):
        rid = _req_str(r, "slug", source=src, row_id=f"line {i}")
        _assert_absence_consulted(r, source=src, row_id=rid)
        display = _req_str(r, "display", source=src, row_id=rid)
        prenomina = _from_titulary_list(r, "throne_names", source=src, row_id=rid)
        scalar = _opt_str(r, "prenomen", source=src, row_id=rid)
        if not prenomina and scalar:
            _append(prenomina, scalar)
        nomina: list[NameForm] = []
        nomen = _opt_str(r, "nomen", source=src, row_id=rid)
        if nomen:
            _append(nomina, nomen)
        nomina += _from_titulary_list(r, "birth_names", source=src, row_id=rid)
        out.append(
            RulerRecord(
                source_id=src,
                local_id=f"{src}-{rid}",
                display_name=display,
                alt_names=_str_list(r, "alt_labels", source=src, row_id=rid),
                dynasty=_opt_int(r, "dynasty_number", source=src, row_id=rid),
                dynasty_label=_opt_str(r, "dynasty_label", source=src, row_id=rid),
                prenomina=prenomina,
                horus_names=_from_titulary_list(r, "horus_names", source=src, row_id=rid),
                nomina=nomina,
                reign_start_bce=_opt_int(r, "start_year", source=src, row_id=rid),
                reign_end_bce=_opt_int(r, "end_year", source=src, row_id=rid),
                intra_source_same_as=[],
                authority=auth,
            )
        )
    return SourceLoad(source_id=src, records=out)


def load_ryholt(root: Path) -> SourceLoad:
    src = "ryholt"
    auth = SOURCE_AUTHORITY[src]
    out = []
    for i, r in enumerate(_read_jsonl(root, "ryholt-1997-sip"), 1):
        rid = _req_str(r, "ryholt_id", source=src, row_id=f"line {i}")
        # NB Ryholt's `is_lacunose` is NOT an absence flag and is deliberately absent
        # from the registry: its README §is_lacunose states the `[...]` marker is KEPT
        # in the name string because it shows the POSITION of missing characters. The
        # name is present and matchable; only some signs inside it are lost.
        _assert_absence_consulted(r, source=src, row_id=rid)
        nomen = _opt_str(r, "nomen", source=src, row_id=rid)
        prenomen = _opt_str(r, "prenomen", source=src, row_id=rid)
        display = nomen or prenomen
        if display is None:
            # Ryholt has no separate display field: a row with neither a nomen nor a
            # prenomen has no name at all and cannot be rendered or matched → raise.
            raise _err(src, rid, "nomen/prenomen", "row has neither a nomen nor a prenomen")
        prenomen_translit = _opt_str(r, "prenomen_transliterated", source=src, row_id=rid)
        prenomina: list[NameForm] = []
        pren_form = _name_form(prenomen, prenomen_translit)
        if pren_form is not None:
            prenomina.append(pren_form)
        horus_names: list[NameForm] = []
        horus_translit = _opt_str(r, "horus_name_transliterated", source=src, row_id=rid)
        horus_form = _name_form(None, horus_translit)
        if horus_form is not None:
            horus_names.append(horus_form)
        out.append(
            RulerRecord(
                source_id=src,
                local_id=f"{src}-{rid}",
                display_name=display,
                alt_names=[],
                dynasty=_opt_int(r, "dynasty", source=src, row_id=rid),
                dynasty_label=_opt_str(r, "dynasty_label", source=src, row_id=rid),
                prenomina=prenomina,
                horus_names=horus_names,
                nomina=[
                    NameForm(
                        surface=nomen or "",
                        translit=_opt_str(r, "nomen_transliterated", source=src, row_id=rid),
                    )
                ],
                reign_start_bce=_opt_int(r, "date_bce_start", source=src, row_id=rid),
                reign_end_bce=_opt_int(r, "date_bce_end", source=src, row_id=rid),
                intra_source_same_as=[],
                authority=auth,
            )
        )
    return SourceLoad(source_id=src, records=out)


@dataclass
class LoadResult:
    records: list[RulerRecord]
    per_source: dict[str, int] = field(default_factory=dict)
    # The drop report the module promises: source id → [(row id, why it is not a ruler)].
    non_ruler_rows: dict[str, list[tuple[str, str]]] = field(default_factory=dict)


def load_all_sources(authority_root: Path) -> LoadResult:
    groups = [
        load_leprohon(authority_root),
        load_beckerath(authority_root),
        load_kitchen(authority_root),
        load_pharaoh_se(authority_root),
        load_ryholt(authority_root),
    ]
    records = [rec for g in groups for rec in g.records]
    local_ids: dict[str, str] = {}
    for rec in records:
        if rec.local_id in local_ids:
            raise ValueError(
                f"Duplicate ruler local_id {rec.local_id!r}: the stable source ids are the "
                f"web artifact's PRIMARY KEY and must be unique across all sources."
            )
        local_ids[rec.local_id] = rec.source_id
    return LoadResult(
        records=records,
        per_source={g.source_id: len(g.records) for g in groups},
        non_ruler_rows={g.source_id: g.non_ruler_rows for g in groups if g.non_ruler_rows},
    )
