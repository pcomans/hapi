# Reviewer prompt leak audit — 2026-10-11 (Rule 14)

**Subject:** `pipeline/pipeline/authority/claimgraph/reviewer.py` — `SYSTEM_PROMPT`,
`_record_context`, `_build_user_prompt`, after the change that renders the source's
"epithets added to the throne / Horus / birth name" on their own lines instead of mixed into
the name lines. Audited by the `prompt-auditor` agent against three fully composed requests
(a true match, the Dyn 17/18 Nebmaatre trap, Ramesses IV vs Ramesses II) before any call.

**Verdict: PASS** — no P0/P1/P2.

- No stage-1 verdict or proxy reaches the model: `_build_user_prompt` does not read the
  candidate's basis, shared keys, homonym/era/clash status or ids; the only stage-1 text is
  the fixed sentence "surfaced by a name pre-filter as a possible identity match".
- The system prompt names no member of the committed homonym list.
- The epithet split is not a leak: the flag comes from the source's own transcription
  notes, every record shows all three epithet lines (often `(none)`), and non-empty
  epithet lines occur in both a true match and a trap in the audited set.
- `source:` lines and A/B order (sorted `local_id`, fixed per source pair) carry no
  per-candidate information; no row, local or candidate id is rendered.

Known biases recorded (P3, not leaks): the system prompt's repeated "when in doubt,
ESCALATE" and "reuse is common" are uniform priors that lower the approval rate on every
call; A/B order is fixed per source pair rather than shuffled; the pre-filter sentence is
slightly inaccurate because name-only pairs never reach the model. The request text change
invalidates every earlier cached verdict by digest, so the 2026-10-11 run is not
like-for-like with the 2026-10-10 run.
