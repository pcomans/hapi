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

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .matcher import Candidate
from .sources import RulerRecord

VERDICT_APPROVED = "hapi:verdict_approved"
VERDICT_REJECTED = "hapi:verdict_rejected"
VERDICT_RETRACTED = "hapi:verdict_retracted"
VERDICT_ESCALATED = "hapi:verdict_escalated"

PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_OPENROUTER = "openrouter"

# The request parameters are committed constants, not caller-tunable knobs: the persisted
# provenance record (and the cache digest built from it) must describe the request that was
# actually sent, and a per-call override would let those two drift apart (Rule 4/13).
# OpenRouter's budget is generous because reasoning models (GLM 5.2) spend completion
# tokens on reasoning before emitting the JSON answer.
ANTHROPIC_PARAMETERS: dict[str, Any] = {"max_tokens": 600}
OPENROUTER_PARAMETERS: dict[str, Any] = {"max_tokens": 3000, "temperature": 0}
PROVIDER_PARAMETERS: dict[str, dict[str, Any]] = {
    PROVIDER_ANTHROPIC: ANTHROPIC_PARAMETERS,
    PROVIDER_OPENROUTER: OPENROUTER_PARAMETERS,
}


@dataclass
class ReviewerInteraction:
    """ONE complete request/response round-trip with the reviewer model.

    Constitutional Rule 13: a stored interaction must be enough to *reconstruct and replay
    the request* — so it holds the provider, the requested model id AND the dated snapshot
    the provider actually served, every request parameter, the full system prompt, the full
    user prompt, and the complete raw response body. Every attempt made for a candidate is
    persisted, not just the one that happened to parse: a malformed attempt influenced the
    decision (it consumed a retry, and after the last retry it *is* the decision).
    """

    attempt: int  # 1-based position in the retry sequence for this candidate
    provider: str
    requested_model: str | None
    model_snapshot: str | None
    parameters: dict[str, Any]
    system_prompt: str
    user_prompt: str
    # The provider's response body, verbatim — INCLUDING an HTTP error body (rate-limit,
    # context-length, auth details). ``None`` ONLY when no bytes were ever received (see
    # ``call_error``); that absence is itself provenance and is recorded, never omitted.
    raw_response: Any
    parse_error: str | None = None  # set when THIS attempt's response could not be parsed
    # Set when THIS attempt ended in a provider/transport error instead of a usable body.
    # ``raw_response`` still holds the provider's error body whenever one was returned.
    call_error: str | None = None


