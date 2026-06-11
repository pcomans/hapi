"""Guard against answer leakage in the matcher prompt (ADR-020 §6 / prompt hygiene).

The source ids encode the cross-source dynasty.sequence alignment (both sides
carry e.g. "18.09"), so showing ids to the model leaks the answer. _opaque_view
must strip every ruler_id and present candidates under opaque, shuffled labels.
"""

from __future__ import annotations

import json

from pipeline.authority.graph.matcher.constraint_narrowed import _opaque_view


def _has_id(blob) -> bool:
    return "ruler_id" in json.dumps(blob) or "::" in json.dumps(blob)


def test_opaque_view_strips_all_ids():
    left = {"ruler_id": "leprohon::leprohon-18.09", "display_name": "Amenhotep III", "dynasty": 18}
    rights = [
        {"ruler_id": "beckerath::18.09", "display_name": "Amenophis III.", "dynasty": 18},
        {"ruler_id": "beckerath::18.07", "display_name": "Tuthmosis III.", "dynasty": 18},
    ]
    target_view, cand_view, label_to_id = _opaque_view(left, rights)
    # No ruler_id key and no id-shaped value anywhere the model can see.
    assert not _has_id(target_view)
    assert not _has_id(cand_view)
    # Candidates carry opaque labels C1..Cn.
    labels = {c["label"] for c in cand_view}
    assert labels == {"C1", "C2"}
    # Labels map back to the real ids (outside the prompt).
    assert set(label_to_id.values()) == {"beckerath::18.09", "beckerath::18.07"}


def test_opaque_view_is_deterministic():
    left = {"ruler_id": "x", "display_name": "A"}
    rights = [{"ruler_id": f"r{i}", "display_name": str(i)} for i in range(6)]
    a = _opaque_view(left, rights)[1]
    b = _opaque_view(left, rights)[1]
    assert a == b  # same target → same shuffle (reproducible)


def test_opaque_view_preserves_evidence_fields():
    left = {"ruler_id": "L", "display_name": "Amenhotep III", "throne_name": ["neb maat ra"], "reign_bce": [-1388, -1350]}
    rights = [{"ruler_id": "R", "display_name": "Amenophis III.", "reign_bce": [-1390, -1352]}]
    target_view, cand_view, _ = _opaque_view(left, rights)
    # The disambiguating evidence is kept — only the id is removed.
    assert target_view["throne_name"] == ["neb maat ra"]
    assert target_view["reign_bce"] == [-1388, -1350]
    assert cand_view[0]["reign_bce"] == [-1390, -1352]
    assert cand_view[0]["display_name"] == "Amenophis III."
