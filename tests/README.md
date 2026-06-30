# Knowledge Workflow Regression Tests

Run from the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python .\tests\knowledge_workflow_regression.py
```

The suite is offline and uses temporary directories. It verifies the currently
productized workflow paths:

- local transcript to `10_video/video_analysis_pack.md` and `20_document` planning artifacts
- ASR resume mode from existing ASR JSONL, including `primary_audio_asr` provenance
- Chrome probe URL-only gating, ensuring a discovered URL does not become acquired media
- document composer source gate checks
- blocked/degraded source validation against full-pack shells

It intentionally does not test real Chrome control, live platform URLs, network
fetching, real ASR model execution, or final report drafting. Those require
separate integration fixtures and environment checks.
