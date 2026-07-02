# Phase 2 Plan: Chinese Output And Report Quality

Phase 2 stabilizes Chinese CLI parameters, UTF-8 artifact writing, and
`--final-language zh-CN` final-report behavior.

## Carry-Forward Risks From Phase 1

These risks were found during the Phase 1 review and should be handled during
Phase 2 or Phase 3.

1. `yt-dlp-ejs` and `curl_cffi` must be installed in the actual Python runtime
   used by `yt-dlp`, not necessarily the repository virtual environment.
   `INSTALL.md` should make this explicit.
2. `sync_to_codex_skills.sh` was statically reviewed on Windows, but it still
   needs a real shell run on macOS, Linux, Git Bash, or WSL.

## Phase 2 Scope

- Preserve the source gate.
- Preserve blocked/degraded behavior.
- Preserve cookie privacy rules.
- Do not refactor `kw.py` into a package.
- Make Chinese output a first-class report path.

## Acceptance Criteria

- Chinese `document-goal` and `audience` survive through composer intake,
  commitments, quality gate, and final report.
- `--final-language zh-CN` produces a final report whose body is Chinese.
- `quality_gate.json` blocks a report when requested `zh-CN` but the report is
  effectively English.
- A local transcript regression test covers Chinese report output without using
  YouTube or any platform URL.
