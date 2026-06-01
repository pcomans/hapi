# Agent-teams playbook

Hard-learned guidance for using Claude Code's experimental agent-teams feature in this repository. Based on a single session that attempted to run three parallel Phase-0-source ingestion teammates and hit the hard limits.

## When to use — and when not to

**Use agent teams when** you have multiple truly-independent work units that:
- Each produce a separate deliverable (own PR, own files, own branch).
- Do not need to spawn further parallel workers inside themselves.
- Benefit from teammates-messaging-teammates coordination.

**Do NOT use agent teams when** a unit of work requires spawning its own parallel subagents. The canonical example in this repo is an ADR-017 Phase-0 source: its pipeline is OCR subagent + 3 parallel extraction subagents + reviewer subagent. Teammates cannot do this (see next section). Use the lead session for such work, or the lead-spawns-on-behalf workaround below.

**Decision tree:**
- One piece of work, nested parallelism required → plain `Agent` calls from the lead session.
- Many pieces of independent work, each flat (no further parallelism) → agent team.
- Many pieces of independent work, each with nested parallelism → **hybrid**: lead runs Phase-0 pipelines itself via `Agent` calls, task list tracks progress, no teammates.

## The hard limit: teammates cannot spawn subagents

This is the single most important fact about agent teams and the reason the 2026-04-16 attempt failed:

> "Teammates cannot spawn subagents, create teams, or add other teammates. The `Agent` tool, `TeamCreate`, `TeamDelete`, and `CronCreate/Delete/List` are all removed from teammates at spawn time."

