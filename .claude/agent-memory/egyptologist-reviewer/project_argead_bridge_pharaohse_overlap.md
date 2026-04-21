---
name: Argead bridge — pharaoh.se actually covers these kings
description: Hölbl-2001-argead source README claims pharaoh.se begins at Ptolemy I, but pharaoh.se already has full rows for Alexander the Great, Philip III Arrhidaeus, and Alexander IV (dynasty_label "Argead Dynasty"). Any "bridge" extract must treat pharaoh.se as an overlap, not a gap.
type: project
---

Pharaoh.se's `reconciled.jsonl` contains full `kind: ruler` entries for `Alexander-the-Great`, `Philip-III-Arrhidaeus`, and `Alexander-IV`, each tagged `dynasty_label: "Argead Dynasty"`, with full Beckerath-cited titulary (prenomen `Setep en Ra, mery Amun` for Alexander and Philip III; `Haa ib Ra, setep en Amun` for Alexander IV), Dodson/Shaw/von Beckerath/Redford reign dates, and Greek-form `alt_labels`.

**Why:** When the Hölbl-2001-argead README (PR #74, branch `feat/holbl-2001-argead`) states "these three kings are absent from... pharaoh.se (which begins at Ptolemy I Soter)" and justifies the extract on that premise, it is factually wrong. The extract is still useful (Hölbl gives event-level prose, dates are slightly different — e.g. Alexander IV end year -310 Hölbl vs -309 pharaoh.se), but it is an *overlapping* source, not a *gap-filling* source.

**How to apply:** For any future Argead/Ptolemaic Phase-0 PR, check pharaoh.se coverage first by globbing `pharaoh-se/raw/*.md` for the relevant ruler name. Naming conventions: pharaoh.se uses "Philip III Arrhidaeus" (-eus), Hölbl prints "PHILIP III ARRHIDAIOS" (-os). Expect naming mismatches that Phase A will have to reconcile; flag them in reviews rather than letting them slide as "Phase A problem".
