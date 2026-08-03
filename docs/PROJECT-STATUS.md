# Project Status

_Snapshot: 2026-08-03._

A one-page, honest picture of where Hapi actually is. For the vision and architecture, see the [README](../README.md), [`prd.md`](prd.md), and the [ADRs](adr/).

## Progress

| Phase | What it is | Progress | Status |
|---|---|---|---|
| **MVP ingest + search** | Museum APIs → canonical schema → search UI | `██████████` **100%** | ✅ Working, 3 museums, local only |
| **Phase 0 — Authority sourcing** | Extract scholarly reference works into reproducible, page-cited facts | `███████▁▁▁` **70–80%** | 🟡 One MVP-blocking source not started |
| **Phase A — Authority curation** | Reconcile facts into consolidated authority files; link artifacts to rulers/sites | `▁▁▁▁▁▁▁▁▁▁` **0%** | 🔜 Not started, and not yet unblocked |
| **Phase B — Matching** | Resolve provenance strings to authority IDs; surface companion pieces | **implementation exists**<br>`▁▁▁▁▁▁▁▁▁▁` **0% integrated** | 🟠 POC exists, fails review, on no branch that ships |
| **Web UX beyond search** | Artifact detail, browse-by-site, museum browse | `▁▁▁▁▁▁▁▁▁▁` **0%** | 🔜 0 of 4 tasks; 2 are blocked on Phase A |
| **Beta launch** | Deploy, seed, open to users | `▁▁▁▁▁▁▁▁▁▁` **0%** | 🔜 Nothing deployed anywhere |
| **Map view + companion pieces** _(optional)_ | Post-beta | `▁▁▁▁▁▁▁▁▁▁` **0%** | 🔜 Not started |

**Read the table this way:** the two phases that carry the product promise — A and B — are at zero delivered. Everything green is either infrastructure or inert data.

## TL;DR

Hapi is a working data pipeline with a real search front end, in the middle of building its scholarly authority layer. **You can search ~36,000 artifacts from three museums on a local machine today.** What's not done is the step that links each artifact to a canonical ruler and origin site — the feature that makes the index *useful* rather than merely searchable.

Think of it as a solid **v0.1** (search + filter works) some distance from **v1** (search that actually reunifies scattered finds).

## What demonstrably works end-to-end

- **Ingest → normalize → index → search**, for three museums: the Metropolitan Museum of Art (CC0 open-access), Harvard Art Museums, and Brooklyn Museum — roughly **36,000 normalized artifacts**. Three museums is the stated v1 scope in [`prd.md`](prd.md), not a shortfall.
- **Full-text search** over the indexed artifacts (Typesense), with **faceted filters**: museum, period, dynasty, ruler, site, object type, and pagination.
- **License-aware image rendering** — CC0 images embed directly; restricted images show a placeholder and a link out, never the asset. Enforced in the web component layer and covered by tests.
- **A strict, fixture-based test suite** — 2,194 pipeline tests on `main` assert specific field values against real museum API responses (no mocks for data shapes).

Caveat on "works": everything runs locally. There is no deployment, and `web/` carries exactly one test file.

## Phase 0 — sourced, inert, and not as done as previously reported

**4,583 reconciled rows across 12 source directories**, by three different methods — the split matters, because only the first carries multi-agent reconciliation:

- **Eight sources** (Leprohon, Beckerath, Kitchen, Ryholt, Baud, Dodson & Hilton, both Porter & Moss volumes) went through the deterministic 3-agent-extraction → merge → review workflow, each with a committed `merge.py`. These are page-cited. The text-acquisition step varies — most are OCR'd, Baud was extracted directly from the PDF text layer — and six of the eight also carry a committed `tie-break-overrides.json`; Baud and Dodson & Hilton needed none.
- **Two sources** (`shaw-ohae-2000`, `hkw-chronology-2006`) are page-cited transcriptions without multi-agent reconciliation — neither has a `merge.py`. HKW's 207 rows are LLM transcription with manual spot-checking plus four hand-extracted rows.
- **Two sources** (`idai-gazetteer`, `pharaoh-se`) are API/web-derived via committed fetch scripts, carrying source URLs and retrieval provenance rather than page citations. Ruler titulary (Leprohon 2013), chronology (von Beckerath, Kitchen, Ryholt, Shaw, HKW), Old Kingdom prosopography (Baud), queens (Dodson & Hilton), the Porter & Moss tomb registers for Thebes and Memphis, ~1,000 iDAI gazetteer sites, and the pharaoh.se ruler list.

