# Release Process

This process is for local release preparation. Do not publish a GitHub release
until tests pass and the repository owner approves the tag.

For the detailed checklist, see `docs/release-checklist.md`.

## Preflight

```powershell
git status --short
python .\kw.py validate --include-sync
```

Live platform and real ASR checks are release-candidate add-ons only when the
environment provides authorized URLs, cookies handoff, media files, and ASR
runtime:

```powershell
python .\kw.py validate --include-live-platform --include-real-asr --include-sync
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
- `sync_to_codex_skills.sh`

Do not include `outputs/`, `test_outputs/`, `cookies.txt`, local browser data,
or private source material.
