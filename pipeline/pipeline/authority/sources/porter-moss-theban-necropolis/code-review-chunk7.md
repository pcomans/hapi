# code-reviewer findings — chunk 7 (PM I.2 §§ II + III.A/C/D)

Retrospective code-review of the merged PR #100 (commit `996535b`), run
after the user flagged that `feedback_pr_reviewers.md`'s "code-reviewer +
egyptologist-reviewer on every PR" policy was not invoked during the
original PR cycle. The code-reviewer subagent's full findings are
transcribed here (the subagent declined to write the file itself due to
a system-reminder override; I captured the return-message content
verbatim).

## P2 — `test_chunk7_notes_from_pm_populated_rows` weakens rule-5 discipline

`tests/test_sources_porter_moss_theban_necropolis.py` (pre-fix-up lines
1684–1720) dropped from the exact-match pattern chunks 1–5 use
(`assert r["notes_from_pm"] == "..."`) to `substr in notes`. Worse, for
`DAN-AntefSehertaui` and `DAN-AntefSekhemreWepmaet`:

```python
val = _row(tid)["notes_from_pm"]
assert val is None or (isinstance(val, str) and val.strip()), tid
```

That is literally "absence of errors" — rule 5's explicit anti-pattern.
The stated justification ("full verbatim is too brittle to per-char
text-layer noise") does not hold: `fix_rows.py` exists precisely to
normalise text-layer noise to PM-verbatim. If the text-layer noise is
real, pin the *fixed* value; don't loosen the assertion. Chunks 1–5
manage full-verbatim; chunk 7 has no principled reason not to.

**Fix-up PR applied:** `test_chunk7_notes_from_pm_populated_rows` →
`test_chunk7_notes_from_pm` with exact-match assertions on every
populated row + `notes_from_pm is None` on the three Antef rows that
have no headword prose beyond name + cartouche + biblio.

## P2 — `VALLEY_ORDER` ↔ `_TOMB_ID_RE` synced by comment, not by test (rule 3)

`merge.py` lines 54–55 explicitly say "Prefix vocabulary is kept in
sync with the test regex at tests/…::_TOMB_ID_RE." That's a markdown
rule, not deterministic enforcement. If someone adds a prefix to one
but not the other, the failure mode is silent mis-sort or mis-
validation. A one-line test (e.g. assert
`set(VALLEY_ORDER) == {prefixes extracted from the test regex}`)
would enforce this mechanically.

**Fix-up PR applied:** added `test_prefix_vocabulary_consistent` which
reflectively imports `merge.VALLEY_ORDER` and matches its descriptor
prefixes against `_TOMB_ID_RE`'s descriptor alternation. Drift now
fails CI instead of silently mis-sorting.

## P2 — speculative generality in prefix registration

`merge.py` pre-registers `ASS`/`DEB`/`SAQN`/`RAM` in `VALLEY_ORDER` and
the test regex lists them too, before any rows in those chunks exist.
This is YAGNI. Chunks 9+ can add their own prefix when they land;
doing it ahead of time adds vocabulary to two places with no rows to
exercise it, and now can't fail if the entry is wrong.

**Fix-up PR applied:** removed `ASS`/`DEB`/`SAQN`/`RAM` from both
`merge.VALLEY_ORDER` and `_TOMB_ID_RE`. Future chunks extend both
together (and `test_prefix_vocabulary_consistent` will fail CI if they
diverge).

## P3 — dead regexes

`_TOMB_ID_NUM_RE` (test line 173) and `_TOMB_ID_DESC_RE` (line 174) are
defined but unused — only `_TOMB_ID_RE` is referenced. Delete or use
them.

**Fix-up PR applied:** removed both; added `_DESCRIPTOR_PREFIX_RE` as
a single helper used by the new consistency test.

## P3 — two chunk-7 correction rationales lack reviewer attribution (rule 1)

Per `feedback_fix_rows_unattributed_restoration.md`:
`DAN-MentuhotpIWifeOfDjhuti` notes restores `Ḍḥuti` (underdot-D +
underdot-H) — characters absent from the text layer — but the rationale
does not name the egyptologist-reviewer verdict. The reviewer DID flag
this (reviewer-notes-chunk7.md line 20); the attribution exists, the
rationale just needs to cite it as chunk-3 KV36 does. Same nit applies
to `DAN-AhmosiNefertere` notes expansion. Low-cost fix.

**Fix-up PR applied:** both rationales now cite
`reviewer-notes-chunk7.md` + the P1/P2 severity + the reviewer's
paraphrased verdict.

## Things that check out

- `test_all_renames_includes_every_chunk_dict` is well-designed and
  mirrors `test_all_corrections_includes_every_chunk_list`'s natural-
  numeric sort.
- Rename + re-sort path is idempotent and loud-fails on target collision.
- The module-level duplicate-`(tomb_id, field)` raise (`fix_rows.py`
  504–513) is correct rule-2 loud-fail.
- The `ḥ→h` sweep rationales ("Gemini round-3 sweep on PR #101") are
  **not** rule-1 violations — they're mechanical application of the
  README's codified strip-rule (removing characters), not insertion of
  characters absent from raw. The chunk-4 KV55 anti-pattern in the
  `fix_rows_unattributed_restoration` memory is about *insertion*, not
  *removal*.
- `_import_merge_sort_key` via `importlib.util` is ugly but forced by
  the hyphenated directory name. Not worth flagging.
