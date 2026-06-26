# Publish-Readiness Audit & Runbook

_Audit date: 2026-06-25. Purpose: assess what it takes to make this repository public, and in what order._

> **Not legal advice.** This is an engineering audit of the repository's contents and history. The fact-extraction approach for copyrighted scholarship is well-documented and defensible, but it is an untested working assumption. If you need certainty rather than "defensible," get a lawyer's sign-off on that one question (see §2).

## Verdict

**Publishable, with a finite punch list. No hard blockers were found.** The repository was deliberately architected for an eventual public release, and the load-bearing safeguards hold.

## 1. What's already clean (verified)

- **No copyrighted PDF ever entered this repo's history.** `git log --all --diff-filter=A -- '*.pdf'` returns empty. The ~20 in-copyright books live only in the separate **private** `hapi-proprietary` submodule; the public repo carries a gitlink pointer, not content.
- **No secrets, ever.** A full-history scan for API keys, tokens, OAuth credentials, and private keys came back empty. The devcontainer auth churn used `${localEnv:...}` indirection — no literal token was committed. Database/Typesense values are local-dev placeholders (`hapi/hapi`, `hapi-dev-key`) bound to localhost.
- **Raw OCR/transcription is gitignored and CI-enforced** (`test_no_tracked_files_under_raw_for_phase0_sources`). Only derived, page-cited `reconciled.jsonl` fact tables ship.
- **Dependencies are permissive** (no GPL/AGPL obligations on a public release).

## 2. Copyright posture on derived data (decision: publish as-is)

The authority `reconciled.jsonl` files contain mostly structured facts (name → dynasty → page cite). A few fields carry short verbatim scholarly prose — `notes` (Dodson-Hilton: 549 sentence-length "Brief Lives" fragments; Leprohon: 6 rows; HKW: 64), `source_note` (Shaw: 3) — plus the `merge-disagreements.txt` audit dumps.

