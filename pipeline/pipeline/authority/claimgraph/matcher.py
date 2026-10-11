"""Stage-1 deterministic candidate generation + structured corroboration (ADR-020 §6).

Design choices that diverge deliberately from the PR-#303 prototype (which ADR-020 hands
to issue #306 to replace):

* Corroboration is SET-VALUED prenomen/throne-name intersection over the STRUCTURED
  titulary fields, on a deterministically normalized form — never scalar display names,
  never surface-string similarity (ADR-009/020).
* Name agreement ALONE never accepts; it produces a ``name_only`` candidate whose default
  disposition is escalation.
* There is NO transitive closure / connected-components clustering at match time. Every
  ``same_entity_as`` is an independent pairwise candidate, so an A~B, B~C pair never
  silently manufactures A~C (the Pinudjem I ↔ Menkheperre false merge, ADR-020 finding 1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .normalize import NameForm, key_set, keys_for_form
from .sources import RulerRecord

# Committed homonym exception list (ADR-020 decision 3). A shared prenomen among these is
# NOT sufficient to accept — the pair must escalate. Keys are computed with the same
# normalizer used for matching (skeleton included), so representative spellings — and any
# German/anglicised/transliterated variant that normalizes to them — stay in sync.
# Each entry pairs an anglicised spelling with a transliteration so a source that supplies
# only one form (e.g. Ryholt's translit, Beckerath's German) is still covered.
_HOMONYM_SPELLINGS = [
    # Thutmose III; HP Menkheperre; Necho I; contested Ini/Piye.
    "Menkheperre", "men kheper ra", "mn-ḫpr-rꜥ",
    # Amenhotep III; Ramesses VI; a standalone Nebmaatre.
    "Nebmaatre", "neb maat ra", "nb-mꜣꜥt-rꜥ",
    # Ramesses II + several TIP kings.
    "Usermaatre", "user maat ra", "wsr-mꜣꜥt-rꜥ",
    # THE most reused throne name: Pepi II, a cluster of Dyn 8 kings (Neby, Khendu,
    # Terru, Pepiseneb…), Herakleopolitan FIP kings, Neferkare Peftjauawybast (Dyn 23).
    "Neferkare", "nefer ka ra", "nfr-kꜣ-rꜥ",
    # Senwosret I and Nectanebo I — two famous, distinct kings.
    "Kheperkare", "kheper ka ra", "ḫpr-kꜣ-rꜥ",
    # Amenemhat I and a Dyn 13 king.
    "Sehetepibre", "sehetep ib ra", "sḥtp-ꞽb-rꜥ",
    # Khety (Herakleopolitan) and Bakenrenef (Dyn 24).
    "Wahkare", "wah ka ra", "wꜣḥ-kꜣ-rꜥ",
    # Amenemhat V and other Dyn 13 kings.
    "Sekhemkare", "sekhem ka ra", "sḫm-kꜣ-rꜥ",
]
_HOMONYM_KEYS: set[str] = key_set(
    [NameForm(surface=s) for s in _HOMONYM_SPELLINGS], skeleton=True
)
# Sekhemre-* compounds (Dyn 13/16/17): a prefix trap. NOTE: this is deliberately broad in
# the SAFE direction — it also escalates genuine same-king Sekhemre matches (a recall
# cost), because the many distinct Sekhemre-X kings make any Sekhemre-prefixed prenomen
# untrustworthy as a sole corroborator. Escalate, never merge.
# All normalized keys of the sample spellings become prefixes (sorted for determinism —
# NEVER next(iter(set)), whose result depends on hash order and would make the trap
# non-reproducible run to run). The skeleton form ``skhmr`` is what catches the many
# ``Sekhemre-X`` compounds regardless of their trailing element.
_SEKHEMRE_PREFIXES = sorted(
    {
        k
        for s in ("skhmra", "sekhemra", "sḫmrꜥ")
        for k in keys_for_form(NameForm(surface=s), skeleton=True)
        if len(k) >= 4
    }
)

_EARLY_DYNASTY_MAX = 3  # Re-formed prenomen not yet stable (ADR-020 carve-out)

# Era gate (ADR-020 amendment 2026-10-10, issue #342). A pair whose eras are far apart is
# REJECTED at stage 1 and never reaches the reviewer, whatever names it shares: Ramesses II
# and the four Dyn 22/23 kings who reused his throne name are ~400 years apart, and
# Leprohon's Amenhotep III and Dyn 6 Merenre ~900. Two independent tests, either suffices:
#
# * reign starts at least ERA_MIN_REIGN_START_GAP_YEARS apart AND beyond the period-scaled
#   cross-chronology tolerance (`chronology_tolerance`, the same tolerance the reviewer's
#   far-apart hint uses — one chronology rule, not two). Cross-framework dates diverge with
#   antiquity (Beckerath opens Dyn 1 ~3032 BCE vs Hornung–Krauss–Warburton ~2900), so the
#   threshold grows with age.
# * dynasty numbers more than ERA_MAX_DYNASTY_GAP apart — EXCEPT when both fall inside the
#   same contested band, where the sources number kings or parallel lines differently and
#   a dynasty gap is not evidence of distinct kings (the pair goes on to review):
#   - Dyn 6–10: von Beckerath's unplaced kings of the Dyn 8 era (Handbuch 1999, 70–71,
#     a–h: Sekhemkare, Wadjkare, Iti, Imhotep, Hotep, Khui, Isu, Iytjenu) are Leprohon's
#     "Dynasty 8a" but filed by pharaoh.se under Dyn 10 — pharaoh.se's own placement, not
#     a scholarly renumbering; and Ryholt derives the Turin list's Neith-iqerti (Leprohon's
#     Dyn 6 entry) from pharaoh.se's Dyn 8 Netjerkare Siptah.
#   - Dyn 13–17: Ryholt's Second Intermediate Period numbering differs from Beckerath's.
#   - Dyn 21–26: Takelot III is Dyn 22 in Beckerath, Dyn 23 in Kitchen; Kitchen files
#     Necho I under Dyn 24, Leprohon under Dyn 26.
# Every era-rejected pair is listed, with the earlier graph's verdict for it, and reviewed
# in docs/evaluations/ruler-cluster-reconciliation-342/results/.
ERA_MIN_REIGN_START_GAP_YEARS = 200
ERA_MAX_DYNASTY_GAP = 1
CONTESTED_DYNASTY_BANDS: tuple[tuple[int, int], ...] = ((6, 10), (13, 17), (21, 26))

# Where a SHARED dynasty number is itself unreliable — the sources put different blocks
# of kings under one number — so "both in Dyn N" cannot clear a reused throne name or
# decide a uniqueness clash. Dyn 8–10: Leprohon files every Herakleopolitan king as Dyn 9
# ("Dynasties 9–10a/b") where pharaoh.se splits them between 9 and 10, and pharaoh.se's
# Dyn 10 also holds the Dyn 8-era unplaced kings; pharaoh.se even carries a second Dyn 9
# Neferkare as a birth name, invisible to a throne-name bearer check. Dyn 6 and 7 are
# contested only for the era gate (Neith-iqerti/Netjerkare), so Pepi II (Dyn 6) still
# clears his reused Neferkare.
SHARED_DYNASTY_UNRELIABLE_BANDS: tuple[tuple[int, int], ...] = ((8, 10), (13, 17), (21, 26))


def chronology_tolerance(a_bce: int, b_bce: int) -> int:
    """Years two absolute dates for one reign may differ across chronological frameworks;
    grows with antiquity (ADR-020 §6)."""
    return 150 + max(abs(a_bce), abs(b_bce)) // 20


def _contested_band(dynasty: int) -> tuple[int, int] | None:
    return next((b for b in CONTESTED_DYNASTY_BANDS if b[0] <= dynasty <= b[1]), None)


def _shared_dynasty_reliable(dynasty: int) -> bool:
    return not any(lo <= dynasty <= hi for lo, hi in SHARED_DYNASTY_UNRELIABLE_BANDS)


def era_conflict(a: RulerRecord, b: RulerRecord) -> str | None:
    """The reason two records cannot denote one king because their eras are far apart, or
    ``None`` when the era evidence is compatible or absent (absence never rejects)."""
    if a.reign_start_bce is not None and b.reign_start_bce is not None:
        gap = abs(a.reign_start_bce - b.reign_start_bce)
        limit = max(ERA_MIN_REIGN_START_GAP_YEARS,
                    chronology_tolerance(a.reign_start_bce, b.reign_start_bce) + 1)
        if gap >= limit:
            return (
                f"Reign starts {gap} years apart ({a.reign_start_bce} vs "
                f"{b.reign_start_bce}); >= {limit} is distinct kings."
            )
    if a.dynasty is not None and b.dynasty is not None:
        gap = abs(a.dynasty - b.dynasty)
        band = _contested_band(a.dynasty)
        if gap > ERA_MAX_DYNASTY_GAP and (band is None or band != _contested_band(b.dynasty)):
            return (
                f"Dynasties {a.dynasty} and {b.dynasty} are {gap} apart and not within one "
                f"contested numbering band {CONTESTED_DYNASTY_BANDS}."
            )
    return None


def _is_homonym_key(k: str) -> bool:
    if k in _HOMONYM_KEYS:
        return True
    return any(p and k.startswith(p) for p in _SEKHEMRE_PREFIXES)


@dataclass
class Candidate:
    id: str
    a_id: str
    b_id: str
    a_source: str
    b_source: str
    a_name: str
    b_name: str
    basis: str  # "prenomen" | "horus_early" | "name_only"
    shared_prenomen_keys: list[str]
    shared_name_keys: list[str]
    dynasty_match: bool | None
    reign_far_apart: bool
    homonym_trap: str | None
    era_conflict: str | None = None
    # Both records carry the same dynasty number, outside SHARED_DYNASTY_UNRELIABLE_BANDS —
    # the only setting in which a shared dynasty is evidence.
    same_uncontested_dynasty: bool = False


def _join(a: str | None, b: str | None) -> str | None:
    return f"{a} {b}" if a and b else None


def _matchable(forms: list[NameForm], *, compound: bool = False) -> list[NameForm]:
    """The forms a name slot contributes to matching.

    An epithet the source records as ADDED to a name ("Whom Re has loved", mr.n rꜥ) is not
    itself a name: alone as a key it collides with any king whose name it happens to spell
    (Amenhotep III's epithet mr.n rꜥ vs the Dyn 6 throne name Merenre), so it never
    matches alone.

    With ``compound`` (throne names only), the slot's PRIMARY name — the first non-epithet
    form, the source's variant 1 — is also matched together with each added epithet, as the
    cartouche the source says was written: Leprohon's Ramesses II throne name wsr mꜣꜥt rꜥ
    plus his added epithet stp.n rꜥ is the Usermaatre-setepenre that Beckerath and
    pharaoh.se print as one throne name. Only the primary name is compounded, because an
    epithet the source attaches to the slot is not attested with every variant (Thutmose
    III's year-22 epithets never stood with his early Menkheperkare). Birth names are never
    compounded: epithets such as ḥqꜣ wꜣst turn one king's birth name into another's
    (Amenhotep II + ḥqꜣ wꜣst spells Amenhotep III's nomen). A compound only corroborates
    when another source independently prints it."""
    names = [f for f in forms if not f.is_added_epithet]
    if not compound or not names:
        return names
    epithets = [f for f in forms if f.is_added_epithet]
    primary = names[0]
    compounds = [
        NameForm(
            surface=_join(primary.surface, e.surface) or "",
            translit=_join(primary.translit, e.translit),
        )
        for e in epithets
    ]
    return names + [c for c in compounds if c.surface or c.translit]


# A gap the source marks in a name it could only partly read: Leprohon `///`, pharaoh.se
# `//` / `...` / `[..]`, Ryholt `[...]` / `...`. NOT a lone `/` (Beckerath and Kitchen use
# it between alternative readings, `A-qen-en-rê/A-user-rê`) and NOT a bracketed
# restoration (`[nemty?]`), which supplies text rather than marking its absence.
_LACUNA = re.compile(r"/{2,}|\.{2,}|…")


def _is_fragmentary(form: NameForm) -> bool:
    return any(_LACUNA.search(v) for v in (form.surface, form.translit or "") if v)


def _corroborating(forms: list[NameForm], *, compound: bool = False) -> list[NameForm]:
    """Throne/Horus forms that may corroborate an identity. A fragmentary name never does:
    with the gap stripped, `Senefer[...]re` keys to `snfrr`, Piye's complete Sneferre, and
    `Djed /// Re` fits every Djed-…-re king of Dyn 13–14. Such pairs stay name-only and
    escalate deterministically."""
    return [f for f in _matchable(forms, compound=compound) if not _is_fragmentary(f)]


def _prenomen_keys(rec: RulerRecord) -> set[str]:
    # skeleton on: the throne name is the primary corroborator; collapse epenthetic-vowel
    # spelling divergence. Over-generated candidates are gated by the homonym list +
    # reviewer, never auto-merged.
    return key_set(_corroborating(rec.prenomina, compound=True), skeleton=True)


def _horus_keys(rec: RulerRecord) -> set[str]:
    return key_set(_corroborating(rec.horus_names), skeleton=True)


def _name_keys(rec: RulerRecord) -> set[str]:
    # skeleton OFF here: the loose name blocker must not fold every vowel-differing name
    # together, or name_only candidates explode with no precision benefit.
    forms: list[NameForm] = []
    # `display_name` has two roles — what we render, and what we match on. When the
    # source's designation is a statement that the name is LOST (Leprohon's "Name Lost",
    # "Five Names Lost"), only the first role survives: `namelost` is not a name two
    # records can share, and two king-list entries lost in different lists are not the
    # same king. Leprohon alone carries eight such rows, two of them already colliding
    # on `namelost`.
    #
    # Gated on the typed field, never on the string: `Kloster` (iDAI's
    # Katharinenkloster, Simeonskloster, Jeremias-Kloster) CONTAINS "lost", so any
    # substring test here would strike real places out of the blocker.
    if rec.display_name_absence is None:
        forms.append(NameForm(surface=rec.display_name))
    forms += [NameForm(surface=n) for n in rec.alt_names]
    forms += _matchable(rec.nomina)
    return key_set(forms)


def _shared(a: set[str], b: set[str]) -> list[str]:
    return sorted(a & b)


def _reign_far_apart(a: RulerRecord, b: RulerRecord) -> bool:
    as_, bs = a.reign_start_bce, b.reign_start_bce
    if as_ is None or bs is None:
        return False
    # Beyond the cross-framework tolerance but under the era gate's 200-year floor (only
    # possible after ~1000 BCE): a HINT for escalation, never a hard block.
    return abs(as_ - bs) > chronology_tolerance(as_, bs)


@dataclass
class _Indexed:
    rec: RulerRecord
    pren: set[str]
    horus: set[str]
    name: set[str]


def generate_candidates(records: list[RulerRecord]) -> list[Candidate]:
    person_of = same_person_groups(records)
    idx = [
        _Indexed(rec, _prenomen_keys(rec), _horus_keys(rec), _name_keys(rec))
        for rec in records
    ]

    # Blocking: inverted index from any normalized key (prenomen ∪ horus ∪ name) to the
    # records carrying it. Only records sharing at least one key ever become a pair.
    by_key: dict[str, list[_Indexed]] = {}
    by_pren: dict[str, list[_Indexed]] = {}
    for item in idx:
        for k in item.pren | item.horus | item.name:
            by_key.setdefault(k, []).append(item)
        for k in item.pren:
            by_pren.setdefault(k, []).append(item)

    seen: set[str] = set()
    candidates: list[Candidate] = []

    for bucket in by_key.values():
        for i in range(len(bucket)):
            for j in range(i + 1, len(bucket)):
                x, y = bucket[i], bucket[j]
                if x.rec.source_id == y.rec.source_id:
                    continue  # cross-source only
                if x.rec.local_id > y.rec.local_id:
                    x, y = y, x  # deterministic ordering
                pair_key = f"{x.rec.local_id}|{y.rec.local_id}"
                if pair_key in seen:
                    continue
                seen.add(pair_key)

                shared_pren = _shared(x.pren, y.pren)
                shared_horus = _shared(x.horus, y.horus)
                shared_name = _shared(x.name, y.name)
                if not shared_pren and not shared_horus and not shared_name:
                    continue

                dynasty_match = (
                    (x.rec.dynasty == y.rec.dynasty)
                    if (x.rec.dynasty is not None and y.rec.dynasty is not None)
                    else None
                )
                # NB: `is not None`, not `or 99` — Dynasty 0 (Narmer et al.) is exactly the
                # earliest-dynasty case the Horus-name basis exists to serve; truthiness
                # would misclassify it as "missing dynasty".
                xd = x.rec.dynasty if x.rec.dynasty is not None else 99
                yd = y.rec.dynasty if y.rec.dynasty is not None else 99
                early = xd <= _EARLY_DYNASTY_MAX and yd <= _EARLY_DYNASTY_MAX

                if shared_pren:
                    basis = "prenomen"
                elif early and shared_horus:
                    basis = "horus_early"
                else:
                    basis = "name_only"

                homonym_trap = None
                if basis == "prenomen":
                    # Trapped when every shared REUSED throne name is ambiguous for this
                    # pair; cleared when ANY of them is unambiguous. Keys off the committed
                    # homonym list neither trap nor clear: the list is the record of reused
                    # names, and reuse of a compound within a block surfaces as a
                    # uniqueness clash instead (the Dyn 21–22 Hedjkheperre-setepenre kings).
                    # Thutmose III's sources share the full Menkheperre, which only he
                    # bears in Dyn 18, so the vowel-less skeleton `mnkhprr` that Thutmose
                    # IV's Menkheperure also yields does not veto the pair; the reviewer
                    # still judges it.
                    reused = [k for k in shared_pren if _is_homonym_key(k)]
                    ambiguous = [
                        k
                        for k in reused
                        if not _sole_bearers_in_dynasty(x, y, k, by_pren, person_of)
                    ]
                    if reused and len(ambiguous) == len(reused):
                        homonym_trap = ambiguous[0]

                candidates.append(
                    Candidate(
                        id=f"cand-{pair_key}",
                        a_id=x.rec.local_id,
                        b_id=y.rec.local_id,
                        a_source=x.rec.source_id,
                        b_source=y.rec.source_id,
                        a_name=x.rec.display_name,
                        b_name=y.rec.display_name,
                        basis=basis,
                        shared_prenomen_keys=shared_pren,
                        shared_name_keys=shared_name,
                        dynasty_match=dynasty_match,
                        reign_far_apart=_reign_far_apart(x.rec, y.rec),
                        homonym_trap=homonym_trap,
                        era_conflict=era_conflict(x.rec, y.rec),
                        same_uncontested_dynasty=bool(dynasty_match)
                        and _shared_dynasty_reliable(x.rec.dynasty),
                    )
                )

    candidates.sort(key=lambda c: c.id)
    return candidates


def _sole_bearers_in_dynasty(
    x: _Indexed,
    y: _Indexed,
    key: str,
    by_pren: dict[str, list[_Indexed]],
    person_of: dict[str, str],
) -> bool:
    """Whether a reused throne name is nonetheless unambiguous FOR THIS PAIR: both records
    are in one dynasty outside SHARED_DYNASTY_UNRELIABLE_BANDS, and no other PERSON from
    either source bears the name in that dynasty. Amenhotep III is the only Nebmaatre of
    Dynasty 18 in every source; the reuse by a Dyn 17 king and by Ramesses VI cannot be
    confused with him inside that block. Where dynasty numbers are unreliable (the
    bands) the trap always holds.

    A source's own stage rows of one king are one bearer (Leprohon's Thutmose III (a)/(b)
    are not rival Menkheperres). A bearer with NO dynasty does not block: its own pairs
    with this king share no dynasty, so they stay trapped, and lifting the trap here only
    sends the pair to the reviewer — it never approves."""
    d = x.rec.dynasty
    if d is None or d != y.rec.dynasty or not _shared_dynasty_reliable(d):
        return False
    sources = {x.rec.source_id, y.rec.source_id}
    pair = {person_of[x.rec.local_id], person_of[y.rec.local_id]}
    return not any(
        o.rec.source_id in sources
        and person_of[o.rec.local_id] not in pair
        and o.rec.dynasty == d
        for o in by_pren[key]
    )


def same_person_groups(records: list[RulerRecord]) -> dict[str, str]:
    """Map every record to a representative of the person its own source says it is: the
    smallest local id among it and the records its source declares identical
    (``intra_source_same_as``). A record with no such declaration represents itself."""
    linked: dict[str, set[str]] = {r.local_id: set() for r in records}
    for r in records:
        for other in r.intra_source_same_as:
            linked[r.local_id].add(other)
            linked[other].add(r.local_id)
    rep: dict[str, str] = {}
    for start in sorted(linked):
        if start in rep:
            continue
        component, frontier = {start}, [start]
        while frontier:
            for nxt in linked[frontier.pop()] - component:
                component.add(nxt)
                frontier.append(nxt)
        for local_id in component:
            rep[local_id] = min(component)
    return rep


def uniqueness_clashes(
    candidates: list[Candidate], person_of: dict[str, str] | None = None
) -> set[str]:
    """If, among approvable candidates, a record in one source is the corroborated match
    of two *distinct* persons from the other source, that is a clash — never resolved by
    an order-dependent incumbent; both escalate. Returns candidate ids forced to escalate.

    Two records the other source itself declares one person (``person_of``, from
    :func:`same_person_groups`) are one target, not two: Beckerath's single Amenophis IV
    matching Leprohon's Amenhotep IV and Akhenaten stage rows is not a clash (ADR-020:
    stage-suffix phase siblings are one person).

    One clash is resolved by rule rather than escalated whole: when exactly one of the
    competing targets shares the record's dynasty outside SHARED_DYNASTY_UNRELIABLE_BANDS,
    and every other target is in a different dynasty, only the others escalate. pharaoh.se's
    Ramesses II (Dyn 19) shares a full throne name with Leprohon's Ramesses II (Dyn 19)
    AND Ramesses IV (Dyn 20); outside those bands a shared dynasty number is reliable
    (the premise of the era gate), so the Dyn 20 king is the homonym. The surviving pair
    is still judged by the reviewer — the rule only stops escalating it unseen."""
    person_of = person_of or {}
    approvable = [
        c
        for c in candidates
        if c.basis != "name_only" and not c.homonym_trap and not c.era_conflict
    ]
    def person(local_id: str) -> str:
        return person_of.get(local_id, local_id)

    forced: set[str] = set()
    groups: dict[str, list[Candidate]] = {}
    for c in approvable:
        # Grouped by PERSON too: two stage rows of one king matching two distinct records
        # of the other source is still that one king matching two people — a clash.
        groups.setdefault(f"{person(c.a_id)}|{c.b_source}", []).append(c)
        groups.setdefault(f"{person(c.b_id)}|{c.a_source}", []).append(c)
    for g in groups.values():
        distinct_targets = {frozenset((person(c.a_id), person(c.b_id))) for c in g}
        if len(distinct_targets) <= 1:
            continue
        same_dynasty = {
            frozenset((person(c.a_id), person(c.b_id))) for c in g if c.same_uncontested_dynasty
        }
        # An alternative whose dynasty is unknown (dynasty_match None) is not evidence of a
        # different king, so its presence keeps the whole clash escalated.
        resolvable = len(same_dynasty) == 1 and all(
            c.same_uncontested_dynasty or c.dynasty_match is False for c in g
        )
        for c in g:
            if resolvable and frozenset((person(c.a_id), person(c.b_id))) in same_dynasty:
                continue
            forced.add(c.id)
    return forced
