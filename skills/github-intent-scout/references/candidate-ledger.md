# Candidate Ledger

Use this reference to classify plausible repositories before scoring or recommending them.

## Core Rule

Do not recommend from name, description, stars, or README alone. Put plausible projects into a ledger, then check evidence as relevant.

## Ledger Table

| Candidate | Category | Stars | Updated | Host/format | Best use role | Evidence checked | Fit notes |
|---|---|---:|---|---|---|---|---|

For agent skill, plugin, MCP, sync, converter, migrator, or host-bridge tasks, add `Subtype` and `Direction` in notes when relevant. Use existing subtype labels from answer-shape routing and direction labels below.

## Candidate Categories

| Category | Meaning |
|---|---|
| `Direct` | Same mechanism and directly usable in at least one agent/tool host. |
| `Adaptable` | Close mechanism, needs glue or conversion. |
| `UnderlyingTool` | Useful component, not a skill/plugin/workflow by itself. |
| `ReferencePattern` | Useful design pattern only. |
| `NearMiss` | Adjacent but likely not worth using. |
| `Excluded` | Misleading or unsuitable. |

Treat agent host or ecosystem as an adoption note, not a core quality penalty, unless the user explicitly requires one host.

## Best Use Role

| Role | Meaning |
|---|---|
| `core-solution` | Best candidate to actually use as the main path. |
| `host-adapter` | Useful because it adapts a stronger upstream project to the user's agent host. |
| `supporting-component` | Useful for conversion, parsing, indexing, retrieval, or other sub-work. |
| `architecture-reference` | Useful design pattern, but not the main tool to install. |
| `inspiration-only` | Interesting idea; do not rely on implementation. |
| `exclude` | Do not use for this task. |

For composite recommendations, a candidate can be best in its layer even if it is not the final answer by itself.

Example layers:

- `core engine`
- `agent adapter`
- `method skill`
- `parser/converter`
- `knowledge platform`

## Portability Labels

| Portability | Meaning |
|---|---|
| `native` | Works directly in the user's requested host/tool. |
| `mostly-compatible` | Same skill/plugin style; minor path or command edits likely. |
| `portable-with-edits` | Mechanism is right but host assumptions need adaptation. |
| `component-only` | Useful parser/library/workflow, not an installable skill/plugin. |
| `rewrite-needed` | Only the idea transfers; implementation is not reusable. |

Use portability labels instead of over-penalizing ecosystem mismatch.

## Direction Labels

| Direction | Meaning |
|---|---|
| `source -> target` | Explicit conversion from one host/format to another. |
| `bidirectional` | Clear two-way conversion or sync. |
| `sync-only` | Synchronizes files without format conversion. |
| `migrator-into-host` | Imports content into one target host. |
| `from-host-supported` | Explicitly exports or converts from a named host. |
| `unknown` | Direction is unclear; do not treat as strong adaptation evidence. |

## Conversion / Sync Boundary

For agent skill, plugin, converter, sync, or migrator candidates, record these fields in Fit notes or Project Notes:

| Field | Values |
|---|---|
| Transform semantics | yes / no / partial / unknown |
| Copy or sync only | yes / no / partial / unknown |
| Host-specific rewrite | yes / no / unknown |
| Target host validation | yes / no / unknown |

Use these fields to separate real semantic conversion from file copying or host-folder sync.

## Evidence To Check

- README and docs.
- `SKILL.md`, `skill.md`, `.claude/skills`, `.codex/skills`.
- `.codex-plugin/plugin.json` or equivalent manifest.
- MCP server config, tools, connector setup, or API entry points.
- Examples, demos, screenshots, CLI commands, tests, releases.
- Dependency files and setup instructions.
- Recent commits, issue/release activity, archived status.
- Key source files when README claims need confirmation.
