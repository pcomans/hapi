"""Typed absence: the difference between "the source is silent" and "the source
states the value is not known".

Two genuinely different facts were being stored as one:

* **not printed** — the page simply gives no throne name for this king. Silence.
  Represented by the value field being ``null`` with **no** absence sibling. It
  needs no vocabulary term, because it is the ordinary sparse-field case (Rule 4:
  a fact recorded in one place, not two).
* **stated unknown** — the scholar positively asserts the name is not recorded.
  Leprohon prints ``(unknown)`` / ``unknown`` / ``unknown (?)`` in the titulary
  slot; Kitchen prints ``[Prenomen unknown]`` in the prenomen column. That
  assertion is *sourced information with a page citation* — collapsing it into
  silence destroys a scholarly claim (Rule 1).

The old encoding put the scholar's prose INTO the name field. Loaded verbatim it
became a matching key — ``(unknown)`` normalises to ``{unknown, nknwn}`` — so two
kings whose throne names are equally UNrecorded corroborated each other into an
identity. The absence of a fact behaved like a fact (Rule 2).

Representation
--------------
The value field is ``null``; a typed sibling records the reason **out of band**::

    {"kind": "stated_unknown", "printed_as": "(unknown)"}

``printed_as`` retains the scholar's exact printed token, so migrating a row to
this shape loses nothing that the page carried (Rule 6) — the token simply stops
living in the field that means "this IS the name".

Placement is by convention, enforced by :func:`iter_absence_fields`:

* key ``"absence"`` — on an object that owns exactly one name (a Leprohon
  titulary entry: the entry *is* the name slot).
* key ``"<field>_absence"`` — sibling of a named scalar (Kitchen's
  ``prenomen`` → ``prenomen_absence``).

Vocabulary
----------
``ABSENCE_KINDS`` has exactly ONE term. It is justified only by what the committed
sources actually distinguish, never by what is imaginable:

* ``stated_unknown`` — attested in Leprohon p. 37 / 39 / 42 / 43 (``(unknown)``,
  bare ``unknown``, ``unknown (?)``) and Kitchen (``[Prenomen unknown]``,
  kitchen-tipe README §85).

Deliberately NOT minted:

* a separate term for Leprohon's ``(?)`` hedge on p. 43. The arbiter rationales in
  ``tie-break-overrides.json`` distinguish the three printed *spellings*, but no
  committed material defines what force the ``(?)`` carries, so asserting a second
  epistemic class would be a guess. The hedge is preserved verbatim in
  ``printed_as`` instead.
* a term for ``////`` (Leprohon's epigraphic lacuna marker). That is a different
  fact — an *attested* inscription whose signs are destroyed, not a statement that
  the name is unknown — and no row is migrated to it.
* a term for "not printed". That is the absent-sibling case, above.

Extending this vocabulary requires a committed page citation showing the source
draws the distinction. Absent that, the term does not exist.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

#: The controlled vocabulary. See the module docstring for why it has one term.
ABSENCE_KINDS: frozenset[str] = frozenset({"stated_unknown"})

#: Exact key used when the enclosing object owns exactly one name.
ABSENCE_KEY = "absence"

#: Suffix used when the absence is a sibling of a named scalar field.
ABSENCE_SUFFIX = "_absence"


class AbsenceError(ValueError):
    """A typed-absence value violates the committed representation."""


def is_absence_key(key: str) -> bool:
    """Whether ``key`` is a typed-absence field under the committed convention."""
    return key == ABSENCE_KEY or key.endswith(ABSENCE_SUFFIX)


def is_absence_signal_key(key: str) -> bool:
    """Whether ``key`` *looks like* it signals an absence, under any naming shape
    attested in this repo.

    Broader than :func:`is_absence_key` on purpose. This is the anti-rot net: it is
    what lets the loader RAISE when a source ships an absence flag the loader never
    consults. Kitchen shipped ``prenomen_is_kitchen_unknown`` — a correct, page-cited
    typed assertion — and the loader ignored it for the entire life of the field
    while happily reading the placeholder string next to it. Silence about a flag you
    do not read is the failure; it must be loud (Rule 2).
    """
    return is_absence_key(key) or "unknown" in key.lower()


def iter_absence_fields(obj: Any, path: str = "") -> Iterator[tuple[str, str, Any]]:
    """Yield ``(dotted_path, key, value)`` for every absence-signalling key in a row,
    at any nesting depth. Used both to validate and to enforce that every such field
    is consulted."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            here = f"{path}.{k}" if path else k
            if is_absence_signal_key(k):
                yield here, k, v
            else:
                yield from iter_absence_fields(v, here)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_absence_fields(v, f"{path}[{i}]")


def parse_absence(value: Any, *, where: str) -> tuple[str, str]:
    """Validate one typed-absence object → ``(kind, printed_as)``.

    Raises on anything off-vocabulary or malformed. An unrecognised ``kind`` is NOT
    tolerated: it would mean the loader is silently dropping a distinction the source
    took the trouble to make.
    """
    if not isinstance(value, dict):
        raise AbsenceError(
            f"{where}: typed absence must be an object, got "
            f"{type(value).__name__} ({value!r})"
        )
    unexpected = set(value) - {"kind", "printed_as"}
    if unexpected:
        raise AbsenceError(f"{where}: unexpected typed-absence keys {sorted(unexpected)!r}")
    kind = value.get("kind")
    if kind not in ABSENCE_KINDS:
        raise AbsenceError(
            f"{where}: unknown absence kind {kind!r}; the committed vocabulary is "
            f"{sorted(ABSENCE_KINDS)!r}. Adding a term requires a page citation "
            f"showing the source draws the distinction."
        )
    printed_as = value.get("printed_as")
    if not isinstance(printed_as, str) or not printed_as.strip():
        raise AbsenceError(
            f"{where}: 'printed_as' must be the scholar's exact printed token, got "
            f"{printed_as!r}. Without it the migration would erase what the page shows."
        )
    return kind, printed_as
