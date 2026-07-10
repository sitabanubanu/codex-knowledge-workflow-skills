# Agent-Reach Install

Agent-Reach is an upstream capability layer. Do not copy `work/agent-reach`
into this repository as formal project code.

## Install

```powershell
python -m pip install https://github.com/Panniantong/Agent-Reach/archive/main.zip
agent-reach install --env=auto
agent-reach doctor --json
```

## Safe Mode

Use safe mode when system-level changes should be reviewed first:

```powershell
agent-reach install --env=auto --safe
agent-reach install --env=auto --dry-run
```

Safe mode should report missing requirements without automatically changing the
system.

## Update

```powershell
python -m pip install --upgrade https://github.com/Panniantong/Agent-Reach/archive/main.zip
agent-reach install --env=auto
agent-reach doctor --json
```

## Version And Doctor

```powershell
agent-reach --version
agent-reach doctor --json
```

`agent-reach doctor --json` is the health-check entrypoint for this project. It
reports channel `status`, `name`, `message`, `tier`, `backends`, and
`active_backend`.

## Windows Notes

- Prefer PowerShell commands shown in this repository.
- Keep command output UTF-8 safe when saving JSON or Markdown artifacts.
- Do not inspect or copy browser cookies. If a platform requires cookies, the
  user must provide an authorized export or configure Agent-Reach outside this
  repository.
- Never commit cookies, tokens, private logs, `outputs/`, `test_outputs/`, or
  `work/`.
