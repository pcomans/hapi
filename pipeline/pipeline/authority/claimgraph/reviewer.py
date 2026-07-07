"""Stage-2 review. Two interchangeable paths, both precision-first (ADR-020 §6):

* :func:`review_deterministic` — no external dependency; encodes the corroborate-or-
  escalate policy as pure logic. Used ONLY when the operator explicitly selects the
  ``deterministic`` mode, and as the reference the LLM is measured against. It is never
  an automatic fallback for a failed/absent LLM.
* :func:`review_with_llm` — the live Anthropic reviewer chosen for this POC. It sees the
  FULL structured record of both sides (never just display names, ADR-020 §6) and its
  complete interaction is captured for replay (Constitutional Rule 13).

A verdict never silently drops a candidate: everything resolves to approved / rejected /
escalated, and doubt routes to escalated.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .matcher import Candidate
from .sources import RulerRecord

VERDICT_APPROVED = "hapi:verdict_approved"
VERDICT_REJECTED = "hapi:verdict_rejected"
VERDICT_RETRACTED = "hapi:verdict_retracted"
VERDICT_ESCALATED = "hapi:verdict_escalated"


class ReviewerParseError(ValueError):
    """The reviewer returned a response that could not be parsed into a verdict. Carries
    the full interaction (prompt + raw response + model snapshot) so that when this drives
    an escalation, the response that caused it is still persisted (Constitutional Rule 13):
    a decision must be replayable from a stored request/response, even a malformed one."""

    def __init__(
        self,
        message: str,
        *,
        prompt: str,
        raw_response: Any,
        model_id: str | None,
        model_snapshot: str | None,
    ) -> None:
        super().__init__(message)
        self.prompt = prompt
        self.raw_response = raw_response
        self.model_id = model_id
        self.model_snapshot = model_snapshot


@dataclass
class Verdict:
    candidate_id: str
    outcome: str
    reason: str
    reviewer: str  # "deterministic" | "llm"
    # Reasoning capture (Rule 13) — populated on the llm path.
    model_id: str | None = None
    model_snapshot: str | None = None
    prompt: str | None = None
    raw_response: Any = None


# --- deterministic path ----------------------------------------------------


def review_deterministic(candidate: Candidate, forced_escalate: bool) -> Verdict:
    base = dict(candidate_id=candidate.id, reviewer="deterministic")
    if forced_escalate:
        return Verdict(
            **base,
            outcome=VERDICT_ESCALATED,
            reason=(
                "Uniqueness clash: a record is the corroborated match of two distinct "
                "records from the other source; escalated rather than resolved by an "
                "order-dependent incumbent."
            ),
        )
    if candidate.basis == "name_only":
        return Verdict(
            **base,
            outcome=VERDICT_ESCALATED,
            reason=(
                "Name agreement alone is not sufficient to accept (ADR-020 §6); no "
                "prenomen/throne-name corroboration. Escalated."
            ),
        )
    if candidate.homonym_trap:
        return Verdict(
            **base,
            outcome=VERDICT_ESCALATED,
            reason=(
                f"Shared prenomen '{candidate.homonym_trap}' is on the committed homonym "
                "exception list (borne by distinct kings); escalated."
            ),
        )
    if candidate.reign_far_apart:
        return Verdict(
            **base,
            outcome=VERDICT_ESCALATED,
            reason=(
                "Prenomen corroborated but reign spans are far apart even under cross-"
                "framework tolerance; escalated for adjudication."
            ),
        )
    via = (
        f"shared throne name(s) {', '.join(candidate.shared_prenomen_keys)}"
        if candidate.basis == "prenomen"
        else "shared Horus name (early-dynastic corroborator)"
    )
    dyn = " with matching dynasty" if candidate.dynasty_match else ""
    return Verdict(
        **base,
        outcome=VERDICT_APPROVED,
        reason=f"Structured corroboration via {via}{dyn}.",
    )


# --- live LLM path ---------------------------------------------------------


def _names(forms) -> str:
    vals = [f.surface or f.translit or "" for f in forms]
    vals = [v for v in vals if v]
    return "; ".join(vals) if vals else "(none)"


def _record_context(rec: RulerRecord) -> str:
    return "\n".join(
        [
            f"source: {rec.source_id}",
            f"display_name: {rec.display_name}",
            f"alt_names: {'; '.join(rec.alt_names) or '(none)'}",
            f"dynasty: {rec.dynasty if rec.dynasty is not None else '(unknown)'} "
            f"({rec.dynasty_label or '?'})",
            f"throne_names/prenomina: {_names(rec.prenomina)}",
            f"horus_names: {_names(rec.horus_names)}",
            f"nomina: {_names(rec.nomina)}",
            f"reign_bce: {rec.reign_start_bce if rec.reign_start_bce is not None else '?'}"
            f"..{rec.reign_end_bce if rec.reign_end_bce is not None else '?'}",
        ]
    )


SYSTEM_PROMPT = (
    "You are an Egyptological identity reviewer for a source-attributed authority graph.\n"
    "You judge whether two ruler records from DIFFERENT scholarly sources denote the SAME "
    "historical king.\n"
    "Policy (non-negotiable, precision-first):\n"
    "- A false merge (conflating two distinct kings) is far worse than a missed merge. "
    "When in doubt, ESCALATE.\n"
    "- Name (display-name) agreement ALONE is never sufficient to APPROVE. Require throne-"
    "name (prenomen) corroboration, or for the earliest dynasties a Horus-name match.\n"
    # Rule 14: state the phenomenon generically. Do NOT name the specific reused throne
    # names here — those are the committed homonym answer-key (matcher._HOMONYM_SPELLINGS),
    # and naming them would hand the model the escalate verdict for exactly the cases the
    # eval exists to test. The model must recognise reuse from the record content itself.
    "- Prenomen (throne-name) reuse across distinct, unrelated kings is common in Egyptian "
    "history, not a rare edge case — a shared throne name alone is not proof of identity. "
    "Weigh the full record context (dynasty, reign window, other titulary) rather than "
    "treating a shared prenomen as decisive; when in doubt, ESCALATE.\n"
    "- Regnal numerals and dynasty labels are convention-relative and weak; never let them "
    "alone carry a merge.\n"
    'Respond with ONLY a single JSON object and nothing else, outcome FIRST: '
    '{"outcome":"approved"|"rejected"|"escalated","reason":"<one concise sentence, under 40 words>"}.'
)


def _build_user_prompt(candidate: Candidate, a: RulerRecord, b: RulerRecord) -> str:
    # Rule 14 (no answer leakage): the reviewer sees ONLY the two full records and must
    # reach its own judgement. We do NOT tell it the deterministic stage-1 basis, the
    # shared-key set, or that a prenomen is on the homonym list — every one of those is a
    # proxy for the stage-1 verdict (name_only/homonym ⇒ escalate; prenomen ⇒ likely
    # approve) and would bias the model toward the pre-filter's own conclusion. The shared
    # throne name is present in both records below; the model must notice and weigh it
    # (including recognising a reused prenomen) unaided.
    return "\n".join(
        [
            "Two ruler records from DIFFERENT scholarly sources, surfaced by a name "
            "pre-filter as a possible identity match. Judge them on their merits.",
            "",
            f"RECORD A:\n{_record_context(a)}",
            "",
            f"RECORD B:\n{_record_context(b)}",
            "",
            "Do these two records denote the same historical king? Apply the policy.",
        ]
    )


_MAPPING = {
    "approved": VERDICT_APPROVED,
    "rejected": VERDICT_REJECTED,
    "escalated": VERDICT_ESCALATED,
}


def _parse_verdict_json(text: str) -> tuple[str, str]:
    # strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            outcome = _MAPPING.get(str(obj.get("outcome", "")).lower())
            if outcome:
                return outcome, obj.get("reason", "(no reason given)")
        except json.JSONDecodeError:
            pass  # fall through to lenient salvage (e.g. truncated reason)
    # Lenient salvage: extract the outcome (and best-effort reason) even from a truncated
    # or slightly malformed object, so a cut-off long reason doesn't waste the call.
    om = re.search(r'"outcome"\s*:\s*"(approved|rejected|escalated)"', cleaned, re.IGNORECASE)
    if om:
        outcome = _MAPPING[om.group(1).lower()]
        rm = re.search(r'"reason"\s*:\s*"([^"]*)', cleaned)
        reason = (rm.group(1).strip() if rm else "(reason truncated)") or "(no reason given)"
        return outcome, reason
    raise ValueError(f"Reviewer response was not parseable JSON: {text[:200]!r}")


def review_with_llm(
    client,
    candidate: Candidate,
    a: RulerRecord,
    b: RulerRecord,
    model: str = "claude-opus-4-8",
    max_tokens: int = 600,
) -> Verdict:
    """Review one candidate with the live Anthropic API. Raises on any error (no silent
    fallback — Constitutional Rule 2); the caller decides retry/stop policy.

    A ``ValueError`` signals an unparseable model response specifically (distinct from an
    API/transport error), so the caller can escalate that one candidate instead of
    aborting the whole run."""
    prompt = _build_user_prompt(candidate, a, b)
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(
        block.text for block in resp.content if getattr(block, "type", None) == "text"
    ).strip()
    try:
        outcome, reason = _parse_verdict_json(text)
    except ValueError as err:
        # Attach the full interaction so a parse-driven escalation stays replayable (R13).
        raise ReviewerParseError(
            str(err),
            prompt=prompt,
            raw_response=resp.model_dump(mode="json"),
            model_id=model,
            model_snapshot=resp.model,
        ) from err
    return Verdict(
        candidate_id=candidate.id,
        outcome=outcome,
        reason=reason,
        reviewer="llm",
        model_id=model,
        model_snapshot=resp.model,
        prompt=prompt,
        raw_response=resp.model_dump(mode="json"),
    )


def review_with_openrouter(
    api_key: str,
    candidate: Candidate,
    a: RulerRecord,
    b: RulerRecord,
    model: str = "z-ai/glm-5.2",
    max_tokens: int = 3000,
) -> Verdict:
    """Same contract as :func:`review_with_llm`, against an OpenRouter chat model (e.g.
    GLM 5.2). The IDENTICAL de-leaked system+user prompt is used, so a run is directly
    comparable to the Anthropic path. Fails loud on transport/HTTP error (no silent
    fallback, Rule 2); raises :class:`ReviewerParseError` (with the full body, Rule 13) on
    an unparseable or empty response so the caller escalates that one candidate.

    ``max_tokens`` is generous because reasoning models (GLM 5.2) spend completion tokens
    on reasoning before the JSON answer; too small a budget truncates ``content`` to null.
    The full body — including the model's ``reasoning``/``reasoning_details`` — is captured
    as the replayable provenance record."""
    import httpx

    prompt = _build_user_prompt(candidate, a, b)
    resp = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "max_tokens": max_tokens,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=180,
    )
    resp.raise_for_status()  # transport/HTTP error → fail loud, caller retries then raises
    body = resp.json()
    choice = body["choices"][0]
    text = (choice["message"].get("content") or "").strip()
    snapshot = body.get("model")
    if not text:
        raise ReviewerParseError(
            f"OpenRouter returned empty content (finish_reason={choice.get('finish_reason')})",
            prompt=prompt, raw_response=body, model_id=model, model_snapshot=snapshot,
        )
    try:
        outcome, reason = _parse_verdict_json(text)
    except ValueError as err:
        raise ReviewerParseError(
            str(err), prompt=prompt, raw_response=body, model_id=model, model_snapshot=snapshot,
        ) from err
    return Verdict(
        candidate_id=candidate.id,
        outcome=outcome,
        reason=reason,
        reviewer="llm",
        model_id=model,
        model_snapshot=snapshot,
        prompt=prompt,
        raw_response=body,
    )
