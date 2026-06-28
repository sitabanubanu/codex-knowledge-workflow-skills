# Source Patterns

This reference explains which external multi-agent patterns inform `subagent-supervisor`, what should be copied as protocol, what should be rejected as runtime or product surface, and how each idea becomes Codex-native subagent supervision.

## LangGraph Supervisor / langchain-ai/langgraph

### What to copy

- A central supervisor coordinates specialist workers instead of letting every agent talk to every other agent.
- Each worker should have a narrow role, clear tools or file scope, and an output that the supervisor can inspect.
- Delegation should happen through an explicit handoff: the supervisor names the worker, the task, the context, and the expected return.
- The supervisor owns global state, sequencing, and final acceptance.

### What not to copy

- Do not introduce the LangGraph runtime, graph compiler, state objects, checkpointing model, or Python/JavaScript framework APIs.
- Do not make the skill depend on LangChain tools, graph nodes, graph edges, or framework-specific message schemas.
- Do not turn Codex skill instructions into a durable workflow engine.

### How to adapt for Codex

- Treat the main Codex agent as the central supervisor.
- Treat Codex subagents as specialist workers with one bounded prompt, one allowed scope, one return contract, and an explicit stop condition.
- Express handoff in plain-language subagent prompts, not framework objects.
- Preserve the rule that the supervisor verifies real files, commands, and outputs before accepting work.

## CrewAI Hierarchical Process / crewAIInc/crewAI

### What to copy

- A manager agent can decompose work, delegate to role-specific agents, and validate returned results.
- Hierarchy is useful when a task has planning, execution, review, and correction stages.
- Delegation needs guardrails: role, objective, allowed actions, forbidden scope, expected artifacts, and completion criteria.
- A manager should decide when to run sequential work and when parallel workers are safe.

### What not to copy

- Do not introduce the CrewAI engine, crew definitions, process classes, decorators, tools, memory system, or control plane.
- Do not copy autonomous role-play behavior where workers self-delegate without supervisor permission.
- Do not add a separate manager runtime inside the skill.

### How to adapt for Codex

- Use hierarchy as a supervision rule: the main agent plans, assigns, verifies, and either accepts or requests rework.
- Keep worker autonomy bounded to the prompt and write scope the supervisor grants.
- Require every worker prompt to include guardrails for files, commands, assumptions, and final response fields.
- Use sequential mode for dependent steps and parallel mode only for disjoint scopes or independent reviews.

## OpenAI Swarm / openai/swarm

### What to copy

- Handoff should be lightweight, explicit, and easy to reason about.
- Agent coordination can be represented by simple routines: do the current task, hand off when another role is better, return control to the caller.
- The useful abstraction is not a heavy platform; it is a clear transition from one responsible agent to another.

### What not to copy

- Do not introduce the Swarm SDK, client loop, handoff functions, or Python package.
- Do not make agents recursively hand off to each other.
- Do not create an open-ended agent network where the supervisor loses the thread of ownership.

### How to adapt for Codex

- Model handoff as a one-shot subagent assignment created by the supervisor.
- The supervisor states why the handoff is needed, what the subagent owns, and when control returns.
- Workers should not spawn further workers unless the user explicitly asked for that mode and the supervisor authorizes it.
- Keep handoff records in the conversation and final summary, not in framework state.

## AutoGen SelectorGroupChat / microsoft/autogen

### What to copy

- Worker selection should be deliberate: choose the next agent based on task state, role fit, available context, and remaining risk.
- Speaker selection is a useful concept for deciding whether the next action belongs to an explorer, worker, reviewer, or the main supervisor.
- Candidate filtering matters: only agents with relevant scope should be considered.
- Termination conditions matter: every delegated run needs a clear return point.

### What not to copy

- Do not create free-form group chat between subagents.
- Do not allow agents to debate indefinitely, select speakers without supervisor approval, or continue after the assigned stop condition.
- Do not copy AutoGen's conversation runtime, group manager, message loop, or speaker-selection APIs.

### How to adapt for Codex

- Replace speaker selection with supervisor selection: the main agent chooses exactly which role runs next.
- Use three stable Codex modes: `explorer`, `worker`, and `reviewer`.
- Before spawning a subagent, check whether the task is independent, bounded, and worth delegation.
- End each delegated turn when the return contract is satisfied or when a blocker is reported.

## AlexWortega/ai-peer-review-skill

### What to copy

- Independent parallel reviewers reduce shared blind spots when evaluating the same artifact.
- Reviewers should work separately, then the main thread synthesizes common findings, unique findings, disagreements, and final judgment.
- A meta-review is stronger when it ranks issues by usefulness or severity instead of merely merging reviewer prose.
- Reviewer identity can be role-based rather than person-based, so each reviewer checks a different angle.

### What not to copy

