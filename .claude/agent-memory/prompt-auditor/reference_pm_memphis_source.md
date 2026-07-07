---
name: reference-pm-memphis-source
description: File layout and cross-check paths for auditing porter-moss-memphis Phase-0 prompts.
metadata:
  type: reference
---

`pipeline/pipeline/authority/sources/porter-moss-memphis/` — PM Vol III (Memphis)
extraction source, sibling to `porter-moss-theban-necropolis/`.

- `prompt-chunk-<N>.md` — the extraction prompt to audit.
- `raw/chunk-<N>-p<start>-p<end>-<slug>.{txt,md}` — gitignored raw text-layer dump; present
  locally, use `Glob` to find the exact filename (slug varies).
- `README.md` — schema reference + per-chunk changelog (the "Multi-chunk plan" section
  documents what each prior chunk landed — occupant names, row counts, PR numbers — useful
  for confirming whether a name in the current prompt is legitimate "earlier chunk"
  precedent or a fresh leak).
- `reconciled.jsonl` — committed merged output of all prior chunks. `grep '"occupant_name":
  "<Name>"'` against this to check whether a name the current prompt cites has already been
  extracted (legitimate precedent) or is new (potential leak of the current chunk's answer).
- `merge.py` — has an `AREA_ORDER` dict that must list every `tomb_id` prefix in use
  (`G`, `LG`, `SAQ`, `MAR`, `DAH`, ...). A new prompt introducing a new prefix (e.g. `ABU-`
  for Abûsîr, chunk 36) needs a corresponding `AREA_ORDER` entry before merge can run —
  not a prompt leak, but worth flagging as a P2/heads-up since the prompt's new prefix
  won't sort correctly otherwise.
- Earlier prompts (`prompt-chunk-2.md`, `-7.md`, `-8.md`, or whichever numerically precede
  the audited chunk) show the established rule-based discipline pattern for this source —
  read one or two for calibration before flagging something as novel/leaky.

Related: [[feedback_diacritics_section_leaks_real_names]]
