# Chrome Probe Example

This example does not control Chrome. It shows how a Chrome/page observation
contract can be normalized into workflow artifacts.

```powershell
python .\kw.py chrome-probe `
  --input-json .\examples\chrome_probe\chrome_observation_url_only.json `
  --project-root .\outputs\knowledge-workflow\chrome-probe-demo
```

Expected behavior: a URL-only observation records a possible browser-derived
media URL, but it does not become `source_confirmed` until an actual subtitle or
media file is fetched, saved locally, and parsed/transcribed.

Local exported subtitle example:

```powershell
python .\kw.py chrome-probe `
  --input-json .\examples\chrome_probe\chrome_observation_exported_subtitle.json `
  --project-root .\outputs\knowledge-workflow\chrome-probe-exported-subtitle
```

Expected behavior: the relative `exported_subtitle.vtt` path is resolved
relative to the observation JSON file, then recorded as browser-derived local
material. It still must be parsed or normalized before a full report is written.
