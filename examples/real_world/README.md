# Real-World Validation Examples

This directory contains offline fixtures that behave like realistic user inputs
without depending on live platform state.

## Samples

- `transcript_interview.txt`: local transcript route.
- `subtitle_talk.srt`: local subtitle route.
- `long_transcript.txt`: longer transcript route.
- `batch_links.csv`: batch route covering all three local samples.

## Run The Samples

```powershell
python ..\..\kw.py run `
  --input .\transcript_interview.txt `
  --project-root ..\..\outputs\knowledge-workflow\real-world-transcript `
  --mode audit `
  --language en `
  --final-language en
```

```powershell
python ..\..\kw.py batch `
  --input .\batch_links.csv `
  --output-root ..\..\outputs\knowledge-workflow\real-world-batch
```

Start from each generated `result_index.md`. A sample is ready for reuse only
after source status is confirmed and the quality gate approves the final report.

Live video URLs are intentionally not included here because they depend on
network, account, subtitle, cookies, and platform behavior. Record those runs in
`docs/real-world-validation-log.md`.

