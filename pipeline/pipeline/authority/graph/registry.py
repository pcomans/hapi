"""Predicate-registry loader and validator (ADR-018 § "Predicate registry").

The registry is the controlled vocabulary of P177-target claim predicates. This
module loads ``predicate_registry.json`` and enforces every invariant the ADR
states, deterministically (Constitutional rule 3): missing fields, the
``p177_target == NOT derived`` rule, the ``emit_shortcut`` permission rule, and
existence of every ``subject_class`` / ``value_class`` / ``crm_nearest`` in the
vendored CIDOC catalogue. Anything off fails loud (Constitutional rule 2).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .cidoc_spec import load_catalogue

_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "predicate_registry.json"

_REQUIRED_FIELDS = {
    "id",
    "label",
    "definition",
    "subject_class",
    "value_class",
    "value_cardinality",
    "crm_nearest",
    "is_symmetric",
    "derived",
    "p177_target",
    "emit_shortcut",
    "notes",
}
_CARDINALITIES = {"single", "multi"}


@dataclass(frozen=True)
class Predicate:
    id: str
    label: str
    definition: str
    subject_class: str
    value_class: str
    value_cardinality: str
    crm_nearest: str | None
    is_symmetric: bool
    derived: bool
    p177_target: bool
    emit_shortcut: bool
    notes: str | None

    @property
    def local_name(self) -> str:
        """The hapi local name, e.g. ``same_entity_as`` for ``hapi:same_entity_as``."""
        return self.id.split(":", 1)[1] if ":" in self.id else self.id


class RegistryError(ValueError):
    """Raised on any predicate-registry validation failure."""


def _validate_entry(raw: dict[str, Any], catalogue) -> Predicate:
    missing = _REQUIRED_FIELDS - raw.keys()
    if missing:
        raise RegistryError(
            f"Predicate {raw.get('id', '<unknown>')!r} missing fields: {sorted(missing)}"
        )
    extra = raw.keys() - _REQUIRED_FIELDS
    if extra:
        raise RegistryError(
            f"Predicate {raw['id']!r} has unknown fields: {sorted(extra)}"
        )

    pid = raw["id"]
    if not isinstance(pid, str) or not pid.startswith("hapi:"):
        raise RegistryError(f"Predicate id {pid!r} must be 'hapi:'-prefixed")

    for boolean in ("is_symmetric", "derived", "p177_target", "emit_shortcut"):
        if not isinstance(raw[boolean], bool):
            raise RegistryError(f"{pid}: field {boolean!r} must be a bool")

    if raw["value_cardinality"] not in _CARDINALITIES:
        raise RegistryError(
            f"{pid}: value_cardinality must be one of {_CARDINALITIES}, "
            f"got {raw['value_cardinality']!r}"
        )

    # Rule: p177_target == NOT derived (registry is P177-target-scoped).
    if raw["p177_target"] != (not raw["derived"]):
        raise RegistryError(
            f"{pid}: p177_target ({raw['p177_target']}) must equal NOT derived "
            f"({not raw['derived']})"
        )

    # Rule: emit_shortcut only when p177_target; must be false otherwise.
    if not raw["p177_target"] and raw["emit_shortcut"]:
        raise RegistryError(
            f"{pid}: emit_shortcut must be false when p177_target is false"
        )

    # Existence of subject/value classes in the vendored catalogue.
    for field_name in ("subject_class", "value_class"):
        code = raw[field_name]
        if not catalogue.has_class(code):
            raise RegistryError(
                f"{pid}: {field_name}={code!r} is not a CIDOC class in the catalogue"
            )

    # crm_nearest, when present, must resolve to a real CRM/CRMdig property.
    nearest = raw["crm_nearest"]
    if nearest is not None and not catalogue.has_property(nearest):
        raise RegistryError(
            f"{pid}: crm_nearest={nearest!r} is not a CIDOC/CRMdig property"
        )

    # The hapi predicate itself must be declared in the extension manifest.
    pred = Predicate(**raw)
    if not catalogue.has_property(pred.local_name):
        raise RegistryError(
            f"{pid}: not declared as a property in hapi_extension.rdf "
            f"(local name {pred.local_name!r})"
        )
    return pred


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Predicate]:
    """Load + validate the registry; return {predicate_id: Predicate}."""
    if not _REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Predicate registry missing: {_REGISTRY_PATH}")
    data = json.loads(_REGISTRY_PATH.read_text())
    catalogue = load_catalogue()

    predicates: dict[str, Predicate] = {}
    for raw in data["predicates"]:
        pred = _validate_entry(raw, catalogue)
        if pred.id in predicates:
            raise RegistryError(f"Duplicate predicate id {pred.id!r}")
        predicates[pred.id] = pred
    return predicates


def primary_predicates() -> dict[str, Predicate]:
    """P177-target predicates that materialise an :E55 Type (``p177_target``)."""
    return {pid: p for pid, p in load_registry().items() if p.p177_target}


def derived_predicates() -> dict[str, Predicate]:
    """Derived / query-only predicates the loader REJECTS as P177 targets."""
    return {pid: p for pid, p in load_registry().items() if p.derived}
