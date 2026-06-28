# Agent Registry

Use a lightweight registry when delegation is used, especially if there may be reuse, rework, review, or closure decisions.

## Record Per Subagent

- id: stable label used in prompts and supervisor notes.
- role: explorer, worker, or reviewer.
- task chain: the parent task, handoff, or rework sequence this agent belongs to.
- read/write scope: exact files, directories, URLs, commands, or artifacts allowed.
- current status: proposed, active, waiting, returned, blocked, accepted, rework, or closed.
- reusable: yes or no, with the short reason.
- last decision: supervisor-only, reuse, spawn, close, stop waiting, rework, accept, or reject.
- close reason: required when current status is closed.

## Storage

Project logs may store this as `logs/subagent_handoffs.jsonl` or `logs/subagent_registry.md` when delegation is used. Keep records concise and update them after dispatch, return, acceptance, rework, stop-waiting, or close decisions.

## Rules

- Check the registry before spawning a new subagent.
- Reuse only when role, task chain, scope, status, and reusable flag still fit.
- Treat missing registry state as no reusable state found; do not invent continuity.