- Do not limit the pattern to academic papers.
- Do not copy the paper-specific extraction pipeline, reviewer personas, CSV concern matrix, or result bundle format.
- Do not let reviewer agents make final acceptance decisions.

### How to adapt for Codex

- Add a reviewer mode for independent checks of code changes, skill documents, plans, research notes, or generated artifacts.
- Run reviewers in parallel only when they can inspect the same artifact without writing to it.
- Require reviewers to return findings, evidence, severity, confidence, test gaps, and residual risk.
- The main supervisor performs the meta-review and decides pass, partial, rework, or fail.

## jnopareboateng/codex-claude-subagents

### What to copy

- Workers need explicit write scope. If no write scope is granted, they should be read-only.
- Every worker summary should identify outcome, files inspected, files changed, verification, risks, and next steps.
- Run logs and summaries are useful because the supervisor must verify what happened, not trust vague claims.
- Prompts should remind workers that they are not alone in the workspace and must not revert unrelated changes.

### What not to copy

- Do not use the Claude CLI launcher, Claude-specific session management, or `.agent-runs/claude` implementation.
- Do not require external resumable sessions, shell wrappers, or gitignored log directories as part of this skill.
- Do not assume the worker is Claude; this skill is for Codex-native subagents.

### How to adapt for Codex

- Turn the launcher contract into prompt rules and return-contract rules.
- In every worker prompt, specify allowed files, forbidden files, whether edits are permitted, and what validation is expected.
- Require the final worker response to list inspected and changed files so the supervisor can verify directly.
- Keep logs lightweight: use conversation summaries and checked artifacts unless the user asks for persistent run logs.

## Yeachan-Heo/oh-my-claudecode

### What to copy

- Team-first orchestration: multiple specialized agents can work from a shared task list when roles are separated.
- Role separation helps avoid one agent mixing architecture, implementation, testing, and review responsibilities.
- Session summaries and replay-style traces are useful as audit concepts: the supervisor should know who did what and why.
- Commands, skills, and reusable role patterns can make delegation faster and more consistent.

### What not to copy

- Do not build a dashboard, HUD, tmux team runner, notification system, rate-limit monitor, memory layer, or platform wrapper.
- Do not copy Claude-specific commands, model matrices, session directories, or long-running autonomous modes.
- Do not make `subagent-supervisor` a team operating system.

### How to adapt for Codex

- Keep the team idea as a lightweight role taxonomy inside the skill.
- Use `explorer`, `worker`, and `reviewer` as stable roles instead of many named teammates.
- Preserve auditability through explicit prompts, scoped assignments, return contracts, and supervisor verification notes.
- Prefer short-lived subagents that close after completion.

## cft0808/edict

### What to copy

- Strong role separation can create checks and balances: planning, dispatch, execution, review, and veto are different responsibilities.
- A visible task state model helps prevent invalid jumps from request to completion.
- Audit trails are valuable when multiple agents touch a project.
- Specialized agents should have clear permissions and communication boundaries.

### What not to copy

- Do not copy the dashboard, event bus, Redis streams, state-machine scripts, model configuration UI, permission platform, or ceremonial product layer.
- Do not create a large multi-agent bureaucracy for ordinary Codex tasks.
- Do not introduce persistent services, agent registries, or cross-agent communication infrastructure.

### How to adapt for Codex

- Translate checks and balances into lightweight gates: classify, delegate, verify, rework, accept.
- Use task status labels such as pass, partial, rework, or fail after inspecting evidence.
- Keep permission boundaries prompt-level and file-scope-level.
- Escalate to multiple agents only when risk, scope, or independence justifies it.

## Design Transfer Summary

The final rules transferred into `subagent-supervisor` are:

- The main Codex agent is always the supervisor and keeps final acceptance authority.
- Spawn subagents only for bounded work that materially improves reliability, speed, or independence.
- Use three Codex-native delegation modes: `explorer` for read-only investigation, `worker` for scoped edits, and `reviewer` for independent critique.
- Every handoff must state role, task, context, allowed scope, forbidden scope, expected output, validation expectations, and stop condition.
- Workers do not self-delegate, expand scope, or continue after the return contract is satisfied.
- Parallelism is allowed only for independent read-only work, disjoint write scopes, or independent reviewers.
- Shared mutable files require sequential execution unless the supervisor can prove non-overlap.
- Reviewer mode copies the peer-review pattern: independent reviewers return evidence-backed findings, and the supervisor performs the meta-review.
- Every worker or reviewer final response must expose outcome, files inspected, files changed, verification, risks, and next step.
- The supervisor must inspect real files, outputs, commands, or artifacts before reporting a subagent result as accepted.
- Rework is supervisor-directed: identify failed acceptance criteria, issue a narrower correction prompt, and verify again.
- Do not import external agent frameworks, SDKs, dashboards, launchers, event buses, memory layers, or long-running autonomous team platforms.
