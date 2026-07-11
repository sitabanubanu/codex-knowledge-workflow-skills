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
python -m pip install --upgrade "git+https://github.com/Panniantong/Agent-Reach.git@v1.5.0"
agent-reach install --env=auto --safe
agent-reach doctor --json
agent-reach check-update
```

Through this CLI:

```powershell
python .\kw.py agent-reach install
python .\kw.py agent-reach doctor
python .\kw.py agent-reach matrix
```

Doctor must report `status: ok` for the backend used by the requested
operation. An installed backend in `warn` state is not considered ready.

For OpenCLI routes, install its extension in the actual host browser, keep that
exact Edge or Chrome host open, sign in through your own authorized account,
and verify with:

```powershell
opencli doctor
agent-reach doctor --json
```

The upstream `v1.5.0` installer can attempt automatic Chrome/Firefox cookie
discovery for `twitter`, `bilibili`, `xueqiu`, or `all`. The `kw` wrapper
requires `--allow-upstream-cookie-import` before that route. For Edge, use an
explicit user-authorized upstream command instead:

```powershell
agent-reach configure --from-browser edge
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
python -m pip install --upgrade "git+https://github.com/Panniantong/Agent-Reach.git@v1.5.0"
agent-reach install --env=auto
agent-reach doctor --json
agent-reach check-update
```

## Verify Bundle Output

Run an acquisition:

```powershell
python .\kw.py acquire --input https://example.com --target web_article --operation read --project-root .\outputs\knowledge-workflow\example
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

## Install Workflow Skills

```powershell
.\sync_to_codex_skills.ps1 -DryRun
.\sync_to_codex_skills.ps1
.\sync_to_codex_skills.ps1 -VerifyOnly
```

The managed skills are `knowledge-workflow-console`, `agent-reach-console`,
`browser-host-identity`, `source-gated-evidence-layer`, and
`knowledge-document-composer`.
`knowledge-video-decomposer` remains a repository-internal compatibility
library and is not synced as a user-facing skill.

## Full Agent-Reach Coverage

Agent-Reach owns all 15 native channels. This project has direct structured
adapters for the high-frequency routes and an auditable native handoff for the
rest:

```powershell
python .\kw.py agent-reach matrix
python .\kw.py agent-reach import --input-file .\exports\primary.txt --source-url <original-url> --platform reddit --target social_post --operation read --browser-host edge --credentialed-session --project-root .\outputs\knowledge-workflow\reddit
```

Read [Agent-Reach integration guide](docs/agent-reach-integration-guide.md)
for the full channel map, current version policy, and import boundary.

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
