# Handoff: proving the authority layer on rulers (and next, locations)

_Snapshot: 2026-11-04, after #388. Read this before touching `pipeline/pipeline/enrich/`,
`pipeline/pipeline/authority/{graph_kings,king_context,royal_women}.py`, or any
`docs/evaluations/ruler-*` tree. It follows `handoff-site-graph-v0.md`, which covers #326–#337._

## The goal

Hapi is a single index over many museums' Egyptian collections. Objects that belong together
should come up together even when each museum spells the name differently ("Sesostris I",
"Senwosret I", "Senusret I"). The authority layer does that: it links each museum's ruler and
place mentions to canonical entities (the claim graph's kings, Dodson & Hilton's royal women,
iDAI sites, Porter & Moss tombs). The current work is to **prove those links are right**, museum
by museum, and fix what is wrong or missing. Rulers first, then locations.

## How the owner works (follow these)

- **Plain language, first principles.** The owner is not a programmer and has said "I'm pretty
  lost" and "I don't understand what that means dude". Explain without jargon (no "scope",
  "transition", "arm", "calibration" unexplained). Give a tl;dr when asked. Define any coined term
  the first time ("decoys" needed explaining).
- **Proceed without asking** on agreed next steps. Use AskUserQuestion only for real decisions, in
  plain words, with a recommended option. Don't ask what you can find out yourself.
- **Ignore the website** (`web/`) until told otherwise: no web work or web next steps. Keep CI green
  and Drizzle introspection current, nothing more.
- **Evaluate each museum against the authority**, not museum pairs against plain text. A pairwise
  test left most pairs undecidable and confused the owner.
