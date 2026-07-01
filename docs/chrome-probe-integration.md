# Chrome Probe Integration

Chrome probe support is intentionally a two-layer workflow:

1. A browser-capable agent observes page state and writes a stable JSON contract.
2. The repository normalizes that contract into workflow artifacts.

The repository script does not control Chrome by itself.

## CLI

```powershell
python .\kw.py chrome-probe `
  --input-json .\examples\chrome_probe\chrome_observation_url_only.json `
  --project-root .\outputs\knowledge-workflow\chrome-probe-demo
```

## Important Boundary

"Chrome can play the video" is not primary material. Full analysis requires:

- exported subtitle file that can be parsed,
- exported media file that can be transcribed,
- browser-visible transcript that can be cited,
- or a confirmed public media/subtitle URL that is fetched and saved locally.

URL-only observations remain blocked or failed until the material is actually
acquired and processed.
