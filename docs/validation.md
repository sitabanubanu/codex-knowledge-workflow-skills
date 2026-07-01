# Validation Matrix

Default tests are offline and fixture-based. Real platform and real ASR tests
are opt-in because they depend on external sites, local media, network state,
and user authorization.

## Default Validation

```powershell
python .\kw.py demo
python .\tests\knowledge_workflow_regression.py
python .\tests\live_platform_smoke.py
python .\tests\asr_integration.py
python .\tests\real_workflow_acceptance.py
```

## Live Platform Matrix

See:

```text
validation/live_platform_matrix.csv
```

Run only after setting explicit URL environment variables:

```powershell
$env:KW_LIVE_PLATFORM_SMOKE='1'
$env:KW_YOUTUBE_WITH_SUBTITLES_URL='...'
$env:KW_YOUTUBE_WITHOUT_SUBTITLES_URL='...'
$env:KW_YOUTUBE_COOKIES_REQUIRED_URL='...'
$env:KW_X_BLOCKED_URL='...'
$env:KW_XIAOHONGSHU_BLOCKED_URL='...'
$env:KW_DOUYIN_BLOCKED_URL='...'
$env:KW_INVALID_FAILED_URL='https://example.invalid/not-a-video'
python .\tests\live_platform_smoke.py
```

## Real ASR Matrix

See:

```text
validation/real_asr_matrix.csv
```

Run only after setting explicit media environment variables:

```powershell
$env:KW_REAL_ASR_SMOKE='1'
$env:KW_REAL_ASR_MP3='C:\path\sample.mp3'
$env:KW_REAL_ASR_MP4='C:\path\sample.mp4'
python .\tests\asr_integration.py
```

Record `source_status`, transcript existence, ASR reports, quality notes, and
failure reasons for each real sample.
