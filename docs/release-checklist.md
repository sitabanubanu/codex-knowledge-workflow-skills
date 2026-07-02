# Release Checklist

Use this checklist before publishing a GitHub release.

## Local Checks

```powershell
python .\kw.py validate --include-sync
```

Confirm:

- validation summary passes,
- installed Codex skills match the repository copy,
- no generated outputs, cookies, browser data, or private source material are
  staged.

## CI Checks

Confirm GitHub Actions `offline-validation` passes for:

- Ubuntu latest,
- Windows latest,
- Python 3.10,
- Python 3.11,
- Python 3.12.

The CI workflow must stay offline. Do not add live platform URLs, cookies, real
ASR media, or browser automation to default CI.

## Release Notes

Release notes must name:

- stable path,
- experimental path,
- unsupported access-bypass behavior,
- validation evidence,
- known limits.

## Artifact

Create release archives from tracked files only, for example:

```powershell
git archive --format=zip --output=dist\release.zip HEAD
```

Do not include:

- `outputs/`,
- `test_outputs/`,
- `work/youtube-cookies/`,
- browser profiles,
- private transcripts or media.
