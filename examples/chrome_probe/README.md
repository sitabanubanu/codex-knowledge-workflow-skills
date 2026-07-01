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
