---
name: revise-priors
description: Halt the workflow because a load-bearing assumption (about scope, schema, source content, or constraints) needs to be revised before any further work can ship. Creates a marker file that blocks subsequent `git push`, `git commit`, `gh pr create`, and `gh pr merge` until the user reviews and resolves it. Use when you're about to invent a slip-workaround for an assumption that's wrong instead of surfacing the conflict.
---

# revise-priors

## When to use this skill

Invoke `/revise-priors` when you (parent agent or subagent) reach a point where:

- The current task's scope assumes something the data, code, or source contradicts.
- A subagent finds the schema unsuitable for the data and the right fix is bigger than the current PR.
- An audit reveals a finding that, if addressed, requires changing assumptions baked into how subsequent work was scoped.
- You're tempted to add a special-case workaround, a "TODO defer this", or a hedge in a rationale string instead of stopping and re-aligning with the user.

The signal is internal: if you catch yourself writing prose that explains why this PR is *kind of* doing the right thing under a *partially correct* assumption, that's the moment.

## What this skill does

Creates a marker file at `.claude/revise-priors/<unix-timestamp>-<short-slug>.md` containing:

- **Scope**: what task / PR / source / file you were working on
- **Assumption suspected**: the prior that's now in question
- **Evidence**: what you found that triggered the doubt (file path + line, source text, audit finding, etc.)
- **Decision needed from user**: a concrete question
- **Recommendation**: your best read of how to revise the prior, with the option you'd take if forced to choose

Marker files block any subsequent `git push`, `git commit`, `gh pr create`, or `gh pr merge` via a PreToolUse hook. The block surfaces the marker contents so the next agent (or you, in the next turn) can see why the workflow is halted.

## How to invoke

User can type `/revise-priors <one-line summary>` directly.

When you (the agent) need to invoke this from inside your work, use the `Skill` tool with `revise-priors` and pass a one-line summary as `args`. After the skill writes the marker, surface the situation to the user via `AskUserQuestion` or end-of-turn prose — don't just leave the marker on disk silently.

## How to write the marker

When invoked, write a file at the path the args dictate (or a default if not). The structure:

```markdown
# Revise priors: <one-line summary>

- **Date**: <ISO timestamp>
- **Agent**: <parent | code-reviewer | egyptologist-reviewer | scope-accountability-enforcer | general-purpose | …>
- **Triggered by**: <PR / issue / task / subagent invocation context>

## Scope

<what you were working on — be specific>

## Assumption suspected

<the prior that's now in question, in 1-2 sentences>

## Evidence

<what you found that triggered the doubt — concrete: file paths + line numbers, source quotes, audit findings>

## Decision needed from user

<a concrete question the user has to answer>

## Recommendation

<your best read, with the option you'd take if forced — but acknowledge the user may decide differently>
```

## How markers get resolved

Resolution is by the human user, not by an agent. Two paths:

1. **Dismiss** (the agent's concern was unfounded or the user wants to proceed under current assumptions): `rm .claude/revise-priors/<file>.md`. The hook then unblocks pushes/commits/PRs.
2. **Resolve** (the user has revised the prior — updated scope, changed schema, modified source assumptions): move to `.claude/revise-priors/resolved/<file>.md` after updating priors in code/docs. The audit trail persists; the hook unblocks.

When the user is going to decide via you, transparently present the marker contents and the recommendation, then ask them which path they want via `AskUserQuestion`. Do not invoke `/resolve-priors` (or its equivalent) on the user's behalf without explicit confirmation.

## Subagent guidance

If you are a subagent spawned via the `Agent` tool, you may not have direct access to invoke this skill (skills are not auto-inherited). In that case: write the marker file directly via the `Write` tool to `.claude/revise-priors/<unix-timestamp>-<short-slug>.md` using the structure above. The hook fires on the marker presence, not on the skill invocation.

## What this skill is NOT for

- Routine scope clarifications — use `AskUserQuestion` directly.
- Disagreement with a code review — push back on the comment, don't halt the workflow.
- Asking permission to ship something risky — describe the risk in the PR description and proceed; the user can revert.
- TODO bookkeeping — open a follow-up issue.

The bar is: **the assumption I'm about to violate or work around is load-bearing for the user's intent, not just for this PR's polish.**