- **Matching kings by name alone is "amateur level".** King links must use the record's dynasty and
  date (done in #388).
- **Usage limits:** on a usage or rate limit, stop and tell the owner. Never switch models to get
  around it. Paid API runs need approval; subscription (Claude Code harness) runs are free.
- **Merging is your job.** Push, open the PR, and merge once:
  - the local `code-reviewer` subagent has no blocker (it is the review of record; Codex is often
    over quota);
  - CI is green;
  - every Codex inline comment has a reply. Before each batch of replies, run the
    `scope-accountability-enforcer` subagent once, and prefix the replies with `SCOPE_CHECKED=1`.

  For anything historical, also run the `egyptologist-reviewer`. It caught real errors in #388.
- **`gh`:** prefix every call with
  `GH_TOKEN=$(printf 'protocol=https\nhost=github.com\n\n' | git credential fill | sed -n 's/^password=//p')`.
  Never print, save or export the token, and never `gh auth login`.
- **Database:** Neon, through the Vercel project web-claim-graph-hapi (`vercel env pull` in
  `web-claimgraph/`, then use `DATABASE_URL_UNPOOLED` as `DATABASE_URL`).

## Where things are

- **Code.** The repo is github.com/pcomans/hapi. `/workspaces/content` is the main checkout, but it
  sits on an unrelated branch and has uncommitted agent-memory files; don't use it for this work.
  This work happened in the worktree `/workspaces/hapi-338`: start a fresh branch from
  `origin/main` there, or make a new worktree.
- **Private data** (museum text, never committed), in `/workspaces/content/dropbox/`:
  - `hapi-museum-corpus-2026-08-27.tar.gz`: the frozen Met, Brooklyn and Harvard corpus.
  - `hapi-added-museums-2026-10-16/…tar.gz`: Cleveland's and the Walters' raw tables.
  - `hapi-ruler-per-museum-2026-10-17/`: the per-museum test's run, queues, private answer key,
    720 stored calls, fix list and logs.
  - `hapi-ruler-reregistration-2026-10-16/`, `hapi-361-*`: earlier registrations.
- **Browserbase key** (`BROWSERBASE_API_KEY`, needed by `open_page` for a few sources). It was
  kept in a session scratchpad, `/tmp/claude-1000/-workspaces-content/e94d96de-5992-406d-a8e0-26faf505e839/scratchpad/browserbase.env`.
  Scratchpads are per session, so if that file is gone, ask the owner for the key. Never commit it.
- **Review runtime:** each evaluation has `runtime/` (pyproject plus uv.lock). Run `uv sync --frozen`
  there. Claude Code releases are installed under `~/.local/share/claude/versions/`, and the review
  pins one by path.

## What happened (in order)

| PR | What | Result |
|---|---|---|
| #372–#378 | #338: museum mentions to authority links in the pipeline (`enrich/authority_links.py`, `link_files.py`, `cross_museum.py`), on Neon | proven equal to #337/#361 on the frozen corpus |
| #380, #381 | Added Cleveland and the Walters (CC0) | resolver deliberately *not* tuned on their spellings |
| #382, #383 | Ruler re-registration, pairwise vs plain text, 87 cases | only Met–Walters decidable, and it qualified (`QUALIFIED_SCOPES["ruler"]`) |
| #386, #387 | **Per-museum ruler test.** Every distinct link (174) and miss (161), 20 hidden decoys, two reviewers plus a reconciler | all 20 decoys rejected. Brooklyn, Cleveland, Harvard and the Walters pass (no wrong link). The Met fails on 2 wrong links of 107: "Aya" and "Mentuhotep III" |
| #388 | **Kings resolved in their record's context** (`authority/king_context.py`) | 7 wrong Aya links removed, 2 Teti gained, 1 Amenhotep II dropped; no change outside the Met |

### The #388 rule, which you must keep consistent

- The record's single dynasty chooses among kings of one name.
- A king *clashes* with a record only when the dynasty **and** the date both disagree (date more
  than 50 years outside his reign). Either alone is not enough: dynasty numbers depend on the
  chronology a museum follows (Takeloth II: Met 23, three of four king lists 22), and museum dates
  are loose. This was the owner's choice, after the Egyptology review.
- A **reign field** drops a clashing king. A **title** or royal-woman cue never does: objects can
  postdate the king they name. The exception is a king the same record's reign field dropped.
- With no context, a name links only when exactly one king has it.
- Dates do not break ties.
- `graph_kings.KNOWN_REVERSED_REIGNS = {kitchen-21H.06}` is the only reversed reign excused; any
  other raises (#391).

Measurement: `docs/evaluations/king-context-2026-10-17/`. #338's proof was re-run
(`authority-bridge-338/results/rerun-after-king-context/`), and tests pin it.

## What's next, in recommended order

1. **Merge duplicate king entries, with identity checks.** 56 of the 59 king mentions still
   ambiguous have candidates sharing a label: Djoser 48, Shabaka 2, and one each of Iuput II,
   Sobekhotep III, Xerxes I, Smendes I, Menkheperre and Alexander the Great. Most are one king
   entered by two king lists, **but not all**:
   - "Menkheperre" there is the High Priest of Amun (Leprohon 21a.02, Kitchen 21H.07), and a bare
     "Menkheperre" in museum records usually means Thutmose III;
   - pharaoh.se's Shoshenq VI is not Kitchen's.

   So each merge needs a sourced identity decision, not a label match. See the claim-graph
   matcher/escalation work in `docs/evaluations/ruler-escalation-queue/` and
   `ruler-cluster-reconciliation-342/`.
2. **Sourced spellings for the fix list.** The fix list is `dropbox/hapi-ruler-per-museum-2026-10-17/records/fix-list.json`:
   99 texts naming one ruler, on 316 records. The largest are Djoser, Ahmose I, Shabaqo,
   Khasekhemui, Sebekhotep IV, Thutmosis III and Ptolemy II. Some name queens or high priests the
   authority may rightly not hold as kings. Every alias needs a source on disk (constitutional
   rule 1); "the model knows" is not a source. #370 already covers Amasis/"Ahmose II" and Taa/Tao.
3. **#389, the Met's "Mentuhotep III."** Some of its records are Nebhepetre Mentuhotep II's. The
   context rule can't catch it (same dynasty), so research how the Met numbers them.
4. **Re-test the Met** with the per-museum test. Copy `ruler-per-museum-2026-10-17/` to a new dated
   directory, rebuild the run and queues, re-audit any prompt change with `prompt-auditor`, and get
   the owner's approval before any model call.
   - **Tuned-on records** are counted apart: the 7 Aya records, 2 Teti, met-549239, and whatever
     the fixes above touch.
5. **Locations, the same way.** The Met, Brooklyn and Harvard have site links (#337 qualified
   them pairwise). Cleveland's places sit in `culture` and aren't read (#379). The Walters has no
   place field at all.
6. **Housekeeping issues:**
   - #385: move `QUALIFIED_SCOPES` out of the resolver-version digest. Any edit to
     `authority_links.py` changes every link's version.
   - #390: list every reign-field drop when a museum is added.
   - #391: carry Kitchen's corrected reign into the graph.
   - #374, #375: ingest housekeeping.

## Lessons that cost time

- **Review runs.**
  - Each `xvfb-run` per call leaked an Xvfb. 1,738 of them filled the container's 2,048-process
    limit, and the browser silently failed (2026-10-16 run). The per-museum runner starts one
    display per run (`run_harness_review.virtual_display`). Check `pgrep -c Xvfb` before long runs.
  - Claude Code auto-updated mid-run. Pin the release by path, with `DISABLE_AUTOUPDATER=1`.
  - Never move or delete a stored LLM call (rule 13). Use the committed `set-asides.json` ledger
    and disclose every entry. The scorer requires attempts numbered 1..n.
  - Fix in advance, and get approval for, what happens when a call gives no answer
    (`decision-rule.md`, "Calls that give no answer").
- **Measuring a resolver change.**
  - Compare **record links** (`build_links`), not only mention rows: one record kept a wrong link
    through a second mention.
  - Compare an unresolved row's candidates (`row["resolution"]["target_ids"]`). Otherwise a
    narrowing that stays ambiguous is invisible.
  - Re-run `authority-bridge-338/scripts/check_promotion.py` and `run_end_to_end.py` after any edit
    to the resolution code. Their README requires it, and tests pin each re-run.
- **Fail loud, narrowly.** Excuse a known bad source row by its ID, never with a generic filter
  that would hide the next one (the scope check caught this).
- **Write-ups.** Write-ups were caught three times overclaiming, so state only what the reviewers'
  records show:
  - "most" when it was 3 of 6;
  - an unsourced "older numbering";
  - "links are right" when the rule only says "no wrong link found".

  Never quote museum text beyond short ruler names in the repo.
