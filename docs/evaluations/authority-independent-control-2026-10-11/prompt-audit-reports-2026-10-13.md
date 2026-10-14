# Prompt-auditor reports, rounds 12–16 (2026-10-13), verbatim

The final reports of the `prompt-auditor` agent (a Claude Code subagent of the working
session) for the audit rounds summarised in `prompt-audit-2026-10-11.md`, copied exactly as
returned. Rounds 1–11 were summarised only; from round 12 the reports are kept.

## Round 12 (v4 first drafts)

Rule 14 audit of the v4 prompts. I found no P0 or P1 and no answer leakage. All four prompts get a conditional PASS: there is one P2, shared by all four, to fix first. I edited nothing. I read all 4 v4 prompts against their v3 versions, the system prompt, the tool description, and the composed requests (reviewer cases 001 and 002 for Stage 1, reviewer cases 001 and 003 for Stage 2, reconciler review-unit-023, and the Stage 2 reconciler case-001).

**Verdicts**
- stage-1-reviewer-v4: PASS once P2-1 is fixed.
- stage-1-reconciler-v4: PASS once P2-1 is fixed.
- stage-2-reviewer-v4: PASS once P2-1 is fixed.
- stage-2-reconciler-v4: PASS once P2-1 is fixed.

**Leak checks that came back clean**
- The v4 sourcing paragraph is identical in all four prompts apart from the reconciler additions, and it names no outcome, arm, class or selection.
- The diff against v3 only removes the exception route and the `web fetch` wording, and adds the open_page and loaded rules. Nothing case-specific was added.
- No `exception` or `web fetch` wording survives in the v4 prompts, the new system prompt, or the case-v2 schemas.
- The strings rule is still symmetric: "Whether the two sides' strings match or differ is never, by itself, a basis for any judgment."
- Case facts and `shown_records` are explicitly "case evidence, not sources". "Case evidence is never, by itself, a basis" is consistent with "Every judgment must rest on a page you opened".
- Does the stricter citation rule favor one outcome or class? No, not by wording. Every outcome, including `different_entity` and `insufficient_evidence`, needs an opened and loaded page. The prompts give identical-string and differing-string cases the same path: open both museum records, then a page that connects them. The cost of finding that page is the residual already disclosed for earlier rounds.
- Reviewer ordering: reconciler review labels are opaque, and the dissent order in the sample (review-1 `insufficient_evidence`, review-2 `same_entity`) is arbitrary.

**P2-1 (all four prompts): "Always cite at least one" contradicts "cite only loaded pages", and the schema forces it**
- The quoted text is, in the reviewers: "Always cite at least one, including when you answer insufficient_evidence (then cite the pages you opened)". The reconciler versions have the same sentence. It sits beside "Cite only pages you opened yourself and that loaded" and "A page is a source only if open_page returned it with loaded: true".
- Every `citations` array in the case-v2 schemas has `"minItems": 1`.
- A reviewer whose every open_page call fails to load (HTTP 429, 404 or an unreachable site) cannot comply. It must either break the schema or cite a page that did not load, which the prompt forbids. That pushes toward a fabricated or non-loaded citation exactly when the honest answer is `insufficient_evidence`.
- "the pages you opened" is also ambiguous. A page can be opened without loading, and the tool description says only loaded: true may be cited.
- Replacement wording, for all four prompts:
  - Reviewers: "Cite the URLs of the opened pages that loaded and that you relied on. Give at least one citation for any outcome other than insufficient_evidence. If you answer insufficient_evidence, cite the loaded pages you read, if any; if no page loaded, return an empty citations array."
  - Reconcilers: the same text, per disputed question.
- Schema change needed with it: allow an empty `citations` array when the outcome is `insufficient_evidence`. Keep `minItems: 1` conditional on the other outcomes, and for reconcilers apply it per resolution. Without that schema change the prompt fix is useless. A post-run check that every citation URL appears among the call's loaded open_page results would then make this deterministic (rule 3).