**Finding — can this be scrubbed cleanly? No.** The prose fields do **not** feed cross-source matching (the matcher keys on names/titulary), so removing them wouldn't affect matching. But they are load-bearing in each source's reproducible extraction scripts (e.g. Dodson-Hilton's `diff_*.py` read and concatenate `notes`) and are locked down by ~700 test assertions plus the determinism checks. Nulling them out would break the "reproducibly-acquired" guarantee (constitutional rules 1/6) and a large part of the test suite. A real scrub is a *refactor* (regenerate extraction to exclude prose at the source, rewrite coupled tests), not a pre-publish chore.

**Decision:** publish the authority data **as-is**, relying on the project's documented fact-compilation posture (see the rights policy in `playbook-phase-0-ocr-transcription.md`) plus the `NOTICE` file. The exposure is sentence-level, field-scoped, and citation-bearing.

**Update — Dodson-Hilton `notes` scrubbed (the largest single concentration).** The 549 verbatim "Brief Lives" fragments have been removed via a new deterministic terminal pipeline stage, `destructure_notes.py`. A harvest pass first verified that every matchable fact already lives in a structured field (0 name-variant gaps, 0 kinship gaps), so the drop loses no matching data. The stage also strips the verbatim `notes:` lines from `merge-disagreements.txt`, and the 5 `notes`-targeting corrections were removed from `fix_rows.py` (they would otherwise re-introduce prose on a re-run). Full pipeline suite green (2170 passed).

**The other sources' note fields were reviewed and intentionally KEPT** (do not blindly drop them in a future pass):

- **HKW `note` (64 rows)** — overwhelmingly the project's *own* transcription-provenance and method notes (OCR-correction rationale, period-mapping decisions). That is rule-1 documentation, not copyright exposure. Only ~15 quote the source, mostly short facts (dates/names); a single note carries one verbatim Hendrickx sentence. Kept.
- **Shaw `source_note` (3 rows)** — first-party chapter-label → canonical-period mapping notes. No verbatim Shaw prose. Kept.
- **Leprohon `notes` (6 rows / 3 distinct)** — short uncopyrightable factual statements ("King X is not known from hieroglyphic sources"). No matching data. Kept under the documented Feist posture.

Dodson-Hilton was the only source carrying wholesale verbatim copyrighted prose.

## 3. Attribution obligations (done in this change)

Three incorporated data sources require attribution under CC BY 4.0 — CIDOC CRM, the iDAI gazetteer, and pharaoh.se — and the museum terms must be surfaced. All are now recorded in [`NOTICE`](../NOTICE). Note: **Brooklyn and Harvard data are noncommercial-only**; any future monetization must revisit those integrations. Image display is gated per-object by the `license` field (constitutional rule 8).

## 4. The pre-publish punch list

Ordered. Items 1–3 are done in this change; 4–6 are actions to take when you flip the repo public.

1. ✅ **Add `LICENSE`** (Apache-2.0) — done.
2. ✅ **Add `NOTICE`** with required attributions — done.
3. ✅ **Set the `license` field** in `web/package.json` and `pipeline/pyproject.toml` (and fix the placeholder description) — done.
4. ⏳ **Scrub PII from commit history** (decided: yes). Author/committer history contains an employer email and a private machine hostname (enumerate them locally — do not paste them into committed docs; see §5). This requires a one-time history rewrite — **run it as the final step**, because it rewrites every commit SHA.
5. ⏳ **Confirm `hapi-proprietary` is and stays private** on GitHub before publishing. This is the single load-bearing external assumption: if that repo is public, all the copyrighted PDFs are exposed. (Cannot be verified from inside this repo.)
6. ⏳ **Resolve open PRs first.** A history rewrite (step 4) orphans every open PR by changing SHAs. Merge or close the 5 open PRs — notably #303 (the ADR-018 POC) — *before* rewriting and force-pushing.

## 5. Runbook — PII history rewrite (run last)

Uses [`git filter-repo`](https://github.com/newren/git-filter-repo). **Do this after open PRs are resolved and against a fresh mirror clone you can verify before force-pushing.**

```bash
# 1. Enumerate the identities actually present in history (locally — do NOT
#    commit the output). Pick out the employer email and the *.local hostname.
git log --all --format='%an <%ae>%n%cn <%ce>' | sort -u

# 2. Build a mailmap that maps every sensitive identity to your clean public
#    identity. Fill in the placeholders from step 1's output — keep this file
#    local; never commit it. Mailmap syntax is `Proper Name <proper-email>
#    <commit-email-to-replace>`: the NAME is plain text (no angle brackets),
#    only the emails are bracketed.
cat > /tmp/hapi-mailmap <<'EOF'
Your Public Name <your-public-email>  <employer-email-to-scrub>
Your Public Name <your-public-email>  <other-private-email-to-scrub>
Your Public Name <your-public-email>  <user@private-hostname.local>
EOF

# 3. Work on a fresh mirror so the live repo is untouched until you've verified.
git clone --mirror <repo-url> hapi-rewrite.git
cd hapi-rewrite.git
# --force is required: a --mirror clone has a remote, and git filter-repo
# refuses to run on a non-"fresh" clone without it.
git filter-repo --force --mailmap /tmp/hapi-mailmap

# 4. Verify no sensitive identity remains before pushing anywhere public.
git log --all --format='%ae%n%ce' | sort -u   # employer domain / *.local must be gone

# 5. Only then force-push the rewritten history to the (now public) remote.
```

The placeholders above are intentional — the whole point of this step is to keep the sensitive email/hostname out of the public tree, so they must not be pasted into this committed runbook. Fill them in from step 1 at run time. Every SHA changes; anyone with an old clone must re-clone.

## 6. Optional cleanups (not blockers)

- The `merge-disagreements.txt` files (~12.5k lines total) are regenerable audit artifacts. The Dodson-Hilton one has had its verbatim `notes:` lines stripped (see §2); the others still carry per-field disagreement prose for their respective sources and can be sanitised the same way if those sources' prose fields are scrubbed.
- A large `build/claim_graph.json` (~18 MB) and a `tm-places` reconciled file appear in history but are **not** currently tracked. They don't leak secrets or copyrighted text, but if you ever want a smaller public history you could prune them in the same `filter-repo` pass.
