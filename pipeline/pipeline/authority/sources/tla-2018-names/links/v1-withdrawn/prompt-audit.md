# Prompt audit (Rule 14), 2026-10-15

`prompts/system-v1.txt`, `reviewer-v1.txt` and `reconciler-v1.txt` were audited by the
prompt-auditor agent before any model call, in three rounds:

1. **No answer leak.** Two P1 contradictions:
   - ꜣ/ꜥ both "part of the name" and "may be left out";
   - weak w/j "freely interchangeable" but a "root" w/j a difference.

   Also found: a presupposing first line, D&H kin/roles/dynasty that could make person
   identity decide name identity, an undefined `insufficient_evidence`, and an ambiguous bare h.

   All were fixed. The comparison is now an ordered sign-by-sign procedure, and the D&H record
   carries the name only.
2. **No leak.** P2s:
   - which D&H spelling is compared;
   - an element-final t;
   - a leftover y/w.

   P3s: identity mappings, doubled letters, capitals, ꜣ/ꜥ position. All were fixed.
3. **No leak and no contradiction:** "fine to run". The optional P3 wording for ꜣ/ꜥ at the
   start or end of a name was adopted verbatim.

Final SHA-256s (checked by `pipeline/tests/test_tla_links.py`):

- `system-v1.txt`: `fc8c8e1723e158d6acec8d352205cc6a0dc5a9dbc855d045436e860f68ac2ed1`
- `reviewer-v1.txt`: `bd56f5df13c7fb701f006850eab14f562ea22b821c60ab4621d3fb95d9dc8ec4`
- `reconciler-v1.txt`: `bad76fb2c63cd61ecfbe6f61dde25d25b9ffc48edcafea18c5bb18ddeafa443a`
