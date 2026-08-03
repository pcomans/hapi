"""Resolve stage-1 candidates into verdicts, then gate ``same_entity_as`` shortcut
emission on an approved verdict tip (ADR-018 shortcut-emission rule). This POC runs a
single verdict per candidate (no supersession round yet), so the tip IS that verdict."""

from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
from typing import Callable

from .matcher import Candidate, generate_candidates, uniqueness_clashes
from .reviewer import (
    PROVIDER_PARAMETERS,
    SYSTEM_PROMPT,
    VERDICT_APPROVED,
    VERDICT_ESCALATED,
    ReviewerCallError,
    ReviewerInteraction,
    ReviewerParseError,
    Verdict,
    _build_user_prompt,
    _serialisable,
    request_digest,
    review_deterministic,
    review_with_llm,
    review_with_openrouter,
)

# A name-only candidate (similar names, no shared throne-name/Horus-name to corroborate)
# is escalated deterministically and NEVER sent to the paid reviewer: an LLM "approved"
# here could only rest on world knowledge ("the model knows Usaphais = Den"), which is not
# a committed source (Rule 1). Confirming such a match needs external evidence — a cited
# scholarly identification / documented source — added by a curator, not a model assertion.
_NAME_ONLY_ESCALATION_REASON = (
    "Name-only match: the records share a similar name but NO throne-name or Horus-name "
    "corroboration. Escalated for manual review — confirming this identity requires "
    "external documented evidence (a cited scholarly identification), not a model's "
    "unsourced assertion (Constitutional Rule 1)."
)
from .sources import RulerRecord


@dataclass
class MatchEdge:
    """An approved cross-source identity link (the gated shortcut)."""

    candidate_id: str
    a_id: str
    b_id: str
    a_source: str
    b_source: str
    a_name: str
    b_name: str
    basis: str
    shared_prenomen_keys: list[str]
    reason: str
    reviewer: str


@dataclass
class Escalation:
    """A candidate referred to the human curator queue — no shortcut."""

    candidate_id: str
    a_id: str
    b_id: str
    a_source: str
    b_source: str
    a_name: str
    b_name: str
    basis: str
    reason: str
    homonym_trap: str | None
    reviewer: str


@dataclass
class ResolveResult:
    candidates: list[Candidate]
    verdicts: list[Verdict]
    approved_edges: list[MatchEdge]
    escalations: list[Escalation]
    mode: str


def _stamped(
    interaction: ReviewerInteraction, attempt: int, model: str
) -> ReviewerInteraction:
    """Place one interaction in the retry sequence, and fill in the model that was
    REQUESTED when the reviewer did not report one (the provider's own snapshot may be
    absent from a malformed body). ``model`` is the run's requested model id, passed in
    explicitly by :func:`resolve_matches` — it is not in scope here otherwise."""
    return replace(
        interaction,
        attempt=attempt,
        requested_model=interaction.requested_model or model,
    )


def _failed_call_interaction(
    c: Candidate, a, b, attempt: int, *, model: str, provider: str, err: Exception
) -> ReviewerInteraction:
    """Provenance for an attempt that raised an exception carrying no interaction of its
    own (the reviewer functions attach one to every failure they raise themselves).

    Provider SDKs put the server's error payload on the exception — the Anthropic client
    raises ``APIStatusError`` with a ``body`` rather than handing us a response object — so
    that payload is captured here instead of being discarded. When there genuinely is none
    (connection error, timeout), ``raw_response`` stays ``None``: the absence of a response
    is itself provenance, and the attempt is recorded rather than omitted, because it was
    still a real call that consumed a retry and shaped the outcome (Rule 13)."""
    return ReviewerInteraction(
        attempt=attempt,
        provider=provider,
        requested_model=model,
        model_snapshot=None,
        parameters=dict(PROVIDER_PARAMETERS[provider]),
        system_prompt=SYSTEM_PROMPT,
        user_prompt=_build_user_prompt(c, a, b),
        raw_response=_serialisable(getattr(err, "body", None)),
        call_error=f"{type(err).__name__}: {err}",
    )


