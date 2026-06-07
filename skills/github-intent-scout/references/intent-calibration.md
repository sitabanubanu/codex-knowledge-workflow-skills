# Intent Calibration Patterns

Use this reference when a user's words are likely overloaded across AI ecosystems.

## The Agent Ambiguity

When the user says "agent", identify which layer they mean:

1. Model role agent
   - A prompt/persona wrapped around an LLM.
   - Search terms: `multi-agent framework`, `CrewAI`, `AutoGen`, `LangGraph`, `role-playing agents`.

2. Tool/coding agent
   - A CLI/app that reads files, edits code, runs commands, uses browser/search, and has its own session.
   - Search terms: `Claude Code`, `Codex CLI`, `Gemini CLI`, `OpenCode`, `Aider`, `coding agent`, `terminal agent`.

3. Agent orchestration layer
   - A manager for multiple coding agents, usually with tasks, worktrees, logs, review, diff, PR, or dashboards.
   - Search terms: `coding agent manager`, `agent ops`, `AI coding agent workspace`, `worktree orchestrator`, `vibe kanban`, `agent session manager`.

4. Skill/config layer
   - Instructions that teach an agent a repeatable workflow.
   - Search terms: `Claude Code skill`, `Codex skill`, `.claude/skills`, `.codex/skills`, `AGENTS.md`, `CLAUDE.md`, `hooks`.

5. Protocol/runtime layer
   - Standards and transports for agent tools or agent-to-agent communication.
   - Search terms: `MCP`, `A2A`, `agent protocol`, `agent runtime`, `agent server`.

## Drift Examples

User asks: "connect several agents: supervisor, planner, worker, tester."

Possible searches:

- If they mean model roles: `multi-agent framework supervisor planner worker tester`.
- If they mean existing coding agents: `"Claude Code" "Codex" "reviewer" worktree`.
- If they mean a platform: `AI coding agent manager worktree dashboard`.
- If they mean a skill: `Claude Code skill multi-agent worktree workflow`.

Do not collapse all branches into `multi-agent framework`.

## Mechanism Translation

Translate user metaphors into mechanisms:

- "hand/feet/tools" -> file editing, shell commands, browser/search, MCP tools.
- "eyes" -> search API, browser, web retrieval, repo inspection.
- "office/workbench" -> workspace, worktree, dashboard, session manager.
- "handoff" -> task files, message bus, SQLite, comments, PR review, artifacts.
- "foreman/supervisor" -> orchestrator, manager, router, conductor, scheduler.
- "quality inspector/tester" -> reviewer, verifier, CI, test runner, gate.

Use these translations to create search families.

## Clarification Heuristic

Ask the user only when:

- The request can lead to different tool classes and the user wants implementation.
- Installing/running the wrong class would take time or money.
- The answer depends on OS or already-installed agents.

Otherwise search multiple branches and state the assumption.

## Report Failure Honestly

If early searches were biased, say:

```text
The first query family was too broad and retrieved model-role frameworks. Your intent fits coding-agent orchestration, so I pivoted to worktree/session/CLI-agent vocabulary.
```

This explanation is part of the deliverable; it teaches the user how to search better next time.
