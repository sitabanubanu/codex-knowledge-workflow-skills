# Release Process

This process is for local release preparation. Do not publish a GitHub release
until tests pass and the repository owner approves the tag.

## Preflight

```powershell
git status --short
python .\kw.py demo
python .\tests\knowledge_workflow_regression.py
python .\tests\live_platform_smoke.py
python .\tests\asr_integration.py
python .\tests\real_workflow_acceptance.py
.\sync_to_codex_skills.ps1 -VerifyOnly
```

## Package Contents

Release archives should include:

- `skills/`
- `tests/`
- `examples/`
- `docs/`
- `README.md`
- `README.zh-CN.md`
- `QUICKSTART.md`
- `USER_MANUAL.md`
- `LICENSE`
- `SECURITY.md`
- `PRIVACY.md`
- `SUPPORTED_PLATFORMS.md`
- `TROUBLESHOOTING.md`
- `RELEASE_NOTES.md`
- `CHANGELOG.md`
- `kw.py`
- `sync_to_codex_skills.ps1`

Do not include `outputs/`, `test_outputs/`, `cookies.txt`, local browser data,
or private source material.
