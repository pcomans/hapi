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


def _prenomen_keys(rec: RulerRecord) -> set[str]:
    # skeleton on: the throne name is the primary corroborator; collapse epenthetic-vowel
    # spelling divergence. Over-generated candidates are gated by the homonym list +
    # reviewer, never auto-merged.
    return key_set(rec.prenomina, skeleton=True)


def _horus_keys(rec: RulerRecord) -> set[str]:
    return key_set(rec.horus_names, skeleton=True)


def _name_keys(rec: RulerRecord) -> set[str]:
    # skeleton OFF here: the loose name blocker must not fold every vowel-differing name
    # together, or name_only candidates explode with no precision benefit.
    forms: list[NameForm] = [NameForm(surface=rec.display_name)]
    forms += [NameForm(surface=n) for n in rec.alt_names]
    forms += rec.nomina
    return key_set(forms)


def _shared(a: set[str], b: set[str]) -> list[str]:
    return sorted(a & b)


def _reign_far_apart(a: RulerRecord, b: RulerRecord) -> bool:
    as_, bs = a.reign_start_bce, b.reign_start_bce
    if as_ is None or bs is None:
        return False
    # Cross-framework absolute chronology diverges with antiquity; use a generous,
    # period-scaled tolerance. Only "far apart" (centuries) is flagged, and even then it
    # is a HINT for escalation, never a hard block (ADR-020 §6 reign-span disjointness).
    tolerance = 150 + abs(as_) // 20
    return abs(as_ - bs) > tolerance


@dataclass
class _Indexed:
    rec: RulerRecord
    pren: set[str]
    horus: set[str]
    name: set[str]


def generate_candidates(records: list[RulerRecord]) -> list[Candidate]:
    idx = [
        _Indexed(rec, _prenomen_keys(rec), _horus_keys(rec), _name_keys(rec))
        for rec in records
    ]

    # Blocking: inverted index from any normalized key (prenomen ∪ horus ∪ name) to the
    # records carrying it. Only records sharing at least one key ever become a pair.
    by_key: dict[str, list[_Indexed]] = {}
    for item in idx:
        for k in item.pren | item.horus | item.name:
            by_key.setdefault(k, []).append(item)

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
                    homonym_trap = next((k for k in shared_pren if _is_homonym_key(k)), None)

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
                    )
                )

    candidates.sort(key=lambda c: c.id)
    return candidates


def uniqueness_clashes(candidates: list[Candidate]) -> set[str]:
    """If, among approvable candidates, a record in one source is the corroborated match
    of two *distinct* records from the other source, that is a clash — never resolved by
    an order-dependent incumbent; both escalate. Returns candidate ids forced to escalate.
    """
    approvable = [c for c in candidates if c.basis != "name_only" and not c.homonym_trap]
    forced: set[str] = set()
    groups: dict[str, list[Candidate]] = {}
    for c in approvable:
        groups.setdefault(f"{c.a_id}|{c.b_source}", []).append(c)
        groups.setdefault(f"{c.b_id}|{c.a_source}", []).append(c)
    for g in groups.values():
        distinct_targets = {f"{c.a_id}|{c.b_id}" for c in g}
        if len(distinct_targets) > 1:
            for c in g:
                forced.add(c.id)
    return forced
