---
name: editorial_notes additions are chunk-PR scope, even when motivated by downstream concerns
description: Don't accept "downstream museum-matching" as a scope-out justification for editorial_notes/note-field changes on chunk-owned rows
type: feedback
---

When an egyptologist-reviewer requests an `editorial_notes` (or `notes_from_beckerath`, etc.) addition on a row owned by the current chunk PR, the change is in-scope — even if the reviewer's *rationale* invokes downstream museum matching, alias coverage, or curator workflows.

**Rule:** The artifact of the change is what determines scope, not the rationale for wanting it. A one-line editorial_notes string on a row this PR is producing is a chunk-local fix_rows.py change. The downstream consequence is *why it matters*, not *where it lives*.

**Why:** "Downstream concern" / "alias-coverage problem" is becoming a recurring jargon-flex used to push scholarly polish out of chunk PRs. Observed on PR #139 with Pije (25.02 slash semantics) and Si-ptah (19.07 anfangs/später prenomen) — both single-row editorial_notes adds were nearly deferred as "downstream museum-matching commentary."

**How to apply:** When a main agent flags an editorial_notes/note request for deferral citing downstream effects, ask: does the change itself live in this chunk's owned files (fix_rows.py, reconciled.jsonl via re-merge, prompt-*.md)? If yes, the rationale is irrelevant — accept it.
