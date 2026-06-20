# Answer Shape Routing

Use this reference before ranking candidates. The best answer may be a skill, plugin/MCP, library/CLI, platform, workflow, or composite toolchain.

## Core Rule

Do not force the final answer to be a skill or plugin if the evidence points to a library, platform, workflow, or toolchain. Explain the shape mismatch plainly.

## Shape Table

| Shape | Use When | Example adoption answer |
|---|---|---|
| `skill` | The user wants agent instructions, reusable workflow, or host-native skill files. | Install or port the skill. |
| `plugin-mcp` | The user needs an agent-callable tool or connector. | Add the MCP/plugin and point it at data. |
| `library-cli` | The best implementation is a package or command-line tool. | Use it as the engine behind a small skill. |
| `platform` | The user needs a hosted/self-hosted app with UI, indexing, permissions, or knowledge bases. | Deploy/use the platform. |
| `workflow` | The main value is method, protocol, checklist, or analysis structure. | Use it as the agent's procedure. |
| `composite-toolchain` | No single project covers the need; several components fit together. | Combine engine + adapter + method skill + parser. |

## Routing Questions

- Is the user asking for something installable in an agent host?
- Is the core value a callable tool, an engine, a hosted app, or a repeatable process?
- Does a candidate actually implement the mechanism, or only describe it?
- Would a library plus a thin skill be better than a host-specific low-star port?
- Is the desired result a single project or a layered toolchain?

## Adoption Guidance By Shape

| Shape | Evidence to require | Recommendation wording |
|---|---|---|
| `skill` | `SKILL.md`, references, bundled scripts/tools, examples if present. | "Port/install this skill; verify host-specific paths." |
| `plugin-mcp` | Manifest/config, server entry point, tool definitions, setup path. | "Use this connector if its data boundary and setup fit." |
| `library-cli` | Package metadata, CLI/API entry, examples, tests or import path. | "Use this as the engine; wrap it with a small workflow." |
| `platform` | Ingest/index/query pipeline, deployment, auth/storage notes. | "Use/deploy this when UI and persistence matter." |
| `workflow` | Procedure, required inputs, intermediate artifacts, verification. | "Adopt the method; implementation remains yours." |
| `composite-toolchain` | Interfaces between components, data movement, runtime requirements. | "Combine these layers; no single repo is enough." |

## Shape Drift Red Flags

- Results are all generic LLM frameworks when the user asked for installable skills/plugins.
- Results are all chat apps when the user asked for task/workflow tools.
- Results are all model orchestration when the user asked for file or terminal tools.
- The final answer assumes one answer shape while the evidence points to a toolchain.

