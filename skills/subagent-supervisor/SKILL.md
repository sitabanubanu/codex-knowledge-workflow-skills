---
name: subagent-supervisor
description: Supervise Codex subagent delegation, reuse, parallel work, independent review, bounded file edits, result verification, and rework. Use when deciding whether to spawn, reuse, avoid, or close subagents; when the user mentions subagent, agent, manager, supervisor, orchestrator, dispatch, delegation, reuse, parallel work, acceptance, review, rework, "do not over-spawn agents", or pinyin equivalents such as zi-agent, zhuguan, diaodu, paifa, fuyong, bingxing, yanshou, shenhe, fangong, or bu-yao-luan-kai-agent; when a task is complex enough to split; when multiple subagents may reduce time or hallucination risk; or when execution and review should be separated.
---

# Subagent Supervisor

## Overview

Use this skill as a general supervisor protocol for Codex subagents. It is independent of any single business workflow: apply it to code edits, skill creation, document work, research, audits, and multi-step projects whenever delegation, reuse, parallelism, or independent verification may affect reliability.

Using this skill does not mean a subagent must be spawned. The default mode is supervisor-only: the main agent reads the rules, decides whether delegation is justified, and keeps the work in the main thread unless the spawn gate passes.

## Supervisor Workflow

1. Read `references/spawn-gate.md` and make an explicit dispatch decision before spawning, reusing, avoiding, or closing a subagent.
2. When delegation state exists or reuse is possible, read `references/agent-registry.md` and `references/agent-lifecycle.md` before deciding.
3. Decide supervisor-only, reuse existing subagent, spawn new subagent, stop waiting, or close subagent.
4. Read `references/delegation-rules.md` to classify the task and choose the subagent role only after delegation appears justified.
5. Read `references/parallelism-patterns.md` before spawning more than one subagent.
6. Use `references/prompt-template.md` to write a bounded task prompt with clear ownership and stop conditions.
7. Require the subagent to follow `references/return-contract.md`.
8. After the subagent returns, inspect real files and outputs using `references/acceptance-checklist.md`.
9. If the result fails acceptance, follow `references/rework-protocol.md`.
10. Close completed, obsolete, unsafe, or no-longer-needed subagents.

## Role Boundary

The main agent remains the supervisor. Subagents execute, inspect, or review bounded work; they do not make final acceptance decisions. Do not trust a subagent summary by itself: verify the claimed files, content, commands, and scope before marking work complete.

## Delegation Modes

- `explorer`: read-only investigation, source checking, architecture questions, or comparison.
- `worker`: scoped file creation or editing with explicit ownership.
- `reviewer`: independent check of an artifact, plan, patch, or report.

Prefer small, independently verifiable tasks only when they are worth the coordination cost. Split write tasks by disjoint file scope. For critical work, separate execution and review.

## Reference Map

- Read `references/source-patterns.md` when updating this skill or explaining the design sources.
- Read `references/spawn-gate.md` before spawning, reusing, or explicitly choosing not to spawn a subagent.
- Read `references/agent-registry.md` when delegation state exists, reuse is possible, or a dispatch record is needed.
- Read `references/agent-lifecycle.md` before closing, replacing, stopping waits, or deciding whether a slow or obsolete subagent still matters.
- Read `references/delegation-rules.md` before deciding to spawn subagents.
- Read `references/parallelism-patterns.md` before spawning more than one subagent.
- Read `references/prompt-template.md` before writing any subagent prompt.
- Read `references/return-contract.md` when specifying subagent final response requirements.
- Read `references/acceptance-checklist.md` before accepting or rejecting returned work.
- Read `references/rework-protocol.md` when a subagent result needs correction.

## Operating Rules

- Do not spawn a subagent merely because this skill is active or the user says to use this skill for each step.
- Default to zero subagents. Spawn only when the spawn gate shows a concrete benefit over supervisor-only work.
- Make the dispatch decision explicit before spawn, reuse, supervisor-only, stop-waiting, or close actions.
- Keep a lightweight registry when delegation is used, and check it before reusing or spawning another agent.
- Keep progress audits, route choices, next-step planning, skill-rule discussions, and simple fact checks supervisor-owned unless there is a specific independent-review need.
- Reuse an existing subagent for the same task chain, file scope, or follow-up rework when continuity matters and the role still fits.
- Stop waiting on or close subagents when they are obsolete, too slow for the critical path, redirected by the user, unsafe, or no longer needed.
- Spawn subagents only for clear, bounded tasks that materially advance the work.
- Prefer at most one worker for ordinary execution. Add a reviewer only when independent verification is worth the extra cost.
- State the allowed write scope and forbidden scope in every worker prompt.
- Tell workers they are not alone in the workspace and must not revert unrelated changes.
- Do not delegate the same unresolved task twice unless the second agent has a distinct role.
- Do not redo a delegated task while it is running; do non-overlapping supervisor work.
- Verify artifacts directly after return; do not accept based on the summary alone.
- Record pass, partial, rework, or fail with evidence checked.
- Close subagents after completion.

## Minimum Acceptance

Before reporting delegated work as done, confirm:

- The subagent stayed within scope.
- Expected files or findings exist.
- Content satisfies the assigned acceptance criteria.
- Validation or relevant checks were run when applicable.
- Remaining risks are explicit.
- The next step is supervisor-owned, not silently executed by the subagent.
