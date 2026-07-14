# ADR 0003: Isolate The Shared Agent-Reach Runtime

## Decision

Knowledge Workflow manages Agent-Reach as a shared external runtime under:

```text
C:\Users\Socrates\github-tools
```

The Agent-Reach source project, Python environment, command shim, and install
manifest are kept in separate subdirectories. Knowledge Workflow resolves the
Agent-Reach executable by explicit runtime path and rejects Hermes-private
paths.

## Context

The previous installer used `sys.executable -m pip`. On this machine, the
current Python resolved to the Hermes virtual environment, so Agent-Reach was
installed into Hermes. This coupled acquisition to one agent's private runtime.

## Layout

```text
github-tools/
  sources/Agent-Reach
  runtimes/agent-reach/venv
  bin/agent-reach.cmd
  manifests/agent-reach.json
  cache/
```

Agent-Reach configuration and authorized browser integration remain under the
user-level `.agent-reach` directory. Cookies, tokens, and browser profiles are
not copied into `github-tools`.

## Consequences

- Codex, Hermes, Claude, and Knowledge Workflow can share one Agent-Reach CLI.
- PATH order and the launching agent's `sys.executable` no longer select the
  Agent-Reach Python environment.
- `kw agent-reach doctor` records the runtime location for auditability.
- The upstream package remains external and pinned to `v1.5.0`.
- Other projects downloaded manually with `git clone` are not automatically
  redirected; only tools managed by this project's installer use this policy.

## Validation

- The standalone executable is outside `.hermes`.
- The standalone Python package is outside `.hermes`.
- The resolver rejects a Hermes executable.
- Offline workflow tests and Agent-Reach doctor/matrix checks pass.
