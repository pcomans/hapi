"""A king mention resolved in its record's context: the record's dynasty, and then its dates,
against each candidate king's dynasties and reign dates.

Name-only matching links a name to the one king the authority spells that way, whatever the record
says of its date: the Met's "Aya" records of Dynasty 18 (Ay, Tutankhamun's successor, whom the
authority spells "Ay") went to the Dynasty 13 king Merneferre Aya, the only king it spells "Aya"
(per-museum ruler test, 2026-10-17). The owner asked that king matching use the record's dynasty
and date (2026-10-17).

The rule, for the candidates the name gives (`Kings.resolve`):

- **The dynasty decides.** A candidate fits when the record's single dynasty is one the king lists
  give the king, conflicts when it is not, and is unknown when the record gives no single dynasty
  or the king lists give the king none.
- **A catalogued reign is checked strictly.** A museum's reign field ("reign of Aya") says the
  object dates to that reign, so a candidate whose dynasty conflicts is dropped. If every
  candidate conflicts, the mention is unmatched (`record_context_conflict`).
- **Any other mention** (a royal cue in a title, "Scarab of King Thutmose III") may postdate the
  king it names: scarabs bearing Thutmose III's name were made for centuries after his reign. Its
  dynasty only chooses among the candidates; it never refuses the one candidate the name gives.
- **One candidate that fits, and none unknown, resolves the mention** (`record_context`).
- **Dates only break a tie between different kings.** When several candidates remain, all with
  reign dates and no two with the same label, the one whose reign, widened by `DATE_SLACK_YEARS`
  on each side, alone overlaps the record's date range resolves the mention (`record_date`).
  Candidates that share a label are the same king entered twice by different king lists (Djoser
  as `beckerath-03.02` and `cluster-leprohon-leprohon-3.01`); choosing one of them by its dates
  would be an arbitrary pick, so they stay ambiguous until the authority merges them. A candidate
  without reign dates cannot be compared, so then no date decides. A date never refuses a
  candidate: the museums' date
  fields are not precise enough. In the frozen corpus 191 Met records of "reign of Ramesses IV"
  are Dynasty 20, as he is, but carry the single year 1295 BCE, where Dynasty 19 begins; early
  chronologies differ by up to two centuries (Den: Met 3013 BCE, Leprohon 2814–2772).
- **Otherwise the name alone decides** as before: one candidate resolves, several are ambiguous.
  So a record with no dynasty or date links only when one king has the name (owner's choice,
  2026-10-17).

A record whose reign field names a king of its own dynasty but the wrong one (the Met's
"Mentuhotep III" on records of Nebhepetre Mentuhotep II) is beyond this rule: only a date could
tell them apart, and the dates cannot be trusted to.
"""

from __future__ import annotations

from typing import Protocol

# Years by which a king's reign is widened on each side before it is compared with a record's dates.
DATE_SLACK_YEARS = 50
CONTEXT_RULE = "record_context"
DATE_RULE = "record_date"
CONFLICT_RULE = "record_context_conflict"


class Kings(Protocol):
    def resolve(self, name: str) -> dict: ...

    def dynasties(self, target_id: str) -> tuple[int, ...]: ...

    def reign(self, target_id: str) -> tuple[int, int] | None: ...

    def label(self, target_id: str) -> str: ...


def record_range(date_start: int | None, date_end: int | None) -> tuple[int, int] | None:
    """A record's date range (years, negative BCE), or None when it gives no usable date; one bound
    alone is a single year. A range that ends before it starts is the museum's error (142 of the
    38,451 frozen records, e.g. a Met "664–380 B.C." stored as -664..-712), not a date, so it is read
    as no date; the record's dynasty is still compared."""
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


def date_fits(kings: Kings, target_id: str, dates: tuple[int, int] | None) -> bool:
    """Whether the king's reign, widened by the slack, overlaps the record's dates."""
    reign = kings.reign(target_id)
    if dates is None or reign is None:
        return False
    return dates[0] <= reign[1] + DATE_SLACK_YEARS and reign[0] - DATE_SLACK_YEARS <= dates[1]


def resolve_in_context(kings: Kings, name: str, *, record_dynasty: int | None, record_dates: tuple[int, int] | None,
                       strict: bool) -> dict:
    """The king `name` names in a record with this dynasty and date range (module rule)."""
    found = kings.resolve(name)
    if found["status"] == "unmatched":
        return {**found, "context_rule": None}
    fits = {t: dynasty_fit(kings, t, record_dynasty) for t in found["target_ids"]}
    context = {"record_dynasty": record_dynasty, "record_dates": list(record_dates) if record_dates else None,
               "candidate_fit": dict(sorted(fits.items()))}
    kept = [t for t in found["target_ids"] if not (strict and fits[t] is False)]
    if not kept:
        return {**found, "status": "unmatched", "target_ids": [], "context_rule": CONFLICT_RULE, "context": context}
    fitting = [t for t in kept if fits[t] is True]
    if len(fitting) == 1 and all(fits[t] is not None for t in kept):
        return {**found, "status": "resolved", "target_ids": fitting,
                "context_rule": CONTEXT_RULE if len(found["target_ids"]) > 1 or strict else None, "context": context}
    # Dates break a tie among the candidates whose dynasty fits, or else among those it cannot
    # judge; never in favour of a candidate whose dynasty conflicts.
    remaining = fitting or [t for t in kept if fits[t] is None]
    labels = [kings.label(t).casefold() for t in remaining]
    if (len(remaining) > 1 and len(set(labels)) == len(labels)
            and all(kings.reign(t) is not None for t in remaining)):
        dated = [t for t in remaining if date_fits(kings, t, record_dates)]
        context["candidates_in_date"] = dated
        if len(dated) == 1:
            return {**found, "status": "resolved", "target_ids": dated, "context_rule": DATE_RULE, "context": context}
    status = "resolved" if len(kept) == 1 else "ambiguous"
    return {**found, "status": status, "target_ids": kept, "context_rule": None, "context": context}