def _serialisable(value: Any) -> Any:
    """Keep a provider payload only in a JSON-writable form (the interaction is persisted
    as JSON). Anything exotic is preserved as its ``repr`` rather than dropped — losing the
    payload is what this whole class of bug is about."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _serialisable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialisable(v) for v in value]
    return repr(value)


class ReviewerCallError(Exception):
    """Base for reviewer failures that carry the complete :class:`ReviewerInteraction`, so
    the request and whatever the provider returned are still persisted (Constitutional
    Rule 13): a decision — or a failed attempt that shaped one — must be replayable."""

    def __init__(
        self,
        message: str,
        *,
        interaction: ReviewerInteraction,
        request_digest: str,
    ) -> None:
        super().__init__(message)
        self.interaction = interaction
        self.request_digest = request_digest


class ReviewerParseError(ReviewerCallError, ValueError):
    """The reviewer returned a response that could not be parsed into a verdict. After the
    retries are spent this escalates THAT candidate, so the malformed response that drove
    the escalation travels with it."""


class ReviewerHttpError(ReviewerCallError, RuntimeError):
    """The provider answered with an error status. This is a real blocker (rate limit,
    credits, auth, context length) so it still fails the run loud after retries — but the
    error BODY the provider sent is the most diagnostic payload in the exchange and is
    captured, never thrown away by a status check that ran before the body was read."""


@dataclass
class Verdict:
    candidate_id: str
    outcome: str
    reason: str
    reviewer: str  # "deterministic" | "llm"
    # Reasoning capture (Rule 13) — populated on the llm path. ``interactions`` holds EVERY
    # attempt in order; the last one produced ``outcome``. ``request_digest`` pins the exact
    # request (records + prompts + provider + model + parameters) the verdict was reached
    # under, so a cached verdict can never be replayed under a different configuration.
    request_digest: str | None = None
    interactions: list[ReviewerInteraction] = field(default_factory=list)


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
    """STRICT parse of the reviewer response: the whole response must be exactly one JSON
    object with exactly the keys ``outcome`` (one of the three literals the system prompt
    mandates) and ``reason`` (a non-empty string). Anything else — truncated JSON, a code
    fence, prose around the object, an extra key, a wrong type — raises.

    There is deliberately NO salvage path. Regex-extracting an ``outcome`` out of a
    malformed or truncated body turns a broken response into an authoritative verdict: a
    cut-off ``{"outcome":"approved"`` would mint an identity edge whose stated reason was
    never actually produced by the model. Malformed output must route through the caller's
    explicit :class:`ReviewerParseError` path (retry, then escalate that one candidate with
    every attempt persisted) — it must never approve.
    """
    stripped = text.strip()
    if not stripped:
        raise ValueError("Reviewer response was empty.")
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError as err:
        raise ValueError(
            f"Reviewer response is not a single valid JSON object ({err}): {text[:200]!r}"
        ) from err
    if not isinstance(obj, dict):
        raise ValueError(
            f"Reviewer response is JSON but not an object (got {type(obj).__name__}): "
            f"{text[:200]!r}"
        )
    keys = set(obj)
    if keys != {"outcome", "reason"}:
        raise ValueError(
            f"Reviewer response object must have exactly the keys "
            f"{{'outcome', 'reason'}}, got {sorted(keys)}: {text[:200]!r}"
        )
    outcome_raw = obj["outcome"]
    if not isinstance(outcome_raw, str) or outcome_raw not in _MAPPING:
        raise ValueError(
            f"Reviewer response 'outcome' must be one of {sorted(_MAPPING)}, got "
            f"{outcome_raw!r}: {text[:200]!r}"
        )
    reason = obj["reason"]
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError(
            f"Reviewer response 'reason' must be a non-empty string, got {reason!r}: "
            f"{text[:200]!r}"
        )
    return _MAPPING[outcome_raw], reason.strip()


def request_digest(
    candidate: Candidate,
    a: RulerRecord,
    b: RulerRecord,
    *,
    provider: str,
    model: str,
    parameters: dict[str, Any],
) -> str:
    """Stable digest of the COMPLETE reviewer request: both source records verbatim, the
    system + user prompt, the provider, the requested model and every request parameter.

    A verdict is only reusable (from the resumable cache) if this digest still matches:
    otherwise the artifact would claim one reviewer configuration while its edges were
    decided under another — provenance that does not describe the decision (Rule 6/13)."""
    payload = {
        "candidate_id": candidate.id,
        "provider": provider,
        "model": model,
        "parameters": parameters,
        "system_prompt": SYSTEM_PROMPT,
        "user_prompt": _build_user_prompt(candidate, a, b),
        "record_a": asdict(a),
        "record_b": asdict(b),
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def review_with_llm(
    client,
    candidate: Candidate,
    a: RulerRecord,
    b: RulerRecord,
    model: str = "claude-opus-4-8",
) -> Verdict:
    """Review one candidate with the live Anthropic API. Raises on any error (no silent
    fallback — Constitutional Rule 2); the caller decides retry/stop policy.

    A :class:`ReviewerParseError` signals an unparseable model response specifically
    (distinct from an API/transport error), so the caller can escalate that one candidate
    instead of aborting the whole run. Either way the complete interaction — the request
    parameters, both prompts, the raw body — is attached (Rule 13)."""
    user_prompt = _build_user_prompt(candidate, a, b)
    parameters = dict(ANTHROPIC_PARAMETERS)
    resp = client.messages.create(
        model=model,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        **parameters,
    )
    interaction = ReviewerInteraction(
        attempt=1,
        provider=PROVIDER_ANTHROPIC,
        requested_model=model,
        model_snapshot=resp.model,
        parameters=parameters,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        raw_response=resp.model_dump(mode="json"),
    )
    digest = request_digest(
        candidate, a, b, provider=PROVIDER_ANTHROPIC, model=model, parameters=parameters
    )
    # A response DID arrive, so every failure from here on must escalate through the
    # parse-error path carrying that response — including a body whose *structure* is
    # unexpected. This is not a swallowed exception: it is re-raised as the documented
    # loud error, with the provenance the escalation depends on attached (Rule 2/13).
    try:
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        ).strip()
    except (AttributeError, TypeError) as err:
        interaction.parse_error = (
            f"Anthropic response had an unexpected content structure: "
            f"{type(err).__name__}: {err}"
        )
        raise ReviewerParseError(
            interaction.parse_error, interaction=interaction, request_digest=digest
        ) from err
    try:
        outcome, reason = _parse_verdict_json(text)
    except ValueError as err:
        # Attach the full interaction so a parse-driven escalation stays replayable (R13).
        interaction.parse_error = str(err)
        raise ReviewerParseError(
            str(err), interaction=interaction, request_digest=digest
        ) from err
    return Verdict(
        candidate_id=candidate.id,
        outcome=outcome,
        reason=reason,
        reviewer="llm",
        request_digest=digest,
        interactions=[interaction],
    )


def review_with_openrouter(
    api_key: str,
    candidate: Candidate,
    a: RulerRecord,
    b: RulerRecord,
    model: str = "z-ai/glm-5.2",
) -> Verdict:
    """Same contract as :func:`review_with_llm`, against an OpenRouter chat model (e.g.
    GLM 5.2). The IDENTICAL de-leaked system+user prompt is used, so a run is directly
    comparable to the Anthropic path. Fails loud on transport/HTTP error (no silent
    fallback, Rule 2) — as :class:`ReviewerHttpError`, carrying the provider's error body;
    raises :class:`ReviewerParseError` (with the full interaction, Rule 13) on an
    unparseable or empty response so the caller escalates that candidate.

    The full body — including the model's ``reasoning``/``reasoning_details``, or the error
    payload on a 4xx/5xx — is captured as the replayable provenance record."""
    import httpx

    user_prompt = _build_user_prompt(candidate, a, b)
    parameters = dict(OPENROUTER_PARAMETERS)
    resp = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            **parameters,
        },
        timeout=180,
    )
    digest = request_digest(
        candidate, a, b, provider=PROVIDER_OPENROUTER, model=model, parameters=parameters
    )

    def _interaction(raw: Any, snapshot: str | None) -> ReviewerInteraction:
        return ReviewerInteraction(
            attempt=1,
            provider=PROVIDER_OPENROUTER,
            requested_model=model,
            model_snapshot=snapshot,
            parameters=parameters,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            raw_response=_serialisable(raw),
        )

    # A response HAS arrived, so the body is captured BEFORE anything can raise on it —
    # including the status check. A 429/500 carries the provider's most diagnostic payload
    # (rate-limit window, context-length overflow, auth failure); checking the status first
    # would throw that away and leave the attempt claiming no body was ever received.
    body: Any
    try:
        body = resp.json()
    except ValueError as err:
        json_error = str(err)
        body = None
        raw_body: Any = resp.text
    else:
        json_error = None
        raw_body = body

    if resp.status_code >= 400:
        interaction = _interaction(raw_body, body.get("model") if isinstance(body, dict) else None)
        interaction.call_error = (
            f"OpenRouter returned HTTP {resp.status_code}; error body captured above."
        )
        raise ReviewerHttpError(
            f"OpenRouter returned HTTP {resp.status_code} for candidate {candidate.id}: "
            f"{str(raw_body)[:400]}",
            interaction=interaction,
            request_digest=digest,
        )

    # From here every failure escalates through the parse-error path carrying that response
    # verbatim, so the call stays replayable (Rule 13). A body that is not JSON, or is JSON
    # of an unexpected shape, is exactly such a failure — it must not surface as a bare
    # exception with the response dropped on the floor.
    if json_error is not None:
        interaction = _interaction(raw_body, None)
        interaction.parse_error = f"OpenRouter response body was not JSON: {json_error}"
        raise ReviewerParseError(
            interaction.parse_error, interaction=interaction, request_digest=digest
        )
    interaction = _interaction(body, body.get("model") if isinstance(body, dict) else None)
    try:
        choice = body["choices"][0]
        text = (choice["message"].get("content") or "").strip()
    except (KeyError, IndexError, TypeError, AttributeError) as err:
        interaction.parse_error = (
            f"OpenRouter response had an unexpected structure: {type(err).__name__}: {err}"
        )
        raise ReviewerParseError(
            interaction.parse_error, interaction=interaction, request_digest=digest
        ) from err
    if not text:
        interaction.parse_error = (
            f"OpenRouter returned empty content (finish_reason={choice.get('finish_reason')})"
        )
        raise ReviewerParseError(
            interaction.parse_error, interaction=interaction, request_digest=digest
        )
    try:
        outcome, reason = _parse_verdict_json(text)
    except ValueError as err:
        interaction.parse_error = str(err)
        raise ReviewerParseError(
            str(err), interaction=interaction, request_digest=digest
        ) from err
    return Verdict(
        candidate_id=candidate.id,
        outcome=outcome,
        reason=reason,
        reviewer="llm",
        request_digest=digest,
        interactions=[interaction],
    )