**Why this is 70–80% and not the 95% previously published here.** [`mvp-tasks.md`](mvp-tasks.md) sets the Phase-0 completion gate at **~5,700–6,500 rows across ~14 sources**. We are at 4,583 across 12. Of its eight items marked *"Must-land before Phase A can start (MVP-blocking)"*, **four are still open** (tasks 4–7) — and the largest has not been started at all. (Task 3, Porter & Moss III, closed when the Abûsîr pyramid-field chunk landed in PR #311 on 2026-07-07; `mvp-tasks.md` still shows it 🟡 and is stale on that point. Task 8's two actionable audits are closed, with the FIP Dyn 7–10 gap standing as an accepted authority gap rather than open work.)

- **Porter & Moss Vol IV (Lower & Middle Egypt) — Task 7, MVP-blocker added 2026-05-19. Not started; no source directory exists.** Its highest-priority content is the **entire Amarna corpus**, the second-most-dispersed material in Egyptology after Thebes and among the most heavily partaged (Berlin, Cairo, the Met, Boston MFA, Brooklyn). Estimated ~400–700 rows. **It is blocked on one parked schema decision**: PM IV is multi-site, so the per-volume `theban_area` / `memphite_area` field pattern doesn't map, and a generic `site` field vs. field reuse decision was parked on 2026-06-01 and never taken.
- Dodson & Hilton Ch 5 (Ptolemaic) — zero rows extracted.
- Dodson & Hilton Ch 4 — roughly 150–200 of 250–300 rows outstanding.
- Porter & Moss I mortuary-temple sections and QV beyond chunk 8 (task 6) — open.

**How the 70–80% is calculated.** Row volume against the doc's own gate, and nothing else: 4,583 committed rows ÷ the 5,700–6,500 target = 71–80%. It is a range because the gate is a range. No blended or judgement-weighted figure is offered — by the other available measure, blocker completion, it would be 4 of 8.

The previous snapshot described this as "a small tail … acceptable to finish post-MVP." That contradicted this repo's own blocker list, and for the reunification promise specifically, omitting Amarna is not a tail.

**None of this data is consumed yet.** Every artifact's `ruler_id` and `origin_site_id` is still null.

## Phase A — genuinely at zero

`pipeline/pipeline/assets/enrich/__init__.py` is an empty file. `tests/test_enrichment/` contains only an empty `__init__.py`. No consolidated `rulers.json` or `sites.json` exists.

What *is* in place is cheap groundwork: the `ruler_id`, `origin_site_id` and `origin_site_display_name` columns exist and are indexed in `types/models.py`, and several blocking design questions (plural-named chronologies, Beckerath-lead, the pharaoh.se role) are resolved.

## Phase B — a real proof of concept that ships nowhere

The authority claim graph ([ADR-018](adr/018-authority-as-claim-graph.md)) — a CIDOC CRM 7.1.3 + CRMdig source-attributed model that preserves cross-source disagreement instead of collapsing it, with a deterministic + LLM two-stage matcher and a human-escalation path — is specified in full, and a substantial implementation exists: nine Python modules, five source loaders, 114 tests, and a deployable Next.js demo.

It is also, as of today:

- **On no branch that ships.** `git ls-files` returns nothing for `pipeline/pipeline/authority/claimgraph/` or `web-claimgraph/`; the code exists only in [PR #312](https://github.com/pcomans/hapi/pull/312), open since 2026-07-07.
- **Imported by nothing.** Not wired into `definitions.py`; no Dagster asset consumes it.
- **Recently carrying a do-not-merge verdict** — 9 findings, 5 of them P1, including a live `NameError` on the malformed-response path that the branch's whole passing suite never reached. Fixes for all nine are now pushed to the branch and awaiting re-review; the verdict stands until that lands.
- **Resolving 14% of candidates** — 226 approved links against 1,344 escalated to a human queue. That escalation rate is the design working as intended (precision-first), but it is not a finished matcher.

The "built" side deliberately carries **no percentage**. There is no agreed denominator for a finished matcher — the module count says work happened, not how much of the job it covers — and a made-up figure would read as measured. What is measurable is the integration: zero.

_(The earlier POC, PR #303, was closed 2026-08-03 as superseded by #312.)_

## The honest gap

The flagship promise — "see everything that came from one place" — is not deliverable, because artifacts aren't linked to origins.

The previous snapshot said that floor was "unblocked." It isn't, quite. Phase A's own gate requires PM IV, which is unstarted and waiting on a schema decision nobody has made. **That decision is the single cheapest unblock on the board.**

## Architectural maturity

19 Architecture Decision Records ([`docs/adr/`](adr/) — 001–018 plus 020; there is no 019) cover the pipeline/web split, Dagster orchestration, Typesense, schema ownership, authority sourcing, the OCR protocol, and the claim-graph model. Most are implemented; ADR-018 and ADR-020 are designed and awaiting Phase A.

## Automated code review

Both third-party GitHub review bots are non-functional: the previous app was sunset, and the Codex connector is not linked to this repo. Automated review currently runs from the local Codex CLI in-session. See the PR workflow in [`CLAUDE.md`](../CLAUDE.md).
