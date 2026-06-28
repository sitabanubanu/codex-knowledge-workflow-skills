# Delegation Rules

## First Principle

Delegation is optional. Using subagent-supervisor means applying a supervisor decision protocol, not automatically spawning a subagent.

Read `spawn-gate.md` before spawning or reusing a subagent. If the gate does not pass, keep the task in supervisor-only mode. The default budget remains 0 subagents until the gate passes.

A new prompt is not a new agent. Reuse the same suitable agent for the same task chain, same file scope, and same role.

When delegation state exists, also check `agent-registry.md` and `agent-lifecycle.md` before reusing, replacing, closing, or waiting on a subagent.

## When to delegate

Delegate when the task benefits from bounded subagent work and the result can be verified by the supervisor:

- The task can be split into independent parts.
- Parallel work would materially reduce elapsed time or context load.
- Independent review is needed to reduce hallucination, missed defects, or confirmation bias.
- The main context burden is high enough that a focused subagent can inspect or execute more effectively.
- The user asks for supervisor, manager, orchestrator, or comparable coordination mode and the spawn gate still justifies delegation.
- Execution and acceptance should be separated.
- The output can be verified as concrete files, diffs, logs, reports, or other inspectable artifacts.

## When not to delegate

Keep the task with the main agent when delegation would add ambiguity, conflict, or unverifiable work:

- The task is a project progress audit, route choice, next-step plan, or skill-rule discussion.
- The user is asking why delegation happened or how the supervisor should behave.
- The task is small enough to complete directly.
- The task is ordinary single-file work or a narrow documentation edit that the supervisor can inspect and complete directly.
- The boundary is unclear or the supervisor cannot state a specific objective.
- Multiple agents would need to write the same file or other high-conflict surface.
- An existing suitable agent already owns the same task chain, file scope, and role.
- The work requires continuous interactive judgment by the main agent or user.
- A subagent lacks the necessary context and cannot reconstruct it from bounded inputs.
- The result cannot be checked against real artifacts, source citations, tests, or explicit acceptance criteria.

## Role selection

- Use `explorer` for read-only investigation, source discovery, architecture mapping, risk checks, or candidate comparison before any edit.
- Use `worker` for bounded creation or editing when the write scope is explicit and the output can be inspected afterward.
- Use `reviewer` for independent review of a plan, patch, artifact, report, or completed worker output.

Use at most one `worker` for ordinary single-file or narrowly bounded execution. Use a `reviewer` only when independent review is worth its cost, such as high-risk changes, broad blast radius, or user-facing artifacts where a second check is likely to catch meaningful defects.

## Reuse Rules

Prefer continuity over creating fresh subagents.

Reuse the same subagent when the next instruction is follow-up work in the same task chain, the same file scope, or the same artifact family. This is especially important for worker rework after review, because the original worker already knows the implementation context.

When a registry is available, reuse requires a matching id, role, task chain, scope, current status, reusable flag, and last decision. Do not reuse a subagent that is closed, obsolete, unsafe, outside scope, too slow for the critical path, or marked non-reusable.

Spawn a new subagent only when the role changes, the scope changes materially, the old subagent is closed or unsuitable, or an independent review is needed and worth the cost. Do not create a new subagent merely because the supervisor has written a new prompt, renamed the step, or refined the instructions.

If the same role is still appropriate and the work still touches the same file range or artifact family, reuse is the default. A supervisor who wants a new agent in that situation must first state why reuse would be unsafe or materially worse.

Close or stop waiting according to `agent-lifecycle.md` before creating a replacement or continuing supervisor-only.

## Agent Budget

Default to zero subagents.

- Ordinary single-file or narrowly bounded work: 0 subagents by default; 1 worker maximum if delegation is clearly justified.
- Same task chain, same file scope, same role: reuse the existing suitable agent.
- Reviewer: add only when independent verification is worth the coordination cost.
- More than 2 agents: require an explicit parallelism reason, non-overlapping scopes, a reuse check, and a closure plan for every agent.

Do not exceed 2 agents for sequential work, duplicate coverage, or prompt-by-prompt decomposition.

## Scope rules

- Every `worker` prompt must include an allowed write scope.
- State read scope, write scope, forbidden scope, and stop condition explicitly.
- Prefer file-level ownership for write tasks.
- Do not assign overlapping write scope to multiple active workers.
- Tell workers they are sharing the workspace and must not delete, overwrite, revert, or reformat unrelated user or peer changes.
- Use stop conditions that prevent runaway work, such as "stop after editing these files", "stop if the required file is missing", or "stop and report if the scope needs to expand".

## Supervisor obligations

The main agent remains accountable for acceptance.

- Do not accept a subagent result from its summary alone.
- Inspect the real files, diffs, outputs, citations, logs, or screenshots the subagent claims to have produced.
- Confirm the subagent stayed within scope and met the acceptance criteria.
- Run or review relevant validation when practical.
- Decide pass, partial, rework, or fail based on evidence checked by the supervisor.
- Close each returned agent after the supervisor makes the acceptance or rework decision, unless there is an explicit same-chain, same-scope, same-role reuse decision.
