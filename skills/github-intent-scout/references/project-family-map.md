# Project Family Map

Use this reference when multiple candidates share a concept, naming pattern, README phrasing, architecture, or explicit acknowledgements.

## Core Rule

Map families before ranking so the scout does not double-count the same idea or let a weak host-port outrank a stronger upstream solely because it names the user's host.

## Family Map

| Project | Family role | Relationship evidence | Practical consequence |
|---|---|---|---|

## Family Roles

| Role | Meaning |
|---|---|
| `origin` | Likely original or strongest upstream. |
| `fork` | GitHub fork or direct copy. |
| `host-port` | Adaptation to another agent host, CLI, model, or runtime. |
| `model-port` | Same idea bound to a different model/provider. |
| `architecture-descendant` | Reuses the architecture in another domain. |
| `parallel` | Similar solution without clear lineage. |
| `unrelated-name-match` | Name or terms overlap but mechanism differs. |

Use the family map to prefer mature upstreams for trust, host-ports for installation clues, and architecture-descendants for design ideas.

## Adapter Upstream Strength

For low-star adapters, wrappers, MCP servers, or host ports, score wrapper and upstream separately:

| Adapter Check | What To Ask |
|---|---|
| Upstream strength | Is the wrapped library/platform mature, maintained, licensed, documented, and fit for the mechanism? |
| Wrapper thinness | Is the adapter mostly configuration/glue, or does it add complex fragile behavior? |
| Interface clarity | Are commands, config, environment variables, indexing paths, and failure modes documented? |
| Version pinning | Does the adapter pin compatible upstream versions or explain supported ranges? |
| Data boundary | Does the adapter clearly state what data goes local, to APIs, or to external services? |

Do not reject a thin adapter only because it has few stars if it wraps a strong upstream and has clear setup. Label adapter maturity risk separately from upstream strength.

