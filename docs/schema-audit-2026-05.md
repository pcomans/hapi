# Schema audit — authority sources (2026-05)

A sanity-check pass over the schema of every `reconciled.jsonl` in `pipeline/pipeline/authority/sources/`. Triggered by PR #169 (Porter-Moss `occupant_alt_names` audit-fix) — the failures we found there are likely not unique to PM, and the cost of reproducing them across 10 other sources is real.

This document is the **rubric** for the audit. Each source gets one subagent whose job is to read the source's `reconciled.jsonl` + supporting docs/code and produce a findings file (`/tmp/claude/schema-audit-<source>.md`) per the format below.

---

## Why schema discipline matters

The pipeline's job is to make *museum records* joinable to *authority records*. A search for "objects from KV9" has to land on the rows that catalog Ramesses VI's tomb. The join key is the data the schema encodes — a museum record's `provenance: "Tomb of Memnon"` joins to an authority row only if the authority schema has a place for `"Tomb of Memnon"` that's queryable.

When the schema conflates two distinct concepts into one field, the join fails silently:

- A field like `occupant_alt_names` that carries both `"Akhenaten"` (Amenhotep IV's birth-name = same person) AND `"Belzoni's tomb"` (a tomb-name = different concept) cannot answer "is this provenance string a person-name match or a tomb-name match?". The Phase-A enrichment guesses, and the wrong guess silently merges unrelated records.
- A field like `occupant_name` that carries both `"Ramesses VI"` (one person) AND `"Yuia and Thuiu"` (two people in a string) cannot be joined against `pharaoh.se` or any person authority — `"Yuia and Thuiu"` matches no record.
- A `notes_from_pm` field carrying load-bearing facts ("Foreman in the Place of Truth") that should be in `occupant_role` cannot be filtered, faceted, or matched.

These failures are *invisible*. The data passes existing tests, the row roundtrips through the pipeline, the JSONL looks reasonable. The bug surfaces years later when a museum-record join produces zero matches or — worse — wrong matches that look plausible enough to ship.

CLAUDE.md rule 6 (Data is sacred) and rule 4 (Single source of truth) are the constitutional articles this audit enforces. A schema that violates either is producing data with no provenance and no canonical home — slop, not authority data.

## The two failure modes from PR #169 — what to look for elsewhere

**Shape A — conflated semantics.** A field's name and its actual contents disagree. PM's `occupant_alt_names` was supposed to carry alternate readings of the SAME person's name (prenomens, throne-name vs birth-name pairs, transliteration variants). In practice it carried tomb-nicknames (`"Belzoni's tomb"`, `"Tomb of Memnon"`) — a different concept entirely. The fix was a new `tomb_aliases` field + narrowing `occupant_alt_names` semantics.

**Shape B — compound strings where structured data is the truth.** PM's `occupant_name` carried `"Yuia and Thuiu"` for joint burials — two distinct people packed into one string. The fix was a new `co_occupants` field + an `is_joint_burial` flag for coordinate burials with no PM-marked principal.

Both failure modes share a root cause: the schema was *under-typed* for the actual content. The agents extracted truthfully (PM does print `"Yuia and Thuiu"` in the headword), but the schema gave them no honest place to put the structure.

## Other failure modes to watch for

- **Shape C — load-bearing facts hidden in prose fields.** A `notes` / `notes_from_pm` / `description` field that contains structured facts (titles, dynasty, dates) that should be in their own typed fields. Test: can you mechanically extract every structured fact from `notes_from_pm` and verify it matches the typed fields? If `notes_from_pm` is the *only* place a fact lives, the typed schema is incomplete.

- **Shape D — silent defaults for "unknown" vs "verified empty".** An empty list `[]` or null that means both "we know there's nothing here" and "we don't know what's here" is unfalsifiable. Test: is there a way to distinguish "agent looked and saw nothing" from "agent didn't have data on this row"?

- **Shape E — implicit conventions ("when X looks like Y, treat as Z").** A schema where downstream consumers must remember rules like "if `occupant_name` contains `'and'`, treat as multi-person" is a Rule-3 violation (deterministic enforcement over convention). The KV46 → SWV-ThreePrincesses split in PR #169 fixed exactly this: the `is_joint_burial: bool` flag makes the convention explicit.

- **Shape F — controlled vocabulary not enforced.** A `role` / `dynasty` / `category` field with a documented controlled vocab but no test asserting every value is in the allowlist. Free-text drift accumulates silently.

- **Shape G — ambiguous join keys.** A field intended as a join key (`occupant_name`, `display_name`, `kitchen_id`, `dh_id`) where two distinct authority records can share the same value and the consumer can't disambiguate. If two rows have the same join key, downstream merges are non-deterministic.

- **Shape H — compound IDs / opaque keys.** A row identifier like `"Antef (Sehertaui)"` that packs multiple structured facts into one string. Test: can you parse the ID back into its components without scholarly knowledge? If not, the components are hidden in the ID and not in their own fields.

- **Shape I — fields that should be a list but are a scalar (or vice versa).** PM's `occupant_alt_names` was correctly a list. But Leprohon's `birth_names` is a list — what about a king who only has one birth name? Is `[]` valid, or is the field always non-empty? Schemas should be honest about cardinality.

- **Shape J — missing typed flags for known structural variants.** A row that's part of a series with a special property (joint burial, posthumous attribution, regnal-number disambiguation) where the property is implicit in field values. Add a typed `bool` / `enum` flag.

## Audit format (per source)

Each subagent produces `/tmp/claude/schema-audit-<source>.md` with these sections:

### Inventory

- Source name + path.
- Number of rows.
- Field set (every key that appears in any row).
- For each field: type (str/int/list/dict/bool/null), what fraction of rows populate it (non-null), and a one-line semantic description (read from README / prompt / fix_rows rationale, NOT inferred).

### Per-shape findings (A through J)

For each Shape A–J, one of:

- **CLEAN** — `<one-sentence rationale>`. (No instances of this failure mode in this source.)
- **FOUND** — `<finding description>`. List the affected rows / fields with values. Cite the README / prompt / fix_rows line where the schema is documented (or where it should be documented). Severity: **P0** (blocks downstream use right now), **P1** (will block downstream use when consumed), **P2** (sloppy, fix in next iteration), **P3** (nit / style).

### Cross-cutting recommendations

If the source has multiple Shape findings, propose how to fix them together (one schema-revision PR vs separate). Cite the PR #169 audit-fix as the reference pattern (`SCHEMA_FIELD_DEFAULTS` + `AUDIT_FIX_CORRECTIONS` + per-row migrations + new structural tests).

### Confidence

- **HIGH** — read every row, every prompt, every test; findings are concrete with citations.
- **MEDIUM** — spot-checked rows + read prompts/tests; some findings inferential.
- **LOW** — too many rows / unfamiliar source; recommend deeper pass.

State the confidence level and which sections are most/least certain.

## What NOT to flag

- **Field-naming bikeshed.** `display_name` vs `name` vs `english_name` is style preference, not a schema bug, unless the inconsistency creates an ambiguous join.
- **Optional fields being null.** CLAUDE.md rule 4 (sparse rows are valid) means most fields can be null. Don't flag nulls as bugs unless the field is documented as required.
- **Diacritic / transliteration variants.** Out of scope for this audit (different audit altogether).
- **Per-row data correctness.** This audit checks the *schema*, not whether individual values are right. Flag only schema-shape issues, not "I think KV23's role should be Queen not King".

## Reference: PR #169 (Porter-Moss audit-fix)

The canonical example of how to fix Shape A + Shape B in one PR:

- `pipeline/pipeline/authority/sources/porter-moss-theban-necropolis/fix_rows.py` — `SCHEMA_FIELD_DEFAULTS` (idempotent field-add) + `AUDIT_FIX_CORRECTIONS` (per-row migration) + `is_joint_burial: bool` flag for coordinate burials.
- `pipeline/tests/test_sources_porter_moss_theban_necropolis.py` — `test_no_compound_occupant_name`, `test_occupant_alt_names_are_person_variants_not_tomb_nicknames`, `test_co_occupants_each_have_name_and_role`, `test_tomb_aliases_is_list_of_strings`, `test_is_joint_burial_flag_paired_with_co_occupants`. Mechanical (Rule-3) enforcement of the new contract.
- README + 8 prompt files updated together so the schema rename is atomic.

Use this PR as the reference pattern when proposing fixes for other sources.
