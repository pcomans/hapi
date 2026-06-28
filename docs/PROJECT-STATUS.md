# Project Status

_Snapshot: 2026-06-25._

A one-page, honest picture of where Hapi actually is. For the vision and architecture, see the [README](../README.md), [`prd.md`](prd.md), and the [ADRs](adr/).

## TL;DR

Hapi is a working data pipeline with a real search front end, in the middle of building its scholarly authority layer. **You can search ~36,000 artifacts from three museums today.** What's not done yet is the step that links each artifact to a canonical ruler and origin site — which is exactly the feature that makes the index *useful* rather than just searchable. The hard, slow scholarly groundwork for that step is ~95% done; the curation that consumes it has not started.

Think of it as a solid **v0.1** (search + filter works) on its way to **v1** (search that actually reunifies scattered finds).

## The roadmap, in four phases

| Phase | What it is | Status |
|---|---|---|
| **MVP ingest + search** | Museum APIs → canonical schema → search UI | ✅ Working for 3 museums |
| **Phase 0 — Authority sourcing** | Extract scholarly reference works into reproducible, page-cited facts | 🟢 ~95% complete |
| **Phase A — Authority curation** | Reconcile those facts across sources into consolidated authority files; link artifacts to rulers/sites | 🔜 Not started (now unblocked) |
| **Phase B — Matching** | Resolve museum provenance strings to authority IDs; surface companion pieces | 🔜 Designed, not built |

## What demonstrably works end-to-end

- **Ingest → normalize → index → search**, for three museums:
  - The Metropolitan Museum of Art (CC0 open-access), Harvard Art Museums, Brooklyn Museum — roughly **36,000 normalized artifacts** total.
- **Full-text search** over the indexed artifacts (Typesense), with **faceted filters**: museum, period, dynasty, ruler, site, object type, and pagination.
- **License-aware image rendering** — CC0 images embed directly; restricted images show a placeholder and a link out, never the asset. Enforced in the web component layer and covered by tests.
- **A strict, fixture-based test suite** — mapper and source tests assert specific field values against real museum API responses (no mocks for data shapes).

## What's sourced but not yet wired in

**Phase 0** has extracted **~4,600 reconciled, page-cited facts** from **11 scholarly works**, each via the deterministic OCR → 3-agent-extraction → merge → review pipeline. Highlights:

- Ruler titulary (Leprohon 2013), chronology (von Beckerath, Kitchen, Ryholt, Shaw, HKW), Old Kingdom prosopography (Baud), queens (Dodson & Hilton), and the large Porter & Moss tomb registers for Thebes and Memphis.
- Site authority from the iDAI gazetteer (~1,000 sites); ruler list from pharaoh.se.
- All sources pass the schema-integrity gate; remaining work is a small tail (a couple of Porter & Moss / Dodson-Hilton sub-sections), acceptable to finish post-MVP.

This data is committed and tested, but **not yet consumed** — the enrich stage that would attach it to artifacts isn't built. Today every artifact's `ruler_id` and `origin_site_id` are still null.

## What's designed but not built

- **The authority claim graph (ADR-018).** A CIDOC CRM 7.1.3 + CRMdig source-attributed model that preserves cross-source disagreement instead of collapsing it, with a deterministic + LLM two-stage matcher and a human-escalation path. The spec is complete and a proof-of-concept exists ([open PR #303](https://github.com/pcomans/hapi/pull/303)); it is **not** merged or wired into the pipeline.
- **Web features beyond search:** artifact detail pages, browse-by-site, museum browse, the map view, and companion-piece discovery are all planned, not implemented.

## The honest gap

The flagship promise — "see everything that came from one place" — is not deliverable yet, because artifacts aren't linked to origins. The search works; the *meaning* (ruler and site resolution) is the next floor to build. That floor is unblocked: Phase 0 produced the materials, ADR-018 is the blueprint, and Phase A is where they come together.

## Architectural maturity

18 accepted Architecture Decision Records ([`docs/adr/`](adr/)) cover the pipeline/web split, Dagster orchestration, Typesense, schema ownership, authority sourcing, the OCR protocol, and the claim-graph model — 17 of 18 are implemented or in implementation; ADR-018 is designed and awaiting Phase A.