**P3 (disclose or tidy, none blocking)**
1. **Cited URL form.** The tool returns both `requested_url` and `final_url`, and the prompts don't say which to cite. If a harness check matches citations against open_page logs, redirects (Met search URLs, brooklynmuseum.org vs opencollection.brooklynmuseum.org) will cause false mismatches. Suggested sentence: "Cite the final_url of a page whose loaded is true." The real v3 reviews already mix collectionapi and opencollection hosts.
2. **"institutional" dropped.** v3 said "Every judgment must rest on an institutional source you cite". v4 says "a page you opened", and "institutional" survives only in the "Prefer ..." sentence. That makes any loaded page citable (Wikipedia, blogs, Wikidata mirrors, GeoNames), in every class equally. If it is intentional, disclose it in the README. If not, use "rest on a page you opened with open_page, preferably an institutional one, and cite".
3. **`loaded: true` is only HTTP 200.** A 200 Security Checkpoint or soft-404 page can still be cited. A reviewer who cites one is a risk that is equal across classes. The prompt could add "and whose text is the page's content, not a checkpoint or error page".
4. **Stage 2 target metadata.** `representation: "approved_claim_graph_cluster"` (rulers) vs `"idai_reconciled_source_row"` (sites) is a class-correlated builder label, and "approved" could read as an endorsement of the target. `parent_in_file`, `member_ids` and the cross_refs are also builder internals. This is the same residual accepted in rounds 10 and 11. If the release step can strip `representation`, do so (it is unused by the prompt text).
5. **The reconciler sample is not a clean v4 composition.** The v3 reviews' reasoning narrates WebFetch failures ("brooklynmuseum.org returned HTTP 429 on every attempt", "I could not open any Brooklyn record"). Their citations include URLs the reviewers say they never opened, such as `www.brooklynmuseum.org/objects/117777` and `/118333`.
   - In a v4 run these should come from v4 reviewers.
   - If v3 reviews are reused, a reconciler is told that Brooklyn pages can't be opened and may not retry with open_page, which skews it toward `insufficient_evidence` on Brooklyn-heavy cases. Don't reuse them.
   - The Stage 2 reconciler placeholder reviews (both `insufficient_evidence`) are not realistic, so real reviews remain unaudited. Scan the first real reconciler requests for repo or evaluation self-reference before the run.
6. **Gate.** Rule 14's round-9 check applies again. Measure the open_page loaded rate per museum (and per case class) against the private answer key before reading results. Without the exception route, an unloadable Met or Brooklyn record forces `insufficient_evidence`, which is class-neutral only if the loaded rate is.
7. **Tool configuration.** The prompt and system prompt only say "use open_page". Confirm in the launcher that WebFetch and Bash are actually not available to the agents, or the "loaded" discipline is only a convention.
8. **Tool description text.** The file you gave me shows `f"{MAX_TEXT_CHARS} characters"` in source form. Confirm the rendered description carries the real number.

Files audited:
- /workspaces/hapi-342/docs/evaluations/authority-independent-control-2026-10-11/prompts/ (the v3 and v4 prompts)
- /tmp/claude-1000/-workspaces-content/e94d96de-5992-406d-a8e0-26faf505e839/scratchpad/audit-v4/ (the composed requests, system prompt and tool description)

I could not read `scripts/open_page_server.py`, because that path doesn't exist under /workspaces/hapi-342 (my search only covered that directory).

## Round 13 (v4 after the round-12 fixes)

Round 2 re-audit: all four v4 prompts PASS, with no P0, P1 or P2. I edited nothing.

**Verdicts**
- stage-1-reviewer-v4: PASS
- stage-1-reconciler-v4: PASS
- stage-2-reviewer-v4: PASS
- stage-2-reconciler-v4: PASS

**Round-1 findings**
- **P2-1 is resolved.** "Any outcome other than insufficient_evidence needs at least one citation. For insufficient_evidence, cite the loaded pages you read, if any; if no page loaded, give an empty citations list." no longer conflicts with "cite only pages you opened and that loaded".
  - The Stage 1 reconciler schema now uses if/else: `outcome == insufficient_evidence` allows an empty `citations`, and the else branch requires `minItems: 1`. It is applied per resolution, so each resolution is checked on its own.
  - That matches the prompt wording. The reviewer schemas are the same pattern. I only read the Stage 1 reconciler schema in full, so the Stage 2 and reviewer schemas are assumed from your description.
  - "Any outcome other than insufficient_evidence" with a shared reviewer `citations` array is clear enough: [] is legal only if every answered field is insufficient_evidence.
- **P3-1 is resolved.** "by the URL you opened or its final_url" matches the tool output (`requested_url` / `final_url`).
- **P3-2 is resolved.** "institutional source that you opened with open_page" is back in all four prompts. It is not contradicted by "A museum's own record page ... is a source".
- **P3-3 is resolved.** The added clause is also enforced in code, because `loaded` is false for a checkpoint title.
- **P3-5 is resolved.** The reconciler samples now use placeholder v4-style reviews, so the stale v3 narration that Brooklyn pages can't be opened is gone.
- **P3-7 and P3-8** are confirmed by the rendered tool description (40000) and by your launcher description.

