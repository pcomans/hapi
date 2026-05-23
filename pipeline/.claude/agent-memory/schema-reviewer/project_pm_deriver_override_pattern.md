---
name: PM DERIVER_OVERRIDES pattern for regnal-date hedges
description: When PM's (?) or Probably qualifies a regnal date or secondary clause, DERIVER_OVERRIDES must pin attribution_certainty=attested; this is a recurring finding across chunks
type: project
---

The `_detect_attribution_certainty` regex in `fix_rows.py` is context-free: it fires on ANY `(?)` or `Probably` in `notes_from_pm`, including regnal-date hedges (`Temp. Sethos I(?)`) and usurper-role hedges that don't apply to the primary occupant.

DERIVER_OVERRIDES are needed whenever:
1. PM's `(?)` qualifies a regnal date (`Temp. King X(?)`) — pin to `"attested"` (see TT12, TT17, TT19, TT20, TT43, TT46 pattern)
2. PM's `Probably` qualifies a regnal period (`Probably temp. King`) — pin to `"attested"` (TT49 pattern; TT2 similar for wife identification)
3. PM's `(?)` qualifies a usurper's role or regnal date inside a usurpation clause — pin to `"attested"` (TT22, TT45 pattern)

**NOT needing override:** when `(?)` or `Probably` directly qualifies the primary occupant identification itself (`Probably Amenophis IV...` = KV55, `Probably Princess Neferure...` = SWV-Neferure). Those rows correctly get `"probable"` or `"uncertain"`.

**Structural test:** `test_sources_porter_moss_theban_necropolis.py` does not automatically catch missing DERIVER_OVERRIDES. The schema-reviewer must manually check each chunk-13 row's `notes_from_pm` for hedge tokens and assess whether they're primary vs secondary.

**Exception — anonymous rows with usurper-clause (?):** When the primary occupant is anonymous (no name), there is NO headword attribution to override. In this case `"uncertain"` from the deriver is correct and no DERIVER_OVERRIDE is added. TT70 is the canonical example (PM I.1 p.139, anonymous original occupant, usurper-clause `sandal-makers (?)`). The test docstring at lines 3445–3452 explicitly documents this exception.

**Null-name ⇔ Unknown-role pairing invariant:** When `occupant_name=null`, `occupant_role` MUST be `"Unknown"` (not null). This is enforced by explicit CHUNK*_CORRECTIONS entries for every anonymous row (KV12, QV36/40/73/75, TT58). The `test_occupant_role_controlled_vocab` test skips null roles, so the invariant is NOT mechanically enforced — schema-reviewer must check manually. TT70 (chunk-15) had `occupant_role: null` — P1 merge-blocker, fix via CHUNK15_CORRECTIONS.

**Pattern found in:** chunks 9 (TT2), 10 (TT12, TT17, TT19, TT20), 11 (TT22), 13 (TT41, TT43, TT45, TT46, TT49 — missing overrides flagged as P1 in chunk-13 review 2026-05-10), 14 (TT52, TT54), 15 (TT62, TT65, TT69 — overrides present; TT70 no override needed, anonymous-occupant exception), 16 (TT79 regnal-range tail `Amenophis II (?)` — override present with full printed-source citation; TT73 genuine primary-attribution `(?)` correctly gets `uncertain`, no override needed).
