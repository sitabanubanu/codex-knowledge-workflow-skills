# Spawn Gate

Read this before spawning, reusing, or explicitly choosing not to spawn a subagent.

## Core Rule

Using subagent-supervisor means applying a decision protocol. It does not grant a subagent budget and does not mean spawning a subagent.

The default budget is 0 subagents. Stay in supervisor-only mode unless the expected reliability, speed, or review benefit is concrete, bounded, independently verifiable, and greater than the coordination and token cost.

A new idea, phase, instruction wording, or prompt draft is not a reason to create a new agent. New agents require a new justified role or a materially different, non-overlapping scope.

## Trigger Interpretation

When the user says "use the subagent skill", "use this skill for every step", "you are the supervisor", "mei yi bu dou yong zhe ge skill", "ni shi zhuguan", or similar, interpret it as:

1. Read this skill.
2. Make an explicit delegation decision.
3. Spawn only if the decision passes this gate.

Do not interpret it as "always create a new subagent" or "create a new subagent for every prompt".

## Supervisor-Only Defaults

Do not spawn by default for:

- Project progress audits.
- Route choice or next-step planning.
- Discussion about this skill's own rules.
- Explaining why a previous delegation happened.
- Simple file checks or local status checks the supervisor can do directly.
- Acceptance summaries after the supervisor can inspect the real artifacts.
- Small single-thread edits where a subagent adds more coordination cost than value.
- Ordinary single-file edits or narrowly scoped documentation changes.
- Follow-up prompts in the same task chain, file scope, and role when an existing suitable subagent can be reused.

## Pre-Spawn Questions

Before spawning, answer these internally:

1. What exact work should a subagent do that the supervisor should not do directly?
2. Is the task bounded by clear read scope, write scope, stop conditions, and return format?
3. Is the result independently verifiable through files, commands, citations, screenshots, or logs?
4. Would delegation reduce time, context load, hallucination risk, or review risk enough to justify the cost?
5. Does the registry or current lifecycle state show an existing subagent that can continue this task?
6. Is the role distinct from current agents: explorer, worker, or reviewer?
7. If this would make more than 2 agents active or needed, what work is truly parallel and what scopes are non-overlapping?
8. Can the supervisor verify the returned result directly from real files, diffs, logs, citations, screenshots, or commands instead of trusting the summary?
9. When will the subagent be closed after return, acceptance, rework, or obsolescence?

If any answer is unclear, stay in supervisor-only mode.

If the only reason for a new agent is a freshly written prompt, stay supervisor-only or reuse the existing suitable agent.

## Reuse Gate

Reuse an existing subagent when:

- The follow-up belongs to the same task chain.
- The task uses the same file scope or artifact family.
- The same role still fits, such as worker rework after review.
- The registry and lifecycle state do not mark the subagent closed, obsolete, unsafe, or non-reusable.
- Continuity would reduce semantic drift or repeated explanation.

Same task chain plus same file scope plus same role means reuse by default. Do not spawn a duplicate agent merely to restate, refine, or continue the prompt.

Spawn a new subagent only when:

- A different role is needed, such as independent reviewer after worker output.
- The previous subagent is closed and continuity is no longer valuable.
- The task scope is materially different.
- The current subagent is blocked, unreliable, or has violated scope.

Before replacing an agent, close it or stop waiting on it according to `agent-lifecycle.md`.

## Budget

- Default: 0 subagents. This is a hard starting budget, not a suggestion.
- Ordinary single-file or narrowly bounded work: supervisor-only, or 1 worker at most if delegation clearly beats direct work.
- Same task chain, same file scope, same role: reuse the existing suitable agent instead of spawning another one.
- Reviewer: spawn only when independent review is worth the extra coordination cost and direct supervisor inspection alone is not enough for the risk level.
- More than 2 agents: allowed only with a concrete parallelism reason, named non-overlapping scopes for each agent, a reuse check showing no existing agent fits, and a close plan for every agent.

If scopes overlap, the work is sequential rather than parallel, or the benefit is only "more coverage", the gate fails.

## Required Dispatch Decision

Before each supervisor-only, reuse, spawn, close, or stop-waiting decision, be able to state:

- Decision: supervisor-only, reuse, spawn, close, or stop waiting.
- Reason: why this choice is better than the alternatives.
- Reuse Check: registry and lifecycle state checked, or no registry exists.
- Scope: what the subagent may inspect or modify.
- Agent Count: current active or waiting agents, requested total, and why this is the minimum.
- Cost Control: why the number of subagents is minimal.
- Acceptance Plan: which real files, outputs, logs, citations, screenshots, or commands the supervisor will inspect directly.
- Lifecycle Plan: when every agent will be closed or when waiting should stop.

## Post-Return Rules

After any subagent returns:

- The supervisor must inspect the real artifacts before accepting, rejecting, or requesting rework.
- A subagent summary is not acceptance evidence by itself.
- Record pass, partial, rework, or fail from supervisor-checked evidence.
- Close the returned agent after the supervisor makes the acceptance or rework decision, unless there is an explicit reuse decision for the same task chain, file scope, and role.