**Leakage and class-symmetry re-check**
- The changed text names no outcome, arm, class or selection.
- The new empty-citations path costs nothing for `insufficient_evidence` and requires a loaded page for decisive outcomes. That asymmetry is intended. It becomes class-linked only through the loaded-page rate, which your planned per-museum and per-class gate (P3-6) covers. Keep it as a hard gate before reading any results.
- The open_page server code has no answer-relevant content: pacing, a blocked-domains list, and a checkpoint wait. It returns no hints about the case.

**New P3s (none blocking)**
1. **Tool description vs code.** The description says `loaded` is "true only if the page loaded with status 200". The code also requires that the title is not a checkpoint title. The prompt's "not an error or checkpoint page" clause covers the gap, but you could align the description: "true only if status is 200 and the page is not a checkpoint page".
2. **Sample defect.** In `stage_1_reconciler-review-unit-001.txt`, placeholder review-2 has `"useful_granularity": "same_entity"`, which is not an allowed outcome. It should be `useful`. Harmless as a sample, but make sure the builder doesn't emit it.
3. **Open the stage-2 audit dir's remaining requests.** I did not re-read the r2 reviewer requests in full. Only the schema sections and the Stage 1 reconciler were checked. The prompt texts and schemas came from the files you pointed to, and the case bodies match round 1.
4. **Carried over and unchanged.** The accepted builder-internal target metadata (`representation: approved_claim_graph_cluster` vs `idai_reconciled_source_row`, P3-4) is still a class-correlated label. A navigation error such as a timeout or blocked domain raises a tool error and gives no `loaded` record. The prompt doesn't say so, but the behavior is harmless.

## Round 14 (v5 first drafts)

Round 14 audit: v5 prompts and review-system-v4, checked against the composed requests (Stage 1 units 001/002, Stage 2 cases 001/003, both reconcilers, system prompt, rendered tool description).

I read v4 and v5 side by side by eye, because Bash was unavailable. In all four prompts the only changes are the three you described: the citable-sources sentence, "citable source" replacing "institutional source", and the lumping sentence. The lumping sentence is in all four v5 prompts, including both reconcilers. The rendered "Citable sources" block is identical in all six composed requests. It sits after the role prompt and before the response schema, and carries 48 lines of host/path plus institution. The roles are not rendered.

### Verdicts
| Prompt | Verdict |
|---|---|
| stage-1-reviewer-v5 | FAIL (P2-1) |
| stage-1-reconciler-v5 | FAIL (P2-1) |
| stage-2-reviewer-v5 | FAIL (P2-1) |
| stage-2-reconciler-v5 | FAIL (P2-1) |
| review-system-v4 | PASS (P3 only) |

The one P2 is the same sentence in all four prompts. There are no P0 or P1 findings.

### 1. Does the allowlist leak? No (PASS)
- The block is constant across every case, class and stage. Order is by category (case museums first, then other museums, gazetteers, projects, publications, repositories, authorities), not by case. Nothing in it is per-row.
- The case museums (Met, Brooklyn, Harvard) are already visible in each case's `museum_pair`. iDAI/"dainst.org" was already named in v4 ("Prefer official museum, iDAI, ..."), so the allowlist adds no new disclosure about where the Stage 2 site targets come from.
- Roles are not rendered. I confirmed that in the request text.
- P3: the target metadata in Stage 2 ruler requests lists `source_ids` beckerath, leprohon and pharaoh_se. None of the three is citable under the allowlist, and `citable-sources.json` says so for all three. That tells a ruler reviewer that its target derives from non-openable sources. It is uniform across rulers, so it is not class-linked, but it feeds item 4. It is the same builder-internal metadata accepted in rounds 10-11 (`representation: approved_claim_graph_cluster`). Check once, in aggregate against the private key, that `representation` and `source_ids` do not vary by class.

### 2. Lumping sentence: P2-1, asymmetric
Quoted text (all four prompts): "A source that treats a whole area as one place (a UNESCO World Heritage property, a Pleiades place) does not by itself show identity at the level of a site, necropolis or tomb within it."

It cautions only against concluding identity. It is silent on concluding difference, and a coarse source cannot show difference either. This is the round-2 and round-10 pattern: a one-sided push.

It also lands unevenly on the classes. Differing-string cases (variant site spellings, which the authority arm would link) depend on alias-bearing gazetteers such as Pleiades, UNESCO and iDAI to show equivalence. Identical-string cases can lean on the two museums' own record pages. The sentence names two of the main alias sources as insufficient, so it pushes differing-string cases toward `insufficient_evidence` more than identical-string ones.

In Stage 2 it also duplicates the existing rule that a containing place, contained place or broad region is a different entity. That rule already carries the point symmetrically.

