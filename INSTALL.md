# Installation

## Repository

```powershell
git clone https://github.com/sitabanubanu/codex-knowledge-workflow-skills.git
cd codex-knowledge-workflow-skills
python -m pip install -e .
```

You can also run through the wrapper without installing:

```powershell
python .\kw.py demo
```

## Agent-Reach

Agent-Reach is the acquisition layer. Install it separately; do not commit
`work/agent-reach` as a project dependency.

```powershell
python -m pip install https://github.com/Panniantong/Agent-Reach/archive/main.zip
agent-reach install --env=auto
agent-reach doctor --json
```

Through this CLI:

```powershell
python .\kw.py agent-reach install
python .\kw.py agent-reach doctor
```

## Safe Mode

Use safe mode when you want to review system changes first:

```powershell
agent-reach install --env=auto --safe
agent-reach install --env=auto --dry-run
python .\kw.py agent-reach install --safe
```

## Update Agent-Reach

```powershell
python -m pip install --upgrade https://github.com/Panniantong/Agent-Reach/archive/main.zip
agent-reach install --env=auto
agent-reach doctor --json
```

## Verify Bundle Output

Run an acquisition:

```powershell
python .\kw.py acquire --input https://example.com --project-root .\outputs\knowledge-workflow\example
python .\kw.py validate-bundle --bundle .\outputs\knowledge-workflow\example\00_acquisition\manifest.json
```

Expected stable output:

```text
00_acquisition/manifest.json
```

Then ingest:

```powershell
python .\kw.py ingest --bundle .\outputs\knowledge-workflow\example\00_acquisition\manifest.json --project-root .\outputs\knowledge-workflow\example
```

## Cookie And Token Safety

- Do not commit cookies, tokens, Authorization headers, or private logs.
- Do not paste cookie values into issues, reports, manifests, or command logs.
- `commands.jsonl` must record only redacted command summaries and exit codes.
- `manifest.json` may record `cookies_used=true`, never cookie contents.

## Windows Notes

- Use PowerShell examples from this repository.
- Keep generated Chinese and Markdown files UTF-8 encoded.
- Do not use `work/` as formal project code.
- `outputs/` and `test_outputs/` are generated directories and should stay out
  of commits.
