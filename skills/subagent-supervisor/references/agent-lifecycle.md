# Agent Lifecycle

Use this before waiting, reusing, closing, replacing, or stopping attention on a subagent.

## Close Or Stop Waiting When

- The user redirects the task or changes priority.
- The delegated task becomes obsolete.
- The worker times out or is too slow for the critical path.
- The supervisor solves the scope directly.
- The agent violates read/write scope or workspace safety rules.
- Independent review is no longer needed.
- The agent has returned and the supervisor has made the acceptance or rework decision, unless the supervisor makes an explicit same-chain, same-scope, same-role reuse decision.

## Close Record

When closing, record the id, status `closed`, close reason, and last decision. If stopping the wait without closing, record the reason and the safe next owner.

## Rules

- Do not keep waiting just because an agent exists.
- Do not spawn a replacement without a dispatch decision and reuse check.
- Keep a returned agent open only when reuse is explicit, immediate, and matches the same task chain, file scope, and role.
- If a late result arrives after closure, treat it as advisory and verify before using it.
