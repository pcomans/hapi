"""Source-attributed claim-graph POC generator (ADR-018 / ADR-020).

Reads the committed authority ``reconciled.jsonl`` sources, builds a per-source E13 claim
graph, runs a best-effort cross-source ruler matcher whose verdicts are decided by a live
Anthropic reviewer (precision-first, corroborate-or-escalate), and emits the committed
JSON artifact the ``web-claimgraph`` Next.js app serves.
"""
