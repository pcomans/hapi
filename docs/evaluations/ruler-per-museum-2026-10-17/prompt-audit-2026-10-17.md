# Prompt audit (Rule 14) — per-museum ruler test, 2026-10-17

Audited by the `prompt-auditor` agent on 2026-10-17, before any model call, over the four prompts,
the four schemas, `launcher-instructions/review-system-v4.txt`, `citable-sources.json`,
`scripts/review_protocol.py` (`compose_user_content`, `validate`, `reconciliation_queue`,
`build_consensus`), `scripts/build_queue.py`, `scripts/run_harness_review.py`, `scripts/score.py`,
`scripts/open_page_server.py` (tool description) and a dry-run build of the real queues (194 link
cases including the 20 decoys, 161 miss cases), with the private answer key used only to look for
proxies. The agent reported inline; this file records its findings and what was done.

**Verdict: no P1.** Two P2s, four P3s.

## Findings

1. **Answer, decoy and selection hints: none.**
   - No prompt, schema, system prompt or tool description names decoys, calibration or controls,
     and none gives a worked example.
   - The case JSON keys are exactly `allowed_outcomes`, `case_id`, `entity_type`, `evidence`,
     `proposed_target` and `question`. `evidence_sha256` is stripped, and the private keys are
     refused (`forbidden_keys`).
2. **Decoy proxies: none visible within a call.**
   - Decoy case IDs are spread over 1–194 with no clustering, and are unordered relative to their
     real twins.
   - The museum mix (Met 12, Walters 6, Cleveland 2) matches random draws from the eligible set.
   - Target `representation` (17 clusters, 3 singleton source nodes, 0 royal women) is not
     significant (p ≈ 0.09). Every case has the same metadata keys, and decoy targets are genuine
     catalog entries.
   - Record counts, field paths and record texts equal each twin's by construction. Calls are
     separate processes with no memory.
   - Population-level only: decoy labels are always "Name N", and "Ramesses XI" is the target of
     4 of the 20.
   - The only in-call feature that separates a decoy is the identity itself, which is the
     question.
3. **Miss prompt steer: none.** The categories are generic and quote no case strings. The
   outcome order and question are fixed.
4. **Contradictions:** the miss `ruler` rules agree across the prompt, schema and validator.

| ID | Finding | Done |
|---|---|---|
| P2-a | A miss's named ruler is not reconciled: two agreeing `one_ruler` reviews may name different rulers. | Option (iii): disclosed in `decision-rule.md` (rule 4) and the README. The fix list gives both names as written, never one picked. Misses decide nothing. |
| P2-b | The decoys are the easiest wrong ruler (same name, other numeral), and the link prompt's definition names that construction. | Kept the definition. `decision-rule.md` ("What the decoys do and do not show") and the README say that calibration measures this class only, not the real-link error rate. |
| P3-a | The link prompts mention "roles", which no case has. | Replaced with "the museum". |
| P3-b | The validator also fails a call whose search results merely list Wikidata or GitHub, and an uncited insufficient_evidence without a citable page tried. | Unchanged, as in the earlier registrations. These are retries triggered by search noise, not by answers. |
| P3-c | A slash form ("Amenhotep IV/Akhenaten") is one ruler under two names, and the miss prompt did not say which side it falls on. | Added to both miss prompts: "Several names or spellings of the same ruler name one ruler." |
| P3-d | The decoy target concentration (Ramesses XI ×4, no royal women) is population-level. | Disclosed in the README. |

The auditor noted, as the question rather than a leak, that the real population has links whose
target label is numbered differently from the text (a Met "Ahmose I" shown as "Ahmose (II)"; an
Amasis shown as "Ahmose III"). The review will judge them.

## Delta audit

The auditor delta-checked the two edits made after the audit (P3-a, P3-c): both are clean, with
no P1 or P2.
- P3-a's list matches the case keys.
- P3-c's sentence is generic. It resolves the slash-alias case toward `one_ruler`, as the design
  intends, and balances the five "not one ruler" categories.
- One P3: "Several names" sits next to "several rulers of that name", which a reviewer could
  confuse. Disclosed; no edit.

## Audited bytes

These are the files as audited, delta included; a test binds them.

| File | SHA-256 |
|---|---|
| `prompts/link-reconciler-v1.txt` | `1d3dfd777c4745347b9645345a0992d7b67a194a6fafcdfc7c1aee8bc79b585f` |
| `prompts/link-reviewer-v1.txt` | `924ea5f7bcd18803acc18b325415593898450a25542b0658b6dde33c51920826` |
| `prompts/miss-reconciler-v1.txt` | `362aea36cd87e0a86f23d1f0801c5aa611e343a8ba9ff032393e3bc0b3b2bad8` |
| `prompts/miss-reviewer-v1.txt` | `f44633b9f5856768bbbbccc7972dc2abdc8ee5348702b72a3fe95d85f1f6cc6f` |
| `raw-response-contracts/link-reconciler-case-v1.schema.json` | `c90d6a164308f2d668e17cbd893241f5982bd68288ebbcc6a54e9f1b37fc1ed0` |
| `raw-response-contracts/link-reviewer-case-v1.schema.json` | `d682ba041eb7c0daab725dd57d798b6d5e43ddabfe07c5faab8d239d69ef0e9b` |
| `raw-response-contracts/miss-reconciler-case-v1.schema.json` | `4a35bebef57c1a889f5a515d435578176b2c9b2f44ba5446129c3398b6bd989a` |
| `raw-response-contracts/miss-reviewer-case-v1.schema.json` | `85dbdf119646c90040c2358bd0c5bf829d3869332c1033b134b08dbd14cc79ad` |
| `launcher-instructions/review-system-v4.txt` | `290ab72e433d8cbbd167d4f906e874fee1d6994c38201bfe10d01e7cd3116451` |
| `citable-sources.json` | `4bd37e0670ecbeccd441b22e311a69e09cfe2925617a8fc1e00272396a4721d5` |