def _review_with_retry(
    reviewer_fn, c, a, b, retries: int, *, model: str, provider: str
) -> Verdict:
    """``reviewer_fn(candidate, a, b) -> Verdict`` is the provider-bound live reviewer
    (Anthropic or OpenRouter). Retries on any error; a persistent parse failure escalates
    THIS candidate (with every attempt's full interaction), any other error fails the run
    loud (Rule 2).

    EVERY attempt is retained, in order, on the returned verdict — the malformed ones a
    later successful attempt superseded, AND the ones that raised without a response. Each
    was a real call that influenced the decision (it consumed a retry), so dropping it
    would leave the artifact claiming a clean single-shot interaction that never happened
    (Rule 13)."""
    interactions: list[ReviewerInteraction] = []
    last_err: Exception | None = None
    digest: str | None = None
    for attempt in range(1, retries + 2):
        try:
            verdict = reviewer_fn(c, a, b)
        except ReviewerCallError as err:
            # Unparseable output, or an error status whose body the reviewer captured —
            # either way the complete interaction travels with the exception.
            last_err = err
            digest = err.request_digest
            interactions.append(_stamped(err.interaction, attempt, model))
        except Exception as err:  # noqa: BLE001 — transport/API error, retried then raised
            last_err = err
            interactions.append(
                _failed_call_interaction(
                    c, a, b, attempt, model=model, provider=provider, err=err
                )
            )
        else:
            verdict.interactions = interactions + [
                _stamped(i, attempt, model) for i in verdict.interactions
            ]
            return verdict
    # An API/transport error is a real blocker (credits, network, auth) → fail loud.
    if not isinstance(last_err, ReviewerParseError):
        raise RuntimeError(
            f"Live reviewer failed for candidate {c.id} ({c.a_name} ↔ {c.b_name}) "
            f"after {retries + 1} attempts: {last_err}"
        )
    # Unparseable output after retries: escalate THIS candidate (doubt → curator queue),
    # visibly and counted — never silently, and never aborting the rest of the run. Every
    # offending response drove this escalation, so all are persisted in full (Rule 13).
    import sys

    sys.stderr.write(
        f"[reviewer] WARN: unparseable output for {c.id} after {retries + 1} attempts; "
        f"escalating this candidate. Last: {last_err}\n"
    )
    return Verdict(
        candidate_id=c.id,
        outcome=VERDICT_ESCALATED,
        reason="Reviewer output could not be parsed after retries; escalated for manual review.",
        reviewer="llm",
        request_digest=digest,
        interactions=interactions,
    )


def _verdict_from_json(obj: dict) -> Verdict:
    """Rehydrate a checkpointed verdict. Any schema drift (missing/unknown key) raises."""
    data = dict(obj)
    data["interactions"] = [ReviewerInteraction(**i) for i in data["interactions"]]
    return Verdict(**data)