The Claude Code sub-agents documentation ([docs.claude.com/en/docs/claude-code/sub-agents](https://docs.claude.com/en/docs/claude-code/sub-agents)) states that subagents cannot spawn other subagents, and that listing `Agent` in a subagent's `tools` allowlist has no effect when that definition runs as a subagent. Teammates inherit this — despite the agent-teams docs calling them "full, independent Claude Code sessions," empirically they have no `Agent` tool in their harness. No settings flag, no env var, no `tools: Agent, ...` line in a subagent definition overrides this; only main-thread agents (`claude --agent`) honour the `Agent` tool.

GitHub issues confirming: [#32731](https://github.com/anthropics/claude-code/issues/32731), [#23506](https://github.com/anthropics/claude-code/issues/23506), [#4182](https://github.com/anthropics/claude-code/issues/4182).

**Practical consequence:** ADR-017's three-independent-extraction-subagents property cannot be satisfied from within a teammate. If a teammate tries to fake it by running three sequential passes of the same model, that's correlated errors, not independent majority vote — and violates constitutional rule 1.

## Enabling agent teams

Prerequisites (both are user-local, not tracked in this repo — verify before spawning a team):
- Claude Code v2.1.32+ (check with `claude --version`).
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` exported in your shell, or set in your user-level `~/.claude.json` env block.

## Spawning teammates (canonical pattern)

Two paths:

**Natural language (docs-default):** tell Claude in the lead session "create a team with N teammates to ..." and let it compose the `TeamCreate` + `Agent` calls. Simpler, fewer knobs.

**Programmatic (explicit):** these are tool calls as they appear in the lead's harness; use JSON-object argument shape consistently.
```
TeamCreate({"team_name": "phase-0-batch-<date>", "agent_type": "team-lead", "description": "..."})
TaskCreate({"subject": "...", "description": "..."})  # repeat per task
Agent({
  "subagent_type": "general-purpose",    // or a custom .claude/agents/ definition by name
  "team_name": "phase-0-batch-<date>",
  "name": "<teammate-name>",
  "prompt": "<self-contained brief; teammate does NOT inherit lead conversation history>",
  "run_in_background": true
})
```

Notes on parameters (same `key: value` JSON shape as above):
- **Do NOT pass `"isolation": "worktree"`.** Teammates are already independent sessions. Passing worktree isolation on top is redundant at best; in the 2026-04-16 attempt, 2 of 3 teammates ended up working in the main repo tree anyway (switching its branch under the lead's feet). If you need a worktree, create it yourself before spawning and point the teammate at it via `cwd`-like instructions in the prompt — do not rely on the `isolation` parameter.
- **`"run_in_background": true`** is correct for long-running Phase-0 work; notifications arrive automatically via mailbox.
- **`"mode": "bypassPermissions"`** inherits from the lead's permission mode regardless; per-teammate modes can't be set at spawn time.
- **`"subagent_type": "general-purpose"`** gets the widest tool surface on paper (`Tools: *`) but still loses the `Agent` tool (see hard limit above). Custom `.claude/agents/` definitions honour their `tools` allowlist for teammates, but `skills` and `mcpServers` frontmatter fields are NOT applied when a subagent definition runs as a teammate.

## Pre-built teammate-ready agent definitions

The repo ships several `.claude/agents/<name>.md` definitions with `memory: project` that work both as Task-spawned subagents and as agent-team teammates (the agent-teams docs say *"the teammate honors that definition's `tools` allowlist and `model`, and the definition's body is appended to the teammate's system prompt as additional instructions"* — `skills` and `mcpServers` frontmatter fields are NOT applied when used as a teammate).

| Definition | Role | Typical use |
|---|---|---|
| `code-reviewer` | CLAUDE.md-rules compliance review | Review reviewer for any non-trivial PR. |
| `egyptologist-reviewer` | PM-faithfulness against printed source | Phase-0 source PRs; needs PDF on disk. |
| `scope-accountability-enforcer` | Audit planned PR replies for improper deferrals | Run once per review-feedback batch before posting replies. |
| `reconciliation-agent` | Drive `merge.py` + `fix_rows.py` end-to-end on a chunk | Phase-0 chunk reconciliation; reports disagreements + idempotence. |
| `cidoc-crm-validator` | CIDOC CRM 7.1.3 + CRMdig 5.0 conformance review | ADR-018 onward; run before merging claim-graph, manifest, predicate-registry, mapper, or schema changes that claim CIDOC/CRMdig compatibility. |
| `schema-reviewer` | Mechanical structural-fitness gate over `reconciled.jsonl` | Phase-0 source PRs; complements code-reviewer + egyptologist with non-overlapping scope. |
| `prompt-auditor` | Phase-0 extraction prompt audit (rule-1/7 leak detection) | Run BEFORE spawning the 3-agent extraction triplet on a new chunk prompt. |

Reference any of these by name in a teammate spawn:

```
Agent({
  "subagent_type": "schema-reviewer",
  "team_name": "phase-0-batch-<date>",
  "name": "schema-<source>",
  "prompt": "<task-specific brief; teammate doesn't inherit lead conversation history>",
  "run_in_background": true
})
```

Custom one-off agents that don't fit any of these slots: spawn `general-purpose` and pass the role-specific instructions in the prompt.

## Workaround for nested parallelism: lead-spawns-on-behalf

When a teammate's task genuinely needs ADR-017-style parallel subagents:

1. Teammate does all the preparatory work it can (scaffolding, OCR-page-range scoping, sub-PDF generation, prompt composition) and commits to its branch.
2. Teammate `SendMessage`s the lead describing exactly what subagents to spawn: prompt path, input files, output paths, expected row count.
3. Lead spawns the subagents via plain `Agent` calls (no `team_name`) pointed at the teammate's committed files; output files land in the teammate's worktree.
4. Lead `SendMessage`s the teammate "subagents done, outputs at X/Y/Z."
5. Teammate resumes with merge, reviewer pass, tests, PR.

This preserves:
- **Independence** — three real parallel subagents, not three sequential passes.
- **Teammate orchestration** — per-source worktree, branch, PR continue to live in the teammate.
- **Task-list coordination** — progress is visible in the shared task list.

Cost: lead context grows with each spawn round; keep briefs terse.

## SendMessage schema (beyond the shutdown handshake)

The shutdown handshake is the only message shape covered above. Other messages use the same outer envelope (`{"to": "<teammate-name>", "message": {...}}`) with the inner `message` carrying free-form content. The teammate sees the inner `message` as a user-turn and replies in normal Claude Code conversation form (no enforced reply schema for non-shutdown messages).

Two canonical exchanges from the lead-spawns-on-behalf workaround:

**Lead → teammate task handoff:**
```
SendMessage({
  "to": "phase-0-<source>",
  "message": {
    "type": "task_handoff",
    "subject": "subagent outputs ready",
    "files": [
      "pipeline/.../sources/<source>/raw/agent-a-chunk<N>.jsonl",
      "pipeline/.../sources/<source>/raw/agent-b-chunk<N>.jsonl",
      "pipeline/.../sources/<source>/raw/agent-c-chunk<N>.jsonl"
    ],
    "next_step": "run merge.py + fix_rows.py, report disagreements"
  }
})
```

**Teammate → lead status / blocker:**
```
SendMessage({
  "to": "lead",
  "message": {
    "type": "status",
    "task_id": "<task-id>",
    "summary": "extraction prepared; need 3 parallel general-purpose subagents",
    "request": "spawn agents A/B/C with prompt at <path>, output to raw/agent-{a,b,c}-chunk<N>.jsonl"
  }
})
```

The `type` field is convention only (the schema is free-form) but typing each message lets the recipient route it. Established conventions in this repo: `task_handoff`, `status`, `blocker`, `shutdown_request` (required schema), `shutdown_response` (required schema). The lead does not need to poll — the mailbox delivers messages as user-turns automatically.

## Shutdown and cleanup

Strict order:
1. `SendMessage({"to": "<teammate>", "message": {"type": "shutdown_request"}})` for every teammate. The `type` key lives *inside* the `message` object — passing it as a top-level argument errors on the schema. Teammate responds with `{"type": "shutdown_response", "approve": true/false, "request_id": "..."}`. Wait for approval.
2. `TeamDelete()` after all teammates are gone. Fails if any are still active.
3. Filesystem: `git worktree list` → `git worktree remove -f <path>` for each, `git branch -D <teammate-branches>`, remove any remote branches the teammates pushed.
4. Task list and team config: automatically wiped by `TeamDelete` (they live at `~/.claude/teams/{name}/` and `~/.claude/tasks/{name}/`, outside the repo).

## Cardinal mistake to avoid

**Never `rm -rf` a path that contains the lead session's working directory.** The primary working directory may itself be a worktree like `.claude/worktrees/<something>`. If the lead session's own cwd gets removed mid-cleanup, the `Bash` tool becomes unusable (every command errors `Working directory ... no longer exists`) and the only recovery is to exit and restart Claude Code from a valid directory. Before any recursive delete of `.claude/worktrees/`, confirm the lead's cwd is OUTSIDE that tree.

The 2026-04-16 session lost its shell to exactly this. `git worktree remove -f` each worktree individually; do not recursively delete the parent.

## Worked example: 3-teammate Phase-0 batch

End-to-end walkthrough for the most common pattern — three independent Phase-0 sources, each owned by a teammate. Each step is what the lead actually executes.

**1. Spawn the team:**
```
TeamCreate({
  "team_name": "phase-0-batch-2026-05-04",
  "agent_type": "team-lead",
  "description": "Phase-0 ingestion: Source A, Source B, Source C"
})
```

**2. Create one task per source on the shared task list:**
```
TaskCreate({"subject": "Phase-0 ingest: Source A", "description": "<one-line scope>"})
TaskCreate({"subject": "Phase-0 ingest: Source B", "description": "<one-line scope>"})
TaskCreate({"subject": "Phase-0 ingest: Source C", "description": "<one-line scope>"})
```

**3. Spawn one teammate per task (parallel — single message, three Agent calls):**
```
Agent({"subagent_type": "general-purpose", "team_name": "phase-0-batch-2026-05-04",
       "name": "phase-0-source-a", "run_in_background": true,
       "prompt": "<self-contained brief: source name, target pages, scaffold per playbook step 1>"})
Agent({...same shape, name: "phase-0-source-b"...})
Agent({...same shape, name: "phase-0-source-c"...})
```

**4. Teammates each scaffold + OCR + write extraction prompt; commit on per-source branch.**

**5. Each teammate hits the lead-spawns-on-behalf step (3-agent extraction needs nested parallelism, which teammates can't do):**
```
[teammate → lead]
SendMessage({"to": "lead", "message": {
  "type": "status", "task_id": "<id>",
  "summary": "extraction prepared; need 3 parallel general-purpose subagents",
  "request": "spawn agents A/B/C with prompt at <path>, output to raw/agent-{a,b,c}-chunk<N>.jsonl"
}})
```

**6. Lead spawns the 3 subagents (plain `Agent`, no `team_name`), waits, then notifies the teammate:**
```
SendMessage({"to": "phase-0-source-a", "message": {
  "type": "task_handoff", "subject": "subagent outputs ready",
  "files": ["...agent-a-chunkN.jsonl", "...agent-b-chunkN.jsonl", "...agent-c-chunkN.jsonl"],
  "next_step": "run merge.py + fix_rows.py, then reviewer passes"
}})
```

**7. Teammate runs reconciliation (the new `reconciliation-agent` definition is appropriate for this step but cannot be spawned from inside a teammate; teammate runs `merge.py` + `fix_rows.py` itself), then reviewer passes (also via lead-on-behalf), then opens PR.**

**8. Lead monitors the task list. When all three tasks are completed and PRs are open:**
```
SendMessage({"to": "phase-0-source-a", "message": {"type": "shutdown_request"}})  // ×3
[wait for shutdown_response from each]
TeamDelete()
git worktree list  // verify no orphans
```

**Total round-trip:** 3 sources × ~2 hours each, parallel, ~2 hours wall-clock for the lead (vs ~6 hours sequential). Token cost ≈ 3× a single source — see [agent team token costs](https://code.claude.com/docs/en/costs#agent-team-token-costs).

## Other notes

- Teammates load project context (CLAUDE.md, MCP servers, skills) but NOT the lead's conversation history. Briefs must be self-contained.
- Teammate idle notifications are NORMAL — not errors. "Idle" means waiting for input. Do not react to idle as if something broke; only react if the teammate messages with a specific question or blocker.
- One team per lead session. Cannot transfer leadership; the session that created the team is lead for team lifetime.
- Teammates inherit the lead's permission mode. If you ran the lead with `--dangerously-skip-permissions`, all teammates do too.
- Hook enforcement: `TeammateIdle`, `TaskCreated`, `TaskCompleted` hooks can gate teammate behaviour. See the Claude Code hooks documentation at [docs.claude.com/en/docs/claude-code/hooks](https://docs.claude.com/en/docs/claude-code/hooks).

## Known bugs to watch for

- [#40270](https://github.com/anthropics/claude-code/issues/40270) — `Agent` with `team_name` sometimes fails silently with internal error.
- [#36670](https://github.com/anthropics/claude-code/issues/36670) — teammates don't inherit `[1m]` 1M-context variant from leader; may need to pin via `model` explicitly.
- [#24316](https://github.com/anthropics/claude-code/issues/24316) — feature request: allow custom `.claude/agents/` definitions as teammates (already partially supported but with the `skills`/`mcpServers` caveat).
