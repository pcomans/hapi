"""A king mention resolved in its record's context: the record's dynasty and dates against each
candidate king's dynasties and reign dates.

Name-only matching links a name to the one king the authority spells that way, whatever the record
says of its date: the Met's "Aya" records of Dynasty 18 (Ay, Tutankhamun's successor, whom the
authority spells "Ay") went to the Dynasty 13 king Merneferre Aya, the only king it spells "Aya"
(per-museum ruler test, 2026-10-17). The owner asked that king matching use the record's dynasty
and date (2026-10-17).

The rule, for the candidates the name gives (`Kings.resolve`):

- **The dynasty chooses among kings of one name.** A candidate fits when the record's single
  dynasty is one the king lists give the king, and is unknown when the record gives no single
  dynasty or the king lists give the king none. When the name gives several candidates, one that
  fits, with none unknown, resolves the mention (`record_context`): Dynasty 6 picks King Teti over
  Aha and Sekhemkhet, whom other lists also call Teti.
- **A candidate clashes with the record only when its dynasty and its dates both do**: the
  record's single dynasty is not the king's, and the record's date range lies clear of the king's
  reign widened by `DATE_SLACK_YEARS` on each side. A dynasty number alone is not a date: museums
  number by different chronologies (the Met puts Takeloth II in Aston's Theban Dynasty 23; three
  of the authority's four king lists put him in 22), and museum dates alone are loose (191 Met
  "reign of Ramesses IV" records carry the single year 1295 BCE). Two independent signals that
  agree are evidence; either alone is not (owner's choice, 2026-10-17).
- **A catalogued reign drops a clashing candidate.** A museum's reign field ("reign of Aya") dates
  the object to the reign. If every candidate clashes, the mention is unmatched
  (`record_context_conflict`).
- **Any other mention** (a royal cue in a title, "Scarab of King Thutmose III") may postdate the
  king it names: scarabs bearing Thutmose III's name were made for centuries after his reign. It
  never drops a candidate for clashing, except one that the same record's reign field dropped
  (`refused_on_record`): the record has already said the object is not of that king's reign, and
  its title names him with the same name.
- **Otherwise the name alone decides** as before: one candidate resolves, several are ambiguous.
  So a record with no dynasty links only when one king has the name (owner's choice, 2026-10-17).

A record whose reign field names a king of its own dynasty and reign period but the wrong one (the
Met's "Mentuhotep III" on records of Nebhepetre Mentuhotep II) is beyond this rule.
"""

from __future__ import annotations

from typing import Protocol

# Years by which a king's reign is widened on each side before it is compared with a record's dates.
DATE_SLACK_YEARS = 50
CONTEXT_RULE = "record_context"
CONFLICT_RULE = "record_context_conflict"


class Kings(Protocol):
    def resolve(self, name: str) -> dict: ...

    def dynasties(self, target_id: str) -> tuple[int, ...]: ...

    def reign(self, target_id: str) -> tuple[int, int] | None: ...


def record_range(date_start: int | None, date_end: int | None) -> tuple[int, int] | None:
    """A record's date range (years, negative BCE), or None when it gives no usable date; one bound
    alone is a single year. A range that ends before it starts is the museum's error (a Met
    "664–380 B.C." stored as -664..-712), not a date, so it is read as no date."""
    if date_start is None and date_end is None:
        return None
    start = date_start if date_start is not None else date_end
    end = date_end if date_end is not None else date_start
    if start > end:
        return None
    return start, end


def dynasty_fit(kings: Kings, target_id: str, record_dynasty: int | None) -> bool | None:
    """True when the record's dynasty is the king's, False when it is not, None when either is unknown."""
    dynasties = kings.dynasties(target_id)
    if record_dynasty is None or not dynasties:
        return None
    return record_dynasty in dynasties


def dates_clash(kings: Kings, target_id: str, dates: tuple[int, int] | None) -> bool:
    """Whether the record's dates lie clear of the king's reign widened by the slack; False when
    either has no dates."""
    reign = kings.reign(target_id)
    if dates is None or reign is None:
        return False
    return dates[1] < reign[0] - DATE_SLACK_YEARS or reign[1] + DATE_SLACK_YEARS < dates[0]


def clashes(kings: Kings, target_id: str, record_dynasty: int | None, dates: tuple[int, int] | None) -> bool:
    """Both the record's dynasty and its dates contradict this king (module rule)."""
    return dynasty_fit(kings, target_id, record_dynasty) is False and dates_clash(kings, target_id, dates)


def resolve_in_context(kings: Kings, name: str, *, record_dynasty: int | None, record_dates: tuple[int, int] | None,
                       catalogued_reign: bool, refused_on_record: frozenset[str]) -> dict:
    """The king `name` names in a record with this dynasty and date range (module rule)."""
    found = kings.resolve(name)
    if found["status"] == "unmatched":
        return {**found, "context_rule": None}
    candidates = found["target_ids"]
    fits = {t: dynasty_fit(kings, t, record_dynasty) for t in candidates}
    clash = {t: clashes(kings, t, record_dynasty, record_dates) for t in candidates}
    context = {"record_dynasty": record_dynasty, "record_dates": list(record_dates) if record_dates else None,
               "candidate_fit": dict(sorted(fits.items())), "candidate_clash": dict(sorted(clash.items()))}
    dropped = {t for t in candidates if (catalogued_reign and clash[t]) or t in refused_on_record}
    if dropped:
        context["dropped"] = sorted(dropped)
    kept = [t for t in candidates if t not in dropped]
    if not kept:
        return {**found, "status": "unmatched", "target_ids": [], "context_rule": CONFLICT_RULE, "context": context}
    fitting = [t for t in kept if fits[t] is True]
    if len(kept) > 1 and len(fitting) == 1 and all(fits[t] is not None for t in kept):
        return {**found, "status": "resolved", "target_ids": fitting, "context_rule": CONTEXT_RULE, "context": context}
    status = "resolved" if len(kept) == 1 else "ambiguous"
    # A context rule decided whenever it dropped a candidate the name gave.
    return {**found, "status": status, "target_ids": kept,
            "context_rule": CONTEXT_RULE if dropped and status == "resolved" else None, "context": context}
