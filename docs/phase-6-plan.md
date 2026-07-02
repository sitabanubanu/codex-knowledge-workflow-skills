# Phase 6 Plan: Chrome Probe Integration

## Goal

Make Chrome/page observations usable without pretending the repository controls
Chrome or that page playback is primary material.

## Scope

- Preserve the two-layer model: browser-capable agent observes; repository
  normalizes.
- Keep URL-only candidates blocked from full source confirmation.
- Resolve relative local files in observation JSON relative to that JSON file.
- Add a local exported subtitle example.
- Add regression coverage for the CLI wrapper and relative file handoff.

## Out Of Scope

- No direct Chrome automation in repository scripts.
- No cookie extraction.
- No platform bypassing.
- No full report from page metadata, screenshots, or candidate URLs alone.

## Measures

- URL-only public media/subtitle candidates remain unconfirmed until fetched and
  processed.
- Local exported subtitle/media files are detected only when the file exists.
- Missing local files do not unlock browser-derived media.
- `kw.py chrome-probe` writes normalized artifacts and refreshes the project
  result index.

## Validation

- Run `chrome_media_probe.py --self-test`.
- Run the URL-only example.
- Run the exported subtitle example through `kw.py chrome-probe`.
- Run the full offline regression suite.
