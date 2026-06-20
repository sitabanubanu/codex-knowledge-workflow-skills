# Runtime Smoke Test

Use this reference when runtime behavior affects the recommendation.

## Core Rule

Do not run every candidate by default. Escalate to a minimal task-shaped smoke test only when runtime evidence would materially change the recommendation.

## Smoke Test Gate

Run or attempt an L4 smoke test when at least one condition is true:

- The user wants to actually use/install/adopt the project now.
- The project is low-star or personal but highly matched to the user's concrete task.
- The README is empty, sparse, or mostly marketing, and code appears to be the real evidence.
- The recommendation depends on a CLI, parser, MCP server, plugin, or script actually starting successfully.
- Project claims are easy to fake and a small sample run can verify the main mechanism.
- Top candidates are close and runtime behavior is the deciding factor.

## Minimal Task-Shaped Test

- Prefer clone/install/import/run one tiny example over broad test suites.
- Use a toy input that matches the user's likely use case.
- Avoid sending private data to external APIs unless the user explicitly approves and understands the boundary.
- Avoid expensive, destructive, or long-running setup.
- If setup is heavy, inspect install instructions and mark runtime status instead.

## Blockers

If credentials, paid APIs, GPU, large models, unavailable services, OS mismatch, or heavy dependencies block the test, do not fake success. State the blocker and mark runtime status accurately.

## Runtime Status

| Runtime Status | Meaning |
|---|---|
| `SmokeTested` | A minimal install/import/run path succeeded. |
| `PartiallySmokeTested` | Some runtime path worked, but not the full claimed workflow. |
| `RuntimeBlocked` | Could not run because of credentials, OS, dependencies, cost, network, or unavailable service. |
| `RuntimeUnverified` | No runtime check was attempted. |
| `RuntimeFailed` | A reasonable minimal run failed. |

Source inspection is not equivalent to runtime verification.

