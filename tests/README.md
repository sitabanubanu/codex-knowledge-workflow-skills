# Knowledge Workflow Regression Tests

Run the default offline regression suite from the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python .\tests\knowledge_workflow_regression.py
```

The suite is offline and uses temporary directories. It verifies the currently
productized workflow paths:

- local transcript to `10_video/video_analysis_pack.md` and `20_document` planning artifacts
- end-to-end runner self-test coverage for URL subtitle, URL audio, URL metadata-only, URL blocked, local media, and URL resume routes
- ASR resume mode from existing ASR JSONL, including `primary_audio_asr` provenance
- Chrome probe URL-only gating, ensuring a discovered URL does not become acquired media
- platform media runner gating, ensuring acquired audio remains pending ASR and does not unlock full decomposition
- document composer source gate checks
- blocked/degraded source validation against full-pack shells

It intentionally does not test real Chrome control, live platform URLs, network
fetching, real ASR model execution, or final report drafting. Those require
separate integration fixtures and environment checks.

## Stage 8 Smoke Tests

Run the fixture-backed real-world smoke tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python .\tests\live_platform_smoke.py
python .\tests\asr_integration.py
```

These tests are deterministic by default:

- `tests/fixtures/transcript_sample.txt` covers local `.txt` transcript input.
- `tests/fixtures/subtitle_sample.srt` covers `.srt` subtitle parsing.
- `tests/fixtures/subtitle_sample.vtt` covers `.vtt` subtitle parsing.
- `tests/fixtures/fixture.mp3` and `tests/fixtures/fixture.mp4` cover local media
  routing through ASR pipeline resume mode using `asr_sample.jsonl`.
- Chrome metadata-only smoke verifies that page metadata does not create a full
  analysis pack.
- X, Xiaohongshu, and Douyin blocked fixtures verify that blocked platform
  signals stay out of full decomposition.
- Final report audit smoke verifies that `quality_gate.json` contains the final
  delivery gates before `final_report.md` is created.

Optional live platform smoke is disabled unless explicitly enabled:

```powershell
$env:KW_LIVE_PLATFORM_SMOKE='1'
$env:KW_YOUTUBE_WITH_SUBTITLES_URL='https://www.youtube.com/watch?v=...'
$env:KW_YOUTUBE_WITHOUT_SUBTITLES_URL='https://www.youtube.com/watch?v=...'
$env:KW_X_BLOCKED_URL='https://x.com/...'
$env:KW_XIAOHONGSHU_BLOCKED_URL='https://www.xiaohongshu.com/explore/...'
$env:KW_DOUYIN_BLOCKED_URL='https://www.douyin.com/...'
$env:KW_YOUTUBE_COOKIES='work/youtube-cookies/youtube.cookies.txt'
python .\tests\live_platform_smoke.py
```

Optional real ASR smoke is also disabled by default:

```powershell
$env:KW_REAL_ASR_SMOKE='1'
$env:KW_REAL_ASR_MP3='C:\path\sample.mp3'
$env:KW_REAL_ASR_MP4='C:\path\sample.mp4'
$env:KW_REAL_ASR_MODEL='tiny'
$env:KW_REAL_ASR_LANGUAGE='en'
python .\tests\asr_integration.py
```

Do not require live platform or real ASR smoke in ordinary CI unless the
environment provides the URLs, cookies handoff, media files, and ASR runtime.