def _load_cache(cache_path: str) -> dict[str, Verdict]:
    """Load previously-checkpointed raw verdicts, keyed by candidate id.

    Two lines for the same candidate are NOT resolved by file order: if they disagree in
    any field the load raises (Rule 2/6 — a verdict picked by iteration order has no
    provenance). Byte-identical repeats are idempotent and accepted."""
    out: dict[str, Verdict] = {}
    if not cache_path or not os.path.exists(cache_path):
        return out
    seen: dict[str, tuple[int, dict]] = {}
    with open(cache_path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            cid = obj["candidate_id"]
            prev = seen.get(cid)
            if prev is not None and prev[1] != obj:
                raise RuntimeError(
                    f"Verdict cache {cache_path} holds CONFLICTING entries for candidate "
                    f"{cid} (line {prev[0]} vs line {lineno}). Refusing to resolve by file "
                    f"order — delete the cache and re-review (--fresh), or remove the "
                    f"stale line."
                )
            seen[cid] = (lineno, obj)
            out[cid] = _verdict_from_json(obj)
    return out


def resolve_matches(
    records: list[RulerRecord],
    *,
    mode: str,
    client=None,
    provider: str = "anthropic",
    api_key: str | None = None,
    reviewer_fn=None,
    model: str = "claude-opus-4-8",
    retries_per_candidate: int = 2,
    max_workers: int = 10,
    limit: int | None = None,
    cache_path: str | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> ResolveResult:
    """``mode`` is "llm" (live reviewer decides every CORROBORATED candidate; fails loud on
    repeated error — no silent fallback) or "deterministic" (the committed corroborate-or-
    escalate policy; an explicitly-chosen mode, never an auto-substitute).

    ``provider`` selects the live reviewer backend: "anthropic" (needs ``client``) or
    "openrouter" (needs ``api_key``); ``reviewer_fn`` overrides both (used by tests). In
    "llm" mode, name-only candidates are escalated deterministically and NEVER sent to the
    reviewer — only prenomen/Horus-corroborated candidates cost a call. Reviews run
    concurrently (``max_workers`` threads); any candidate still failing after retries fails
    the whole run loudly. ``limit`` caps the candidates for a thin-slice validation.
    """
    candidates = generate_candidates(records)
    if limit is not None:
        candidates = candidates[:limit]
    forced = uniqueness_clashes(candidates)
    by_id = {r.local_id: r for r in records}

    if mode == "llm" and reviewer_fn is None:
        if provider == "openrouter":
            if not api_key:
                raise RuntimeError(
                    "resolve_matches called in 'llm'/openrouter mode without an api_key. "
                    "Refusing to run — the live reviewer must decide the matches."
                )
            reviewer_fn = lambda c, a, b: review_with_openrouter(api_key, c, a, b, model=model)  # noqa: E731
        else:
            if client is None:
                raise RuntimeError(
                    "resolve_matches called in 'llm' mode without an Anthropic client. "
                    "Refusing to run — the live reviewer must decide the matches."
                )
            reviewer_fn = lambda c, a, b: review_with_llm(client, c, a, b, model=model)  # noqa: E731

    total = len(candidates)

    def finalize(c: Candidate, verdict: Verdict) -> Verdict:
        # Deterministic hard guards applied OVER the model verdict (Rule 3: the committed
        # policy is enforced in code, never delegated to the LLM). Both only ever downgrade
        # an APPROVE to an ESCALATE — never the reverse. Crucially, the reviewer is NOT told
        # either guard applies (Rule 14: no answer leak), so it judges the pair blind and
        # the guard is enforced here regardless of what it decided.
        if verdict.outcome != VERDICT_APPROVED:
            return verdict
        if c.id in forced:
            # A record is the corroborated match of two distinct records in the other
            # source — never resolved by an order-dependent incumbent.
            verdict.outcome = VERDICT_ESCALATED
            verdict.reason = f"{verdict.reason} [overridden to escalate: uniqueness clash]"
        elif c.homonym_trap:
            # The shared throne name is on the committed homonym exception list — a reused
            # prenomen borne by DISTINCT kings. This is the hard guard against false merges
            # (ADR-020 decision 3 / Rule 6); an LLM 'approved' here cannot stand.
            verdict.outcome = VERDICT_ESCALATED
            verdict.reason = (
                f"{verdict.reason} [overridden to escalate: shared prenomen "
                f"'{c.homonym_trap}' is on the committed homonym exception list — a reused "
                f"throne name is not sufficient to merge distinct kings (ADR-020 decision 3)]"
            )
        return verdict

    if mode != "llm":
        verdicts = [finalize(c, review_deterministic(c, c.id in forced)) for c in candidates]
        if on_progress:
            on_progress(total, total)
    else:
        # Resumable checkpoint cache: raw (pre-finalize) verdicts are appended to
        # `cache_path` as each completes, so a mid-run failure (e.g. the API running out
        # of credits) never wastes prior work — a re-run reviews only the remainder. Reuse
        # is pinned to the request digest below: resuming is only legitimate while the run
        # is the SAME run.
        cached: dict[str, Verdict] = _load_cache(cache_path) if cache_path else {}
        if provider not in PROVIDER_PARAMETERS:
            raise RuntimeError(f"Unknown reviewer provider {provider!r}")
        parameters = PROVIDER_PARAMETERS[provider]
        verdicts_by_id: dict[str, Verdict] = {}
        for c in candidates:
            if c.id in cached:
                # A cached verdict may ONLY be reused if the request that produced it is
                # byte-for-byte the request we would send now — same records, same prompts,
                # same provider/model/parameters. Otherwise the artifact would claim one
                # reviewer configuration while its edges were decided under another
                # (Rule 6/13); refuse rather than silently mix configurations.
                a, b = by_id.get(c.a_id), by_id.get(c.b_id)
                if a is None or b is None:
                    raise RuntimeError(f"Missing record(s) for candidate {c.id}")
                expected = request_digest(
                    c, a, b, provider=provider, model=model, parameters=parameters
                )
                if cached[c.id].request_digest != expected:
                    raise RuntimeError(
                        f"Cached verdict for candidate {c.id} was produced under a "
                        f"DIFFERENT request (digest {cached[c.id].request_digest} != "
                        f"{expected}): the records, prompt, provider, model or parameters "
                        f"changed since it was written. Re-review with --fresh instead of "
                        f"reusing a verdict that does not describe this configuration."
                    )
                verdicts_by_id[c.id] = cached[c.id]
            elif c.basis == "name_only":
                # Never reaches the paid reviewer — deterministic escalate (see module note).
                verdicts_by_id[c.id] = Verdict(
                    candidate_id=c.id,
                    outcome=VERDICT_ESCALATED,
                    reason=_NAME_ONLY_ESCALATION_REASON,
                    reviewer="deterministic",
                )
        todo = [c for c in candidates if c.id not in verdicts_by_id]
        done = len(candidates) - len(todo)
        if on_progress and done:
            on_progress(done, total)
        lock = threading.Lock()
        cache_fh = open(cache_path, "a", encoding="utf-8") if cache_path else None

        def work(c: Candidate) -> tuple[str, Verdict]:
            a, b = by_id.get(c.a_id), by_id.get(c.b_id)
            if a is None or b is None:
                raise RuntimeError(f"Missing record(s) for candidate {c.id}")
            v = _review_with_retry(
                reviewer_fn, c, a, b, retries_per_candidate, model=model, provider=provider
            )
            return c.id, v

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {pool.submit(work, c): c for c in todo}
                for fut in as_completed(futures):
                    cid, v = fut.result()  # re-raises loudly on failure → whole run fails
                    with lock:
                        verdicts_by_id[cid] = v
                        if cache_fh:
                            cache_fh.write(json.dumps(asdict(v), ensure_ascii=False) + "\n")
                            cache_fh.flush()
                        done += 1
                        if on_progress:
                            on_progress(done, total)
        finally:
            if cache_fh:
                cache_fh.close()
        verdicts = [finalize(c, verdicts_by_id[c.id]) for c in candidates]

    approved_edges: list[MatchEdge] = []
    escalations: list[Escalation] = []
    cand_by_id = {c.id: c for c in candidates}

    for v in verdicts:
        c = cand_by_id[v.candidate_id]
        if v.outcome == VERDICT_APPROVED:
            approved_edges.append(
                MatchEdge(
                    candidate_id=c.id,
                    a_id=c.a_id,
                    b_id=c.b_id,
                    a_source=c.a_source,
                    b_source=c.b_source,
                    a_name=c.a_name,
                    b_name=c.b_name,
                    basis=c.basis,
                    shared_prenomen_keys=c.shared_prenomen_keys,
                    reason=v.reason,
                    reviewer=v.reviewer,
                )
            )
        elif v.outcome == VERDICT_ESCALATED:
            escalations.append(
                Escalation(
                    candidate_id=c.id,
                    a_id=c.a_id,
                    b_id=c.b_id,
                    a_source=c.a_source,
                    b_source=c.b_source,
                    a_name=c.a_name,
                    b_name=c.b_name,
                    basis=c.basis,
                    reason=v.reason,
                    homonym_trap=c.homonym_trap,
                    reviewer=v.reviewer,
                )
            )
        # rejected → nothing emitted

    approved_edges.sort(key=lambda e: e.candidate_id)
    escalations.sort(key=lambda e: e.candidate_id)
    return ResolveResult(
        candidates=candidates,
        verdicts=verdicts,
        approved_edges=approved_edges,
        escalations=escalations,
        mode=mode,
    )