Replacement (same position, all four prompts; the reconcilers say "disputed question" instead of "question"):
"A source can show only what it documents, at the granularity it documents it. A source that treats a whole area as one place (a UNESCO World Heritage property, a Pleiades place) shows neither that a site, necropolis or tomb within it is the same as another entity nor that it is different. Settle each question from sources that document the entity at the level being judged."

### 3. Consistency (P3)
- **P3-a, wording:**
  - Quote: "Give concise reasoning and the URLs of the loaded pages you relied on" and "For insufficient_evidence, cite the loaded pages you read, if any; if no page loaded, give an empty citations list."
  - The second quote means that a page which loaded but is not on the allowlist could be cited under `insufficient_evidence`. That contradicts "Any other page ... is never a citation."
  - Fix: "the loaded citable pages" in both places, and "if no citable page loaded, give an empty citations list".
- **P3-b, wording:**
  - Quote: "A page is a source only if open_page returned it with loaded: true ..."
  - Fix: add "and it belongs to a citable source". The tool description already says this; the prompt does not.
- **P3-c, wording:**
  - Quote: "A museum's own record page, once you have opened it, is a source you may cite for what that record says".
  - It reads as covering any museum, including ones not on the list.
  - Fix: "A record page of a listed museum, once you have opened it, ...".
- **P3-d, which URL must match:**
  - Quote: "by the URL you opened or its final_url".
  - It does not say which one must match the allowlist. A redirect from a listed host to an unlisted one, or the reverse, is ambiguous.
  - Fix: "A page counts only if its final_url is on a citable source."
  - Confirm the code gate uses `final_url`.
- **P3-e, wording:** the system prompt says "the citable sources listed with the case" and the role prompts say "listed after this prompt". The meaning is clear; align the phrasing if you edit.
- The "Every judgment must rest on a citable source" versus empty-citations path is the same as round 13. It is fine once P3-a is applied.
- The tool description ("Only a page with loaded: true that belongs to a citable source may be cited") is consistent with the prompts.

### 4. Class-linked effect of the allowlist itself: a measured residual, not a prompt leak
The prompt does not name an outcome, class or arm. The effects below come from what the allowlist contains, which was an owner and Egyptologist decision. I am not recommending a prompt change; I am recommending the gate be stratified.

- **Rulers have no openable authority.**
  - Beckerath, Leprohon and Horn/Krauss/Warburton are non-citable (`not_citable_but_standard`), and pharaoh.se is excluded.
  - Ruler identity can rest only on museum record pages (role `case_input`, which show what the case says), the UCL Digital Egypt pages, UEE, TLA, Trismegistos, and similar pages.
  - Stage 2 ruler targets are clusters of non-citable sources, so the target cannot be checked against its own record. Site targets have an openable iDAI record (role `target_record`). This is an entity-type asymmetry in the achievable `insufficient_evidence` rate.
  - Case-001 shows a spelling mismatch: museums read "Senwosret III", the target is labelled "Senusret III". Differing-spelling ruler cases need a source documenting the equivalence. Identical-string ones are easier to cite, but the citation then rests only on the case-input museum pages.
  - Net: expect more `insufficient_evidence` for rulers than for sites, and within each type for differing-string (authority-only) cases more than identical-string (retained) ones.
- **What to measure** (aggregate against the private key, before any result is read, as in the round-9/12 gates):
  - Loaded-and-citable rate and `insufficient_evidence` rate by entity type × class × museum (the museum split is the Met/Brooklyn checkpoint issue from the earlier rounds).
  - The citation-role report: the share of decisions whose only citations are `case_input` or `target_record`, by class.
  - Stratify by entity type first. A pooled class comparison would confound class with type.
- **Decision-rule caveat:** if the ruler class mix differs between arms, a ruler-driven `insufficient_evidence` excess will look like an arm effect. The pre-registered decision rule should say how a type-stratified excess is read. This is a reporting matter and needs no prompt change.
- **Circularity of `target_record` and `case_input`:** a reviewer can cite iDAI for what the target is and a case museum for what the record says, and still conclude identity without an independent source. The role report catches this. The prompt neither causes nor prevents it, and that is acceptable.

### Summary
Apply the P2-1 replacement in all four prompts and the P3 wording fixes, then re-run this audit on the recomposed requests. The allowlist block itself needs no change. After the lumping sentence is replaced, I expect PASS.

## Round 15 (v5 after the round-14 fixes)

Round 15 re-audit: PASS for all five items. There are no P0, P1 or P2 findings.

I read the four v5 prompts, review-system-v4 and the rendered tool description, and grepped the six composed requests in audit-v5-r2.

