# Agent-Reach Install

Agent-Reach is an upstream capability layer. Do not copy `work/agent-reach`
into this repository as formal project code.

## Install

Use the Knowledge Workflow wrapper. It creates the shared runtime under
`C:\Users\Socrates\github-tools` and never installs into the current Python or
Hermes:

```powershell
python .\kw.py agent-reach install --safe
agent-reach --version
python .\kw.py agent-reach doctor
```

Managed layout:

```text
C:\Users\Socrates\github-tools\
  sources\Agent-Reach
  runtimes\agent-reach\venv
  bin\agent-reach.cmd
  manifests\agent-reach.json
```

## Safe Mode

Use safe mode when system-level changes should be reviewed first:

```powershell
python .\kw.py agent-reach install --safe
python .\kw.py agent-reach install --safe --dry-run
```

Safe mode should report missing requirements without automatically changing the
system.

## Update

```powershell
python .\kw.py agent-reach install --safe
agent-reach check-update
python .\kw.py agent-reach doctor
```

## Version And Doctor

```powershell
agent-reach --version
agent-reach doctor --json
```

`agent-reach doctor --json` is the health-check entrypoint for this project. It
reports channel `status`, `name`, `message`, `tier`, `backends`, and
`active_backend`.

Knowledge Workflow also records the resolved executable and runtime under
`00_acquisition/logs/agent_reach_runtime.json` for each acquisition.

## Windows Notes

- Prefer PowerShell commands shown in this repository.
- Keep command output UTF-8 safe when saving JSON or Markdown artifacts.
- Do not inspect or copy browser cookies. If a platform requires cookies, the
  user must provide an authorized export or configure Agent-Reach outside this
  repository.
- The upstream `v1.5.0` installer can auto-probe Chrome/Firefox cookies for
  some channels. Use `kw agent-reach install --safe` to review first. For an
  Edge session, use the explicit user-authorized upstream command
  `agent-reach configure --from-browser edge`.
- Never commit cookies, tokens, private logs, `outputs/`, `test_outputs/`, or
  `work/`.