| Prompt | Verdict |
|---|---|
| stage-1-reviewer-v5 | PASS |
| stage-1-reconciler-v5 | PASS |
| stage-2-reviewer-v5 | PASS |
| stage-2-reconciler-v5 | PASS |
| review-system-v4 | PASS |

**Round-14 fixes, checked in the text**
- **P2-1 (lumping sentence):** My replacement is in all four prompts. The reconcilers say "disputed question". It is symmetric: a coarse source shows neither sameness nor difference, and each question is settled at the level being judged. It also no longer fights the Stage 2 rule that a containing, contained or broad-region place is a different entity.
- **P3-a:** "loaded citable pages" appears in both the relied-on sentence and the `insufficient_evidence` sentence, with the empty-citations path. This is consistent with "any other page ... is never a citation".
- **P3-b and P3-d:** "its final_url belongs to a citable source" is in all four.
- **P3-c:** "A record page of a listed museum" is in all four.
- **P3-e:** The system prompt says "listed after the role prompt". The grep finds the citable-sources block, the new granularity wording, the final_url clause and the "loaded citable pages" wording in all six requests, and the block starts with `metmuseum` and ends with `whc.unesco.org` in each.

**Remaining P3**
- The prompts still say "Cite only pages ... by the URL you opened or its final_url". The code now requires both the cited URL and the final URL of the open to be on the list. A cited URL that is not itself listed but redirects to a listed host would pass the prompt and fail the code. This does not depend on case, arm or class. An optional tightening: "... by the URL you opened or its final_url; both must belong to a citable source."
- The tool description says "belongs to a citable source", which matches the prompts. You could say "its final_url belongs to a citable source" there too, for exact agreement. Cosmetic.

**Your aggregate checks** (`representation` fixed by entity type, `source_ids` differing in 2 of 11 cases, one per class) closes the metadata P3. A single ruler-class difference per class is symmetric. The stratified entity-type × class page-load gate (within 5 pp, rule committed before the run) and the role report cover item 4. As I said in round 14, that effect is a measured residual of the allowlist, not something the prompt causes.

## Round 16 (v6: Trismegistos excluded, Browserbase routing)

Round 16 (v6) verdict: PASS. There are no P0, P1 or P2 findings, so the four v5 prompts and review-system-v4 stand (they are byte-identical to round 15, as stated). I read the rendered 50-line citable block, the tool description, and the Trismegistos and browser entries in `citable-sources.json`. I did not diff the composed requests against round 15.

**1. Trismegistos removal: a measured residual, not a prompt leak or bias**
- The prompts name no source. The block is the same for every case, class and stage, and `trismegistos.org` is now gone from it. The change is also stated in `excluded_examples` with a non-class reason (subscription, IP block).
- It is class-neutral by construction. It was made before the v6 run, with no v5 results read, and applies to every case.
- Effect I expect:
  - Sites: Trismegistos was an alias-bearing source for variant Graeco-Roman and Pharaonic place names. Differing-string site cases, where the authority arm would link variant spellings, lose it, so they have fewer routes to a citable equivalence. The remaining alias sources are Pleiades, iDAI (dainst.org), TLA and the museum pages.
  - Rulers: little effect. Trismegistos was not a main source for Pharaonic ruler identity, and the ruler weakness from round 14 is unchanged.
- The stratified entity-type × class gate (each class within 5 pp of its type's citable-open loaded rate) is the correct control. Two additions I recommend:
  - Report the citation share per source domain for site cases by class, so a fall in alias-bearing citations shows up.
  - Record the removal in the README/decision-rule as a known limitation. It is a pre-registered source-scope choice, not a result.

**2. New tool-result fields: no leak**
- `browser` ("local" or "browserbase") and the opaque `browserbase_session_id` are determined by the committed per-source routing field, not by the case, arm or class. They carry no case, answer or selection information.
- A reviewer seeing `browserbase` learns only that a page from one of two named sources needed the cloud browser. The routing is identical for every case.
- The session ID is an opaque UUID. It is noise at replay, and it is already persisted with the response under rule 13.
- Two P3 notes:
  - Only two sources route to Browserbase (UCL Digital Egypt by path, pcma.uw.edu.pl). Their load success will differ from the local browser's. Include `browser` as a stratum or covariate in the page-load report, so a difference between browsers is not read as an entity-type or class effect. Digital Egypt and the Polish Centre cover particular sites, so the effect could be site-linked.
  - Tell the model nothing about `browser` in the prompts. They already do not mention it.

**3. Tool description:** the new wording ("whose final_url belongs to a citable source may be cited") agrees with the prompt text and the code gate.
